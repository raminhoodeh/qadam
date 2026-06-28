#!/usr/bin/env python3
"""Validate and write QSASE-4 full-universe pattern search artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_full_universe_pattern_search import (
    CANDIDATE_PATTERNS_ARTIFACT,
    DASHBOARD_SUMMARY_ARTIFACT,
    EVENTS_ARTIFACT,
    HISTORY_ARTIFACT,
    PRIMARY_ARTIFACT,
    REJECTED_PATTERNS_ARTIFACT,
    _read_jsonl,
    _runtime_dir,
    build_and_write_full_universe_pattern_search,
    load_full_universe_pattern_search,
    validate_full_universe_pattern_search,
    validate_negative_pattern_search_probes,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    settings = Settings.from_env()
    payload, written, errors = build_and_write_full_universe_pattern_search(settings)
    runtime_dir = _runtime_dir(settings)

    validation_errors = list(errors)
    for filename in (
        PRIMARY_ARTIFACT,
        CANDIDATE_PATTERNS_ARTIFACT,
        REJECTED_PATTERNS_ARTIFACT,
        EVENTS_ARTIFACT,
        HISTORY_ARTIFACT,
        DASHBOARD_SUMMARY_ARTIFACT,
    ):
        path = runtime_dir / filename
        if not path.exists():
            validation_errors.append(f"{filename}_missing")

    primary = _load_json(runtime_dir / PRIMARY_ARTIFACT)
    candidates = _read_jsonl(runtime_dir / CANDIDATE_PATTERNS_ARTIFACT)
    rejected = _read_jsonl(runtime_dir / REJECTED_PATTERNS_ARTIFACT)
    loaded = load_full_universe_pattern_search(settings)
    if primary.get("generated_at") != payload.get("generated_at"):
        validation_errors.append("written_primary_generated_at_mismatch")
    if len(candidates) != payload.get("candidate_pattern_count"):
        validation_errors.append("written_candidate_pattern_count_mismatch")
    if len(rejected) != payload.get("rejected_pattern_count"):
        validation_errors.append("written_rejected_pattern_count_mismatch")
    validation_errors.extend(validate_full_universe_pattern_search(loaded))
    validation_errors.extend(validate_negative_pattern_search_probes())

    print(f"artifact={written.get('pattern_search')}")
    print(f"candidate_patterns={written.get('candidate_patterns')}")
    print(f"rejected_patterns={written.get('rejected_patterns')}")
    print(f"dashboard_summary={written.get('dashboard_summary')}")
    print(f"phase_status={written.get('phase_status')}")
    print(f"implementation_log={written.get('implementation_log')}")
    print(f"status={payload.get('status')}")
    print(f"matrix_row_count={payload.get('matrix_row_count')}")
    print(f"complete_relationship_count={payload.get('complete_relationship_count')}")
    print(f"candidate_pattern_count={payload.get('candidate_pattern_count')}")
    print(f"rejected_pattern_count={payload.get('rejected_pattern_count')}")
    print(f"new_strategy_candidate_count={payload.get('new_strategy_candidate_count')}")
    print(f"strategy_label_count={payload.get('strategy_label_count')}")
    print(f"patterns_are_not_strategies={payload.get('patterns_are_not_strategies')}")
    print(f"no_trade_candidates_created={payload.get('no_trade_candidates_created')}")
    if validation_errors:
        for error in validation_errors:
            print(f"error={error}")
        return 1
    print("qsase_full_universe_pattern_search_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
