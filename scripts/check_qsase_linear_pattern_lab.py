#!/usr/bin/env python3
"""Validate and write QSASE-5 linear pattern recognition lab artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_linear_pattern_lab import (
    BACKTEST_RESULTS_ARTIFACT,
    DASHBOARD_SUMMARY_ARTIFACT,
    EVENTS_ARTIFACT,
    HISTORY_ARTIFACT,
    PRIMARY_ARTIFACT,
    REJECTED_PATTERNS_ARTIFACT,
    _read_jsonl,
    _runtime_dir,
    build_and_write_linear_pattern_results,
    load_linear_pattern_results,
    validate_linear_pattern_results,
    validate_negative_linear_pattern_probes,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    settings = Settings.from_env()
    payload, written, errors = build_and_write_linear_pattern_results(settings)
    runtime_dir = _runtime_dir(settings)

    validation_errors = list(errors)
    for filename in (
        PRIMARY_ARTIFACT,
        BACKTEST_RESULTS_ARTIFACT,
        REJECTED_PATTERNS_ARTIFACT,
        EVENTS_ARTIFACT,
        HISTORY_ARTIFACT,
        DASHBOARD_SUMMARY_ARTIFACT,
    ):
        path = runtime_dir / filename
        if not path.exists():
            validation_errors.append(f"{filename}_missing")

    primary = _load_json(runtime_dir / PRIMARY_ARTIFACT)
    linear_results = _read_jsonl(runtime_dir / BACKTEST_RESULTS_ARTIFACT)
    rejected = _read_jsonl(runtime_dir / REJECTED_PATTERNS_ARTIFACT)
    loaded = load_linear_pattern_results(settings)
    if primary.get("generated_at") != payload.get("generated_at"):
        validation_errors.append("written_primary_generated_at_mismatch")
    if len(linear_results) != payload.get("tested_relationship_count"):
        validation_errors.append("written_linear_result_count_mismatch")
    if len(rejected) != payload.get("rejected_linear_pattern_count"):
        validation_errors.append("written_rejected_linear_pattern_count_mismatch")
    validation_errors.extend(validate_linear_pattern_results(loaded))
    validation_errors.extend(validate_negative_linear_pattern_probes())

    print(f"artifact={written.get('linear_pattern_lab')}")
    print(f"linear_results={written.get('linear_results')}")
    print(f"linear_rejected_patterns={written.get('linear_rejected_patterns')}")
    print(f"dashboard_summary={written.get('dashboard_summary')}")
    print(f"phase_status={written.get('phase_status')}")
    print(f"implementation_log={written.get('implementation_log')}")
    print(f"status={payload.get('status')}")
    print(f"tested_relationship_count={payload.get('tested_relationship_count')}")
    print(f"accepted_linear_pattern_count={payload.get('accepted_linear_pattern_count')}")
    print(f"inconclusive_linear_pattern_count={payload.get('inconclusive_linear_pattern_count')}")
    print(f"rejected_linear_pattern_count={payload.get('rejected_linear_pattern_count')}")
    print(f"candidate_for_nonlinear_review_count={payload.get('candidate_for_nonlinear_review_count')}")
    print(f"candidate_for_strategy_foundry_count={payload.get('candidate_for_strategy_foundry_count')}")
    print(f"leakage_rejected_count={payload.get('leakage_rejected_count')}")
    print(f"coverage_blocked_count={payload.get('coverage_blocked_count')}")
    print(f"linear_success_is_research_evidence_only={payload.get('linear_success_is_research_evidence_only')}")
    print(f"no_trade_candidates_created={payload.get('no_trade_candidates_created')}")
    if validation_errors:
        for error in validation_errors:
            print(f"error={error}")
        return 1
    print("qsase_linear_pattern_lab_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
