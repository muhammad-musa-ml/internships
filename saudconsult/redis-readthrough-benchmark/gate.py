"""The opening gate: read the conditions a measurement depends on, then mint its token.

    "the arm is verified against the running service's /stats before anything is
     measured - this script records the arm, it does not assert it."
        -- run_k6_sweep.py, in this repository, long before this file existed.

That sentence is this file's whole posture. THE GATE RECORDS FACTS READ FROM THE
WORLD; it does not assert them. Every value under `realized` was read at gate
time, and the run token is a digest of what was read.

WHAT THE TOKEN IS MINTED FROM, AND WHY THOSE THINGS
-----------------------------------------------------
The inputs are the things that would INVALIDATE a measurement if they changed
between the gate and the run. A token minted from an empty or incidental input
set certifies nothing, so they are listed by name in GATE_INPUTS below rather
than globbed: the service and its pinned base image, the schema and the seeding
that build the data it reads, the seeded request sequence and its description,
the three load scripts, the four programs that drive or finalise a run, and the
compose file that pins Postgres and Redis by digest. Changing any one of them
moves the token, and a results file stamped with the old one is then visibly
stamped with the old one.

A file named here but ABSENT is recorded as absent rather than dropped from the
digest. A missing input that simply vanished from the hash would be
indistinguishable from one that was never declared.

TWO DIFFERENT FAILURES, AND THEY MUST NOT BE COLLAPSED
--------------------------------------------------------
    REFUSAL (exit 2)     A precondition makes measuring impossible or
                         meaningless. The gate COULD NOT LOOK. No record is
                         written, because a record would imply it did.
    FAILED GATE (exit 3) The gate looked, and a declared assertion did not hold.
                         A FULL record IS written, `passed: false`, the failing
                         ids named - AND THE TOKEN IS STILL MINTED.

WHY A FAILED GATE STILL MINTS ITS TOKEN.
Minting no token would leave a failed gate with no key at all, and a measurement
that ran anyway would then be undetectable - there would be nothing to compare.
Minting one means such a measurement carries a token that ties it to a gate
whose own record says it did not pass. The failure becomes evidence instead of a
silence.

WHY THE DATE IS NOT PART OF THE DIGEST.
The token is a function of gate CONTENT ONLY, and `dated_at` is stamped BESIDE
it. The two failures a run token exists to catch are (i) results produced under
a gate that has since CHANGED, caught exactly by a content digest, and (ii)
results copied from an EARLIER SESSION, caught by the separately stamped
`dated_at`, which names the gate INSTANCE. Folding the date into the digest buys
no discrimination over that pair and forces a full re-measure after any gate
re-run.

ORDERING IS BY THE RECORDED TIMESTAMPS INSIDE THE JSON, never by file mtime.
mtime is weak across the Windows/WSL2 boundary, it is preserved by ordinary
copies, and it is trivially touched - so a results file copied forward from an
earlier session keeps an entirely plausible mtime while its recorded stamps
cannot be laundered the same way.

WHAT IS RECORDED BUT DELIBERATELY NOT MINTED.
Whether the Docker engine is reachable is written into `environment_probe`,
outside `realized`, and therefore outside the token. The engine being down at
gate time and up at run time is the NORMAL path, not a corruption, so folding it
into the digest would report a false invalidation every time. What the engine
was actually running is recorded per run, by the run recorder, at the instant it
mattered.
"""

# ORDERING RULE, and why it is a comment rather than prose in the docstring: a
# scan over this file that judges by token type sees a docstring as a string
# expression, not a comment. Stating the rule here puts it where such a scan can
# tell an explanation apart from a use.
#
# Records are ordered by the recorded timestamps INSIDE the JSON, never by file
# mtime, for the reasons given above.

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

import canonkit

SCHEMA = "readthrough/gate/1"

# The Windows path ceiling this repository works under. Printed on EVERY branch:
# a limit that is only mentioned when it is breached leaves the passing run
# unable to say what it measured.
MAX_PATH_CHARS = 240

# Assertions whose failure is a REFUSAL (exit 2) rather than a failed gate.
# These say the gate could not look at all.
REFUSAL_ASSERTION_IDS = (
    "ENV-PATH-LENGTH",
    "ENV-PATH-CASE",
)

