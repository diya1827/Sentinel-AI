"""FastAPI application entrypoint.

This module wires together the transport layer (routers), middleware, and
application lifecycle. It intentionally contains no business logic — that
lives in the `services`, `agents`, and `scanners` layers.

NOTE: This is scaffold only. Routers and services are stubs to be filled in.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.dependencies import get_job_service
from app.api.router import api_router
from app.config.settings import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the in-process worker pool; cancel it on shutdown."""
    settings = get_settings()
    job_service = get_job_service()
    workers = [
        asyncio.create_task(job_service.run_worker(f"worker-{i}"))
        for i in range(max(1, settings.worker_concurrency))
    ]
    logger.info("Started %d scan worker(s)", len(workers))
    try:
        yield
    finally:
        for task in workers:
            task.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
        logger.info("Worker pool stopped")


def create_app() -> FastAPI:
    """Application factory — keeps construction testable and explicit."""
    settings = get_settings()

    app = FastAPI(
        title="Sentinel AI",
        description="AI-powered Application Security Reviewer",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        # Optional regex lets a deployed frontend (e.g. Vercel preview URLs)
        # be allowed without hardcoding every domain.
        allow_origin_regex=settings.cors_origin_regex or None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Transport layer.
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        """Liveness probe used by Docker/K8s healthchecks."""
        return {"status": "ok"}

    return app


app = create_app()
