#!/usr/bin/env python3
"""Validate Qadam operational perfection certification."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qadam_operational_perfection import (
    PRIMARY_ARTIFACT,
    _runtime_dir,
    build_and_write_operational_perfection_certification,
    validate_operational_perfection,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    settings = Settings.from_env()
    payload, written, errors = build_and_write_operational_perfection_certification(settings, refresh_self_healing=True)
    runtime = _runtime_dir(settings)
    loaded = _load_json(runtime / PRIMARY_ARTIFACT)
    validation_errors = list(errors)

    if not (runtime / PRIMARY_ARTIFACT).exists():
        validation_errors.append(f"{PRIMARY_ARTIFACT}_missing")
    validation_errors.extend(validate_operational_perfection(loaded))
    if loaded.get("generated_at") != payload.get("generated_at"):
        validation_errors.append("written_generated_at_mismatch")

    print(f"artifact={written.get('primary')}")
    print(f"status={loaded.get('status')}")
    print(f"status_family={loaded.get('status_family')}")
    print(f"operationally_complete={loaded.get('operationally_complete')}")
    print(f"required_source_freshness_passed={loaded.get('required_source_freshness_passed')}")
    print(f"source_quorum_protected_by_quarantine={loaded.get('source_quorum_protected_by_quarantine')}")
    print(f"historical_memory_coverage_passed={loaded.get('historical_memory_coverage_passed')}")
    print(f"akber_input_completeness_passed={loaded.get('akber_input_completeness_passed')}")
    print(f"validated_edge_pathway_passed={loaded.get('validated_edge_pathway_passed')}")
    print(f"router_decision_integrity_passed={loaded.get('router_decision_integrity_passed')}")
    print(f"paperops_guarded_route_passed={loaded.get('paperops_guarded_route_passed')}")
    print(f"dashboard_public_contract_passed={loaded.get('dashboard_public_contract_passed')}")
    print(f"telegram_boundary_passed={loaded.get('telegram_boundary_passed')}")
    print(f"self_healing_passed={loaded.get('self_healing_passed')}")
    print(f"deployment_closure_passed={loaded.get('deployment_closure_passed')}")
    print(f"safety_boundaries_passed={loaded.get('safety_boundaries_passed')}")
    print(f"failed_gate_count={loaded.get('failed_gate_count')}")
    print(f"paper_review_candidate_count={loaded.get('paper_review_candidate_count')}")
    print(f"active_paper_position_count={loaded.get('active_paper_position_count')}")
    print(f"why_not_trading_now={loaded.get('why_not_trading_now')}")
    print(f"paper_order_created_count={loaded.get('paper_order_created_count')}")
    print(f"broker_write_count={loaded.get('broker_write_count')}")
    print(f"live_capital_enabled={loaded.get('live_capital_enabled')}")
    for blocker in loaded.get("unresolved_blockers", []):
        print(f"blocker={blocker.get('gate')}:{blocker.get('reason')}")

    if validation_errors:
        for error in sorted(set(validation_errors)):
            print(f"error={error}")
        return 1
    print("qadam_operational_perfection_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
