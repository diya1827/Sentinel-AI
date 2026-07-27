"""Async scan-job endpoints.

    POST /jobs           enqueue a scan (by repo URL or ingested repository_id)
    GET  /jobs/{id}      poll a job's status / result
    GET  /metrics        live platform counters

The handlers stay thin: submit returns a `job_id` immediately; the heavy work
runs on the worker pool. This is the async seam that makes the scanner a
throughput-oriented platform instead of a blocking request.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator

from app.api.dependencies import get_job_service
from app.models.job import Job, Metrics, SubmitResponse
from app.services.job_service import JobService
from app.utils.git import InvalidRepoUrlError

router = APIRouter()

JobServiceDep = Annotated[JobService, Depends(get_job_service)]


class JobSubmitRequest(BaseModel):
    """Submit a scan by public repo URL *or* an already-ingested repository id."""

    repo_url: str | None = Field(default=None, description="Public GitHub URL.")
    repository_id: str | None = Field(
        default=None, description="Id of a repo already ingested (e.g. ZIP upload)."
    )

    @model_validator(mode="after")
    def _exactly_one(self) -> "JobSubmitRequest":
        if bool(self.repo_url) == bool(self.repository_id):
            raise ValueError("Provide exactly one of repo_url or repository_id.")
        return self


@router.post(
    "/jobs",
    response_model=SubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue a scan + AI review job (returns immediately)",
)
async def submit_job(body: JobSubmitRequest, jobs: JobServiceDep) -> SubmitResponse:
    """Enqueue a job and return its id; poll GET /jobs/{id} for the result."""
    try:
        if body.repo_url:
            return await jobs.submit_github(body.repo_url)
        return await jobs.submit_repository(body.repository_id)  # type: ignore[arg-type]
    except InvalidRepoUrlError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.get(
    "/jobs/{job_id}",
    response_model=Job,
    summary="Poll a job's status and result",
)
async def get_job(job_id: str, jobs: JobServiceDep) -> Job:
    job = await jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found or expired.")
    return job


@router.get("/metrics", response_model=Metrics, summary="Live platform counters")
async def get_metrics(jobs: JobServiceDep) -> Metrics:
    return await jobs.get_metrics()
