# Measured results - 2026-07-31 (SUPERSEDED)

**This document is the record of the campaign of 2026-07-31. It was SUPERSEDED
on 2026-09-18 by a re-run on the same machine, and its headline figure is
REFUTED rather than merely out of date.** It is kept, unedited below this
header, because a superseded record is the only evidence of what was superseded;
deleting it would leave the correction pointing at nothing.

Three things a reader needs before reading on:

- **Its capacity ratio is refuted, not stale.** The re-run's open-loop ladder
  establishes a bracket for each arm, and the ratio implied by those brackets
  does not contain the figure below. The current numbers, their populations and
  that bracket are in `results/RESULTS.md`; the run itself is in `RUN-RECORD.md`.
- **Every number below rests on `capacity-open-loop.json`, which has no producer
  in this directory.** It was written by hand from a run whose own records are
  not in the tree. That alone is reason enough not to quote it.
- **Its retracted list is NOT here.** Items thirteen and fourteen stay in
  `results/RESULTS.md`, where `benchlib/workload.py` points a reader at them by
  name. The numbering below is the list they belong to.

Nothing below this line has been edited.

---

# Measured results - 2026-07-31

Every number here comes from `results.json` (closed-loop sweep + guards) and
`capacity-open-loop.json` (the fixed-tail capacity test). Nothing is estimated.

**This document reports the result AFTER two independent adversarial reviews,
both of which found real defects. The
headline moved as a result. The pre-review numbers and what was wrong with them
are kept below rather than quietly replaced.**

## Environment

| | |
|---|---|
| Postgres | `postgres:16.4`, `shared_buffers=512MB`, prewarmed |
| Redis | `redis:7.4-alpine`, 512 MB, `allkeys-lru`, no persistence |
| Service | FastAPI + asyncpg (pool 8-32) + `redis-py`, uvicorn, 4 workers |
| Load generator | k6 v2.1.0 in Docker, on the compose network |
| Dataset | 20,000 tenants / 240,000 features / 120,000 quotas = 34.0 MiB |
| Resolve plan | index scans only, `Execution Time: 0.095 ms`, all buffer hits |
| Workload | seeded Zipf a=1.2; top 10 tenants = 50.5% of requests |

## HEADLINE - capacity at a genuinely fixed p99 (open loop)

Highest offered arrival rate that held **p99 <= 250 ms** with <1% dropped
iterations and zero errors:

| | uncached | cached | ratio |
|---|---|---|---|
| **Capacity at p99 <= 250 ms** | **5,469.9 rps** | **7,457.5 rps** | **1.363x** |
| p99 at that rate | 173.65 ms | 53.90 ms | |
| p50 at that rate | 28.13 ms | 4.87 ms | |
| first rate that FAILED | 6,000 (p99 **1,500 ms**, 12,012 dropped) | 8,000 (p99 138 ms, 2,070 dropped) | |

The pass/fail boundary is clean and monotone: uncached passes 4000/4500/5000/5500
and fails from 6000; cached passes 4000/6000/6500/7000/7500 and fails from 8000.

**Server-side handler time (p50), sampled separately at low concurrency:
1,050 us -> 433 us = 2.42x.**

## Why there are two methods, and why the first one was not enough

The original measurement was a **closed-loop** `constant-vus` sweep. Both reviews
independently called it the critical flaw, and they were right: with a fixed VU
count each virtual user waits for its own response before issuing the next, so
**when the service slows the generator silently offers less load**. The tail never
climbs to the ceiling, so "highest rps with p99 <= 250 ms" degenerates into "peak
rps", and the 250 ms figure does no work at all. That is coordinated omission.

The open-loop `constant-arrival-rate` test above fixes the offer rate independently
of service speed and reports `dropped_iterations` when the generator cannot keep
up, so an arm that cannot sustain a rate is **visible instead of quietly throttled**.

The two methods agree closely, which is the reassuring part:

