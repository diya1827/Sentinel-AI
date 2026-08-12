"""Password-reset token table.

Only the SHA-256 *hash* of the token is stored (`token_hash`), never the raw
value the user receives. A token is valid only if it exists, hasn't expired, and
hasn't been used — enforced in `AuthService.reset_password`.
"""

from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel


class PasswordResetToken(SQLModel, table=True):
    __tablename__ = "password_reset_tokens"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    token_hash: str = Field(index=True, unique=True)
    expires_at: datetime
    used_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
