#!/usr/bin/env python3
"""Validate and write Qadam's Stage 4E Self-Improvement Proposals."""

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
from orchestrator.self_improvement_proposals import (  # noqa: E402
    SELF_IMPROVEMENT_PROPOSALS_AUTHORITY_FALSE_FIELDS,
    build_self_improvement_proposals,
    validate_self_improvement_proposals,
    write_self_improvement_proposals,
)


REPORT_PATH = ROOT / "data/runtime/self_improvement_proposals_check.json"


def _blocked_quantum_meta_review(
    quantum_meta_review: dict[str, object],
) -> dict[str, object]:
    blocked = deepcopy(quantum_meta_review)
    blocked["status"] = "quantum_meta_review_blocked_pending_strategy_weight_updates"
    blocked["strategy_weight_updates_status"] = (
        "strategy_weight_updates_blocked_pending_hypothesis_lifecycle"
    )
    blocked["quantum_meta_review_count"] = 0
    blocked["quantum_meta_review_passed_count"] = 0
    blocked["quantum_meta_review_blocked_count"] = 0
    blocked["quantum_meta_review_hold_count"] = 0
    blocked["quantum_dependency_satisfied_count"] = 0
    blocked["oracle_contract_accepted_count"] = 0
    blocked["hypothesis_lifecycle_linked_count"] = 0
    blocked["meta_review_records"] = []
    blocked["blocked_reason"] = "strategy_weight_updates_or_quantum_dependencies_not_ready"
    loop = dict(blocked.get("loop_level_decision") or {})
    loop["status"] = "quantum_meta_review_blocked"
    loop["meta_review_passed"] = False
    loop["recommendation_only"] = True
    loop["can_update_strategy_weights"] = False
    loop["can_mutate_strategy"] = False
    loop["can_change_order_sizing"] = False
    loop["can_submit_paper_orders"] = False
    loop["can_call_brokers"] = False
    loop["can_call_quantum_providers"] = False
    loop["can_send_live_telegram"] = False
    blocked["loop_level_decision"] = loop
    contract = dict(blocked.get("recursive_improvement_contract") or {})
    contract["status"] = "blocked"
    contract["recommendation_only"] = True
    contract["holds_recorded"] = False
    contract["applies_weight_updates"] = False
    contract["mutates_active_strategy"] = False
    contract["changes_order_sizing"] = False
    contract["paper_order_allowed"] = False
    contract["broker_write_allowed"] = False
    contract["quantum_provider_call_allowed"] = False
    blocked["recursive_improvement_contract"] = contract
    return blocked


def _probe_rejected(payload: dict[str, object]) -> bool:
    try:
        validate_self_improvement_proposals(payload)
    except ValueError:
        return True
    return False


