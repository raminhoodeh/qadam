"""Qadam operational perfection certification.

This is the canonical yes/no certification for whether Qadam is operationally
complete. It verifies the current runtime and records why Qadam is or is not
complete without forcing trades or weakening any PaperOps boundary.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_self_healing_supervisor import build_and_write_self_healing_state
from orchestrator.qsase_governance_safety_contract import universal_authority_flags

SCHEMA_VERSION = "qadam_operational_perfection.v1"

PRIMARY_ARTIFACT = "qadam_operational_perfection_certification.json"
DASHBOARD_SUMMARY_ARTIFACT = "qadam_operational_perfection_dashboard_summary.json"
HISTORY_ARTIFACT = "qadam_operational_perfection_history.jsonl"
EVENTS_ARTIFACT = "qadam_operational_perfection_events.jsonl"
PHASE_STATUS_ARTIFACT = "qsase_phase_implementation_status.json"

SOURCE_RELIABILITY_ARTIFACT = "qsase_source_reliability.json"
HISTORICAL_MEMORY_ARTIFACT = "qsase_historical_memory_completion.json"
AKBER_INPUT_COMPLETENESS_ARTIFACT = "qsase_akber_input_completeness.json"
VALIDATED_EDGE_ARTIFACT = "qsase_validated_edge_graduation.json"
PATTERN_SEARCH_ARTIFACT = "qsase_full_universe_pattern_search_v2.json"
STRATEGY_FOUNDRY_ARTIFACT = "qsase_strategy_foundry_v2.json"
AKBER_FILTER_ARTIFACT = "qsase_akber_filter_v2.json"
SHADOW_SIMULATOR_ARTIFACT = "qsase_shadow_simulator_v2.json"
ROUTER_ARTIFACT = "qsase_strategy_router_v2.json"
PAPEROPS_HANDOFF_ARTIFACT = "qsase_paperops_handoff_v2.json"
PAPER_LIFECYCLE_ARTIFACT = "qsase_paper_lifecycle_v2.json"
PROOF_LEDGER_ARTIFACT = "qsase_proof_ledger_v2.json"
LEARNING_ATTRIBUTION_ARTIFACT = "qsase_learning_attribution_v2.json"
DASHBOARD_COMPLETION_ARTIFACT = "qsase_dashboard_completion_v2.json"
TELEGRAM_SUMMARY_ARTIFACT = "qsase_telegram_summary_v2.json"
SELF_HEALING_ARTIFACT = "qadam_self_healing_state.json"
GIT_DEPLOY_ARTIFACT = "qadam_git_deploy_readiness.json"
WHY_NOT_ARTIFACT = "qsase_why_not_trading_now_v2.json"
PAPER_POSITIONS_ARTIFACT = "paper_positions.jsonl"

AUTHORITY_FLAGS = {
    "read_only": True,
    "paper_only": True,
    "proposal_first": True,
    "command_disabled": True,
    "certification_only": True,
    "trade_candidate_created": False,
    "qualified_setup_created": False,
    "risk_approval_created": False,
    "execution_approval_created": False,
    "paper_order_allowed": False,
    "paper_order_created": False,
    "paper_order_created_count": 0,
    "broker_write_allowed": False,
    "broker_write_count": 0,
    "telegram_live_send_allowed": False,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
    "proof_credit_allowed": False,
    "paper_proof_ledger_credit_created": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "simulated_elapsed_time_allowed": False,
    "policy_mutation_created": False,
    "strategy_mutation_created": False,
    "live_capital_enabled": False,
}

FALSE_AUTHORITY_FIELDS = {key for key, value in AUTHORITY_FLAGS.items() if value is False}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _runtime_dir(settings: Settings | None = None) -> Path:
    active_settings = settings or Settings.from_env()
    path = Path(active_settings.runtime_dir)
    if not path.is_absolute():
        path = _repo_root() / path
    return path


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _json_dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _jsonl_line(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True) + "\n"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    if limit is not None:
        lines = lines[-limit:]
    rows: list[dict[str, Any]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_dump(payload), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(_jsonl_line(payload))


def _artifact_ref(filename: str) -> str:
    return f"data/runtime/{filename}"


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


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


def _status_ready(payload: dict[str, Any]) -> bool:
    status = str(payload.get("status") or "")
    return "ready" in status or status.endswith("_ok") or status == "ok"


def _component_safe_present(payload: dict[str, Any]) -> bool:
    return bool(payload) and _int(payload.get("paper_order_created_count"), 0) == 0 and _int(payload.get("broker_write_count"), 0) == 0 and payload.get("live_capital_enabled") is not True


def _load_context(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "runtime": runtime,
        "source": _read_json(runtime / SOURCE_RELIABILITY_ARTIFACT),
        "historical": _read_json(runtime / HISTORICAL_MEMORY_ARTIFACT),
        "akber_inputs": _read_json(runtime / AKBER_INPUT_COMPLETENESS_ARTIFACT),
        "validated_edge": _read_json(runtime / VALIDATED_EDGE_ARTIFACT),
        "pattern_search": _read_json(runtime / PATTERN_SEARCH_ARTIFACT),
        "strategy_foundry": _read_json(runtime / STRATEGY_FOUNDRY_ARTIFACT),
        "akber_filter": _read_json(runtime / AKBER_FILTER_ARTIFACT),
        "shadow": _read_json(runtime / SHADOW_SIMULATOR_ARTIFACT),
        "router": _read_json(runtime / ROUTER_ARTIFACT),
        "paperops": _read_json(runtime / PAPEROPS_HANDOFF_ARTIFACT),
        "lifecycle": _read_json(runtime / PAPER_LIFECYCLE_ARTIFACT),
        "proof": _read_json(runtime / PROOF_LEDGER_ARTIFACT),
        "learning": _read_json(runtime / LEARNING_ATTRIBUTION_ARTIFACT),
        "dashboard": _read_json(runtime / DASHBOARD_COMPLETION_ARTIFACT),
        "telegram": _read_json(runtime / TELEGRAM_SUMMARY_ARTIFACT),
        "self_healing": _read_json(runtime / SELF_HEALING_ARTIFACT),
        "deploy": _read_json(runtime / GIT_DEPLOY_ARTIFACT),
        "why_not": _read_json(runtime / WHY_NOT_ARTIFACT),
        "positions": _read_jsonl(runtime / PAPER_POSITIONS_ARTIFACT, limit=1000),
    }


def _gate(name: str, passed: bool, reason: str, artifact: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "gate": name,
        "passed": passed,
        "reason": reason,
        "artifact_ref": _artifact_ref(artifact),
        "details": details or {},
    }


def build_operational_perfection_certification(settings: Settings | None = None, *, refresh_self_healing: bool = True) -> dict[str, Any]:
    if refresh_self_healing:
        build_and_write_self_healing_state(settings, perform_refresh=True)
    context = _load_context(settings)
    generated_at = _iso(_now())

    source = context["source"]
    historical = context["historical"]
    akber_inputs = context["akber_inputs"]
    validated_edge = context["validated_edge"]
    pattern_search = context["pattern_search"]
    strategy_foundry = context["strategy_foundry"]
    akber_filter = context["akber_filter"]
    shadow = context["shadow"]
    router = context["router"]
    paperops = context["paperops"]
    lifecycle = context["lifecycle"]
    proof = context["proof"]
    learning = context["learning"]
    dashboard = context["dashboard"]
    telegram = context["telegram"]
    self_healing = context["self_healing"]
    deploy = context["deploy"]
    why_not = context["why_not"]
    positions = context["positions"]

    required_source_freshness_passed = source.get("target_required_source_freshness_passed") is True
    source_quorum_protected = _safe_dict(self_healing.get("quarantine_tier")).get("source_quorum_protected") is True
    historical_memory_coverage_passed = historical.get("target_complete_forward_window_passed") is True
    akber_input_completeness_passed = str(akber_inputs.get("status")) == "akber_inputs_complete"
    validated_edge_pathway_passed = _status_ready(validated_edge) and _int(validated_edge.get("paper_order_created_count"), 0) == 0
    pattern_search_passed = _status_ready(pattern_search)
    strategy_foundry_passed = _component_safe_present(strategy_foundry)
    akber_filter_passed = _status_ready(akber_filter)
    shadow_simulator_passed = _status_ready(shadow)
    router_decision_integrity_passed = _status_ready(router) and _int(router.get("paper_order_created_count"), 0) == 0 and _int(router.get("broker_write_count"), 0) == 0
    paperops_guarded_route_passed = bool(paperops) and _int(paperops.get("paper_order_created_count"), 0) == 0 and _int(paperops.get("broker_write_count"), 0) == 0
    lifecycle_proof_passed = (
        _status_ready(lifecycle)
        and _int(lifecycle.get("ambiguous_lifecycle_count"), 0) == 0
        and bool(proof)
        and proof.get("proof_credit_allowed") is False
    )
    learning_passed = _status_ready(learning) and learning.get("policy_mutation_created") is False
    dashboard_public_contract_passed = (
        _status_ready(dashboard)
        and dashboard.get("portfolio_consistency_status") == "ok"
        and _int(dashboard.get("anti_slop_error_count"), 0) == 0
    )
    telegram_boundary_passed = (
        _status_ready(telegram)
        and telegram.get("telegram_live_send_allowed") is False
        and telegram.get("telegram_command_path_enabled") is False
    )
    self_healing_passed = self_healing.get("self_healing_passed") is True
    deployment_closure_passed = deploy.get("deployment_closure_passed") is True
    safety_boundaries_passed = all(
        [
            _int(router.get("paper_order_created_count"), 0) == 0,
            _int(paperops.get("paper_order_created_count"), 0) == 0,
            _int(lifecycle.get("paper_order_created_count"), 0) == 0,
            _int(telegram.get("paper_order_created_count"), 0) == 0,
            _int(router.get("broker_write_count"), 0) == 0,
            _int(paperops.get("broker_write_count"), 0) == 0,
            _int(lifecycle.get("broker_write_count"), 0) == 0,
            _int(telegram.get("broker_write_count"), 0) == 0,
            proof.get("proof_credit_allowed") is False,
        ]
    )

    gates = [
        _gate(
            "required_source_freshness",
            required_source_freshness_passed,
            "required source freshness target passed" if required_source_freshness_passed else "required source freshness target is not passed",
            SOURCE_RELIABILITY_ARTIFACT,
            {
                "source_status": source.get("status"),
                "required_source_freshness_ratio": source.get("required_source_freshness_ratio"),
                "source_quorum_protected_by_quarantine": source_quorum_protected,
                "outage_count": source.get("outage_count"),
            },
        ),
        _gate(
            "historical_memory_coverage",
            historical_memory_coverage_passed,
            "historical source-price forward windows satisfy target" if historical_memory_coverage_passed else "historical source-price forward windows are incomplete",
            HISTORICAL_MEMORY_ARTIFACT,
            {
                "complete_forward_window_count": historical.get("complete_forward_window_count"),
                "missing_forward_window_count": historical.get("missing_forward_window_count"),
                "complete_forward_window_ratio": historical.get("complete_forward_window_ratio"),
            },
        ),
        _gate(
            "akber_input_completeness",
            akber_input_completeness_passed,
            "Akber practical confirmation inputs are complete" if akber_input_completeness_passed else "Akber practical confirmation inputs are incomplete",
            AKBER_INPUT_COMPLETENESS_ARTIFACT,
            {"missing_input_counts": akber_inputs.get("missing_input_counts")},
        ),
        _gate("validated_edge_pathway", validated_edge_pathway_passed, "validated-edge pathway is safe and present", VALIDATED_EDGE_ARTIFACT),
        _gate("full_universe_pattern_search", pattern_search_passed, "pattern search V2 is present", PATTERN_SEARCH_ARTIFACT),
        _gate("strategy_foundry", strategy_foundry_passed, "strategy foundry V2 is present", STRATEGY_FOUNDRY_ARTIFACT),
        _gate("akber_filter", akber_filter_passed, "Akber filter V2 is present", AKBER_FILTER_ARTIFACT),
        _gate("shadow_simulator", shadow_simulator_passed, "shadow simulator V2 is present", SHADOW_SIMULATOR_ARTIFACT),
        _gate("router_decision_integrity", router_decision_integrity_passed, "router decisions are safe", ROUTER_ARTIFACT),
        _gate("paperops_guarded_route", paperops_guarded_route_passed, "PaperOps handoff route is guarded", PAPEROPS_HANDOFF_ARTIFACT),
        _gate("lifecycle_and_proof_boundary", lifecycle_proof_passed, "lifecycle and proof ledger boundary is safe", PAPER_LIFECYCLE_ARTIFACT),
        _gate("learning_attribution", learning_passed, "learning changes are proposal-only", LEARNING_ATTRIBUTION_ARTIFACT),
        _gate("dashboard_public_contract", dashboard_public_contract_passed, "dashboard public contract is safe", DASHBOARD_COMPLETION_ARTIFACT),
        _gate("telegram_boundary", telegram_boundary_passed, "Telegram boundary is review-only", TELEGRAM_SUMMARY_ARTIFACT),
        _gate("self_healing", self_healing_passed, "self-healing supervisor is operational", SELF_HEALING_ARTIFACT),
        _gate(
            "deployment_closure",
            deployment_closure_passed,
            "git and deploy closure passed" if deployment_closure_passed else "git or deployment closure is blocked",
            GIT_DEPLOY_ARTIFACT,
            {"blockers": _safe_list(deploy.get("blockers"))},
        ),
        _gate("safety_boundaries", safety_boundaries_passed, "no unsafe authority was created", PRIMARY_ARTIFACT),
    ]

    unresolved_blockers = [
        {
            "gate": gate["gate"],
            "reason": gate["reason"],
            "artifact_ref": gate["artifact_ref"],
            "details": gate["details"],
        }
        for gate in gates
        if gate["passed"] is not True
    ]
    operationally_complete = not unresolved_blockers
    paper_review_candidate_count = _int(router.get("paper_review_candidate_count"), 0)
    active_paper_position_count = len(positions)
    if not safety_boundaries_passed:
        status = "qadam_operationally_unsafe_fail_closed"
    elif not operationally_complete:
        status = "qadam_operationally_incomplete"
    elif active_paper_position_count:
        status = "qadam_operationally_complete_with_active_paper_position"
    elif paper_review_candidate_count:
        status = "qadam_operationally_complete_with_paper_review_candidate"
    else:
        status = "qadam_operationally_complete_no_qualified_setup"

    why_not_trading_now = str(why_not.get("reason") or "no qualified setup")
    if not operationally_complete and unresolved_blockers:
        why_not_trading_now = f"system blocker: {unresolved_blockers[0]['reason']}"

    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operational_perfection_certification",
        "generated_at": generated_at,
        "status": status,
        "status_family": "qadam_operationally_complete" if operationally_complete else "qadam_operationally_incomplete",
        "operationally_complete": operationally_complete,
        "paper_only": True,
        "public_safe": True,
        "read_only": True,
        "proposal_first": True,
        "command_disabled": True,
        "authority": universal_authority_flags(),
        "authority_flags": AUTHORITY_FLAGS,
        "live_capital_enabled": False,
        "required_source_freshness_passed": required_source_freshness_passed,
        "source_quorum_protected_by_quarantine": source_quorum_protected,
        "historical_memory_coverage_passed": historical_memory_coverage_passed,
        "akber_input_completeness_passed": akber_input_completeness_passed,
        "validated_edge_pathway_passed": validated_edge_pathway_passed,
        "pattern_search_passed": pattern_search_passed,
        "strategy_foundry_passed": strategy_foundry_passed,
        "akber_filter_passed": akber_filter_passed,
        "shadow_simulator_passed": shadow_simulator_passed,
        "router_decision_integrity_passed": router_decision_integrity_passed,
        "paperops_guarded_route_passed": paperops_guarded_route_passed,
        "lifecycle_proof_boundary_passed": lifecycle_proof_passed,
        "learning_attribution_passed": learning_passed,
        "dashboard_public_contract_passed": dashboard_public_contract_passed,
        "telegram_boundary_passed": telegram_boundary_passed,
        "self_healing_passed": self_healing_passed,
        "deployment_closure_passed": deployment_closure_passed,
        "safety_boundaries_passed": safety_boundaries_passed,
        "gate_count": len(gates),
        "passed_gate_count": sum(1 for gate in gates if gate["passed"]),
        "failed_gate_count": sum(1 for gate in gates if not gate["passed"]),
        "gates": gates,
        "unresolved_blockers": unresolved_blockers,
        "paper_review_candidate_count": paper_review_candidate_count,
        "active_paper_position_count": active_paper_position_count,
        "why_not_trading_now": why_not_trading_now,
        "final_answer_contract": (
            "Yes. Qadam is operationally complete and running as designed."
            if operationally_complete
            else f"No. Qadam is not operationally complete yet. The current blocker is: {unresolved_blockers[0]['reason'] if unresolved_blockers else 'unknown'}."
        ),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "boundary": "Operational perfection certification is a read-only yes/no audit. It never forces trades or treats no-trade periods as failures when gates are healthy.",
    }


def validate_operational_perfection(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if payload.get("artifact_type") != "qadam_operational_perfection_certification":
        errors.append("artifact_type_mismatch")
    for field in ("paper_only", "public_safe", "read_only", "proposal_first", "command_disabled"):
        if payload.get(field) is not True:
            errors.append(f"{field}_must_be_true")
    for field in FALSE_AUTHORITY_FIELDS:
        if payload.get(field) is True:
            errors.append(f"{field}_must_not_be_true")
    if payload.get("status") == "qadam_operationally_complete" and payload.get("unresolved_blockers"):
        errors.append("complete_status_with_unresolved_blockers")
    if payload.get("status_family") == "qadam_operationally_complete" and payload.get("unresolved_blockers"):
        errors.append("complete_family_with_unresolved_blockers")
    if payload.get("safety_boundaries_passed") is not True:
        errors.append("safety_boundaries_not_passed")
    if _int(payload.get("paper_order_created_count"), 0) != 0:
        errors.append("paper_order_created_count_must_be_zero")
    if _int(payload.get("broker_write_count"), 0) != 0:
        errors.append("broker_write_count_must_be_zero")
    if payload.get("proof_credit_allowed") is not False:
        errors.append("proof_credit_allowed_must_be_false")
    if payload.get("live_capital_enabled") is not False:
        errors.append("live_capital_enabled_must_be_false")
    return sorted(set(errors))


def _dashboard_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operational_perfection_dashboard_summary",
        "generated_at": payload.get("generated_at"),
        "status": payload.get("status"),
        "operationally_complete": payload.get("operationally_complete"),
        "failed_gate_count": payload.get("failed_gate_count"),
        "first_blocker": payload.get("unresolved_blockers", [{}])[0].get("reason") if payload.get("unresolved_blockers") else "none",
        "why_not_trading_now": payload.get("why_not_trading_now"),
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "command_disabled": True,
        "live_capital_enabled": False,
    }


def _phase_record(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": "Perfect Operation Phase 16: End-To-End Operational Certification",
        "status": payload.get("status"),
        "artifact_path": _artifact_ref(PRIMARY_ARTIFACT),
        "operationally_complete": payload.get("operationally_complete"),
        "passed_gate_count": payload.get("passed_gate_count"),
        "failed_gate_count": payload.get("failed_gate_count"),
        "why_not_trading_now": payload.get("why_not_trading_now"),
        "paper_only": True,
        "public_safe": True,
        "read_only": True,
        "proposal_first": True,
        "no_trade_candidates_created": True,
        "no_paper_orders_created": True,
        "no_broker_writes": True,
        "no_proof_credit_granted": True,
        "live_capital_enabled": False,
    }


def _update_phase_status(path: Path, payload: dict[str, Any]) -> None:
    current = _read_json(path)
    phases = _safe_dict(current.get("phases"))
    phases["perfect_operation_phase_16_operational_perfection_certification"] = _phase_record(payload)
    safety = {
        **_safe_dict(current.get("safety")),
        "phase16_certification_outputs_are_review_only": True,
        "paper_only": True,
        "live_capital_enabled": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "telegram_command_path_enabled": False,
    }
    _write_json(
        path,
        {
            **current,
            "schema_version": current.get("schema_version", 1),
            "generated_at": payload.get("generated_at"),
            "active_phase": "perfect_operation_phase_16_operational_perfection_certification",
            "phases": phases,
            "safety": safety,
        },
    )


def build_and_write_operational_perfection_certification(settings: Settings | None = None, *, refresh_self_healing: bool = True) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    payload = build_operational_perfection_certification(settings, refresh_self_healing=refresh_self_healing)
    runtime = _runtime_dir(settings)
    written: dict[str, str] = {}
    _write_json(runtime / PRIMARY_ARTIFACT, payload)
    written["primary"] = str(runtime / PRIMARY_ARTIFACT)
    _write_json(runtime / DASHBOARD_SUMMARY_ARTIFACT, _dashboard_summary(payload))
    written["dashboard_summary"] = str(runtime / DASHBOARD_SUMMARY_ARTIFACT)
    event = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": payload.get("generated_at"),
        "event": "qadam_operational_perfection_certification_written",
        "status": payload.get("status"),
        "operationally_complete": payload.get("operationally_complete"),
        "failed_gate_count": payload.get("failed_gate_count"),
        "why_not_trading_now": payload.get("why_not_trading_now"),
    }
    _append_jsonl(runtime / HISTORY_ARTIFACT, event)
    _append_jsonl(runtime / EVENTS_ARTIFACT, event)
    written["history"] = str(runtime / HISTORY_ARTIFACT)
    written["events"] = str(runtime / EVENTS_ARTIFACT)
    _update_phase_status(runtime / PHASE_STATUS_ARTIFACT, payload)
    written["phase_status"] = str(runtime / PHASE_STATUS_ARTIFACT)
    errors = validate_operational_perfection(payload)
    return payload, written, errors
