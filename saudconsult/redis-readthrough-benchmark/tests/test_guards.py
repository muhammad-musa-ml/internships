"""Every integrity guard must say what it examined, and how little would be too little.

WHY THIS TEST EXISTS
--------------------
A guard array is this benchmark's own self-assessment: seven records, each with a
`passed` boolean, and one line in finalize.py that reads

    all(g["passed"] for g in guards)

`all()` over an EMPTY sequence returns True. That is not a quirk to work around,
it is the exact shape of the failure worth guarding: a guard array that was never
populated reports every guard passing, the run publishes, and nothing anywhere
says that nothing was checked. The seven appends in finalize.py are unconditional
today, which is the only reason that line is safe - and "safe because of how the
code above it happens to be written" is a property nobody re-checks.

So the emptiness case is CONSTRUCTED here and asserted to be a violation, rather
than argued about. A refusal nobody has seen fire is a refusal nobody has
evidence for.

THE SECOND HALF IS THE POPULATION, AND IT IS THE HALF THAT WAS MISSING
-----------------------------------------------------------------------
A verdict with no count beside it cannot be read. `passed: true` over three
thousand compared keys and `passed: true` over four are the same two words. Every
guard here therefore carries three fields beyond its own domain-specific ones:

    population         an int: how many things it actually examined
    population_label   a string: what those things were, in words
    minimum_required   a number: the population below which its verdict would
                       not mean anything

and the validator treats `passed: true` on a population below that floor as a
violation - a guard that passes under its own floor measured nothing.

The domain-specific key each guard already carried is KEPT beside the uniform
three, never replaced by them. `compared_keys` and `required_factor` say what
they are; `population` and `minimum_required` say the same thing in a shape
something mechanical can read. Renaming rather than adding would have satisfied a
reader of the schema while destroying the meaning for a reader of the guard.

WHAT IS AND IS NOT TESTED HERE
--------------------------------
Not the benchmark: re-running it is how that is tested. What is tested is the
shape and the honesty of the record the run leaves behind, which is the far
cheaper failure and the one no run catches.

Every assertion below states its population and refuses over an empty one, for
the reason in the first paragraph.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
RESULTS_JSON = ROOT / "results" / "results.json"
CORE_PATH = ROOT / "canonkit.py"

# The seven guards this benchmark runs, as a COMMITTED LITERAL rather than a
# count derived from the file under test. A purely derived expectation silently
# stops checking when its input shrinks, because `expected` falls to match
# `found`; the literal is the tripwire on the derivation's own input, and a
# disagreement between the two IS the finding rather than a number to pick
# between.
EXPECTED_GUARD_IDS = (
    "G1a-equivalence-server-attested",
    "G1b-equivalence-client-recomputed",
    "G2-coverage",
    "G3-driver-headroom",
    "G4a-cache-exercised",
    "G4b-keys-bounded-by-workload",
    "G5-two-clocks",
)
EXPECTED_GUARD_COUNT = 7

# The domain-specific fields that must SURVIVE beside the uniform three. These
# are what a human reads; the uniform three are what a machine reads. Losing
# either half would be a loss.
DOMAIN_KEYS = {
    "G1a-equivalence-server-attested": ("compared_keys", "mismatches"),
    "G1b-equivalence-client-recomputed": ("compared_keys", "mismatches"),
    "G2-coverage": ("compared_keys",),
    "G3-driver-headroom": ("driver_ceiling_rps", "fastest_arm_rps",
                           "required_factor", "measured_factor"),
    "G4a-cache-exercised": ("hits", "misses", "measured_hit_rate"),
    "G4b-keys-bounded-by-workload": ("redis_dbsize_after_run",
                                     "distinct_tenants_in_sequence"),
    "G5-two-clocks": ("client_rps_delta", "server_us_p50_off",
                      "server_us_p50_on"),
}

UNIFORM_KEYS = ("population", "population_label", "minimum_required")


class Refused(Exception):
    """A comparison that could not be made. Never a pass."""


def _refuse(reason: str, repair: str) -> "Refused":
    return Refused("REFUSING: %s REPAIR: %s" % (reason, repair))


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------

def load_core():
    """Load the shared core BY PATH, under a bare module name.

    Never a package import: this file is a byte-identical copy of one that lives
    elsewhere, and importing it as a package member is how two copies of the one
    file whose job is preventing drift begin to drift.
    """
    if not CORE_PATH.exists():
        raise _refuse(
            "there is no %s beside this repository's tests, so the guard "
            "validator cannot be loaded." % CORE_PATH.name,
            "restore the shared core file at the repository root.")
    spec = importlib.util.spec_from_file_location("frozen_core", str(CORE_PATH))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_record(path: pathlib.Path = RESULTS_JSON) -> dict:
    if not path.exists():
        raise _refuse(
            "there is no %s, so there is no guard record to check." % path.name,
            "run finalize.py, which merges both arms and writes the guards.")
    record = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise _refuse(
            "%s does not hold an object at its top level." % path.name,
            "re-run finalize.py rather than hand-editing the record.")
    return record


def load_guards(path: pathlib.Path = RESULTS_JSON) -> list:
    guards = load_record(path).get("guards")
    if not isinstance(guards, list):
        raise _refuse(
            "%s carries no guards[] array." % path.name,
            "re-run finalize.py, which writes the guard records.")
    if not guards:
        raise _refuse(
            "%s carries ZERO guards. A guard array that was never populated "
            "reports every guard passing, because all() over an empty sequence "
            "is True." % path.name,
            "re-run finalize.py and read the guard block it writes.")
    return guards


def a_valid_guard_record() -> dict:
    """A minimal, well-formed record. The base every control below breaks ONE thing in.

    Deliberately synthetic rather than a copy of the real one: a control built by
    mutating today's record would test whatever today's record happens to be, and
    would stop discriminating the moment that changed.
    """
    return {
        "guards": [
            {"id": "GX-example", "passed": True, "population": 1000,
             "population_label": "things examined", "minimum_required": 500,
             "domain_specific_count": 1000},
        ],
        "all_guards_passed": True,
    }


# --------------------------------------------------------------------------
# the record this run actually published
# --------------------------------------------------------------------------

def test_the_record_carries_exactly_the_guards_expected():
    guards = load_guards()
    assert len(guards) == EXPECTED_GUARD_COUNT, (
        "the record carries %d guard(s); the committed expectation is %d. A "
        "guard appearing or vanishing without this literal moving is the "
        "finding, not a number to pick between: %r"
        % (len(guards), EXPECTED_GUARD_COUNT, [g.get("id") for g in guards]))
    ids = tuple(str(g.get("id")) for g in guards)
    assert ids == EXPECTED_GUARD_IDS, (
        "the record's guard ids are %r; expected %r" % (ids, EXPECTED_GUARD_IDS))


def test_the_validator_reports_no_violation_over_the_published_record():
    """The headline. Every other test here explains one way this one can fail."""
    core = load_core()
    record = load_record()
    guards = load_guards()
    violations = core.validate_guards(record)
    assert violations == [], (
        "the published guard record does not satisfy the shared guard shape. "
        "%d guard(s) examined, %d violation(s):\n  %s"
        % (len(guards), len(violations), "\n  ".join(violations)))


def test_every_guard_carries_the_uniform_population_and_floor():
    guards = load_guards()
    assert len(guards) == EXPECTED_GUARD_COUNT, len(guards)
    problems = []
    for guard in guards:
        gid = guard.get("id")
        missing = [key for key in UNIFORM_KEYS if key not in guard]
        if missing:
            problems.append("%s is missing %s" % (gid, ", ".join(missing)))
            continue
        population = guard["population"]
        label = guard["population_label"]
        floor = guard["minimum_required"]
        if not isinstance(population, int) or isinstance(population, bool):
            problems.append("%s.population is %r, expected an int"
                            % (gid, population))
        if not isinstance(label, str) or not label.strip():
            problems.append("%s.population_label is %r, expected a non-empty "
                            "string: a count with no name cannot be read"
                            % (gid, label))
        if isinstance(floor, bool) or not isinstance(floor, (int, float)):
            problems.append("%s.minimum_required is %r, expected a number"
                            % (gid, floor))
    assert not problems, (
        "%d of %d guard(s) do not carry a readable population and floor:\n  %s"
        % (len(problems), len(guards), "\n  ".join(problems)))


def test_every_guard_that_passed_did_so_at_or_above_its_own_floor():
    """Not a schema check. The published run must actually clear its own bars."""
    guards = load_guards()
    under = []
    for guard in guards:
        if guard.get("passed") is not True:
            continue
        population = guard.get("population")
        floor = guard.get("minimum_required")
        if isinstance(population, int) and isinstance(floor, (int, float)):
            if population < floor:
                under.append("%s passed on %d, floor %s"
                             % (guard.get("id"), population, floor))
    assert not under, (
        "%d of %d guard(s) report passing on a population below their own "
        "declared floor, which measures nothing:\n  %s"
        % (len(under), len(guards), "\n  ".join(under)))


def test_every_guard_keeps_the_domain_specific_keys_it_always_had():
    """The uniform three are ADDED. Nothing was renamed into them."""
    guards = load_guards()
    assert sorted(DOMAIN_KEYS) == sorted(EXPECTED_GUARD_IDS), (
        "the domain-key map covers %d guard(s), the expected set names %d; the "
        "two must move together" % (len(DOMAIN_KEYS), len(EXPECTED_GUARD_IDS)))
    lost = []
    for guard in guards:
        gid = str(guard.get("id"))
        for key in DOMAIN_KEYS.get(gid, ()):
            if key not in guard:
                lost.append("%s lost %s" % (gid, key))
    assert not lost, (
        "%d domain-specific field(s) are gone from %d guard(s). A rename into "
        "the uniform shape satisfies a schema and destroys the meaning:\n  %s"
        % (len(lost), len(guards), "\n  ".join(lost)))


def test_the_headroom_guard_keeps_its_own_factor_beside_the_uniform_floor():
    """The one guard whose floor was already there, under a domain name.

    `required_factor` is a floor on a RATIO; `minimum_required` is a floor on a
    POPULATION. They are different quantities and the second is not a rename of
    the first - which is exactly the mistake that would have been made had the
    key simply been renamed to fit.
    """
    guards = load_guards()
    matching = [g for g in guards if str(g.get("id")) == "G3-driver-headroom"]
    assert len(matching) == 1, (
        "expected exactly one headroom guard, found %d: %r"
        % (len(matching), [g.get("id") for g in guards]))
    guard = matching[0]
    assert "required_factor" in guard, (
        "the headroom guard lost required_factor: %r" % sorted(guard))
    assert "minimum_required" in guard, (
        "the headroom guard carries no uniform floor: %r" % sorted(guard))
    assert guard["minimum_required"] != guard["required_factor"], (
        "the headroom guard's population floor holds the same value as its "
        "ratio floor (%r). A floor on how many probe levels the ceiling was "
        "taken over is not a rename of a floor on the ratio between two rates, "
        "and reusing the value is exactly how that distinction gets lost."
        % (guard["required_factor"],))


# --------------------------------------------------------------------------
# the live controls: the validator must be able to FAIL
# --------------------------------------------------------------------------

def test_an_empty_guards_array_is_a_violation():
    """CONSTRUCTED, not reasoned about. This is the failure the file exists for."""
    core = load_core()
    empty = {"guards": [], "all_guards_passed": True}
    violations = core.validate_guards(empty)
    assert violations, (
        "an EMPTY guards array produced no violation. all() over an empty "
        "sequence is True, so a guard array that was never populated would "
        "report every guard passing and nothing would say so.")
    assert any("EMPTY" in v.upper() for v in violations), violations


def test_a_guard_that_passes_below_its_floor_is_a_violation():
    core = load_core()
    record = a_valid_guard_record()
    assert core.validate_guards(record) == [], (
        "the control record is not valid to begin with, so breaking it proves "
        "nothing: %r" % core.validate_guards(record))
    broken = copy.deepcopy(record)
    broken["guards"][0]["population"] = 3
    violations = core.validate_guards(broken)
    assert violations, (
        "a guard reporting passed: true on a population of 3 against its own "
        "declared floor of 500 produced no violation")
    assert any("floor" in v for v in violations), violations


def test_a_guard_with_no_population_is_a_violation():
    core = load_core()
    broken = a_valid_guard_record()
    del broken["guards"][0]["population"]
    violations = core.validate_guards(broken)
    assert violations, "a guard with no population produced no violation"
    assert any("population" in v for v in violations), violations


def test_a_population_label_that_is_not_a_string_is_a_violation():
    """A label is a string, and a count with no name cannot be read.

    The shared validator checks the TYPE. EMPTINESS is checked against the
    published record instead, by the uniform-shape test above, so the two
    questions stay separable rather than one hiding the other.
    """
    core = load_core()
    broken = a_valid_guard_record()
    broken["guards"][0]["population_label"] = 12345
    violations = core.validate_guards(broken)
    assert violations, "a numeric population_label produced no violation"


def test_the_summary_flag_must_agree_with_the_guards_it_summarises():
    core = load_core()
    broken = a_valid_guard_record()
    broken["guards"][0]["passed"] = False
    violations = core.validate_guards(broken)
    assert violations, (
        "all_guards_passed stayed true over a guard that failed, and nothing "
        "objected")


def test_a_bare_list_is_reported_as_a_missing_summary_rather_than_passed():
    """There is no mode in which the top-level flag goes unchecked."""
    core = load_core()
    violations = core.validate_guards(a_valid_guard_record()["guards"])
    assert violations, "a bare guards list passed with no summary flag at all"
    assert any("all_guards_passed" in v for v in violations), violations


def load_finalize():
    """Load finalize.py BY PATH, with the repository root on sys.path.

    finalize.py imports the shared core by bare name from beside it, which is how
    it is actually run. Under pytest the repository root is not on sys.path - the
    tests directory is - so the insert makes that import resolve the same way it
    does at the command line, and is undone immediately afterwards.
    """
    root = str(ROOT)
    inserted = root not in sys.path
    if inserted:
        sys.path.insert(0, root)
    try:
        spec = importlib.util.spec_from_file_location(
            "finalize_under_test", str(ROOT / "finalize.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        if inserted and root in sys.path:
            sys.path.remove(root)
    return module


def test_finalize_refuses_to_publish_a_block_that_does_not_validate(monkeypatch):
    """The refusal is in the PROGRAM, not only in a test that reads its output.

    A test can only object after a bad record has been written and committed.
    This forces the validator to object and asserts two things about what
    finalize.py then does: it exits guard-fail, and it leaves the published
    record untouched. An invalid record on disk is worse than none, because the
    next reader cannot tell it from a valid one without re-running the thing they
    were trying to avoid re-running.
    """
    finalize = load_finalize()
    before = RESULTS_JSON.read_bytes()
    monkeypatch.setattr(
        finalize.canonkit, "validate_guards",
        lambda record: ["a constructed violation, so the refusal branch runs"])

    code = finalize.main([])

    after = RESULTS_JSON.read_bytes()
    assert code == 3, (
        "finalize.py returned %r over a guard block its own validator rejected; "
        "expected the guard-fail code 3" % (code,))
    assert after == before, (
        "finalize.py WROTE the record despite a violation. %d bytes before, %d "
        "after." % (len(before), len(after)))


def test_the_refusals_are_refusals_and_not_quiet_passes():
    """Every path that cannot make the comparison raises, and says how to fix it."""
    missing = ROOT / "results" / "no-such-record.json"
    with pytest.raises(Refused) as excinfo:
        load_guards(missing)
    text = str(excinfo.value)
    assert text.startswith("REFUSING:"), text
    assert "REPAIR:" in text, text
