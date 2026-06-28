#!/usr/bin/env python3
"""Validate and write QSASE-6 nonlinear and quantum pattern lab artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_nonlinear_quantum_pattern_lab import (
    DASHBOARD_SUMMARY_ARTIFACT,
    EVENTS_ARTIFACT,
    HISTORY_ARTIFACT,
    NONLINEAR_RESULTS_ARTIFACT,
    PRIMARY_ARTIFACT,
    QUANTUM_REVIEWS_ARTIFACT,
    _read_jsonl,
    _runtime_dir,
    build_and_write_nonlinear_quantum_pattern_lab,
    load_nonlinear_quantum_pattern_lab,
    validate_negative_nonlinear_quantum_probes,
    validate_nonlinear_pattern_results,
    validate_quantum_pattern_reviews,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    settings = Settings.from_env()
    payload, written, errors = build_and_write_nonlinear_quantum_pattern_lab(settings)
    runtime_dir = _runtime_dir(settings)

    validation_errors = list(errors)
    for filename in (
        PRIMARY_ARTIFACT,
        NONLINEAR_RESULTS_ARTIFACT,
        QUANTUM_REVIEWS_ARTIFACT,
        EVENTS_ARTIFACT,
        HISTORY_ARTIFACT,
        DASHBOARD_SUMMARY_ARTIFACT,
    ):
        path = runtime_dir / filename
        if not path.exists():
            validation_errors.append(f"{filename}_missing")

    primary = _load_json(runtime_dir / PRIMARY_ARTIFACT)
    nonlinear_results = _read_jsonl(runtime_dir / NONLINEAR_RESULTS_ARTIFACT)
    quantum_reviews = _read_jsonl(runtime_dir / QUANTUM_REVIEWS_ARTIFACT)
    loaded = load_nonlinear_quantum_pattern_lab(settings)
    if primary.get("generated_at") != payload.get("generated_at"):
        validation_errors.append("written_primary_generated_at_mismatch")
    if len(nonlinear_results) != payload.get("tested_interaction_count"):
        validation_errors.append("written_nonlinear_result_count_mismatch")
    if len(quantum_reviews) != payload.get("reviewed_pattern_count"):
        validation_errors.append("written_quantum_review_count_mismatch")
    validation_errors.extend(validate_nonlinear_pattern_results(loaded))
    validation_errors.extend(validate_quantum_pattern_reviews(loaded))
    validation_errors.extend(validate_negative_nonlinear_quantum_probes())

    print(f"artifact={written.get('nonlinear_quantum_lab')}")
    print(f"nonlinear_results={written.get('nonlinear_results')}")
    print(f"quantum_reviews={written.get('quantum_reviews')}")
    print(f"dashboard_summary={written.get('dashboard_summary')}")
    print(f"phase_status={written.get('phase_status')}")
    print(f"implementation_log={written.get('implementation_log')}")
    print(f"status={payload.get('status')}")
    print(f"candidate_input_count={payload.get('candidate_input_count')}")
    print(f"tested_interaction_count={payload.get('tested_interaction_count')}")
    print(f"accepted_nonlinear_pattern_count={payload.get('accepted_nonlinear_pattern_count')}")
    print(f"rejected_nonlinear_pattern_count={payload.get('rejected_nonlinear_pattern_count')}")
    print(f"inconclusive_nonlinear_pattern_count={payload.get('inconclusive_nonlinear_pattern_count')}")
    print(f"linear_baseline_beat_count={payload.get('linear_baseline_beat_count')}")
    print(f"candidate_for_quantum_review_count={payload.get('candidate_for_quantum_review_count')}")
    print(f"reviewed_pattern_count={payload.get('reviewed_pattern_count')}")
    print(f"quantum_hold_count={payload.get('quantum_hold_count')}")
    print(f"quantum_useful_information_count={payload.get('quantum_useful_information_count')}")
    print(f"quantum_backend={payload.get('quantum_summary', {}).get('quantum_backend')}")
    print(f"quantum_mode={payload.get('quantum_summary', {}).get('quantum_mode')}")
    print(f"candidate_for_strategy_foundry_count={payload.get('candidate_for_strategy_foundry_count')}")
    print(f"quantum_review_is_not_trade_approval={payload.get('quantum_review_is_not_trade_approval')}")
    print(f"no_trade_candidates_created={payload.get('no_trade_candidates_created')}")
    if validation_errors:
        for error in validation_errors:
            print(f"error={error}")
        return 1
    print("qsase_nonlinear_quantum_pattern_lab_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