ONEDRIVE_MARKERS = ("onedrive",)

# THE DECLARED INPUT SET. See the module docstring for why each one is here.
# Order is irrelevant - compute_inputs_hash sorts - but it is written grouped so
# a reader can see the four kinds at a glance.
GATE_INPUTS = (
    # the service under test, and the base image it is pinned to
    "app/Dockerfile",
    "app/main.py",
    "app/seed.py",
    # the workload: how the sequence is built, and the sequence itself
    "benchlib/workload.py",
    "make_sequence.py",
    "results/sequence.json",
    "results/workload.json",
    # the load scripts
    "k6/sweep.js",
    "k6/rate.js",
    "k6/null.js",
    # the programs that drive a run and finalise it
    "run_k6_sweep.py",
    "run_rate_test.py",
    "run_benchmark.py",
    "collect_checksums.py",
    "capture_dbsize.py",
    "finalize.py",
    # the services, pinned by digest
    "docker-compose.yml",
)

GATE_INPUT_COUNT = 17

if len(GATE_INPUTS) != GATE_INPUT_COUNT:
    raise RuntimeError(
        "GATE_INPUTS lists %d file(s) but the committed literal says %d. Update "
        "BOTH in the same commit, or the derived count silently stops checking "
        "and the input set can shrink without anyone seeing it."
        % (len(GATE_INPUTS), GATE_INPUT_COUNT))

# Where the images this benchmark runs are named, and how a pinned one looks.
COMPOSE_FILE = "docker-compose.yml"
DOCKERFILE = "app/Dockerfile"
DIGEST_MARKER = "@sha256:"
_IMAGE_RE = re.compile(r"^\s*image:\s*(\S+)\s*$")
_FROM_RE = re.compile(r"^\s*FROM\s+(\S+)", re.IGNORECASE)

# The load generator is pinned in BOTH drivers, and they must agree: two drivers
# pinning different generators would make "the same benchmark" mean two
# different tools depending on which number you read.
K6_PIN_SOURCES = ("run_k6_sweep.py", "run_rate_test.py")
_K6_IMAGE_RE = re.compile(r"^K6_IMAGE\s*=\s*[\"']([^\"']+)[\"']", re.MULTILINE)

SEQUENCE_FILE = "results/sequence.json"
WORKLOAD_FILE = "results/workload.json"

DOCKER_INFO_ARGV = ("docker", "info", "--format", "{{.ServerVersion}}")
DOCKER_INFO_TIMEOUT_SECONDS = 30


class AssertionResult(object):
    """One declared assertion, its verdict, and the value READ FROM THE WORLD."""

    def __init__(self, id, passed, realized, detail=""):
        self.id = id
        self.passed = passed
        self.realized = realized
        self.detail = detail

    def as_string(self):
        """The stable rendering that enters the token.

        json.dumps with sort_keys so a nested value renders identically in every
        process. repr() would not be safe: float formatting and set iteration
        order can both vary, and a token that is not reproducible is not a token.
        """
        return "%s=%s" % (self.id, json.dumps(self.passed, sort_keys=True))


# ---------------------------------------------------------------------------
# Reading the world
# ---------------------------------------------------------------------------

# Directories excluded from the path enumeration, and the exclusion is
# load-bearing rather than tidiness:
#
#   __pycache__ EXISTS ONLY AFTER A RUN. The longest path is a `realized` value,
#   so it enters the digest; with the cache directory included, a cold run and a
#   warm one mint DIFFERENT tokens for a gate whose content has not changed by a
#   byte.
#
#   results/ IS WRITTEN BY THE RUNS THIS GATE AUTHORISES. Enumerating it would
#   make the gate's own token depend on the output of measurements taken under
#   it, so re-running the gate after a measurement would invalidate that
#   measurement. The gate describes the environment it authorises, never the
#   results of what it authorised. (The two results files in GATE_INPUTS are
#   INPUTS to a measurement rather than output of one: they are the sequence the
#   run replays, and they are hashed by name, not by enumeration.)
EXCLUDED_DIRS = ("__pycache__", ".git", ".venv", ".pytest_cache", ".deepeval",
                 ".mypy_cache", ".ruff_cache", "node_modules", "results")


