"""Repository ingestion contracts.

Shared vocabulary for ingesting a codebase (from a ZIP upload or a public
GitHub URL) and describing what was found: the file tree, detected languages,
and detected package managers.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """How a repository entered the system."""

    UPLOAD = "upload"
    GITHUB = "github"


class NodeType(str, Enum):
    """Kind of a repository tree node."""

    FILE = "file"
    DIRECTORY = "directory"


class TreeNode(BaseModel):
    """A node in the repository file tree.

    Directories carry `children`; files carry `size`. Paths are POSIX-style
    and relative to the repository root.
    """

    name: str
    path: str
    type: NodeType
    size: int | None = None
    children: list["TreeNode"] | None = None


class LanguageStat(BaseModel):
    """Per-language file count and share of the codebase."""

    language: str
    file_count: int
    percentage: float


class GitHubIngestRequest(BaseModel):
    """Request body for ingesting a public GitHub repository."""

    repo_url: str = Field(
        ...,
        description="Public GitHub repository URL, e.g. https://github.com/owner/repo",
        examples=["https://github.com/psf/requests"],
    )


class RepositoryMetadata(BaseModel):
    """Result of a successful ingestion — the handle used by later stages."""

    repository_id: str
    source: SourceType
    primary_language: str | None = None
    languages: list[LanguageStat] = Field(default_factory=list)
    package_managers: list[str] = Field(default_factory=list)
    file_count: int = 0
    total_size_bytes: int = 0
    truncated: bool = Field(
        default=False,
        description="True if the tree hit the max-files cap and was truncated.",
    )
    tree: TreeNode


# Resolve the `TreeNode` forward reference used in its own `children` field.
TreeNode.model_rebuild()
