"""User table and the auth request/response schemas.

`User` is the persisted row (includes `hashed_password`, which never leaves the
server). The `UserCreate` / `UserRead` schemas are the API surface — `UserRead`
deliberately omits the password hash so it can't be serialized to a client.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import EmailStr
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    # Naive UTC — stored consistently so comparisons work across SQLite/Postgres.
    return datetime.utcnow()


class User(SQLModel, table=True):
    """A registered account (persisted)."""

    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str
    is_verified: bool = Field(default=False)
    created_at: datetime = Field(default_factory=_utcnow)


# ── API schemas ──────────────────────────────────────────────────

class UserCreate(SQLModel):
    """Sign-up payload."""

    email: EmailStr
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)


class UserRead(SQLModel):
    """Public view of a user — never includes the password hash."""

    id: int
    email: EmailStr
    username: str
    is_verified: bool
    created_at: datetime
