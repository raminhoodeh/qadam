#!/usr/bin/env python3
"""Validate and write Qadam's Stage 4C Strategy Weight Updates."""

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
from orchestrator.strategy_weight_updates import (  # noqa: E402
    STRATEGY_FAMILIES,
    STRATEGY_WEIGHT_UPDATES_AUTHORITY_FALSE_FIELDS,
    build_strategy_weight_updates,
    validate_strategy_weight_updates,
    write_strategy_weight_updates,
)


REPORT_PATH = ROOT / "data/runtime/strategy_weight_updates_check.json"


def _blocked_hypothesis_lifecycle(
    hypothesis_lifecycle: dict[str, object],
) -> dict[str, object]:
    blocked = deepcopy(hypothesis_lifecycle)
    blocked["status"] = "hypothesis_lifecycle_blocked_pending_strategy_update_record"
    blocked["hypothesis_threads"] = []
    blocked["unique_hypothesis_thread_count"] = 0
    blocked["duplicate_source_hypothesis_count"] = 0
    blocked["source_hypothesis_execution_allowed_count"] = 0
    blocked["held_for_corroboration_count"] = 0
    blocked["ready_for_signal_integrity_review_count"] = 0
    blocked["retained_shadow_count"] = 0
    blocked["refutation_candidate_count"] = 0
    blocked["blocked_authority_mismatch_count"] = 0
    blocked["quantum_dependency_satisfied_count"] = 0
    blocked["strategy_update_linked_count"] = 0
    blocked["candidate_promotion_count"] = 0
    blocked["applied_lifecycle_transition_count"] = 0
    contract = dict(blocked.get("recursive_improvement_contract") or {})
    contract["status"] = "blocked"
    blocked["recursive_improvement_contract"] = contract
    blocked["blocked_reason"] = "strategy_update_record_not_ready"
    return blocked


def _probe_rejected(payload: dict[str, object]) -> bool:
    try:
        validate_strategy_weight_updates(payload)
    except ValueError:
        return True
    return False


