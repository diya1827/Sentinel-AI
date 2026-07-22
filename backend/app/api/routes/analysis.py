"""AI analysis endpoint.

    POST /repositories/{repository_id}/analyze   scan + AI security review

Composes the pipeline over an already-ingested repository: describe its
structure, run the scanners, then hand both to the AppSec-engineer agent. The
handler stays thin — orchestration is a few service calls; the reasoning lives
in `AgentService`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_agent_service,
    get_repository_service,
    get_scanner_service,
)
from app.agents.provider import LLMConfigError, LLMError
from app.models.agent import AgentReport
from app.services.agent_service import AgentService
from app.services.repository_service import RepositoryService
from app.services.scanner_service import ScannerService

router = APIRouter()

RepoServiceDep = Annotated[RepositoryService, Depends(get_repository_service)]
ScannerServiceDep = Annotated[ScannerService, Depends(get_scanner_service)]
AgentServiceDep = Annotated[AgentService, Depends(get_agent_service)]


@router.post(
    "/{repository_id}/analyze",
    response_model=AgentReport,
    summary="Run scanners + AI security review on an ingested repository",
)
async def analyze_repository(
    repository_id: str,
    repositories: RepoServiceDep,
    scanners: ScannerServiceDep,
    agent: AgentServiceDep,
) -> AgentReport:
    """Scan a staged repository and produce a prioritized AI security review."""
    try:
        metadata = await repositories.describe(repository_id)
        scan = await scanners.scan_repository(repository_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Repository not found. Ingest it first via /repositories.",
        ) from exc

    try:
        return await agent.analyze(metadata, scan)
    except LLMConfigError as exc:
        # Misconfiguration (e.g. missing API key) — the service isn't ready.
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except LLMError as exc:
        # Upstream model failure.
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
