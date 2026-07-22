"""Safe async subprocess execution for scanner CLIs.

One place to run an external tool correctly:

* **No shell** — commands are argument lists passed to `create_subprocess_exec`,
  so a crafted file path or config value can never inject a shell command.
* **Bounded** — every call has a hard timeout; a hung tool is killed, not left
  to block the event loop forever.
* **Explicit missing-binary signal** — a not-installed tool raises
  `CommandNotFoundError` so callers can report it gracefully.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path


class CommandNotFoundError(RuntimeError):
    """Raised when the executable is not found on PATH."""


@dataclass
class ProcessResult:
    """Captured result of a finished (or timed-out) subprocess."""

    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


async def run_command(
    cmd: list[str],
    *,
    timeout: int,
    cwd: str | Path | None = None,
    env: dict[str, str] | None = None,
) -> ProcessResult:
    """Run `cmd` (no shell) and capture its output.

    Args:
        cmd: Executable + args as a list. Never a shell string.
        timeout: Hard timeout in seconds; the process is killed if exceeded.
        cwd: Optional working directory.
        env: Optional environment overrides.

    Raises:
        CommandNotFoundError: If `cmd[0]` is not installed.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(cwd) if cwd is not None else None,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise CommandNotFoundError(f"Executable not found: {cmd[0]!r}") from exc

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return ProcessResult(
            returncode=-1,
            stdout="",
            stderr=f"Command timed out after {timeout}s.",
            timed_out=True,
        )

    return ProcessResult(
        returncode=proc.returncode if proc.returncode is not None else -1,
        stdout=stdout.decode("utf-8", "replace"),
        stderr=stderr.decode("utf-8", "replace"),
    )
