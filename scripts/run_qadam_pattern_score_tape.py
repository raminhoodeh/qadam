#!/usr/bin/env python3
"""Refresh the resumable OR-6 score-tape manifest without fabricating rows."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_pattern_score_tape import build_and_write_pattern_score_tape  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.parse_args()
    _state, checks, errors = build_and_write_pattern_score_tape(Settings.from_env())
    print(f"status={checks['status']}")
    print(f"partition_count={checks['partition_count']}")
    print(f"score_tape_row_count={checks['score_tape_row_count']}")
    print(f"input_alignment_record_count={checks['input_alignment_record_count']}")
    print(f"input_alignment_coverage_ratio={checks['input_alignment_coverage_ratio']}")
    print(f"label_column_detected={checks['label_column_detected']}")
    print(f"future_horizon_metadata_accessed={checks['future_horizon_metadata_accessed']}")
    print(f"input_snapshot_id={checks.get('input_snapshot_id')}")
    print(f"input_snapshot_pinned={checks.get('input_snapshot_pinned', False)}")
    print(
        f"input_snapshot_template_verified={checks.get('input_snapshot_template_verified', False)}"
    )
    for error in errors:
        print(f"validation_error={error}")
    print(f"validation_error_count={len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
