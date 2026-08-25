#!/usr/bin/env python3
"""Build and validate the canonical pre-armed paper exit engine."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_canonical_exit_engine import (  # noqa: E402
    build_canonical_exit_engine,
    validate_canonical_exit_engine,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-due-exits", action="store_true")
    args = parser.parse_args()
    artifact = build_canonical_exit_engine(
        Settings.from_env(),
        execute_due_exits=args.execute_due_exits,
    )
    errors = validate_canonical_exit_engine(artifact)
    print(f"qadam_canonical_exit_status={artifact['status']}")
    print(f"qadam_canonical_exit_candidate_count={artifact['candidate_count']}")
    print(f"qadam_canonical_exit_close_requested_count={artifact['close_requested_count']}")
    print(f"qadam_canonical_exit_validation_error_count={len(errors)}")
    return 1 if errors or artifact.get("blockers") else 0


if __name__ == "__main__":
    raise SystemExit(main())
