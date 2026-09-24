# Measured results

<!-- artifact:run:begin -->
Every number in this document is computed from the committed per-run records by
`derive.py` and written into these regions by `render.py`. Nothing here is typed
and nothing is estimated. The run reported below finished
<!--artifact:key:dated_at-->2026-09-18T05:22:01.784149-05:00<!--/artifact:key-->, under gate token <!--artifact:key:gate_token-->e3d1b772b6d9dc605ac8f210ec11a419fa338799f70c634928beca34e33fb1ed<!--/artifact:key-->, and the figures
rest on <!--artifact:key:cache_hit_rate_pct.population-->713755<!--/artifact:key--> counted cache lookups and the
ladder levels named in each table.
<!-- artifact:run:end -->

**This document reports the campaign that SUPERSEDED the one of 2026-07-31.**
The earlier document is kept unedited at
`RESULTS-2026-07-31-SUPERSEDED.md`, with a header saying what happened to it.
Its headline capacity ratio is **refuted**, not merely out of date: the ladder
below brackets each arm's capacity, and the ratio those brackets allow does not
contain the figure that document reports. The earlier figure also rested on a
results file with no producer in this directory, which is reason enough on its
own not to quote it.

## The headline is a bracket, and no ratio is formed from it

The open-loop ladder offers a fixed arrival rate regardless of service speed and
reports dropped iterations when the generator cannot keep up, so an arm that
cannot sustain a rate is visible instead of quietly throttled. What it
establishes is where each arm stops, to the resolution of its own step.

<!-- artifact:capacity:begin -->
| | uncached | cached |
|---|---|---|
| highest offered rate the arm held | <!--artifact:key:open_loop_capacity_uncached_rps-->6034.3<!--/artifact:key--> rps | <!--artifact:key:open_loop_capacity_cached_rps-->11975.0<!--/artifact:key--> rps |
| offered at that level | <!--artifact:key:open_loop_capacity_uncached_rps.at_target_rate-->6000<!--/artifact:key--> rps | <!--artifact:key:open_loop_capacity_cached_rps.at_target_rate-->12000<!--/artifact:key--> rps |
| p99 there | <!--artifact:key:open_loop_capacity_uncached_rps.p99_ms-->64.09<!--/artifact:key--> ms | <!--artifact:key:open_loop_capacity_cached_rps.p99_ms-->58.52<!--/artifact:key--> ms |
| dropped fraction there | <!--artifact:key:open_loop_capacity_uncached_rps.dropped_fraction-->0.00155<!--/artifact:key--> | <!--artifact:key:open_loop_capacity_cached_rps.dropped_fraction-->0.00955<!--/artifact:key--> |
| capacity lies in | [<!--artifact:key:open_loop_capacity_uncached_rps.bracket_low-->6000<!--/artifact:key-->, <!--artifact:key:open_loop_capacity_uncached_rps.bracket_high-->8000<!--/artifact:key-->) rps | [<!--artifact:key:open_loop_capacity_cached_rps.bracket_low-->12000<!--/artifact:key-->, <!--artifact:key:open_loop_capacity_cached_rps.bracket_high-->14000<!--/artifact:key-->) rps |
| population | <!--artifact:key:open_loop_capacity_uncached_rps.population-->6<!--/artifact:key--> offered-rate levels | <!--artifact:key:open_loop_capacity_cached_rps.population-->6<!--/artifact:key--> offered-rate levels |
| ladder step | <!--artifact:key:open_loop_capacity_uncached_rps.ladder_step_rps-->2000<!--/artifact:key--> rps | <!--artifact:key:open_loop_capacity_cached_rps.ladder_step_rps-->2000<!--/artifact:key--> rps |
<!-- artifact:capacity:end -->

**A quotient of two quantised lower bounds is a function of the step size, not of
capacity.** Each arm's figure says only that it held its highest passing level
and failed at the next one, so dividing one by the other nets two bounds and
reports the result as a measurement. No such ratio is computed here, and the
derivation refuses to author one. What the data supports is the pair of
brackets above: the true ratio lies somewhere between the ratio of the interval
endpoints, and narrowing it needs a finer ladder than this campaign ran.

