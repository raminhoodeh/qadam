#!/usr/bin/env python3
"""Validate and write Qadam's Stage 4A Edge Memory Ledger."""

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
    EDGE_MEMORY_LEDGER_AUTHORITY_FALSE_FIELDS,
    build_edge_memory_ledger,
    read_edge_memory_ledger,
    validate_edge_memory_ledger,
    write_edge_memory_ledger,
)


REPORT_PATH = ROOT / "data/runtime/edge_memory_ledger_check.json"


def _blocked_engine(pattern_engine: dict[str, object]) -> dict[str, object]:
    blocked = deepcopy(pattern_engine)
    blocked["status"] = "pattern_engine_blocked_pending_quantum_gate"
    blocked["candidate_patterns"] = []
    blocked["candidate_pattern_count"] = 0
    blocked["quantum_oracle_contract_accepted_count"] = 0
    blocked["quantum_oracle_job_preview_count"] = 0
    blocked["blocked_reason"] = "synthetic_edge_memory_probe"
    gate = dict(blocked.get("quantum_gate") or {})
    gate["status"] = "quantum_review_gate_blocked"
    blocked["quantum_gate"] = gate
    optimization = dict(blocked.get("quantum_optimization") or {})
    optimization["quantum_gate_status"] = "quantum_review_gate_blocked"
    optimization["quantum_gate_passed"] = False
    blocked["quantum_optimization"] = optimization
    summary = dict(blocked.get("engine_summary") or {})
    summary["candidate_pattern_count"] = 0
    summary["quantum_oracle_contract_accepted_count"] = 0
    summary["quantum_oracle_job_preview_count"] = 0
    blocked["engine_summary"] = summary
    return blocked


def main() -> None:
    settings = Settings.from_env()
    cockpit_status = build_cockpit_status(settings)
    pattern_engine = cockpit_status["pattern_recognition_engine"]
    previous_ledger = read_edge_memory_ledger(settings)
    ledger = build_edge_memory_ledger(
        pattern_recognition_engine=pattern_engine,
        edge_pattern_ledger=cockpit_status["edge_pattern_ledger"],
        previous_ledger=previous_ledger,
    )
    validate_edge_memory_ledger(ledger)
    paths = write_edge_memory_ledger(ledger, settings=settings)

    errors: list[str] = []
    authority_leaks = [
        field for field in EDGE_MEMORY_LEDGER_AUTHORITY_FALSE_FIELDS if ledger.get(field) is not False
    ]
    if authority_leaks:
        errors.append("authority_leaks=" + ",".join(authority_leaks))
    record_authority_leaks = [
        record.get("memory_id", record.get("sleeve_key", "unknown"))
        for record in ledger["memory_records"]
        if any(record.get(field) is not False for field in EDGE_MEMORY_LEDGER_AUTHORITY_FALSE_FIELDS)
    ]
    if record_authority_leaks:
        errors.append("record_authority_leaks=" + ",".join(map(str, record_authority_leaks)))
    if ledger["status"] != "edge_memory_active":
        errors.append(f"edge_memory_not_active={ledger['status']}")
    if ledger["memory_record_count"] != 5:
        errors.append("memory_record_count_not_5")
    if ledger["minimum_observation_count"] < 1:
        errors.append("minimum_observation_count_below_1")
    if ledger["quantum_gate_status"] != "quantum_review_gate_passed":
        errors.append("quantum_gate_not_passed")
    if ledger["quantum_dependency_satisfied"] is not True:
        errors.append("quantum_dependency_not_satisfied")
    if not all(record.get("observation_count") == len(record.get("observation_dates", [])) for record in ledger["memory_records"]):
        errors.append("observation_count_mismatch")

    blocked_probe = build_edge_memory_ledger(
        pattern_recognition_engine=_blocked_engine(pattern_engine),
        edge_pattern_ledger=cockpit_status["edge_pattern_ledger"],
        previous_ledger=previous_ledger,
    )
    validate_edge_memory_ledger(blocked_probe)
    fail_closed_probe_rejected = (
        blocked_probe["status"] == "edge_memory_blocked_pending_pattern_engine"
        and blocked_probe["memory_record_count"] == 0
        and blocked_probe["memory_records"] == []
    )
    if not fail_closed_probe_rejected:
        errors.append("fail_closed_probe_not_rejected")

    authority_probe_rejected = False
    authority_probe = deepcopy(ledger)
    authority_probe["memory_records"][0]["paper_order_allowed"] = True
    try:
        validate_edge_memory_ledger(authority_probe)
    except ValueError:
        authority_probe_rejected = True
    if not authority_probe_rejected:
        errors.append("authority_probe_not_rejected")

    duplicate_date_probe_rejected = False
    duplicate_probe = deepcopy(ledger)
    dates = list(duplicate_probe["memory_records"][0]["observation_dates"])
    duplicate_probe["memory_records"][0]["observation_dates"] = dates + [dates[-1]]
    duplicate_probe["memory_records"][0]["observation_count"] = len(dates) + 1
    try:
        validate_edge_memory_ledger(duplicate_probe)
    except ValueError:
        duplicate_date_probe_rejected = True
    if not duplicate_date_probe_rejected:
        errors.append("duplicate_date_probe_not_rejected")

    report = {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "ledger_status": ledger["status"],
        "memory_date": ledger["memory_date"],
        "pattern_engine_status": ledger["pattern_engine_status"],
        "memory_record_count": ledger["memory_record_count"],
        "minimum_observation_count": ledger["minimum_observation_count"],
        "maximum_observation_count": ledger["maximum_observation_count"],
        "quantum_gate_status": ledger["quantum_gate_status"],
        "fail_closed_probe_rejected": fail_closed_probe_rejected,
        "authority_probe_rejected": authority_probe_rejected,
        "duplicate_date_probe_rejected": duplicate_date_probe_rejected,
        "paths": paths,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if errors:
        raise SystemExit("; ".join(errors))

    print("edge_memory_ledger_check=ok")
    print(f"edge_memory_ledger_status={ledger['status']}")
    print(f"edge_memory_ledger_memory_date={ledger['memory_date']}")
    print(f"edge_memory_ledger_pattern_engine_status={ledger['pattern_engine_status']}")
    print(f"edge_memory_ledger_memory_record_count={ledger['memory_record_count']}")
    print(f"edge_memory_ledger_minimum_observation_count={ledger['minimum_observation_count']}")
    print(f"edge_memory_ledger_maximum_observation_count={ledger['maximum_observation_count']}")
    print(f"edge_memory_ledger_quantum_gate_status={ledger['quantum_gate_status']}")
    print(f"edge_memory_ledger_fail_closed_probe_rejected={fail_closed_probe_rejected}")
    print(f"edge_memory_ledger_authority_probe_rejected={authority_probe_rejected}")
    print(f"edge_memory_ledger_duplicate_date_probe_rejected={duplicate_date_probe_rejected}")
    print(f"edge_memory_ledger_artifact_path={paths['output_path']}")


if __name__ == "__main__":
    main()
