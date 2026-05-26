#!/usr/bin/env python3
"""Validate Q7-16 Phase 7 weekly review packets."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase7_cockpit_visibility import (  # noqa: E402
    build_phase7_cockpit_visibility,
    validate_phase7_cockpit_visibility,
    write_phase7_cockpit_visibility,
)
from orchestrator.phase7_weekly_review_pack import (  # noqa: E402
    PHASE7_WEEKLY_REVIEW_PACK_SCHEMA_VERSION,
    PUBLIC_STATUS_FIELDS,
    build_phase7_weekly_review_pack,
    phase7_weekly_review_pack_paths,
    validate_phase7_weekly_review_pack,
    write_phase7_weekly_review_pack,
)


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _sync_public_status(artifact: dict[str, object]) -> dict[str, object]:
    probe = deepcopy(artifact)
    probe["public_status"] = {
        field: deepcopy(probe.get(field))
        for field in PUBLIC_STATUS_FIELDS
        if field in probe
    }
    probe["public_status"]["validation_error_count"] = len(
        probe.get("validation_errors", []) or []
    )
    return probe


def _with_future_activity(artifact: dict[str, object]) -> dict[str, object]:
    probe = deepcopy(artifact)
    records = deepcopy(probe.get("review_packet_records") or [])
    first = records[0]
    first.update(
        {
            "review_state": "read_only_review_required",
            "qualified_setup_count": 3,
            "target_proof_trade_count": 3,
            "proof_trade_count": 3,
            "closed_proof_trade_count": 2,
            "missed_qualified_setup_count": 0,
            "missed_qualified_setup_unexplained_count": 0,
            "no_trade_rationale": "none_required_qualified_setups_reviewed",
        }
    )
    first["funnel_conversion_summary"].update(
        {
            "qualified_setup_count": 3,
            "target_proof_trade_count": 3,
            "staged_proof_order_count": 3,
            "submitted_paper_order_count": 3,
            "broker_receipt_count": 3,
            "open_position_count": 1,
            "closed_proof_trade_count": 2,
            "complete_decision_chain_count": 2,
            "missing_decision_chain_count": 0,
        }
    )
    records[0] = first
    probe.update(
        {
            "review_packet_records": records,
            "qualified_setup_count": 3,
            "source_submitted_paper_order_count": 3,
            "source_closed_proof_trade_count": 2,
            "source_postmortem_due_count": 2,
            "source_postmortem_missing_count": 0,
            "source_complete_decision_chain_count": 2,
            "source_missing_decision_chain_count": 0,
            "source_expectancy_after_costs_positive": True,
        }
    )
    return _sync_public_status(probe)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase7_weekly_review_pack_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    visibility = build_phase7_cockpit_visibility(settings=settings)
    _, _, _, visibility_written = write_phase7_cockpit_visibility(
        visibility,
        settings=settings,
        record_event=True,
    )
    visibility_errors = validate_phase7_cockpit_visibility(visibility_written)

    artifact = build_phase7_weekly_review_pack(settings=settings)
    output_path, history_path, event_log_path, written = write_phase7_weekly_review_pack(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase7_weekly_review_pack(written)
    runtime_copy = _read_json(output_path)
    replay = EventLog(event_log_path, echo=False).replay()

    valid_future_activity_errors = validate_phase7_weekly_review_pack(
        _with_future_activity(written)
    )

    missing_packet_probe = deepcopy(written)
    missing_packet_probe["review_packet_records"] = missing_packet_probe[
        "review_packet_records"
    ][:-1]
    missing_packet_errors = validate_phase7_weekly_review_pack(missing_packet_probe)

    intervention_probe = deepcopy(written)
    intervention_probe["trade_level_intervention_allowed"] = True
    intervention_probe["trade_level_intervention_count"] = 1
    intervention_probe["review_packet_records"][0]["trade_level_intervention_allowed"] = True
    intervention_probe["review_packet_records"][0]["trade_level_intervention_count"] = 1
    intervention_errors = validate_phase7_weekly_review_pack(intervention_probe)

    comment_scope_probe = deepcopy(written)
    comment_scope_probe["review_packet_records"][0][
        "fund_manager_comment_scope"
    ] = "current_trade_review"
    comment_scope_errors = validate_phase7_weekly_review_pack(comment_scope_probe)

    rationale_probe = deepcopy(written)
    rationale_probe["review_packet_records"][0]["no_trade_rationale"] = ""
    rationale_errors = validate_phase7_weekly_review_pack(rationale_probe)

    ui_probe = deepcopy(written)
    ui_probe["source_visibility_ui_inferred_readiness_count"] = 1
    ui_probe["source_status_records"][0]["ui_inferred_readiness"] = True
    ui_errors = validate_phase7_weekly_review_pack(ui_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["authority_ledger"]["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_probe["review_packet_records"][0]["proof_credit_allowed"] = True
    proof_credit_errors = validate_phase7_weekly_review_pack(proof_credit_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["authority_ledger"]["live_capital_enabled"] = True
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_phase7_weekly_review_pack(live_capital_probe)

    broker_write_probe = deepcopy(written)
    broker_write_probe["broker_post_allowed"] = True
    broker_write_probe["authority_ledger"]["broker_post_allowed"] = True
    broker_write_probe["broker_post_called_count"] = 1
    broker_write_probe["prediction_market_write_allowed"] = True
    broker_write_probe["authority_ledger"]["prediction_market_write_allowed"] = True
    broker_write_probe["prediction_market_write_allowed_count"] = 1
    broker_write_errors = validate_phase7_weekly_review_pack(broker_write_probe)

    raw_payload_probe = deepcopy(written)
    raw_payload_probe["public_status"]["raw_payload"] = {"secret": "hidden"}
    raw_payload_errors = validate_phase7_weekly_review_pack(raw_payload_probe)

    next_stage_probe = deepcopy(written)
    next_stage_probe["q7_17_certification_stage_allowed"] = False
    next_stage_errors = validate_phase7_weekly_review_pack(next_stage_probe)

    print(f"phase7_weekly_review_status={written['status']}")
    print(f"phase7_weekly_review_stage_status={written['stage_status']}")
    print(
        "phase7_weekly_review_schema_version="
        f"{PHASE7_WEEKLY_REVIEW_PACK_SCHEMA_VERSION}"
    )
    print(f"phase7_weekly_review_artifact_path={output_path}")
    print(f"phase7_weekly_review_history_path={history_path}")
    print(f"phase7_weekly_review_event_log_path={event_log_path}")
    print(
        "phase7_weekly_review_source_visibility_status="
        f"{written['source_visibility_status']}"
    )
    print(
        "phase7_weekly_review_source_visibility_backend_derived="
        f"{written['source_visibility_backend_derived']}"
    )
    print(
        "phase7_weekly_review_source_visibility_ui_inferred_readiness_count="
        f"{written['source_visibility_ui_inferred_readiness_count']}"
    )
    print(f"phase7_weekly_review_source_artifact_count={written['source_artifact_count']}")
    print(f"phase7_weekly_review_source_missing_count={written['source_missing_count']}")
    print(
        "phase7_weekly_review_source_validation_error_count="
        f"{written['source_validation_error_count']}"
    )
    print(f"phase7_weekly_review_proof_week_count={written['proof_week_count']}")
    print(
        "phase7_weekly_review_review_pack_record_count="
        f"{written['review_pack_record_count']}"
    )
    print(
        "phase7_weekly_review_packet_created="
        f"{written['weekly_review_packet_created']}"
    )
    print(
        "phase7_weekly_review_packet_created_count="
        f"{written['weekly_review_packet_created_count']}"
    )
    print(
        "phase7_weekly_review_all_proof_weeks_have_review_packet="
        f"{written['all_proof_weeks_have_review_packet']}"
    )
    print(
        "phase7_weekly_review_future_policy_comment_allowed="
        f"{written['future_policy_comment_allowed']}"
    )
    print(
        "phase7_weekly_review_trade_level_intervention_allowed="
        f"{written['trade_level_intervention_allowed']}"
    )
    print(
        "phase7_weekly_review_trade_level_intervention_count="
        f"{written['trade_level_intervention_count']}"
    )
    no_trade_rationale_count = sum(
        1
        for record in written["review_packet_records"]
        if record.get("no_trade_rationale")
    )
    print(f"phase7_weekly_review_no_trade_rationale_count={no_trade_rationale_count}")
    print(
        "phase7_weekly_review_missed_qualified_setup_count="
        f"{written['missed_qualified_setup_count']}"
    )
    print(
        "phase7_weekly_review_source_manual_trade_level_override_count="
        f"{written['source_manual_trade_level_override_count']}"
    )
    print(
        "phase7_weekly_review_phase7_statistical_immaturity_hidden="
        f"{written['phase7_statistical_immaturity_hidden']}"
    )
    print(
        "phase7_weekly_review_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(f"phase7_weekly_review_live_capital_enabled={written['live_capital_enabled']}")
    print(f"phase7_weekly_review_broker_post_called_count={written['broker_post_called_count']}")
    print(f"phase7_weekly_review_alpaca_post_called_count={written['alpaca_post_called_count']}")
    print(
        "phase7_weekly_review_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(
        "phase7_weekly_review_q7_17_certification_stage_allowed="
        f"{written['q7_17_certification_stage_allowed']}"
    )
    print(f"phase7_weekly_review_event_log_events={replay['total_events']}")
    print(f"phase7_weekly_review_validation_errors={validation_errors}")

    if visibility_errors:
        errors.append(f"visibility validation failed: {visibility_errors}")
    if validation_errors:
        errors.append(f"weekly review validation failed: {validation_errors}")
    if runtime_copy.get("artifact_id") != written["artifact_id"]:
        errors.append("runtime artifact did not persist weekly review artifact")
    if replay["total_events"] != 1:
        errors.append("weekly review event log did not record exactly one event")
    if replay["by_type"].get("phase7_weekly_review_recorded") != 1:
        errors.append("weekly review event log event type mismatch")
    if written["status"] != "read_only":
        errors.append("Q7-16 should be read-only after Q7-15")
    if written["review_pack_record_count"] != written["proof_week_count"]:
        errors.append("Q7-16 did not create one packet for each proof week")
    if written["weekly_review_packet_created_count"] != written["proof_week_count"]:
        errors.append("Q7-16 created packet count mismatch")
    if written["future_policy_comment_allowed"] is not True:
        errors.append("Q7-16 does not allow future-policy comments")
    if written["trade_level_intervention_allowed"] is not False:
        errors.append("Q7-16 allows trade-level intervention")
    if written["trade_level_intervention_count"] != 0:
        errors.append("Q7-16 recorded trade-level interventions")
    if no_trade_rationale_count != written["proof_week_count"]:
        errors.append("Q7-16 missing no-trade rationale for at least one proof week")
    if written["q7_17_certification_stage_allowed"] is not True:
        errors.append("Q7-16 does not allow Q7-17 certification stage")
    if valid_future_activity_errors:
        errors.append(
            "valid future weekly activity probe rejected: "
            f"{valid_future_activity_errors}"
        )
    if not missing_packet_errors:
        errors.append("missing packet probe was not rejected")
    if not intervention_errors:
        errors.append("trade-level intervention probe was not rejected")
    if not comment_scope_errors:
        errors.append("current-trade comment scope probe was not rejected")
    if not rationale_errors:
        errors.append("missing no-trade rationale probe was not rejected")
    if not ui_errors:
        errors.append("UI inference probe was not rejected")
    if not proof_credit_errors:
        errors.append("proof credit probe was not rejected")
    if not live_capital_errors:
        errors.append("live capital probe was not rejected")
    if not broker_write_errors:
        errors.append("broker/market write probe was not rejected")
    if not raw_payload_errors:
        errors.append("raw public payload probe was not rejected")
    if not next_stage_errors:
        errors.append("Q7-17 gate probe was not rejected")

    if errors:
        print("phase7_weekly_review_check=failed")
        for error in errors:
            print(f"error={error}")
        return 1
    print("phase7_weekly_review_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
