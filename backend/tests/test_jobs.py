"""Tests for the async job platform — queue, idempotency, cache, counters.

Uses a real in-memory fakeredis (same async API as production Redis) plus small
fakes for the ingest/scan/LLM pipeline, so the concurrency/consistency logic is
exercised without network, git, or an LLM.
"""

from types import SimpleNamespace

import fakeredis.aioredis
import pytest

from app.services.job_service import JobService
from app.models.job import JobStatus

REPO_URL = "https://github.com/owner/repo"


class FakeRepos:
    def __init__(self) -> None:
        self.cleaned: list[str] = []

    async def ingest_from_github(self, url: str):
        return SimpleNamespace(repository_id="abc123")

    async def describe(self, repository_id: str):
        return SimpleNamespace(repository_id=repository_id)

    def cleanup(self, repository_id: str) -> bool:
        self.cleaned.append(repository_id)
        return True


class FakeScanners:
    def __init__(self) -> None:
        self.calls = 0

    async def scan_repository(self, repository_id: str):
        self.calls += 1
        return SimpleNamespace(
            severity_counts={"critical": 1, "high": 2, "medium": 0, "low": 0, "info": 0}
        )


class FakeReport:
    def model_dump(self, mode: str = "python") -> dict:
        return {"overall_risk": "high", "prioritized_findings": []}


class FakeAgent:
    async def analyze(self, metadata, scan):
        return FakeReport()


@pytest.fixture
def redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def service(redis):
    return JobService(
        redis=redis,
        repositories=FakeRepos(),
        scanners=FakeScanners(),
        agent=FakeAgent(),
    )


# ── Submit / enqueue ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_submit_enqueues_and_counts(service, redis):
    resp = await service.submit_github(REPO_URL)
    assert resp.status is JobStatus.QUEUED
    assert not resp.deduplicated

    job = await service.get_job(resp.job_id)
    assert job.status is JobStatus.QUEUED
    metrics = await service.get_metrics()
    assert metrics.jobs_queued == 1
    # The job id is on the queue.
    assert await redis.llen("sentinel:queue") == 1


@pytest.mark.asyncio
async def test_submit_is_idempotent_per_url(service):
    first = await service.submit_github(REPO_URL)
    second = await service.submit_github(REPO_URL)  # duplicate in-flight

    assert second.job_id == first.job_id
    assert second.deduplicated is True
    metrics = await service.get_metrics()
    assert metrics.jobs_deduplicated == 1
    assert metrics.jobs_queued == 1  # only one job actually enqueued


# ── Worker processing ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_process_runs_pipeline_and_updates_counters(service, monkeypatch):
    monkeypatch.setattr(
        "app.services.job_service.get_head_sha",
        _fake_sha("sha-1"),
    )
    resp = await service.submit_github(REPO_URL)
    await service._process(resp.job_id)

    job = await service.get_job(resp.job_id)
    assert job.status is JobStatus.DONE
    assert job.result == {"overall_risk": "high", "prioritized_findings": []}
    assert job.commit_sha == "sha-1"
    assert job.cached is False

    m = await service.get_metrics()
    assert m.jobs_done == 1
    assert m.jobs_running == 0
    assert m.jobs_queued == 0
    assert m.findings_by_severity["critical"] == 1
    assert m.findings_by_severity["high"] == 2


@pytest.mark.asyncio
async def test_result_is_cached_by_commit_sha(service, redis, monkeypatch):
    # Pre-seed the cache for sha-9; a job resolving to that sha must not rescan.
    await redis.set("sentinel:result:sha-9", '{"overall_risk": "low"}')
    monkeypatch.setattr("app.services.job_service.get_head_sha", _fake_sha("sha-9"))

    resp = await service.submit_github(REPO_URL)
    await service._process(resp.job_id)

    job = await service.get_job(resp.job_id)
    assert job.status is JobStatus.DONE
    assert job.cached is True
    assert job.result == {"overall_risk": "low"}
    assert service._scanners.calls == 0  # cache hit → scanner never ran
    assert (await service.get_metrics()).cache_hits == 1


@pytest.mark.asyncio
async def test_failed_job_is_recorded(service, monkeypatch):
    async def boom(url):
        raise RuntimeError("clone exploded")

    monkeypatch.setattr(service._repositories, "ingest_from_github", boom)
    resp = await service.submit_github(REPO_URL)
    await service._process(resp.job_id)

    job = await service.get_job(resp.job_id)
    assert job.status is JobStatus.FAILED
    assert "clone exploded" in job.error
    assert (await service.get_metrics()).jobs_failed == 1


@pytest.mark.asyncio
async def test_missing_job_returns_none(service):
    assert await service.get_job("does-not-exist") is None


def _fake_sha(sha: str):
    async def _inner(path, **kwargs):
        return sha

    return _inner
