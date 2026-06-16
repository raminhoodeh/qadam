#!/usr/bin/env python3
"""Validate and write Qadam's Stage 4D Quantum Meta-Review."""

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
from orchestrator.quantum_mandatory_review_gate import (  # noqa: E402
    build_quantum_mandatory_review_gate,
)
from orchestrator.quantum_meta_review import (  # noqa: E402
    QUANTUM_META_REVIEW_AUTHORITY_FALSE_FIELDS,
    build_quantum_meta_review,
    validate_quantum_meta_review,
    write_quantum_meta_review,
)


REPORT_PATH = ROOT / "data/runtime/quantum_meta_review_check.json"


def _blocked_strategy_weight_updates(
    strategy_weight_updates: dict[str, object],
) -> dict[str, object]:
    blocked = deepcopy(strategy_weight_updates)
    active_before = dict(blocked.get("active_before_weights") or {})
    zero_delta = {key: 0.0 for key in active_before}
    blocked["status"] = "strategy_weight_updates_blocked_pending_hypothesis_lifecycle"
    blocked["strategy_weight_update_proposal_count"] = 0
    blocked["strategy_weight_update_applied_count"] = 0
    blocked["active_strategy_weight_mutation_count"] = 0
    blocked["quantum_dependency_satisfied_count"] = 0
    blocked["hypothesis_lifecycle_linked_count"] = 0
    blocked["weight_update_records"] = []
    blocked["proposed_after_weights"] = active_before
    blocked["proposed_weight_delta"] = zero_delta
    blocked["applied_weight_delta"] = zero_delta
    blocked["active_after_weights"] = active_before
    blocked["active_after_weight_sum"] = blocked.get("active_before_weight_sum")
    blocked["proposed_after_weight_sum"] = blocked.get("active_before_weight_sum")
    blocked["proposed_weight_delta_total_abs"] = 0.0
    blocked["applied_weight_delta_total_abs"] = 0.0
    blocked["blocked_reason"] = "edge_memory_strategy_record_or_hypothesis_lifecycle_not_ready"
    contract = dict(blocked.get("recursive_improvement_contract") or {})
    contract["status"] = "blocked"
    contract["active_weights_unchanged"] = True
    contract["applies_weight_updates"] = False
    contract["mutates_active_strategy"] = False
    contract["changes_order_sizing"] = False
    contract["paper_order_allowed"] = False
    contract["broker_write_allowed"] = False
    blocked["recursive_improvement_contract"] = contract
    return blocked


def _probe_rejected(payload: dict[str, object]) -> bool:
    try:
        validate_quantum_meta_review(payload)
    except ValueError:
        return True
    return False


