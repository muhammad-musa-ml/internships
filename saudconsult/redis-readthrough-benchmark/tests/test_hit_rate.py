"""The documented hit rate must equal the one the machine record implies.

WHY THIS TEST EXISTS
--------------------
Two sentences in this repository printed a hit rate that the run's own guard
record contradicts. `results/results.json` carries the counted `hits` and
`misses` for the `G4a` guard, and those two integers are the authority: the rate
is a function of them and of nothing else. Prose that disagrees with them is the
defect, and prose is exactly the thing no run re-checks.

So the number is recomputed here, from the record, every time the suite runs. If
anyone edits a documented figure to a value the counts do not produce - or
re-runs the benchmark and leaves the prose behind - the suite fails and names
both numbers.

WHAT WAS DELIBERATELY NOT DONE
------------------------------
The rate is NOT computed at import time inside `benchlib/workload.py` and
interpolated into its docstring. A workload generator must not depend on its own
results: that would make the module unimportable before a run, and it would make
the documented figure agree with the record by construction, which is the same
as not checking it. The figure stays a written number; the test is what binds it.

REFUSAL, NOT A QUIET PASS
-------------------------
Every path that cannot make the comparison RAISES rather than returning a
neutral verdict:

  * no guard whose id starts `G4a`          -> refused
  * more than one such guard                -> refused
  * `hits` or `misses` absent               -> refused
  * `hits + misses == 0`                    -> refused
  * no documented figure found in a source  -> refused
  * more than one documented figure found   -> refused

A comparison that examined nothing is not a comparison that succeeded, and a
zero population must never read as agreement.

HOW TO RUN IT
-------------
From the repository root, with any CPython 3.11 or newer that has pytest:

    python -m pytest tests -q

See `tests/README.md`, which records the interpreter and pytest version this was
last executed with.
"""
from __future__ import annotations

import ast
import json
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
RESULTS_JSON = ROOT / "results" / "results.json"
WORKLOAD_PY = ROOT / "benchlib" / "workload.py"
README_MD = ROOT / "README.md"

GUARD_ID_PREFIX = "G4a"

# The stored rounded rate in the guard record, to this many decimal places. The
# raw counts remain the authority; this pins the record's own rounding so a
# hand-edited `measured_hit_rate` cannot drift away from the integers beside it.
STORED_RATE_DECIMALS = 4

# Anchored on the PHRASE, not on a bare percentage. A bare `\d+\.\d+%` needle
# also matches the ~90% figure in the uniform-draw paragraph, and a needle that
# matches two different claims cannot report on either. The optional HTML
# comment lets the figure later be wrapped for templated rendering without
# silently un-binding this test.
_COMMENT = r"(?:<!--[^>]*-->)?"
DOCUMENTED_RATE_RE = re.compile(
    r"measured\s+hit\s+rate[^%\n]*?" + _COMMENT
    + r"\s*([0-9]+(?:\.[0-9]+)?)\s*" + _COMMENT + r"\s*%",
    re.IGNORECASE,
)


class Refused(Exception):
    """A comparison that could not be made. Never a pass."""


def _refuse(reason: str, repair: str) -> "Refused":
    return Refused("REFUSING: %s REPAIR: %s" % (reason, repair))


# --------------------------------------------------------------------------
# reading the machine record
# --------------------------------------------------------------------------

def load_guards(path: pathlib.Path = RESULTS_JSON) -> list:
    if not path.exists():
        raise _refuse(
            "there is no %s, so there is no counted hits/misses pair to "
            "compare a documented rate against." % path.name,
            "run the benchmark, which writes the guard record.")
    record = json.loads(path.read_text(encoding="utf-8"))
    guards = record.get("guards")
    if not isinstance(guards, list):
        raise _refuse(
            "%s carries no guards[] array." % path.name,
            "re-run finalize.py, which writes the guard records.")
    return guards


def find_guard(guards: list, prefix: str = GUARD_ID_PREFIX) -> dict:
    """The one guard whose id starts with `prefix`, or a refusal."""
    matching = [g for g in guards
                if isinstance(g, dict) and str(g.get("id", "")).startswith(prefix)]
    if not matching:
        raise _refuse(
            "no guard id starts with %r; the %d guard(s) present are %r."
            % (prefix, len(guards),
               [g.get("id") for g in guards if isinstance(g, dict)]),
            "re-run finalize.py so the cache-exercised guard is recorded, or "
            "correct the prefix this test looks for.")
    if len(matching) > 1:
        raise _refuse(
            "%d guards start with %r (%r), so which one the documented rate "
            "refers to is ambiguous."
            % (len(matching), prefix, [g.get("id") for g in matching]),
            "give the guards distinct ids, one per measured quantity.")
    return matching[0]


