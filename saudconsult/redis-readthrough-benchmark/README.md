# Redis read-through cache benchmark

<!-- artifact:date:begin -->
Measured <!--artifact:key:dated_at-->2026-09-18T05:22:01.784149-05:00<!--/artifact:key--> on my own machine.
<!-- artifact:date:end -->

<!-- artifact:claim:begin -->
**What this is.** A standalone measurement of the MECHANISM behind a claim made
about work I did as Data Science & Software Engineering Intern at SAUDCONSULT
(Saudi Consulting Services for Engineering Consultancy), on site in Riyadh,
from 2024-06 to 2024-08. It is deliberately NOT described as a from-scratch
reproduction of the thing I built there, because it is not one: the service I
fronted with this cache was never load-tested inside the firm, so there is no
measurement of it to reproduce. What this directory does is build the mechanism
itself -- a Redis read-through cache in front of a repeated per-request
Postgres lookup -- from scratch on my own machine and measure it, so the order
of magnitude behind the claim can be checked instead of taken. It was built and
measured on the date above, and this repository's commit dates are the build's
rather than the placement's.

**Claim under test.** This artifact exists to back one portfolio row, named here
so a reader can check it rather than take it.

| Field | Value |
|---|---|
| Employer | SAUDCONSULT (Saudi Consulting Services for Engineering Consultancy) |
| Role | Data Science & Software Engineering Intern |
| Placement | 2024-06 to 2024-08, on site in Riyadh |
| Workstream | P5 |
| Canon | saudconsult |
| Bullet id | saudconsult:P5-B3 |
| Bullet text, verbatim | Fronted the certified-metric query path with a Redis read-through cache over precomputed rows, sized from a hot-key profile; the p99 174ms to 54ms pair is measured on a standalone open-loop benchmark, not on this service. |
| Measured counterpart | the tail-latency pair and the capacity bracket rendered below, both from the run this file is dated by |
| Verdict | SUPPORTS-WITH-REVISION |

**THIS IS THE SUBSTITUTE MEASUREMENT FOR THAT ROW, NOT THE WORKSTREAM'S OWN
ARTIFACT.** The service that row describes ran inside the firm on the firm's
own systems; it is not mine to publish and it was never load-tested there. This
harness is a stand-in built to measure the same mechanism at a comparable key
scale, and it contains no company data. A reader who takes this benchmark for
that service has been misled, which is why the sentence is here rather than in
a footnote.

`P5` names a WORKSTREAM within an internship, never a personal undertaking of
mine. `Canon` is the frozen record of what was claimed before anything was
measured, and `Bullet id` is that record's own key for this one row - the
prefix is the canon, the rest identifies the workstream and the row inside it.

**The live row this measurement corrects is in a private career record and is
not published here.** What IS published is the whole of what a reader needs to
judge the comparison without it: the claim's exact text, the measurement beside
it, the population that measurement was taken over, and the verdict. Naming the
file it lives in would add a path nobody outside can open; leaving out the
claim itself would leave a benchmark with nothing to compare against. So the
coordinate is withheld and the comparison is not.

**The verdict above is a reading, and it is the owner's.** It is recorded for
confirmation rather than asserted: the direction and the mechanism hold, and
both figures the row quotes move. Where the measurement disagrees with the row,
the measurement wins and the row changes -- its metric, and its description of
what was done and how.
<!-- artifact:claim:end -->

## What it measures

One FastAPI service, two arms. On every request the handler resolves a tenant's
effective configuration - a three-table join with two ordered aggregates, the
shape of a config/entitlement lookup that a request cannot proceed without:

| | resolve path |
|---|---|
| **off** | straight to Postgres on every request, through a pooled prepared statement |
| **on** | Redis `GET` first; on a miss, the same Postgres resolve, then `SET` with a TTL |

Both answer the same logical question and return byte-identical bodies. The arm
is chosen by one env var so there is no second copy of the handler to drift.

## Why the uncached arm is not a strawman

The "before" side is a competent implementation, and the build refuses to
proceed if it stops being one:

- **The plan is asserted, not claimed.** `app/seed.py` EXPLAINs the exact
  resolve query after seeding and **fails the run if the plan contains a
  sequential scan**. Measured: index scan on `tenants_pkey` plus index scans on
  both child tables, a sub-millisecond execution time, all buffer hits and zero
  disk reads. The script prints the plan it asserted against.
- **The buffer pool is warm and oversized for the data.** The whole dataset is
  tens of mebibytes against a shared buffer pool more than an order of
  magnitude larger, prewarmed with `pg_prewarm`; the exact sizes are set in
  `docker-compose.yml` and reported by `app/seed.py`. The uncached arm is never
  paying disk I/O the cached arm avoids.
- **One round trip, not an N-plus-one loop**, over an asyncpg pool whose bounds
  are declared in `app/main.py`.

