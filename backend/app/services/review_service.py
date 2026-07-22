"""ReviewService — orchestrates an end-to-end security review.

SCAFFOLD: signatures and flow documented; implementation deferred.

Flow (to implement):
    1. Stage target code into the scan workspace.
    2. Run each registered scanner (Semgrep, Gitleaks) concurrently.
    3. Normalize raw findings into the shared `Finding` model.
    4. Hand findings to the triage agent for dedup / false-positive removal
       / exploitability scoring.
    5. Ask the remediation agent to explain and propose fixes.
    6. Assemble and return a `ReviewReport`.
"""

from __future__ import annotations


class ReviewService:
    """Coordinates scanners + agents to produce a review report."""

    def __init__(self) -> None:
        # TODO: inject scanner registry + agent orchestrator
        ...

    async def run_review(self, *args, **kwargs):  # noqa: ANN002, ANN003
        """Execute a full review. To be implemented."""
        raise NotImplementedError