## The tail pair, at a rate both arms held

A tail read at a rate one arm cannot serve compares a working system against a
collapsed one, so both arms are read at the highest offered rate both of them
held.

<!-- artifact:tail:begin -->
| | uncached | cached |
|---|---|---|
| offered rate | <!--artifact:key:p99_ms_uncached_at_matched_rate.at_target_rate-->6000<!--/artifact:key--> rps | <!--artifact:key:p99_ms_cached_at_matched_rate.at_target_rate-->6000<!--/artifact:key--> rps |
| delivered | <!--artifact:key:p99_ms_uncached_at_matched_rate.achieved_rps-->6034.3<!--/artifact:key--> rps | <!--artifact:key:p99_ms_cached_at_matched_rate.achieved_rps-->5998.7<!--/artifact:key--> rps |
| p99 | <!--artifact:key:p99_ms_uncached_at_matched_rate-->64.09<!--/artifact:key--> ms | <!--artifact:key:p99_ms_cached_at_matched_rate-->17.51<!--/artifact:key--> ms |
| median | <!--artifact:key:p99_ms_uncached_at_matched_rate.p50_ms-->6.29<!--/artifact:key--> ms | <!--artifact:key:p99_ms_cached_at_matched_rate.p50_ms-->1.46<!--/artifact:key--> ms |
| dropped fraction | <!--artifact:key:p99_ms_uncached_at_matched_rate.dropped_fraction-->0.00155<!--/artifact:key--> | <!--artifact:key:p99_ms_cached_at_matched_rate.dropped_fraction-->0.0<!--/artifact:key--> |
| population | <!--artifact:key:p99_ms_uncached_at_matched_rate.population-->1<!--/artifact:key--> ladder level | <!--artifact:key:p99_ms_cached_at_matched_rate.population-->1<!--/artifact:key--> ladder level |
<!-- artifact:tail:end -->

**Both tail figures have a population of one.** The ladder runs each level once,
so neither carries an interval and neither may be read as a replicated result. A
reader who needs a replicated figure should use the boundary-rate replicates
below, which are the only replicated measurements in this campaign.

## The replicates at the boundary rate

<!-- artifact:replicates:begin -->
| | uncached | cached |
|---|---|---|
| offered rate | <!--artifact:key:uncached_replicates_holding_the_boundary_rate.at_target_rate-->6000<!--/artifact:key--> rps | <!--artifact:key:cached_replicates_holding_the_boundary_rate.at_target_rate-->8000<!--/artifact:key--> rps |
| replicates that held the tail budget | <!--artifact:key:uncached_replicates_holding_the_boundary_rate.numerator-->3<!--/artifact:key--> of <!--artifact:key:uncached_replicates_holding_the_boundary_rate.denominator-->3<!--/artifact:key--> | <!--artifact:key:cached_replicates_holding_the_boundary_rate.numerator-->3<!--/artifact:key--> of <!--artifact:key:cached_replicates_holding_the_boundary_rate.denominator-->3<!--/artifact:key--> |
| tail budget | <!--artifact:key:uncached_replicates_holding_the_boundary_rate.p99_ceiling_ms-->250.0<!--/artifact:key--> ms | <!--artifact:key:cached_replicates_holding_the_boundary_rate.p99_ceiling_ms-->250.0<!--/artifact:key--> ms |
<!-- artifact:replicates:end -->

The replicates were run interleaved by round rather than arm by arm, so a drift
in machine conditions over the session cannot land entirely on one arm. Every
run's own record - its timestamps, its gate token and a census of what else was
on the Docker VM before and after - is under `results/raw/`, and the run-by-run
table is in `RUN-RECORD.md`.

**This is evidence about the earlier instability, not proof.** The superseded
record reports three consecutive catastrophic failures at the uncached
boundary rate; here the same rate held on every replicate. The most that
supports is that the earlier instability came from uncontrolled load on the same
machine. One host, one day, one campaign.