def main() -> None:
    settings = Settings.from_env()
    cockpit_status = build_cockpit_status(settings)
    quantum_gate = build_quantum_mandatory_review_gate(
        edge_ledger=cockpit_status["edge_pattern_ledger"]
    )
    record = build_quantum_meta_review(
        quantum_gate=quantum_gate,
        pattern_recognition_engine=cockpit_status["pattern_recognition_engine"],
        edge_memory_ledger=cockpit_status["edge_memory_ledger"],
        strategy_update_record=cockpit_status["strategy_update_record"],
        hypothesis_lifecycle=cockpit_status["hypothesis_lifecycle"],
        strategy_weight_updates=cockpit_status["strategy_weight_updates"],
    )
    validate_quantum_meta_review(record)
    paths = write_quantum_meta_review(record, settings=settings)

    errors: list[str] = []
    if record["status"] != "quantum_meta_review_ready":
        errors.append(f"quantum_meta_review_not_ready={record['status']}")
    if record["quantum_meta_review_count"] != 5:
        errors.append("quantum_meta_review_count_not_5")
    if (
        record["quantum_meta_review_passed_count"]
        + record["quantum_meta_review_blocked_count"]
        != record["quantum_meta_review_count"]
    ):
        errors.append("quantum_meta_review_count_reconciliation_failed")
    if record["quantum_dependency_satisfied_count"] != 5:
        errors.append("quantum_dependency_satisfied_count_not_5")
    if record["oracle_contract_accepted_count"] != 5:
        errors.append("oracle_contract_accepted_count_not_5")
    if record["hypothesis_lifecycle_linked_count"] < 1:
        errors.append("hypothesis_lifecycle_linked_count_below_1")
    if record["strategy_weight_update_applied_count"] != 0:
        errors.append("strategy_weight_update_applied_count_nonzero")
    if record["meta_review_applied_count"] != 0:
        errors.append("meta_review_applied_count_nonzero")
    if record["active_strategy_weight_mutation_count"] != 0:
        errors.append("active_strategy_weight_mutation_count_nonzero")
    if record["active_before_weights"] != record["active_after_weights"]:
        errors.append("active_strategy_weights_changed")
    if record["applied_weight_delta_total_abs"] != 0.0:
        errors.append("applied_weight_delta_total_abs_nonzero")
    loop = record["loop_level_decision"]
    if loop["status"] not in {
        "quantum_meta_review_coherent",
        "quantum_meta_review_completed_with_holds",
    }:
        errors.append("loop_decision_invalid")
    if loop["can_submit_paper_orders"] is not False:
        errors.append("loop_can_submit_paper_orders")
    if loop["can_call_quantum_providers"] is not False:
        errors.append("loop_can_call_quantum_providers")
    authority_leaks = [
        field
        for field in QUANTUM_META_REVIEW_AUTHORITY_FALSE_FIELDS
        if record.get(field) is not False
    ]
    if authority_leaks:
        errors.append("authority_leaks=" + ",".join(authority_leaks))
    record_authority_leaks = [
        item.get("meta_review_id", item.get("strategy_family_key", "unknown"))
        for item in record["meta_review_records"]
        if any(
            item.get(field) is not False
            for field in QUANTUM_META_REVIEW_AUTHORITY_FALSE_FIELDS
        )
    ]
    if record_authority_leaks:
        errors.append("record_authority_leaks=" + ",".join(map(str, record_authority_leaks)))

    blocked_probe = build_quantum_meta_review(
        quantum_gate=quantum_gate,
        pattern_recognition_engine=cockpit_status["pattern_recognition_engine"],
        edge_memory_ledger=cockpit_status["edge_memory_ledger"],
        strategy_update_record=cockpit_status["strategy_update_record"],
        hypothesis_lifecycle=cockpit_status["hypothesis_lifecycle"],
        strategy_weight_updates=_blocked_strategy_weight_updates(
            cockpit_status["strategy_weight_updates"]
        ),
    )
    validate_quantum_meta_review(blocked_probe)
    fail_closed_probe_rejected = (
        blocked_probe["status"]
        == "quantum_meta_review_blocked_pending_strategy_weight_updates"
        and blocked_probe["quantum_meta_review_count"] == 0
        and blocked_probe["meta_review_records"] == []
    )
    if not fail_closed_probe_rejected:
        errors.append("fail_closed_probe_not_rejected")

    authority_probe = deepcopy(record)
    authority_probe["meta_review_records"][0]["broker_write_allowed"] = True
    authority_probe_rejected = _probe_rejected(authority_probe)
    if not authority_probe_rejected:
        errors.append("authority_probe_not_rejected")

    applied_probe = deepcopy(record)
    applied_probe["meta_review_applied_count"] = 1
    applied_probe["meta_review_records"][0]["applied"] = True
    applied_probe["meta_review_records"][0]["applied_at"] = record["generated_at"]
    applied_probe_rejected = _probe_rejected(applied_probe)
    if not applied_probe_rejected:
        errors.append("applied_probe_not_rejected")

    active_mutation_probe = deepcopy(record)
    first_key = next(iter(active_mutation_probe["active_after_weights"]))
    active_mutation_probe["active_after_weights"][first_key] = round(
        float(active_mutation_probe["active_after_weights"][first_key]) + 0.01,
        6,
    )
    active_mutation_probe["active_strategy_weight_mutation_count"] = 1
    active_mutation_probe_rejected = _probe_rejected(active_mutation_probe)
    if not active_mutation_probe_rejected:
        errors.append("active_mutation_probe_not_rejected")

    quantum_bypass_probe = deepcopy(record)
    quantum_bypass_probe["meta_review_records"][0]["quantum_dependency_satisfied"] = False
    quantum_bypass_probe["meta_review_records"][0]["meta_review_passed"] = True
    quantum_bypass_probe_rejected = _probe_rejected(quantum_bypass_probe)
    if not quantum_bypass_probe_rejected:
        errors.append("quantum_bypass_probe_not_rejected")

    report = {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "record_status": record["status"],
        "quantum_gate_status": record["quantum_gate_status"],
        "pattern_engine_status": record["pattern_engine_status"],
        "strategy_weight_updates_status": record["strategy_weight_updates_status"],
        "quantum_meta_review_count": record["quantum_meta_review_count"],
        "quantum_meta_review_passed_count": record["quantum_meta_review_passed_count"],
        "quantum_meta_review_blocked_count": record["quantum_meta_review_blocked_count"],
        "quantum_meta_review_hold_count": record["quantum_meta_review_hold_count"],
        "quantum_dependency_satisfied_count": record["quantum_dependency_satisfied_count"],
        "oracle_contract_accepted_count": record["oracle_contract_accepted_count"],
        "hypothesis_lifecycle_linked_count": record["hypothesis_lifecycle_linked_count"],
        "strategy_weight_update_applied_count": record[
            "strategy_weight_update_applied_count"
        ],
        "meta_review_applied_count": record["meta_review_applied_count"],
        "active_strategy_weight_mutation_count": record[
            "active_strategy_weight_mutation_count"
        ],
        "proposed_weight_delta_total_abs": record["proposed_weight_delta_total_abs"],
        "applied_weight_delta_total_abs": record["applied_weight_delta_total_abs"],
        "fail_closed_probe_rejected": fail_closed_probe_rejected,
        "authority_probe_rejected": authority_probe_rejected,
        "applied_probe_rejected": applied_probe_rejected,
        "active_mutation_probe_rejected": active_mutation_probe_rejected,
        "quantum_bypass_probe_rejected": quantum_bypass_probe_rejected,
        "paths": paths,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if errors:
        raise SystemExit("; ".join(errors))

    print("quantum_meta_review_check=ok")
    print(f"quantum_meta_review_status={record['status']}")
    print(f"quantum_meta_review_quantum_gate_status={record['quantum_gate_status']}")
    print(f"quantum_meta_review_pattern_engine_status={record['pattern_engine_status']}")
    print(
        "quantum_meta_review_strategy_weight_updates_status="
        f"{record['strategy_weight_updates_status']}"
    )
    print(f"quantum_meta_review_count={record['quantum_meta_review_count']}")
    print(
        "quantum_meta_review_passed_count="
        f"{record['quantum_meta_review_passed_count']}"
    )
    print(
        "quantum_meta_review_blocked_count="
        f"{record['quantum_meta_review_blocked_count']}"
    )
    print(f"quantum_meta_review_hold_count={record['quantum_meta_review_hold_count']}")
    print(
        "quantum_meta_review_quantum_dependency_satisfied_count="
        f"{record['quantum_dependency_satisfied_count']}"
    )
    print(
        "quantum_meta_review_oracle_contract_accepted_count="
        f"{record['oracle_contract_accepted_count']}"
    )
    print(
        "quantum_meta_review_hypothesis_lifecycle_linked_count="
        f"{record['hypothesis_lifecycle_linked_count']}"
    )
    print(
        "quantum_meta_review_strategy_weight_applied_count="
        f"{record['strategy_weight_update_applied_count']}"
    )
    print(f"quantum_meta_review_applied_count={record['meta_review_applied_count']}")
    print(
        "quantum_meta_review_active_mutation_count="
        f"{record['active_strategy_weight_mutation_count']}"
    )
    print(
        "quantum_meta_review_proposed_delta_total_abs="
        f"{record['proposed_weight_delta_total_abs']}"
    )
    print(
        "quantum_meta_review_applied_delta_total_abs="
        f"{record['applied_weight_delta_total_abs']}"
    )
    print(f"quantum_meta_review_fail_closed_probe_rejected={fail_closed_probe_rejected}")
    print(f"quantum_meta_review_authority_probe_rejected={authority_probe_rejected}")
    print(f"quantum_meta_review_applied_probe_rejected={applied_probe_rejected}")
    print(
        "quantum_meta_review_active_mutation_probe_rejected="
        f"{active_mutation_probe_rejected}"
    )
    print(f"quantum_meta_review_quantum_bypass_probe_rejected={quantum_bypass_probe_rejected}")
    print(f"quantum_meta_review_artifact_path={paths['output_path']}")


if __name__ == "__main__":
    main()
