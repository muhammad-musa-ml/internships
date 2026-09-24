"""The service under test.

ONE handler, TWO arms. The only difference between arms is whether a Redis
read-through cache sits in front of the Postgres resolve; the SQL, the pool, the
serialization and the response body are byte-identical either way. The arm is
chosen by the CACHE env var so that neither side can drift from the other by
accident - there is no second copy of the handler to keep in sync.

WHY THE UNCACHED ARM IS NOT A STRAWMAN
--------------------------------------
The "before" side is a competent implementation, not a crippled one:
  - the resolve is a single round-trip, not an N+1 loop;
  - every join column is indexed and the plan is an index scan (asserted at seed
    time by seed.py, which fails the build if a sequential scan appears);
  - it runs on a warm 512MB buffer pool sized to hold the whole dataset, so it is
    NOT paying disk I/O the cached arm avoids;
  - it uses a prepared statement over a properly sized asyncpg pool.
The work the cache removes is therefore genuine repeated COMPUTATION (a 3-table
join with two aggregates, re-executed per request for the same tenant), which is
exactly the bottleneck the claim describes. Making the uncached side slow on
purpose - an unindexed column, a tiny pool, a cold cache - would have produced a
bigger number and a worthless one.
"""
from __future__ import annotations

import hashlib
import os
import time

import asyncpg
import orjson
import redis.asyncio as aioredis
from fastapi import FastAPI, Response

PG_DSN = os.environ["PG_DSN"]
REDIS_URL = os.environ["REDIS_URL"]
CACHE_ON = os.environ.get("CACHE", "off").lower() in ("1", "on", "true")
POOL_MIN = int(os.environ.get("PG_POOL_MIN", "8"))
POOL_MAX = int(os.environ.get("PG_POOL_MAX", "32"))
TTL = int(os.environ.get("CACHE_TTL_SECONDS", "300"))

# The repeated per-request lookup: resolve a tenant's effective configuration.
# One round-trip, three tables, two aggregates - the shape of a real
# config/entitlement resolve that a request handler needs before it can do
# anything else, which is why it ends up on every request.
RESOLVE_SQL = """
SELECT t.id,
       t.name,
       t.plan,
       t.region,
       COALESCE((SELECT json_agg(json_build_object('k', f.feature_key, 'e', f.enabled)
                                 ORDER BY f.feature_key)
                 FROM features f WHERE f.tenant_id = t.id), '[]'::json) AS features,
       COALESCE((SELECT json_agg(json_build_object('k', q.quota_key, 'v', q.limit_value)
                                 ORDER BY q.quota_key)
                 FROM quotas q WHERE q.tenant_id = t.id), '[]'::json) AS quotas
FROM tenants t
WHERE t.id = $1
"""

app = FastAPI()
_state: dict = {"pool": None, "redis": None, "hits": 0, "misses": 0, "uncached": 0}


@app.on_event("startup")
async def _startup() -> None:
    _state["pool"] = await asyncpg.create_pool(
        PG_DSN, min_size=POOL_MIN, max_size=POOL_MAX, command_timeout=30
    )
    _state["redis"] = aioredis.from_url(REDIS_URL, decode_responses=False)


@app.on_event("shutdown")
async def _shutdown() -> None:
    if _state["pool"]:
        await _state["pool"].close()
    if _state["redis"]:
        await _state["redis"].aclose()


async def _resolve_from_pg(tenant_id: int) -> bytes:
    """Do the work, and serialize it into the EXACT bytes the cache would store."""
    row = await _state["pool"].fetchrow(RESOLVE_SQL, tenant_id)
    if row is None:
        return b""
    payload = {
        "tenant_id": row["id"],
        "name": row["name"],
        "plan": row["plan"],
        "region": row["region"],
        # asyncpg hands json back as text; parse so the canonical form is stable
        # and identical on both arms rather than depending on whitespace.
        "features": orjson.loads(row["features"]),
        "quotas": orjson.loads(row["quotas"]),
    }
    canonical = orjson.dumps(payload, option=orjson.OPT_SORT_KEYS)
    checksum = hashlib.sha256(canonical).hexdigest()
    # The cached VALUE is this whole body. Storing the checksum inside it is what
    # makes cross-arm byte-equality checkable from the client side.
    return orjson.dumps({"payload": payload, "checksum": checksum},
                        option=orjson.OPT_SORT_KEYS)


@app.get("/config/{tenant_id}")
async def get_config(tenant_id: int) -> Response:
    t0 = time.perf_counter_ns()
    cache_state = "off"

    if CACHE_ON:
        key = f"cfg:{tenant_id}"
        body = await _state["redis"].get(key)
        if body is not None:
            cache_state = "hit"
            _state["hits"] += 1
        else:
            cache_state = "miss"
            _state["misses"] += 1
            body = await _resolve_from_pg(tenant_id)
            if body:
                await _state["redis"].set(key, body, ex=TTL)
    else:
        _state["uncached"] += 1
        body = await _resolve_from_pg(tenant_id)

    if not body:
        return Response(content=b'{"error":"not found"}', status_code=404,
                        media_type="application/json")

    # SECOND CLOCK: server-side handler time, independent of the client's wall
    # clock. If the two clocks disagreed about the direction of the result, the
    # result would not be trustworthy (the discipline PH-A used).
    server_us = (time.perf_counter_ns() - t0) // 1000
    # Splice the two timing fields onto the cached body WITHOUT re-serializing it:
    # `{...}` + `,` + `"cache":...,"server_us":...}`. The comma is load-bearing -
    # concatenating the two fragments without it yields invalid JSON, and the
    # driver would then fail every request rather than measure anything.
    tail = orjson.dumps({"cache": cache_state, "server_us": server_us})
    return Response(
        content=body[:-1] + b"," + tail[1:],
        media_type="application/json",
        headers={"x-cache": cache_state, "x-server-us": str(server_us)},
    )


@app.get("/null")
async def null() -> Response:
    """DRIVER HEADROOM PROBE. Touches neither Postgres nor Redis.

    A throughput number is meaningless if the load generator, not the service, is
    the limiter. The driver measures this endpoint first and asserts its ceiling
    sits well above both measured arms; without that check a 'sustained RPS'
    figure could be reporting the driver's own limit for both arms and calling the
    difference a cache effect."""
    return Response(content=b'{"ok":true}', media_type="application/json")


@app.get("/config-info")
async def config_info() -> dict:
    """The service's OWN account of how it is configured.

    Added after adversarial review: the runner previously verified only
    `cache_on`, so nothing in the result artifacts recorded worker count or pool
    sizing - the two settings that most affect a throughput number. An arm could
    have run with a different shape and nothing would have noticed."""
    return {
        "cache_on": CACHE_ON,
        "workers": int(os.environ.get("WORKERS", "?")) if os.environ.get(
            "WORKERS", "").isdigit() else os.environ.get("WORKERS", "unset"),
        "pg_pool_min": POOL_MIN, "pg_pool_max": POOL_MAX,
        "cache_ttl_seconds": TTL,
    }


@app.get("/stats")
async def stats() -> dict:
    return {"cache_on": CACHE_ON, "hits": _state["hits"], "misses": _state["misses"],
            "uncached": _state["uncached"], "workers_note": "per-process counters"}


@app.post("/reset-stats")
async def reset_stats() -> dict:
    _state["hits"] = _state["misses"] = _state["uncached"] = 0
    return {"reset": True}
