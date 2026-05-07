import json
from datetime import datetime
from typing import Literal

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt
from pydantic import BaseModel, Field

# load_dotenv must run before ChatGroq() instantiation reads GROQ_API_KEY
load_dotenv()

from .state import AgentState
from .tools import (
    get_account_info,
    get_order_info,
    search_knowledge_base,
    update_crm,
    send_customer_email,
    create_escalation_ticket,
)

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)


class TicketClassification(BaseModel):
    urgency: Literal["low", "medium", "high", "critical"] = Field(
        description=(
            "low=general question, medium=partial issue, "
            "high=major feature broken or payment issue, "
            "critical=security breach / data loss / complete outage"
        )
    )
    category: Literal["billing", "technical", "account", "shipping", "general"] = Field(
        description="The primary type of issue"
    )
    summary: str = Field(description="One sentence — what is the customer's core problem?")
    keywords: list[str] = Field(description="3-6 key terms that describe the issue, used for KB search")


class ResolutionDecision(BaseModel):
    decision: Literal["auto_resolve", "clarify", "escalate"] = Field(
        description=(
            "auto_resolve = clear solution exists, send it now. "
            "clarify = need more info from customer before resolving. "
            "escalate = too complex / risky / sensitive for AI — needs human agent."
        )
    )
    reasoning: str = Field(description="One sentence explaining why you made this decision")
    email_subject: str = Field(description="Subject line for the outgoing customer email")


def classify_node(state: AgentState) -> dict:
    ticket = state["ticket"]
    timestamp = _now()

    classifier = llm.with_structured_output(TicketClassification)
    result = classifier.invoke([
        SystemMessage(content="""You are a customer support triage specialist.
Classify incoming support tickets by urgency and category.

Urgency rules:
- critical: account compromised, data breach, total service outage for a paying customer
- high: major feature broken, payment failure, account locked, angry repeat contact
- medium: partial functionality issue, billing question, general configuration help
- low: how-to question, minor inconvenience, feature request"""),
        HumanMessage(content=(
            f"Ticket ID: {ticket['id']}\n"
            f"Customer ID: {ticket['customer_id']}\n"
            f"Subject: {ticket['subject']}\n"
            f"Body:\n{ticket['body']}"
        )),
    ])

    print(f"\n[classify] urgency={result.urgency}  category={result.category}")
    print(f"[classify] summary: {result.summary}")

    return {
        "classification": {
            "urgency": result.urgency,
            "category": result.category,
            "summary": result.summary,
            "keywords": result.keywords,
        },
        "audit_log": [
            f"[{timestamp}] CLASSIFY → urgency={result.urgency}  category={result.category}"
        ],
    }


def investigate_node(state: AgentState) -> dict:
    ticket = state["ticket"]
    timestamp = _now()

    account_info = get_account_info(ticket["customer_id"])
    order_info = get_order_info(ticket["order_id"]) if ticket.get("order_id") else None

    print(f"\n[investigate] account={account_info.get('name', '?')}  plan={account_info.get('plan', '?')}")
    if order_info:
        print(f"[investigate] order status={order_info.get('status', '?')}")

    return {
        "account_info": account_info,
        "order_info": order_info,
        "audit_log": [
            f"[{timestamp}] INVESTIGATE → account fetched, order={'fetched' if order_info else 'N/A'}"
        ],
    }


def search_kb_node(state: AgentState) -> dict:
    classification = state["classification"]
    timestamp = _now()

    articles = search_knowledge_base(
        category=classification["category"],
        keywords=classification.get("keywords", []),
    )

    print(f"\n[search_kb] found {len(articles)} relevant articles")
    for a in articles:
        print(f"  → {a['id']}: {a['title']}")

    return {
        "kb_articles": articles,
        "audit_log": [f"[{timestamp}] SEARCH KB → {len(articles)} articles found"],
    }


