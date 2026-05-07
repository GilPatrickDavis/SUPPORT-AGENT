import os
from dotenv import load_dotenv
from langgraph.types import Command

from .graph import compile_graph
from .state import AgentState

load_dotenv()


def make_initial_state(ticket: dict) -> AgentState:
    return {
        "ticket": ticket,
        "classification": None,
        "account_info": None,
        "order_info": None,
        "kb_articles": [],
        "draft_resolution": None,
        "decision": None,
        "decision_reasoning": None,
        "human_approved": None,
        "human_notes": None,
        "actions_taken": [],
        "audit_log": [],
    }


TICKET_FAQ = {
    "id": "TKT-1001",
    "customer_id": "CUST-001",
    "customer_email": "alice@example.com",
    "subject": "Forgot my password, can't log in",
    "body": (
        "Hi, I forgot my password and now I'm completely locked out of my account. "
        "I tried the forgot password link but I'm not sure if the email arrived. "
        "Can you help me get back in?"
    ),
    "order_id": None,
}

TICKET_BILLING = {
    "id": "TKT-1002",
    "customer_id": "CUST-002",
    "customer_email": "bob@example.com",
    "subject": "Charged twice for my subscription last month",
    "body": (
        "Hello, I was charged twice last month for my Basic plan subscription. "
        "Order number ORD-8891. I need a refund for the duplicate charge ASAP. "
        "This is really frustrating."
    ),
    "order_id": "ORD-8891",
}

TICKET_CRITICAL = {
    "id": "TKT-1003",
    "customer_id": "CUST-003",
    "customer_email": "carol@example.com",
    "subject": "URGENT: My account was hacked, company data at risk",
    "body": (
        "I just received alerts showing logins from an IP in a country I've never been to. "
        "Someone has accessed my Enterprise account without my permission. "
        "We have confidential client data in there. "
        "I need this locked down immediately — this is a serious security incident."
    ),
    "order_id": None,
}


def run_scenario_1():
    print("\n" + "█" * 60)
    print("  SCENARIO 1: FAQ — Password Reset (expect: auto_resolve)")
    print("█" * 60)

    app = compile_graph()
    # Each ticket gets its own thread_id so multiple tickets can run concurrently
    config = {"configurable": {"thread_id": "TKT-1001"}}
    result = app.invoke(make_initial_state(TICKET_FAQ), config=config)

    print(f"\n  ✓ Final decision : {result['decision']}")
    print(f"  ✓ Actions taken  : {result['actions_taken']}")


def run_scenario_2():
    print("\n" + "█" * 60)
    print("  SCENARIO 2: Billing — Duplicate Charge (expect: clarify or auto_resolve)")
    print("█" * 60)

    app = compile_graph()
    config = {"configurable": {"thread_id": "TKT-1002"}}
    result = app.invoke(make_initial_state(TICKET_BILLING), config=config)

    print(f"\n  ✓ Final decision : {result['decision']}")
    print(f"  ✓ Actions taken  : {result['actions_taken']}")


def run_scenario_3():
    print("\n" + "█" * 60)
    print("  SCENARIO 3: Security Breach (expect: escalate → human approval)")
    print("█" * 60)

    app = compile_graph()
    config = {"configurable": {"thread_id": "TKT-1003"}}

    print("\n--- Phase 1: AI pipeline running (will pause at human_approval) ---")
    app.invoke(make_initial_state(TICKET_CRITICAL), config=config)

    snapshot = app.get_state(config)
    if snapshot.next:
        print(f"\n  Graph is PAUSED. Waiting at: {snapshot.next}")

        human_decision = {
            "approved": True,
            "notes": (
                "Verified — IP is from a known threat actor region. "
                "Account locked. Escalation approved. Priority response."
            ),
        }
        print(f"\n  Simulating human approval: {human_decision}")

        print("\n--- Phase 2: Resuming graph after human approval ---")
        result = app.invoke(Command(resume=human_decision), config=config)

        print(f"\n  ✓ Final decision  : {result['decision']}")
        print(f"  ✓ Human approved  : {result['human_approved']}")
        print(f"  ✓ Human notes     : {result['human_notes']}")
        print(f"  ✓ Actions taken   : {result['actions_taken']}")
    else:
        print(f"\n  ✓ Completed without human review")
        print(f"  ✓ Decision: {snapshot.values.get('decision')}")


def run_scenario_3_rejected():
    print("\n" + "█" * 60)
    print("  SCENARIO 3b: Security — Human REJECTS the AI draft")
    print("█" * 60)

    app = compile_graph()
    config = {"configurable": {"thread_id": "TKT-1003-b"}}

    print("\n--- Phase 1: Running AI pipeline ---")
    app.invoke(make_initial_state(TICKET_CRITICAL), config=config)

    snapshot = app.get_state(config)
    if snapshot.next:
        human_decision = {
            "approved": False,
            "notes": "Draft response is too generic. Rewriting manually — do not send.",
        }
        print(f"\n  Simulating human REJECTION: {human_decision}")

        print("\n--- Phase 2: Resuming after rejection ---")
        result = app.invoke(Command(resume=human_decision), config=config)

        print(f"\n  ✓ Decision        : {result['decision']}")
        print(f"  ✓ Human approved  : {result['human_approved']}  (no action taken)")
        print(f"  ✓ Actions taken   : {result['actions_taken']}  (empty — rejected)")


if __name__ == "__main__":
    if not os.getenv("GROQ_API_KEY"):
        print("ERROR: Set GROQ_API_KEY in your .env file first.")
        exit(1)

    run_scenario_1()
    run_scenario_2()
    run_scenario_3()
    run_scenario_3_rejected()
