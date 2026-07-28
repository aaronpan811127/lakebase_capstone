# T9 — Lakebase Ops

Instance: `capstone-pg` (PG 16, CU_1, us-west-2, 7-day retention window).

---

## T9a — Branch + PITR

Lakebase branches are copy-on-write child instances forked from a parent at a
point in time. A branch is fully isolated: writes (and destructive deletes) on
the branch never touch the parent. This is the safe way to test a destructive
change, and the mechanism behind point-in-time restore (PITR).

### What was done (live)

1. **Recorded a pre-branch timestamp** `T0 = 2026-07-28T23:24:59Z`.
2. **Created a child branch** from `capstone-pg` at the current head:
   ```bash
   databricks database create-database-instance --json '{
     "name": "capstone-pg-branch",
     "capacity": "CU_1",
     "parent_instance_ref": { "name": "capstone-pg" }
   }' --profile lakebase-capstone
   ```
   Branch came up `AVAILABLE` with its own DNS
   (`ep-ancient-scene-d189h0wu...`) and `parent_instance_ref.uid` pointing at
   the parent — confirming the fork.
3. **Ran the destructive delete on the branch only:**
   ```sql
   DELETE FROM customer_notes_staging;   -- on capstone-pg-branch
   ```
4. **Verified isolation** — row counts before/after:

   | table | parent `capstone-pg` | branch `capstone-pg-branch` |
   |---|---|---|
   | `customer_notes_staging` before DELETE | 1 | 1 (inherited at branch point) |
   | `customer_notes_staging` after DELETE | **1 (unchanged)** | **0 (deleted)** |

   The parent is untouched — exactly the safety property PITR relies on.
5. **Cleaned up** the branch: `databricks database delete-database-instance
   capstone-pg-branch --purge`.

### Parent PITR restore (procedure)

The parent instance backs the running app, so a live parent rollback was **not**
executed against production. To restore the parent to a timestamp *before* a
destructive change, create a new instance branched at that time (PITR = branch
at `T0`), then promote / repoint the app:

```bash
databricks database create-database-instance --json '{
  "name": "capstone-pg-restored",
  "capacity": "CU_1",
  "parent_instance_ref": {
    "name": "capstone-pg",
    "branch_time": "2026-07-28T23:24:59Z"
  }
}' --profile lakebase-capstone
```

`branch_time` (or `lsn`) selects the restore point within the 7-day retention
window. The restored instance contains the data as of `T0` — i.e. before the
`DELETE` — which is the PITR guarantee.

> **Screenshots:** branch creation (Lakebase UI → Branches), the branch row
> count = 0 vs parent = 1 after DELETE, and the restored-instance row count.
> _(Placeholder — capture from the workspace UI.)_

---

## T9b — Query insights (index impact)

**Scenario:** the audit-log lookup `WHERE actor_email = …` is a Seq Scan without
an index. Seeded `customer_audit_log` to ~20k rows and ran the query 100×.

Client-side wall-clock latency is dominated by the ~250 ms laptop→us-west-2
round trip, which masks the query cost, so the improvement is reported as
**server-side execution time** via `EXPLAIN (ANALYZE, TIMING)` (30 samples each).

### Before — no index

```
Seq Scan on customer_audit_log
  (cost=0.00..497.04 rows=400 width=30) (actual time=0.028..5.013 rows=400)
exec p50 = 5.38 ms   p95 = 8.13 ms
```

### Fix

```sql
CREATE INDEX idx_audit_actor ON customer_audit_log (actor_email);
ANALYZE customer_audit_log;
```

### After — indexed

```
Bitmap Heap Scan on customer_audit_log
  (cost=7.39..268.99 rows=400 width=30) (actual time=0.200..0.881 rows=400)
  Recheck Cond: ((actor_email)::text = 'user7@example.com')
exec p50 = 1.39 ms   p95 = 1.55 ms
```

### Result

| metric | before (Seq Scan) | after (index) | improvement |
|---|---|---|---|
| plan | Seq Scan | Bitmap Heap Scan (idx_audit_actor) | — |
| exec p50 | 5.38 ms | 1.39 ms | 3.9× |
| **exec p95** | **8.13 ms** | **1.55 ms** | **5.3×** |

The planner switched from a full Seq Scan to an index-backed Bitmap Heap Scan
and server-side p95 dropped **5.3×**. The index (`idx_audit_actor`) is kept in
the schema.

> **Screenshots:** Lakebase Query Performance UI showing the query before/after,
> or `pg_stat_statements` mean/p95 rows. _(Placeholder — capture from the UI.)_
