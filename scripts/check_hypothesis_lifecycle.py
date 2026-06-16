#!/usr/bin/env python3
"""Validate and write Qadam's Stage 4B Hypothesis Lifecycle."""

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
from orchestrator.hypothesis_lifecycle import (  # noqa: E402
    HYPOTHESIS_LIFECYCLE_AUTHORITY_FALSE_FIELDS,
    build_hypothesis_lifecycle,
    read_hypothesis_lifecycle,
    validate_hypothesis_lifecycle,
    write_hypothesis_lifecycle,
)


REPORT_PATH = ROOT / "data/runtime/hypothesis_lifecycle_check.json"


def _blocked_strategy_update(strategy_update_record: dict[str, object]) -> dict[str, object]:
    blocked = deepcopy(strategy_update_record)
    blocked["status"] = "strategy_update_record_blocked_pending_edge_memory"
    blocked["strategy_update_proposal_count"] = 0
    blocked["strategy_update_applied_count"] = 0
    blocked["proposals"] = []
    blocked["blocked_reason"] = "edge_memory_or_pattern_engine_not_ready"
    blocked["quantum_dependency_satisfied"] = False
    policy = dict(blocked.get("recursive_improvement_policy") or {})
    policy["status"] = "blocked"
    blocked["recursive_improvement_policy"] = policy
    return blocked


