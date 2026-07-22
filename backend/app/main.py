"""FastAPI application entrypoint.

This module wires together the transport layer (routers), middleware, and
application lifecycle. It intentionally contains no business logic — that
lives in the `services`, `agents`, and `scanners` layers.

NOTE: This is scaffold only. Routers and services are stubs to be filled in.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown hooks (e.g. warm LLM client, verify scanner CLIs)."""
    # TODO: initialize shared clients / validate `semgrep` & `gitleaks` on PATH
    yield
    # TODO: graceful cleanup


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
