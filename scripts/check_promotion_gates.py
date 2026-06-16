#!/usr/bin/env python3
"""Validate and write Qadam's Stage 4F Promotion Gates."""

from __future__ import annotations

from copy import deepcopy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.cockpit_status import build_cockpit_status  # noqa: E402
from orchestrator.config import Settings  # noqa: E402
from orchestrator.promotion_gates import (  # noqa: E402
    PROMOTION_GATES_AUTHORITY_FALSE_FIELDS,
    build_promotion_gates,
    validate_promotion_gates,
    write_promotion_gates,
)


REPORT_PATH = ROOT / "data/runtime/promotion_gates_check.json"


def _blocked_self_improvement_proposals(
    self_improvement_proposals: dict[str, object],
) -> dict[str, object]:
    blocked = deepcopy(self_improvement_proposals)
    blocked["status"] = "self_improvement_proposals_blocked_pending_quantum_meta_review"
    blocked["quantum_meta_review_status"] = (
        "quantum_meta_review_blocked_pending_strategy_weight_updates"
    )
    blocked["self_improvement_proposal_count"] = 0
    blocked["self_improvement_ready_for_review_count"] = 0
    blocked["hold_resolution_proposal_count"] = 0
    blocked["passed_loop_proposal_count"] = 0
    blocked["quantum_dependency_satisfied_count"] = 0
    blocked["oracle_contract_accepted_count"] = 0
    blocked["self_improvement_proposals"] = []
    blocked["blocked_reason"] = "quantum_meta_review_or_strategy_weight_updates_not_ready"
    loop = dict(blocked.get("loop_level_decision") or {})
    loop["status"] = "self_improvement_proposals_blocked"
    loop["recommendation_only"] = True
    loop["proposal_records_created"] = 0
    loop["can_edit_code"] = False
    loop["can_mutate_prompts"] = False
    loop["can_apply_strategy_weights"] = False
    loop["can_mutate_strategy"] = False
    loop["can_change_order_sizing"] = False
    loop["can_submit_paper_orders"] = False
    loop["can_call_brokers"] = False
    loop["can_call_quantum_providers"] = False
    loop["can_send_live_telegram"] = False
    blocked["loop_level_decision"] = loop
    contract = dict(blocked.get("self_improvement_contract") or {})
    contract["status"] = "blocked"
    contract["recommendation_only"] = True
    contract["repo_write_allowed"] = False
    contract["code_change_allowed"] = False
    contract["prompt_mutation_allowed"] = False
    contract["applies_weight_updates"] = False
    contract["mutates_active_strategy"] = False
    contract["changes_order_sizing"] = False
    contract["paper_order_allowed"] = False
    contract["broker_write_allowed"] = False
    contract["quantum_provider_call_allowed"] = False
    contract["telegram_live_send_allowed"] = False
    blocked["self_improvement_contract"] = contract
    return blocked


def _probe_rejected(payload: dict[str, object]) -> bool:
    try:
        validate_promotion_gates(payload)
    except ValueError:
        return True
    return False


