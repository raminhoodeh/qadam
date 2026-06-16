"""Read-only self-improvement proposals for Qadam.

Stage 4E converts Qadam's quantum meta-review into explicit proposals for how
the research loop should improve itself. It is deliberately non-executing: it
can document recommended improvements, but it cannot edit code, mutate prompts,
apply strategy weights, change order sizing, call providers, send Telegram
messages, or submit paper trades.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.quantum_meta_review import (
    QUANTUM_META_REVIEW_AUTHORITY_FALSE_FIELDS,
    validate_quantum_meta_review,
)
from orchestrator.strategy_weight_updates import (
    STRATEGY_FAMILIES,
    validate_strategy_weight_updates,
)


SELF_IMPROVEMENT_PROPOSALS_SCHEMA_VERSION = 1
SELF_IMPROVEMENT_PROPOSALS_RUNTIME_ARTIFACT = "self_improvement_proposals.json"
SELF_IMPROVEMENT_PROPOSALS_HISTORY = "self_improvement_proposals_history.jsonl"
SELF_IMPROVEMENT_PROPOSALS_EVENT_LOG = "self_improvement_proposals_events.jsonl"
SELF_IMPROVEMENT_PROPOSALS_EVENT_TYPE = "self_improvement_proposals_recorded"
SELF_IMPROVEMENT_PROPOSALS_COMPONENT = "self_improvement_proposals"

SELF_IMPROVEMENT_PROPOSALS_AUTHORITY_FALSE_FIELDS: tuple[str, ...] = tuple(
    dict.fromkeys(
        (
            *QUANTUM_META_REVIEW_AUTHORITY_FALSE_FIELDS,
            "self_improvement_apply_allowed",
            "self_improvement_applied",
            "repo_write_allowed",
            "code_change_allowed",
            "prompt_mutation_allowed",
            "system_prompt_mutation_allowed",
            "model_weight_mutation_allowed",
            "strategy_weight_application_allowed",
            "active_strategy_mutation_allowed",
            "portfolio_rebalance_allowed",
            "order_sizing_allowed",
            "risk_approval_allowed",
            "paper_order_submission_allowed",
            "broker_write_allowed",
            "telegram_live_send_allowed",
            "live_notification_send_allowed",
            "quantum_provider_call_allowed",
            "quantum_hardware_submission_allowed",
            "auto_merge_allowed",
            "proof_credit_grant_allowed",
        )
    )
)

SELF_IMPROVEMENT_PROPOSALS_STATUSES = {
    "self_improvement_proposals_ready",
    "self_improvement_proposals_blocked_pending_quantum_meta_review",
}

SELF_IMPROVEMENT_PROPOSALS_BOUNDARY = (
    "Self-Improvement Proposals is a read-only self-improvement proposal "
    "ledger. It can recommend how Qadam should improve its evidence, "
    "hypothesis lifecycle, quantum-reviewed pattern recognition, and outcome "
    "feedback loops, but it cannot edit code, mutate prompts, apply strategy "
    "weights, mutate active strategy, change order sizing, approve risk, "
    "submit paper orders, write brokers, send live Telegram messages, call "
    "quantum providers, submit hardware jobs, enable live capital, or grant "
    "proof credit."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def self_improvement_proposals_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / SELF_IMPROVEMENT_PROPOSALS_RUNTIME_ARTIFACT,
        runtime / SELF_IMPROVEMENT_PROPOSALS_HISTORY,
        runtime / SELF_IMPROVEMENT_PROPOSALS_EVENT_LOG,
    )


def read_self_improvement_proposals(settings: Settings | None = None) -> dict[str, Any]:
    output_path, _, _ = self_improvement_proposals_paths(settings)
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


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clip(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 6)


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


def _proposal_text(meta_record: dict[str, Any]) -> tuple[str, str, str, list[str]]:
    family_name = str(meta_record.get("strategy_family_name") or "This strategy family")
    hold_reasons = [
        str(reason)
        for reason in _as_list(meta_record.get("hold_reasons"))
        if str(reason)
    ]
    if meta_record.get("meta_review_passed") is True:
        return (
            "preserve_quantum_reviewed_edge_path_and_collect_outcome_feedback",
            "edge_learning_coherence",
            (
                f"Keep {family_name} under quantum-reviewed observation and "
                "link future paper outcomes, postmortems, and signal-integrity "
                "reviews back into the edge memory ledger before any strategy "
                "mutation is proposed."
            ),
            [
                "paper_outcome_feedback",
                "postmortem_alignment",
                "signal_integrity_review",
                "quantum_meta_review_regression_check",
            ],
        )
    if "hypothesis_lifecycle_thread_missing" in hold_reasons:
        return (
            "create_hypothesis_lifecycle_observation_target",
            "hypothesis_lifecycle_coverage",
            (
                f"Create a hypothesis lifecycle thread for {family_name} so "
                "the quantum-reviewed pattern has a durable observation path "
                "before Qadam considers any future strategy-weight change."
            ),
            [
                "hypothesis_thread_creation",
                "independent_source_corroboration",
                "edge_memory_linkage",
                "quantum_gate_recheck",
            ],
        )
    return (
        "reduce_ambiguity_before_strategy_mutation",
        "edge_ambiguity_reduction",
        (
            f"Hold {family_name} in observation and collect more source, price, "
            "and quantum-review evidence until the meta-review hold reasons are "
            "resolved."
        ),
        [
            "fresh_source_evidence",
            "price_response_follow_through",
            "ambiguity_score_reduction",
            "quantum_gate_recheck",
        ],
    )


def _proposal_record(
    *,
    family: dict[str, str],
    meta_record: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    proposal_kind, target_surface, proposed_action, evidence_to_collect = _proposal_text(
        meta_record
    )
    meta_review_passed = meta_record.get("meta_review_passed") is True
    hold_reasons = sorted(
        {
            str(reason)
            for reason in _as_list(meta_record.get("hold_reasons"))
            if str(reason)
        }
    )
    quantum_dependency_satisfied = meta_record.get("quantum_dependency_satisfied") is True
    oracle_contract_accepted = meta_record.get("oracle_contract_accepted") is True
    optimized_for_quantum_oracle = meta_record.get("optimized_for_quantum_oracle") is True
    proposal_ready_for_review = (
        quantum_dependency_satisfied
        and oracle_contract_accepted
        and optimized_for_quantum_oracle
    )
    proposal_id = "self-improvement-proposal:" + sha256(
        json.dumps(
            {
                "sleeve_key": family["sleeve_key"],
                "strategy_family_key": family["strategy_family_key"],
                "meta_review_id": meta_record.get("meta_review_id"),
                "proposal_kind": proposal_kind,
                "hold_reasons": hold_reasons,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:18]
    record = {
        "proposal_id": proposal_id,
        "status": "self_improvement_proposal_outcome_feedback_pending"
        if meta_review_passed
        else "self_improvement_proposal_hold_resolution_pending",
        "decision_status": "proposed_not_applied",
        "proposal_kind": proposal_kind,
        "proposal_scope": "research_process_improvement_only",
        "write_scope": "artifact_only",
        "target_surface": target_surface,
        "priority": "medium" if meta_review_passed else "high",
        "human_review_required": True,
        "proposal_ready_for_review": proposal_ready_for_review,
        "sleeve_key": family["sleeve_key"],
        "instrument_key": family["instrument_key"],
        "strategy_family_key": family["strategy_family_key"],
        "strategy_family_name": family["strategy_family_name"],
        "quantum_meta_review_id": meta_record.get("meta_review_id"),
        "quantum_required": True,
        "quantum_dependency_satisfied": quantum_dependency_satisfied,
        "quantum_gate_decision_status": meta_record.get("quantum_gate_decision_status"),
        "quantum_review_status": meta_record.get("quantum_review_status"),
        "quantum_backend": meta_record.get("quantum_backend"),
        "fire_opal_ibm_status": meta_record.get("fire_opal_ibm_status"),
        "oracle_contract_accepted": oracle_contract_accepted,
        "optimized_for_quantum_oracle": optimized_for_quantum_oracle,
        "meta_review_passed": meta_review_passed,
        "meta_review_score": _clip(_float(meta_record.get("meta_review_score"))),
        "meta_review_hold_reasons": hold_reasons,
        "hypothesis_lifecycle_linked": meta_record.get("hypothesis_lifecycle_linked")
        is True,
        "hypothesis_lifecycle_ids": sorted(
            str(item)
            for item in _as_list(meta_record.get("hypothesis_lifecycle_ids"))
            if str(item)
        ),
        "blocked_reasons_to_resolve": [] if meta_review_passed else hold_reasons,
        "proposed_action": proposed_action,
        "why_it_matters": (
            "Qadam is trying to improve its edge-finding process without "
            "changing trading behavior until the proposal is separately "
            "reviewed and approved."
        ),
        "evidence_to_collect": evidence_to_collect,
        "acceptance_criteria": [
            "linked evidence packet exists",
            "quantum meta-review remains available",
            "proposal remains read-only and non-executing",
            "paper outcomes or source follow-through can be reviewed later",
        ],
        "rejection_criteria": [
            "proposal would grant broker, order, provider, or code-write authority",
            "quantum dependency is missing or bypassed",
            "proposal changes active strategy weights without explicit approval",
        ],
        "apply_condition": (
            "A later explicit human-governance path must approve implementation "
            "after paper outcomes, Signal Integrity, Risk, and quantum review "
            "remain coherent."
        ),
        "rollback_condition": (
            "Withdraw if quantum dependency breaks, hold reasons worsen, source "
            "evidence weakens, or paper outcomes refute the pattern."
        ),
        "mutation_policy": {
            "can_edit_code": False,
            "can_mutate_prompts": False,
            "can_apply_strategy_weights": False,
            "can_mutate_active_strategy": False,
            "can_change_order_sizing": False,
            "can_submit_paper_orders": False,
            "can_call_brokers": False,
            "can_call_quantum_providers": False,
            "can_send_live_telegram": False,
        },
        "created_at": generated_at,
        "applied": False,
        "applied_at": None,
    }
    for field in SELF_IMPROVEMENT_PROPOSALS_AUTHORITY_FALSE_FIELDS:
        record[field] = False
    return record


def build_self_improvement_proposals(
    *,
    quantum_meta_review: dict[str, Any],
    strategy_weight_updates: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build Qadam's Stage 4E self-improvement proposal ledger."""

    generated_at = generated_at or _now()
    validate_quantum_meta_review(quantum_meta_review)
    validate_strategy_weight_updates(strategy_weight_updates)
    dependency_ready = (
        quantum_meta_review.get("status") == "quantum_meta_review_ready"
        and strategy_weight_updates.get("status") == "strategy_weight_updates_ready"
    )
    status = (
        "self_improvement_proposals_ready"
        if dependency_ready
        else "self_improvement_proposals_blocked_pending_quantum_meta_review"
    )
    meta_by_family = _records_by_family(_as_list(quantum_meta_review.get("meta_review_records")))
    proposals = [
        _proposal_record(
            family=family,
            meta_record=meta_by_family.get(family["strategy_family_key"], {}),
            generated_at=generated_at,
        )
        for family in STRATEGY_FAMILIES
        if status == "self_improvement_proposals_ready"
    ]
    hold_resolution_count = sum(
        1 for record in proposals if record["meta_review_passed"] is not True
    )
    passed_loop_count = len(proposals) - hold_resolution_count
    proposal_ready_count = sum(
        1 for record in proposals if record["proposal_ready_for_review"] is True
    )
    quantum_count = sum(
        1 for record in proposals if record["quantum_dependency_satisfied"] is True
    )
    oracle_count = sum(
        1 for record in proposals if record["oracle_contract_accepted"] is True
    )
    active_before_weights = dict(strategy_weight_updates.get("active_before_weights") or {})
    active_after_weights = dict(strategy_weight_updates.get("active_after_weights") or {})
    artifact = {
        "schema_version": SELF_IMPROVEMENT_PROPOSALS_SCHEMA_VERSION,
        "artifact_type": "self_improvement_proposals",
        "artifact_id": "self-improvement-proposals:latest",
        "stage": "Stage 4E - Self-Improvement Proposals",
        "generated_at": generated_at,
        "status": status,
        "public_safe": True,
        "purpose": (
            "Record how Qadam should improve its edge-learning process after "
            "quantum meta-review, while keeping every recommendation read-only "
            "until a later explicit approval path exists."
        ),
        "quantum_meta_review_status": quantum_meta_review.get("status"),
        "strategy_weight_updates_status": strategy_weight_updates.get("status"),
        "strategy_family_count": len(STRATEGY_FAMILIES),
        "self_improvement_proposal_count": len(proposals),
        "self_improvement_applied_count": 0,
        "self_improvement_ready_for_review_count": proposal_ready_count,
        "hold_resolution_proposal_count": hold_resolution_count,
        "passed_loop_proposal_count": passed_loop_count,
        "quantum_dependency_satisfied_count": quantum_count,
        "oracle_contract_accepted_count": oracle_count,
        "code_change_proposal_count": 0,
        "code_change_applied_count": 0,
        "prompt_mutation_proposal_count": 0,
        "prompt_mutation_applied_count": 0,
        "strategy_weight_application_count": 0,
        "active_strategy_mutation_count": 0,
        "portfolio_rebalance_count": 0,
        "paper_order_submission_count": 0,
        "broker_write_count": 0,
        "quantum_provider_call_count": 0,
        "telegram_live_send_count": 0,
        "proof_credit_grant_count": 0,
        "active_before_weights": active_before_weights,
        "active_after_weights": active_after_weights,
        "active_before_weight_sum": _weight_sum(active_before_weights),
        "active_after_weight_sum": _weight_sum(active_after_weights),
        "active_weights_unchanged": active_before_weights == active_after_weights,
        "loop_level_decision": {
            "status": "self_improvement_proposals_recorded"
            if dependency_ready
            else "self_improvement_proposals_blocked",
            "review_scope": "recursive_edge_learning_improvement_candidates",
            "recommendation_only": True,
            "proposal_records_created": len(proposals),
            "can_edit_code": False,
            "can_mutate_prompts": False,
            "can_apply_strategy_weights": False,
            "can_mutate_strategy": False,
            "can_change_order_sizing": False,
            "can_submit_paper_orders": False,
            "can_call_brokers": False,
            "can_call_quantum_providers": False,
            "can_send_live_telegram": False,
            "boundary": (
                "Self-improvement proposals are review records only. They do "
                "not implement themselves or create execution authority."
            ),
        },
        "self_improvement_contract": {
            "status": "proposal_ledger_active" if dependency_ready else "blocked",
            "uses_quantum_meta_review": True,
            "uses_strategy_weight_updates": True,
            "proposal_only": True,
            "recommendation_only": True,
            "active_weights_unchanged": active_before_weights == active_after_weights,
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
            "boundary": (
                "Stage 4E can only write a runtime proposal artifact. Any "
                "actual implementation must be separately requested, reviewed, "
                "tested, committed, and deployed."
            ),
        },
        "self_improvement_proposals": proposals,
        "blocked_reason": None
        if status == "self_improvement_proposals_ready"
        else "quantum_meta_review_or_strategy_weight_updates_not_ready",
        "documentation_routes": {
            "runtime_artifact": f"data/runtime/{SELF_IMPROVEMENT_PROPOSALS_RUNTIME_ARTIFACT}",
            "history": f"data/runtime/{SELF_IMPROVEMENT_PROPOSALS_HISTORY}",
            "event_log": f"data/runtime/{SELF_IMPROVEMENT_PROPOSALS_EVENT_LOG}",
            "source_quantum_meta_review": "data/runtime/quantum_meta_review.json",
            "source_strategy_weight_updates": "data/runtime/strategy_weight_updates.json",
        },
        "boundary": SELF_IMPROVEMENT_PROPOSALS_BOUNDARY,
    }
    for field in SELF_IMPROVEMENT_PROPOSALS_AUTHORITY_FALSE_FIELDS:
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