def main() -> None:
    settings = Settings.from_env()
    cockpit_status = build_cockpit_status(settings)
    record = build_self_improvement_proposals(
        quantum_meta_review=cockpit_status["quantum_meta_review"],
        strategy_weight_updates=cockpit_status["strategy_weight_updates"],
    )
    validate_self_improvement_proposals(record)
    paths = write_self_improvement_proposals(record, settings=settings)

    errors: list[str] = []
    if record["status"] != "self_improvement_proposals_ready":
        errors.append(f"self_improvement_proposals_not_ready={record['status']}")
    if record["self_improvement_proposal_count"] != 5:
        errors.append("self_improvement_proposal_count_not_5")
    if record["self_improvement_applied_count"] != 0:
        errors.append("self_improvement_applied_count_nonzero")
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
    if record["quantum_dependency_satisfied_count"] != 5:
        errors.append("quantum_dependency_satisfied_count_not_5")
    if record["oracle_contract_accepted_count"] != 5:
        errors.append("oracle_contract_accepted_count_not_5")
    if record["hold_resolution_proposal_count"] < 1:
        errors.append("hold_resolution_proposal_count_below_1")
    if record["passed_loop_proposal_count"] < 1:
        errors.append("passed_loop_proposal_count_below_1")
    if record["active_before_weights"] != record["active_after_weights"]:
        errors.append("active_strategy_weights_changed")
    loop = record["loop_level_decision"]
    if loop["can_submit_paper_orders"] is not False:
        errors.append("loop_can_submit_paper_orders")
    if loop["can_call_quantum_providers"] is not False:
        errors.append("loop_can_call_quantum_providers")
    if loop["can_edit_code"] is not False:
        errors.append("loop_can_edit_code")
    authority_leaks = [
        field
        for field in SELF_IMPROVEMENT_PROPOSALS_AUTHORITY_FALSE_FIELDS
        if record.get(field) is not False
    ]
    if authority_leaks:
        errors.append("authority_leaks=" + ",".join(authority_leaks))
    record_authority_leaks = [
        item.get("proposal_id", item.get("strategy_family_key", "unknown"))
        for item in record["self_improvement_proposals"]
        if any(
            item.get(field) is not False
            for field in SELF_IMPROVEMENT_PROPOSALS_AUTHORITY_FALSE_FIELDS
        )
    ]
    if record_authority_leaks:
        errors.append("record_authority_leaks=" + ",".join(map(str, record_authority_leaks)))

    blocked_probe = build_self_improvement_proposals(
        quantum_meta_review=_blocked_quantum_meta_review(cockpit_status["quantum_meta_review"]),
        strategy_weight_updates=cockpit_status["strategy_weight_updates"],
    )
    validate_self_improvement_proposals(blocked_probe)
    fail_closed_probe_rejected = (
        blocked_probe["status"]
        == "self_improvement_proposals_blocked_pending_quantum_meta_review"
        and blocked_probe["self_improvement_proposal_count"] == 0
        and blocked_probe["self_improvement_proposals"] == []
    )
    if not fail_closed_probe_rejected:
        errors.append("fail_closed_probe_not_rejected")

    authority_probe = deepcopy(record)
    authority_probe["self_improvement_proposals"][0]["broker_write_allowed"] = True
    authority_probe_rejected = _probe_rejected(authority_probe)
    if not authority_probe_rejected:
        errors.append("authority_probe_not_rejected")

    applied_probe = deepcopy(record)
    applied_probe["self_improvement_applied_count"] = 1
    applied_probe["self_improvement_proposals"][0]["applied"] = True
    applied_probe["self_improvement_proposals"][0]["applied_at"] = record["generated_at"]
    applied_probe_rejected = _probe_rejected(applied_probe)
    if not applied_probe_rejected:
        errors.append("applied_probe_not_rejected")

    code_mutation_probe = deepcopy(record)
    code_mutation_probe["repo_write_allowed"] = True
    code_mutation_probe["self_improvement_proposals"][0]["code_change_allowed"] = True
    code_mutation_probe_rejected = _probe_rejected(code_mutation_probe)
    if not code_mutation_probe_rejected:
        errors.append("code_mutation_probe_not_rejected")

    quantum_bypass_probe = deepcopy(record)
    quantum_bypass_probe["self_improvement_proposals"][0][
        "quantum_dependency_satisfied"
    ] = False
    quantum_bypass_probe["self_improvement_proposals"][0][
        "proposal_ready_for_review"
    ] = True
    quantum_bypass_probe_rejected = _probe_rejected(quantum_bypass_probe)
    if not quantum_bypass_probe_rejected:
        errors.append("quantum_bypass_probe_not_rejected")

    report = {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "record_status": record["status"],
        "quantum_meta_review_status": record["quantum_meta_review_status"],
        "strategy_weight_updates_status": record["strategy_weight_updates_status"],
        "self_improvement_proposal_count": record["self_improvement_proposal_count"],
        "self_improvement_applied_count": record["self_improvement_applied_count"],
        "self_improvement_ready_for_review_count": record[
            "self_improvement_ready_for_review_count"
        ],
        "hold_resolution_proposal_count": record["hold_resolution_proposal_count"],
        "passed_loop_proposal_count": record["passed_loop_proposal_count"],
        "quantum_dependency_satisfied_count": record["quantum_dependency_satisfied_count"],
        "oracle_contract_accepted_count": record["oracle_contract_accepted_count"],
        "code_change_applied_count": record["code_change_applied_count"],
        "active_strategy_mutation_count": record["active_strategy_mutation_count"],
        "strategy_weight_application_count": record["strategy_weight_application_count"],
        "paper_order_submission_count": record["paper_order_submission_count"],
        "broker_write_count": record["broker_write_count"],
        "fail_closed_probe_rejected": fail_closed_probe_rejected,
        "authority_probe_rejected": authority_probe_rejected,
        "applied_probe_rejected": applied_probe_rejected,
        "code_mutation_probe_rejected": code_mutation_probe_rejected,
        "quantum_bypass_probe_rejected": quantum_bypass_probe_rejected,
        "paths": paths,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if errors:
        raise SystemExit("; ".join(errors))

    print("self_improvement_proposals_check=ok")
    print(f"self_improvement_proposals_status={record['status']}")
    print(
        "self_improvement_proposals_quantum_meta_review_status="
        f"{record['quantum_meta_review_status']}"
    )
    print(
        "self_improvement_proposals_strategy_weight_updates_status="
        f"{record['strategy_weight_updates_status']}"
    )
    print(
        "self_improvement_proposal_count="
        f"{record['self_improvement_proposal_count']}"
    )
    print(
        "self_improvement_ready_for_review_count="
        f"{record['self_improvement_ready_for_review_count']}"
    )
    print(
        "self_improvement_hold_resolution_proposal_count="
        f"{record['hold_resolution_proposal_count']}"
    )
    print(
        "self_improvement_passed_loop_proposal_count="
        f"{record['passed_loop_proposal_count']}"
    )
    print(
        "self_improvement_quantum_dependency_satisfied_count="
        f"{record['quantum_dependency_satisfied_count']}"
    )
    print(
        "self_improvement_oracle_contract_accepted_count="
        f"{record['oracle_contract_accepted_count']}"
    )
    print(
        "self_improvement_applied_count="
        f"{record['self_improvement_applied_count']}"
    )
    print(f"self_improvement_code_change_applied_count={record['code_change_applied_count']}")
    print(
        "self_improvement_active_strategy_mutation_count="
        f"{record['active_strategy_mutation_count']}"
    )
    print(
        "self_improvement_strategy_weight_application_count="
        f"{record['strategy_weight_application_count']}"
    )
    print(f"self_improvement_fail_closed_probe_rejected={fail_closed_probe_rejected}")
    print(f"self_improvement_authority_probe_rejected={authority_probe_rejected}")
    print(f"self_improvement_applied_probe_rejected={applied_probe_rejected}")
    print(f"self_improvement_code_mutation_probe_rejected={code_mutation_probe_rejected}")
    print(f"self_improvement_quantum_bypass_probe_rejected={quantum_bypass_probe_rejected}")
    print(f"self_improvement_proposals_artifact_path={paths['output_path']}")


if __name__ == "__main__":
    main()
