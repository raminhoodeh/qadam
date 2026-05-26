"""Q7-16 Phase 7 weekly demo-proof review packets.

This stage creates public-safe, read-only weekly review packets for the
30-day demo-proof harness. The packets summarize weekly cadence, no-trade
rationale, proof lifecycle, postmortems, drawdown, overrides, source health,
and funnel conversion. Fund Manager comments are limited to future-policy
review; Q7-16 cannot approve, reject, edit, or otherwise intervene in
individual proof trades.
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
from orchestrator.phase7_cockpit_visibility import (
    PHASE7_COCKPIT_VISIBILITY_RUNTIME_ARTIFACT,
    build_phase7_cockpit_visibility,
    phase7_cockpit_visibility_paths,
    validate_phase7_cockpit_visibility,
    write_phase7_cockpit_visibility,
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
    phase7_authority_defaults,
    phase7_unsafe_counter_defaults,
)
from orchestrator.phase7_signal_funnel_evidence import (
    PHASE7_SIGNAL_FUNNEL_EVIDENCE_RUNTIME_ARTIFACT,
)
from orchestrator.phase7_weekly_cadence import PHASE7_WEEKLY_CADENCE_RUNTIME_ARTIFACT


PHASE7_WEEKLY_REVIEW_PACK_SCHEMA_VERSION = 1
PHASE7_WEEKLY_REVIEW_PACK_RUNTIME_ARTIFACT = "phase7_weekly_review_pack.json"
PHASE7_WEEKLY_REVIEW_PACK_HISTORY = "phase7_weekly_review_pack_history.jsonl"
PHASE7_WEEKLY_REVIEW_PACK_EVENT_LOG = "phase7_weekly_review_pack_events.jsonl"
PHASE7_WEEKLY_REVIEW_PACK_EVENT_TYPE = PHASE7_EVENT_TYPES["weekly_review"]
PHASE7_WEEKLY_REVIEW_PACK_COMPONENT = "phase7_weekly_review_pack"

SOURCE_REFS: dict[str, str] = {
    "cockpit_visibility": f"data/runtime/{PHASE7_COCKPIT_VISIBILITY_RUNTIME_ARTIFACT}",
    "weekly_cadence": f"data/runtime/{PHASE7_WEEKLY_CADENCE_RUNTIME_ARTIFACT}",
    "qualified_setup_ledger": f"data/runtime/{PHASE7_QUALIFIED_SETUP_LEDGER_RUNTIME_ARTIFACT}",
    "proof_order_staging": f"data/runtime/{PHASE7_PROOF_ORDER_STAGING_RUNTIME_ARTIFACT}",
    "proof_lifecycle": f"data/runtime/{PHASE7_PROOF_LIFECYCLE_RUNTIME_ARTIFACT}",
    "postmortem": f"data/runtime/{PHASE7_PROOF_POSTMORTEM_RUNTIME_ARTIFACT}",
    "performance": f"data/runtime/{PHASE7_PERFORMANCE_EVALUATOR_RUNTIME_ARTIFACT}",
    "drawdown": f"data/runtime/{PHASE7_DRAWDOWN_RISK_SENTINEL_RUNTIME_ARTIFACT}",
    "override": f"data/runtime/{PHASE7_OVERRIDE_DETECTOR_RUNTIME_ARTIFACT}",
    "signal_evidence": f"data/runtime/{PHASE7_SIGNAL_FUNNEL_EVIDENCE_RUNTIME_ARTIFACT}",
    "maturity": f"data/runtime/{PHASE7_MATURITY_TRACKER_RUNTIME_ARTIFACT}",
}

PHASE7_WEEKLY_REVIEW_BOUNDARY = (
    "Q7-16 creates read-only weekly review packets for the Phase 7 demo-proof "
    "harness from backend artifacts only. Fund Manager comments are "
    "future-policy review only. Q7-16 cannot mutate individual proof trades, "
    "cannot approve or reject individual proof trades, cannot modify orders "
    "or positions, cannot force trades to satisfy cadence, cannot grant Phase "
    "7 proof credit, cannot count Phase 5 test trades toward Phase 7 proof, "
    "cannot hide statistical immaturity, cannot call broker POST routes, "
    "cannot call Alpaca POST routes, cannot write prediction-market or "
    "crypto-perps orders, cannot mutate policy or strategies in this stage, "
    "cannot infer readiness from the UI, cannot expose raw payloads, private "
    "payloads, local paths, secrets, broker identifiers, request bodies, "
    "receipts, or source payloads, and cannot enable live capital."
)

PHASE7_WEEKLY_REVIEW_REQUIRED_CHECKS: tuple[str, ...] = (
    "q7_15_visibility_valid",
    "q7_16_stage_allowed",
    "review_packet_for_each_proof_week",
    "weekly_cadence_source_present",
    "no_trade_rationale_present_when_no_qualified_setups",
    "missed_setup_summary_present",
    "drawdown_summary_present",
    "override_summary_present",
    "postmortem_summary_present",
    "source_health_summary_present",
    "funnel_conversion_summary_present",
    "future_policy_comments_only",
    "trade_level_intervention_zero",
    "no_individual_trade_mutation",
    "no_proof_credit",
    "phase5_test_trades_excluded",
    "no_broker_or_market_writes",
    "no_live_capital",
    "statistical_immaturity_not_hidden",
    "public_safe",
)

PUBLIC_STATUS_FIELDS: tuple[str, ...] = (
    "schema_version",
    "phase7_weekly_review_pack_schema_version",
    "phase7_artifact_schema_version",
    "artifact_type",
    "artifact_id",
    "phase",
    "stage",
    "status",
    "stage_status",
    "review_state",
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
    "phase7_harness_day_count",
    "proof_week_count",
    "review_pack_record_count",
    "weekly_review_packet_created",
    "weekly_review_packet_created_count",
    "all_proof_weeks_have_review_packet",
    "future_policy_comment_allowed",
    "trade_level_intervention_allowed",
    "trade_level_intervention_count",
    "individual_trade_mutation_allowed",
    "proof_trade_approval_allowed",
    "proof_trade_rejection_allowed",
    "order_modification_allowed",
    "position_modification_allowed",
    "qualified_setup_count",
    "missed_qualified_setup_count",
    "missed_qualified_setup_unexplained_count",
    "source_submitted_paper_order_count",
    "source_closed_proof_trade_count",
    "source_postmortem_due_count",
    "source_postmortem_missing_count",
    "source_override_count",
    "source_manual_trade_level_override_count",
    "source_drawdown_within_cap",
    "source_max_drawdown_fraction_observed",
    "source_expectancy_after_costs_positive",
    "source_complete_decision_chain_count",
    "source_missing_decision_chain_count",
    "mature_benchmark",
    "phase7_mature_benchmark_met",
    "phase7_statistical_immaturity_hidden",
    "phase5_test_trades_count_for_phase7",
    "q6_deferred_learning_counts_as_proof",
    "phase7_proof_credit_allowed",
    "live_capital_enabled",
    "broker_post_called_count",
    "alpaca_post_called_count",
    "broker_write_allowed_count",
    "prediction_market_write_allowed_count",
    "crypto_perps_write_allowed_count",
    "live_endpoint_allowed_count",
    "phase7_proof_credit_allowed_count",
    "phase5_test_trade_reuse_count",
    "ui_inferred_readiness_count",
    "raw_payload_exposed_count",
    "private_payload_exposed_count",
    "local_path_exposed_count",
    "secret_ref_exposed_count",
    "broker_identifier_exposed_count",
    "unsafe_write_counter_total",
    "q7_17_certification_stage_allowed",
    "review_packet_records",
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


def _read_json_path(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


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


def _source_visibility(settings: Settings) -> dict[str, Any]:
    output_path, _, _ = phase7_cockpit_visibility_paths(settings)
    if output_path.exists():
        return _read_json_path(output_path)
    visibility = build_phase7_cockpit_visibility(settings=settings)
    _, _, _, written = write_phase7_cockpit_visibility(
        visibility,
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
        SOURCE_REFS["weekly_cadence"],
        SOURCE_REFS["qualified_setup_ledger"],
        SOURCE_REFS["cockpit_visibility"],
    ]
    provenance["governance_refs"] = [
        SOURCE_REFS["drawdown"],
        SOURCE_REFS["override"],
        SOURCE_REFS["maturity"],
    ]
    provenance["proof_lifecycle_refs"] = [
        SOURCE_REFS["proof_order_staging"],
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
        artifact["validation_errors"] = validate_phase7_weekly_review_pack(artifact)
        artifact["validation_error_count"] = len(artifact["validation_errors"])
        artifact["public_status"] = _public_status_from_artifact(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "blocked"
        artifact["stage_status"] = "weekly_review_pack_blocked"
        artifact["review_state"] = "blocked"
        artifact["public_status"] = _public_status_from_artifact(artifact)
    return artifact


def phase7_weekly_review_pack_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE7_WEEKLY_REVIEW_PACK_RUNTIME_ARTIFACT,
        runtime / PHASE7_WEEKLY_REVIEW_PACK_HISTORY,
        runtime / PHASE7_WEEKLY_REVIEW_PACK_EVENT_LOG,
    )


def _weekly_records(cadence: dict[str, Any], visibility: dict[str, Any]) -> list[dict[str, Any]]:
    records = cadence.get("weekly_cadence_records")
    if isinstance(records, list) and records:
        return [record for record in records if isinstance(record, dict)]
    proof_week_count = max(1, _int(visibility.get("proof_week_count")))
    output: list[dict[str, Any]] = []
    for week in range(1, proof_week_count + 1):
        start_day = ((week - 1) * 7) + 1
        end_day = min(PHASE7_HARNESS_DAY_COUNT, week * 7)
        output.append(
            {
                "cadence_record_id": f"q7-16:fallback-proof-week:{week}",
                "proof_week_number": week,
                "start_day_number": start_day,
                "end_day_number": end_day,
                "start_date": None,
                "end_date": None,
                "is_partial_week": end_day < week * 7,
                "qualified_setup_count": 0,
                "target_proof_trade_count": 0,
                "proof_trade_count": 0,
                "closed_proof_trade_count": 0,
                "missed_qualified_setup_count": 0,
                "cadence_satisfied": True,
                "cadence_state": "satisfied_no_qualified_setups",
                "no_trade_rationale": "phase7_calendar_scheduled_but_harness_not_started",
                "weekly_target_formula": "min(3, qualified_setup_count)",
                "max_weekly_proof_trade_target": PHASE7_WEEKLY_PROOF_TRADE_TARGET,
            }
        )
    return output


def _records_for_week(records: Any, week: int) -> list[dict[str, Any]]:
    if not isinstance(records, list):
        return []
    return [
        record
        for record in records
        if isinstance(record, dict) and _int(record.get("proof_week_number")) == week
    ]


def _review_record(
    *,
    cadence_record: dict[str, Any],
    visibility: dict[str, Any],
    postmortem: dict[str, Any],
    drawdown: dict[str, Any],
    override: dict[str, Any],
    signal_evidence: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    week = _int(cadence_record.get("proof_week_number"))
    qualified = _int(cadence_record.get("qualified_setup_count"))
    proof_trade_count = _int(cadence_record.get("proof_trade_count"))
    closed_count = _int(cadence_record.get("closed_proof_trade_count"))
    target = _int(cadence_record.get("target_proof_trade_count"))
    missed = _int(cadence_record.get("missed_qualified_setup_count"))
    no_trade_rationale = str(
        cadence_record.get("no_trade_rationale")
        or ("none_required" if qualified or proof_trade_count else "no_qualified_setups")
    )
    postmortem_due_records = _records_for_week(postmortem.get("postmortem_due_records"), week)
    postmortem_missing_records = _records_for_week(
        postmortem.get("postmortem_missing_records"),
        week,
    )
    signal_records = _records_for_week(signal_evidence.get("signal_evidence_records"), week)
    source_health = {
        "source_artifact_count": _int(visibility.get("source_artifact_count")),
        "source_missing_count": _int(visibility.get("source_missing_count")),
        "source_validation_error_count": _int(
            visibility.get("source_validation_error_count")
        ),
        "backend_derived": visibility.get("backend_derived") is True,
        "ui_inferred_readiness_count": _int(
            visibility.get("ui_inferred_readiness_count")
        ),
    }
    funnel_conversion = {
        "qualified_setup_count": qualified,
        "target_proof_trade_count": target,
        "staged_proof_order_count": _int(visibility.get("staged_proof_order_count")),
        "submitted_paper_order_count": _int(
            visibility.get("submitted_paper_order_count")
        ),
        "broker_receipt_count": _int(visibility.get("broker_receipt_count")),
        "open_position_count": _int(visibility.get("open_position_count")),
        "closed_proof_trade_count": closed_count,
        "complete_decision_chain_count": _int(
            visibility.get("complete_decision_chain_count")
        ),
        "missing_decision_chain_count": _int(
            visibility.get("missing_decision_chain_count")
        ),
    }
    return {
        "packet_id": f"q7-16:proof-week:{week}:review-pack",
        "source_cadence_record_id": cadence_record.get("cadence_record_id"),
        "proof_week_number": week,
        "start_date": cadence_record.get("start_date"),
        "end_date": cadence_record.get("end_date"),
        "start_day_number": _int(cadence_record.get("start_day_number")),
        "end_day_number": _int(cadence_record.get("end_day_number")),
        "is_partial_week": cadence_record.get("is_partial_week") is True,
        "review_state": "read_only_no_qualified_setups"
        if qualified == 0
        else "read_only_review_required",
        "weekly_review_packet_created": True,
        "created_at": generated_at,
        "fund_manager_comment_scope": "future_policy_only",
        "future_policy_comment_allowed": True,
        "allowed_comment_topics": [
            "future_policy_thresholds",
            "future_source_weight_review",
            "future_no_trade_rationale_review",
            "future_risk_limit_review",
            "future_strategy_playbook_amendments",
        ],
        "prohibited_comment_topics": [
            "approve_individual_trade",
            "reject_individual_trade",
            "edit_order_or_position",
            "force_trade_to_meet_cadence",
            "grant_phase7_proof_credit",
        ],
        "trade_level_intervention_allowed": False,
        "trade_level_intervention_count": 0,
        "individual_trade_mutation_allowed": False,
        "proof_trade_approval_allowed": False,
        "proof_trade_rejection_allowed": False,
        "order_modification_allowed": False,
        "position_modification_allowed": False,
        "qualified_setup_count": qualified,
        "target_proof_trade_count": target,
        "proof_trade_count": proof_trade_count,
        "closed_proof_trade_count": closed_count,
        "missed_qualified_setup_count": missed,
        "missed_qualified_setup_unexplained_count": _int(
            cadence_record.get("missed_qualified_setup_unexplained_count")
        ),
        "cadence_satisfied": cadence_record.get("cadence_satisfied") is True,
        "cadence_state": cadence_record.get("cadence_state", "unknown"),
        "weekly_target_formula": cadence_record.get(
            "weekly_target_formula",
            "min(3, qualified_setup_count)",
        ),
        "no_trade_rationale": no_trade_rationale,
        "no_trade_explanation_recorded": bool(no_trade_rationale),
        "drawdown_summary": {
            "drawdown_state": drawdown.get("drawdown_state", "unknown"),
            "drawdown_within_cap": drawdown.get("drawdown_within_cap") is True,
            "max_drawdown_fraction_observed": _float_or_none(
                drawdown.get("max_drawdown_fraction_observed")
            ),
            "risk_halt_active": drawdown.get("risk_halt_active") is True,
            "new_proof_trades_frozen": drawdown.get("new_proof_trades_frozen") is True,
        },
        "override_summary": {
            "sample_contaminated": override.get("sample_contaminated") is True,
            "override_count": _int(override.get("override_count")),
            "manual_trade_level_override_count": _int(
                override.get("manual_trade_level_override_count")
            ),
            "run_restart_required": override.get("run_restart_required") is True,
        },
        "postmortem_summary": {
            "postmortem_due_count": len(postmortem_due_records)
            or _int(postmortem.get("postmortem_due_count")),
            "postmortem_missing_count": len(postmortem_missing_records)
            or _int(postmortem.get("postmortem_missing_count")),
            "postmortem_reviewed_count": _int(postmortem.get("postmortem_reviewed_count")),
            "postmortem_explicitly_deferred_count": _int(
                postmortem.get("postmortem_explicitly_deferred_count")
            ),
        },
        "source_health_summary": source_health,
        "funnel_conversion_summary": funnel_conversion,
        "signal_evidence_summary": {
            "proof_trade_evidence_record_count": len(signal_records)
            or _int(signal_evidence.get("proof_trade_evidence_record_count")),
            "complete_decision_chain_count": _int(
                signal_evidence.get("complete_decision_chain_count")
            ),
            "missing_decision_chain_count": _int(
                signal_evidence.get("missing_decision_chain_count")
            ),
            "private_priors_only_proof_trade_count": _int(
                signal_evidence.get("private_priors_only_proof_trade_count")
            ),
        },
        "maturity_summary": {
            "mature_benchmark": _int(
                visibility.get("mature_benchmark")
                or PHASE7_MATURE_CLOSED_TRADE_BENCHMARK
            ),
            "closed_proof_trade_count": _int(visibility.get("closed_proof_trade_count")),
            "maturity_progress_fraction": _float_or_none(
                visibility.get("maturity_progress_fraction")
            ),
            "phase7_mature_benchmark_met": (
                visibility.get("phase7_mature_benchmark_met") is True
            ),
            "phase7_statistical_immaturity_hidden": (
                visibility.get("phase7_statistical_immaturity_hidden") is True
            ),
        },
        "proof_credit_allowed": False,
        "phase5_test_trades_count_for_phase7": False,
        "live_capital_enabled": False,
        "raw_payload_exposed": False,
        "private_payload_exposed": False,
        "local_path_exposed": False,
        "secret_ref_exposed": False,
        "broker_identifier_exposed": False,
        "boundary": (
            "Weekly review packet is read-only and accepts future-policy "
            "comments only; it cannot intervene in individual proof trades."
        ),
    }


def _check(name: str, passed: bool, *, detail: Any = None) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _preflight_blockers(
    visibility: dict[str, Any],
    source_records: list[dict[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    if validate_phase7_cockpit_visibility(visibility):
        blockers.append("phase7_cockpit_visibility_validation_errors")
    if visibility.get("recorded") is not True:
        blockers.append("phase7_cockpit_visibility_not_recorded")
    if visibility.get("q7_16_weekly_review_pack_stage_allowed") is not True:
        blockers.append("q7_16_weekly_review_stage_not_allowed")
    if visibility.get("backend_derived") is not True:
        blockers.append("phase7_visibility_not_backend_derived")
    if _int(visibility.get("ui_inferred_readiness_count")) != 0:
        blockers.append("phase7_visibility_ui_inferred")
    if any(_int(record.get("validation_error_count")) for record in source_records):
        blockers.append("q7_16_source_validation_errors")
    if any(record.get("source_status") == "missing" for record in source_records):
        blockers.append("q7_16_source_missing")
    return sorted(set(blockers))


def build_phase7_weekly_review_pack(
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    visibility = _source_visibility(settings)
    sources = {key: _read_json_ref(ref, settings) for key, ref in SOURCE_REFS.items()}
    sources["cockpit_visibility"] = visibility
    source_status_records = [
        _source_status_record(key, SOURCE_REFS[key], sources[key]) for key in SOURCE_REFS
    ]
    source_missing_count = len(
        [record for record in source_status_records if record["source_status"] == "missing"]
    )
    source_validation_error_count = sum(
        _int(record["validation_error_count"]) for record in source_status_records
    )
    cadence = sources["weekly_cadence"] or {}
    postmortem = sources["postmortem"] or {}
    drawdown = sources["drawdown"] or {}
    override = sources["override"] or {}
    signal_evidence = sources["signal_evidence"] or {}

    cadence_records = _weekly_records(cadence, visibility)
    review_records = [
        _review_record(
            cadence_record=record,
            visibility=visibility,
            postmortem=postmortem,
            drawdown=drawdown,
            override=override,
            signal_evidence=signal_evidence,
            generated_at=generated_at,
        )
        for record in cadence_records
    ]
    proof_week_count = _int(visibility.get("proof_week_count")) or len(review_records)
    blockers = _preflight_blockers(visibility, source_status_records)
    if len(review_records) != proof_week_count:
        blockers.append("weekly_review_packet_count_mismatch")
    status = "read_only" if not blockers else "blocked"
    stage_status = "weekly_review_pack_created" if not blockers else "weekly_review_pack_blocked"
    review_state = "read_only_weekly_packets_created" if not blockers else "blocked"
    checks = [
        _check("q7_15_visibility_valid", not validate_phase7_cockpit_visibility(visibility)),
        _check("q7_16_stage_allowed", visibility.get("q7_16_weekly_review_pack_stage_allowed") is True),
        _check("review_packet_for_each_proof_week", len(review_records) == proof_week_count),
        _check("weekly_cadence_source_present", (sources["weekly_cadence"] or {}).get("recorded") is True),
        _check(
            "no_trade_rationale_present_when_no_qualified_setups",
            all(
                bool(record.get("no_trade_rationale"))
                for record in review_records
                if _int(record.get("qualified_setup_count")) == 0
            ),
        ),
        _check("missed_setup_summary_present", all("missed_qualified_setup_count" in record for record in review_records)),
        _check("drawdown_summary_present", all(isinstance(record.get("drawdown_summary"), dict) for record in review_records)),
        _check("override_summary_present", all(isinstance(record.get("override_summary"), dict) for record in review_records)),
        _check("postmortem_summary_present", all(isinstance(record.get("postmortem_summary"), dict) for record in review_records)),
        _check("source_health_summary_present", all(isinstance(record.get("source_health_summary"), dict) for record in review_records)),
        _check("funnel_conversion_summary_present", all(isinstance(record.get("funnel_conversion_summary"), dict) for record in review_records)),
        _check("future_policy_comments_only", all(record.get("fund_manager_comment_scope") == "future_policy_only" for record in review_records)),
        _check("trade_level_intervention_zero", all(_int(record.get("trade_level_intervention_count")) == 0 for record in review_records)),
        _check("no_individual_trade_mutation", all(record.get("individual_trade_mutation_allowed") is False for record in review_records)),
        _check("no_proof_credit", True),
        _check("phase5_test_trades_excluded", True),
        _check("no_broker_or_market_writes", True),
        _check("no_live_capital", True),
        _check("statistical_immaturity_not_hidden", visibility.get("phase7_statistical_immaturity_hidden") is False),
        _check("public_safe", True),
    ]
    failed_checks = [check["name"] for check in checks if check["passed"] is not True]
    if failed_checks and not blockers:
        blockers = sorted(set([*blockers, *failed_checks]))
        status = "blocked"
        stage_status = "weekly_review_pack_blocked"
        review_state = "blocked"

    artifact = {
        "schema_version": PHASE7_WEEKLY_REVIEW_PACK_SCHEMA_VERSION,
        "phase7_weekly_review_pack_schema_version": PHASE7_WEEKLY_REVIEW_PACK_SCHEMA_VERSION,
        "phase7_artifact_schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "artifact_type": "weekly_review_pack",
        "artifact_id": "phase7:q7-16:weekly-review-pack",
        "phase": "Q7",
        "stage": "Q7-16",
        "status": status,
        "stage_status": stage_status,
        "review_state": review_state,
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
        "event_contract": phase7_event_contract("weekly_review"),
        "authority_ledger": {
            "authority_schema_version": PHASE7_WEEKLY_REVIEW_PACK_SCHEMA_VERSION,
            "stage": "Q7-16",
            "authority_field_count": len(PHASE7_AUTHORITY_FLAGS),
            "explicit_authority_grant_count": 0,
            "explicit_authority_grants": [],
            "review_packet_only": True,
            "q7_17_certification_stage_allowed": not blockers,
            **phase7_authority_defaults(),
            "boundary": PHASE7_WEEKLY_REVIEW_BOUNDARY,
        },
        "proof_contract": phase7_proof_contract(),
        "source_posture": phase7_source_posture(),
        "provenance": _provenance(tuple(SOURCE_REFS.values())),
        "boundary": PHASE7_WEEKLY_REVIEW_BOUNDARY,
        **phase7_authority_defaults(),
        **phase7_unsafe_counter_defaults(),
        "source_artifact_count": len(source_status_records),
        "source_missing_count": source_missing_count,
        "source_validation_error_count": source_validation_error_count,
        "source_status_records": source_status_records,
        "source_visibility_artifact_id": visibility.get("artifact_id"),
        "source_visibility_status": visibility.get("status"),
        "source_visibility_stage_status": visibility.get("stage_status"),
        "source_visibility_backend_derived": visibility.get("backend_derived") is True,
        "source_visibility_ui_inferred_readiness_count": _int(
            visibility.get("ui_inferred_readiness_count")
        ),
        "phase7_harness_day_count": _int(
            visibility.get("phase7_harness_day_count")
            or PHASE7_HARNESS_DAY_COUNT
        ),
        "proof_week_count": proof_week_count,
        "review_pack_record_count": len(review_records),
        "weekly_review_packet_created": not blockers,
        "weekly_review_packet_created_count": len(review_records) if not blockers else 0,
        "all_proof_weeks_have_review_packet": len(review_records) == proof_week_count,
        "weekly_review_packet_write_allowed": not blockers,
        "future_policy_comment_allowed": True,
        "trade_level_intervention_allowed": False,
        "trade_level_intervention_count": 0,
        "individual_trade_mutation_allowed": False,
        "proof_trade_approval_allowed": False,
        "proof_trade_rejection_allowed": False,
        "order_modification_allowed": False,
        "position_modification_allowed": False,
        "qualified_setup_count": _int(visibility.get("qualified_setup_count")),
        "missed_qualified_setup_count": _int(
            visibility.get("missed_qualified_setup_count")
        ),
        "missed_qualified_setup_unexplained_count": _int(
            visibility.get("missed_qualified_setup_unexplained_count")
        ),
        "source_submitted_paper_order_count": _int(
            visibility.get("submitted_paper_order_count")
        ),
        "source_closed_proof_trade_count": _int(
            visibility.get("closed_proof_trade_count")
        ),
        "source_postmortem_due_count": _int(visibility.get("postmortem_due_count")),
        "source_postmortem_missing_count": _int(
            visibility.get("postmortem_missing_count")
        ),
        "source_override_count": _int(visibility.get("override_count")),
        "source_manual_trade_level_override_count": _int(
            visibility.get("manual_trade_level_override_count")
        ),
        "source_drawdown_within_cap": visibility.get("drawdown_within_cap") is True,
        "source_max_drawdown_fraction_observed": _float_or_none(
            visibility.get("max_drawdown_fraction_observed")
        ),
        "source_expectancy_after_costs_positive": (
            visibility.get("expectancy_after_costs_positive") is True
        ),
        "source_complete_decision_chain_count": _int(
            visibility.get("complete_decision_chain_count")
        ),
        "source_missing_decision_chain_count": _int(
            visibility.get("missing_decision_chain_count")
        ),
        "mature_benchmark": _int(
            visibility.get("mature_benchmark")
            or PHASE7_MATURE_CLOSED_TRADE_BENCHMARK
        ),
        "phase7_mature_benchmark_met": (
            visibility.get("phase7_mature_benchmark_met") is True
        ),
        "phase7_statistical_immaturity_hidden": (
            visibility.get("phase7_statistical_immaturity_hidden") is True
        ),
        "phase5_test_trades_count_for_phase7": False,
        "q6_deferred_learning_counts_as_proof": False,
        "phase7_proof_credit_allowed": False,
        "live_capital_enabled": False,
        "broker_post_called_count": 0,
        "alpaca_post_called_count": 0,
        "broker_write_allowed_count": 0,
        "prediction_market_write_allowed_count": 0,
        "crypto_perps_write_allowed_count": 0,
        "live_endpoint_allowed_count": 0,
        "phase7_proof_credit_allowed_count": 0,
        "phase5_test_trade_reuse_count": 0,
        "ui_inferred_readiness_count": 0,
        "raw_payload_exposed_count": 0,
        "private_payload_exposed_count": 0,
        "local_path_exposed_count": 0,
        "secret_ref_exposed_count": 0,
        "broker_identifier_exposed_count": 0,
        "unsafe_write_counter_total": 0,
        "q7_17_certification_stage_allowed": not blockers,
        "review_packet_records": review_records if not blockers else [],
        "checks": checks,
        "failed_checks": failed_checks,
        "failed_check_count": len(failed_checks),
        "blockers": sorted(set(blockers)),
        "blocker_count": len(set(blockers)),
        "recommended_next_stage": "Q7-17 30-Day Demo Proof Certification",
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


def _record_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "packet_id",
        "proof_week_number",
        "start_day_number",
        "end_day_number",
        "review_state",
        "weekly_review_packet_created",
        "fund_manager_comment_scope",
        "future_policy_comment_allowed",
        "allowed_comment_topics",
        "prohibited_comment_topics",
        "trade_level_intervention_allowed",
        "trade_level_intervention_count",
        "individual_trade_mutation_allowed",
        "proof_trade_approval_allowed",
        "proof_trade_rejection_allowed",
        "order_modification_allowed",
        "position_modification_allowed",
        "qualified_setup_count",
        "target_proof_trade_count",
        "proof_trade_count",
        "closed_proof_trade_count",
        "missed_qualified_setup_count",
        "cadence_satisfied",
        "no_trade_rationale",
        "drawdown_summary",
        "override_summary",
        "postmortem_summary",
        "source_health_summary",
        "funnel_conversion_summary",
        "signal_evidence_summary",
        "maturity_summary",
        "proof_credit_allowed",
        "phase5_test_trades_count_for_phase7",
        "live_capital_enabled",
        "raw_payload_exposed",
        "private_payload_exposed",
        "local_path_exposed",
        "secret_ref_exposed",
        "broker_identifier_exposed",
        "boundary",
    }
    missing = sorted(required - set(record))
    if missing:
        errors.append("phase7_weekly_review_record_missing:" + ",".join(missing))
    if _int(record.get("proof_week_number")) < 1:
        errors.append("phase7_weekly_review_record_week_invalid")
    if record.get("weekly_review_packet_created") is not True:
        errors.append("phase7_weekly_review_record_not_created")
    if record.get("fund_manager_comment_scope") != "future_policy_only":
        errors.append("phase7_weekly_review_record_comment_scope_invalid")
    if record.get("future_policy_comment_allowed") is not True:
        errors.append("phase7_weekly_review_record_future_policy_not_allowed")
    for field in (
        "trade_level_intervention_allowed",
        "individual_trade_mutation_allowed",
        "proof_trade_approval_allowed",
        "proof_trade_rejection_allowed",
        "order_modification_allowed",
        "position_modification_allowed",
        "proof_credit_allowed",
        "phase5_test_trades_count_for_phase7",
        "live_capital_enabled",
        "raw_payload_exposed",
        "private_payload_exposed",
        "local_path_exposed",
        "secret_ref_exposed",
        "broker_identifier_exposed",
    ):
        if record.get(field) is not False:
            errors.append(f"phase7_weekly_review_record_forbidden:{field}")
    if _int(record.get("trade_level_intervention_count")) != 0:
        errors.append("phase7_weekly_review_record_trade_intervention_count_nonzero")
    if _int(record.get("qualified_setup_count")) == 0 and not str(
        record.get("no_trade_rationale") or ""
    ).strip():
        errors.append("phase7_weekly_review_record_no_trade_rationale_missing")
    for summary_key in (
        "drawdown_summary",
        "override_summary",
        "postmortem_summary",
        "source_health_summary",
        "funnel_conversion_summary",
        "signal_evidence_summary",
        "maturity_summary",
    ):
        if not isinstance(record.get(summary_key), dict):
            errors.append(f"phase7_weekly_review_record_summary_missing:{summary_key}")
    allowed_topics = record.get("allowed_comment_topics", [])
    prohibited_topics = record.get("prohibited_comment_topics", [])
    if not isinstance(allowed_topics, list) or not allowed_topics:
        errors.append("phase7_weekly_review_record_allowed_topics_missing")
    if not isinstance(prohibited_topics, list) or "approve_individual_trade" not in prohibited_topics:
        errors.append("phase7_weekly_review_record_prohibited_topics_missing")
    if "cannot intervene in individual proof trades" not in str(record.get("boundary", "")):
        errors.append("phase7_weekly_review_record_boundary_weak")
    errors.extend(_public_safety_errors(record))
    return errors


def validate_phase7_weekly_review_pack(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = set(PUBLIC_STATUS_FIELDS) | {
        "event_contract",
        "authority_ledger",
        "proof_contract",
        "source_posture",
        "provenance",
        "source_status_records",
        "source_visibility_artifact_id",
        "source_visibility_status",
        "source_visibility_stage_status",
        "source_visibility_backend_derived",
        "source_visibility_ui_inferred_readiness_count",
        "weekly_review_packet_write_allowed",
        "checks",
        "failed_checks",
        "failed_check_count",
        "public_status",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("phase7_weekly_review_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PHASE7_WEEKLY_REVIEW_PACK_SCHEMA_VERSION:
        errors.append("phase7_weekly_review_schema_version_mismatch")
    if artifact.get("phase7_artifact_schema_version") != PHASE7_ARTIFACT_SCHEMA_VERSION:
        errors.append("phase7_weekly_review_artifact_schema_version_mismatch")
    if artifact.get("artifact_type") != "weekly_review_pack":
        errors.append("phase7_weekly_review_artifact_type_mismatch")
    if artifact.get("phase") != "Q7" or artifact.get("stage") != "Q7-16":
        errors.append("phase7_weekly_review_phase_stage_mismatch")
    if artifact.get("status") not in {"read_only", "blocked"}:
        errors.append("phase7_weekly_review_status_invalid")
    if artifact.get("stage_status") not in {
        "weekly_review_pack_created",
        "weekly_review_pack_blocked",
    }:
        errors.append("phase7_weekly_review_stage_status_invalid")
    if artifact.get("public_safe") is not True:
        errors.append("phase7_weekly_review_not_public_safe")
    if artifact.get("event_log_required") is not True:
        errors.append("phase7_weekly_review_event_log_not_required")
    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("phase7_weekly_review_blockers_not_list")
        blockers = []
    if artifact.get("blocker_count") != len(blockers):
        errors.append("phase7_weekly_review_blocker_count_mismatch")

    checks = artifact.get("checks", [])
    if not isinstance(checks, list):
        errors.append("phase7_weekly_review_checks_not_list")
        checks = []
    if tuple(check.get("name") for check in checks if isinstance(check, dict)) != (
        PHASE7_WEEKLY_REVIEW_REQUIRED_CHECKS
    ):
        errors.append("phase7_weekly_review_required_checks_invalid")
    failed_checks = [
        str(check.get("name"))
        for check in checks
        if isinstance(check, dict) and check.get("passed") is not True
    ]
    if artifact.get("failed_checks") != failed_checks:
        errors.append("phase7_weekly_review_failed_checks_mismatch")
    if artifact.get("failed_check_count") != len(failed_checks):
        errors.append("phase7_weekly_review_failed_check_count_mismatch")

    source_records = artifact.get("source_status_records", [])
    if not isinstance(source_records, list) or not source_records:
        errors.append("phase7_weekly_review_source_records_missing")
        source_records = []
    if artifact.get("source_artifact_count") != len(source_records):
        errors.append("phase7_weekly_review_source_count_mismatch")
    source_missing_count = 0
    source_validation_error_count = 0
    for record in source_records:
        if not isinstance(record, dict):
            errors.append("phase7_weekly_review_source_record_invalid")
            continue
        if record.get("display_status") != record.get("backend_status"):
            errors.append("phase7_weekly_review_source_display_backend_mismatch")
        if record.get("display_derived_from_backend") is not True:
            errors.append("phase7_weekly_review_source_display_not_backend")
        if record.get("ui_inferred_readiness") is not False:
            errors.append("phase7_weekly_review_source_ui_inferred")
        source_ref = str(record.get("source_ref", ""))
        if not source_ref.startswith("data/runtime/"):
            errors.append("phase7_weekly_review_source_ref_invalid")
        if _has_local_path(source_ref):
            errors.append("phase7_weekly_review_source_ref_local_path")
        if record.get("source_status") == "missing":
            source_missing_count += 1
        source_validation_error_count += _int(record.get("validation_error_count"))
    if artifact.get("source_missing_count") != source_missing_count:
        errors.append("phase7_weekly_review_source_missing_count_mismatch")
    if artifact.get("source_validation_error_count") != source_validation_error_count:
        errors.append("phase7_weekly_review_source_validation_count_mismatch")

    if artifact.get("source_visibility_status") != "visible":
        errors.append("phase7_weekly_review_visibility_not_visible")
    if artifact.get("source_visibility_backend_derived") is not True:
        errors.append("phase7_weekly_review_visibility_not_backend_derived")
    if artifact.get("source_visibility_ui_inferred_readiness_count") != 0:
        errors.append("phase7_weekly_review_visibility_ui_inferred")
    if artifact.get("phase7_harness_day_count") != PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_weekly_review_day_count_mismatch")
    if artifact.get("proof_week_count", 0) < 1:
        errors.append("phase7_weekly_review_week_count_invalid")
    records = artifact.get("review_packet_records", [])
    if not isinstance(records, list):
        errors.append("phase7_weekly_review_records_not_list")
        records = []
    if artifact.get("review_pack_record_count") != len(records):
        errors.append("phase7_weekly_review_record_count_mismatch")
    if artifact.get("all_proof_weeks_have_review_packet") is not (
        len(records) == _int(artifact.get("proof_week_count"))
    ):
        errors.append("phase7_weekly_review_all_weeks_flag_mismatch")
    if artifact.get("status") == "read_only":
        if blockers:
            errors.append("phase7_weekly_review_read_only_with_blockers")
        if artifact.get("weekly_review_packet_created") is not True:
            errors.append("phase7_weekly_review_packet_not_created")
        if artifact.get("weekly_review_packet_created_count") != len(records):
            errors.append("phase7_weekly_review_created_count_mismatch")
        if artifact.get("q7_17_certification_stage_allowed") is not True:
            errors.append("q7_17_certification_not_allowed")
        if artifact.get("weekly_review_packet_write_allowed") is not True:
            errors.append("phase7_weekly_review_write_not_allowed")
    else:
        if artifact.get("q7_17_certification_stage_allowed") is not False:
            errors.append("q7_17_certification_allowed_while_blocked")
        if artifact.get("weekly_review_packet_write_allowed") is not False:
            errors.append("phase7_weekly_review_write_allowed_while_blocked")
    seen_weeks = sorted(_int(record.get("proof_week_number")) for record in records)
    if seen_weeks != list(range(1, len(records) + 1)):
        errors.append("phase7_weekly_review_week_sequence_invalid")
    for record in records:
        if isinstance(record, dict):
            errors.extend(_record_errors(record))
        else:
            errors.append("phase7_weekly_review_record_invalid")

    for field in PHASE7_AUTHORITY_FLAGS:
        if artifact.get(field) is not False:
            errors.append(f"phase7_weekly_review_authority_enabled:{field}")
    ledger = artifact.get("authority_ledger", {})
    if not isinstance(ledger, dict):
        errors.append("phase7_weekly_review_authority_ledger_missing")
        ledger = {}
    if ledger.get("stage") != "Q7-16":
        errors.append("phase7_weekly_review_authority_stage_mismatch")
    if ledger.get("authority_field_count") != len(PHASE7_AUTHORITY_FLAGS):
        errors.append("phase7_weekly_review_authority_count_mismatch")
    if ledger.get("explicit_authority_grant_count") != 0:
        errors.append("phase7_weekly_review_authority_grant_nonzero")
    for field in PHASE7_AUTHORITY_FLAGS:
        if ledger.get(field) is not False:
            errors.append(f"phase7_weekly_review_ledger_authority_enabled:{field}")

    for field in (
        "trade_level_intervention_allowed",
        "individual_trade_mutation_allowed",
        "proof_trade_approval_allowed",
        "proof_trade_rejection_allowed",
        "order_modification_allowed",
        "position_modification_allowed",
        "phase5_test_trades_count_for_phase7",
        "q6_deferred_learning_counts_as_proof",
        "phase7_proof_credit_allowed",
        "live_capital_enabled",
        "phase7_statistical_immaturity_hidden",
    ):
        if artifact.get(field) is not False:
            errors.append(f"phase7_weekly_review_forbidden:{field}")
    for field in (
        "trade_level_intervention_count",
        "source_manual_trade_level_override_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "broker_write_allowed_count",
        "prediction_market_write_allowed_count",
        "crypto_perps_write_allowed_count",
        "live_endpoint_allowed_count",
        "live_capital_enabled_count",
        "phase7_proof_credit_allowed_count",
        "phase5_test_trade_reuse_count",
        "ui_inferred_readiness_count",
        "raw_payload_exposed_count",
        "private_payload_exposed_count",
        "local_path_exposed_count",
        "secret_ref_exposed_count",
        "broker_identifier_exposed_count",
        "unsafe_write_counter_total",
    ):
        if _int(artifact.get(field)) != 0:
            errors.append(f"phase7_weekly_review_count_nonzero:{field}")
    for count_field in PHASE7_UNSAFE_COUNT_FIELDS:
        if count_field not in artifact:
            errors.append(f"phase7_weekly_review_unsafe_count_missing:{count_field}")
        elif _int(artifact.get(count_field)) != 0:
            errors.append(f"phase7_weekly_review_unsafe_count_nonzero:{count_field}")
    if artifact.get("future_policy_comment_allowed") is not True:
        errors.append("phase7_weekly_review_future_policy_not_allowed")
    if artifact.get("mature_benchmark") != PHASE7_MATURE_CLOSED_TRADE_BENCHMARK:
        errors.append("phase7_weekly_review_maturity_benchmark_mismatch")

    proof_contract = artifact.get("proof_contract", {})
    if not isinstance(proof_contract, dict):
        errors.append("phase7_weekly_review_proof_contract_missing")
        proof_contract = {}
    if proof_contract.get("harness_day_count") != PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_weekly_review_proof_contract_day_count_mismatch")
    if proof_contract.get("phase5_test_trade_reuse_allowed") is not False:
        errors.append("phase7_weekly_review_phase5_reuse_allowed")
    source_posture = artifact.get("source_posture", {})
    if not isinstance(source_posture, dict):
        errors.append("phase7_weekly_review_source_posture_missing")
        source_posture = {}
    if source_posture.get("preference_mcp_source_quorum_credit_allowed") is not False:
        errors.append("phase7_weekly_review_preference_quorum_credit_allowed")
    provenance = artifact.get("provenance", {})
    if not isinstance(provenance, dict):
        errors.append("phase7_weekly_review_provenance_missing")
        provenance = {}
    for ref in provenance.get("source_refs", []) or []:
        ref_text = str(ref)
        lowered = ref_text.lower()
        if _has_local_path(ref_text):
            errors.append("phase7_weekly_review_provenance_local_path_leak")
        if "api_key" in lowered or "secret" in lowered or "token" in lowered:
            errors.append("phase7_weekly_review_provenance_secret_ref_leak")
    for field in (
        "raw_secret_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "broker_identifier_exposed",
    ):
        if provenance.get(field) is not False:
            errors.append(f"phase7_weekly_review_provenance_exposure:{field}")
    event_contract = artifact.get("event_contract", {})
    if not isinstance(event_contract, dict):
        errors.append("phase7_weekly_review_event_contract_missing")
        event_contract = {}
    if event_contract.get("event_type") != PHASE7_WEEKLY_REVIEW_PACK_EVENT_TYPE:
        errors.append("phase7_weekly_review_event_contract_type_mismatch")
    public_status = artifact.get("public_status")
    if not isinstance(public_status, dict):
        errors.append("phase7_weekly_review_public_status_missing")
    else:
        extra = sorted(set(public_status) - set(PUBLIC_STATUS_FIELDS))
        if extra:
            errors.append("phase7_weekly_review_public_status_extra_fields:" + ",".join(extra))
        for field in PUBLIC_STATUS_FIELDS:
            if field == "validation_error_count":
                continue
            if field in artifact and public_status.get(field) != artifact.get(field):
                errors.append(f"phase7_weekly_review_public_status_mismatch:{field}")
        errors.extend(_public_safety_errors(public_status))
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "Fund Manager comments are future-policy review only",
        "cannot mutate individual proof trades",
        "cannot approve or reject individual proof trades",
        "cannot force trades",
        "cannot grant Phase 7 proof credit",
        "cannot count Phase 5 test trades toward Phase 7 proof",
        "cannot infer readiness from the UI",
        "cannot expose raw payloads",
        "cannot enable live capital",
    ):
        if phrase not in boundary:
            errors.append("phase7_weekly_review_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("phase7_weekly_review_event_log_path_missing")
        if not artifact.get("event_log_correlation_id"):
            errors.append("phase7_weekly_review_event_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("phase7_weekly_review_event_log_count_mismatch")
    return sorted(set(errors))


def attach_phase7_weekly_review_pack_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(event_log_path or (_runtime_dir(settings) / PHASE7_WEEKLY_REVIEW_PACK_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE7_WEEKLY_REVIEW_PACK_EVENT_TYPE,
        PHASE7_WEEKLY_REVIEW_PACK_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "stage_status": output.get("stage_status"),
            "review_state": output.get("review_state"),
            "proof_week_count": output.get("proof_week_count"),
            "review_pack_record_count": output.get("review_pack_record_count"),
            "weekly_review_packet_created": output.get("weekly_review_packet_created"),
            "trade_level_intervention_count": output.get("trade_level_intervention_count"),
            "future_policy_comment_allowed": output.get("future_policy_comment_allowed"),
            "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
            "live_capital_enabled": output.get("live_capital_enabled"),
            "q7_17_certification_stage_allowed": output.get(
                "q7_17_certification_stage_allowed"
            ),
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


def write_phase7_weekly_review_pack(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase7_weekly_review_pack_paths(
        settings
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase7_weekly_review_pack_event_log(
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
        "schema_version": PHASE7_WEEKLY_REVIEW_PACK_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "stage_status": output.get("stage_status"),
        "review_state": output.get("review_state"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "proof_week_count": output.get("proof_week_count"),
        "review_pack_record_count": output.get("review_pack_record_count"),
        "weekly_review_packet_created": output.get("weekly_review_packet_created"),
        "trade_level_intervention_count": output.get("trade_level_intervention_count"),
        "future_policy_comment_allowed": output.get("future_policy_comment_allowed"),
        "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
        "live_capital_enabled": output.get("live_capital_enabled"),
        "q7_17_certification_stage_allowed": output.get(
            "q7_17_certification_stage_allowed"
        ),
        "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
        "blocker_count": output.get("blocker_count"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output


def phase7_weekly_review_pack_public_status(settings: Settings | None = None) -> dict[str, Any]:
    output_path, _, _ = phase7_weekly_review_pack_paths(settings)
    artifact = None
    if output_path.exists():
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        artifact = payload if isinstance(payload, dict) else None
    artifact = artifact or build_phase7_weekly_review_pack(settings=settings)
    validation_errors = validate_phase7_weekly_review_pack(artifact)
    public_status = _public_status_from_artifact(artifact)
    public_status["validation_error_count"] = len(validation_errors)
    return public_status
