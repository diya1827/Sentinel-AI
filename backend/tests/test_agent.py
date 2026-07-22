"""Tests for the AI agent layer (no network — a scripted provider is injected)."""

import json

import pytest

from app.agents.prompts import PromptLibrary
from app.agents.provider import LLMError, LLMMessage, LLMResponse, ToolCall
from app.agents.tools import ToolRegistry
from app.models.agent import AgentReport
from app.models.finding import Finding, Severity
from app.models.repository import NodeType, RepositoryMetadata, SourceType, TreeNode
from app.models.scan import ScanReport
from app.services.agent_service import AgentService

VALID_REPORT_JSON = json.dumps(
    {
        "overall_risk": "high",
        "executive_summary": "One leaked secret puts production data at risk.",
        "developer_summary": "Rotate the exposed key and stop committing secrets.",
        "duplicates_removed": 1,
        "correlations": ["F1 and F2 are the same leaked database password"],
        "prioritized_findings": [
            {
                "id": "V1",
                "title": "Hardcoded database password",
                "severity": "high",
                "priority": 1,
                "category": "Secret Exposure",
                "affected_files": ["app/config.py"],
                "source_finding_ids": ["F1", "F2"],
                "scanners": ["gitleaks", "semgrep"],
                "why_it_matters": "Anyone with the repo can reach the DB.",
                "exploitability": "Direct: use the credential.",
                "remediation": "Rotate the credential; load from env.",
                "confidence": "high",
                "duplicate_of": None,
            }
        ],
        "notes": None,
    }
)


class ScriptedProvider:
    """Returns pre-canned responses in order; records call count."""

    model = "fake-model"

    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = list(responses)
        self.calls = 0
        self.last_messages: list[LLMMessage] = []

    async def chat(self, messages, *, tools=None, response_format=None):  # noqa: ANN001
        self.calls += 1
        self.last_messages = messages
        return self._responses.pop(0)


def _text(content: str) -> LLMResponse:
    return LLMResponse(content=content, tool_calls=[])


def _make_repo() -> RepositoryMetadata:
    tree = TreeNode(
        name="root",
        path=".",
        type=NodeType.DIRECTORY,
        children=[
            TreeNode(name="config.py", path="app/config.py", type=NodeType.FILE, size=10)
        ],
    )
    return RepositoryMetadata(
        repository_id="abc123",
        source=SourceType.UPLOAD,
        primary_language="Python",
        languages=[],
        package_managers=["pip"],
        file_count=1,
        total_size_bytes=10,
        tree=tree,
    )


def _make_scan(findings: list[Finding]) -> ScanReport:
    return ScanReport(
        repository_id="abc123",
        results=[],
        findings=findings,
        total_findings=len(findings),
        severity_counts={},
    )


def _secret_finding() -> Finding:
    return Finding(
        scanner="gitleaks", severity=Severity.HIGH, file="app/config.py", line=3, title="secret"
    )


# ── Prompt library ───────────────────────────────────────────────

def test_prompt_library_renders_tokens() -> None:
    lib = PromptLibrary()
    assert "Application Security Engineer" in lib.load("system")
    rendered = lib.render("analysis", {"REPO_SUMMARY": "MYREPO", "FINDINGS_JSON": "[]", "FINDINGS_COUNT": "0"})
    assert "MYREPO" in rendered
    assert "{{REPO_SUMMARY}}" not in rendered


# ── Tool registry ────────────────────────────────────────────────

class _EchoTool:
    name = "echo"
    description = "Echo a message back."
    parameters = {"type": "object", "properties": {"msg": {"type": "string"}}}

    async def run(self, msg: str = "") -> str:
        return f"echo:{msg}"


@pytest.mark.asyncio
async def test_tool_registry_schema_and_dispatch() -> None:
    reg = ToolRegistry([_EchoTool()])
    assert reg.schemas()[0]["function"]["name"] == "echo"

    msg = await reg.dispatch(ToolCall(id="c1", name="echo", arguments={"msg": "hi"}))
    assert msg.role == "tool"
    assert msg.content == "echo:hi"

    unknown = await reg.dispatch(ToolCall(id="c2", name="nope", arguments={}))
    assert "Unknown tool" in (unknown.content or "")


