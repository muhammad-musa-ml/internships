"""Run ONE arm's sweep with the RETIRED Python driver and write results/arm-<arm>.json.

The arm is whatever the running service was started with (CACHE=off|on); this
script does not choose it, it RECORDS it - reading /stats back from the service so
the file cannot claim an arm the service was not actually running.

THIS DRIVER IS RETIRED FOR THROUGHPUT, and the reason is recorded in the results
rather than in a changelog: its own do-nothing ceiling measured 244 rps while it
was reporting 799 rps for the service, so above roughly 8 connections it was
measuring itself. The headroom guard caught that. It survives for the
low-concurrency correctness pass, where throughput is irrelevant.

It writes the SAME results/arm-<arm>.json the k6 sweep writes. Running it after
a k6 sweep therefore REPLACES that sweep's results file with numbers from the
retired driver. Its run record is keyed separately (`bench-<arm>` rather than
`sweep-<arm>`), so the two runs remain distinguishable even when their output
files do not.

NOTHING IS MEASURED WITHOUT A GATE. The first thing this script does, before it
even asks the service which arm it is running, is require an existing gate record
and read its token. It does NOT mint one: a gate minted at measurement time
proves nothing about what preceded what. Run `python gate.py`.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import sys

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import canonkit  # noqa: E402
import runmeta  # noqa: E402
from benchlib import driver, workload  # noqa: E402

RESULTS = pathlib.Path(__file__).parent / "results"
LADDER = [1, 2, 4, 8, 16, 32, 64, 128, 256]


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["off", "on"])
    ap.add_argument("--base", default="http://127.0.0.1:58000")
    ap.add_argument("--tenants", type=int, default=20000)
    ap.add_argument("--requests", type=int, default=200000)
    ap.add_argument("--seconds", type=float, default=6.0)
    ap.add_argument("--warmup", type=float, default=2.0)
    ap.add_argument("--null-probe", action="store_true")
    a = ap.parse_args()
    RESULTS.mkdir(exist_ok=True)

    # THE GATE COMES FIRST, before the service is even asked which arm it is.
    # require_gate exits 2 with a repair instruction when no gate record exists,
    # when it carries no token, or when it records a gate that did not pass.
    gate_token = canonkit.require_gate(RESULTS)

    async with httpx.AsyncClient(timeout=30.0) as c:
        st = (await c.get(f"{a.base}/stats")).json()
        actual = "on" if st["cache_on"] else "off"
        if actual != a.arm:
            print(f"REFUSING: --arm={a.arm} but the running service reports cache_on="
                  f"{st['cache_on']} (arm '{actual}'). Recreate the app with the right "
                  f"CACHE value.", file=sys.stderr)
            return 2
        await c.post(f"{a.base}/reset-stats")

    seq = workload.build_sequence(a.requests, a.tenants)
    desc = workload.describe(seq, a.tenants)
    print(f"[{a.arm}] workload: {desc['requests']} reqs over "
          f"{desc['distinct_tenants_touched']} distinct tenants; top-1% share="
          f"{desc['share_top_1pct_of_tenants']}; theoretical max hit rate="
          f"{desc['theoretical_max_hit_rate']}")

    run_id = f"bench-{a.arm}"
    output_name = f"arm-{a.arm}.json"
    handle = runmeta.start_run(RESULTS, run_id, gate_token, extra={
        "driver": "run_benchmark.py (retired Python driver)",
        "measurement": {
            "kind": "closed-loop asyncio/httpx sweep",
            "arm": a.arm, "ladder": LADDER,
            "seconds_per_level": a.seconds, "warmup_seconds": a.warmup,
            "tenants": a.tenants, "requests": a.requests,
            "null_probe": bool(a.null_probe), "base": a.base,
        },
        "output": output_name,
    })
    print(f"[{a.arm}] run {run_id} started {handle.started_at} "
          f"under gate {gate_token[:12]}")

    out: dict = {"arm": a.arm, "workload": desc, "ladder": LADDER,
                 "seconds_per_level": a.seconds, "warmup_seconds": a.warmup}

    if a.null_probe:
        print(f"[{a.arm}] driver headroom probe (/null):")
        out["driver_headroom"] = await driver.null_ceiling(a.base, [64, 128, 256], a.seconds)

    print(f"[{a.arm}] sweep:")
    levels = await driver.sweep(a.base, seq, LADDER, a.seconds, a.warmup, collect_ck=True)
    merged_ck: dict[str, str] = {}
    for lvl in levels:
        for k, v in lvl.pop("_checksums", {}).items():
            merged_ck[str(k)] = v
    agg_states: dict[str, int] = {}
    for lvl in levels:
        for k, v in lvl.get("cache_states", {}).items():
            agg_states[k] = agg_states.get(k, 0) + v
    out["levels"] = levels
    out["sustained"] = driver.sustained_at_ceiling(levels)
    out["cache_states_total"] = agg_states
    out["checksums"] = merged_ck

    async with httpx.AsyncClient(timeout=30.0) as c:
        out["service_stats_after"] = (await c.get(f"{a.base}/stats")).json()

    # The run record is CLOSED before the results file is written, so the stamp
    # the results file carries is a finished run rather than an open one.
    runmeta.finish_run(handle, api_spend_usd=0.0, gpu_minutes=0.0, extra={
        "levels_measured": len(levels), "levels_offered": len(LADDER),
        "sustained": out["sustained"], "cache_states_total": agg_states,
    })
    out["run"] = runmeta.run_block(handle)
    p = RESULTS / output_name
    p.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"[{a.arm}] sustained @ p99<=250ms: {out['sustained']}")
    print(f"[{a.arm}] wrote {p}")
    print(f"[{a.arm}] run {run_id} finished in "
          f"{out['run']['wall_seconds']:.1f}s; record {handle.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
