"""Action registry: a new agent capability is a YAML entry, not graph surgery.

Each action maps to (model, prompt template, optional generation params).
Validation happens at load time so a malformed registry fails the deploy,
not a run.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

REQUIRED_KEYS = {"model", "prompt"}


class RegistryError(ValueError):
    pass


@dataclass(frozen=True)
class ActionSpec:
    name: str
    model: str
    prompt: str
    params: dict = field(default_factory=dict)

    def render(self, payload: dict) -> str:
        try:
            return self.prompt.format(**payload)
        except KeyError as e:
            raise RegistryError(
                f"action '{self.name}': payload missing placeholder {e}"
            ) from None


class ActionRegistry:
    def __init__(self, specs: dict[str, ActionSpec]):
        self._specs = specs

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ActionRegistry":
        raw = yaml.safe_load(Path(path).read_text())
        actions = (raw or {}).get("actions")
        if not actions:
            raise RegistryError(f"{path}: no 'actions' mapping found")
        specs: dict[str, ActionSpec] = {}
        for name, body in actions.items():
            missing = REQUIRED_KEYS - set(body)
            if missing:
                raise RegistryError(f"action '{name}' missing keys: {sorted(missing)}")
            specs[name] = ActionSpec(
                name=name,
                model=body["model"],
                prompt=body["prompt"],
                params=body.get("params", {}),
            )
        return cls(specs)

    def get(self, name: str) -> ActionSpec:
        try:
            return self._specs[name]
        except KeyError:
            raise RegistryError(
                f"unknown action '{name}'; known: {sorted(self._specs)}"
            ) from None

    def names(self) -> list[str]:
        return sorted(self._specs)
