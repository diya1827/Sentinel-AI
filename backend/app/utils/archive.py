"""Safe ZIP extraction.

Defends against the two classic archive attacks before writing anything to
disk — this is a security product, so untrusted uploads are treated as hostile:

* **Zip-slip / path traversal** — a member named `../../etc/passwd` must never
  escape the destination directory.
* **Zip bombs** — refuse archives with too many entries or too large an
  uncompressed footprint.
"""

from __future__ import annotations

import zipfile
from pathlib import Path


class ArchiveError(ValueError):
    """Raised when an archive is malformed, unsafe, or exceeds limits."""


def _is_within(base: Path, target: Path) -> bool:
    """True if `target` resolves to a path inside `base`."""
    try:
        target.relative_to(base)
        return True
    except ValueError:
        return False


def extract_zip(
    zip_path: Path,
    dest_dir: Path,
    *,
    max_files: int,
    max_total_size: int,
) -> None:
    """Safely extract `zip_path` into `dest_dir`.

    Args:
        zip_path: Path to the uploaded `.zip` file.
        dest_dir: Directory to extract into (created if missing).
        max_files: Maximum number of entries allowed.
        max_total_size: Maximum total *uncompressed* size in bytes.

    Raises:
        ArchiveError: If the file is not a valid zip, breaks out of `dest_dir`,
            or exceeds the configured limits.
    """
    dest_dir = dest_dir.resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)

    if not zipfile.is_zipfile(zip_path):
        raise ArchiveError("Uploaded file is not a valid ZIP archive.")

    with zipfile.ZipFile(zip_path) as archive:
        infos = archive.infolist()

        if len(infos) > max_files:
            raise ArchiveError(
                f"Archive has too many entries ({len(infos)} > {max_files})."
            )

        total = sum(info.file_size for info in infos)
        if total > max_total_size:
            raise ArchiveError(
                f"Archive uncompressed size {total} exceeds limit {max_total_size}."
            )

        for info in infos:
            # Reject absolute paths and traversal before touching the FS.
            target = (dest_dir / info.filename).resolve()
            if not _is_within(dest_dir, target) and target != dest_dir:
                raise ArchiveError(
                    f"Refusing unsafe archive path: {info.filename!r}"
                )

            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as src, open(target, "wb") as dst:
                # Stream to avoid loading large members fully into memory.
                while chunk := src.read(64 * 1024):
                    dst.write(chunk)
