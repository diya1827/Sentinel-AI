"""Build a repository file tree in a single directory walk.

Produces both the nested `TreeNode` structure (for the API/UI) and a flat list
of `(relative_path, size)` file entries (for language/package detection), so
callers never walk the filesystem twice.

Noise directories (VCS metadata, dependency caches, build output) are skipped —
they bloat the tree and aren't meaningful to a security review. Symlinks are
skipped entirely to avoid escaping the workspace or infinite loops.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from app.models.repository import NodeType, TreeNode

# Directories that add noise/size without review value.
IGNORED_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".next",
        "dist",
        "build",
        ".gradle",
        "target",
        ".idea",
        ".vscode",
    }
)


@dataclass
class TreeBuildResult:
    """Everything a single walk yields."""

    tree: TreeNode
    files: list[tuple[str, int]] = field(default_factory=list)  # (relpath, size)
    file_count: int = 0
    total_size: int = 0
    truncated: bool = False


def build_tree(root: Path, *, max_files: int) -> TreeBuildResult:
    """Walk `root` once and return the tree plus flat file stats.

    Args:
        root: Repository root directory.
        max_files: Stop adding file nodes past this many (sets `truncated`).
    """
    root = root.resolve()
    result = TreeBuildResult(tree=TreeNode(name=root.name or "/", path=".", type=NodeType.DIRECTORY, children=[]))

    def walk(directory: Path) -> list[TreeNode]:
        children: list[TreeNode] = []
        try:
            # Directories first, then files, each alphabetically.
            entries = sorted(
                os.scandir(directory),
                key=lambda e: (e.is_file(follow_symlinks=False), e.name.lower()),
            )
        except OSError:
            return children

        for entry in entries:
            if entry.is_symlink():
                continue

            rel = Path(entry.path).resolve().relative_to(root).as_posix()

            if entry.is_dir(follow_symlinks=False):
                if entry.name in IGNORED_DIRS:
                    continue
                children.append(
                    TreeNode(
                        name=entry.name,
                        path=rel,
                        type=NodeType.DIRECTORY,
                        children=walk(Path(entry.path)),
                    )
                )
            elif entry.is_file(follow_symlinks=False):
                if result.file_count >= max_files:
                    result.truncated = True
                    continue
                try:
                    size = entry.stat(follow_symlinks=False).st_size
                except OSError:
                    size = 0
                result.files.append((rel, size))
                result.file_count += 1
                result.total_size += size
                children.append(
                    TreeNode(name=entry.name, path=rel, type=NodeType.FILE, size=size)
                )

        return children

    result.tree.children = walk(root)
    return result
