"""PT-3 guarded qualified setup production path.

PT-3 reads the current paper-run evidence stack and classifies whether a setup
is production-qualified for the PaperOps path. It records the handoff contract
only; it does not mutate the Q7 ledger, auto-approve, stage, submit, call a
broker, grant proof credit, or force a trade.
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
from orchestrator.qadam_router_v3_paperops import (
    ABSOLUTE_PAPER_TRADE_CEILING_USD,
    read_consumed_v3_handoffs_for_paperops,
)
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT


PAPEROPS_QUALIFIED_SETUP_SCHEMA_VERSION = 1
PAPEROPS_QUALIFIED_SETUP_RUNTIME_ARTIFACT = "paperops_qualified_setup_production.json"
PAPEROPS_QUALIFIED_SETUP_HISTORY = "paperops_qualified_setup_production_history.jsonl"
PAPEROPS_QUALIFIED_SETUP_EVENT_LOG = "paperops_qualified_setup_production_events.jsonl"
PAPEROPS_QUALIFIED_SETUP_EVENT_TYPE = "paperops_qualified_setup_production_recorded"
PAPEROPS_QUALIFIED_SETUP_COMPONENT = "paperops_qualified_setup_production"

PAPEROPS_QUALIFIED_SETUP_BOUNDARY = (
    "PT-3 records the guarded qualified setup production path for PaperOps. It "
    "can classify current evidence as production-qualified only when canonical "
    "source posture, Signal Integrity, Risk Agent paper sizing, kill switches, "
    "execution adapter read readiness, venue read availability, order-field "
    "integrity, and paper-only safety gates pass. It cannot mutate the Q7 "
    "ledger, cannot auto-approve trades, cannot stage or submit paper orders, "
    "cannot call brokers, cannot call live endpoints, cannot consult Q-CTRL "
    "for execution, cannot grant Phase 7 proof credit, cannot force trades, "
    "and cannot enable live capital."
)

PAPEROPS_QUALIFIED_SETUP_PUBLIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "artifact_type",
    "artifact_id",
    "phase",
    "stage",
    "status",
    "generated_at",
    "public_safe",
    "mode",
    "paper_operational_mode_status",
    "paper_operational_mode_effective",
    "paper_operational_flag_disabled",
    "phase7_run_state",
    "phase7_active_day_number",
    "phase7_demo_qualified_setup_count",
    "phase7_demo_qualified_setup_count_scope",
    "production_candidate_count",
    "qualified_setup_count",
    "blocked_candidate_count",
    "ready_to_stage_q7_order",
    "qualified_setup_production_path_ready",
    "no_trade_rationale",
    "qctrl_consultation_required_for_full_parity",
    "qctrl_paper_consultation_status",
    "qctrl_paper_consultation_connected",
    "qctrl_product_access_status",
    "qctrl_product_access_verified",
    "qctrl_product_access_blocker",
    "qctrl_consultation_blocker",
    "paper_size_eligible_count",
    "staged_order_count",
    "source_qualified_setup_ledger_status",
    "source_qualified_setup_ledger_count",
    "source_qualified_setup_ledger_count_scope",
    "source_posture_canonical_source_count",
    "source_quorum_bypass_allowed",
    "supplemental_source_bypass_allowed",
    "yahoo_finance_role",
    "preference_mcp_role",
    "production_gate_pass_count",
    "production_gate_required_count",
    "production_gate_records",
    "candidate_setup_records",
    "router_v3_handoff_enforced",
    "router_v3_handoff_consumer_status",
    "router_v3_accepted_handoff_count",
    "router_v3_handoff_validation_error_count",
    "execution_allowed",
    "paper_order_allowed",
    "paper_order_staging_allowed",
    "paper_order_submission_allowed",
    "broker_post_allowed",
    "alpaca_post_allowed",
    "live_endpoint_allowed",
    "live_capital_enabled",
    "qctrl_direct_execution_allowed",
    "qctrl_broker_post_allowed",
    "phase7_proof_credit_allowed",
    "forced_trades_allowed",
    "manual_trade_level_override_allowed",
    "qualified_setup_creation_forced",
    "broker_post_called_count",
    "alpaca_post_called_count",
    "live_endpoint_called_count",
    "qctrl_provider_call_count",
    "qctrl_broker_post_called_count",
    "qctrl_live_endpoint_called_count",
    "phase7_proof_credit_granted_count",
    "forced_trade_count",
    "unsafe_write_counter_total",
    "next_required_action",
    "boundary",
)

REQUIRED_PRODUCTION_GATES: tuple[tuple[str, str], ...] = (
    ("paper_operational_mode_effective", "PT-2 PaperOps runtime mode is effective."),
    ("phase7_run_active", "The actual Phase 7 paper-operation run is active."),
    ("canonical_source_posture", "Canonical replayable source posture is present."),
    (
        "supplemental_sources_context_only",
        "Yahoo Finance and Preference/PREF MCP remain supplemental only.",
    ),
    ("signal_integrity_passed", "Signal Integrity has passed to risk shadow."),
    ("risk_agent_paper_sizing", "Risk Agent marks the setup paper-size eligible."),
    ("kill_switches_clear", "Kill switches are clear for the setup scope."),
    (
        "execution_adapter_read_ready",
        "Execution adapter is read-ready and write authority remains blocked.",
    ),
    ("venue_read_available", "The selected paper venue is readable."),
    (
        "paper_order_staged_not_submitted",
        "A paper order is staged for dry-run only and not submitted.",
    ),
    ("notional_within_paperops_cap", "Notional remains within the PaperOps cap."),
    ("broker_write_blocked", "Broker write and live endpoint authority remain false."),
    (
        "phase7_safety_boundaries",
        "No forced trades, proof credit, manual override, or live capital are enabled.",
    ),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _hash_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _records(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def paperops_qualified_setup_production_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PAPEROPS_QUALIFIED_SETUP_RUNTIME_ARTIFACT,
        runtime / PAPEROPS_QUALIFIED_SETUP_HISTORY,
        runtime / PAPEROPS_QUALIFIED_SETUP_EVENT_LOG,
    )


def read_latest_paperops_qualified_setup_production(
    settings: Settings | None = None,
) -> dict[str, Any]:
    output_path, _, _ = paperops_qualified_setup_production_paths(settings)
    return _read_json(output_path)


def _source_snapshot(settings: Settings) -> dict[str, dict[str, Any]]:
    runtime = _runtime_dir(settings)
    return {
        "paper_operational_mode": _read_json(runtime / "paper_operational_mode.json"),
        "paper_live_qctrl_product_access": _read_json(
            runtime / "paper_live_qctrl_product_access.json"
        ),
        "paperops_qctrl_consultation": _read_json(
            runtime / "paperops_qctrl_paper_consultation.json"
        ),
        "demo_run": _read_json(runtime / "phase7_demo_proof_run.json"),
        "q7_ledger": _read_json(runtime / "phase7_qualified_setup_ledger.json"),
        "risk_sizing": _read_json(runtime / "phase5_risk_sizing_reviews.json"),
        "paper_staging": _read_json(runtime / "phase5_paper_order_staging_gate.json"),
    }


def _gate_record(key: str, passed: bool, detail: str) -> dict[str, Any]:
    return {
        "gate_key": key,
        "passed": passed,
        "status": "passed" if passed else "blocked",
        "detail": detail,
    }


def _gate_pass(gates: list[dict[str, Any]], key: str) -> bool:
    return any(gate.get("gate_key") == key and gate.get("passed") is True for gate in gates)


def _match_by_strategy(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for record in records:
        strategy = str(record.get("strategy_family_key") or "")
        if strategy:
            output[strategy] = record
    return output


def _source_posture(record: dict[str, Any]) -> dict[str, Any]:
    posture = record.get("source_posture")
    return posture if isinstance(posture, dict) else {}


def _signal_evidence(record: dict[str, Any]) -> dict[str, Any]:
    evidence = record.get("signal_evidence")
    return evidence if isinstance(evidence, dict) else {}


def _source_summary(record: dict[str, Any]) -> dict[str, Any]:
    summary = record.get("source_summary")
    return summary if isinstance(summary, dict) else {}


def _lineage_material(
    *,
    strategy: str,
    staging_record: dict[str, Any],
    risk_record: dict[str, Any],
    signal: dict[str, Any],
) -> dict[str, Any]:
    source_signal_id = str(signal.get("latest_review_source_signal_id") or "").strip()
    review_id = str(signal.get("latest_review_id") or "").strip()
    if source_signal_id:
        identity = {"latest_review_source_signal_id": source_signal_id}
    elif review_id:
        identity = {"latest_review_id": review_id}
    else:
        identity = {
            "source_staging_artifact_id": staging_record.get("artifact_id"),
            "source_risk_sizing_artifact_id": risk_record.get("artifact_id"),
        }
    return {
        "strategy_family_key": strategy,
        **identity,
        "latest_review_status": signal.get("latest_review_status"),
        "latest_market_confirmation_status": signal.get("latest_market_confirmation_status"),
        "latest_market_confirmation_pricing_gap_status": signal.get(
            "latest_market_confirmation_pricing_gap_status"
        ),
    }


def _candidate_record(
    *,
    settings: Settings,
    staging_record: dict[str, Any],
    risk_record: dict[str, Any],
    paper_mode: dict[str, Any],
    demo_run: dict[str, Any],
) -> dict[str, Any]:
    strategy = str(staging_record.get("strategy_family_key") or "unknown")
    posture = _source_posture(staging_record) or _source_posture(risk_record)
    source_summary = _source_summary(staging_record) or _source_summary(risk_record)
    signal = _signal_evidence(risk_record)
    lineage_material = _lineage_material(
        strategy=strategy,
        staging_record=staging_record,
        risk_record=risk_record,
        signal=signal,
    )
    lineage_token = _hash_payload(lineage_material)[:16]
    research_goal_id = f"paperops-research-goal:{strategy}:{lineage_token}"
    candidate_identity = f"paperops-candidate:{strategy}:{lineage_token}"
    checks = _records(staging_record, "checks")
    check_pass = {str(check.get("name")): check.get("passed") is True for check in checks}
    paper_mode_effective = (
        paper_mode.get("status") == "enabled_pending_downstream_gates"
        and paper_mode.get("paper_operational_mode_effective") is True
        and paper_mode.get("paper_operational_flag_disabled") is False
    )
    canonical_source_count = _int(posture.get("canonical_source_count"))
    decision_source_coverage_complete = (
        source_summary.get("canonical_source_count") == EXPECTED_SOURCE_COUNT
        and source_summary.get("all_canonical_sources_considered") is True
        and source_summary.get("decision_source_usage_complete") is True
        and source_summary.get("source_quorum_bypass_allowed") is False
    )
    source_quorum_bypass = posture.get("source_quorum_bypass_allowed") is True
    supplemental_bypass = posture.get("supplemental_source_bypass_allowed") is True
    yahoo_role = str(posture.get("yahoo_finance_role") or "missing")
    preference_role = str(posture.get("preference_mcp_role") or "missing")
    broker_blocked = all(
        staging_record.get(key) is False
        for key in (
            "broker_write_allowed",
            "broker_post_called",
            "live_endpoint_allowed",
            "paper_order_submission_allowed",
            "paper_order_submitted",
        )
    )
    safety_boundaries = all(
        value is False
        for value in (
            settings.live_capital_enabled,
            staging_record.get("live_capital_enabled") is True,
            staging_record.get("trade_candidate_creation_allowed") is True,
            staging_record.get("paper_order_submission_allowed") is True,
            staging_record.get("broker_write_allowed") is True,
            staging_record.get("live_endpoint_allowed") is True,
            staging_record.get("broker_post_called") is True,
        )
    )

    gates = [
        _gate_record(
            "paper_operational_mode_effective",
            paper_mode_effective,
            str(paper_mode.get("status") or "missing"),
        ),
        _gate_record(
            "phase7_run_active",
            demo_run.get("run_state") == "active" and demo_run.get("actual_calendar_run") is True,
            (
                f"state={demo_run.get('run_state', 'missing')}; "
                f"day={demo_run.get('paper_operation_day_number') or demo_run.get('active_day_number')}"
            ),
        ),
        _gate_record(
            "canonical_source_posture",
            canonical_source_count == EXPECTED_SOURCE_COUNT
            and not source_quorum_bypass
            and decision_source_coverage_complete,
            (
                f"canonical_sources={canonical_source_count}; "
                f"source_quorum_bypass={source_quorum_bypass}; "
                f"decision_source_coverage={decision_source_coverage_complete}"
            ),
        ),
        _gate_record(
            "supplemental_sources_context_only",
            not supplemental_bypass
            and yahoo_role == "supplemental_market_confirmation_only"
            and preference_role == "supplemental_multi_source_data_plane",
            f"yahoo={yahoo_role}; preference={preference_role}",
        ),
        _gate_record(
            "signal_integrity_passed",
            signal.get("signal_integrity_passed") is True
            and signal.get("latest_review_status") == "passed_to_risk_shadow"
            and _int(signal.get("latest_source_count")) > 0,
            (
                f"status={signal.get('latest_review_status', 'missing')}; "
                f"sources={_int(signal.get('latest_source_count'))}"
            ),
        ),
        _gate_record(
            "risk_agent_paper_sizing",
            risk_record.get("paper_size_eligible") is True
            and risk_record.get("risk_decision") == "paper_size_eligible"
            and _float(risk_record.get("proposed_risk_gbp")) > 0.0,
            (
                f"decision={risk_record.get('risk_decision', 'missing')}; "
                f"risk_gbp={_float(risk_record.get('proposed_risk_gbp')):.2f}"
            ),
        ),
        _gate_record(
            "kill_switches_clear",
            staging_record.get("kill_switch_clear") is True
            and _int(staging_record.get("kill_switch_validation_error_count")) == 0,
            (
                f"clear={staging_record.get('kill_switch_clear')}; "
                f"errors={_int(staging_record.get('kill_switch_validation_error_count'))}"
            ),
        ),
        _gate_record(
            "execution_adapter_read_ready",
            staging_record.get("execution_adapter_read_health") == "read_only_available"
            and staging_record.get("execution_adapter_write_authority") is False
            and staging_record.get("execution_adapter_write_health")
            == "blocked_q5_5_status_contract",
            (
                f"read={staging_record.get('execution_adapter_read_health', 'missing')}; "
                f"write={staging_record.get('execution_adapter_write_health', 'missing')}"
            ),
        ),
        _gate_record(
            "venue_read_available",
            staging_record.get("selected_venue") == "alpaca_paper"
            and check_pass.get("venue_read_ready") is True
            and check_pass.get("venue_write_blocked") is True,
            f"venue={staging_record.get('selected_venue', 'missing')}",
        ),
        _gate_record(
            "paper_order_staged_not_submitted",
            staging_record.get("status") == "staged"
            and staging_record.get("staging_allowed") is True
            and staging_record.get("order_state") == "staged_ready_for_dry_run"
            and staging_record.get("submission_allowed") is False
            and staging_record.get("paper_order_submitted") is False
            and bool(staging_record.get("idempotency_key")),
            (
                f"status={staging_record.get('status', 'missing')}; "
                f"state={staging_record.get('order_state', 'missing')}"
            ),
        ),
        _gate_record(
            "notional_within_paperops_cap",
            0.0
            < _float(staging_record.get("notional_gbp"))
            <= float(settings.paper_operational_max_notional_gbp),
            (
                f"notional_gbp={_float(staging_record.get('notional_gbp')):.2f}; "
                f"cap_gbp={settings.paper_operational_max_notional_gbp}"
            ),
        ),
        _gate_record(
            "broker_write_blocked",
            broker_blocked,
            "broker/live write authority remains false",
        ),
        _gate_record(
            "phase7_safety_boundaries",
            safety_boundaries,
            "forced trades, proof credit, manual override, and live capital remain blocked",
        ),
    ]
    required_keys = {key for key, _ in REQUIRED_PRODUCTION_GATES}
    passed = all(_gate_pass(gates, key) for key in required_keys)
    rejection_reasons = [gate["gate_key"] for gate in gates if gate.get("passed") is not True]
    return {
        "setup_record_id": f"paperops:pt-3:qualified-setup:{strategy}:{lineage_token}",
        "source_phase": "Q5",
        "source_artifact_id": staging_record.get("artifact_id"),
        "source_risk_sizing_artifact_id": staging_record.get("source_risk_sizing_artifact_id")
        or risk_record.get("artifact_id"),
        "source_signal_id": signal.get("latest_review_source_signal_id"),
        "source_signal_review_id": signal.get("latest_review_id"),
        "source_signal_reviewed_at": signal.get("latest_reviewed_at"),
        "source_signal_status": signal.get("latest_review_status"),
        "signal_evidence_lineage_key": f"paperops-signal-lineage:{lineage_token}",
        "setup_freshness_key": f"paperops-fresh:{strategy}:{lineage_token}",
        "research_goal_id": research_goal_id,
        "research_goal_lineage": {
            "strategy_family_key": strategy,
            "lineage_token": lineage_token,
            "source_signal_id": signal.get("latest_review_source_signal_id"),
            "source_signal_review_id": signal.get("latest_review_id"),
            "source_signal_reviewed_at": signal.get("latest_reviewed_at"),
            "source_signal_status": signal.get("latest_review_status"),
            "lineage_material": lineage_material,
        },
        "candidate_identity": candidate_identity,
        "strategy_family_key": strategy,
        "instrument": staging_record.get("instrument"),
        "selected_venue": staging_record.get("selected_venue"),
        "side": staging_record.get("side"),
        "quantity": _float(staging_record.get("quantity")),
        "order_type": staging_record.get("order_type"),
        "time_in_force": staging_record.get("time_in_force"),
        "notional_gbp": _float(staging_record.get("notional_gbp")),
        "risk_gbp": _float(staging_record.get("risk_size_gbp"))
        or _float(risk_record.get("proposed_risk_gbp")),
        "all_required_gates_passed": passed,
        "eligible_setup": passed,
        "qualified_setup": passed,
        "setup_state": "production_qualified" if passed else "blocked",
        "decision_state": (
            "qualified_for_q7_production_handoff" if passed else "blocked_pending_required_gate"
        ),
        "rejection_reasons": rejection_reasons,
        "gate_results": gates,
        "canonical_source_quorum_passed": _gate_pass(gates, "canonical_source_posture"),
        "source_quorum_passed": _gate_pass(gates, "canonical_source_posture"),
        "decision_source_coverage_complete": decision_source_coverage_complete,
        "decision_source_coverage": source_summary.get("decision_source_coverage", {}),
        "signal_integrity_passed": _gate_pass(gates, "signal_integrity_passed"),
        "risk_paper_sizing_passed": _gate_pass(gates, "risk_agent_paper_sizing"),
        "kill_switches_clear": _gate_pass(gates, "kill_switches_clear"),
        "supplemental_only": False,
        "phase5_lifecycle_counts_as_q7_proof": False,
        "phase5_test_trade_counted_for_phase7": False,
        "proof_trade_created": False,
        "proof_credit_allowed": False,
        "paper_order_submission_allowed": False,
        "broker_post_allowed": False,
        "broker_post_called": False,
        "live_capital_enabled": False,
    }


def _v3_candidate_record(
    *,
    accepted_record: dict[str, Any],
    paper_mode: dict[str, Any],
    demo_run: dict[str, Any],
) -> dict[str, Any]:
    handoff = accepted_record.get("source_handoff")
    handoff = handoff if isinstance(handoff, dict) else {}
    lineage = handoff.get("lineage")
    lineage = lineage if isinstance(lineage, dict) else {}
    source_quorum = handoff.get("source_quorum")
    source_quorum = source_quorum if isinstance(source_quorum, dict) else {}
    direction = str(handoff.get("direction") or "").lower()
    side = (
        "buy" if direction in {"buy", "long"} else "sell" if direction in {"sell", "short"} else ""
    )
    quantity = _float(handoff.get("proposed_quantity"))
    notional_usd = _float(handoff.get("proposed_notional_usd"))
    risk_usd = _float(handoff.get("maximum_loss_at_invalidation"))
    receipt_id = accepted_record.get("consumption_receipt_id")
    paper_mode_effective = (
        paper_mode.get("status") == "enabled_pending_downstream_gates"
        and paper_mode.get("paper_operational_mode_effective") is True
        and paper_mode.get("paper_operational_flag_disabled") is False
    )
    calendar_run_active = (
        demo_run.get("run_state") == "active" and demo_run.get("actual_calendar_run") is True
    )
    lineage_complete = all(
        lineage.get(field)
        for field in (
            "research_goal_id",
            "score_id",
            "edge_id",
            "hypothesis_id",
            "akber_result_id",
            "shadow_evidence_id",
            "risk_proposal_id",
        )
    )
    source_quorum_passed = (
        handoff.get("source_quorum_passed") is True
        and source_quorum.get("passed") is True
        and handoff.get("supplemental_source_bypass_allowed") is False
    )
    risk_passed = (
        quantity > 0 and 0 < notional_usd <= ABSOLUTE_PAPER_TRADE_CEILING_USD and risk_usd > 0
    )
    safety_clear = (
        handoff.get("duplicate_exposure_conflict") is False
        and handoff.get("drawdown_context_complete") is True
        and handoff.get("drawdown_breached") is False
        and handoff.get("qctrl_state") == "pass"
    )
    guarded_route = (
        handoff.get("route") == "guarded_alpaca_paper_via_paperops"
        and handoff.get("instrument_paperable") is True
        and handoff.get("market_family") != "prediction_market"
    )
    handoff_is_not_order = (
        handoff.get("paperops_handoff_is_not_order") is True
        and handoff.get("paperops_direct_call_allowed") is False
        and handoff.get("paper_order_created") is False
        and _int(handoff.get("broker_write_count")) == 0
        and handoff.get("live_capital_enabled") is False
        and handoff.get("proof_credit_allowed") is False
    )
    gates = [
        _gate_record(
            "paper_operational_mode_effective",
            paper_mode_effective,
            str(paper_mode.get("status") or "missing"),
        ),
        _gate_record(
            "phase7_run_active",
            calendar_run_active,
            f"state={demo_run.get('run_state', 'missing')}; actual_calendar={demo_run.get('actual_calendar_run')}",
        ),
        _gate_record(
            "canonical_source_posture",
            source_quorum_passed,
            f"source_quorum_passed={source_quorum_passed}; independent_sources={_int(source_quorum.get('independent_source_count'))}",
        ),
        _gate_record(
            "supplemental_sources_context_only",
            handoff.get("supplemental_source_bypass_allowed") is False,
            "supplemental sources cannot bypass V3 source quorum",
        ),
        _gate_record(
            "signal_integrity_passed", lineage_complete, f"complete_v3_lineage={lineage_complete}"
        ),
        _gate_record(
            "risk_agent_paper_sizing",
            risk_passed,
            f"notional_usd={notional_usd:.2f}; max_loss_usd={risk_usd:.2f}",
        ),
        _gate_record(
            "kill_switches_clear",
            safety_clear,
            f"duplicate={handoff.get('duplicate_exposure_conflict')}; drawdown={handoff.get('drawdown_breached')}; qctrl={handoff.get('qctrl_state')}",
        ),
        _gate_record(
            "execution_adapter_read_ready",
            guarded_route and bool(receipt_id),
            f"route={handoff.get('route')}; receipt={receipt_id}",
        ),
        _gate_record("venue_read_available", guarded_route, "guarded Alpaca Paper route selected"),
        _gate_record(
            "paper_order_staged_not_submitted",
            handoff_is_not_order,
            "V3 handoff consumed before PT-4 staging; no order exists",
        ),
        _gate_record(
            "notional_within_paperops_cap",
            risk_passed,
            f"notional_usd={notional_usd:.2f}; cap_usd={ABSOLUTE_PAPER_TRADE_CEILING_USD:.2f}",
        ),
        _gate_record(
            "broker_write_blocked", handoff_is_not_order, "handoff created no broker write"
        ),
        _gate_record(
            "phase7_safety_boundaries",
            handoff_is_not_order,
            "paper-only, no live capital, no proof credit",
        ),
    ]
    required_keys = {key for key, _ in REQUIRED_PRODUCTION_GATES}
    passed = all(_gate_pass(gates, key) for key in required_keys)
    rejection_reasons = [gate["gate_key"] for gate in gates if gate.get("passed") is not True]
    strategy = str(handoff.get("strategy_family_id") or "v3_edge_strategy")
    return {
        "setup_record_id": f"paperops:pt-3:v3:{handoff.get('setup_id')}",
        "source_phase": "OR-15",
        "source_artifact_id": handoff.get("paperops_handoff_id"),
        "source_risk_sizing_artifact_id": lineage.get("risk_proposal_id"),
        "source_signal_id": lineage.get("score_id"),
        "source_signal_review_id": lineage.get("akber_result_id"),
        "source_signal_reviewed_at": handoff.get("generated_at"),
        "source_signal_status": "router_v3_paper_review_candidate",
        "signal_evidence_lineage_key": lineage.get("edge_id"),
        "setup_freshness_key": handoff.get("paperops_handoff_id"),
        "research_goal_id": lineage.get("research_goal_id"),
        "research_goal_lineage": lineage,
        "candidate_identity": handoff.get("candidate_identity_id"),
        "strategy_family_key": strategy,
        "instrument": handoff.get("instrument"),
        "selected_venue": "alpaca_paper",
        "side": side,
        "quantity": quantity,
        "order_type": "market",
        "time_in_force": "day",
        "notional_usd": notional_usd,
        "notional_currency": "USD",
        "risk_usd": risk_usd,
        "notional_gbp": 0.0,
        "risk_gbp": 0.0,
        "paperops_handoff_id": handoff.get("paperops_handoff_id"),
        "router_decision_id": handoff.get("router_decision_id"),
        "v3_consumption_receipt_id": receipt_id,
        "source_router_idempotency_key": handoff.get("idempotency_material", {}).get(
            "idempotency_key"
        ),
        "complete_v3_lineage": lineage,
        "all_required_gates_passed": passed,
        "eligible_setup": passed,
        "qualified_setup": passed,
        "setup_state": "production_qualified" if passed else "blocked",
        "decision_state": "qualified_for_q7_production_handoff"
        if passed
        else "blocked_pending_required_gate",
        "rejection_reasons": rejection_reasons,
        "gate_results": gates,
        "canonical_source_quorum_passed": source_quorum_passed,
        "source_quorum_passed": source_quorum_passed,
        "decision_source_coverage_complete": source_quorum_passed,
        "decision_source_coverage": source_quorum,
        "signal_integrity_passed": lineage_complete,
        "risk_paper_sizing_passed": risk_passed,
        "kill_switches_clear": safety_clear,
        "supplemental_only": False,
        "phase5_lifecycle_counts_as_q7_proof": False,
        "phase5_test_trade_counted_for_phase7": False,
        "proof_trade_created": False,
        "proof_credit_allowed": False,
        "paper_order_submission_allowed": False,
        "broker_post_allowed": False,
        "broker_post_called": False,
        "live_capital_enabled": False,
    }


def _candidate_records(
    *,
    settings: Settings,
    snapshot: dict[str, dict[str, Any]],
    v3_consumer_state: dict[str, Any],
    v3_accepted_handoffs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if v3_consumer_state.get("enforcement_active") is True:
        return [
            _v3_candidate_record(
                accepted_record=record,
                paper_mode=snapshot["paper_operational_mode"],
                demo_run=snapshot["demo_run"],
            )
            for record in v3_accepted_handoffs
        ]
    risk_by_strategy = _match_by_strategy(_records(snapshot["risk_sizing"], "reviews"))
    records: list[dict[str, Any]] = []
    for staging_record in _records(snapshot["paper_staging"], "records"):
        strategy = str(staging_record.get("strategy_family_key") or "")
        if not strategy:
            continue
        risk_record = risk_by_strategy.get(strategy, {})
        records.append(
            _candidate_record(
                settings=settings,
                staging_record=staging_record,
                risk_record=risk_record,
                paper_mode=snapshot["paper_operational_mode"],
                demo_run=snapshot["demo_run"],
            )
        )
    return records


def _production_gate_records(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for key, meaning in REQUIRED_PRODUCTION_GATES:
        candidate_gate_records = [
            gate
            for candidate in candidates
            for gate in candidate.get("gate_results", [])
            if gate.get("gate_key") == key
        ]
        passed_count = sum(1 for gate in candidate_gate_records if gate.get("passed"))
        records.append(
            {
                "gate_key": key,
                "meaning": meaning,
                "candidate_count": len(candidate_gate_records),
                "passed_count": passed_count,
                "blocked_count": len(candidate_gate_records) - passed_count,
                "passed_for_any_candidate": passed_count > 0,
            }
        )
    return records


def _qctrl_status(snapshot: dict[str, dict[str, Any]]) -> dict[str, Any]:
    product = snapshot["paper_live_qctrl_product_access"]
    consultation = snapshot["paperops_qctrl_consultation"]
    connected = (
        consultation.get("status") == "consultation_recorded"
        and consultation.get("provider_call_recorded") is True
        and _int(consultation.get("provider_call_count")) > 0
        and consultation.get("execution_allowed") is False
        and consultation.get("broker_post_allowed") is False
    )
    blocker = "none" if connected else "qctrl_paper_consultation_not_connected"
    if product.get("product_access_verified") is not True:
        blocker = str(product.get("product_access_blocker") or "qctrl_product_access_not_verified")
    return {
        "qctrl_consultation_required_for_full_parity": True,
        "qctrl_paper_consultation_status": consultation.get("status", "missing"),
        "qctrl_paper_consultation_connected": connected,
        "qctrl_product_access_status": product.get("status", "missing"),
        "qctrl_product_access_verified": product.get("product_access_verified") is True,
        "qctrl_product_access_blocker": product.get(
            "product_access_blocker",
            "missing",
        ),
        "qctrl_consultation_blocker": blocker,
        "qctrl_provider_call_count": _int(consultation.get("provider_call_count")),
        "qctrl_broker_post_called_count": _int(consultation.get("broker_post_called_count"))
        + _int(product.get("broker_post_called_count")),
        "qctrl_live_endpoint_called_count": _int(consultation.get("live_endpoint_called_count"))
        + _int(product.get("live_endpoint_called_count")),
    }


def build_paperops_qualified_setup_production(
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    snapshot = _source_snapshot(settings)
    v3_consumer_state, v3_accepted_handoffs, v3_handoff_errors = (
        read_consumed_v3_handoffs_for_paperops(settings)
    )
    paper_mode = snapshot["paper_operational_mode"]
    demo_run = snapshot["demo_run"]
    q7_ledger = snapshot["q7_ledger"]
    candidates = _candidate_records(
        settings=settings,
        snapshot=snapshot,
        v3_consumer_state=v3_consumer_state,
        v3_accepted_handoffs=v3_accepted_handoffs,
    )
    qualified = [candidate for candidate in candidates if candidate.get("qualified_setup") is True]
    blocked = [
        candidate for candidate in candidates if candidate.get("qualified_setup") is not True
    ]
    gate_records = _production_gate_records(candidates)
    source_postures = [
        _source_posture(record)
        for record in _records(snapshot["paper_staging"], "records")
        if _source_posture(record)
    ]
    first_posture = source_postures[0] if source_postures else {}
    qctrl = _qctrl_status(snapshot)
    unsafe_total = sum(
        _int(value)
        for value in (
            snapshot["paper_staging"].get("broker_post_called_count"),
            snapshot["paper_staging"].get("live_endpoint_allowed_count"),
            snapshot["risk_sizing"].get("paper_order_submitted_count"),
            qctrl["qctrl_broker_post_called_count"],
            qctrl["qctrl_live_endpoint_called_count"],
        )
    )
    q7_ledger_consumed_count = _int(q7_ledger.get("qualified_setup_count"))
    path_ready = (
        settings.mode == "paper"
        and settings.live_capital_enabled is False
        and not v3_handoff_errors
        and paper_mode.get("status") == "enabled_pending_downstream_gates"
        and paper_mode.get("paper_operational_mode_effective") is True
        and paper_mode.get("paper_operational_flag_disabled") is False
        and demo_run.get("run_state") == "active"
        and unsafe_total == 0
    )
    ready_to_stage = path_ready and bool(qualified)
    if ready_to_stage:
        status = "production_path_ready_with_qualified_setup"
        next_action = (
            "Continue the Q7 guarded proof lifecycle and closeout path; the "
            "PaperOps qualified setup has been consumed by the Q7 setup ledger."
            if q7_ledger_consumed_count
            else (
                "Consume the qualified setup through the Q7 setup ledger, "
                "auto-approval, and guarded proof-order staging path; do not "
                "submit until the explicit Alpaca paper gate allows it."
            )
        )
        no_trade_rationale = None
    elif path_ready:
        status = "production_path_ready_no_current_qualified_setup"
        next_action = (
            "Keep the indefinite paper operation running and wait for a candidate where all "
            "PT-3 production gates pass."
        )
        no_trade_rationale = "no_current_pt3_qualified_setup_detected"
    else:
        status = "blocked_pending_paperops_prerequisite"
        next_action = "Restore PaperOps prerequisites before producing qualified setups."
        no_trade_rationale = "paperops_prerequisite_not_ready"

    artifact = {
        "schema_version": PAPEROPS_QUALIFIED_SETUP_SCHEMA_VERSION,
        "artifact_type": "paperops_qualified_setup_production",
        "artifact_id": "paperops:pt-3:qualified-setup-production-path",
        "phase": "PaperOps",
        "stage": "PT-3",
        "status": status,
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
        "mode": settings.mode,
        "paper_operational_mode_status": paper_mode.get("status", "missing"),
        "paper_operational_mode_effective": (
            paper_mode.get("paper_operational_mode_effective") is True
        ),
        "paper_operational_flag_disabled": (
            paper_mode.get("paper_operational_flag_disabled") is True
        ),
        "phase7_run_state": demo_run.get("run_state", "missing"),
        "phase7_active_day_number": demo_run.get("active_day_number"),
        "phase7_demo_qualified_setup_count": _int(demo_run.get("qualified_setup_count")),
        "phase7_demo_qualified_setup_count_scope": "cumulative_demo_run",
        "production_candidate_count": len(candidates),
        "qualified_setup_count": len(qualified),
        "blocked_candidate_count": len(blocked),
        "ready_to_stage_q7_order": ready_to_stage,
        "qualified_setup_production_path_ready": path_ready,
        "no_trade_rationale": no_trade_rationale,
        **qctrl,
        "paper_size_eligible_count": _int(snapshot["risk_sizing"].get("paper_size_eligible_count")),
        "staged_order_count": _int(snapshot["paper_staging"].get("staged_order_count")),
        "source_qualified_setup_ledger_status": q7_ledger.get("status", "missing"),
        "source_qualified_setup_ledger_count": q7_ledger_consumed_count,
        "source_qualified_setup_ledger_count_scope": "cumulative_runtime_ledger",
        "source_posture_canonical_source_count": _int(first_posture.get("canonical_source_count")),
        "source_quorum_bypass_allowed": (first_posture.get("source_quorum_bypass_allowed") is True),
        "supplemental_source_bypass_allowed": (
            first_posture.get("supplemental_source_bypass_allowed") is True
        ),
        "yahoo_finance_role": first_posture.get("yahoo_finance_role", "missing"),
        "preference_mcp_role": first_posture.get("preference_mcp_role", "missing"),
        "production_gate_pass_count": sum(
            1 for record in gate_records if record.get("passed_for_any_candidate")
        ),
        "production_gate_required_count": len(REQUIRED_PRODUCTION_GATES),
        "production_gate_records": gate_records,
        "candidate_setup_records": candidates,
        "router_v3_handoff_enforced": (v3_consumer_state.get("enforcement_active") is True),
        "router_v3_handoff_consumer_status": v3_consumer_state.get(
            "status",
            "missing",
        ),
        "router_v3_accepted_handoff_count": len(v3_accepted_handoffs),
        "router_v3_handoff_validation_error_count": len(v3_handoff_errors),
        "execution_allowed": False,
        "paper_order_allowed": False,
        "paper_order_staging_allowed": False,
        "paper_order_submission_allowed": False,
        "broker_post_allowed": False,
        "alpaca_post_allowed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": settings.live_capital_enabled,
        "qctrl_direct_execution_allowed": False,
        "qctrl_broker_post_allowed": False,
        "phase7_proof_credit_allowed": False,
        "forced_trades_allowed": False,
        "manual_trade_level_override_allowed": False,
        "qualified_setup_creation_forced": False,
        "broker_post_called_count": _int(snapshot["paper_staging"].get("broker_post_called_count")),
        "alpaca_post_called_count": 0,
        "live_endpoint_called_count": _int(
            snapshot["paper_staging"].get("live_endpoint_allowed_count")
        ),
        "phase7_proof_credit_granted_count": 0,
        "forced_trade_count": 0,
        "unsafe_write_counter_total": unsafe_total,
        "next_required_action": next_action,
        "boundary": PAPEROPS_QUALIFIED_SETUP_BOUNDARY,
    }
    artifact["validation_errors"] = validate_paperops_qualified_setup_production(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "invalid"
    artifact["public_status"] = paperops_qualified_setup_production_public_status_from_artifact(
        artifact
    )
    return artifact


def validate_paperops_qualified_setup_production(
    artifact: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    required = set(PAPEROPS_QUALIFIED_SETUP_PUBLIC_FIELDS) | {
        "recorded",
        "event_log_required",
        "event_log_written",
        "event_log_correlation_id",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("paperops_qualified_setup_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PAPEROPS_QUALIFIED_SETUP_SCHEMA_VERSION:
        errors.append("paperops_qualified_setup_schema_mismatch")
    if artifact.get("artifact_type") != "paperops_qualified_setup_production":
        errors.append("paperops_qualified_setup_type_mismatch")
    if artifact.get("phase") != "PaperOps" or artifact.get("stage") != "PT-3":
        errors.append("paperops_qualified_setup_phase_stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("paperops_qualified_setup_not_public_safe")
    if artifact.get("mode") != "paper":
        errors.append("paperops_qualified_setup_mode_not_paper")
    if artifact.get("live_capital_enabled") is not False:
        errors.append("paperops_qualified_setup_live_capital_enabled")
    if artifact.get("paper_operational_mode_effective") is not True:
        errors.append("paperops_qualified_setup_paper_mode_not_effective")
    if artifact.get("paper_operational_flag_disabled") is not False:
        errors.append("paperops_qualified_setup_paper_mode_disabled")
    if artifact.get("phase7_run_state") != "active":
        errors.append("paperops_qualified_setup_phase7_run_not_active")
    if artifact.get("router_v3_handoff_enforced") is True:
        if _int(artifact.get("router_v3_handoff_validation_error_count")) != 0:
            errors.append("paperops_qualified_setup_v3_handoff_validation_failed")
        for record in artifact.get("candidate_setup_records", []):
            if isinstance(record, dict) and record.get("source_phase") != "OR-15":
                errors.append("paperops_qualified_setup_legacy_candidate_under_v3_enforcement")
    if artifact.get("qualified_setup_count", 0) > artifact.get(
        "production_candidate_count",
        0,
    ):
        errors.append("paperops_qualified_setup_count_exceeds_candidates")
    if (
        artifact.get("ready_to_stage_q7_order") is True
        and _int(artifact.get("qualified_setup_count")) == 0
    ):
        errors.append("paperops_qualified_setup_ready_without_qualified_setup")
    if (
        artifact.get("ready_to_stage_q7_order") is True
        and artifact.get("qualified_setup_production_path_ready") is not True
    ):
        errors.append("paperops_qualified_setup_ready_without_path")
    if _int(artifact.get("qualified_setup_count")):
        qualified_records = [
            record
            for record in artifact.get("candidate_setup_records", [])
            if isinstance(record, dict) and record.get("qualified_setup") is True
        ]
        if len(qualified_records) != _int(artifact.get("qualified_setup_count")):
            errors.append("paperops_qualified_setup_record_count_mismatch")
        for record in qualified_records:
            if record.get("all_required_gates_passed") is not True:
                errors.append("paperops_qualified_setup_gate_false_positive")
            if record.get("decision_source_coverage_complete") is not True:
                errors.append("paperops_qualified_setup_without_decision_source_coverage")
            if record.get("phase5_lifecycle_counts_as_q7_proof") is not False:
                errors.append("paperops_qualified_setup_phase5_lifecycle_reused")
            if record.get("proof_credit_allowed") is not False:
                errors.append("paperops_qualified_setup_record_grants_proof_credit")
    for record in artifact.get("candidate_setup_records", []):
        if not isinstance(record, dict):
            errors.append("paperops_qualified_setup_candidate_record_invalid")
            continue
        if record.get("supplemental_only") is True:
            errors.append("paperops_qualified_setup_supplemental_only_candidate")
        if (
            record.get("source_quorum_passed") is True
            and record.get("decision_source_coverage_complete") is not True
        ):
            errors.append("paperops_qualified_setup_source_quorum_without_decision_coverage")
        if record.get("broker_post_called") is not False:
            errors.append("paperops_qualified_setup_record_broker_post_called")
        if record.get("live_capital_enabled") is not False:
            errors.append("paperops_qualified_setup_record_live_capital_enabled")
    for key in (
        "execution_allowed",
        "paper_order_allowed",
        "paper_order_staging_allowed",
        "paper_order_submission_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "qctrl_direct_execution_allowed",
        "qctrl_broker_post_allowed",
        "phase7_proof_credit_allowed",
        "forced_trades_allowed",
        "manual_trade_level_override_allowed",
        "qualified_setup_creation_forced",
    ):
        if artifact.get(key) is not False:
            errors.append(f"paperops_qualified_setup_forbidden:{key}")
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "live_endpoint_called_count",
        "qctrl_broker_post_called_count",
        "qctrl_live_endpoint_called_count",
        "phase7_proof_credit_granted_count",
        "forced_trade_count",
        "unsafe_write_counter_total",
    ):
        if _int(artifact.get(key)) != 0:
            errors.append(f"paperops_qualified_setup_unsafe_counter_nonzero:{key}")
    if artifact.get("source_quorum_bypass_allowed") is not False:
        errors.append("paperops_qualified_setup_source_quorum_bypass_allowed")
    if artifact.get("supplemental_source_bypass_allowed") is not False:
        errors.append("paperops_qualified_setup_supplemental_bypass_allowed")
    if artifact.get("yahoo_finance_role") != "supplemental_market_confirmation_only":
        errors.append("paperops_qualified_setup_yahoo_not_supplemental")
    if artifact.get("preference_mcp_role") != "supplemental_multi_source_data_plane":
        errors.append("paperops_qualified_setup_preference_not_supplemental")
    if (
        artifact.get("recorded") is True
        and artifact.get("event_log_required") is True
        and artifact.get("event_log_written") is not True
    ):
        errors.append("paperops_qualified_setup_event_log_missing")
    if artifact.get("event_log_written") is True:
        if artifact.get("event_log_event_count") != 1:
            errors.append("paperops_qualified_setup_event_count_mismatch")
        if not artifact.get("event_log_correlation_id"):
            errors.append("paperops_qualified_setup_event_correlation_missing")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "guarded qualified setup production path",
        "cannot mutate the Q7 ledger",
        "cannot auto-approve trades",
        "cannot stage or submit paper orders",
        "cannot call brokers",
        "cannot call live endpoints",
        "cannot consult Q-CTRL for execution",
        "cannot grant Phase 7 proof credit",
        "cannot force trades",
        "cannot enable live capital",
    ):
        if phrase not in boundary:
            errors.append("paperops_qualified_setup_boundary_weak")
            break
    return sorted(set(errors))


def paperops_qualified_setup_production_public_status_from_artifact(
    artifact: dict[str, Any],
) -> dict[str, Any]:
    public_status = {
        field: deepcopy(artifact.get(field))
        for field in PAPEROPS_QUALIFIED_SETUP_PUBLIC_FIELDS
        if field in artifact
    }
    public_status["validation_error_count"] = len(artifact.get("validation_errors", []) or [])
    public_status["recorded"] = artifact.get("recorded") is True
    public_status["event_log_written"] = artifact.get("event_log_written") is True
    public_status["event_log_event_count"] = artifact.get("event_log_event_count", 0)
    return public_status


def paperops_qualified_setup_production_public_status(
    settings: Settings | None = None,
) -> dict[str, Any]:
    artifact = read_latest_paperops_qualified_setup_production(settings)
    if not artifact:
        return {
            "schema_version": PAPEROPS_QUALIFIED_SETUP_SCHEMA_VERSION,
            "artifact_type": "paperops_qualified_setup_production",
            "artifact_id": "paperops:pt-3:qualified-setup-production-path",
            "phase": "PaperOps",
            "stage": "PT-3",
            "status": "not_run",
            "public_safe": True,
            "recorded": False,
            "event_log_written": False,
            "event_log_event_count": 0,
            "mode": "paper",
            "paper_operational_mode_effective": False,
            "paper_operational_flag_disabled": True,
            "phase7_run_state": "missing",
            "production_candidate_count": 0,
            "qualified_setup_count": 0,
            "blocked_candidate_count": 0,
            "ready_to_stage_q7_order": False,
            "qualified_setup_production_path_ready": False,
            "phase7_demo_qualified_setup_count": 0,
            "source_qualified_setup_ledger_count": 0,
            "qctrl_consultation_required_for_full_parity": True,
            "qctrl_paper_consultation_status": "not_run",
            "qctrl_paper_consultation_connected": False,
            "paper_order_submission_allowed": False,
            "live_capital_enabled": False,
            "phase7_proof_credit_allowed": False,
            "forced_trades_allowed": False,
            "qualified_setup_creation_forced": False,
            "broker_post_called_count": 0,
            "alpaca_post_called_count": 0,
            "live_endpoint_called_count": 0,
            "unsafe_write_counter_total": 0,
            "validation_error_count": 0,
            "boundary": PAPEROPS_QUALIFIED_SETUP_BOUNDARY,
        }
    return paperops_qualified_setup_production_public_status_from_artifact(artifact)


def attach_paperops_qualified_setup_production_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(event_log_path or (_runtime_dir(settings) / PAPEROPS_QUALIFIED_SETUP_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PAPEROPS_QUALIFIED_SETUP_EVENT_TYPE,
        PAPEROPS_QUALIFIED_SETUP_COMPONENT,
        {
            "status": output.get("status"),
            "production_candidate_count": output.get("production_candidate_count"),
            "qualified_setup_count": output.get("qualified_setup_count"),
            "blocked_candidate_count": output.get("blocked_candidate_count"),
            "ready_to_stage_q7_order": output.get("ready_to_stage_q7_order"),
            "qctrl_paper_consultation_connected": output.get("qctrl_paper_consultation_connected"),
            "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
        },
    )
    output["recorded"] = True
    output["event_log_written"] = True
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = 1
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_created_at"] = entry.created_at
    output["validation_errors"] = validate_paperops_qualified_setup_production(output)
    if output["validation_errors"]:
        output["status"] = "invalid"
    output["public_status"] = paperops_qualified_setup_production_public_status_from_artifact(
        output
    )
    return output, entry


def write_paperops_qualified_setup_production(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = paperops_qualified_setup_production_paths(
        settings
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_paperops_qualified_setup_production_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_paperops_qualified_setup_production(output)
        output["public_status"] = paperops_qualified_setup_production_public_status_from_artifact(
            output
        )
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_paperops_qualified_setup_production(output)
    if output["validation_errors"]:
        output["status"] = "invalid"
    output["public_status"] = paperops_qualified_setup_production_public_status_from_artifact(
        output
    )
    output_path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_record = {
        "schema_version": PAPEROPS_QUALIFIED_SETUP_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "recorded_at": _now(),
        "production_candidate_count": output.get("production_candidate_count"),
        "qualified_setup_count": output.get("qualified_setup_count"),
        "ready_to_stage_q7_order": output.get("ready_to_stage_q7_order"),
        "qctrl_paper_consultation_connected": output.get("qctrl_paper_consultation_connected"),
        "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
        "validation_error_count": len(output.get("validation_errors", []) or []),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
