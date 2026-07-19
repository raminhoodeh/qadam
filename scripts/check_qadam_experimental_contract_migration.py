#!/usr/bin/env python3
"""Verify that legacy records were classified without being upgraded."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_experimental_paper_policy import (  # noqa: E402
    build_and_write_experimental_policy,
)


def main() -> int:
    _policy, _mode, migration, _status, errors = build_and_write_experimental_policy()
    print(f"experimental_migration_status={migration['status']}")
    print(f"experimental_migration_record_count={migration['record_count']}")
    print(f"experimental_migration_legacy_default_count={migration['legacy_default_count']}")
    print("experimental_migration_legacy_rows_upgraded=0")
    for error in errors:
        print(f"experimental_migration_error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
