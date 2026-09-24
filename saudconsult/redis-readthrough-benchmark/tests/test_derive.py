"""The published figures must be DERIVED from this repository's own records.

WHY THIS TEST EXISTS
--------------------
Every number this benchmark ships used to be typed. `results/figures.json` is
now authored by `derive.py` from the per-run JSON records under `results/`, and
this module is what makes that claim checkable rather than merely stated.

THE THING IT GUARDS HARDEST IS THE POPULATION, NOT THE VALUE.
`results/` holds records from TWO campaigns plus one withdrawn run. A derivation
that walked `results/*.json` and averaged what it found would silently span
them, and nothing downstream could tell. So the census is asserted three ways:

  * every record any figure was derived from carries THIS run's gate token,
    checked by OPENING the record rather than by trusting the filter that
    selected it;
  * no figure was derived from any of the three files the 2026-07-31 retraction
    withdrew;
  * the excluded counts plus the derived-from count EQUAL the number of JSON
    files directly under `results/`, so a record that is neither used nor
    excluded cannot exist.

THE TOKEN IS NESTED, AND A TOP-LEVEL SCAN GETS A WRONG ANSWER THAT LOOKS RIGHT.
A per-run record carries its token at `run.gate_token`, not at the top level.
Scanning top-level keys reports that ONE file out of 136 carries a token -- a
false answer with a real answer's shape, and it was actually arrived at before a
substring search corrected it. `test_the_token_is_read_from_the_nested_run_block`
pins the correct reader against exactly that mistake.

BYTE STABILITY IS ASSERTED IN BOTH DIRECTIONS.
"running it twice gives the same bytes" is satisfied by a derive.py that writes
a constant. The paired assertion -- change one input record and the bytes change
-- is what makes the first one mean anything.

HOW TO RUN IT
-------------
From the repository root, with any CPython 3.11 or newer that has pytest:

    python -m pytest tests -q
"""
from __future__ import annotations

import glob
import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
GATE_JSON = RESULTS / "gate.json"
RESULTS_JSON = RESULTS / "results.json"
FIGURES_JSON = RESULTS / "figures.json"
SPECS_JSON = ROOT / "figure-specs.json"
DERIVE_PY = ROOT / "derive.py"

WITHDRAWN_RECORDS = ("arm-off-mild.json", "arm-on-mild.json",
                     "sensitivity-mild-skew.json")

# The guard whose counted integers the hit-rate figure must agree with. The two
# paths are genuinely independent: derive.py reads the cached arm's own
# cache_states_total, finalize.py wrote these counts into the guard record.
GUARD_ID_PREFIX = "G4a"


# --------------------------------------------------------------------------
# loading derive.py
# --------------------------------------------------------------------------

