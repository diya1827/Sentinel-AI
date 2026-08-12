"""ScannerService — run every scanner against a staged repository.

Orchestrates the scanning use-case: resolve the repository's staged path, run
all registered scanners **concurrently**, and merge their outputs into one
`ScanReport`. Because each `Scanner.scan` handles its own errors, one tool
failing (or being uninstalled) never sinks the others — the report simply
records that scanner as `FAILED`.

No AI here — this layer is pure static analysis + secret scanning.
"""

from __future__ import annotations

import asyncio
from collections import Counter

from app.config.settings import Settings, get_settings
from app.models.finding import Severity
from app.models.scan import ScannerResult, ScanReport
from app.scanners.base import Scanner
from app.scanners.checkov import CheckovScanner
from app.scanners.gitleaks import GitleaksScanner
from app.scanners.osv import OsvScanner
from app.scanners.semgrep import SemgrepScanner
from app.scanners.xss import XssScanner
from app.utils.logging import get_logger
from app.utils.workspace import Workspace

# Shown in the OWASP-coverage summary for findings we couldn't map to a category.
_UNCLASSIFIED = "Unclassified"

logger = get_logger(__name__)


class ScannerService:
    """Runs the registered scanners over an ingested repository."""

    def __init__(
        self,
        settings: Settings | None = None,
        scanners: list[Scanner] | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._workspace = Workspace(self._settings.scan_workspace_dir)
        # Default registry; injectable for tests / future tools.
        self._scanners = (
            scanners
            if scanners is not None
            else [
                SemgrepScanner(self._settings),   # SAST → A01/A03/…
                XssScanner(self._settings),        # XSS → A03
                GitleaksScanner(self._settings),   # secrets → A07
                OsvScanner(self._settings),        # SCA → A06
                CheckovScanner(self._settings),    # IaC misconfig → A05
            ]
        )

    async def scan_repository(self, repository_id: str) -> ScanReport:
        """Scan a previously ingested repository.

        Raises:
            ValueError: If `repository_id` is not a valid workspace id.
            FileNotFoundError: If no repository is staged under that id.
        """
        target = self._workspace.path_for(repository_id)  # validates the id
        if not target.exists():
            raise FileNotFoundError(repository_id)

        logger.info(
            "Scanning %s with: %s",
            repository_id,
            ", ".join(s.name for s in self._scanners),
        )
        # scan() never raises, so gather always yields one result per scanner.
        # On memory-constrained hosts a semaphore caps how many scanner
        # subprocesses run at once (each — Semgrep especially — is RAM-hungry).
        limit = self._settings.scanner_concurrency
        if limit and limit > 0:
            sem = asyncio.Semaphore(limit)

            async def _run(scanner: Scanner) -> ScannerResult:
                async with sem:
                    return await scanner.scan(target)

            results = await asyncio.gather(*(_run(s) for s in self._scanners))
        else:
            results = await asyncio.gather(*(s.scan(target) for s in self._scanners))
        return self._build_report(repository_id, list(results))

    @staticmethod
    def _build_report(
        repository_id: str, results: list[ScannerResult]
    ) -> ScanReport:
        merged = [finding for result in results for finding in result.findings]
        counts: Counter[str] = Counter(f.severity.value for f in merged)
        # Always emit every severity key (0-filled) for a stable frontend shape.
        severity_counts = {sev.value: counts.get(sev.value, 0) for sev in Severity}

        # OWASP Top 10 coverage: how many findings landed in each category.
        owasp_counts: Counter[str] = Counter(
            f.owasp_category or _UNCLASSIFIED for f in merged
        )

        return ScanReport(
            repository_id=repository_id,
            results=results,
            findings=merged,
            total_findings=len(merged),
            severity_counts=severity_counts,
            owasp_counts=dict(sorted(owasp_counts.items())),
        )