| method | uncached | cached | ratio |
|---|---|---|---|
| closed loop (peak, tail non-binding) | 6,751.2 | 9,475.7 | 1.404x |
| **open loop (true fixed-tail capacity)** | **5,469.9** | **7,457.5** | **1.363x** |

The closed-loop numbers are ~20% higher in absolute terms - exactly the
overstatement coordinated omission predicts - but the **ratio** is stable to within
3%. Only the open-loop figure may be described as "at a fixed p99 of 250 ms".

## Integrity guards (closed-loop artifacts) - all passed

| guard | result |
|---|---|
| **G1a equivalence, server-attested** | 3,000 keys, 0 mismatches |
| **G1b equivalence, client-recomputed** | 3,000 keys, 0 mismatches - recomputed from the delivered payload, does **not** trust the service's own checksum field |
| **G2 coverage** | 3,000 keys compared (min 500) |
| **G3 driver headroom** | generator ceiling 32,516 rps vs fastest arm 9,475.7 = **3.43x** |
| **G4a cache exercised** | 497,982 hits / 7,245 misses; hit rate 0.9857 |
| **G4b keys bounded** | Redis held 10,536 keys; sequence requested 11,106 distinct |
| **G5 two clocks** | throughput +2,724 rps and handler time -617 us agree on direction |

## Everything the reviews found, and what happened to it

**Fixed, and the headline moved:**

1. **Coordinated omission** (both reviewers, critical). The p99 ceiling never bound.
   Fixed by adding the open-loop capacity test, which is now the headline.
   Effect: uncached 6,751 -> 5,470 rps; the honest ratio is 1.363x.
2. **The warmup replayed the measured key stream.** Warmup and measured runs are
   separate k6 processes, so `__VU`/`__ITER` restarted and the measured window
   asked for exactly the keys the warmup had just loaded - hit rate climbed
   0.9375 -> 0.9997 across the ladder. Fixed with disjoint `OFFSET` windows.
   Effect: the ratio moved **up** (1.329 -> 1.404), the opposite of the reviewer's
   predicted ~1.22.
3. **VU start clustering.** `__VU * 100003 mod 200000` collapsed all VU offsets
   into two narrow bands. Replaced with the coprime 99991.
4. **G1 was self-attested.** The client compared a checksum the *server* computed
   and stored inside the cached value. Added G1b, recomputed client-side from the
   delivered payload.
5. **Arms were reported at different concurrency** (256 vs 128 VUs). After the
   offset fix both peak at 256; the open-loop test removes the question entirely.

**Verified and found overstated:**

6. "The ratio is dominated by benchmark instrumentation (sha256 + orjson)."
   **Measured: ~31 us/request** for canonicalization + SHA-256 using stdlib - an
   upper bound, since the service uses the faster orjson - against a 1,050 us
   handler. That is ~3%, not a dominant confound. The finding is real in kind and
   small in size; the ratio does not isolate the Postgres resolve alone, and that
   is now stated rather than implied.

**Subsequently FIXED rather than left as limitations:**

7. **Replication (was: single unreplicated samples).** Now replicated - see the
   matched-load section below. It also uncovered something a single run hid: the
   uncached arm is **bimodal at 6,000 rps** on this host.
9. **Provenance (was: no manifest).** `provenance.py` now records the sha256 of
   all 14 source files, the sha256 of the exact sequence, resolved image
   **digests** (all three images are digest-pinned, no `:latest`), and the
   service's self-reported config from a new `/config-info` endpoint. The `--tag`
   bug that let one run overwrite another's raw exports is fixed in both runners -
   raw files are now tag-scoped.
10. **`pg_prewarm` now warms INDEXES too**, read from `pg_indexes` rather than
    hard-coded: 8 relations, 5 of them indexes. **This measurably changed the
    result** - it sped the UNCACHED arm up (p99 at 5,500 rps fell from 174 ms to
    37-70 ms), i.e. fixing it worked against the cache, which is the direction that
    matters for honesty.
