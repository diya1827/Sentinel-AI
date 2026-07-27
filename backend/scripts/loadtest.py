"""Load test for the async scan platform.

Fires many concurrent `POST /jobs` submissions, measures submit throughput and
idempotent dedup, then (optionally) polls `/metrics` while the worker pool
drains the queue to measure end-to-end completion throughput.

Usage:
    python scripts/loadtest.py --base http://127.0.0.1:8000 --total 100 --unique 20
    python scripts/loadtest.py --base <url> --total 100 --unique 20 --wait

`--total` submissions are spread over `--unique` distinct repos; the remainder
are duplicates, which the server should deduplicate (exactly-once). Point it at
a LOCAL backend for the `--wait` end-to-end run so you don't hit Gemini's
free-tier rate limits.
"""

from __future__ import annotations

import argparse
import asyncio
import time

import httpx

# Small public repos used to fill the unique slots (cycled as needed).
_REPOS = [
    "https://github.com/Plazmaz/leaky-repo",
    "https://github.com/snyk-labs/nodejs-goof",
    "https://github.com/OWASP/NodeGoat",
    "https://github.com/digininja/DVWA",
    "https://github.com/appsecco/dvna",
]


def _build_urls(total: int, unique: int) -> list[str]:
    # The server rejects query strings, so duplicates are just repeated URLs —
    # which is what idempotency should collapse. Distinct repos come from the
    # pool, capped at its size.
    effective = max(1, min(unique, len(_REPOS)))
    return [_REPOS[i % effective] for i in range(total)]


async def _submit(client: httpx.AsyncClient, base: str, url: str) -> dict:
    t0 = time.perf_counter()
    r = await client.post(f"{base}/api/v1/jobs", json={"repo_url": url}, timeout=30)
    dt = time.perf_counter() - t0
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    return {"status": r.status_code, "dt": dt, "dedup": bool(body.get("deduplicated"))}


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--total", type=int, default=100)
    ap.add_argument("--unique", type=int, default=20)
    ap.add_argument("--concurrency", type=int, default=50)
    ap.add_argument("--wait", action="store_true", help="poll /metrics until drained")
    args = ap.parse_args()

    urls = _build_urls(args.total, args.unique)
    sem = asyncio.Semaphore(args.concurrency)

    async with httpx.AsyncClient() as client:
        async def guarded(u: str) -> dict:
            async with sem:
                return await _submit(client, args.base, u)

        print(f"Submitting {args.total} jobs ({args.unique} unique) -> {args.base}")
        t0 = time.perf_counter()
        results = await asyncio.gather(*(guarded(u) for u in urls))
        elapsed = time.perf_counter() - t0

        ok = sum(r["status"] in (200, 202) for r in results)
        dedup = sum(r["dedup"] for r in results)
        lat = sorted(r["dt"] for r in results)
        p50 = lat[len(lat) // 2] * 1000
        p95 = lat[min(len(lat) - 1, int(len(lat) * 0.95))] * 1000

        print("\n-- Submit phase ----------------------------")
        print(f"  accepted        : {ok}/{args.total}")
        print(f"  deduplicated    : {dedup}  (idempotent repeats collapsed)")
        print(f"  submit throughput: {args.total / elapsed:.0f} req/s")
        print(f"  latency p50/p95 : {p50:.0f}ms / {p95:.0f}ms")

        if not args.wait:
            print("\n(pass --wait to measure end-to-end drain throughput)")
            return

        target = args.unique  # distinct jobs that actually run
        print(f"\n-- Drain phase (waiting for {target} jobs to finish) --")
        start = time.perf_counter()
        while True:
            m = (await client.get(f"{args.base}/api/v1/metrics")).json()
            done = m.get("jobs_done", 0) + m.get("jobs_failed", 0)
            running, queued = m.get("jobs_running", 0), m.get("jobs_queued", 0)
            print(f"  done={done} running={running} queued={queued}", end="\r")
            if done >= target:
                break
            await asyncio.sleep(1)
        drain = time.perf_counter() - start
        print(f"\n  drained {target} jobs in {drain:.1f}s "
              f"-> {target / drain:.2f} jobs/s end-to-end")


if __name__ == "__main__":
    asyncio.run(main())
