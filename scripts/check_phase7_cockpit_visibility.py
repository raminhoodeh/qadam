#!/usr/bin/env python3
"""Validate Q7-15 Phase 7 Demo Proof cockpit visibility."""

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
    PHASE7_COCKPIT_VISIBILITY_SCHEMA_VERSION,
    build_phase7_cockpit_visibility,
    phase7_cockpit_visibility_paths,
    validate_phase7_cockpit_visibility,
    write_phase7_cockpit_visibility,
)
from orchestrator.phase7_maturity_tracker import (  # noqa: E402
    build_phase7_maturity_tracker,
    validate_phase7_maturity_tracker,
    write_phase7_maturity_tracker,
)


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _with_lifecycle_counts(artifact: dict[str, object]) -> dict[str, object]:
    probe = deepcopy(artifact)
    probe.update(
        {
            "status": "visible",
            "stage_status": "phase7_demo_proof_visible",
            "visibility_state": "backend_derived_phase7_demo_proof_visible",
            "proof_state": "maturity_progress_recorded",
            "blockers": [],
            "blocker_count": 0,
            "q7_16_weekly_review_pack_stage_allowed": True,
            "submitted_paper_order_count": 3,
            "broker_receipt_count": 3,
            "mirrored_submitted_order_count": 3,
            "open_position_count": 1,
            "closed_proof_trade_count": 2,
            "postmortem_due_count": 2,
            "postmortem_missing_count": 1,
            "postmortem_reviewed_count": 1,
            "expectancy_after_costs_gbp": -1.25,
            "expectancy_after_costs_positive": False,
            "evaluated_trade_count": 2,
            "drawdown_state": "within_cap",
            "drawdown_within_cap": True,
            "drawdown_cap_breached": False,
            "max_drawdown_fraction_observed": 0.011,
            "risk_halt_active": False,
            "new_proof_trades_frozen": False,
            "override_count": 0,
            "manual_trade_level_override_count": 0,
            "sample_contaminated": False,
            "complete_decision_chain_count": 2,
            "missing_decision_chain_count": 0,
            "private_priors_only_proof_trade_count": 0,
            "maturity_state": "statistically_immature_in_progress",
            "mature_benchmark": 100,
            "maturity_progress_fraction": 0.02,
            "closed_trades_remaining_to_mature": 98,
            "phase7_mature_benchmark_met": False,
            "phase7_mature_status_blocked": True,
            "phase7_statistically_immature": False,
            "phase7_statistical_immaturity_hidden": False,
            "phase7_certification_blocked_by_signal_evidence": False,
            "phase7_certification_blocked_by_maturity": True,
            "broker_post_called_count": 3,
            "alpaca_post_called_count": 3,
            "external_broker_post_performed_count": 3,
            "paper_order_submitted_count": 3,
            "proof_trade_created_count": 3,
            "proof_trade_credit_count": 0,
            "phase7_proof_credit_allowed_count": 0,
            "phase5_test_trade_reuse_count": 0,
            "ui_inferred_readiness_count": 0,
            "unsafe_write_counter_total": 0,
            "validation_errors": [],
        }
    )
    probe["public_status"] = {
        key: deepcopy(probe[key])
        for key in probe.get("public_status", {})
        if key in probe
    }
    for key in (
        "submitted_paper_order_count",
        "broker_receipt_count",
        "mirrored_submitted_order_count",
        "open_position_count",
        "closed_proof_trade_count",
        "postmortem_due_count",
        "postmortem_missing_count",
        "postmortem_reviewed_count",
        "expectancy_after_costs_gbp",
        "expectancy_after_costs_positive",
        "evaluated_trade_count",
        "drawdown_state",
        "drawdown_within_cap",
        "max_drawdown_fraction_observed",
        "complete_decision_chain_count",
        "missing_decision_chain_count",
        "maturity_state",
        "maturity_progress_fraction",
        "closed_trades_remaining_to_mature",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "external_broker_post_performed_count",
    ):
        if key in probe["public_status"]:
            probe["public_status"][key] = deepcopy(probe[key])
    return probe


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase7_cockpit_visibility_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    maturity = build_phase7_maturity_tracker(settings=settings)
    _, _, _, maturity_written = write_phase7_maturity_tracker(
        maturity,
        settings=settings,
        record_event=True,
    )
    maturity_errors = validate_phase7_maturity_tracker(maturity_written)

    artifact = build_phase7_cockpit_visibility(settings=settings)
    output_path, history_path, event_log_path, written = write_phase7_cockpit_visibility(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase7_cockpit_visibility(written)
    runtime_copy = _read_json(output_path)
    replay = EventLog(event_log_path, echo=False).replay()

    valid_lifecycle_probe = _with_lifecycle_counts(written)
    valid_lifecycle_errors = validate_phase7_cockpit_visibility(valid_lifecycle_probe)

    ui_probe = deepcopy(written)
    ui_probe["ui_inferred_readiness_count"] = 1
    ui_errors = validate_phase7_cockpit_visibility(ui_probe)

    display_probe = deepcopy(written)
    display_probe["source_status_records"][0]["display_status"] = "frontend_override"
    display_errors = validate_phase7_cockpit_visibility(display_probe)

    local_source_probe = deepcopy(written)
    local_source_probe["source_status_records"][0]["source_ref"] = (
        "/Users/raminhoodeh/Desktop/qadam/data/runtime/phase7_readiness.json"
    )
    local_source_errors = validate_phase7_cockpit_visibility(local_source_probe)

    hidden_probe = deepcopy(written)
    hidden_probe["phase7_statistical_immaturity_hidden"] = True
    hidden_errors = validate_phase7_cockpit_visibility(hidden_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["authority_ledger"]["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase7_cockpit_visibility(proof_credit_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["authority_ledger"]["live_capital_enabled"] = True
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_phase7_cockpit_visibility(live_capital_probe)

    phase5_reuse_probe = deepcopy(written)
    phase5_reuse_probe["phase5_test_trades_count_for_phase7"] = True
    phase5_reuse_probe["phase5_test_trade_reuse_count"] = 1
    phase5_reuse_errors = validate_phase7_cockpit_visibility(phase5_reuse_probe)

    raw_payload_probe = deepcopy(written)
    raw_payload_probe["public_status"]["raw_payload"] = {"secret": "hidden"}
    raw_payload_errors = validate_phase7_cockpit_visibility(raw_payload_probe)

    next_stage_probe = deepcopy(written)
    next_stage_probe["q7_16_weekly_review_pack_stage_allowed"] = False
    next_stage_errors = validate_phase7_cockpit_visibility(next_stage_probe)

    print(f"phase7_cockpit_visibility_status={written['status']}")
    print(f"phase7_cockpit_visibility_stage_status={written['stage_status']}")
    print(f"phase7_cockpit_visibility_schema_version={PHASE7_COCKPIT_VISIBILITY_SCHEMA_VERSION}")
    print(f"phase7_cockpit_visibility_artifact_path={output_path}")
    print(f"phase7_cockpit_visibility_history_path={history_path}")
    print(f"phase7_cockpit_visibility_event_log_path={event_log_path}")
    print(f"phase7_cockpit_visibility_backend_derived={written['backend_derived']}")
    print(
        "phase7_cockpit_visibility_display_derived_from_backend="
        f"{written['display_derived_from_backend']}"
    )
    print(
        "phase7_cockpit_visibility_dashboard_uses_backend_status="
        f"{written['dashboard_uses_backend_status']}"
    )
    print(
        "phase7_cockpit_visibility_ui_inferred_readiness_count="
        f"{written['ui_inferred_readiness_count']}"
    )
    print(f"phase7_cockpit_visibility_source_artifact_count={written['source_artifact_count']}")
    print(f"phase7_cockpit_visibility_source_missing_count={written['source_missing_count']}")
    print(
        "phase7_cockpit_visibility_source_validation_error_count="
        f"{written['source_validation_error_count']}"
    )
    print(
        "phase7_cockpit_visibility_completed_calendar_day_count="
        f"{written['completed_calendar_day_count']}"
    )
    print(f"phase7_cockpit_visibility_phase7_harness_day_count={written['phase7_harness_day_count']}")
    print(f"phase7_cockpit_visibility_proof_week_count={written['proof_week_count']}")
    print(f"phase7_cockpit_visibility_qualified_setup_count={written['qualified_setup_count']}")
    print(
        "phase7_cockpit_visibility_missed_qualified_setup_count="
        f"{written['missed_qualified_setup_count']}"
    )
    print(
        "phase7_cockpit_visibility_submitted_paper_order_count="
        f"{written['submitted_paper_order_count']}"
    )
    print(f"phase7_cockpit_visibility_broker_receipt_count={written['broker_receipt_count']}")
    print(f"phase7_cockpit_visibility_open_position_count={written['open_position_count']}")
    print(f"phase7_cockpit_visibility_closed_proof_trade_count={written['closed_proof_trade_count']}")
    print(f"phase7_cockpit_visibility_postmortem_due_count={written['postmortem_due_count']}")
    print(
        "phase7_cockpit_visibility_expectancy_after_costs_positive="
        f"{written['expectancy_after_costs_positive']}"
    )
    print(f"phase7_cockpit_visibility_drawdown_within_cap={written['drawdown_within_cap']}")
    print(f"phase7_cockpit_visibility_override_count={written['override_count']}")
    print(f"phase7_cockpit_visibility_sample_contaminated={written['sample_contaminated']}")
    print(
        "phase7_cockpit_visibility_complete_decision_chain_count="
        f"{written['complete_decision_chain_count']}"
    )
    print(f"phase7_cockpit_visibility_maturity_state={written['maturity_state']}")
    print(f"phase7_cockpit_visibility_mature_benchmark={written['mature_benchmark']}")
    print(
        "phase7_cockpit_visibility_maturity_progress_fraction="
        f"{written['maturity_progress_fraction']}"
    )
    print(
        "phase7_cockpit_visibility_phase7_mature_benchmark_met="
        f"{written['phase7_mature_benchmark_met']}"
    )
    print(
        "phase7_cockpit_visibility_phase7_mature_status_blocked="
        f"{written['phase7_mature_status_blocked']}"
    )
    print(
        "phase7_cockpit_visibility_phase7_statistical_immaturity_hidden="
        f"{written['phase7_statistical_immaturity_hidden']}"
    )
    print(
        "phase7_cockpit_visibility_phase5_test_trades_count_for_phase7="
        f"{written['phase5_test_trades_count_for_phase7']}"
    )
    print(
        "phase7_cockpit_visibility_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(f"phase7_cockpit_visibility_live_capital_enabled={written['live_capital_enabled']}")
    print(f"phase7_cockpit_visibility_broker_post_called_count={written['broker_post_called_count']}")
    print(f"phase7_cockpit_visibility_alpaca_post_called_count={written['alpaca_post_called_count']}")
    print(f"phase7_cockpit_visibility_unsafe_write_counter_total={written['unsafe_write_counter_total']}")
    print(
        "phase7_cockpit_visibility_q7_16_weekly_review_pack_stage_allowed="
        f"{written['q7_16_weekly_review_pack_stage_allowed']}"
    )
    print(f"phase7_cockpit_visibility_event_log_events={replay['total_events']}")
    print(f"phase7_cockpit_visibility_validation_errors={validation_errors}")

    if maturity_errors:
        errors.append(f"maturity validation failed: {maturity_errors}")
    if validation_errors:
        errors.append(f"visibility validation failed: {validation_errors}")
    if runtime_copy.get("artifact_id") != written["artifact_id"]:
        errors.append("runtime artifact did not persist the visibility artifact")
    if replay["total_events"] != 1:
        errors.append("visibility event log did not record exactly one event")
    if replay["by_type"].get("phase7_visibility_recorded") != 1:
        errors.append("visibility event log event type mismatch")
    if written["status"] != "visible":
        errors.append("Q7-15 should be visible after Q7-14")
    if written["source_missing_count"] != 0:
        errors.append("Q7-15 source artifacts are missing")
    if written["source_validation_error_count"] != 0:
        errors.append("Q7-15 source validation errors present")
    if written["backend_derived"] is not True:
        errors.append("Q7-15 is not backend-derived")
    if written["ui_inferred_readiness_count"] != 0:
        errors.append("Q7-15 UI inference was present")
    if written["phase7_proof_credit_allowed"] is not False:
        errors.append("Q7-15 grants Phase 7 proof credit")
    if written["live_capital_enabled"] is not False:
        errors.append("Q7-15 enables live capital")
    if written["q7_16_weekly_review_pack_stage_allowed"] is not True:
        errors.append("Q7-15 does not allow Q7-16 weekly review pack stage")
    if valid_lifecycle_errors:
        errors.append(f"valid paper lifecycle visibility probe rejected: {valid_lifecycle_errors}")
    if not ui_errors:
        errors.append("UI inference probe was not rejected")
    if not display_errors:
        errors.append("display/backend mismatch probe was not rejected")
    if not local_source_errors:
        errors.append("local source ref probe was not rejected")
    if not hidden_errors:
        errors.append("hidden immaturity probe was not rejected")
    if not proof_credit_errors:
        errors.append("proof credit probe was not rejected")
    if not live_capital_errors:
        errors.append("live capital probe was not rejected")
    if not phase5_reuse_errors:
        errors.append("Phase 5 proof reuse probe was not rejected")
    if not raw_payload_errors:
        errors.append("raw public payload probe was not rejected")
    if not next_stage_errors:
        errors.append("Q7-16 gate probe was not rejected")

    if errors:
        print("phase7_cockpit_visibility_check=failed")
        for error in errors:
            print(f"error={error}")
        return 1
    print("phase7_cockpit_visibility_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
