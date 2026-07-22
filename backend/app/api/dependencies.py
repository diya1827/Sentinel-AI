"""Shared FastAPI dependencies (injectable providers).

Keeps construction of services out of the route handlers so they stay thin and
are easy to override in tests via `app.dependency_overrides`.
"""

from __future__ import annotations

from functools import lru_cache

from app.services.agent_service import AgentService
from app.services.repository_service import RepositoryService
from app.services.scanner_service import ScannerService


@lru_cache
def get_repository_service() -> RepositoryService:
    """Provide a singleton RepositoryService."""
    return RepositoryService()


@lru_cache
def get_scanner_service() -> ScannerService:
    """Provide a singleton ScannerService."""
    return ScannerService()


@lru_cache
def get_agent_service() -> AgentService:
    """Provide a singleton AgentService."""
    return AgentService()
