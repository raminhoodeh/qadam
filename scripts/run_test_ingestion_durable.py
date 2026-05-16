#!/usr/bin/env python3
"""Write deterministic test ingestion observations into Postgres/Timescale."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.ingestion import build_test_observation, selected_sources
from orchestrator.postgres_store import write_source_observations
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT


def _arg_value(prefix: str) -> str | None:
    for arg in sys.argv:
        if arg.startswith(prefix):
            return arg.split("=", 1)[1]
    return None


async def main() -> int:
    limit_arg = _arg_value("--limit=")
    tier_arg = _arg_value("--tier=")
    pipeline = _arg_value("--pipeline=")
    limit = None if "--all" in sys.argv else int(limit_arg or "5")
    tier = int(tier_arg) if tier_arg else None

    observations = [
        build_test_observation(source)
        for source in selected_sources(limit=limit, tier=tier, pipeline=pipeline)
    ]

    try:
        counts = await write_source_observations(observations, Settings.from_env())
    except Exception as exc:  # noqa: BLE001 - CLI should explain dependency or connection failures
        print("durable_test_ingestion_status=failed")
        print(f"durable_test_ingestion_error={exc}")
        return 1

    print("durable_test_ingestion_status=ok")
    print(f"durable_test_ingestion_selected_count={len(observations)}")
    print(f"durable_test_ingestion_expected_source_count={EXPECTED_SOURCE_COUNT}")
    for table, count in sorted(counts.items()):
        print(f"{table}_inserted={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
