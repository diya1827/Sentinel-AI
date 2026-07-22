"""Gitleaks secret-scanning wrapper.

Runs `gitleaks dir` over the staged files (filesystem mode, not git history) and
writes a JSON report to a temp file, which we then normalize into `Finding`s.

Exit-code convention (Gitleaks): 0 = no leaks, 1 = leaks found, other = error.
Gitleaks findings carry no severity, so leaked secrets are reported as HIGH.

Requires Gitleaks >= 8.18 (for the `dir` subcommand); the backend image pins a
compatible release.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from app.models.finding import Finding, Severity
from app.scanners.base import Scanner
from app.utils.subprocess import run_command

_SECRET_REMEDIATION = (
    "Treat the exposed secret as compromised: rotate/revoke it immediately, "
    "remove it from the codebase and history, and load it from a secrets "
    "manager or environment variable instead."
)


class GitleaksScanner(Scanner):
    """Runs Gitleaks and normalizes its findings."""

    name = "gitleaks"

    async def _run_scan(self, target: Path) -> list[Finding]:
        fd, report_path = tempfile.mkstemp(suffix=".json", prefix="gitleaks-")
        os.close(fd)  # gitleaks writes the file itself; we just need the path
        try:
            cmd = [
                "gitleaks",
                "dir",
                str(target),
                "--report-format",
                "json",
                "--report-path",
                report_path,
                "--no-banner",
                "--exit-code",
                "0",  # don't fail the process merely because leaks were found
            ]
            result = await run_command(
                cmd, timeout=self._settings.gitleaks_timeout + 30
            )

            if result.timed_out:
                raise RuntimeError(result.stderr)
            if result.returncode != 0:
                raise RuntimeError(
                    result.stderr.strip()
                    or f"gitleaks exited with {result.returncode}"
                )

            report = Path(report_path)
            if not report.exists() or report.stat().st_size == 0:
                return []
            return self.parse(report.read_text(encoding="utf-8"))
        finally:
            Path(report_path).unlink(missing_ok=True)

    def parse(self, report_json: str) -> list[Finding]:
        """Parse a Gitleaks JSON report into normalized findings (pure/testable)."""
        data = json.loads(report_json) or []
        findings: list[Finding] = []

        for item in data:
            item: dict[str, Any]
            rule_id = item.get("RuleID") or "secret"
            findings.append(
                Finding(
                    scanner=self.name,
                    severity=Severity.HIGH,
                    file=item.get("File", ""),
                    line=item.get("StartLine"),
                    title=f"Exposed secret: {rule_id}",
                    description=item.get("Description"),
                    remediation=_SECRET_REMEDIATION,
                    rule_id=rule_id,
                )
            )
        return findings
