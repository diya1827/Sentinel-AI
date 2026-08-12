"""Security scanner layer.

Responsibility: wrap external security CLIs behind one uniform `Scanner`
interface so the orchestration layer treats every tool identically and new
tools can be added without touching the pipeline.

Each scanner is chosen to cover a distinct OWASP Top 10 (2021) category, so the
suite is defense-in-depth rather than overlapping tools:

Contents:
    base.py     — Scanner protocol + shared result normalization
    semgrep.py  — SAST (code vulnerabilities)        → A01/A03/…
    xss.py      — dedicated XSS ruleset               → A03 Injection
    gitleaks.py — secret scanning                     → A07 Auth Failures
    osv.py      — dependency/SCA (osv-scanner)         → A06 Vulnerable Components
    checkov.py  — IaC misconfiguration (checkov)       → A05 Misconfiguration
"""
