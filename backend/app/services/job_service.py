"""JobService — the async scan platform: queue, workers, cache, counters.

Turns the (slow, rate-limited) scan+LLM pipeline from a blocking request into a
queue-backed job:

    POST /jobs ──▶ enqueue (Redis list) ──▶ worker pool (BRPOP) ──▶ ingest+scan+
                     │                                              LLM ──▶ store
                     └── returns job_id immediately ── GET /jobs/{id} polls ──────┘

Consistency & efficiency mechanics (the interesting part):

* **Idempotency** — a submit does `SET NX` on the (normalized) repo URL, so a
  double-click / concurrent duplicate returns the *existing* job instead of
  scanning twice.
* **Atomic job claim** — workers pull with `BRPOP`, which is atomic, so two
  workers can never grab the same job even under contention → each job runs once.
* **Result cache by commit SHA** — identical commit ⇒ identical result, served
  from cache; unchanged code is never rescanned.
* **Atomic counters** — every state transition is an `HINCRBY` (atomic
  server-side), so live metrics stay correct under concurrent workers where a
  read-modify-write counter would lose updates.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from app.config.settings import Settings, get_settings
from app.infra.redis import get_redis
from app.models.finding import Severity
from app.models.job import Job, JobKind, JobStatus, Metrics, SubmitResponse
from app.services.agent_service import AgentService
from app.services.repository_service import RepositoryService
from app.services.scanner_service import ScannerService
from app.utils.git import get_head_sha, normalize_github_url
from app.utils.logging import get_logger
from app.utils.workspace import Workspace

logger = get_logger(__name__)

_PREFIX = "sentinel"
_QUEUE_KEY = f"{_PREFIX}:queue"
_METRICS_KEY = f"{_PREFIX}:metrics"
_BRPOP_TIMEOUT = 5  # seconds a blocked worker waits before looping (for shutdown)


class JobService:
    """Submit, run (via a worker pool), and observe async scan jobs."""

    def __init__(
        self,
        settings: Settings | None = None,
        redis: Any | None = None,
        repositories: RepositoryService | None = None,
        scanners: ScannerService | None = None,
        agent: AgentService | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._redis = redis or get_redis()
        self._repositories = repositories or RepositoryService(self._settings)
        self._scanners = scanners or ScannerService(self._settings)
        self._agent = agent or AgentService(self._settings)
        self._workspace = Workspace(self._settings.scan_workspace_dir)

    # ── Keys ─────────────────────────────────────────────────────
    @staticmethod
    def _job_key(job_id: str) -> str:
        return f"{_PREFIX}:job:{job_id}"

    @staticmethod
    def _idem_key(url: str) -> str:
        return f"{_PREFIX}:idem:{url}"

    @staticmethod
    def _result_key(sha: str) -> str:
        return f"{_PREFIX}:result:{sha}"

    # ── Submit ───────────────────────────────────────────────────
    async def submit_github(self, repo_url: str) -> SubmitResponse:
        """Enqueue a scan of a public GitHub URL (idempotent per URL).

        Raises:
            InvalidRepoUrlError: If the URL is malformed or not allow-listed.
        """
        url = normalize_github_url(repo_url, self._settings.allowed_git_hosts_list)
        job_id = _new_id()

        # Atomic idempotency: only the first submit of an in-flight URL wins.
        claimed = await self._redis.set(
            self._idem_key(url), job_id, nx=True, ex=self._settings.idempotency_ttl
        )
        if not claimed:
            existing_id = await self._redis.get(self._idem_key(url))
            existing = existing_id and await self._redis.hget(
                self._job_key(existing_id), "status"
            )
            if existing:  # a live duplicate → return it, don't scan again
                await self._redis.hincrby(_METRICS_KEY, "jobs_deduplicated", 1)
                return SubmitResponse(
                    job_id=existing_id,
                    status=JobStatus(existing),
                    deduplicated=True,
                )
            # Stale key (job expired) — take it over for our new job.
            await self._redis.set(
                self._idem_key(url), job_id, ex=self._settings.idempotency_ttl
            )

        await self._enqueue(job_id, JobKind.GITHUB, repo_url=url)
        return SubmitResponse(job_id=job_id, status=JobStatus.QUEUED)

    async def submit_repository(self, repository_id: str) -> SubmitResponse:
        """Enqueue a scan of an already-ingested repository (e.g. a ZIP upload)."""
        job_id = _new_id()
        await self._enqueue(job_id, JobKind.UPLOAD, repository_id=repository_id)
        return SubmitResponse(job_id=job_id, status=JobStatus.QUEUED)

    async def _enqueue(
        self,
        job_id: str,
        kind: JobKind,
        *,
        repo_url: str | None = None,
        repository_id: str | None = None,
    ) -> None:
        now = time.time()
        mapping = {
            "id": job_id,
            "kind": kind.value,
            "status": JobStatus.QUEUED.value,
            "created_at": now,
            "updated_at": now,
        }
        if repo_url:
            mapping["repo_url"] = repo_url
        if repository_id:
            mapping["repository_id"] = repository_id

        await self._redis.hset(self._job_key(job_id), mapping=mapping)
        await self._redis.expire(self._job_key(job_id), self._settings.job_ttl)
        await self._redis.hincrby(_METRICS_KEY, "jobs_queued", 1)
        await self._redis.lpush(_QUEUE_KEY, job_id)  # FIFO with BRPOP
        logger.info("Enqueued job %s (%s)", job_id, kind.value)

    # ── Read ─────────────────────────────────────────────────────
    async def get_job(self, job_id: str) -> Job | None:
        data = await self._redis.hgetall(self._job_key(job_id))
        return _job_from_hash(data) if data else None

    async def get_metrics(self) -> Metrics:
        raw = await self._redis.hgetall(_METRICS_KEY)
        counts = {k: int(v) for k, v in raw.items()}
        by_sev = {
            sev.value: counts.get(f"findings_{sev.value}", 0) for sev in Severity
        }
        return Metrics(
            jobs_queued=counts.get("jobs_queued", 0),
            jobs_running=counts.get("jobs_running", 0),
            jobs_done=counts.get("jobs_done", 0),
            jobs_failed=counts.get("jobs_failed", 0),
            jobs_deduplicated=counts.get("jobs_deduplicated", 0),
            cache_hits=counts.get("cache_hits", 0),
            findings_by_severity=by_sev,
        )

    # ── Worker ───────────────────────────────────────────────────
    async def run_worker(self, name: str) -> None:
        """Long-running loop: atomically claim jobs and process them.

        Cancelled on shutdown; `BRPOP` blocks only up to `_BRPOP_TIMEOUT` so
        cancellation is responsive.
        """
        logger.info("Worker %s started", name)
        while True:
            try:
                popped = await self._redis.brpop(_QUEUE_KEY, timeout=_BRPOP_TIMEOUT)
            except asyncio.CancelledError:
                logger.info("Worker %s stopping", name)
                raise
            except Exception:  # noqa: BLE001 — never let the pool die
                logger.exception("Worker %s: queue read failed; backing off", name)
                await asyncio.sleep(1)
                continue

            if popped is None:
                continue  # timed out with an empty queue → loop
            _, job_id = popped
            await self._process(job_id)

    async def _process(self, job_id: str) -> None:
        job_key = self._job_key(job_id)
        await self._transition(job_key, JobStatus.RUNNING, running_delta=+1, queued_delta=-1)

        kind = await self._redis.hget(job_key, "kind")
        repo_url = await self._redis.hget(job_key, "repo_url")
        repository_id: str | None = None
        try:
            if kind == JobKind.GITHUB.value:
                metadata = await self._repositories.ingest_from_github(repo_url)
                repository_id = metadata.repository_id
                sha = await get_head_sha(self._workspace.path_for(repository_id))

                cached = await self._redis.get(self._result_key(sha)) if sha else None
                if cached:
                    await self._redis.hincrby(_METRICS_KEY, "cache_hits", 1)
                    await self._finish(job_key, json.loads(cached), sha, cached=True)
                    return

                result = await self._run_pipeline(metadata, repository_id)
                if sha:
                    await self._redis.set(
                        self._result_key(sha),
                        json.dumps(result),
                        ex=self._settings.result_cache_ttl,
                    )
                await self._finish(job_key, result, sha, cached=False)
            else:  # UPLOAD — already staged under repository_id
                repository_id = await self._redis.hget(job_key, "repository_id")
                metadata = await self._repositories.describe(repository_id)
                result = await self._run_pipeline(metadata, repository_id)
                await self._finish(job_key, result, None, cached=False)
        except Exception as exc:  # noqa: BLE001 — record failure, keep worker alive
            logger.exception("Job %s failed", job_id)
            await self._fail(job_key, exc)
            # Let a failed URL be retried later.
            if kind == JobKind.GITHUB.value and repo_url:
                await self._redis.delete(self._idem_key(repo_url))
        finally:
            if repository_id:
                self._repositories.cleanup(repository_id)

    async def _run_pipeline(self, metadata: Any, repository_id: str) -> dict[str, Any]:
        """Scan + AI review; bump findings counters; return the report dict."""
        scan = await self._scanners.scan_repository(repository_id)
        report = await self._agent.analyze(metadata, scan)
        for sev, count in scan.severity_counts.items():
            if count:
                await self._redis.hincrby(_METRICS_KEY, f"findings_{sev}", count)
        return report.model_dump(mode="json")

    # ── State transitions (atomic counters) ──────────────────────
    async def _transition(
        self, job_key: str, status: JobStatus, *, running_delta=0, queued_delta=0
    ) -> None:
        await self._redis.hset(
            job_key, mapping={"status": status.value, "updated_at": time.time()}
        )
        if queued_delta:
            await self._redis.hincrby(_METRICS_KEY, "jobs_queued", queued_delta)
        if running_delta:
            await self._redis.hincrby(_METRICS_KEY, "jobs_running", running_delta)

    async def _finish(
        self, job_key: str, result: dict[str, Any], sha: str | None, *, cached: bool
    ) -> None:
        mapping = {
            "status": JobStatus.DONE.value,
            "result": json.dumps(result),
            "cached": "1" if cached else "0",
            "updated_at": time.time(),
        }
        if sha:
            mapping["commit_sha"] = sha
        await self._redis.hset(job_key, mapping=mapping)
        await self._redis.expire(job_key, self._settings.job_ttl)
        await self._redis.hincrby(_METRICS_KEY, "jobs_done", 1)
        await self._redis.hincrby(_METRICS_KEY, "jobs_running", -1)

    async def _fail(self, job_key: str, exc: Exception) -> None:
        await self._redis.hset(
            job_key,
            mapping={
                "status": JobStatus.FAILED.value,
                "error": f"{type(exc).__name__}: {exc}"[:2000],
                "updated_at": time.time(),
            },
        )
        await self._redis.expire(job_key, self._settings.job_ttl)
        await self._redis.hincrby(_METRICS_KEY, "jobs_failed", 1)
        await self._redis.hincrby(_METRICS_KEY, "jobs_running", -1)


# ── module helpers ───────────────────────────────────────────────

def _new_id() -> str:
    from uuid import uuid4

    return uuid4().hex


def _job_from_hash(data: dict[str, str]) -> Job:
    return Job(
        id=data["id"],
        kind=JobKind(data["kind"]),
        status=JobStatus(data["status"]),
        repo_url=data.get("repo_url"),
        repository_id=data.get("repository_id"),
        commit_sha=data.get("commit_sha"),
        result=json.loads(data["result"]) if data.get("result") else None,
        error=data.get("error"),
        cached=data.get("cached") == "1",
        created_at=float(data["created_at"]) if data.get("created_at") else None,
        updated_at=float(data["updated_at"]) if data.get("updated_at") else None,
    )
