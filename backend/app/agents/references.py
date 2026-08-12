"""Curated help links for a finding — generated server-side, never by the LLM.

Letting the model emit URLs risks hallucinated/404 links. Instead we map a
finding's category (and OWASP Top 10 code) to well-known, stable references: the
relevant OWASP Cheat Sheet and the OWASP Top 10 category page. This keeps every
"how to fix" link real.
"""

from __future__ import annotations

import re

from app.models.agent import Reference

# (keywords, title, url) — first match wins. Order specific → general.
_CHEATSHEETS: list[tuple[tuple[str, ...], str, str]] = [
    (("xss", "cross-site scripting", "cross site scripting"),
     "OWASP: XSS Prevention",
     "https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html"),
    (("sql injection", "sqli"),
     "OWASP: SQL Injection Prevention",
     "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html"),
    (("command injection", "os command", "rce", "code injection"),
     "OWASP: Command Injection Defense",
     "https://cheatsheetseries.owasp.org/cheatsheets/OS_Command_Injection_Defense_Cheat_Sheet.html"),
    (("ssrf", "server-side request"),
     "OWASP: SSRF Prevention",
     "https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html"),
    (("secret", "credential", "api key", "hardcoded", "token", "password expos"),
     "OWASP: Secrets Management",
     "https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html"),
    (("path traversal", "directory traversal", "lfi"),
     "OWASP: Path Traversal",
     "https://owasp.org/www-community/attacks/Path_Traversal"),
    (("deserial",),
     "OWASP: Deserialization",
     "https://cheatsheetseries.owasp.org/cheatsheets/Deserialization_Cheat_Sheet.html"),
    (("crypto", "encryption", "hashing", "weak hash", "md5", "sha1"),
     "OWASP: Cryptographic Storage",
     "https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html"),
    (("csrf", "cross-site request"),
     "OWASP: CSRF Prevention",
     "https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html"),
    (("auth", "session", "login", "jwt"),
     "OWASP: Authentication",
     "https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html"),
    (("access control", "authorization", "idor"),
     "OWASP: Authorization",
     "https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html"),
    (("dependency", "outdated", "vulnerable component", "cve", "sca"),
     "OWASP: Vulnerable Dependency Management",
     "https://cheatsheetseries.owasp.org/cheatsheets/Vulnerable_Dependency_Management_Cheat_Sheet.html"),
    (("xxe", "xml external"),
     "OWASP: XXE Prevention",
     "https://cheatsheetseries.owasp.org/cheatsheets/XML_External_Entity_Prevention_Cheat_Sheet.html"),
    (("upload",),
     "OWASP: File Upload",
     "https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html"),
    (("docker", "container", "kubernetes", "k8s", "misconfig", "terraform", "iac"),
     "OWASP: Infrastructure Security",
     "https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html"),
    (("input validation", "injection"),
     "OWASP: Input Validation",
     "https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html"),
]

# OWASP Top 10 2021 code → (label, page url).
_OWASP_PAGES: dict[str, tuple[str, str]] = {
    "A01": ("Broken Access Control", "https://owasp.org/Top10/A01_2021-Broken_Access_Control/"),
    "A02": ("Cryptographic Failures", "https://owasp.org/Top10/A02_2021-Cryptographic_Failures/"),
    "A03": ("Injection", "https://owasp.org/Top10/A03_2021-Injection/"),
    "A04": ("Insecure Design", "https://owasp.org/Top10/A04_2021-Insecure_Design/"),
    "A05": ("Security Misconfiguration", "https://owasp.org/Top10/A05_2021-Security_Misconfiguration/"),
    "A06": ("Vulnerable & Outdated Components", "https://owasp.org/Top10/A06_2021-Vulnerable_and_Outdated_Components/"),
    "A07": ("Identification & Authentication Failures", "https://owasp.org/Top10/A07_2021-Identification_and_Authentication_Failures/"),
    "A08": ("Software & Data Integrity Failures", "https://owasp.org/Top10/A08_2021-Software_and_Data_Integrity_Failures/"),
    "A09": ("Security Logging & Monitoring Failures", "https://owasp.org/Top10/A09_2021-Security_Logging_and_Monitoring_Failures/"),
    "A10": ("Server-Side Request Forgery", "https://owasp.org/Top10/A10_2021-Server-Side_Request_Forgery_%28SSRF%29/"),
}

_OWASP_FALLBACK = Reference(title="OWASP Top 10", url="https://owasp.org/www-project-top-ten/")


def curate_references(category: str, owasp_category: str | None) -> list[Reference]:
    """Return up to 3 real, relevant help links for a finding."""
    text = f"{category} {owasp_category or ''}".lower()
    refs: list[Reference] = []
    seen: set[str] = set()

    def add(title: str, url: str) -> None:
        if url not in seen:
            seen.add(url)
            refs.append(Reference(title=title, url=url))

    for keywords, title, url in _CHEATSHEETS:
        if any(k in text for k in keywords):
            add(title, url)
            break  # one best-matched cheat sheet is enough

    match = re.search(r"a(\d{2})", (owasp_category or "").lower())
    if match:
        page = _OWASP_PAGES.get(f"A{match.group(1)}")
        if page:
            add(f"OWASP {page[0]}", page[1])

    if not refs:
        add(_OWASP_FALLBACK.title, _OWASP_FALLBACK.url)
    return refs[:3]
