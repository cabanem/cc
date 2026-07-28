import pytest

from agent_graph.registry import ActionRegistry, RegistryError

VALID = """
actions:
  summarize:
    model: gemini-2.5-flash
    prompt: "Summarize: {text}"
"""

MISSING_PROMPT = """
actions:
  broken:
    model: gemini-2.5-flash
"""


def test_valid_load(tmp_path):
    p = tmp_path / "a.yaml"
    p.write_text(VALID)
    reg = ActionRegistry.from_yaml(p)
    assert reg.names() == ["summarize"]
    assert reg.get("summarize").render({"text": "hi"}) == "Summarize: hi"


def test_missing_required_key(tmp_path):
    p = tmp_path / "a.yaml"
    p.write_text(MISSING_PROMPT)
    with pytest.raises(RegistryError, match="missing keys"):
        ActionRegistry.from_yaml(p)


def test_unknown_action(tmp_path):
    p = tmp_path / "a.yaml"
    p.write_text(VALID)
    reg = ActionRegistry.from_yaml(p)
    with pytest.raises(RegistryError, match="unknown action"):
        reg.get("nope")


def test_payload_missing_placeholder(tmp_path):
    p = tmp_path / "a.yaml"
    p.write_text(VALID)
    reg = ActionRegistry.from_yaml(p)
    with pytest.raises(RegistryError, match="placeholder"):
        reg.get("summarize").render({})
