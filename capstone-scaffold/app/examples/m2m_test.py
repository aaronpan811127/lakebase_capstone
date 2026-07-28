"""M2M happy-path test (T3a).

Simulates a partner system: obtains an OAuth bearer for the SP via
client_credentials, then calls the deployed app's external endpoint. The Apps
proxy validates the bearer and forwards ``X-Forwarded-Access-Token`` to the
handler, which reads gold via the SQL warehouse as the SP (never Lakebase,
never the app SP fallback).

Expects HTTP 200 + the customer JSON. Capture stdout for the writeup.

Env:
    DATABRICKS_HOST, DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET (see _token.py)
    APP_URL       deployed app base URL, e.g. https://customer360-xxx.databricksapps.com
    CUSTOMER_ID   optional (default C0003600)
"""
from __future__ import annotations

import json
import os
import sys

import httpx

from _token import get_bearer


def main() -> int:
    app_url = os.environ["APP_URL"].rstrip("/")
    customer_id = os.environ.get("CUSTOMER_ID", "C0003600")

    print(f"→ minting OAuth bearer via client_credentials for SP {os.environ['DATABRICKS_CLIENT_ID']}")
    bearer = get_bearer()
    print(f"  bearer acquired: {bearer[:16]}… ({len(bearer)} chars)")

    url = f"{app_url}/api/external/customers/{customer_id}"
    print(f"→ GET {url}")
    resp = httpx.get(url, headers={"Authorization": f"Bearer {bearer}"}, timeout=60)

    print(f"← HTTP {resp.status_code}")
    if resp.status_code != 200:
        print(resp.text)
        print("FAIL: expected 200")
        return 1

    body = resp.json()
    print(json.dumps(body, indent=2)[:1200])
    assert body.get("customer_id") == customer_id, "customer_id mismatch"
    assert "recent_transactions" in body, "missing recent_transactions"
    print(f"\nPASS: 200 + customer JSON ({len(body['recent_transactions'])} recent transactions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
