"""OWASP Top 10 (2021) classification for findings.

Every scanner speaks a different dialect — Semgrep emits CWE/OWASP metadata,
Gitleaks emits nothing, dependency and IaC scanners emit their own taxonomies.
This module gives the whole pipeline one shared security vocabulary: it pulls
CWE ids out of raw scanner metadata and maps a finding to its OWASP Top 10
category, so the report can answer "which OWASP categories showed up, and which
are clean?" regardless of which tool produced a result.

The mapping is intentionally small and standards-based: the OWASP Top 10 2021
category → representative CWE list is public, and we invert it. Where a scanner
has no CWE at all (Gitleaks secrets, SCA, IaC), a per-scanner default category
is used — each tool is chosen to cover a *distinct* OWASP category.
"""

from __future__ import annotations

import re

# ── OWASP Top 10 2021 categories ─────────────────────────────────
# Canonical display labels, keyed by category code.
CATEGORY_NAMES: dict[str, str] = {
    "A01:2021": "Broken Access Control",
    "A02:2021": "Cryptographic Failures",
    "A03:2021": "Injection",
    "A04:2021": "Insecure Design",
    "A05:2021": "Security Misconfiguration",
    "A06:2021": "Vulnerable and Outdated Components",
    "A07:2021": "Identification and Authentication Failures",
    "A08:2021": "Software and Data Integrity Failures",
    "A09:2021": "Security Logging and Monitoring Failures",
    "A10:2021": "Server-Side Request Forgery (SSRF)",
}

# ── CWE → OWASP category ─────────────────────────────────────────
# Keyed by CWE number. Based on the OWASP Top 10 2021 CWE mappings; scoped to
# the CWEs our scanners actually emit plus the well-known web classes.
CWE_TO_OWASP: dict[int, str] = {
    # A01 — Broken Access Control
    22: "A01:2021",   # Path Traversal
    23: "A01:2021",
    35: "A01:2021",
    59: "A01:2021",
    200: "A01:2021",  # Exposure of Sensitive Information
    201: "A01:2021",
    284: "A01:2021",  # Improper Access Control
    285: "A01:2021",  # Improper Authorization
    352: "A01:2021",  # CSRF
    425: "A01:2021",  # Forced Browsing
    639: "A01:2021",  # IDOR
    862: "A01:2021",  # Missing Authorization
    863: "A01:2021",  # Incorrect Authorization
    # A02 — Cryptographic Failures
    259: "A02:2021",  # Hard-coded Password (crypto context)
    261: "A02:2021",
    296: "A02:2021",
    310: "A02:2021",
    311: "A02:2021",  # Missing Encryption
    312: "A02:2021",  # Cleartext Storage
    319: "A02:2021",  # Cleartext Transmission
    321: "A02:2021",  # Hard-coded Crypto Key
    326: "A02:2021",  # Inadequate Encryption Strength
    327: "A02:2021",  # Broken/Risky Crypto Algorithm
    328: "A02:2021",  # Reversible/weak Hash
    330: "A02:2021",  # Insufficiently Random Values
    338: "A02:2021",  # Weak PRNG
    # A03 — Injection
    74: "A03:2021",
    77: "A03:2021",   # Command Injection
    78: "A03:2021",   # OS Command Injection
    79: "A03:2021",   # XSS
    80: "A03:2021",
    89: "A03:2021",   # SQL Injection
    90: "A03:2021",   # LDAP Injection
    91: "A03:2021",   # XML Injection
    94: "A03:2021",   # Code Injection
    95: "A03:2021",   # Eval Injection
    98: "A03:2021",   # PHP file inclusion
    116: "A03:2021",
    643: "A03:2021",  # XPath Injection
    917: "A03:2021",  # Expression Language Injection
    # A04 — Insecure Design
    209: "A04:2021",  # Error message info leak
    256: "A04:2021",
    501: "A04:2021",  # Trust Boundary Violation
    522: "A04:2021",  # Insufficiently Protected Credentials
    602: "A04:2021",
    # A05 — Security Misconfiguration
    16: "A05:2021",
    260: "A05:2021",
    315: "A05:2021",
    520: "A05:2021",
    525: "A05:2021",
    548: "A05:2021",  # Directory listing exposure
    611: "A05:2021",  # XXE
    614: "A05:2021",  # Sensitive cookie without Secure
    732: "A05:2021",  # Incorrect Permission Assignment
    756: "A05:2021",
    776: "A05:2021",
    942: "A05:2021",  # Permissive CORS
    1004: "A05:2021", # Sensitive cookie without HttpOnly
    1032: "A05:2021",
    # A06 — Vulnerable and Outdated Components
    937: "A06:2021",
    1035: "A06:2021",
    1104: "A06:2021",
    # A07 — Identification and Authentication Failures
    255: "A07:2021",
    287: "A07:2021",  # Improper Authentication
    288: "A07:2021",
    290: "A07:2021",
    294: "A07:2021",
    295: "A07:2021",  # Improper Cert Validation
    297: "A07:2021",
    300: "A07:2021",
    306: "A07:2021",  # Missing Authentication
    307: "A07:2021",  # Improper Restriction of Auth Attempts
    346: "A07:2021",
    384: "A07:2021",  # Session Fixation
    521: "A07:2021",  # Weak Password Requirements
    613: "A07:2021",  # Insufficient Session Expiration
    620: "A07:2021",
    798: "A07:2021",  # Use of Hard-coded Credentials (secrets)
    # A08 — Software and Data Integrity Failures
    345: "A08:2021",
    353: "A08:2021",
    426: "A08:2021",
    494: "A08:2021",  # Download of Code Without Integrity Check
    502: "A08:2021",  # Deserialization of Untrusted Data
    565: "A08:2021",
    784: "A08:2021",
    829: "A08:2021",  # Inclusion of Functionality from Untrusted Sphere
    915: "A08:2021",
    # A09 — Security Logging and Monitoring Failures
    117: "A09:2021",  # Improper Output Neutralization for Logs
    223: "A09:2021",
    532: "A09:2021",  # Insertion of Sensitive Info into Log
    778: "A09:2021",  # Insufficient Logging
    # A10 — Server-Side Request Forgery
    918: "A10:2021",  # SSRF
}

