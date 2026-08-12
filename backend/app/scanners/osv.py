"""OSV-Scanner dependency (SCA) wrapper.

Runs Google's `osv-scanner` over a repository's lockfiles/manifests and reports
known-vulnerable dependencies. This covers **OWASP A06:2021 — Vulnerable and
Outdated Components**, a whole class SAST can't see: the code may be perfect but
a pinned library ships a CVE.

One tool spans every ecosystem the repo uses (pip, npm, Go modules, Maven,
etc.), so it complements the language-specific SAST rather than duplicating it.

Exit codes (osv-scanner): 0 = no vulnerabilities, 1 = vulnerabilities found,
others = operational error. We parse whatever JSON is produced and only fail if
no JSON comes back at all — that way a missing binary or a genuine crash surfaces
as a FAILED scanner result instead of silent emptiness.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.models.finding import Finding, Severity
from app.models.owasp import classify_owasp, extract_cwe_ids
from app.scanners.base import Scanner
from app.utils.subprocess import run_command

# GHSA/OSV severity words → our normalized scale.
_SEVERITY_MAP = {
    "CRITICAL": Severity.CRITICAL,
    "HIGH": Severity.HIGH,
    "MODERATE": Severity.MEDIUM,
    "MEDIUM": Severity.MEDIUM,
    "LOW": Severity.LOW,
}


class OsvScanner(Scanner):
    """Runs osv-scanner and normalizes vulnerable-dependency findings."""

    name = "osv"

    async def _run_scan(self, target: Path) -> list[Finding]:
        cmd = ["osv-scanner", "--format", "json", "--recursive", str(target)]
        result = await run_command(cmd, timeout=self._settings.osv_timeout + 30)

        if result.timed_out:
            raise RuntimeError(result.stderr or "osv-scanner timed out")
        # osv-scanner prints the report to stdout regardless of the (0/1) exit
        # code; a non-JSON stdout means a real failure.
        stdout = (result.stdout or "").strip()
        if not stdout:
            if result.returncode in (0, 1):
                return []
            raise RuntimeError(
                result.stderr.strip() or f"osv-scanner exited with {result.returncode}"
            )
        return self.parse(stdout, target)

    def parse(self, stdout: str, target: Path | None = None) -> list[Finding]:
        """Parse osv-scanner JSON into normalized findings (pure/testable)."""
        data = json.loads(stdout) or {}
        root = target.resolve() if target else None
        findings: list[Finding] = []

        for result in data.get("results", []):
            source_path = (result.get("source") or {}).get("path", "")
            rel = self._relativize(source_path, root)
            for pkg in result.get("packages", []):
                info: dict[str, Any] = pkg.get("package") or {}
                name = info.get("name", "dependency")
                version = info.get("version", "?")
                for vuln in pkg.get("vulnerabilities", []):
                    findings.append(
                        self._build_finding(vuln, name, version, rel)
                    )
        return findings

    def _build_finding(
        self, vuln: dict[str, Any], name: str, version: str, file: str
    ) -> Finding:
        vuln_id = vuln.get("id", "OSV")
        db: dict[str, Any] = vuln.get("database_specific") or {}
        severity = _SEVERITY_MAP.get(
            str(db.get("severity", "")).upper(), Severity.MEDIUM
        )
        cwe_ids = extract_cwe_ids(db.get("cwe_ids"))
        summary = vuln.get("summary") or (vuln.get("details") or "")[:300]

        return Finding(
            scanner=self.name,
            severity=severity,
            file=file,
            line=None,
            title=f"Vulnerable dependency: {name}@{version} ({vuln_id})",
            description=summary or f"{name} {version} is affected by {vuln_id}.",
            remediation=(
                f"Upgrade {name} beyond the affected range to a patched "
                f"version. See https://osv.dev/vulnerability/{vuln_id}."
            ),
            cwe_ids=cwe_ids,
            owasp_category=classify_owasp(cwe_ids, self.name),
            rule_id=vuln_id,
        )

    @staticmethod
    def _relativize(source_path: str, root: Path | None) -> str:
        """Best-effort repo-relative path for the manifest/lockfile."""
        if not source_path:
            return ""
        if root is None:
            return source_path
        try:
            return Path(source_path).resolve().relative_to(root).as_posix()
        except (ValueError, OSError):
            return source_path
