from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .state import AgentState
from .nodes import (
    classify_node,
    investigate_node,
    search_kb_node,
    draft_node,
    decide_node,
    human_approval_node,
    action_node,
    audit_node,
)


def route_after_decide(state: AgentState) -> str:
    decision = state["decision"]
    urgency = state["classification"]["urgency"]
    if decision == "escalate" or urgency == "critical":
        return "needs_human"
    return "execute"


def route_after_human(state: AgentState) -> str:
    return "execute" if state.get("human_approved") else "skip_to_audit"


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("classify",       classify_node)
    graph.add_node("investigate",    investigate_node)
    graph.add_node("search_kb",      search_kb_node)
    graph.add_node("draft",          draft_node)
    graph.add_node("decide",         decide_node)
    graph.add_node("human_approval", human_approval_node)
    graph.add_node("action",         action_node)
    graph.add_node("audit",          audit_node)

    graph.add_edge(START,         "classify")
    graph.add_edge("classify",    "investigate")
    graph.add_edge("investigate", "search_kb")
    graph.add_edge("search_kb",   "draft")
    graph.add_edge("draft",       "decide")

    graph.add_conditional_edges(
        "decide",
        route_after_decide,
        {"needs_human": "human_approval", "execute": "action"},
    )

    graph.add_conditional_edges(
        "human_approval",
        route_after_human,
        {"execute": "action", "skip_to_audit": "audit"},
    )

    graph.add_edge("action", "audit")
    graph.add_edge("audit",  END)

    return graph


def compile_graph():
    # MemorySaver checkpointer is required for interrupt() to persist graph state
    # between the first invoke() call and the Command(resume=...) call
    return build_graph().compile(checkpointer=MemorySaver())
