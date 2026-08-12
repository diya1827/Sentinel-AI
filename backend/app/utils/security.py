"""Security primitives — password hashing, JWTs, and reset-token hashing.

Kept in one small module so the crypto choices live in a single place:

* **Passwords** → bcrypt (salted, slow-by-design). We only ever store the hash;
  verification is constant-time via passlib.
* **Access tokens** → signed JWTs (HS256) with an expiry; verified on every
  protected request.
* **Reset tokens** → a high-entropy random string given to the user, but only
  its SHA-256 hash is stored, so a database leak can't yield usable tokens.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config.settings import get_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Passwords ────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _pwd_context.verify(password, hashed)


# ── Access tokens (JWT) ──────────────────────────────────────────
def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    """Sign a JWT whose `sub` identifies the user (we use the user id)."""
    settings = get_settings()
    minutes = expires_minutes or settings.jwt_expire_minutes
    payload = {
        "sub": str(subject),
        "exp": datetime.utcnow() + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any] | None:
    """Return the JWT claims, or None if the token is invalid/expired."""
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


# ── Reset tokens ─────────────────────────────────────────────────
def generate_reset_token() -> str:
    """A URL-safe, high-entropy token to email the user (raw form)."""
    return secrets.token_urlsafe(32)


def hash_reset_token(raw: str) -> str:
    """SHA-256 of a reset token — this (not the raw token) is stored/looked up.

    SHA-256 is appropriate here (not bcrypt): the token is already high-entropy
    and random, so it needs no salting/stretching, and a deterministic hash lets
    us look the token up by value.
    """
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
