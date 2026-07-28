"""Shared M2M helper (T3a).

Runs the SDK's OAuth ``client_credentials`` (M2M) flow for a service principal
and returns the resulting OAuth **access token** — this is what goes in the
``Authorization: Bearer`` header sent to the Apps proxy. You cannot use the
SP's ``client_secret`` directly as the bearer.

Env:
    DATABRICKS_HOST           workspace URL, e.g. https://xxx.cloud.databricks.com
    DATABRICKS_CLIENT_ID      SP application/client id
    DATABRICKS_CLIENT_SECRET  SP OAuth secret (from service-principal-secrets create)
"""
from __future__ import annotations

import os


def get_bearer() -> str:
    """Return an OAuth access token for the configured SP via client_credentials."""
    host = os.environ["DATABRICKS_HOST"].rstrip("/")
    client_id = os.environ["DATABRICKS_CLIENT_ID"]
    client_secret = os.environ["DATABRICKS_CLIENT_SECRET"]

    from databricks.sdk.core import Config, oauth_service_principal

    cfg = Config(host=host, client_id=client_id, client_secret=client_secret)
    provider = oauth_service_principal(cfg)
    return provider().token().access_token


if __name__ == "__main__":
    print(get_bearer()[:24] + "…")
