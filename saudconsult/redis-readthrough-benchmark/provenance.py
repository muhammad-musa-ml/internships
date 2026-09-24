"""Emit an immutable manifest binding code, workload, images and host to a result.

WHY THIS EXISTS - a Critical finding of adversarial review. The result file
recorded no way to tell WHICH code, WHICH seeded sequence, WHICH container images
or WHICH service configuration produced it. Two consequences, both real:

  * a later run silently overwrote the earlier run's raw k6 exports, because the
    `--tag` option renamed only the final aggregate and not the per-level files,
    so the original headline could no longer be re-aggregated from raw evidence;
  * `grafana/k6:latest` is a moving tag - "the same benchmark" could quietly mean
    a different load generator next week.

This module records the sha256 of every source file, the sha256 of the exact
sequence used, the resolved image DIGESTS (not tags), and the service's own
reported configuration - so a result can be checked against the thing that made it
rather than trusted.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import urllib.request

HERE = pathlib.Path(__file__).parent
R = HERE / "results"
SOURCES = [
    "app/main.py", "app/seed.py", "app/Dockerfile", "docker-compose.yml",
    "benchlib/workload.py", "benchlib/driver.py", "k6/sweep.js", "k6/null.js",
    "k6/rate.js", "run_k6_sweep.py", "run_rate_test.py", "collect_checksums.py",
    "finalize.py", "make_sequence.py",
]


def sha256_file(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def image_digest(tag: str) -> str | None:
    try:
        out = subprocess.run(
            ["docker", "inspect", "--format", "{{index .RepoDigests 0}}", tag],
            capture_output=True, text=True, timeout=60)
        return out.stdout.strip() or None
    except Exception:                                              # noqa: BLE001
        return None


def main() -> int:
    host_base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:58000"
    man: dict = {
        "sources": {s: sha256_file(HERE / s) for s in SOURCES if (HERE / s).exists()},
        "images": {t: image_digest(t) for t in
                   ("postgres:16.4", "redis:7.4-alpine", "grafana/k6:latest")},
        "host": {"cpu_count": os.cpu_count(), "platform": sys.platform},
    }
    seq = R / "sequence.json"
    if seq.exists():
        man["sequence"] = {"sha256": sha256_file(seq), "bytes": seq.stat().st_size,
                           "description": json.loads(
                               (R / "workload.json").read_text(encoding="utf-8"))}
    try:
        with urllib.request.urlopen(f"{host_base}/config-info", timeout=5) as f:
            man["service_config"] = json.loads(f.read())
    except Exception as exc:                                       # noqa: BLE001
        man["service_config"] = {"error": f"{exc.__class__.__name__}: {exc}",
                                 "note": "service not reachable when the manifest was cut"}
    (R / "provenance.json").write_text(json.dumps(man, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in man.items() if k != "sources"}, indent=2))
    print(f"[provenance] {len(man['sources'])} source files hashed -> results/provenance.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
