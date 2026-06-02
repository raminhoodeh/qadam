#!/usr/bin/env python3
"""Validate Q7-14 Phase 7 100-trade maturity tracker."""

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
from orchestrator.phase7_maturity_tracker import (  # noqa: E402
    PHASE7_MATURITY_REQUIRED_CHECKS,
    PHASE7_MATURITY_TRACKER_SCHEMA_VERSION,
    _authority_ledger,
    _maturity_summary,
    _snapshot_record,
    build_phase7_maturity_tracker,
    phase7_maturity_tracker_paths,
    validate_phase7_maturity_tracker,
    write_phase7_maturity_tracker,
)
from orchestrator.phase7_readiness import (  # noqa: E402
    PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
    phase7_authority_defaults,
)
from orchestrator.phase7_signal_funnel_evidence import (  # noqa: E402
    build_phase7_signal_funnel_evidence,
    validate_phase7_signal_funnel_evidence,
    write_phase7_signal_funnel_evidence,
)


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _checks() -> list[dict[str, object]]:
    return [
        {"name": name, "passed": True, "detail": None}
        for name in PHASE7_MATURITY_REQUIRED_CHECKS
    ]


def _status_for(*, closed_count: int, run_complete: bool) -> tuple[str, str]:
    if closed_count >= PHASE7_MATURE_CLOSED_TRADE_BENCHMARK:
        return "maturity_benchmark_met", "maturity_tracker_benchmark_met"
    if run_complete and closed_count < PHASE7_MATURE_CLOSED_TRADE_BENCHMARK:
        return "statistically_immature", "maturity_tracker_statistically_immature_after_30_days"
    if closed_count:
        return "maturity_progress_recorded", "maturity_tracker_progress_recorded"
    return "ready_no_closed_trades", "maturity_tracker_ready_no_closed_trades"


