#!/usr/bin/env python3
"""Build and validate Qadam next-generation Phase 7 Akber Filter V2."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qadam_akber_filter_v2 import (
    ABLATION_ARTIFACT,
    DASHBOARD_SUMMARY_ARTIFACT,
    EVENTS_ARTIFACT,
    EXPLANATIONS_ARTIFACT,
    HISTORICAL_REPLAY_ARTIFACT,
    INPUTS_ARTIFACT,
    PRIMARY_ARTIFACT,
    RESULTS_ARTIFACT,
    THRESHOLD_PROPOSALS_ARTIFACT,
    _runtime_dir,
    build_and_write_akber_filter_v2,
    load_akber_filter_v2,
    validate_akber_filter_v2_bundle,
    validate_negative_akber_filter_v2_probes,
)


def main() -> int:
    settings = Settings.from_env()
    bundle, written = build_and_write_akber_filter_v2(settings)
    runtime_dir = _runtime_dir(settings)

    validation_errors: list[str] = []
    for filename in (
        PRIMARY_ARTIFACT,
        INPUTS_ARTIFACT,
        RESULTS_ARTIFACT,
        HISTORICAL_REPLAY_ARTIFACT,
        ABLATION_ARTIFACT,
        THRESHOLD_PROPOSALS_ARTIFACT,
        EXPLANATIONS_ARTIFACT,
        DASHBOARD_SUMMARY_ARTIFACT,
        EVENTS_ARTIFACT,
    ):
        if not (runtime_dir / filename).exists():
            validation_errors.append(f"{filename}_missing")

    validation_errors.extend(validate_akber_filter_v2_bundle(bundle))
    validation_errors.extend(validate_akber_filter_v2_bundle(load_akber_filter_v2(settings)))
    validation_errors.extend(validate_negative_akber_filter_v2_probes(settings))

    print(f"primary={written.get('primary')}")
    print(f"inputs={written.get('inputs')}")
    print(f"results={written.get('results')}")
    print(f"historical_replay={written.get('historical_replay')}")
    print(f"ablation_tests={written.get('ablation_tests')}")
    print(f"threshold_proposals={written.get('threshold_proposals')}")
    print(f"explanations={written.get('explanations')}")
    print(f"dashboard_summary={written.get('dashboard_summary')}")
    print(f"events={written.get('events')}")
    print(f"status={bundle.primary.get('status')}")
    print(f"akber_input_count={bundle.primary.get('akber_input_count')}")
    print(f"akber_result_count={bundle.primary.get('akber_result_count')}")
    print(f"historical_replay_count={bundle.primary.get('historical_replay_count')}")
    print(f"ablation_test_count={bundle.primary.get('ablation_test_count')}")
    print(f"threshold_proposal_count={bundle.primary.get('threshold_proposal_count')}")
    print(f"plain_english_explanation_count={bundle.primary.get('plain_english_explanation_count')}")
    print(f"pass_count={bundle.primary.get('pass_count')}")
    print(f"hold_count={bundle.primary.get('hold_count')}")
    print(f"veto_count={bundle.primary.get('veto_count')}")
    print(f"router_eligible_count={bundle.primary.get('router_eligible_count')}")
    print(f"router_eligible_with_missing_context_count={bundle.primary.get('router_eligible_with_missing_context_count')}")
    print(f"no_router_eligible_setup_has_missing_akber_context={bundle.primary.get('no_router_eligible_setup_has_missing_akber_context')}")
    print(f"akber_filter_pass_is_execution_approval={bundle.primary.get('akber_filter_pass_is_execution_approval')}")
    print(f"execution_approval_created={bundle.primary.get('execution_approval_created')}")
    print(f"trade_candidate_created={bundle.primary.get('trade_candidate_created')}")
    print(f"paper_order_created={bundle.primary.get('paper_order_created')}")
    print(f"broker_write_count={bundle.primary.get('broker_write_count')}")
    print(f"live_capital_enabled={bundle.primary.get('live_capital_enabled')}")
    print(f"proof_credit_allowed={bundle.primary.get('proof_credit_allowed')}")
    print(f"threshold_change_applied={bundle.primary.get('threshold_change_applied')}")
    print(f"paper_growth_trial_calendar_advanced={bundle.primary.get('paper_growth_trial_calendar_advanced')}")
    if validation_errors:
        for error in validation_errors:
            print(f"error={error}")
        return 1
    print("qadam_akber_filter_v2_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
