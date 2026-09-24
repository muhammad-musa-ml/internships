"""Deterministic seed + the guard that keeps the uncached arm honest.

Everything here is driven by a fixed SEED, so the dataset is reproducible byte for
byte across runs and across arms - the same discipline PH-A used to guarantee both
corpora were identical.

THE PLAN ASSERTION IS THE POINT. After seeding it EXPLAINs the exact resolve query
the service runs and FAILS if the plan contains a sequential scan. An unindexed
join would make the uncached arm arbitrarily slow and the speedup arbitrarily
large - a rigged comparison. This turns "we indexed it properly" from a claim in a
README into something the build refuses to proceed without.
"""
from __future__ import annotations

import asyncio
import os
import random
import sys

import asyncpg

SEED = 20260731
PLANS = ["free", "team", "business", "enterprise"]
REGIONS = ["us-east-1", "us-west-2", "eu-central-1", "ap-southeast-1"]
FEATURE_KEYS = [
    "sso", "audit_log", "custom_domain", "api_v2", "webhooks", "rbac",
    "data_export", "sandbox", "priority_support", "byok", "ip_allowlist", "scim",
]
QUOTA_KEYS = ["api_rpm", "seats", "storage_gb", "projects", "webhook_endpoints", "retention_days"]

DDL = """
DROP TABLE IF EXISTS features, quotas, tenants CASCADE;
CREATE TABLE tenants (
  id     integer PRIMARY KEY,
  name   text NOT NULL,
  plan   text NOT NULL,
  region text NOT NULL
);
CREATE TABLE features (
  tenant_id   integer NOT NULL REFERENCES tenants(id),
  feature_key text    NOT NULL,
  enabled     boolean NOT NULL,
  PRIMARY KEY (tenant_id, feature_key)
);
CREATE TABLE quotas (
  tenant_id   integer NOT NULL REFERENCES tenants(id),
  quota_key   text    NOT NULL,
  limit_value integer NOT NULL,
  PRIMARY KEY (tenant_id, quota_key)
);
CREATE INDEX ON features (tenant_id);
CREATE INDEX ON quotas   (tenant_id);
"""

RESOLVE_SQL = """
SELECT t.id, t.name, t.plan, t.region,
       COALESCE((SELECT json_agg(json_build_object('k', f.feature_key, 'e', f.enabled)
                                 ORDER BY f.feature_key)
                 FROM features f WHERE f.tenant_id = t.id), '[]'::json) AS features,
       COALESCE((SELECT json_agg(json_build_object('k', q.quota_key, 'v', q.limit_value)
                                 ORDER BY q.quota_key)
                 FROM quotas q WHERE q.tenant_id = t.id), '[]'::json) AS quotas
FROM tenants t
WHERE t.id = $1
"""


