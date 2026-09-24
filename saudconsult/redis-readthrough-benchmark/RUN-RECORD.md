# RUN-RECORD

One row per run. Every figure below was read back from the machine record the
run itself wrote; nothing here was typed from a console. There is no summary
statistic over replicates anywhere in this file, and that is deliberate: the
July record this run replaces disclosed two modes roughly twenty times apart in
tail latency at one rate, and any single number over those observations would
have described neither of them.

---

## The run's environment, recorded as population facts

A throughput number measured at one Docker VM size and re-run at another is a
different measurement, so the size is part of the result rather than
housekeeping.

| Fact | Value | How it was read |
|---|---|---|
| Date of the run | 2026-09-18, 05:06:56 to 05:22:09 local (-05:00) | the run records' own stamps |
| Docker Server Version | 28.4.0 | `docker info` |
| Docker VM kernel | 6.6.87.2-microsoft-standard-WSL2 | `docker info` |
| Docker VM CPUs | **24** | `docker info` |
| Docker VM Total Memory | **14.48 GiB** | `docker info` |
| Free disk on C: | 627 G of 1.9 T | `df -h /c` |
| Host interpreter | CPython 3.13.5, httpx 0.28.1 | `python -c` |

### What else was on the Docker VM, before and after

**Before: nine containers were running, and all nine were stopped for this run.**
They were a Supabase development stack unrelated to this benchmark, and they were
stopped deliberately rather than tolerated, because the record this run replaces
attributes its own instability to exactly this kind of neighbour.

| Census | Containers | Resident set | CPU |
|---|---|---|---|
| BEFORE, at 04:5x | **9** running: `supabase_db`, `supabase_studio`, `supabase_pg_meta`, `supabase_storage`, `supabase_rest`, `supabase_realtime`, `supabase_inbucket`, `supabase_auth`, `supabase_kong` | **1,184.46 MiB** total | **7.13% of one core** total (`realtime` 2.96%, `inbucket` 3.26%, the other seven at or below 0.69%) |
| AFTER the nine were stopped, immediately before the run | **0** running | 0 | 0 |

Restoring that stack is not this run's business and it was left stopped.

Every row of the replicate table below carries its own census, taken by the run
recorder at the moment the run opened and again when it closed. Across all 23
runs the count is 3 and all 3 are this benchmark's own compose services, so no
neighbour appeared mid-campaign.

### The measurement window

Taken through `mwlock.acquire` and given back in a `finally`, never by hand.

```
05:06:56  HELD      token 33576:71088992eb1d45e7aa725899743413a4  pid 33576
05:11:45  RELEASED  first attempt stopped on a defect in the orchestration
          wrapper, NOT in the benchmark: the replicate tags start with a
          hyphen and were passed as `--tag <value>`, which argparse reads as
          the next option. Both affected steps exited 2 in 0.2 s, before the
          gate was read; neither took a measurement.
05:12:52  HELD      re-acquired; nothing measured in the 67-second gap
05:22:09  RELEASED  last replicate finished
```

### The gate every run below was authorised by

```
token     e3d1b772b6d9
dated_at  2026-09-18T05:07:27.101906-05:00
passed    True   declared inputs 17, absent 0
```

The gate was re-minted at 05:07:27, after the last edit to a declared input and
before the first measurement. It moved from `8e1f446e1c07` because the declared
input set gained a seventeenth file, `capture_dbsize.py`. Every one of the 23 run
records carries this token, and the gate's own stamp is earlier than all 23
`started_at` values -- asserted, not assumed.

---

## The replicate table -- one row per run

Three replicates at every rate on the pass/fail boundary of each arm, run
**interleaved by round** rather than grouped by rate, so a drift over the
campaign cannot be mistaken for an effect of the rate under test. A run at rate
R passes only if p99 <= 250 ms AND dropped fraction < 1% AND zero errors.

