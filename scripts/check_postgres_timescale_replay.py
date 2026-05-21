#!/usr/bin/env python3
"""Verify replay coverage from durable Postgres/Timescale observations.

Default mode is a read-only readiness check and may pass while the local
Postgres/Timescale service is offline. Use --require-full-source-coverage when
the durable service is expected to be live and all canonical sources must be
replayable.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.local_store import local_store_health  # noqa: E402
from orchestrator.postgres_store import connect, schema_state  # noqa: E402
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT, SOURCE_SPECS  # noqa: E402


async def main() -> int:
    parser = argparse.ArgumentParser(description="Check durable source observation replay coverage.")
    parser.add_argument("--require-full-source-coverage", action="store_true")
    args = parser.parse_args()

    settings = Settings.from_env()
    expected_source_keys = {source.key for source in SOURCE_SPECS}
    stores = local_store_health(settings)
    if "postgres" in stores["summary"]["offline_services"]:
        print("postgres_replay_status=offline")
        print("postgres_replay_missing_service=postgres")
        print("postgres_replay_contract_status=ready_waiting_for_local_service")
        print("postgres_replay_boundary=Read-only replay check. No ingestion writes or trading actions.")
        if args.require_full_source_coverage:
            print("postgres_replay_full_source_coverage_required=true")
            return 1
        print("postgres_replay_check=ok")
        return 0

    try:
        state = await schema_state(settings)
    except Exception as exc:  # noqa: BLE001 - status script must report the database failure.
        print("postgres_replay_status=unavailable")
        print(f"postgres_replay_error={exc.__class__.__name__}")
        print("postgres_replay_contract_status=schema_unavailable")
        print("postgres_replay_boundary=Read-only replay check. No ingestion writes or trading actions.")
        if args.require_full_source_coverage:
            print("postgres_replay_full_source_coverage_required=true")
            return 1
        print("postgres_replay_check=ok")
        return 0

    missing_tables = set(state["missing_tables"])
    print(f"postgres_replay_schema_status={state['status']}")
    print(f"postgres_replay_missing_tables={sorted(missing_tables)}")
    if missing_tables:
        print("postgres_replay_status=missing_tables")
        print("postgres_replay_contract_status=schema_incomplete")
        if args.require_full_source_coverage:
            print("postgres_replay_full_source_coverage_required=true")
            return 1
        print("postgres_replay_check=ok")
        return 0

    conn = await connect(settings)
    try:
        summary = await conn.fetchrow(
            """
            SELECT
                COUNT(*)::int AS observation_count,
                COUNT(DISTINCT source_key)::int AS distinct_source_count,
                MIN(observed_at) AS first_observed_at,
                MAX(observed_at) AS latest_observed_at
            FROM source_observation
            """
        )
        event_log_count = await conn.fetchval(
            """
            SELECT COUNT(*)::int
            FROM event_log
            WHERE event_type = 'source_test_observation_recorded'
            """
        )
        rows = await conn.fetch(
            """
            SELECT source_key, COUNT(*)::int AS observation_count, MAX(observed_at) AS latest_observed_at
            FROM source_observation
            GROUP BY source_key
            ORDER BY source_key
            """
        )
    finally:
        await conn.close()

    observed_source_keys = {row["source_key"] for row in rows}
    missing_source_keys = sorted(expected_source_keys - observed_source_keys)

    print("postgres_replay_status=ok" if not missing_source_keys else "postgres_replay_status=partial")
    print(
        "postgres_replay_contract_status="
        + ("durable_replay_ready" if not missing_source_keys else "durable_replay_partial")
    )
    print(f"postgres_replay_observation_count={summary['observation_count']}")
    print(f"postgres_replay_distinct_source_count={summary['distinct_source_count']}")
    print(f"postgres_replay_expected_source_count={EXPECTED_SOURCE_COUNT}")
    print(f"postgres_replay_event_log_ingestion_event_count={event_log_count}")
    print(f"postgres_replay_first_observed_at={summary['first_observed_at']}")
    print(f"postgres_replay_latest_observed_at={summary['latest_observed_at']}")
    print(f"postgres_replay_missing_source_count={len(missing_source_keys)}")
    if missing_source_keys:
        print("postgres_replay_missing_sources=" + ",".join(missing_source_keys))
    print("postgres_replay_boundary=Read-only replay check. Durable observations cannot create signals or orders.")

    if args.require_full_source_coverage and missing_source_keys:
        print("postgres_replay_full_source_coverage_required=true")
        return 1
    print("postgres_replay_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
