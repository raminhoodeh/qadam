#!/usr/bin/env python3
"""Build and validate Qadam next-generation Phase 8 Shadow Simulator V2."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qadam_shadow_simulator_v2 import (
    ALTERNATE_THRESHOLD_OUTCOMES_ARTIFACT,
    COUNTERFACTUAL_NO_ORDER_ARTIFACT,
    DASHBOARD_SUMMARY_ARTIFACT,
    EVENTS_ARTIFACT,
    FORWARD_TRACKING_ARTIFACT,
    HISTORICAL_REPLAY_ARTIFACT,
    MISSED_OPPORTUNITIES_ARTIFACT,
    PRIMARY_ARTIFACT,
    _runtime_dir,
    build_and_write_shadow_simulator_v2,
    load_shadow_simulator_v2,
    validate_negative_shadow_simulator_v2_probes,
    validate_shadow_simulator_v2_bundle,
)


def main() -> int:
    settings = Settings.from_env()
    bundle, written = build_and_write_shadow_simulator_v2(settings)
    runtime_dir = _runtime_dir(settings)

    validation_errors: list[str] = []
    for filename in (
        PRIMARY_ARTIFACT,
        HISTORICAL_REPLAY_ARTIFACT,
        FORWARD_TRACKING_ARTIFACT,
        COUNTERFACTUAL_NO_ORDER_ARTIFACT,
        ALTERNATE_THRESHOLD_OUTCOMES_ARTIFACT,
        MISSED_OPPORTUNITIES_ARTIFACT,
        DASHBOARD_SUMMARY_ARTIFACT,
        EVENTS_ARTIFACT,
    ):
        if not (runtime_dir / filename).exists():
            validation_errors.append(f"{filename}_missing")

    validation_errors.extend(validate_shadow_simulator_v2_bundle(bundle))
    validation_errors.extend(validate_shadow_simulator_v2_bundle(load_shadow_simulator_v2(settings)))
    validation_errors.extend(validate_negative_shadow_simulator_v2_probes(settings))

    primary = bundle.primary
    print(f"primary={written.get('primary')}")
    print(f"historical_replay={written.get('historical_replay')}")
    print(f"forward_tracking={written.get('forward_tracking')}")
    print(f"counterfactual_no_order={written.get('counterfactual_no_order')}")
    print(f"alternate_threshold_outcomes={written.get('alternate_threshold_outcomes')}")
    print(f"missed_opportunities={written.get('missed_opportunities')}")
    print(f"dashboard_summary={written.get('dashboard_summary')}")
    print(f"events={written.get('events')}")
    print(f"status={primary.get('status')}")
    print(f"hypothesis_count={primary.get('hypothesis_count')}")
    print(f"hypothesis_with_shadow_evidence_count={primary.get('hypothesis_with_shadow_evidence_count')}")
    print(f"missing_shadow_evidence_count={primary.get('missing_shadow_evidence_count')}")
    print(f"historical_shadow_replay_count={primary.get('historical_shadow_replay_count')}")
    print(f"forward_tracking_count={primary.get('forward_tracking_count')}")
    print(f"counterfactual_no_order_count={primary.get('counterfactual_no_order_count')}")
    print(f"alternate_threshold_outcome_count={primary.get('alternate_threshold_outcome_count')}")
    print(f"missed_opportunity_count={primary.get('missed_opportunity_count')}")
    print(f"every_hypothesis_has_shadow_evidence={primary.get('every_hypothesis_has_shadow_evidence')}")
    print(
        "router_confidence_increase_without_shadow_evidence_count="
        f"{primary.get('router_confidence_increase_without_shadow_evidence_count')}"
    )
    print(f"router_confidence_increase_created={primary.get('router_confidence_increase_created')}")
    print(f"shadow_success_cannot_create_paper_order={primary.get('shadow_success_cannot_create_paper_order')}")
    print(f"shadow_success_cannot_create_proof_credit={primary.get('shadow_success_cannot_create_proof_credit')}")
    print(f"paper_order_created={primary.get('paper_order_created')}")
    print(f"paper_order_created_count={primary.get('paper_order_created_count')}")
    print(f"proof_credit_allowed={primary.get('proof_credit_allowed')}")
    print(f"paper_proof_ledger_credit_allowed={primary.get('paper_proof_ledger_credit_allowed')}")
    print(f"broker_write_count={primary.get('broker_write_count')}")
    print(f"live_capital_enabled={primary.get('live_capital_enabled')}")
    print(f"simulated_elapsed_time_allowed={primary.get('simulated_elapsed_time_allowed')}")
    print(f"paper_growth_trial_calendar_advanced={primary.get('paper_growth_trial_calendar_advanced')}")
    if validation_errors:
        for error in validation_errors:
            print(f"error={error}")
        return 1
    print("qadam_shadow_simulator_v2_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
