#!/usr/bin/env python3
"""Validate and write Qadam's quantum-mandatory review gate."""

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
from orchestrator.edge_pattern_ledger import EDGE_PATTERN_AUTHORITY_FALSE_FIELDS  # noqa: E402
from orchestrator.quantum_mandatory_review_gate import (  # noqa: E402
    build_quantum_mandatory_review_gate,
    validate_quantum_mandatory_review_gate,
    write_quantum_mandatory_review_gate,
)

REPORT_PATH = ROOT / "data/runtime/quantum_mandatory_review_gate_check.json"


def _blocked_probe(edge_ledger: dict[str, object]) -> dict[str, object]:
    probe = deepcopy(edge_ledger)
    quantum_review = dict(probe.get("quantum_review") or {})
    quantum_review["status"] = "not_run"
    quantum_review["mode"] = "not_run"
    quantum_review["backend"] = "not_exported"
    quantum_review["core_gate"] = False
    probe["quantum_review"] = quantum_review
    return build_quantum_mandatory_review_gate(edge_ledger=probe)


def _tamper_probe_rejected(blocked_gate: dict[str, object]) -> bool:
    tampered = deepcopy(blocked_gate)
    tampered["status"] = "quantum_review_gate_passed"
    tampered["edge_validation_dependency_satisfied"] = True
    tampered["candidate_ranking_dependency_satisfied"] = True
    tampered["strategy_update_dependency_satisfied"] = True
    tampered["telegram_findings_dependency_satisfied"] = True
    effects = dict(tampered.get("downstream_effects") or {})
    effects["candidate_ranking_dependency_satisfied"] = True
    effects["strategy_update_proposal_dependency_satisfied"] = True
    tampered["downstream_effects"] = effects
    try:
        validate_quantum_mandatory_review_gate(tampered)
    except ValueError:
        return True
    return False


def _pattern_bypass_probe_rejected(gate: dict[str, object]) -> bool:
    tampered = deepcopy(gate)
    decisions = list(tampered.get("pattern_gate_decisions") or [])
    if not decisions:
        return False
    first = dict(decisions[0])
    first["review_attached"] = False
    first["review_complete"] = False
    first["core_gate"] = False
    first["dependency_satisfied"] = True
    first["candidate_ranking_dependency_satisfied"] = True
    first["strategy_update_dependency_satisfied"] = True
    first["missing_requirements"] = ["quantum_review_missing"]
    decisions[0] = first
    tampered["pattern_gate_decisions"] = decisions
    try:
        validate_quantum_mandatory_review_gate(tampered)
    except ValueError:
        return True
    return False


