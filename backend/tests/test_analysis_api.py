"""API-level tests for the /analyze endpoint (services faked via overrides)."""

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_agent_service,
    get_repository_service,
    get_scanner_service,
)
from app.agents.provider import LLMResponse
from app.main import app
from app.models.finding import Finding, Severity
from app.models.repository import NodeType, RepositoryMetadata, SourceType, TreeNode
from app.models.scan import ScanReport
from app.services.agent_service import AgentService
from tests.test_agent import VALID_REPORT_JSON, ScriptedProvider

BASE = "/api/v1/repositories"


def _metadata() -> RepositoryMetadata:
    return RepositoryMetadata(
        repository_id="abc123",
        source=SourceType.UPLOAD,
        primary_language="Python",
        file_count=1,
        total_size_bytes=1,
        tree=TreeNode(name="root", path=".", type=NodeType.DIRECTORY, children=[]),
    )


class _FakeRepos:
    def __init__(self, missing: bool = False) -> None:
        self._missing = missing

    async def describe(self, repository_id: str) -> RepositoryMetadata:
        if self._missing:
            raise FileNotFoundError(repository_id)
        return _metadata()


class _FakeScanners:
    async def scan_repository(self, repository_id: str) -> ScanReport:
        finding = Finding(
            scanner="gitleaks", severity=Severity.HIGH, file="app/config.py", title="secret"
        )
        return ScanReport(
            repository_id=repository_id,
            findings=[finding],
            total_findings=1,
            severity_counts={},
        )


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_analyze_returns_agent_report() -> None:
    provider = ScriptedProvider([LLMResponse(content=VALID_REPORT_JSON)])
    app.dependency_overrides[get_repository_service] = lambda: _FakeRepos()
    app.dependency_overrides[get_scanner_service] = lambda: _FakeScanners()
    app.dependency_overrides[get_agent_service] = lambda: AgentService(provider=provider)

    client = TestClient(app)
    resp = client.post(f"{BASE}/abc123/analyze")

    assert resp.status_code == 200
    body = resp.json()
    assert body["overall_risk"] == "high"
    assert body["repository_id"] == "abc123"
    assert body["prioritized_findings"][0]["category"] == "Secret Exposure"


def test_analyze_missing_repo_returns_404() -> None:
    app.dependency_overrides[get_repository_service] = lambda: _FakeRepos(missing=True)
    app.dependency_overrides[get_scanner_service] = lambda: _FakeScanners()

    client = TestClient(app)
    assert client.post(f"{BASE}/abc123/analyze").status_code == 404
