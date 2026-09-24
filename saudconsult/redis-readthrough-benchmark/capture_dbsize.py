"""Read Redis's distinct key count at the end of a run, and write it down.

WHY THIS FILE EXISTS, AND WHAT WAS WRONG BEFORE IT.
`results/redis-dbsize.json` is the population G4b's whole verdict rests on:
`finalize.py` reads its `dbsize` and asks whether Redis held more distinct keys
than the replayed sequence ever requested. Until now NOTHING in this repository
wrote that file. The committed value was a number typed at a console after a run
in July, carrying no machine timestamp, no gate token, and no record of the
command that produced it - only the prose `"captured": "after the offset-corrected
cached-arm sweep"`.

That is worse than it sounds, and the reason is not tidiness. A file nothing
reproduces does not go stale loudly: it sits there and is READ. A later run that
regenerates every other results file leaves this one untouched, and G4b then
compares a fresh Redis against a key count from a different month and reports
PASS over a population it never measured. A guard that cannot fail is not a
guard.

So the capture is a program, it runs under the same gate as every other
measurement, and it records what it did:

  * the EXACT argv it ran, so the number can be reproduced rather than believed;
  * a machine-written timestamp in both local and UTC form, from the same clock
    every other record here uses;
  * the gate token the run was authorised by, which is what ties this number to
    the measurements it is published beside;
  * the PREVIOUS record, verbatim, under `previous`. A re-capture that silently
    replaced the old value would destroy the only evidence that the two describe
    different runs. Both are printed side by side on every branch.

A NUMBER THAT DOES NOT PARSE IS A REFUSAL, NEVER A GUESS.
`redis-cli DBSIZE` is asked for one integer. If the reply is not exactly that -
the container gone, the engine down, an error string on stdout - this exits 2
with a REPAIR clause and writes nothing. Writing a zero would be the worst
available outcome: `0 < dbsize` is G4b's lower bound, so a failed probe recorded
as zero would fail the guard for a reason that has nothing to do with the cache,
and a reader would be looking for a cache defect that was never there.

WHEN TO RUN IT: after the cached arm has finished everything it is going to do,
immediately before `finalize.py`. The label the guard prints is "distinct keys
Redis held when the run ended", and that is only true if this is the last thing
that touches Redis.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

import canonkit
import runmeta

HERE = pathlib.Path(__file__).parent
R = HERE / "results"
OUTPUT_NAME = "redis-dbsize.json"

# The compose service container. Named rather than discovered: a probe that
# searches for "something that looks like redis" would happily read a DIFFERENT
# Redis if one were running, and this machine has had several.
DEFAULT_CONTAINER = "redis-readthrough-benchmark-redis-1"
DBSIZE_TIMEOUT_SECONDS = 30


def read_dbsize(container, runner=None):
    """Return (dbsize, argv, raw) or raise ValueError with what it saw instead."""
    argv = ["docker", "exec", container, "redis-cli", "DBSIZE"]
    runner = runner or _default_runner
    raw = runner(argv)
    text = str(raw).strip()
    # redis-cli prints a bare integer when it is not attached to a terminal and
    # "(integer) N" when it is. Both are accepted; anything else is refused,
    # because a lenient parse over an error string is how a diagnostic becomes a
    # measurement.
    token = text.split()[-1] if text else ""
    if not token.isdigit():
        raise ValueError(
            "DBSIZE did not reply with an integer. Read %r from %s"
            % (text[:200], " ".join(argv)))
    return int(token), argv, text


def _default_runner(argv):
    completed = subprocess.run(argv, capture_output=True, text=True,
                               timeout=DBSIZE_TIMEOUT_SECONDS, shell=False)
    if completed.returncode != 0:
        raise OSError("exited %d: %s"
                      % (completed.returncode,
                         (completed.stderr or completed.stdout or "").strip()[-300:]))
    return completed.stdout


def previous_record(path):
    """The record this capture supersedes, or None. Never an exception."""
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except Exception:                                           # noqa: BLE001
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Read Redis's distinct key count at the end of a run and "
                    "write results/redis-dbsize.json, carrying the command that "
                    "produced it, a machine timestamp, the gate token, and the "
                    "record it supersedes.")
    ap.add_argument("--container", default=DEFAULT_CONTAINER)
    a = ap.parse_args(argv)
    R.mkdir(exist_ok=True)

    # THE GATE COMES FIRST, exactly as it does for the three measuring drivers.
    # This number is published beside their numbers and is read by the same
    # finalisation step, so it is authorised by the same record or not taken.
    gate_token = canonkit.require_gate(R)

    out_path = R / OUTPUT_NAME
    before = previous_record(out_path)
    before_value = before.get("dbsize") if isinstance(before, dict) else None

    handle = runmeta.start_run(R, "dbsize", gate_token, extra={
        "driver": "capture_dbsize.py",
        "measurement": {
            "kind": "point read of Redis's distinct key count",
            "container": a.container,
        },
        "output": OUTPUT_NAME,
    })

    try:
        dbsize, probe_argv, raw = read_dbsize(a.container)
    except Exception as exc:                                    # noqa: BLE001
        runmeta.finish_run(handle, api_spend_usd=0.0, gpu_minutes=0.0, extra={
            "error": "%s: %s" % (exc.__class__.__name__, exc),
            "dbsize": None,
        })
        print("DBSIZE           DID-NOT-RUN found=0 checked=0 of 1 not-examined=1 "
              "floor=1 waived=0  could not read a key count from %s" % a.container,
              file=sys.stderr)
        print("REFUSING: %s: %s" % (exc.__class__.__name__, exc), file=sys.stderr)
        print("REPAIR: bring the compose stack up (`docker compose up -d redis`) "
              "and re-run `python capture_dbsize.py`. Nothing was written, so the "
              "previous record (dbsize=%r) is still on disk and still describes "
              "the run it was taken from." % (before_value,), file=sys.stderr)
        return 2

    record = {
        "schema": "readthrough/dbsize/1",
        "schema_version": canonkit.SCHEMA_VERSION,
        # THE KEY finalize.py READS. Kept first and kept named `dbsize`: the
        # fields around it are new, the contract is not.
        "dbsize": dbsize,
        "container": a.container,
        "probe": " ".join(probe_argv),
        "raw_reply": raw,
        "captured": "read by capture_dbsize.py after the cached arm finished, "
                    "immediately before finalize.py",
        "previous": before,
    }

    runmeta.finish_run(handle, api_spend_usd=0.0, gpu_minutes=0.0, extra={
        "dbsize": dbsize, "previous_dbsize": before_value,
    })
    record["run"] = runmeta.run_block(handle)
    canonkit.atomic_write_json(str(out_path), record)

    # BOTH NUMBERS, ON EVERY BRANCH. A re-capture that printed only the new value
    # would make a stale file and a genuine reproduction look identical, which is
    # the exact confusion this program was written to end.
    moved = "unchanged" if before_value == dbsize else "moved"
    print("DBSIZE           PASS        found=1 checked=1 of 1 not-examined=0 "
          "floor=1 waived=0  previous=%r new=%d (%s)"
          % (before_value, dbsize, moved))
    print("  probe   %s" % " ".join(probe_argv))
    print("  gate    %s" % gate_token[:12])
    print("  record  %s" % handle.path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
