#!/usr/bin/env python3
"""Validate Q7-10 Phase 7 Demo Proof performance evaluator."""

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
from orchestrator.phase7_performance_evaluator import (  # noqa: E402
    PHASE7_PERFORMANCE_EVALUATOR_SCHEMA_VERSION,
    PHASE7_PERFORMANCE_REQUIRED_CHECKS,
    _metric_summary,
    build_phase7_performance_evaluator,
    phase7_performance_evaluator_paths,
    validate_phase7_performance_evaluator,
    write_phase7_performance_evaluator,
)
from orchestrator.phase7_proof_postmortem_contract import (  # noqa: E402
    build_phase7_proof_postmortem_contract,
    validate_phase7_proof_postmortem_contract,
    write_phase7_proof_postmortem_contract,
)


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _outcome_bucket(net_pnl: float) -> str:
    if net_pnl > 0:
        return "win"
    if net_pnl < 0:
        return "loss"
    return "breakeven"


def _valid_metric_record(
    *,
    suffix: str = "probe0001",
    realized_pnl_gbp: float = 151.0,
    estimated_cost_gbp: float = 1.0,
    risk_size_gbp: float = 100.0,
    closed_at: str = "2026-05-25T00:00:00+00:00",
) -> dict[str, object]:
    net_pnl = realized_pnl_gbp - estimated_cost_gbp
    r_multiple = net_pnl / risk_size_gbp
    checks = [
        {"name": name, "passed": True, "detail": None}
        for name in PHASE7_PERFORMANCE_REQUIRED_CHECKS
    ]
    bucket = _outcome_bucket(net_pnl)
    return {
        "schema_version": 1,
        "performance_evaluator_schema_version": PHASE7_PERFORMANCE_EVALUATOR_SCHEMA_VERSION,
        "artifact_type": "performance_evaluation",
        "artifact_id": f"phase7:q7-10:performance-metric:q7_closed_trade_{suffix}",
        "phase": "Q7",
        "stage": "Q7-10",
        "status": "evaluated",
        "generated_at": "2026-05-25T00:00:00+00:00",
        "public_safe": True,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "source_q7_9_artifact_id": f"phase7:q7-9:proof-postmortem:{suffix}",
        "source_lifecycle_event_ref": f"phase7:q7-8:proof-lifecycle:{suffix}",
        "source_closed_trade_ref": f"q7-closed-trade-{suffix}",
        "source_setup_record_id": "probe:q7-setup",
        "source_auto_approval_decision_id": "probe:auto-approval:q7-setup",
        "source_order_ref": f"q7-paper-order-{suffix}",
        "source_broker_receipt_ref": f"q7-local-broker-receipt-{suffix}",
        "closed_at": closed_at,
        "realized_pnl_gbp": realized_pnl_gbp,
        "estimated_cost_gbp": estimated_cost_gbp,
        "net_pnl_after_costs_gbp": net_pnl,
        "risk_size_gbp": risk_size_gbp,
        "r_multiple": r_multiple,
        "outcome_bucket": bucket,
        "win": bucket == "win",
        "loss": bucket == "loss",
        "breakeven": bucket == "breakeven",
        "postmortem_coverage_present": True,
        "postmortem_reviewed": False,
        "postmortem_explicitly_deferred": False,
        "performance_evaluation_write_allowed": True,
        "phase7_proof_credit_allowed": False,
        "proof_trade_credit_count": 0,
        "broker_post_called": False,
        "broker_post_called_count": 0,
        "alpaca_post_called": False,
        "alpaca_post_called_count": 0,
        "external_broker_post_performed": False,
        "broker_write_allowed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "prediction_market_write_allowed": False,
        "crypto_perps_write_allowed": False,
        "manual_trade_level_override_allowed": False,
        "secret_value_exposed": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "authorization_header_exposed": False,
        "broker_order_identifier_exposed": False,
        "required_checks": list(PHASE7_PERFORMANCE_REQUIRED_CHECKS),
        "required_check_count": len(PHASE7_PERFORMANCE_REQUIRED_CHECKS),
        "checks": checks,
        "failed_checks": [],
        "failed_check_count": 0,
        "blocked_reasons": [],
        "blocked_reason_count": 0,
    }