def validate_self_improvement_proposals(payload: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "stage",
        "generated_at",
        "status",
        "public_safe",
        "purpose",
        "quantum_meta_review_status",
        "strategy_weight_updates_status",
        "strategy_family_count",
        "self_improvement_proposal_count",
        "self_improvement_applied_count",
        "self_improvement_ready_for_review_count",
        "hold_resolution_proposal_count",
        "passed_loop_proposal_count",
        "quantum_dependency_satisfied_count",
        "oracle_contract_accepted_count",
        "code_change_proposal_count",
        "code_change_applied_count",
        "prompt_mutation_proposal_count",
        "prompt_mutation_applied_count",
        "strategy_weight_application_count",
        "active_strategy_mutation_count",
        "portfolio_rebalance_count",
        "paper_order_submission_count",
        "broker_write_count",
        "quantum_provider_call_count",
        "telegram_live_send_count",
        "proof_credit_grant_count",
        "active_before_weights",
        "active_after_weights",
        "active_before_weight_sum",
        "active_after_weight_sum",
        "active_weights_unchanged",
        "loop_level_decision",
        "self_improvement_contract",
        "self_improvement_proposals",
        "blocked_reason",
        "documentation_routes",
        "boundary",
        *SELF_IMPROVEMENT_PROPOSALS_AUTHORITY_FALSE_FIELDS,
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"self-improvement proposals missing fields: {missing}")
    if payload.get("schema_version") != SELF_IMPROVEMENT_PROPOSALS_SCHEMA_VERSION:
        raise ValueError("self-improvement proposals schema mismatch")
    if payload.get("artifact_type") != "self_improvement_proposals":
        raise ValueError("self-improvement proposals artifact type mismatch")
    if payload.get("status") not in SELF_IMPROVEMENT_PROPOSALS_STATUSES:
        raise ValueError("self-improvement proposals status invalid")
    if payload.get("public_safe") is not True:
        raise ValueError("self-improvement proposals must be public-safe")
    if "read-only self-improvement proposal ledger" not in str(payload.get("boundary", "")):
        raise ValueError("self-improvement proposals boundary weak")
    for field in SELF_IMPROVEMENT_PROPOSALS_AUTHORITY_FALSE_FIELDS:
        if payload.get(field) is not False:
            raise ValueError(f"self-improvement proposals authority leak: {field}")
    active_before = _validate_weights("active_before_weights", payload.get("active_before_weights"))
    active_after = _validate_weights("active_after_weights", payload.get("active_after_weights"))
    if active_before != active_after:
        raise ValueError("self-improvement proposals active weights mutated")
    if payload.get("active_weights_unchanged") is not True:
        raise ValueError("self-improvement proposals active weights changed")
    if payload.get("active_before_weight_sum") != _weight_sum(active_before):
        raise ValueError("self-improvement proposals active before sum mismatch")
    if payload.get("active_after_weight_sum") != _weight_sum(active_after):
        raise ValueError("self-improvement proposals active after sum mismatch")
    if _int(payload.get("strategy_family_count")) != len(STRATEGY_FAMILIES):
        raise ValueError("self-improvement proposals strategy family count mismatch")
    records = payload.get("self_improvement_proposals")
    if not isinstance(records, list):
        raise ValueError("self-improvement proposals records must be a list")
    if _int(payload.get("self_improvement_proposal_count")) != len(records):
        raise ValueError("self-improvement proposals count mismatch")
    zero_count_fields = (
        "self_improvement_applied_count",
        "code_change_proposal_count",
        "code_change_applied_count",
        "prompt_mutation_proposal_count",
        "prompt_mutation_applied_count",
        "strategy_weight_application_count",
        "active_strategy_mutation_count",
        "portfolio_rebalance_count",
        "paper_order_submission_count",
        "broker_write_count",
        "quantum_provider_call_count",
        "telegram_live_send_count",
        "proof_credit_grant_count",
    )
    for field in zero_count_fields:
        if _int(payload.get(field)) != 0:
            raise ValueError(f"self-improvement proposals count must stay zero: {field}")
    loop = _as_dict(payload.get("loop_level_decision"))
    contract = _as_dict(payload.get("self_improvement_contract"))
    for field in (
        "can_edit_code",
        "can_mutate_prompts",
        "can_apply_strategy_weights",
        "can_mutate_strategy",
        "can_change_order_sizing",
        "can_submit_paper_orders",
        "can_call_brokers",
        "can_call_quantum_providers",
        "can_send_live_telegram",
    ):
        if loop.get(field) is not False:
            raise ValueError(f"self-improvement proposals loop authority leak: {field}")
    for field in (
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
    ):
        if contract.get(field) is not False:
            raise ValueError(f"self-improvement proposals contract authority leak: {field}")
    if loop.get("recommendation_only") is not True:
        raise ValueError("self-improvement proposals loop must be recommendation-only")
    if contract.get("recommendation_only") is not True:
        raise ValueError("self-improvement proposals contract must be recommendation-only")
    ready = payload.get("status") == "self_improvement_proposals_ready"
    if ready:
        if payload.get("quantum_meta_review_status") != "quantum_meta_review_ready":
            raise ValueError("ready self-improvement proposals need quantum meta-review")
        if payload.get("strategy_weight_updates_status") != "strategy_weight_updates_ready":
            raise ValueError("ready self-improvement proposals need strategy weight updates")
        if payload.get("blocked_reason") is not None:
            raise ValueError("ready self-improvement proposals cannot be blocked")
        if len(records) != len(STRATEGY_FAMILIES):
            raise ValueError("ready self-improvement proposals must cover all families")
        if loop.get("status") != "self_improvement_proposals_recorded":
            raise ValueError("ready self-improvement proposals loop invalid")
    else:
        if payload.get("blocked_reason") != "quantum_meta_review_or_strategy_weight_updates_not_ready":
            raise ValueError("blocked self-improvement proposals need blocked reason")
        if records:
            raise ValueError("blocked self-improvement proposals cannot emit records")
        if loop.get("status") != "self_improvement_proposals_blocked":
            raise ValueError("blocked self-improvement proposals loop invalid")
    seen_families: set[str] = set()
    ready_count = 0
    hold_count = 0
    pass_count = 0
    quantum_count = 0
    oracle_count = 0
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("self-improvement proposal record must be a dict")
        family_key = str(record.get("strategy_family_key") or "")
        if family_key in seen_families:
            raise ValueError("duplicate self-improvement proposal family")
        seen_families.add(family_key)
        if family_key not in active_before:
            raise ValueError("self-improvement proposal family unknown")
        if record.get("decision_status") != "proposed_not_applied":
            raise ValueError("self-improvement proposal decision must not apply")
        if record.get("proposal_scope") != "research_process_improvement_only":
            raise ValueError("self-improvement proposal scope invalid")
        if record.get("write_scope") != "artifact_only":
            raise ValueError("self-improvement proposal write scope invalid")
        if record.get("human_review_required") is not True:
            raise ValueError("self-improvement proposal needs human review")
        if record.get("quantum_required") is not True:
            raise ValueError("self-improvement proposal must require quantum")
        if record.get("applied") is not False:
            raise ValueError("self-improvement proposal cannot be applied")
        if record.get("applied_at") is not None:
            raise ValueError("self-improvement proposal applied_at must be empty")
        if record.get("proposal_ready_for_review") is True:
            ready_count += 1
            if record.get("quantum_dependency_satisfied") is not True:
                raise ValueError("self-improvement proposal ready without quantum")
            if record.get("oracle_contract_accepted") is not True:
                raise ValueError("self-improvement proposal ready without oracle contract")
            if record.get("optimized_for_quantum_oracle") is not True:
                raise ValueError("self-improvement proposal ready without quantum optimization")
        if record.get("quantum_dependency_satisfied") is True:
            quantum_count += 1
        if record.get("oracle_contract_accepted") is True:
            oracle_count += 1
        if record.get("meta_review_passed") is True:
            pass_count += 1
            if record.get("proposal_kind") != (
                "preserve_quantum_reviewed_edge_path_and_collect_outcome_feedback"
            ):
                raise ValueError("passed self-improvement proposal kind invalid")
            if record.get("blocked_reasons_to_resolve") != []:
                raise ValueError("passed self-improvement proposal cannot resolve holds")
        else:
            hold_count += 1
            if record.get("proposal_kind") not in {
                "create_hypothesis_lifecycle_observation_target",
                "reduce_ambiguity_before_strategy_mutation",
            }:
                raise ValueError("held self-improvement proposal kind invalid")
            if not record.get("blocked_reasons_to_resolve"):
                raise ValueError("held self-improvement proposal needs blocked reasons")
        mutation_policy = _as_dict(record.get("mutation_policy"))
        for field in (
            "can_edit_code",
            "can_mutate_prompts",
            "can_apply_strategy_weights",
            "can_mutate_active_strategy",
            "can_change_order_sizing",
            "can_submit_paper_orders",
            "can_call_brokers",
            "can_call_quantum_providers",
            "can_send_live_telegram",
        ):
            if mutation_policy.get(field) is not False:
                raise ValueError(
                    f"self-improvement proposal mutation policy authority leak: {field}"
                )
        for field in SELF_IMPROVEMENT_PROPOSALS_AUTHORITY_FALSE_FIELDS:
            if record.get(field) is not False:
                raise ValueError(f"self-improvement proposal record authority leak: {field}")
    if _int(payload.get("self_improvement_ready_for_review_count")) != ready_count:
        raise ValueError("self-improvement ready count mismatch")
    if _int(payload.get("hold_resolution_proposal_count")) != hold_count:
        raise ValueError("self-improvement hold proposal count mismatch")
    if _int(payload.get("passed_loop_proposal_count")) != pass_count:
        raise ValueError("self-improvement passed proposal count mismatch")
    if _int(payload.get("quantum_dependency_satisfied_count")) != quantum_count:
        raise ValueError("self-improvement quantum dependency count mismatch")
    if _int(payload.get("oracle_contract_accepted_count")) != oracle_count:
        raise ValueError("self-improvement oracle contract count mismatch")
    if ready and ready_count != len(STRATEGY_FAMILIES):
        raise ValueError("ready self-improvement proposals must be quantum-reviewable")


