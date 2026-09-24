# SAUDCONSULT

**Data Science & Software Engineering Intern, Jun 2024 – Aug 2024, on site in
Riyadh.**

Saudi Consulting Services for Engineering Consultancy. This folder belongs to a
repository of from-scratch rebuilds, built 2026-09, of work done during that
placement. The originals ran on the firm's own systems and are not mine to
publish, so what appears here is built again on my own machine and measured
there — which is also why the commit dates are the rebuild's rather than the
placement's. The [repository README](../README.md) says that in full.

## The five workstreams

Named here in plain words, so that a project folder beside this page can be
placed in the work it came out of.

| | Workstream | What it was |
|---|---|---|
| P1 | Bilingual specification retrieval evaluation | Design reviewers ask the same question dozens of times a week — which clause of which standard governs this detail — and the correspondence is Arabic-first while the governing volumes it cites are English. A bounded pilot indexed one building-type programme's documents and measured retrieval against a gold set whose clause judgments came from the discipline engineers who read both languages natively. |
| P2 | Project-controls data platform | Project controls ran on periodic exports refreshed by hand every working morning, from five separate systems, with each dashboard carrying its own private definition of the truth. This built the scheduled pipeline, the warehouse behind it and the tested, certified metric layer on top. |
| P3 | Engineering-format data extraction | Two of the firm's richest datasets lived inside tools that do not hand data out easily. The scheduling feed was a tabular export that drops the relationships, calendars and resource assignments which make a schedule a network, so the export format itself was parsed to recover them; building-model exports were walked into a checked per-element store; and the classification codes a scored rule could not resolve confidently were routed past a human reviewer whose decisions became the metric. |
| P4 | Inspection-outcome triage: calibration, operating point and drift | Site inspection produces far more observations than a quality team can chase and the ones that become a nonconformance are rare. The classifier was the quick part; the rest was the work that decides whether such a model is usable at all — calibration, an operating point taken from a stated cost ratio and a real weekly capacity, and a drift check replayed against the record. |
| P5 | Internal query service: delivery, caching and natural-language access | The platform was only useful if the people who needed it could reach it without opening a SQL client. The certified metric layer was packaged behind a small internal service on the firm's single-node cluster, with a read-through cache over precomputed metric rows because dashboard traffic is heavily skewed, and a natural-language interface that never writes SQL of its own. |

## What is rebuilt here

**One thing, and it is scoped narrowly on purpose.**

[`redis-readthrough-benchmark/`](redis-readthrough-benchmark/) measures the caching
**mechanism** from P5 — a read-through cache in front of a repeated per-request
database lookup — built from scratch on my own machine and load-tested there.

It is deliberately **not** a reproduction of the service itself. That service
ran inside the firm and was never load-tested there, so there is no measurement
of it to reproduce; what this rebuild does is measure the same mechanism at a
comparable key scale, so the order of magnitude behind the claim can be checked
instead of taken. Its README opens with that distinction, names the claim it is
testing in full, and closes with a paragraph on what it does not show. Read both
before quoting anything from it.

The other four workstreams are not rebuilt here. When one is, it gets its own
folder beside this page.