def _with_metric_records(
    artifact: dict[str, object],
    records: list[dict[str, object]],
) -> dict[str, object]:
    probe = deepcopy(artifact)
    summary = _metric_summary(records)
    closed_count = len(records)
    probe.update(
        {
            "status": (
                "performance_metrics_recorded"
                if closed_count
                else "ready_no_closed_trades"
            ),
            "stage_status": (
                "performance_metrics_recorded"
                if closed_count
                else "performance_evaluator_ready_no_closed_trades"
            ),
            "source_postmortem_status": (
                "postmortem_due_markers_recorded"
                if closed_count
                else "ready_no_closed_trades"
            ),
            "source_postmortem_stage_status": (
                "proof_postmortem_due_markers_recorded"
                if closed_count
                else "proof_postmortem_contract_ready_no_closed_trades"
            ),
            "source_closed_proof_trade_count": closed_count,
            "source_postmortem_due_count": closed_count,
            "source_postmortem_missing_coverage_count": 0,
            "q7_10_performance_evaluator_stage_allowed": True,
            "q7_11_drawdown_risk_sentinel_stage_allowed": True,
            "performance_evaluator_recorded": True,
            "performance_evaluation_write_allowed": True,
            "trade_metric_records": records,
            "performance_metric_record_count": closed_count,
            "closed_proof_trade_count": closed_count,
            "postmortem_covered_trade_count": closed_count,
            "paper_order_submitted_count": closed_count,
            "proof_trade_created_count": closed_count,
            "blockers": [],
            "blocker_count": 0,
            "validation_errors": [],
            **summary,
        }
    )
    return probe