def enumerate_paths(root):
    """Every path under `root`, as ABSOLUTE forward-slash strings.

    ABSOLUTE, because the ceiling this feeds is a limit on absolute paths. A
    relative measurement under-reports by the whole length of the leading
    directories - it would report a comfortable 40 characters for a tree whose
    real paths sit near the limit, which is to say it could not detect the
    condition it exists to detect.

    Returned rather than acted on, so a caller can supply the list instead.
    """
    found = []
    for base, dirnames, filenames in os.walk(str(root)):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        for name in filenames:
            full = os.path.abspath(os.path.join(base, name))
            found.append(str(full).replace(chr(92), "/"))
    return sorted(found)


def assert_path_length(paths, limit=MAX_PATH_CHARS):
    longest = max((len(p) for p in paths), default=0)
    return AssertionResult(
        "ENV-PATH-LENGTH", longest < limit, longest,
        "longest path is %d character(s), limit %d" % (longest, limit))


def assert_no_case_collision(paths):
    seen = {}
    for path in paths:
        seen.setdefault(path.lower(), []).append(path)
    collisions = sorted(v for v in seen.values() if len(v) > 1)
    return AssertionResult(
        "ENV-PATH-CASE", not collisions, len(collisions),
        "case-only collision(s): %s" % (collisions or "none"))


def assert_not_synced(root):
    """Refuse a sync-managed directory. Matched against the ABSOLUTE root.

    Matching the root AS PASSED would be a check that can never fire: the
    documented way to run this file is `python gate.py` from the repository
    root, which makes `root` the string ".", and no sync marker can appear in
    ".". The realized value is the matched marker rather than a bare bool, so
    the record says WHICH marker fired instead of only that something did.

    It matters more here than it would elsewhere: this repository measures tail
    latency, and a sync client that decides to walk the tree mid-run adds I/O
    the measurement would silently attribute to the service.
    """
    lowered = os.path.abspath(str(root)).replace(chr(92), "/").lower()
    hit = [marker for marker in ONEDRIVE_MARKERS if marker in lowered]
    return AssertionResult(
        "ENV-NOT-SYNCED", not hit, hit,
        "repository root matched %s" % (hit or "no sync marker"))


def read_image_references(root):
    """Every image this benchmark runs, with the file that names it.

    Returns a list of (source, reference) pairs. The compose file's `image:`
    lines and the Dockerfile's `FROM` line are the only two places an image
    enters this repository; the `app` service is BUILT from that Dockerfile
    rather than pulled, which is why it has no `image:` line to read.
    """
    references = []
    compose = os.path.join(str(root), COMPOSE_FILE)
    if os.path.isfile(compose):
        with open(compose, "r", encoding="utf-8") as handle:
            for line in handle:
                if line.lstrip().startswith("#"):
                    continue
                match = _IMAGE_RE.match(line)
                if match:
                    references.append((COMPOSE_FILE, match.group(1)))

    dockerfile = os.path.join(str(root), DOCKERFILE)
    if os.path.isfile(dockerfile):
        with open(dockerfile, "r", encoding="utf-8") as handle:
            for line in handle:
                if line.lstrip().startswith("#"):
                    continue
                match = _FROM_RE.match(line)
                if match:
                    references.append((DOCKERFILE, match.group(1)))
    return references


def assert_images_digest_pinned(root):
    """Every image the benchmark runs is pinned by digest, not by a tag.

    A tag is a moving target, so "the same benchmark" would otherwise silently
    mean different software on a different day. This assertion has already had
    something to say: the service's own base image was pinned by tag until it
    was read from the registry and pinned by digest.

    A population of ZERO is a FAILURE, not a pass. Finding no image reference at
    all means the files that name them were not read, and `all()` over an empty
    sequence is True - which is exactly how a check that examined nothing
    reports that everything is fine.
    """
    references = read_image_references(root)
    unpinned = sorted("%s: %s" % (src, ref) for src, ref in references
                      if DIGEST_MARKER not in ref)
    passed = bool(references) and not unpinned
    return AssertionResult(
        "IMAGES-DIGEST-PINNED", passed,
        sorted("%s: %s" % (src, ref) for src, ref in references),
        "%d image reference(s) read, %d not digest-pinned%s"
        % (len(references), len(unpinned),
           (": " + ", ".join(unpinned)) if unpinned else ""))


