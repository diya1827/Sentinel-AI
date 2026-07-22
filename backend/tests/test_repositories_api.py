"""API-level tests for the repository endpoints (transport + validation)."""

import io
import zipfile

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

BASE = "/api/v1/repositories"


def test_github_rejects_invalid_url() -> None:
    resp = client.post(f"{BASE}/github", json={"repo_url": "https://gitlab.com/a/b"})
    assert resp.status_code == 422


def test_upload_rejects_non_zip() -> None:
    resp = client.post(
        f"{BASE}/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 422


def test_upload_ingests_zip() -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("src/main.py", "print('hi')\n")
        zf.writestr("requirements.txt", "fastapi\n")
    buf.seek(0)

    resp = client.post(
        f"{BASE}/upload",
        files={"file": ("repo.zip", buf.getvalue(), "application/zip")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["primary_language"] == "Python"
    assert "pip" in body["package_managers"]

    # And it can be cleaned up.
    assert client.delete(f"{BASE}/{body['repository_id']}").status_code == 204
    assert client.delete(f"{BASE}/{body['repository_id']}").status_code == 404


def test_delete_rejects_bad_id() -> None:
    assert client.delete(f"{BASE}/..%2Fetc").status_code in (400, 404)