# ── AgentService ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analyze_returns_structured_report() -> None:
    provider = ScriptedProvider([_text(VALID_REPORT_JSON)])
    service = AgentService(provider=provider)

    report = await service.analyze(_make_repo(), _make_scan([_secret_finding()]))

    assert isinstance(report, AgentReport)
    assert report.overall_risk is Severity.HIGH
    assert report.prioritized_findings[0].title == "Hardcoded database password"
    # Service-owned fields are stamped, not trusted from the model.
    assert report.repository_id == "abc123"
    assert report.model_used == "fake-model"
    assert report.total_input_findings == 1
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_analyze_strips_code_fences() -> None:
    fenced = f"```json\n{VALID_REPORT_JSON}\n```"
    service = AgentService(provider=ScriptedProvider([_text(fenced)]))
    report = await service.analyze(_make_repo(), _make_scan([_secret_finding()]))
    assert report.overall_risk is Severity.HIGH


@pytest.mark.asyncio
async def test_analyze_retries_on_bad_json() -> None:
    provider = ScriptedProvider([_text("not json"), _text(VALID_REPORT_JSON)])
    service = AgentService(provider=provider)
    report = await service.analyze(_make_repo(), _make_scan([_secret_finding()]))
    assert report.overall_risk is Severity.HIGH
    assert provider.calls == 2  # one bad, one good


@pytest.mark.asyncio
async def test_analyze_raises_after_exhausting_retries() -> None:
    provider = ScriptedProvider([_text("nope"), _text("still nope")])
    service = AgentService(provider=provider)
    with pytest.raises(LLMError):
        await service.analyze(_make_repo(), _make_scan([_secret_finding()]))


@pytest.mark.asyncio
async def test_analyze_short_circuits_when_no_findings() -> None:
    provider = ScriptedProvider([])  # would IndexError if chat() were called
    service = AgentService(provider=provider)
    report = await service.analyze(_make_repo(), _make_scan([]))
    assert provider.calls == 0
    assert report.overall_risk is Severity.INFO
    assert report.prioritized_findings == []


def test_loads_lenient_repairs_invalid_escapes() -> None:
    from app.services.agent_service import _loads_lenient

    # A regex with a lone `\d` — invalid JSON escape the model sometimes emits.
    raw = r'{"notes": "matches \d+ digits in C:\Users\app"}'
    data = _loads_lenient(raw)
    assert data["notes"] == r"matches \d+ digits in C:\Users\app"

    # Already-valid JSON (with proper escapes) is untouched.
    assert _loads_lenient('{"a": "line\\nbreak"}')["a"] == "line\nbreak"


@pytest.mark.asyncio
async def test_analyze_recovers_from_bad_escape_without_retry() -> None:
    bad_escape = r'{"overall_risk":"low","executive_summary":"re: \d+","developer_summary":"x","duplicates_removed":0,"correlations":[],"prioritized_findings":[],"notes":null}'
    provider = ScriptedProvider([_text(bad_escape)])
    service = AgentService(provider=provider)
    report = await service.analyze(_make_repo(), _make_scan([_secret_finding()]))
    assert report.overall_risk is Severity.LOW
    assert provider.calls == 1  # repaired in place, no retry needed


@pytest.mark.asyncio
async def test_analyze_forces_final_answer_on_last_turn() -> None:
    """A tool-hungry agent is made to finalize instead of erroring out."""
    from app.services.agent_service import _MAX_TURNS

    tool_call = LLMResponse(
        content=None, tool_calls=[ToolCall(id="c", name="echo", arguments={"msg": "x"})]
    )
    # Ask for a tool every turn; only the forced final turn returns JSON.
    responses = [tool_call] * (_MAX_TURNS - 1) + [_text(VALID_REPORT_JSON)]
    provider = ScriptedProvider(responses)
    service = AgentService(provider=provider, tools=ToolRegistry([_EchoTool()]))

    report = await service.analyze(_make_repo(), _make_scan([_secret_finding()]))
    assert report.overall_risk is Severity.HIGH
    assert provider.calls == _MAX_TURNS


@pytest.mark.asyncio
async def test_analyze_services_tool_calls() -> None:
    # First turn: model asks to call the echo tool. Second turn: final answer.
    responses = [
        LLMResponse(content=None, tool_calls=[ToolCall(id="c1", name="echo", arguments={"msg": "x"})]),
        _text(VALID_REPORT_JSON),
    ]
    provider = ScriptedProvider(responses)
    service = AgentService(provider=provider, tools=ToolRegistry([_EchoTool()]))

    report = await service.analyze(_make_repo(), _make_scan([_secret_finding()]))
    assert report.overall_risk is Severity.HIGH
    assert provider.calls == 2
