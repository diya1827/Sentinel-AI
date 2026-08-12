"""Auth API tests — Phases 2, 3, 5, 6.

An isolated in-memory DB is injected via `get_session` override, so tests never
touch the real SQLite file. Login rate-limiting uses the app's Redis (fakeredis
in tests); tests use distinct identifiers to stay independent.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.db.session import get_session
from app.infra.redis import get_redis
from app.main import app
from app.models.auth_token import PasswordResetToken  # noqa: F401 — register table
from app.models.user import User
from app.services.auth_service import AuthService


@pytest.fixture
def ctx():
    # Fresh fakeredis bound to this TestClient's event loop (the client is a
    # cached singleton otherwise, which breaks across per-test loops).
    get_redis.cache_clear()
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)

    def _override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = _override
    with TestClient(app) as client:
        yield client, engine
    app.dependency_overrides.clear()
    get_redis.cache_clear()


def _signup(client, email="a@b.com", username="alice", password="supersecret"):
    return client.post(
        "/api/v1/auth/signup",
        json={"email": email, "username": username, "password": password},
    )


# ── Signup (Phase 2) ─────────────────────────────────────────────

def test_signup_creates_user_and_hides_hash(ctx):
    client, engine = ctx
    r = _signup(client)
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "a@b.com"
    assert "hashed_password" not in body  # never serialized

    # Password is stored hashed (bcrypt), not plaintext.
    with Session(engine) as s:
        user = s.exec(select(User)).one()
        assert user.hashed_password != "supersecret"
        assert user.hashed_password.startswith("$2")


def test_signup_rejects_duplicate(ctx):
    client, _ = ctx
    assert _signup(client).status_code == 201
    dup = _signup(client, username="other")  # same email
    assert dup.status_code == 409


def test_signup_rejects_weak_password(ctx):
    client, _ = ctx
    r = _signup(client, password="short")  # < 8 chars
    assert r.status_code == 422


# ── Login + /me (Phases 2, 3) ────────────────────────────────────

def test_login_then_me(ctx):
    client, _ = ctx
    _signup(client, email="log@in.com", username="loginuser")
    r = client.post(
        "/api/v1/auth/login",
        json={"identifier": "log@in.com", "password": "supersecret"},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "loginuser"


def test_login_wrong_password_is_generic_401(ctx):
    client, _ = ctx
    _signup(client, email="w@p.com", username="wpuser")
    r = client.post(
        "/api/v1/auth/login", json={"identifier": "w@p.com", "password": "nope"}
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid credentials."


def test_me_requires_token(ctx):
    client, _ = ctx
    assert client.get("/api/v1/auth/me").status_code == 401
    bad = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert bad.status_code == 401


# ── Forgot / reset (Phase 5) ─────────────────────────────────────

def test_forgot_password_does_not_enumerate(ctx):
    client, _ = ctx
    _signup(client, email="real@x.com", username="realx")
    exists = client.post("/api/v1/auth/forgot-password", json={"email": "real@x.com"})
    missing = client.post("/api/v1/auth/forgot-password", json={"email": "nope@x.com"})
    assert exists.status_code == missing.status_code == 200
    assert exists.json() == missing.json()  # identical response either way


def test_reset_password_flow_and_single_use(ctx):
    client, engine = ctx
    assert _signup(
        client, email="r@x.com", username="rxuser", password="oldpassword"
    ).status_code == 201

    # Mint a real reset token via the service (same DB engine).
    with Session(engine) as s:
        raw = AuthService().create_reset_token(s, "r@x.com")
    assert raw

    r = client.post(
        "/api/v1/auth/reset-password", json={"token": raw, "new_password": "newpassword"}
    )
    assert r.status_code == 200

    # Old password no longer works; new one does.
    assert client.post(
        "/api/v1/auth/login", json={"identifier": "r@x.com", "password": "oldpassword"}
    ).status_code == 401
    assert client.post(
        "/api/v1/auth/login", json={"identifier": "r@x.com", "password": "newpassword"}
    ).status_code == 200

    # Token is single-use.
    reuse = client.post(
        "/api/v1/auth/reset-password", json={"token": raw, "new_password": "another1"}
    )
    assert reuse.status_code == 400


# ── Rate limiting (Phase 6) ──────────────────────────────────────

def test_login_rate_limited_after_max_attempts(ctx):
    client, _ = ctx
    _signup(client, email="rl@x.com", username="rluser")
    ident = {"identifier": "rl@x.com", "password": "wrongpass"}
    codes = [client.post("/api/v1/auth/login", json=ident).status_code for _ in range(11)]
    assert codes[:10] == [401] * 10   # allowed attempts fail normally
    assert codes[10] == 429            # 11th is locked out
