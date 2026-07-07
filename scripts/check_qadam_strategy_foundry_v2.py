#!/usr/bin/env python3
"""Build and validate Qadam next-generation Phase 6 Strategy Foundry V2."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qadam_strategy_foundry_v2 import (
    DASHBOARD_SUMMARY_ARTIFACT,
    EVENTS_ARTIFACT,
    HYPOTHESES_ARTIFACT,
    PRIMARY_ARTIFACT,
    REJECTIONS_ARTIFACT,
    _runtime_dir,
    build_and_write_strategy_foundry_v2,
    load_strategy_foundry_v2,
    validate_negative_strategy_foundry_v2_probes,
    validate_strategy_foundry_v2_bundle,
)


def main() -> int:
    settings = Settings.from_env()
    bundle, written = build_and_write_strategy_foundry_v2(settings)
    runtime_dir = _runtime_dir(settings)

    validation_errors: list[str] = []
    for filename in (
        PRIMARY_ARTIFACT,
        HYPOTHESES_ARTIFACT,
        REJECTIONS_ARTIFACT,
        DASHBOARD_SUMMARY_ARTIFACT,
        EVENTS_ARTIFACT,
    ):
        if not (runtime_dir / filename).exists():
            validation_errors.append(f"{filename}_missing")

    validation_errors.extend(validate_strategy_foundry_v2_bundle(bundle))
    validation_errors.extend(validate_strategy_foundry_v2_bundle(load_strategy_foundry_v2(settings)))
    validation_errors.extend(validate_negative_strategy_foundry_v2_probes(settings))

    print(f"primary={written.get('primary')}")
    print(f"hypotheses={written.get('hypotheses')}")
    print(f"rejections={written.get('rejections')}")
    print(f"dashboard_summary={written.get('dashboard_summary')}")
    print(f"events={written.get('events')}")
    print(f"status={bundle.primary.get('status')}")
    print(f"source_strategy_count={bundle.primary.get('source_strategy_count')}")
    print(f"strategy_hypothesis_count={bundle.primary.get('strategy_hypothesis_count')}")
    print(f"accepted_for_akber_input_builder_count={bundle.primary.get('accepted_for_akber_input_builder_count')}")
    print(f"rejected_before_akber_count={bundle.primary.get('rejected_before_akber_count')}")
    print(f"weak_pattern_rejection_count={bundle.primary.get('weak_pattern_rejection_count')}")
    print(f"strategy_family_rejection_count={bundle.primary.get('strategy_family_rejection_count')}")
    print(f"weak_hypotheses_rejected_before_akber={bundle.primary.get('weak_hypotheses_rejected_before_akber')}")
    print(f"akber_filter_run={bundle.primary.get('akber_filter_run')}")
    print(f"akber_filter_passed={bundle.primary.get('akber_filter_passed')}")
    print(f"trade_candidate_creation_allowed={bundle.primary.get('trade_candidate_creation_allowed')}")
    print(f"trade_candidate_created={bundle.primary.get('trade_candidate_created')}")
    print(f"paper_order_allowed={bundle.primary.get('paper_order_allowed')}")
    print(f"paper_order_created={bundle.primary.get('paper_order_created')}")
    print(f"broker_write_count={bundle.primary.get('broker_write_count')}")
    print(f"live_capital_enabled={bundle.primary.get('live_capital_enabled')}")
    print(f"proof_credit_allowed={bundle.primary.get('proof_credit_allowed')}")
    print(f"paper_growth_trial_calendar_advanced={bundle.primary.get('paper_growth_trial_calendar_advanced')}")
    if validation_errors:
        for error in validation_errors:
            print(f"error={error}")
        return 1
    print("qadam_strategy_foundry_v2_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
