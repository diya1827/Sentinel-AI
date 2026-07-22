"""RepositoryService — ingest a codebase and describe it.

Coordinates the ingestion use-case:

    ZIP upload  ─┐
                 ├─▶ stage into workspace ─▶ walk tree ─▶ detect language +
    GitHub URL ─┘                                          package managers
                                                           ─▶ RepositoryMetadata

The service owns the workspace lifecycle: on any failure mid-ingestion the
partially-staged directory is removed so nothing leaks. Successful ingestions
persist under their `repository_id` until explicitly cleaned up (so later
scanning stages can reuse them).

CPU/IO-bound steps (zip extraction, tree walking) are dispatched to a thread
pool so the event loop stays responsive.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.concurrency import run_in_threadpool

from app.config.settings import Settings, get_settings
from app.models.repository import RepositoryMetadata, SourceType
from app.services.detection import detect_languages, detect_package_managers
from app.utils.archive import extract_zip
from app.utils.filetree import build_tree
from app.utils.git import clone_repository, normalize_github_url
from app.utils.logging import get_logger
from app.utils.workspace import Workspace

logger = get_logger(__name__)


class RepositoryService:
    """Ingests repositories from ZIP uploads or public GitHub URLs."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._workspace = Workspace(self._settings.scan_workspace_dir)

    # ── Public API ───────────────────────────────────────────────

    async def ingest_from_github(self, repo_url: str) -> RepositoryMetadata:
        """Clone a public GitHub repo and analyze it.

        Raises:
            InvalidRepoUrlError: If `repo_url` is malformed or not allow-listed.
            GitCloneError: If the clone fails or times out.
        """
        url = normalize_github_url(repo_url, self._settings.allowed_git_hosts_list)
        repository_id = Workspace.new_id()
        dest = self._workspace.path_for(repository_id)

        logger.info("Cloning %s into %s", url, repository_id)
        try:
            await clone_repository(
                url,
                dest,
                depth=self._settings.git_clone_depth,
                timeout=self._settings.git_clone_timeout,
            )
            return await run_in_threadpool(
                self._analyze, dest, repository_id, SourceType.GITHUB
            )
        except Exception:
            self._workspace.remove(repository_id)
            raise

    async def ingest_from_zip(self, zip_path: Path) -> RepositoryMetadata:
        """Extract an already-spooled ZIP file and analyze it.

        The caller is responsible for the lifetime of `zip_path` itself; this
        method only owns the extracted workspace directory.

        Raises:
            ArchiveError: If the archive is invalid, unsafe, or over limits.
        """
        repository_id = Workspace.new_id()
        dest = self._workspace.path_for(repository_id)

        logger.info("Extracting upload into %s", repository_id)
        try:
            await run_in_threadpool(
                extract_zip,
                zip_path,
                dest,
                max_files=self._settings.max_archive_files,
                max_total_size=self._settings.max_archive_total_size_mb * 1024 * 1024,
            )
            return await run_in_threadpool(
                self._analyze, dest, repository_id, SourceType.UPLOAD
            )
        except Exception:
            self._workspace.remove(repository_id)
            raise

    async def describe(self, repository_id: str) -> RepositoryMetadata:
        """Re-analyze an already-staged repository (tree, languages, managers).

        Used by later stages (e.g. the AI agent) that need the repository
        structure without re-ingesting it.

        Raises:
            ValueError: If `repository_id` is invalid.
            FileNotFoundError: If nothing is staged under that id.
        """
        target = self._workspace.path_for(repository_id)
        if not target.exists():
            raise FileNotFoundError(repository_id)
        # Infer the original source from whether a git checkout is present.
        source = SourceType.GITHUB if (target / ".git").exists() else SourceType.UPLOAD
        return await run_in_threadpool(self._analyze, target, repository_id, source)

    def cleanup(self, repository_id: str) -> bool:
        """Remove a staged repository. Returns True if it existed.

        Raises:
            ValueError: If `repository_id` is not a valid workspace id.
        """
        logger.info("Cleaning up repository %s", repository_id)
        return self._workspace.remove(repository_id)

    # ── Internals ────────────────────────────────────────────────

    def _analyze(
        self, repo_dir: Path, repository_id: str, source: SourceType
    ) -> RepositoryMetadata:
        """Synchronous analysis: walk the tree and run detectors."""
        walk = build_tree(repo_dir, max_files=self._settings.max_tree_files)
        primary_language, languages = detect_languages(walk.files)
        package_managers = detect_package_managers(walk.files)

        return RepositoryMetadata(
            repository_id=repository_id,
            source=source,
            primary_language=primary_language,
            languages=languages,
            package_managers=package_managers,
            file_count=walk.file_count,
            total_size_bytes=walk.total_size,
            truncated=walk.truncated,
            tree=walk.tree,
        )
