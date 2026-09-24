"""THE ONLY PLACE A NUMBER THIS BENCHMARK PUBLISHES IS AUTHORED.

Every figure the repository ships is computed here, from the per-run JSON
records the measuring scripts wrote, and written to results/figures.json.
Nothing else may author a number: the documents are RENDERED from this file and
the figure carries its own population, its population label and the list of
records it came from, so a reader can walk back to the machine.

    per-run records -> select -> count -> figure -> rendered

WHY THIS FILE HAS ITS OWN READER RATHER THAN THE SHARED ONE
-----------------------------------------------------------
The shared contract reads `results/items/*.json`, one record per replayed item.
This benchmark has never written per-item records and does not need to: its
measuring scripts write one record PER RUN, flat under `results/`, each holding
an `arm`, the ladder of `levels[]` it offered, and the level it settled on as
`capacity_at_p99_ceiling`. So the three REFUSALS and the figure record are
copied from that contract exactly; the reader is written for this shape.

THE POPULATION IS THE HARD PART, NOT THE ARITHMETIC
---------------------------------------------------
`results/` holds records from TWO campaigns plus one withdrawn run:

  * the July campaign, whose per-run records survive because the re-run used
    the same naming convention and overwrote only some of them;
  * the 2026-09-18 re-run, which is the record (see RUN-RECORD.md);
  * three files belonging to the milder-skew run RETRACTED on 2026-07-31 --
    withdrawn, never deleted (see RETRACTION-SWEEP.md).

A derivation that walked `results/*.json` and folded in what it found would
span two campaigns and a withdrawn run, and nothing downstream could detect it.
What distinguishes them is the GATE TOKEN, not the filename: every run of the
accepted campaign stamps `run.gate_token`, and no July record carries one.

So every file directly under `results/` is classified, and EVERY EXCLUSION IS
COUNTED AND GIVEN ITS REASON, printed beside the derivation. The counts close
as an identity -- excluded plus derived-from equals listed -- which is enforced
by the shared reporter rather than asserted in prose, so a record that is
neither used nor accounted for cannot exist.

NOTHING IS DELETED. A superseded machine record is the BEFORE side a
measurement-wins programme needs, and a withdrawn one is the evidence of what
was withdrawn. They stay tracked, and they stay excluded with their reason.

THE TOKEN IS NESTED, AND READING THE TOP LEVEL GETS A WRONG ANSWER
------------------------------------------------------------------
A per-run record carries its token at `run.gate_token`. A scan of TOP-LEVEL
keys finds only `results/gate.json`'s own `run_token` and reports that ONE file
of 136 carries a token -- a false answer with a real answer's shape. That
mistake was actually made here before a substring search corrected it, which is
why `record_gate_token()` is a named function with a test pointed at it.

WHAT IS DELIBERATELY NOT REFUSED: population 1. The open-loop ladder runs each
offered rate ONCE, so a figure reading one level's tail latency has a
population of 1 and says so in its label. Requiring an excuse for every n=1
figure would be a constraint nobody asked for. What IS refused is a THRESHOLD
claim on fewer than three replicates, and a population of zero.

BYTE STABILITY. This file stamps no wall clock. `dated_at` is the moment the
last measurement it rests on FINISHED, read from that run's own record, so
re-deriving over unchanged records produces byte-identical output and
results/figures.json can be hash-pinned. Changing one recorded number still
changes the bytes; both directions are asserted in tests/test_derive.py.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import canonkit

SCHEMA = "canonkit/figures/1"

# What this file writes, and therefore the one name in results/ that is never
# part of its own input population. See load_flat_records().
OUTPUT_NAME = "figures.json"

# The key the hit-rate cross-check reads. Named here rather than typed in the
# test, so the two cannot drift apart silently.
HIT_RATE_KEY = "cache_hit_rate_pct"

# The exclusion reasons, in the order they print. Each is a MECHANICAL property
# of the record, not a judgement about it, and each is exactly true of every
# file it holds.
WITHDRAWN = "withdrawn by retraction 13"
GENERATOR_RAW = "the load generator's raw per-level output"
NOT_A_RUN = "not a per-run measurement record"
SUPERSEDED = "superseded by the re-run"
EXCLUSION_ORDER = (SUPERSEDED, WITHDRAWN, GENERATOR_RAW, NOT_A_RUN)

# k6 writes its own per-level summary beside the run record. Its top-level key
# set is exactly these two and nothing else, which is what identifies it.
GENERATOR_RAW_KEYS = frozenset(("metrics", "root_group"))


class Refusal(Exception):
    """Raised only by helpers that cannot reach canonkit.die directly."""


# ---------------------------------------------------------------------------
# reading a record
# ---------------------------------------------------------------------------


def record_gate_token(record):
    """THIS record's gate token, read from where the run recorder writes it.

    `run.gate_token` first, because that is the per-run shape. The flat
    `gate_token` fallback is what the records under results/raw/ use, so the
    same function answers for both without a second spelling.
    """
    if not isinstance(record, dict):
        return None
    run = record.get("run")
    if isinstance(run, dict):
        token = run.get("gate_token")
        if isinstance(token, str) and token:
            return token
    token = record.get("gate_token")
    return token if isinstance(token, str) and token else None


def run_block(record):
    run = record.get("run") if isinstance(record, dict) else None
    return run if isinstance(run, dict) else {}


def is_withdrawn(record):
    """Marked by an earlier plan with `aggregate: false`. Read the MARKER, not a name.

    A hardcoded list of three filenames would go quietly wrong the first time a
    fourth record is withdrawn, and the marker is the thing the retraction
    sweep actually wrote. A retracted run's records are EVIDENCE of what was
    retracted, so they are excluded and counted rather than deleted.
    """
    if not isinstance(record, dict):
        return False
    block = record.get("withdrawn")
    return isinstance(block, dict) and block.get("aggregate") is False


def is_generator_raw(record):
    return isinstance(record, dict) and set(record) == GENERATOR_RAW_KEYS


def is_measurement(record):
    """A per-run measurement record: an arm, and the ladder of levels it ran."""
    return (isinstance(record, dict)
            and isinstance(record.get("arm"), str)
            and isinstance(record.get("levels"), list))


def load_flat_records(results_dir):
    """Every JSON file DIRECTLY under results/, as (name, payload) pairs.

    NOT recursive, and that is a decision rather than an oversight.
    results/raw/ holds one RUN record per measurement -- the provenance index,
    carrying timestamps, the driver and the contention census. Its records
    restate the same `capacity_at_p99_ceiling` the flat records carry, so
    walking it too would double-count every ladder run. It is read for the run
    identity below and never as a figure population.

    THE DERIVATION'S OWN OUTPUT IS NOT ONE OF ITS INPUTS, and leaving it in the
    population is not a harmless over-count: `figures.json` does not exist on
    the first run and does on every later one, so the listed population would
    step from N to N+1 the moment the file was first written and the record's
    bytes would move for a reason that has nothing to do with any measurement.
    MEASURED, not supposed -- the byte-stability test caught exactly that.
    """
    pairs = []
    for path in sorted(glob.glob(os.path.join(str(results_dir), "*.json"))):
        name = os.path.basename(path)
        if name == OUTPUT_NAME:
            continue
        with open(path, "rb") as handle:
            pairs.append((name, json.loads(handle.read().decode("utf-8"))))
    return pairs


# ---------------------------------------------------------------------------
# the census
# ---------------------------------------------------------------------------


class Census(object):
    """What was derived from, what was not, and why -- with the counts.

    `excluded` is a list of (reason, names) in EXCLUSION_ORDER rather than a
    dict, so the printed line cannot re-order between runs.
    """

    def __init__(self, total, listed, derived, buckets, records):
        self.total = total
        self.listed = listed
        self.derived = derived
        self.records = records
        self.excluded = [(reason, sorted(buckets.get(reason, [])))
                         for reason in EXCLUSION_ORDER]

    @property
    def excluded_count(self):
        return sum(len(names) for _reason, names in self.excluded)

    def exclusion_line(self):
        parts = ["%s, %d records" % (reason, len(names))
                 for reason, names in self.excluded]
        return ("[derive] excluded %d of %d record(s): %s"
                % (self.excluded_count, self.total, "; ".join(parts)))


def classify(results_dir, token):
    """Sort every flat results record into exactly one class.

    Order matters and is argued: WITHDRAWN first, because a withdrawn record is
    also a July record and the retraction is the reason that matters; then the
    two structural classes, which say what a file IS; then the token, which is
    the only thing that separates two campaigns of the same shape.
    """
    buckets = {}
    derived = []
    listed = []
    records = {}
    for name, record in load_flat_records(results_dir):
        listed.append(name)
        records[name] = record
        if is_withdrawn(record):
            buckets.setdefault(WITHDRAWN, []).append(name)
        elif is_generator_raw(record):
            buckets.setdefault(GENERATOR_RAW, []).append(name)
        elif not is_measurement(record):
            buckets.setdefault(NOT_A_RUN, []).append(name)
        elif record_gate_token(record) != token:
            buckets.setdefault(SUPERSEDED, []).append(name)
        else:
            derived.append(name)
    return Census(len(listed), sorted(listed), sorted(derived), buckets,
                  records)


# ---------------------------------------------------------------------------
# selecting the records one declared figure rests on
# ---------------------------------------------------------------------------


def select_records(spec, census):
    """The derived records this spec names, as (name, payload), name-sorted."""
    selector = spec.get("select") or {}
    chosen = []
    for name in census.derived:
        record = census.records[name]
        run_id = run_block(record).get("run_id")
        if "run_id" in selector and run_id != selector["run_id"]:
            continue
        if "run_id_prefix" in selector and not str(run_id).startswith(
                selector["run_id_prefix"]):
            continue
        if "run_id_in" in selector and run_id not in selector["run_id_in"]:
            continue
        if "arm" in selector and record.get("arm") != selector["arm"]:
            continue
        chosen.append((name, record))
    return chosen


def ladder_records(census):
    """The two open-loop ladders, by arm. The context every rate question needs."""
    ladders = {}
    for name in census.derived:
        record = census.records[name]
        if run_block(record).get("run_id") in ("rate-off", "rate-on"):
            ladders[record["arm"]] = (name, record)
    return ladders


def passing_rates(record):
    return set(int(level["target_rate"]) for level in record["levels"]
               if level.get("passed"))


def build_context(census):
    """The quantities a spec may refer to but must never type.

    `matched_offered_rate` is the highest offered rate BOTH arms held. A tail
    pair read at a rate one arm cannot serve is comparing a working system
    against a collapsed one, so the rate is derived from the ladders rather
    than chosen.
    """
    ladders = ladder_records(census)
    ceilings = sorted(set(float(record["p99_ceiling_ms"])
                          for _name, record in ladders.values()
                          if record.get("p99_ceiling_ms") is not None))
    if len(ceilings) > 1:
        canonkit.die(
            canonkit.EXIT_DID_NOT_RUN,
            "%s the open-loop ladders declare %d different p99 ceilings (%s). "
            "A capacity 'at a fixed p99' whose ceiling is not fixed is not one "
            "figure.\n"
            "  REPAIR: re-run both arms under one ceiling."
            % (canonkit.REFUSAL_PREFIX, len(ceilings), ceilings))

    matched = None
    if len(ladders) >= 2:
        common = set.intersection(*[passing_rates(record)
                                    for _name, record in ladders.values()])
        matched = max(common) if common else None
    return {
        "ladders": ladders,
        "p99_ceiling_ms": ceilings[0] if ceilings else None,
        "matched_offered_rate": matched,
    }


# ---------------------------------------------------------------------------
# the declared figure kinds
# ---------------------------------------------------------------------------


def _one(spec, selected):
    if len(selected) != 1:
        canonkit.die(
            canonkit.EXIT_DID_NOT_RUN,
            "%s figure %r is a single-record figure but its selector matched "
            "%d record(s) (%s).\n"
            "  REPAIR: name one run in the spec's `select` block."
            % (canonkit.REFUSAL_PREFIX, spec["key"], len(selected),
               [name for name, _ in selected]))
    return selected[0]


def compute_cache_hit_rate(spec, selected, context):
    hits = misses = 0
    for _name, record in selected:
        states = record.get("cache_states_total") or {}
        hits += int(states.get("cache_hit", 0))
        misses += int(states.get("cache_miss", 0))
    total = hits + misses
    value = round(100.0 * hits / total, 6) if total else None
    return {"value": value, "numerator": hits, "denominator": total,
            "population": total,
            "extra": {"hits": hits, "misses": misses}}


def compute_ladder_capacity(spec, selected, context):
    name, record = _one(spec, selected)
    levels = list(record["levels"])
    passed = [level for level in levels if level.get("passed")]
    if not passed:
        canonkit.die(
            canonkit.EXIT_DID_NOT_RUN,
            "%s figure %r found no passing level in %s: the arm held no "
            "offered rate at all, so it has no capacity to report.\n"
            "  REPAIR: re-run the ladder from a lower first rate."
            % (canonkit.REFUSAL_PREFIX, spec["key"], name))
    chosen = max(passed, key=lambda level: int(level["target_rate"]))
    held = int(chosen["target_rate"])
    failed_above = sorted(int(level["target_rate"]) for level in levels
                          if not level.get("passed")
                          and int(level["target_rate"]) > held)
    offered = sorted(int(level["target_rate"]) for level in levels)
    steps = sorted(set(b - a for a, b in zip(offered, offered[1:])))
    return {
        "value": round(float(chosen["achieved_rps"]), 6),
        "numerator": len(passed),
        "denominator": len(levels),
        "population": len(levels),
        "extra": {
            "at_target_rate": held,
            "p99_ms": chosen.get("p99_ms"),
            "p50_ms": chosen.get("p50_ms"),
            "completed": chosen.get("completed"),
            "dropped_iterations": chosen.get("dropped_iterations"),
            "dropped_fraction": chosen.get("dropped_fraction"),
            "p99_ceiling_ms": context["p99_ceiling_ms"],
            # The bracket is what the ladder actually establishes. The capacity
            # is a QUANTISED LOWER BOUND: the arm held `bracket_low` and failed
            # at `bracket_high`, so the true figure lies between them.
            "bracket_low": held,
            "bracket_high": failed_above[0] if failed_above else None,
            "ladder_step_rps": steps[0] if len(steps) == 1 else None,
        },
    }


def compute_ladder_level_p99(spec, selected, context):
    name, record = _one(spec, selected)
    rate = context.get("matched_offered_rate")
    if rate is None:
        canonkit.die(
            canonkit.EXIT_DID_NOT_RUN,
            "%s figure %r asks for the highest offered rate BOTH arms held, "
            "and the derived population holds no such rate.\n"
            "  REPAIR: re-run both open-loop ladders over a common rate set."
            % (canonkit.REFUSAL_PREFIX, spec["key"]))
    matching = [level for level in record["levels"]
                if int(level["target_rate"]) == rate]
    if len(matching) != 1:
        canonkit.die(
            canonkit.EXIT_DID_NOT_RUN,
            "%s figure %r found %d level(s) at %d rps in %s; it needs exactly "
            "one.\n"
            "  REPAIR: re-run the ladder; a rate offered twice in one run is a "
            "bookkeeping bug."
            % (canonkit.REFUSAL_PREFIX, spec["key"], len(matching), rate, name))
    level = matching[0]
    return {
        "value": round(float(level["p99_ms"]), 6),
        "numerator": 1,
        "denominator": 1,
        "population": 1,
        "extra": {
            "at_target_rate": rate,
            "achieved_rps": level.get("achieved_rps"),
            "p50_ms": level.get("p50_ms"),
            "dropped_fraction": level.get("dropped_fraction"),
            "p99_ceiling_ms": context["p99_ceiling_ms"],
        },
    }


def compute_replicates_holding(spec, selected, context):
    """an earlier finding: the RAW replicates travel, never only a statistic over them."""
    runs = []
    rates = set()
    for name, record in selected:
        level = record["capacity_at_p99_ceiling"]
        rates.add(int(level["target_rate"]))
        runs.append({
            "run_id": run_block(record).get("run_id"),
            "record": name,
            "target_rate": int(level["target_rate"]),
            "achieved_rps": level.get("achieved_rps"),
            "p50_ms": level.get("p50_ms"),
            "p99_ms": level.get("p99_ms"),
            "dropped_iterations": level.get("dropped_iterations"),
            "dropped_fraction": level.get("dropped_fraction"),
            "passed": bool(level.get("passed")),
        })
    runs.sort(key=lambda entry: str(entry["run_id"]))
    if len(rates) != 1:
        canonkit.die(
            canonkit.EXIT_DID_NOT_RUN,
            "%s figure %r gathered replicates at %d different offered rates "
            "(%s). Replicates at different rates are not replicates.\n"
            "  REPAIR: narrow the spec's selector to one rate."
            % (canonkit.REFUSAL_PREFIX, spec["key"], len(rates),
               sorted(rates)))
    held = sum(1 for entry in runs if entry["passed"])
    return {
        "value": float(held),
        "numerator": held,
        "denominator": len(runs),
        "population": len(runs),
        "runs": runs,
        "extra": {
            "at_target_rate": sorted(rates)[0],
            "p99_ceiling_ms": context["p99_ceiling_ms"],
        },
    }


def compute_sweep_sustained(spec, selected, context):
    name, record = _one(spec, selected)
    sustained = record.get("sustained") or {}
    if "sustained_rps" not in sustained:
        canonkit.die(
            canonkit.EXIT_DID_NOT_RUN,
            "%s figure %r found no `sustained` block in %s.\n"
            "  REPAIR: re-run the closed-loop sweep, which writes it."
            % (canonkit.REFUSAL_PREFIX, spec["key"], name))
    ceiling = context["p99_ceiling_ms"]
    levels = list(record["levels"])
    under = [level for level in levels
             if ceiling is not None
             and (level.get("ms") or {}).get("p99") is not None
             and float(level["ms"]["p99"]) <= ceiling]
    return {
        "value": round(float(sustained["sustained_rps"]), 6),
        "numerator": len(under),
        "denominator": len(levels),
        "population": len(levels),
        "extra": {
            "at_vus": sustained.get("at_vus"),
            "p99_ms": sustained.get("p99_ms"),
            "p50_ms": sustained.get("p50_ms"),
            "p99_ceiling_ms": ceiling,
        },
    }


def compute_probe_ceiling(spec, selected, context):
    name, record = _one(spec, selected)
    probe = record.get("driver_headroom") or {}
    levels = list(probe.get("levels") or [])
    if not levels:
        canonkit.die(
            canonkit.EXIT_DID_NOT_RUN,
            "%s figure %r found no driver-headroom probe levels in %s. A "
            "throughput benchmark that never measures its own generator is "
            "reporting an unknown mixture of the system and the tool.\n"
            "  REPAIR: re-run the sweep with --null-probe."
            % (canonkit.REFUSAL_PREFIX, spec["key"], name))
    best = max(levels, key=lambda level: float(level["rps"]))
    return {
        "value": round(float(best["rps"]), 6),
        "numerator": len(levels),
        "denominator": len(levels),
        "population": len(levels),
        "extra": {
            "at_vus": best.get("vus"),
            "p99_ms": (best.get("ms") or {}).get("p99"),
        },
    }


KINDS = {
    "cache_hit_rate": compute_cache_hit_rate,
    "ladder_capacity": compute_ladder_capacity,
    "ladder_level_p99": compute_ladder_level_p99,
    "replicates_holding": compute_replicates_holding,
    "sweep_sustained": compute_sweep_sustained,
    "probe_ceiling": compute_probe_ceiling,
}


# ---------------------------------------------------------------------------
# the three refusals, copied from the shared contract
# ---------------------------------------------------------------------------


def refuse_zero_population(key, population, because):
    """COPIED VERBATIM in its diagnosis; only the REPAIR names this artifact."""
    canonkit.die(
        canonkit.EXIT_DID_NOT_RUN,
        "%s figure %r has a population of %d (%s). A figure over zero inputs "
        "did not measure anything, and every count derived from it would be a "
        "0/0 pass. Population 1 is legal; 0 is not.\n"
        "  REPAIR: run the measuring scripts so results/ holds per-run records "
        "this spec can select, then re-run derive.py."
        % (canonkit.REFUSAL_PREFIX, key, population, because))


def refuse_threshold_claim(key, count):
    canonkit.die(
        canonkit.EXIT_DID_NOT_RUN,
        "%s figure %r carries threshold_claim: true with %d recorded run(s); "
        "at least %d are required. A single run landing the right side of a "
        "line does not establish that the line was crossed.\n"
        "  REPAIR: record %d more run(s), or drop threshold_claim and report "
        "the figure without the crossing claim."
        % (canonkit.REFUSAL_PREFIX, key, count,
           canonkit.THRESHOLD_CLAIM_MIN_RUNS,
           canonkit.THRESHOLD_CLAIM_MIN_RUNS - count))


# ---------------------------------------------------------------------------
# the derivation
# ---------------------------------------------------------------------------


def latest_run(census):
    """The last-STARTED run among the records actually derived from.

    Selected by the recorded started_at INSIDE the record, never by file mtime,
    and drawn from the used population rather than from every run on disk: the
    figures record is dated by the last measurement it rests on.
    """
    runs = [run_block(census.records[name]) for name in census.derived]
    runs = [run for run in runs if run.get("started_at")]
    if not runs:
        return {}
    return sorted(runs, key=lambda run: str(run["started_at"]))[-1]


def derive(root, specs, slug=None, stream=None):
    """Author every declared figure and write results/figures.json."""
    stream = stream if stream is not None else sys.stdout
    results_dir = os.path.join(str(root), "results")
    slug = slug or os.path.basename(os.path.abspath(str(root)))

    # Refuses with exit 2 when the gate is absent or failed, BEFORE any record
    # is read. A number authored past a failed gate has nothing behind it.
    token = canonkit.require_gate(results_dir)

    census = classify(results_dir, token)
    context = build_context(census)
    run = latest_run(census)

    figures = {}
    for spec in specs:
        key = spec["key"]
        kind = spec.get("kind")
        if kind not in KINDS:
            canonkit.die(
                canonkit.EXIT_DID_NOT_RUN,
                "%s figure %r declares kind %r, which this artifact cannot "
                "author. Known kinds: %s.\n"
                "  REPAIR: correct the kind in figure-specs.json."
                % (canonkit.REFUSAL_PREFIX, key, kind, sorted(KINDS)))

        selected = select_records(spec, census)
        if not selected:
            refuse_zero_population(
                key, 0,
                "no record in the derived population of %d matches its "
                "selector %r" % (len(census.derived), spec.get("select")))

        computed = KINDS[kind](spec, selected, context)
        population = int(computed["population"])
        if population < 1:
            refuse_zero_population(
                key, population,
                "its %d selected record(s) counted nothing" % len(selected))

        runs = list(computed.get("runs") or [])
        if spec.get("threshold_claim"):
            if len(runs) < canonkit.THRESHOLD_CLAIM_MIN_RUNS:
                refuse_threshold_claim(key, len(runs))

        figure = {
            "value": computed["value"],
            "unit": spec["unit"],
            "population": population,
            "population_label": spec["population_label"],
            "derived_from": sorted(name for name, _ in selected),
            "canon_bullet": spec["canon_bullet"],
            "canon_value": spec.get("canon_value"),
            "similar": spec.get("similar"),
            "similar_reason_ref": spec.get("similar_reason_ref"),
            "tier_achieved": spec.get("tier_achieved"),
            "reproduce_criterion": spec.get("reproduce_criterion"),
            "threshold_claim": bool(spec.get("threshold_claim")),
            "not_shown": spec.get("not_shown"),
            # The chain, recorded so it can be re-walked rather than trusted.
            "kind": kind,
            "predicate": spec.get("select"),
            "numerator": computed["numerator"],
            "denominator": computed["denominator"],
        }
        figure.update(computed.get("extra") or {})
        # an earlier finding: the RAW replicates, never only a summary statistic over them.
        if runs:
            figure["runs"] = runs
        figures[key] = figure

    record = {
        "schema": SCHEMA,
        "schema_version": canonkit.SCHEMA_VERSION,
        "artifact": slug,
        "gate_token": token,
        # NOT a wall clock. The instant the last measurement these figures rest
        # on finished, read from that run's own record -- so re-deriving over
        # unchanged records is byte-identical and this file can be hash-pinned,
        # while the provenance it carries is still machine-written.
        "dated_at": run.get("finished_at") or run.get("started_at"),
        "started_at": run.get("started_at"),
        "started_at_utc": run.get("started_at_utc"),
        # `source_run_id`, NOT `run_id`. A top-level `run_id` is how the
        # conformance runner recognises a file as being ITSELF a run record,
        # and it then requires the full seven-field run block -- finished_at,
        # the cost triple, the wall clock. A figures record is not a run and
        # would be reported as a PARTIAL one. MEASURED: naming this key
        # `run_id` moved CHECK-06 from PASS to FAIL with
        # `run-record:partial-record:results/figures.json`. With the key
        # renamed the runner follows `gate_token` to the raw record instead,
        # which is the path its own locator documents as the normal case for a
        # derived figures record.
        "source_run_id": run.get("run_id"),
        "matched_offered_rate": context["matched_offered_rate"],
        "p99_ceiling_ms": context["p99_ceiling_ms"],
        "population": {
            "listed": census.total,
            "derived_from": len(census.derived),
            "excluded": census.excluded_count,
            "derived_from_records": census.derived,
            "excluded_by_reason": [
                {"reason": reason, "records": len(names), "names": names}
                for reason, names in census.excluded],
        },
        "figures": figures,
    }

    violations = canonkit.validate_figures(record)
    if violations:
        canonkit.die(
            canonkit.EXIT_DID_NOT_RUN,
            "%s derive.py assembled a figures record its own validator rejects "
            "(%d violation(s)):\n%s\n"
            "  REPAIR: this is a defect in the figure SPECS or in derive.py, "
            "not in the measurement."
            % (canonkit.REFUSAL_PREFIX, len(violations), "\n".join(violations)))

    canonkit.atomic_write_json(os.path.join(results_dir, OUTPUT_NAME), record)

    # The population line. `listed` is every JSON file directly under results/,
    # `checked` is what the figures rest on, and the reporter RAISES if the
    # two do not close against the exclusions -- so the identity is enforced
    # rather than claimed.
    canonkit.report("DERIVE", True, 0, len(census.derived), 1,
                    not_examined=census.excluded_count, listed=census.total,
                    note="authored %d figure(s) over %d per-run record(s)"
                         % (len(figures), len(census.derived)))
    stream.write(census.exclusion_line() + "\n")
    for reason, names in census.excluded:
        if names and len(names) <= 12:
            stream.write("[derive]   %s, %d records: %s\n"
                         % (reason, len(names), ", ".join(names)))
        elif names:
            stream.write("[derive]   %s, %d records: %s, ... (%d more)\n"
                         % (reason, len(names), ", ".join(names[:6]),
                            len(names) - 6))
    stream.write("[derive] census identity: derived-from %d + excluded %d == "
                 "%d listed\n"
                 % (len(census.derived), census.excluded_count, census.total))
    for key in sorted(figures):
        figure = figures[key]
        stream.write("[derive] %s = %s %s  (%d of %d %s)\n"
                     % (key, figure["value"], figure["unit"],
                        figure["numerator"], figure["denominator"],
                        figure["population_label"]))
    return record


def main(argv=None, stream=None):
    parser = argparse.ArgumentParser(
        description="Author this benchmark's figures from its own records.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--specs", default="figure-specs.json",
                        help="path to the JSON file holding the declared specs")
    args = parser.parse_args(argv)
    with open(args.specs, "rb") as handle:
        specs = json.loads(handle.read().decode("utf-8"))
    derive(args.root, specs, stream=stream)
    return canonkit.EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
