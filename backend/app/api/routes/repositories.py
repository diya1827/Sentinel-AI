"""Repository ingestion endpoints.

    POST   /repositories/github   ingest a public GitHub repo (JSON body)
    POST   /repositories/upload   ingest an uploaded ZIP (multipart form)
    DELETE /repositories/{id}      clean up a staged repository

Handlers stay thin: validate transport-level concerns, delegate to
`RepositoryService`, and translate domain errors into HTTP status codes.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.dependencies import get_repository_service
from app.config.settings import get_settings
from app.models.repository import GitHubIngestRequest, RepositoryMetadata
from app.services.repository_service import RepositoryService
from app.utils.archive import ArchiveError
from app.utils.git import GitCloneError, InvalidRepoUrlError

router = APIRouter()

ServiceDep = Annotated[RepositoryService, Depends(get_repository_service)]

_UPLOAD_CHUNK = 1024 * 1024  # 1 MiB


@router.post(
    "/github",
    response_model=RepositoryMetadata,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a public GitHub repository",
)
async def ingest_github(
    payload: GitHubIngestRequest,
    service: ServiceDep,
) -> RepositoryMetadata:
    """Clone and analyze a public GitHub repository."""
    try:
        return await service.ingest_from_github(payload.repo_url)
    except InvalidRepoUrlError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except GitCloneError as exc:
        # Upstream (git/host) failed — a bad gateway from our perspective.
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc


@router.post(
    "/upload",
    response_model=RepositoryMetadata,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest an uploaded ZIP archive",
)
async def ingest_upload(
    service: ServiceDep,
    file: Annotated[UploadFile, File(description="A .zip archive of the repository")],
) -> RepositoryMetadata:
    """Extract and analyze an uploaded ZIP archive."""
    settings = get_settings()

    filename = file.filename or ""
    if not filename.lower().endswith(".zip"):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Only .zip uploads are supported.",
        )

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    tmp_path = await _spool_upload(file, max_bytes)

    try:
        return await service.ingest_from_zip(tmp_path)
    except ArchiveError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    finally:
        # The extracted copy is owned by the service; the raw upload is not.
        tmp_path.unlink(missing_ok=True)


@router.delete(
    "/{repository_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,  # 204 carries no body; avoid inferring NoneType as one
    summary="Delete a staged repository",
)
async def delete_repository(repository_id: str, service: ServiceDep) -> None:
    """Remove a previously ingested repository's staged files."""
    try:
        removed = service.cleanup(repository_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if not removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Repository not found.")


async def _spool_upload(file: UploadFile, max_bytes: int) -> Path:
    """Stream an upload to a temp file, enforcing a size cap as we go.

    Returns the path to the spooled file. Raises 413 if the cap is exceeded.
    """
    fd, tmp_name = tempfile.mkstemp(suffix=".zip")
    tmp_path = Path(tmp_name)
    written = 0
    try:
        with os.fdopen(fd, "wb") as buffer:
            while chunk := await file.read(_UPLOAD_CHUNK):
                written += len(chunk)
                if written > max_bytes:
                    raise HTTPException(
                        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        f"Upload exceeds the {max_bytes // (1024 * 1024)} MB limit.",
                    )
                buffer.write(chunk)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
    return tmp_path
