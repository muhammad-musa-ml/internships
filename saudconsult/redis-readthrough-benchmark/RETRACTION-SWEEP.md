# Retracted figures: where they still appear, and what each appearance is

*2026-09-18*

Two numbers and one claim were retracted from this benchmark on 2026-07-31 (the
retracted list at the end of `results/RESULTS.md`). A retraction is only worth
anything if the retracted figure actually stops being asserted, and nothing here
was checking that. So this is the count: every place any retracted figure still
appears, in this repository and in the sibling log-search benchmark next to it,
with each appearance classified.

The point is the classification, not the total. A retraction record that quotes
what it withdrew is doing its job and must be left exactly as it is; a sentence
that still asserts the withdrawn figure is a defect. Those two look identical to
a grep, which is why a grep alone was never going to settle this.

---

## How it was run

Everything below is reproducible from these parameters alone.

| | |
|---|---|
| roots | `redis-readthrough-benchmark`, `example-search-benchmark` - both, not just this one |
| walked | every directory except `.git`, `__pycache__`, `.pytest_cache`, `.venv`, `node_modules` |
| extensions | `.py .md .json .yml .yaml .txt .toml .cfg .sh .js .ini .sql .log .csv`, plus any file whose name starts `Dockerfile` |
| excluded by name | **nothing.** No file is skipped. `results/RESULTS.md` is walked like every other document |
| adjudication radius | 12 lines either side of the hit |
| interpreter | CPython 3.13.5 |

### The needles

A figure has more than one spelling, and a needle that knows only one of them
reports a zero that means nothing. Each retracted figure is therefore hunted in
every form it could have been written in, and the word-form of the claim is
hunted in six spellings rather than one:

| # | needle | what it is |
|---|---|---|
| 1 | `98.8` | the withdrawn hit rate, written as a percentage |
| 2 | `0.9882` | the same figure written as a fraction |
| 3 | `0.9794` | what the withdrawn run moved that figure to |
| 4 | `97.94` | the same, as a percentage |
| 5 | `1.527` | the withdrawn closed-loop ratio |
| 6 | `152.7` | the same, as a percentage |
| 7 | `near-zero` / `near zero` / `near_zero` | the retracted claim, in words |
| 8 | `negligible` | the same claim, another spelling |
| 9 | `essentially zero` | the same claim |
| 10 | `almost no` / `almost nothing` / `almost zero` | the same claim |
| 11 | `close to zero` | the same claim |
| 12 | `virtually no` / `virtually zero` | the same claim |
| 13 | `vanishingly` | the same claim |

Needles 4, 6, 8, 9, 11, 12 and 13 found nothing in either repository; the only
place they match is the table above. They are listed because a needle that
returned zero is part of the population: dropping it would turn "we looked for
thirteen spellings" into "we looked for six", which is a different and much
weaker statement.

### The four arms, in order

No exclusion list. A hit nobody can place is `UNCLASSIFIED` and is a finding,
repaired by writing an adjudication beside the hit - never by quietly widening
the cue set until the hit stops matching.

1. **FALSE-POSITIVE** - the needle matched something that is not the figure at
   all. Two rules, both mechanical: a numeric needle whose match is preceded or
   followed by another digit is the *tail of a longer number*, not the figure;
   and a word-form needle with no `cache` or `hit rate` anywhere within four
   lines is ordinary English about some other subject.
2. **FROZEN** - a marker (`retract`, `withdraw`, `withdrawn`, `frozen`,
   `superseded`, `unvalidated`) sits within twelve lines, so the appearance is a
   record quoting what was withdrawn.
3. **LIVE** - everything else, **wherever it lives**. A live appearance inside
   `results/RESULTS.md` would still be a finding; the document gets no immunity
   from its name.
4. **UNCLASSIFIED** - reserved. Never silent.

The marker set was fixed before the scan was run, not after seeing what it
returned. That ordering matters: a cue set adjusted until the count reads zero
is measuring the adjuster.

---

