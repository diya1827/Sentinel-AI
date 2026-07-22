"""Agentic AI layer.

Responsibility: all LLM reasoning. This layer is **provider-agnostic** — it
depends on the `LLMProvider` abstraction, never on a vendor SDK directly, so the
model is swappable via configuration (default: free Google Gemini).

Contents:
    provider.py   — LLMProvider protocol + OpenAI-compatible/Anthropic backends
    tools.py      — Tool protocol + registry for (future) tool calling
    prompts.py    — PromptLibrary loader
    prompts/      — externalized prompt templates (system.md, analysis.md)

The agent itself is orchestrated by `app.services.agent_service.AgentService`.
"""