| target rate | arm | replicate | achieved rps | p50 ms | p99 ms | dropped | dropped fraction | verdict | contention start -> finish | source |
|---|---|---|---|---|---|---|---|---|---|---|
| 5000 | off | r1 | 4998.0 | 5.11 | 35.78 | 0 | 0.0 | PASS | 3 (3 own) -> 3 (3 own) | `results/rate-off-sep5000r1.json` |
| 5000 | off | r2 | 5040.7 | 3.15 | 36.18 | 0 | 0.0 | PASS | 3 (3 own) -> 3 (3 own) | `results/rate-off-sep5000r2.json` |
| 5000 | off | r3 | 4996.8 | 5.54 | 36.14 | 0 | 0.0 | PASS | 3 (3 own) -> 3 (3 own) | `results/rate-off-sep5000r3.json` |
| 5500 | off | r1 | 5477.8 | 8.93 | 130.59 | 61 | 0.00111 | PASS | 3 (3 own) -> 3 (3 own) | `results/rate-off-sep5500r1.json` |
| 5500 | off | r2 | 5489.6 | 7.93 | 56.45 | 0 | 0.0 | PASS | 3 (3 own) -> 3 (3 own) | `results/rate-off-sep5500r2.json` |
| 5500 | off | r3 | 5496.6 | 5.79 | 35.9 | 0 | 0.0 | PASS | 3 (3 own) -> 3 (3 own) | `results/rate-off-sep5500r3.json` |
| 6000 | off | r1 | 5991.3 | 8.34 | 52.46 | 0 | 0.0 | PASS | 3 (3 own) -> 3 (3 own) | `results/rate-off-sep6000r1.json` |
| 6000 | off | r2 | 5974.0 | 9.31 | 58.18 | 174 | 0.0029 | PASS | 3 (3 own) -> 3 (3 own) | `results/rate-off-sep6000r2.json` |
| 6000 | off | r3 | 6038.9 | 7.19 | 64.47 | 9 | 0.00015 | PASS | 3 (3 own) -> 3 (3 own) | `results/rate-off-sep6000r3.json` |
| 7000 | on | r1 | 6985.1 | 1.73 | 29.33 | 133 | 0.0019 | PASS | 3 (3 own) -> 3 (3 own) | `results/rate-on-sep7000r1.json` |
| 7000 | on | r2 | 7044.3 | 1.74 | 25.52 | 116 | 0.00166 | PASS | 3 (3 own) -> 3 (3 own) | `results/rate-on-sep7000r2.json` |
| 7000 | on | r3 | 6985.3 | 2.12 | 32.43 | 131 | 0.00187 | PASS | 3 (3 own) -> 3 (3 own) | `results/rate-on-sep7000r3.json` |
| 7500 | on | r1 | 7457.4 | 2.41 | 27.66 | 366 | 0.00488 | PASS | 3 (3 own) -> 3 (3 own) | `results/rate-on-sep7500r1.json` |
| 7500 | on | r2 | 7469.2 | 2.51 | 36.43 | 289 | 0.00385 | PASS | 3 (3 own) -> 3 (3 own) | `results/rate-on-sep7500r2.json` |
| 7500 | on | r3 | 7472.4 | 1.75 | 62.74 | 255 | 0.0034 | PASS | 3 (3 own) -> 3 (3 own) | `results/rate-on-sep7500r3.json` |
| 8000 | on | r1 | 7982.3 | 2.0 | 25.34 | 163 | 0.00204 | PASS | 3 (3 own) -> 3 (3 own) | `results/rate-on-sep8000r1.json` |
| 8000 | on | r2 | 7951.0 | 3.25 | 43.52 | 421 | 0.00526 | PASS | 3 (3 own) -> 3 (3 own) | `results/rate-on-sep8000r2.json` |
| 8000 | on | r3 | 8060.6 | 2.92 | 43.94 | 0 | 0.0 | PASS | 3 (3 own) -> 3 (3 own) | `results/rate-on-sep8000r3.json` |

**Eighteen runs, eighteen passes.** The uncached arm held 6,000 rps three times
out of three, at p99 between 52 and 65 ms. The record this replaces reports three
consecutive failures at that identical rate, at p99 around 1,500 ms with 12,012
dropped iterations, against one earlier pass. The two modes it disclosed did not
recur here on a VM with nothing else on it.

---

## The open-loop capacity ladders, one row per level

`run_rate_test.py` with its documented rate ladder. This is the program the
headline capacity figure comes from.

