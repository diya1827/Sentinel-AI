"""Repository investigation tools for the AppSec agent.

These give the agent **read-only, sandboxed** access to the code it is reviewing
so it can *verify* scanner findings instead of trusting them blind: open the
exact file/line a finding points at, search for related sources/sinks/usages,
and inspect project structure. That verification loop is what turns the agent
from a summarizer into an investigator — confirming a vulnerability is real and
reachable, or downgrading a dummy "secret" that is obviously a test fixture.

Because this is a security product, the code under review is treated as hostile:
- every path is resolved and re-checked to live inside the repository root
  (symlinks that escape are rejected, since `resolve()` follows them first),
- reads are byte- and line-capped so a huge file can't blow the token budget,
- binary files are skipped rather than dumped,
- search skips heavy vendor/VCS directories and bounds how much it scans.

`build_repo_tools(root)` returns the tool instances to register for one review.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any

# Guardrails — keep tool output bounded so it can't exhaust the context window.
_MAX_FILE_BYTES = 64_000
_MAX_FILE_LINES = 400
_MAX_LINE_WIDTH = 300
_MAX_MATCH_RESULTS = 50
_MAX_SEARCH_FILES = 2_000
_MAX_DIR_ENTRIES = 200
_SNIFF_BYTES = 1_024
_SKIP_DIRS = frozenset(
    {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next", ".mypy_cache"}
)


class _Sandbox:
    """Resolves repo-relative paths safely and performs the file operations."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    # ── path safety ──────────────────────────────────────────────
    def _resolve(self, rel: str) -> Path:
        """Resolve a caller-supplied path, rejecting anything outside the root."""
        candidate = (self._root / (rel or "").strip()).resolve()
        if not candidate.is_relative_to(self._root):
            raise ValueError(f"Path escapes repository root: {rel!r}")
        return candidate

    def _rel(self, path: Path) -> str:
        return path.relative_to(self._root).as_posix()

    # ── operations ───────────────────────────────────────────────
    def read_file(
        self, path: str, start_line: int | None, end_line: int | None
    ) -> str:
        try:
            target = self._resolve(path)
        except ValueError as exc:
            return json.dumps({"error": str(exc)})
        if not target.is_file():
            return json.dumps({"error": f"Not a file: {path}"})

        data = target.read_bytes()
        truncated_bytes = len(data) > _MAX_FILE_BYTES
        if _looks_binary(data[:_SNIFF_BYTES]):
            return json.dumps({"error": f"Binary file, not shown: {path}"})

        lines = data[:_MAX_FILE_BYTES].decode("utf-8", errors="replace").splitlines()
        total = len(lines)

        if start_line is not None or end_line is not None:
            first = max(1, start_line or 1)
            last = min(total, end_line or total)
            chosen, offset = lines[first - 1 : last], first
        else:
            chosen, offset = lines[:_MAX_FILE_LINES], 1
            truncated_bytes = truncated_bytes or total > _MAX_FILE_LINES

        body = "\n".join(
            f"{offset + i}\t{ln[:_MAX_LINE_WIDTH]}" for i, ln in enumerate(chosen)
        )
        note = "\n… (truncated)" if truncated_bytes else ""
        return f"{self._rel(target)} ({total} lines):\n{body}{note}" if body else "(empty file)"

    def list_dir(self, path: str) -> str:
        try:
            target = self._resolve(path or ".")
        except ValueError as exc:
            return json.dumps({"error": str(exc)})
        if not target.is_dir():
            return json.dumps({"error": f"Not a directory: {path}"})

        entries: list[dict[str, Any]] = []
        for child in sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name)):
            if child.name in _SKIP_DIRS:
                continue
            is_dir = child.is_dir()
            entries.append(
                {
                    "name": child.name,
                    "type": "dir" if is_dir else "file",
                    "size": None if is_dir else child.stat().st_size,
                }
            )
            if len(entries) >= _MAX_DIR_ENTRIES:
                break
        return json.dumps({"path": self._rel(target), "entries": entries})

    def search(self, query: str, regex: bool, max_results: int) -> str:
        if not query:
            return json.dumps({"error": "Empty query."})
        try:
            matcher = re.compile(query) if regex else re.compile(re.escape(query))
        except re.error as exc:
            return json.dumps({"error": f"Invalid regex: {exc}"})

        cap = max(1, min(max_results or _MAX_MATCH_RESULTS, _MAX_MATCH_RESULTS))
        results: list[dict[str, Any]] = []
        scanned = 0

        for file in self._walk_files():
            if scanned >= _MAX_SEARCH_FILES:
                break
            scanned += 1
            try:
                data = file.read_bytes()
            except OSError:
                continue
            if _looks_binary(data[:_SNIFF_BYTES]):
                continue
            for lineno, line in enumerate(
                data.decode("utf-8", errors="replace").splitlines(), start=1
            ):
                if matcher.search(line):
                    results.append(
                        {
                            "file": self._rel(file),
                            "line": lineno,
                            "text": line.strip()[:_MAX_LINE_WIDTH],
                        }
                    )
                    if len(results) >= cap:
                        return json.dumps({"matches": results, "capped": True})
        return json.dumps({"matches": results, "files_scanned": scanned})

    def _walk_files(self):
        for dirpath, dirnames, filenames in os.walk(self._root):
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
            for name in filenames:
                yield Path(dirpath) / name


