# Databricks notebook source
# MAGIC %md
# MAGIC # T7 · Forward-ETL — psycopg + MERGE INTO Delta (Pattern A, pull/on-demand)
# MAGIC
# MAGIC Reads unprocessed rows from the Lakebase **staging** tables via psycopg,
# MAGIC `MERGE`s them into Delta **gold**, then marks the staged rows
# MAGIC `processed = true` — all in one pass. The Reports page triggers this job
# MAGIC via the Jobs API (`POST /api/jobs/run-forward-etl`).
# MAGIC
# MAGIC **Idempotent:** only `processed = false` rows are read, and the MERGE keys
# MAGIC on the row PK, so re-running with no new staged rows is a no-op.
# MAGIC
# MAGIC Chosen over Pattern B (Lakehouse Sync / Lakebase CDF) because that feature
# MAGIC requires an **Autoscaling Postgres 17** instance; `capstone-pg` is
# MAGIC provisioned **Postgres 16**, so CDF cannot be enabled. Pattern A needs no
# MAGIC extra Databricks feature and runs on the existing instance.

# COMMAND ----------

# MAGIC %md
# MAGIC `psycopg[binary]` is provided via the serverless job environment
# MAGIC (see resources/jobs.yml `environments`), so no in-notebook `%pip` /
# MAGIC `restartPython()` is needed — those are unreliable on serverless.

# COMMAND ----------

dbutils.widgets.text("gold_catalog", "lakebase_capstone_catalog")
dbutils.widgets.text("instance_name", "capstone-pg")
dbutils.widgets.text("database_name", "capstone_db")

GOLD_CATALOG = dbutils.widgets.get("gold_catalog")
INSTANCE = dbutils.widgets.get("instance_name")
DB_NAME = dbutils.widgets.get("database_name")
GOLD = f"{GOLD_CATALOG}.gold"

# COMMAND ----------

# MAGIC %md ## Connect to Lakebase (as the job's identity)

# COMMAND ----------

import uuid
import psycopg
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
me = w.current_user.me().user_name
host = w.database.get_database_instance(name=INSTANCE).read_write_dns
token = w.database.generate_database_credential(
    request_id=str(uuid.uuid4()), instance_names=[INSTANCE]
).token

conn = psycopg.connect(
    host=host, port=5432, dbname=DB_NAME, user=me, password=token, sslmode="require"
)
print(f"connected to {host}/{DB_NAME} as {me}")

# COMMAND ----------

# MAGIC %md ## Ensure gold targets exist

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

spark.sql(f"""
  CREATE TABLE IF NOT EXISTS {GOLD}.customer_segment_overrides (
    customer_id      STRING,
    override_segment STRING,
    reason           STRING,
    author_email     STRING,
    created_at       TIMESTAMP
  ) USING DELTA
""")

# COMMAND ----------

# MAGIC %md ## Promote one staging table → gold (read → MERGE → mark processed)

# COMMAND ----------

from pyspark.sql import Row


def promote(staging_table: str, gold_table: str, pk: str, id_col: str, cols: list[str]):
    """Read processed=false rows, MERGE into gold on `pk`, mark them processed.

    `id_col` is the staging PK used in the WHERE ... IN (...) update; `pk` is the
    business key the gold MERGE matches on (same value for notes; customer_id for
    the idempotent segment overrides).
    """
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT {', '.join(cols)}, {id_col}::text AS _sid "
            f"FROM {staging_table} WHERE processed = false"
        )
        rows = cur.fetchall()
        colnames = [d.name for d in cur.description]

    if not rows:
        print(f"{staging_table}: no unprocessed rows — no-op")
        return 0

    sids = [r[colnames.index("_sid")] for r in rows]
    df = spark.createDataFrame([Row(**dict(zip(colnames, r))) for r in rows]).drop("_sid")
    df.createOrReplaceTempView("staged")

    set_clause = ", ".join(f"t.{c} = s.{c}" for c in cols)
    insert_cols = ", ".join(cols)
    insert_vals = ", ".join(f"s.{c}" for c in cols)
    spark.sql(f"""
      MERGE INTO {gold_table} t
      USING staged s ON t.{pk} = s.{pk}
      WHEN MATCHED THEN UPDATE SET {set_clause}
      WHEN NOT MATCHED THEN INSERT ({insert_cols}) VALUES ({insert_vals})
    """)

    # Mark processed in the SAME transaction as the read's logical unit.
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE {staging_table} SET processed = true, processed_at = NOW() "
            f"WHERE {id_col}::text = ANY(%s)",
            (sids,),
        )
    conn.commit()
    print(f"{staging_table}: promoted {len(rows)} rows → {gold_table}")
    return len(rows)


n_notes = promote(
    "customer_notes_staging", f"{GOLD}.customer_notes",
    pk="note_id", id_col="note_id",
    cols=["note_id", "customer_id", "author_email", "note_text", "created_at"],
)
n_over = promote(
    "customer_segment_overrides_staging", f"{GOLD}.customer_segment_overrides",
    pk="customer_id", id_col="override_id",
    cols=["customer_id", "override_segment", "reason", "author_email", "created_at"],
)

# COMMAND ----------

notes_total = spark.table(f"{GOLD}.customer_notes").count()
over_total = spark.table(f"{GOLD}.customer_segment_overrides").count()
conn.close()
msg = (
    f"OK: promoted {n_notes} notes + {n_over} overrides. "
    f"gold.customer_notes={notes_total}, gold.customer_segment_overrides={over_total}"
)
print(msg)
dbutils.notebook.exit(msg)
