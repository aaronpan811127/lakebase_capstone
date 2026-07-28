"""Application settings, read from environment (`.env` locally; real env in Apps)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Databricks / workspace
    databricks_host: str = ""
    databricks_profile: str = ""

    # Gold data
    capstone_catalog: str = "lakebase_capstone_catalog"
    capstone_schema: str = "gold"
    warehouse_id: str = ""

    # Lakebase (Postgres)
    pghost: str = ""
    pgdatabase: str = "capstone_db"
    pg_instance_name: str = "capstone-pg"
    pg_uc_catalog: str = "capstone_lb_ap"
    secret_scope: str = ""

    # BI / Genie
    dashboard_id: str = ""
    genie_space_id: str = ""

    # Forward-ETL job (bound via app.yaml valueFrom in prod)
    forward_etl_job_id: str = ""

    # Misc
    parent_path: str = "/Workspace/Shared/capstone"

    @property
    def gold(self) -> str:
        """Fully-qualified gold schema, e.g. `catalog.gold`."""
        return f"{self.capstone_catalog}.{self.capstone_schema}"


settings = Settings()
