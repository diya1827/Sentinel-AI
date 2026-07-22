"""API-level tests for the scan endpoint (wiring + graceful degradation)."""

import io
import zipfile

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

BASE = "/api/v1/repositories"


def test_scan_missing_repo_returns_404() -> None:
    resp = client.post(f"{BASE}/0123456789abcdef/scan")
    assert resp.status_code == 404


def test_scan_ingested_repo_returns_report() -> None:
    # Ingest a tiny repo first.
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("src/main.py", "print('hi')\n")
    resp = client.post(
        f"{BASE}/upload",
        files={"file": ("repo.zip", buf.getvalue(), "application/zip")},
    )
    repo_id = resp.json()["repository_id"]

    # Scan it. Tools aren't installed in this env, so scanners report FAILED —
    # but the endpoint must still return a well-formed 200 report.
    scan = client.post(f"{BASE}/{repo_id}/scan")
    assert scan.status_code == 200
    body = scan.json()

    assert body["repository_id"] == repo_id
    assert {r["scanner"] for r in body["results"]} == {"semgrep", "gitleaks"}
    assert "critical" in body["severity_counts"]
    assert body["total_findings"] == len(body["findings"])

    client.delete(f"{BASE}/{repo_id}")
