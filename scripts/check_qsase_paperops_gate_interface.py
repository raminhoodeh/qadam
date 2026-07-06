#!/usr/bin/env python3
"""Validate and write QSASE-11 PaperOps Gate Interface artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_paperops_gate_interface import (
    DASHBOARD_SUMMARY_ARTIFACT,
    EVENTS_ARTIFACT,
    GATE_RECORDS_ARTIFACT,
    HANDOFF_RECORDS_ARTIFACT,
    HISTORY_ARTIFACT,
    PRIMARY_ARTIFACT,
    REJECTED_HANDOFFS_ARTIFACT,
    _read_jsonl,
    _runtime_dir,
    build_and_write_paperops_gate_interface,
    load_paperops_gate_interface,
    validate_negative_paperops_gate_interface_probes,
    validate_paperops_gate_interface,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    settings = Settings.from_env()
    payload, written, errors = build_and_write_paperops_gate_interface(settings)
    runtime_dir = _runtime_dir(settings)

    validation_errors = list(errors)
    for filename in (
        PRIMARY_ARTIFACT,
        GATE_RECORDS_ARTIFACT,
        HANDOFF_RECORDS_ARTIFACT,
        REJECTED_HANDOFFS_ARTIFACT,
        EVENTS_ARTIFACT,
        HISTORY_ARTIFACT,
        DASHBOARD_SUMMARY_ARTIFACT,
    ):
        path = runtime_dir / filename
        if not path.exists():
            validation_errors.append(f"{filename}_missing")

    primary = _load_json(runtime_dir / PRIMARY_ARTIFACT)
    gate_records = _read_jsonl(runtime_dir / GATE_RECORDS_ARTIFACT)
    handoff_records = _read_jsonl(runtime_dir / HANDOFF_RECORDS_ARTIFACT)
    rejected_handoffs = _read_jsonl(runtime_dir / REJECTED_HANDOFFS_ARTIFACT)
    loaded = load_paperops_gate_interface(settings)

    if primary.get("generated_at") != payload.get("generated_at"):
        validation_errors.append("written_primary_generated_at_mismatch")
    if len(gate_records) != payload.get("gate_record_count"):
        validation_errors.append("written_gate_record_count_mismatch")
    if len(handoff_records) != payload.get("handoff_record_count"):
        validation_errors.append("written_handoff_record_count_mismatch")
    if len(rejected_handoffs) != payload.get("non_eligible_handoff_count"):
        validation_errors.append("written_rejected_handoff_count_mismatch")
    validation_errors.extend(validate_paperops_gate_interface(loaded))
    validation_errors.extend(validate_negative_paperops_gate_interface_probes())

    print(f"artifact={written.get('paperops_gate_interface')}")
    print(f"gate_records={written.get('gate_records')}")
    print(f"handoff_records={written.get('handoff_records')}")
    print(f"rejected_handoffs={written.get('rejected_handoffs')}")
    print(f"dashboard_summary={written.get('dashboard_summary')}")
    print(f"phase_status={written.get('phase_status')}")
    print(f"implementation_log={written.get('implementation_log')}")
    print(f"status={payload.get('status')}")
    print(f"router_candidate_count={payload.get('router_candidate_count')}")
    print(f"gate_record_count={payload.get('gate_record_count')}")
    print(f"handoff_record_count={payload.get('handoff_record_count')}")
    print(f"eligible_for_paperops_review_count={payload.get('eligible_for_paperops_review_count')}")
    print(f"held_handoff_count={payload.get('held_handoff_count')}")
    print(f"rejected_handoff_count={payload.get('rejected_handoff_count')}")
    print(f"non_eligible_handoff_count={payload.get('non_eligible_handoff_count')}")
    print(f"duplicate_idempotency_count={payload.get('duplicate_idempotency_count')}")
    print(f"duplicate_exposure_count={payload.get('duplicate_exposure_count')}")
    print(f"source_quorum_block_count={payload.get('source_quorum_block_count')}")
    print(f"drawdown_block_count={payload.get('drawdown_block_count')}")
    print(f"qctrl_hold_count={payload.get('qctrl_hold_count')}")
    print(f"paper_route_unavailable_count={payload.get('paper_route_unavailable_count')}")
    print(f"guarded_alpaca_paper_route_state={payload.get('guarded_alpaca_paper_route_state')}")
    print(f"qctrl_paper_consultation_state={payload.get('qctrl_paper_consultation_state')}")
    print(f"top_blocking_gate={payload.get('top_blocking_gate')}")
    print(f"paper_order_created_count={payload.get('paper_order_created_count')}")
    print(f"broker_write_count={payload.get('broker_write_count')}")
    print(f"proof_credit_allowed={payload.get('proof_credit_allowed')}")
    print(f"live_capital_enabled={payload.get('live_capital_enabled')}")
    if validation_errors:
        for error in validation_errors:
            print(f"error={error}")
        return 1
    print("qsase_paperops_gate_interface_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
