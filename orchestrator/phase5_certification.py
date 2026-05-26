"""Q5-15 Phase 5 certification gate.

This gate aggregates the Layer B implementation evidence and decides whether
Phase 5 may exit into Phase 6 and Phase 7 planning. The evaluation is
replayable even while blocked: Q5-15 can certify only after Q5-14 proves one
complete paper lifecycle, and it cannot grant live-capital or Phase 7 proof
credit by itself.
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.phase5_alpaca_paper_dry_run import (
    ALPACA_PAPER_DRY_RUN_RUNTIME_ARTIFACT,
    build_phase5_alpaca_paper_dry_run,
    validate_phase5_alpaca_paper_dry_run_bundle,
)
from orchestrator.phase5_approval_policy import (
    APPROVAL_POLICY_RUNTIME_ARTIFACT,
    build_phase5_approval_policy_decisions,
    validate_phase5_approval_policy_bundle,
)
from orchestrator.phase5_artifacts import (
    PHASE5_ARTIFACT_SCHEMA_VERSION,
    PHASE5_AUTHORITY_FIELDS,
    build_phase5_sample_artifacts,
    phase5_artifact_bundle_summary,
    phase5_authority_defaults,
    phase5_authority_ledger,
    phase5_provenance,
    phase5_source_posture,
    validate_phase5_artifact,
)
from orchestrator.phase5_execution_adapter_status import (
    EXECUTION_ADAPTER_RUNTIME_ARTIFACT,
    build_phase5_execution_adapter_status,
    validate_phase5_execution_adapter_status_bundle,
)
from orchestrator.phase5_kill_switch import (
    KILL_SWITCH_RUNTIME_ARTIFACT,
    build_phase5_kill_switch_ledger,
    validate_phase5_kill_switch_ledger,
)
from orchestrator.phase5_paper_order_staging import (
    PAPER_ORDER_STAGING_RUNTIME_ARTIFACT,
    build_phase5_paper_order_staging_gate,
    validate_phase5_paper_order_staging_bundle,
)
from orchestrator.phase5_paper_submit_enablement import (
    PAPER_SUBMIT_ENABLEMENT_RUNTIME_ARTIFACT,
    build_phase5_paper_submit_enablement_gate,
    validate_phase5_paper_submit_enablement_bundle,
)
from orchestrator.phase5_paper_trade_drill import (
    PAPER_TRADE_DRILL_RUNTIME_ARTIFACT,
    build_phase5_paper_trade_drill,
    validate_phase5_paper_trade_drill_bundle,
)
from orchestrator.phase5_position_monitor import (
    POSITION_MONITOR_RUNTIME_ARTIFACT,
    build_phase5_position_monitor,
    validate_phase5_position_monitor_bundle,
)
from orchestrator.phase5_prediction_market_adapter import (
    PREDICTION_MARKET_ADAPTER_RUNTIME_ARTIFACT,
    build_phase5_prediction_market_adapter,
    validate_phase5_prediction_market_adapter_bundle,
)
from orchestrator.phase5_readiness import (
    PHASE5_READINESS_ARTIFACT,
    build_phase5_layer_b_readiness,
    validate_phase5_layer_b_readiness,
)
from orchestrator.phase5_risk_sizing import (
    RISK_SIZING_RUNTIME_ARTIFACT,
    build_phase5_risk_sizing_reviews,
    validate_phase5_risk_sizing_bundle,
)
from orchestrator.phase5_signal_review import (
    SIGNAL_REVIEW_RUNTIME_ARTIFACT,
    build_phase5_signal_review,
    validate_phase5_signal_review_bundle,
)
from orchestrator.phase5_system_map import (
    SYSTEM_MAP_RUNTIME_ARTIFACT,
    validate_phase5_system_map_bundle,
)
from orchestrator.phase5_telegram_notifier import (
    TELEGRAM_NOTIFIER_RUNTIME_ARTIFACT,
    build_phase5_telegram_notifier,
    validate_phase5_telegram_notifier_bundle,
)
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT


PHASE5_CERTIFICATION_SCHEMA_VERSION = 1
PHASE5_CERTIFICATION_RUNTIME_ARTIFACT = "phase5_certification.json"
PHASE5_CERTIFICATION_HISTORY = "phase5_certification_history.jsonl"
PHASE5_CERTIFICATION_EVENT_LOG = "phase5_certification_events.jsonl"
PHASE5_CERTIFICATION_EVENT_TYPE = "phase5_certification_evaluated"
PHASE5_CERTIFICATION_COMPONENT = "phase5_certification"

PHASE5_INPUT_STAGE_COUNT = 15
PHASE5_TOTAL_STAGE_COUNT = 16

PHASE5_CERTIFICATION_SOURCE_REFS: tuple[str, ...] = (
    f"data/runtime/{PHASE5_READINESS_ARTIFACT}",
    "orchestrator/phase5_artifacts.py",
    f"data/runtime/{APPROVAL_POLICY_RUNTIME_ARTIFACT}",
    f"data/runtime/{RISK_SIZING_RUNTIME_ARTIFACT}",
    f"data/runtime/{KILL_SWITCH_RUNTIME_ARTIFACT}",
    f"data/runtime/{EXECUTION_ADAPTER_RUNTIME_ARTIFACT}",
    f"data/runtime/{PAPER_ORDER_STAGING_RUNTIME_ARTIFACT}",
    f"data/runtime/{ALPACA_PAPER_DRY_RUN_RUNTIME_ARTIFACT}",
    f"data/runtime/{PAPER_SUBMIT_ENABLEMENT_RUNTIME_ARTIFACT}",
    f"data/runtime/{PREDICTION_MARKET_ADAPTER_RUNTIME_ARTIFACT}",
    f"data/runtime/{TELEGRAM_NOTIFIER_RUNTIME_ARTIFACT}",
    f"data/runtime/{POSITION_MONITOR_RUNTIME_ARTIFACT}",
    f"data/runtime/{SIGNAL_REVIEW_RUNTIME_ARTIFACT}",
    f"data/runtime/{SYSTEM_MAP_RUNTIME_ARTIFACT}",
    f"data/runtime/{PAPER_TRADE_DRILL_RUNTIME_ARTIFACT}",
)

PHASE5_CERTIFICATION_REQUIRED_INPUT_STAGES: tuple[str, ...] = (
    "Q5-0",
    "Q5-1",
    "Q5-2",
    "Q5-3",
    "Q5-4",
    "Q5-5",
    "Q5-6",
    "Q5-7",
    "Q5-8",
    "Q5-9",
    "Q5-10",
    "Q5-11",
    "Q5-12",
    "Q5-13",
    "Q5-14",
)

PHASE5_CERTIFICATION_SAFE_ZERO_FIELDS: tuple[str, ...] = (
    "broker_write_allowed_count",
    "prediction_market_write_allowed_count",
    "crypto_perps_write_allowed_count",
    "telegram_live_notifications_allowed_count",
    "telegram_command_path_enabled_count",
    "position_monitor_write_authority_count",
    "position_close_allowed_count",
    "position_resize_allowed_count",
    "order_cancel_allowed_count",
    "live_endpoint_allowed_count",
    "live_capital_enabled_count",
    "phase7_proof_credit_allowed_count",
    "secret_value_exposed_count",
    "raw_payload_exposed_count",
    "local_path_exposed_count",
    "authorization_header_exposed_count",
    "broker_order_identifier_exposed_count",
    "account_identifier_exposed_count",
)

PHASE5_CERTIFICATION_BLOCKING_COUNTS: tuple[str, ...] = (
    "broker_write_allowed_count",
    "prediction_market_write_allowed_count",
    "crypto_perps_write_allowed_count",
    "live_endpoint_allowed_count",
    "live_capital_enabled_count",
    "phase7_proof_credit_allowed_count",
)

PHASE5_CERTIFICATION_BOUNDARY = (
    "Q5-15 is a certification gate only. It can record whether Layer B paper "
    "orchestration is complete, but it cannot bypass Q5-14, cannot submit or "
    "modify orders, cannot call live endpoints, cannot write prediction-market "
    "or crypto-perps venues, cannot enable live capital, and cannot let Phase 5 "
    "test trades count toward Phase 7 proof."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def phase5_certification_paths(settings: Settings | None = None) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE5_CERTIFICATION_RUNTIME_ARTIFACT,
        runtime / PHASE5_CERTIFICATION_HISTORY,
        runtime / PHASE5_CERTIFICATION_EVENT_LOG,
    )


def _certification_authority_ledger() -> dict[str, Any]:
    ledger = phase5_authority_ledger()
    ledger["stage"] = "Q5-15"
    ledger["boundary"] = PHASE5_CERTIFICATION_BOUNDARY
    return ledger


def _runtime_or_build(
    settings: Settings,
    artifact_name: str,
    builder: Callable[..., dict[str, Any]],
    validator: Callable[[dict[str, Any]], list[str]],
) -> tuple[dict[str, Any], bool, list[str]]:
    runtime = _read_json(_runtime_dir(settings) / artifact_name)
    recorded = runtime is not None
    bundle = runtime or builder(settings=settings)
    return bundle, recorded, list(validator(bundle))


def _artifact_schema_gate() -> tuple[dict[str, Any], bool, list[str]]:
    sample = build_phase5_sample_artifacts()
    summary = phase5_artifact_bundle_summary(sample)
    errors = list(summary.get("errors", []))
    return summary, True, errors


def _system_map_gate(settings: Settings) -> tuple[dict[str, Any], bool, list[str]]:
    runtime = _read_json(_runtime_dir(settings) / SYSTEM_MAP_RUNTIME_ARTIFACT)
    recorded = runtime is not None
    if runtime is None:
        return {"status": "missing", "validation_errors": ["system_map_runtime_missing"]}, False, [
            "system_map_runtime_missing"
        ]
    return runtime, recorded, list(validate_phase5_system_map_bundle(runtime))


def _source_gates(settings: Settings) -> list[dict[str, Any]]:
    readiness, readiness_recorded, readiness_errors = _runtime_or_build(
        settings,
        PHASE5_READINESS_ARTIFACT,
        build_phase5_layer_b_readiness,
        validate_phase5_layer_b_readiness,
    )
    artifact_schema, artifact_schema_recorded, artifact_schema_errors = _artifact_schema_gate()
    approval, approval_recorded, approval_errors = _runtime_or_build(
        settings,
        APPROVAL_POLICY_RUNTIME_ARTIFACT,
        build_phase5_approval_policy_decisions,
        validate_phase5_approval_policy_bundle,
    )
    risk, risk_recorded, risk_errors = _runtime_or_build(
        settings,
        RISK_SIZING_RUNTIME_ARTIFACT,
        build_phase5_risk_sizing_reviews,
        validate_phase5_risk_sizing_bundle,
    )
    kill_switch, kill_switch_recorded, kill_switch_errors = _runtime_or_build(
        settings,
        KILL_SWITCH_RUNTIME_ARTIFACT,
        build_phase5_kill_switch_ledger,
        validate_phase5_kill_switch_ledger,
    )
    execution_adapter, execution_adapter_recorded, execution_adapter_errors = _runtime_or_build(
        settings,
        EXECUTION_ADAPTER_RUNTIME_ARTIFACT,
        build_phase5_execution_adapter_status,
        validate_phase5_execution_adapter_status_bundle,
    )
    staging, staging_recorded, staging_errors = _runtime_or_build(
        settings,
        PAPER_ORDER_STAGING_RUNTIME_ARTIFACT,
        build_phase5_paper_order_staging_gate,
        validate_phase5_paper_order_staging_bundle,
    )
    dry_run, dry_run_recorded, dry_run_errors = _runtime_or_build(
        settings,
        ALPACA_PAPER_DRY_RUN_RUNTIME_ARTIFACT,
        build_phase5_alpaca_paper_dry_run,
        validate_phase5_alpaca_paper_dry_run_bundle,
    )
    submit, submit_recorded, submit_errors = _runtime_or_build(
        settings,
        PAPER_SUBMIT_ENABLEMENT_RUNTIME_ARTIFACT,
        build_phase5_paper_submit_enablement_gate,
        validate_phase5_paper_submit_enablement_bundle,
    )
    prediction, prediction_recorded, prediction_errors = _runtime_or_build(
        settings,
        PREDICTION_MARKET_ADAPTER_RUNTIME_ARTIFACT,
        build_phase5_prediction_market_adapter,
        validate_phase5_prediction_market_adapter_bundle,
    )
    telegram, telegram_recorded, telegram_errors = _runtime_or_build(
        settings,
        TELEGRAM_NOTIFIER_RUNTIME_ARTIFACT,
        build_phase5_telegram_notifier,
        validate_phase5_telegram_notifier_bundle,
    )
    position, position_recorded, position_errors = _runtime_or_build(
        settings,
        POSITION_MONITOR_RUNTIME_ARTIFACT,
        build_phase5_position_monitor,
        validate_phase5_position_monitor_bundle,
    )
    signal_review, signal_review_recorded, signal_review_errors = _runtime_or_build(
        settings,
        SIGNAL_REVIEW_RUNTIME_ARTIFACT,
        build_phase5_signal_review,
        validate_phase5_signal_review_bundle,
    )
    system_map, system_map_recorded, system_map_errors = _system_map_gate(settings)
    drill, drill_recorded, drill_errors = _runtime_or_build(
        settings,
        PAPER_TRADE_DRILL_RUNTIME_ARTIFACT,
        build_phase5_paper_trade_drill,
        validate_phase5_paper_trade_drill_bundle,
    )

    return [
        _gate_record(
            stage="Q5-0",
            label="Re-entry and Phase 5 readiness",
            artifact_key="phase5_layer_b_readiness",
            bundle=readiness,
            recorded=readiness_recorded,
            validation_errors=readiness_errors,
            pass_conditions={
                "implementation_allowed": readiness.get(
                    "phase5_layer_b_implementation_allowed"
                )
                is True,
                "orchestration_start_blocked": readiness.get(
                    "phase5_orchestration_start_allowed"
                )
                is False,
            },
        ),
        _gate_record(
            stage="Q5-1",
            label="Artifact schema and authority ledger",
            artifact_key="phase5_artifact_schema",
            bundle=artifact_schema,
            recorded=artifact_schema_recorded,
            validation_errors=artifact_schema_errors,
            pass_conditions={
                "artifact_bundle_valid": artifact_schema.get("status") == "ok",
                "all_contracts_present": artifact_schema.get("artifact_count")
                == artifact_schema.get("artifact_type_count"),
                "no_authority_enabled": artifact_schema.get("authority_enabled_count") == 0,
            },
        ),
        _gate_record(
            stage="Q5-2",
            label="Approval policy router",
            artifact_key="phase5_approval_policy_decisions",
            bundle=approval,
            recorded=approval_recorded,
            validation_errors=approval_errors,
            pass_conditions={"decisions_recorded": int(approval.get("decision_count", 0) or 0) > 0},
        ),
        _gate_record(
            stage="Q5-3",
            label="Risk Agent paper sizing",
            artifact_key="phase5_risk_sizing_reviews",
            bundle=risk,
            recorded=risk_recorded,
            validation_errors=risk_errors,
            pass_conditions={
                "risk_reviews_recorded": int(risk.get("risk_review_count", 0) or 0) > 0,
                "risk_reviews_classified": (
                    int(risk.get("paper_size_eligible_count", 0) or 0)
                    + int(risk.get("blocked_count", 0) or 0)
                )
                == int(risk.get("risk_review_count", 0) or 0),
            },
        ),
        _gate_record(
            stage="Q5-4",
            label="Kill-switch ledger",
            artifact_key="phase5_kill_switch_ledger",
            bundle=kill_switch,
            recorded=kill_switch_recorded,
            validation_errors=kill_switch_errors,
            pass_conditions={
                "switches_recorded": int(kill_switch.get("switch_count", 0) or 0) > 0,
                "blocking_switch_count_exported": int(
                    kill_switch.get("blocking_switch_count", 0) or 0
                )
                >= 0,
            },
        ),
        _gate_record(
            stage="Q5-5",
            label="Execution adapter status",
            artifact_key="phase5_execution_adapter_status",
            bundle=execution_adapter,
            recorded=execution_adapter_recorded,
            validation_errors=execution_adapter_errors,
            pass_conditions={
                "adapters_recorded": int(
                    execution_adapter.get("adapter_status_count", 0) or 0
                )
                > 0,
                "write_paths_blocked": int(
                    execution_adapter.get("write_allowed_count", 0) or 0
                )
                == 0,
            },
        ),
        _gate_record(
            stage="Q5-6",
            label="Paper order staging gate",
            artifact_key="phase5_paper_order_staging_gate",
            bundle=staging,
            recorded=staging_recorded,
            validation_errors=staging_errors,
            pass_conditions={
                "staging_records_recorded": int(staging.get("staging_record_count", 0) or 0)
                > 0,
                "no_submitted_orders": int(staging.get("paper_order_submitted_count", 0) or 0)
                == 0,
            },
        ),
        _gate_record(
            stage="Q5-7",
            label="Alpaca paper dry-run",
            artifact_key="phase5_alpaca_paper_dry_run",
            bundle=dry_run,
            recorded=dry_run_recorded,
            validation_errors=dry_run_errors,
            pass_conditions={
                "dry_run_records_recorded": int(dry_run.get("dry_run_record_count", 0) or 0)
                > 0,
                "broker_post_blocked": int(dry_run.get("broker_post_called_count", 0) or 0)
                == 0,
            },
        ),
        _gate_record(
            stage="Q5-8",
            label="Paper submit enablement gate",
            artifact_key="phase5_paper_submit_enablement_gate",
            bundle=submit,
            recorded=submit_recorded,
            validation_errors=submit_errors,
            pass_conditions={
                "submit_records_recorded": int(
                    submit.get("submit_enablement_record_count", 0) or 0
                )
                > 0,
                "paper_submit_approval_required": submit.get("paper_submit_approval_present")
                is False
                or submit.get("paper_submit_approval_present") is True,
                "broker_post_not_called": int(submit.get("broker_post_called_count", 0) or 0)
                == 0,
                "paper_order_state_has_receipt": int(
                    submit.get("broker_submit_receipt_created_count", 0) or 0
                )
                == int(submit.get("paper_order_submitted_count", 0) or 0),
            },
        ),
        _gate_record(
            stage="Q5-9",
            label="Prediction market adapter",
            artifact_key="phase5_prediction_market_adapter",
            bundle=prediction,
            recorded=prediction_recorded,
            validation_errors=prediction_errors,
            pass_conditions={
                "routes_recorded": int(
                    prediction.get("prediction_market_route_count", 0) or 0
                )
                > 0,
                "prediction_writes_disabled": int(
                    prediction.get("prediction_market_write_allowed_count", 0) or 0
                )
                == 0,
            },
        ),
        _gate_record(
            stage="Q5-10",
            label="Telegram notifier",
            artifact_key="phase5_telegram_notifier",
            bundle=telegram,
            recorded=telegram_recorded,
            validation_errors=telegram_errors,
            pass_conditions={
                "alerts_recorded": int(telegram.get("alert_type_count", 0) or 0) > 0,
                "live_send_disabled": int(telegram.get("live_send_allowed_count", 0) or 0)
                == 0,
                "command_path_disabled": int(
                    telegram.get("telegram_command_path_enabled_count", 0) or 0
                )
                == 0,
            },
        ),
        _gate_record(
            stage="Q5-11",
            label="Position monitor",
            artifact_key="phase5_position_monitor",
            bundle=position,
            recorded=position_recorded,
            validation_errors=position_errors,
            pass_conditions={
                "position_records_recorded": int(position.get("monitor_record_count", 0) or 0)
                > 0,
                "write_authority_disabled": int(
                    position.get("position_monitor_write_authority_count", 0) or 0
                )
                == 0,
            },
        ),
        _gate_record(
            stage="Q5-12",
            label="Signal review governance actions",
            artifact_key="phase5_signal_review",
            bundle=signal_review,
            recorded=signal_review_recorded,
            validation_errors=signal_review_errors,
            pass_conditions={
                "signal_reviews_recorded": int(
                    signal_review.get("signal_review_record_count", 0) or 0
                )
                > 0,
                "backend_truth_displayed": int(
                    signal_review.get("backend_truth_displayed_count", 0) or 0
                )
                == int(signal_review.get("signal_review_record_count", 0) or 0),
                "ui_inferred_readiness_zero": int(
                    signal_review.get("ui_inferred_readiness_count", 0) or 0
                )
                == 0,
            },
        ),
        _gate_record(
            stage="Q5-13",
            label="Functional system map dashboard",
            artifact_key="phase5_system_map",
            bundle=system_map,
            recorded=system_map_recorded,
            validation_errors=system_map_errors,
            pass_conditions={
                "system_map_recorded": system_map_recorded,
                "backend_display_parity": int(
                    system_map.get("backend_parity_error_count", 0) or 0
                )
                == 0,
                "unsafe_controls_absent": int(system_map.get("unsafe_control_count", 0) or 0)
                == 0,
            },
        ),
        _gate_record(
            stage="Q5-14",
            label="End-to-end paper trade drill",
            artifact_key="phase5_paper_trade_drill",
            bundle=drill,
            recorded=drill_recorded,
            validation_errors=drill_errors,
            pass_conditions={
                "paper_trade_drill_complete": drill.get("paper_trade_drill_complete")
                is True,
                "paper_trade_drill_exit_gate_passed": drill.get(
                    "phase5_paper_trade_drill_exit_gate_passed"
                )
                is True,
                "submitted_order_recorded": int(
                    drill.get("submitted_paper_order_count", 0) or 0
                )
                > 0,
                "open_position_recorded": drill.get("position_open_lifecycle_satisfied") is True
                or int(drill.get("open_position_count", 0) or 0) > 0
                or int(drill.get("closed_trade_count", 0) or 0) > 0,
                "closed_trade_recorded": int(drill.get("closed_trade_count", 0) or 0) > 0,
                "postmortem_due_recorded": int(drill.get("postmortem_due_count", 0) or 0)
                > 0,
            },
        ),
    ]


def _gate_record(
    *,
    stage: str,
    label: str,
    artifact_key: str,
    bundle: dict[str, Any],
    recorded: bool,
    validation_errors: list[str],
    pass_conditions: dict[str, bool],
) -> dict[str, Any]:
    failed_conditions = sorted(key for key, passed in pass_conditions.items() if not passed)
    safe_zero_fields = PHASE5_CERTIFICATION_SAFE_ZERO_FIELDS
    blocking_count_fields = PHASE5_CERTIFICATION_BLOCKING_COUNTS
    if artifact_key == "phase5_paper_submit_enablement_gate":
        safe_zero_fields = tuple(
            field for field in safe_zero_fields if field != "broker_write_allowed_count"
        )
        blocking_count_fields = tuple(
            field for field in blocking_count_fields if field != "broker_write_allowed_count"
        )
    unsafe_counts = {
        field: int(bundle.get(field, 0) or 0)
        for field in safe_zero_fields
        if int(bundle.get(field, 0) or 0) != 0
    }
    safe_blocking_counts = {
        field: int(bundle.get(field, 0) or 0)
        for field in blocking_count_fields
        if int(bundle.get(field, 0) or 0) != 0
    }
    backend_status = (
        "passed"
        if recorded and not validation_errors and not failed_conditions and not safe_blocking_counts
        else "blocked"
    )
    return {
        "schema_version": PHASE5_ARTIFACT_SCHEMA_VERSION,
        "phase5_certification_schema_version": PHASE5_CERTIFICATION_SCHEMA_VERSION,
        "artifact_type": "phase5_certification_gate",
        "artifact_id": f"phase5:q5-15:gate:{stage.lower()}",
        "phase": "Q5",
        "stage": "Q5-15",
        "source_stage": stage,
        "label": label,
        "artifact_key": artifact_key,
        "source_artifact_id": bundle.get("artifact_id"),
        "source_status": bundle.get("status", "unknown"),
        "backend_status": backend_status,
        "display_status": backend_status,
        "display_derived_from_backend": True,
        "ui_inferred_readiness": False,
        "gate_passed": backend_status == "passed",
        "recorded": recorded,
        "validation_error_count": len(validation_errors),
        "validation_errors": validation_errors,
        "pass_conditions": pass_conditions,
        "failed_conditions": failed_conditions,
        "unsafe_counts": unsafe_counts,
        "blocking_unsafe_counts": safe_blocking_counts,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_correlation_id": None,
        "public_safe": True,
        "phase7_proof_credit_allowed": False,
        "phase5_test_trade_counted_for_phase7": False,
        **phase5_authority_defaults(),
        "boundary": PHASE5_CERTIFICATION_BOUNDARY,
    }


def _stage_gate(gates: list[dict[str, Any]], stage: str) -> dict[str, Any]:
    for gate in gates:
        if gate.get("source_stage") == stage:
            return gate
    return {}


def _aggregate_count(gates: list[dict[str, Any]], field: str) -> int:
    total = 0
    for gate in gates:
        unsafe_counts = gate.get("unsafe_counts", {})
        if isinstance(unsafe_counts, dict):
            total += int(unsafe_counts.get(field, 0) or 0)
    return total


def build_phase5_certification(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    gates = _source_gates(settings)
    q5_14 = _stage_gate(gates, "Q5-14")
    q5_14_conditions = q5_14.get("pass_conditions", {})

    certification_blockers: list[str] = []
    for gate in gates:
        if gate.get("gate_passed") is not True:
            certification_blockers.append(
                f"{str(gate.get('source_stage')).lower()}_gate_not_passed"
            )
    if q5_14_conditions.get("paper_trade_drill_complete") is not True:
        certification_blockers.append("q5_14_paper_trade_lifecycle_incomplete")
    if q5_14_conditions.get("paper_trade_drill_exit_gate_passed") is not True:
        certification_blockers.append("q5_14_exit_gate_not_passed")
    if q5_14_conditions.get("submitted_order_recorded") is not True:
        certification_blockers.append("submitted_paper_order_missing")
    if q5_14_conditions.get("open_position_recorded") is not True:
        certification_blockers.append("open_position_missing")
    if q5_14_conditions.get("closed_trade_recorded") is not True:
        certification_blockers.append("closed_trade_missing")
    if q5_14_conditions.get("postmortem_due_recorded") is not True:
        certification_blockers.append("postmortem_due_missing")

    blocking_unsafe_count = sum(
        sum(int(value or 0) for value in gate.get("blocking_unsafe_counts", {}).values())
        for gate in gates
    )
    if blocking_unsafe_count:
        certification_blockers.append("blocking_unsafe_count_nonzero")

    certification_blockers = sorted(set(certification_blockers))
    phase5_certified = not certification_blockers
    status = "eligible" if phase5_certified else "blocked"

    certification_artifact = {
        "schema_version": PHASE5_ARTIFACT_SCHEMA_VERSION,
        "phase5_certification_schema_version": PHASE5_CERTIFICATION_SCHEMA_VERSION,
        "artifact_type": "phase5_certification",
        "artifact_id": "phase5:q5-15:certification",
        "phase": "Q5",
        "stage": "Q5-15",
        "status": status,
        "stage_status": "phase5_certified" if phase5_certified else "blocked_pending_q5_14",
        "generated_at": generated_at,
        "public_safe": True,
        "recorded": False,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_event_count": 0,
        "event_log_correlation_id": None,
        "runtime_artifact_path": None,
        "history_log_path": None,
        "authority_ledger": _certification_authority_ledger(),
        "source_posture": phase5_source_posture(),
        "provenance": phase5_provenance(PHASE5_CERTIFICATION_SOURCE_REFS),
        "boundary": PHASE5_CERTIFICATION_BOUNDARY,
        **phase5_authority_defaults(),
        "canonical_source_count": EXPECTED_SOURCE_COUNT,
        "phase5_certified": phase5_certified,
        "phase5_complete": phase5_certified,
        "phase5_exit_gate": phase5_certified,
        "phase6_handoff_allowed": phase5_certified,
        "phase7_planning_allowed": phase5_certified,
        "phase7_proof_credit_allowed": False,
        "phase5_test_trades_count_for_phase7": False,
        "q5_stage_count": PHASE5_TOTAL_STAGE_COUNT,
        "required_input_stage_count": PHASE5_INPUT_STAGE_COUNT,
        "required_input_stages": list(PHASE5_CERTIFICATION_REQUIRED_INPUT_STAGES),
        "input_gate_count": len(gates),
        "input_gate_passed_count": sum(1 for gate in gates if gate.get("gate_passed") is True),
        "input_gate_blocked_count": sum(1 for gate in gates if gate.get("gate_passed") is not True),
        "gate_records": gates,
        "certification_blockers": certification_blockers,
        "certification_blocker_count": len(certification_blockers),
        "paper_trade_drill_complete": q5_14_conditions.get(
            "paper_trade_drill_complete"
        )
        is True,
        "paper_trade_drill_exit_gate_passed": q5_14_conditions.get(
            "paper_trade_drill_exit_gate_passed"
        )
        is True,
        "submitted_paper_order_count": 1
        if q5_14_conditions.get("submitted_order_recorded") is True
        else 0,
        "open_position_count": 1 if q5_14_conditions.get("open_position_recorded") is True else 0,
        "closed_trade_count": 1 if q5_14_conditions.get("closed_trade_recorded") is True else 0,
        "postmortem_due_count": 1 if q5_14_conditions.get("postmortem_due_recorded") is True else 0,
        "blocking_unsafe_count": blocking_unsafe_count,
        "broker_write_allowed_count": _aggregate_count(gates, "broker_write_allowed_count"),
        "prediction_market_write_allowed_count": _aggregate_count(
            gates,
            "prediction_market_write_allowed_count",
        ),
        "crypto_perps_write_allowed_count": _aggregate_count(
            gates,
            "crypto_perps_write_allowed_count",
        ),
        "telegram_live_notifications_allowed_count": _aggregate_count(
            gates,
            "telegram_live_notifications_allowed_count",
        ),
        "live_endpoint_allowed_count": _aggregate_count(gates, "live_endpoint_allowed_count"),
        "live_capital_enabled_count": _aggregate_count(gates, "live_capital_enabled_count"),
        "phase7_proof_credit_allowed_count": 0,
        "risk_bad_state_probe_status": "covered_by_q5_3_check_script",
        "kill_switch_bad_state_probe_status": "covered_by_q5_4_check_script",
        "telegram_dashboard_parity_status": "covered_by_q5_10_q5_13_checks",
        "prediction_market_write_status": "disabled",
        "live_endpoint_status": "disabled",
    }
    certification_artifact["validation_errors"] = validate_phase5_certification(
        certification_artifact
    )
    if certification_artifact["validation_errors"]:
        certification_artifact["status"] = "error"
    return certification_artifact


def _validate_gate_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("schema_version") != PHASE5_ARTIFACT_SCHEMA_VERSION:
        errors.append("gate_schema_version_mismatch")
    if record.get("phase5_certification_schema_version") != PHASE5_CERTIFICATION_SCHEMA_VERSION:
        errors.append("gate_certification_schema_version_mismatch")
    if record.get("artifact_type") != "phase5_certification_gate":
        errors.append("gate_artifact_type_mismatch")
    if record.get("phase") != "Q5" or record.get("stage") != "Q5-15":
        errors.append("gate_phase_stage_mismatch")
    if record.get("source_stage") not in PHASE5_CERTIFICATION_REQUIRED_INPUT_STAGES:
        errors.append("gate_source_stage_invalid")
    if record.get("public_safe") is not True:
        errors.append("gate_not_public_safe")
    if record.get("event_log_required") is not True:
        errors.append("gate_event_log_not_required")
    if not isinstance(record.get("event_log_written"), bool):
        errors.append("gate_event_log_written_not_bool")
    if record.get("event_log_written") is True and not str(
        record.get("event_log_correlation_id") or ""
    ).strip():
        errors.append("gate_event_correlation_missing")
    if record.get("display_status") != record.get("backend_status"):
        errors.append("gate_display_backend_mismatch")
    if record.get("display_derived_from_backend") is not True:
        errors.append("gate_display_not_backend_derived")
    if record.get("ui_inferred_readiness") is not False:
        errors.append("gate_ui_inferred_readiness")
    if record.get("gate_passed") is True and record.get("backend_status") != "passed":
        errors.append("gate_passed_status_mismatch")
    if record.get("gate_passed") is not True and record.get("backend_status") != "blocked":
        errors.append("gate_blocked_status_mismatch")
    if record.get("phase7_proof_credit_allowed") is not False:
        errors.append("gate_phase7_credit_allowed")
    if record.get("phase5_test_trade_counted_for_phase7") is not False:
        errors.append("gate_phase5_trade_counted_for_phase7")
    for field in PHASE5_AUTHORITY_FIELDS:
        if record.get(field) is not False:
            errors.append(f"gate_authority_enabled:{field}")
    blocking_counts = record.get("blocking_unsafe_counts", {})
    if not isinstance(blocking_counts, dict):
        errors.append("gate_blocking_counts_not_dict")
    else:
        for field, value in blocking_counts.items():
            if field in PHASE5_CERTIFICATION_BLOCKING_COUNTS and int(value or 0) != 0:
                errors.append(f"gate_blocking_unsafe_count_nonzero:{field}")
    boundary = str(record.get("boundary") or "")
    if "cannot bypass Q5-14" not in boundary or "cannot enable live capital" not in boundary:
        errors.append("gate_boundary_weak")
    return sorted(set(errors))


def validate_phase5_certification(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "phase5_certification_schema_version",
        "artifact_type",
        "artifact_id",
        "phase",
        "stage",
        "status",
        "stage_status",
        "generated_at",
        "public_safe",
        "event_log_required",
        "event_log_written",
        "authority_ledger",
        "source_posture",
        "provenance",
        "boundary",
        "phase5_certified",
        "phase5_complete",
        "phase5_exit_gate",
        "phase6_handoff_allowed",
        "phase7_planning_allowed",
        "phase7_proof_credit_allowed",
        "q5_stage_count",
        "required_input_stage_count",
        "required_input_stages",
        "input_gate_count",
        "input_gate_passed_count",
        "input_gate_blocked_count",
        "gate_records",
        "certification_blockers",
        "certification_blocker_count",
        "paper_trade_drill_complete",
        "paper_trade_drill_exit_gate_passed",
        "submitted_paper_order_count",
        "open_position_count",
        "closed_trade_count",
        "postmortem_due_count",
        "blocking_unsafe_count",
        "phase7_proof_credit_allowed_count",
    }
    missing = sorted(required_fields - set(artifact))
    if missing:
        errors.append("certification_missing_fields:" + ",".join(missing))
    errors.extend(
        validate_phase5_artifact(
            artifact,
            expected_stage="Q5-15",
        )
    )
    if artifact.get("phase5_certification_schema_version") != PHASE5_CERTIFICATION_SCHEMA_VERSION:
        errors.append("certification_schema_version_mismatch")
    if artifact.get("artifact_type") != "phase5_certification":
        errors.append("certification_artifact_type_mismatch")
    if artifact.get("q5_stage_count") != PHASE5_TOTAL_STAGE_COUNT:
        errors.append("q5_stage_count_mismatch")
    if artifact.get("required_input_stage_count") != PHASE5_INPUT_STAGE_COUNT:
        errors.append("required_input_stage_count_mismatch")
    if list(artifact.get("required_input_stages", [])) != list(
        PHASE5_CERTIFICATION_REQUIRED_INPUT_STAGES
    ):
        errors.append("required_input_stages_mismatch")
    gates = artifact.get("gate_records", [])
    if not isinstance(gates, list):
        errors.append("gate_records_not_list")
        gates = []
    if artifact.get("input_gate_count") != len(gates):
        errors.append("input_gate_count_mismatch")
    if artifact.get("input_gate_count") != PHASE5_INPUT_STAGE_COUNT:
        errors.append("input_gate_count_not_required")
    gate_stage_order = [gate.get("source_stage") for gate in gates if isinstance(gate, dict)]
    if gate_stage_order != list(PHASE5_CERTIFICATION_REQUIRED_INPUT_STAGES):
        errors.append("gate_stage_order_mismatch")
    gate_passed_count = sum(1 for gate in gates if gate.get("gate_passed") is True)
    if artifact.get("input_gate_passed_count") != gate_passed_count:
        errors.append("input_gate_passed_count_mismatch")
    if artifact.get("input_gate_blocked_count") != len(gates) - gate_passed_count:
        errors.append("input_gate_blocked_count_mismatch")
    blockers = artifact.get("certification_blockers", [])
    if not isinstance(blockers, list):
        errors.append("certification_blockers_not_list")
        blockers = []
    if artifact.get("certification_blocker_count") != len(blockers):
        errors.append("certification_blocker_count_mismatch")
    for gate in gates:
        if not isinstance(gate, dict):
            errors.append("gate_record_not_dict")
            continue
        errors.extend(_validate_gate_record(gate))
    phase5_certified = artifact.get("phase5_certified") is True
    if phase5_certified:
        if blockers:
            errors.append("phase5_certified_with_blockers")
        if artifact.get("status") != "eligible":
            errors.append("phase5_certified_status_not_eligible")
        for field in (
            "phase5_complete",
            "phase5_exit_gate",
            "phase6_handoff_allowed",
            "phase7_planning_allowed",
            "paper_trade_drill_complete",
            "paper_trade_drill_exit_gate_passed",
        ):
            if artifact.get(field) is not True:
                errors.append(f"phase5_certified_missing_true:{field}")
        for field in (
            "submitted_paper_order_count",
            "open_position_count",
            "closed_trade_count",
            "postmortem_due_count",
        ):
            if int(artifact.get(field, 0) or 0) <= 0:
                errors.append(f"phase5_certified_missing_count:{field}")
    else:
        if artifact.get("status") != "blocked":
            errors.append("blocked_certification_status_not_blocked")
        if artifact.get("phase5_complete") is not False:
            errors.append("blocked_certification_phase5_complete")
        if artifact.get("phase5_exit_gate") is not False:
            errors.append("blocked_certification_exit_gate")
        if artifact.get("phase6_handoff_allowed") is not False:
            errors.append("blocked_certification_phase6_handoff")
        if artifact.get("phase7_planning_allowed") is not False:
            errors.append("blocked_certification_phase7_planning")
        if not blockers:
            errors.append("blocked_certification_without_blockers")
    if (
        artifact.get("paper_trade_drill_exit_gate_passed") is not True
        and "q5_14_exit_gate_not_passed" not in blockers
    ):
        errors.append("missing_q5_14_exit_gate_blocker")
    if (
        artifact.get("paper_trade_drill_complete") is not True
        and "q5_14_paper_trade_lifecycle_incomplete" not in blockers
    ):
        errors.append("missing_q5_14_lifecycle_blocker")
    if artifact.get("phase7_proof_credit_allowed") is not False:
        errors.append("phase7_proof_credit_allowed")
    if artifact.get("phase5_test_trades_count_for_phase7") is not False:
        errors.append("phase5_test_trades_count_for_phase7")
    if int(artifact.get("phase7_proof_credit_allowed_count", 0) or 0) != 0:
        errors.append("phase7_proof_credit_allowed_count_nonzero")
    for field in PHASE5_AUTHORITY_FIELDS:
        if artifact.get(field) is not False:
            errors.append(f"certification_authority_enabled:{field}")
    for field in PHASE5_CERTIFICATION_BLOCKING_COUNTS:
        if int(artifact.get(field, 0) or 0) != 0:
            errors.append(f"certification_blocking_count_nonzero:{field}")
    if int(artifact.get("blocking_unsafe_count", 0) or 0) != 0:
        errors.append("blocking_unsafe_count_nonzero")
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("certification_event_log_path_missing")
        if not str(artifact.get("event_log_correlation_id") or "").strip():
            errors.append("certification_event_log_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("certification_event_log_count_mismatch")
    boundary = str(artifact.get("boundary") or "")
    if (
        "cannot bypass Q5-14" not in boundary
        or "cannot call live endpoints" not in boundary
        or "cannot enable live capital" not in boundary
        or "cannot let Phase 5 test trades count toward Phase 7 proof" not in boundary
    ):
        errors.append("certification_boundary_weak")
    return sorted(set(errors))


def attach_phase5_certification_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(event_log_path or (_runtime_dir(settings) / PHASE5_CERTIFICATION_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE5_CERTIFICATION_EVENT_TYPE,
        PHASE5_CERTIFICATION_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "stage_status": output.get("stage_status"),
            "phase5_certified": output.get("phase5_certified"),
            "phase5_exit_gate": output.get("phase5_exit_gate"),
            "phase6_handoff_allowed": output.get("phase6_handoff_allowed"),
            "phase7_planning_allowed": output.get("phase7_planning_allowed"),
            "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
            "certification_blocker_count": output.get("certification_blocker_count"),
            "input_gate_passed_count": output.get("input_gate_passed_count"),
            "input_gate_blocked_count": output.get("input_gate_blocked_count"),
            "paper_trade_drill_complete": output.get("paper_trade_drill_complete"),
            "paper_trade_drill_exit_gate_passed": output.get(
                "paper_trade_drill_exit_gate_passed"
            ),
            "submitted_paper_order_count": output.get("submitted_paper_order_count"),
            "open_position_count": output.get("open_position_count"),
            "closed_trade_count": output.get("closed_trade_count"),
            "postmortem_due_count": output.get("postmortem_due_count"),
            "live_capital_enabled_count": output.get("live_capital_enabled_count"),
            "boundary": output.get("boundary"),
        },
    )
    output["recorded"] = True
    output["event_log_written"] = True
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = 1
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_created_at"] = entry.created_at
    output["validation_errors"] = validate_phase5_certification(output)
    if output["validation_errors"]:
        output["status"] = "error"
    return output, entry


def write_phase5_certification(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase5_certification_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase5_certification_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase5_certification(output)
        if output["validation_errors"]:
            output["status"] = "error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase5_certification(output)
    if output["validation_errors"]:
        output["status"] = "error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE5_CERTIFICATION_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "stage_status": output.get("stage_status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "phase5_certified": output.get("phase5_certified"),
        "phase5_exit_gate": output.get("phase5_exit_gate"),
        "phase6_handoff_allowed": output.get("phase6_handoff_allowed"),
        "phase7_planning_allowed": output.get("phase7_planning_allowed"),
        "certification_blocker_count": output.get("certification_blocker_count"),
        "input_gate_passed_count": output.get("input_gate_passed_count"),
        "input_gate_blocked_count": output.get("input_gate_blocked_count"),
        "paper_trade_drill_complete": output.get("paper_trade_drill_complete"),
        "paper_trade_drill_exit_gate_passed": output.get(
            "paper_trade_drill_exit_gate_passed"
        ),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
