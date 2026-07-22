"""Top-level API router aggregation.

Individual resource routers (e.g. reviews, scans) are included here and the
combined router is mounted in `app.main` under the `/api/v1` prefix.

SCAFFOLD: no routes implemented yet.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import analysis, repositories, scans

api_router = APIRouter()

api_router.include_router(
    repositories.router, prefix="/repositories", tags=["repositories"]
)
api_router.include_router(scans.router, prefix="/repositories", tags=["scans"])
api_router.include_router(analysis.router, prefix="/repositories", tags=["analysis"])
