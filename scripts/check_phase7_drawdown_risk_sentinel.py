#!/usr/bin/env python3
"""Validate Q7-11 Phase 7 Demo Proof drawdown and risk sentinel."""

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
from orchestrator.phase7_drawdown_risk_sentinel import (  # noqa: E402
    PHASE7_DRAWDOWN_RISK_REQUIRED_CHECKS,
    PHASE7_DRAWDOWN_RISK_SENTINEL_SCHEMA_VERSION,
    _authority_ledger,
    _equity_summary,
    build_phase7_drawdown_risk_sentinel,
    phase7_drawdown_risk_sentinel_paths,
    validate_phase7_drawdown_risk_sentinel,
    write_phase7_drawdown_risk_sentinel,
)
from orchestrator.phase7_performance_evaluator import (  # noqa: E402
    PHASE7_PERFORMANCE_EVALUATOR_SCHEMA_VERSION,
    PHASE7_PERFORMANCE_REQUIRED_CHECKS,
    build_phase7_performance_evaluator,
    validate_phase7_performance_evaluator,
    write_phase7_performance_evaluator,
)
from orchestrator.phase7_readiness import phase7_authority_defaults  # noqa: E402
from orchestrator.release_contract import PAPER_ACCOUNT_BALANCE_GBP  # noqa: E402


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
    net_pnl_after_costs_gbp: float = 100.0,
    closed_at: str = "2026-05-25T00:00:00+00:00",
) -> dict[str, object]:
    estimated_cost_gbp = 1.0
    realized_pnl_gbp = net_pnl_after_costs_gbp + estimated_cost_gbp
    risk_size_gbp = 100.0
    checks = [
        {"name": name, "passed": True, "detail": None}
        for name in PHASE7_PERFORMANCE_REQUIRED_CHECKS
    ]
    bucket = _outcome_bucket(net_pnl_after_costs_gbp)
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
        "net_pnl_after_costs_gbp": net_pnl_after_costs_gbp,
        "risk_size_gbp": risk_size_gbp,
        "r_multiple": net_pnl_after_costs_gbp / risk_size_gbp,
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


def _records_from_pnls(pnls: list[float], *, prefix: str) -> list[dict[str, object]]:
    return [
        _valid_metric_record(
            suffix=f"{prefix}{index:04d}",
            net_pnl_after_costs_gbp=pnl,
            closed_at=f"2026-05-{min(25, index + 1):02d}T00:00:00+00:00",
        )
        for index, pnl in enumerate(pnls, start=1)
    ]


