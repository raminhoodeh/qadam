"""Q7-3 Phase 7 Demo Proof qualified setup ledger.

This stage defines and records qualified setup eligibility against the Q7
calendar harness. It is read-only eligibility accounting: it does not start the
harness, create qualified setups, auto-approve trades, stage or submit orders,
create proof trades, grant proof credit, or enable live capital.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.phase7_artifacts import (
    PHASE7_ARTIFACT_SCHEMA_VERSION,
    PHASE7_EVENT_TYPES,
    phase7_proof_contract,
    phase7_provenance,
    phase7_source_posture,
)
from orchestrator.phase7_calendar_harness import (
    PHASE7_CALENDAR_HARNESS_RUNTIME_ARTIFACT,
    build_phase7_calendar_harness,
    phase7_calendar_harness_paths,
    validate_phase7_calendar_harness,
)
from orchestrator.phase7_readiness import (
    PHASE7_AUTHORITY_FLAGS,
    PHASE7_HARNESS_DAY_COUNT,
    PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
    PHASE7_MAX_DRAWDOWN_FRACTION,
    PHASE7_PAPER_ACCOUNT_STARTING_GBP,
    PHASE7_UNSAFE_COUNT_FIELDS,
    PHASE7_WEEKLY_PROOF_TRADE_TARGET,
    phase7_authority_defaults,
    phase7_unsafe_counter_defaults,
)


PHASE7_QUALIFIED_SETUP_LEDGER_SCHEMA_VERSION = 1
PHASE7_QUALIFIED_SETUP_LEDGER_RUNTIME_ARTIFACT = "phase7_qualified_setup_ledger.json"
PHASE7_QUALIFIED_SETUP_LEDGER_HISTORY = "phase7_qualified_setup_ledger_history.jsonl"
PHASE7_QUALIFIED_SETUP_LEDGER_EVENT_LOG = "phase7_qualified_setup_ledger_events.jsonl"
PHASE7_QUALIFIED_SETUP_LEDGER_EVENT_TYPE = PHASE7_EVENT_TYPES["qualified_setup"]
PHASE7_QUALIFIED_SETUP_LEDGER_COMPONENT = "phase7_qualified_setup_ledger"
PAPEROPS_QUALIFIED_SETUP_RUNTIME_ARTIFACT = "paperops_qualified_setup_production.json"

QUALIFICATION_GATE_KEYS: tuple[str, ...] = (
    "source_quorum",
    "akber_filter",
    "signal_integrity",
    "risk_agent_paper_sizing",
    "execution_policy",
    "kill_switches",
    "venue_availability",
    "broker_paper_readiness",
)

PHASE7_QUALIFIED_SETUP_BOUNDARY = (
    "Q7-3 records the qualified setup ledger and no-trade eligibility "
    "explanations only. It cannot start the proof harness, cannot create "
    "qualified setups from Phase 5 lifecycle records, cannot qualify a setup "
    "from supplemental-only sources, cannot auto-approve trades, cannot stage "
    "or submit proof orders, cannot create proof trades, cannot grant Phase 7 "
    "proof credit, cannot call broker POST routes, cannot call live endpoints, "
    "cannot enable live capital, and cannot permit manual trade-level overrides."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _int(value: Any) -> int:
    return int(value or 0)


def phase7_qualified_setup_ledger_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE7_QUALIFIED_SETUP_LEDGER_RUNTIME_ARTIFACT,
        runtime / PHASE7_QUALIFIED_SETUP_LEDGER_HISTORY,
        runtime / PHASE7_QUALIFIED_SETUP_LEDGER_EVENT_LOG,
    )


def _calendar_harness(settings: Settings) -> dict[str, Any]:
    calendar_path, _, _ = phase7_calendar_harness_paths(settings)
    if calendar_path.exists():
        return _read_json(calendar_path)
    return build_phase7_calendar_harness(settings=settings)


def _qualification_contract() -> dict[str, Any]:
    return {
        "contract_schema_version": PHASE7_QUALIFIED_SETUP_LEDGER_SCHEMA_VERSION,
        "required_gate_keys": list(QUALIFICATION_GATE_KEYS),
        "required_gate_count": len(QUALIFICATION_GATE_KEYS),
        "all_required_gates_must_pass": True,
        "canonical_source_quorum_required": True,
        "supplemental_source_bypass_allowed": False,
        "supplemental_only_qualification_allowed": False,
        "yahoo_finance_counts_as_canonical": False,
        "preference_mcp_counts_as_canonical": False,
        "preference_mcp_source_quorum_credit_allowed": False,
        "qctrl_counts_as_execution_truth": False,
        "private_world_model_counts_as_proof": False,
        "phase5_lifecycle_counts_as_q7_proof": False,
        "q6_deferred_learning_counts_as_proof": False,
        "harness_start_required_before_positive_setup_count": True,
        "proof_trade_creation_allowed": False,
        "proof_credit_allowed": False,
        "manual_trade_level_override_allowed": False,
    }


def _authority_ledger() -> dict[str, Any]:
    return {
        "authority_schema_version": PHASE7_QUALIFIED_SETUP_LEDGER_SCHEMA_VERSION,
        "stage": "Q7-3",
        "authority_field_count": len(PHASE7_AUTHORITY_FLAGS),
        "explicit_authority_grant_count": 0,
        "q7_4_weekly_cadence_tracker_stage_allowed": True,
        **phase7_authority_defaults(),
        "boundary": PHASE7_QUALIFIED_SETUP_BOUNDARY,
    }


def _provenance() -> dict[str, Any]:
    provenance = phase7_provenance(
        (
            f"data/runtime/{PHASE7_CALENDAR_HARNESS_RUNTIME_ARTIFACT}",
            "orchestrator/phase7_artifacts.py",
            "orchestrator/phase7_calendar_harness.py",
            "docs/qadam-phase-7-demo-proof-implementation-plan.md",
            "data/runtime/phase5_paper_trade_drill.json",
            "data/runtime/phase5_signal_review.json",
            "data/runtime/phase5_risk_sizing_reviews.json",
            "data/runtime/phase5_paper_order_staging_gate.json",
            f"data/runtime/{PAPEROPS_QUALIFIED_SETUP_RUNTIME_ARTIFACT}",
        )
    )
    provenance["decision_chain_refs"] = [
        "data/runtime/phase5_signal_review.json",
        "data/runtime/phase5_risk_sizing_reviews.json",
        "data/runtime/phase5_paper_order_staging_gate.json",
    ]
    provenance["execution_evidence_refs"] = [
        "data/runtime/phase5_paper_trade_drill.json",
        f"data/runtime/{PAPEROPS_QUALIFIED_SETUP_RUNTIME_ARTIFACT}",
    ]
    return provenance


def _active_day_number_from_paperops_handoff(
    paperops_handoff: dict[str, Any],
) -> int | None:
    candidates = (
        paperops_handoff.get("phase7_active_day_number"),
        paperops_handoff.get("phase7_demo_active_day_number"),
        paperops_handoff.get("phase7_run", {}).get("active_day_number")
        if isinstance(paperops_handoff.get("phase7_run"), dict)
        else None,
    )
    for candidate in candidates:
        try:
            day_number = int(candidate or 0)
        except (TypeError, ValueError):
            continue
        if day_number >= 1:
            # The proof ledger keeps the original 30-day evidence shape, while
            # PaperOps may continue indefinitely after that milestone.
            return min(day_number, PHASE7_HARNESS_DAY_COUNT)
    return None


def _daily_setup_decisions(
    calendar: dict[str, Any],
    *,
    qualified_setup_count: int = 0,
    active_day_number: int | None = None,
) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for day in calendar.get("proof_calendar_days", []):
        if not isinstance(day, dict):
            continue
        is_active_setup_day = (
            qualified_setup_count > 0
            and active_day_number is not None
            and day.get("day_number") == active_day_number
        )
        if is_active_setup_day:
            decisions.append(
                {
                    "decision_id": (
                        f"q7-3:day:{day.get('day_number')}:paperops-qualified-handoff"
                    ),
                    "day_number": day.get("day_number"),
                    "calendar_date": day.get("calendar_date"),
                    "proof_week_number": day.get("proof_week_number"),
                    "decision_state": "qualified_setup_pending_auto_approval",
                    "setup_window_state": "paperops_qualified_setup_handoff_recorded",
                    "no_trade_explanation_recorded": False,
                    "no_trade_rationale": None,
                    "eligible_setup_count": qualified_setup_count,
                    "qualified_setup_count": qualified_setup_count,
                    "blocked_setup_count": 0,
                    "expired_setup_count": 0,
                    "target_proof_trade_count": min(
                        PHASE7_WEEKLY_PROOF_TRADE_TARGET,
                        qualified_setup_count,
                    ),
                    "proof_trade_count": 0,
                    "phase5_lifecycle_reuse_count": 0,
                    "supplemental_only_setup_count": 0,
                    "forced_trade_allowed": False,
                    "proof_credit_allowed": False,
                    "broker_post_allowed": False,
                    "live_capital_enabled": False,
                }
            )
            continue
        decisions.append(
            {
                "decision_id": f"q7-3:day:{day.get('day_number')}:no-q7-setup-window",
                "day_number": day.get("day_number"),
                "calendar_date": day.get("calendar_date"),
                "proof_week_number": day.get("proof_week_number"),
                "decision_state": "no_trade_no_q7_setup_window",
                "setup_window_state": "scheduled_harness_not_started",
                "no_trade_explanation_recorded": True,
                "no_trade_rationale": "phase7_calendar_scheduled_but_harness_not_started",
                "eligible_setup_count": 0,
                "qualified_setup_count": 0,
                "blocked_setup_count": 0,
                "expired_setup_count": 0,
                "proof_trade_count": 0,
                "phase5_lifecycle_reuse_count": 0,
                "supplemental_only_setup_count": 0,
                "forced_trade_allowed": False,
                "proof_credit_allowed": False,
                "broker_post_allowed": False,
                "live_capital_enabled": False,
            }
        )
    return decisions


def _weekly_setup_summaries(
    calendar: dict[str, Any],
    *,
    qualified_setup_count: int = 0,
    active_day_number: int | None = None,
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for week in calendar.get("proof_weeks", []):
        if not isinstance(week, dict):
            continue
        start_day = _int(week.get("start_day_number"))
        end_day = _int(week.get("end_day_number"))
        is_active_setup_week = (
            qualified_setup_count > 0
            and active_day_number is not None
            and start_day <= active_day_number <= end_day
        )
        target_count = (
            min(PHASE7_WEEKLY_PROOF_TRADE_TARGET, qualified_setup_count)
            if is_active_setup_week
            else 0
        )
        summaries.append(
            {
                "proof_week_number": week.get("proof_week_number"),
                "start_day_number": week.get("start_day_number"),
                "end_day_number": week.get("end_day_number"),
                "start_date": week.get("start_date"),
                "end_date": week.get("end_date"),
                "is_partial_week": week.get("is_partial_week") is True,
                "weekly_setup_state": (
                    "qualified_setups_pending_auto_approval"
                    if is_active_setup_week
                    else "no_q7_setup_window_not_started"
                ),
                "weekly_target_formula": "min(3, qualified_setup_count)",
                "max_weekly_proof_trade_target": PHASE7_WEEKLY_PROOF_TRADE_TARGET,
                "qualified_setup_count": (
                    qualified_setup_count if is_active_setup_week else 0
                ),
                "target_proof_trade_count": target_count,
                "proof_trade_count": 0,
                "blocked_setup_count": 0,
                "expired_setup_count": 0,
                "pending_auto_approval_count": target_count,
                "no_trade_explanation_recorded": not is_active_setup_week,
                "no_trade_rationale": (
                    None
                    if is_active_setup_week
                    else "phase7_calendar_scheduled_but_harness_not_started"
                ),
                "forced_trade_allowed": False,
                "partial_week_trade_pressure_allowed": False,
            }
        )
    return summaries


def _phase5_rejection_record(settings: Settings) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    drill = _read_json(runtime / "phase5_paper_trade_drill.json")
    staging = _read_json(runtime / "phase5_paper_order_staging_gate.json")
    staged_records = staging.get("records") or staging.get("staging_records") or []
    strategy_family_key = "unknown"
    instrument = "unknown"
    if isinstance(staged_records, list) and staged_records:
        first = staged_records[0] if isinstance(staged_records[0], dict) else {}
        strategy_family_key = str(first.get("strategy_family_key") or "unknown")
        instrument = str(first.get("instrument") or "unknown")
    return {
        "setup_record_id": "q7-3:rejected-phase5-lifecycle:paper-trade-drill",
        "setup_state": "rejected",
        "decision_state": "rejected_phase5_test_lifecycle",
        "strategy_family_key": strategy_family_key,
        "instrument": instrument,
        "source_phase": "Q5",
        "source_artifact_ref": "data/runtime/phase5_paper_trade_drill.json",
        "source_artifact_id": drill.get("artifact_id"),
        "source_status": drill.get("status"),
        "paper_trade_drill_complete": drill.get("paper_trade_drill_complete") is True,
        "phase5_exit_gate_passed": (
            drill.get("phase5_paper_trade_drill_exit_gate_passed") is True
        ),
        "closed_trade_count": int(drill.get("closed_trade_count", 0) or 0),
        "postmortem_due_count": int(drill.get("postmortem_due_count", 0) or 0),
        "eligible_setup": False,
        "qualified_setup": False,
        "source_quorum_passed": False,
        "canonical_source_quorum_passed": False,
        "supplemental_only": False,
        "all_required_gates_passed": False,
        "phase5_lifecycle_counts_as_q7_proof": False,
        "phase5_test_trade_counted_for_phase7": False,
        "proof_trade_created": False,
        "proof_credit_allowed": False,
        "rejection_reasons": [
            "phase5_test_lifecycle_excluded_from_phase7_proof",
            "phase7_harness_not_started",
        ],
        "gate_results": [
            {"gate_key": gate_key, "status": "not_evaluated_for_q7"}
            for gate_key in QUALIFICATION_GATE_KEYS
        ],
    }


def _paperops_qualified_setup_handoff(settings: Settings) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return _read_json(runtime / PAPEROPS_QUALIFIED_SETUP_RUNTIME_ARTIFACT)


def _paperops_gate_map(handoff: dict[str, Any]) -> dict[str, dict[str, Any]]:
    gate_results = handoff.get("gate_results", [])
    mapped: dict[str, dict[str, Any]] = {}
    if isinstance(gate_results, list):
        for gate in gate_results:
            if isinstance(gate, dict) and str(gate.get("gate_key") or "").strip():
                mapped[str(gate.get("gate_key"))] = gate
    return mapped


def _pt3_gate_passed(gates: dict[str, dict[str, Any]], gate_key: str) -> bool:
    gate = gates.get(gate_key, {})
    return gate.get("passed") is True or gate.get("status") in {"pass", "passed"}


def _q7_gate(
    gate_key: str,
    *,
    passed: bool,
    source_gate_keys: tuple[str, ...],
    detail: str,
) -> dict[str, Any]:
    return {
        "gate_key": gate_key,
        "status": "pass" if passed else "blocked",
        "passed": passed,
        "source_gate_keys": list(source_gate_keys),
        "source_stage": "PaperOps PT-3",
        "detail": detail,
    }


def _paperops_q7_gate_results(handoff: dict[str, Any]) -> list[dict[str, Any]]:
    gates = _paperops_gate_map(handoff)
    canonical_source = (
        _pt3_gate_passed(gates, "canonical_source_posture")
        and handoff.get("canonical_source_quorum_passed") is True
        and handoff.get("source_quorum_bypass_allowed") is not True
    )
    supplemental_context_only = _pt3_gate_passed(
        gates,
        "supplemental_sources_context_only",
    )
    signal_integrity = (
        _pt3_gate_passed(gates, "signal_integrity_passed")
        and handoff.get("signal_integrity_passed") is True
    )
    risk_sizing = _pt3_gate_passed(gates, "risk_agent_paper_sizing")
    execution_policy = all(
        _pt3_gate_passed(gates, key)
        for key in (
            "execution_adapter_read_ready",
            "paper_order_staged_not_submitted",
            "broker_write_blocked",
        )
    )
    broker_paper_readiness = all(
        _pt3_gate_passed(gates, key)
        for key in ("venue_read_available", "paper_order_staged_not_submitted")
    ) and handoff.get("broker_post_allowed") is False
    return [
        _q7_gate(
            "source_quorum",
            passed=canonical_source,
            source_gate_keys=("canonical_source_posture",),
            detail="PT-3 canonical source quorum passed with no source-quorum bypass.",
        ),
        _q7_gate(
            "akber_filter",
            passed=signal_integrity and canonical_source and supplemental_context_only,
            source_gate_keys=(
                "signal_integrity_passed",
                "canonical_source_posture",
                "supplemental_sources_context_only",
            ),
            detail=(
                "PT-3 signal-integrity handoff preserves the Akber filter boundary "
                "with canonical posture and supplemental sources as context only."
            ),
        ),
        _q7_gate(
            "signal_integrity",
            passed=signal_integrity,
            source_gate_keys=("signal_integrity_passed",),
            detail="PT-3 signal integrity passed before Q7 handoff.",
        ),
        _q7_gate(
            "risk_agent_paper_sizing",
            passed=risk_sizing,
            source_gate_keys=("risk_agent_paper_sizing",),
            detail="PT-3 risk agent paper sizing passed.",
        ),
        _q7_gate(
            "execution_policy",
            passed=execution_policy,
            source_gate_keys=(
                "execution_adapter_read_ready",
                "paper_order_staged_not_submitted",
                "broker_write_blocked",
            ),
            detail="Execution adapter is read-ready while broker writes remain blocked.",
        ),
        _q7_gate(
            "kill_switches",
            passed=_pt3_gate_passed(gates, "kill_switches_clear"),
            source_gate_keys=("kill_switches_clear",),
            detail="PT-3 kill switches are clear.",
        ),
        _q7_gate(
            "venue_availability",
            passed=_pt3_gate_passed(gates, "venue_read_available"),
            source_gate_keys=("venue_read_available",),
            detail="Paper venue read availability was verified by PT-3.",
        ),
        _q7_gate(
            "broker_paper_readiness",
            passed=broker_paper_readiness,
            source_gate_keys=(
                "venue_read_available",
                "paper_order_staged_not_submitted",
            ),
            detail="Paper broker readiness is read-only; no broker POST is allowed here.",
        ),
    ]


def _paperops_q7_handoff_records(handoff: dict[str, Any]) -> list[dict[str, Any]]:
    if not handoff:
        return []
    if (
        handoff.get("path_ready") is not True
        and handoff.get("qualified_setup_production_path_ready") is not True
    ):
        return []
    source_records = handoff.get("qualified_setup_records")
    if not isinstance(source_records, list):
        source_records = [
            record
            for record in handoff.get("candidate_setup_records", [])
            if isinstance(record, dict) and record.get("qualified_setup") is True
        ]
    if not isinstance(source_records, list):
        return []
    records: list[dict[str, Any]] = []
    for source in source_records:
        if not isinstance(source, dict):
            continue
        gate_results = _paperops_q7_gate_results(source)
        passed_gates = {
            gate.get("gate_key")
            for gate in gate_results
            if isinstance(gate, dict) and gate.get("status") == "pass"
        }
        handoff_forbidden = any(
            source.get(field) is True
            for field in (
                "phase5_lifecycle_counts_as_q7_proof",
                "phase5_test_trade_counted_for_phase7",
                "supplemental_only",
                "proof_trade_created",
                "proof_credit_allowed",
                "paper_order_submission_allowed",
                "broker_post_allowed",
                "broker_post_called",
                "live_capital_enabled",
            )
        )
        qualified = (
            source.get("qualified_setup") is True
            and source.get("eligible_setup") is True
            and source.get("all_required_gates_passed") is True
            and source.get("canonical_source_quorum_passed") is True
            and passed_gates == set(QUALIFICATION_GATE_KEYS)
            and not handoff_forbidden
        )
        strategy_key = str(source.get("strategy_family_key") or "unknown")
        lineage_material = {
            "strategy_family_key": strategy_key,
            "source_origin_record_id": source.get("setup_record_id"),
            "source_signal_id": source.get("source_signal_id"),
            "source_signal_review_id": source.get("source_signal_review_id"),
            "setup_freshness_key": source.get("setup_freshness_key"),
            "research_goal_id": source.get("research_goal_id"),
            "candidate_identity": source.get("candidate_identity"),
        }
        lineage_token = _hash_payload(lineage_material)[:16]
        research_goal_lineage = source.get("research_goal_lineage")
        if not isinstance(research_goal_lineage, dict):
            research_goal_lineage = {}
        record = {
            "setup_record_id": f"q7-3:paperops-handoff:{strategy_key}:{lineage_token}",
            "setup_state": (
                "qualified_pending_auto_approval" if qualified else "blocked"
            ),
            "decision_state": (
                "qualified_for_q7_auto_approval"
                if qualified
                else "blocked_paperops_handoff"
            ),
            "strategy_family_key": strategy_key,
            "instrument": source.get("instrument"),
            "selected_venue": source.get("selected_venue"),
            "side": source.get("side"),
            "quantity": source.get("quantity"),
            "order_type": source.get("order_type"),
            "time_in_force": source.get("time_in_force"),
            "notional_gbp": source.get("notional_gbp"),
            "risk_gbp": source.get("risk_gbp"),
            "source_phase": "Q7",
            "source_origin_phase": "PaperOps",
            "source_origin_record_id": source.get("setup_record_id"),
            "paperops_source_setup_record_id": source.get("setup_record_id"),
            "source_signal_id": source.get("source_signal_id"),
            "source_signal_review_id": source.get("source_signal_review_id"),
            "source_signal_reviewed_at": source.get("source_signal_reviewed_at"),
            "source_signal_status": source.get("source_signal_status"),
            "signal_evidence_lineage_key": source.get("signal_evidence_lineage_key"),
            "setup_freshness_key": source.get("setup_freshness_key"),
            "research_goal_id": source.get("research_goal_id")
            or f"paperops-research-goal:{strategy_key}:{lineage_token}",
            "research_goal_lineage": {
                **research_goal_lineage,
                "q7_handoff_lineage_token": lineage_token,
                "q7_handoff_lineage_material": lineage_material,
            },
            "candidate_identity": source.get("candidate_identity")
            or f"paperops-candidate:{strategy_key}:{lineage_token}",
            "source_artifact_ref": (
                f"data/runtime/{PAPEROPS_QUALIFIED_SETUP_RUNTIME_ARTIFACT}"
            ),
            "source_artifact_id": handoff.get("artifact_id"),
            "source_status": handoff.get("status"),
            "paperops_path_ready": (
                handoff.get("path_ready") is True
                or handoff.get("qualified_setup_production_path_ready") is True
            ),
            "paperops_ready_to_stage_q7_order": (
                handoff.get("ready_to_stage_q7_order") is True
            ),
            "eligible_setup": qualified,
            "qualified_setup": qualified,
            "source_quorum_passed": source.get("source_quorum_passed") is True,
            "canonical_source_quorum_passed": (
                source.get("canonical_source_quorum_passed") is True
            ),
            "supplemental_only": False,
            "all_required_gates_passed": qualified,
            "phase5_lifecycle_counts_as_q7_proof": False,
            "phase5_test_trade_counted_for_phase7": False,
            "proof_trade_created": False,
            "proof_credit_allowed": False,
            "paper_order_submission_allowed": False,
            "broker_post_allowed": False,
            "live_endpoint_allowed": False,
            "live_capital_enabled": False,
            "rejection_reasons": [] if qualified else ["paperops_q7_handoff_gate_blocked"],
            "gate_results": gate_results,
        }
        records.append(record)
    return records


def _preflight_blockers(calendar: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    calendar_errors = validate_phase7_calendar_harness(calendar)
    if calendar_errors:
        blockers.append("phase7_calendar_validation_errors")
    if calendar.get("status") != "scheduled":
        blockers.append("phase7_calendar_not_scheduled")
    if calendar.get("stage_status") != "phase7_calendar_harness_scheduled":
        blockers.append("phase7_calendar_stage_status_not_scheduled")
    if calendar.get("q7_3_qualified_setup_ledger_stage_allowed") is not True:
        blockers.append("q7_3_qualified_setup_ledger_not_allowed")
    if int(calendar.get("calendar_day_record_count", 0) or 0) != PHASE7_HARNESS_DAY_COUNT:
        blockers.append("phase7_calendar_day_count_mismatch")
    if calendar.get("calendar_harness_started") is not False:
        blockers.append("phase7_calendar_harness_already_started")
    return sorted(set(blockers))


def build_phase7_qualified_setup_ledger(
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    calendar = _calendar_harness(settings)
    blockers = _preflight_blockers(calendar)
    paperops_handoff = _paperops_qualified_setup_handoff(settings)
    paperops_handoff_records = _paperops_q7_handoff_records(paperops_handoff)
    qualified_records = [
        record
        for record in paperops_handoff_records
        if record.get("qualified_setup") is True
    ]
    blocked_handoff_count = sum(
        1
        for record in paperops_handoff_records
        if record.get("qualified_setup") is not True
    )
    qualified_setup_count = len(qualified_records)
    active_day_number = _active_day_number_from_paperops_handoff(paperops_handoff)
    daily_decisions = _daily_setup_decisions(
        calendar,
        qualified_setup_count=qualified_setup_count,
        active_day_number=active_day_number,
    )
    weekly_summaries = _weekly_setup_summaries(
        calendar,
        qualified_setup_count=qualified_setup_count,
        active_day_number=active_day_number,
    )
    candidate_records = [_phase5_rejection_record(settings), *paperops_handoff_records]
    unsafe_counts = phase7_unsafe_counter_defaults()
    ledger_recorded = not blockers
    status = "read_only_no_q7_setups"
    stage_status = "qualified_setup_ledger_recorded_no_q7_setup_window"
    if qualified_setup_count:
        status = "read_only_q7_setups_recorded"
        stage_status = "qualified_setup_ledger_recorded_with_q7_setups"
    if not ledger_recorded:
        status = "blocked"
        stage_status = "qualified_setup_ledger_blocked"
    artifact = {
        "schema_version": PHASE7_QUALIFIED_SETUP_LEDGER_SCHEMA_VERSION,
        "phase7_artifact_schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "artifact_type": "phase7_qualified_setup_ledger",
        "artifact_id": "phase7:q7-3:qualified-setup-ledger",
        "phase": "Q7",
        "stage": "Q7-3",
        "status": status,
        "stage_status": stage_status,
        "generated_at": _now(),
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
        "authority_ledger": _authority_ledger(),
        "proof_contract": phase7_proof_contract(),
        "source_posture": phase7_source_posture(),
        "provenance": _provenance(),
        "qualification_contract": _qualification_contract(),
        "daily_setup_decisions": daily_decisions,
        "weekly_setup_summaries": weekly_summaries,
        "candidate_setup_records": candidate_records,
        "qualified_setup_records": qualified_records,
        "boundary": PHASE7_QUALIFIED_SETUP_BOUNDARY,
        **phase7_authority_defaults(),
        **unsafe_counts,
        "source_calendar_artifact_id": calendar.get("artifact_id"),
        "source_calendar_status": calendar.get("status"),
        "source_calendar_stage_status": calendar.get("stage_status"),
        "source_paperops_qualified_setup_artifact_id": paperops_handoff.get("artifact_id"),
        "source_paperops_qualified_setup_status": paperops_handoff.get("status"),
        "source_paperops_ready_to_stage_q7_order": (
            paperops_handoff.get("ready_to_stage_q7_order") is True
        ),
        "source_paperops_path_ready": (
            paperops_handoff.get("path_ready") is True
            or paperops_handoff.get("qualified_setup_production_path_ready") is True
        ),
        "source_paperops_qualified_setup_count": int(
            paperops_handoff.get("qualified_setup_count", 0) or 0
        ),
        "phase7_active_day_number": active_day_number,
        "q7_3_qualified_setup_ledger_stage_allowed": (
            calendar.get("q7_3_qualified_setup_ledger_stage_allowed") is True
        ),
        "q7_4_weekly_cadence_tracker_stage_allowed": ledger_recorded,
        "qualified_setup_ledger_recorded": ledger_recorded,
        "read_only_eligibility_ledger_allowed": ledger_recorded,
        "calendar_harness_started": calendar.get("calendar_harness_started") is True,
        "calendar_day_record_count": int(calendar.get("calendar_day_record_count", 0) or 0),
        "daily_setup_decision_count": len(daily_decisions),
        "weekly_setup_summary_count": len(weekly_summaries),
        "candidate_setup_record_count": len(candidate_records),
        "qualified_setup_record_count": len(qualified_records),
        "eligible_setup_count": qualified_setup_count,
        "qualified_setup_count": qualified_setup_count,
        "blocked_setup_count": blocked_handoff_count,
        "expired_setup_count": 0,
        "no_trade_day_explanation_count": sum(
            1 for day in daily_decisions if day.get("no_trade_explanation_recorded")
        ),
        "no_trade_week_explanation_count": sum(
            1 for week in weekly_summaries if week.get("no_trade_explanation_recorded")
        ),
        "rejected_phase5_lifecycle_count": sum(
            1
            for record in candidate_records
            if record.get("decision_state") == "rejected_phase5_test_lifecycle"
        ),
        "supplemental_only_setup_rejected_count": 0,
        "supplemental_only_qualification_allowed": False,
        "source_quorum_bypass_allowed": False,
        "phase5_test_trades_count_for_phase7": False,
        "q6_deferred_learning_counts_as_proof": False,
        "private_world_model_counts_as_proof": False,
        "phase7_demo_day_count": 0,
        "target_proof_trade_count": sum(
            int(week.get("target_proof_trade_count", 0) or 0)
            for week in weekly_summaries
        ),
        "proof_trade_count": 0,
        "closed_proof_trade_count": 0,
        "postmortem_due_count": 0,
        "paper_account_starting_gbp": PHASE7_PAPER_ACCOUNT_STARTING_GBP,
        "max_drawdown_fraction": PHASE7_MAX_DRAWDOWN_FRACTION,
        "mature_closed_trade_benchmark": PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
        "statistical_immaturity_allowed": True,
        "unsafe_write_counter_total": sum(unsafe_counts.values()),
        "blockers": blockers,
        "blocker_count": len(blockers),
        "recommended_next_stage": "Q7-4 Weekly Proof Cadence Tracker",
    }
    artifact["validation_errors"] = validate_phase7_qualified_setup_ledger(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "error"
        artifact["stage_status"] = "qualified_setup_ledger_validation_error"
    return artifact


def _authority_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    ledger = artifact.get("authority_ledger", {})
    if not isinstance(ledger, dict):
        return ["qualified_setup_authority_ledger_missing"]
    if ledger.get("stage") != "Q7-3":
        errors.append("qualified_setup_authority_stage_mismatch")
    if ledger.get("authority_field_count") != len(PHASE7_AUTHORITY_FLAGS):
        errors.append("qualified_setup_authority_count_mismatch")
    if ledger.get("explicit_authority_grant_count") != 0:
        errors.append("qualified_setup_explicit_authority_grant")
    for field in PHASE7_AUTHORITY_FLAGS:
        if artifact.get(field) is not False:
            errors.append(f"qualified_setup_authority_enabled:{field}")
        if ledger.get(field) is not False:
            errors.append(f"qualified_setup_ledger_authority_enabled:{field}")
    for field in PHASE7_UNSAFE_COUNT_FIELDS:
        if int(artifact.get(field, 0) or 0) != 0:
            errors.append(f"qualified_setup_unsafe_count_nonzero:{field}")
    unsafe_total = sum(int(artifact.get(field, 0) or 0) for field in PHASE7_UNSAFE_COUNT_FIELDS)
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("qualified_setup_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("qualified_setup_unsafe_total_nonzero")
    return errors


def _contract_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    contract = artifact.get("qualification_contract", {})
    if not isinstance(contract, dict):
        return ["qualification_contract_missing"]
    if tuple(contract.get("required_gate_keys", ())) != QUALIFICATION_GATE_KEYS:
        errors.append("qualification_contract_gate_sequence_mismatch")
    if contract.get("required_gate_count") != len(QUALIFICATION_GATE_KEYS):
        errors.append("qualification_contract_gate_count_mismatch")
    for field in (
        "all_required_gates_must_pass",
        "canonical_source_quorum_required",
        "harness_start_required_before_positive_setup_count",
    ):
        if contract.get(field) is not True:
            errors.append(f"qualification_contract_missing_true:{field}")
    for field in (
        "supplemental_source_bypass_allowed",
        "supplemental_only_qualification_allowed",
        "yahoo_finance_counts_as_canonical",
        "preference_mcp_counts_as_canonical",
        "preference_mcp_source_quorum_credit_allowed",
        "qctrl_counts_as_execution_truth",
        "private_world_model_counts_as_proof",
        "phase5_lifecycle_counts_as_q7_proof",
        "q6_deferred_learning_counts_as_proof",
        "proof_trade_creation_allowed",
        "proof_credit_allowed",
        "manual_trade_level_override_allowed",
    ):
        if contract.get(field) is not False:
            errors.append(f"qualification_contract_forbidden:{field}")
    return errors


def _daily_decision_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    decisions = artifact.get("daily_setup_decisions", [])
    if not isinstance(decisions, list):
        return ["daily_setup_decisions_not_list"]
    if len(decisions) != PHASE7_HARNESS_DAY_COUNT:
        errors.append("daily_setup_decision_count_mismatch")
    day_numbers = [decision.get("day_number") for decision in decisions if isinstance(decision, dict)]
    if day_numbers != list(range(1, PHASE7_HARNESS_DAY_COUNT + 1)):
        errors.append("daily_setup_decision_day_numbers_invalid")
    for decision in decisions:
        if not isinstance(decision, dict):
            errors.append("daily_setup_decision_invalid")
            continue
        decision_state = decision.get("decision_state")
        qualified_count = int(decision.get("qualified_setup_count", 0) or 0)
        eligible_count = int(decision.get("eligible_setup_count", 0) or 0)
        if decision_state == "no_trade_no_q7_setup_window":
            if decision.get("no_trade_explanation_recorded") is not True:
                errors.append("daily_setup_no_trade_explanation_missing")
            if not str(decision.get("no_trade_rationale") or "").strip():
                errors.append("daily_setup_no_trade_rationale_missing")
            if qualified_count != 0 or eligible_count != 0:
                errors.append("daily_setup_no_trade_count_nonzero")
        elif decision_state == "qualified_setup_pending_auto_approval":
            if qualified_count <= 0:
                errors.append("daily_setup_qualified_count_missing")
            if eligible_count != qualified_count:
                errors.append("daily_setup_eligible_qualified_mismatch")
            if decision.get("no_trade_explanation_recorded") is not False:
                errors.append("daily_setup_qualified_no_trade_explanation_present")
        else:
            errors.append("daily_setup_decision_state_invalid")
        for count_field in (
            "blocked_setup_count",
            "expired_setup_count",
            "proof_trade_count",
            "phase5_lifecycle_reuse_count",
            "supplemental_only_setup_count",
        ):
            if int(decision.get(count_field, 0) or 0) != 0:
                errors.append(f"daily_setup_count_nonzero:{count_field}")
        for forbidden_field in (
            "forced_trade_allowed",
            "proof_credit_allowed",
            "broker_post_allowed",
            "live_capital_enabled",
        ):
            if decision.get(forbidden_field) is not False:
                errors.append(f"daily_setup_forbidden:{forbidden_field}")
    return errors


def _weekly_summary_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    summaries = artifact.get("weekly_setup_summaries", [])
    if not isinstance(summaries, list):
        return ["weekly_setup_summaries_not_list"]
    if len(summaries) != 5:
        errors.append("weekly_setup_summary_count_mismatch")
    for expected_week, summary in enumerate(summaries, start=1):
        if not isinstance(summary, dict):
            errors.append("weekly_setup_summary_invalid")
            continue
        if summary.get("proof_week_number") != expected_week:
            errors.append("weekly_setup_summary_week_mismatch")
        setup_state = summary.get("weekly_setup_state")
        qualified_count = int(summary.get("qualified_setup_count", 0) or 0)
        target_count = int(summary.get("target_proof_trade_count", 0) or 0)
        if setup_state not in {
            "no_q7_setup_window_not_started",
            "qualified_setups_pending_auto_approval",
        }:
            errors.append("weekly_setup_state_invalid")
        if summary.get("weekly_target_formula") != "min(3, qualified_setup_count)":
            errors.append("weekly_setup_target_formula_invalid")
        if summary.get("max_weekly_proof_trade_target") != PHASE7_WEEKLY_PROOF_TRADE_TARGET:
            errors.append("weekly_setup_target_mismatch")
        expected_target = min(PHASE7_WEEKLY_PROOF_TRADE_TARGET, qualified_count)
        if target_count != expected_target:
            errors.append("weekly_setup_target_count_invalid")
        if setup_state == "no_q7_setup_window_not_started":
            if summary.get("no_trade_explanation_recorded") is not True:
                errors.append("weekly_setup_no_trade_explanation_missing")
            if qualified_count != 0:
                errors.append("weekly_setup_no_trade_qualified_count_nonzero")
        if setup_state == "qualified_setups_pending_auto_approval":
            if qualified_count <= 0:
                errors.append("weekly_setup_qualified_count_missing")
            if summary.get("no_trade_explanation_recorded") is not False:
                errors.append("weekly_setup_qualified_no_trade_explanation_present")
            if int(summary.get("pending_auto_approval_count", 0) or 0) != target_count:
                errors.append("weekly_setup_pending_auto_approval_count_invalid")
        for count_field in ("proof_trade_count", "blocked_setup_count", "expired_setup_count"):
            if int(summary.get(count_field, 0) or 0) != 0:
                errors.append(f"weekly_setup_count_nonzero:{count_field}")
        if summary.get("forced_trade_allowed") is not False:
            errors.append("weekly_setup_forced_trade_allowed")
        if summary.get("partial_week_trade_pressure_allowed") is not False:
            errors.append("weekly_setup_partial_week_pressure_allowed")
    return errors


def _candidate_record_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    records = artifact.get("candidate_setup_records", [])
    if not isinstance(records, list):
        return ["candidate_setup_records_not_list"]
    for record in records:
        if not isinstance(record, dict):
            errors.append("candidate_setup_record_invalid")
            continue
        if record.get("source_phase") == "Q5" and record.get("qualified_setup") is True:
            errors.append("phase5_lifecycle_marked_qualified")
        if record.get("phase5_lifecycle_counts_as_q7_proof") is not False:
            errors.append("phase5_lifecycle_counts_as_q7_proof")
        if record.get("phase5_test_trade_counted_for_phase7") is not False:
            errors.append("phase5_test_trade_counted_for_phase7")
        if record.get("supplemental_only") is True and record.get("qualified_setup") is True:
            errors.append("supplemental_only_setup_marked_qualified")
        if record.get("proof_trade_created") is not False:
            errors.append("candidate_setup_proof_trade_created")
        if record.get("proof_credit_allowed") is not False:
            errors.append("candidate_setup_proof_credit_allowed")
        if record.get("qualified_setup") is True:
            gate_results = record.get("gate_results", [])
            passed_gates = {
                gate.get("gate_key")
                for gate in gate_results
                if isinstance(gate, dict) and gate.get("status") == "pass"
            }
            if passed_gates != set(QUALIFICATION_GATE_KEYS):
                errors.append("qualified_setup_missing_required_gate_pass")
            if record.get("canonical_source_quorum_passed") is not True:
                errors.append("qualified_setup_missing_canonical_source_quorum")
            if record.get("all_required_gates_passed") is not True:
                errors.append("qualified_setup_all_required_gates_not_passed")
    if artifact.get("candidate_setup_record_count") != len(records):
        errors.append("candidate_setup_record_count_mismatch")
    rejected_phase5 = sum(
        1
        for record in records
        if isinstance(record, dict)
        and record.get("decision_state") == "rejected_phase5_test_lifecycle"
    )
    if artifact.get("rejected_phase5_lifecycle_count") != rejected_phase5:
        errors.append("rejected_phase5_lifecycle_count_mismatch")
    return errors


def validate_phase7_qualified_setup_ledger(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "phase7_artifact_schema_version",
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
        "proof_contract",
        "source_posture",
        "provenance",
        "qualification_contract",
        "daily_setup_decisions",
        "weekly_setup_summaries",
        "candidate_setup_records",
        "qualified_setup_records",
        "boundary",
        "source_calendar_status",
        "q7_3_qualified_setup_ledger_stage_allowed",
        "q7_4_weekly_cadence_tracker_stage_allowed",
        "qualified_setup_ledger_recorded",
        "read_only_eligibility_ledger_allowed",
        "calendar_harness_started",
        "calendar_day_record_count",
        "daily_setup_decision_count",
        "weekly_setup_summary_count",
        "candidate_setup_record_count",
        "qualified_setup_record_count",
        "eligible_setup_count",
        "qualified_setup_count",
        "blocked_setup_count",
        "expired_setup_count",
        "no_trade_day_explanation_count",
        "no_trade_week_explanation_count",
        "rejected_phase5_lifecycle_count",
        "supplemental_only_setup_rejected_count",
        "supplemental_only_qualification_allowed",
        "source_quorum_bypass_allowed",
        "phase5_test_trades_count_for_phase7",
        "q6_deferred_learning_counts_as_proof",
        "private_world_model_counts_as_proof",
        "phase7_demo_day_count",
        "target_proof_trade_count",
        "proof_trade_count",
        "closed_proof_trade_count",
        "postmortem_due_count",
        "paper_account_starting_gbp",
        "max_drawdown_fraction",
        "mature_closed_trade_benchmark",
        "statistical_immaturity_allowed",
        "unsafe_write_counter_total",
        "blockers",
        "blocker_count",
        "recommended_next_stage",
    }
    missing = sorted(required_fields - set(artifact))
    if missing:
        errors.append("qualified_setup_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PHASE7_QUALIFIED_SETUP_LEDGER_SCHEMA_VERSION:
        errors.append("qualified_setup_schema_version_mismatch")
    if artifact.get("phase7_artifact_schema_version") != PHASE7_ARTIFACT_SCHEMA_VERSION:
        errors.append("qualified_setup_artifact_schema_version_mismatch")
    if artifact.get("artifact_type") != "phase7_qualified_setup_ledger":
        errors.append("qualified_setup_artifact_type_mismatch")
    if artifact.get("phase") != "Q7" or artifact.get("stage") != "Q7-3":
        errors.append("qualified_setup_phase_stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("qualified_setup_not_public_safe")
    if artifact.get("event_log_required") is not True:
        errors.append("qualified_setup_event_log_not_required")

    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("qualified_setup_blockers_not_list")
        blockers = []
    if artifact.get("blocker_count") != len(blockers):
        errors.append("qualified_setup_blocker_count_mismatch")
    if artifact.get("q7_3_qualified_setup_ledger_stage_allowed") is not True:
        errors.append("q7_3_qualified_setup_ledger_not_allowed")
    if artifact.get("source_calendar_status") != "scheduled":
        errors.append("qualified_setup_source_calendar_not_scheduled")
    if int(artifact.get("calendar_day_record_count", 0) or 0) != PHASE7_HARNESS_DAY_COUNT:
        errors.append("qualified_setup_calendar_day_count_mismatch")

    gate_passed = artifact.get("qualified_setup_ledger_recorded") is True
    has_qualified_setups = int(artifact.get("qualified_setup_count", 0) or 0) > 0
    if gate_passed:
        expected_status = (
            "read_only_q7_setups_recorded"
            if has_qualified_setups
            else "read_only_no_q7_setups"
        )
        expected_stage_status = (
            "qualified_setup_ledger_recorded_with_q7_setups"
            if has_qualified_setups
            else "qualified_setup_ledger_recorded_no_q7_setup_window"
        )
        if artifact.get("status") != expected_status:
            errors.append("qualified_setup_status_invalid")
        if artifact.get("stage_status") != expected_stage_status:
            errors.append("qualified_setup_stage_status_invalid")
        if blockers:
            errors.append("qualified_setup_recorded_with_blockers")
        if artifact.get("q7_4_weekly_cadence_tracker_stage_allowed") is not True:
            errors.append("q7_4_weekly_cadence_not_allowed")
        if artifact.get("read_only_eligibility_ledger_allowed") is not True:
            errors.append("read_only_eligibility_ledger_not_allowed")
    else:
        if artifact.get("status") not in {"blocked", "error"}:
            errors.append("qualified_setup_blocked_status_invalid")
        if not blockers and artifact.get("status") != "error":
            errors.append("qualified_setup_blocked_without_blockers")
        if artifact.get("q7_4_weekly_cadence_tracker_stage_allowed") is not False:
            errors.append("q7_4_weekly_cadence_allowed_while_blocked")

    errors.extend(_authority_errors(artifact))
    errors.extend(_contract_errors(artifact))
    errors.extend(_daily_decision_errors(artifact))
    errors.extend(_weekly_summary_errors(artifact))
    errors.extend(_candidate_record_errors(artifact))

    qualified_records = artifact.get("qualified_setup_records", [])
    if not isinstance(qualified_records, list):
        errors.append("qualified_setup_records_not_list")
        qualified_records = []
    if artifact.get("qualified_setup_record_count") != len(qualified_records):
        errors.append("qualified_setup_record_count_mismatch")
    qualified_record_count = sum(
        1
        for record in qualified_records
        if isinstance(record, dict) and record.get("qualified_setup") is True
    )
    if artifact.get("qualified_setup_count") != qualified_record_count:
        errors.append("qualified_setup_count_mismatch")
    if artifact.get("eligible_setup_count") != qualified_record_count:
        errors.append("eligible_setup_count_mismatch")
    for record in qualified_records:
        if not isinstance(record, dict):
            errors.append("qualified_setup_record_invalid")
            continue
        if record.get("source_phase") != "Q7":
            errors.append("qualified_setup_record_non_q7_source")
        if record.get("phase5_lifecycle_counts_as_q7_proof") is not False:
            errors.append("qualified_setup_record_phase5_reuse")
        if record.get("proof_trade_created") is not False:
            errors.append("qualified_setup_record_proof_trade_created")
        if record.get("proof_credit_allowed") is not False:
            errors.append("qualified_setup_record_proof_credit_allowed")

    for count_field in (
        "expired_setup_count",
        "supplemental_only_setup_rejected_count",
        "phase7_demo_day_count",
        "proof_trade_count",
        "closed_proof_trade_count",
        "postmortem_due_count",
    ):
        if int(artifact.get(count_field, 0) or 0) != 0:
            errors.append(f"qualified_setup_count_nonzero:{count_field}")
    if has_qualified_setups and int(artifact.get("target_proof_trade_count", 0) or 0) <= 0:
        errors.append("qualified_setup_target_count_missing")
    if not has_qualified_setups and int(artifact.get("target_proof_trade_count", 0) or 0) != 0:
        errors.append("qualified_setup_target_count_without_setups")
    if artifact.get("daily_setup_decision_count") != len(artifact.get("daily_setup_decisions", [])):
        errors.append("daily_setup_decision_count_field_mismatch")
    if artifact.get("weekly_setup_summary_count") != len(artifact.get("weekly_setup_summaries", [])):
        errors.append("weekly_setup_summary_count_field_mismatch")
    expected_no_trade_days = sum(
        1
        for day in artifact.get("daily_setup_decisions", [])
        if isinstance(day, dict) and day.get("no_trade_explanation_recorded") is True
    )
    expected_no_trade_weeks = sum(
        1
        for week in artifact.get("weekly_setup_summaries", [])
        if isinstance(week, dict) and week.get("no_trade_explanation_recorded") is True
    )
    if artifact.get("no_trade_day_explanation_count") != expected_no_trade_days:
        errors.append("no_trade_day_explanation_count_mismatch")
    if artifact.get("no_trade_week_explanation_count") != expected_no_trade_weeks:
        errors.append("no_trade_week_explanation_count_mismatch")
    if artifact.get("rejected_phase5_lifecycle_count") < 1:
        errors.append("rejected_phase5_lifecycle_missing")
    for field in (
        "supplemental_only_qualification_allowed",
        "source_quorum_bypass_allowed",
        "phase5_test_trades_count_for_phase7",
        "q6_deferred_learning_counts_as_proof",
        "private_world_model_counts_as_proof",
        "calendar_harness_started",
    ):
        if artifact.get(field) is not False:
            errors.append(f"qualified_setup_forbidden:{field}")
    if float(artifact.get("paper_account_starting_gbp", 0.0) or 0.0) != (
        PHASE7_PAPER_ACCOUNT_STARTING_GBP
    ):
        errors.append("qualified_setup_paper_account_starting_gbp_mismatch")
    if float(artifact.get("max_drawdown_fraction", 0.0) or 0.0) != (
        PHASE7_MAX_DRAWDOWN_FRACTION
    ):
        errors.append("qualified_setup_max_drawdown_fraction_mismatch")
    if artifact.get("mature_closed_trade_benchmark") != PHASE7_MATURE_CLOSED_TRADE_BENCHMARK:
        errors.append("qualified_setup_mature_benchmark_mismatch")
    if artifact.get("statistical_immaturity_allowed") is not True:
        errors.append("qualified_setup_statistical_immaturity_not_allowed")

    source_posture = artifact.get("source_posture", {})
    if not isinstance(source_posture, dict):
        errors.append("qualified_setup_source_posture_missing")
        source_posture = {}
    if source_posture.get("yahoo_finance_role") != "supplemental_market_confirmation_only":
        errors.append("qualified_setup_yahoo_finance_role_invalid")
    if source_posture.get("preference_mcp_role") != "supplemental_multi_source_data_plane":
        errors.append("qualified_setup_preference_mcp_role_invalid")
    if source_posture.get("preference_mcp_source_quorum_credit_allowed") is not False:
        errors.append("qualified_setup_preference_quorum_credit_allowed")
    if source_posture.get("qctrl_role") != "shadow_annotation_only":
        errors.append("qualified_setup_qctrl_role_invalid")
    if source_posture.get("phase5_test_lifecycle_role") != "excluded_from_phase7_proof":
        errors.append("qualified_setup_phase5_lifecycle_role_invalid")
    if source_posture.get("supplemental_source_bypass_allowed") is not False:
        errors.append("qualified_setup_supplemental_bypass_allowed")

    proof_contract = artifact.get("proof_contract", {})
    if not isinstance(proof_contract, dict):
        errors.append("qualified_setup_proof_contract_missing")
        proof_contract = {}
    if proof_contract.get("harness_day_count") != PHASE7_HARNESS_DAY_COUNT:
        errors.append("qualified_setup_proof_contract_day_count_mismatch")
    if proof_contract.get("weekly_proof_trade_target") != PHASE7_WEEKLY_PROOF_TRADE_TARGET:
        errors.append("qualified_setup_proof_contract_weekly_target_mismatch")
    if proof_contract.get("phase5_test_trade_reuse_allowed") is not False:
        errors.append("qualified_setup_proof_contract_phase5_reuse_allowed")
    if proof_contract.get("manual_trade_level_override_allowed") is not False:
        errors.append("qualified_setup_proof_contract_manual_override_allowed")

    provenance = artifact.get("provenance", {})
    if not isinstance(provenance, dict):
        errors.append("qualified_setup_provenance_missing")
        provenance = {}
    for ref in provenance.get("source_refs", []) or []:
        ref_text = str(ref)
        lowered = ref_text.lower()
        if ref_text.startswith("/") or ref_text.startswith("~"):
            errors.append("qualified_setup_provenance_local_path_leak")
        if "api_key" in lowered or "secret" in lowered or "token" in lowered:
            errors.append("qualified_setup_provenance_secret_ref_leak")
    for field in (
        "raw_secret_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "broker_identifier_exposed",
    ):
        if provenance.get(field) is not False:
            errors.append(f"qualified_setup_provenance_exposure_enabled:{field}")

    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "cannot start the proof harness",
        "cannot create qualified setups from Phase 5 lifecycle records",
        "cannot qualify a setup from supplemental-only sources",
        "cannot create proof trades",
        "cannot grant Phase 7 proof credit",
        "cannot enable live capital",
        "cannot permit manual trade-level overrides",
    ):
        if phrase not in boundary:
            errors.append("qualified_setup_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("qualified_setup_event_log_path_missing")
        if not str(artifact.get("event_log_correlation_id") or "").strip():
            errors.append("qualified_setup_event_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("qualified_setup_event_log_count_mismatch")
    return sorted(set(errors))


def attach_phase7_qualified_setup_ledger_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(
        event_log_path or (_runtime_dir(settings) / PHASE7_QUALIFIED_SETUP_LEDGER_EVENT_LOG)
    )
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE7_QUALIFIED_SETUP_LEDGER_EVENT_TYPE,
        PHASE7_QUALIFIED_SETUP_LEDGER_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "stage_status": output.get("stage_status"),
            "daily_setup_decision_count": output.get("daily_setup_decision_count"),
            "weekly_setup_summary_count": output.get("weekly_setup_summary_count"),
            "qualified_setup_count": output.get("qualified_setup_count"),
            "no_trade_day_explanation_count": output.get("no_trade_day_explanation_count"),
            "no_trade_week_explanation_count": output.get("no_trade_week_explanation_count"),
            "rejected_phase5_lifecycle_count": output.get("rejected_phase5_lifecycle_count"),
            "phase5_test_trades_count_for_phase7": output.get(
                "phase5_test_trades_count_for_phase7"
            ),
            "proof_trade_count": output.get("proof_trade_count"),
            "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
            "live_capital_enabled": output.get("live_capital_enabled"),
            "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
            "recommended_next_stage": output.get("recommended_next_stage"),
            "boundary": output.get("boundary"),
        },
    )
    output["recorded"] = True
    output["event_log_written"] = True
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = 1
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_created_at"] = entry.created_at
    output["validation_errors"] = validate_phase7_qualified_setup_ledger(output)
    if output["validation_errors"]:
        output["status"] = "error"
        output["stage_status"] = "qualified_setup_ledger_validation_error"
    return output, entry


def write_phase7_qualified_setup_ledger(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase7_qualified_setup_ledger_paths(
        settings
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase7_qualified_setup_ledger_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase7_qualified_setup_ledger(output)
        if output["validation_errors"]:
            output["status"] = "error"
            output["stage_status"] = "qualified_setup_ledger_validation_error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase7_qualified_setup_ledger(output)
    if output["validation_errors"]:
        output["status"] = "error"
        output["stage_status"] = "qualified_setup_ledger_validation_error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE7_QUALIFIED_SETUP_LEDGER_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "stage_status": output.get("stage_status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "daily_setup_decision_count": output.get("daily_setup_decision_count"),
        "weekly_setup_summary_count": output.get("weekly_setup_summary_count"),
        "qualified_setup_count": output.get("qualified_setup_count"),
        "rejected_phase5_lifecycle_count": output.get("rejected_phase5_lifecycle_count"),
        "proof_trade_count": output.get("proof_trade_count"),
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
