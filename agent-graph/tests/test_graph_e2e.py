"""The Phase 1 exit test as an assertion suite.

Covers: dynamic fan-out, reducer fan-in (results length == task count proves
the merge), interrupt at the review gate, and resume via Command.
"""
from pathlib import Path

from langgraph.types import Command

try:  # naming drifted across langgraph versions
    from langgraph.checkpoint.memory import InMemorySaver
except ImportError:
    from langgraph.checkpoint.memory import MemorySaver as InMemorySaver

from agent_graph.graph import build_graph
from agent_graph.llm import FakeLLM
from agent_graph.registry import ActionRegistry

REGISTRY = Path(__file__).resolve().parent.parent / "registry" / "actions.yaml"

REQUEST = {
    "tasks": [
        {"action": "summarize", "payload": {"text": "alpha"}},
        {"action": "classify", "payload": {"text": "beta", "labels": "x | y"}},
    ]
}


def _graph():
    registry = ActionRegistry.from_yaml(REGISTRY)
    return build_graph(registry, llm=FakeLLM(), checkpointer=InMemorySaver())


def test_fan_out_pause_resume():
    graph = _graph()
    config = {"configurable": {"thread_id": "t1"}}

    paused = graph.invoke({"request": REQUEST}, config)

    # Paused, not finished: interrupt surfaced, no final yet.
    assert "__interrupt__" in paused
    assert paused["__interrupt__"][0].value["awaiting"] == "review"
    assert "final" not in paused

    # Fan-in proof: both branch writes merged by the reducer.
    assert len(paused["results"]) == 2
    assert {r["action"] for r in paused["results"]} == {"summarize", "classify"}

    final = graph.invoke(Command(resume={"approved": True}), config)
    assert final["final"]["approved"] is True
    assert final["final"]["n_results"] == 2


def test_rejection_verdict_recorded():
    graph = _graph()
    config = {"configurable": {"thread_id": "t2"}}
    graph.invoke({"request": REQUEST}, config)
    final = graph.invoke(Command(resume={"approved": False, "notes": "redo"}), config)
    assert final["final"]["approved"] is False
    assert final["verdict"]["notes"] == "redo"
