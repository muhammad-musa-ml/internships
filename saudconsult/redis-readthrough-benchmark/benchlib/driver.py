"""Closed-loop concurrency sweep that holds p99 as the control variable.

WHY A SWEEP AND NOT A SINGLE NUMBER
-----------------------------------
"Throughput" alone is not comparable between two systems - anyone can push RPS up
by letting latency grow without bound. The claim under test pins the tail
("at a fixed p99 of 250 ms"), so the measurement has to pin it too: sweep
concurrency, record (rps, p99) at each level, and report the HIGHEST rps whose
measured p99 is still at or under the ceiling. Peak RPS at unbounded latency is
NOT reported, because it would not be the claim.

Both arms run the identical ladder, the identical seeded key sequence in the
identical order, and an uncounted warmup at every level.
"""
from __future__ import annotations

import asyncio
import statistics
import time

import httpx

P99_CEILING_MS = 250.0


def _pct(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    s = sorted(values)
    # Nearest-rank percentile: unambiguous, no interpolation to argue about.
    k = max(0, min(len(s) - 1, int(round(q / 100.0 * len(s) + 0.5)) - 1))
    return s[k]


async def _worker(client: httpx.AsyncClient, base: str, seq: list[int], cursor: list[int],
                  deadline: float, lat_ms: list[float], srv_us: list[int],
                  errors: list[str], checksums: dict[int, str], collect_ck: bool,
                  cache_states: dict[str, int]) -> None:
    n = len(seq)
    while time.perf_counter() < deadline:
        i = cursor[0]
        cursor[0] = i + 1
        tid = seq[i % n]
        t0 = time.perf_counter()
        try:
            r = await client.get(f"{base}/config/{tid}")
            dt = (time.perf_counter() - t0) * 1000.0
            if r.status_code != 200:
                errors.append(f"HTTP {r.status_code}")
                continue
            lat_ms.append(dt)
            body = r.json()          # parsing failure surfaces as an error, not a silent pass
            srv_us.append(int(body["server_us"]))
            # Hit rate is counted CLIENT-SIDE, per response. The service's /stats
            # counters live in process memory and uvicorn runs several workers, so
            # /stats reports one worker's slice - reading the hit rate off it would
            # under-report by roughly the worker count. The per-response `cache`
            # field is exact and is observed by the party doing the measuring.
            cache_states[body["cache"]] = cache_states.get(body["cache"], 0) + 1
            if collect_ck:
                checksums[tid] = body["checksum"]
        except Exception as exc:                                   # noqa: BLE001
            errors.append(f"{exc.__class__.__name__}: {exc}")


async def measure_level(base: str, seq: list[int], concurrency: int, seconds: float,
                        warmup_seconds: float, collect_ck: bool) -> dict:
    limits = httpx.Limits(max_connections=concurrency + 16,
                          max_keepalive_connections=concurrency + 16)
    timeout = httpx.Timeout(30.0)
    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        # UNCOUNTED WARMUP at this level - pools, connections and JIT-ish effects
        # settle before anything is recorded, so neither arm pays a cold penalty
        # the other avoids.
        wcur, wl, ws, we, wc, wcs = [0], [], [], [], {}, {}
        wdead = time.perf_counter() + warmup_seconds
        await asyncio.gather(*[
            _worker(client, base, seq, wcur, wdead, wl, ws, we, wc, False, wcs)
            for _ in range(concurrency)])

        cursor, lat, srv, errs, cks, cstates = [0], [], [], [], {}, {}
        t_start = time.perf_counter()
        deadline = t_start + seconds
        await asyncio.gather(*[
            _worker(client, base, seq, cursor, deadline, lat, srv, errs, cks,
                    collect_ck, cstates)
            for _ in range(concurrency)])
        elapsed = time.perf_counter() - t_start

    completed = len(lat)
    return {
        "concurrency": concurrency,
        "elapsed_s": round(elapsed, 3),
        "completed": completed,
        "errors": len(errs),
        "error_sample": errs[:5],
        "rps": round(completed / elapsed, 1) if elapsed > 0 else 0.0,
        "client_ms": {
            "p50": round(_pct(lat, 50), 2), "p95": round(_pct(lat, 95), 2),
            "p99": round(_pct(lat, 99), 2), "max": round(max(lat), 2) if lat else None,
            "mean": round(statistics.fmean(lat), 2) if lat else None,
        },
        "server_us": {
            "p50": int(_pct([float(x) for x in srv], 50)) if srv else None,
            "p99": int(_pct([float(x) for x in srv], 99)) if srv else None,
        },
        "cache_states": cstates,
        "checksums": cks,
    }


async def sweep(base: str, seq: list[int], ladder: list[int], seconds: float,
                warmup_seconds: float, collect_ck: bool) -> list[dict]:
    out = []
    for c in ladder:
        lvl = await measure_level(base, seq, c, seconds, warmup_seconds, collect_ck)
        ck = lvl.pop("checksums")
        if collect_ck and ck:
            lvl["_checksums"] = ck
        out.append(lvl)
        print(f"    c={c:<4} rps={lvl['rps']:<9} p50={lvl['client_ms']['p50']:<8} "
              f"p99={lvl['client_ms']['p99']:<9} err={lvl['errors']}")
    return out


def sustained_at_ceiling(levels: list[dict], ceiling_ms: float = P99_CEILING_MS) -> dict:
    """The reported number: highest rps among levels whose p99 <= the ceiling."""
    ok = [l for l in levels
          if l["errors"] == 0 and l["client_ms"]["p99"] is not None
          and l["client_ms"]["p99"] <= ceiling_ms]
    if not ok:
        return {"sustained_rps": None, "at_concurrency": None, "p99_ms": None,
                "note": f"no level held p99 <= {ceiling_ms} ms with zero errors"}
    best = max(ok, key=lambda l: l["rps"])
    return {"sustained_rps": best["rps"], "at_concurrency": best["concurrency"],
            "p99_ms": best["client_ms"]["p99"], "p50_ms": best["client_ms"]["p50"],
            "server_us_p50": best["server_us"]["p50"],
            "server_us_p99": best["server_us"]["p99"]}


async def null_ceiling(base: str, ladder: list[int], seconds: float) -> dict:
    """DRIVER HEADROOM. Max rps the driver can pull from a do-nothing endpoint.

    If this is not comfortably above both arms, the 'throughput' being compared is
    partly the driver's own limit and the comparison is not trustworthy."""
    best = 0.0
    at = None
    for c in ladder:
        limits = httpx.Limits(max_connections=c + 16, max_keepalive_connections=c + 16)
        async with httpx.AsyncClient(limits=limits, timeout=httpx.Timeout(30.0)) as client:
            cnt = [0]

            async def w() -> None:
                dead = time.perf_counter() + seconds
                while time.perf_counter() < dead:
                    try:
                        await client.get(f"{base}/null")
                        cnt[0] += 1
                    except Exception:                              # noqa: BLE001
                        pass

            t0 = time.perf_counter()
            await asyncio.gather(*[w() for _ in range(c)])
            el = time.perf_counter() - t0
        rps = cnt[0] / el
        if rps > best:
            best, at = rps, c
        print(f"    [null] c={c:<4} rps={rps:.1f}")
    return {"driver_ceiling_rps": round(best, 1), "at_concurrency": at}