## The counts

Two populations, because this document is itself a file full of retracted
figures. Both are measured and both print; neither is an exclusion.

| | the two repositories, before this file existed | the same, with this file in them |
|---|---:|---:|
| files scanned | 148 | 149 |
| needles applied | 13 | 13 |
| raw hits, by (file, line) | 16 | 50 |
| raw hits, by (file, line, needle) | 17 | 51 |
| **LIVE** | **0** | **0** |
| FROZEN | 14 | 38 |
| FALSE-POSITIVE | 3 | 13 |
| UNCLASSIFIED | 0 | 0 |
| sum of the four | 17 | 51 |
| sum == raw hits by (file, line, needle) | yes | yes |

So this document contributes 34 of the 51, all of them references and none of
them a live claim. The left column is the one that answers the question that was
asked - what does the benchmark itself still assert - and the right column is
what a scan run tomorrow will actually print, which is worth knowing before
somebody runs one and is surprised.

Two hit totals print in each column because one line can carry two different
retracted figures - `results/RESULTS.md` has exactly one such line - so a
per-line count and a per-needle count are genuinely different numbers, and
publishing only one of them invites a reader to reconcile two figures that were
never meant to match.

**`LIVE = 0` is the result.** It is worth exactly as much as the needle set and
the scope above, which is why both are written out in full rather than
summarised.

---

## Every appearance, classified

### This repository

All fifteen of this repository's own appearances, plus this file's thirty-four.

| file | line | needle | class | why |
|---|---:|---|---|---|
| `finalize.py` | 20 | `0.9882` | FROZEN | a superseded reading, quoted in the guard notes to record what the first, wrong guard saw |
| `finalize.py` | 23 | `0.9882` | FROZEN | the adjudication written beside it, naming it superseded and giving the live figure |
| `finalize.py` | 86 | `0.9882` | FROZEN | the same superseded reading in the G4 correction comment, adjudicated on its own line |
| `results/RESULTS.md` | 175 | `0.9882` | FROZEN | the retraction quoting the figure it withdrew |
| `results/RESULTS.md` | 175 | `0.9794` | FROZEN | the same line, the second figure on it |
| `results/RESULTS.md` | 177 | `1.527` | FROZEN | the retraction naming the ratio it withdrew |
| `results/RESULTS.md` | 191 | `near-zero` | FROZEN | the retraction quoting the claim it withdrew. **The only appearance of that claim left in the tree** |
| `results/sensitivity-mild-skew.json` | 8 | `1.527` | FROZEN | inside the withdrawal block added to that file |
| `results/sensitivity-mild-skew.json` | 10 | `1.527` | FROZEN | the same block's quotation note |
| `results/sensitivity-mild-skew.json` | 21 | `1.527` | FROZEN | the withdrawn run's own recorded ratio |
| `results/arm-off-mild.json` | 8 | `1.527` | FROZEN | the withdrawal block |
| `results/arm-off-mild.json` | 10 | `1.527` | FROZEN | the same block's quotation note |
| `results/arm-on-mild.json` | 8 | `1.527` | FROZEN | the withdrawal block |
| `results/arm-on-mild.json` | 10 | `1.527` | FROZEN | the same block's quotation note |
| `results/arm-off-mild.json` | 123 | `98.8` | **FALSE-POSITIVE** | `"rps": 6398.8` - a throughput number. See below |
| `RETRACTION-SWEEP.md` | 34 appearances | all thirteen needles | FROZEN and FALSE-POSITIVE | this document. See "this document is inside its own scan" |

Neither `benchlib/workload.py` nor the top-level `README.md` appears in that
table, and that is the whole point of the exercise: both carried a live
retracted claim on 2026-09-17 and neither carries one now.

### The sibling log-search benchmark

| file | line | needle | class | why |
|---|---:|---|---|---|
| `README.md` | 24 | `almost nothing` | **FALSE-POSITIVE** | about how many documents a query matches. No cache, no hit rate, nothing withdrawn |
| `esbench/queries.py` | 57 | `almost nothing` | **FALSE-POSITIVE** | the same sentence, in the comment it came from |

