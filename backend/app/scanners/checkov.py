"""Checkov infrastructure-as-code (IaC) misconfiguration wrapper.

Runs Bridgecrew's `checkov` over a repository's Terraform, Dockerfiles, K8s
manifests, CloudFormation, etc., and reports insecure configuration. This covers
**OWASP A05:2021 — Security Misconfiguration**: an open S3 bucket, a security
group open to 0.0.0.0/0, a container running as root — none of which SAST or a
dependency scan would ever surface.

Exit codes (checkov): 0 = all checks passed, 1 = failed checks present, others =
operational error. Both 0 and 1 are successful runs; we parse the JSON either
way and only fail when no JSON is produced.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.models.finding import Finding, Severity
from app.models.owasp import classify_owasp
from app.scanners.base import Scanner
from app.utils.subprocess import run_command

# Checkov severities (when present; the community edition often omits them) →
# our normalized scale.
_SEVERITY_MAP = {
    "CRITICAL": Severity.CRITICAL,
    "HIGH": Severity.HIGH,
    "MEDIUM": Severity.MEDIUM,
    "MODERATE": Severity.MEDIUM,
    "LOW": Severity.LOW,
    "INFO": Severity.INFO,
}


class CheckovScanner(Scanner):
    """Runs checkov and normalizes IaC misconfiguration findings."""

    name = "checkov"

    async def _run_scan(self, target: Path) -> list[Finding]:
        cmd = [
            "checkov",
            "--directory",
            str(target),
            "--output",
            "json",
            "--compact",
            "--quiet",
        ]
        result = await run_command(cmd, timeout=self._settings.checkov_timeout + 30)

        if result.timed_out:
            raise RuntimeError(result.stderr or "checkov timed out")
        stdout = (result.stdout or "").strip()
        if not stdout:
            if result.returncode in (0, 1):
                return []
            raise RuntimeError(
                result.stderr.strip() or f"checkov exited with {result.returncode}"
            )
        return self.parse(stdout, target)

    def parse(self, stdout: str, target: Path | None = None) -> list[Finding]:
        """Parse checkov JSON into normalized findings (pure/testable).

        Checkov emits a single object for one framework, or a list of objects
        when several frameworks (Terraform, Dockerfile, ...) are detected.
        """
        data = json.loads(stdout)
        reports = data if isinstance(data, list) else [data]
        findings: list[Finding] = []

        for report in reports:
            results = (report or {}).get("results") or {}
            for check in results.get("failed_checks", []):
                findings.append(self._build_finding(check))
        return findings

    def _build_finding(self, check: dict[str, Any]) -> Finding:
        check_id = check.get("check_id", "CKV")
        check_name = check.get("check_name", "IaC misconfiguration")
        line_range = check.get("file_line_range") or []
        line = line_range[0] if line_range else None
        severity = _SEVERITY_MAP.get(
            str(check.get("severity") or "").upper(), Severity.MEDIUM
        )
        resource = check.get("resource")
        guideline = check.get("guideline")

        return Finding(
            scanner=self.name,
            severity=severity,
            file=str(check.get("file_path", "")).lstrip("/"),
            line=line,
            title=f"{check_id}: {check_name}",
            description=(
                f"Misconfiguration in {resource}." if resource else check_name
            ),
            remediation=(
                f"Review and harden this resource. See {guideline}."
                if guideline
                else "Harden this resource per the check's recommendation."
            ),
            owasp_category=classify_owasp([], self.name),
            rule_id=check_id,
        )