def main() -> None:
    settings = Settings.from_env()
    cockpit_status = build_cockpit_status(settings)
    record = build_strategy_weight_updates(
        edge_memory_ledger=cockpit_status["edge_memory_ledger"],
        strategy_update_record=cockpit_status["strategy_update_record"],
        hypothesis_lifecycle=cockpit_status["hypothesis_lifecycle"],
    )
    validate_strategy_weight_updates(record)
    paths = write_strategy_weight_updates(record, settings=settings)

    errors: list[str] = []
    if record["status"] != "strategy_weight_updates_ready":
        errors.append(f"strategy_weight_updates_not_ready={record['status']}")
    if record["strategy_weight_update_proposal_count"] != len(STRATEGY_FAMILIES):
        errors.append("strategy_weight_update_proposal_count_mismatch")
    if record["strategy_weight_update_applied_count"] != 0:
        errors.append("strategy_weight_update_applied_count_nonzero")
    if record["active_strategy_weight_mutation_count"] != 0:
        errors.append("active_strategy_weight_mutation_count_nonzero")
    if record["active_before_weights"] != record["active_after_weights"]:
        errors.append("active_strategy_weights_changed")
    if record["applied_weight_delta_total_abs"] != 0.0:
        errors.append("applied_weight_delta_total_abs_nonzero")
    if record["quantum_dependency_satisfied_count"] != len(STRATEGY_FAMILIES):
        errors.append("quantum_dependency_satisfied_count_mismatch")
    if record["hypothesis_lifecycle_linked_count"] < 1:
        errors.append("hypothesis_lifecycle_not_linked")
    if record["proposed_after_weight_sum"] != 1.0:
        errors.append("proposed_after_weight_sum_not_one")
    authority_leaks = [
        field
        for field in STRATEGY_WEIGHT_UPDATES_AUTHORITY_FALSE_FIELDS
        if record.get(field) is not False
    ]
    if authority_leaks:
        errors.append("authority_leaks=" + ",".join(authority_leaks))
    record_authority_leaks = [
        item.get("weight_update_id", item.get("strategy_family_key", "unknown"))
        for item in record["weight_update_records"]
        if any(
            item.get(field) is not False
            for field in STRATEGY_WEIGHT_UPDATES_AUTHORITY_FALSE_FIELDS
        )
    ]
    if record_authority_leaks:
        errors.append("record_authority_leaks=" + ",".join(map(str, record_authority_leaks)))

    blocked_probe = build_strategy_weight_updates(
        edge_memory_ledger=cockpit_status["edge_memory_ledger"],
        strategy_update_record=cockpit_status["strategy_update_record"],
        hypothesis_lifecycle=_blocked_hypothesis_lifecycle(
            cockpit_status["hypothesis_lifecycle"]
        ),
    )
    validate_strategy_weight_updates(blocked_probe)
    fail_closed_probe_rejected = (
        blocked_probe["status"]
        == "strategy_weight_updates_blocked_pending_hypothesis_lifecycle"
        and blocked_probe["strategy_weight_update_proposal_count"] == 0
        and blocked_probe["weight_update_records"] == []
    )
    if not fail_closed_probe_rejected:
        errors.append("fail_closed_probe_not_rejected")

    authority_probe = deepcopy(record)
    authority_probe["weight_update_records"][0]["broker_write_allowed"] = True
    authority_probe_rejected = _probe_rejected(authority_probe)
    if not authority_probe_rejected:
        errors.append("authority_probe_not_rejected")

    applied_probe = deepcopy(record)
    applied_probe["strategy_weight_update_applied_count"] = 1
    applied_probe["weight_update_records"][0]["applied"] = True
    applied_probe["weight_update_records"][0]["applied_at"] = record["generated_at"]
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

    normalization_probe = deepcopy(record)
    first_key = next(iter(normalization_probe["proposed_after_weights"]))
    normalization_probe["proposed_after_weights"][first_key] = round(
        float(normalization_probe["proposed_after_weights"][first_key]) + 0.1,
        6,
    )
    normalization_probe_rejected = _probe_rejected(normalization_probe)
    if not normalization_probe_rejected:
        errors.append("normalization_probe_not_rejected")

    report = {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "record_status": record["status"],
        "strategy_weight_update_proposal_count": record[
            "strategy_weight_update_proposal_count"
        ],
        "strategy_weight_update_applied_count": record[
            "strategy_weight_update_applied_count"
        ],
        "active_strategy_weight_mutation_count": record[
            "active_strategy_weight_mutation_count"
        ],
        "quantum_dependency_satisfied_count": record[
            "quantum_dependency_satisfied_count"
        ],
        "hypothesis_lifecycle_linked_count": record[
            "hypothesis_lifecycle_linked_count"
        ],
        "proposed_weight_delta_total_abs": record["proposed_weight_delta_total_abs"],
        "applied_weight_delta_total_abs": record["applied_weight_delta_total_abs"],
        "fail_closed_probe_rejected": fail_closed_probe_rejected,
        "authority_probe_rejected": authority_probe_rejected,
        "applied_probe_rejected": applied_probe_rejected,
        "active_mutation_probe_rejected": active_mutation_probe_rejected,
        "normalization_probe_rejected": normalization_probe_rejected,
        "paths": paths,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if errors:
        raise SystemExit("; ".join(errors))

    print("strategy_weight_updates_check=ok")
    print(f"strategy_weight_updates_status={record['status']}")
    print(
        "strategy_weight_updates_proposal_count="
        f"{record['strategy_weight_update_proposal_count']}"
    )
    print(
        "strategy_weight_updates_applied_count="
        f"{record['strategy_weight_update_applied_count']}"
    )
    print(
        "strategy_weight_updates_active_mutation_count="
        f"{record['active_strategy_weight_mutation_count']}"
    )
    print(
        "strategy_weight_updates_quantum_dependency_satisfied_count="
        f"{record['quantum_dependency_satisfied_count']}"
    )
    print(
        "strategy_weight_updates_hypothesis_lifecycle_linked_count="
        f"{record['hypothesis_lifecycle_linked_count']}"
    )
    print(
        "strategy_weight_updates_proposed_delta_total_abs="
        f"{record['proposed_weight_delta_total_abs']}"
    )
    print(
        "strategy_weight_updates_applied_delta_total_abs="
        f"{record['applied_weight_delta_total_abs']}"
    )
    print(
        "strategy_weight_updates_fail_closed_probe_rejected="
        f"{fail_closed_probe_rejected}"
    )
    print(
        "strategy_weight_updates_authority_probe_rejected="
        f"{authority_probe_rejected}"
    )
    print(
        "strategy_weight_updates_applied_probe_rejected="
        f"{applied_probe_rejected}"
    )
    print(
        "strategy_weight_updates_active_mutation_probe_rejected="
        f"{active_mutation_probe_rejected}"
    )
    print(
        "strategy_weight_updates_normalization_probe_rejected="
        f"{normalization_probe_rejected}"
    )
    print(f"strategy_weight_updates_artifact_path={paths['output_path']}")


if __name__ == "__main__":
    main()
