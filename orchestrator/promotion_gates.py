"""Read-only promotion gates for Qadam.

Stage 4F evaluates whether Stage 4E self-improvement proposals can be promoted
into a later implementation or strategy-review path. It is a gate ledger only:
it can hold or flag proposals for later human review, but it cannot promote,
implement, approve, merge, deploy, mutate strategy, or create trading authority.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.self_improvement_proposals import (
    SELF_IMPROVEMENT_PROPOSALS_AUTHORITY_FALSE_FIELDS,
    validate_self_improvement_proposals,
)
from orchestrator.strategy_weight_updates import STRATEGY_FAMILIES


PROMOTION_GATES_SCHEMA_VERSION = 1
PROMOTION_GATES_RUNTIME_ARTIFACT = "promotion_gates.json"
PROMOTION_GATES_HISTORY = "promotion_gates_history.jsonl"
PROMOTION_GATES_EVENT_LOG = "promotion_gates_events.jsonl"
PROMOTION_GATES_EVENT_TYPE = "promotion_gates_recorded"
PROMOTION_GATES_COMPONENT = "promotion_gates"

PROMOTION_GATES_AUTHORITY_FALSE_FIELDS: tuple[str, ...] = tuple(
    dict.fromkeys(
        (
            *SELF_IMPROVEMENT_PROPOSALS_AUTHORITY_FALSE_FIELDS,
            "promotion_apply_allowed",
            "promotion_applied",
            "promotion_allowed",
            "promotion_gate_override_allowed",
            "human_approval_inferred",
            "implementation_ticket_creation_allowed",
            "implementation_ticket_created",
            "repo_write_allowed",
            "code_change_allowed",
            "prompt_mutation_allowed",
            "strategy_weight_application_allowed",
            "active_strategy_mutation_allowed",
            "portfolio_rebalance_allowed",
            "paper_order_submission_allowed",
            "broker_write_allowed",
            "quantum_provider_call_allowed",
            "telegram_live_send_allowed",
            "deployment_allowed",
            "auto_merge_allowed",
            "live_capital_enablement_allowed",
            "proof_credit_grant_allowed",
        )
    )
)

PROMOTION_GATES_STATUSES = {
    "promotion_gates_ready",
    "promotion_gates_blocked_pending_self_improvement_proposals",
}

PROMOTION_GATES_BOUNDARY = (
    "Promotion Gates is a read-only promotion gate ledger. It can evaluate "
    "whether self-improvement proposals satisfy quantum, evidence, outcome, "
    "and human-governance criteria for a later review path, but it cannot "
    "promote proposals, create implementation tickets, edit code, mutate "
    "prompts, apply strategy weights, mutate active strategy, change order "
    "sizing, approve risk, submit paper orders, write brokers, send live "
    "Telegram messages, call quantum providers, submit hardware jobs, deploy "
    "changes, enable live capital, or grant proof credit."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def promotion_gates_paths(settings: Settings | None = None) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PROMOTION_GATES_RUNTIME_ARTIFACT,
        runtime / PROMOTION_GATES_HISTORY,
        runtime / PROMOTION_GATES_EVENT_LOG,
    )


def read_promotion_gates(settings: Settings | None = None) -> dict[str, Any]:
    output_path, _, _ = promotion_gates_paths(settings)
    if not output_path.exists():
        return {}
    try:
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _weight_key(family: dict[str, str]) -> str:
    return family["strategy_family_key"]


def _weight_sum(weights: dict[str, Any]) -> float:
    return round(sum(float(value) for value in weights.values()), 6)


def _records_by_family(records: list[Any]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        family_key = str(record.get("strategy_family_key") or "").strip()
        if family_key:
            output[family_key] = record
    return output


def _decision_hold_reasons(proposal: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if proposal.get("proposal_ready_for_review") is not True:
        reasons.append("proposal_not_ready_for_review")
    if proposal.get("quantum_dependency_satisfied") is not True:
        reasons.append("quantum_dependency_not_satisfied")
    if proposal.get("oracle_contract_accepted") is not True:
        reasons.append("oracle_contract_not_accepted")
    if proposal.get("optimized_for_quantum_oracle") is not True:
        reasons.append("not_optimized_for_quantum_oracle")
    unresolved = [
        str(reason)
        for reason in _as_list(proposal.get("blocked_reasons_to_resolve"))
        if str(reason)
    ]
    if unresolved:
        reasons.append("upstream_meta_review_hold_unresolved")
        reasons.extend(unresolved)
    if proposal.get("meta_review_passed") is True:
        reasons.append("paper_outcome_feedback_missing")
    reasons.append("explicit_human_promotion_approval_missing")
    return sorted(set(reasons))


def _criteria(proposal: dict[str, Any], hold_reasons: list[str]) -> dict[str, bool]:
    return {
        "proposal_ready_for_review": proposal.get("proposal_ready_for_review") is True,
        "quantum_dependency_satisfied": proposal.get("quantum_dependency_satisfied") is True,
        "oracle_contract_accepted": proposal.get("oracle_contract_accepted") is True,
        "optimized_for_quantum_oracle": proposal.get("optimized_for_quantum_oracle") is True,
        "upstream_holds_resolved": "upstream_meta_review_hold_unresolved" not in hold_reasons,
        "paper_outcome_feedback_available": "paper_outcome_feedback_missing"
        not in hold_reasons,
        "explicit_human_approval_present": False,
        "authority_boundary_clean": True,
    }


def _promotion_gate_decision(
    *,
    family: dict[str, str],
    proposal: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    hold_reasons = _decision_hold_reasons(proposal)
    criteria = _criteria(proposal, hold_reasons)
    promotion_gate_passed = all(criteria.values())
    decision_id = "promotion-gate:" + sha256(
        json.dumps(
            {
                "proposal_id": proposal.get("proposal_id"),
                "strategy_family_key": family["strategy_family_key"],
                "hold_reasons": hold_reasons,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:18]
    decision = {
        "promotion_gate_id": decision_id,
        "status": "promotion_gate_passed_not_applied"
        if promotion_gate_passed
        else "promotion_gate_held",
        "decision_status": "gate_evaluated_not_promoted",
        "sleeve_key": family["sleeve_key"],
        "instrument_key": family["instrument_key"],
        "strategy_family_key": family["strategy_family_key"],
        "strategy_family_name": family["strategy_family_name"],
        "source_proposal_id": proposal.get("proposal_id"),
        "source_proposal_kind": proposal.get("proposal_kind"),
        "promotion_scope": "human_governed_review_path_only",
        "promotion_gate_passed": promotion_gate_passed,
        "promotion_review_ready": proposal.get("proposal_ready_for_review") is True,
        "promotion_allowed": False,
        "promotion_applied": False,
        "promotion_applied_at": None,
        "human_approval_required": True,
        "human_approval_present": False,
        "explicit_approval_source": None,
        "quantum_required": True,
        "quantum_dependency_satisfied": proposal.get("quantum_dependency_satisfied") is True,
        "quantum_review_status": proposal.get("quantum_review_status"),
        "quantum_backend": proposal.get("quantum_backend"),
        "fire_opal_ibm_status": proposal.get("fire_opal_ibm_status"),
        "oracle_contract_accepted": proposal.get("oracle_contract_accepted") is True,
        "optimized_for_quantum_oracle": proposal.get("optimized_for_quantum_oracle") is True,
        "meta_review_passed": proposal.get("meta_review_passed") is True,
        "meta_review_hold_reasons": [
            str(reason)
            for reason in _as_list(proposal.get("meta_review_hold_reasons"))
            if str(reason)
        ],
        "blocked_reasons_to_resolve": [
            str(reason)
            for reason in _as_list(proposal.get("blocked_reasons_to_resolve"))
            if str(reason)
        ],
        "promotion_hold_reasons": hold_reasons,
        "promotion_gate_criteria": criteria,
        "next_review_requirements": [
            "resolve upstream meta-review holds",
            "link paper outcome or source follow-through evidence",
            "keep quantum dependency and oracle contract accepted",
            "obtain explicit human promotion approval",
            "run implementation-specific tests before any later code or strategy change",
        ],
        "allowed_next_action": (
            "Record this proposal for later human-governed review; do not "
            "implement or promote it automatically."
        ),
        "blocked_action": (
            "No code edits, prompt changes, strategy-weight changes, paper "
            "orders, broker writes, provider calls, deployments, or proof "
            "credit can be triggered by this promotion gate."
        ),
        "created_at": generated_at,
    }
    for field in PROMOTION_GATES_AUTHORITY_FALSE_FIELDS:
        decision[field] = False
    return decision


def build_promotion_gates(
    *,
    self_improvement_proposals: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build Qadam's Stage 4F promotion gate ledger."""

    generated_at = generated_at or _now()
    validate_self_improvement_proposals(self_improvement_proposals)
    dependency_ready = (
        self_improvement_proposals.get("status") == "self_improvement_proposals_ready"
    )
    status = (
        "promotion_gates_ready"
        if dependency_ready
        else "promotion_gates_blocked_pending_self_improvement_proposals"
    )
    proposals_by_family = _records_by_family(
        _as_list(self_improvement_proposals.get("self_improvement_proposals"))
    )
    decisions = [
        _promotion_gate_decision(
            family=family,
            proposal=proposals_by_family.get(family["strategy_family_key"], {}),
            generated_at=generated_at,
        )
        for family in STRATEGY_FAMILIES
        if status == "promotion_gates_ready"
    ]
    passed_count = sum(1 for decision in decisions if decision["promotion_gate_passed"] is True)
    held_count = len(decisions) - passed_count
    review_ready_count = sum(
        1 for decision in decisions if decision["promotion_review_ready"] is True
    )
    quantum_count = sum(
        1 for decision in decisions if decision["quantum_dependency_satisfied"] is True
    )
    oracle_count = sum(
        1 for decision in decisions if decision["oracle_contract_accepted"] is True
    )
    upstream_unresolved_count = sum(
        1
        for decision in decisions
        if "upstream_meta_review_hold_unresolved" in decision["promotion_hold_reasons"]
    )
    outcome_missing_count = sum(
        1
        for decision in decisions
        if "paper_outcome_feedback_missing" in decision["promotion_hold_reasons"]
    )
    human_approval_missing_count = sum(
        1
        for decision in decisions
        if "explicit_human_promotion_approval_missing"
        in decision["promotion_hold_reasons"]
    )
    active_before_weights = dict(
        self_improvement_proposals.get("active_before_weights") or {}
    )
    active_after_weights = dict(self_improvement_proposals.get("active_after_weights") or {})
    artifact = {
        "schema_version": PROMOTION_GATES_SCHEMA_VERSION,
        "artifact_type": "promotion_gates",
        "artifact_id": "promotion-gates:latest",
        "stage": "Stage 4F - Promotion Gates",
        "generated_at": generated_at,
        "status": status,
        "public_safe": True,
        "purpose": (
            "Evaluate whether self-improvement proposals satisfy the gates for "
            "a later human-governed promotion path, without promoting or "
            "implementing anything automatically."
        ),
        "self_improvement_proposals_status": self_improvement_proposals.get("status"),
        "strategy_family_count": len(STRATEGY_FAMILIES),
        "promotion_gate_decision_count": len(decisions),
        "promotion_gate_passed_count": passed_count,
        "promotion_gate_held_count": held_count,
        "promotion_review_ready_count": review_ready_count,
        "promotion_allowed_count": 0,
        "promotion_applied_count": 0,
        "human_approval_present_count": 0,
        "human_approval_missing_count": human_approval_missing_count,
        "quantum_dependency_satisfied_count": quantum_count,
        "oracle_contract_accepted_count": oracle_count,
        "upstream_hold_unresolved_count": upstream_unresolved_count,
        "outcome_feedback_missing_count": outcome_missing_count,
        "implementation_ticket_created_count": 0,
        "code_change_applied_count": 0,
        "prompt_mutation_applied_count": 0,
        "strategy_weight_application_count": 0,
        "active_strategy_mutation_count": 0,
        "portfolio_rebalance_count": 0,
        "paper_order_submission_count": 0,
        "broker_write_count": 0,
        "quantum_provider_call_count": 0,
        "telegram_live_send_count": 0,
        "deployment_count": 0,
        "proof_credit_grant_count": 0,
        "active_before_weights": active_before_weights,
        "active_after_weights": active_after_weights,
        "active_before_weight_sum": _weight_sum(active_before_weights),
        "active_after_weight_sum": _weight_sum(active_after_weights),
        "active_weights_unchanged": active_before_weights == active_after_weights,
        "loop_level_decision": {
            "status": "promotion_gates_evaluated"
            if dependency_ready
            else "promotion_gates_blocked",
            "review_scope": "self_improvement_proposal_promotion_readiness",
            "recommendation_only": True,
            "promotion_gate_records_created": len(decisions),
            "can_promote_proposals": False,
            "can_create_implementation_tickets": False,
            "can_edit_code": False,
            "can_mutate_prompts": False,
            "can_apply_strategy_weights": False,
            "can_mutate_strategy": False,
            "can_change_order_sizing": False,
            "can_submit_paper_orders": False,
            "can_call_brokers": False,
            "can_call_quantum_providers": False,
            "can_send_live_telegram": False,
            "can_deploy": False,
            "boundary": (
                "Promotion gates can evaluate readiness only. They do not "
                "promote proposals or create implementation authority."
            ),
        },
        "promotion_gate_contract": {
            "status": "promotion_gate_ledger_active" if dependency_ready else "blocked",
            "uses_self_improvement_proposals": True,
            "gate_only": True,
            "recommendation_only": True,
            "human_approval_required": True,
            "human_approval_present": False,
            "active_weights_unchanged": active_before_weights == active_after_weights,
            "promotes_proposals": False,
            "creates_implementation_tickets": False,
            "repo_write_allowed": False,
            "code_change_allowed": False,
            "prompt_mutation_allowed": False,
            "applies_weight_updates": False,
            "mutates_active_strategy": False,
            "changes_order_sizing": False,
            "paper_order_allowed": False,
            "broker_write_allowed": False,
            "quantum_provider_call_allowed": False,
            "telegram_live_send_allowed": False,
            "deployment_allowed": False,
            "boundary": (
                "Stage 4F can only write a runtime gate artifact. Any later "
                "promotion must be separately requested, approved, implemented, "
                "tested, committed, and deployed."
            ),
        },
        "promotion_gate_decisions": decisions,
        "blocked_reason": None
        if status == "promotion_gates_ready"
        else "self_improvement_proposals_not_ready",
        "documentation_routes": {
            "runtime_artifact": f"data/runtime/{PROMOTION_GATES_RUNTIME_ARTIFACT}",
            "history": f"data/runtime/{PROMOTION_GATES_HISTORY}",
            "event_log": f"data/runtime/{PROMOTION_GATES_EVENT_LOG}",
            "source_self_improvement_proposals": "data/runtime/self_improvement_proposals.json",
        },
        "boundary": PROMOTION_GATES_BOUNDARY,
    }
    for field in PROMOTION_GATES_AUTHORITY_FALSE_FIELDS:
        artifact[field] = False
    return artifact


