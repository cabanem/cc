import pytest

from agent_graph.nodes import fan_out


def test_one_send_per_task():
    state = {
        "request": {
            "tasks": [
                {"action": "summarize", "payload": {"text": "a"}},
                {"action": "classify", "payload": {"text": "b", "labels": "x|y"}},
                {"action": "summarize", "payload": {"text": "c"}},
            ]
        }
    }
    sends = fan_out(state)
    assert len(sends) == 3
    assert all(s.node == "agent" for s in sends)
    assert [s.arg["action"] for s in sends] == ["summarize", "classify", "summarize"]
    # task_ids must be unique — they key idempotency later
    assert len({s.arg["task_id"] for s in sends}) == 3


def test_empty_tasks_raises():
    with pytest.raises(ValueError, match="nothing to fan out"):
        fan_out({"request": {"tasks": []}})