async def main(n_tenants: int) -> int:
    rnd = random.Random(SEED)
    conn = await asyncpg.connect(os.environ["PG_DSN"])
    await conn.execute(DDL)

    tenants, features, quotas = [], [], []
    for tid in range(1, n_tenants + 1):
        tenants.append((tid, f"tenant-{tid:06d}", rnd.choice(PLANS), rnd.choice(REGIONS)))
        for fk in FEATURE_KEYS:
            features.append((tid, fk, rnd.random() < 0.55))
        for qk in QUOTA_KEYS:
            quotas.append((tid, qk, rnd.randrange(10, 100000)))

    await conn.copy_records_to_table("tenants", records=tenants,
                                     columns=["id", "name", "plan", "region"])
    await conn.copy_records_to_table("features", records=features,
                                     columns=["tenant_id", "feature_key", "enabled"])
    await conn.copy_records_to_table("quotas", records=quotas,
                                     columns=["tenant_id", "quota_key", "limit_value"])
    await conn.execute("ANALYZE tenants; ANALYZE features; ANALYZE quotas;")

    sizes = await conn.fetchrow("""
        SELECT pg_total_relation_size('tenants')
             + pg_total_relation_size('features')
             + pg_total_relation_size('quotas') AS total_bytes
    """)
    print(f"[seed] tenants={len(tenants)} features={len(features)} quotas={len(quotas)}")
    print(f"[seed] total relation bytes = {sizes['total_bytes']} "
          f"({sizes['total_bytes'] / 1048576:.1f} MiB) against shared_buffers=512MB")

    # ---- THE NON-STRAWMAN GUARD -------------------------------------------------
    # HARDENED after adversarial review. The first version had three weaknesses,
    # each of which let it pass while proving less than it claimed:
    #   (a) it EXPLAINed a literal-substituted copy of the SQL, not the
    #       PARAMETERIZED statement the service executes - and Postgres can choose
    #       a DIFFERENT (generic) plan for a prepared statement;
    #   (b) it substring-matched "Seq Scan" and asserted nothing positive, so a
    #       plan with no index scan at all would have passed;
    #   (c) it sampled exactly one tenant.
    # It now PREPAREs the real statement, samples several tenants, and asserts
    # positively: index scans present, no sequential scan, and zero disk reads.
    await conn.execute("PREPARE resolve_stmt (integer) AS " + RESOLVE_SQL.replace("$1", "$1"))
    sample = [1, 2, 500, 7777, n_tenants // 2, n_tenants]
    failures = []
    for tid in sample:
        rows = await conn.fetch(
            f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) EXECUTE resolve_stmt({tid})")
        plan = "\n".join(r[0] for r in rows)
        if tid == sample[0]:
            print("[seed] --- resolve plan (prepared statement, tenant 1) ---")
            print(plan)
        n_index = plan.count("Index Scan")
        seq_scan = "Seq Scan" in plan
        # `read=` in a BUFFERS plan means blocks fetched from disk rather than the
        # buffer pool. The uncached arm is claimed to be disk-free; assert it.
        #
        # SCOPED TO THE EXECUTION PLAN. EXPLAIN also prints a trailing `Planning:`
        # section, and planning legitimately reads catalog blocks ONCE while the
        # plan cache is cold - it is not per-request I/O and asserting on it made
        # the guard fail for the wrong reason on its first run. Everything from
        # "Planning:" onward is excluded; the execution nodes above it are not.
        exec_plan = plan.split("Planning:")[0]
        disk_reads = [ln for ln in exec_plan.splitlines() if "read=" in ln]
        if seq_scan or n_index < 3 or disk_reads:
            failures.append((tid, seq_scan, n_index, len(disk_reads)))
    await conn.execute("DEALLOCATE resolve_stmt")
    if failures:
        for tid, ss, ni, dr in failures:
            print(f"[seed] FAIL tenant={tid}: seq_scan={ss} index_scans={ni} "
                  f"disk_read_lines={dr}", file=sys.stderr)
        print("[seed] The uncached arm would be handicapped and the comparison "
              "rigged. Refusing.", file=sys.stderr)
        await conn.close()
        return 2
    print(f"[seed] PLAN GUARD PASSED on {len(sample)} tenants (prepared statement): "
          f">=3 index scans, no sequential scan, no disk reads.")

    # Warm the buffer pool so the uncached arm does not pay first-touch disk I/O
    # that the cached arm would never pay. pg_prewarm is contrib; if it is absent
    # say so rather than silently skipping - a warm-cache claim that quietly did
    # not happen is exactly the kind of unverified assertion this project bans.
    try:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_prewarm")
        # HEAPS **AND INDEXES**. The first version prewarmed only the three heap
        # relations, so the index relations the resolve actually walks were left to
        # chance - adversarial review caught it. Index names are read from the
        # catalog rather than hard-coded, so a renamed or added index cannot be
        # silently skipped.
        rels = ["tenants", "features", "quotas"]
        idx = await conn.fetch(
            "SELECT indexname FROM pg_indexes WHERE schemaname='public' "
            "AND tablename = ANY($1::text[])", rels)
        rels += [r["indexname"] for r in idx]
        for rel in rels:
            await conn.fetchval(f'SELECT pg_prewarm(\'"{rel}"\')')
        print(f"[seed] buffer pool prewarmed (pg_prewarm): {len(rels)} relations "
              f"({len(idx)} of them indexes)")
    except Exception as exc:  # noqa: BLE001
        print(f"[seed] WARNING: pg_prewarm unavailable ({exc.__class__.__name__}: {exc}); "
              f"falling back to a full-scan warm pass", file=sys.stderr)
        await conn.fetchval("SELECT count(*) FROM tenants")
        await conn.fetchval("SELECT count(*) FROM features")
        await conn.fetchval("SELECT count(*) FROM quotas")
        print("[seed] buffer pool warmed by full scan")
    await conn.close()
    return 0


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    raise SystemExit(asyncio.run(main(n)))
