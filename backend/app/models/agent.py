"""AI agent output contracts.

`AgentReport` is the structured result of the AppSec-engineer agent: prioritized,
correlated, deduplicated issues (not a restatement of scanner output) plus the
executive and developer summaries. The frontend renders this directly.

Service-populated fields (`repository_id`, `model_used`, `total_input_findings`)
default so the model's JSON need not include them.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from app.models.finding import Severity


class Confidence(str, Enum):
    """How sure the agent is that an issue is real and correctly assessed."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Reference(BaseModel):
    """A curated help link (title + url). Populated server-side, not by the LLM."""

    title: str
    url: str


class PrioritizedFinding(BaseModel):
    """One correlated, deduplicated, ranked issue produced by the agent."""

    id: str = Field(description="Agent-assigned issue id, e.g. 'V1'.")
    title: str
    severity: Severity
    priority: int = Field(description="1-based rank; 1 is most urgent.")
    category: str = Field(description="Vulnerability class, e.g. 'SQL Injection'.")
    owasp_category: str | None = Field(
        default=None,
        description="OWASP Top 10 2021 label, e.g. 'A03:2021 - Injection', if known.",
    )
    affected_files: list[str] = Field(default_factory=list)
    source_finding_ids: list[str] = Field(
        default_factory=list,
        description="Raw scanner finding ids this issue was built from.",
    )
    scanners: list[str] = Field(default_factory=list)
    why_it_matters: str
    exploitability: str | None = None
    remediation: str
    confidence: Confidence = Confidence.MEDIUM
    duplicate_of: str | None = None

    # ── Human-friendly, actionable extras ────────────────────────
    plain_summary: str = Field(
        default="",
        description="1-2 sentences a non-technical person understands (no jargon).",
    )
    fix_steps: list[str] = Field(
        default_factory=list,
        description="A few short, plain-language steps to fix it.",
    )
    fix_prompt: str = Field(
        default="",
        description="A copy-paste prompt for an AI coding assistant to fix this issue.",
    )
    references: list[Reference] = Field(
        default_factory=list,
        description="Curated help links (added server-side; not from the model).",
    )


class AgentReport(BaseModel):
    """The agent's full security review."""

    repository_id: str = ""
    model_used: str | None = None
    total_input_findings: int = 0

    overall_risk: Severity
    executive_summary: str
    developer_summary: str
    prioritized_findings: list[PrioritizedFinding] = Field(default_factory=list)
    correlations: list[str] = Field(default_factory=list)
    duplicates_removed: int = 0
    notes: str | None = None
