# DeepLearnHQ

**AI Engineer Intern, Jun 2025 – Aug 2025, remote.**

This folder belongs to a repository of from-scratch rebuilds, built 2026-09, of
work done during that placement. The originals ran on the company's own systems
and are not mine to publish, so anything that appears here is built again on my
own machine and measured there.

**Nothing from this placement is rebuilt here yet.** This page exists so the
folder says what it is rather than reading as a claim about work that is not in
it. See the [repository README](../README.md) for why the commit dates are the
rebuild's and not the placement's.

## The six workstreams

Named here in plain words. These describe what the placement worked on; none of
them carries a measured figure in this repository, because none of them has been
rebuilt yet.

| | Workstream | What it was |
|---|---|---|
| P1 | Evaluation gate and run reproducibility | A blocking pre-merge gate that scores every proposed prompt or model change against a held-out golden set before release, and a run store in which a reported headline number can be re-derived from the run id that produced it. |
| P2 | Request telemetry and token accounting | Tracing one internal language-model path end to end — prompt version, model id, retrieved-chunk ids, token counts, per-stage latency — into a span store, so a single trace answers which stage is slow and which prompt version regressed. |
| P3 | Token economics: cost-tier routing and prefix caching | Routing the easy majority of requests to a cheap model tier and auditing the misroutes that an aggregate quality number averages away, plus separating two things usually reported as one: hoisting a stable prefix DELETES tokens, a provider cache changes the PRICE of what remains. |
| P4 | Self-hosted serving and inference optimisation | Serving an open-weights instruct model behind an OpenAI-compatible endpoint in a container on a single workstation GPU, with a load harness whose own ceiling is measured before the system's, a precision sweep showing where quality breaks, and one server flag isolated with everything else fixed. |
| P5 | Retrieval-versus-adaptation spike | Indexing one corpus in two vector stores, sweeping each into a recall-versus-latency frontier, and comparing them on the axes a store choice actually turns on — build time, index memory, filtered-query latency — against a fine-tuned adapter and a prompted baseline scored on the same golden set. |
| P6 | Bounded agent and scoped tool surface | A small agent with a hard step cap, a per-run token budget and backoff retries, scored on a fixed scenario suite by a deterministic end-state checker rather than on demos, with its tool surface served under per-tool credentials, rate limits and one audit record per call. |

## What is rebuilt here

**Nothing, yet.** When a workstream is rebuilt it gets a folder beside this
page, and that folder is sufficient on its own: the problem, the commands, and
the measured result with its population and its date.
