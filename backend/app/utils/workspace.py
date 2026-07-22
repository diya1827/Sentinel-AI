"""Workspace management for staged repositories.

Every ingested repository lives in its own subdirectory of the scan workspace,
named by an opaque id. This helper is the single place that maps an id → path
(guarding against traversal) and removes directories on cleanup.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4


class Workspace:
    """Owns the on-disk staging area for ingested repositories."""

    def __init__(self, base_dir: str | Path) -> None:
        self._base = Path(base_dir).resolve()
        self._base.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def new_id() -> str:
        """Generate a fresh, opaque repository id."""
        return uuid4().hex

    def path_for(self, repository_id: str) -> Path:
        """Resolve the directory for `repository_id`, rejecting traversal.

        Raises:
            ValueError: If the id resolves outside the workspace root.
        """
        # A valid id is a single path segment; anything else is suspect.
        if not repository_id or "/" in repository_id or "\\" in repository_id or ".." in repository_id:
            raise ValueError(f"Invalid repository id: {repository_id!r}")

        candidate = (self._base / repository_id).resolve()
        if candidate.parent != self._base:
            raise ValueError(f"Invalid repository id: {repository_id!r}")
        return candidate

    def remove(self, repository_id: str) -> bool:
        """Delete a repository's staged files. Returns True if something was removed."""
        target = self.path_for(repository_id)
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
            return True
        return False
