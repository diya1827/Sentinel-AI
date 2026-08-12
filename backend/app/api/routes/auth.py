"""Authentication endpoints.

    POST /auth/signup           create an account
    POST /auth/login            exchange credentials for a JWT (rate-limited)
    GET  /auth/me               the current user (requires a Bearer token)
    POST /auth/forgot-password  request a reset link (no account enumeration)
    POST /auth/reset-password   consume a reset token, set a new password
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlmodel import Session

from app.api.dependencies import (
    get_auth_service,
    get_current_user,
    get_email_service,
)
from app.config.settings import get_settings
from app.db.session import get_session
from app.infra.redis import get_redis
from app.models.user import User, UserCreate, UserRead
from app.services.auth_service import AuthService, DuplicateUserError
from app.services.email_service import EmailService

router = APIRouter(prefix="/auth", tags=["auth"])

SessionDep = Annotated[Session, Depends(get_session)]
AuthDep = Annotated[AuthService, Depends(get_auth_service)]


class LoginRequest(BaseModel):
    identifier: str = Field(description="Email or username.")
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class MessageResponse(BaseModel):
    message: str


@router.post(
    "/signup",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
)
def signup(body: UserCreate, session: SessionDep, auth: AuthDep) -> User:
    try:
        return auth.signup(session, body)
    except DuplicateUserError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.post("/login", response_model=TokenResponse, summary="Log in")
async def login(
    body: LoginRequest, session: SessionDep, auth: AuthDep
) -> TokenResponse:
    settings = get_settings()
    redis = get_redis()

    # Abuse protection: atomically count attempts per identifier and lock out.
    key = f"sentinel:login:{body.identifier.lower()}"
    attempts = await redis.incr(key)
    if attempts == 1:
        await redis.expire(key, settings.login_lockout_seconds)
    if attempts > settings.login_max_attempts:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many login attempts. Try again later.",
        )

    user = auth.authenticate(session, body.identifier, body.password)
    if user is None:
        # Generic error — never reveal whether the account exists.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials.")

    await redis.delete(key)  # reset the counter on success
    from app.utils.security import create_access_token

    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserRead, summary="Current user")
def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


@router.post(
    "/forgot-password", response_model=MessageResponse, summary="Request a reset link"
)
def forgot_password(
    body: ForgotPasswordRequest,
    session: SessionDep,
    auth: AuthDep,
    email: Annotated[EmailService, Depends(get_email_service)],
) -> MessageResponse:
    raw_token = auth.create_reset_token(session, body.email)
    if raw_token:  # only send if the user exists — response is identical either way
        link = f"{get_settings().frontend_base_url}/reset-password?token={raw_token}"
        email.send_password_reset(body.email, link)
    # Same response whether or not the email exists (no enumeration).
    return MessageResponse(
        message="If that email is registered, a reset link has been sent."
    )


@router.post(
    "/reset-password", response_model=MessageResponse, summary="Set a new password"
)
def reset_password(
    body: ResetPasswordRequest, session: SessionDep, auth: AuthDep
) -> MessageResponse:
    if not auth.reset_password(session, body.token, body.new_password):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Invalid or expired reset token."
        )
    return MessageResponse(message="Password updated. You can now log in.")
