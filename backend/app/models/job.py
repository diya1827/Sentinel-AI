"""Job models — an async scan/review job and the platform metrics snapshot.

A `Job` is submitted (`POST /jobs`), enqueued in Redis, picked up by a worker,
and polled (`GET /jobs/{id}`) until it reaches a terminal state. The heavy work
(clone + Semgrep + Gitleaks + LLM) happens off the request path.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class JobKind(str, Enum):
    GITHUB = "github"   # submitted as a repo URL; the worker clones it
    UPLOAD = "upload"   # already-ingested repository_id (from a ZIP upload)


class Job(BaseModel):
    """A unit of async work and its current state (mirrors the Redis hash)."""

    id: str
    kind: JobKind
    status: JobStatus
    repo_url: str | None = None
    repository_id: str | None = None
    commit_sha: str | None = None
    # Set when status == done: the AgentReport (kept as a raw dict so the API
    # returns exactly what the synchronous endpoint used to).
    result: dict[str, Any] | None = None
    error: str | None = None
    cached: bool = False          # result served from the commit-SHA cache
    created_at: float | None = None
    updated_at: float | None = None


class SubmitResponse(BaseModel):
    """Returned immediately from POST /jobs — the client then polls the job."""

    job_id: str
    status: JobStatus
    deduplicated: bool = Field(
        default=False,
        description="True if an identical in-flight submit already existed.",
    )


class Metrics(BaseModel):
    """Live platform counters, all maintained via atomic Redis increments."""

    jobs_queued: int = 0
    jobs_running: int = 0
    jobs_done: int = 0
    jobs_failed: int = 0
    jobs_deduplicated: int = 0
    cache_hits: int = 0
    findings_by_severity: dict[str, int] = Field(default_factory=dict)