## The closed-loop sweep is kept, and it is not the headline

<!-- artifact:closedloop:begin -->
| | uncached | cached |
|---|---|---|
| sustained | <!--artifact:key:closed_loop_sustained_uncached_rps-->7693.4<!--/artifact:key--> rps | <!--artifact:key:closed_loop_sustained_cached_rps-->14317.5<!--/artifact:key--> rps |
| at | <!--artifact:key:closed_loop_sustained_uncached_rps.at_vus-->256<!--/artifact:key--> virtual users | <!--artifact:key:closed_loop_sustained_cached_rps.at_vus-->512<!--/artifact:key--> virtual users |
| p99 there | <!--artifact:key:closed_loop_sustained_uncached_rps.p99_ms-->58.07<!--/artifact:key--> ms | <!--artifact:key:closed_loop_sustained_cached_rps.p99_ms-->70.52<!--/artifact:key--> ms |
| median there | <!--artifact:key:closed_loop_sustained_uncached_rps.p50_ms-->31.64<!--/artifact:key--> ms | <!--artifact:key:closed_loop_sustained_cached_rps.p50_ms-->33.12<!--/artifact:key--> ms |
| population | <!--artifact:key:closed_loop_sustained_uncached_rps.population-->8<!--/artifact:key--> concurrency levels | <!--artifact:key:closed_loop_sustained_cached_rps.population-->8<!--/artifact:key--> concurrency levels |
<!-- artifact:closedloop:end -->

In a closed loop every virtual user waits for its own response, so when the
service slows the generator silently offers less load and the tail budget does
no work at all. That is coordinated omission, and it is why these figures are
**not** the headline. They are kept because two methods disagreeing about the
DIRECTION of the result would itself be a finding, and they do not disagree.

**The earlier document claimed three independent methods converged on one
ratio. That claim is withdrawn and is not restated here.** It cannot be
re-derived from this campaign: the open-loop leg is a bracket rather than a
point, and the closed-loop legs themselves moved between campaigns. A
convergence claim needs three comparable legs, and at least two of the three
are unsettled. Nothing is substituted in its place, because computing a fresh
ratio to rescue the sentence would be the same error that produced it.

## The guards, re-derived over this run

`finalize.py` re-derives every guard from this campaign's own records rather
than inheriting a verdict.

<!-- artifact:guards:begin -->
| guard | what it measured here |
|---|---|
| cache exercised | hit rate <!--artifact:key:cache_hit_rate_pct-->98.92344<!--/artifact:key-->% - <!--artifact:key:cache_hit_rate_pct.hits-->706071<!--/artifact:key--> hits against <!--artifact:key:cache_hit_rate_pct.misses-->7684<!--/artifact:key--> misses over <!--artifact:key:cache_hit_rate_pct.population-->713755<!--/artifact:key--> counted lookups |
| generator headroom | ceiling <!--artifact:key:load_generator_ceiling_rps-->29862.6<!--/artifact:key--> rps, the maximum over <!--artifact:key:load_generator_ceiling_rps.population-->3<!--/artifact:key--> do-nothing probe levels, at p99 <!--artifact:key:load_generator_ceiling_rps.p99_ms-->35.26<!--/artifact:key--> ms |
<!-- artifact:guards:end -->

The hit rate is a steady-state WARM window: every concurrency level runs an
uncounted warmup first, so it is not a cold-start figure and must never be read
as one. It is bounded above by the sequence's own perfect-cache ceiling, which
is recorded in `results/workload-primary.json`. The equivalence, coverage and
two-clock guards carry no figure in this document; their populations and
verdicts are in `RUN-RECORD.md`.

## Does this support the row it was built to test?

The row's own wording, and the figures it claims, are quoted verbatim in the
claim table in `README.md`. They are not restated here: one authoritative copy
of a claim is a record, and a second copy is a thing that can drift.