def _validate_weights(prefix: str, value: Any) -> dict[str, float]:
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{prefix} missing")
    expected_keys = {_weight_key(family) for family in STRATEGY_FAMILIES}
    if set(value) != expected_keys:
        raise ValueError(f"{prefix} keys mismatch")
    weights: dict[str, float] = {}
    for key, item in value.items():
        if not isinstance(item, int | float):
            raise ValueError(f"{prefix} value invalid")
        weights[str(key)] = round(float(item), 6)
    if not 0.999 <= _weight_sum(weights) <= 1.001:
        raise ValueError(f"{prefix} not normalized")
    return weights


def validate_promotion_gates(payload: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "stage",
        "generated_at",
        "status",
        "public_safe",
        "purpose",
        "self_improvement_proposals_status",
        "strategy_family_count",
        "promotion_gate_decision_count",
        "promotion_gate_passed_count",
        "promotion_gate_held_count",
        "promotion_review_ready_count",
        "promotion_allowed_count",
        "promotion_applied_count",
        "human_approval_present_count",
        "human_approval_missing_count",
        "quantum_dependency_satisfied_count",
        "oracle_contract_accepted_count",
        "upstream_hold_unresolved_count",
        "outcome_feedback_missing_count",
        "implementation_ticket_created_count",
        "code_change_applied_count",
        "prompt_mutation_applied_count",
        "strategy_weight_application_count",
        "active_strategy_mutation_count",
        "portfolio_rebalance_count",
        "paper_order_submission_count",
        "broker_write_count",
        "quantum_provider_call_count",
        "telegram_live_send_count",
        "deployment_count",
        "proof_credit_grant_count",
        "active_before_weights",
        "active_after_weights",
        "active_before_weight_sum",
        "active_after_weight_sum",
        "active_weights_unchanged",
        "loop_level_decision",
        "promotion_gate_contract",
        "promotion_gate_decisions",
        "blocked_reason",
        "documentation_routes",
        "boundary",
        *PROMOTION_GATES_AUTHORITY_FALSE_FIELDS,
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"promotion gates missing fields: {missing}")
    if payload.get("schema_version") != PROMOTION_GATES_SCHEMA_VERSION:
        raise ValueError("promotion gates schema mismatch")
    if payload.get("artifact_type") != "promotion_gates":
        raise ValueError("promotion gates artifact type mismatch")
    if payload.get("status") not in PROMOTION_GATES_STATUSES:
        raise ValueError("promotion gates status invalid")
    if payload.get("public_safe") is not True:
        raise ValueError("promotion gates must be public-safe")
    if "read-only promotion gate ledger" not in str(payload.get("boundary", "")):
        raise ValueError("promotion gates boundary weak")
    for field in PROMOTION_GATES_AUTHORITY_FALSE_FIELDS:
        if payload.get(field) is not False:
            raise ValueError(f"promotion gates authority leak: {field}")
    active_before = _validate_weights("active_before_weights", payload.get("active_before_weights"))
    active_after = _validate_weights("active_after_weights", payload.get("active_after_weights"))
    if active_before != active_after:
        raise ValueError("promotion gates active weights mutated")
    if payload.get("active_weights_unchanged") is not True:
        raise ValueError("promotion gates active weights changed")
    if payload.get("active_before_weight_sum") != _weight_sum(active_before):
        raise ValueError("promotion gates active before sum mismatch")
    if payload.get("active_after_weight_sum") != _weight_sum(active_after):
        raise ValueError("promotion gates active after sum mismatch")
    if _int(payload.get("strategy_family_count")) != len(STRATEGY_FAMILIES):
        raise ValueError("promotion gates strategy family count mismatch")
    decisions = payload.get("promotion_gate_decisions")
    if not isinstance(decisions, list):
        raise ValueError("promotion gate decisions must be a list")
    if _int(payload.get("promotion_gate_decision_count")) != len(decisions):
        raise ValueError("promotion gate decision count mismatch")
    zero_count_fields = (
        "promotion_allowed_count",
        "promotion_applied_count",
        "human_approval_present_count",
        "implementation_ticket_created_count",
        "code_change_applied_count",
        "prompt_mutation_applied_count",
        "strategy_weight_application_count",
        "active_strategy_mutation_count",
        "portfolio_rebalance_count",
        "paper_order_submission_count",
        "broker_write_count",
        "quantum_provider_call_count",
        "telegram_live_send_count",
        "deployment_count",
        "proof_credit_grant_count",
    )
    for field in zero_count_fields:
        if _int(payload.get(field)) != 0:
            raise ValueError(f"promotion gates count must stay zero: {field}")
    loop = _as_dict(payload.get("loop_level_decision"))
    contract = _as_dict(payload.get("promotion_gate_contract"))
    for field in (
        "can_promote_proposals",
        "can_create_implementation_tickets",
        "can_edit_code",
        "can_mutate_prompts",
        "can_apply_strategy_weights",
        "can_mutate_strategy",
        "can_change_order_sizing",
        "can_submit_paper_orders",
        "can_call_brokers",
        "can_call_quantum_providers",
        "can_send_live_telegram",
        "can_deploy",
    ):
        if loop.get(field) is not False:
            raise ValueError(f"promotion gates loop authority leak: {field}")
    for field in (
        "promotes_proposals",
        "creates_implementation_tickets",
        "repo_write_allowed",
        "code_change_allowed",
        "prompt_mutation_allowed",
        "applies_weight_updates",
        "mutates_active_strategy",
        "changes_order_sizing",
        "paper_order_allowed",
        "broker_write_allowed",
        "quantum_provider_call_allowed",
        "telegram_live_send_allowed",
        "deployment_allowed",
    ):
        if contract.get(field) is not False:
            raise ValueError(f"promotion gates contract authority leak: {field}")
    if loop.get("recommendation_only") is not True:
        raise ValueError("promotion gates loop must be recommendation-only")
    if contract.get("recommendation_only") is not True:
        raise ValueError("promotion gates contract must be recommendation-only")
    ready = payload.get("status") == "promotion_gates_ready"
    if ready:
        if payload.get("self_improvement_proposals_status") != (
            "self_improvement_proposals_ready"
        ):
            raise ValueError("ready promotion gates need self-improvement proposals")
        if payload.get("blocked_reason") is not None:
            raise ValueError("ready promotion gates cannot be blocked")
        if len(decisions) != len(STRATEGY_FAMILIES):
            raise ValueError("ready promotion gates must cover all families")
        if loop.get("status") != "promotion_gates_evaluated":
            raise ValueError("ready promotion gates loop invalid")
    else:
        if payload.get("blocked_reason") != "self_improvement_proposals_not_ready":
            raise ValueError("blocked promotion gates need blocked reason")
        if decisions:
            raise ValueError("blocked promotion gates cannot emit decisions")
        if loop.get("status") != "promotion_gates_blocked":
            raise ValueError("blocked promotion gates loop invalid")
    seen_families: set[str] = set()
    passed_count = 0
    held_count = 0
    review_ready_count = 0
    quantum_count = 0
    oracle_count = 0
    upstream_unresolved_count = 0
    outcome_missing_count = 0
    human_missing_count = 0
    for decision in decisions:
        if not isinstance(decision, dict):
            raise ValueError("promotion gate decision must be a dict")
        family_key = str(decision.get("strategy_family_key") or "")
        if family_key in seen_families:
            raise ValueError("duplicate promotion gate family")
        seen_families.add(family_key)
        if family_key not in active_before:
            raise ValueError("promotion gate family unknown")
        if decision.get("decision_status") != "gate_evaluated_not_promoted":
            raise ValueError("promotion gate decision must not promote")
        if decision.get("promotion_scope") != "human_governed_review_path_only":
            raise ValueError("promotion gate scope invalid")
        if decision.get("human_approval_required") is not True:
            raise ValueError("promotion gate must require human approval")
        if decision.get("human_approval_present") is not False:
            raise ValueError("promotion gate cannot infer human approval")
        if decision.get("promotion_allowed") is not False:
            raise ValueError("promotion gate cannot allow promotion")
        if decision.get("promotion_applied") is not False:
            raise ValueError("promotion gate cannot apply promotion")
        if decision.get("promotion_applied_at") is not None:
            raise ValueError("promotion gate applied_at must be empty")
        if decision.get("promotion_review_ready") is True:
            review_ready_count += 1
            if decision.get("quantum_dependency_satisfied") is not True:
                raise ValueError("promotion gate review-ready without quantum")
            if decision.get("oracle_contract_accepted") is not True:
                raise ValueError("promotion gate review-ready without oracle contract")
            if decision.get("optimized_for_quantum_oracle") is not True:
                raise ValueError("promotion gate review-ready without quantum optimization")
        if decision.get("quantum_dependency_satisfied") is True:
            quantum_count += 1
        if decision.get("oracle_contract_accepted") is True:
            oracle_count += 1
        hold_reasons = [
            str(reason)
            for reason in _as_list(decision.get("promotion_hold_reasons"))
            if str(reason)
        ]
        criteria = _as_dict(decision.get("promotion_gate_criteria"))
        if "upstream_meta_review_hold_unresolved" in hold_reasons:
            upstream_unresolved_count += 1
        if "paper_outcome_feedback_missing" in hold_reasons:
            outcome_missing_count += 1
        if "explicit_human_promotion_approval_missing" in hold_reasons:
            human_missing_count += 1
        if decision.get("promotion_gate_passed") is True:
            passed_count += 1
            if not all(criteria.values()):
                raise ValueError("promotion gate passed with failed criterion")
            if decision.get("promotion_allowed") is not False:
                raise ValueError("promotion gate pass cannot create promotion authority")
        else:
            held_count += 1
            if not hold_reasons:
                raise ValueError("held promotion gate needs hold reasons")
        if criteria.get("explicit_human_approval_present") is not False:
            raise ValueError("promotion gate cannot infer approval criterion")
        if criteria.get("authority_boundary_clean") is not True:
            raise ValueError("promotion gate authority boundary criterion invalid")
        for field in PROMOTION_GATES_AUTHORITY_FALSE_FIELDS:
            if decision.get(field) is not False:
                raise ValueError(f"promotion gate decision authority leak: {field}")
    if _int(payload.get("promotion_gate_passed_count")) != passed_count:
        raise ValueError("promotion gate passed count mismatch")
    if _int(payload.get("promotion_gate_held_count")) != held_count:
        raise ValueError("promotion gate held count mismatch")
    if _int(payload.get("promotion_review_ready_count")) != review_ready_count:
        raise ValueError("promotion gate review-ready count mismatch")
    if _int(payload.get("quantum_dependency_satisfied_count")) != quantum_count:
        raise ValueError("promotion gate quantum dependency count mismatch")
    if _int(payload.get("oracle_contract_accepted_count")) != oracle_count:
        raise ValueError("promotion gate oracle count mismatch")
    if _int(payload.get("upstream_hold_unresolved_count")) != upstream_unresolved_count:
        raise ValueError("promotion gate upstream hold count mismatch")
    if _int(payload.get("outcome_feedback_missing_count")) != outcome_missing_count:
        raise ValueError("promotion gate outcome missing count mismatch")
    if _int(payload.get("human_approval_missing_count")) != human_missing_count:
        raise ValueError("promotion gate human missing count mismatch")
    if ready and passed_count != 0:
        raise ValueError("promotion gates cannot pass without explicit approval")


