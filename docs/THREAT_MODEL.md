# Sentinel AI — Threat Model

Sentinel AI ingests and inspects **untrusted third-party code** (a public repo or
an uploaded zip), runs security scanners over it, and feeds the results to an LLM
agent that can read the code. That makes the code under review a **hostile input**
and the application itself an attractive target. This document models the threats
using STRIDE and records the mitigations already in the codebase.

## Assets
- The host running the backend (filesystem, network, process, credentials).
- The LLM API key and the app's own secrets (JWT signing key, GitHub token, DB).
- User accounts and their scan history.
- The integrity of the security report returned to the user.

## Trust boundaries
1. **Internet → API** — anonymous or authenticated HTTP requests.
2. **API → untrusted repo** — cloned/unzipped code staged on disk.
3. **Agent → repo files** — the LLM's read-only tool access to that code.
4. **Backend → external services** — LLM provider, GitHub, Redis, DB.

## STRIDE analysis

### Spoofing
- **Threat:** an attacker impersonates a user to read their scans.
- **Mitigations:** JWT auth (`HS256`), login attempt throttling with lockout
  (Redis-backed, `login_max_attempts` / `login_lockout_seconds`). The JWT secret
  **must** be overridden in production (`JWT_SECRET`); the dev default is
  intentionally insecure and flagged as such.

### Tampering
- **Threat:** a malicious repo writes outside its staged directory (path
  traversal / Zip Slip) or poisons another scan.
- **Mitigations:** the agent's file tools resolve every path with `.resolve()`
  and reject anything not `is_relative_to(root)` — symlink escapes included.
  Archive ingestion validates entries against Zip Slip and enforces file-count
  and total-size caps (`max_archive_files`, `max_archive_total_size_mb`). Repos
  are staged in per-id workspace directories.

### Repudiation
- **Threat:** actions can't be traced.
- **Mitigations:** structured logging around scans, scanner outcomes, and agent
  tool calls. *Gap:* no tamper-evident audit log (see Residual risks).

### Information disclosure
- **Threat:** leaking the app's own secrets, or one repo's data to another user.
- **Mitigations:** secrets are read only via typed settings (never
  `os.environ` directly) and are never returned in responses; tool output is
  size-capped so a huge file can't exfiltrate via the report; CORS is restricted
  to configured origins. The app runs its **own** Gitleaks over itself in CI to
  catch committed secrets.

### Denial of service
- **Threat:** a huge or pathological repo exhausts CPU, memory, or the token
  budget; request floods overwhelm the service.
- **Mitigations:** Semgrep memory/parallelism caps (`semgrep_max_memory`,
  `semgrep_jobs`); per-scanner timeouts; agent turn cap and findings cap
  (`_MAX_TURNS`, `_MAX_FINDINGS`); tool reads bounded by byte/line/result limits;
  Redis-backed rate limiting and a bounded worker pool on the job queue.

### Elevation of privilege
- **Threat:** the untrusted repo achieves code execution on the host.
- **Mitigations:** Sentinel **never executes the repo's code** — scanners are
  static analysis only, and the agent's tools are strictly read-only (no write,
  no exec). Scanners run as subprocesses over files, not the app's interpreter.

## Key design invariant
> The repository under review is treated as hostile: its code is read, never run;
> its paths are sandboxed; its size is bounded; and nothing it contains is trusted
> to be well-formed.

## Residual risks / future work
- No sandboxing (container/seccomp) around the scanner subprocesses themselves —
  a scanner RCE via a crafted input would run with app privileges. Isolating
  scans in an ephemeral container is the next hardening step.
- No tamper-evident audit trail.
- LLM prompt-injection from repo contents could bias the *narrative* of a report
  (not its scanner facts); triage decisions should be treated as advisory.