def main() -> None:
    settings = Settings.from_env()
    cockpit_status = build_cockpit_status(settings)
    record = build_promotion_gates(
        self_improvement_proposals=cockpit_status["self_improvement_proposals"],
    )
    validate_promotion_gates(record)
    paths = write_promotion_gates(record, settings=settings)

    errors: list[str] = []
    if record["status"] != "promotion_gates_ready":
        errors.append(f"promotion_gates_not_ready={record['status']}")
    if record["promotion_gate_decision_count"] != 5:
        errors.append("promotion_gate_decision_count_not_5")
    if record["promotion_review_ready_count"] != 5:
        errors.append("promotion_review_ready_count_not_5")
    if record["promotion_gate_passed_count"] != 0:
        errors.append("promotion_gate_passed_count_nonzero")
    if record["promotion_gate_held_count"] != 5:
        errors.append("promotion_gate_held_count_not_5")
    if record["promotion_allowed_count"] != 0:
        errors.append("promotion_allowed_count_nonzero")
    if record["promotion_applied_count"] != 0:
        errors.append("promotion_applied_count_nonzero")
    if record["human_approval_present_count"] != 0:
        errors.append("human_approval_present_count_nonzero")
    if record["human_approval_missing_count"] != 5:
        errors.append("human_approval_missing_count_not_5")
    if record["quantum_dependency_satisfied_count"] != 5:
        errors.append("quantum_dependency_satisfied_count_not_5")
    if record["oracle_contract_accepted_count"] != 5:
        errors.append("oracle_contract_accepted_count_not_5")
    if record["upstream_hold_unresolved_count"] < 1:
        errors.append("upstream_hold_unresolved_count_below_1")
    if record["outcome_feedback_missing_count"] < 1:
        errors.append("outcome_feedback_missing_count_below_1")
    if record["implementation_ticket_created_count"] != 0:
        errors.append("implementation_ticket_created_count_nonzero")
    if record["code_change_applied_count"] != 0:
        errors.append("code_change_applied_count_nonzero")
    if record["active_strategy_mutation_count"] != 0:
        errors.append("active_strategy_mutation_count_nonzero")
    if record["strategy_weight_application_count"] != 0:
        errors.append("strategy_weight_application_count_nonzero")
    if record["paper_order_submission_count"] != 0:
        errors.append("paper_order_submission_count_nonzero")
    if record["broker_write_count"] != 0:
        errors.append("broker_write_count_nonzero")
    if record["active_before_weights"] != record["active_after_weights"]:
        errors.append("active_strategy_weights_changed")
    loop = record["loop_level_decision"]
    if loop["can_promote_proposals"] is not False:
        errors.append("loop_can_promote_proposals")
    if loop["can_edit_code"] is not False:
        errors.append("loop_can_edit_code")
    if loop["can_submit_paper_orders"] is not False:
        errors.append("loop_can_submit_paper_orders")
    authority_leaks = [
        field
        for field in PROMOTION_GATES_AUTHORITY_FALSE_FIELDS
        if record.get(field) is not False
    ]
    if authority_leaks:
        errors.append("authority_leaks=" + ",".join(authority_leaks))
    decision_authority_leaks = [
        item.get("promotion_gate_id", item.get("strategy_family_key", "unknown"))
        for item in record["promotion_gate_decisions"]
        if any(
            item.get(field) is not False
            for field in PROMOTION_GATES_AUTHORITY_FALSE_FIELDS
        )
    ]
    if decision_authority_leaks:
        errors.append(
            "decision_authority_leaks=" + ",".join(map(str, decision_authority_leaks))
        )

    blocked_probe = build_promotion_gates(
        self_improvement_proposals=_blocked_self_improvement_proposals(
            cockpit_status["self_improvement_proposals"]
        ),
    )
    validate_promotion_gates(blocked_probe)
    fail_closed_probe_rejected = (
        blocked_probe["status"]
        == "promotion_gates_blocked_pending_self_improvement_proposals"
        and blocked_probe["promotion_gate_decision_count"] == 0
        and blocked_probe["promotion_gate_decisions"] == []
    )
    if not fail_closed_probe_rejected:
        errors.append("fail_closed_probe_not_rejected")

    authority_probe = deepcopy(record)
    authority_probe["promotion_gate_decisions"][0]["broker_write_allowed"] = True
    authority_probe_rejected = _probe_rejected(authority_probe)
    if not authority_probe_rejected:
        errors.append("authority_probe_not_rejected")

    applied_probe = deepcopy(record)
    applied_probe["promotion_applied_count"] = 1
    applied_probe["promotion_gate_decisions"][0]["promotion_applied"] = True
    applied_probe["promotion_gate_decisions"][0]["promotion_applied_at"] = record[
        "generated_at"
    ]
    applied_probe_rejected = _probe_rejected(applied_probe)
    if not applied_probe_rejected:
        errors.append("applied_probe_not_rejected")

    code_mutation_probe = deepcopy(record)
    code_mutation_probe["repo_write_allowed"] = True
    code_mutation_probe["promotion_gate_decisions"][0]["code_change_allowed"] = True
    code_mutation_probe_rejected = _probe_rejected(code_mutation_probe)
    if not code_mutation_probe_rejected:
        errors.append("code_mutation_probe_not_rejected")

    promotion_bypass_probe = deepcopy(record)
    promotion_bypass_probe["promotion_gate_passed_count"] = 1
    promotion_bypass_probe["promotion_gate_held_count"] = 4
    promotion_bypass_probe["promotion_gate_decisions"][0]["promotion_gate_passed"] = True
    promotion_bypass_probe["promotion_gate_decisions"][0]["promotion_allowed"] = True
    promotion_bypass_probe_rejected = _probe_rejected(promotion_bypass_probe)
    if not promotion_bypass_probe_rejected:
        errors.append("promotion_bypass_probe_not_rejected")

    quantum_bypass_probe = deepcopy(record)
    quantum_bypass_probe["promotion_gate_decisions"][0][
        "quantum_dependency_satisfied"
    ] = False
    quantum_bypass_probe["promotion_gate_decisions"][0]["promotion_review_ready"] = True
    quantum_bypass_probe_rejected = _probe_rejected(quantum_bypass_probe)
    if not quantum_bypass_probe_rejected:
        errors.append("quantum_bypass_probe_not_rejected")

    report = {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "record_status": record["status"],
        "self_improvement_proposals_status": record[
            "self_improvement_proposals_status"
        ],
        "promotion_gate_decision_count": record["promotion_gate_decision_count"],
        "promotion_gate_passed_count": record["promotion_gate_passed_count"],
        "promotion_gate_held_count": record["promotion_gate_held_count"],
        "promotion_review_ready_count": record["promotion_review_ready_count"],
        "promotion_allowed_count": record["promotion_allowed_count"],
        "promotion_applied_count": record["promotion_applied_count"],
        "human_approval_present_count": record["human_approval_present_count"],
        "human_approval_missing_count": record["human_approval_missing_count"],
        "quantum_dependency_satisfied_count": record["quantum_dependency_satisfied_count"],
        "oracle_contract_accepted_count": record["oracle_contract_accepted_count"],
        "upstream_hold_unresolved_count": record["upstream_hold_unresolved_count"],
        "outcome_feedback_missing_count": record["outcome_feedback_missing_count"],
        "implementation_ticket_created_count": record[
            "implementation_ticket_created_count"
        ],
        "code_change_applied_count": record["code_change_applied_count"],
        "active_strategy_mutation_count": record["active_strategy_mutation_count"],
        "strategy_weight_application_count": record["strategy_weight_application_count"],
        "paper_order_submission_count": record["paper_order_submission_count"],
        "broker_write_count": record["broker_write_count"],
        "fail_closed_probe_rejected": fail_closed_probe_rejected,
        "authority_probe_rejected": authority_probe_rejected,
        "applied_probe_rejected": applied_probe_rejected,
        "code_mutation_probe_rejected": code_mutation_probe_rejected,
        "promotion_bypass_probe_rejected": promotion_bypass_probe_rejected,
        "quantum_bypass_probe_rejected": quantum_bypass_probe_rejected,
        "paths": paths,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if errors:
        raise SystemExit("; ".join(errors))

    print("promotion_gates_check=ok")
    print(f"promotion_gates_status={record['status']}")
    print(
        "promotion_gates_self_improvement_proposals_status="
        f"{record['self_improvement_proposals_status']}"
    )
    print(f"promotion_gate_decision_count={record['promotion_gate_decision_count']}")
    print(f"promotion_review_ready_count={record['promotion_review_ready_count']}")
    print(f"promotion_gate_passed_count={record['promotion_gate_passed_count']}")
    print(f"promotion_gate_held_count={record['promotion_gate_held_count']}")
    print(f"promotion_allowed_count={record['promotion_allowed_count']}")
    print(f"promotion_applied_count={record['promotion_applied_count']}")
    print(f"promotion_human_approval_present_count={record['human_approval_present_count']}")
    print(f"promotion_human_approval_missing_count={record['human_approval_missing_count']}")
    print(
        "promotion_quantum_dependency_satisfied_count="
        f"{record['quantum_dependency_satisfied_count']}"
    )
    print(
        "promotion_oracle_contract_accepted_count="
        f"{record['oracle_contract_accepted_count']}"
    )
    print(f"promotion_upstream_hold_unresolved_count={record['upstream_hold_unresolved_count']}")
    print(f"promotion_outcome_feedback_missing_count={record['outcome_feedback_missing_count']}")
    print(
        "promotion_implementation_ticket_created_count="
        f"{record['implementation_ticket_created_count']}"
    )
    print(f"promotion_code_change_applied_count={record['code_change_applied_count']}")
    print(
        "promotion_active_strategy_mutation_count="
        f"{record['active_strategy_mutation_count']}"
    )
    print(
        "promotion_strategy_weight_application_count="
        f"{record['strategy_weight_application_count']}"
    )
    print(f"promotion_fail_closed_probe_rejected={fail_closed_probe_rejected}")
    print(f"promotion_authority_probe_rejected={authority_probe_rejected}")
    print(f"promotion_applied_probe_rejected={applied_probe_rejected}")
    print(f"promotion_code_mutation_probe_rejected={code_mutation_probe_rejected}")
    print(f"promotion_bypass_probe_rejected={promotion_bypass_probe_rejected}")
    print(f"promotion_quantum_bypass_probe_rejected={quantum_bypass_probe_rejected}")
    print(f"promotion_gates_artifact_path={paths['output_path']}")


if __name__ == "__main__":
    main()
