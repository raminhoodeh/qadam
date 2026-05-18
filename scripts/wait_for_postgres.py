#!/usr/bin/env python3
"""Wait for local Postgres/Timescale to accept connections."""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.postgres_store import connect  # noqa: E402


async def _probe(settings: Settings) -> bool:
    try:
        conn = await connect(settings)
    except Exception:
        return False
    try:
        await conn.execute("SELECT 1")
        return True
    finally:
        await conn.close()


async def main() -> int:
    parser = argparse.ArgumentParser(description="Wait for Qadam's local Postgres service.")
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()

    settings = Settings.from_env()
    deadline = time.monotonic() + args.timeout
    attempts = 0
    while True:
        attempts += 1
        if await _probe(settings):
            print("postgres_wait_status=ok")
            print(f"postgres_wait_attempts={attempts}")
            print("postgres_wait_boundary=Connection check only; no schema changes or ingestion writes.")
            return 0
        if time.monotonic() >= deadline:
            print("postgres_wait_status=timeout")
            print(f"postgres_wait_attempts={attempts}")
            print("postgres_wait_boundary=Postgres did not become reachable; no ingestion writes were attempted.")
            return 1
        await asyncio.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
