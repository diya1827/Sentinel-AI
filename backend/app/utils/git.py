"""Safe `git clone` of public repositories.

Security posture (again, this is a security product ingesting attacker-supplied
input):

* **URL allow-listing** — only `https` URLs to configured hosts (default
  `github.com`) are accepted. Embedded credentials (`user:pass@`) are stripped.
* **No shell** — git is invoked with an argument list via
  `create_subprocess_exec`, so a crafted URL can never inject a shell command.
* **No prompts / no hang** — `GIT_TERMINAL_PROMPT=0` plus a hard timeout stop a
  private/invalid repo from blocking on an interactive auth prompt.
* **Shallow** — `--depth` keeps clones small and fast.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from urllib.parse import urlparse


class GitCloneError(RuntimeError):
    """Raised when a clone fails or times out."""


class InvalidRepoUrlError(ValueError):
    """Raised when a repository URL is malformed or not allow-listed."""


def normalize_github_url(raw: str, allowed_hosts: list[str]) -> str:
    """Validate and canonicalize a public repo URL to `https://host/owner/repo.git`.

    Raises:
        InvalidRepoUrlError: If the URL is not a clean https URL to an
            allow-listed host with an `owner/repo` path.
    """
    candidate = (raw or "").strip()
    if not candidate:
        raise InvalidRepoUrlError("Repository URL must not be empty.")

    parsed = urlparse(candidate)

    if parsed.scheme != "https":
        raise InvalidRepoUrlError("Only https:// repository URLs are supported.")
    if parsed.username or parsed.password:
        raise InvalidRepoUrlError("Credentials in repository URLs are not allowed.")
    # Params/query/fragment have no place in a clone URL and can smuggle
    # characters past path parsing (e.g. "re;po" → params="po").
    if parsed.params or parsed.query or parsed.fragment:
        raise InvalidRepoUrlError("Repository URL must not contain query/fragment parts.")

    host = (parsed.hostname or "").lower()
    if host not in allowed_hosts:
        raise InvalidRepoUrlError(
            f"Host {host!r} is not allowed. Allowed hosts: {', '.join(allowed_hosts)}."
        )

    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        raise InvalidRepoUrlError("URL must point to an owner/repository.")

    owner, repo = parts[0], parts[1]
    if repo.endswith(".git"):
        repo = repo[: -len(".git")]

    # Reject anything outside a conservative character set for owner/repo.
    for segment in (owner, repo):
        if not segment or not all(c.isalnum() or c in "-._" for c in segment):
            raise InvalidRepoUrlError(f"Invalid path segment: {segment!r}")

    return f"https://{host}/{owner}/{repo}.git"


async def clone_repository(
    url: str,
    dest_dir: Path,
    *,
    depth: int,
    timeout: int,
) -> None:
    """Shallow-clone `url` into `dest_dir`.

    Args:
        url: A validated https clone URL (see `normalize_github_url`).
        dest_dir: Target directory (must not already exist).
        depth: Shallow clone depth.
        timeout: Hard timeout in seconds.

    Raises:
        GitCloneError: On non-zero exit or timeout.
    """
    env = {
        **os.environ,
        "GIT_TERMINAL_PROMPT": "0",  # never prompt for credentials
        "GCM_INTERACTIVE": "Never",  # disable Git Credential Manager UI
    }

    cmd = [
        "git",
        "clone",
        "--depth",
        str(depth),
        "--single-branch",
        "--no-tags",
        url,
        str(dest_dir),
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError as exc:  # git not installed
        raise GitCloneError("`git` executable not found on PATH.") from exc

    try:
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError as exc:
        proc.kill()
        await proc.wait()
        raise GitCloneError(f"Clone timed out after {timeout}s.") from exc

    if proc.returncode != 0:
        detail = stderr.decode("utf-8", "replace").strip()
        raise GitCloneError(f"git clone failed: {detail}")
