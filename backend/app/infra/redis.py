"""Redis client — the single backbone for the queue, cache, and counters.

One dependency, several uses: the scan job queue (a Redis list), the
result cache (keyed by commit SHA), submit idempotency (`SET NX`), and atomic
metrics counters (`HINCRBY`).

To keep local development and tests friction-free, if `REDIS_URL` is not set we
fall back to an in-process `fakeredis` instance that speaks the same async API.
Production sets `REDIS_URL` to a real Redis (e.g. Upstash), and not a single
call site changes. The client is a process-wide singleton so the API handlers
and the in-process worker pool share the same connection/state.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.config.settings import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


@lru_cache
def get_redis() -> Any:
    """Return the shared async Redis client (real or in-process fake)."""
    url = get_settings().redis_url.strip()
    if url:
        import redis.asyncio as redis

        logger.info("Using Redis at %s", _safe_url(url))
        return redis.from_url(url, decode_responses=True)

    # No REDIS_URL → in-process fake so the app runs without a Redis install.
    import fakeredis.aioredis

    logger.warning(
        "REDIS_URL not set — using in-process fakeredis (fine for local/dev, "
        "not shared across processes or restarts)."
    )
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


def _safe_url(url: str) -> str:
    """Redact any credentials before logging a connection URL."""
    if "@" in url:
        scheme, _, tail = url.partition("://")
        return f"{scheme}://***@{tail.rsplit('@', 1)[-1]}"
    return url
