# Databricks notebook source
# MAGIC %md
# MAGIC # T7 · Forward-ETL setup — Lakebase Lakehouse Sync (Pattern B)
# MAGIC
# MAGIC Lakehouse Sync natively replicates the writable Lakebase **staging** tables
# MAGIC into UC-managed Delta history tables as **SCD Type 2** — every insert /
# MAGIC update / delete becomes a new row with `_change_type`, `_commit_timestamp`,
# MAGIC `_lsn`, `_xid` system columns. Replication needs **no external compute** —
# MAGIC it's powered by the `wal2delta` Postgres extension inside Lakebase.
# MAGIC
# MAGIC This notebook enables sync once (idempotent). The actual promotion into
# MAGIC `gold.customer_notes` is done by `dedup_into_gold.py`, which the Reports
# MAGIC page triggers via the Jobs API.
# MAGIC
# MAGIC > Run once, manually, as a workspace admin / the app SP. Wired here for
# MAGIC > reproducibility; the live enablement is also possible from the Lakebase UI.

# COMMAND ----------

dbutils.widgets.text("pg_uc_catalog", "capstone_lb_ap")
dbutils.widgets.text("gold_catalog", "lakebase_capstone_catalog")

PG_UC_CATALOG = dbutils.widgets.get("pg_uc_catalog")   # UC catalog fronting Lakebase
GOLD_CATALOG = dbutils.widgets.get("gold_catalog")
HISTORY_SCHEMA = "lakehouse_sync"                        # where lb_*_history land

STAGING_TABLES = [
    "customer_notes_staging",
    "customer_segment_overrides_staging",
]

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {GOLD_CATALOG}.{HISTORY_SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Enable Lakehouse Sync per staging table
# MAGIC
# MAGIC The Beta SQL surface (adjust to the version available in your workspace;
# MAGIC the equivalent is also a one-click toggle in the Lakebase UI):
# MAGIC
# MAGIC ```sql
# MAGIC ALTER DATABASE INSTANCE `capstone-pg`
# MAGIC   ENABLE LAKEHOUSE SYNC FOR TABLE public.customer_notes_staging
# MAGIC   INTO lakebase_capstone_catalog.lakehouse_sync.lb_customer_notes_staging_history;
# MAGIC ```

# COMMAND ----------

for tbl in STAGING_TABLES:
    target = f"{GOLD_CATALOG}.{HISTORY_SCHEMA}.lb_{tbl}_history"
    print(f"→ enable Lakehouse Sync: public.{tbl}  →  {target}")
    # Uncomment once your workspace exposes the ALTER DATABASE INSTANCE syntax:
    # spark.sql(f"""
    #   ALTER DATABASE INSTANCE `capstone-pg`
    #     ENABLE LAKEHOUSE SYNC FOR TABLE public.{tbl}
    #     INTO {target}
    # """)

print("Lakehouse Sync setup complete (or enable via the Lakebase UI).")
