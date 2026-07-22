"""Tests for the scanning layer: parsing, aggregation, and graceful failure."""

import json
from pathlib import Path

import pytest

from app.config.settings import Settings
from app.models.finding import Finding, Severity
from app.models.scan import ScanStatus
from app.scanners.base import Scanner
from app.scanners.gitleaks import GitleaksScanner
from app.scanners.semgrep import SemgrepScanner
from app.services.scanner_service import ScannerService
from app.utils.subprocess import CommandNotFoundError, run_command


def _settings(tmp_path: Path) -> Settings:
    return Settings(scan_workspace_dir=str(tmp_path / "ws"))


# ── Parsing ──────────────────────────────────────────────────────

def test_semgrep_parse_maps_fields_and_severity(tmp_path: Path) -> None:
    stdout = json.dumps(
        {
            "results": [
                {
                    "check_id": "python.lang.security.audit.dangerous-eval",
                    "path": "app/main.py",
                    "start": {"line": 42},
                    "extra": {
                        "severity": "ERROR",
                        "message": "Detected use of eval().",
                        "metadata": {"references": ["https://owasp.org/eval"]},
                    },
                }
            ]
        }
    )
    findings = SemgrepScanner(_settings(tmp_path)).parse(stdout)
    assert len(findings) == 1
    f = findings[0]
    assert f.scanner == "semgrep"
    assert f.severity is Severity.HIGH
    assert f.file == "app/main.py"
    assert f.line == 42
    assert f.title == "dangerous-eval"
    assert "eval" in (f.description or "")
    assert f.remediation and "owasp" in f.remediation
    assert f.rule_id == "python.lang.security.audit.dangerous-eval"


def test_gitleaks_parse(tmp_path: Path) -> None:
    report = json.dumps(
        [
            {
                "RuleID": "aws-access-token",
                "Description": "AWS Access Token",
                "File": "config/prod.env",
                "StartLine": 3,
            }
        ]
    )
    findings = GitleaksScanner(_settings(tmp_path)).parse(report)
    assert len(findings) == 1
    f = findings[0]
    assert f.scanner == "gitleaks"
    assert f.severity is Severity.HIGH
    assert f.file == "config/prod.env"
    assert f.line == 3
    assert "aws-access-token" in f.title
    assert f.remediation and "rotate" in f.remediation.lower()


def test_gitleaks_parse_empty(tmp_path: Path) -> None:
    assert GitleaksScanner(_settings(tmp_path)).parse("[]") == []


# ── Graceful failure ─────────────────────────────────────────────

class _MissingBinaryScanner(Scanner):
    name = "ghost"

    async def _run_scan(self, target: Path) -> list[Finding]:
        # An executable that certainly does not exist.
        await run_command(["sentinel-nonexistent-binary"], timeout=5)
        return []


class _ExplodingScanner(Scanner):
    name = "boom"

    async def _run_scan(self, target: Path) -> list[Finding]:
        raise RuntimeError("parser blew up")


class _FakeGoodScanner(Scanner):
    name = "good"

    async def _run_scan(self, target: Path) -> list[Finding]:
        return [
            Finding(scanner="good", severity=Severity.MEDIUM, file="a.py", line=1, title="x")
        ]


@pytest.mark.asyncio
async def test_run_command_missing_binary_raises() -> None:
    with pytest.raises(CommandNotFoundError):
        await run_command(["sentinel-nonexistent-binary"], timeout=5)


@pytest.mark.asyncio
async def test_scan_wraps_missing_binary_as_failed(tmp_path: Path) -> None:
    result = await _MissingBinaryScanner(_settings(tmp_path)).scan(tmp_path)
    assert result.status is ScanStatus.FAILED
    assert "not installed" in (result.error or "")
    assert result.findings == []


@pytest.mark.asyncio
async def test_scan_wraps_exception_as_failed(tmp_path: Path) -> None:
    result = await _ExplodingScanner(_settings(tmp_path)).scan(tmp_path)
    assert result.status is ScanStatus.FAILED
    assert "parser blew up" in (result.error or "")


# ── Aggregation ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_service_aggregates_partial_failure(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    repo_dir = Path(settings.scan_workspace_dir) / "deadbeef"
    repo_dir.mkdir(parents=True)

    service = ScannerService(
        settings=settings,
        scanners=[_FakeGoodScanner(settings), _ExplodingScanner(settings)],
    )
    report = await service.scan_repository("deadbeef")

    assert report.total_findings == 1
    assert report.severity_counts["medium"] == 1
    assert report.severity_counts["critical"] == 0
    statuses = {r.scanner: r.status for r in report.results}
    assert statuses["good"] is ScanStatus.SUCCESS
    assert statuses["boom"] is ScanStatus.FAILED


@pytest.mark.asyncio
async def test_service_missing_repo_raises(tmp_path: Path) -> None:
    service = ScannerService(settings=_settings(tmp_path), scanners=[])
    with pytest.raises(FileNotFoundError):
        await service.scan_repository("0123456789abcdef")


@pytest.mark.asyncio
async def test_service_invalid_id_raises(tmp_path: Path) -> None:
    service = ScannerService(settings=_settings(tmp_path), scanners=[])
    with pytest.raises(ValueError):
        await service.scan_repository("../etc")
