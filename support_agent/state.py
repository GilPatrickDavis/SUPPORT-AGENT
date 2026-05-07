from __future__ import annotations
from typing import TypedDict, Annotated, Optional
import operator


class TicketData(TypedDict):
    id: str
    customer_id: str
    customer_email: str
    subject: str
    body: str
    order_id: Optional[str]


class Classification(TypedDict):
    urgency: str    # low | medium | high | critical
    category: str   # billing | technical | account | shipping | general
    summary: str
    keywords: list[str]


class AgentState(TypedDict):
    ticket: TicketData
    classification: Optional[Classification]
    account_info: Optional[dict]
    order_info: Optional[dict]
    kb_articles: list[dict]
    draft_resolution: Optional[str]
    decision: Optional[str]          # auto_resolve | clarify | escalate
    decision_reasoning: Optional[str]
    human_approved: Optional[bool]
    human_notes: Optional[str]
    actions_taken: list[str]
    # operator.add means each node appends to this list instead of replacing it
    audit_log: Annotated[list[str], operator.add]