def main() -> None:
    settings = Settings.from_env()
    cockpit_status = build_cockpit_status(settings)
    lifecycle = build_hypothesis_lifecycle(
        cognition=cockpit_status["cognition"],
        edge_memory_ledger=cockpit_status["edge_memory_ledger"],
        strategy_update_record=cockpit_status["strategy_update_record"],
        previous_lifecycle=read_hypothesis_lifecycle(settings),
    )
    validate_hypothesis_lifecycle(lifecycle)
    paths = write_hypothesis_lifecycle(lifecycle, settings=settings)

    errors: list[str] = []
    authority_leaks = [
        field
        for field in HYPOTHESIS_LIFECYCLE_AUTHORITY_FALSE_FIELDS
        if lifecycle.get(field) is not False
    ]
    if authority_leaks:
        errors.append("authority_leaks=" + ",".join(authority_leaks))
    thread_authority_leaks = [
        thread.get("lifecycle_id", thread.get("hypothesis_key", "unknown"))
        for thread in lifecycle["hypothesis_threads"]
        if any(
            thread.get(field) is not False
            for field in HYPOTHESIS_LIFECYCLE_AUTHORITY_FALSE_FIELDS
        )
    ]
    if thread_authority_leaks:
        errors.append("thread_authority_leaks=" + ",".join(map(str, thread_authority_leaks)))
    if lifecycle["status"] != "hypothesis_lifecycle_active":
        errors.append(f"hypothesis_lifecycle_not_active={lifecycle['status']}")
    if lifecycle["source_hypothesis_count"] < 1:
        errors.append("source_hypothesis_count_below_1")
    if lifecycle["unique_hypothesis_thread_count"] < 1:
        errors.append("unique_hypothesis_thread_count_below_1")
    if lifecycle["unique_hypothesis_thread_count"] > lifecycle["source_hypothesis_count"]:
        errors.append("more_threads_than_source_hypotheses")
    if lifecycle["candidate_promotion_count"] != 0:
        errors.append("candidate_promotion_count_nonzero")
    if lifecycle["applied_lifecycle_transition_count"] != 0:
        errors.append("applied_lifecycle_transition_count_nonzero")
    if lifecycle["quantum_gate_status"] != "quantum_review_gate_passed":
        errors.append("quantum_gate_not_passed")
    if lifecycle["quantum_dependency_satisfied_count"] < 1:
        errors.append("quantum_dependency_satisfied_count_below_1")
    if lifecycle["held_for_corroboration_count"] < 1:
        errors.append("held_for_corroboration_count_below_1")

    blocked_probe = build_hypothesis_lifecycle(
        cognition=cockpit_status["cognition"],
        edge_memory_ledger=cockpit_status["edge_memory_ledger"],
        strategy_update_record=_blocked_strategy_update(cockpit_status["strategy_update_record"]),
        previous_lifecycle=read_hypothesis_lifecycle(settings),
    )
    validate_hypothesis_lifecycle(blocked_probe)
    fail_closed_probe_rejected = (
        blocked_probe["status"]
        == "hypothesis_lifecycle_blocked_pending_strategy_update_record"
        and blocked_probe["unique_hypothesis_thread_count"] == 0
        and blocked_probe["hypothesis_threads"] == []
    )
    if not fail_closed_probe_rejected:
        errors.append("fail_closed_probe_not_rejected")

    authority_probe_rejected = False
    authority_probe = deepcopy(lifecycle)
    authority_probe["hypothesis_threads"][0]["paper_order_allowed"] = True
    try:
        validate_hypothesis_lifecycle(authority_probe)
    except ValueError:
        authority_probe_rejected = True
    if not authority_probe_rejected:
        errors.append("authority_probe_not_rejected")

    promotion_probe_rejected = False
    promotion_probe = deepcopy(lifecycle)
    promotion_probe["candidate_promotion_count"] = 1
    promotion_probe["hypothesis_threads"][0]["candidate_promotion_allowed"] = True
    try:
        validate_hypothesis_lifecycle(promotion_probe)
    except ValueError:
        promotion_probe_rejected = True
    if not promotion_probe_rejected:
        errors.append("promotion_probe_not_rejected")

    duplicate_id_probe_rejected = False
    duplicate_probe = deepcopy(lifecycle)
    duplicate_probe["hypothesis_threads"].append(deepcopy(duplicate_probe["hypothesis_threads"][0]))
    duplicate_probe["unique_hypothesis_thread_count"] = len(duplicate_probe["hypothesis_threads"])
    try:
        validate_hypothesis_lifecycle(duplicate_probe)
    except ValueError:
        duplicate_id_probe_rejected = True
    if not duplicate_id_probe_rejected:
        errors.append("duplicate_id_probe_not_rejected")

    report = {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "lifecycle_status": lifecycle["status"],
        "lifecycle_date": lifecycle["lifecycle_date"],
        "source_hypothesis_count": lifecycle["source_hypothesis_count"],
        "unique_hypothesis_thread_count": lifecycle["unique_hypothesis_thread_count"],
        "duplicate_source_hypothesis_count": lifecycle["duplicate_source_hypothesis_count"],
        "held_for_corroboration_count": lifecycle["held_for_corroboration_count"],
        "ready_for_signal_integrity_review_count": lifecycle[
            "ready_for_signal_integrity_review_count"
        ],
        "candidate_promotion_count": lifecycle["candidate_promotion_count"],
        "applied_lifecycle_transition_count": lifecycle["applied_lifecycle_transition_count"],
        "quantum_dependency_satisfied_count": lifecycle["quantum_dependency_satisfied_count"],
        "fail_closed_probe_rejected": fail_closed_probe_rejected,
        "authority_probe_rejected": authority_probe_rejected,
        "promotion_probe_rejected": promotion_probe_rejected,
        "duplicate_id_probe_rejected": duplicate_id_probe_rejected,
        "paths": paths,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if errors:
        raise SystemExit("; ".join(errors))

    print("hypothesis_lifecycle_check=ok")
    print(f"hypothesis_lifecycle_status={lifecycle['status']}")
    print(f"hypothesis_lifecycle_date={lifecycle['lifecycle_date']}")
    print(f"hypothesis_lifecycle_source_hypothesis_count={lifecycle['source_hypothesis_count']}")
    print(
        "hypothesis_lifecycle_unique_thread_count="
        f"{lifecycle['unique_hypothesis_thread_count']}"
    )
    print(
        "hypothesis_lifecycle_duplicate_source_count="
        f"{lifecycle['duplicate_source_hypothesis_count']}"
    )
    print(
        "hypothesis_lifecycle_held_for_corroboration_count="
        f"{lifecycle['held_for_corroboration_count']}"
    )
    print(
        "hypothesis_lifecycle_ready_for_signal_integrity_count="
        f"{lifecycle['ready_for_signal_integrity_review_count']}"
    )
    print(f"hypothesis_lifecycle_candidate_promotion_count={lifecycle['candidate_promotion_count']}")
    print(
        "hypothesis_lifecycle_applied_transition_count="
        f"{lifecycle['applied_lifecycle_transition_count']}"
    )
    print(
        "hypothesis_lifecycle_quantum_dependency_satisfied_count="
        f"{lifecycle['quantum_dependency_satisfied_count']}"
    )
    print(f"hypothesis_lifecycle_fail_closed_probe_rejected={fail_closed_probe_rejected}")
    print(f"hypothesis_lifecycle_authority_probe_rejected={authority_probe_rejected}")
    print(f"hypothesis_lifecycle_promotion_probe_rejected={promotion_probe_rejected}")
    print(f"hypothesis_lifecycle_duplicate_id_probe_rejected={duplicate_id_probe_rejected}")
    print(f"hypothesis_lifecycle_artifact_path={paths['output_path']}")


if __name__ == "__main__":
    main()
