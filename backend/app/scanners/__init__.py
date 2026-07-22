"""Security scanner layer.

Responsibility: wrap external security CLIs behind one uniform `Scanner`
interface so the orchestration layer treats every tool identically and new
tools can be added without touching the pipeline.

Contents:
    base.py     — Scanner protocol + shared result normalization
    semgrep.py  — Semgrep static-analysis wrapper
    gitleaks.py — Gitleaks secret-scanning wrapper
"""