11. **The plan guard is hardened.** It now `PREPARE`s and EXPLAINs the *actual
    parameterized statement* the service runs (Postgres can pick a different
    generic plan for a prepared statement), samples **6 tenants**, and asserts
    positively: >=3 index scans, no sequential scan, and **zero execution-time disk
    reads**. Proven to bite: with `features_tenant_id_idx` dropped the plan
    degrades to a Seq Scan at 12 ms vs 0.09 ms and the guard refuses to proceed.

**Still open, honestly:**

8. **G4a/G4b remain loose.** Falsifiable but weak; rewritten after seeing a
   failing run, disclosed inline at `finalize.py`.
12. **No stampede protection, single host, warm steady state** (98.9% hit rate).
13. **Measurement stability near saturation is poor on this host** - see below.

## Matched-load comparison, replicated (the most trustworthy result here)

Knee-hunting proved unstable, so both arms were run at the **same offered rate**,
3 replicates each. Same work offered; which arm delivers it?

**6,000 rps offered, open loop, 3 reps per arm:**

| | cached | uncached |
|---|---|---|
| delivered rps | 5,976.6 / 5,984.3 / 5,997.5 | 4,394.5 / 4,413.9 / 4,579.3 |
| p50 | 4.7 / 4.5 / 7.7 ms | **372.5 / 369.2 / 360.2 ms** |
| p99 | 39.6 / 57.2 / 77.3 ms | **1,647 / 1,612 / 1,513 ms** |
| dropped | 0.07-0.21% | **21.6-24.9%** |
| verdict | **passed 3/3** | **failed 3/3** |

Median p99 is **28.2x** better cached (57 ms vs 1,612 ms); median delivered
throughput ratio **1.356x**. The three replicates per arm agree tightly.

**Three independent methods now converge on the same ratio:** closed-loop 1.404x,
open-loop capacity 1.363x, matched-load delivered 1.356x.

### The instability, disclosed rather than hidden

An **earlier single** uncached run at this same 6,000 rps **passed** (5,993.9 rps,
p99 72.5 ms, 0.06% dropped). Three later replicates all failed catastrophically at
the identical rate. The uncached arm is bimodal near saturation on this host, and
which mode you land in depends on conditions I did not control (background load
from other containers and builds on the same machine).

That earlier observation is **kept, not discarded** - discarding the run that
disagrees is how a benchmark lies. It is the reason the capacity knee is reported
as unstable rather than as a point, and the reason the matched-load block above,
not any single knee figure, is the result worth quoting.

## Does this support the published claim?

The bullet under test read:

> raised sustained throughput from **~450 to ~1,200 requests/sec** at a fixed p99
> of 250 ms

**No.** That is a 2.67x claim. Measured, open-loop, at a genuinely fixed tail:
**1.363x** (5,470 -> 7,457 rps). The absolute figures are also more than an order of
magnitude off - this service sustains ~5,500 rps uncached, not ~450.

**What the evidence does support:**

- A read-through cache in front of a repeated per-request Postgres resolve raises
  capacity at a fixed p99 by **~1.36x**, and cuts p99 at that load from 174 ms to
  54 ms.
- **The strongest true number is server-side: 1,050 us -> 433 us, a 2.42x reduction
  in the handler's own work.**
- **Throughput improved far less than handler time did** - 1.36x against 2.42x -
  because the Postgres resolve was never the whole per-request cost. Once cached
  away, HTTP parsing, serialization and scheduling dominate and are unchanged.
  Removing a bottleneck returns the ratio of the part you removed, not the ratio of
  the part you measured.

## What this benchmark is NOT

It does not establish what happened at any company. It is a reproducible
measurement of the mechanism at a stated scale on stated hardware, built so a claim
about that mechanism can be defended with numbers that exist. A bullet resting on
it must describe the measured configuration, not borrow its authority for a
different one.
