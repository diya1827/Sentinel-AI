"""Scanning endpoints.

    POST /repositories/{repository_id}/scan   run all scanners on a staged repo

The handler stays thin: delegate to `ScannerService` and translate the two
addressing errors (bad id / not ingested) into HTTP codes. Individual scanner
failures are *not* errors here — they're reported inside the 200 `ScanReport`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_scanner_service
from app.models.scan import ScanReport
from app.services.scanner_service import ScannerService

router = APIRouter()

ServiceDep = Annotated[ScannerService, Depends(get_scanner_service)]


@router.post(
    "/{repository_id}/scan",
    response_model=ScanReport,
    summary="Run all security scanners on an ingested repository",
)
async def scan_repository(
    repository_id: str,
    service: ServiceDep,
) -> ScanReport:
    """Scan a staged repository with Semgrep and Gitleaks."""
    try:
        return await service.scan_repository(repository_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Repository not found. Ingest it first via /repositories.",
        ) from exc
