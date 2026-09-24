# Internships

Work I did during two internships, rebuilt from scratch on my own machine so the
numbers can be checked.

| Placement | Role | When | Where | Folder |
|---|---|---|---|---|
| **DeepLearnHQ** | AI Engineer Intern | Jun 2025 – Aug 2025 | remote | [`deeplearn-hq/`](deeplearn-hq/) |
| **SAUDCONSULT** (Saudi Consulting Services for Engineering Consultancy) | Data Science & Software Engineering Intern | Jun 2024 – Aug 2024 | on site, Riyadh | [`saudconsult/`](saudconsult/) |

## The commit dates here are this repository's, not the placements'

Read this first, because it is the one thing about this repository a visitor can
check in a single click and the one thing that would otherwise look wrong.

**The work described here was done in 2024 and 2025. This repository was built
in 2026-09.** The originals ran on each firm's own systems and are not mine to
publish, so what lives here is built again from scratch on a laptop of my own —
Windows, Docker, one consumer GPU, metered API access — and every figure in it
is measured on that machine, on the date the figure carries.

So the git history below is the history of the **rebuild**. It is not evidence
about when the original work happened, and nothing here asks you to read it that
way.

## What is actually built here, and what is not

| Placement | Workstreams during the placement | Rebuilt and measured here |
|---|---|---|
| DeepLearnHQ | six | **none yet** |
| SAUDCONSULT | five | **one** — [`saudconsult/redis-readthrough-benchmark/`](saudconsult/redis-readthrough-benchmark/) |

**An empty company folder is not a claim.** A folder whose page lists
workstreams with nothing built beneath it means exactly that: the work was done
during the placement, and nothing in this repository measures it yet. Each
company page says which of its workstreams are rebuilt here and which are not,
so the absence is stated rather than left for a reader to infer.

The repository grows as more is built. It does not get quieter about what is
still missing.

## How to read a project folder

Every project folder stands on its own. Open only that folder and its README
tells you the problem it addresses, the exact commands that produce the result,
and what the result was — each figure with the population it was measured over
and the date it was measured on.

Two rules hold across all of them, and they are the reason the folders are worth
reading at all:

- **Every command in a README here was executed before it was written down.** A
  documented command nobody ran is a dead instruction.
- **No measured figure in a project README here was typed by hand.** Each one
  is computed from committed machine records by a script in the folder and
  written into the document by a second script, which, run without `--write`,
  re-renders every figure in memory and byte-compares it. A hand edit to a
  rendered figure is a detected error, not a shortcut.

Where a measurement disagreed with what had previously been said about the work,
the measurement wins and the description changes. That is the point of building
any of this.