def hit_rate(guard: dict) -> tuple:
    """Return (rate, hits, misses, total) or refuse.

    The rate is a function of the two counted integers. `measured_hit_rate` in
    the record is a rounding OF this, never an input TO it.
    """
    hits = guard.get("hits")
    misses = guard.get("misses")
    for name, value in (("hits", hits), ("misses", misses)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise _refuse(
                "guard %r has no integer %s (found %r), so no rate can be "
                "computed from it." % (guard.get("id"), name, value),
                "re-run finalize.py, which writes both counts.")
        if value < 0:
            raise _refuse(
                "guard %r reports a negative %s (%d)."
                % (guard.get("id"), name, value),
                "re-run the benchmark; a negative count is a bookkeeping bug.")
    total = hits + misses
    if total == 0:
        raise _refuse(
            "guard %r reports hits=0 and misses=0, so the denominator is zero "
            "and the run measured no requests at all." % guard.get("id"),
            "re-run the benchmark; a rate over a zero denominator measured "
            "nothing and must not be reported as a rate.")
    return hits / total, hits, misses, total


# --------------------------------------------------------------------------
# reading the documented figure
# --------------------------------------------------------------------------

def module_docstring(path: pathlib.Path) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    doc = ast.get_docstring(tree)
    if not doc:
        raise _refuse(
            "%s has no module docstring to read a figure from." % path.name,
            "restore the docstring, or point this test at the prose that "
            "actually carries the figure.")
    return doc


def documented_rate(text: str, where: str) -> str:
    """The one documented percentage, as the STRING that was written.

    Returned as a string on purpose: the number of decimal places written is
    the precision the comparison is made at, and parsing to float loses it.
    """
    found = DOCUMENTED_RATE_RE.findall(text)
    if not found:
        raise _refuse(
            "no documented measured-hit-rate percentage was found in %s, so "
            "there is nothing to compare against the machine record." % where,
            "state the measured hit rate in %s, or point this test at the "
            "prose that does." % where)
    if len(set(found)) > 1:
        raise _refuse(
            "%s states %d DIFFERENT measured hit rates (%r); a document that "
            "disagrees with itself cannot be checked against a record."
            % (where, len(set(found)), sorted(set(found))),
            "state one figure, once, and let the others refer to it.")
    return found[0]


def compare(documented: str, computed: float, guard_id: str,
            hits: int, misses: int, where: str) -> tuple:
    """(agrees, message). Compared at the precision the document was written to."""
    decimals = len(documented.split(".")[1]) if "." in documented else 0
    expected = round(computed * 100.0, decimals)
    written = float(documented)
    agrees = abs(expected - written) < 10.0 ** -(decimals + 6)
    message = (
        "%s documents %s%% as the measured hit rate; guard %r counts "
        "hits=%d misses=%d total=%d, which is %.10f -> %s%% at the %d decimal "
        "place(s) the document is written to. documented=%s%% computed=%s%% "
        "-- they %s."
        % (where, documented, guard_id, hits, misses, hits + misses,
           computed, format(expected, ".%df" % decimals), decimals,
           documented, format(expected, ".%df" % decimals),
           "agree" if agrees else "DISAGREE"))
    return agrees, message


# --------------------------------------------------------------------------
# the tests
# --------------------------------------------------------------------------

def test_the_guard_record_is_present_and_names_its_population():
    guards = load_guards()
    assert len(guards) > 0, "results.json carries zero guards; nothing to read"
    guard = find_guard(guards)
    rate, hits, misses, total = hit_rate(guard)
    assert total > 0, guard
    assert 0.0 < rate < 1.0, (
        "guard %r reports a rate of %r, which is not a rate a real cache "
        "produces (a 0 or a 1 means the cache was never exercised or was "
        "pre-seeded outside the measured window)" % (guard.get("id"), rate))


def test_the_workload_docstring_hit_rate_equals_the_machine_record():
    guard = find_guard(load_guards())
    computed, hits, misses, _total = hit_rate(guard)
    written = documented_rate(module_docstring(WORKLOAD_PY),
                              "benchlib/workload.py's module docstring")
    agrees, message = compare(written, computed, str(guard.get("id")),
                              hits, misses,
                              "benchlib/workload.py's module docstring")
    assert agrees, message


def test_the_readme_hit_rate_equals_the_machine_record():
    """The same figure lives in the README, and an unbound copy is how it drifts."""
    guard = find_guard(load_guards())
    computed, hits, misses, _total = hit_rate(guard)
    written = documented_rate(README_MD.read_text(encoding="utf-8"), "README.md")
    agrees, message = compare(written, computed, str(guard.get("id")),
                              hits, misses, "README.md")
    assert agrees, message


def test_the_two_documents_state_the_same_figure():
    """The two copies must not DISAGREE. They may be written to different
    precisions, and since the README's figure became generated they are.

    This test compared the two as STRINGS while both were typed by hand, and
    that was the right comparison then: two hand-typed copies written to
    different precisions is itself a drift risk, because the second one is
    someone's rounding rather than the record's.

    The README's copy is no longer typed. It is computed from the guard record
    by `derive.py`, written into a paired region by `render.py`, and re-rendered
    and byte-compared on every check, so it carries the record's own full
    precision and cannot drift from it at all. The docstring is still a typed
    copy and is still bound to the record by
    `test_the_workload_docstring_hit_rate_equals_the_machine_record` above.

    So the comparison moves to the coarser of the two precisions, which is the
    only precision at which both documents make a claim. It still
    DISCRIMINATES: the wrong figure this pair of tests was written to catch
    differs from the record in the first decimal place, so it fails here too.
    """
    doc = documented_rate(module_docstring(WORKLOAD_PY), "workload docstring")
    readme = documented_rate(README_MD.read_text(encoding="utf-8"), "README.md")
    decimals = len(doc.split(".")[1]) if "." in doc else 0
    rounded = format(round(float(readme), decimals), ".%df" % decimals)
    assert float(doc) == float(rounded), (
        "the workload docstring says %s%% and README.md says %s%%, which is "
        "%s%% at the %d decimal place(s) the docstring is written to; two "
        "copies of one measurement that disagree mean at least one of them is "
        "wrong" % (doc, readme, rounded, decimals))


def test_the_stored_rounded_rate_agrees_with_the_counts_beside_it():
    guard = find_guard(load_guards())
    computed, hits, misses, total = hit_rate(guard)
    stored = guard.get("measured_hit_rate")
    assert isinstance(stored, float), (
        "guard %r has no float measured_hit_rate" % guard.get("id"))
    assert round(computed, STORED_RATE_DECIMALS) == round(stored, STORED_RATE_DECIMALS), (
        "guard %r stores measured_hit_rate=%r but its own counts "
        "(hits=%d misses=%d total=%d) give %.10f -> %r"
        % (guard.get("id"), stored, hits, misses, total, computed,
           round(computed, STORED_RATE_DECIMALS)))


def test_a_drifted_figure_is_actually_caught():
    """The live control: the comparison must be able to FAIL, not only to pass.

    A check nobody has seen fire is a check nobody has evidence works. This
    feeds the real computed rate a deliberately wrong documented figure and
    asserts the verdict flips and the message names both numbers.
    """
    guard = find_guard(load_guards())
    computed, hits, misses, _total = hit_rate(guard)
    true_figure = format(round(computed * 100.0, 1), ".1f")
    drifted = format(round(computed * 100.0, 1) + 0.2, ".1f")
    assert drifted != true_figure

    agrees_true, _ = compare(true_figure, computed, str(guard.get("id")),
                             hits, misses, "a control")
    agrees_drift, message = compare(drifted, computed, str(guard.get("id")),
                                    hits, misses, "a control")
    assert agrees_true, "the control's TRUE figure did not agree; the comparison is broken"
    assert not agrees_drift, "a %s%% drift from %s%% was not caught" % (drifted, true_figure)
    assert drifted in message and true_figure in message, message
    assert str(guard.get("id")) in message, message


def test_a_missing_guard_is_refused_rather_than_passed():
    guards = [{"id": "G1a-equivalence-server-attested", "passed": True},
              {"id": "G5-two-clocks", "passed": True}]
    with pytest.raises(Refused) as excinfo:
        find_guard(guards)
    text = str(excinfo.value)
    assert text.startswith("REFUSING:"), text
    assert "REPAIR:" in text, text
    assert GUARD_ID_PREFIX in text, text


def test_two_matching_guards_are_refused_rather_than_guessed_between():
    guards = [{"id": "G4a-cache-exercised", "hits": 1, "misses": 1},
              {"id": "G4a-cache-exercised-again", "hits": 2, "misses": 2}]
    with pytest.raises(Refused) as excinfo:
        find_guard(guards)
    assert "ambiguous" in str(excinfo.value), str(excinfo.value)


def test_a_zero_denominator_is_refused_rather_than_passed():
    with pytest.raises(Refused) as excinfo:
        hit_rate({"id": "G4a-cache-exercised", "hits": 0, "misses": 0})
    text = str(excinfo.value)
    assert text.startswith("REFUSING:"), text
    assert "zero" in text.lower(), text
    assert "REPAIR:" in text, text


def test_absent_counts_are_refused_rather_than_treated_as_zero():
    with pytest.raises(Refused) as excinfo:
        hit_rate({"id": "G4a-cache-exercised", "measured_hit_rate": 0.9857})
    assert "hits" in str(excinfo.value), str(excinfo.value)


def test_a_document_with_no_figure_is_refused_rather_than_passed():
    with pytest.raises(Refused) as excinfo:
        documented_rate("a paragraph that states no rate at all", "a control")
    assert str(excinfo.value).startswith("REFUSING:"), str(excinfo.value)


def test_a_document_stating_two_different_figures_is_refused():
    text = ("the measured hit rate of 98.6% is a warm-window number, and "
            "elsewhere the measured hit rate (~97.1%) is claimed")
    with pytest.raises(Refused) as excinfo:
        documented_rate(text, "a control")
    assert "DIFFERENT" in str(excinfo.value), str(excinfo.value)


def test_the_needle_ignores_an_unrelated_percentage():
    """The uniform-draw paragraph states ~90%, which is not the measured rate."""
    text = ("A uniform draw reaches roughly 90% once the cache is warm. "
            "The measured hit rate (~98.6%) reflects the warm window.")
    assert documented_rate(text, "a control") == "98.6"
