"""Phase 1 exit test, human-runnable:

    AGENT_GRAPH_FAKE_LLM=1 python scripts/run_local.py

Starts a run (fan-out of 3 tasks), hits the review pause, then resumes with an
approval — all against the in-memory checkpointer, no GCP anywhere.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("AGENT_GRAPH_FAKE_LLM", "1")

from langgraph.types import Command

try:  # naming drifted across langgraph versions
    from langgraph.checkpoint.memory import InMemorySaver
except ImportError:
    from langgraph.checkpoint.memory import MemorySaver as InMemorySaver

from agent_graph.graph import build_graph
from agent_graph.registry import ActionRegistry

REQUEST = {
    "tasks": [
        {"action": "summarize", "payload": {"text": "Supplier onboarding notes..."}},
        {"action": "classify", "payload": {"text": "Please resend the template", "labels": "question | complaint | request"}},
        {"action": "extract_fields", "payload": {"text": "Acme Corp, NET30, contact jane@acme.com", "fields": "name, terms, email"}},
    ]
}


def main() -> None:
    registry = ActionRegistry.from_yaml(ROOT / "registry" / "actions.yaml")
    graph = build_graph(registry, checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "demo-1"}}

    paused = graph.invoke({"request": REQUEST}, config)
    print("--- paused at review gate ---")
    print(json.dumps(paused["__interrupt__"][0].value, indent=2))

    final = graph.invoke(Command(resume={"approved": True, "notes": "LGTM"}), config)
    print("\n--- final ---")
    print(json.dumps(final["final"], indent=2))


if __name__ == "__main__":
    main()
