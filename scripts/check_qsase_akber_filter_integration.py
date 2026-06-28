#!/usr/bin/env python3
"""Validate and write QSASE-8 Akber Filter Integration artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_akber_filter_integration import (
    ABLATION_ARTIFACT,
    DASHBOARD_SUMMARY_ARTIFACT,
    EVENTS_ARTIFACT,
    HISTORY_ARTIFACT,
    PRIMARY_ARTIFACT,
    RESULTS_ARTIFACT,
    THRESHOLD_PROPOSALS_ARTIFACT,
    _read_jsonl,
    _runtime_dir,
    build_and_write_akber_filter_results,
    load_akber_filter_results,
    validate_akber_filter_results,
    validate_negative_akber_filter_probes,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    settings = Settings.from_env()
    payload, written, errors = build_and_write_akber_filter_results(settings)
    runtime_dir = _runtime_dir(settings)

    validation_errors = list(errors)
    for filename in (
        PRIMARY_ARTIFACT,
        RESULTS_ARTIFACT,
        THRESHOLD_PROPOSALS_ARTIFACT,
        ABLATION_ARTIFACT,
        EVENTS_ARTIFACT,
        HISTORY_ARTIFACT,
        DASHBOARD_SUMMARY_ARTIFACT,
    ):
        path = runtime_dir / filename
        if not path.exists():
            validation_errors.append(f"{filename}_missing")

    primary = _load_json(runtime_dir / PRIMARY_ARTIFACT)
    results = _read_jsonl(runtime_dir / RESULTS_ARTIFACT)
    threshold_proposals = _load_json(runtime_dir / THRESHOLD_PROPOSALS_ARTIFACT)
    ablation = _load_json(runtime_dir / ABLATION_ARTIFACT)
    loaded = load_akber_filter_results(settings)
    if primary.get("generated_at") != payload.get("generated_at"):
        validation_errors.append("written_primary_generated_at_mismatch")
    if len(results) != payload.get("input_filter_record_count"):
        validation_errors.append("written_filter_result_count_mismatch")
    if threshold_proposals.get("threshold_change_applied") is not False:
        validation_errors.append("written_threshold_proposal_applied")
    if ablation.get("historical_filter_replay_exists") is not True:
        validation_errors.append("written_ablation_missing_historical_replay")
    validation_errors.extend(validate_akber_filter_results(loaded))
    validation_errors.extend(validate_negative_akber_filter_probes())

    print(f"artifact={written.get('akber_filter_integration')}")
    print(f"akber_filter_results={written.get('akber_filter_results')}")
    print(f"threshold_proposals={written.get('threshold_proposals')}")
    print(f"ablation={written.get('ablation')}")
    print(f"dashboard_summary={written.get('dashboard_summary')}")
    print(f"phase_status={written.get('phase_status')}")
    print(f"implementation_log={written.get('implementation_log')}")
    print(f"status={payload.get('status')}")
    print(f"input_hypothesis_count={payload.get('input_hypothesis_count')}")
    print(f"input_rejected_hypothesis_count={payload.get('input_rejected_hypothesis_count')}")
    print(f"input_filter_record_count={payload.get('input_filter_record_count')}")
    print(f"passed_filter_count={payload.get('passed_filter_count')}")
    print(f"hold_filter_count={payload.get('hold_filter_count')}")
    print(f"rejected_filter_count={payload.get('rejected_filter_count')}")
    print(f"audit_only_filter_count={payload.get('audit_only_filter_count')}")
    print(f"missing_context_count={payload.get('missing_context_count')}")
    print(f"ablation_ready_count={payload.get('ablation_ready_count')}")
    print(f"historical_improvement_observed={payload.get('historical_improvement_observed')}")
    print(f"candidate_for_shadow_replay_count={payload.get('candidate_for_shadow_replay_count')}")
    print(f"candidate_for_router_count={payload.get('candidate_for_router_count')}")
    print(f"akber_filter_pass_is_not_execution_approval={payload.get('akber_filter_pass_is_not_execution_approval')}")
    print(f"trade_candidate_created={payload.get('trade_candidate_created')}")
    print(f"paper_order_allowed={payload.get('paper_order_allowed')}")
    if validation_errors:
        for error in validation_errors:
            print(f"error={error}")
        return 1
    print("qsase_akber_filter_integration_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
