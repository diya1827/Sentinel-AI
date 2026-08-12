"""Scan result contracts.

`ScannerResult` describes one tool's run (so a single scanner failing is a
first-class, reportable outcome — not an exception that sinks the whole scan).
`ScanReport` is the aggregate the API returns: per-scanner results plus a merged
findings list and severity tally for convenient frontend consumption.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from app.models.finding import Finding


class ScanStatus(str, Enum):
    """Outcome of a single scanner's run."""

    SUCCESS = "success"
    FAILED = "failed"


class ScannerResult(BaseModel):
    """The outcome of running one scanner against a target."""

    scanner: str
    status: ScanStatus
    findings: list[Finding] = Field(default_factory=list)
    error: str | None = Field(
        default=None, description="Failure reason when status is 'failed'."
    )
    duration_seconds: float | None = None


class ScanReport(BaseModel):
    """Aggregated result of scanning a repository with every scanner."""

    repository_id: str
    results: list[ScannerResult] = Field(default_factory=list)
    findings: list[Finding] = Field(
        default_factory=list, description="All findings merged across scanners."
    )
    total_findings: int = 0
    severity_counts: dict[str, int] = Field(default_factory=dict)
    owasp_counts: dict[str, int] = Field(
        default_factory=dict,
        description="OWASP Top 10 2021 category label → finding count.",
    )
