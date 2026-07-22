"""Prompt loading & rendering.

Prompts live as plain-text files under `agents/prompts/` — externalized so they
can be edited, versioned, and reviewed without touching Python. Because the
templates contain literal JSON braces, rendering uses `{{TOKEN}}` placeholders
(not `str.format`, which would choke on `{`).
"""

from __future__ import annotations

from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent / "prompts"


class PromptLibrary:
    """Loads and renders prompt templates from disk (cached)."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = base_dir or _PROMPTS_DIR
        self._cache: dict[str, str] = {}

    def load(self, name: str) -> str:
        """Return the raw template text for `name` (without extension)."""
        if name not in self._cache:
            self._cache[name] = (self._dir / f"{name}.md").read_text(encoding="utf-8")
        return self._cache[name]

    def render(self, name: str, variables: dict[str, str] | None = None) -> str:
        """Return the template with each `{{KEY}}` replaced by its value."""
        text = self.load(name)
        for key, value in (variables or {}).items():
            text = text.replace(f"{{{{{key}}}}}", value)
        return text