Measured here, against that row:

| | |
|---|---|
| the direction | holds. The cached arm serves the same work at a lower tail and holds a higher offered rate |
| the tail pair | moves. Both arms are faster than the row claims, and the row's absolute figures must change |
| the capacity claim | is refuted as a point. The ladder supports a bracket per arm and no ratio, and the row's figure lies outside the interval those brackets allow |
| the mechanism | is what this directory measures, and it is what the row may keep |

**Where the measurement disagrees with the row, the measurement wins and the row
changes** - its metric, and its description of what was done and how. The
verdict recorded in the claim table is a reading and it is the owner's; the
correction to the row is recorded separately from this document.

## Retracted

The list below belongs to the numbered review findings of the superseded
campaign, which are in `RESULTS-2026-07-31-SUPERSEDED.md`. These two items stay
here, where `benchlib/workload.py` points a reader at them by name.

<!-- artifact:frozen:begin -->
**Retracted:**

13. The earlier claim that the milder-skew run showed "the aggressive skew does not
    inflate the result" is **withdrawn**. That run executed no guards, no driver
    probe and no checksum pass, and its hit rate barely moved (0.9882 -> 0.9794),
    so it could not discriminate the hypothesis it was cited for. `zipf_a=0.8` gave
    1.527x closed-loop; that number is recorded in
    `sensitivity-mild-skew.json` and should be treated as unvalidated.

    *2026-09-18 - the retraction above is left exactly as written; this is what
    happened next.* Nothing in the tree distinguished that withdrawn run's own
    records from a live one, so anything that later aggregated `results/` would
    have folded it in silently. The three files it produced -
    `sensitivity-mild-skew.json`, `arm-off-mild.json` and `arm-on-mild.json` -
    now each carry a top-level `withdrawn` block naming the date, the reason and
    `aggregate: false`. They are kept, not deleted: a withdrawn machine record is
    evidence of what was withdrawn, and deleting it would leave the retraction
    above pointing at nothing.

14. The claim in `benchlib/workload.py` that uniform traffic over 20,000 tenants
    would give a "near-zero hit rate" is **false** - over 200,000 requests a warm
    cache reaches ~90% even uniformly. Corrected in place.

    *2026-09-18 - the sentence above is left exactly as written, and this line
    exists because it was not true when it was written.* The claim was still in
    `benchlib/workload.py`'s module docstring and in the "Why the key distribution
    is skewed" section of `README.md` for seven weeks after this retraction said
    it had been fixed. Both now state the ~90% bound and show the arithmetic it
    comes from. Editing the sentence above to make it true in hindsight would
    destroy the only evidence that a completion was announced before it happened,
    which is a more useful thing to keep than a tidy record.
<!-- artifact:frozen:end -->

*2026-09-19 - the line above about showing the arithmetic is narrowed, and this
note exists rather than an edit.* `README.md` still states the bound, in words,
but no longer prints the arithmetic inline: a figure in un-rendered prose is
exactly what this directory now refuses, and the arithmetic that was there is in
`benchlib/workload.py`, which the README names. The retraction's own claim was
true when it was written and is narrower now, and saying so beside it is worth
more than a tidy sentence.

## What this benchmark is NOT

<!-- artifact:limits:begin -->
It does not establish what happened at any company. It is a reproducible
measurement of one mechanism at a stated scale on stated hardware, built so a
claim about that mechanism can be defended with numbers that exist, and a bullet
resting on it must describe the measured configuration rather than borrow its
authority for a different one. The capacity figures are quantised lower bounds
and are not capacities, so no ratio is formed from them. The tail pair is one
reading per arm and carries no interval; only the boundary-rate replicates are
replicated, and they are three per arm on one host on one day. The hit rate is a
warm-window figure and cannot be read as a cold-start one. Nothing here is
measured under eviction pressure, with stampede protection, across more than one
host, or against real traffic, and absolute throughput on this machine is not
comparable with any other machine's.
<!-- artifact:limits:end -->
