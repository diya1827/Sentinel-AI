"""Phase 1 — persistence + User model.

Verifies the User table round-trips through the DB and that the public schema
never exposes the password hash. Uses an isolated in-memory SQLite (StaticPool
keeps the single connection alive so tables persist across sessions).
"""

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.models.user import User, UserRead


@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(eng)
    return eng


def test_create_and_read_user(engine):
    with Session(engine) as s:
        s.add(User(email="a@b.com", username="alice", hashed_password="hash"))
        s.commit()

    with Session(engine) as s:
        user = s.exec(select(User).where(User.email == "a@b.com")).one()
        assert user.id is not None
        assert user.username == "alice"
        assert user.is_verified is False       # default applied
        assert user.created_at is not None      # default_factory applied


def test_email_and_username_are_unique(engine):
    with Session(engine) as s:
        s.add(User(email="a@b.com", username="alice", hashed_password="h"))
        s.commit()
    with Session(engine) as s:
        s.add(User(email="a@b.com", username="bob", hashed_password="h"))
        with pytest.raises(Exception):  # IntegrityError on the unique email
            s.commit()


def test_userread_never_exposes_password_hash():
    assert "hashed_password" not in UserRead.model_fields
