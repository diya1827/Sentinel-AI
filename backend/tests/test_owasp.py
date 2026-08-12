"""Tests for OWASP/CWE classification and the SCA/IaC scanner parsers."""

import json
from pathlib import Path

from app.config.settings import Settings
from app.models.finding import Severity
from app.models.owasp import (
    classify_owasp,
    extract_cwe_ids,
    normalize_owasp,
)
from app.scanners.checkov import CheckovScanner
from app.scanners.gitleaks import GitleaksScanner
from app.scanners.osv import OsvScanner
from app.scanners.semgrep import SemgrepScanner


def _settings(tmp_path: Path) -> Settings:
    return Settings(scan_workspace_dir=str(tmp_path / "ws"))


# ── OWASP mapping helpers ────────────────────────────────────────

def test_extract_cwe_ids_handles_strings_and_lists() -> None:
    assert extract_cwe_ids("CWE-89: SQL Injection") == ["CWE-89"]
    assert extract_cwe_ids(["CWE-79", "CWE-89: SQLi"]) == ["CWE-79", "CWE-89"]
    assert extract_cwe_ids(None) == []
    # De-duplicates, order-preserving.
    assert extract_cwe_ids(["CWE-89", "cwe_89"]) == ["CWE-89"]


def test_normalize_owasp_from_metadata() -> None:
    assert normalize_owasp(["A03:2021 - Injection"]) == "A03:2021 - Injection"
    assert normalize_owasp("A3:2021") == "A03:2021 - Injection"
    assert normalize_owasp("not a category") is None


def test_classify_owasp_from_cwe_then_scanner_default() -> None:
    assert classify_owasp(["CWE-89"]) == "A03:2021 - Injection"
    assert classify_owasp(["CWE-798"]) == (
        "A07:2021 - Identification and Authentication Failures"
    )
    # No CWE → scanner default.
    assert classify_owasp([], "osv") == "A06:2021 - Vulnerable and Outdated Components"
    assert classify_owasp([], "checkov") == "A05:2021 - Security Misconfiguration"
    # Unknown CWE, no scanner → None.
    assert classify_owasp(["CWE-999999"]) is None


# ── Scanner tagging ──────────────────────────────────────────────

def test_semgrep_tags_owasp_and_cwe_from_metadata(tmp_path: Path) -> None:
    stdout = json.dumps(
        {
            "results": [
                {
                    "check_id": "python.lang.security.audit.sqli",
                    "path": "app/db.py",
                    "start": {"line": 10},
                    "extra": {
                        "severity": "ERROR",
                        "message": "SQL injection.",
                        "metadata": {
                            "cwe": ["CWE-89: SQL Injection"],
                            "owasp": ["A03:2021 - Injection"],
                        },
                    },
                }
            ]
        }
    )
    f = SemgrepScanner(_settings(tmp_path)).parse(stdout)[0]
    assert f.cwe_ids == ["CWE-89"]
    assert f.owasp_category == "A03:2021 - Injection"


def test_gitleaks_tags_secret_as_a07(tmp_path: Path) -> None:
    report = json.dumps(
        [{"RuleID": "aws-token", "File": "prod.env", "StartLine": 1}]
    )
    f = GitleaksScanner(_settings(tmp_path)).parse(report)[0]
    assert f.cwe_ids == ["CWE-798"]
    assert f.owasp_category.startswith("A07:2021")


# ── SCA / IaC parsers ────────────────────────────────────────────

def test_osv_parse_maps_dependency_vuln(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root).mkdir()
    stdout = json.dumps(
        {
            "results": [
                {
                    "source": {"path": str(root / "requirements.txt")},
                    "packages": [
                        {
                            "package": {"name": "flask", "version": "0.5"},
                            "vulnerabilities": [
                                {
                                    "id": "GHSA-xxxx",
                                    "summary": "Flask RCE",
                                    "database_specific": {
                                        "severity": "HIGH",
                                        "cwe_ids": ["CWE-94"],
                                    },
                                }
                            ],
                        }
                    ],
                }
            ]
        }
    )
    f = OsvScanner(_settings(tmp_path)).parse(stdout, root)[0]
    assert f.scanner == "osv"
    assert f.severity is Severity.HIGH
    assert f.file == "requirements.txt"
    assert "flask@0.5" in f.title
    assert f.owasp_category == "A03:2021 - Injection"  # from CWE-94


def test_osv_parse_defaults_to_a06_without_cwe(tmp_path: Path) -> None:
    stdout = json.dumps(
        {
            "results": [
                {
                    "source": {"path": "go.mod"},
                    "packages": [
                        {
                            "package": {"name": "lib", "version": "1.0"},
                            "vulnerabilities": [{"id": "OSV-1"}],
                        }
                    ],
                }
            ]
        }
    )
    f = OsvScanner(_settings(tmp_path)).parse(stdout)[0]
    assert f.severity is Severity.MEDIUM
    assert f.owasp_category.startswith("A06:2021")


def test_checkov_parse_maps_failed_check(tmp_path: Path) -> None:
    stdout = json.dumps(
        {
            "results": {
                "failed_checks": [
                    {
                        "check_id": "CKV_AWS_20",
                        "check_name": "S3 bucket is public",
                        "file_path": "/main.tf",
                        "file_line_range": [12, 18],
                        "resource": "aws_s3_bucket.data",
                    }
                ]
            }
        }
    )
    f = CheckovScanner(_settings(tmp_path)).parse(stdout)[0]
    assert f.scanner == "checkov"
    assert f.file == "main.tf"
    assert f.line == 12
    assert "CKV_AWS_20" in f.title
    assert f.owasp_category.startswith("A05:2021")


def test_checkov_parse_handles_multi_framework_list(tmp_path: Path) -> None:
    stdout = json.dumps(
        [
            {"results": {"failed_checks": [
                {"check_id": "CKV_DOCKER_2", "check_name": "no healthcheck",
                 "file_path": "Dockerfile", "file_line_range": [1, 1]}
            ]}},
            {"results": {"failed_checks": []}},
        ]
    )
    findings = CheckovScanner(_settings(tmp_path)).parse(stdout)
    assert len(findings) == 1
    assert findings[0].rule_id == "CKV_DOCKER_2"
