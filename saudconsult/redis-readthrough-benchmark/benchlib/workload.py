"""The seeded request workload, and an honest account of its skew.

WHY THE KEY DISTRIBUTION IS SKEWED, AND WHY THAT IS NOT RIGGING
--------------------------------------------------------------
A read-through cache earns its place when the same keys recur, and how strongly
they recur is what this module controls. An earlier version of this paragraph
overstated that badly, and its claim was RETRACTED on 2026-07-31; the exact
wording is preserved in the retracted list in results/RESULTS.md, item 14, and
is deliberately not repeated here, because one authoritative copy of a withdrawn
sentence is a record and three copies are a rumour.

What it got wrong is that a UNIFORM draw over 20,000 tenants makes a cache
useless. It does not, and the sequence arithmetic settles it without a run.
`theoretical_max_hit_rate` in the results records is defined as every request
after the first for a given key; a uniform draw over 20,000 tenants touches
essentially all of them within 200,000 requests (19,999 expected), so the
ceiling is 1 - 19999/200000 = 0.9000. About 90%. That is not a cache failing.

What skew actually changes is the SIZE of the working set that has to stay
resident, and therefore how a cache behaves under memory pressure and eviction -
not whether it helps at all. Reporting a uniform draw as "caches don't work"
would be as dishonest as the opposite.

Real multi-tenant traffic is heavily skewed: a small number of tenants generate
most requests. This module draws from a Zipf distribution to model that, and
`describe()` reports the resulting concentration (what share of requests the top
1% of tenants receive) so a reader can judge the assumption instead of taking it
on faith. **The skew is stated in the results, and the same seeded sequence is
replayed against BOTH arms in the same order**, so it can never advantage one.

WHAT THE MEASURED WINDOW ACTUALLY IS - CORRECTED 2026-07-31
-----------------------------------------------------------
An earlier version of this docstring claimed "the cache is NOT pre-warmed: the
cached arm pays its own cold misses inside the measured window." **That was false**
and the G4 guard caught it: every concurrency level runs an UNCOUNTED WARMUP before
its measured run, so by the time measurement starts the hot keys are already
resident. The measured condition is therefore **steady-state warm**, which is the
right condition for a sustained-throughput claim - but it must be stated, not
implied. The measured hit rate (~98.9%) reflects that, and is reported as such:
706,071 hits against 7,684 misses over 713,755 counted requests, which is what
the G4a guard record in results/results.json holds and what tests/test_hit_rate.py
recomputes on every run rather than trusting this sentence.

THOSE THREE COUNTS MOVED ON 2026-09-18, when both arms were re-measured end to
end on a machine with nothing else running on it. The figure this sentence
carried before was 497,982 hits against 7,245 misses over 505,227 counted
requests -- a real reading of a real run, superseded by a larger one rather than
corrected. It is deliberately not restated as a percentage here: the test above
refuses a document that states two different rates, on the ground that a
document disagreeing with itself cannot be checked against a record, and it is
right to. The test is also the reason this paragraph exists at all -- an unbound
copy of a measured figure is a sentence that goes quietly false the next time
anyone measures, and this one was caught by a failing test rather than by a
reader.

Redis is flushed before the cached arm begins, so the run as a whole starts cold;
it is the per-level warmup, not a pre-seeding step, that makes the measured window
warm.
"""
from __future__ import annotations

import random
from collections import Counter

SEED = 20260731


def build_sequence(n_requests: int, n_tenants: int, zipf_a: float = 1.2) -> list[int]:
    """Return a deterministic tenant-id sequence of length `n_requests`.

    `random.Random.zipf` does not exist, so this uses the standard inverse-rank
    construction: sample a Zipf-distributed RANK, then map rank -> tenant id
    through a fixed seeded permutation, so the hot tenants are not simply the
    lowest ids (which would let the database's own clustering flatter the result).
    """
    rnd = random.Random(SEED)
    ids = list(range(1, n_tenants + 1))
    rnd.shuffle(ids)                       # rank -> tenant id, fixed by SEED

    # Zipf weights over ranks 1..n_tenants, sampled by inverse CDF.
    weights = [1.0 / (r ** zipf_a) for r in range(1, n_tenants + 1)]
    total = sum(weights)
    cum, acc = [], 0.0
    for w in weights:
        acc += w
        cum.append(acc / total)

    import bisect
    seq = []
    for _ in range(n_requests):
        u = rnd.random()
        rank = bisect.bisect_left(cum, u)
        seq.append(ids[min(rank, n_tenants - 1)])
    return seq


def describe(seq: list[int], n_tenants: int) -> dict:
    """Report the concentration so the reader can price the assumption."""
    c = Counter(seq)
    ranked = sorted(c.values(), reverse=True)
    total = len(seq)
    top1pct_n = max(1, n_tenants // 100)
    return {
        "requests": total,
        "distinct_tenants_touched": len(c),
        "n_tenants_total": n_tenants,
        "share_top_1pct_of_tenants": round(sum(ranked[:top1pct_n]) / total, 4),
        "share_top_10_tenants": round(sum(ranked[:10]) / total, 4),
        "theoretical_max_hit_rate": round((total - len(c)) / total, 4),
        "note": "theoretical_max_hit_rate is the ceiling a perfect cache could reach "
                "on this sequence: every request after the first for a given key. The "
                "measured hit rate must be at or below it.",
    }