def draft_node(state: AgentState) -> dict:
    ticket = state["ticket"]
    classification = state["classification"]
    account_info = state["account_info"] or {}
    order_info = state["order_info"]
    kb_articles = state["kb_articles"] or []
    timestamp = _now()

    kb_context = "\n\n".join(
        f"[{a['id']}] {a['title']}:\n{a['content']}"
        for a in kb_articles[:2]
    )
    order_section = (
        f"\nOrder on file:\n{json.dumps(order_info, indent=2)}" if order_info else ""
    )

    response = llm.invoke([
        SystemMessage(content="""You are a senior customer support specialist.
Write a professional, empathetic, and specific resolution email body.
- Reference the customer's actual situation (plan, order status, etc.)
- Give concrete steps they can take right now
- Be concise: 2-4 short paragraphs
- Do NOT include greeting or sign-off — those are added separately
- Do NOT make promises you can't keep unless the KB explicitly states a timeframe"""),
        HumanMessage(content=(
            f"TICKET\n"
            f"Subject: {ticket['subject']}\n"
            f"Issue: {ticket['body']}\n\n"
            f"CUSTOMER CONTEXT\n"
            f"Name: {account_info.get('name', 'Valued Customer')}\n"
            f"Plan: {account_info.get('plan', 'Unknown')}\n"
            f"Billing: {account_info.get('billing_status', 'Unknown')}\n"
            f"{order_section}\n\n"
            f"CLASSIFICATION\n"
            f"Urgency: {classification['urgency']}\n"
            f"Category: {classification['category']}\n"
            f"Summary: {classification['summary']}\n\n"
            f"KNOWLEDGE BASE\n"
            f"{kb_context if kb_context else 'No specific articles — use general support knowledge.'}\n\n"
            f"Write the email body:"
        )),
    ])

    print(f"\n[draft] resolution drafted ({len(response.content)} chars)")

    return {
        "draft_resolution": response.content,
        "audit_log": [f"[{timestamp}] DRAFT → {len(response.content)} chars"],
    }


def decide_node(state: AgentState) -> dict:
    ticket = state["ticket"]
    classification = state["classification"]
    account_info = state["account_info"] or {}
    timestamp = _now()

    decider = llm.with_structured_output(ResolutionDecision)
    result = decider.invoke([
        SystemMessage(content="""You are a customer support manager making routing decisions.

Decision guide:
- auto_resolve: clear solution exists from KB, low/medium urgency, standard issue
- clarify: the customer's message is missing critical info (order number, error message, steps to reproduce)
- escalate: ANY of these → security incident, data breach suspicion, critical urgency,
  billing dispute over $200, VIP/Enterprise customer with major issue, repeated contacts

When in doubt about security issues: ALWAYS escalate."""),
        HumanMessage(content=(
            f"Ticket: {ticket['subject']}\n"
            f"Body: {ticket['body']}\n\n"
            f"Urgency: {classification['urgency']}\n"
            f"Category: {classification['category']}\n"
            f"Customer plan: {account_info.get('plan', 'unknown')}\n"
            f"Billing status: {account_info.get('billing_status', 'unknown')}\n"
            f"Lifetime value: ${account_info.get('lifetime_value', 0):,.2f}\n\n"
            f"Draft resolution (first 400 chars):\n{state.get('draft_resolution', '')[:400]}\n\n"
            f"Make your routing decision:"
        )),
    ])

    print(f"\n[decide] decision={result.decision}")
    print(f"[decide] reasoning: {result.reasoning}")

    return {
        "decision": result.decision,
        "decision_reasoning": result.reasoning,
        "audit_log": [
            f"[{timestamp}] DECIDE → {result.decision.upper()} | {result.reasoning[:100]}"
        ],
    }


