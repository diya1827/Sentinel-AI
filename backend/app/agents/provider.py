"""LLM provider abstraction — the seam that keeps models swappable.

Agents talk to the `LLMProvider` protocol, never to a vendor SDK. Because
Gemini (our free default), Groq, Ollama, OpenRouter, and OpenAI all speak the
OpenAI Chat Completions API, a single `OpenAICompatibleProvider` serves all of
them — only the `base_url`/key/model change. Anthropic would be a separate
implementation of the same protocol.

The interface is deliberately message- and tool-shaped (not a bare
`complete(prompt)`), so multi-turn tool calling can be added without touching
callers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from app.config.settings import Settings, get_settings


class LLMError(RuntimeError):
    """A call to the model failed."""


class LLMConfigError(LLMError):
    """The provider is misconfigured (e.g. missing API key)."""


# ── Message / response value objects ─────────────────────────────

@dataclass
class ToolCall:
    """A tool invocation the model requested."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMMessage:
    """One chat message. `role` is system|user|assistant|tool."""

    role: str
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None  # set on role="tool" replies
    name: str | None = None
    # When set, this exact dict is sent on the wire instead of rebuilding the
    # message. Used to replay a provider's raw assistant turn verbatim — e.g.
    # Gemini requires its `thought_signature` on tool calls to be echoed back.
    wire_override: dict[str, Any] | None = None


@dataclass
class LLMResponse:
    """The model's reply: free text and/or tool calls."""

    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: Any = None
    # The provider's assistant message as a wire-ready dict, preserved so a
    # tool-calling turn can be replayed without losing provider-specific fields.
    raw_message: dict[str, Any] | None = None


@runtime_checkable
class LLMProvider(Protocol):
    """Contract every LLM backend implements."""

    model: str

    async def chat(
        self,
        messages: list[LLMMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Send a chat request and return the model's reply."""
        ...


# ── OpenAI-compatible implementation (Gemini/Groq/Ollama/OpenAI…) ─

class OpenAICompatibleProvider:
    """Drives any OpenAI Chat Completions-compatible endpoint."""

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None,
        base_url: str | None,
        temperature: float,
        max_tokens: int,
        timeout: int,
    ) -> None:
        self.model = model
        self._api_key = api_key
        self._base_url = base_url
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout = timeout
        self._client: Any = None  # lazily built so `openai` import is optional

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self._api_key:
            raise LLMConfigError(
                "No LLM API key configured. Set LLM_API_KEY (or use LLM_PROVIDER=ollama)."
            )
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:  # pragma: no cover - depends on env
            raise LLMConfigError("The 'openai' package is required.") from exc

        self._client = AsyncOpenAI(
            api_key=self._api_key, base_url=self._base_url, timeout=self._timeout
        )
        return self._client

    async def chat(
        self,
        messages: list[LLMMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        client = self._get_client()
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [_to_wire(m) for m in messages],
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if response_format:
            kwargs["response_format"] = response_format

        try:
            resp = await client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001 — normalize any SDK error
            text = str(exc)
            if "429" in text or "RESOURCE_EXHAUSTED" in text or "quota" in text.lower():
                raise LLMError(
                    "The free AI tier is rate-limited right now (too many requests "
                    "this minute). Wait about a minute and try again."
                ) from exc
            raise LLMError(f"LLM request failed: {exc}") from exc

        message = resp.choices[0].message
        tool_calls = [
            ToolCall(
                id=tc.id,
                name=tc.function.name,
                arguments=_safe_json(tc.function.arguments),
            )
            for tc in (message.tool_calls or [])
        ]
        # Keep the raw assistant message (incl. provider extras like Gemini's
        # thought_signature) so a tool-calling turn can be replayed verbatim.
        raw_message = _dump_message(message) if tool_calls else None
        return LLMResponse(
            content=message.content,
            tool_calls=tool_calls,
            raw=resp,
            raw_message=raw_message,
        )


class AnthropicProvider:
    """Claude-backed provider (separate API). Implement when needed."""

    def __init__(self, *, model: str, api_key: str | None) -> None:
        self.model = model
        self._api_key = api_key

    async def chat(self, messages, *, tools=None, response_format=None):  # noqa: D102, ANN001
        raise LLMConfigError("Anthropic provider is not implemented yet.")


# ── Factory ──────────────────────────────────────────────────────

def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    """Build the configured provider from settings."""
    settings = settings or get_settings()

    if settings.llm_provider == "anthropic":
        return AnthropicProvider(
            model=settings.anthropic_model, api_key=settings.anthropic_api_key
        )

    # Ollama needs no real key; the SDK just requires a non-empty string.
    api_key = settings.llm_api_key or (
        "ollama" if settings.llm_provider == "ollama" else None
    )
    return OpenAICompatibleProvider(
        model=settings.llm_model,
        api_key=api_key,
        base_url=settings.resolved_llm_base_url,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        timeout=settings.llm_timeout,
    )


# ── helpers ──────────────────────────────────────────────────────

def _dump_message(message: Any) -> dict[str, Any] | None:
    """Serialize a provider SDK message to a wire-ready dict, extras included.

    Falls back to None if the SDK object can't be dumped, in which case the
    caller rebuilds the message from parsed fields (losing provider extras).
    """
    try:
        return message.model_dump(exclude_none=True)
    except Exception:  # noqa: BLE001 — best-effort; never break the turn loop
        return None


def _to_wire(message: LLMMessage) -> dict[str, Any]:
    """Convert an `LLMMessage` to the OpenAI wire format."""
    if message.wire_override is not None:
        return message.wire_override

    wire: dict[str, Any] = {"role": message.role}
    if message.content is not None:
        wire["content"] = message.content
    if message.tool_calls:
        wire["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
            }
            for tc in message.tool_calls
        ]
    if message.tool_call_id:
        wire["tool_call_id"] = message.tool_call_id
    if message.name:
        wire["name"] = message.name
    return wire


def _safe_json(raw: str | None) -> dict[str, Any]:
    try:
        return json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return {}
