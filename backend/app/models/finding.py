"""The unified `Finding` — the single vocabulary every scanner normalizes into.

Semgrep and Gitleaks emit very different JSON; each wrapper maps its output
onto this one shape so that services, the API, and ultimately the frontend deal
with exactly one schema regardless of which tool produced a result.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Normalized severity scale, shared across all scanners."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Finding(BaseModel):
    """A single, tool-agnostic security finding.

    The seven core fields below are the contract the frontend consumes.
    `rule_id` is kept as optional provenance (used later for dedup/triage) but
    is not required by consumers.
    """

    scanner: str = Field(description="Which scanner produced this, e.g. 'semgrep'.")
    severity: Severity
    file: str = Field(description="Repo-relative path of the affected file.")
    line: int | None = Field(default=None, description="1-based line number, if known.")
    title: str = Field(description="Short, human-readable summary of the issue.")
    description: str | None = Field(default=None, description="What the issue is.")
    remediation: str | None = Field(default=None, description="How to fix it.")

    # Provenance (optional; not part of the minimal consumed contract).
    rule_id: str | None = Field(default=None, description="Originating rule identifier.")
