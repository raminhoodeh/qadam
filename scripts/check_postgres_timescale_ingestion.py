#!/usr/bin/env python3
"""Check Postgres/Timescale durable ingestion contract.

Default mode is non-destructive and passes when the contract exists but the
local database is offline. Use --require-live when Postgres/Timescale is
running and the check should fail if durable ingestion is unavailable.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.ingestion import build_test_observation, selected_sources
from orchestrator.local_store import local_store_health
from orchestrator.postgres_store import schema_state, write_source_observations


async def main() -> int:
    require_live = "--require-live" in sys.argv
    settings = Settings.from_env()
    stores = local_store_health(settings)
    postgres_online = "postgres" not in stores["summary"]["offline_services"]
    print(f"postgres_timescale_status={'online' if postgres_online else 'offline'}")
    print(f"postgres_timescale_require_live={require_live}")
    print(f"postgres_timescale_database_url_configured={bool(settings.database_url)}")
    print("postgres_timescale_boundary=Durable ingestion writes local Postgres/Timescale observations only; it cannot create signals or orders.")

    if not postgres_online:
        print("postgres_timescale_contract_status=ready_waiting_for_local_service")
        if require_live:
            print("postgres_timescale_service_required_but_offline=true")
            return 1
        print("postgres_timescale_ingestion_check=ok")
        return 0

    try:
        state = await schema_state(settings)
    except Exception as exc:  # noqa: BLE001 - check reports database details
        print("postgres_timescale_schema_status=unavailable")
        print(f"postgres_timescale_schema_error={exc}")
        return 1 if require_live else 0

    print(f"postgres_timescale_schema_status={state['status']}")
    print(f"postgres_timescale_missing_tables={state['missing_tables']}")
    if state["missing_tables"]:
        return 1 if require_live else 0

    observations = [build_test_observation(source) for source in selected_sources(limit=5)]
    counts = await write_source_observations(observations, settings)
    print(f"postgres_timescale_source_observation_inserted={counts['source_observation']}")
    print(f"postgres_timescale_event_log_inserted={counts['event_log']}")
    print("postgres_timescale_ingestion_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
