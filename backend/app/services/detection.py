"""Language and package-manager detection.

Pure, side-effect-free functions that operate on a flat list of relative file
paths (as produced by `utils.filetree.build_tree`). Kept separate from the
service so they're trivially unit-testable and reusable.
"""

from __future__ import annotations

import os
from collections import Counter

from app.models.repository import LanguageStat

# Map file extension → human language name. Extend freely.
_EXTENSION_LANGUAGE: dict[str, str] = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".kt": "Kotlin",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".hpp": "C++",
    ".swift": "Swift",
    ".scala": "Scala",
    ".sh": "Shell",
    ".bash": "Shell",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "CSS",
    ".vue": "Vue",
    ".dart": "Dart",
    ".ex": "Elixir",
    ".exs": "Elixir",
}

# Map marker filename → package manager name. Some are refined by lockfiles.
_MARKER_PACKAGE_MANAGER: dict[str, str] = {
    "requirements.txt": "pip",
    "pyproject.toml": "pip",  # refined to poetry/pdm below when a lock is present
    "pipfile": "pipenv",
    "setup.py": "pip",
    "go.mod": "Go modules",
    "cargo.toml": "Cargo",
    "pom.xml": "Maven",
    "build.gradle": "Gradle",
    "build.gradle.kts": "Gradle",
    "gemfile": "Bundler",
    "composer.json": "Composer",
    "package.json": "npm",  # refined to yarn/pnpm below when a lock is present
}


def detect_languages(files: list[tuple[str, int]]) -> tuple[str | None, list[LanguageStat]]:
    """Return `(primary_language, breakdown)` from file extensions.

    The breakdown is sorted by descending file count; `primary_language` is the
    most common, or `None` if nothing recognizable was found.
    """
    counts: Counter[str] = Counter()
    for path, _size in files:
        ext = os.path.splitext(path)[1].lower()
        language = _EXTENSION_LANGUAGE.get(ext)
        if language:
            counts[language] += 1

    total = sum(counts.values())
    if total == 0:
        return None, []

    breakdown = [
        LanguageStat(
            language=language,
            file_count=count,
            percentage=round(count / total * 100, 2),
        )
        for language, count in counts.most_common()
    ]
    return breakdown[0].language, breakdown


def detect_package_managers(files: list[tuple[str, int]]) -> list[str]:
    """Return the sorted, de-duplicated set of package managers in use."""
    basenames = {os.path.basename(path).lower() for path, _ in files}

    managers: set[str] = set()
    for marker, manager in _MARKER_PACKAGE_MANAGER.items():
        if marker in basenames:
            managers.add(manager)

    # Refine JavaScript tooling by lockfile.
    if "package.json" in basenames:
        if "yarn.lock" in basenames:
            managers.discard("npm")
            managers.add("Yarn")
        if "pnpm-lock.yaml" in basenames:
            managers.discard("npm")
            managers.add("pnpm")

    # Refine Python tooling by lockfile.
    if "poetry.lock" in basenames:
        managers.discard("pip")
        managers.add("Poetry")
    if "pdm.lock" in basenames:
        managers.discard("pip")
        managers.add("PDM")

    return sorted(managers)