def load_derive():
    """Import derive.py by path, with the repository root importable.

    By PATH and under a bare module name, because derive.py imports `canonkit`
    and `runmeta` as siblings -- the same way every other script here is run.
    """
    if not DERIVE_PY.exists():
        raise AssertionError(
            "REFUSING: there is no %s, so no figure in this repository is "
            "derived from a machine record. REPAIR: author derive.py."
            % DERIVE_PY.name)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location("artifact_derive", DERIVE_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_specs():
    if not SPECS_JSON.exists():
        raise AssertionError(
            "REFUSING: there is no %s, so no figure is DECLARED. REPAIR: "
            "author figure-specs.json." % SPECS_JSON.name)
    return json.loads(SPECS_JSON.read_text(encoding="utf-8"))


def gate_token():
    return json.loads(GATE_JSON.read_text(encoding="utf-8"))["run_token"]


def flat_results_names():
    """Every JSON INPUT directly under results/. Not recursive, on purpose.

    results/raw/ holds one RUN record per measurement -- the provenance index,
    read for timestamps. Its 23 records restate the same
    capacity_at_p99_ceiling the flat records carry, so folding it into the
    figure population would double-count every ladder run.

    figures.json is the OUTPUT and is excluded here by its own literal name,
    so this population is computed independently of derive.py rather than by
    asking derive.py what it decided to ignore.
    """
    return sorted(os.path.basename(p)
                  for p in glob.glob(os.path.join(str(RESULTS), "*.json"))
                  if os.path.basename(p) != "figures.json")


def read_figures():
    if not FIGURES_JSON.exists():
        raise AssertionError(
            "REFUSING: there is no %s. REPAIR: run `python derive.py --specs "
            "figure-specs.json`." % FIGURES_JSON.name)
    return json.loads(FIGURES_JSON.read_text(encoding="utf-8"))


def derive_here(stream=None):
    """Derive over the REAL tree, in process, returning (module, record, text).

    Writes results/figures.json, which is what the repository ships; the
    committed file and a fresh derivation are byte-identical by construction
    and test_deriving_twice_over_identical_records_is_byte_identical proves it.
    """
    import io
    module = load_derive()
    stream = stream if stream is not None else io.StringIO()
    record = module.derive(str(ROOT), load_specs(), stream=stream)
    return module, record, stream.getvalue()


def copy_tree(tmp_path, name="redis-readthrough-benchmark"):
    """A throwaway copy of results/, so no test mutates the real records."""
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(RESULTS, root / "results")
    return root


def sha256_of(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def synthetic_spec(**overrides):
    """A declared figure that selects nothing, for the refusal paths."""
    spec = {
        "key": "synthetic_control",
        "unit": "percent",
        "kind": "cache_hit_rate",
        "select": {"run_id": "a-run-id-no-record-carries"},
        "population_label": "a control that selects no record at all",
        "canon_bullet": "saudconsult:P5-B3",
        "threshold_claim": False,
    }
    spec.update(overrides)
    return spec


# --------------------------------------------------------------------------
# the gate
# --------------------------------------------------------------------------

def test_derive_refuses_with_exit_2_when_the_gate_is_absent(tmp_path, capsys):
    """No gate, no authorised measurement, no number. Before any record is read.

    Exit 2 rather than 1: a derivation with no gate COULD NOT LOOK, which is a
    different claim from having looked and found a problem.
    """
    module = load_derive()
    root = copy_tree(tmp_path)
    (root / "results" / "gate.json").unlink()
    capsys.readouterr()

    with pytest.raises(SystemExit) as excinfo:
        module.derive(str(root), load_specs(), stream=None)

    assert excinfo.value.code == 2, excinfo.value.code
    message = capsys.readouterr().err
    assert "REFUSING:" in message, message
    assert "gate.json" in message, message


def test_the_gate_token_the_figures_record_carries_is_the_gates_own(tmp_path):
    _, record, _ = derive_here()
    assert record["gate_token"] == gate_token()


# --------------------------------------------------------------------------
# the census -- the part that keeps two campaigns apart
# --------------------------------------------------------------------------

def test_the_token_is_read_from_the_nested_run_block(tmp_path):
    """The trap: a top-level key scan reports ONE token-bearing file of 136.

    A per-run record carries its token at run.gate_token. Reading the top level
    only finds gate.json's own `run_token` and reports a population of one --
    a wrong answer with a right answer's shape.
    """
    module = load_derive()
    token = gate_token()

    payloads = [(name, json.loads((RESULTS / name).read_text(encoding="utf-8")))
                for name in flat_results_names()]
    nested = [name for name, payload in payloads
              if module.record_gate_token(payload) == token]
    # `.get` guarded, because results/sequence.json is a JSON ARRAY -- which is
    # itself part of why a naive top-level scan is the wrong instrument here.
    top_level_only = [name for name, payload in payloads
                      if isinstance(payload, dict)
                      and payload.get("gate_token") == token]

    assert len(top_level_only) <= 1, (
        "a top-level-only scan found %d; if this ever rises the shape moved"
        % len(top_level_only))
    assert len(nested) > len(top_level_only) + 1, (
        "the nested reader found %d token-bearing record(s) and the top-level "
        "scan found %d. If those are the same number the reader is reading the "
        "wrong place." % (len(nested), len(top_level_only)))


def test_the_census_identity_closes_over_every_flat_results_json():
    """excluded + derived-from == listed. A record that is neither cannot exist."""
    module = load_derive()
    census = module.classify(str(RESULTS), gate_token())

    listed = flat_results_names()
    excluded = sum(len(names) for _reason, names in census.excluded)

    assert census.total == len(listed), (census.total, len(listed))
    assert len(census.derived) + excluded == len(listed), (
        "derived-from %d + excluded %d != listed %d"
        % (len(census.derived), excluded, len(listed)))
    assert sorted(census.derived
                  + [n for _r, names in census.excluded for n in names]) == listed


def test_the_derivation_does_not_count_its_own_output(tmp_path):
    """A census that counts what the census wrote steps from N to N+1.

    MEASURED: before this was fixed, the first derivation listed 136 records
    and every later one listed 137, because results/figures.json is a JSON
    file directly under results/. The bytes then moved for a reason that had
    nothing to do with any measurement, and the byte-stability test caught it.
    """
    module = load_derive()
    root = copy_tree(tmp_path)
    (root / "results" / "figures.json").unlink(missing_ok=True)

    first = module.derive(str(root), load_specs(), stream=None)
    assert (root / "results" / "figures.json").exists()
    second = module.derive(str(root), load_specs(), stream=None)

    assert first["population"]["listed"] == second["population"]["listed"], (
        "listed moved from %d to %d once the output existed"
        % (first["population"]["listed"], second["population"]["listed"]))
    everywhere = [name
                  for _reason, names in module.classify(
                      str(root / "results"), gate_token()).excluded
                  for name in names]
    census = module.classify(str(root / "results"), gate_token())
    assert "figures.json" not in everywhere
    assert "figures.json" not in census.derived
    assert "figures.json" not in census.listed


def test_the_exclusion_line_carries_both_classes_with_their_own_counts():
    _, _, text = derive_here()

    assert "superseded by the re-run" in text, text
    assert "withdrawn by retraction 13" in text, text
    for name in WITHDRAWN_RECORDS:
        assert name in text, ("the exclusion did not name %s:\n%s" % (name, text))
    assert "withdrawn by retraction 13, 3 records" in text, text


def test_the_superseded_class_is_not_empty_and_is_not_everything():
    """A filter that excluded nothing, or everything, would also 'pass' above."""
    module = load_derive()
    census = module.classify(str(RESULTS), gate_token())
    reasons = dict(census.excluded)

    superseded = reasons[module.SUPERSEDED]
    withdrawn = reasons[module.WITHDRAWN]

    assert len(withdrawn) == 3, sorted(withdrawn)
    assert sorted(withdrawn) == sorted(WITHDRAWN_RECORDS), sorted(withdrawn)
    assert len(superseded) > 0, "nothing was superseded; the token filter is inert"
    assert len(census.derived) > 0, "everything was excluded; nothing was derived"


def test_every_record_a_figure_was_derived_from_carries_this_runs_token():
    """Asserted by OPENING the records, never by trusting the filter."""
    module = load_derive()
    record = read_figures()
    token = gate_token()

    checked = 0
    for key, figure in sorted(record["figures"].items()):
        for name in figure["derived_from"]:
            payload = json.loads((RESULTS / name).read_text(encoding="utf-8"))
            assert module.record_gate_token(payload) == token, (
                "figure %r was derived from %s, which carries %r, not this "
                "run's %r" % (key, name,
                              module.record_gate_token(payload), token))
            checked += 1
    assert checked > 0, "no figure names any source record"


def test_no_figure_was_derived_from_a_withdrawn_record():
    record = read_figures()
    for key, figure in sorted(record["figures"].items()):
        for name in figure["derived_from"]:
            assert name not in WITHDRAWN_RECORDS, (
                "figure %r folds the withdrawn run's %s into a published "
                "number" % (key, name))


# --------------------------------------------------------------------------
# the three refusals, copied from the contract
# --------------------------------------------------------------------------

def test_a_figure_over_a_zero_population_refuses(tmp_path, capsys):
    """Population 1 is legal; 0 is not. The refusal NAMES the key."""
    module = load_derive()
    capsys.readouterr()

    with pytest.raises(SystemExit) as excinfo:
        module.derive(str(ROOT), [synthetic_spec()], stream=None)

    assert excinfo.value.code == 2
    message = capsys.readouterr().err
    assert "synthetic_control" in message, message
    assert "Population 1 is legal" in message, message


def test_a_population_of_one_is_legal_and_derives():
    """a design rule. The open-loop ladder runs each level once; that n=1 is stated."""
    record = read_figures()
    singles = [key for key, figure in record["figures"].items()
               if figure["population"] == 1]
    assert singles, "no figure carries a population of 1, so the path is untested"
    for key in singles:
        assert record["figures"][key]["population_label"], key


def test_a_threshold_claim_with_too_few_replicates_refuses_naming_both_counts(
        capsys):
    module = load_derive()
    specs = load_specs()
    claimed = [s for s in specs if s.get("threshold_claim")]
    assert claimed, "no declared figure exercises the threshold-claim path"

    # Narrowed to two of the three replicates by naming them, which is a
    # selector the spec format already has -- no test-only hook in derive.py.
    prefix = claimed[0]["select"]["run_id_prefix"]
    starved = dict(claimed[0])
    starved["key"] = "starved_threshold_claim"
    starved["select"] = {"run_id_in": [prefix + "1", prefix + "2"]}
    capsys.readouterr()

    with pytest.raises(SystemExit) as excinfo:
        module.derive(str(ROOT), [starved], stream=None)

    assert excinfo.value.code == 2
    message = capsys.readouterr().err
    assert "starved_threshold_claim" in message, message
    assert "2" in message and "3" in message, message


# --------------------------------------------------------------------------
# the figure record
# --------------------------------------------------------------------------

def test_every_figure_carries_a_labelled_non_zero_population_and_its_sources():
    record = read_figures()
    assert record["figures"], "the record carries zero figures"
    for key, figure in sorted(record["figures"].items()):
        assert isinstance(figure["population"], int), key
        assert figure["population"] >= 1, (key, figure["population"])
        assert str(figure["population_label"]).strip(), key
        assert figure["derived_from"], key


def test_a_figure_with_replicates_carries_the_raw_runs(capsys):
    """an earlier finding: the replicates travel, never only a summary statistic over them."""
    record = read_figures()
    replicated = {key: figure for key, figure in record["figures"].items()
                  if figure.get("threshold_claim")}
    assert replicated, "no figure carries replicates, so an earlier finding is untested here"
    for key, figure in sorted(replicated.items()):
        runs = figure.get("runs")
        assert isinstance(runs, list) and len(runs) >= 3, (key, runs)
        assert len(runs) == len(figure["derived_from"]), (key, runs)


def test_the_declared_specs_hand_type_no_value():
    """A spec carrying a literal `value` would be a typed number in disguise."""
    for spec in load_specs():
        assert "value" not in spec, spec["key"]
        assert "numerator" not in spec, spec["key"]
        assert "denominator" not in spec, spec["key"]


def test_the_derived_record_validates_against_the_frozen_core():
    module = load_derive()
    record = read_figures()
    violations = module.canonkit.validate_figures(record)
    assert violations == [], "\n".join(violations)


# --------------------------------------------------------------------------
# the cross-check: two paths must agree on the hit rate
# --------------------------------------------------------------------------

def test_the_hit_rate_figure_equals_the_value_the_g4a_guard_implies():
    """Two paths that agree is a measurement; one path is an assertion.

    derive.py counts the cached arm's own cache_states_total. finalize.py wrote
    hits and misses into the G4a guard record. Neither reads the other.
    """
    module = load_derive()
    record = read_figures()

    key = module.HIT_RATE_KEY
    assert key in record["figures"], sorted(record["figures"])
    figure = record["figures"][key]

    guards = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))["guards"]
    matching = [g for g in guards
                if str(g.get("id", "")).startswith(GUARD_ID_PREFIX)]
    assert len(matching) == 1, [g.get("id") for g in matching]
    hits, misses = matching[0]["hits"], matching[0]["misses"]
    assert hits + misses > 0

    expected = round(100.0 * hits / (hits + misses), 6)
    assert figure["value"] == expected, (figure["value"], expected)
    assert figure["population"] == hits + misses, (
        figure["population"], hits + misses)
    assert figure["numerator"] == hits, (figure["numerator"], hits)


