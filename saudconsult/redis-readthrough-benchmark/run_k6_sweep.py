"""Orchestrate the k6 concurrency sweep for ONE arm and write results/arm-<arm>.json.

Every level gets an UNCOUNTED WARMUP run followed by the measured run, so neither
arm pays a cold-connection or cold-cache penalty the other avoids. The arm is
verified against the running service's /stats before anything is measured - this
script records the arm, it does not assert it.

NOTHING IS MEASURED WITHOUT A GATE. The first thing this script does, before it
even asks the service which arm it is running, is require an existing gate record
and read its token. It does NOT mint one: a gate minted at measurement time
proves nothing about what preceded what, and the ordering - gate first, then the
run - is the whole reason the token is worth stamping. Run `python gate.py`.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import urllib.request

import canonkit
import runmeta

HERE = pathlib.Path(__file__).parent
R = HERE / "results"
LADDER = [4, 8, 16, 32, 64, 128, 256, 512]
P99_CEILING_MS = 250.0
# Digest-pinned: "latest" is a moving tag, so "the same benchmark" could
# silently mean a different load generator on a later run.
K6_IMAGE = "grafana/k6@sha256:e7eeddf1ce2361df6920d925297f487c0ba549c44be242c6a9c22f28d9b08efa"


def _win(p: pathlib.Path) -> str:
    return str(p).replace("\\", "/")


# The measured window reads a different region of the seeded sequence than the
# warmup did. Without this the warmup pre-loads exactly the keys the measured run
# is about to ask for (k6 restarts __VU/__ITER in each process), which lifted the
# cached arm's hit rate to 0.9997 - measuring the warmup, not the workload.
WARMUP_OFFSET = 0
MEASURE_OFFSET = 100_000


def k6(script: str, vus: int, duration: str, base: str, net: str,
       export: pathlib.Path | None, offset: int = 0) -> dict | None:
    cmd = ["docker", "run", "--rm", "--network", net,
           "-v", f"{_win(HERE)}:/work", "-w", "/work",
           "-e", f"BASE={base}", "-e", f"VUS={vus}", "-e", f"DURATION={duration}",
           "-e", f"OFFSET={offset}",
           K6_IMAGE, "run", "--quiet"]
    if export:
        cmd += [f"--summary-export=/work/results/{export.name}"]
    cmd += [f"/work/k6/{script}"]
    env = {"MSYS_NO_PATHCONV": "1"}
    import os
    e = dict(os.environ)
    e.update(env)
    r = subprocess.run(cmd, capture_output=True, text=True, env=e)
    if r.returncode != 0:
        print(f"    k6 FAILED (exit {r.returncode}): {r.stderr[-400:]}", file=sys.stderr)
        return None
    if export:
        return json.loads((R / export.name).read_text(encoding="utf-8"))
    return {}


def level_from_summary(s: dict, vus: int) -> dict:
    m = s["metrics"]
    d = m["http_req_duration"]
    reqs = m["http_reqs"]
    failed = m.get("http_req_failed", {}).get("value", 0.0)
    return {
        "vus": vus,
        "rps": round(reqs["rate"], 1),
        "completed": int(reqs["count"]),
        "failed_rate": failed,
        "ms": {"p50": round(d["med"], 2), "p95": round(d["p(95)"], 2),
               "p99": round(d["p(99)"], 2), "max": round(d["max"], 2),
               "avg": round(d["avg"], 2)},
        "cache_states": {k: int(m[k]["count"]) for k in ("cache_hit", "cache_miss", "cache_off")
                         if k in m},
    }


def sustained(levels: list[dict]) -> dict:
    ok = [l for l in levels if l["failed_rate"] == 0.0 and l["ms"]["p99"] <= P99_CEILING_MS]
    if not ok:
        return {"sustained_rps": None, "note": f"no level held p99 <= {P99_CEILING_MS} ms"}
    b = max(ok, key=lambda l: l["rps"])
    return {"sustained_rps": b["rps"], "at_vus": b["vus"], "p99_ms": b["ms"]["p99"],
            "p50_ms": b["ms"]["p50"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["off", "on"])
    ap.add_argument("--base", default="http://app:8000")
    ap.add_argument("--host-base", default="http://127.0.0.1:58000")
    ap.add_argument("--net", default="redis-readthrough-benchmark_default")
    ap.add_argument("--duration", default="8s")
    ap.add_argument("--warmup", default="3s")
    ap.add_argument("--null-probe", action="store_true")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    R.mkdir(exist_ok=True)

    # THE GATE COMES FIRST, before the service is even asked which arm it is.
    # require_gate exits 2 with a repair instruction when no gate record exists,
    # when it carries no token, or when it records a gate that did not pass.
    gate_token = canonkit.require_gate(R)

    with urllib.request.urlopen(f"{a.host_base}/stats") as f:
        st = json.loads(f.read())
    actual = "on" if st["cache_on"] else "off"
    if actual != a.arm:
        print(f"REFUSING: --arm={a.arm} but the service reports arm '{actual}'.",
              file=sys.stderr)
        return 2

    run_id = f"sweep-{a.arm}{a.tag}"
    output_name = f"arm-{a.arm}{a.tag}.json"
    handle = runmeta.start_run(R, run_id, gate_token, extra={
        "driver": "run_k6_sweep.py",
        "measurement": {
            "kind": "closed-loop constant-vus sweep",
            "arm": a.arm, "tag": a.tag, "ladder": LADDER,
            "duration": a.duration, "warmup": a.warmup,
            "warmup_offset": WARMUP_OFFSET, "measure_offset": MEASURE_OFFSET,
            "p99_ceiling_ms": P99_CEILING_MS,
            "load_generator_image": K6_IMAGE,
            "null_probe": bool(a.null_probe),
            "base": a.base, "host_base": a.host_base, "net": a.net,
        },
        "output": output_name,
    })
    print(f"  [{a.arm}] run {run_id} started {handle.started_at} "
          f"under gate {gate_token[:12]}")

    out: dict = {"arm": a.arm, "ladder": LADDER, "duration": a.duration,
                 "warmup": a.warmup,
                 "warmup_offset": WARMUP_OFFSET,
                 "measure_offset": MEASURE_OFFSET,
                 "workload": json.loads((R / "workload.json").read_text(encoding="utf-8"))}

    if a.null_probe:
        print("  driver headroom (/null):")
        nl = []
        for v in [64, 256, 512]:
            k6("null.js", v, a.warmup, a.base, a.net, None)
            s = k6("null.js", v, a.duration, a.base, a.net,
                   pathlib.Path(f"_null_{v}.json"))
            if s:
                lv = level_from_summary(s, v)
                nl.append(lv)
                print(f"    [null] vus={v:<4} rps={lv['rps']:<10} p99={lv['ms']['p99']}")
        out["driver_headroom"] = {"levels": nl,
                                  "driver_ceiling_rps": max(l["rps"] for l in nl) if nl else None}

    print(f"  [{a.arm}] sweep:")
    levels = []
    for v in LADDER:
        k6("sweep.js", v, a.warmup, a.base, a.net, None,
           offset=WARMUP_OFFSET)                                     # uncounted warmup
        s = k6("sweep.js", v, a.duration, a.base, a.net,
               pathlib.Path(f"_lvl_{a.arm}{a.tag}_{v}.json"), offset=MEASURE_OFFSET)
        if not s:
            continue
        lv = level_from_summary(s, v)
        levels.append(lv)
        print(f"    vus={v:<4} rps={lv['rps']:<10} p50={lv['ms']['p50']:<8} "
              f"p99={lv['ms']['p99']:<9} failed={lv['failed_rate']}")

    agg: dict[str, int] = {}
    for l in levels:
        for k, n in l["cache_states"].items():
            agg[k] = agg.get(k, 0) + n
    out["levels"] = levels
    out["sustained"] = sustained(levels)
    out["cache_states_total"] = agg

    # The run record is CLOSED before the results file is written, so the stamp
    # the results file carries is a finished run rather than an open one.
    runmeta.finish_run(handle, api_spend_usd=0.0, gpu_minutes=0.0, extra={
        "levels_measured": len(levels), "levels_offered": len(LADDER),
        "sustained": out["sustained"], "cache_states_total": agg,
    })
    out["run"] = runmeta.run_block(handle)
    (R / output_name).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"  [{a.arm}] sustained @ p99<={P99_CEILING_MS}ms: {out['sustained']}")
    print(f"  [{a.arm}] run {run_id} finished in "
          f"{out['run']['wall_seconds']:.1f}s; record {handle.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
