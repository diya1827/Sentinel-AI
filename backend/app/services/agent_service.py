"""AgentService — the AppSec-engineer AI reviewer.

Takes the repository structure plus Semgrep and Gitleaks findings and asks an
LLM to reason about them like a human security engineer: correlate across tools,
deduplicate, prioritize by real risk, explain why each issue matters, propose
remediations, and write executive + developer summaries. The result is
structured `AgentReport` JSON, not prose.

Design notes:
- Prompts are externalized (`agents/prompts/`), loaded via `PromptLibrary`.
- The provider is swappable (`LLMProvider`); default is free Google Gemini.
- Tool calling is supported via `ToolRegistry` — none registered yet, but the
  turn loop already handles tool-call round-trips.
- Model output is parsed and validated against `AgentReport`, with a bounded
  retry that feeds the validation error back to the model.
"""

from __future__ import annotations

import json
import re

from pydantic import ValidationError

from app.agents.prompts import PromptLibrary
from app.agents.provider import (
    LLMError,
    LLMMessage,
    LLMProvider,
    LLMResponse,
    get_llm_provider,
)
from app.agents.references import curate_references
from app.agents.repo_tools import build_repo_tools
from app.agents.tools import ToolRegistry
from app.config.settings import Settings, get_settings
from app.models.agent import AgentReport
from app.models.finding import Finding, Severity
from app.models.repository import RepositoryMetadata
from app.models.scan import ScanReport
from app.utils.logging import get_logger
from app.utils.workspace import Workspace

logger = get_logger(__name__)

# Cap findings sent to the model to keep the prompt within budget.
_MAX_FINDINGS = 300
# Max model round-trips per review. The last turn forces a final answer (tools
# withdrawn), so this bounds investigation depth without ever erroring out.
_MAX_TURNS = 10

# Sent on the final turn to make the agent stop investigating and report.
_FORCE_FINAL = (
    "You have gathered enough evidence. Stop calling tools now and output ONLY "
    "the final AgentReport JSON object, based on the findings and everything you "
    "have already investigated."
)


