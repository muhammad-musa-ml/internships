# tests

What this directory is for, how to run it, and what it is pinned to.

## What is tested here

Not the benchmark. The benchmark is a measurement; re-running it is how you test
it, and `finalize.py` already refuses to publish a run whose integrity guards
did not pass.

What is tested here is the far cheaper failure that no run catches: **a number
written into prose drifting away from the machine record it came from.** The
hit rate appears in `benchlib/workload.py`'s docstring and in `README.md`, and
it is a function of exactly two counted integers in
`results/results.json` - the `hits` and `misses` of the `G4a` guard. Anything
else written in either place is wrong by definition, and nothing re-derives it.

So `test_hit_rate.py` recomputes the rate from those integers on every run and
compares it against what each document actually says, at the precision the
document is written to. If they disagree, the suite fails and the message names
both numbers, the guard it read, and the counts behind it.

It refuses - loudly, rather than passing - when the guard is missing, when two
guards match, when either count is absent, and when `hits + misses` is zero. A
rate over a zero denominator measured nothing; reporting that as agreement is
the failure this directory exists to prevent.

## How to run it

From the repository root:

```
python -m pytest tests -q
```

Nothing else is needed. The tests import only the standard library plus
`pytest`, and read two files that are already committed here, so there is no
service to start, no container to build and no network access involved.

## What this was last executed with

| | |
|---|---|
| interpreter | CPython 3.13.5 on Windows 11 |
| pytest | 9.0.3 |
| command | `python -m pytest tests -q`, from the repository root |
| collected | 13 tests |
| date | 2026-09-18 |

Both the command and the collection count above were **run before they were
written down**. That is deliberate: a documented command nobody executed is a
dead instruction, and this repository has already shipped one.

Any CPython 3.11 or newer with `pytest` installed will do. The version above is
recorded because it is what the row was measured on, not because it is a floor.

## Why the figure is not computed at import time

The obvious alternative is to have `benchlib/workload.py` read
`results/results.json` at import and interpolate the rate into its own
docstring. That was considered and rejected twice over:

- it would make a **workload generator depend on its own results**, so the
  module could not be imported before a run had produced them; and
- it would make the documented figure agree with the record **by construction**,
  which is indistinguishable from not checking it at all.

The figure stays a written number that a human can read without running
anything. This suite is what stops it from quietly becoming the wrong one.
