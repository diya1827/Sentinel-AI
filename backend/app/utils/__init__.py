"""Cross-cutting utilities (logging, subprocess helpers, workspace mgmt).

Responsibility: small, dependency-free helpers used across layers. Must not
import from `api`, `services`, or `agents` to avoid circular dependencies.
"""