# ── Per-scanner default category ─────────────────────────────────
# Used when a scanner emits no CWE. Each scanner is chosen to map cleanly to a
# single OWASP category, so this default is meaningful rather than a guess.
SCANNER_DEFAULT_OWASP: dict[str, str] = {
    "gitleaks": "A07:2021",  # Hard-coded credentials / secrets (CWE-798)
    "osv": "A06:2021",       # Vulnerable & outdated components (SCA)
    "checkov": "A05:2021",   # Security misconfiguration (IaC)
}

_CWE_RE = re.compile(r"CWE[-_ ]?(\d+)", re.IGNORECASE)
_OWASP_RE = re.compile(r"A(\d{1,2}):?\s*(20\d{2})", re.IGNORECASE)


def label(code: str) -> str | None:
    """Return the canonical 'A03:2021 - Injection' label for a category code."""
    name = CATEGORY_NAMES.get(code)
    return f"{code} - {name}" if name else None


def extract_cwe_ids(raw: object) -> list[str]:
    """Pull normalized 'CWE-89' ids out of raw scanner metadata.

    Accepts a string, a list of strings, or anything stringifiable — scanners
    emit CWE in wildly different shapes (bare id, 'CWE-79: XSS', a list, etc.).
    Order-preserving and de-duplicated.
    """
    if raw is None:
        return []
    items = raw if isinstance(raw, (list, tuple)) else [raw]
    seen: dict[str, None] = {}
    for item in items:
        for match in _CWE_RE.finditer(str(item)):
            seen.setdefault(f"CWE-{int(match.group(1))}", None)
    return list(seen)


def normalize_owasp(raw: object) -> str | None:
    """Turn a scanner's raw OWASP metadata into a canonical category label.

    Handles 'A03:2021 - Injection', 'A3:2021', a list of such strings, etc.
    Returns None if no recognizable category is present.
    """
    if raw is None:
        return None
    items = raw if isinstance(raw, (list, tuple)) else [raw]
    for item in items:
        match = _OWASP_RE.search(str(item))
        if match:
            code = f"A{int(match.group(1)):02d}:{match.group(2)}"
            if code in CATEGORY_NAMES:
                return label(code)
    return None


def classify_owasp(cwe_ids: list[str], scanner: str | None = None) -> str | None:
    """Map CWE ids (falling back to a scanner default) to an OWASP category.

    Returns the canonical label, or None if nothing matches.
    """
    for cwe in cwe_ids:
        match = _CWE_RE.search(cwe)
        if match:
            code = CWE_TO_OWASP.get(int(match.group(1)))
            if code:
                return label(code)
    if scanner and scanner in SCANNER_DEFAULT_OWASP:
        return label(SCANNER_DEFAULT_OWASP[scanner])
    return None