def human_approval_node(state: AgentState) -> dict:
    ticket = state["ticket"]
    classification = state["classification"]
    account_info = state["account_info"] or {}
    timestamp = _now()

    review_packet = {
        "ticket_id": ticket["id"],
        "customer_name": account_info.get("name", "Unknown"),
        "customer_email": ticket["customer_email"],
        "customer_plan": account_info.get("plan", "Unknown"),
        "urgency": classification["urgency"],
        "issue_summary": classification["summary"],
        "ai_decision": state["decision"],
        "ai_reasoning": state["decision_reasoning"],
        "draft_response_preview": (state.get("draft_resolution") or "")[:500],
        "instructions": "Reply with: {'approved': True/False, 'notes': 'your comments'}",
    }

    print("\n" + "=" * 60)
    print("  !! HUMAN REVIEW REQUIRED — graph is paused !!")
    print("=" * 60)
    print(json.dumps(review_packet, indent=2))
    print("=" * 60)

    # Graph checkpoints here and sleeps until Command(resume=...) is called
    human_response = interrupt(review_packet)

    approved = bool(human_response.get("approved", False))
    notes = human_response.get("notes", "")

    print(f"\n[human_approval] {'APPROVED ✓' if approved else 'REJECTED ✗'}")
    if notes:
        print(f"[human_approval] Notes: {notes}")

    return {
        "human_approved": approved,
        "human_notes": notes,
        "audit_log": [
            f"[{timestamp}] HUMAN REVIEW → {'APPROVED' if approved else 'REJECTED'}"
            + (f" | Notes: {notes}" if notes else "")
        ],
    }


def action_node(state: AgentState) -> dict:
    ticket = state["ticket"]
    classification = state["classification"]
    decision = state["decision"]
    account_info = state["account_info"] or {}
    timestamp = _now()

    actions_taken = []

    crm_status = {
        "auto_resolve": "resolved",
        "clarify": "pending_customer_reply",
        "escalate": "escalated_to_human",
    }.get(decision, "in_progress")

    crm_result = update_crm(
        ticket_id=ticket["id"],
        status=crm_status,
        resolution_notes=state.get("draft_resolution") or "",
        category=classification["category"],
    )
    if crm_result["success"]:
        actions_taken.append(f"CRM updated → {crm_status}")

    subject = {
        "auto_resolve": f"Re: {ticket['subject']} — We've resolved your issue",
        "clarify":      f"Re: {ticket['subject']} — Quick question from support",
        "escalate":     f"Re: {ticket['subject']} — Your case has been escalated",
    }.get(decision, f"Re: {ticket['subject']}")

    human_note_section = (
        f"\n\nNote from your support manager: {state.get('human_notes')}"
        if state.get("human_notes") else ""
    )

    email_body = (
        f"Hi {account_info.get('name', 'there')},\n\n"
        f"{state.get('draft_resolution', '')}"
        f"{human_note_section}\n\n"
        f"Best regards,\nSupport Team"
    )

    email_result = send_customer_email(
        to_email=ticket["customer_email"],
        subject=subject,
        body=email_body,
    )
    if email_result["success"]:
        actions_taken.append(f"Email sent → {ticket['customer_email']}")

    if decision == "escalate":
        esc_result = create_escalation_ticket(
            ticket_id=ticket["id"],
            customer_id=ticket["customer_id"],
            reason=state.get("decision_reasoning") or "",
            urgency=classification["urgency"],
        )
        if esc_result["success"]:
            actions_taken.append(f"Escalation created → {esc_result['escalation_id']}")

    print(f"\n[action] completed: {actions_taken}")

    return {
        "actions_taken": actions_taken,
        "audit_log": [f"[{timestamp}] ACTION → {' | '.join(actions_taken)}"],
    }


def audit_node(state: AgentState) -> dict:
    ticket = state["ticket"]
    classification = state["classification"] or {}
    timestamp = _now()

    final_entry = (
        f"[{timestamp}] COMPLETE | "
        f"ticket={ticket['id']} | "
        f"urgency={classification.get('urgency', '?')} | "
        f"decision={state.get('decision', '?')} | "
        f"human_reviewed={state.get('human_approved') is not None} | "
        f"actions={len(state.get('actions_taken', []))}"
    )

    print("\n" + "=" * 60)
    print("  AUDIT TRAIL")
    print("=" * 60)
    for entry in state.get("audit_log", []):
        print(f"  {entry}")
    print(f"  {final_entry}")
    print("=" * 60)

    return {"audit_log": [final_entry]}


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")
