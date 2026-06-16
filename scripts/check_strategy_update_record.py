#!/usr/bin/env python3
"""Validate and write Qadam's Stage 4 Strategy Update Record."""

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
from orchestrator.edge_memory_ledger import (  # noqa: E402
    build_edge_memory_ledger,
    read_edge_memory_ledger,
)
from orchestrator.strategy_update_record import (  # noqa: E402
    STRATEGY_UPDATE_RECORD_AUTHORITY_FALSE_FIELDS,
    build_strategy_update_record,
    validate_strategy_update_record,
    write_strategy_update_record,
)


REPORT_PATH = ROOT / "data/runtime/strategy_update_record_check.json"


def _blocked_edge_memory(edge_memory_ledger: dict[str, object]) -> dict[str, object]:
    blocked = deepcopy(edge_memory_ledger)
    blocked["status"] = "edge_memory_blocked_pending_pattern_engine"
    blocked["memory_records"] = []
    blocked["memory_record_count"] = 0
    blocked["minimum_observation_count"] = 0
    blocked["maximum_observation_count"] = 0
    blocked["quantum_dependency_satisfied"] = False
    blocked["blocked_reason"] = "pattern_recognition_engine_not_ready_for_memory"
    contract = dict(blocked.get("recursive_improvement_contract") or {})
    contract["status"] = "blocked"
    contract["strategy_update_record_input_allowed"] = False
    blocked["recursive_improvement_contract"] = contract
    return blocked


def main() -> None:
    settings = Settings.from_env()
    cockpit_status = build_cockpit_status(settings)
    pattern_engine = cockpit_status["pattern_recognition_engine"]
    edge_memory = build_edge_memory_ledger(
        pattern_recognition_engine=pattern_engine,
        edge_pattern_ledger=cockpit_status["edge_pattern_ledger"],
        previous_ledger=read_edge_memory_ledger(settings),
    )
    record = build_strategy_update_record(
        edge_memory_ledger=edge_memory,
        pattern_recognition_engine=pattern_engine,
    )
    validate_strategy_update_record(record)
    paths = write_strategy_update_record(record, settings=settings)

    errors: list[str] = []
    authority_leaks = [
        field
        for field in STRATEGY_UPDATE_RECORD_AUTHORITY_FALSE_FIELDS
        if record.get(field) is not False
    ]
    if authority_leaks:
        errors.append("authority_leaks=" + ",".join(authority_leaks))
    proposal_authority_leaks = [
        proposal.get("update_id", proposal.get("sleeve_key", "unknown"))
        for proposal in record["proposals"]
        if any(
            proposal.get(field) is not False
            for field in STRATEGY_UPDATE_RECORD_AUTHORITY_FALSE_FIELDS
        )
    ]
    if proposal_authority_leaks:
        errors.append("proposal_authority_leaks=" + ",".join(map(str, proposal_authority_leaks)))
    if record["status"] != "strategy_update_record_ready":
        errors.append(f"strategy_update_record_not_ready={record['status']}")
    if record["strategy_update_proposal_count"] != 5:
        errors.append("strategy_update_proposal_count_not_5")
    if record["strategy_update_applied_count"] != 0:
        errors.append("strategy_update_applied_count_nonzero")
    if record["quantum_gate_status"] != "quantum_review_gate_passed":
        errors.append("quantum_gate_not_passed")
    if record["quantum_dependency_satisfied"] is not True:
        errors.append("quantum_dependency_not_satisfied")
    if any(proposal.get("applied") is not False for proposal in record["proposals"]):
        errors.append("proposal_applied")

    blocked_probe = build_strategy_update_record(
        edge_memory_ledger=_blocked_edge_memory(edge_memory),
        pattern_recognition_engine=pattern_engine,
    )
    validate_strategy_update_record(blocked_probe)
    fail_closed_probe_rejected = (
        blocked_probe["status"] == "strategy_update_record_blocked_pending_edge_memory"
        and blocked_probe["strategy_update_proposal_count"] == 0
        and blocked_probe["proposals"] == []
    )
    if not fail_closed_probe_rejected:
        errors.append("fail_closed_probe_not_rejected")

    authority_probe_rejected = False
    authority_probe = deepcopy(record)
    authority_probe["proposals"][0]["broker_write_allowed"] = True
    try:
        validate_strategy_update_record(authority_probe)
    except ValueError:
        authority_probe_rejected = True
    if not authority_probe_rejected:
        errors.append("authority_probe_not_rejected")

    applied_probe_rejected = False
    applied_probe = deepcopy(record)
    applied_probe["strategy_update_applied_count"] = 1
    applied_probe["proposals"][0]["applied"] = True
    applied_probe["proposals"][0]["applied_at"] = record["generated_at"]
    try:
        validate_strategy_update_record(applied_probe)
    except ValueError:
        applied_probe_rejected = True
    if not applied_probe_rejected:
        errors.append("applied_probe_not_rejected")

    report = {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "record_status": record["status"],
        "edge_memory_ledger_status": record["edge_memory_ledger_status"],
        "pattern_engine_status": record["pattern_engine_status"],
        "strategy_update_proposal_count": record["strategy_update_proposal_count"],
        "strategy_update_applied_count": record["strategy_update_applied_count"],
        "quantum_gate_status": record["quantum_gate_status"],
        "fail_closed_probe_rejected": fail_closed_probe_rejected,
        "authority_probe_rejected": authority_probe_rejected,
        "applied_probe_rejected": applied_probe_rejected,
        "paths": paths,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if errors:
        raise SystemExit("; ".join(errors))

    print("strategy_update_record_check=ok")
    print(f"strategy_update_record_status={record['status']}")
    print(f"strategy_update_record_edge_memory_status={record['edge_memory_ledger_status']}")
    print(f"strategy_update_record_pattern_engine_status={record['pattern_engine_status']}")
    print(f"strategy_update_record_proposal_count={record['strategy_update_proposal_count']}")
    print(f"strategy_update_record_applied_count={record['strategy_update_applied_count']}")
    print(f"strategy_update_record_quantum_gate_status={record['quantum_gate_status']}")
    print(f"strategy_update_record_fail_closed_probe_rejected={fail_closed_probe_rejected}")
    print(f"strategy_update_record_authority_probe_rejected={authority_probe_rejected}")
    print(f"strategy_update_record_applied_probe_rejected={applied_probe_rejected}")
    print(f"strategy_update_record_artifact_path={paths['output_path']}")


if __name__ == "__main__":
    main()