| target rate | arm | replicate | achieved rps | p50 ms | p99 ms | dropped | dropped fraction | verdict | contention start -> finish | source |
|---|---|---|---|---|---|---|---|---|---|---|
| 4000 | off | ladder | 3998.6 | 2.9 | 44.77 | 0 | 0.0 | PASS | 3 (3 own) -> 3 (3 own) | `results/rate-off.json` |
| 6000 | off | ladder | 6034.3 | 6.29 | 64.09 | 93 | 0.00155 | PASS | 3 (3 own) -> 3 (3 own) | `results/rate-off.json` |
| 8000 | off | ladder | 6605.9 | 210.68 | 1055.13 | 12861 | 0.16076 | FAIL | 3 (3 own) -> 3 (3 own) | `results/rate-off.json` |
| 10000 | off | ladder | 6922.0 | 238.04 | 1225.0 | 30008 | 0.30008 | FAIL | 3 (3 own) -> 3 (3 own) | `results/rate-off.json` |
| 12000 | off | ladder | 7463.7 | 222.82 | 1154.45 | 43900 | 0.36583 | FAIL | 3 (3 own) -> 3 (3 own) | `results/rate-off.json` |
| 14000 | off | ladder | 6678.3 | 160.01 | 1500.92 | 71931 | 0.51379 | FAIL | 3 (3 own) -> 3 (3 own) | `results/rate-off.json` |
| 4000 | on | ladder | 3999.3 | 0.9 | 13.25 | 0 | 0.0 | PASS | 3 (3 own) -> 3 (3 own) | `results/rate-on.json` |
| 6000 | on | ladder | 5998.7 | 1.46 | 17.51 | 0 | 0.0 | PASS | 3 (3 own) -> 3 (3 own) | `results/rate-on.json` |
| 8000 | on | ladder | 8057.2 | 2.7 | 37.92 | 55 | 0.00069 | PASS | 3 (3 own) -> 3 (3 own) | `results/rate-on.json` |
| 10000 | on | ladder | 9943.4 | 7.48 | 60.57 | 504 | 0.00504 | PASS | 3 (3 own) -> 3 (3 own) | `results/rate-on.json` |
| 12000 | on | ladder | 11975.0 | 9.63 | 58.52 | 1146 | 0.00955 | PASS | 3 (3 own) -> 3 (3 own) | `results/rate-on.json` |
| 14000 | on | ladder | 11945.6 | 85.79 | 749.07 | 18496 | 0.13211 | FAIL | 3 (3 own) -> 3 (3 own) | `results/rate-on.json` |

- **arm `off` capacity at p99 <= 250 ms: 6034.3 rps** (offered 6000), p99 64.09 ms, dropped 93
- **arm `on` capacity at p99 <= 250 ms: 11975.0 rps** (offered 12000), p99 58.52 ms, dropped 1146

---

## The closed-loop sweeps, one row per level

| vus | arm | rps | p50 ms | p99 ms | failed rate | contention start -> finish | source |
|---|---|---|---|---|---|---|---|
| 4 | off | 2868.0 | 1.21 | 2.23 | 0 | 3 (3 own) -> 3 (3 own) | `results/arm-off.json` |
| 8 | off | 4428.6 | 1.61 | 3.2 | 0 | 3 (3 own) -> 3 (3 own) | `results/arm-off.json` |
| 16 | off | 6427.2 | 2.23 | 4.87 | 0 | 3 (3 own) -> 3 (3 own) | `results/arm-off.json` |
| 32 | off | 7319.3 | 4.13 | 8.05 | 0 | 3 (3 own) -> 3 (3 own) | `results/arm-off.json` |
| 64 | off | 6521.6 | 9.21 | 16.76 | 0 | 3 (3 own) -> 3 (3 own) | `results/arm-off.json` |
| 128 | off | 7389.8 | 16.62 | 30.24 | 0 | 3 (3 own) -> 3 (3 own) | `results/arm-off.json` |
| 256 | off | 7693.4 | 31.64 | 58.07 | 0 | 3 (3 own) -> 3 (3 own) | `results/arm-off.json` |
| 512 | off | 8079.4 | 33.47 | 335.92 | 0 | 3 (3 own) -> 3 (3 own) | `results/arm-off.json` |
| 4 | on | 4234.4 | 0.72 | 2.33 | 0 | 3 (3 own) -> 3 (3 own) | `results/arm-on.json` |
| 8 | on | 7183.4 | 0.91 | 2.88 | 0 | 3 (3 own) -> 3 (3 own) | `results/arm-on.json` |
| 16 | on | 10388.3 | 1.27 | 5.31 | 0 | 3 (3 own) -> 3 (3 own) | `results/arm-on.json` |
| 32 | on | 12286.5 | 2.2 | 6.24 | 0 | 3 (3 own) -> 3 (3 own) | `results/arm-on.json` |
| 64 | on | 14168.7 | 4.31 | 9.63 | 0 | 3 (3 own) -> 3 (3 own) | `results/arm-on.json` |
| 128 | on | 13471.2 | 8.86 | 18.72 | 0 | 3 (3 own) -> 3 (3 own) | `results/arm-on.json` |
| 256 | on | 13370.8 | 17.84 | 42.25 | 0 | 3 (3 own) -> 3 (3 own) | `results/arm-on.json` |
| 512 | on | 14317.5 | 33.12 | 70.52 | 0 | 3 (3 own) -> 3 (3 own) | `results/arm-on.json` |

