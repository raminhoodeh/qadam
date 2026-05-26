"""Q7-17 Phase 7 Demo Proof certification gate.

This stage aggregates the Phase 7 demo-proof evidence and decides whether the
run can be certified. It is intentionally fail-closed: a clean 30-day
operational result is preserved separately from the 100 closed proof-trade
maturity benchmark, and live capital remains disabled even after certification.
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
from orchestrator.phase7_calendar_harness import PHASE7_CALENDAR_HARNESS_RUNTIME_ARTIFACT
from orchestrator.phase7_cockpit_visibility import PHASE7_COCKPIT_VISIBILITY_RUNTIME_ARTIFACT
from orchestrator.phase7_demo_proof_run import PHASE7_DEMO_PROOF_RUN_RUNTIME_ARTIFACT
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
from orchestrator.phase7_weekly_cadence import PHASE7_WEEKLY_CADENCE_RUNTIME_ARTIFACT
from orchestrator.phase7_weekly_review_pack import (
    PHASE7_WEEKLY_REVIEW_PACK_RUNTIME_ARTIFACT,
    build_phase7_weekly_review_pack,
    validate_phase7_weekly_review_pack,
    write_phase7_weekly_review_pack,
)


PHASE7_CERTIFICATION_SCHEMA_VERSION = 1
PHASE7_CERTIFICATION_RUNTIME_ARTIFACT = "phase7_certification.json"
PHASE7_CERTIFICATION_HISTORY = "phase7_certification_history.jsonl"
PHASE7_CERTIFICATION_EVENT_LOG = "phase7_certification_events.jsonl"
PHASE7_CERTIFICATION_EVENT_TYPE = PHASE7_EVENT_TYPES["certification"]
PHASE7_CERTIFICATION_COMPONENT = "phase7_certification"

SOURCE_REFS: dict[str, str] = {
    "weekly_review": f"data/runtime/{PHASE7_WEEKLY_REVIEW_PACK_RUNTIME_ARTIFACT}",
    "cockpit_visibility": f"data/runtime/{PHASE7_COCKPIT_VISIBILITY_RUNTIME_ARTIFACT}",
    "calendar": f"data/runtime/{PHASE7_CALENDAR_HARNESS_RUNTIME_ARTIFACT}",
    "demo_proof_run": f"data/runtime/{PHASE7_DEMO_PROOF_RUN_RUNTIME_ARTIFACT}",
    "weekly_cadence": f"data/runtime/{PHASE7_WEEKLY_CADENCE_RUNTIME_ARTIFACT}",
    "proof_lifecycle": f"data/runtime/{PHASE7_PROOF_LIFECYCLE_RUNTIME_ARTIFACT}",
    "postmortem": f"data/runtime/{PHASE7_PROOF_POSTMORTEM_RUNTIME_ARTIFACT}",
    "performance": f"data/runtime/{PHASE7_PERFORMANCE_EVALUATOR_RUNTIME_ARTIFACT}",
    "drawdown": f"data/runtime/{PHASE7_DRAWDOWN_RISK_SENTINEL_RUNTIME_ARTIFACT}",
    "override": f"data/runtime/{PHASE7_OVERRIDE_DETECTOR_RUNTIME_ARTIFACT}",
    "signal_evidence": f"data/runtime/{PHASE7_SIGNAL_FUNNEL_EVIDENCE_RUNTIME_ARTIFACT}",
    "maturity": f"data/runtime/{PHASE7_MATURITY_TRACKER_RUNTIME_ARTIFACT}",
}

PHASE7_CERTIFICATION_BOUNDARY = (
    "Q7-17 is a certification gate only. It can certify Phase 7 only when the "
    "30 consecutive calendar day demo-proof run is complete, weekly cadence is "
    "satisfied under the qualified-setup rule, expectancy after costs is "
    "positive, drawdown remains within the 20 percent cap, manual trade-level "
    "overrides are zero, postmortem coverage is complete, source and signal "
    "chains are complete, and the 100 closed proof-trade maturity benchmark is "
    "met. It preserves a clean 30-day operational result separately from "
    "statistical maturity, cannot hide statistical immaturity, cannot force "
    "trades, cannot mutate individual proof trades, cannot grant Phase 7 proof "
    "credit, cannot count Phase 5 test trades toward Phase 7 proof, cannot "
    "call broker POST routes, cannot call Alpaca POST routes, cannot write "
    "prediction-market or crypto-perps orders, cannot infer readiness from "
    "the UI, cannot expose raw payloads or secrets, cannot approve live "
    "promotion, and cannot enable live capital."
)

PHASE7_CERTIFICATION_REQUIRED_GATES: tuple[str, ...] = (
    "q7_16_weekly_review_pack",
    "thirty_day_calendar_complete",
    "weekly_cadence_satisfied",
    "positive_expectancy_after_costs",
    "drawdown_within_cap",
    "zero_manual_trade_level_overrides",
    "postmortem_coverage_complete",
    "source_signal_chains_complete",
    "maturity_classified_and_benchmark_met",
)

PUBLIC_STATUS_FIELDS: tuple[str, ...] = (
    "schema_version",
    "phase7_certification_schema_version",
    "phase7_artifact_schema_version",
    "artifact_type",
    "artifact_id",
    "phase",
    "stage",
    "status",
    "stage_status",
    "certification_state",
    "generated_at",
    "public_safe",
    "recorded",
    "event_log_required",
    "event_log_written",
    "event_log_event_count",
    "validation_error_count",
    "phase7_demo_proof_certified",
    "phase7_demo_proof_exit_gate",
    "phase7_30_day_operational_result_clean",
    "phase7_30_day_operational_result_preserved",
    "phase7_30_day_operational_result_erased_by_immaturity",
    "phase7_30_day_run_complete",
    "phase7_harness_day_count",
    "completed_calendar_day_count",
    "proof_week_count",
    "weekly_cadence_satisfied_count",
    "weekly_cadence_failed_count",
    "weekly_review_packet_created_count",
    "qualified_setup_count",
    "missed_qualified_setup_count",
    "missed_qualified_setup_unexplained_count",
    "evaluated_trade_count",
    "expectancy_after_costs_gbp",
    "expectancy_after_costs_positive",
    "drawdown_within_cap",
    "drawdown_cap_breached",
    "max_drawdown_fraction_observed",
    "risk_halt_active",
    "override_count",
    "manual_trade_level_override_count",
    "sample_contaminated",
    "closed_proof_trade_count",
    "postmortem_due_count",
    "postmortem_missing_count",
    "postmortem_reviewed_count",
    "postmortem_coverage_satisfied",
    "complete_decision_chain_count",
    "missing_decision_chain_count",
    "private_priors_only_proof_trade_count",
    "source_signal_chains_complete",
    "maturity_state",
    "maturity_classification",
    "mature_benchmark",
    "phase7_mature_benchmark_met",
    "phase7_mature_status_blocked",
    "phase7_statistically_immature",
    "phase7_statistical_immaturity_hidden",
    "phase7_certification_blocked_by_maturity",
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
    "live_capital_enabled_count",
    "phase7_proof_credit_allowed_count",
    "phase5_test_trade_reuse_count",
    "ui_inferred_readiness_count",
    "unsafe_write_counter_total",
    "source_artifact_count",
    "source_missing_count",
    "source_validation_error_count",
    "certification_gate_count",
    "certification_gate_passed_count",
    "certification_gate_blocked_count",
    "certification_gate_records",
    "certification_blockers",
    "certification_blocker_count",
    "q7_18_live_promotion_review_stage_allowed",
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


def _source_weekly_review(settings: Settings) -> dict[str, Any]:
    artifact = _read_json_ref(SOURCE_REFS["weekly_review"], settings)
    if artifact:
        return artifact
    weekly_review = build_phase7_weekly_review_pack(settings=settings)
    _, _, _, written = write_phase7_weekly_review_pack(
        weekly_review,
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
        SOURCE_REFS["calendar"],
        SOURCE_REFS["weekly_cadence"],
        SOURCE_REFS["weekly_review"],
        SOURCE_REFS["cockpit_visibility"],
    ]
    provenance["governance_refs"] = [
        SOURCE_REFS["drawdown"],
        SOURCE_REFS["override"],
        SOURCE_REFS["maturity"],
    ]
    provenance["proof_lifecycle_refs"] = [
        SOURCE_REFS["proof_lifecycle"],
        SOURCE_REFS["postmortem"],
    ]
    return provenance


def _maturity_classification(
    *,
    run_complete: bool,
    closed_trade_count: int,
    maturity_state: str,
) -> str:
    if closed_trade_count >= PHASE7_MATURE_CLOSED_TRADE_BENCHMARK:
        return "statistically_mature_100_closed_trades"
    if run_complete:
        return "statistically_immature_after_30_days_under_100_closed_trades"
    if closed_trade_count:
        return "statistically_immature_in_progress"
    if maturity_state:
        return maturity_state
    return "no_sample"


def _certification_gate(
    name: str,
    label: str,
    passed: bool,
    *,
    blocker: str,
    detail: Any = None,
) -> dict[str, Any]:
    backend_status = "passed" if passed else "blocked"
    return {
        "gate_name": name,
        "label": label,
        "backend_status": backend_status,
        "display_status": backend_status,
        "display_derived_from_backend": True,
        "ui_inferred_readiness": False,
        "gate_passed": passed,
        "blocker": None if passed else blocker,
        "detail": detail,
        "public_safe": True,
    }


def _public_status_from_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    output = {field: deepcopy(artifact.get(field)) for field in PUBLIC_STATUS_FIELDS if field in artifact}
    output["validation_error_count"] = len(artifact.get("validation_errors", []) or [])
    return output


def _refresh_validation(artifact: dict[str, Any]) -> dict[str, Any]:
    artifact.setdefault("validation_errors", [])
    artifact["public_status"] = _public_status_from_artifact(artifact)
    for _ in range(2):
        artifact["validation_errors"] = validate_phase7_certification(artifact)
        artifact["validation_error_count"] = len(artifact["validation_errors"])
        artifact["public_status"] = _public_status_from_artifact(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "blocked"
        artifact["stage_status"] = "phase7_certification_validation_error"
        artifact["certification_state"] = "validation_error"
        artifact["phase7_demo_proof_certified"] = False
        artifact["phase7_demo_proof_exit_gate"] = False
        artifact["q7_18_live_promotion_review_stage_allowed"] = False
        artifact["public_status"] = _public_status_from_artifact(artifact)
    return artifact


def phase7_certification_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE7_CERTIFICATION_RUNTIME_ARTIFACT,
        runtime / PHASE7_CERTIFICATION_HISTORY,
        runtime / PHASE7_CERTIFICATION_EVENT_LOG,
    )


def build_phase7_certification(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    weekly_review = _source_weekly_review(settings)
    sources = {key: _read_json_ref(ref, settings) for key, ref in SOURCE_REFS.items()}
    sources["weekly_review"] = weekly_review
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
    demo_run = sources["demo_proof_run"] or {}
    cadence = sources["weekly_cadence"] or {}
    lifecycle = sources["proof_lifecycle"] or {}
    postmortem = sources["postmortem"] or {}
    performance = sources["performance"] or {}
    drawdown = sources["drawdown"] or {}
    override = sources["override"] or {}
    signal = sources["signal_evidence"] or {}
    maturity = sources["maturity"] or {}

    if demo_run:
        completed_days = _int(demo_run.get("completed_calendar_day_count"))
        run_complete = (
            demo_run.get("phase7_30_day_run_complete") is True
            and completed_days >= PHASE7_HARNESS_DAY_COUNT
        )
    else:
        completed_days = _int(
            maturity.get("completed_calendar_day_count")
            or visibility.get("completed_calendar_day_count")
        )
        run_complete = (
            maturity.get("phase7_30_day_run_complete") is True
            or visibility.get("phase7_30_day_run_complete") is True
            or completed_days >= PHASE7_HARNESS_DAY_COUNT
        )
    proof_week_count = _int(
        weekly_review.get("proof_week_count") or visibility.get("proof_week_count")
    )
    weekly_satisfied = _int(cadence.get("weekly_cadence_satisfied_count"))
    weekly_failed = _int(cadence.get("weekly_cadence_failed_count"))
    weekly_packet_count = _int(weekly_review.get("weekly_review_packet_created_count"))
    qualified_setup_count = _int(visibility.get("qualified_setup_count"))
    missed_setup_count = _int(visibility.get("missed_qualified_setup_count"))
    missed_unexplained = _int(
        visibility.get("missed_qualified_setup_unexplained_count")
        or cadence.get("missed_qualified_setup_unexplained_count")
    )
    closed_trade_count = _int(
        maturity.get("closed_proof_trade_count")
        or visibility.get("closed_proof_trade_count")
        or lifecycle.get("closed_proof_trade_count")
    )
    evaluated_trade_count = _int(performance.get("evaluated_trade_count"))
    expectancy_after_costs = _float_or_none(performance.get("expectancy_after_costs_gbp"))
    expectancy_positive = performance.get("expectancy_after_costs_positive") is True
    drawdown_within_cap = drawdown.get("drawdown_within_cap") is True
    drawdown_breached = drawdown.get("drawdown_cap_breached") is True
    risk_halt_active = drawdown.get("risk_halt_active") is True
    manual_override_count = _int(
        override.get("manual_trade_level_override_count")
        or signal.get("manual_trade_level_override_count")
    )
    override_count = _int(override.get("override_count"))
    sample_contaminated = override.get("sample_contaminated") is True
    postmortem_due_count = _int(postmortem.get("postmortem_due_count"))
    postmortem_missing_count = _int(postmortem.get("postmortem_missing_count"))
    postmortem_reviewed_count = _int(postmortem.get("postmortem_reviewed_count"))
    postmortem_coverage_satisfied = (
        postmortem_missing_count == 0
        and postmortem.get("phase7_certification_blocked_by_missing_postmortem") is not True
        and postmortem_due_count >= closed_trade_count
    )
    complete_decision_chain_count = _int(signal.get("complete_decision_chain_count"))
    missing_decision_chain_count = _int(signal.get("missing_decision_chain_count"))
    private_priors_only_count = _int(signal.get("private_priors_only_proof_trade_count"))
    source_signal_complete = (
        signal.get("phase7_certification_blocked_by_signal_evidence") is not True
        and signal.get("phase7_certification_blocked_by_override") is not True
        and signal.get("phase7_certification_blocked_by_contaminated_sample") is not True
        and missing_decision_chain_count == 0
        and private_priors_only_count == 0
    )
    maturity_state = str(maturity.get("maturity_state") or visibility.get("maturity_state") or "no_sample")
    mature_met = maturity.get("phase7_mature_benchmark_met") is True
    statistically_immature = maturity.get("phase7_statistically_immature") is True
    immaturity_hidden = (
        maturity.get("phase7_statistical_immaturity_hidden") is True
        or visibility.get("phase7_statistical_immaturity_hidden") is True
    )
    maturity_blocked = maturity.get("phase7_certification_blocked_by_maturity") is True
    maturity_classification = _maturity_classification(
        run_complete=run_complete,
        closed_trade_count=closed_trade_count,
        maturity_state=maturity_state,
    )

    q7_16_valid = not validate_phase7_weekly_review_pack(weekly_review)
    gate_inputs = (
        (
            "q7_16_weekly_review_pack",
            "Q7-16 weekly review pack exists for each proof week",
            q7_16_valid
            and weekly_review.get("status") == "read_only"
            and weekly_review.get("q7_17_certification_stage_allowed") is True
            and weekly_packet_count == proof_week_count
            and weekly_packet_count > 0,
            "q7_16_weekly_review_pack_not_ready",
            {
                "weekly_review_status": weekly_review.get("status"),
                "weekly_review_packet_created_count": weekly_packet_count,
                "proof_week_count": proof_week_count,
            },
        ),
        (
            "thirty_day_calendar_complete",
            "30 consecutive calendar days complete",
            run_complete and completed_days >= PHASE7_HARNESS_DAY_COUNT,
            "phase7_30_day_run_incomplete",
            {
                "completed_calendar_day_count": completed_days,
                "phase7_harness_day_count": PHASE7_HARNESS_DAY_COUNT,
            },
        ),
        (
            "weekly_cadence_satisfied",
            "Weekly cadence satisfied under qualified-setup rule",
            proof_week_count > 0
            and weekly_satisfied == proof_week_count
            and weekly_failed == 0
            and missed_unexplained == 0,
            "weekly_cadence_not_satisfied",
            {
                "weekly_cadence_satisfied_count": weekly_satisfied,
                "weekly_cadence_failed_count": weekly_failed,
                "missed_qualified_setup_unexplained_count": missed_unexplained,
            },
        ),
        (
            "positive_expectancy_after_costs",
            "Positive expectancy after costs",
            evaluated_trade_count > 0 and expectancy_positive,
            "positive_expectancy_after_costs_missing",
            {
                "evaluated_trade_count": evaluated_trade_count,
                "expectancy_after_costs_gbp": expectancy_after_costs,
                "expectancy_after_costs_positive": expectancy_positive,
            },
        ),
        (
            "drawdown_within_cap",
            "Drawdown remains within 20 percent cap",
            drawdown_within_cap and not drawdown_breached and not risk_halt_active,
            "drawdown_cap_or_risk_halt_not_clear",
            {
                "drawdown_within_cap": drawdown_within_cap,
                "drawdown_cap_breached": drawdown_breached,
                "risk_halt_active": risk_halt_active,
            },
        ),
        (
            "zero_manual_trade_level_overrides",
            "Zero manual trade-level overrides and clean sample",
            manual_override_count == 0 and override_count == 0 and not sample_contaminated,
            "manual_override_or_contaminated_sample",
            {
                "manual_trade_level_override_count": manual_override_count,
                "override_count": override_count,
                "sample_contaminated": sample_contaminated,
            },
        ),
        (
            "postmortem_coverage_complete",
            "Postmortem coverage exists for every closed proof trade",
            postmortem_coverage_satisfied,
            "postmortem_coverage_incomplete",
            {
                "closed_proof_trade_count": closed_trade_count,
                "postmortem_due_count": postmortem_due_count,
                "postmortem_missing_count": postmortem_missing_count,
            },
        ),
        (
            "source_signal_chains_complete",
            "Source and signal decision chains complete",
            source_signal_complete,
            "source_signal_chain_incomplete",
            {
                "complete_decision_chain_count": complete_decision_chain_count,
                "missing_decision_chain_count": missing_decision_chain_count,
                "private_priors_only_proof_trade_count": private_priors_only_count,
            },
        ),
        (
            "maturity_classified_and_benchmark_met",
            "Maturity classification explicit and 100-trade benchmark met",
            mature_met and not maturity_blocked and not immaturity_hidden,
            "phase7_maturity_benchmark_not_met",
            {
                "maturity_state": maturity_state,
                "maturity_classification": maturity_classification,
                "closed_proof_trade_count": closed_trade_count,
                "mature_benchmark": PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
                "phase7_mature_benchmark_met": mature_met,
                "phase7_certification_blocked_by_maturity": maturity_blocked,
                "phase7_statistical_immaturity_hidden": immaturity_hidden,
            },
        ),
    )
    gate_records = [
        _certification_gate(name, label, passed, blocker=blocker, detail=detail)
        for name, label, passed, blocker, detail in gate_inputs
    ]
    gate_blockers = [
        str(record.get("blocker"))
        for record in gate_records
        if record.get("gate_passed") is not True and record.get("blocker")
    ]
    source_blockers: list[str] = []
    if source_missing_count:
        source_blockers.append("phase7_certification_source_missing")
    if source_validation_error_count:
        source_blockers.append("phase7_certification_source_validation_errors")
    if immaturity_hidden:
        source_blockers.append("phase7_statistical_immaturity_hidden")

    phase5_test_trades_count_for_phase7 = False
    q6_deferred_learning_counts_as_proof = False
    phase7_30_day_operational_clean = all(
        record.get("gate_passed") is True
        for record in gate_records
        if record.get("gate_name") != "maturity_classified_and_benchmark_met"
    )
    blockers = sorted(set([*gate_blockers, *source_blockers]))
    phase7_demo_proof_certified = not blockers
    status = "certified" if phase7_demo_proof_certified else "blocked"
    if phase7_demo_proof_certified:
        stage_status = "phase7_demo_proof_certified"
        certification_state = "certified_mature_sample"
    elif phase7_30_day_operational_clean and not mature_met:
        stage_status = "phase7_operational_clean_but_maturity_blocked"
        certification_state = "blocked_by_maturity_benchmark"
    elif not run_complete:
        stage_status = "phase7_certification_blocked_run_incomplete"
        certification_state = "blocked_run_incomplete"
    else:
        stage_status = "phase7_certification_blocked"
        certification_state = "blocked"

    artifact = {
        "schema_version": PHASE7_CERTIFICATION_SCHEMA_VERSION,
        "phase7_certification_schema_version": PHASE7_CERTIFICATION_SCHEMA_VERSION,
        "phase7_artifact_schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "artifact_type": "phase7_certification",
        "artifact_id": "phase7:q7-17:certification",
        "phase": "Q7",
        "stage": "Q7-17",
        "status": status,
        "stage_status": stage_status,
        "certification_state": certification_state,
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
        "event_contract": phase7_event_contract("certification"),
        "authority_ledger": {
            "authority_schema_version": PHASE7_CERTIFICATION_SCHEMA_VERSION,
            "stage": "Q7-17",
            "authority_field_count": len(PHASE7_AUTHORITY_FLAGS),
            "explicit_authority_grant_count": 0,
            "explicit_authority_grants": [],
            "certification_only": True,
            "q7_18_live_promotion_review_stage_allowed": phase7_demo_proof_certified,
            **phase7_authority_defaults(),
            "boundary": PHASE7_CERTIFICATION_BOUNDARY,
        },
        "proof_contract": phase7_proof_contract(),
        "source_posture": phase7_source_posture(),
        "provenance": _provenance(tuple(SOURCE_REFS.values())),
        "boundary": PHASE7_CERTIFICATION_BOUNDARY,
        **phase7_authority_defaults(),
        **phase7_unsafe_counter_defaults(),
        "source_artifact_count": len(source_status_records),
        "source_missing_count": source_missing_count,
        "source_validation_error_count": source_validation_error_count,
        "source_status_records": source_status_records,
        "phase7_demo_proof_certified": phase7_demo_proof_certified,
        "phase7_demo_proof_exit_gate": phase7_demo_proof_certified,
        "phase7_30_day_operational_result_clean": phase7_30_day_operational_clean,
        "phase7_30_day_operational_result_preserved": True,
        "phase7_30_day_operational_result_erased_by_immaturity": False,
        "phase7_30_day_run_complete": run_complete,
        "phase7_harness_day_count": PHASE7_HARNESS_DAY_COUNT,
        "completed_calendar_day_count": completed_days,
        "proof_week_count": proof_week_count,
        "weekly_cadence_satisfied_count": weekly_satisfied,
        "weekly_cadence_failed_count": weekly_failed,
        "weekly_review_packet_created_count": weekly_packet_count,
        "qualified_setup_count": qualified_setup_count,
        "missed_qualified_setup_count": missed_setup_count,
        "missed_qualified_setup_unexplained_count": missed_unexplained,
        "evaluated_trade_count": evaluated_trade_count,
        "expectancy_after_costs_gbp": expectancy_after_costs,
        "expectancy_after_costs_positive": expectancy_positive,
        "drawdown_within_cap": drawdown_within_cap,
        "drawdown_cap_breached": drawdown_breached,
        "max_drawdown_fraction_observed": _float_or_none(
            drawdown.get("max_drawdown_fraction_observed")
        ),
        "risk_halt_active": risk_halt_active,
        "override_count": override_count,
        "manual_trade_level_override_count": manual_override_count,
        "sample_contaminated": sample_contaminated,
        "closed_proof_trade_count": closed_trade_count,
        "postmortem_due_count": postmortem_due_count,
        "postmortem_missing_count": postmortem_missing_count,
        "postmortem_reviewed_count": postmortem_reviewed_count,
        "postmortem_coverage_satisfied": postmortem_coverage_satisfied,
        "complete_decision_chain_count": complete_decision_chain_count,
        "missing_decision_chain_count": missing_decision_chain_count,
        "private_priors_only_proof_trade_count": private_priors_only_count,
        "source_signal_chains_complete": source_signal_complete,
        "maturity_state": maturity_state,
        "maturity_classification": maturity_classification,
        "mature_benchmark": PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
        "phase7_mature_benchmark_met": mature_met,
        "phase7_mature_status_blocked": not mature_met,
        "phase7_statistically_immature": statistically_immature,
        "phase7_statistical_immaturity_hidden": immaturity_hidden,
        "phase7_certification_blocked_by_maturity": not mature_met,
        "phase5_test_trades_count_for_phase7": phase5_test_trades_count_for_phase7,
        "q6_deferred_learning_counts_as_proof": q6_deferred_learning_counts_as_proof,
        "phase7_proof_credit_allowed": False,
        "live_capital_enabled": False,
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
        "unsafe_write_counter_total": 0,
        "certification_gate_count": len(gate_records),
        "certification_gate_passed_count": sum(
            1 for record in gate_records if record.get("gate_passed") is True
        ),
        "certification_gate_blocked_count": sum(
            1 for record in gate_records if record.get("gate_passed") is not True
        ),
        "certification_gate_records": gate_records,
        "certification_blockers": blockers,
        "certification_blocker_count": len(blockers),
        "q7_18_live_promotion_review_stage_allowed": phase7_demo_proof_certified,
        "recommended_next_stage": (
            "Q7-18 Live Promotion Review Flow"
            if phase7_demo_proof_certified
            else "Complete the 30-day proof run and maturity benchmark before Q7-18"
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


def _certification_gate_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("gate_name") not in PHASE7_CERTIFICATION_REQUIRED_GATES:
        errors.append("phase7_certification_gate_name_invalid")
    if record.get("display_status") != record.get("backend_status"):
        errors.append("phase7_certification_gate_display_backend_mismatch")
    if record.get("display_derived_from_backend") is not True:
        errors.append("phase7_certification_gate_display_not_backend")
    if record.get("ui_inferred_readiness") is not False:
        errors.append("phase7_certification_gate_ui_inferred")
    if record.get("gate_passed") is True and record.get("backend_status") != "passed":
        errors.append("phase7_certification_gate_passed_status_mismatch")
    if record.get("gate_passed") is not True and record.get("backend_status") != "blocked":
        errors.append("phase7_certification_gate_blocked_status_mismatch")
    if record.get("gate_passed") is not True and not record.get("blocker"):
        errors.append("phase7_certification_gate_blocker_missing")
    if record.get("public_safe") is not True:
        errors.append("phase7_certification_gate_not_public_safe")
    errors.extend(_public_safety_errors(record))
    return errors


def _forbidden_unsafe_count(artifact: dict[str, Any]) -> int:
    return sum(_int(artifact.get(field)) for field in PHASE7_UNSAFE_COUNT_FIELDS)


def validate_phase7_certification(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = set(PUBLIC_STATUS_FIELDS) | {
        "event_contract",
        "authority_ledger",
        "proof_contract",
        "source_posture",
        "provenance",
        "source_status_records",
        "public_status",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("phase7_certification_missing_fields:" + ",".join(missing))
    errors.extend(validate_phase7_artifact(artifact, expected_stage="Q7-17"))
    if artifact.get("phase7_certification_schema_version") != PHASE7_CERTIFICATION_SCHEMA_VERSION:
        errors.append("phase7_certification_schema_version_mismatch")
    if artifact.get("phase7_artifact_schema_version") != PHASE7_ARTIFACT_SCHEMA_VERSION:
        errors.append("phase7_certification_artifact_schema_version_mismatch")
    if artifact.get("artifact_type") != "phase7_certification":
        errors.append("phase7_certification_artifact_type_mismatch")
    if artifact.get("status") not in {"blocked", "certified"}:
        errors.append("phase7_certification_status_invalid")
    if artifact.get("stage_status") not in {
        "phase7_demo_proof_certified",
        "phase7_operational_clean_but_maturity_blocked",
        "phase7_certification_blocked_run_incomplete",
        "phase7_certification_blocked",
        "phase7_certification_validation_error",
    }:
        errors.append("phase7_certification_stage_status_invalid")

    source_records = artifact.get("source_status_records", [])
    if not isinstance(source_records, list) or not source_records:
        errors.append("phase7_certification_source_records_missing")
        source_records = []
    if artifact.get("source_artifact_count") != len(source_records):
        errors.append("phase7_certification_source_count_mismatch")
    source_missing_count = 0
    source_validation_error_count = 0
    for record in source_records:
        if not isinstance(record, dict):
            errors.append("phase7_certification_source_record_invalid")
            continue
        if record.get("display_status") != record.get("backend_status"):
            errors.append("phase7_certification_source_display_backend_mismatch")
        if record.get("display_derived_from_backend") is not True:
            errors.append("phase7_certification_source_display_not_backend")
        if record.get("ui_inferred_readiness") is not False:
            errors.append("phase7_certification_source_ui_inferred")
        source_ref = str(record.get("source_ref") or "")
        if not source_ref.startswith("data/runtime/"):
            errors.append("phase7_certification_source_ref_invalid")
        if _has_local_path(source_ref):
            errors.append("phase7_certification_source_ref_local_path")
        if record.get("source_status") == "missing":
            source_missing_count += 1
        source_validation_error_count += _int(record.get("validation_error_count"))
    if artifact.get("source_missing_count") != source_missing_count:
        errors.append("phase7_certification_source_missing_count_mismatch")
    if artifact.get("source_validation_error_count") != source_validation_error_count:
        errors.append("phase7_certification_source_validation_count_mismatch")

    gates = artifact.get("certification_gate_records", [])
    if not isinstance(gates, list):
        errors.append("phase7_certification_gates_not_list")
        gates = []
    gate_names = [gate.get("gate_name") for gate in gates if isinstance(gate, dict)]
    if gate_names != list(PHASE7_CERTIFICATION_REQUIRED_GATES):
        errors.append("phase7_certification_gate_order_mismatch")
    if artifact.get("certification_gate_count") != len(gates):
        errors.append("phase7_certification_gate_count_mismatch")
    gate_passed_count = sum(1 for gate in gates if gate.get("gate_passed") is True)
    if artifact.get("certification_gate_passed_count") != gate_passed_count:
        errors.append("phase7_certification_gate_passed_count_mismatch")
    if artifact.get("certification_gate_blocked_count") != len(gates) - gate_passed_count:
        errors.append("phase7_certification_gate_blocked_count_mismatch")
    for gate in gates:
        if isinstance(gate, dict):
            errors.extend(_certification_gate_errors(gate))
        else:
            errors.append("phase7_certification_gate_invalid")
    operational_gate_names = set(PHASE7_CERTIFICATION_REQUIRED_GATES) - {
        "maturity_classified_and_benchmark_met"
    }
    operational_clean_from_gates = all(
        gate.get("gate_passed") is True
        for gate in gates
        if isinstance(gate, dict) and gate.get("gate_name") in operational_gate_names
    )
    if artifact.get("phase7_30_day_operational_result_clean") != operational_clean_from_gates:
        errors.append("phase7_certification_operational_clean_gate_mismatch")

    blockers = artifact.get("certification_blockers", [])
    if not isinstance(blockers, list):
        errors.append("phase7_certification_blockers_not_list")
        blockers = []
    if artifact.get("certification_blocker_count") != len(blockers):
        errors.append("phase7_certification_blocker_count_mismatch")
    gate_blockers = sorted(
        str(gate.get("blocker"))
        for gate in gates
        if isinstance(gate, dict)
        and gate.get("gate_passed") is not True
        and gate.get("blocker")
    )
    for blocker in gate_blockers:
        if blocker not in blockers:
            errors.append(f"phase7_certification_missing_gate_blocker:{blocker}")

    certified = artifact.get("phase7_demo_proof_certified") is True
    if certified:
        if artifact.get("status") != "certified":
            errors.append("phase7_certified_status_not_certified")
        if blockers:
            errors.append("phase7_certified_with_blockers")
        if artifact.get("certification_gate_blocked_count") != 0:
            errors.append("phase7_certified_with_blocked_gates")
        if artifact.get("certification_gate_passed_count") != len(
            PHASE7_CERTIFICATION_REQUIRED_GATES
        ):
            errors.append("phase7_certified_without_all_gates")
        if artifact.get("phase7_demo_proof_exit_gate") is not True:
            errors.append("phase7_certified_exit_gate_false")
        if artifact.get("phase7_30_day_operational_result_clean") is not True:
            errors.append("phase7_certified_operational_result_not_clean")
        if artifact.get("phase7_30_day_run_complete") is not True:
            errors.append("phase7_certified_run_incomplete")
        if artifact.get("completed_calendar_day_count") != PHASE7_HARNESS_DAY_COUNT:
            errors.append("phase7_certified_day_count_not_30")
        if artifact.get("weekly_cadence_satisfied_count") != artifact.get("proof_week_count"):
            errors.append("phase7_certified_weekly_cadence_incomplete")
        if artifact.get("weekly_cadence_failed_count") != 0:
            errors.append("phase7_certified_weekly_cadence_failed")
        if artifact.get("evaluated_trade_count", 0) <= 0:
            errors.append("phase7_certified_without_evaluated_trades")
        if artifact.get("expectancy_after_costs_positive") is not True:
            errors.append("phase7_certified_without_positive_expectancy")
        if artifact.get("drawdown_within_cap") is not True:
            errors.append("phase7_certified_drawdown_not_within_cap")
        if artifact.get("drawdown_cap_breached") is True or artifact.get("risk_halt_active") is True:
            errors.append("phase7_certified_drawdown_or_halt_active")
        if artifact.get("manual_trade_level_override_count") != 0 or artifact.get("override_count") != 0:
            errors.append("phase7_certified_with_overrides")
        if artifact.get("sample_contaminated") is True:
            errors.append("phase7_certified_sample_contaminated")
        if artifact.get("postmortem_coverage_satisfied") is not True:
            errors.append("phase7_certified_postmortem_coverage_incomplete")
        if artifact.get("source_signal_chains_complete") is not True:
            errors.append("phase7_certified_signal_chain_incomplete")
        if artifact.get("phase7_mature_benchmark_met") is not True:
            errors.append("phase7_certified_without_maturity_benchmark")
        if artifact.get("phase7_certification_blocked_by_maturity") is not False:
            errors.append("phase7_certified_maturity_blocked")
        if artifact.get("q7_18_live_promotion_review_stage_allowed") is not True:
            errors.append("phase7_certified_q7_18_not_allowed")
    else:
        if artifact.get("status") != "blocked":
            errors.append("phase7_blocked_status_not_blocked")
        if artifact.get("phase7_demo_proof_exit_gate") is not False:
            errors.append("phase7_blocked_exit_gate_true")
        if artifact.get("q7_18_live_promotion_review_stage_allowed") is not False:
            errors.append("phase7_blocked_q7_18_allowed")
        if not blockers:
            errors.append("phase7_blocked_without_blockers")

    if artifact.get("phase7_harness_day_count") != PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_certification_harness_day_count_mismatch")
    if artifact.get("completed_calendar_day_count") > PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_certification_completed_days_invalid")
    if artifact.get("phase7_30_day_run_complete") is True and artifact.get(
        "completed_calendar_day_count"
    ) < PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_certification_run_complete_without_30_days")
    if artifact.get("weekly_review_packet_created_count") != artifact.get("proof_week_count"):
        errors.append("phase7_certification_weekly_review_packet_count_mismatch")
    if artifact.get("weekly_cadence_satisfied_count") + artifact.get(
        "weekly_cadence_failed_count"
    ) != artifact.get("proof_week_count"):
        errors.append("phase7_certification_weekly_cadence_count_mismatch")
    if artifact.get("weekly_cadence_failed_count") and (
        "weekly_cadence_not_satisfied" not in blockers
    ):
        errors.append("phase7_certification_weekly_failure_not_blocking")
    if artifact.get("missed_qualified_setup_unexplained_count") and (
        "weekly_cadence_not_satisfied" not in blockers
    ):
        errors.append("phase7_certification_missed_setup_not_blocking")
    if (
        artifact.get("evaluated_trade_count", 0) <= 0
        or artifact.get("expectancy_after_costs_positive") is not True
    ) and "positive_expectancy_after_costs_missing" not in blockers:
        errors.append("phase7_certification_expectancy_not_blocking")
    if (
        artifact.get("drawdown_within_cap") is not True
        or artifact.get("drawdown_cap_breached") is True
        or artifact.get("risk_halt_active") is True
    ) and "drawdown_cap_or_risk_halt_not_clear" not in blockers:
        errors.append("phase7_certification_drawdown_not_blocking")
    if (
        artifact.get("manual_trade_level_override_count") != 0
        or artifact.get("override_count") != 0
        or artifact.get("sample_contaminated") is True
    ) and "manual_override_or_contaminated_sample" not in blockers:
        errors.append("phase7_certification_override_not_blocking")
    if artifact.get("postmortem_missing_count") > 0 and (
        "postmortem_coverage_incomplete" not in blockers
    ):
        errors.append("phase7_certification_postmortem_not_blocking")
    if artifact.get("closed_proof_trade_count") > artifact.get("postmortem_due_count"):
        if "postmortem_coverage_incomplete" not in blockers:
            errors.append("phase7_certification_closed_without_postmortem_not_blocking")
    if (
        artifact.get("missing_decision_chain_count") != 0
        or artifact.get("private_priors_only_proof_trade_count") != 0
        or artifact.get("source_signal_chains_complete") is not True
    ) and "source_signal_chain_incomplete" not in blockers:
        errors.append("phase7_certification_signal_chain_not_blocking")
    if artifact.get("phase7_mature_benchmark_met") is True:
        if artifact.get("closed_proof_trade_count") < PHASE7_MATURE_CLOSED_TRADE_BENCHMARK:
            errors.append("phase7_certification_mature_under_100")
        if artifact.get("phase7_statistically_immature") is True:
            errors.append("phase7_certification_mature_and_immature")
    else:
        if artifact.get("phase7_certification_blocked_by_maturity") is not True:
            errors.append("phase7_certification_under_100_not_maturity_blocked")
        if "phase7_maturity_benchmark_not_met" not in blockers:
            errors.append("phase7_certification_maturity_not_blocking")
    if (
        artifact.get("phase7_30_day_run_complete") is True
        and artifact.get("closed_proof_trade_count") < PHASE7_MATURE_CLOSED_TRADE_BENCHMARK
        and artifact.get("phase7_statistically_immature") is not True
    ):
        errors.append("phase7_certification_30d_under_100_not_immature")
    if artifact.get("phase7_statistical_immaturity_hidden") is not False:
        errors.append("phase7_certification_hidden_immaturity")
    if artifact.get("phase7_30_day_operational_result_preserved") is not True:
        errors.append("phase7_certification_operational_result_not_preserved")
    if artifact.get("phase7_30_day_operational_result_erased_by_immaturity") is not False:
        errors.append("phase7_certification_operational_result_erased")

    for field in (
        "phase5_test_trades_count_for_phase7",
        "q6_deferred_learning_counts_as_proof",
        "phase7_proof_credit_allowed",
        "live_capital_enabled",
    ):
        if artifact.get(field) is not False:
            errors.append(f"phase7_certification_forbidden:{field}")
    for field in PHASE7_AUTHORITY_FLAGS:
        if artifact.get(field) is not False:
            errors.append(f"phase7_certification_authority_enabled:{field}")
    ledger = artifact.get("authority_ledger", {})
    if not isinstance(ledger, dict):
        errors.append("phase7_certification_authority_ledger_missing")
        ledger = {}
    if ledger.get("stage") != "Q7-17":
        errors.append("phase7_certification_authority_stage_mismatch")
    if ledger.get("authority_field_count") != len(PHASE7_AUTHORITY_FLAGS):
        errors.append("phase7_certification_authority_count_mismatch")
    if ledger.get("explicit_authority_grant_count") != 0:
        errors.append("phase7_certification_authority_grant_nonzero")
    for field in PHASE7_AUTHORITY_FLAGS:
        if ledger.get(field) is not False:
            errors.append(f"phase7_certification_ledger_authority_enabled:{field}")
    if ledger.get("q7_18_live_promotion_review_stage_allowed") != artifact.get(
        "q7_18_live_promotion_review_stage_allowed"
    ):
        errors.append("phase7_certification_q7_18_ledger_mismatch")

    if artifact.get("unsafe_write_counter_total") != _forbidden_unsafe_count(artifact):
        errors.append("phase7_certification_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("phase7_certification_unsafe_total_nonzero")
    for count_field in PHASE7_UNSAFE_COUNT_FIELDS:
        if count_field not in artifact:
            errors.append(f"phase7_certification_unsafe_count_missing:{count_field}")
        elif _int(artifact.get(count_field)) != 0:
            errors.append(f"phase7_certification_unsafe_count_nonzero:{count_field}")

    public_status = artifact.get("public_status")
    if not isinstance(public_status, dict):
        errors.append("phase7_certification_public_status_missing")
    else:
        extra = sorted(set(public_status) - set(PUBLIC_STATUS_FIELDS))
        if extra:
            errors.append("phase7_certification_public_status_extra_fields:" + ",".join(extra))
        for field in PUBLIC_STATUS_FIELDS:
            if field == "validation_error_count":
                continue
            if field in artifact and public_status.get(field) != artifact.get(field):
                errors.append(f"phase7_certification_public_status_mismatch:{field}")
        errors.extend(_public_safety_errors(public_status))

    provenance = artifact.get("provenance", {})
    if isinstance(provenance, dict):
        for ref in provenance.get("source_refs", []) or []:
            ref_text = str(ref)
            lowered = ref_text.lower()
            if _has_local_path(ref_text):
                errors.append("phase7_certification_provenance_local_path_leak")
            if "api_key" in lowered or "secret" in lowered or "token" in lowered:
                errors.append("phase7_certification_provenance_secret_ref_leak")
    event_contract = artifact.get("event_contract", {})
    if not isinstance(event_contract, dict):
        errors.append("phase7_certification_event_contract_missing")
        event_contract = {}
    if event_contract.get("event_type") != PHASE7_CERTIFICATION_EVENT_TYPE:
        errors.append("phase7_certification_event_contract_type_mismatch")
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("phase7_certification_event_log_path_missing")
        if not artifact.get("event_log_correlation_id"):
            errors.append("phase7_certification_event_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("phase7_certification_event_log_count_mismatch")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "30 consecutive calendar day",
        "weekly cadence is satisfied",
        "expectancy after costs is positive",
        "drawdown remains within the 20 percent cap",
        "manual trade-level overrides are zero",
        "postmortem coverage is complete",
        "source and signal chains are complete",
        "100 closed proof-trade maturity benchmark is met",
        "preserves a clean 30-day operational result",
        "cannot hide statistical immaturity",
        "cannot grant Phase 7 proof credit",
        "cannot count Phase 5 test trades toward Phase 7 proof",
        "cannot enable live capital",
    ):
        if phrase not in boundary:
            errors.append("phase7_certification_boundary_weak")
            break
    return sorted(set(errors))


def attach_phase7_certification_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(event_log_path or (_runtime_dir(settings) / PHASE7_CERTIFICATION_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE7_CERTIFICATION_EVENT_TYPE,
        PHASE7_CERTIFICATION_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "stage_status": output.get("stage_status"),
            "certification_state": output.get("certification_state"),
            "phase7_demo_proof_certified": output.get("phase7_demo_proof_certified"),
            "phase7_demo_proof_exit_gate": output.get("phase7_demo_proof_exit_gate"),
            "phase7_30_day_operational_result_clean": output.get(
                "phase7_30_day_operational_result_clean"
            ),
            "phase7_30_day_run_complete": output.get("phase7_30_day_run_complete"),
            "completed_calendar_day_count": output.get("completed_calendar_day_count"),
            "closed_proof_trade_count": output.get("closed_proof_trade_count"),
            "mature_benchmark": output.get("mature_benchmark"),
            "phase7_mature_benchmark_met": output.get("phase7_mature_benchmark_met"),
            "phase7_statistically_immature": output.get("phase7_statistically_immature"),
            "certification_blocker_count": output.get("certification_blocker_count"),
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


def write_phase7_certification(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase7_certification_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase7_certification_event_log(
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
        "schema_version": PHASE7_CERTIFICATION_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "stage_status": output.get("stage_status"),
        "certification_state": output.get("certification_state"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "phase7_demo_proof_certified": output.get("phase7_demo_proof_certified"),
        "phase7_demo_proof_exit_gate": output.get("phase7_demo_proof_exit_gate"),
        "phase7_30_day_operational_result_clean": output.get(
            "phase7_30_day_operational_result_clean"
        ),
        "phase7_30_day_run_complete": output.get("phase7_30_day_run_complete"),
        "completed_calendar_day_count": output.get("completed_calendar_day_count"),
        "closed_proof_trade_count": output.get("closed_proof_trade_count"),
        "phase7_mature_benchmark_met": output.get("phase7_mature_benchmark_met"),
        "phase7_statistically_immature": output.get("phase7_statistically_immature"),
        "certification_blocker_count": output.get("certification_blocker_count"),
        "q7_18_live_promotion_review_stage_allowed": output.get(
            "q7_18_live_promotion_review_stage_allowed"
        ),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output


def phase7_certification_public_status(settings: Settings | None = None) -> dict[str, Any]:
    artifact = _read_json_ref(
        f"data/runtime/{PHASE7_CERTIFICATION_RUNTIME_ARTIFACT}",
        settings,
    )
    if not artifact:
        artifact = build_phase7_certification(settings=settings)
    artifact = _refresh_validation(artifact)
    return _public_status_from_artifact(artifact)