def read_load_generator_pins(root):
    """The load-generator image each driver pins, keyed by the file that pins it."""
    pins = {}
    for name in K6_PIN_SOURCES:
        path = os.path.join(str(root), name)
        if not os.path.isfile(path):
            pins[name] = None
            continue
        with open(path, "r", encoding="utf-8") as handle:
            match = _K6_IMAGE_RE.search(handle.read())
        pins[name] = match.group(1) if match else None
    return pins


def assert_one_load_generator(root):
    """Both drivers pin the SAME load generator, by digest.

    Two drivers pinning different generators would make the closed-loop sweep
    and the open-loop capacity test measure with different tools while reporting
    into the same document - and the ratio between them is one of the things
    this benchmark reports.
    """
    pins = read_load_generator_pins(root)
    values = sorted(set(v for v in pins.values() if v))
    missing = sorted(name for name, value in pins.items() if not value)
    passed = (not missing and len(values) == 1
              and DIGEST_MARKER in values[0])
    detail = "%d driver(s) read" % len(pins)
    if missing:
        detail += "; no pin found in %s" % ", ".join(missing)
    elif len(values) != 1:
        detail += "; %d DIFFERENT generators pinned" % len(values)
    elif DIGEST_MARKER not in values[0]:
        detail += "; the shared pin is not a digest"
    else:
        detail += "; both pin the same digest"
    return AssertionResult("LOAD-GENERATOR-PINNED", passed,
                           {"distinct": values, "sources": sorted(pins)},
                           detail)


def read_sequence_facts(root):
    """The replayed sequence, re-counted from the sequence itself.

    The description beside it is not trusted: it is re-derived here so a
    description that no longer matches the sequence it describes is visible at
    gate time rather than after a run has been spent.
    """
    facts = {"sequence_length": None, "sequence_distinct": None,
             "declared_requests": None, "declared_distinct": None,
             "error": None}
    try:
        with open(os.path.join(str(root), SEQUENCE_FILE), "r",
                  encoding="utf-8") as handle:
            sequence = json.load(handle)
        facts["sequence_length"] = len(sequence)
        facts["sequence_distinct"] = len(set(sequence))
        with open(os.path.join(str(root), WORKLOAD_FILE), "r",
                  encoding="utf-8") as handle:
            described = json.load(handle)
        facts["declared_requests"] = described.get("requests")
        facts["declared_distinct"] = described.get("distinct_tenants_touched")
    except (OSError, ValueError, TypeError) as exc:
        facts["error"] = "%s: %s" % (exc.__class__.__name__, exc)
    return facts


def assert_sequence_matches_description(root):
    """The sequence on disk is the sequence the description claims.

    Both arms replay this file in the same order, and every hit-rate figure this
    benchmark publishes is a function of its repetition structure. A sequence
    regenerated under different parameters, or a description left behind by one,
    would move every one of those figures without moving a single line of prose.
    """
    facts = read_sequence_facts(root)
    passed = (facts["error"] is None
              and isinstance(facts["sequence_length"], int)
              and facts["sequence_length"] > 0
              and facts["sequence_length"] == facts["declared_requests"]
              and facts["sequence_distinct"] == facts["declared_distinct"])
    if facts["error"]:
        detail = "could not read the sequence: %s" % facts["error"]
    else:
        detail = ("sequence holds %s request(s) over %s distinct key(s); the "
                  "description declares %s and %s"
                  % (facts["sequence_length"], facts["sequence_distinct"],
                     facts["declared_requests"], facts["declared_distinct"]))
    return AssertionResult("WORKLOAD-SEQUENCE-DESCRIBED", passed, facts, detail)


