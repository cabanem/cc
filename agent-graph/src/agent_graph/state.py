"""State schema.

The important idea: fan-in is not a node doing collection work — it's the
reducer on `results`. Parallel branches each return {"results": [one_item]},
and LangGraph merges them with operator.add before the next superstep runs.
"""
import operator
from typing import Annotated, Any, TypedDict


class RunState(TypedDict, total=False):
    request: dict[str, Any]
    """Intake payload. v1 shape: {"tasks": [{"action": str, "payload": dict}, ...]}"""

    results: Annotated[list[dict[str, Any]], operator.add]
    """Fan-in point. Concurrent branch writes are merged by the reducer."""

    verdict: dict[str, Any]
    """Reviewer decision — arrives via Command(resume=...) through the review gate."""

    final: dict[str, Any]


class AgentTask(TypedDict):
    """The private state of one agent branch — exactly what a Send() carries."""
    task_id: str
    action: str
    payload: dict[str, Any]
