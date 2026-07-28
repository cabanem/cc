"""Wiring.

Shape:  START → plan ──(fan_out: Send × N)──> agent ──> review ──> finalize → END

All parallel `agent` branches complete before `review` runs once — that is
superstep semantics doing the join for free.
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .llm import LLM, make_llm
from .nodes import fan_out, finalize, make_agent_node, plan, review
from .registry import ActionRegistry
from .state import RunState


def build_graph(registry: ActionRegistry, llm: LLM | None = None, checkpointer=None):
    llm = llm or make_llm()
    b = StateGraph(RunState)
    b.add_node("plan", plan)
    b.add_node("agent", make_agent_node(registry, llm))
    b.add_node("review", review)
    b.add_node("finalize", finalize)
    b.add_edge(START, "plan")
    b.add_conditional_edges("plan", fan_out, ["agent"])
    b.add_edge("agent", "review")
    b.add_edge("review", "finalize")
    b.add_edge("finalize", END)
    return b.compile(checkpointer=checkpointer)