def probe_docker(runner=None):
    """Is the engine reachable, and what is it? RECORDED, never minted.

    Outside `realized` on purpose - see the module docstring. A down engine at
    gate time is the normal path: the gate authorises a measurement that has not
    started yet.
    """
    runner = runner or _default_docker_info
    try:
        version = str(runner(list(DOCKER_INFO_ARGV))).strip()
    except Exception as exc:                                    # noqa: BLE001
        return {"reachable": False, "server_version": None,
                "error": "%s: %s" % (exc.__class__.__name__, exc)}
    return {"reachable": True, "server_version": version, "error": None}


def _default_docker_info(argv):
    completed = subprocess.run(argv, capture_output=True, text=True,
                               timeout=DOCKER_INFO_TIMEOUT_SECONDS, shell=False)
    if completed.returncode != 0:
        raise OSError("docker info exited %d: %s"
                      % (completed.returncode,
                         (completed.stderr or "").strip()[-300:]))
    return completed.stdout


def compute_inputs_hash(root, inputs):
    """Digest the DECLARED input set, recording absences rather than skipping them.

    A file simply missing from the digest is indistinguishable from one that was
    never declared. Recording `<absent>` keeps the two apart, so a disappearing
    input MOVES the token instead of quietly shrinking its domain.
    """
    lines = []
    for relative in sorted(inputs or []):
        full = os.path.join(str(root), relative)
        if os.path.isfile(full):
            lines.append("%s=%s" % (relative, canonkit.sha256_file(full)))
        else:
            lines.append("%s=<absent>" % relative)
    return canonkit.sha256_bytes("\n".join(lines).encode("ascii", "backslashreplace"))


def missing_inputs(root, inputs):
    """The declared inputs that are not on disk. Reported, never silently dropped."""
    return sorted(rel for rel in (inputs or [])
                  if not os.path.isfile(os.path.join(str(root), rel)))


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------


def evaluate_assertions(root, paths=None):
    """Evaluate every declared assertion and return the results in a fixed order."""
    if paths is None:
        paths = enumerate_paths(root)
    return [
        assert_path_length(paths),
        assert_no_case_collision(paths),
        assert_not_synced(root),
        assert_images_digest_pinned(root),
        assert_one_load_generator(root),
        assert_sequence_matches_description(root),
    ]


def _repair_for(result):
    if result.id == "ENV-PATH-LENGTH":
        return ("move this repository nearer the drive root so its longest path "
                "is under %d characters, then re-run `python gate.py`."
                % MAX_PATH_CHARS)
    if result.id == "ENV-PATH-CASE":
        return ("rename one of the colliding paths so no two differ only by "
                "case, then re-run `python gate.py`.")
    return "fix the condition named above, then re-run `python gate.py`."


def build_gate_record(slug, results, inputs_hash, dated_at, dated_at_utc,
                      declared_inputs, absent_inputs, environment_probe):
    """Assemble the record. THE TOKEN IS MINTED FROM CONTENT ONLY."""
    assertions = [r.as_string() for r in results]
    realized = {}
    for result in results:
        realized[result.id] = result.realized
    failed_ids = [r.id for r in results if not r.passed]

    # CONTENT ONLY. `dated_at` is a parameter of this function and is
    # deliberately NOT passed to the mint - it is stamped into the record below,
    # BESIDE the token, for the reason given in the module docstring.
    token = canonkit.mint_run_token(slug, assertions, realized, inputs_hash)

    return {
        "schema": SCHEMA,
        "schema_version": canonkit.SCHEMA_VERSION,
        "artifact": slug,
        "passed": not failed_ids,
        "run_token": token,
        "dated_at": dated_at,
        "dated_at_utc": dated_at_utc,
        "assertions": assertions,
        "realized": realized,
        "inputs_hash": inputs_hash,
        "failed_ids": failed_ids,
        # This repository's gate quotes no fallback wording: its failure mode is
        # "do not measure", and `failed_ids` above is what says why. The two
        # fields are kept because the record's shape is shared, and an empty
        # string is a recorded emptiness rather than an absent key.
        "fallback_wording": "",
        "fallback_source": None,
        "env": {
            "platform": sys.platform,
            "python": sys.version.split()[0],
        },
        "declared_inputs": sorted(declared_inputs),
        "declared_input_count": len(declared_inputs),
        "absent_inputs": absent_inputs,
        "environment_probe": environment_probe,
    }