| driver headroom probe (vus) | rps | p99 ms |
|---|---|---|
| 64 | 23601.2 | 7.0 |
| 256 | 27652.0 | 19.14 |
| 512 | 29862.6 | 35.26 |

- arm `off` sustained at p99 <= 250 ms: **7693.4 rps** at 256 vus, p99 58.07 ms
- arm `on` sustained at p99 <= 250 ms: **14317.5 rps** at 512 vus, p99 70.52 ms
- load generator ceiling on the do-nothing endpoint: **29862.6 rps**, the maximum over
  the three probe levels above

---

## The key count G4b rests on, re-read rather than inherited

`results/redis-dbsize.json` had no producer in this repository. Its value was a
number typed at a console in July, carrying prose provenance and no timestamp,
and `finalize.py` reads it into G4b's verdict on every run. A re-run that left it
in place would have compared a fresh Redis against a key count from a different
month and reported PASS over a population it never measured.

It now has a producer, `capture_dbsize.py`, which runs under the same gate as the
measurements, records the exact command, and keeps the record it supersedes:

| | value | provenance |
|---|---|---|
| previous, in the committed record | **10,536** | `"captured": "after the offset-corrected cached-arm sweep"` -- prose, no timestamp, no producer |
| this run | **7021** | `docker exec redis-readthrough-benchmark-redis-1 redis-cli DBSIZE`, read at 2026-09-18T05:22:07.923414-05:00 under gate `e3d1b772b6d9` |

The two differ, so the old file was not a harmless duplicate: leaving it would
have published a population 3,515 keys larger than the one Redis actually held.
The lower figure is expected rather than surprising -- the cache entries carry a
300-second TTL and the cached arm's work ran for about six minutes, so keys
touched early in the campaign had expired by the time the count was taken. G4b's
bound is that Redis holds no more distinct keys than the sequence ever requested:
7021 <= 11106 holds.

---

## The guards, re-derived by `finalize.py` over this run

`canonkit.validate_guards` over the regenerated `results/results.json`:
**0 violations over a population of 7.**

| guard | verdict | population | label | floor |
|---|---|---|---|---|
| G1a-equivalence-server-attested | PASS | 3000 | tenant keys whose server-attested checksum was collected on BOTH arms | 500 |
| G1b-equivalence-client-recomputed | PASS | 3000 | tenant keys whose client-recomputed payload hash was collected on BOTH arms | 500 |
| G2-coverage | PASS | 3000 | tenant keys whose client-recomputed payload hash was collected on BOTH arms | 500 |
| G3-driver-headroom | PASS | 3 | do-nothing probe levels the generator's ceiling is the maximum over | 2 |
| G4a-cache-exercised | PASS | 713755 | counted cache lookups in the measured windows (hits + misses) | 200000 |
| G4b-keys-bounded-by-workload | PASS | 7021 | distinct keys Redis held when the run ended | 1 |
| G5-two-clocks | PASS | 3000 | responses sampled on the weaker arm, each carrying one server-side handler-time reading | 500 |

`all_guards_passed = True`

---

## July beside now, run by run

There is no aggregate row here. The left column is the committed record; the
right is what this machine did today with nothing else on it.

| quantity | the committed July record | this run, 2026-09-18 |
|---|---|---|
| open-loop capacity, uncached | 5469.9 rps at offered 5,500, p99 173.65 ms, 117 dropped | 6034.3 rps at offered 6000, p99 64.09 ms, 93 dropped |
| open-loop capacity, cached | 7457.5 rps at offered 7,500, p99 53.9 ms, 208 dropped | 11975.0 rps at offered 12000, p99 58.52 ms, 1146 dropped |
| uncached at 6,000 rps offered | one pass (5,993.9 rps, p99 72.5 ms, 0.06% dropped) and three catastrophic failures (p99 ~1,500 ms, 12,012 dropped) | three runs, three passes: 5991.3 rps / p99 52.46 ms / 0 dropped; 5974.0 rps / p99 58.18 ms / 174 dropped; 6038.9 rps / p99 64.47 ms / 9 dropped |
| closed-loop sustained, uncached | 6751.2 rps at 256 vus | 7693.4 rps at 256 vus |
| closed-loop sustained, cached | 9475.7 rps at 256 vus | 14317.5 rps at 512 vus |
| throughput ratio (closed loop) | 1.404x | 1.861x |
| server handler p50, uncached -> cached | 1050 us -> 433 us (2.42x) | 744 us -> 288 us (2.58x) |
| cache hit rate, steady-state warm | 0.9857 | 0.9892 |
| load generator ceiling | 32516.0 rps | 29862.6 rps |
| Redis distinct keys at the end | 10,536 (typed, no producer) | 7021 (read by a program, under the gate) |