# ── Tool wrappers (implement the `Tool` protocol) ────────────────

class ReadFileTool:
    name = "read_file"
    description = (
        "Read a text file from the repository under review, optionally a line "
        "range, to inspect the actual code a finding points at. Returns the "
        "content with line numbers."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Repository-relative file path, e.g. 'src/db.py'.",
            },
            "start_line": {"type": "integer", "description": "First line (1-based, optional)."},
            "end_line": {"type": "integer", "description": "Last line, inclusive (optional)."},
        },
        "required": ["path"],
    }

    def __init__(self, sandbox: _Sandbox) -> None:
        self._sb = sandbox

    async def run(
        self, path: str, start_line: int | None = None, end_line: int | None = None
    ) -> str:
        return await asyncio.to_thread(self._sb.read_file, path, start_line, end_line)


class SearchCodeTool:
    name = "search_code"
    description = (
        "Search the repository for a string (or regex) and return matching "
        "file:line snippets. Use it to find where user input enters, where a "
        "dangerous sink is called, or every usage of a secret/variable."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Substring, or regex if regex=true."},
            "regex": {"type": "boolean", "description": "Treat query as a regex (default false)."},
            "max_results": {"type": "integer", "description": "Cap on matches (max 50)."},
        },
        "required": ["query"],
    }

    def __init__(self, sandbox: _Sandbox) -> None:
        self._sb = sandbox

    async def run(
        self, query: str, regex: bool = False, max_results: int = _MAX_MATCH_RESULTS
    ) -> str:
        return await asyncio.to_thread(self._sb.search, query, regex, max_results)


class ListDirectoryTool:
    name = "list_directory"
    description = (
        "List files and subdirectories at a path in the repository to understand "
        "its structure. Defaults to the repository root."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Repository-relative directory (default '.')."},
        },
    }

    def __init__(self, sandbox: _Sandbox) -> None:
        self._sb = sandbox

    async def run(self, path: str = ".") -> str:
        return await asyncio.to_thread(self._sb.list_dir, path)


def build_repo_tools(root: Path) -> list[Any]:
    """Build the read-only investigation tools bound to a repository root."""
    sandbox = _Sandbox(root)
    return [ReadFileTool(sandbox), SearchCodeTool(sandbox), ListDirectoryTool(sandbox)]


# ── helpers ──────────────────────────────────────────────────────

def _looks_binary(chunk: bytes) -> bool:
    """Heuristic: a NUL byte or a high ratio of non-text bytes ⇒ binary."""
    if not chunk:
        return False
    if b"\x00" in chunk:
        return True
    text_bytes = bytes(range(0x20, 0x7F)) + b"\n\r\t\f\b"
    nontext = sum(byte not in text_bytes for byte in chunk)
    return nontext / len(chunk) > 0.30