def write_promotion_gates(
    payload: dict[str, Any],
    settings: Settings | None = None,
) -> dict[str, Any]:
    validate_promotion_gates(payload)
    output_path, history_path, event_path = promotion_gates_paths(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    event = {
        "schema_version": PROMOTION_GATES_SCHEMA_VERSION,
        "event_type": PROMOTION_GATES_EVENT_TYPE,
        "component": PROMOTION_GATES_COMPONENT,
        "created_at": payload.get("generated_at") or _now(),
        "status": payload.get("status"),
        "promotion_gate_decision_count": payload.get("promotion_gate_decision_count"),
        "promotion_gate_passed_count": payload.get("promotion_gate_passed_count"),
        "promotion_gate_held_count": payload.get("promotion_gate_held_count"),
        "promotion_review_ready_count": payload.get("promotion_review_ready_count"),
        "promotion_applied_count": payload.get("promotion_applied_count"),
        "human_approval_present_count": payload.get("human_approval_present_count"),
        "quantum_dependency_satisfied_count": payload.get(
            "quantum_dependency_satisfied_count"
        ),
        "oracle_contract_accepted_count": payload.get("oracle_contract_accepted_count"),
        "authority_leak_count": sum(
            1
            for field in PROMOTION_GATES_AUTHORITY_FALSE_FIELDS
            if payload.get(field) is not False
        ),
        "public_safe": True,
        "boundary": PROMOTION_GATES_BOUNDARY,
    }
    with event_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return {
        "output_path": str(output_path),
        "history_path": str(history_path),
        "event_log_path": str(event_path),
    }
