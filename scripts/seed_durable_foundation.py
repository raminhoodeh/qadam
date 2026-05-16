#!/usr/bin/env python3
"""Seed durable Postgres tables from local registry modules."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.postgres_store import seed_reference_and_world_model


async def main() -> int:
    try:
        counts = await seed_reference_and_world_model(Settings.from_env())
    except Exception as exc:  # noqa: BLE001 - CLI should explain dependency or connection failures
        print("durable_seed_status=failed")
        print(f"durable_seed_error={exc}")
        return 1

    print("durable_seed_status=ok")
    for table, count in sorted(counts.items()):
        print(f"{table}_seeded={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
