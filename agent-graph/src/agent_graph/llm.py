"""Model client boundary.

Vertex mode authenticates via Application Default Credentials — zero secrets,
zero Secret Manager. Set AGENT_GRAPH_FAKE_LLM=1 to run the entire graph with
no GCP dependencies at all (this is what keeps Phase 1 local).
"""
from __future__ import annotations

import os
from typing import Protocol


class LLM(Protocol):
    def generate(self, model: str, prompt: str, **params) -> str: ...


class FakeLLM:
    """Deterministic stand-in for local runs and tests."""

    def generate(self, model: str, prompt: str, **params) -> str:
        return f"[fake:{model}] {prompt[:120]}"


class VertexGeminiLLM:
    def __init__(self) -> None:
        from google import genai  # lazy import — not installed for local-only work

        self._client = genai.Client(
            vertexai=True,
            project=os.environ["GOOGLE_CLOUD_PROJECT"],
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
        )

    def generate(self, model: str, prompt: str, **params) -> str:
        resp = self._client.models.generate_content(
            model=model, contents=prompt, config=params or None
        )
        return resp.text or ""


def make_llm() -> LLM:
    if os.environ.get("AGENT_GRAPH_FAKE_LLM") == "1":
        return FakeLLM()
    return VertexGeminiLLM()
