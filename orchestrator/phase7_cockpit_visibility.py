"""Q7-15 public-safe Phase 7 Demo Proof cockpit visibility.

This stage exposes a backend-derived readout for the 30-day demo-proof
harness. It reads Q7 runtime artifacts, summarizes the proof state for
Mission Control, and keeps the visibility layer non-authoritative: it cannot
infer readiness from frontend state, grant proof credit, expose raw/private
payloads, or enable live capital.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.phase7_artifacts import (
    PHASE7_ARTIFACT_SCHEMA_VERSION,
    PHASE7_EVENT_TYPES,
    phase7_event_contract,
    phase7_proof_contract,
    phase7_provenance,
    phase7_source_posture,
)
from orchestrator.phase7_calendar_harness import PHASE7_CALENDAR_HARNESS_RUNTIME_ARTIFACT
from orchestrator.phase7_drawdown_risk_sentinel import (
    PHASE7_DRAWDOWN_RISK_SENTINEL_RUNTIME_ARTIFACT,
)
from orchestrator.phase7_guarded_alpaca_paper_submit import (
    PHASE7_GUARDED_ALPACA_SUBMIT_RUNTIME_ARTIFACT,
)
from orchestrator.phase7_maturity_tracker import PHASE7_MATURITY_TRACKER_RUNTIME_ARTIFACT
from orchestrator.phase7_override_detector import PHASE7_OVERRIDE_DETECTOR_RUNTIME_ARTIFACT
from orchestrator.phase7_performance_evaluator import (
    PHASE7_PERFORMANCE_EVALUATOR_RUNTIME_ARTIFACT,
)
from orchestrator.phase7_proof_lifecycle_monitor import (
    PHASE7_PROOF_LIFECYCLE_RUNTIME_ARTIFACT,
)
from orchestrator.phase7_proof_order_staging import PHASE7_PROOF_ORDER_STAGING_RUNTIME_ARTIFACT
from orchestrator.phase7_proof_postmortem_contract import (
    PHASE7_PROOF_POSTMORTEM_RUNTIME_ARTIFACT,
)
from orchestrator.phase7_qualified_setup_ledger import (
    PHASE7_QUALIFIED_SETUP_LEDGER_RUNTIME_ARTIFACT,
)
from orchestrator.phase7_readiness import (
    PHASE7_AUTHORITY_FLAGS,
    PHASE7_HARNESS_DAY_COUNT,
    PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
    PHASE7_UNSAFE_COUNT_FIELDS,
    PHASE7_WEEKLY_PROOF_TRADE_TARGET,
    PHASE7_READINESS_RUNTIME_ARTIFACT,
    phase7_authority_defaults,
    phase7_unsafe_counter_defaults,
)
from orchestrator.phase7_signal_funnel_evidence import (
    PHASE7_SIGNAL_FUNNEL_EVIDENCE_RUNTIME_ARTIFACT,
)
from orchestrator.phase7_test_mode_auto_approval import (
    PHASE7_TEST_MODE_AUTO_APPROVAL_RUNTIME_ARTIFACT,
)
from orchestrator.phase7_weekly_cadence import PHASE7_WEEKLY_CADENCE_RUNTIME_ARTIFACT


PHASE7_COCKPIT_VISIBILITY_SCHEMA_VERSION = 1
PHASE7_COCKPIT_VISIBILITY_RUNTIME_ARTIFACT = "phase7_cockpit_visibility.json"
PHASE7_COCKPIT_VISIBILITY_HISTORY = "phase7_cockpit_visibility_history.jsonl"
PHASE7_COCKPIT_VISIBILITY_EVENT_LOG = "phase7_cockpit_visibility_events.jsonl"
PHASE7_COCKPIT_VISIBILITY_EVENT_TYPE = PHASE7_EVENT_TYPES["visibility"]
PHASE7_COCKPIT_VISIBILITY_COMPONENT = "phase7_cockpit_visibility"

SOURCE_REFS: dict[str, str] = {
    "readiness": f"data/runtime/{PHASE7_READINESS_RUNTIME_ARTIFACT}",
    "calendar": f"data/runtime/{PHASE7_CALENDAR_HARNESS_RUNTIME_ARTIFACT}",
    "qualified_setup_ledger": f"data/runtime/{PHASE7_QUALIFIED_SETUP_LEDGER_RUNTIME_ARTIFACT}",
    "weekly_cadence": f"data/runtime/{PHASE7_WEEKLY_CADENCE_RUNTIME_ARTIFACT}",
    "auto_approval": f"data/runtime/{PHASE7_TEST_MODE_AUTO_APPROVAL_RUNTIME_ARTIFACT}",
    "proof_order_staging": f"data/runtime/{PHASE7_PROOF_ORDER_STAGING_RUNTIME_ARTIFACT}",
    "guarded_alpaca_submit": f"data/runtime/{PHASE7_GUARDED_ALPACA_SUBMIT_RUNTIME_ARTIFACT}",
    "proof_lifecycle": f"data/runtime/{PHASE7_PROOF_LIFECYCLE_RUNTIME_ARTIFACT}",
    "postmortem": f"data/runtime/{PHASE7_PROOF_POSTMORTEM_RUNTIME_ARTIFACT}",
    "performance": f"data/runtime/{PHASE7_PERFORMANCE_EVALUATOR_RUNTIME_ARTIFACT}",
    "drawdown": f"data/runtime/{PHASE7_DRAWDOWN_RISK_SENTINEL_RUNTIME_ARTIFACT}",
    "override": f"data/runtime/{PHASE7_OVERRIDE_DETECTOR_RUNTIME_ARTIFACT}",
    "signal_evidence": f"data/runtime/{PHASE7_SIGNAL_FUNNEL_EVIDENCE_RUNTIME_ARTIFACT}",
    "maturity": f"data/runtime/{PHASE7_MATURITY_TRACKER_RUNTIME_ARTIFACT}",
}

PHASE7_COCKPIT_VISIBILITY_BOUNDARY = (
    "Q7-15 exposes Phase 7 demo-proof cockpit visibility from backend "
    "artifacts only. It cannot infer readiness from the UI, cannot expose raw "
    "payloads, private payloads, local paths, secrets, broker identifiers, "
    "request bodies, receipts, or source payloads, cannot count Phase 5 test "
    "trades toward Phase 7 proof, cannot hide statistical immaturity, cannot "
    "grant Phase 7 proof credit, cannot call broker POST routes, cannot call "
    "Alpaca POST routes, cannot write prediction-market or crypto-perps "
    "orders, cannot mutate policy or strategies, cannot approve or reject "
    "individual proof trades, and cannot enable live capital."
)

PUBLIC_STATUS_FIELDS: tuple[str, ...] = (
    "schema_version",
    "phase7_cockpit_visibility_schema_version",
    "phase7_artifact_schema_version",
    "artifact_type",
    "artifact_id",
    "phase",
    "stage",
    "status",
    "stage_status",
    "visibility_state",
    "proof_state",
    "generated_at",
    "public_safe",
    "recorded",
    "backend_derived",
    "display_derived_from_backend",
    "dashboard_panel_enabled",
    "dashboard_uses_backend_status",
    "event_log_required",
    "event_log_written",
    "event_log_event_count",
    "validation_error_count",
    "source_artifact_count",
    "source_validation_error_count",
    "source_missing_count",
    "source_status_records",
    "phase7_harness_day_count",
    "completed_calendar_day_count",
    "phase7_30_day_run_complete",
    "proof_week_count",
    "current_proof_week_number",
    "weekly_proof_trade_target",
    "weekly_target_formula",
    "candidate_setup_count",
    "qualified_setup_count",
    "eligible_setup_count",
    "missed_qualified_setup_count",
    "missed_qualified_setup_unexplained_count",
    "staged_proof_order_count",
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
    "drawdown_cap_breached",
    "max_drawdown_fraction_observed",
    "risk_halt_active",
    "new_proof_trades_frozen",
    "override_count",
    "manual_trade_level_override_count",
    "sample_contaminated",
    "complete_decision_chain_count",
    "missing_decision_chain_count",
    "private_priors_only_proof_trade_count",
    "maturity_state",
    "mature_benchmark",
    "maturity_progress_fraction",
    "closed_trades_remaining_to_mature",
    "phase7_mature_benchmark_met",
    "phase7_mature_status_blocked",
    "phase7_statistically_immature",
    "phase7_statistical_immaturity_hidden",
    "phase7_certification_blocked_by_signal_evidence",
    "phase7_certification_blocked_by_maturity",
    "phase5_test_trades_count_for_phase7",
    "q6_deferred_learning_counts_as_proof",
    "phase7_proof_credit_allowed",
    "phase7_proof_credit_allowed_count",
    "proof_trade_credit_count",
    "live_capital_enabled",
    "live_capital_enabled_count",
    "broker_post_called_count",
    "alpaca_post_called_count",
    "external_broker_post_performed_count",
    "broker_write_allowed_count",
    "prediction_market_write_allowed_count",
    "crypto_perps_write_allowed_count",
    "live_endpoint_allowed_count",
    "phase5_test_trade_reuse_count",
    "ui_inferred_readiness_count",
    "unsafe_write_counter_total",
    "raw_payload_exposed_count",
    "private_payload_exposed_count",
    "local_path_exposed_count",
    "secret_ref_exposed_count",
    "broker_identifier_exposed_count",
    "q7_16_weekly_review_pack_stage_allowed",
    "recommended_next_stage",
    "blockers",
    "blocker_count",
    "boundary",
)

SOURCE_STATUS_REQUIRED_FIELDS: tuple[str, ...] = (
    "source_key",
    "source_stage",
    "source_status",
    "backend_status",
    "display_status",
    "display_derived_from_backend",
    "ui_inferred_readiness",
    "source_ref",
    "public_safe",
    "recorded",
    "event_log_written",
    "validation_error_count",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _repo_root(settings: Settings | None = None) -> Path:
    return _runtime_dir(settings).parent.parent


def _path(ref: str, settings: Settings | None = None) -> Path:
    return _repo_root(settings) / ref


def _read_json(ref: str, settings: Settings | None = None) -> dict[str, Any] | None:
    path = _path(ref, settings)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pick_int(*values: Any) -> int:
    for value in values:
        if value is None:
            continue
        return _int(value)
    return 0


def _pick_bool(*values: Any, default: bool = False) -> bool:
    for value in values:
        if isinstance(value, bool):
            return value
    return default


def _has_local_path(ref: str) -> bool:
    if ref.startswith("/") or ref.startswith("~"):
        return True
    return len(ref) > 2 and ref[1:3] == ":\\"


def _source_status_record(
    source_key: str,
    source_ref: str,
    artifact: dict[str, Any] | None,
) -> dict[str, Any]:
    source_status = str((artifact or {}).get("status") or "missing")
    return {
        "source_key": source_key,
        "source_stage": (artifact or {}).get("stage", "missing"),
        "source_status": source_status,
        "backend_status": source_status,
        "display_status": source_status,
        "display_derived_from_backend": True,
        "ui_inferred_readiness": False,
        "source_ref": source_ref,
        "public_safe": (artifact or {}).get("public_safe") is True,
        "recorded": artifact is not None and (artifact or {}).get("recorded") is True,
        "event_log_written": (artifact or {}).get("event_log_written") is True,
        "validation_error_count": len((artifact or {}).get("validation_errors", []) or []),
    }


def _provenance(source_refs: tuple[str, ...]) -> dict[str, Any]:
    provenance = phase7_provenance(source_refs)
    provenance["decision_chain_refs"] = [
        SOURCE_REFS["signal_evidence"],
        SOURCE_REFS["qualified_setup_ledger"],
    ]
    provenance["execution_evidence_refs"] = [
        SOURCE_REFS["guarded_alpaca_submit"],
        SOURCE_REFS["proof_lifecycle"],
        SOURCE_REFS["postmortem"],
        SOURCE_REFS["performance"],
    ]
    provenance["market_context_refs"] = [
        SOURCE_REFS["calendar"],
        SOURCE_REFS["qualified_setup_ledger"],
        SOURCE_REFS["weekly_cadence"],
    ]
    provenance["governance_refs"] = [
        SOURCE_REFS["drawdown"],
        SOURCE_REFS["override"],
        SOURCE_REFS["maturity"],
    ]
    provenance["proof_lifecycle_refs"] = [
        SOURCE_REFS["proof_order_staging"],
        SOURCE_REFS["guarded_alpaca_submit"],
        SOURCE_REFS["proof_lifecycle"],
    ]
    return provenance


def _public_status_from_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    output = {field: deepcopy(artifact.get(field)) for field in PUBLIC_STATUS_FIELDS if field in artifact}
    output["validation_error_count"] = len(artifact.get("validation_errors", []) or [])
    return output


def _refresh_validation(artifact: dict[str, Any]) -> dict[str, Any]:
    artifact.setdefault("validation_errors", [])
    artifact["public_status"] = _public_status_from_artifact(artifact)
    for _ in range(2):
        artifact["validation_errors"] = validate_phase7_cockpit_visibility(artifact)
        artifact["validation_error_count"] = len(artifact["validation_errors"])
        artifact["public_status"] = _public_status_from_artifact(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "blocked"
        artifact["stage_status"] = "phase7_demo_proof_visibility_blocked"
        artifact["visibility_state"] = "backend_derived_phase7_demo_proof_visibility_blocked"
        artifact["public_status"] = _public_status_from_artifact(artifact)
    return artifact


def phase7_cockpit_visibility_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE7_COCKPIT_VISIBILITY_RUNTIME_ARTIFACT,
        runtime / PHASE7_COCKPIT_VISIBILITY_HISTORY,
        runtime / PHASE7_COCKPIT_VISIBILITY_EVENT_LOG,
    )


def _weekly_count(cadence: dict[str, Any]) -> int:
    explicit = _int(cadence.get("weekly_cadence_record_count"))
    if explicit:
        return explicit
    records = cadence.get("weekly_cadence_records")
    if isinstance(records, list):
        return len(records)
    return 0


def _current_week(completed_days: int, proof_week_count: int) -> int:
    if completed_days <= 0:
        return 0
    return min(proof_week_count or 1, ((completed_days - 1) // 7) + 1)


def _forbidden_unsafe_count(artifact: dict[str, Any]) -> int:
    count_fields = (
        "broker_write_allowed_count",
        "prediction_market_write_allowed_count",
        "crypto_perps_write_allowed_count",
        "live_endpoint_allowed_count",
        "live_capital_enabled_count",
        "proof_trade_credit_count",
        "phase7_proof_credit_allowed_count",
        "manual_trade_level_override_count",
        "phase5_test_trade_reuse_count",
        "ui_inferred_readiness_count",
    )
    return sum(_int(artifact.get(field)) for field in count_fields)


def build_phase7_cockpit_visibility(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    sources = {key: _read_json(ref, settings) for key, ref in SOURCE_REFS.items()}
    source_status_records = [
        _source_status_record(key, SOURCE_REFS[key], sources[key]) for key in SOURCE_REFS
    ]
    source_missing_count = len(
        [record for record in source_status_records if record["source_status"] == "missing"]
    )
    source_validation_error_count = sum(
        record["validation_error_count"] for record in source_status_records
    )

    calendar = sources["calendar"] or {}
    ledger = sources["qualified_setup_ledger"] or {}
    cadence = sources["weekly_cadence"] or {}
    staging = sources["proof_order_staging"] or {}
    submit = sources["guarded_alpaca_submit"] or {}
    lifecycle = sources["proof_lifecycle"] or {}
    postmortem = sources["postmortem"] or {}
    performance = sources["performance"] or {}
    drawdown = sources["drawdown"] or {}
    override = sources["override"] or {}
    signal = sources["signal_evidence"] or {}
    maturity = sources["maturity"] or {}

    blockers = []
    if source_missing_count:
        blockers.append("phase7_cockpit_visibility_source_missing")
    if source_validation_error_count:
        blockers.append("phase7_cockpit_visibility_source_validation_errors")
    if maturity.get("q7_15_cockpit_visibility_stage_allowed") is not True:
        blockers.append("q7_15_cockpit_visibility_stage_not_allowed")
    if maturity.get("phase7_statistical_immaturity_hidden") is True:
        blockers.append("phase7_statistical_immaturity_hidden")
    if override.get("sample_contaminated") is True:
        blockers.append("phase7_override_sample_contaminated")

    completed_days = _pick_int(maturity.get("completed_calendar_day_count"))
    proof_week_count = _weekly_count(cadence)
    closed_trade_count = _pick_int(
        maturity.get("closed_proof_trade_count"),
        lifecycle.get("closed_proof_trade_count"),
    )
    paper_order_submitted_count = _pick_int(
        submit.get("paper_order_submitted_count"),
        lifecycle.get("paper_order_submitted_count"),
        lifecycle.get("source_submitted_paper_order_count"),
    )
    proof_trade_created_count = _pick_int(
        signal.get("source_proof_trade_count"),
        lifecycle.get("proof_trade_count"),
        closed_trade_count,
    )
    new_proof_trades_frozen = _pick_bool(
        drawdown.get("new_proof_trades_frozen"),
        override.get("new_proof_trades_frozen"),
        signal.get("new_proof_trades_frozen"),
        maturity.get("new_proof_trades_frozen"),
    )
    unsafe_counts = phase7_unsafe_counter_defaults()
    unsafe_counts.update(
        {
            "broker_post_called_count": _pick_int(submit.get("broker_post_called_count")),
            "alpaca_post_called_count": _pick_int(submit.get("alpaca_post_called_count")),
            "paper_order_submitted_count": paper_order_submitted_count,
            "proof_trade_created_count": proof_trade_created_count,
            "proof_trade_credit_count": 0,
            "phase7_proof_credit_allowed_count": 0,
            "manual_trade_level_override_count": _pick_int(
                override.get("manual_trade_level_override_count"),
                signal.get("manual_trade_level_override_count"),
            ),
            "phase5_test_trade_reuse_count": 0,
            "ui_inferred_readiness_count": 0,
        }
    )

    status = "visible" if not blockers else "blocked"
    stage_status = "phase7_demo_proof_visible" if not blockers else "phase7_demo_proof_visibility_blocked"
    proof_state = str(maturity.get("status") or "not_run")
    artifact = {
        "schema_version": PHASE7_COCKPIT_VISIBILITY_SCHEMA_VERSION,
        "phase7_cockpit_visibility_schema_version": PHASE7_COCKPIT_VISIBILITY_SCHEMA_VERSION,
        "phase7_artifact_schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "artifact_type": "cockpit_proof_visibility",
        "artifact_id": "phase7:q7-15:cockpit-proof-visibility",
        "phase": "Q7",
        "stage": "Q7-15",
        "status": status,
        "stage_status": stage_status,
        "visibility_state": f"backend_derived_{stage_status}",
        "proof_state": proof_state,
        "generated_at": generated_at,
        "public_safe": True,
        "recorded": False,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_event_count": 0,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "runtime_artifact_path": None,
        "history_log_path": None,
        "event_contract": phase7_event_contract("visibility"),
        "authority_ledger": {
            "authority_schema_version": PHASE7_COCKPIT_VISIBILITY_SCHEMA_VERSION,
            "stage": "Q7-15",
            "authority_field_count": len(PHASE7_AUTHORITY_FLAGS),
            "explicit_authority_grant_count": 0,
            "explicit_authority_grants": [],
            "q7_16_weekly_review_pack_stage_allowed": not blockers,
            "visibility_only": True,
            **phase7_authority_defaults(),
            "boundary": PHASE7_COCKPIT_VISIBILITY_BOUNDARY,
        },
        "proof_contract": phase7_proof_contract(),
        "source_posture": phase7_source_posture(),
        "provenance": _provenance(tuple(SOURCE_REFS.values())),
        "boundary": PHASE7_COCKPIT_VISIBILITY_BOUNDARY,
        **phase7_authority_defaults(),
        **unsafe_counts,
        "backend_derived": True,
        "display_derived_from_backend": True,
        "dashboard_panel_enabled": True,
        "dashboard_uses_backend_status": True,
        "source_artifact_count": len(source_status_records),
        "source_validation_error_count": source_validation_error_count,
        "source_missing_count": source_missing_count,
        "source_status_records": source_status_records,
        "phase7_harness_day_count": _pick_int(
            maturity.get("phase7_harness_day_count"),
            calendar.get("phase7_harness_day_count"),
            PHASE7_HARNESS_DAY_COUNT,
        ),
        "completed_calendar_day_count": completed_days,
        "phase7_30_day_run_complete": maturity.get("phase7_30_day_run_complete") is True,
        "proof_week_count": proof_week_count,
        "current_proof_week_number": _current_week(completed_days, proof_week_count),
        "weekly_proof_trade_target": _pick_int(
            cadence.get("weekly_proof_trade_target"),
            calendar.get("weekly_proof_trade_target"),
            PHASE7_WEEKLY_PROOF_TRADE_TARGET,
        ),
        "weekly_target_formula": cadence.get(
            "weekly_target_formula",
            "min(3, qualified_setup_count)",
        ),
        "candidate_setup_count": _pick_int(ledger.get("candidate_setup_record_count")),
        "qualified_setup_count": _pick_int(
            ledger.get("qualified_setup_count"),
            cadence.get("qualified_setup_count"),
        ),
        "eligible_setup_count": _pick_int(
            ledger.get("eligible_setup_count"),
            cadence.get("eligible_setup_count"),
        ),
        "missed_qualified_setup_count": _pick_int(
            cadence.get("missed_qualified_setup_count")
        ),
        "missed_qualified_setup_unexplained_count": _pick_int(
            cadence.get("missed_qualified_setup_unexplained_count")
        ),
        "staged_proof_order_count": _pick_int(staging.get("staged_order_count")),
        "submitted_paper_order_count": _pick_int(
            submit.get("submitted_paper_order_count"),
            lifecycle.get("source_submitted_paper_order_count"),
        ),
        "broker_receipt_count": _pick_int(
            submit.get("broker_receipt_record_count"),
            lifecycle.get("broker_submit_receipt_created_count"),
        ),
        "mirrored_submitted_order_count": _pick_int(
            lifecycle.get("mirrored_submitted_order_count"),
            submit.get("mirrored_submitted_order_count"),
        ),
        "open_position_count": _pick_int(lifecycle.get("open_position_count")),
        "closed_proof_trade_count": closed_trade_count,
        "postmortem_due_count": _pick_int(
            postmortem.get("postmortem_due_count"),
            lifecycle.get("postmortem_due_count"),
        ),
        "postmortem_missing_count": _pick_int(postmortem.get("postmortem_missing_count")),
        "postmortem_reviewed_count": _pick_int(postmortem.get("postmortem_reviewed_count")),
        "expectancy_after_costs_gbp": _float_or_none(
            performance.get("expectancy_after_costs_gbp")
        ),
        "expectancy_after_costs_positive": (
            performance.get("expectancy_after_costs_positive") is True
        ),
        "evaluated_trade_count": _pick_int(performance.get("evaluated_trade_count")),
        "drawdown_state": drawdown.get("drawdown_state", "unknown"),
        "drawdown_within_cap": drawdown.get("drawdown_within_cap") is True,
        "drawdown_cap_breached": drawdown.get("drawdown_cap_breached") is True,
        "max_drawdown_fraction_observed": _float_or_none(
            drawdown.get("max_drawdown_fraction_observed")
        ),
        "risk_halt_active": drawdown.get("risk_halt_active") is True,
        "new_proof_trades_frozen": new_proof_trades_frozen,
        "override_count": _pick_int(override.get("override_count")),
        "manual_trade_level_override_count": unsafe_counts[
            "manual_trade_level_override_count"
        ],
        "sample_contaminated": override.get("sample_contaminated") is True,
        "complete_decision_chain_count": _pick_int(signal.get("complete_decision_chain_count")),
        "missing_decision_chain_count": _pick_int(signal.get("missing_decision_chain_count")),
        "private_priors_only_proof_trade_count": _pick_int(
            signal.get("private_priors_only_proof_trade_count")
        ),
        "maturity_state": maturity.get("maturity_state", "no_sample"),
        "mature_benchmark": _pick_int(
            maturity.get("mature_benchmark"),
            PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
        ),
        "maturity_progress_fraction": _float_or_none(
            maturity.get("maturity_progress_fraction")
        ),
        "closed_trades_remaining_to_mature": _pick_int(
            maturity.get("closed_trades_remaining_to_mature"),
            PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
        ),
        "phase7_mature_benchmark_met": (
            maturity.get("phase7_mature_benchmark_met") is True
        ),
        "phase7_mature_status_blocked": (
            maturity.get("phase7_mature_status_blocked") is True
        ),
        "phase7_statistically_immature": (
            maturity.get("phase7_statistically_immature") is True
        ),
        "phase7_statistical_immaturity_hidden": (
            maturity.get("phase7_statistical_immaturity_hidden") is True
        ),
        "phase7_certification_blocked_by_signal_evidence": (
            signal.get("phase7_certification_blocked_by_signal_evidence") is True
            or maturity.get("phase7_certification_blocked_by_signal_evidence") is True
        ),
        "phase7_certification_blocked_by_maturity": (
            maturity.get("phase7_certification_blocked_by_maturity") is True
        ),
        "phase5_test_trades_count_for_phase7": False,
        "q6_deferred_learning_counts_as_proof": False,
        "phase7_proof_credit_allowed": False,
        "live_capital_enabled": False,
        "external_broker_post_performed_count": _pick_int(
            submit.get("external_broker_post_performed_count"),
            lifecycle.get("external_broker_post_performed_count"),
        ),
        "broker_write_allowed_count": 0,
        "prediction_market_write_allowed_count": 0,
        "crypto_perps_write_allowed_count": 0,
        "live_endpoint_allowed_count": 0,
        "unsafe_write_counter_total": 0,
        "raw_payload_exposed_count": 0,
        "private_payload_exposed_count": 0,
        "local_path_exposed_count": 0,
        "secret_ref_exposed_count": 0,
        "broker_identifier_exposed_count": 0,
        "q7_16_weekly_review_pack_stage_allowed": not blockers,
        "recommended_next_stage": "Q7-16 Weekly Review Pack",
        "blockers": sorted(set(blockers)),
        "blocker_count": len(set(blockers)),
    }
    artifact["unsafe_write_counter_total"] = _forbidden_unsafe_count(artifact)
    return _refresh_validation(artifact)


def _public_safety_errors(payload: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            lowered = str(key).lower()
            if lowered in {
                "raw_payload",
                "private_payload",
                "request_body",
                "receipt_payload",
                "broker_order_id",
                "external_order_id",
                "fill_id",
            }:
                errors.append(f"public_forbidden_key:{path}.{key}")
            errors.extend(_public_safety_errors(value, f"{path}.{key}"))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            errors.extend(_public_safety_errors(value, f"{path}[{index}]"))
    elif isinstance(payload, str):
        lowered = payload.lower()
        if _has_local_path(payload):
            errors.append(f"public_local_path:{path}")
        if (
            "api_key" in lowered
            or "bearer " in lowered
            or "secret_" in lowered
            or "token_" in lowered
            or "token=" in lowered
            or "secret=" in lowered
        ):
            errors.append(f"public_secret_ref:{path}")
        if any(
            marker in lowered
            for marker in ("broker_order_id", "external_order_id", "fill_id")
        ):
            errors.append(f"public_broker_identifier:{path}")
    return errors


def validate_phase7_cockpit_visibility(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = set(PUBLIC_STATUS_FIELDS) | {
        "event_contract",
        "authority_ledger",
        "proof_contract",
        "source_posture",
        "provenance",
        "public_status",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("phase7_cockpit_visibility_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PHASE7_COCKPIT_VISIBILITY_SCHEMA_VERSION:
        errors.append("phase7_cockpit_visibility_schema_version_mismatch")
    if artifact.get("phase7_artifact_schema_version") != PHASE7_ARTIFACT_SCHEMA_VERSION:
        errors.append("phase7_cockpit_visibility_artifact_schema_version_mismatch")
    if artifact.get("artifact_type") != "cockpit_proof_visibility":
        errors.append("phase7_cockpit_visibility_artifact_type_mismatch")
    if artifact.get("phase") != "Q7" or artifact.get("stage") != "Q7-15":
        errors.append("phase7_cockpit_visibility_phase_stage_mismatch")
    if artifact.get("status") not in {"visible", "blocked"}:
        errors.append("phase7_cockpit_visibility_status_invalid")
    if artifact.get("stage_status") not in {
        "phase7_demo_proof_visible",
        "phase7_demo_proof_visibility_blocked",
    }:
        errors.append("phase7_cockpit_visibility_stage_status_invalid")
    if artifact.get("public_safe") is not True:
        errors.append("phase7_cockpit_visibility_not_public_safe")
    if artifact.get("event_log_required") is not True:
        errors.append("phase7_cockpit_visibility_event_log_not_required")
    if artifact.get("backend_derived") is not True:
        errors.append("phase7_cockpit_visibility_not_backend_derived")
    if artifact.get("display_derived_from_backend") is not True:
        errors.append("phase7_cockpit_visibility_display_not_backend_derived")
    if artifact.get("dashboard_uses_backend_status") is not True:
        errors.append("phase7_cockpit_visibility_dashboard_not_backend_derived")
    if artifact.get("ui_inferred_readiness_count") != 0:
        errors.append("phase7_cockpit_visibility_ui_inferred_readiness")
    if not str(artifact.get("visibility_state", "")).startswith("backend_derived_"):
        errors.append("phase7_cockpit_visibility_state_not_backend_derived")

    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("phase7_cockpit_visibility_blockers_not_list")
        blockers = []
    if artifact.get("blocker_count") != len(blockers):
        errors.append("phase7_cockpit_visibility_blocker_count_mismatch")
    if artifact.get("status") == "visible":
        if blockers:
            errors.append("phase7_cockpit_visibility_visible_with_blockers")
        if artifact.get("q7_16_weekly_review_pack_stage_allowed") is not True:
            errors.append("q7_16_weekly_review_not_allowed")
    if artifact.get("status") == "blocked":
        if artifact.get("q7_16_weekly_review_pack_stage_allowed") is not False:
            errors.append("q7_16_weekly_review_allowed_while_blocked")

    source_records = artifact.get("source_status_records", [])
    if not isinstance(source_records, list) or not source_records:
        errors.append("phase7_cockpit_visibility_source_records_missing")
        source_records = []
    if artifact.get("source_artifact_count") != len(source_records):
        errors.append("phase7_cockpit_visibility_source_count_mismatch")
    source_validation_error_count = 0
    source_missing_count = 0
    for record in source_records:
        if not isinstance(record, dict):
            errors.append("phase7_cockpit_visibility_source_record_invalid")
            continue
        missing_record = sorted(set(SOURCE_STATUS_REQUIRED_FIELDS) - set(record))
        if missing_record:
            errors.append(
                "phase7_cockpit_visibility_source_record_missing:"
                + ",".join(missing_record)
            )
        if record.get("display_status") != record.get("backend_status"):
            errors.append("phase7_cockpit_visibility_source_display_backend_mismatch")
        if record.get("display_derived_from_backend") is not True:
            errors.append("phase7_cockpit_visibility_source_display_not_backend_derived")
        if record.get("ui_inferred_readiness") is not False:
            errors.append("phase7_cockpit_visibility_source_ui_inferred")
        source_ref = str(record.get("source_ref", ""))
        if not source_ref.startswith("data/runtime/"):
            errors.append("phase7_cockpit_visibility_source_ref_invalid")
        if _has_local_path(source_ref):
            errors.append("phase7_cockpit_visibility_source_ref_local_path")
        source_validation_error_count += _int(record.get("validation_error_count"))
        if record.get("source_status") == "missing":
            source_missing_count += 1
    if artifact.get("source_validation_error_count") != source_validation_error_count:
        errors.append("phase7_cockpit_visibility_source_validation_count_mismatch")
    if artifact.get("source_missing_count") != source_missing_count:
        errors.append("phase7_cockpit_visibility_source_missing_count_mismatch")

    if artifact.get("phase7_harness_day_count") != PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_cockpit_visibility_day_count_mismatch")
    if artifact.get("weekly_proof_trade_target") != PHASE7_WEEKLY_PROOF_TRADE_TARGET:
        errors.append("phase7_cockpit_visibility_weekly_target_mismatch")
    if artifact.get("mature_benchmark") != PHASE7_MATURE_CLOSED_TRADE_BENCHMARK:
        errors.append("phase7_cockpit_visibility_maturity_benchmark_mismatch")
    if _int(artifact.get("closed_proof_trade_count")) > _int(
        artifact.get("submitted_paper_order_count")
    ):
        errors.append("phase7_cockpit_visibility_closed_gt_submitted")
    if _int(artifact.get("closed_proof_trade_count")) > _int(
        artifact.get("broker_receipt_count")
    ) and _int(artifact.get("broker_receipt_count")) > 0:
        errors.append("phase7_cockpit_visibility_closed_gt_receipts")
    if _int(artifact.get("completed_calendar_day_count")) > PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_cockpit_visibility_completed_days_invalid")
    if artifact.get("phase7_statistical_immaturity_hidden") is not False:
        errors.append("phase7_cockpit_visibility_hidden_immaturity")
    if (
        artifact.get("phase7_mature_benchmark_met") is False
        and artifact.get("phase7_mature_status_blocked") is not True
    ):
        errors.append("phase7_cockpit_visibility_immature_not_blocked")
    if artifact.get("sample_contaminated") is True:
        errors.append("phase7_cockpit_visibility_sample_contaminated")
    if artifact.get("drawdown_cap_breached") is True and artifact.get("new_proof_trades_frozen") is not True:
        errors.append("phase7_cockpit_visibility_drawdown_without_freeze")

    for field in PHASE7_AUTHORITY_FLAGS:
        if artifact.get(field) is not False:
            errors.append(f"phase7_cockpit_visibility_authority_enabled:{field}")
    ledger = artifact.get("authority_ledger", {})
    if not isinstance(ledger, dict):
        errors.append("phase7_cockpit_visibility_authority_ledger_missing")
        ledger = {}
    if ledger.get("stage") != "Q7-15":
        errors.append("phase7_cockpit_visibility_authority_stage_mismatch")
    if ledger.get("authority_field_count") != len(PHASE7_AUTHORITY_FLAGS):
        errors.append("phase7_cockpit_visibility_authority_count_mismatch")
    if ledger.get("explicit_authority_grant_count") != 0:
        errors.append("phase7_cockpit_visibility_authority_grant_nonzero")
    for field in PHASE7_AUTHORITY_FLAGS:
        if ledger.get(field) is not False:
            errors.append(f"phase7_cockpit_visibility_ledger_authority_enabled:{field}")

    for field in (
        "phase5_test_trades_count_for_phase7",
        "q6_deferred_learning_counts_as_proof",
        "phase7_proof_credit_allowed",
        "live_capital_enabled",
    ):
        if artifact.get(field) is not False:
            errors.append(f"phase7_cockpit_visibility_forbidden:{field}")
    for count_field in (
        "broker_write_allowed_count",
        "prediction_market_write_allowed_count",
        "crypto_perps_write_allowed_count",
        "live_endpoint_allowed_count",
        "live_capital_enabled_count",
        "proof_trade_credit_count",
        "phase7_proof_credit_allowed_count",
        "phase5_test_trade_reuse_count",
        "ui_inferred_readiness_count",
    ):
        if _int(artifact.get(count_field)) != 0:
            errors.append(f"phase7_cockpit_visibility_count_nonzero:{count_field}")
    if artifact.get("unsafe_write_counter_total") != _forbidden_unsafe_count(artifact):
        errors.append("phase7_cockpit_visibility_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("phase7_cockpit_visibility_unsafe_total_nonzero")
    for count_field in PHASE7_UNSAFE_COUNT_FIELDS:
        if count_field not in artifact:
            errors.append(f"phase7_cockpit_visibility_unsafe_count_missing:{count_field}")

    for exposure_count in (
        "raw_payload_exposed_count",
        "private_payload_exposed_count",
        "local_path_exposed_count",
        "secret_ref_exposed_count",
        "broker_identifier_exposed_count",
    ):
        if artifact.get(exposure_count) != 0:
            errors.append(f"phase7_cockpit_visibility_exposure_count_nonzero:{exposure_count}")

    public_status = artifact.get("public_status")
    if not isinstance(public_status, dict):
        errors.append("phase7_cockpit_visibility_public_status_missing")
    else:
        extra = sorted(set(public_status) - set(PUBLIC_STATUS_FIELDS))
        if extra:
            errors.append(
                "phase7_cockpit_visibility_public_status_extra_fields:"
                + ",".join(extra)
            )
        for field in PUBLIC_STATUS_FIELDS:
            if field == "validation_error_count":
                continue
            if field in artifact and public_status.get(field) != artifact.get(field):
                errors.append(f"phase7_cockpit_visibility_public_status_mismatch:{field}")
        errors.extend(_public_safety_errors(public_status))

    proof_contract = artifact.get("proof_contract", {})
    if not isinstance(proof_contract, dict):
        errors.append("phase7_cockpit_visibility_proof_contract_missing")
        proof_contract = {}
    if proof_contract.get("harness_day_count") != PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_cockpit_visibility_proof_contract_day_count_mismatch")
    if proof_contract.get("phase5_test_trade_reuse_allowed") is not False:
        errors.append("phase7_cockpit_visibility_phase5_reuse_allowed")
    source_posture = artifact.get("source_posture", {})
    if not isinstance(source_posture, dict):
        errors.append("phase7_cockpit_visibility_source_posture_missing")
        source_posture = {}
    if source_posture.get("preference_mcp_source_quorum_credit_allowed") is not False:
        errors.append("phase7_cockpit_visibility_preference_quorum_credit_allowed")
    provenance = artifact.get("provenance", {})
    if not isinstance(provenance, dict):
        errors.append("phase7_cockpit_visibility_provenance_missing")
        provenance = {}
    for ref in provenance.get("source_refs", []) or []:
        ref_text = str(ref)
        lowered = ref_text.lower()
        if _has_local_path(ref_text):
            errors.append("phase7_cockpit_visibility_provenance_local_path_leak")
        if "api_key" in lowered or "secret" in lowered or "token" in lowered:
            errors.append("phase7_cockpit_visibility_provenance_secret_ref_leak")
    for field in (
        "raw_secret_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "broker_identifier_exposed",
    ):
        if provenance.get(field) is not False:
            errors.append(f"phase7_cockpit_visibility_provenance_exposure:{field}")
    event_contract = artifact.get("event_contract", {})
    if not isinstance(event_contract, dict):
        errors.append("phase7_cockpit_visibility_event_contract_missing")
        event_contract = {}
    if event_contract.get("event_type") != PHASE7_COCKPIT_VISIBILITY_EVENT_TYPE:
        errors.append("phase7_cockpit_visibility_event_contract_type_mismatch")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "from backend artifacts only",
        "cannot infer readiness from the UI",
        "cannot expose raw payloads",
        "cannot count Phase 5 test trades toward Phase 7 proof",
        "cannot hide statistical immaturity",
        "cannot grant Phase 7 proof credit",
        "cannot enable live capital",
    ):
        if phrase not in boundary:
            errors.append("phase7_cockpit_visibility_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("phase7_cockpit_visibility_event_log_path_missing")
        if not artifact.get("event_log_correlation_id"):
            errors.append("phase7_cockpit_visibility_event_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("phase7_cockpit_visibility_event_log_count_mismatch")
    return sorted(set(errors))


def attach_phase7_cockpit_visibility_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(event_log_path or (_runtime_dir(settings) / PHASE7_COCKPIT_VISIBILITY_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE7_COCKPIT_VISIBILITY_EVENT_TYPE,
        PHASE7_COCKPIT_VISIBILITY_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "stage_status": output.get("stage_status"),
            "visibility_state": output.get("visibility_state"),
            "backend_derived": output.get("backend_derived"),
            "ui_inferred_readiness_count": output.get("ui_inferred_readiness_count"),
            "completed_calendar_day_count": output.get("completed_calendar_day_count"),
            "proof_week_count": output.get("proof_week_count"),
            "qualified_setup_count": output.get("qualified_setup_count"),
            "submitted_paper_order_count": output.get("submitted_paper_order_count"),
            "closed_proof_trade_count": output.get("closed_proof_trade_count"),
            "mature_benchmark": output.get("mature_benchmark"),
            "phase7_mature_benchmark_met": output.get("phase7_mature_benchmark_met"),
            "phase7_statistical_immaturity_hidden": output.get(
                "phase7_statistical_immaturity_hidden"
            ),
            "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
            "live_capital_enabled": output.get("live_capital_enabled"),
            "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
            "boundary": output.get("boundary"),
        },
    )
    output["recorded"] = True
    output["event_log_written"] = True
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = 1
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_created_at"] = entry.created_at
    output = _refresh_validation(output)
    return output, entry


def write_phase7_cockpit_visibility(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase7_cockpit_visibility_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase7_cockpit_visibility_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output = _refresh_validation(output)
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output = _refresh_validation(output)
    output_path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_record = {
        "schema_version": PHASE7_COCKPIT_VISIBILITY_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "stage_status": output.get("stage_status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "backend_derived": output.get("backend_derived"),
        "ui_inferred_readiness_count": output.get("ui_inferred_readiness_count"),
        "completed_calendar_day_count": output.get("completed_calendar_day_count"),
        "proof_week_count": output.get("proof_week_count"),
        "qualified_setup_count": output.get("qualified_setup_count"),
        "submitted_paper_order_count": output.get("submitted_paper_order_count"),
        "closed_proof_trade_count": output.get("closed_proof_trade_count"),
        "mature_benchmark": output.get("mature_benchmark"),
        "maturity_progress_fraction": output.get("maturity_progress_fraction"),
        "phase7_mature_benchmark_met": output.get("phase7_mature_benchmark_met"),
        "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
        "live_capital_enabled": output.get("live_capital_enabled"),
        "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
        "blocker_count": output.get("blocker_count"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output


def phase7_cockpit_visibility_public_status(settings: Settings | None = None) -> dict[str, Any]:
    output_path, _, _ = phase7_cockpit_visibility_paths(settings)
    artifact = None
    if output_path.exists():
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        artifact = payload if isinstance(payload, dict) else None
    artifact = artifact or build_phase7_cockpit_visibility(settings=settings)
    validation_errors = validate_phase7_cockpit_visibility(artifact)
    public_status = _public_status_from_artifact(artifact)
    public_status["validation_error_count"] = len(validation_errors)
    return public_status
