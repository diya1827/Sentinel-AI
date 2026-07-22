"""Tests for the agent's read-only repository investigation tools.

The sandbox is security-critical (it reads an untrusted repo), so traversal
rejection and binary/size guards are covered alongside the happy paths.
"""

import json
from pathlib import Path

import pytest

from app.agents.repo_tools import build_repo_tools


def _tools(root: Path) -> dict:
    return {t.name: t for t in build_repo_tools(root)}


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "db.py").write_text(
        "import os\nQUERY = 'SELECT * FROM users WHERE id=' + user_input\nTOKEN = 'dummy'\n"
    )
    (tmp_path / "README.md").write_text("# Demo\n")
    (tmp_path / "logo.png").write_bytes(b"\x89PNG\x00\x00\x00\x00binary\x00bytes")
    return tmp_path


@pytest.mark.asyncio
async def test_read_file_returns_numbered_lines(repo: Path) -> None:
    out = await _tools(repo)["read_file"].run(path="app/db.py")
    assert "SELECT * FROM users" in out
    assert "2\t" in out  # line numbers are present


@pytest.mark.asyncio
async def test_read_file_line_range(repo: Path) -> None:
    out = await _tools(repo)["read_file"].run(path="app/db.py", start_line=2, end_line=2)
    assert "SELECT * FROM users" in out
    assert "import os" not in out


@pytest.mark.asyncio
async def test_read_file_rejects_traversal(repo: Path) -> None:
    out = await _tools(repo)["read_file"].run(path="../../../etc/passwd")
    assert "escapes repository root" in out


@pytest.mark.asyncio
async def test_read_file_skips_binary(repo: Path) -> None:
    out = await _tools(repo)["read_file"].run(path="logo.png")
    assert "Binary file" in out


@pytest.mark.asyncio
async def test_search_code_finds_matches(repo: Path) -> None:
    out = json.loads(await _tools(repo)["search_code"].run(query="SELECT"))
    assert out["matches"]
    assert out["matches"][0]["file"] == "app/db.py"
    assert out["matches"][0]["line"] == 2


@pytest.mark.asyncio
async def test_search_code_skips_binary_files(repo: Path) -> None:
    out = json.loads(await _tools(repo)["search_code"].run(query="binary"))
    assert out["matches"] == []  # the PNG is skipped, not matched


@pytest.mark.asyncio
async def test_list_directory(repo: Path) -> None:
    out = json.loads(await _tools(repo)["list_directory"].run(path="."))
    names = {e["name"] for e in out["entries"]}
    assert {"app", "README.md"} <= names
