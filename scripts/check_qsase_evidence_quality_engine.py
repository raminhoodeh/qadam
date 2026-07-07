#!/usr/bin/env python3
"""Validate and write the QSASE evidence quality engine artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_evidence_quality_engine import (
    DASHBOARD_SUMMARY_ARTIFACT,
    EVENTS_ARTIFACT,
    HISTORY_ARTIFACT,
    PRIMARY_ARTIFACT,
    RECORDS_ARTIFACT,
    _read_jsonl,
    _runtime_dir,
    build_and_write_evidence_quality_engine,
    load_evidence_quality_engine,
    validate_evidence_quality_engine,
    validate_negative_evidence_quality_probes,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    settings = Settings.from_env()
    payload, written, errors = build_and_write_evidence_quality_engine(settings)
    runtime_dir = _runtime_dir(settings)
    validation_errors = list(errors)

    for filename in (
        PRIMARY_ARTIFACT,
        RECORDS_ARTIFACT,
        DASHBOARD_SUMMARY_ARTIFACT,
        HISTORY_ARTIFACT,
        EVENTS_ARTIFACT,
    ):
        if not (runtime_dir / filename).exists():
            validation_errors.append(f"{filename}_missing")

    primary = _load_json(runtime_dir / PRIMARY_ARTIFACT)
    records = _read_jsonl(runtime_dir / RECORDS_ARTIFACT)
    dashboard_summary = _load_json(runtime_dir / DASHBOARD_SUMMARY_ARTIFACT)
    loaded = load_evidence_quality_engine(settings)

    if primary.get("generated_at") != payload.get("generated_at"):
        validation_errors.append("written_primary_generated_at_mismatch")
    if len(records) != payload.get("evidence_record_count"):
        validation_errors.append("written_record_count_mismatch")
    if dashboard_summary.get("evidence_record_count") != payload.get("evidence_record_count"):
        validation_errors.append("written_dashboard_summary_count_mismatch")
    validation_errors.extend(validate_evidence_quality_engine(loaded))
    validation_errors.extend(validate_negative_evidence_quality_probes())

    print(f"artifact={written.get('primary')}")
    print(f"records={written.get('records')}")
    print(f"dashboard_summary={written.get('dashboard_summary')}")
    print(f"history={written.get('history')}")
    print(f"events={written.get('events')}")
    print(f"status={payload.get('status')}")
    print(f"candidate_pattern_count={payload.get('candidate_pattern_count')}")
    print(f"evidence_record_count={payload.get('evidence_record_count')}")
    print(f"paper_review_candidate_count={payload.get('paper_review_candidate_count')}")
    print(f"held_for_evidence_count={payload.get('held_for_evidence_count')}")
    print(f"validated_edge_count={payload.get('validated_edge_count')}")
    print(f"akber_pass_count={payload.get('akber_pass_count')}")
    print(f"akber_hold_count={payload.get('akber_hold_count')}")
    print(f"akber_missing_context_count={payload.get('akber_missing_context_count')}")
    print(f"evidence_contracts_status={payload.get('evidence_contracts', {}).get('status')}")
    print(f"evidence_contract_total_count={payload.get('evidence_contracts', {}).get('total_contract_count')}")
    print(f"evidence_contract_missing_count={payload.get('evidence_contracts', {}).get('missing_evidence_count')}")
    print(f"evidence_contract_downstream_reader_state={payload.get('evidence_contracts', {}).get('downstream_reader_state')}")
    print(f"router_paper_review_candidate_count={payload.get('router_paper_review_candidate_count')}")
    print(f"router_hold_count={payload.get('router_hold_count')}")
    print(
        "historical_complete_forward_window_ratio="
        f"{payload.get('historical_memory', {}).get('complete_forward_window_ratio')}"
    )
    print(f"historical_missing_window_count={payload.get('historical_memory', {}).get('missing_window_count')}")
    print(f"source_freshness_ratio={payload.get('source_reliability', {}).get('freshness_ratio')}")
    print(f"paper_order_created_count={payload.get('paper_order_created_count')}")
    print(f"broker_write_count={payload.get('broker_write_count')}")
    print(f"proof_credit_allowed={payload.get('proof_credit_allowed')}")
    print(f"live_capital_enabled={payload.get('live_capital_enabled')}")

    if validation_errors:
        for error in sorted(set(validation_errors)):
            print(f"error={error}")
        return 1
    print("qsase_evidence_quality_engine_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