Handicapping any of these - an unindexed column, a cold cache, a tiny pool -
would have produced a bigger ratio and a worthless one.

## Why the key distribution is skewed, and why that is disclosed

A read-through cache earns its place when keys recur, and how strongly they
recur is the assumption under test. An earlier version of this paragraph
overstated that badly; the claim was **retracted** on 2026-07-31, and its exact
wording is preserved in the retracted list in `results/RESULTS.md` rather than
being repeated here - one authoritative copy of a withdrawn sentence is a
record, three copies are a rumour.

What it got wrong is that a uniform draw makes a cache useless. It does not: a
uniform draw over the tenant population touches essentially every tenant within
the replayed sequence, so almost every request is a repeat and the ceiling for
a perfect cache is about nine in ten. The sequence arithmetic settles that
without a run, and `benchlib/workload.py` carries it in full. What skew changes
is the size of the working set that must stay resident, and therefore the
behaviour under eviction; a maximally skewed draw would make any cache look
perfect, which is the failure in the other direction.

This uses a Zipf draw over a **seeded permutation** of tenant ids, so the hot
tenants are not simply the low ids that Postgres happens to cluster well. The
exponent is recorded as `zipf_a` in the workload description under `results/`.

The resulting concentration is **reported in the results rather than left
implicit**: the top one percent of tenants take roughly four in five requests,
and the top ten tenants take about half. The exact shares, the distinct-tenant
count and the perfect-cache ceiling are all fields of
`results/workload-primary.json`, written by the run. That is an assumption
about traffic shape, and a reader should price it. The identical seeded
sequence is replayed against **both** arms in the same order, so it cannot
favour either one.

## Measurement discipline

- The dataset is generated from a **fixed seed** and is identical across runs.
- The **same seeded key sequence** drives both arms, in the same order.
- Every concurrency level runs an **uncounted warmup** before its measured run,
  so neither arm pays a cold-connection penalty the other avoids. **This makes
  the measured window steady-state warm, and that is stated rather than
  implied.**
- Redis is **flushed before the cached arm begins**, so the run as a whole
  starts cold.
- **Two independent clocks**: the load generator's client-observed duration, and
  the service's own `server_us` handler stamp. If they disagreed on the
  direction of the result, the result would not be trustworthy.
- The p99 ceiling is the **control variable**: a reported capacity is the
  highest offered rate at which measured p99 stayed at or under the budget.
  Peak throughput at unbounded latency is deliberately not reported, because it
  is not the claim.

<!-- artifact:hitrate:begin -->
The measured hit rate is <!--artifact:key:cache_hit_rate_pct-->98.92344<!--/artifact:key-->% - a warm-window number,
over a population of <!--artifact:key:cache_hit_rate_pct.population-->713755<!--/artifact:key--> counted cache
lookups on the cached arm, being <!--artifact:key:cache_hit_rate_pct.hits-->706071<!--/artifact:key--> hits
against <!--artifact:key:cache_hit_rate_pct.misses-->7684<!--/artifact:key--> misses. The tail budget it was
measured under is <!--artifact:key:p99_ms_uncached_at_matched_rate.p99_ceiling_ms-->250.0<!--/artifact:key--> ms,
and every capacity figure in this directory is bounded by that budget.
<!-- artifact:hitrate:end -->

That hit rate is **no longer typed here**. It is computed from the guard record
by `derive.py` and written into the sentence above by `render.py`, which
re-renders in memory and byte-compares on every check. A hand edit to a rendered
region is a detected error, not a shortcut.

## What the run found

Two figures, both from the campaign this file is dated by, and both with their
populations beside them. Neither is a point estimate dressed as a certainty.