def run_gate(root, slug, paths=None, inputs=GATE_INPUTS, clock_local=None,
             clock_utc=None, docker_runner=None, stream=None):
    """Run the gate. Returns 0 (pass) or 3 (failed gate); refusals exit 2."""
    clock_local = clock_local or canonkit.now_local
    clock_utc = clock_utc or canonkit.now_utc
    stream = stream if stream is not None else sys.stdout

    results = evaluate_assertions(root, paths=paths)
    by_id = dict((r.id, r) for r in results)

    # PRINTED ON EVERY BRANCH, before any decision. A measurement the passing run
    # never reports is indistinguishable from one it never took.
    absent = missing_inputs(root, inputs)
    stream.write("[gate] slug = %s\n" % slug)
    stream.write("[gate] longest path = %d characters (limit %d)\n"
                 % (by_id["ENV-PATH-LENGTH"].realized, MAX_PATH_CHARS))
    stream.write("[gate] declared inputs = %d, absent = %d%s\n"
                 % (len(inputs), len(absent),
                    (" (" + ", ".join(absent) + ")") if absent else ""))
    for result in results:
        stream.write("[gate]   %-28s %-4s %s\n"
                     % (result.id, "pass" if result.passed else "FAIL",
                        result.detail))

    # REFUSE FIRST. Before any record, before the token, before measuring.
    for result in results:
        if result.id in REFUSAL_ASSERTION_IDS and not result.passed:
            canonkit.die(
                canonkit.EXIT_DID_NOT_RUN,
                "%s the gate cannot measure here -- %s failed: %s\n"
                "  REPAIR: %s"
                % (canonkit.REFUSAL_PREFIX, result.id, result.detail,
                   _repair_for(result)))

    dated_at = clock_local()
    dated_at_utc = clock_utc()
    failed = [r for r in results if not r.passed]

    record = build_gate_record(
        slug, results, compute_inputs_hash(root, inputs), dated_at,
        dated_at_utc, inputs, absent, probe_docker(docker_runner))

    violations = canonkit.validate_gate(record)
    if violations:
        canonkit.die(canonkit.EXIT_DID_NOT_RUN,
                     "%s the gate assembled a record its own validator rejects "
                     "(%d violation(s)):\n%s\n  REPAIR: this is a defect in "
                     "gate.py, not in the environment."
                     % (canonkit.REFUSAL_PREFIX, len(violations),
                        "\n".join(violations)))

    # THE RECORD IS WRITTEN ON BOTH BRANCHES, before the verdict is known. A
    # failed gate is a complete record that happens to say `passed: false`, not
    # an absence. A measurement that ran anyway then carries a token tying it to
    # a gate whose record says it did not pass, instead of no key at all.
    results_dir = os.path.join(str(root), "results")
    canonkit.atomic_write_json(os.path.join(results_dir, "gate.json"), record)

    if failed:
        canonkit.report("GATE", False, len(failed), len(results), 1,
                        note="FAILED: %s -- token %s minted anyway"
                             % (", ".join(r.id for r in failed),
                                record["run_token"][:12]))
        return canonkit.EXIT_GUARD_FAIL

    canonkit.report("GATE", True, 0, len(results), 1,
                    note="token %s dated %s"
                         % (record["run_token"][:12], dated_at))
    return canonkit.EXIT_PASS


def default_slug(root):
    """This repository's own directory name.

    A DEFAULT rather than a required argument, deliberately: the command a
    reader is told to run must be runnable exactly as written, and a gate whose
    documented invocation exits for want of an argument is a dead instruction.
    The resolved value prints on every branch and is recorded in the gate, so
    nothing about which name was minted under is left implicit.
    """
    return os.path.basename(os.path.abspath(str(root))) or "artifact"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Read the conditions a measurement depends on, record them, "
                    "and mint the run token every measuring script requires.")
    parser.add_argument("--root", default=".",
                        help="repository root to gate (default: the current "
                             "directory)")
    parser.add_argument("--slug", default=None,
                        help="the name this gate is minted under (default: the "
                             "root's directory name)")
    args = parser.parse_args(argv)
    slug = args.slug or default_slug(args.root)
    return run_gate(args.root, slug)


if __name__ == "__main__":
    sys.exit(main())
