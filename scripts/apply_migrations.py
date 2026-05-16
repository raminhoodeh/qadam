#!/usr/bin/env python3
"""Apply SQL migrations to the local Qadam database."""

from __future__ import annotations

import asyncio
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings

MIGRATIONS_DIR = ROOT / "migrations"


def migration_files() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def checksum_sql(sql: str) -> str:
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()


async def apply() -> int:
    try:
        import asyncpg
    except ImportError:
        print("asyncpg_missing=true")
        print("Install project dependencies before applying database migrations.")
        return 1

    settings = Settings.from_env()
    files = migration_files()
    if not files:
        print("migration_count=0")
        return 1

    conn = await asyncpg.connect(settings.database_url)
    try:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                checksum TEXT NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        applied = 0
        skipped = 0
        for path in files:
            version = path.name
            sql = path.read_text(encoding="utf-8")
            checksum = checksum_sql(sql)
            existing = await conn.fetchrow(
                "SELECT checksum FROM schema_migrations WHERE version = $1",
                version,
            )
            if existing:
                if existing["checksum"] != checksum:
                    raise RuntimeError(f"migration checksum changed after apply: {version}")
                skipped += 1
                continue

            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO schema_migrations (version, checksum) VALUES ($1, $2)",
                    version,
                    checksum,
                )
            applied += 1

        print(f"migration_count={len(files)}")
        print(f"migrations_applied={applied}")
        print(f"migrations_skipped={skipped}")
        print("migration_check=ok")
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(apply()))