def _metric_records_from_pnls(pnls: list[float], *, prefix: str) -> list[dict[str, object]]:
    return [
        _valid_metric_record(
            suffix=f"{prefix}{index:04d}",
            realized_pnl_gbp=pnl + 1.0,
            estimated_cost_gbp=1.0,
            risk_size_gbp=100.0,
            closed_at=f"2026-05-{min(25, index + 1):02d}T00:00:00+00:00",
        )
        for index, pnl in enumerate(pnls, start=1)
    ]


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase7_performance_evaluator_paths(
        settings
    )
    if event_log_path.exists():
        event_log_path.unlink()

    postmortem = build_phase7_proof_postmortem_contract(settings=settings)
    _, _, postmortem_event_path, postmortem_written = (
        write_phase7_proof_postmortem_contract(
            postmortem,
            settings=settings,
            record_event=True,
        )
    )
    postmortem_errors = validate_phase7_proof_postmortem_contract(postmortem_written)

    artifact = build_phase7_performance_evaluator(settings=settings)
    output_path, history_path, event_log_path, written = write_phase7_performance_evaluator(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase7_performance_evaluator(written)
    replay = EventLog(event_log_path, echo=False).replay()
    runtime_copy = _read_json(output_path)

    valid_positive_probe = _with_metric_records(
        written,
        _metric_records_from_pnls([150.0, -50.0, 80.0], prefix="positive"),
    )
    valid_positive_errors = validate_phase7_performance_evaluator(valid_positive_probe)

    missing_r_probe = _with_metric_records(
        written,
        [_valid_metric_record(suffix="missing-r")],
    )
    missing_r_probe["trade_metric_records"][0]["r_multiple"] = None
    missing_r_errors = validate_phase7_performance_evaluator(missing_r_probe)

    net_mismatch_probe = _with_metric_records(
        written,
        [_valid_metric_record(suffix="net-mismatch")],
    )
    net_mismatch_probe["trade_metric_records"][0]["net_pnl_after_costs_gbp"] = 151.0
    net_mismatch_errors = validate_phase7_performance_evaluator(net_mismatch_probe)

    negative_expectancy_probe = _with_metric_records(
        written,
        _metric_records_from_pnls([-30.0, -10.0, 5.0], prefix="negative"),
    )
    negative_expectancy_probe[
        "phase7_certification_blocked_by_negative_expectancy"
    ] = False
    negative_expectancy_errors = validate_phase7_performance_evaluator(
        negative_expectancy_probe
    )

    drawdown_probe = _with_metric_records(
        written,
        _metric_records_from_pnls([200.0, -500.0], prefix="drawdown"),
    )
    drawdown_probe["drawdown_within_cap"] = True
    drawdown_probe["phase7_certification_blocked_by_drawdown"] = False
    drawdown_errors = validate_phase7_performance_evaluator(drawdown_probe)

    maturity_probe = _with_metric_records(
        written,
        _metric_records_from_pnls([2.0] * 100, prefix="mature"),
    )
    maturity_probe["statistical_maturity_state"] = "statistically_immature"
    maturity_errors = validate_phase7_performance_evaluator(maturity_probe)

    cost_count_probe = _with_metric_records(
        written,
        _metric_records_from_pnls([20.0, 40.0], prefix="cost"),
    )
    cost_count_probe["cost_estimated_trade_count"] = 0
    cost_count_errors = validate_phase7_performance_evaluator(cost_count_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["authority_ledger"]["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase7_performance_evaluator(proof_credit_probe)

    broker_post_probe = deepcopy(written)
    broker_post_probe["broker_post_allowed"] = True
    broker_post_probe["authority_ledger"]["broker_post_allowed"] = True
    broker_post_probe["broker_post_called_count"] = 1
    broker_post_errors = validate_phase7_performance_evaluator(broker_post_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["authority_ledger"]["live_capital_enabled"] = True
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_phase7_performance_evaluator(live_capital_probe)

    market_write_probe = deepcopy(written)
    market_write_probe["prediction_market_write_allowed"] = True
    market_write_probe["authority_ledger"]["prediction_market_write_allowed"] = True
    market_write_probe["prediction_market_write_allowed_count"] = 1
    market_write_probe["crypto_perps_write_allowed"] = True
    market_write_probe["authority_ledger"]["crypto_perps_write_allowed"] = True
    market_write_probe["crypto_perps_write_allowed_count"] = 1
    market_write_errors = validate_phase7_performance_evaluator(market_write_probe)

    manual_override_probe = deepcopy(written)
    manual_override_probe["manual_trade_level_override_allowed"] = True
    manual_override_probe["authority_ledger"][
        "manual_trade_level_override_allowed"
    ] = True
    manual_override_probe["manual_trade_level_override_count"] = 1
    manual_override_errors = validate_phase7_performance_evaluator(
        manual_override_probe
    )

    source_posture_probe = deepcopy(written)
    source_posture_probe["source_posture"][
        "preference_mcp_source_quorum_credit_allowed"
    ] = True
    source_posture_probe["source_posture"]["qctrl_role"] = "execution_truth"
    source_posture_errors = validate_phase7_performance_evaluator(source_posture_probe)

    local_path_probe = deepcopy(written)
    local_path_probe["provenance"]["source_refs"] = [
        "/Users/raminhoodeh/Desktop/qadam/data/runtime/private.json"
    ]
    local_path_errors = validate_phase7_performance_evaluator(local_path_probe)

    gate_probe = deepcopy(written)
    gate_probe["q7_10_performance_evaluator_stage_allowed"] = False
    gate_errors = validate_phase7_performance_evaluator(gate_probe)

    next_stage_gate_probe = deepcopy(written)
    next_stage_gate_probe["q7_11_drawdown_risk_sentinel_stage_allowed"] = False
    next_stage_gate_errors = validate_phase7_performance_evaluator(
        next_stage_gate_probe
    )

    print(f"phase7_performance_status={written['status']}")
    print(f"phase7_performance_stage_status={written['stage_status']}")
    print(
        "phase7_performance_schema_version="
        f"{PHASE7_PERFORMANCE_EVALUATOR_SCHEMA_VERSION}"
    )
    print(f"phase7_performance_artifact_path={output_path}")
    print(f"phase7_performance_history_path={history_path}")
    print(f"phase7_performance_event_log_path={event_log_path}")
    print(
        "phase7_performance_source_postmortem_status="
        f"{written['source_postmortem_status']}"
    )
    print(
        "phase7_performance_source_postmortem_stage_status="
        f"{written['source_postmortem_stage_status']}"
    )
    print(
        "phase7_performance_q7_11_drawdown_stage_allowed="
        f"{written['q7_11_drawdown_risk_sentinel_stage_allowed']}"
    )
    print(
        "phase7_performance_write_allowed="
        f"{written['performance_evaluation_write_allowed']}"
    )
    print(
        "phase7_performance_closed_proof_trade_count="
        f"{written['closed_proof_trade_count']}"
    )
    print(
        "phase7_performance_evaluated_trade_count="
        f"{written['evaluated_trade_count']}"
    )
    print(
        "phase7_performance_metric_record_count="
        f"{written['performance_metric_record_count']}"
    )
    print(
        "phase7_performance_expectancy_after_costs_gbp="
        f"{written['expectancy_after_costs_gbp']}"
    )
    print(
        "phase7_performance_expectancy_after_costs_positive="
        f"{written['expectancy_after_costs_positive']}"
    )
    print(f"phase7_performance_win_rate={written['win_rate']}")
    print(f"phase7_performance_loss_rate={written['loss_rate']}")
    print(
        "phase7_performance_max_drawdown_fraction_observed="
        f"{written['max_drawdown_fraction_observed']}"
    )
    print(f"phase7_performance_drawdown_within_cap={written['drawdown_within_cap']}")
    print(
        "phase7_performance_statistical_maturity_state="
        f"{written['statistical_maturity_state']}"
    )
    print(
        "phase7_performance_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(
        "phase7_performance_live_capital_enabled="
        f"{written['live_capital_enabled']}"
    )
    print(
        "phase7_performance_broker_post_called_count="
        f"{written['broker_post_called_count']}"
    )
    print(
        "phase7_performance_alpaca_post_called_count="
        f"{written['alpaca_post_called_count']}"
    )
    print(
        "phase7_performance_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(f"phase7_performance_blocker_count={written['blocker_count']}")
    print(f"phase7_performance_event_log_replay_total_events={replay['total_events']}")
    print(f"phase7_performance_source_postmortem_event_log_path={postmortem_event_path}")
    print(
        "phase7_performance_source_postmortem_error_count="
        f"{len(postmortem_errors)}"
    )
    print(
        "phase7_performance_valid_positive_probe_error_count="
        f"{len(valid_positive_errors)}"
    )
    print(
        "phase7_performance_missing_r_probe_error_count="
        f"{len(missing_r_errors)}"
    )
    print(
        "phase7_performance_net_mismatch_probe_error_count="
        f"{len(net_mismatch_errors)}"
    )
    print(
        "phase7_performance_negative_expectancy_probe_error_count="
        f"{len(negative_expectancy_errors)}"
    )
    print(
        "phase7_performance_drawdown_probe_error_count="
        f"{len(drawdown_errors)}"
    )
    print(
        "phase7_performance_maturity_probe_error_count="
        f"{len(maturity_errors)}"
    )
    print(
        "phase7_performance_cost_count_probe_error_count="
        f"{len(cost_count_errors)}"
    )
    print(
        "phase7_performance_proof_credit_probe_error_count="
        f"{len(proof_credit_errors)}"
    )
    print(
        "phase7_performance_broker_post_probe_error_count="
        f"{len(broker_post_errors)}"
    )
    print(
        "phase7_performance_live_capital_probe_error_count="
        f"{len(live_capital_errors)}"
    )
    print(
        "phase7_performance_market_write_probe_error_count="
        f"{len(market_write_errors)}"
    )
    print(
        "phase7_performance_manual_override_probe_error_count="
        f"{len(manual_override_errors)}"
    )
    print(
        "phase7_performance_source_posture_probe_error_count="
        f"{len(source_posture_errors)}"
    )
    print(
        "phase7_performance_local_path_probe_error_count="
        f"{len(local_path_errors)}"
    )
    print(f"phase7_performance_gate_probe_error_count={len(gate_errors)}")
    print(
        "phase7_performance_next_stage_gate_probe_error_count="
        f"{len(next_stage_gate_errors)}"
    )
    print(f"phase7_performance_next_stage={written['recommended_next_stage']}")
    print("phase7_performance_boundary=" + written["boundary"])

    if postmortem_errors:
        errors.extend(postmortem_errors)
    if validation_errors:
        errors.extend(validation_errors)
    if runtime_copy.get("artifact_id") != written["artifact_id"]:
        errors.append("runtime_phase7_performance_not_written")
    if written["status"] != "ready_no_closed_trades":
        errors.append("phase7_performance_status_invalid")
    if written["stage_status"] != "performance_evaluator_ready_no_closed_trades":
        errors.append("phase7_performance_stage_status_invalid")
    if written["performance_evaluation_write_allowed"] is not True:
        errors.append("phase7_performance_write_authority_missing")
    if written["q7_11_drawdown_risk_sentinel_stage_allowed"] is not True:
        errors.append("phase7_performance_q7_11_not_allowed")
    for count_key in (
        "closed_proof_trade_count",
        "evaluated_trade_count",
        "performance_metric_record_count",
        "paper_order_submitted_count",
        "proof_trade_created_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "unsafe_write_counter_total",
        "blocker_count",
    ):
        if written[count_key] != 0:
            errors.append(f"phase7_performance_count_nonzero:{count_key}")
    for flag_key in (
        "phase7_proof_trade_execution_allowed",
        "phase7_proof_credit_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "manual_trade_level_override_allowed",
    ):
        if written[flag_key] is not False:
            errors.append(f"phase7_performance_forbidden_authority:{flag_key}")
    if written["expectancy_after_costs_gbp"] is not None:
        errors.append("phase7_performance_empty_expectancy_not_none")
    if written["drawdown_within_cap"] is not True:
        errors.append("phase7_performance_empty_drawdown_not_within_cap")
    if written["statistical_maturity_state"] != "no_sample":
        errors.append("phase7_performance_empty_maturity_state_invalid")
    if written["event_log_written"] is not True:
        errors.append("phase7_performance_event_log_not_written")
    if replay["total_events"] != 1:
        errors.append("phase7_performance_event_log_replay_count_mismatch")
    if valid_positive_errors:
        errors.append("valid_positive_performance_probe_rejected")
    if "phase7_performance_record_r_multiple_missing" not in missing_r_errors:
        errors.append("missing_r_probe_not_rejected")
    if "phase7_performance_record_net_pnl_mismatch" not in net_mismatch_errors:
        errors.append("net_mismatch_probe_not_rejected")
    if not any(
        "phase7_performance_metric_mismatch:"
        "phase7_certification_blocked_by_negative_expectancy" in error
        for error in negative_expectancy_errors
    ):
        errors.append("negative_expectancy_probe_not_rejected")
    if not any(
        "phase7_performance_metric_mismatch:drawdown_within_cap" in error
        for error in drawdown_errors
    ):
        errors.append("drawdown_probe_not_rejected")
    if not any(
        "phase7_performance_metric_mismatch:statistical_maturity_state" in error
        for error in maturity_errors
    ):
        errors.append("maturity_probe_not_rejected")
    if not any(
        "phase7_performance_metric_mismatch:cost_estimated_trade_count" in error
        for error in cost_count_errors
    ):
        errors.append("cost_count_probe_not_rejected")
    if "phase7_performance_authority_invalid:phase7_proof_credit_allowed" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_authority_probe_not_rejected")
    if "phase7_performance_unsafe_count_nonzero:phase7_proof_credit_allowed_count" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_count_probe_not_rejected")
    if "phase7_performance_authority_invalid:broker_post_allowed" not in (
        broker_post_errors
    ):
        errors.append("broker_post_authority_probe_not_rejected")
    if "phase7_performance_count_nonzero:broker_post_called_count" not in (
        broker_post_errors
    ):
        errors.append("broker_post_count_probe_not_rejected")
    if "phase7_performance_authority_invalid:live_capital_enabled" not in (
        live_capital_errors
    ):
        errors.append("live_capital_authority_probe_not_rejected")
    if "phase7_performance_unsafe_count_nonzero:live_capital_enabled_count" not in (
        live_capital_errors
    ):
        errors.append("live_capital_count_probe_not_rejected")
    if "phase7_performance_authority_invalid:prediction_market_write_allowed" not in (
        market_write_errors
    ):
        errors.append("prediction_market_authority_probe_not_rejected")
    if "phase7_performance_authority_invalid:crypto_perps_write_allowed" not in (
        market_write_errors
    ):
        errors.append("crypto_perps_authority_probe_not_rejected")
    if "phase7_performance_authority_invalid:manual_trade_level_override_allowed" not in (
        manual_override_errors
    ):
        errors.append("manual_override_authority_probe_not_rejected")
    if "phase7_performance_preference_quorum_credit_allowed" not in (
        source_posture_errors
    ):
        errors.append("source_posture_preference_probe_not_rejected")
    if "phase7_performance_qctrl_role_invalid" not in source_posture_errors:
        errors.append("source_posture_qctrl_probe_not_rejected")
    if "phase7_performance_provenance_local_path_leak" not in local_path_errors:
        errors.append("local_path_probe_not_rejected")
    if "q7_10_performance_evaluator_not_allowed" not in gate_errors:
        errors.append("gate_probe_not_rejected")
    if "q7_11_drawdown_risk_sentinel_not_allowed" not in next_stage_gate_errors:
        errors.append("next_stage_gate_probe_not_rejected")

    if errors:
        for error in sorted(set(errors)):
            print(f"phase7_performance_error={error}")
        print("phase7_performance_evaluator_check=failed")
        return 1

    print("phase7_performance_evaluator_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