def main() -> None:
    settings = Settings.from_env()
    cockpit_status = build_cockpit_status(settings)
    edge_ledger = cockpit_status["edge_pattern_ledger"]
    gate = build_quantum_mandatory_review_gate(edge_ledger=edge_ledger)
    validate_quantum_mandatory_review_gate(gate)
    paths = write_quantum_mandatory_review_gate(gate, settings=settings)

    blocked_gate = _blocked_probe(edge_ledger)
    validate_quantum_mandatory_review_gate(blocked_gate)
    fail_closed_probe_rejected = _tamper_probe_rejected(blocked_gate)
    pattern_bypass_probe_rejected = _pattern_bypass_probe_rejected(gate)

    authority_leaks = [
        field for field in EDGE_PATTERN_AUTHORITY_FALSE_FIELDS if gate.get(field) is not False
    ]
    decision_authority_leaks = [
        decision.get("pattern_id", decision.get("sleeve_key", "unknown"))
        for decision in gate["pattern_gate_decisions"]
        if any(decision.get(field) is not False for field in EDGE_PATTERN_AUTHORITY_FALSE_FIELDS)
    ]
    errors: list[str] = []
    if authority_leaks:
        errors.append("authority_leaks=" + ",".join(authority_leaks))
    if decision_authority_leaks:
        errors.append("decision_authority_leaks=" + ",".join(map(str, decision_authority_leaks)))
    if gate["status"] != "quantum_review_gate_passed":
        errors.append("gate_not_passed")
    if gate["quantum_review_status"] != "ok":
        errors.append("quantum_review_status_not_ok")
    if gate["quantum_core_gate"] is not True:
        errors.append("quantum_core_gate_false")
    if gate["pattern_review_dependency_blocked_count"] != 0:
        errors.append("pattern_dependency_blocked_count_nonzero")
    if not fail_closed_probe_rejected:
        errors.append("blocked_gate_tamper_probe_not_rejected")
    if not pattern_bypass_probe_rejected:
        errors.append("pattern_bypass_probe_not_rejected")

    REPORT_PATH.write_text(
        json.dumps(
            {
                "status": "ok" if not errors else "failed",
                "errors": errors,
                "gate_status": gate["status"],
                "quantum_review_status": gate["quantum_review_status"],
                "quantum_review_mode": gate["quantum_review_mode"],
                "quantum_backend": gate["quantum_backend"],
                "quantum_core_gate": gate["quantum_core_gate"],
                "candidate_pattern_count": gate["candidate_pattern_count"],
                "pattern_review_count": gate["pattern_review_count"],
                "pattern_review_dependency_satisfied_count": gate[
                    "pattern_review_dependency_satisfied_count"
                ],
                "pattern_review_dependency_blocked_count": gate[
                    "pattern_review_dependency_blocked_count"
                ],
                "edge_validation_dependency_satisfied": gate[
                    "edge_validation_dependency_satisfied"
                ],
                "candidate_ranking_dependency_satisfied": gate[
                    "candidate_ranking_dependency_satisfied"
                ],
                "strategy_update_dependency_satisfied": gate[
                    "strategy_update_dependency_satisfied"
                ],
                "blocked_probe_status": blocked_gate["status"],
                "blocked_probe_fail_closed_reasons": blocked_gate["fail_closed_reasons"],
                "fail_closed_probe_rejected": fail_closed_probe_rejected,
                "pattern_bypass_probe_rejected": pattern_bypass_probe_rejected,
                "paths": paths,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    if errors:
        raise SystemExit("; ".join(errors))

    print("quantum_mandatory_review_gate_check=ok")
    print(f"quantum_mandatory_review_gate_status={gate['status']}")
    print(f"quantum_mandatory_review_gate_quantum_status={gate['quantum_review_status']}")
    print(f"quantum_mandatory_review_gate_quantum_mode={gate['quantum_review_mode']}")
    print(f"quantum_mandatory_review_gate_quantum_backend={gate['quantum_backend']}")
    print(f"quantum_mandatory_review_gate_core_gate={gate['quantum_core_gate']}")
    print(f"quantum_mandatory_review_gate_candidate_pattern_count={gate['candidate_pattern_count']}")
    print(f"quantum_mandatory_review_gate_pattern_review_count={gate['pattern_review_count']}")
    print(
        "quantum_mandatory_review_gate_dependency_satisfied_count="
        f"{gate['pattern_review_dependency_satisfied_count']}"
    )
    print(
        "quantum_mandatory_review_gate_dependency_blocked_count="
        f"{gate['pattern_review_dependency_blocked_count']}"
    )
    print(
        "quantum_mandatory_review_gate_edge_validation_dependency_satisfied="
        f"{gate['edge_validation_dependency_satisfied']}"
    )
    print(
        "quantum_mandatory_review_gate_candidate_ranking_dependency_satisfied="
        f"{gate['candidate_ranking_dependency_satisfied']}"
    )
    print(
        "quantum_mandatory_review_gate_strategy_update_dependency_satisfied="
        f"{gate['strategy_update_dependency_satisfied']}"
    )
    print(f"quantum_mandatory_review_gate_blocked_probe_status={blocked_gate['status']}")
    print(f"quantum_mandatory_review_gate_fail_closed_probe_rejected={fail_closed_probe_rejected}")
    print(f"quantum_mandatory_review_gate_pattern_bypass_probe_rejected={pattern_bypass_probe_rejected}")
    print(f"quantum_mandatory_review_gate_artifact_path={paths['output_path']}")


if __name__ == "__main__":
    main()
