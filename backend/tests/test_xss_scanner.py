"""Tests for the XssScanner: XSS-type tagging and config scoping."""

import json
from pathlib import Path

from app.config.settings import Settings
from app.models.finding import Severity
from app.scanners.xss import XssScanner


def _settings(tmp_path: Path) -> Settings:
    return Settings(scan_workspace_dir=str(tmp_path / "ws"))


def _semgrep_json(check_id: str, xss_type: str | None, severity: str = "ERROR") -> str:
    metadata = {"xss-type": xss_type} if xss_type else {}
    return json.dumps(
        {
            "results": [
                {
                    "check_id": check_id,
                    "path": "src/app.js",
                    "start": {"line": 7},
                    "extra": {
                        "severity": severity,
                        "message": "Tainted data reaches an HTML sink.",
                        "metadata": metadata,
                    },
                }
            ]
        }
    )


def test_xss_scanner_uses_custom_ruleset(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    scanner = XssScanner(settings)
    assert scanner.name == "xss"
    assert scanner._config() == settings.xss_rules_path
    assert scanner._config().endswith("xss.yml")


def test_parse_tags_dom_type_and_prefixes_title(tmp_path: Path) -> None:
    stdout = _semgrep_json("rules.dom-xss-source-to-sink", "dom")
    findings = XssScanner(_settings(tmp_path)).parse(stdout)

    assert len(findings) == 1
    f = findings[0]
    assert f.scanner == "xss"
    assert f.xss_type == "dom"
    assert f.title == "DOM-based XSS: dom-xss-source-to-sink"
    assert f.severity is Severity.HIGH
    assert f.file == "src/app.js"
    assert f.line == 7


def test_parse_tags_reflected_and_stored(tmp_path: Path) -> None:
    scanner = XssScanner(_settings(tmp_path))

    reflected = scanner.parse(
        _semgrep_json("rules.express-xss-request-to-response", "reflected")
    )[0]
    assert reflected.xss_type == "reflected"
    assert reflected.title.startswith("Reflected XSS:")

    stored = scanner.parse(
        _semgrep_json("rules.python-markup-marks-tainted-safe", "stored", "WARNING")
    )[0]
    assert stored.xss_type == "stored"
    assert stored.title.startswith("Stored XSS:")
    assert stored.severity is Severity.MEDIUM


def test_parse_without_xss_metadata_leaves_title_untagged(tmp_path: Path) -> None:
    findings = XssScanner(_settings(tmp_path)).parse(
        _semgrep_json("rules.some-other-rule", None)
    )
    f = findings[0]
    assert f.xss_type is None
    assert f.title == "some-other-rule"
