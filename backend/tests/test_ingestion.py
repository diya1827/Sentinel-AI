"""Tests for ZIP safety and end-to-end ZIP ingestion."""

import zipfile
from pathlib import Path

import pytest

from app.config.settings import Settings
from app.models.repository import SourceType
from app.services.repository_service import RepositoryService
from app.utils.archive import ArchiveError, extract_zip


def _make_zip(path: Path, entries: dict[str, str]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, content in entries.items():
            zf.writestr(name, content)


def test_extract_rejects_zip_slip(tmp_path: Path) -> None:
    zip_path = tmp_path / "evil.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../escape.txt", "pwned")

    with pytest.raises(ArchiveError):
        extract_zip(
            zip_path, tmp_path / "out", max_files=100, max_total_size=1_000_000
        )


def test_extract_enforces_file_count(tmp_path: Path) -> None:
    zip_path = tmp_path / "many.zip"
    _make_zip(zip_path, {f"f{i}.txt": "x" for i in range(5)})

    with pytest.raises(ArchiveError):
        extract_zip(zip_path, tmp_path / "out", max_files=3, max_total_size=1_000_000)


@pytest.mark.asyncio
async def test_ingest_from_zip_detects_project(tmp_path: Path) -> None:
    # Build a small Python project as a zip.
    zip_path = tmp_path / "proj.zip"
    _make_zip(
        zip_path,
        {
            "myapp/app.py": "print('hi')\n",
            "myapp/utils.py": "x = 1\n",
            "requirements.txt": "fastapi\n",
            "README.md": "# hi\n",
        },
    )

    settings = Settings(scan_workspace_dir=str(tmp_path / "workspace"))
    service = RepositoryService(settings=settings)

    meta = await service.ingest_from_zip(zip_path)

    assert meta.source == SourceType.UPLOAD
    assert meta.primary_language == "Python"
    assert "pip" in meta.package_managers
    assert meta.file_count == 4
    assert meta.tree.type.value == "directory"

    # Cleanup removes the staged copy.
    assert service.cleanup(meta.repository_id) is True
    assert service.cleanup(meta.repository_id) is False
