"""AuthService — account creation, login, and password reset.

All password hashing / token work lives in `utils.security`; this service owns
the DB interactions and the rules (uniqueness, token validity). It never returns
or logs a password hash.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlmodel import Session, or_, select

from app.config.settings import Settings, get_settings
from app.models.auth_token import PasswordResetToken
from app.models.user import User, UserCreate
from app.utils.security import (
    generate_reset_token,
    hash_password,
    hash_reset_token,
    verify_password,
)


class AuthError(Exception):
    """Base class for auth failures the API turns into 4xx responses."""


class DuplicateUserError(AuthError):
    """Email or username already registered."""


class AuthService:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    # ── Registration / login ─────────────────────────────────────
    def signup(self, session: Session, data: UserCreate) -> User:
        existing = session.exec(
            select(User).where(
                or_(User.email == data.email, User.username == data.username)
            )
        ).first()
        if existing is not None:
            raise DuplicateUserError("Email or username is already in use.")

        user = User(
            email=data.email,
            username=data.username,
            hashed_password=hash_password(data.password),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    def authenticate(
        self, session: Session, identifier: str, password: str
    ) -> User | None:
        """Return the user iff the identifier (email or username) + password match.

        Returns None on any failure — the caller gives a single generic error so
        it can't be used to probe which accounts exist.
        """
        user = session.exec(
            select(User).where(
                or_(User.email == identifier, User.username == identifier)
            )
        ).first()
        if user is None or not verify_password(password, user.hashed_password):
            return None
        return user

    # ── Password reset ───────────────────────────────────────────
    def create_reset_token(self, session: Session, email: str) -> str | None:
        """Issue a reset token for `email`, or None if no such user.

        Returns the *raw* token (to be emailed); only its hash is stored.
        """
        user = session.exec(select(User).where(User.email == email)).first()
        if user is None:
            return None

        raw = generate_reset_token()
        token = PasswordResetToken(
            user_id=user.id,
            token_hash=hash_reset_token(raw),
            expires_at=datetime.utcnow()
            + timedelta(minutes=self._settings.reset_token_expire_minutes),
        )
        session.add(token)
        session.commit()
        return raw

    def reset_password(
        self, session: Session, raw_token: str, new_password: str
    ) -> bool:
        """Consume a valid reset token and set a new password. Returns success."""
        token = session.exec(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == hash_reset_token(raw_token)
            )
        ).first()

        if (
            token is None
            or token.used_at is not None
            or token.expires_at < datetime.utcnow()
        ):
            return False

        user = session.get(User, token.user_id)
        if user is None:
            return False

        user.hashed_password = hash_password(new_password)
        token.used_at = datetime.utcnow()
        session.add(user)
        session.add(token)
        session.commit()
        return True
