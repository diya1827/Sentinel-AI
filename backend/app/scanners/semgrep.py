"""Semgrep static-analysis wrapper.

Runs `semgrep scan --json` and normalizes each result into a `Finding`.

Exit-code convention (Semgrep): 0 = clean, 1 = findings present, >=2 = error.
So 0 and 1 are both "ran successfully"; anything higher is a real failure.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.models.finding import Finding, Severity
from app.models.owasp import classify_owasp, extract_cwe_ids, normalize_owasp
from app.scanners.base import Scanner
from app.utils.subprocess import run_command

# Semgrep severities → our normalized scale.
_SEVERITY_MAP = {
    "ERROR": Severity.HIGH,
    "WARNING": Severity.MEDIUM,
    "INFO": Severity.LOW,
}


class SemgrepScanner(Scanner):
    """Runs Semgrep and normalizes its findings."""

    name = "semgrep"

    def _config(self) -> str:
        """The `--config` value to run. Overridable by subclasses."""
        return self._settings.semgrep_config

    async def _run_scan(self, target: Path) -> list[Finding]:
        cmd = [
            "semgrep",
            "scan",
            "--json",
            "--quiet",
            "--metrics=off",
            "--config",
            self._config(),
            "--timeout",
            str(self._settings.semgrep_timeout),
        ]
        # Optional resource caps for small hosts (e.g. Render's 512MB free tier).
        if self._settings.semgrep_max_memory > 0:
            cmd += ["--max-memory", str(self._settings.semgrep_max_memory)]
        if self._settings.semgrep_jobs > 0:
            cmd += ["--jobs", str(self._settings.semgrep_jobs)]
        cmd.append(str(target))
        # Give the wrapper a little more wall-clock than Semgrep's own per-rule
        # timeout so we capture its output rather than killing it ourselves.
        result = await run_command(cmd, timeout=self._settings.semgrep_timeout + 30)

        if result.timed_out:
            raise RuntimeError(result.stderr)
        if result.returncode not in (0, 1):
            raise RuntimeError(
                result.stderr.strip() or f"semgrep exited with {result.returncode}"
            )

        return self.parse(result.stdout)

    def parse(self, stdout: str) -> list[Finding]:
        """Parse Semgrep JSON stdout into normalized findings (pure/testable)."""
        data = json.loads(stdout)
        return [self._build_finding(item) for item in data.get("results", [])]

    def _build_finding(self, item: dict[str, Any]) -> Finding:
        """Map one Semgrep result to a Finding. Overridable for enrichment."""
        extra: dict[str, Any] = item.get("extra") or {}
        start: dict[str, Any] = item.get("start") or {}
        check_id = item.get("check_id") or "semgrep-finding"

        metadata: dict[str, Any] = extra.get("metadata") or {}
        cwe_ids = extract_cwe_ids(metadata.get("cwe"))
        owasp = normalize_owasp(metadata.get("owasp")) or classify_owasp(
            cwe_ids, self.name
        )

        return Finding(
            scanner=self.name,
            severity=_SEVERITY_MAP.get(
                str(extra.get("severity", "")).upper(), Severity.LOW
            ),
            file=item.get("path", ""),
            line=start.get("line"),
            title=check_id.split(".")[-1],
            description=extra.get("message"),
            remediation=self._remediation(extra),
            cwe_ids=cwe_ids,
            owasp_category=owasp,
            rule_id=check_id,
        )

    @staticmethod
    def _remediation(extra: dict[str, Any]) -> str | None:
        """Prefer Semgrep's autofix, then rule references, else nothing."""
        fix = extra.get("fix")
        if fix:
            return f"Suggested fix: {fix}"
        metadata = extra.get("metadata") or {}
        references = metadata.get("references") or []
        if references:
            return "See: " + ", ".join(references[:3])
        return None
