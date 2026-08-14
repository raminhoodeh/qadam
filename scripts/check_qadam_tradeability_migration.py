#!/usr/bin/env python3
"""Verify one canonical producer and no active legacy downstream readers."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_tradeability_audits import build_and_write_migration_audit


def main() -> int:
    migration, checks, errors = build_and_write_migration_audit()
    print(f"status={checks.get('status')}")
    print(
        "active_canonical_producer_count="
        f"{migration.get('active_canonical_producer_count')}"
    )
    print(f"legacy_active_consumer_count={checks.get('legacy_active_consumer_count')}")
    for error in errors:
        print(f"error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
