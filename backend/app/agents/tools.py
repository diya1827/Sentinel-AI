"""Tool-calling support for the agent.

The agent doesn't call any tools *yet*, but the plumbing is here so future
capabilities — reading a specific file, querying a CVE database, running a
targeted re-scan — can be added by registering a `Tool`, with no change to the
agent loop.

A `Tool` exposes an OpenAI-style function schema and an async `run`. The
`ToolRegistry` turns registered tools into request schemas and dispatches the
model's `ToolCall`s back to them.
"""

from __future__ import annotations

import json
from typing import Any, Protocol, runtime_checkable

from app.agents.provider import LLMMessage, ToolCall


@runtime_checkable
class Tool(Protocol):
    """A callable capability the model may invoke."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema for the arguments

    async def run(self, **kwargs: Any) -> str:
        """Execute the tool and return a string result for the model."""
        ...


class ToolRegistry:
    """Holds the available tools and bridges them to the provider."""

    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {t.name: t for t in (tools or [])}

    def __bool__(self) -> bool:
        return bool(self._tools)

    def schemas(self) -> list[dict[str, Any]]:
        """Return OpenAI-format tool schemas for all registered tools."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]

    async def dispatch(self, call: ToolCall) -> LLMMessage:
        """Run the requested tool and wrap its output as a tool-role message."""
        tool = self._tools.get(call.name)
        if tool is None:
            result = json.dumps({"error": f"Unknown tool: {call.name}"})
        else:
            try:
                result = await tool.run(**call.arguments)
            except Exception as exc:  # noqa: BLE001 — surface to the model, don't crash
                result = json.dumps({"error": f"{type(exc).__name__}: {exc}"})

        return LLMMessage(role="tool", content=result, tool_call_id=call.id, name=call.name)
