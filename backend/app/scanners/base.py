"""Common scanner contract.

Every tool wrapper subclasses `Scanner` and implements `_run_scan`, returning a
list of normalized `Finding`s. The base class wraps that call with timing and
**uniform error handling**: a missing binary, a timeout, malformed output, or
any other exception becomes a `FAILED` `ScannerResult` rather than propagating.
That guarantee is what lets `ScannerService` run every tool and always return a
report, even when some scanners fail.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from time import perf_counter
from typing import ClassVar

from app.config.settings import Settings
from app.models.finding import Finding
from app.models.scan import ScannerResult, ScanStatus
from app.utils.logging import get_logger
from app.utils.subprocess import CommandNotFoundError

logger = get_logger(__name__)


class Scanner(ABC):
    """Uniform interface for a security scanning tool."""

    name: ClassVar[str]

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def scan(self, target: Path) -> ScannerResult:
        """Run the tool against `target`, never raising.

        Returns a `SUCCESS` result with findings, or a `FAILED` result carrying
        the reason.
        """
        start = perf_counter()
        try:
            findings = await self._run_scan(target)
        except CommandNotFoundError as exc:
            return self._failed(
                f"{self.name} is not installed on this host.", start, exc
            )
        except Exception as exc:  # noqa: BLE001 — deliberately defensive boundary
            return self._failed(f"{type(exc).__name__}: {exc}", start, exc)

        return ScannerResult(
            scanner=self.name,
            status=ScanStatus.SUCCESS,
            findings=findings,
            duration_seconds=round(perf_counter() - start, 3),
        )

    @abstractmethod
    async def _run_scan(self, target: Path) -> list[Finding]:
        """Execute the tool and return normalized findings. May raise."""

    def _failed(
        self, message: str, start: float, exc: Exception | None = None
    ) -> ScannerResult:
        logger.warning("Scanner %s failed: %s", self.name, message, exc_info=exc)
        return ScannerResult(
            scanner=self.name,
            status=ScanStatus.FAILED,
            error=message,
            duration_seconds=round(perf_counter() - start, 3),
        )
