#!/usr/bin/env python3
"""Validate and write QSASE-9 Shadow Strategy Simulator artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_shadow_strategy_simulator import (
    ACTUAL_VS_HYPOTHETICAL_ARTIFACT,
    DASHBOARD_SUMMARY_ARTIFACT,
    EVENTS_ARTIFACT,
    HISTORY_ARTIFACT,
    PRIMARY_ARTIFACT,
    REJECTIONS_ARTIFACT,
    RESULTS_ARTIFACT,
    VARIANT_MATRIX_ARTIFACT,
    _read_jsonl,
    _runtime_dir,
    build_and_write_shadow_strategy_replay,
    load_shadow_strategy_replay,
    validate_negative_shadow_strategy_probes,
    validate_shadow_strategy_replay,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    settings = Settings.from_env()
    payload, written, errors = build_and_write_shadow_strategy_replay(settings)
    runtime_dir = _runtime_dir(settings)

    validation_errors = list(errors)
    for filename in (
        PRIMARY_ARTIFACT,
        RESULTS_ARTIFACT,
        REJECTIONS_ARTIFACT,
        VARIANT_MATRIX_ARTIFACT,
        ACTUAL_VS_HYPOTHETICAL_ARTIFACT,
        EVENTS_ARTIFACT,
        HISTORY_ARTIFACT,
        DASHBOARD_SUMMARY_ARTIFACT,
    ):
        path = runtime_dir / filename
        if not path.exists():
            validation_errors.append(f"{filename}_missing")

    primary = _load_json(runtime_dir / PRIMARY_ARTIFACT)
    results = _read_jsonl(runtime_dir / RESULTS_ARTIFACT)
    rejections = _read_jsonl(runtime_dir / REJECTIONS_ARTIFACT)
    variant_matrix = _load_json(runtime_dir / VARIANT_MATRIX_ARTIFACT)
    comparison = _load_json(runtime_dir / ACTUAL_VS_HYPOTHETICAL_ARTIFACT)
    loaded = load_shadow_strategy_replay(settings)

    if primary.get("generated_at") != payload.get("generated_at"):
        validation_errors.append("written_primary_generated_at_mismatch")
    if len(results) != payload.get("replay_record_count"):
        validation_errors.append("written_shadow_result_count_mismatch")
    if len(rejections) != payload.get("rejected_variant_count"):
        validation_errors.append("written_shadow_rejection_count_mismatch")
    if variant_matrix.get("variant_count") != payload.get("variant_count"):
        validation_errors.append("written_variant_matrix_count_mismatch")
    if comparison.get("actual_vs_hypothetical_count") != payload.get("actual_vs_hypothetical_count"):
        validation_errors.append("written_actual_vs_hypothetical_count_mismatch")
    validation_errors.extend(validate_shadow_strategy_replay(loaded))
    validation_errors.extend(validate_negative_shadow_strategy_probes())

    print(f"artifact={written.get('shadow_strategy_simulator')}")
    print(f"shadow_strategy_results={written.get('shadow_strategy_results')}")
    print(f"shadow_strategy_rejections={written.get('shadow_strategy_rejections')}")
    print(f"variant_matrix={written.get('variant_matrix')}")
    print(f"actual_vs_hypothetical={written.get('actual_vs_hypothetical')}")
    print(f"dashboard_summary={written.get('dashboard_summary')}")
    print(f"phase_status={written.get('phase_status')}")
    print(f"implementation_log={written.get('implementation_log')}")
    print(f"status={payload.get('status')}")
    print(f"input_hypothesis_count={payload.get('input_hypothesis_count')}")
    print(f"input_rejected_hypothesis_count={payload.get('input_rejected_hypothesis_count')}")
    print(f"akber_filter_record_count={payload.get('akber_filter_record_count')}")
    print(f"variant_count={payload.get('variant_count')}")
    print(f"replay_record_count={payload.get('replay_record_count')}")
    print(f"active_replay_count={payload.get('active_replay_count')}")
    print(f"blocked_replay_count={payload.get('blocked_replay_count')}")
    print(f"evaluated_replay_count={payload.get('evaluated_replay_count')}")
    print(f"actual_vs_hypothetical_count={payload.get('actual_vs_hypothetical_count')}")
    print(f"candidate_for_router_count={payload.get('candidate_for_router_count')}")
    print(f"rejected_variant_count={payload.get('rejected_variant_count')}")
    print(f"blocked_reason={payload.get('blocked_reason')}")
    print(f"paper_order_created={payload.get('paper_order_created')}")
    print(f"proof_credit_allowed={payload.get('proof_credit_allowed')}")
    if validation_errors:
        for error in validation_errors:
            print(f"error={error}")
        return 1
    print("qsase_shadow_strategy_simulator_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