class AgentService:
    """Runs the LLM security-review agent over scanner output."""

    def __init__(
        self,
        settings: Settings | None = None,
        provider: LLMProvider | None = None,
        prompts: PromptLibrary | None = None,
        tools: ToolRegistry | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._provider = provider or get_llm_provider(self._settings)
        self._prompts = prompts or PromptLibrary()
        # An explicitly injected registry (e.g. in tests) overrides the default
        # of building repo-investigation tools per request.
        self._tools = tools
        self._workspace = Workspace(self._settings.scan_workspace_dir)

    async def analyze(
        self, repository: RepositoryMetadata, scan: ScanReport
    ) -> AgentReport:
        """Produce a prioritized security review from scan output."""
        findings = scan.findings[:_MAX_FINDINGS]

        # No findings → no need to spend a model call.
        if not findings:
            return self._empty_report(repository, scan)

        indexed = {f"F{i + 1}": finding for i, finding in enumerate(findings)}
        messages = [
            LLMMessage(role="system", content=self._prompts.render("system")),
            LLMMessage(
                role="user",
                content=self._prompts.render(
                    "analysis",
                    {
                        "REPO_SUMMARY": self._repo_summary(repository),
                        "FINDINGS_COUNT": str(len(scan.findings)),
                        "FINDINGS_JSON": self._findings_json(indexed),
                    },
                ),
            ),
        ]

        tools = self._resolve_tools(repository.repository_id)
        report = await self._complete_report(messages, tools)

        # Stamp service-owned fields (not trusted from the model).
        report.repository_id = repository.repository_id
        report.model_used = self._provider.model
        report.total_input_findings = len(scan.findings)
        self._enrich_findings(report)
        logger.info(
            "Agent produced %d prioritized issues from %d findings",
            len(report.prioritized_findings),
            len(scan.findings),
        )
        return report

    # ── Enrichment ───────────────────────────────────────────────

    @staticmethod
    def _enrich_findings(report: AgentReport) -> None:
        """Add curated help links and backfill any friendly fields the model
        omitted, so the UI always has a plain summary, steps, and a fix prompt."""
        for f in report.prioritized_findings:
            f.references = curate_references(f.category, f.owasp_category)
            if not f.plain_summary.strip():
                f.plain_summary = f.why_it_matters
            if not f.fix_steps:
                f.fix_steps = [f.remediation] if f.remediation.strip() else []
            if not f.fix_prompt.strip():
                where = ", ".join(f.affected_files) or "the affected file(s)"
                f.fix_prompt = (
                    f"Fix this security issue in {where}: {f.title}. "
                    f"{f.remediation} Keep the existing behavior unchanged."
                )

    # ── Tooling ──────────────────────────────────────────────────

    def _resolve_tools(self, repository_id: str) -> ToolRegistry:
        """Build the agent's tool registry for this review.

        An injected registry (tests) wins; otherwise bind read-only
        investigation tools to the repository's staged directory. If the repo
        isn't on disk (shouldn't happen post-scan), fall back to no tools so the
        agent still produces a report from the findings alone.
        """
        if self._tools is not None:
            return self._tools
        try:
            root = self._workspace.path_for(repository_id)
        except ValueError:
            return ToolRegistry()
        if not root.exists():
            return ToolRegistry()
        return ToolRegistry(build_repo_tools(root))

    # ── Model interaction ────────────────────────────────────────

    async def _complete_report(
        self, messages: list[LLMMessage], tools: ToolRegistry
    ) -> AgentReport:
        """Call the model, parsing/validating JSON with a bounded retry."""
        retries = max(0, self._settings.llm_json_retries)
        for attempt in range(retries + 1):
            response = await self._run_turns(messages, tools)
            text = response.content or ""
            try:
                data = _loads_lenient(text)
                return AgentReport.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as exc:
                if attempt >= retries:
                    raise LLMError(
                        f"Model did not return valid AgentReport JSON: {exc}"
                    ) from exc
                logger.warning("Invalid agent JSON (attempt %d); retrying", attempt + 1)
                messages.append(LLMMessage(role="assistant", content=text))
                messages.append(
                    LLMMessage(
                        role="user",
                        content=(
                            "Your previous reply was not valid JSON for the schema "
                            f"({exc}). Reply with ONLY the corrected JSON object."
                        ),
                    )
                )
        raise LLMError("Unreachable")  # pragma: no cover

    async def _run_turns(
        self, messages: list[LLMMessage], tools: ToolRegistry
    ) -> LLMResponse:
        """Drive the conversation, servicing tool calls until a final answer.

        With no tools registered this is a single request. With tools, the agent
        can read files / search the code to verify findings before answering;
        each turn we run every tool call it requested and feed the results back.
        """
        tool_schemas = tools.schemas() or None

        response = None
        for turn in range(_MAX_TURNS):
            # On the final turn, take the tools away and demand the report, so a
            # big repo (lots to investigate) ends with an answer instead of an
            # error — we keep the evidence already gathered rather than throwing
            # the whole review away.
            final_turn = turn == _MAX_TURNS - 1
            if final_turn and tool_schemas:
                messages.append(LLMMessage(role="user", content=_FORCE_FINAL))

            turn_tools = None if final_turn else tool_schemas
            # `json_object` mode and tool calling don't mix on some backends, so
            # only force JSON when we're not offering tools this turn.
            response_format = {"type": "json_object"} if turn_tools is None else None

            response = await self._provider.chat(
                messages, tools=turn_tools, response_format=response_format
            )
            if not response.tool_calls:
                return response

            messages.append(
                LLMMessage(
                    role="assistant",
                    content=response.content,
                    tool_calls=response.tool_calls,
                    # Replay the provider's exact assistant turn when available
                    # (preserves Gemini's thought_signature on the tool calls).
                    wire_override=response.raw_message,
                )
            )
            logger.info(
                "Agent invoked %d tool(s): %s",
                len(response.tool_calls),
                ", ".join(c.name for c in response.tool_calls),
            )
            for call in response.tool_calls:
                messages.append(await tools.dispatch(call))

        # Unreachable: the final turn offers no tools, so it returns above.
        return response  # pragma: no cover

    # ── Prompt building ──────────────────────────────────────────

    @staticmethod
    def _findings_json(indexed: dict[str, Finding]) -> str:
        payload = [
            {
                "id": fid,
                "scanner": f.scanner,
                "severity": f.severity.value,
                "file": f.file,
                "line": f.line,
                "title": f.title,
                "description": f.description,
                "owasp": f.owasp_category,
                "cwe": f.cwe_ids,
                "rule_id": f.rule_id,
            }
            for fid, f in indexed.items()
        ]
        return json.dumps(payload, indent=2)

    @staticmethod
    def _repo_summary(repository: RepositoryMetadata) -> str:
        languages = ", ".join(
            f"{lang.language} ({lang.percentage}%)" for lang in repository.languages
        ) or "unknown"
        managers = ", ".join(repository.package_managers) or "none detected"
        files = _flatten_files(repository)
        preview = "\n".join(f"- {path}" for path in files[:150])
        more = f"\n… and {len(files) - 150} more files" if len(files) > 150 else ""

        return (
            f"Primary language: {repository.primary_language or 'unknown'}\n"
            f"Languages: {languages}\n"
            f"Package managers: {managers}\n"
            f"File count: {repository.file_count}\n\n"
            f"Files:\n{preview}{more}"
        )

    # ── Fallback ─────────────────────────────────────────────────

    @staticmethod
    def _empty_report(
        repository: RepositoryMetadata, scan: ScanReport
    ) -> AgentReport:
        return AgentReport(
            repository_id=repository.repository_id,
            total_input_findings=0,
            overall_risk=Severity.INFO,
            executive_summary=(
                "The automated scanners reported no security findings for this "
                "repository. This is not a guarantee of safety, but no known "
                "issues were detected by static analysis or secret scanning."
            ),
            developer_summary=(
                "No Semgrep or Gitleaks findings to triage. Consider adding "
                "deeper rulesets or manual review for defense in depth."
            ),
        )


# ── module helpers ───────────────────────────────────────────────

def _flatten_files(repository: RepositoryMetadata) -> list[str]:
    """Depth-first list of file paths from the repository tree."""
    paths: list[str] = []

    def walk(node) -> None:  # noqa: ANN001 — TreeNode, avoid import cycle noise
        if node.type.value == "file":
            paths.append(node.path)
            return
        for child in node.children or []:
            walk(child)

    walk(repository.tree)
    return paths


def _strip_code_fences(text: str) -> str:
    """Remove ```json fences some models add despite instructions."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[-1] if "\n" in stripped else stripped
        if stripped.endswith("```"):
            stripped = stripped[: -len("```")]
    return stripped.strip()


def _loads_lenient(text: str):
    """Parse the model's JSON, repairing invalid escapes as a fallback.

    Once the agent quotes real code/paths/regexes in its report, models
    intermittently emit a lone backslash that isn't a valid JSON escape
    (e.g. `\\d` in a regex, `\\U` in a Windows path). We try a strict parse
    first, then a repaired one, before letting the caller retry.
    """
    cleaned = _strip_code_fences(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return json.loads(_repair_json_escapes(cleaned))


# Valid JSON escape sequences following a backslash.
_VALID_ESCAPE = re.compile(r'\\(["\\/bfnrtu]|u[0-9a-fA-F]{4})')


def _repair_json_escapes(text: str) -> str:
    """Double any backslash that doesn't start a valid JSON escape.

    Consumes valid escapes (incl. `\\\\` and `\\uXXXX`) as whole units so
    adjacent backslashes aren't mangled; a stray `\\x` becomes `\\\\x`.
    JSON has no backslashes outside string literals, so this is safe.
    """
    out: list[str] = []
    i = 0
    while i < len(text):
        if text[i] == "\\":
            match = _VALID_ESCAPE.match(text, i)
            if match:
                out.append(match.group(0))
                i = match.end()
            else:
                out.append("\\\\")
                i += 1
        else:
            out.append(text[i])
            i += 1
    return "".join(out)
