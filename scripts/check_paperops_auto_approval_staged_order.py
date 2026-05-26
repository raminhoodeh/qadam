#!/usr/bin/env python3
"""Validate PT-4 auto-approval and staged paper-order handoff."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.paperops_auto_approval_staged_order import (  # noqa: E402
    PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_SCHEMA_VERSION,
    build_paperops_auto_approval_staged_order,
    paperops_auto_approval_staged_order_paths,
    validate_paperops_auto_approval_staged_order,
    write_paperops_auto_approval_staged_order,
)


def _first_record(records: list[dict[str, object]]) -> dict[str, object] | None:
    return records[0] if records else None


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = (
        paperops_auto_approval_staged_order_paths(settings)
    )
    if event_log_path.exists():
        event_log_path.unlink()

    artifact = build_paperops_auto_approval_staged_order(settings=settings)
    output_path, history_path, event_log_path, written = (
        write_paperops_auto_approval_staged_order(
            artifact,
            settings=settings,
            record_event=True,
            event_log_path=event_log_path,
        )
    )
    validation_errors = validate_paperops_auto_approval_staged_order(written)
    replay = EventLog(event_log_path, echo=False).replay()

    submit_probe = deepcopy(written)
    submit_probe["paper_order_submission_allowed"] = True
    submit_errors = validate_paperops_auto_approval_staged_order(submit_probe)

    broker_probe = deepcopy(written)
    broker_probe["broker_post_called_count"] = 1
    broker_probe["unsafe_write_counter_total"] = 1
    broker_errors = validate_paperops_auto_approval_staged_order(broker_probe)

    proof_probe = deepcopy(written)
    proof_probe["phase7_proof_credit_allowed"] = True
    proof_errors = validate_paperops_auto_approval_staged_order(proof_probe)

    forced_probe = deepcopy(written)
    forced_probe["forced_trades_allowed"] = True
    forced_errors = validate_paperops_auto_approval_staged_order(forced_probe)

    q7_mutation_probe = deepcopy(written)
    q7_mutation_probe["q7_source_ledger_mutation_performed"] = True
    q7_mutation_errors = validate_paperops_auto_approval_staged_order(
        q7_mutation_probe
    )

    manual_override_probe = deepcopy(written)
    manual_override_probe["manual_trade_level_override_allowed"] = True
    manual_override_errors = validate_paperops_auto_approval_staged_order(
        manual_override_probe
    )

    auto_gate_probe = deepcopy(written)
    auto_records = auto_gate_probe.get("auto_approval_records", [])
    if isinstance(auto_records, list) and auto_records:
        first = _first_record(auto_records)
        if first is not None:
            first["source_quorum_passed"] = False
    auto_gate_errors = validate_paperops_auto_approval_staged_order(auto_gate_probe)

    duplicate_probe = deepcopy(written)
    staged_records = duplicate_probe.get("staged_order_records", [])
    if isinstance(staged_records, list) and staged_records:
        staged_records.append(deepcopy(staged_records[0]))
        duplicate_probe["staged_order_count"] = len(
            [
                record
                for record in staged_records
                if isinstance(record, dict) and record.get("status") == "staged"
            ]
        )
        duplicate_probe["idempotency_key_count"] = duplicate_probe["staged_order_count"]
        duplicate_probe["duplicate_idempotency_key_count"] = 1
        duplicate_probe["event_log_prewrite_ready_count"] = duplicate_probe[
            "staged_order_count"
        ]
        duplicate_probe["event_log_prewrite_written_count"] = duplicate_probe[
            "staged_order_count"
        ]
        duplicate_probe["pre_trade_snapshot_present_count"] = duplicate_probe[
            "staged_order_count"
        ]
    duplicate_errors = validate_paperops_auto_approval_staged_order(duplicate_probe)

    prewrite_probe = deepcopy(written)
    prewrite_records = prewrite_probe.get("staged_order_records", [])
    if isinstance(prewrite_records, list) and prewrite_records:
        first_prewrite = _first_record(prewrite_records)
        if first_prewrite is not None:
            first_prewrite["event_log_prewrite_written"] = False
        prewrite_probe["event_log_prewrite_written_count"] = max(
            0,
            int(prewrite_probe["event_log_prewrite_written_count"]) - 1,
        )
    prewrite_errors = validate_paperops_auto_approval_staged_order(prewrite_probe)

    event_probe = deepcopy(written)
    event_probe["event_log_written"] = False
    event_probe["event_log_event_count"] = 0
    event_errors = validate_paperops_auto_approval_staged_order(event_probe)

    print(f"paperops_auto_approval_staged_order_status={written['status']}")
    print(
        "paperops_auto_approval_staged_order_schema_version="
        f"{PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_SCHEMA_VERSION}"
    )
    print(f"paperops_auto_approval_staged_order_artifact_path={output_path}")
    print(f"paperops_auto_approval_staged_order_history_path={history_path}")
    print(f"paperops_auto_approval_staged_order_event_log_path={event_log_path}")
    print(
        "paperops_auto_approval_staged_order_event_log_events="
        f"{replay['total_events']}"
    )
    print(
        "paperops_auto_approval_staged_order_source_pt3_status="
        f"{written['source_pt3_status']}"
    )
    print(
        "paperops_auto_approval_staged_order_source_pt3_path_ready="
        f"{written['source_pt3_path_ready']}"
    )
    print(
        "paperops_auto_approval_staged_order_source_pt3_candidate_count="
        f"{written['source_pt3_candidate_count']}"
    )
    print(
        "paperops_auto_approval_staged_order_source_pt3_qualified_setup_count="
        f"{written['source_pt3_qualified_setup_count']}"
    )
    print(
        "paperops_auto_approval_staged_order_source_pt3_q7_ledger_count="
        f"{written['source_pt3_q7_ledger_count']}"
    )
    print(
        "paperops_auto_approval_staged_order_auto_approval_record_count="
        f"{written['auto_approval_record_count']}"
    )
    print(
        "paperops_auto_approval_staged_order_auto_approved_setup_count="
        f"{written['auto_approved_setup_count']}"
    )
    print(
        "paperops_auto_approval_staged_order_staged_order_count="
        f"{written['staged_order_count']}"
    )
    print(
        "paperops_auto_approval_staged_order_ready_for_paperops2_submit="
        f"{written['ready_for_paperops2_submit']}"
    )
    print(
        "paperops_auto_approval_staged_order_idempotency_namespace="
        f"{written['idempotency_namespace']}"
    )
    print(
        "paperops_auto_approval_staged_order_idempotency_key_count="
        f"{written['idempotency_key_count']}"
    )
    print(
        "paperops_auto_approval_staged_order_duplicate_idempotency_key_count="
        f"{written['duplicate_idempotency_key_count']}"
    )
    print(
        "paperops_auto_approval_staged_order_event_log_prewrite_ready_count="
        f"{written['event_log_prewrite_ready_count']}"
    )
    print(
        "paperops_auto_approval_staged_order_event_log_prewrite_written_count="
        f"{written['event_log_prewrite_written_count']}"
    )
    print(
        "paperops_auto_approval_staged_order_pre_trade_snapshot_present_count="
        f"{written['pre_trade_snapshot_present_count']}"
    )
    print(
        "paperops_auto_approval_staged_order_q7_source_ledger_mutation_performed="
        f"{written['q7_source_ledger_mutation_performed']}"
    )
    print(
        "paperops_auto_approval_staged_order_q7_auto_approval_mutation_performed="
        f"{written['q7_auto_approval_artifact_mutation_performed']}"
    )
    print(
        "paperops_auto_approval_staged_order_q7_staging_mutation_performed="
        f"{written['q7_staging_artifact_mutation_performed']}"
    )
    print(
        "paperops_auto_approval_staged_order_paper_order_submission_allowed="
        f"{written['paper_order_submission_allowed']}"
    )
    print(
        "paperops_auto_approval_staged_order_broker_post_allowed="
        f"{written['broker_post_allowed']}"
    )
    print(
        "paperops_auto_approval_staged_order_live_capital_enabled="
        f"{written['live_capital_enabled']}"
    )
    print(
        "paperops_auto_approval_staged_order_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(
        "paperops_auto_approval_staged_order_forced_trades_allowed="
        f"{written['forced_trades_allowed']}"
    )
    print(
        "paperops_auto_approval_staged_order_broker_post_called_count="
        f"{written['broker_post_called_count']}"
    )
    print(
        "paperops_auto_approval_staged_order_alpaca_post_called_count="
        f"{written['alpaca_post_called_count']}"
    )
    print(
        "paperops_auto_approval_staged_order_live_endpoint_called_count="
        f"{written['live_endpoint_called_count']}"
    )
    print(
        "paperops_auto_approval_staged_order_phase7_proof_credit_granted_count="
        f"{written['phase7_proof_credit_granted_count']}"
    )
    print(
        "paperops_auto_approval_staged_order_forced_trade_count="
        f"{written['forced_trade_count']}"
    )
    print(
        "paperops_auto_approval_staged_order_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(
        "paperops_auto_approval_staged_order_next_required_action="
        f"{written['next_required_action']}"
    )
    print(
        "paperops_auto_approval_staged_order_validation_errors="
        f"{validation_errors}"
    )

    if validation_errors:
        errors.append(f"PT-4 validation failed: {validation_errors}")
    if replay["total_events"] != 1:
        errors.append("PT-4 event log did not record exactly one event")
    if written["status"] not in {
        "staged_paper_order_ready",
        "ready_no_current_auto_approved_setup",
    }:
        errors.append("PT-4 handoff is not ready")
    if written["source_pt3_path_ready"] is not True:
        errors.append("PT-4 source PT-3 path is not ready")
    if written["source_pt3_qualified_setup_count"] > 0:
        if written["auto_approved_setup_count"] < 1:
            errors.append("PT-4 did not auto-approve the PT-3 qualified setup")
        if written["staged_order_count"] < 1:
            errors.append("PT-4 did not stage the auto-approved setup")
        if written["ready_for_paperops2_submit"] is not True:
            errors.append("PT-4 staged order is not ready for PaperOps-2")
    if written["source_pt3_q7_ledger_count"] != 0:
        errors.append("PT-4 source indicates Q7 ledger mutation")
    if written["q7_source_ledger_mutation_performed"] is not False:
        errors.append("PT-4 mutated the Q7 source ledger")
    if written["q7_auto_approval_artifact_mutation_performed"] is not False:
        errors.append("PT-4 mutated the Q7 auto-approval artifact")
    if written["q7_staging_artifact_mutation_performed"] is not False:
        errors.append("PT-4 mutated the Q7 staging artifact")
    if written["paper_order_submission_allowed"] is not False:
        errors.append("PT-4 opened paper-order submit authority")
    if written["broker_post_allowed"] is not False:
        errors.append("PT-4 opened broker POST authority")
    if written["phase7_proof_credit_allowed"] is not False:
        errors.append("PT-4 granted Phase 7 proof credit")
    if written["forced_trades_allowed"] is not False:
        errors.append("PT-4 allowed forced trades")
    if written["broker_post_called_count"] != 0:
        errors.append("PT-4 called broker POST")
    if written["alpaca_post_called_count"] != 0:
        errors.append("PT-4 called Alpaca POST")
    if written["live_endpoint_called_count"] != 0:
        errors.append("PT-4 called a live endpoint")
    if written["unsafe_write_counter_total"] != 0:
        errors.append("PT-4 unsafe write counter is nonzero")
    if (
        written["event_log_prewrite_written_count"]
        != written["staged_order_count"]
    ):
        errors.append("PT-4 prewrite count does not match staged orders")
    if (
        "paperops_pt4_forbidden:paper_order_submission_allowed"
        not in submit_errors
    ):
        errors.append("paper-submit authority probe was not rejected")
    if (
        "paperops_pt4_unsafe_counter_nonzero:broker_post_called_count"
        not in broker_errors
    ):
        errors.append("broker POST probe was not rejected")
    if "paperops_pt4_forbidden:phase7_proof_credit_allowed" not in proof_errors:
        errors.append("proof-credit probe was not rejected")
    if "paperops_pt4_forbidden:forced_trades_allowed" not in forced_errors:
        errors.append("forced-trades probe was not rejected")
    if (
        "paperops_pt4_forbidden:q7_source_ledger_mutation_performed"
        not in q7_mutation_errors
    ):
        errors.append("Q7 ledger mutation probe was not rejected")
    if (
        "paperops_pt4_forbidden:manual_trade_level_override_allowed"
        not in manual_override_errors
    ):
        errors.append("manual override probe was not rejected")
    if (
        written["auto_approved_setup_count"] > 0
        and "pt4_auto_approval_gate_not_passed:source_quorum_passed"
        not in auto_gate_errors
    ):
        errors.append("auto-approval source quorum probe was not rejected")
    if (
        written["staged_order_count"] > 0
        and "paperops_pt4_duplicate_idempotency" not in duplicate_errors
    ):
        errors.append("duplicate idempotency probe was not rejected")
    if (
        written["staged_order_count"] > 0
        and "pt4_staged_order_prewrite_not_written" not in prewrite_errors
    ):
        errors.append("prewrite probe was not rejected")
    if "paperops_pt4_event_log_missing" not in event_errors:
        errors.append("event-log probe was not rejected")

    if errors:
        print("paperops_auto_approval_staged_order_check=failed")
        for error in errors:
            print(f"error={error}")
        return 1
    print("paperops_auto_approval_staged_order_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