def write_self_improvement_proposals(
    payload: dict[str, Any],
    settings: Settings | None = None,
) -> dict[str, Any]:
    validate_self_improvement_proposals(payload)
    output_path, history_path, event_path = self_improvement_proposals_paths(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    event = {
        "schema_version": SELF_IMPROVEMENT_PROPOSALS_SCHEMA_VERSION,
        "event_type": SELF_IMPROVEMENT_PROPOSALS_EVENT_TYPE,
        "component": SELF_IMPROVEMENT_PROPOSALS_COMPONENT,
        "created_at": payload.get("generated_at") or _now(),
        "status": payload.get("status"),
        "self_improvement_proposal_count": payload.get("self_improvement_proposal_count"),
        "self_improvement_applied_count": payload.get("self_improvement_applied_count"),
        "hold_resolution_proposal_count": payload.get("hold_resolution_proposal_count"),
        "passed_loop_proposal_count": payload.get("passed_loop_proposal_count"),
        "quantum_dependency_satisfied_count": payload.get(
            "quantum_dependency_satisfied_count"
        ),
        "oracle_contract_accepted_count": payload.get("oracle_contract_accepted_count"),
        "code_change_applied_count": payload.get("code_change_applied_count"),
        "strategy_weight_application_count": payload.get(
            "strategy_weight_application_count"
        ),
        "active_strategy_mutation_count": payload.get("active_strategy_mutation_count"),
        "authority_leak_count": sum(
            1
            for field in SELF_IMPROVEMENT_PROPOSALS_AUTHORITY_FALSE_FIELDS
            if payload.get(field) is not False
        ),
        "public_safe": True,
        "boundary": SELF_IMPROVEMENT_PROPOSALS_BOUNDARY,
    }
    with event_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return {
        "output_path": str(output_path),
        "history_path": str(history_path),
        "event_log_path": str(event_path),
    }
