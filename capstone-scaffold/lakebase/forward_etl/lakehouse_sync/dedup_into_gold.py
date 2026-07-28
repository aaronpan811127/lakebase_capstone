# Databricks notebook source
# MAGIC %md
# MAGIC # T7 · Forward-ETL — dedup `lb_*_history` → gold (Pattern B)
# MAGIC
# MAGIC Lakehouse Sync appends every staging change as an SCD2 row in
# MAGIC `lb_customer_notes_staging_history`. This job collapses that history to the
# MAGIC **latest surviving row per note** (drop deletes, keep newest by `_lsn`) and
# MAGIC `MERGE`s it into `gold.customer_notes`.
# MAGIC
# MAGIC **Idempotent:** MERGE on `note_id` — re-running with no new history rows is
# MAGIC a no-op. This is the job the Reports page triggers via
# MAGIC `POST /api/jobs/run-forward-etl`.

# COMMAND ----------

dbutils.widgets.text("gold_catalog", "lakebase_capstone_catalog")
GOLD_CATALOG = dbutils.widgets.get("gold_catalog")
HISTORY_SCHEMA = "lakehouse_sync"
GOLD = f"{GOLD_CATALOG}.gold"
HISTORY = f"{GOLD_CATALOG}.{HISTORY_SCHEMA}.lb_customer_notes_staging_history"

# COMMAND ----------

spark.sql(f"""
  CREATE TABLE IF NOT EXISTS {GOLD}.customer_notes (
    note_id      STRING,
    customer_id  STRING,
    author_email STRING,
    note_text    STRING,
    created_at   TIMESTAMP
  ) USING DELTA
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Collapse SCD2 history → latest surviving row per note
# MAGIC
# MAGIC `_change_type` ∈ {insert, update_postimage, delete}; keep the newest
# MAGIC non-delete row per PK by `_lsn` (fall back to `_commit_timestamp`).

# COMMAND ----------

from pyspark.sql import Window
from pyspark.sql import functions as F

if not spark.catalog.tableExists(HISTORY):
    dbutils.notebook.exit(
        f"History table {HISTORY} not found — enable Lakehouse Sync first (setup_sync.py)."
    )

hist = spark.table(HISTORY)
order_col = "_lsn" if "_lsn" in hist.columns else "_commit_timestamp"

w = Window.partitionBy("note_id").orderBy(F.col(order_col).desc())
latest = (
    hist.withColumn("_rn", F.row_number().over(w))
        .filter("_rn = 1")
        .filter("_change_type != 'delete'")
        .select("note_id", "customer_id", "author_email", "note_text", "created_at")
)
latest.createOrReplaceTempView("latest_notes")
print(f"surviving unique notes: {latest.count()}")

# COMMAND ----------

spark.sql(f"""
  MERGE INTO {GOLD}.customer_notes t
  USING latest_notes s ON t.note_id = s.note_id
  WHEN MATCHED THEN UPDATE SET *
  WHEN NOT MATCHED THEN INSERT *
""")

total = spark.table(f"{GOLD}.customer_notes").count()
print(f"gold.customer_notes rowcount: {total}")
dbutils.notebook.exit(f"OK: {total} notes in gold.customer_notes")