<!-- artifact:headline:begin -->
| | uncached | cached | population |
|---|---|---|---|
| p99 at a matched offered rate of <!--artifact:key:p99_ms_uncached_at_matched_rate.at_target_rate-->6000<!--/artifact:key--> rps | <!--artifact:key:p99_ms_uncached_at_matched_rate-->64.09<!--/artifact:key--> ms | <!--artifact:key:p99_ms_cached_at_matched_rate-->17.51<!--/artifact:key--> ms | one ladder level each |
| median at that rate | <!--artifact:key:p99_ms_uncached_at_matched_rate.p50_ms-->6.29<!--/artifact:key--> ms | <!--artifact:key:p99_ms_cached_at_matched_rate.p50_ms-->1.46<!--/artifact:key--> ms | one ladder level each |
| highest offered rate the arm held | <!--artifact:key:open_loop_capacity_uncached_rps-->6034.3<!--/artifact:key--> rps | <!--artifact:key:open_loop_capacity_cached_rps-->11975.0<!--/artifact:key--> rps | <!--artifact:key:open_loop_capacity_uncached_rps.population-->6<!--/artifact:key--> ladder levels each |
| capacity lies in | [<!--artifact:key:open_loop_capacity_uncached_rps.bracket_low-->6000<!--/artifact:key-->, <!--artifact:key:open_loop_capacity_uncached_rps.bracket_high-->8000<!--/artifact:key-->) rps | [<!--artifact:key:open_loop_capacity_cached_rps.bracket_low-->12000<!--/artifact:key-->, <!--artifact:key:open_loop_capacity_cached_rps.bracket_high-->14000<!--/artifact:key-->) rps | ladder step <!--artifact:key:open_loop_capacity_uncached_rps.ladder_step_rps-->2000<!--/artifact:key--> rps |
| replicates that held the boundary rate | <!--artifact:key:uncached_replicates_holding_the_boundary_rate.numerator-->3<!--/artifact:key--> of <!--artifact:key:uncached_replicates_holding_the_boundary_rate.denominator-->3<!--/artifact:key--> at <!--artifact:key:uncached_replicates_holding_the_boundary_rate.at_target_rate-->6000<!--/artifact:key--> rps | <!--artifact:key:cached_replicates_holding_the_boundary_rate.numerator-->3<!--/artifact:key--> of <!--artifact:key:cached_replicates_holding_the_boundary_rate.denominator-->3<!--/artifact:key--> at <!--artifact:key:cached_replicates_holding_the_boundary_rate.at_target_rate-->8000<!--/artifact:key--> rps | interleaved by round |
<!-- artifact:headline:end -->

**The two capacity figures are QUANTISED LOWER BOUNDS and no ratio is formed
from them.** The ladder steps coarsely, so each arm's figure says only that it
held its highest passing level and failed at the next one. A quotient of two
lower bounds is a function of the step size, not of capacity, and it is refused
here for that reason. The honest statement is the bracket in the table: the
uncached arm's capacity lies inside its interval and the cached arm's inside
its, so the ratio between them is bounded but not measured. Refining it needs a
finer ladder, which this campaign did not run.

The full record - every level, every replicate, the environment, the contention
census and the run-by-run comparison against the superseded campaign - is in
`RUN-RECORD.md`. The narrative, its retractions and its disclosed instabilities
are in `results/RESULTS.md`.

## The load generator is part of the experiment

The first driver here was asyncio + httpx on the Windows host. Its own
do-nothing ceiling was a small fraction of the throughput it was reporting for
the service, so above a handful of connections it was measuring itself. Both
numbers are recorded in `run_benchmark.py`'s own docstring and in
`k6/sweep.js`; the driver is kept rather than deleted because the guard's story
lives in it.

The G3 headroom guard caught that, which is the entire reason it exists. The
driver was replaced with **k6 running inside the compose network**, and its
ceiling on the same do-nothing endpoint is measured first, every run:

<!-- artifact:generator:begin -->
  <!--artifact:key:load_generator_ceiling_rps-->29862.6<!--/artifact:key--> rps, the maximum over
  <!--artifact:key:load_generator_ceiling_rps.population-->3<!--/artifact:key--> do-nothing probe levels -
  the maximum rather than a mean, because a ceiling is what the tool can do at
  its best. Every throughput figure here is priced against it, and G3 refuses
  the run unless the ceiling clears the faster arm by half again.
<!-- artifact:generator:end -->

**A throughput benchmark that never measures its own generator is reporting an
unknown mixture of the system and the tool.**

## The guards that make the number mean something

`finalize.py` runs five, and each fails loud:

| | check |
|---|---|
| **G1** | every tenant observed on both arms returned a byte-identical response checksum - the cached arm answers the same question. Two halves: one server-attested, one recomputed client-side from the delivered payload |
| **G2** | G1 compared enough keys to mean anything. The floor is declared in `finalize.py`; a near-empty comparison is an unrun check, not a pass |
| **G3** | the load generator's ceiling clears the faster arm by half again |
| **G4** | the cache was genuinely exercised - there were misses, and the hit rate is below one - and Redis holds no more distinct keys than the workload ever requested |
| **G5** | client-side throughput and the service's own handler clock agree on the direction |

**G4 failed on its first formulation and was rewritten** - it compared a
steady-state warm hit rate against a *cold single pass* ceiling. The guard was
wrong, not the system. The replacement is documented inline at `finalize.py`
G4, and deliberately keeps a falsifiable bound rather than being tuned to pass.

## Running it

