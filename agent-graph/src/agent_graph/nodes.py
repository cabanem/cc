"""Node implementations.

Mechanism worth internalizing: `fan_out` is a *routing function*, not a node.
It returns Send() objects, and LangGraph launches one `agent` invocation per
Send — concurrently, within a single superstep. Each Send's dict becomes that
branch's entire input state (see AgentTask), which is why the agent node's
signature takes a task, not the full RunState.
"""
from __future__ import annotations

import uuid

from langgraph.types import Send, interrupt

from .llm import LLM
from .registry import ActionRegistry
from .state import AgentTask, RunState


def plan(state: RunState) -> dict:
    """v1 planner is pass-through: the request declares its own tasks.
    Swap in an LLM-driven planner later without changing the graph shape."""
    return {}


def fan_out(state: RunState) -> list[Send]:
    tasks = state["request"].get("tasks", [])
    if not tasks:
        raise ValueError("request.tasks is empty — nothing to fan out")
    return [
        Send(
            "agent",
            AgentTask(
                task_id=uuid.uuid4().hex[:8],
                action=t["action"],
                payload=t.get("payload", {}),
            ),
        )
        for t in tasks
    ]


def make_agent_node(registry: ActionRegistry, llm: LLM):
    """One generic node dispatched through the registry — the flexibility knob."""

    def run_agent(task: AgentTask) -> dict:
        spec = registry.get(task["action"])
        output = llm.generate(spec.model, spec.render(task["payload"]), **spec.params)
        # Returning a one-item list is the fan-in contract: the reducer appends it.
        return {
            "results": [
                {"task_id": task["task_id"], "action": task["action"], "output": output}
            ]
        }

    return run_agent


def review(state: RunState) -> dict:
    """The HITL gate. interrupt() checkpoints state and halts; the process may
    exit. Whatever Command(resume=...) later carries becomes interrupt()'s
    return value, on a fresh invocation of this node."""
    verdict = interrupt({"awaiting": "review", "results": state["results"]})
    return {"verdict": verdict}


def finalize(state: RunState) -> dict:
    return {
        "final": {
            "approved": bool(state["verdict"].get("approved")),
            "n_results": len(state["results"]),
            "results": state["results"],
        }
    }
