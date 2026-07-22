"""Review request/response contracts.

SCAFFOLD: shape defined; fields may evolve as features land.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.models.finding import Finding


class ReviewRequest(BaseModel):
    """Input describing what to review (a repo URL, path, or diff)."""

    # Exactly one source will be used; kept optional during scaffold.
    repo_url: str | None = None
    source_path: str | None = None


class ReviewReport(BaseModel):
    """Aggregated, triaged output of a full review."""

    findings: list[Finding] = []
    summary: str | None = None
