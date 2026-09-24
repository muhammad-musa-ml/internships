"""Emit the seeded tenant sequence + its description, shared by BOTH arms and by
both tools (k6 for load, the Python checksum pass for equivalence)."""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from benchlib import workload  # noqa: E402

R = pathlib.Path(__file__).parent / "results"
R.mkdir(exist_ok=True)

n_req = int(sys.argv[1]) if len(sys.argv) > 1 else 200000
n_ten = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
zipf = float(sys.argv[3]) if len(sys.argv) > 3 else 1.2

seq = workload.build_sequence(n_req, n_ten, zipf_a=zipf)
desc = workload.describe(seq, n_ten)
desc["zipf_a"] = zipf
(R / "sequence.json").write_text(json.dumps(seq), encoding="utf-8")
(R / "workload.json").write_text(json.dumps(desc, indent=2), encoding="utf-8")
print(json.dumps(desc, indent=2))
print(f"[seq] wrote {R / 'sequence.json'} ({len(seq)} entries)")
