#!/usr/bin/env python3
"""Certify Qadam's next-generation flow.

This checker is deliberately fail-closed. It reads the current runtime artifacts
and writes a certification artifact, but it does not refresh sources, edit code,
change secrets, mutate authority, submit orders, write brokers, enable live
capital, or grant proof credit.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402

SCHEMA_VERSION = "qadam_next_generation_flow_certification.v1"
PHASE_ID = "qadam_next_generation_phase_15_certification"
CERTIFICATION_ARTIFACT = "qadam_next_generation_flow_certification.json"

ZERO_OR_FALSE_FIELDS = (
    "paper_order_created_count",
    "broker_write_count",
    "trade_candidate_created_count",
    "qualified_setup_created_count",
    "risk_approval_created_count",
    "execution_approval_created_count",
    "backtest_shadow_or_synthetic_proof_credit_count",
)

FALSE_ONLY_FIELDS = (
    "live_capital_enabled",
    "proof_credit_allowed",
    "paper_proof_ledger_credit_allowed",
    "paper_growth_trial_calendar_advanced",
    "simulated_elapsed_time_allowed",
    "telegram_command_path_enabled",
    "telegram_trade_command_enabled",
    "trade_candidate_created",
    "qualified_setup_created",
    "risk_approval_created",
    "execution_approval_created",
    "paper_order_created",
    "broker_write_allowed",
    "paper_order_allowed",
)

ARTIFACTS = {
    "source_reliability": "qsase_source_reliability.json",
    "source_reliability_records": "qsase_source_reliability_records.jsonl",
    "whole_universe_summary": "qsase_whole_universe_backfill_backtest_dashboard_summary.json",
    "whole_universe_state": "qsase_whole_universe_backfill_backtest_state.json",
    "historical_memory": "qsase_historical_memory_completion.json",
    "leakage_audit": "qsase_historical_memory_leakage_audit.json",
    "evidence_contracts": "qadam_evidence_contracts_dashboard_summary.json",
    "strategy_evidence_map": "qadam_strategy_evidence_map_dashboard_summary.json",
    "pattern_engine": "qadam_pattern_engine_v2_dashboard_summary.json",
    "pattern_engine_primary": "qadam_pattern_engine_v2.json",
    "pattern_engine_records": "qadam_pattern_engine_v2_records.jsonl",
    "akber_filter": "qadam_akber_filter_v2_dashboard_summary.json",
    "akber_filter_results": "qadam_akber_filter_v2_results.jsonl",
    "shadow_simulator": "qadam_shadow_simulator_v2_dashboard_summary.json",
    "router": "qadam_router_v2_dashboard_summary.json",
    "router_primary": "qadam_router_v2_paperops_handoff.json",
    "router_decisions": "qadam_router_v2_decisions.jsonl",
    "paperops_handoffs": "qadam_paperops_handoff_v2_records.jsonl",
    "paperops_rejected_handoffs": "qadam_paperops_handoff_v2_rejections.jsonl",
    "paper_lifecycle": "qadam_paper_lifecycle_v2_dashboard_summary.json",
    "dashboard_vnext": "qadam_dashboard_vnext_dashboard_summary.json",
    "dashboard_status": "qsase_dashboard_status.json",
    "dashboard_anti_slop": "qsase_dashboard_anti_slop_audit.json",
    "telegram_vnext": "qadam_telegram_vnext_dashboard_summary.json",
    "telegram_mirror": "qadam_telegram_next_generation_dashboard_communications_mirror.json",
    "learning_attribution": "qadam_learning_attribution_v2_dashboard_summary.json",
    "self_healing": "qadam_self_healing_status.json",
}


def _runtime_dir(settings: Settings | None = None) -> Path:
    active = settings or Settings.from_env()
    path = Path(active.runtime_dir)
    if not path.is_absolute():
        path = ROOT / path
    return path


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _artifact_ref(filename: str) -> str:
    return f"data/runtime/{filename}"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in lines:
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            records.append(value)
    return records


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return default
    return default


def _bool_false(value: Any) -> bool:
    return value is False or value == 0 or value is None


def _gate(
    gate_id: str,
    title: str,
    passed: bool,
    *,
    reason: str,
    blocker: str = "none",
    artifacts: list[str] | None = None,
    details: dict[str, Any] | None = None,
    severity: str = "critical",
) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "title": title,
        "state": "passed" if passed else "blocked",
        "passed": passed,
        "severity": "none" if passed else severity,
        "reason": reason,
        "blocker": "none" if passed else blocker,
        "artifact_refs": artifacts or [],
        "details": details or {},
    }


def _missing_gate(gate_id: str, title: str, filename: str) -> dict[str, Any]:
    return _gate(
        gate_id,
        title,
        False,
        reason=f"Required artifact {filename} is missing or unreadable.",
        blocker=f"{filename}_missing",
        artifacts=[_artifact_ref(filename)],
    )


def _artifact_present(runtime: Path, filename: str) -> bool:
    path = runtime / filename
    if not path.exists():
        return False
    if filename.endswith(".jsonl"):
        return True
    return bool(_read_json(path))


def _source_freshness_gate(runtime: Path, context: dict[str, Any]) -> dict[str, Any]:
    filename = ARTIFACTS["source_reliability_records"]
    records = _read_jsonl(runtime / filename)
    if not records:
        return _missing_gate("source_freshness", "Fresh Sources", filename)
    required = [
        record
        for record in records
        if record.get("raw_required_for_reliability_target") is True
        or record.get("required_for_reliability_target") is True
    ]
    stale_required = [
        record
        for record in required
        if record.get("freshness_state") != "fresh" or record.get("outage_state") != "ok"
    ]
    quorum_blocked = [
        record
        for record in records
        if record.get("source_quorum_contribution", {}).get("can_contribute") is False
        and record.get("supplemental_context_only") is not True
    ]
    self_healing = context.get("self_healing", {})
    provider_outage_count = _int(
        self_healing.get("provider_outage_classification", {}).get("provider_outage_count"),
        0,
    )
    passed = not stale_required and provider_outage_count == 0
    return _gate(
        "source_freshness",
        "Fresh Sources",
        passed,
        reason=(
            "All required source records are fresh and no provider outages are classified."
            if passed
            else f"{len(stale_required)} required source records are stale/offline and {provider_outage_count} provider outages are classified."
        ),
        blocker="source_freshness_or_provider_outage_blocker",
        artifacts=[_artifact_ref(filename), _artifact_ref(ARTIFACTS["self_healing"])],
        details={
            "source_record_count": len(records),
            "required_source_record_count": len(required),
            "stale_required_source_count": len(stale_required),
            "quorum_blocked_source_count": len(quorum_blocked),
            "provider_outage_count": provider_outage_count,
            "sample_blocked_sources": [
                {
                    "source_key": record.get("source_key"),
                    "source_name": record.get("source_name"),
                    "freshness_state": record.get("freshness_state"),
                    "outage_state": record.get("outage_state"),
                    "reason": record.get("outage_reason"),
                }
                for record in stale_required[:5]
            ],
        },
    )


def _baseline_gate(context: dict[str, Any]) -> dict[str, Any]:
    summary = context.get("whole_universe_summary", {})
    if not summary:
        return _missing_gate("baseline_evidence", "Whole-Universe Baseline Evidence", ARTIFACTS["whole_universe_summary"])
    complete_windows = _int(summary.get("complete_forward_window_count"), 0)
    baseline_results = _int(summary.get("baseline_result_count"), 0)
    provider_gaps = _int(summary.get("provider_gap_count"), 0)
    status = str(summary.get("status") or "")
    passed = complete_windows > 0 and baseline_results > 0 and provider_gaps == 0 and "provider_gaps" not in status
    return _gate(
        "baseline_evidence",
        "Whole-Universe Baseline Evidence",
        passed,
        reason=(
            "Whole-universe baseline exists without provider gaps."
            if passed
            else "Whole-universe baseline exists, but provider gaps or incomplete windows still block certification."
        ),
        blocker="baseline_provider_gaps_or_incomplete_windows",
        artifacts=[_artifact_ref(ARTIFACTS["whole_universe_summary"])],
        details={
            "status": summary.get("status"),
            "complete_forward_window_count": complete_windows,
            "missing_forward_window_count": summary.get("missing_forward_window_count"),
            "baseline_result_count": baseline_results,
            "provider_gap_count": provider_gaps,
        },
    )


def _leakage_gate(context: dict[str, Any]) -> dict[str, Any]:
    audit = context.get("leakage_audit", {})
    if not audit:
        return _missing_gate("leakage_checks", "Leakage Checks", ARTIFACTS["leakage_audit"])
    violation_count = sum(
        _int(audit.get(field), 0)
        for field in (
            "future_feature_timestamp_violation_count",
            "outcome_available_before_decision_violation_count",
            "leakage_rejected_record_count",
        )
    )
    passed = str(audit.get("status")) == "leakage_checks_passed" and violation_count == 0
    return _gate(
        "leakage_checks",
        "Leakage Checks",
        passed,
        reason="Historical replay is lookahead-safe." if passed else "Historical replay has leakage violations or no pass state.",
        blocker="historical_leakage_check_failed",
        artifacts=[_artifact_ref(ARTIFACTS["leakage_audit"])],
        details={
            "status": audit.get("status"),
            "lookahead_safe_record_count": audit.get("lookahead_safe_record_count"),
            "leakage_violation_count": violation_count,
        },
    )


def _forward_window_gate(context: dict[str, Any]) -> dict[str, Any]:
    historical = context.get("historical_memory", {})
    summary = context.get("whole_universe_summary", {})
    if not historical:
        return _missing_gate("forward_windows", "Forward Windows For Paper-Review Instruments", ARTIFACTS["historical_memory"])
    passed = (
        historical.get("operational_backtest_memory_passed") is True
        and historical.get("target_complete_forward_window_passed") is True
        and _int(summary.get("complete_forward_window_count"), 0) > 0
    )
    return _gate(
        "forward_windows",
        "Forward Windows For Paper-Review Instruments",
        passed,
        reason=(
            "Forward-window target passes for current paper-review research."
            if passed
            else "Forward-window target is not explicitly passed for current paper-review research."
        ),
        blocker="historical_forward_window_target_not_passed",
        artifacts=[_artifact_ref(ARTIFACTS["historical_memory"]), _artifact_ref(ARTIFACTS["whole_universe_summary"])],
        details={
            "operational_backtest_memory_passed": historical.get("operational_backtest_memory_passed"),
            "target_complete_forward_window_passed": historical.get("target_complete_forward_window_passed"),
            "complete_forward_window_count": historical.get("complete_forward_window_count"),
            "missing_forward_window_count": historical.get("missing_forward_window_count"),
        },
    )


def _evidence_contract_gate(context: dict[str, Any]) -> dict[str, Any]:
    contracts = context.get("evidence_contracts", {})
    if not contracts:
        return _missing_gate("evidence_contracts", "Evidence-Native Contracts", ARTIFACTS["evidence_contracts"])
    missing = _int(contracts.get("missing_evidence_count"), 0)
    total = _int(contracts.get("total_contract_count"), 0)
    passed = total > 0 and missing == 0
    return _gate(
        "evidence_contracts",
        "Evidence-Native Contracts",
        passed,
        reason="All evidence contracts are present and complete." if passed else f"{missing} typed evidence fields are still missing.",
        blocker="typed_evidence_missing",
        artifacts=[_artifact_ref(ARTIFACTS["evidence_contracts"])],
        details={
            "total_contract_count": total,
            "missing_evidence_count": missing,
            "contracts_with_missing_evidence_count": contracts.get("contracts_with_missing_evidence_count"),
        },
    )


def _strategy_evidence_gate(context: dict[str, Any]) -> dict[str, Any]:
    strategy = context.get("strategy_evidence_map", {})
    if not strategy:
        return _missing_gate("strategy_evidence_map", "Strategy Evidence Map", ARTIFACTS["strategy_evidence_map"])
    strategy_count = _int(strategy.get("strategy_count"), 0)
    under_evidenced = _int(strategy.get("under_evidenced_strategy_count"), 0)
    passed = strategy_count > 0 and under_evidenced == 0
    return _gate(
        "strategy_evidence_map",
        "Strategy Evidence Map",
        passed,
        reason="Every strategy family has enough evidence for certification." if passed else f"{under_evidenced} strategy families remain under-evidenced.",
        blocker="strategy_evidence_map_under_evidenced",
        artifacts=[_artifact_ref(ARTIFACTS["strategy_evidence_map"])],
        details={
            "strategy_count": strategy_count,
            "evidence_backed_strategy_count": strategy.get("evidence_backed_strategy_count"),
            "under_evidenced_strategy_count": under_evidenced,
        },
    )


def _pattern_gate(runtime: Path, context: dict[str, Any]) -> dict[str, Any]:
    pattern = context.get("pattern_engine", {})
    primary = context.get("pattern_engine_primary", {})
    records = _read_jsonl(runtime / ARTIFACTS["pattern_engine_records"])
    if not pattern or not primary:
        return _missing_gate("ranked_patterns", "Ranked Non-Repetitive Patterns", ARTIFACTS["pattern_engine"])
    pattern_ids = [record.get("pattern_id") for record in records if record.get("pattern_id")]
    duplicate_ids = [pattern_id for pattern_id, count in Counter(pattern_ids).items() if count > 1]
    signatures = [record.get("distinctness_signature") for record in records if record.get("distinctness_signature")]
    duplicate_signatures = [signature for signature, count in Counter(signatures).items() if count > 1]
    repetitive_records = [record.get("pattern_id") for record in records if record.get("non_repetitive") is not True]
    ranked = _int(pattern.get("ranked_pattern_count"), 0)
    duplicate_rejections = _int(primary.get("duplicate_rejection_count"), 0)
    distinct_count = _int(primary.get("distinct_pattern_count"), 0)
    passed = (
        ranked > 0
        and bool(records)
        and not duplicate_ids
        and not duplicate_signatures
        and not repetitive_records
        and distinct_count == _int(primary.get("pattern_count"), 0)
    )
    return _gate(
        "ranked_patterns",
        "Ranked Non-Repetitive Patterns",
        passed,
        reason=(
            "Pattern engine has ranked, distinct, lifecycle-aware research patterns."
            if passed
            else "Pattern engine lacks ranked distinct patterns or duplicate rejection evidence."
        ),
        blocker="pattern_ranking_or_duplicate_control_incomplete",
        artifacts=[_artifact_ref(ARTIFACTS["pattern_engine"]), _artifact_ref(ARTIFACTS["pattern_engine_primary"])],
        details={
            "pattern_count": pattern.get("pattern_count"),
            "ranked_pattern_count": ranked,
            "distinct_pattern_count": distinct_count,
            "duplicate_rejection_count": duplicate_rejections,
            "duplicate_record_id_count": len(duplicate_ids),
            "duplicate_signature_count": len(duplicate_signatures),
            "repetitive_record_count": len(repetitive_records),
            "lifecycle_counts": primary.get("lifecycle_counts"),
        },
    )


def _akber_gate(context: dict[str, Any]) -> dict[str, Any]:
    akber = context.get("akber_filter", {})
    if not akber:
        return _missing_gate("akber_context", "Complete Akber Context", ARTIFACTS["akber_filter"])
    return _akber_gate_from_payload(akber, [])


def _akber_gate_from_payload(akber: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    if not akber:
        return _missing_gate("akber_context", "Complete Akber Context", ARTIFACTS["akber_filter"])
    router_eligible_missing = _int(akber.get("router_eligible_with_missing_context_count"), 0)
    missing_for_any_current_setup = sum(_int(record.get("missing_context_count"), 0) for record in records)
    critical_missing_context_count = sum(_int(record.get("critical_missing_context_count"), 0) for record in records)
    hold_missing_context_count = sum(1 for record in records if record.get("status") == "akber_v2_hold_missing_context")
    pass_count = _int(akber.get("pass_count"), 0)
    passed = (
        akber.get("no_router_eligible_setup_has_missing_akber_context") is True
        and router_eligible_missing == 0
        and missing_for_any_current_setup == 0
        and critical_missing_context_count == 0
        and hold_missing_context_count == 0
    )
    return _gate(
        "akber_context",
        "Complete Akber Context",
        passed,
        reason=(
            "Akber has complete context for Router-eligible setups and no current missing-context packets."
            if passed
            else "Akber is still holding because practical confirmation context is incomplete."
        ),
        blocker="akber_practical_confirmation_missing",
        artifacts=[_artifact_ref(ARTIFACTS["akber_filter"]), _artifact_ref(ARTIFACTS["akber_filter_results"])],
        details={
            "akber_input_count": akber.get("akber_input_count"),
            "akber_result_count": akber.get("akber_result_count"),
            "pass_count": pass_count,
            "hold_count": akber.get("hold_count"),
            "router_eligible_count": akber.get("router_eligible_count"),
            "router_eligible_with_missing_context_count": router_eligible_missing,
            "missing_context_count": missing_for_any_current_setup,
            "critical_missing_context_count": critical_missing_context_count,
            "hold_missing_context_count": hold_missing_context_count,
            "no_router_eligible_setup_has_missing_akber_context": akber.get("no_router_eligible_setup_has_missing_akber_context"),
        },
    )


def _shadow_gate(context: dict[str, Any]) -> dict[str, Any]:
    shadow = context.get("shadow_simulator", {})
    if not shadow:
        return _missing_gate("shadow_outputs", "Shadow Outputs", ARTIFACTS["shadow_simulator"])
    passed = (
        shadow.get("every_hypothesis_has_shadow_evidence") is True
        and _int(shadow.get("missing_shadow_evidence_count"), 0) == 0
        and _int(shadow.get("historical_shadow_replay_count"), 0) > 0
        and _int(shadow.get("forward_tracking_count"), 0) > 0
        and shadow.get("shadow_success_cannot_create_paper_order") is True
        and shadow.get("shadow_success_cannot_create_proof_credit") is True
    )
    return _gate(
        "shadow_outputs",
        "Shadow Outputs",
        passed,
        reason="Shadow simulator has historical, forward, counterfactual, and safety outputs." if passed else "Shadow outputs are incomplete or unsafe.",
        blocker="shadow_outputs_incomplete",
        artifacts=[_artifact_ref(ARTIFACTS["shadow_simulator"])],
        details={
            "hypothesis_count": shadow.get("hypothesis_count"),
            "hypothesis_with_shadow_evidence_count": shadow.get("hypothesis_with_shadow_evidence_count"),
            "missing_shadow_evidence_count": shadow.get("missing_shadow_evidence_count"),
            "historical_shadow_replay_count": shadow.get("historical_shadow_replay_count"),
            "forward_tracking_count": shadow.get("forward_tracking_count"),
            "counterfactual_no_order_count": shadow.get("counterfactual_no_order_count"),
        },
    )


def _router_gate(runtime: Path, context: dict[str, Any]) -> dict[str, Any]:
    router = context.get("router", {})
    decisions = _read_jsonl(runtime / ARTIFACTS["router_decisions"])
    if not router:
        return _missing_gate("router_single_state", "Single-State Router Decisions", ARTIFACTS["router"])
    invalid_records = [
        record.get("router_decision_id")
        for record in decisions
        if record.get("setup_has_exactly_one_final_state") is not True or not record.get("final_state")
    ]
    setup_count = _int(router.get("setup_count"), 0)
    decision_count = _int(router.get("decision_count"), 0)
    passed = (
        setup_count > 0
        and decision_count == setup_count
        and router.get("all_setups_have_exactly_one_final_state") is True
        and not invalid_records
    )
    return _gate(
        "router_single_state",
        "Single-State Router Decisions",
        passed,
        reason="Every setup has exactly one Router final state." if passed else "Router decisions are missing or not single-state.",
        blocker="router_single_state_contract_failed",
        artifacts=[_artifact_ref(ARTIFACTS["router"]), _artifact_ref(ARTIFACTS["router_decisions"])],
        details={
            "setup_count": setup_count,
            "decision_count": decision_count,
            "all_setups_have_exactly_one_final_state": router.get("all_setups_have_exactly_one_final_state"),
            "invalid_record_count": len(invalid_records),
            "final_state_counts": Counter(str(record.get("final_state")) for record in decisions),
        },
    )


def _paperops_handoff_gate(runtime: Path, context: dict[str, Any]) -> dict[str, Any]:
    router = context.get("router", {})
    primary = context.get("router_primary", {})
    handoffs = _read_jsonl(runtime / ARTIFACTS["paperops_handoffs"])
    rejected = _read_jsonl(runtime / ARTIFACTS["paperops_rejected_handoffs"])
    dirty = [
        record.get("handoff_record_id") or record.get("router_decision_id")
        for record in handoffs
        if record.get("clean_paper_review_candidate") is not True
        or record.get("paperops_handoff_allowed") is not True
        or record.get("paper_order_created") is not False
        or _int(record.get("broker_write_count"), 0) != 0
    ]
    passed = (
        router.get("only_clean_paper_review_candidates_reach_paperops") is True
        and primary.get("only_clean_paper_review_candidates_reach_paperops") is True
        and not dirty
        and _int(router.get("handoff_record_count"), 0) == len(handoffs)
    )
    return _gate(
        "paperops_handoff",
        "Clean PaperOps Handoffs",
        passed,
        reason="Only clean paper-review candidates can reach PaperOps." if passed else "PaperOps handoff records are missing, dirty, or inconsistent.",
        blocker="paperops_handoff_contract_failed",
        artifacts=[
            _artifact_ref(ARTIFACTS["router_primary"]),
            _artifact_ref(ARTIFACTS["paperops_handoffs"]),
            _artifact_ref(ARTIFACTS["paperops_rejected_handoffs"]),
        ],
        details={
            "handoff_record_count": len(handoffs),
            "rejected_handoff_count": len(rejected),
            "dirty_handoff_count": len(dirty),
            "only_clean_paper_review_candidates_reach_paperops": router.get("only_clean_paper_review_candidates_reach_paperops"),
        },
    )


def _dashboard_gate(context: dict[str, Any]) -> dict[str, Any]:
    dashboard = context.get("dashboard_vnext", {})
    status = context.get("dashboard_status", {})
    anti_slop = context.get("dashboard_anti_slop", {})
    if not dashboard or not anti_slop:
        return _missing_gate("dashboard_vnext_quality", "Dashboard VNext Quality", ARTIFACTS["dashboard_vnext"])
    required_flags = (
        "protected_sections_not_reordered",
        "protected_sections_not_renamed",
        "protected_sections_not_removed",
        "protected_sections_not_structurally_overhauled",
        "enrichment_only_inside_protected_sections",
        "all_portfolio_values_agree",
    )
    passed = (
        str(dashboard.get("status", "")).startswith("dashboard_vnext_ready")
        and all(dashboard.get(flag) is True for flag in required_flags)
        and _int(anti_slop.get("error_count"), 0) == 0
        and bool(status)
    )
    return _gate(
        "dashboard_vnext_quality",
        "Dashboard VNext Quality",
        passed,
        reason="Dashboard VNext quality and anti-slop gates pass." if passed else "Dashboard VNext quality or anti-slop gates fail.",
        blocker="dashboard_vnext_quality_failed",
        artifacts=[
            _artifact_ref(ARTIFACTS["dashboard_vnext"]),
            _artifact_ref(ARTIFACTS["dashboard_status"]),
            _artifact_ref(ARTIFACTS["dashboard_anti_slop"]),
        ],
        details={
            "dashboard_status": dashboard.get("status"),
            "dashboard_view_model_status": status.get("status"),
            "anti_slop_error_count": anti_slop.get("error_count"),
            "protected_flags": {flag: dashboard.get(flag) for flag in required_flags},
        },
    )


def _telegram_gate(context: dict[str, Any]) -> dict[str, Any]:
    telegram = context.get("telegram_vnext", {})
    mirror = context.get("telegram_mirror", {})
    if not telegram:
        return _missing_gate("telegram_vnext_quality", "Telegram VNext Quality", ARTIFACTS["telegram_vnext"])
    quality_rejects = _int(telegram.get("message_rejected_quality_count"), 0)
    unsafe_rejects = _int(telegram.get("message_rejected_unsafe_count"), 0)
    candidate_count = _int(telegram.get("message_candidate_count"), 0)
    pass_count = _int(telegram.get("quality_pass_count"), 0)
    passed = (
        candidate_count > 0
        and pass_count == candidate_count
        and quality_rejects == 0
        and unsafe_rejects == 0
        and telegram.get("telegram_live_send_allowed") is False
        and telegram.get("telegram_command_path_enabled") is False
        and bool(mirror)
    )
    return _gate(
        "telegram_vnext_quality",
        "Telegram VNext Quality",
        passed,
        reason="Telegram VNext quality, dedupe, mirror, and safety gates pass." if passed else "Telegram VNext quality or safety gates fail.",
        blocker="telegram_vnext_quality_failed",
        artifacts=[_artifact_ref(ARTIFACTS["telegram_vnext"]), _artifact_ref(ARTIFACTS["telegram_mirror"])],
        details={
            "message_candidate_count": candidate_count,
            "quality_pass_count": pass_count,
            "message_rejected_duplicate_count": telegram.get("message_rejected_duplicate_count"),
            "message_rejected_quality_count": quality_rejects,
            "message_rejected_unsafe_count": unsafe_rejects,
            "telegram_live_send_allowed": telegram.get("telegram_live_send_allowed"),
            "telegram_command_path_enabled": telegram.get("telegram_command_path_enabled"),
        },
    )


def _why_not_trading_gate(context: dict[str, Any]) -> dict[str, Any]:
    router = context.get("router", {})
    reason = str(router.get("why_not_trading_now_reason") or "")
    plain = str(router.get("why_not_trading_now_plain_english") or "")
    bad = not reason or reason == "none" or "not_recorded" in reason
    distinguishes = any(token in reason for token in ("no_setup", "akber", "research_lock", "system", "source", "evidence", "market"))
    passed = not bad and distinguishes and bool(plain)
    return _gate(
        "why_not_trading_now",
        "Why-Not-Trading-Now Clarity",
        passed,
        reason="Why-not-trading-now distinguishes current discipline from blockers." if passed else "Why-not-trading-now is missing or too vague.",
        blocker="why_not_trading_now_not_specific",
        artifacts=[_artifact_ref(ARTIFACTS["router"])],
        details={"reason": reason, "plain_english": plain},
        severity="high",
    )


def _safety_gate(context: dict[str, Any]) -> dict[str, Any]:
    checked: dict[str, dict[str, Any]] = {}
    violations: list[dict[str, Any]] = []
    for key, filename in ARTIFACTS.items():
        payload = context.get(key)
        if not isinstance(payload, dict) or not payload:
            continue
        artifact_violations: list[str] = []
        authority = payload.get("authority") if isinstance(payload.get("authority"), dict) else {}
        for field in FALSE_ONLY_FIELDS:
            value = payload.get(field, authority.get(field))
            if value is True:
                artifact_violations.append(field)
        for field in ZERO_OR_FALSE_FIELDS:
            value = payload.get(field, authority.get(field))
            if value not in (None, False, 0):
                artifact_violations.append(field)
        if artifact_violations:
            violations.append({"artifact": _artifact_ref(filename), "fields": sorted(set(artifact_violations))})
        checked[key] = {"artifact": _artifact_ref(filename), "violation_count": len(set(artifact_violations))}
    lifecycle = context.get("paper_lifecycle", {})
    if _int(lifecycle.get("backtest_shadow_or_synthetic_proof_credit_count"), 0) != 0:
        violations.append(
            {
                "artifact": _artifact_ref(ARTIFACTS["paper_lifecycle"]),
                "fields": ["backtest_shadow_or_synthetic_proof_credit_count"],
            }
        )
    passed = not violations
    return _gate(
        "safety_boundaries",
        "Disabled Live Capital And Proof Boundary",
        passed,
        reason="Live capital, unauthorized broker writes, and unauthorized proof credit are disabled." if passed else "Unsafe authority or proof boundary drift was detected.",
        blocker="authority_or_proof_boundary_violation",
        artifacts=[_artifact_ref(filename) for filename in ARTIFACTS.values() if not filename.endswith(".jsonl")],
        details={
            "checked_artifact_count": len(checked),
            "violation_count": len(violations),
            "violations": violations,
        },
    )


def _required_artifacts_gate(runtime: Path) -> dict[str, Any]:
    missing = [
        filename
        for filename in ARTIFACTS.values()
        if not _artifact_present(runtime, filename)
    ]
    return _gate(
        "required_artifacts",
        "Required Runtime Artifacts",
        not missing,
        reason="All required next-generation runtime artifacts are present." if not missing else f"{len(missing)} required artifacts are missing.",
        blocker="required_runtime_artifacts_missing",
        artifacts=[_artifact_ref(filename) for filename in ARTIFACTS.values()],
        details={"missing_artifacts": [_artifact_ref(filename) for filename in missing]},
    )


def _load_context(runtime: Path) -> dict[str, Any]:
    context: dict[str, Any] = {}
    for key, filename in ARTIFACTS.items():
        if filename.endswith(".jsonl"):
            continue
        context[key] = _read_json(runtime / filename)
    return context


def build_certification(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    generated_at = _now_iso()
    context = _load_context(runtime)
    gates = [
        _required_artifacts_gate(runtime),
        _source_freshness_gate(runtime, context),
        _baseline_gate(context),
        _leakage_gate(context),
        _forward_window_gate(context),
        _evidence_contract_gate(context),
        _strategy_evidence_gate(context),
        _pattern_gate(runtime, context),
        _akber_gate_from_payload(
            context.get("akber_filter", {}),
            _read_jsonl(runtime / ARTIFACTS["akber_filter_results"]),
        ),
        _shadow_gate(context),
        _router_gate(runtime, context),
        _paperops_handoff_gate(runtime, context),
        _dashboard_gate(context),
        _telegram_gate(context),
        _why_not_trading_gate(context),
        _safety_gate(context),
    ]
    blockers = [
        {
            "gate_id": gate["gate_id"],
            "title": gate["title"],
            "severity": gate["severity"],
            "blocker": gate["blocker"],
            "reason": gate["reason"],
            "artifact_refs": gate["artifact_refs"],
            "details": gate["details"],
        }
        for gate in gates
        if not gate["passed"]
    ]
    passed_gate_count = sum(1 for gate in gates if gate["passed"])
    certified = not blockers
    status = "qadam_next_generation_flow_certified" if certified else "qadam_next_generation_flow_blocked"
    final_answer = (
        "Yes. Qadam is running the next-generation flow as designed. It is watching the world, testing historical "
        "source-price relationships, ranking evidence, filtering practical tradeability, routing only safe "
        "paper-review candidates, and learning from every outcome. It is not guaranteed to trade at every moment, "
        "but if it does not trade, the reason is visible and evidence-based."
        if certified
        else "No. Qadam is not yet certified as running the next-generation flow as designed. The certification "
        "failed closed with explicit blockers."
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_next_generation_flow_certification",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": status,
        "certified": certified,
        "operating_as_designed": certified,
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "proposal_first": True,
        "command_disabled": True,
        "gate_count": len(gates),
        "passed_gate_count": passed_gate_count,
        "failed_gate_count": len(gates) - passed_gate_count,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "gates": gates,
        "final_answer_contract": final_answer,
        "certification_does_not_guarantee_profit": True,
        "certification_does_not_guarantee_trades": True,
        "self_healing_may_retry_safe_refreshes": True,
        "code_edit_allowed": False,
        "secret_change_allowed": False,
        "test_bypass_allowed": False,
        "authority_change_allowed": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "paper_growth_trial_calendar_advanced": False,
        "simulated_elapsed_time_allowed": False,
        "artifact_refs": {"certification": _artifact_ref(CERTIFICATION_ARTIFACT), **{key: _artifact_ref(value) for key, value in ARTIFACTS.items()}},
        "boundary": (
            "Certification reads runtime artifacts and writes a certification result only. It cannot refresh sources, "
            "edit code, change secrets, bypass tests, alter authority, create candidates, approve risk, submit orders, "
            "write brokers, enable live capital, advance the 30-day paper growth trial calendar, or grant paper proof ledger credit."
        ),
    }
    return payload


def write_certification(payload: dict[str, Any], settings: Settings | None = None) -> Path:
    path = _runtime_dir(settings) / CERTIFICATION_ARTIFACT
    _write_json(path, payload)
    return path


def validate_certification(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if payload.get("artifact_type") != "qadam_next_generation_flow_certification":
        errors.append("artifact_type_mismatch")
    for field in ("public_safe", "read_only", "paper_only", "proposal_first", "command_disabled"):
        if payload.get(field) is not True:
            errors.append(f"{field}_must_be_true")
    for field in ("code_edit_allowed", "secret_change_allowed", "test_bypass_allowed", "authority_change_allowed"):
        if payload.get(field) is not False:
            errors.append(f"{field}_must_be_false")
    for field in ("paper_order_created_count", "broker_write_count"):
        if _int(payload.get(field), 0) != 0:
            errors.append(f"{field}_must_be_zero")
    for field in ("proof_credit_allowed", "live_capital_enabled", "paper_growth_trial_calendar_advanced", "simulated_elapsed_time_allowed"):
        if payload.get(field) is not False:
            errors.append(f"{field}_must_be_false")
    gates = payload.get("gates")
    if not isinstance(gates, list) or not gates:
        errors.append("gates_missing")
    blocker_count = _int(payload.get("blocker_count"), 0)
    failed_gate_count = _int(payload.get("failed_gate_count"), 0)
    if blocker_count != failed_gate_count:
        errors.append("blocker_count_mismatch")
    if payload.get("certified") is True and blocker_count:
        errors.append("certified_with_blockers")
    if payload.get("certified") is False and blocker_count == 0:
        errors.append("uncertified_without_blockers")
    return sorted(set(errors))


def main() -> int:
    settings = Settings.from_env()
    payload = build_certification(settings)
    artifact_path = write_certification(payload, settings)
    validation_errors = validate_certification(payload)
    if not artifact_path.exists():
        validation_errors.append("certification_artifact_missing_after_write")
    print(f"artifact={artifact_path}")
    print(f"status={payload.get('status')}")
    print(f"certified={payload.get('certified')}")
    print(f"gate_count={payload.get('gate_count')}")
    print(f"passed_gate_count={payload.get('passed_gate_count')}")
    print(f"failed_gate_count={payload.get('failed_gate_count')}")
    print(f"blocker_count={payload.get('blocker_count')}")
    print(f"live_capital_enabled={payload.get('live_capital_enabled')}")
    print(f"broker_write_count={payload.get('broker_write_count')}")
    print(f"proof_credit_allowed={payload.get('proof_credit_allowed')}")
    for blocker in payload.get("blockers", []):
        print(f"blocker={blocker['gate_id']}:{blocker['blocker']}:{blocker['reason']}")
    for error in validation_errors:
        print(f"error={error}")
    if validation_errors or payload.get("certified") is not True:
        print("qadam_next_generation_flow_check=blocked")
        return 1
    print("qadam_next_generation_flow_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