```
docker compose build app
docker compose up -d postgres redis
MSYS_NO_PATHCONV=1 docker compose run --rm app python /srv/seed.py 20000
python make_sequence.py 200000 20000

python gate.py

CACHE=off docker compose up -d --force-recreate app
python run_k6_sweep.py --arm off --null-probe
python run_rate_test.py --arm off
python collect_checksums.py --arm off

CACHE=on docker compose up -d --force-recreate app
docker compose exec -T redis redis-cli FLUSHALL
python run_k6_sweep.py --arm on
python run_rate_test.py --arm on
python collect_checksums.py --arm on

python capture_dbsize.py
python finalize.py
python derive.py --specs figure-specs.json
python render.py . --write
python conformance.py .
```

The `MSYS_NO_PATHCONV` assignment in that block matters on Git Bash: without it
`/srv/seed.py` is rewritten into a Windows path and the container cannot find
the file.

**`gate.py` is not optional and its position is not arbitrary.** It reads the
conditions a measurement depends on - the pinned images, the one load-generator
digest both drivers share, and the seeded sequence against its own description -
and writes `results/gate.json` with a token minted from them. Every measuring
script refuses to start without that record, and refuses again if the gate it
finds says it did not pass. It runs **after** `make_sequence.py`, because the
sequence is one of the things the token is minted from: regenerate the sequence
and the gate must be re-run, or the token stops describing the workload that was
actually replayed.

**`run_rate_test.py` is where the headline comes from.** The sweep above it is
closed-loop and reports peak throughput; the rate test is open-loop and reports
the capacity at a fixed tail, which is the number this benchmark leads with. It
was missing from these steps for weeks, so the documented procedure reproduced
everything except the result being documented.

**`derive.py` and `render.py` are why no figure in this file was typed.**
`derive.py` computes every figure from the committed per-run records and
classifies every input file it did not use, with the reason; `render.py` writes
those figures into the regions of this document and, run without `--write`,
re-renders in memory and byte-compares. There is no override on it. A hand edit
to a rendered region is a detected error, not a shortcut.

Each measuring run also writes its own record under `results/raw/`: machine
timestamps, the gate token it ran under, how long it took, and a census of what
else was on the Docker VM when it started and when it finished. That last one is
not housekeeping - the instability disclosed in `results/RESULTS.md` is
attributed to background load from other containers on the same machine, and a
run with no contention evidence cannot honestly be compared with another.

## Layout

```
app/main.py             the service; one handler, two arms
app/seed.py             deterministic seed + the query-plan guard
benchlib/workload.py    the seeded Zipf sequence and its disclosure
benchlib/driver.py      the RETIRED Python driver, kept because G3's story lives in it
k6/sweep.js             the measured load script
k6/rate.js              the fixed-rate load script
k6/null.js              the driver-headroom probe
make_sequence.py        emits the shared seeded sequence
gate.py                 reads the run's preconditions and mints its token
runmeta.py              the run recorder: timestamps, token, contention census
run_k6_sweep.py         per-level warmup + measured run, per arm (closed loop)
run_rate_test.py        the fixed-tail capacity ladder, per arm (open loop)
run_benchmark.py        the RETIRED Python driver; correctness pass only
collect_checksums.py    equivalence sampling + the server-side clock
finalize.py             the five guards and the final result
derive.py               the single source of truth for every published number
figure-specs.json       what each figure is, and what its population is
render.py               writes the figures into this file's regions; refuses by default
conformance.py          the vendored contract checker - re-run it yourself
canonkit.py             the vendored frozen core, byte-identical to its source
results/gate.json       what the gate read, and the token every run stamps
results/figures.json    the derived figures, with populations and dates
results/raw/            one record per run, written by the machine
results/RESULTS.md      the narrative, the retractions and the disclosed instability
RUN-RECORD.md           the run this file is dated by, level by level
RESULTS-2026-07-31-SUPERSEDED.md  the earlier campaign's own results document
RETRACTION-SWEEP.md     where every retracted figure still appears, and why
```

A retired script is kept rather than deleted when a guard's story lives in it,
with a note saying why. Deleting the evidence of a correction is how a record
stops being one.

## What this does not show

<!-- artifact:limits:begin -->
It does not establish what happened at any company. It is a reproducible
measurement of one mechanism at a stated scale on stated hardware, and a bullet
resting on it must describe the measured configuration rather than borrow its
authority for a different one. The two capacity figures are quantised lower
bounds, not capacities: the ladder's step is coarse, so no ratio may be formed
from them and none is. The tail pair is ONE reading per arm - the ladder runs
each level once - so it carries no interval and must never be read as a
replicated result; only the boundary-rate replicate counts are replicated, and
they are three per arm on one host on one day. The hit rate is a steady-state
WARM window, not a cold-start figure, and is bounded above by the sequence's own
perfect-cache ceiling. Nothing here is measured under stampede protection, under
eviction pressure, across more than one host, or against real traffic. Absolute
throughput on this machine is not comparable with any other machine's, and the
contention census exists because it was not even comparable with itself until
the background load was controlled.
<!-- artifact:limits:end -->