def load_hit_rate_module():
    """tests/test_hit_rate.py, by path -- it is a sibling, not a package."""
    path = pathlib.Path(__file__).resolve().parent / "test_hit_rate.py"
    spec = importlib.util.spec_from_file_location("artifact_hit_rate", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_hit_rate_figure_agrees_with_the_documented_prose():
    """The third path: what benchlib/workload.py already states.

    test_hit_rate.py binds that sentence to the G4a guard. This binds the
    DERIVED figure to the same sentence, so the triangle closes: record ->
    figure, record -> prose, figure -> prose.
    """
    prose = load_hit_rate_module()

    record = read_figures()
    figure = record["figures"][load_derive().HIT_RATE_KEY]
    written = prose.documented_rate(
        prose.module_docstring(prose.WORKLOAD_PY), "the workload docstring")
    decimals = len(written.split(".")[1]) if "." in written else 0

    assert round(figure["value"], decimals) == float(written), (
        "the derived figure is %r and the docstring states %s%%"
        % (figure["value"], written))


# --------------------------------------------------------------------------
# byte stability, asserted in BOTH directions
# --------------------------------------------------------------------------

def test_deriving_twice_over_identical_records_is_byte_identical(tmp_path):
    """Without this, hash-pinning results/figures.json is wrong."""
    module = load_derive()
    root = copy_tree(tmp_path)
    figures = root / "results" / "figures.json"

    module.derive(str(root), load_specs(), stream=None)
    first = sha256_of(figures)
    module.derive(str(root), load_specs(), stream=None)
    second = sha256_of(figures)

    assert first == second, (
        "two derivations over identical records produced different bytes "
        "(%s then %s); something in the record varies for no reason"
        % (first[:12], second[:12]))


def test_changing_one_input_record_changes_the_derived_bytes(tmp_path):
    """The paired assertion. Without it, writing a constant would 'pass' above.

    The record is rewritten in place in a throwaway copy -- never restored with
    `git checkout --`, which restores from HEAD and would make the verdict
    wrong in the direction that flatters us.
    """
    module = load_derive()
    root = copy_tree(tmp_path)
    figures = root / "results" / "figures.json"

    module.derive(str(root), load_specs(), stream=None)
    before = sha256_of(figures)

    mutant = root / "results" / "rate-on.json"
    payload = json.loads(mutant.read_text(encoding="utf-8"))
    level = payload["capacity_at_p99_ceiling"]
    level["achieved_rps"] = level["achieved_rps"] + 1.0
    for entry in payload["levels"]:
        if entry["target_rate"] == level["target_rate"]:
            entry["achieved_rps"] = level["achieved_rps"]
    mutant.write_text(json.dumps(payload, indent=2) + "\n",
                      encoding="utf-8", newline="\n")

    module.derive(str(root), load_specs(), stream=None)
    after = sha256_of(figures)

    assert after != before, (
        "moving one recorded throughput left the derived bytes at %s. The "
        "chain is short-circuited and the stability above means nothing."
        % before[:12])


def test_the_output_key_ordering_is_stable_across_runs(tmp_path):
    """A dict whose iteration order leaks into the bytes breaks a hash pin."""
    module = load_derive()
    root = copy_tree(tmp_path)
    figures = root / "results" / "figures.json"

    module.derive(str(root), load_specs(), stream=None)
    first = figures.read_text(encoding="utf-8")
    module.derive(str(root), list(reversed(load_specs())), stream=None)
    second = figures.read_text(encoding="utf-8")

    assert first.splitlines() == second.splitlines(), (
        "re-ordering the declared specs re-ordered the written record")


def test_the_committed_figures_record_re_derives_to_the_same_bytes(tmp_path):
    """The record this repository ships is the one its own records produce."""
    module = load_derive()
    committed = sha256_of(FIGURES_JSON)

    root = copy_tree(tmp_path)
    (root / "results" / "figures.json").unlink(missing_ok=True)
    module.derive(str(root), load_specs(), stream=None)

    assert sha256_of(root / "results" / "figures.json") == committed, (
        "the committed results/figures.json is not what derive.py writes "
        "today. REPAIR: re-run derive.py and commit the result.")


# --------------------------------------------------------------------------
# the command line
# --------------------------------------------------------------------------

def test_derive_runs_as_a_script_and_exits_zero(tmp_path):
    import io
    module = load_derive()
    stream = io.StringIO()
    code = module.main(["--root", str(ROOT), "--specs", str(SPECS_JSON)],
                       stream=stream)
    assert code == 0, stream.getvalue()
