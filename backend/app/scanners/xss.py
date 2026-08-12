"""XssScanner — dedicated Cross-Site Scripting scanner.

Runs Semgrep against Sentinel's custom XSS ruleset (`backend/rules/xss.yml`)
rather than the general-purpose config, and enriches each finding with its XSS
classification (reflected / stored / DOM) read from the rule's `xss-type`
metadata. Everything else — the subprocess invocation, error handling, severity
mapping — is inherited from `SemgrepScanner`.
"""

from __future__ import annotations

from typing import Any

from app.models.finding import Finding
from app.scanners.semgrep import SemgrepScanner

# Rule metadata `xss-type` → human-readable label prefixed onto the finding title.
_XSS_TYPE_LABEL = {
    "reflected": "Reflected XSS",
    "stored": "Stored XSS",
    "dom": "DOM-based XSS",
}


class XssScanner(SemgrepScanner):
    """Semgrep run scoped to the custom XSS ruleset, with type tagging."""

    name = "xss"

    def _config(self) -> str:
        return self._settings.xss_rules_path

    def _build_finding(self, item: dict[str, Any]) -> Finding:
        finding = super()._build_finding(item)
        # `_build_finding` set scanner to the class name via `self.name`, so it
        # is already "xss"; now layer on the XSS classification.
        metadata = (item.get("extra") or {}).get("metadata") or {}
        xss_type = metadata.get("xss-type")
        if xss_type:
            finding.xss_type = xss_type
            label = _XSS_TYPE_LABEL.get(xss_type)
            if label:
                finding.title = f"{label}: {finding.title}"
        return finding
