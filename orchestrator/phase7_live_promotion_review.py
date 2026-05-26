"""Q7-18 Phase 7 live-promotion review flow.

This stage prepares a public-safe, read-only live-promotion review packet after
Phase 7 certification. It is deliberately fail-closed: the packet cannot be
created before Q7-17 certifies, and Q7-18 never loads live credentials, enables
live capital, submits broker requests, or approves live promotion by itself.
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
    validate_phase7_artifact,
)
from orchestrator.phase7_certification import (
    PHASE7_CERTIFICATION_RUNTIME_ARTIFACT,
    build_phase7_certification,
    validate_phase7_certification,
    write_phase7_certification,
)
from orchestrator.phase7_cockpit_visibility import (
    PHASE7_COCKPIT_VISIBILITY_RUNTIME_ARTIFACT,
)
from orchestrator.phase7_drawdown_risk_sentinel import (
    PHASE7_DRAWDOWN_RISK_SENTINEL_RUNTIME_ARTIFACT,
)
from orchestrator.phase7_maturity_tracker import PHASE7_MATURITY_TRACKER_RUNTIME_ARTIFACT
from orchestrator.phase7_override_detector import PHASE7_OVERRIDE_DETECTOR_RUNTIME_ARTIFACT
from orchestrator.phase7_performance_evaluator import (
    PHASE7_PERFORMANCE_EVALUATOR_RUNTIME_ARTIFACT,
)
from orchestrator.phase7_proof_lifecycle_monitor import (
    PHASE7_PROOF_LIFECYCLE_RUNTIME_ARTIFACT,
)
from orchestrator.phase7_proof_postmortem_contract import (
    PHASE7_PROOF_POSTMORTEM_RUNTIME_ARTIFACT,
)
from orchestrator.phase7_readiness import (
    PHASE7_AUTHORITY_FLAGS,
    PHASE7_HARNESS_DAY_COUNT,
    PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
    PHASE7_UNSAFE_COUNT_FIELDS,
    phase7_authority_defaults,
    phase7_unsafe_counter_defaults,
)
from orchestrator.phase7_signal_funnel_evidence import (
    PHASE7_SIGNAL_FUNNEL_EVIDENCE_RUNTIME_ARTIFACT,
)
from orchestrator.phase7_weekly_review_pack import (
    PHASE7_WEEKLY_REVIEW_PACK_RUNTIME_ARTIFACT,
)


PHASE7_LIVE_PROMOTION_REVIEW_SCHEMA_VERSION = 1
PHASE7_LIVE_PROMOTION_REVIEW_RUNTIME_ARTIFACT = "phase7_live_promotion_review.json"
PHASE7_LIVE_PROMOTION_REVIEW_HISTORY = "phase7_live_promotion_review_history.jsonl"
PHASE7_LIVE_PROMOTION_REVIEW_EVENT_LOG = "phase7_live_promotion_review_events.jsonl"
PHASE7_LIVE_PROMOTION_REVIEW_EVENT_TYPE = PHASE7_EVENT_TYPES["live_promotion"]
PHASE7_LIVE_PROMOTION_REVIEW_COMPONENT = "phase7_live_promotion_review"
PHASE7_LIVE_PROMOTION_COOLING_OFF_HOURS = 72

SOURCE_REFS: dict[str, str] = {
    "certification": f"data/runtime/{PHASE7_CERTIFICATION_RUNTIME_ARTIFACT}",
    "cockpit_visibility": f"data/runtime/{PHASE7_COCKPIT_VISIBILITY_RUNTIME_ARTIFACT}",
    "weekly_review": f"data/runtime/{PHASE7_WEEKLY_REVIEW_PACK_RUNTIME_ARTIFACT}",
    "proof_lifecycle": f"data/runtime/{PHASE7_PROOF_LIFECYCLE_RUNTIME_ARTIFACT}",
    "postmortem": f"data/runtime/{PHASE7_PROOF_POSTMORTEM_RUNTIME_ARTIFACT}",
    "performance": f"data/runtime/{PHASE7_PERFORMANCE_EVALUATOR_RUNTIME_ARTIFACT}",
    "drawdown": f"data/runtime/{PHASE7_DRAWDOWN_RISK_SENTINEL_RUNTIME_ARTIFACT}",
    "override": f"data/runtime/{PHASE7_OVERRIDE_DETECTOR_RUNTIME_ARTIFACT}",
    "signal_evidence": f"data/runtime/{PHASE7_SIGNAL_FUNNEL_EVIDENCE_RUNTIME_ARTIFACT}",
    "maturity": f"data/runtime/{PHASE7_MATURITY_TRACKER_RUNTIME_ARTIFACT}",
}

PHASE7_LIVE_PROMOTION_REVIEW_BOUNDARY = (
    "Q7-18 prepares Ramin's structured live-promotion review packet only after "
    "Q7-17 Phase 7 certification. It can summarize Phase 7 evidence, maturity "
    "state, drawdown, overrides, postmortems, source health, operational "
    "incidents, cooling-off requirements, and later explicit approval "
    "requirements, but it cannot draft an active promotion packet before "
    "certification, cannot approve live promotion, cannot load live "
    "credentials, cannot enable live capital, cannot call broker POST routes, "
    "cannot call Alpaca POST routes, cannot write prediction-market or "
    "crypto-perps orders, cannot bypass the cooling-off period, cannot count "
    "Phase 5 test trades toward Phase 7 proof, cannot grant Phase 7 proof "
    "credit, cannot infer readiness from the UI, and cannot expose raw "
    "payloads, private payloads, local paths, secrets, broker identifiers, "
    "request bodies, receipts, or source payloads."
)

PHASE7_LIVE_PROMOTION_REVIEW_SECTIONS: tuple[str, ...] = (
    "phase7_certification_summary",
    "thirty_day_operational_result",
    "maturity_and_sample_size",
    "drawdown_and_risk",
    "override_and_clean_sample",
    "postmortems",
    "source_signal_chain",
    "weekly_review_notes",
    "operational_incidents",
    "cooling_off_and_approval_requirements",
    "live_credential_and_capital_lockout",
)

PUBLIC_STATUS_FIELDS: tuple[str, ...] = (
    "schema_version",
    "phase7_live_promotion_review_schema_version",
    "phase7_artifact_schema_version",
    "artifact_type",
    "artifact_id",
    "phase",
    "stage",
    "status",
    "stage_status",
    "live_promotion_review_state",
    "generated_at",
    "public_safe",
    "recorded",
    "event_log_required",
    "event_log_written",
    "event_log_event_count",
    "validation_error_count",
    "source_artifact_count",
    "source_missing_count",
    "source_validation_error_count",
    "source_certification_status",
    "source_certification_stage_status",
    "phase7_demo_proof_certified",
    "phase7_demo_proof_exit_gate",
    "phase7_30_day_operational_result_clean",
    "phase7_30_day_operational_result_preserved",
    "phase7_30_day_run_complete",
    "completed_calendar_day_count",
    "phase7_harness_day_count",
    "proof_week_count",
    "weekly_review_packet_created_count",
    "qualified_setup_count",
    "evaluated_trade_count",
    "expectancy_after_costs_positive",
    "drawdown_within_cap",
    "drawdown_cap_breached",
    "risk_halt_active",
    "manual_trade_level_override_count",
    "sample_contaminated",
    "closed_proof_trade_count",
    "postmortem_missing_count",
    "source_signal_chains_complete",
    "maturity_state",
    "maturity_classification",
    "mature_benchmark",
    "phase7_mature_benchmark_met",
    "phase7_statistically_immature",
    "phase7_statistical_immaturity_hidden",
    "certification_blocker_count",
    "certification_blockers",
    "q7_18_live_promotion_review_stage_allowed",
    "live_promotion_review_packet_draft_allowed",
    "live_promotion_review_packet_created",
    "live_promotion_review_packet_section_count",
    "cooling_off_required",
    "cooling_off_period_hours",
    "cooling_off_started_at",
    "cooling_off_ends_at",
    "cooling_off_complete",
    "live_promotion_approval_state",
    "live_promotion_approval_allowed",
    "ramins_explicit_approval_required",
    "fund_manager_review_required",
    "live_credentials_enabled",
    "live_credentials_loaded",
    "live_credentials_required_for_review",
    "live_credentials_write_allowed",
    "live_capital_enabled",
    "live_broker_write_allowed",
    "broker_post_called_count",
    "alpaca_post_called_count",
    "broker_write_allowed_count",
    "prediction_market_write_allowed_count",
    "crypto_perps_write_allowed_count",
    "live_endpoint_allowed_count",
    "live_capital_enabled_count",
    "phase7_proof_credit_allowed_count",
    "phase7_proof_credit_allowed",
    "phase5_test_trades_count_for_phase7",
    "ui_inferred_readiness_count",
    "unsafe_write_counter_total",
    "operational_incident_count",
    "blockers",
    "blocker_count",
    "recommended_next_stage",
    "boundary",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _repo_root(settings: Settings | None = None) -> Path:
    return _runtime_dir(settings).parent.parent


def _path(ref: str, settings: Settings | None = None) -> Path:
    return _repo_root(settings) / ref


def _read_json_ref(ref: str, settings: Settings | None = None) -> dict[str, Any] | None:
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


def _has_local_path(ref: str) -> bool:
    if ref.startswith("/") or ref.startswith("~"):
        return True
    return len(ref) > 2 and ref[1:3] == ":\\"


def _source_certification(settings: Settings) -> dict[str, Any]:
    artifact = _read_json_ref(SOURCE_REFS["certification"], settings)
    if artifact:
        return artifact
    certification = build_phase7_certification(settings=settings)
    _, _, _, written = write_phase7_certification(
        certification,
        settings=settings,
        record_event=True,
    )
    return written


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
    provenance["decision_chain_refs"] = [SOURCE_REFS["signal_evidence"]]
    provenance["execution_evidence_refs"] = [
        SOURCE_REFS["proof_lifecycle"],
        SOURCE_REFS["postmortem"],
        SOURCE_REFS["performance"],
    ]
    provenance["market_context_refs"] = [
        SOURCE_REFS["weekly_review"],
        SOURCE_REFS["cockpit_visibility"],
    ]
    provenance["governance_refs"] = [
        SOURCE_REFS["certification"],
        SOURCE_REFS["drawdown"],
        SOURCE_REFS["override"],
        SOURCE_REFS["maturity"],
    ]
    provenance["proof_lifecycle_refs"] = [
        SOURCE_REFS["proof_lifecycle"],
        SOURCE_REFS["postmortem"],
    ]
    return provenance


def _source_summary(artifact: dict[str, Any], *fields: str) -> dict[str, Any]:
    return {field: deepcopy(artifact.get(field)) for field in fields if field in artifact}


def _public_status_from_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    output = {field: deepcopy(artifact.get(field)) for field in PUBLIC_STATUS_FIELDS if field in artifact}
    output["validation_error_count"] = len(artifact.get("validation_errors", []) or [])
    return output


def _refresh_validation(artifact: dict[str, Any]) -> dict[str, Any]:
    artifact.setdefault("validation_errors", [])
    artifact["public_status"] = _public_status_from_artifact(artifact)
    for _ in range(2):
        artifact["validation_errors"] = validate_phase7_live_promotion_review(artifact)
        artifact["validation_error_count"] = len(artifact["validation_errors"])
        artifact["public_status"] = _public_status_from_artifact(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "blocked"
        artifact["stage_status"] = "live_promotion_review_validation_error"
        artifact["live_promotion_review_state"] = "validation_error"
        artifact["live_promotion_review_packet_draft_allowed"] = False
        artifact["live_promotion_review_packet_created"] = False
        artifact["q7_18_live_promotion_review_stage_allowed"] = False
        artifact["public_status"] = _public_status_from_artifact(artifact)
    return artifact


def phase7_live_promotion_review_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE7_LIVE_PROMOTION_REVIEW_RUNTIME_ARTIFACT,
        runtime / PHASE7_LIVE_PROMOTION_REVIEW_HISTORY,
        runtime / PHASE7_LIVE_PROMOTION_REVIEW_EVENT_LOG,
    )


def build_phase7_live_promotion_review(
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    certification = _source_certification(settings)
    sources = {key: _read_json_ref(ref, settings) for key, ref in SOURCE_REFS.items()}
    sources["certification"] = certification
    source_status_records = [
        _source_status_record(key, SOURCE_REFS[key], sources[key]) for key in SOURCE_REFS
    ]
    source_missing_count = len(
        [record for record in source_status_records if record["source_status"] == "missing"]
    )
    source_validation_error_count = sum(
        _int(record.get("validation_error_count")) for record in source_status_records
    )

    visibility = sources["cockpit_visibility"] or {}
    weekly_review = sources["weekly_review"] or {}
    lifecycle = sources["proof_lifecycle"] or {}
    postmortem = sources["postmortem"] or {}
    performance = sources["performance"] or {}
    drawdown = sources["drawdown"] or {}
    override = sources["override"] or {}
    signal = sources["signal_evidence"] or {}

    certification_errors = validate_phase7_certification(certification)
    phase7_demo_proof_certified = certification.get("phase7_demo_proof_certified") is True
    q7_18_stage_allowed = (
        phase7_demo_proof_certified
        and certification.get("q7_18_live_promotion_review_stage_allowed") is True
        and not certification_errors
    )
    live_promotion_review_packet_created = q7_18_stage_allowed
    blockers: list[str] = []
    if certification_errors:
        blockers.append("phase7_certification_validation_errors")
    if not phase7_demo_proof_certified:
        blockers.append("phase7_certification_not_certified")
    if certification.get("q7_18_live_promotion_review_stage_allowed") is not True:
        blockers.append("q7_18_live_promotion_review_not_allowed")
    if source_missing_count:
        blockers.append("phase7_live_promotion_source_missing")
    if source_validation_error_count:
        blockers.append("phase7_live_promotion_source_validation_errors")
    blockers = sorted(set(blockers))

    status = "read_only" if q7_18_stage_allowed and not blockers else "blocked"
    if status == "read_only":
        stage_status = "live_promotion_review_packet_ready"
        review_state = "read_only_packet_ready_for_human_review"
    elif certification_errors:
        stage_status = "live_promotion_review_blocked_certification_validation"
        review_state = "blocked_certification_validation"
    elif not phase7_demo_proof_certified:
        stage_status = "live_promotion_review_blocked_phase7_not_certified"
        review_state = "blocked_pending_phase7_certification"
    else:
        stage_status = "live_promotion_review_blocked"
        review_state = "blocked"

    operational_incidents = sorted(
        set(
            [
                *[str(blocker) for blocker in certification.get("certification_blockers", [])],
                *blockers,
            ]
        )
    )

    artifact = {
        "schema_version": PHASE7_LIVE_PROMOTION_REVIEW_SCHEMA_VERSION,
        "phase7_live_promotion_review_schema_version": PHASE7_LIVE_PROMOTION_REVIEW_SCHEMA_VERSION,
        "phase7_artifact_schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "artifact_type": "live_promotion_review",
        "artifact_id": "phase7:q7-18:live-promotion-review",
        "phase": "Q7",
        "stage": "Q7-18",
        "status": status,
        "stage_status": stage_status,
        "live_promotion_review_state": review_state,
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
        "event_contract": phase7_event_contract("live_promotion"),
        "authority_ledger": {
            "authority_schema_version": PHASE7_LIVE_PROMOTION_REVIEW_SCHEMA_VERSION,
            "stage": "Q7-18",
            "authority_field_count": len(PHASE7_AUTHORITY_FLAGS),
            "explicit_authority_grant_count": 0,
            "explicit_authority_grants": [],
            "review_only": True,
            "q7_18_live_promotion_review_stage_allowed": q7_18_stage_allowed,
            **phase7_authority_defaults(),
            "boundary": PHASE7_LIVE_PROMOTION_REVIEW_BOUNDARY,
        },
        "proof_contract": phase7_proof_contract(),
        "source_posture": phase7_source_posture(),
        "provenance": _provenance(tuple(SOURCE_REFS.values())),
        "boundary": PHASE7_LIVE_PROMOTION_REVIEW_BOUNDARY,
        **phase7_authority_defaults(),
        **phase7_unsafe_counter_defaults(),
        "source_artifact_count": len(source_status_records),
        "source_missing_count": source_missing_count,
        "source_validation_error_count": source_validation_error_count,
        "source_status_records": source_status_records,
        "source_certification_status": certification.get("status"),
        "source_certification_stage_status": certification.get("stage_status"),
        "source_certification_validation_error_count": len(certification_errors),
        "phase7_demo_proof_certified": phase7_demo_proof_certified,
        "phase7_demo_proof_exit_gate": certification.get("phase7_demo_proof_exit_gate") is True,
        "phase7_30_day_operational_result_clean": certification.get(
            "phase7_30_day_operational_result_clean"
        )
        is True,
        "phase7_30_day_operational_result_preserved": certification.get(
            "phase7_30_day_operational_result_preserved"
        )
        is True,
        "phase7_30_day_run_complete": certification.get("phase7_30_day_run_complete") is True,
        "completed_calendar_day_count": _int(certification.get("completed_calendar_day_count")),
        "phase7_harness_day_count": _int(
            certification.get("phase7_harness_day_count") or PHASE7_HARNESS_DAY_COUNT
        ),
        "proof_week_count": _int(certification.get("proof_week_count")),
        "weekly_review_packet_created_count": _int(
            certification.get("weekly_review_packet_created_count")
        ),
        "qualified_setup_count": _int(certification.get("qualified_setup_count")),
        "evaluated_trade_count": _int(certification.get("evaluated_trade_count")),
        "expectancy_after_costs_gbp": _float_or_none(
            certification.get("expectancy_after_costs_gbp")
        ),
        "expectancy_after_costs_positive": certification.get(
            "expectancy_after_costs_positive"
        )
        is True,
        "drawdown_within_cap": certification.get("drawdown_within_cap") is True,
        "drawdown_cap_breached": certification.get("drawdown_cap_breached") is True,
        "risk_halt_active": certification.get("risk_halt_active") is True,
        "manual_trade_level_override_count": _int(
            certification.get("manual_trade_level_override_count")
        ),
        "sample_contaminated": certification.get("sample_contaminated") is True,
        "closed_proof_trade_count": _int(certification.get("closed_proof_trade_count")),
        "postmortem_due_count": _int(certification.get("postmortem_due_count")),
        "postmortem_missing_count": _int(certification.get("postmortem_missing_count")),
        "postmortem_reviewed_count": _int(certification.get("postmortem_reviewed_count")),
        "source_signal_chains_complete": certification.get(
            "source_signal_chains_complete"
        )
        is True,
        "maturity_state": certification.get("maturity_state", "unknown"),
        "maturity_classification": certification.get("maturity_classification", "unknown"),
        "mature_benchmark": _int(
            certification.get("mature_benchmark")
            or PHASE7_MATURE_CLOSED_TRADE_BENCHMARK
        ),
        "phase7_mature_benchmark_met": certification.get("phase7_mature_benchmark_met")
        is True,
        "phase7_statistically_immature": certification.get("phase7_statistically_immature")
        is True,
        "phase7_statistical_immaturity_hidden": certification.get(
            "phase7_statistical_immaturity_hidden"
        )
        is True,
        "certification_blocker_count": _int(certification.get("certification_blocker_count")),
        "certification_blockers": list(certification.get("certification_blockers", []) or []),
        "q7_18_live_promotion_review_stage_allowed": q7_18_stage_allowed,
        "live_promotion_review_packet_draft_allowed": q7_18_stage_allowed,
        "live_promotion_review_packet_created": live_promotion_review_packet_created,
        "live_promotion_review_packet_section_count": (
            len(PHASE7_LIVE_PROMOTION_REVIEW_SECTIONS)
            if live_promotion_review_packet_created
            else 0
        ),
        "live_promotion_review_packet_sections": (
            list(PHASE7_LIVE_PROMOTION_REVIEW_SECTIONS)
            if live_promotion_review_packet_created
            else []
        ),
        "review_packet": (
            {
                "packet_id": "phase7:q7-18:live-promotion-review-packet",
                "packet_owner": "Ramin",
                "created_at": generated_at,
                "review_state": "read_only_human_review_required",
                "sections": list(PHASE7_LIVE_PROMOTION_REVIEW_SECTIONS),
                "phase7_evidence_summary": _source_summary(
                    certification,
                    "phase7_demo_proof_certified",
                    "phase7_demo_proof_exit_gate",
                    "phase7_30_day_operational_result_clean",
                    "phase7_30_day_run_complete",
                    "completed_calendar_day_count",
                    "proof_week_count",
                    "weekly_cadence_satisfied_count",
                    "weekly_cadence_failed_count",
                    "qualified_setup_count",
                    "evaluated_trade_count",
                    "expectancy_after_costs_gbp",
                    "expectancy_after_costs_positive",
                    "closed_proof_trade_count",
                ),
                "maturity_summary": _source_summary(
                    certification,
                    "maturity_state",
                    "maturity_classification",
                    "mature_benchmark",
                    "phase7_mature_benchmark_met",
                    "phase7_statistically_immature",
                    "phase7_statistical_immaturity_hidden",
                ),
                "drawdown_summary": _source_summary(
                    drawdown,
                    "drawdown_state",
                    "drawdown_within_cap",
                    "drawdown_cap_breached",
                    "max_drawdown_fraction_observed",
                    "risk_halt_active",
                    "new_proof_trades_frozen",
                ),
                "override_summary": _source_summary(
                    override,
                    "sample_contaminated",
                    "override_count",
                    "manual_trade_level_override_count",
                    "broker_side_intervention_count",
                    "run_restart_required",
                ),
                "postmortem_summary": _source_summary(
                    postmortem,
                    "postmortem_due_count",
                    "postmortem_missing_count",
                    "postmortem_reviewed_count",
                    "postmortem_explicitly_deferred_count",
                ),
                "source_health_summary": {
                    "source_artifact_count": len(source_status_records),
                    "source_missing_count": source_missing_count,
                    "source_validation_error_count": source_validation_error_count,
                    "complete_decision_chain_count": _int(
                        signal.get("complete_decision_chain_count")
                    ),
                    "missing_decision_chain_count": _int(
                        signal.get("missing_decision_chain_count")
                    ),
                    "private_priors_only_proof_trade_count": _int(
                        signal.get("private_priors_only_proof_trade_count")
                    ),
                    "backend_derived": visibility.get("backend_derived") is True,
                },
                "weekly_review_summary": _source_summary(
                    weekly_review,
                    "weekly_review_packet_created_count",
                    "all_proof_weeks_have_review_packet",
                    "future_policy_comment_allowed",
                    "trade_level_intervention_allowed",
                    "trade_level_intervention_count",
                ),
                "operational_incident_summary": {
                    "operational_incident_count": len(operational_incidents),
                    "operational_incidents": operational_incidents,
                    "lifecycle_event_count": _int(lifecycle.get("lifecycle_event_count")),
                    "source_closed_proof_trade_count": _int(
                        lifecycle.get("closed_proof_trade_count")
                    ),
                    "performance_evaluated_trade_count": _int(
                        performance.get("evaluated_trade_count")
                    ),
                    "risk_halt_active": drawdown.get("risk_halt_active") is True,
                    "sample_contaminated": override.get("sample_contaminated") is True,
                },
                "cooling_off_summary": {
                    "cooling_off_required": True,
                    "cooling_off_period_hours": PHASE7_LIVE_PROMOTION_COOLING_OFF_HOURS,
                    "cooling_off_started_at": None,
                    "cooling_off_ends_at": None,
                    "cooling_off_complete": False,
                },
                "approval_summary": {
                    "live_promotion_approval_state": "not_requested",
                    "ramins_explicit_approval_required": True,
                    "fund_manager_review_required": True,
                    "live_promotion_approval_allowed": False,
                },
                "live_lockout_summary": {
                    "live_credentials_enabled": False,
                    "live_credentials_loaded": False,
                    "live_credentials_required_for_review": False,
                    "live_credentials_write_allowed": False,
                    "live_capital_enabled": False,
                    "live_broker_write_allowed": False,
                },
            }
            if live_promotion_review_packet_created
            else None
        ),
        "cooling_off_required": True,
        "cooling_off_period_hours": PHASE7_LIVE_PROMOTION_COOLING_OFF_HOURS,
        "cooling_off_started_at": None,
        "cooling_off_ends_at": None,
        "cooling_off_complete": False,
        "live_promotion_approval_state": "not_requested",
        "live_promotion_approval_allowed": False,
        "ramins_explicit_approval_required": True,
        "fund_manager_review_required": True,
        "live_credentials_enabled": False,
        "live_credentials_loaded": False,
        "live_credentials_required_for_review": False,
        "live_credentials_write_allowed": False,
        "live_capital_enabled": False,
        "live_broker_write_allowed": False,
        "phase5_test_trades_count_for_phase7": False,
        "phase7_proof_credit_allowed": False,
        "broker_post_called_count": 0,
        "alpaca_post_called_count": 0,
        "broker_write_allowed_count": 0,
        "prediction_market_write_allowed_count": 0,
        "crypto_perps_write_allowed_count": 0,
        "live_endpoint_allowed_count": 0,
        "live_capital_enabled_count": 0,
        "phase7_proof_credit_allowed_count": 0,
        "phase5_test_trade_reuse_count": 0,
        "ui_inferred_readiness_count": 0,
        "raw_payload_exposed_count": 0,
        "private_payload_exposed_count": 0,
        "local_path_exposed_count": 0,
        "secret_ref_exposed_count": 0,
        "broker_identifier_exposed_count": 0,
        "unsafe_write_counter_total": 0,
        "operational_incident_count": len(operational_incidents),
        "operational_incidents": operational_incidents,
        "blockers": blockers,
        "blocker_count": len(blockers),
        "recommended_next_stage": (
            "Hold read-only packet for Ramin review, cooling-off, and a later explicit live gate"
            if status == "read_only"
            else "Complete Q7-17 certification before drafting live-promotion review"
        ),
    }
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


def _forbidden_unsafe_count(artifact: dict[str, Any]) -> int:
    return sum(_int(artifact.get(field)) for field in PHASE7_UNSAFE_COUNT_FIELDS)


def _source_record_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("display_status") != record.get("backend_status"):
        errors.append("phase7_live_promotion_source_display_backend_mismatch")
    if record.get("display_derived_from_backend") is not True:
        errors.append("phase7_live_promotion_source_display_not_backend")
    if record.get("ui_inferred_readiness") is not False:
        errors.append("phase7_live_promotion_source_ui_inferred")
    source_ref = str(record.get("source_ref") or "")
    if not source_ref.startswith("data/runtime/"):
        errors.append("phase7_live_promotion_source_ref_invalid")
    if _has_local_path(source_ref):
        errors.append("phase7_live_promotion_source_ref_local_path")
    errors.extend(_public_safety_errors(record))
    return errors


def _review_packet_errors(packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "packet_id",
        "packet_owner",
        "created_at",
        "review_state",
        "sections",
        "phase7_evidence_summary",
        "maturity_summary",
        "drawdown_summary",
        "override_summary",
        "postmortem_summary",
        "source_health_summary",
        "weekly_review_summary",
        "operational_incident_summary",
        "cooling_off_summary",
        "approval_summary",
        "live_lockout_summary",
    }
    missing = sorted(required - set(packet))
    if missing:
        errors.append("phase7_live_promotion_packet_missing:" + ",".join(missing))
    if packet.get("packet_owner") != "Ramin":
        errors.append("phase7_live_promotion_packet_owner_invalid")
    if tuple(packet.get("sections", []) or []) != PHASE7_LIVE_PROMOTION_REVIEW_SECTIONS:
        errors.append("phase7_live_promotion_packet_sections_invalid")
    if packet.get("review_state") != "read_only_human_review_required":
        errors.append("phase7_live_promotion_packet_review_state_invalid")
    cooling = packet.get("cooling_off_summary", {})
    if not isinstance(cooling, dict):
        errors.append("phase7_live_promotion_packet_cooling_missing")
        cooling = {}
    if cooling.get("cooling_off_required") is not True:
        errors.append("phase7_live_promotion_packet_cooling_not_required")
    if cooling.get("cooling_off_complete") is not False:
        errors.append("phase7_live_promotion_packet_cooling_complete")
    approval = packet.get("approval_summary", {})
    if not isinstance(approval, dict):
        errors.append("phase7_live_promotion_packet_approval_missing")
        approval = {}
    if approval.get("live_promotion_approval_state") != "not_requested":
        errors.append("phase7_live_promotion_packet_approval_state_invalid")
    if approval.get("live_promotion_approval_allowed") is not False:
        errors.append("phase7_live_promotion_packet_approval_allowed")
    lockout = packet.get("live_lockout_summary", {})
    if not isinstance(lockout, dict):
        errors.append("phase7_live_promotion_packet_lockout_missing")
        lockout = {}
    for field in (
        "live_credentials_enabled",
        "live_credentials_loaded",
        "live_credentials_required_for_review",
        "live_credentials_write_allowed",
        "live_capital_enabled",
        "live_broker_write_allowed",
    ):
        if lockout.get(field) is not False:
            errors.append(f"phase7_live_promotion_packet_lockout_forbidden:{field}")
    errors.extend(_public_safety_errors(packet))
    return errors


def validate_phase7_live_promotion_review(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = set(PUBLIC_STATUS_FIELDS) | {
        "event_contract",
        "authority_ledger",
        "proof_contract",
        "source_posture",
        "provenance",
        "source_status_records",
        "source_certification_validation_error_count",
        "review_packet",
        "live_promotion_review_packet_sections",
        "operational_incidents",
        "public_status",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("phase7_live_promotion_missing_fields:" + ",".join(missing))
    errors.extend(validate_phase7_artifact(artifact, expected_stage="Q7-18"))
    if artifact.get("phase7_live_promotion_review_schema_version") != (
        PHASE7_LIVE_PROMOTION_REVIEW_SCHEMA_VERSION
    ):
        errors.append("phase7_live_promotion_schema_version_mismatch")
    if artifact.get("phase7_artifact_schema_version") != PHASE7_ARTIFACT_SCHEMA_VERSION:
        errors.append("phase7_live_promotion_artifact_schema_version_mismatch")
    if artifact.get("artifact_type") != "live_promotion_review":
        errors.append("phase7_live_promotion_artifact_type_mismatch")
    if artifact.get("status") not in {"blocked", "read_only"}:
        errors.append("phase7_live_promotion_status_invalid")
    if artifact.get("stage_status") not in {
        "live_promotion_review_packet_ready",
        "live_promotion_review_blocked_phase7_not_certified",
        "live_promotion_review_blocked_certification_validation",
        "live_promotion_review_blocked",
        "live_promotion_review_validation_error",
    }:
        errors.append("phase7_live_promotion_stage_status_invalid")

    source_records = artifact.get("source_status_records", [])
    if not isinstance(source_records, list) or not source_records:
        errors.append("phase7_live_promotion_source_records_missing")
        source_records = []
    if artifact.get("source_artifact_count") != len(source_records):
        errors.append("phase7_live_promotion_source_count_mismatch")
    source_missing_count = 0
    source_validation_error_count = 0
    for record in source_records:
        if not isinstance(record, dict):
            errors.append("phase7_live_promotion_source_record_invalid")
            continue
        if record.get("source_status") == "missing":
            source_missing_count += 1
        source_validation_error_count += _int(record.get("validation_error_count"))
        errors.extend(_source_record_errors(record))
    if artifact.get("source_missing_count") != source_missing_count:
        errors.append("phase7_live_promotion_source_missing_count_mismatch")
    if artifact.get("source_validation_error_count") != source_validation_error_count:
        errors.append("phase7_live_promotion_source_validation_count_mismatch")

    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("phase7_live_promotion_blockers_not_list")
        blockers = []
    if artifact.get("blocker_count") != len(blockers):
        errors.append("phase7_live_promotion_blocker_count_mismatch")
    incidents = artifact.get("operational_incidents", [])
    if not isinstance(incidents, list):
        errors.append("phase7_live_promotion_incidents_not_list")
        incidents = []
    if artifact.get("operational_incident_count") != len(incidents):
        errors.append("phase7_live_promotion_incident_count_mismatch")

    certified = artifact.get("phase7_demo_proof_certified") is True
    q7_18_allowed = artifact.get("q7_18_live_promotion_review_stage_allowed") is True
    packet_created = artifact.get("live_promotion_review_packet_created") is True
    draft_allowed = artifact.get("live_promotion_review_packet_draft_allowed") is True
    if certified:
        if artifact.get("phase7_demo_proof_exit_gate") is not True:
            errors.append("phase7_live_promotion_certified_exit_gate_false")
        if artifact.get("phase7_mature_benchmark_met") is not True:
            errors.append("phase7_live_promotion_certified_without_mature_benchmark")
        if artifact.get("phase7_statistical_immaturity_hidden") is not False:
            errors.append("phase7_live_promotion_hidden_immaturity")
    else:
        if q7_18_allowed:
            errors.append("phase7_live_promotion_q7_18_allowed_without_certification")
        if draft_allowed or packet_created:
            errors.append("phase7_live_promotion_packet_created_before_certification")
    if q7_18_allowed and not certified:
        errors.append("phase7_live_promotion_allowed_without_certification")
    if draft_allowed != q7_18_allowed:
        errors.append("phase7_live_promotion_draft_allowed_mismatch")
    if packet_created != draft_allowed:
        errors.append("phase7_live_promotion_packet_created_mismatch")
    if packet_created:
        if artifact.get("status") != "read_only":
            errors.append("phase7_live_promotion_packet_status_not_read_only")
        if blockers:
            errors.append("phase7_live_promotion_packet_with_blockers")
        if artifact.get("live_promotion_review_state") != "read_only_packet_ready_for_human_review":
            errors.append("phase7_live_promotion_packet_state_invalid")
        if artifact.get("live_promotion_review_packet_section_count") != len(
            PHASE7_LIVE_PROMOTION_REVIEW_SECTIONS
        ):
            errors.append("phase7_live_promotion_packet_section_count_mismatch")
        if tuple(artifact.get("live_promotion_review_packet_sections", []) or []) != (
            PHASE7_LIVE_PROMOTION_REVIEW_SECTIONS
        ):
            errors.append("phase7_live_promotion_packet_section_list_mismatch")
        packet = artifact.get("review_packet")
        if not isinstance(packet, dict):
            errors.append("phase7_live_promotion_packet_missing")
        else:
            errors.extend(_review_packet_errors(packet))
    else:
        if artifact.get("status") != "blocked":
            errors.append("phase7_live_promotion_blocked_status_not_blocked")
        if not blockers:
            errors.append("phase7_live_promotion_blocked_without_blockers")
        if artifact.get("review_packet") is not None:
            errors.append("phase7_live_promotion_blocked_packet_present")
        if artifact.get("live_promotion_review_packet_section_count") != 0:
            errors.append("phase7_live_promotion_blocked_section_count_nonzero")
        if artifact.get("live_promotion_review_packet_sections") != []:
            errors.append("phase7_live_promotion_blocked_sections_present")

    if artifact.get("source_certification_validation_error_count", 0) and (
        "phase7_certification_validation_errors" not in blockers
    ):
        errors.append("phase7_live_promotion_certification_validation_not_blocking")
    if not certified and "phase7_certification_not_certified" not in blockers:
        errors.append("phase7_live_promotion_certification_not_blocking")
    if not q7_18_allowed and "q7_18_live_promotion_review_not_allowed" not in blockers:
        errors.append("phase7_live_promotion_q7_18_not_blocking")
    if source_missing_count and "phase7_live_promotion_source_missing" not in blockers:
        errors.append("phase7_live_promotion_source_missing_not_blocking")
    if source_validation_error_count and "phase7_live_promotion_source_validation_errors" not in blockers:
        errors.append("phase7_live_promotion_source_validation_not_blocking")

    if artifact.get("phase7_harness_day_count") != PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_live_promotion_harness_day_count_mismatch")
    if artifact.get("completed_calendar_day_count") > PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_live_promotion_completed_days_invalid")
    if artifact.get("mature_benchmark") != PHASE7_MATURE_CLOSED_TRADE_BENCHMARK:
        errors.append("phase7_live_promotion_mature_benchmark_mismatch")
    if artifact.get("phase7_30_day_operational_result_preserved") is not True:
        errors.append("phase7_live_promotion_operational_result_not_preserved")

    for field in (
        "live_credentials_enabled",
        "live_credentials_loaded",
        "live_credentials_required_for_review",
        "live_credentials_write_allowed",
        "live_capital_enabled",
        "live_broker_write_allowed",
        "phase7_proof_credit_allowed",
        "phase5_test_trades_count_for_phase7",
        "live_promotion_approval_allowed",
    ):
        if artifact.get(field) is not False:
            errors.append(f"phase7_live_promotion_forbidden:{field}")
    if artifact.get("live_promotion_approval_state") != "not_requested":
        errors.append("phase7_live_promotion_approval_state_invalid")
    if artifact.get("ramins_explicit_approval_required") is not True:
        errors.append("phase7_live_promotion_ramin_approval_not_required")
    if artifact.get("fund_manager_review_required") is not True:
        errors.append("phase7_live_promotion_fund_manager_review_not_required")
    if artifact.get("cooling_off_required") is not True:
        errors.append("phase7_live_promotion_cooling_off_not_required")
    if artifact.get("cooling_off_period_hours") != PHASE7_LIVE_PROMOTION_COOLING_OFF_HOURS:
        errors.append("phase7_live_promotion_cooling_off_period_invalid")
    if artifact.get("cooling_off_complete") is not False:
        errors.append("phase7_live_promotion_cooling_off_complete")
    if artifact.get("cooling_off_started_at") is not None:
        errors.append("phase7_live_promotion_cooling_started_without_later_gate")
    if artifact.get("cooling_off_ends_at") is not None:
        errors.append("phase7_live_promotion_cooling_ends_without_later_gate")

    for field in PHASE7_AUTHORITY_FLAGS:
        if artifact.get(field) is not False:
            errors.append(f"phase7_live_promotion_authority_enabled:{field}")
    ledger = artifact.get("authority_ledger", {})
    if not isinstance(ledger, dict):
        errors.append("phase7_live_promotion_authority_ledger_missing")
        ledger = {}
    if ledger.get("stage") != "Q7-18":
        errors.append("phase7_live_promotion_authority_stage_mismatch")
    if ledger.get("authority_field_count") != len(PHASE7_AUTHORITY_FLAGS):
        errors.append("phase7_live_promotion_authority_count_mismatch")
    if ledger.get("explicit_authority_grant_count") != 0:
        errors.append("phase7_live_promotion_authority_grant_nonzero")
    for field in PHASE7_AUTHORITY_FLAGS:
        if ledger.get(field) is not False:
            errors.append(f"phase7_live_promotion_ledger_authority_enabled:{field}")
    if ledger.get("q7_18_live_promotion_review_stage_allowed") != q7_18_allowed:
        errors.append("phase7_live_promotion_q7_18_ledger_mismatch")

    if artifact.get("unsafe_write_counter_total") != _forbidden_unsafe_count(artifact):
        errors.append("phase7_live_promotion_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("phase7_live_promotion_unsafe_total_nonzero")
    for count_field in PHASE7_UNSAFE_COUNT_FIELDS:
        if count_field not in artifact:
            errors.append(f"phase7_live_promotion_unsafe_count_missing:{count_field}")
        elif _int(artifact.get(count_field)) != 0:
            errors.append(f"phase7_live_promotion_unsafe_count_nonzero:{count_field}")
    for count_field in (
        "raw_payload_exposed_count",
        "private_payload_exposed_count",
        "local_path_exposed_count",
        "secret_ref_exposed_count",
        "broker_identifier_exposed_count",
    ):
        if _int(artifact.get(count_field)) != 0:
            errors.append(f"phase7_live_promotion_exposure_count_nonzero:{count_field}")

    public_status = artifact.get("public_status")
    if not isinstance(public_status, dict):
        errors.append("phase7_live_promotion_public_status_missing")
    else:
        extra = sorted(set(public_status) - set(PUBLIC_STATUS_FIELDS))
        if extra:
            errors.append("phase7_live_promotion_public_status_extra_fields:" + ",".join(extra))
        for field in PUBLIC_STATUS_FIELDS:
            if field == "validation_error_count":
                continue
            if field in artifact and public_status.get(field) != artifact.get(field):
                errors.append(f"phase7_live_promotion_public_status_mismatch:{field}")
        errors.extend(_public_safety_errors(public_status))
    errors.extend(_public_safety_errors(artifact.get("provenance", {})))
    event_contract = artifact.get("event_contract", {})
    if not isinstance(event_contract, dict):
        errors.append("phase7_live_promotion_event_contract_missing")
        event_contract = {}
    if event_contract.get("event_type") != PHASE7_LIVE_PROMOTION_REVIEW_EVENT_TYPE:
        errors.append("phase7_live_promotion_event_contract_type_mismatch")
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("phase7_live_promotion_event_log_path_missing")
        if not artifact.get("event_log_correlation_id"):
            errors.append("phase7_live_promotion_event_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("phase7_live_promotion_event_log_count_mismatch")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "Ramin's structured live-promotion review packet",
        "after Q7-17 Phase 7 certification",
        "cooling-off requirements",
        "cannot approve live promotion",
        "cannot load live credentials",
        "cannot enable live capital",
        "cannot call broker POST routes",
        "cannot bypass the cooling-off period",
        "cannot grant Phase 7 proof credit",
        "cannot infer readiness from the UI",
    ):
        if phrase not in boundary:
            errors.append("phase7_live_promotion_boundary_weak")
            break
    return sorted(set(errors))


def attach_phase7_live_promotion_review_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(
        event_log_path or (_runtime_dir(settings) / PHASE7_LIVE_PROMOTION_REVIEW_EVENT_LOG)
    )
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE7_LIVE_PROMOTION_REVIEW_EVENT_TYPE,
        PHASE7_LIVE_PROMOTION_REVIEW_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "stage_status": output.get("stage_status"),
            "live_promotion_review_state": output.get("live_promotion_review_state"),
            "phase7_demo_proof_certified": output.get("phase7_demo_proof_certified"),
            "q7_18_live_promotion_review_stage_allowed": output.get(
                "q7_18_live_promotion_review_stage_allowed"
            ),
            "live_promotion_review_packet_created": output.get(
                "live_promotion_review_packet_created"
            ),
            "cooling_off_required": output.get("cooling_off_required"),
            "cooling_off_complete": output.get("cooling_off_complete"),
            "live_credentials_enabled": output.get("live_credentials_enabled"),
            "live_credentials_loaded": output.get("live_credentials_loaded"),
            "live_capital_enabled": output.get("live_capital_enabled"),
            "live_promotion_approval_state": output.get("live_promotion_approval_state"),
            "blocker_count": output.get("blocker_count"),
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


def write_phase7_live_promotion_review(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase7_live_promotion_review_paths(
        settings
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase7_live_promotion_review_event_log(
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
        "schema_version": PHASE7_LIVE_PROMOTION_REVIEW_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "stage_status": output.get("stage_status"),
        "live_promotion_review_state": output.get("live_promotion_review_state"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "phase7_demo_proof_certified": output.get("phase7_demo_proof_certified"),
        "q7_18_live_promotion_review_stage_allowed": output.get(
            "q7_18_live_promotion_review_stage_allowed"
        ),
        "live_promotion_review_packet_created": output.get(
            "live_promotion_review_packet_created"
        ),
        "cooling_off_required": output.get("cooling_off_required"),
        "cooling_off_complete": output.get("cooling_off_complete"),
        "live_credentials_enabled": output.get("live_credentials_enabled"),
        "live_credentials_loaded": output.get("live_credentials_loaded"),
        "live_capital_enabled": output.get("live_capital_enabled"),
        "blocker_count": output.get("blocker_count"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output


def phase7_live_promotion_review_public_status(
    settings: Settings | None = None,
) -> dict[str, Any]:
    artifact = _read_json_ref(
        f"data/runtime/{PHASE7_LIVE_PROMOTION_REVIEW_RUNTIME_ARTIFACT}",
        settings,
    )
    if not artifact:
        artifact = build_phase7_live_promotion_review(settings=settings)
    artifact = _refresh_validation(artifact)
    return _public_status_from_artifact(artifact)