**Zero appearances of any retracted figure there** - which is what you would
expect, since none of these figures was ever that benchmark's. It was scanned
anyway, because "it can't be there" is a prediction and this is a measurement.

Note that a narrower needle set would have reported a bare zero for that
repository and been *right by accident*. The two hits above are the word-form
needles firing on ordinary English, and they are reported rather than tuned away
because a false positive you can see is worth more than a needle you have
quietly narrowed.

---

## The false positive that matters: a bare decimal is not a figure

`results/arm-off-mild.json`, line 123:

```json
  "rps": 6398.8,
```

A needle of `98.8` matches that. It is a requests-per-second reading and has
nothing to do with a hit rate, but nothing about the six characters says so.

This is the single most useful thing the sweep found, and it generalises:

- **A numeric needle must carry its unit or its context.** `98.8%` does not
  match `6398.8`; `98.8` does. Both were run here, which is how the case was
  found rather than assumed.
- **Or it must carry a digit boundary**, which is the rule used above: a match
  preceded or followed by another digit is the tail of a longer number.

It is also the reason no standing lint for retracted figures was built as part
of this work. A checker that fires on a throughput number in a results file
would train its reader to ignore it, and a checker that is routinely ignored is
worse than none. The population is now known - seventeen appearances across the
two repositories, of which zero are live and three are false positives - and
that is what a future checker should be designed against.

---

## The withdrawn run's own records

Three committed files are the machine records of the run the retraction
withdrew, and until now nothing in the tree distinguished them from a live run:

- `results/sensitivity-mild-skew.json`
- `results/arm-off-mild.json`
- `results/arm-on-mild.json`

Each now carries a top-level `withdrawn` block as its first key, naming the
date, the reason, the sibling files and `aggregate: false`. A script that
aggregates `results/` can branch on that key and **count the exclusion**; before
this, it would have folded a withdrawn run into a total and nobody could have
traced it afterwards.

They were not deleted. A withdrawn machine record is the evidence of what was
withdrawn, and deleting it would leave the retraction pointing at nothing.

---

## The live control

A search that found nothing and a search that never ran print the same thing, so
the needles were pointed at a file built to contain every one of them:

```
control file lines            = 13
needles applied               = 13
needles that fired            = 13 of 13
```

Every needle matched, including the eight that found nothing in either
repository. So the eight zeroes above are measurements of the repositories, not
of a broken search.

---

## This document is inside its own scan

`RETRACTION-SWEEP.md` quotes the retracted figures, so it is a population member
like any other file, and the counts above **include its own appearances**. It is
not excluded, because excluding a file by name is the exact move this whole
document argues against.

**None of its appearances is LIVE, and this sentence is the adjudication that
says so for all thirty-four of them**: every figure quoted anywhere in this file
is quoted in order to identify which figure was withdrawn, never to assert it,
and nothing in this repository may cite one as though it were a current number.
The classifier splits them into FROZEN and FALSE-POSITIVE on its own rules - the
needle table's rows have no cache or hit rate near them, so the word-form
needles land in the false-positive arm there - and that split is reported rather
than smoothed over, because a classifier whose output you edit to look tidier is
not a classifier any more.

The counts were measured with this file present and in its final wording, then
re-measured after the counts were filled in, and the two agreed. A number that
describes a document it lives inside has to be checked that way or it is just a
guess about itself.

---

## What this does not do

It is a measurement taken once, on 2026-09-18. Nothing re-runs it. If a
retracted figure is typed back into a sentence tomorrow, this file will not
notice - and it says so here rather than leaving a reader to assume a standing
guard exists. The one automatic guard that does exist is
`tests/test_hit_rate.py`, which is narrower: it binds the *current* hit rate to
the counted hits and misses in `results/results.json`, and fails the suite if
the documented number and the machine record ever disagree again.
