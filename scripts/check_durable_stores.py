#!/usr/bin/env python3
"""Check Postgres schema readiness for Qadam durable mode."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.local_store import local_store_health
from orchestrator.postgres_store import schema_state


async def main() -> int:
    settings = Settings.from_env()
    stores = local_store_health(settings)
    print(f"local_store_status={stores['status']}")
    print(f"local_store_offline_services={stores['summary']['offline_services']}")

    try:
        state = await schema_state(settings)
    except Exception as exc:  # noqa: BLE001 - CLI should explain dependency or connection failures
        print(f"postgres_schema_status=unavailable")
        print(f"postgres_schema_error={exc}")
        return 1

    print(f"postgres_schema_status={state['status']}")
    print(f"postgres_tables={state['tables']}")
    print(f"postgres_missing_tables={state['missing_tables']}")
    print(f"postgres_migrations={state['migrations']}")

    if state["missing_tables"]:
        print("durable_store_missing_tables=true")
        return 1
    if "postgres" in stores["summary"]["offline_services"] or "chroma" in stores["summary"]["offline_services"]:
        print("durable_store_service_offline=true")
        return 1

    print("durable_store_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