def _with_maturity_state(
    artifact: dict[str, object],
    *,
    closed_count: int,
    run_complete: bool,
    completed_days: int,
    frozen: bool = False,
) -> dict[str, object]:
    probe = deepcopy(artifact)
    status, stage_status = _status_for(
        closed_count=closed_count,
        run_complete=run_complete,
    )
    authorities = phase7_authority_defaults()
    authorities["phase7_proof_lifecycle_write_allowed"] = True
    authorities["phase7_postmortem_write_allowed"] = True
    authorities["phase7_performance_evaluation_write_allowed"] = True
    if not frozen:
        authorities["phase7_test_mode_auto_approval_allowed"] = True
        authorities["phase7_proof_order_staging_allowed"] = True
        authorities["phase7_proof_trade_submission_allowed"] = True
    summary = _maturity_summary(
        closed_trade_count=closed_count,
        phase7_30_day_run_complete=run_complete,
    )
    snapshot = _snapshot_record(
        closed_trade_count=closed_count,
        phase7_30_day_run_complete=run_complete,
        completed_calendar_day_count=completed_days,
        source_signal_evidence_artifact_id="phase7:q7-13:signal-funnel-evidence",
    )
    probe.update(
        {
            "status": status,
            "stage_status": stage_status,
            "authority_ledger": _authority_ledger(
                stage_recorded=True,
                new_proof_trades_frozen=frozen,
            ),
            "maturity_snapshot_records": [snapshot],
            "closed_proof_trade_refs": [
                f"q7-closed-trade-maturity-probe-{index + 1}"
                for index in range(closed_count)
            ],
            "source_signal_evidence_status": "signal_funnel_evidence_recorded"
            if closed_count
            else "ready_no_proof_trades",
            "source_signal_evidence_stage_status": "signal_funnel_evidence_recorded"
            if closed_count
            else "signal_funnel_evidence_ready_no_proof_trades",
            "source_signal_evidence_record_count": closed_count,
            "source_signal_complete_decision_chain_count": closed_count,
            "source_signal_missing_decision_chain_count": 0,
            "source_signal_certification_blocked": False,
            "source_calendar_status": "scheduled",
            "source_calendar_stage_status": "phase7_calendar_harness_scheduled",
            "calendar_harness_started": run_complete,
            "phase7_30_day_run_complete": run_complete,
            "completed_calendar_day_count": completed_days,
            "q7_14_maturity_tracker_stage_allowed": True,
            "q7_15_cockpit_visibility_stage_allowed": True,
            "maturity_tracker_recorded": True,
            "maturity_tracker_write_allowed": True,
            "mature_benchmark_visible": True,
            "forced_trade_allowed": False,
            "proof_trade_creation_allowed": False,
            "phase7_demo_proof_certified": False,
            "phase7_certification_blocked_by_signal_evidence": False,
            "new_proof_trades_frozen": frozen,
            "new_proof_order_staging_allowed": not frozen,
            "new_proof_trade_submission_allowed": not frozen,
            "existing_lifecycle_closeout_allowed": True,
            "paper_order_submitted_count": closed_count,
            "proof_trade_created_count": closed_count,
            "manual_trade_level_override_count": 0,
            "unsafe_write_counter_total": 0,
            "checks": _checks(),
            "failed_checks": [],
            "failed_check_count": 0,
            "blockers": [],
            "blocker_count": 0,
            "validation_errors": [],
            **authorities,
            **summary,
        }
    )
    return probe


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase7_maturity_tracker_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    signal = build_phase7_signal_funnel_evidence(settings=settings)
    _, _, signal_event_path, signal_written = write_phase7_signal_funnel_evidence(
        signal,
        settings=settings,
        record_event=True,
    )
    signal_errors = validate_phase7_signal_funnel_evidence(signal_written)

    artifact = build_phase7_maturity_tracker(settings=settings)
    output_path, history_path, event_log_path, written = write_phase7_maturity_tracker(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase7_maturity_tracker(written)
    replay = EventLog(event_log_path, echo=False).replay()
    runtime_copy = _read_json(output_path)

    valid_no_sample_probe = _with_maturity_state(
        written,
        closed_count=0,
        run_complete=False,
        completed_days=0,
    )
    valid_no_sample_errors = validate_phase7_maturity_tracker(valid_no_sample_probe)

    valid_progress_probe = _with_maturity_state(
        written,
        closed_count=3,
        run_complete=False,
        completed_days=12,
    )
    valid_progress_errors = validate_phase7_maturity_tracker(valid_progress_probe)

    valid_immature_probe = _with_maturity_state(
        written,
        closed_count=25,
        run_complete=True,
        completed_days=30,
    )
    valid_immature_errors = validate_phase7_maturity_tracker(valid_immature_probe)

    valid_mature_probe = _with_maturity_state(
        written,
        closed_count=100,
        run_complete=True,
        completed_days=30,
    )
    valid_mature_errors = validate_phase7_maturity_tracker(valid_mature_probe)

    hidden_immaturity_probe = deepcopy(valid_immature_probe)
    hidden_immaturity_probe["phase7_statistical_immaturity_hidden"] = True
    hidden_immaturity_errors = validate_phase7_maturity_tracker(hidden_immaturity_probe)

    under_100_mature_probe = deepcopy(valid_immature_probe)
    under_100_mature_probe["phase7_mature_benchmark_met"] = True
    under_100_mature_probe["phase7_mature_status_blocked"] = False
    under_100_mature_errors = validate_phase7_maturity_tracker(under_100_mature_probe)

    immature_not_blocking_probe = deepcopy(valid_immature_probe)
    immature_not_blocking_probe["phase7_certification_blocked_by_maturity"] = False
    immature_not_blocking_errors = validate_phase7_maturity_tracker(
        immature_not_blocking_probe
    )

    operational_erased_probe = deepcopy(valid_immature_probe)
    operational_erased_probe["phase7_30_day_operational_result_erased_by_immaturity"] = True
    operational_erased_errors = validate_phase7_maturity_tracker(
        operational_erased_probe
    )

    forced_trade_probe = deepcopy(written)
    forced_trade_probe["forced_trade_allowed"] = True
    forced_trade_errors = validate_phase7_maturity_tracker(forced_trade_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["authority_ledger"]["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase7_maturity_tracker(proof_credit_probe)

    broker_post_probe = deepcopy(written)
    broker_post_probe["broker_post_allowed"] = True
    broker_post_probe["authority_ledger"]["broker_post_allowed"] = True
    broker_post_probe["broker_post_called_count"] = 1
    broker_post_errors = validate_phase7_maturity_tracker(broker_post_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["authority_ledger"]["live_capital_enabled"] = True
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_phase7_maturity_tracker(live_capital_probe)

    market_write_probe = deepcopy(written)
    market_write_probe["prediction_market_write_allowed"] = True
    market_write_probe["authority_ledger"]["prediction_market_write_allowed"] = True
    market_write_probe["prediction_market_write_allowed_count"] = 1
    market_write_probe["crypto_perps_write_allowed"] = True
    market_write_probe["authority_ledger"]["crypto_perps_write_allowed"] = True
    market_write_probe["crypto_perps_write_allowed_count"] = 1
    market_write_errors = validate_phase7_maturity_tracker(market_write_probe)

    manual_authority_probe = deepcopy(written)
    manual_authority_probe["manual_trade_level_override_allowed"] = True
    manual_authority_probe["authority_ledger"]["manual_trade_level_override_allowed"] = True
    manual_authority_errors = validate_phase7_maturity_tracker(manual_authority_probe)

    source_posture_probe = deepcopy(written)
    source_posture_probe["source_posture"]["preference_mcp_source_quorum_credit_allowed"] = True
    source_posture_probe["source_posture"]["qctrl_role"] = "execution_truth"
    source_posture_errors = validate_phase7_maturity_tracker(source_posture_probe)

    local_path_probe = deepcopy(written)
    local_path_probe["provenance"]["source_refs"] = [
        "/Users/raminhoodeh/Desktop/qadam/data/runtime/private.json"
    ]
    local_path_errors = validate_phase7_maturity_tracker(local_path_probe)

    gate_probe = deepcopy(written)
    gate_probe["q7_14_maturity_tracker_stage_allowed"] = False
    gate_errors = validate_phase7_maturity_tracker(gate_probe)

    next_stage_gate_probe = deepcopy(written)
    next_stage_gate_probe["q7_15_cockpit_visibility_stage_allowed"] = False
    next_stage_gate_errors = validate_phase7_maturity_tracker(next_stage_gate_probe)

    print(f"phase7_maturity_status={written['status']}")
    print(f"phase7_maturity_stage_status={written['stage_status']}")
    print(f"phase7_maturity_schema_version={PHASE7_MATURITY_TRACKER_SCHEMA_VERSION}")
    print(f"phase7_maturity_artifact_path={output_path}")
    print(f"phase7_maturity_history_path={history_path}")
    print(f"phase7_maturity_event_log_path={event_log_path}")
    print(f"phase7_maturity_source_signal_status={written['source_signal_evidence_status']}")
    print(
        "phase7_maturity_q7_15_cockpit_visibility_stage_allowed="
        f"{written['q7_15_cockpit_visibility_stage_allowed']}"
    )
    print(f"phase7_maturity_write_allowed={written['maturity_tracker_write_allowed']}")
    print(f"phase7_maturity_closed_proof_trade_count={written['closed_proof_trade_count']}")
    print(f"phase7_maturity_mature_benchmark={written['mature_benchmark']}")
    print(f"phase7_maturity_progress_fraction={written['maturity_progress_fraction']}")
    print(
        "phase7_maturity_closed_trades_remaining_to_mature="
        f"{written['closed_trades_remaining_to_mature']}"
    )
    print(
        "phase7_maturity_phase7_mature_benchmark_met="
        f"{written['phase7_mature_benchmark_met']}"
    )
    print(
        "phase7_maturity_phase7_mature_status_blocked="
        f"{written['phase7_mature_status_blocked']}"
    )
    print(
        "phase7_maturity_phase7_statistically_immature="
        f"{written['phase7_statistically_immature']}"
    )
    print(
        "phase7_maturity_phase7_statistical_immaturity_hidden="
        f"{written['phase7_statistical_immaturity_hidden']}"
    )
    print(
        "phase7_maturity_phase7_30_day_run_complete="
        f"{written['phase7_30_day_run_complete']}"
    )
    print(
        "phase7_maturity_completed_calendar_day_count="
        f"{written['completed_calendar_day_count']}"
    )
    print(
        "phase7_maturity_phase7_30_day_operational_result_erased_by_immaturity="
        f"{written['phase7_30_day_operational_result_erased_by_immaturity']}"
    )
    print(
        "phase7_maturity_phase7_certification_blocked_by_maturity="
        f"{written['phase7_certification_blocked_by_maturity']}"
    )
    print(
        "phase7_maturity_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(f"phase7_maturity_live_capital_enabled={written['live_capital_enabled']}")
    print(f"phase7_maturity_broker_post_called_count={written['broker_post_called_count']}")
    print(f"phase7_maturity_alpaca_post_called_count={written['alpaca_post_called_count']}")
    print(
        "phase7_maturity_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(f"phase7_maturity_blocker_count={written['blocker_count']}")
    print(f"phase7_maturity_event_log_replay_total_events={replay['total_events']}")
    print(f"phase7_maturity_source_signal_event_log_path={signal_event_path}")
    print(f"phase7_maturity_source_signal_error_count={len(signal_errors)}")
    print(
        "phase7_maturity_valid_no_sample_probe_error_count="
        f"{len(valid_no_sample_errors)}"
    )
    print(
        "phase7_maturity_valid_progress_probe_error_count="
        f"{len(valid_progress_errors)}"
    )
    print(
        "phase7_maturity_valid_immature_probe_error_count="
        f"{len(valid_immature_errors)}"
    )
    print(
        "phase7_maturity_valid_mature_probe_error_count="
        f"{len(valid_mature_errors)}"
    )
    print(
        "phase7_maturity_hidden_immaturity_probe_error_count="
        f"{len(hidden_immaturity_errors)}"
    )
    print(
        "phase7_maturity_under_100_mature_probe_error_count="
        f"{len(under_100_mature_errors)}"
    )
    print(
        "phase7_maturity_immature_not_blocking_probe_error_count="
        f"{len(immature_not_blocking_errors)}"
    )
    print(
        "phase7_maturity_operational_erased_probe_error_count="
        f"{len(operational_erased_errors)}"
    )
    print(
        "phase7_maturity_forced_trade_probe_error_count="
        f"{len(forced_trade_errors)}"
    )
    print(
        "phase7_maturity_proof_credit_probe_error_count="
        f"{len(proof_credit_errors)}"
    )
    print(
        "phase7_maturity_broker_post_probe_error_count="
        f"{len(broker_post_errors)}"
    )
    print(
        "phase7_maturity_live_capital_probe_error_count="
        f"{len(live_capital_errors)}"
    )
    print(
        "phase7_maturity_market_write_probe_error_count="
        f"{len(market_write_errors)}"
    )
    print(
        "phase7_maturity_manual_authority_probe_error_count="
        f"{len(manual_authority_errors)}"
    )
    print(
        "phase7_maturity_source_posture_probe_error_count="
        f"{len(source_posture_errors)}"
    )
    print(f"phase7_maturity_local_path_probe_error_count={len(local_path_errors)}")
    print(f"phase7_maturity_gate_probe_error_count={len(gate_errors)}")
    print(
        "phase7_maturity_next_stage_gate_probe_error_count="
        f"{len(next_stage_gate_errors)}"
    )
    print(f"phase7_maturity_next_stage={written['recommended_next_stage']}")
    print("phase7_maturity_boundary=" + written["boundary"])

    if signal_errors:
        errors.extend(signal_errors)
    if validation_errors:
        errors.extend(validation_errors)
    if runtime_copy.get("artifact_id") != written["artifact_id"]:
        errors.append("runtime_phase7_maturity_not_written")
    if written["status"] != "ready_no_closed_trades":
        errors.append("phase7_maturity_status_invalid")
    if written["stage_status"] != "maturity_tracker_ready_no_closed_trades":
        errors.append("phase7_maturity_stage_status_invalid")
    if written["maturity_tracker_write_allowed"] is not True:
        errors.append("phase7_maturity_write_authority_missing")
    if written["q7_15_cockpit_visibility_stage_allowed"] is not True:
        errors.append("phase7_maturity_q7_15_not_allowed")
    for count_key in (
        "closed_proof_trade_count",
        "maturity_progress_fraction",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "unsafe_write_counter_total",
        "completed_calendar_day_count",
        "blocker_count",
    ):
        if written[count_key] != 0:
            errors.append(f"phase7_maturity_count_nonzero:{count_key}")
    for flag_key in (
        "phase7_mature_benchmark_met",
        "phase7_statistically_immature",
        "phase7_statistical_immaturity_hidden",
        "phase7_30_day_run_complete",
        "phase7_30_day_operational_result_erased_by_immaturity",
        "forced_trade_allowed",
        "phase7_demo_proof_certified",
        "phase7_proof_trade_execution_allowed",
        "phase7_proof_credit_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "manual_trade_level_override_allowed",
    ):
        if written[flag_key] is not False:
            errors.append(f"phase7_maturity_forbidden_or_unexpected:{flag_key}")
    for flag_key in (
        "mature_benchmark_visible",
        "phase7_mature_status_blocked",
        "phase7_statistical_immaturity_allowed",
        "phase7_statistical_immaturity_dashboard_warning_required",
        "phase7_30_day_operational_result_preserved",
        "phase7_certification_blocked_by_maturity",
    ):
        if written[flag_key] is not True:
            errors.append(f"phase7_maturity_expected_true_missing:{flag_key}")
    if written["mature_benchmark"] != 100:
        errors.append("phase7_maturity_benchmark_invalid")
    if written["closed_trades_remaining_to_mature"] != 100:
        errors.append("phase7_maturity_remaining_invalid")
    if written["event_log_written"] is not True:
        errors.append("phase7_maturity_event_log_not_written")
    if replay["total_events"] != 1:
        errors.append("phase7_maturity_event_log_replay_count_mismatch")
    if valid_no_sample_errors:
        errors.append("valid_no_sample_probe_rejected")
    if valid_progress_errors:
        errors.append("valid_progress_probe_rejected")
    if valid_immature_errors:
        errors.append("valid_30_day_immature_probe_rejected")
    if valid_mature_errors:
        errors.append("valid_mature_probe_rejected")
    if "phase7_maturity_forbidden:phase7_statistical_immaturity_hidden" not in (
        hidden_immaturity_errors
    ):
        errors.append("hidden_immaturity_probe_not_rejected")
    if "phase7_maturity_summary_mismatch:phase7_mature_benchmark_met" not in (
        under_100_mature_errors
    ):
        errors.append("under_100_mature_probe_not_rejected")
    if "phase7_maturity_summary_mismatch:phase7_certification_blocked_by_maturity" not in (
        immature_not_blocking_errors
    ):
        errors.append("immature_not_blocking_probe_not_rejected")
    if "phase7_maturity_forbidden:phase7_30_day_operational_result_erased_by_immaturity" not in (
        operational_erased_errors
    ):
        errors.append("operational_erased_probe_not_rejected")
    if "phase7_maturity_forbidden:forced_trade_allowed" not in forced_trade_errors:
        errors.append("forced_trade_probe_not_rejected")
    if "phase7_maturity_authority_invalid:phase7_proof_credit_allowed" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_authority_probe_not_rejected")
    if "phase7_maturity_unsafe_count_nonzero:phase7_proof_credit_allowed_count" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_count_probe_not_rejected")
    if "phase7_maturity_authority_invalid:broker_post_allowed" not in broker_post_errors:
        errors.append("broker_post_authority_probe_not_rejected")
    if "phase7_maturity_count_nonzero:broker_post_called_count" not in (
        broker_post_errors
    ):
        errors.append("broker_post_count_probe_not_rejected")
    if "phase7_maturity_authority_invalid:live_capital_enabled" not in live_capital_errors:
        errors.append("live_capital_authority_probe_not_rejected")
    if "phase7_maturity_unsafe_count_nonzero:live_capital_enabled_count" not in (
        live_capital_errors
    ):
        errors.append("live_capital_count_probe_not_rejected")
    if "phase7_maturity_authority_invalid:prediction_market_write_allowed" not in (
        market_write_errors
    ):
        errors.append("prediction_market_authority_probe_not_rejected")
    if "phase7_maturity_authority_invalid:crypto_perps_write_allowed" not in (
        market_write_errors
    ):
        errors.append("crypto_perps_authority_probe_not_rejected")
    if "phase7_maturity_authority_invalid:manual_trade_level_override_allowed" not in (
        manual_authority_errors
    ):
        errors.append("manual_authority_probe_not_rejected")
    if "phase7_maturity_preference_quorum_credit_allowed" not in source_posture_errors:
        errors.append("source_posture_preference_probe_not_rejected")
    if "phase7_maturity_qctrl_role_invalid" not in source_posture_errors:
        errors.append("source_posture_qctrl_probe_not_rejected")
    if "phase7_maturity_provenance_local_path_leak" not in local_path_errors:
        errors.append("local_path_probe_not_rejected")
    if "q7_14_maturity_tracker_not_allowed" not in gate_errors:
        errors.append("gate_probe_not_rejected")
    if "q7_15_cockpit_visibility_not_allowed" not in next_stage_gate_errors:
        errors.append("next_stage_gate_probe_not_rejected")
    if written["recommended_next_stage"] != "Q7-15 Cockpit And Mission Control Visibility":
        errors.append("phase7_maturity_next_stage_mismatch")

    if errors:
        print("phase7_maturity_check=FAIL")
        for error in sorted(set(errors)):
            print(f"error={error}")
        return 1
    print("phase7_maturity_check=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