def _with_source_records(
    artifact: dict[str, object],
    records: list[dict[str, object]],
    *,
    open_position_count: int = 0,
    unrealized_pnl_gbp: float = 0.0,
) -> dict[str, object]:
    probe = deepcopy(artifact)
    summary = _equity_summary(records, unrealized_pnl_gbp=unrealized_pnl_gbp)
    breached = summary["drawdown_cap_breached"] is True
    frozen = breached
    authorities = phase7_authority_defaults()
    authorities["phase7_proof_lifecycle_write_allowed"] = True
    authorities["phase7_postmortem_write_allowed"] = True
    authorities["phase7_performance_evaluation_write_allowed"] = True
    if not frozen:
        authorities["phase7_test_mode_auto_approval_allowed"] = True
        authorities["phase7_proof_order_staging_allowed"] = True
        authorities["phase7_proof_trade_submission_allowed"] = True
    checks = [
        {"name": name, "passed": True, "detail": None}
        for name in PHASE7_DRAWDOWN_RISK_REQUIRED_CHECKS
    ]
    if open_position_count:
        checks[6] = {
            "name": "unrealized_drawdown_tracked",
            "passed": True,
            "detail": {"open_position_count": open_position_count},
        }
    probe.update(
        {
            "status": (
                "risk_halt_active"
                if breached
                else "drawdown_within_cap"
                if records
                else "ready_no_drawdown_sample"
            ),
            "stage_status": (
                "drawdown_breach_risk_halt_active"
                if breached
                else "drawdown_sentinel_within_cap"
                if records
                else "drawdown_sentinel_ready_no_closed_trades"
            ),
            "authority_ledger": _authority_ledger(
                stage_recorded=True,
                new_proof_trades_frozen=frozen,
            ),
            "source_trade_metric_records": records,
            "source_performance_status": (
                "performance_metrics_recorded" if records else "ready_no_closed_trades"
            ),
            "source_performance_stage_status": (
                "performance_metrics_recorded"
                if records
                else "performance_evaluator_ready_no_closed_trades"
            ),
            "source_performance_recorded": True,
            "source_closed_proof_trade_count": len(records),
            "source_evaluated_trade_count": len(records),
            "source_performance_metric_record_count": len(records),
            "source_performance_drawdown_within_cap": not breached,
            "source_performance_max_drawdown_fraction_observed": summary[
                "max_drawdown_fraction_observed"
            ],
            "q7_11_drawdown_risk_sentinel_stage_allowed": True,
            "q7_12_override_detector_stage_allowed": True,
            "drawdown_sentinel_recorded": True,
            "risk_halt_write_allowed": True,
            "risk_halt_allowed": True,
            "risk_halt_required": breached,
            "risk_halt_active": breached,
            "risk_halt_event_required": breached,
            "risk_halt_event_recorded": breached,
            "risk_halt_review_required": breached,
            "risk_halt_review_state": (
                "required_pending_review" if breached else "not_required"
            ),
            "risk_halt_unresolved": breached,
            "new_proof_trades_frozen": frozen,
            "new_proof_trade_freeze_active": frozen,
            "new_proof_trade_freeze_reason": (
                "max_drawdown_cap_breached" if breached else None
            ),
            "new_proof_order_staging_allowed": not frozen,
            "new_proof_trade_submission_allowed": not frozen,
            "existing_lifecycle_closeout_allowed": True,
            "open_position_count": open_position_count,
            "unrealized_mark_to_market_required": open_position_count > 0,
            "unrealized_mark_to_market_available": True,
            "phase7_certification_blocked_by_drawdown": breached,
            "phase7_certification_blocked_by_unresolved_risk_halt": breached,
            "paper_order_submitted_count": len(records),
            "proof_trade_created_count": len(records),
            "checks": checks,
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
    output_path, history_path, event_log_path = phase7_drawdown_risk_sentinel_paths(
        settings
    )
    if event_log_path.exists():
        event_log_path.unlink()

    performance = build_phase7_performance_evaluator(settings=settings)
    _, _, performance_event_path, performance_written = write_phase7_performance_evaluator(
        performance,
        settings=settings,
        record_event=True,
    )
    performance_errors = validate_phase7_performance_evaluator(performance_written)

    artifact = build_phase7_drawdown_risk_sentinel(settings=settings)
    output_path, history_path, event_log_path, written = (
        write_phase7_drawdown_risk_sentinel(
            artifact,
            settings=settings,
            record_event=True,
            event_log_path=event_log_path,
        )
    )
    validation_errors = validate_phase7_drawdown_risk_sentinel(written)
    replay = EventLog(event_log_path, echo=False).replay()
    runtime_copy = _read_json(output_path)

    valid_within_cap_probe = _with_source_records(
        written,
        _records_from_pnls([100.0, -25.0], prefix="within"),
    )
    valid_within_cap_errors = validate_phase7_drawdown_risk_sentinel(
        valid_within_cap_probe
    )

    valid_breach_probe = _with_source_records(
        written,
        _records_from_pnls([200.0, -25000.0], prefix="breach"),
    )
    valid_breach_errors = validate_phase7_drawdown_risk_sentinel(valid_breach_probe)

    breach_not_frozen_probe = deepcopy(valid_breach_probe)
    breach_not_frozen_probe["new_proof_trades_frozen"] = False
    breach_not_frozen_probe["new_proof_trade_freeze_active"] = False
    breach_not_frozen_probe["risk_halt_active"] = False
    breach_not_frozen_probe["new_proof_order_staging_allowed"] = True
    breach_not_frozen_probe["new_proof_trade_submission_allowed"] = True
    breach_not_frozen_errors = validate_phase7_drawdown_risk_sentinel(
        breach_not_frozen_probe
    )

    no_breach_frozen_probe = deepcopy(valid_within_cap_probe)
    no_breach_frozen_probe["new_proof_trades_frozen"] = True
    no_breach_frozen_probe["new_proof_trade_freeze_active"] = True
    no_breach_frozen_probe["risk_halt_active"] = True
    no_breach_frozen_probe["new_proof_order_staging_allowed"] = False
    no_breach_frozen_probe["new_proof_trade_submission_allowed"] = False
    no_breach_frozen_errors = validate_phase7_drawdown_risk_sentinel(
        no_breach_frozen_probe
    )

    certification_block_probe = deepcopy(valid_breach_probe)
    certification_block_probe["phase7_certification_blocked_by_drawdown"] = False
    certification_block_probe[
        "phase7_certification_blocked_by_unresolved_risk_halt"
    ] = False
    certification_block_errors = validate_phase7_drawdown_risk_sentinel(
        certification_block_probe
    )

    cap_probe = deepcopy(written)
    cap_probe["max_drawdown_fraction"] = 0.25
    cap_probe["drawdown_policy"]["max_drawdown_fraction"] = 0.25
    cap_errors = validate_phase7_drawdown_risk_sentinel(cap_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["authority_ledger"]["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase7_drawdown_risk_sentinel(proof_credit_probe)

    broker_post_probe = deepcopy(written)
    broker_post_probe["broker_post_allowed"] = True
    broker_post_probe["authority_ledger"]["broker_post_allowed"] = True
    broker_post_probe["broker_post_called_count"] = 1
    broker_post_errors = validate_phase7_drawdown_risk_sentinel(broker_post_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["authority_ledger"]["live_capital_enabled"] = True
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_phase7_drawdown_risk_sentinel(live_capital_probe)

    market_write_probe = deepcopy(written)
    market_write_probe["prediction_market_write_allowed"] = True
    market_write_probe["authority_ledger"]["prediction_market_write_allowed"] = True
    market_write_probe["prediction_market_write_allowed_count"] = 1
    market_write_probe["crypto_perps_write_allowed"] = True
    market_write_probe["authority_ledger"]["crypto_perps_write_allowed"] = True
    market_write_probe["crypto_perps_write_allowed_count"] = 1
    market_write_errors = validate_phase7_drawdown_risk_sentinel(market_write_probe)

    manual_override_probe = deepcopy(written)
    manual_override_probe["manual_trade_level_override_allowed"] = True
    manual_override_probe["authority_ledger"][
        "manual_trade_level_override_allowed"
    ] = True
    manual_override_probe["manual_trade_level_override_count"] = 1
    manual_override_errors = validate_phase7_drawdown_risk_sentinel(
        manual_override_probe
    )

    source_posture_probe = deepcopy(written)
    source_posture_probe["source_posture"][
        "preference_mcp_source_quorum_credit_allowed"
    ] = True
    source_posture_probe["source_posture"]["qctrl_role"] = "execution_truth"
    source_posture_errors = validate_phase7_drawdown_risk_sentinel(
        source_posture_probe
    )

    local_path_probe = deepcopy(written)
    local_path_probe["provenance"]["source_refs"] = [
        "/Users/raminhoodeh/Desktop/qadam/data/runtime/private.json"
    ]
    local_path_errors = validate_phase7_drawdown_risk_sentinel(local_path_probe)

    gate_probe = deepcopy(written)
    gate_probe["q7_11_drawdown_risk_sentinel_stage_allowed"] = False
    gate_errors = validate_phase7_drawdown_risk_sentinel(gate_probe)

    next_stage_gate_probe = deepcopy(written)
    next_stage_gate_probe["q7_12_override_detector_stage_allowed"] = False
    next_stage_gate_errors = validate_phase7_drawdown_risk_sentinel(
        next_stage_gate_probe
    )

    unrealized_probe = _with_source_records(
        written,
        _records_from_pnls([20.0], prefix="unrealized"),
        open_position_count=1,
    )
    unrealized_probe["unrealized_mark_to_market_available"] = False
    unrealized_errors = validate_phase7_drawdown_risk_sentinel(unrealized_probe)

    print(f"phase7_drawdown_status={written['status']}")
    print(f"phase7_drawdown_stage_status={written['stage_status']}")
    print(
        "phase7_drawdown_schema_version="
        f"{PHASE7_DRAWDOWN_RISK_SENTINEL_SCHEMA_VERSION}"
    )
    print(f"phase7_drawdown_artifact_path={output_path}")
    print(f"phase7_drawdown_history_path={history_path}")
    print(f"phase7_drawdown_event_log_path={event_log_path}")
    print(f"phase7_drawdown_source_performance_status={written['source_performance_status']}")
    print(
        "phase7_drawdown_source_performance_stage_status="
        f"{written['source_performance_stage_status']}"
    )
    print(
        "phase7_drawdown_q7_12_override_stage_allowed="
        f"{written['q7_12_override_detector_stage_allowed']}"
    )
    print(f"phase7_drawdown_risk_halt_write_allowed={written['risk_halt_write_allowed']}")
    print(f"phase7_drawdown_risk_halt_active={written['risk_halt_active']}")
    print(f"phase7_drawdown_new_proof_trades_frozen={written['new_proof_trades_frozen']}")
    print(
        "phase7_drawdown_new_proof_order_staging_allowed="
        f"{written['new_proof_order_staging_allowed']}"
    )
    print(
        "phase7_drawdown_new_proof_trade_submission_allowed="
        f"{written['new_proof_trade_submission_allowed']}"
    )
    print(
        "phase7_drawdown_source_closed_proof_trade_count="
        f"{written['source_closed_proof_trade_count']}"
    )
    print(
        "phase7_drawdown_source_evaluated_trade_count="
        f"{written['source_evaluated_trade_count']}"
    )
    print(f"phase7_drawdown_current_equity_gbp={written['current_equity_gbp']}")
    print(f"phase7_drawdown_peak_equity_gbp={written['peak_equity_gbp']}")
    print(
        "phase7_drawdown_realized_drawdown_fraction_observed="
        f"{written['realized_drawdown_fraction_observed']}"
    )
    print(
        "phase7_drawdown_unrealized_drawdown_fraction_observed="
        f"{written['unrealized_drawdown_fraction_observed']}"
    )
    print(
        "phase7_drawdown_max_drawdown_fraction_observed="
        f"{written['max_drawdown_fraction_observed']}"
    )
    print(f"phase7_drawdown_drawdown_within_cap={written['drawdown_within_cap']}")
    print(f"phase7_drawdown_drawdown_state={written['drawdown_state']}")
    print(
        "phase7_drawdown_phase7_certification_blocked_by_drawdown="
        f"{written['phase7_certification_blocked_by_drawdown']}"
    )
    print(
        "phase7_drawdown_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(f"phase7_drawdown_live_capital_enabled={written['live_capital_enabled']}")
    print(
        "phase7_drawdown_broker_post_called_count="
        f"{written['broker_post_called_count']}"
    )
    print(
        "phase7_drawdown_alpaca_post_called_count="
        f"{written['alpaca_post_called_count']}"
    )
    print(
        "phase7_drawdown_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(f"phase7_drawdown_blocker_count={written['blocker_count']}")
    print(f"phase7_drawdown_event_log_replay_total_events={replay['total_events']}")
    print(f"phase7_drawdown_source_performance_event_log_path={performance_event_path}")
    print(
        "phase7_drawdown_source_performance_error_count="
        f"{len(performance_errors)}"
    )
    print(
        "phase7_drawdown_valid_within_cap_probe_error_count="
        f"{len(valid_within_cap_errors)}"
    )
    print(
        "phase7_drawdown_valid_breach_probe_error_count="
        f"{len(valid_breach_errors)}"
    )
    print(
        "phase7_drawdown_breach_not_frozen_probe_error_count="
        f"{len(breach_not_frozen_errors)}"
    )
    print(
        "phase7_drawdown_no_breach_frozen_probe_error_count="
        f"{len(no_breach_frozen_errors)}"
    )
    print(
        "phase7_drawdown_certification_block_probe_error_count="
        f"{len(certification_block_errors)}"
    )
    print(f"phase7_drawdown_cap_probe_error_count={len(cap_errors)}")
    print(
        "phase7_drawdown_proof_credit_probe_error_count="
        f"{len(proof_credit_errors)}"
    )
    print(
        "phase7_drawdown_broker_post_probe_error_count="
        f"{len(broker_post_errors)}"
    )
    print(
        "phase7_drawdown_live_capital_probe_error_count="
        f"{len(live_capital_errors)}"
    )
    print(
        "phase7_drawdown_market_write_probe_error_count="
        f"{len(market_write_errors)}"
    )
    print(
        "phase7_drawdown_manual_override_probe_error_count="
        f"{len(manual_override_errors)}"
    )
    print(
        "phase7_drawdown_source_posture_probe_error_count="
        f"{len(source_posture_errors)}"
    )
    print(f"phase7_drawdown_local_path_probe_error_count={len(local_path_errors)}")
    print(f"phase7_drawdown_gate_probe_error_count={len(gate_errors)}")
    print(
        "phase7_drawdown_next_stage_gate_probe_error_count="
        f"{len(next_stage_gate_errors)}"
    )
    print(f"phase7_drawdown_unrealized_probe_error_count={len(unrealized_errors)}")
    print(f"phase7_drawdown_next_stage={written['recommended_next_stage']}")
    print("phase7_drawdown_boundary=" + written["boundary"])

    if performance_errors:
        errors.extend(performance_errors)
    if validation_errors:
        errors.extend(validation_errors)
    if runtime_copy.get("artifact_id") != written["artifact_id"]:
        errors.append("runtime_phase7_drawdown_not_written")
    if written["status"] != "ready_no_drawdown_sample":
        errors.append("phase7_drawdown_status_invalid")
    if written["stage_status"] != "drawdown_sentinel_ready_no_closed_trades":
        errors.append("phase7_drawdown_stage_status_invalid")
    if written["risk_halt_write_allowed"] is not True:
        errors.append("phase7_drawdown_risk_halt_write_authority_missing")
    if written["q7_12_override_detector_stage_allowed"] is not True:
        errors.append("phase7_drawdown_q7_12_not_allowed")
    for count_key in (
        "source_closed_proof_trade_count",
        "source_evaluated_trade_count",
        "source_performance_metric_record_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "unsafe_write_counter_total",
        "blocker_count",
    ):
        if written[count_key] != 0:
            errors.append(f"phase7_drawdown_count_nonzero:{count_key}")
    for flag_key in (
        "risk_halt_active",
        "new_proof_trades_frozen",
        "phase7_certification_blocked_by_drawdown",
        "phase7_proof_trade_execution_allowed",
        "phase7_proof_credit_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "manual_trade_level_override_allowed",
    ):
        if written[flag_key] is not False:
            errors.append(f"phase7_drawdown_forbidden_or_unexpected:{flag_key}")
    if written["new_proof_order_staging_allowed"] is not True:
        errors.append("phase7_drawdown_staging_not_allowed_without_breach")
    if written["new_proof_trade_submission_allowed"] is not True:
        errors.append("phase7_drawdown_submission_not_allowed_without_breach")
    expected_equity = float(PAPER_ACCOUNT_BALANCE_GBP)
    if written["current_equity_gbp"] != expected_equity:
        errors.append("phase7_drawdown_current_equity_invalid")
    if written["peak_equity_gbp"] != expected_equity:
        errors.append("phase7_drawdown_peak_equity_invalid")
    if written["max_drawdown_fraction_observed"] != 0.0:
        errors.append("phase7_drawdown_empty_max_drawdown_nonzero")
    if written["drawdown_within_cap"] is not True:
        errors.append("phase7_drawdown_empty_drawdown_not_within_cap")
    if written["drawdown_state"] != "no_sample_within_cap":
        errors.append("phase7_drawdown_empty_state_invalid")
    if written["event_log_written"] is not True:
        errors.append("phase7_drawdown_event_log_not_written")
    if replay["total_events"] != 1:
        errors.append("phase7_drawdown_event_log_replay_count_mismatch")
    if valid_within_cap_errors:
        errors.append("valid_within_cap_drawdown_probe_rejected")
    if valid_breach_errors:
        errors.append("valid_breach_drawdown_probe_rejected")
    if "phase7_drawdown_breach_not_frozen" not in breach_not_frozen_errors:
        errors.append("breach_not_frozen_probe_not_rejected")
    if "phase7_drawdown_frozen_without_breach" not in no_breach_frozen_errors:
        errors.append("no_breach_frozen_probe_not_rejected")
    if "phase7_drawdown_breach_not_blocking_certification" not in (
        certification_block_errors
    ):
        errors.append("certification_block_probe_not_rejected")
    if "phase7_drawdown_cap_mismatch" not in cap_errors:
        errors.append("cap_probe_not_rejected")
    if "phase7_drawdown_authority_invalid:phase7_proof_credit_allowed" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_authority_probe_not_rejected")
    if "phase7_drawdown_unsafe_count_nonzero:phase7_proof_credit_allowed_count" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_count_probe_not_rejected")
    if "phase7_drawdown_authority_invalid:broker_post_allowed" not in (
        broker_post_errors
    ):
        errors.append("broker_post_authority_probe_not_rejected")
    if "phase7_drawdown_count_nonzero:broker_post_called_count" not in (
        broker_post_errors
    ):
        errors.append("broker_post_count_probe_not_rejected")
    if "phase7_drawdown_authority_invalid:live_capital_enabled" not in (
        live_capital_errors
    ):
        errors.append("live_capital_authority_probe_not_rejected")
    if "phase7_drawdown_unsafe_count_nonzero:live_capital_enabled_count" not in (
        live_capital_errors
    ):
        errors.append("live_capital_count_probe_not_rejected")
    if "phase7_drawdown_authority_invalid:prediction_market_write_allowed" not in (
        market_write_errors
    ):
        errors.append("prediction_market_authority_probe_not_rejected")
    if "phase7_drawdown_authority_invalid:crypto_perps_write_allowed" not in (
        market_write_errors
    ):
        errors.append("crypto_perps_authority_probe_not_rejected")
    if "phase7_drawdown_authority_invalid:manual_trade_level_override_allowed" not in (
        manual_override_errors
    ):
        errors.append("manual_override_authority_probe_not_rejected")
    if "phase7_drawdown_preference_quorum_credit_allowed" not in source_posture_errors:
        errors.append("source_posture_preference_probe_not_rejected")
    if "phase7_drawdown_qctrl_role_invalid" not in source_posture_errors:
        errors.append("source_posture_qctrl_probe_not_rejected")
    if "phase7_drawdown_provenance_local_path_leak" not in local_path_errors:
        errors.append("local_path_probe_not_rejected")
    if "q7_11_drawdown_risk_sentinel_not_allowed" not in gate_errors:
        errors.append("gate_probe_not_rejected")
    if "q7_12_override_detector_not_allowed" not in next_stage_gate_errors:
        errors.append("next_stage_gate_probe_not_rejected")
    if "phase7_drawdown_unrealized_mark_to_market_missing" not in unrealized_errors:
        errors.append("unrealized_probe_not_rejected")

    if errors:
        for error in sorted(set(errors)):
            print(f"phase7_drawdown_error={error}")
        print("phase7_drawdown_risk_sentinel_check=failed")
        return 1

    print("phase7_drawdown_risk_sentinel_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
