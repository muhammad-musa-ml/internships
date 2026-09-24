"""Collect per-tenant response checksums + the SERVER-SIDE clock for one arm.

Two jobs k6 is the wrong tool for:

  1. EQUIVALENCE (G1). The cached arm must return byte-identical answers to the
     uncached one. That needs the response BODY per key, not an aggregate.
  2. THE SECOND CLOCK (G5). k6 reports client-observed duration only. The service
     stamps its own handler time (`server_us`); if the two clocks disagreed about
     the DIRECTION of the result, the result would not be trustworthy - the
     discipline PH-A used with Elasticsearch's `took`.

Run at LOW concurrency deliberately: this pass is not measuring throughput, so the
Python client's modest ceiling (the thing that invalidated the first driver) is
irrelevant here. Correctness sampling and load generation are separate jobs.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import pathlib
import statistics
import sys

import httpx

HERE = pathlib.Path(__file__).parent
R = HERE / "results"
CONCURRENCY = 8


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["off", "on"])
    ap.add_argument("--base", default="http://127.0.0.1:58000")
    ap.add_argument("--keys", type=int, default=3000)
    a = ap.parse_args()

    async with httpx.AsyncClient(timeout=30.0) as c:
        st = (await c.get(f"{a.base}/stats")).json()
    actual = "on" if st["cache_on"] else "off"
    if actual != a.arm:
        print(f"REFUSING: --arm={a.arm} but the service reports arm '{actual}'.",
              file=sys.stderr)
        return 2

    seq = json.loads((R / "sequence.json").read_text(encoding="utf-8"))
    # The MOST-REQUESTED distinct keys: the ones that actually carry the workload,
    # so equivalence is checked where it matters rather than on a random tail.
    from collections import Counter
    keys = [k for k, _ in Counter(seq).most_common(a.keys)]

    checksums: dict[str, str] = {}
    client_hashes: dict[str, str] = {}
    server_us: list[int] = []
    errors: list[str] = []
    sem = asyncio.Semaphore(CONCURRENCY)

    async with httpx.AsyncClient(timeout=30.0,
                                 limits=httpx.Limits(max_connections=CONCURRENCY + 4)) as client:
        async def one(tid: int) -> None:
            async with sem:
                try:
                    r = await client.get(f"{a.base}/config/{tid}")
                    if r.status_code != 200:
                        errors.append(f"{tid}: HTTP {r.status_code}")
                        return
                    b = r.json()
                    # TWO INDEPENDENT equivalence signals, because one of them is
                    # self-attested. `b["checksum"]` is computed by the SERVER and
                    # stored INSIDE the cached value, so comparing it across arms
                    # trusts the service's own bookkeeping. The client-side hash
                    # below is recomputed here from the delivered `payload`, under
                    # this process's own canonicalization, and is what actually
                    # proves the two arms delivered the same data.
                    checksums[str(tid)] = b["checksum"]
                    client_hashes[str(tid)] = hashlib.sha256(
                        json.dumps(b["payload"], sort_keys=True,
                                   separators=(",", ":")).encode()).hexdigest()
                    server_us.append(int(b["server_us"]))
                except Exception as exc:                            # noqa: BLE001
                    errors.append(f"{tid}: {exc.__class__.__name__}")

        await asyncio.gather(*[one(t) for t in keys])

    s = sorted(server_us)

    def pct(q: float) -> int:
        if not s:
            return -1
        k = max(0, min(len(s) - 1, int(round(q / 100.0 * len(s) + 0.5)) - 1))
        return s[k]

    out = {
        "arm": a.arm,
        "keys_requested": len(keys),
        "keys_collected": len(checksums),
        "errors": len(errors),
        "error_sample": errors[:5],
        "server_us": {"p50": pct(50), "p95": pct(95), "p99": pct(99),
                      "mean": int(statistics.fmean(s)) if s else -1},
        "checksums": checksums,
        "client_hashes": client_hashes,
    }
    p = R / f"ck-{a.arm}.json"
    p.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"[ck-{a.arm}] collected {len(checksums)}/{len(keys)} keys, errors={len(errors)}, "
          f"server_us p50={out['server_us']['p50']} p99={out['server_us']['p99']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
