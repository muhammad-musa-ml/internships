"""Merge both arms, run the integrity guards, write results/results.json.

THE GUARDS ARE THE POINT. A throughput ratio is worthless on its own - a cache can
be made to look fast by serving less, by serving stale, or by both arms simply
hitting the load generator's ceiling. Each guard closes one of those and FAILS
LOUD rather than degrading to a warning.

  G1 EQUIVALENCE  every tenant observed on BOTH arms returned a byte-identical
                  response checksum, so the cached arm answers the same question.
  G2 COVERAGE     G1 is only as strong as the number of keys compared. A near-empty
                  comparison is an UNRUN check, not a pass.
  G3 HEADROOM     the load generator's do-nothing ceiling must clear the faster arm
                  by a margin. THIS GUARD ALREADY EARNED ITS KEEP: it invalidated
                  the first (Python/httpx) driver, whose own ceiling was BELOW the
                  throughput it was reporting for the service.
  G4a CACHE USED  the cache was genuinely exercised and is not impossibly perfect
                  (0 < hit rate < 1, misses > 0).
  G4b KEY BOUND   Redis holds no more distinct keys than the workload ever asked
                  for. This replaced an earlier cold-single-pass hit-rate ceiling
                  that FAILED at 0.9882 vs 0.9445 - the guard was wrong, not the
                  system, because every level has an uncounted warmup and the
                  measured window is steady-state warm. See the note at G4.
                  The 0.9882 on that line is a SUPERSEDED reading, quoted to
                  record what the wrong guard saw. It is not a live figure: the
                  run this file publishes records 0.9857.
  G5 TWO CLOCKS   client-observed throughput and the service's own handler clock
                  agree on the DIRECTION of the result.

EVERY GUARD ALSO SAYS WHAT IT EXAMINED, AND HOW LITTLE WOULD BE TOO LITTLE.
A verdict with no count beside it cannot be read: `passed: true` over three
thousand compared keys and `passed: true` over four are the same two words. So
each record carries three uniform fields besides its own domain-specific ones -
`population` (how many things it examined), `population_label` (what they were)
and `minimum_required` (the population below which its verdict would not mean
anything) - and the floors are argued for at the site of the value rather than
picked. A floor with no argument is a number someone chose, and the next reader
cannot tell it from one that was measured.

The domain-specific keys are KEPT beside the uniform three. `compared_keys` and
`required_factor` say what they are to a human; the uniform three say it in a
shape something mechanical can read. Renaming rather than adding would satisfy a
schema while destroying the meaning.

AND THE BLOCK IS VALIDATED BEFORE IT IS PUBLISHED. The line that decides the
whole run is `all(g["passed"] for g in guards)`, and `all()` over an EMPTY
sequence is True - so a guard array that was never populated would report every
guard passing. The seven appends below are unconditional, which is the only
reason that line is safe today. The validation makes it safe for a reason that
survives an edit.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import canonkit

R = pathlib.Path(__file__).parent / "results"
MIN_OVERLAP_KEYS = 500
HEADROOM_FACTOR = 1.5

# THE FLOORS THAT WERE NEVER RECORDED, AND THE ARGUMENT FOR EACH.
#
# Five of the seven guards declared no floor at all, and a floor that was never
# recorded cannot be produced by renaming a key. Each of the values below is the
# population below which that guard's VERDICT stops meaning anything - never the
# population the last run happened to have, which would be a bar set to whatever
# already cleared it.
#
# MIN_OVERLAP_KEYS (500) is NOT a new number. It is the bar this benchmark
# already declared, in G2 and in its own README, as the number of compared keys
# below which an equivalence comparison "is an unrun check, not a pass". G1a and
# G1b ARE that comparison, so the bar G2 states about them is written onto them.
# G5 takes the same bar for a different reason given at G5.
#
# MIN_HEADROOM_PROBE_LEVELS is 2, and the argument is this guard's own history.
# The generator ceiling is a MAXIMUM over do-nothing probe levels, and the defect
# G3 exists to catch was a driver whose ceiling FELL as concurrency rose - 244
# rps, degrading, while it reported 799 rps for the service. One level cannot
# distinguish a flat ceiling from the peak of a collapsing one, so two is the
# smallest population over which "the ceiling held across the concurrencies we
# ran" is even a question. Three were run.
MIN_HEADROOM_PROBE_LEVELS = 2

# MIN_REDIS_KEYS is 1, and this floor is deliberately WEAK - saying so is the
# point. G4b is one-sided: it asks whether Redis held MORE distinct keys than the
# sequence ever requested, and a fabricated or double-counted hit stream shows up
# as an excess at any key count whatever. Its discriminating power does not grow
# with the population, so the only population that breaks it is zero, where
# `0 < dbsize` already fails and the upper bound is vacuous. Any larger number
# here would have been chosen to sit under this run's 10,536 rather than derived
# from what the verdict means, which is the thing these floors exist not to be.
MIN_REDIS_KEYS = 1


def main(argv: list | None = None) -> int:
    # THIS SCRIPT TAKES NO OPTIONS AND PARSES ITS ARGUMENTS ANYWAY.
    # Without a parser an unrecognised flag is not a no-op: the argument is
    # ignored and the program does its DEFAULT thing, which here means
    # overwriting results/results.json. Someone typing `python finalize.py
    # --help` to find out what it does would have published a run instead of
    # reading about one. With a parser, `--help` prints and exits 0 and anything
    # unrecognised is a usage error - both before a single file is read.
    argparse.ArgumentParser(
        description="Merge both arms, run the integrity guards, and write "
                    "results/results.json. Takes no options; writes on success "
                    "and refuses on a malformed guard block."
    ).parse_args(argv)

    off = json.loads((R / "arm-off.json").read_text(encoding="utf-8"))
    on = json.loads((R / "arm-on.json").read_text(encoding="utf-8"))
    ck_off = json.loads((R / "ck-off.json").read_text(encoding="utf-8"))
    ck_on = json.loads((R / "ck-on.json").read_text(encoding="utf-8"))
    guards: list[dict] = []

    # ---- G1 + G2 -------------------------------------------------------------
    # TWO signals. The server-side `checksum` field is SELF-ATTESTED: the service
    # computes it and stores it inside the cached value, so comparing it across
    # arms trusts the service's own bookkeeping. `client_hashes` is recomputed by
    # collect_checksums.py from the DELIVERED payload under its own
    # canonicalization, and is the one that actually proves the arms agree.
    # Both are reported; the client-side one is the load-bearing check.
    a, b = ck_off["checksums"], ck_on["checksums"]
    shared = sorted(set(a) & set(b), key=int)
    mismatches = [k for k in shared if a[k] != b[k]]
    ha, hb = ck_off.get("client_hashes", {}), ck_on.get("client_hashes", {})
    shared_h = sorted(set(ha) & set(hb), key=int)
    mismatch_h = [k for k in shared_h if ha[k] != hb[k]]
    # The population of an equivalence guard is the OVERLAP, never either arm's
    # own count: a key present on one arm and absent from the other was never
    # compared, and counting it would report a comparison that did not happen.
    guards.append({"id": "G1a-equivalence-server-attested",
                   "passed": len(mismatches) == 0,
                   "compared_keys": len(shared), "mismatches": len(mismatches),
                   "mismatch_sample": mismatches[:5],
                   "population": len(shared),
                   "population_label": "tenant keys whose server-attested "
                                       "checksum was collected on BOTH arms",
                   "minimum_required": MIN_OVERLAP_KEYS})
    guards.append({"id": "G1b-equivalence-client-recomputed",
                   "passed": len(mismatch_h) == 0 and len(shared_h) > 0,
                   "compared_keys": len(shared_h), "mismatches": len(mismatch_h),
                   "mismatch_sample": mismatch_h[:5],
                   "note": "recomputed client-side over the delivered payload; does "
                           "not trust the service's own checksum field",
                   "population": len(shared_h),
                   "population_label": "tenant keys whose client-recomputed "
                                       "payload hash was collected on BOTH arms",
                   "minimum_required": MIN_OVERLAP_KEYS})
    guards.append({"id": "G2-coverage", "passed": len(shared_h) >= MIN_OVERLAP_KEYS,
                   "compared_keys": len(shared_h), "minimum_required": MIN_OVERLAP_KEYS,
                   "population": len(shared_h),
                   "population_label": "tenant keys whose client-recomputed "
                                       "payload hash was collected on BOTH arms"})

    # ---- G3 ------------------------------------------------------------------
    # TWO DIFFERENT FLOORS SIT ON THIS GUARD AND THEY ARE NOT THE SAME QUANTITY.
    # `required_factor` is a floor on a RATIO - how far the generator's ceiling
    # must clear the faster arm. `minimum_required` is a floor on a POPULATION -
    # how many do-nothing probe levels that ceiling was taken as the maximum
    # over. Renaming the first into the second would have satisfied a schema and
    # silently thrown away the ratio, so both are recorded.
    headroom = off.get("driver_headroom") or {}
    headroom_levels = headroom.get("levels") or []
    ceiling = headroom.get("driver_ceiling_rps")
    fastest = max(x for x in (off["sustained"]["sustained_rps"],
                              on["sustained"]["sustained_rps"]) if x is not None)
    guards.append({"id": "G3-driver-headroom",
                   "passed": ceiling is not None and ceiling >= fastest * HEADROOM_FACTOR,
                   "driver_ceiling_rps": ceiling, "fastest_arm_rps": fastest,
                   "required_factor": HEADROOM_FACTOR,
                   "measured_factor": round(ceiling / fastest, 2) if ceiling else None,
                   "population": len(headroom_levels),
                   "population_label": "do-nothing probe levels the generator's "
                                       "ceiling is the maximum over",
                   "minimum_required": MIN_HEADROOM_PROBE_LEVELS})

    # ---- G4 ------------------------------------------------------------------
    # CORRECTED. The first version compared the measured hit rate against the
    # ceiling for a COLD SINGLE PASS of the 200k sequence (0.9445) and failed at
    # 0.9882 -- a SUPERSEDED reading, quoted to record what the wrong guard saw
    # rather than as a live figure; this run records 0.9857.
    # The guard was wrong, not the system: the sweep issues ~478k counted
    # requests across 8 levels, EACH preceded by an uncounted warmup, so the
    # measured window is steady-state warm and a cold-pass ceiling is simply the
    # wrong reference. Relaxing the bound to whatever the run produced would have
    # been the real error - a guard tuned to pass measures nothing - so it is
    # replaced with two bounds that are still falsifiable:
    #   G4a the cache was genuinely exercised and is not impossibly perfect
    #       (0 < hit rate < 1, and misses > 0 - a run with zero misses would mean
    #       the cache was pre-seeded outside the measurement, which it was not);
    #   G4b Redis cannot hold more distinct keys than the workload ever asked for.
    #       This one is the non-vacuous half: a fabricated or double-counted hit
    #       stream would show up as a key count the sequence cannot explain.
    st = on.get("cache_states_total", {})
    hits, misses = st.get("cache_hit", 0), st.get("cache_miss", 0)
    total_counted = hits + misses
    measured = hits / total_counted if total_counted else 0.0
    distinct_requested = on["workload"]["distinct_tenants_touched"]
    dbsize = json.loads((R / "redis-dbsize.json").read_text(encoding="utf-8"))["dbsize"]

    # G4a's FLOOR IS DERIVED FROM THE SEQUENCE, not typed. It is one complete
    # pass of whatever sequence was replayed. The argument is in the guard's own
    # record: it carries `cold_single_pass_ceiling_for_reference`, a figure
    # defined over every request after the first for a given key across the WHOLE
    # sequence. Measure fewer lookups than that and the window has not seen the
    # sequence's repetition structure, so the reference printed beside the rate
    # describes a different population from the rate itself - and a hit rate
    # compared against a ceiling for some other population means nothing. This
    # run counted 505,227 lookups against a 200,000-request sequence.
    sequence_requests = on["workload"]["requests"]
    guards.append({"id": "G4a-cache-exercised",
                   "passed": 0.0 < measured < 1.0 and misses > 0,
                   "measured_hit_rate": round(measured, 4),
                   "hits": hits, "misses": misses,
                   "window": "steady-state warm (each level has an uncounted warmup)",
                   "cold_single_pass_ceiling_for_reference": on["workload"][
                       "theoretical_max_hit_rate"],
                   "population": total_counted,
                   "population_label": "counted cache lookups in the measured "
                                       "windows (hits + misses)",
                   "minimum_required": sequence_requests})
    guards.append({"id": "G4b-keys-bounded-by-workload",
                   "passed": 0 < dbsize <= distinct_requested,
                   "redis_dbsize_after_run": dbsize,
                   "distinct_tenants_in_sequence": distinct_requested,
                   "population": dbsize,
                   "population_label": "distinct keys Redis held when the run "
                                       "ended",
                   "minimum_required": MIN_REDIS_KEYS})

    # ---- G5 ------------------------------------------------------------------
    so, sn = off["sustained"], on["sustained"]
    client_delta = sn["sustained_rps"] - so["sustained_rps"]
    srv_off, srv_on = ck_off["server_us"]["p50"], ck_on["server_us"]["p50"]
    server_delta = srv_off - srv_on          # positive == cached arm does less work

    # G5'S POPULATION IS THE WEAKER CLOCK'S, because a direction claim is only as
    # strong as the thinner of the two things being compared. The client leg
    # rests on the counted requests of each arm's sustained level - 54,156 and
    # 75,986 in this run - while the server leg rests on the sampled responses
    # that carry a handler-time reading, 3,000 per arm. The server leg is the
    # smaller by eighteen times, so it is the one recorded, and the smaller of
    # the two arms is taken rather than their sum.
    #
    # Its floor is MIN_OVERLAP_KEYS for a reason that is not a coincidence: the
    # handler-time readings and the equivalence keys come out of the SAME
    # sampling pass, one per delivered response. The bar this benchmark already
    # declares for that pass to mean anything is the bar that applies here. It is
    # deliberately not a statistical power calculation, which would be a number
    # chosen at this keyboard rather than one this repository already states.
    server_samples = min(int(ck_off.get("keys_collected", 0)),
                         int(ck_on.get("keys_collected", 0)))
    guards.append({"id": "G5-two-clocks",
                   "passed": (client_delta > 0) == (server_delta > 0),
                   "client_rps_delta": round(client_delta, 1),
                   "server_us_p50_off": srv_off, "server_us_p50_on": srv_on,
                   "server_side_speedup": round(srv_off / srv_on, 2) if srv_on else None,
                   "population": server_samples,
                   "population_label": "responses sampled on the weaker arm, "
                                       "each carrying one server-side "
                                       "handler-time reading",
                   "minimum_required": MIN_OVERLAP_KEYS})

    ratio = sn["sustained_rps"] / so["sustained_rps"]
    summary = {
        "uncached_sustained_rps": so["sustained_rps"],
        "cached_sustained_rps": sn["sustained_rps"],
        "throughput_ratio": round(ratio, 3),
        "p99_ceiling_ms": 250.0,
        "uncached_p99_ms_at_reported_point": so["p99_ms"],
        "cached_p99_ms_at_reported_point": sn["p99_ms"],
        "uncached_at_vus": so["at_vus"], "cached_at_vus": sn["at_vus"],
        "server_us_p50_uncached": srv_off, "server_us_p50_cached": srv_on,
        "server_side_ratio": round(srv_off / srv_on, 2) if srv_on else None,
        "measured_cache_hit_rate": round(measured, 4),
        "cache_hit_rate_window": "steady-state warm",
        "driver_ceiling_rps": ceiling,
    }
    all_passed = all(g["passed"] for g in guards)
    record = {"summary": summary, "guards": guards,
              "all_guards_passed": all_passed,
              "arm_off": off, "arm_on": on,
              "checksum_pass": {"off": {k: v for k, v in ck_off.items() if k != "checksums"},
                                "on": {k: v for k, v in ck_on.items() if k != "checksums"}}}

    # VALIDATED BEFORE IT IS PUBLISHED, AND REFUSED RATHER THAN WRITTEN.
    # `all_passed` above is the line this whole file exists to produce, and over
    # an empty guards list it is True. The seven appends are unconditional, so
    # that cannot happen today - but "cannot happen today" is a property of the
    # code above rather than of the record, and it is one edit away from being
    # false. This asks the record itself: at least one guard, each with an id, a
    # verdict, a population, a label for it and a floor, no duplicate ids, no
    # guard passing under its own floor, and a summary flag that agrees with the
    # records it summarises.
    #
    # Nothing is written on a violation. An invalid record on disk is worse than
    # none: the next reader has no way to tell it from a valid one without
    # re-running this, which is the thing they were trying to avoid.
    violations = canonkit.validate_guards(record)
    if violations:
        print("%s the guard block this run assembled does not satisfy the guard "
              "record shape (%d violation(s)), so it has NOT been written:"
              % (canonkit.REFUSAL_PREFIX, len(violations)), file=sys.stderr)
        for violation in violations:
            print("  %s" % violation, file=sys.stderr)
        print("  REPAIR: this is a defect in finalize.py, not in the run. Every "
              "guard must carry id, passed, population, population_label and "
              "minimum_required.", file=sys.stderr)
        return 3

    (R / "results.json").write_text(json.dumps(record, indent=2),
                                    encoding="utf-8")

    print("=== SUMMARY ===")
    for k, v in summary.items():
        print(f"  {k} = {v}")
    print("\n=== GUARDS ===")
    for g in guards:
        print(f"  [{'PASS' if g['passed'] else 'FAIL'}] {g['id']}  "
              + ", ".join(f"{k}={v}" for k, v in g.items() if k not in ("id", "passed")))
    print(f"\nALL GUARDS PASSED: {all_passed}")
    return 0 if all_passed else 3


if __name__ == "__main__":
    raise SystemExit(main())