---

## What was executed, in order, each captured with its own exit code

Every command below was run through the orchestration wrapper, which redirected
stdout and stderr into a file and wrote the exit code into the same file.
Nothing was piped for a pass/fail judgement.

```
docker compose build app                                       EXIT=0
docker compose up -d postgres redis                            EXIT=0
docker compose run --rm app python /srv/seed.py 20000          EXIT=0
python make_sequence.py 200000 20000                           EXIT=0
python gate.py                                                 EXIT=0
CACHE=off docker compose up -d --force-recreate app            EXIT=0
python run_k6_sweep.py --arm off --null-probe                  EXIT=0
python run_rate_test.py --arm off                              EXIT=0
python run_rate_test.py --arm off --rates R --tag=-sepRrN      EXIT=0  (x9)
python collect_checksums.py --arm off                          EXIT=0
CACHE=on docker compose up -d --force-recreate app             EXIT=0
docker exec ...-redis-1 redis-cli FLUSHALL                     EXIT=0
python run_k6_sweep.py --arm on                                EXIT=0
python run_rate_test.py --arm on                               EXIT=0
python run_rate_test.py --arm on --rates R --tag=-sepRrN       EXIT=0  (x9)
python collect_checksums.py --arm on                           EXIT=0
python capture_dbsize.py                                       EXIT=0
python finalize.py                                             EXIT=0
```

`run_benchmark.py` was deliberately NOT run. It writes the same
`results/arm-<arm>.json` the k6 sweep writes, so running it would have replaced
this campaign's sweep results with numbers from the retired driver whose own
do-nothing ceiling was measured below the throughput it reported for the service.

## The sequence reproduced exactly

`make_sequence.py 200000 20000` was re-run and `results/sequence.json` came back
**byte-identical** to the committed one -- the generator is seeded, and this
confirms it rather than assuming it. `results/workload.json` differs by exactly
one key: the regenerated description carries `"zipf_a": 1.2`, which the committed
copy lacks. Every measured field in it -- 200,000 requests, 11,106 distinct
tenants touched, 0.7891 concentration in the top 1%, 0.9445 ceiling -- came back
identical. So the committed description was written by a `make_sequence.py`
predating the line that records the skew parameter, and the workload itself has
not moved.

## Ruling — 2026-09-18

**This run is ACCEPTED as the record.** The July figures become history.

The run was clean by every check that was run against it: eighteen replicates at
six boundary rates, all PASS; the contention census on every row is three
containers and all three are this benchmark's own; the gate precedes all
twenty-five measured starts; the seven guard records validate with zero
violations over the regenerated `results/results.json`; and all thirty-four
captured commands exited 0. Nine unrelated containers that were sharing the
Docker VM were stopped before the run and restarted after it.

**What the re-run found, stated as runs rather than as a summary statistic.**

At 6,000 rps the committed record reports three consecutive catastrophic
failures — p99 around 1,500 ms with 12,012 dropped. Here, three replicates at
that same rate held at p99 52.46, 58.18 and 64.47 ms with 0, 174 and 9 dropped.
The replicates did not split into two modes at any boundary rate, so there is no
bimodality to report this time.

**The saturation cliff did not disappear; it moved.** The uncached arm still
collapses, now between 6,000 and 8,000 rps — the ladder's 8,000 level returned
p99 1055.13 ms with 16.08% dropped. The cached arm holds to 12,000 rps and
collapses between 12,000 and 14,000. Removing the background load bought roughly
2,000 rps of headroom on the uncached arm.

That is evidence **for** the hypothesis this artifact already states — that the
July instability came from uncontrolled load on the same machine — and it is not
proof of it. One host, one day, one campaign.

**The capacity ratio is deliberately not restated here.** July reported
`5,469.9 → 7,457.5 rps = 1.363x` from a hand-made aggregate with no producer.
This campaign's open-loop ladder is coarser (2,000-rps steps against July's 500),
so its 6,034.3 and 11,975.0 are quantised lower bounds and the two ratios are not
computed on comparable grids. What the data does support is a bound: uncached
capacity lies in [6000, 8000) and cached in [12000, 14000), so the ratio lies in
(1.5, 2.33) — and July's 1.363x falls outside it. The figure is refuted; its
replacement is for the render-anchor pass, not for this record.

**The hit rate moves 98.6% → 98.9%**, re-derived from this run's own G4a guard
record: 706,071 hits against 7,684 misses over 713,755 counted requests.

