"""Shared FastAPI dependencies (injectable providers).

Keeps construction of services out of the route handlers so they stay thin and
are easy to override in tests via `app.dependency_overrides`.
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.db.session import get_session
from app.models.user import User
from app.services.agent_service import AgentService
from app.services.auth_service import AuthService
from app.services.email_service import EmailService
from app.services.job_service import JobService
from app.services.repository_service import RepositoryService
from app.services.scanner_service import ScannerService
from app.utils.security import decode_token

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=True)


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


@lru_cache
def get_job_service() -> JobService:
    """Provide a singleton JobService (shared by API handlers and workers)."""
    return JobService()


@lru_cache
def get_auth_service() -> AuthService:
    """Provide a singleton AuthService."""
    return AuthService()


@lru_cache
def get_email_service() -> EmailService:
    """Provide a singleton EmailService."""
    return EmailService()


def get_current_user(
    token: str = Depends(_oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    """Resolve the authenticated user from a Bearer JWT, or raise 401."""
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Invalid or expired token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise unauthorized
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise unauthorized
    user = session.get(User, user_id)
    if user is None:
        raise unauthorized
    return user
