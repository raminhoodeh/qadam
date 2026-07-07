#!/usr/bin/env python3
"""Build and validate Qadam next-generation Phase 5 Strategy Evidence Map."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qadam_strategy_evidence_map import (
    DASHBOARD_SUMMARY_ARTIFACT,
    EVENTS_ARTIFACT,
    PRIMARY_ARTIFACT,
    RECORDS_ARTIFACT,
    REJECTIONS_ARTIFACT,
    _runtime_dir,
    build_and_write_strategy_evidence_map,
    load_strategy_evidence_map,
    validate_negative_strategy_evidence_map_probes,
    validate_strategy_evidence_map_bundle,
)


def main() -> int:
    settings = Settings.from_env()
    bundle, written = build_and_write_strategy_evidence_map(settings)
    runtime_dir = _runtime_dir(settings)

    validation_errors: list[str] = []
    for filename in (
        PRIMARY_ARTIFACT,
        RECORDS_ARTIFACT,
        REJECTIONS_ARTIFACT,
        DASHBOARD_SUMMARY_ARTIFACT,
        EVENTS_ARTIFACT,
    ):
        if not (runtime_dir / filename).exists():
            validation_errors.append(f"{filename}_missing")

    validation_errors.extend(validate_strategy_evidence_map_bundle(bundle))
    validation_errors.extend(validate_strategy_evidence_map_bundle(load_strategy_evidence_map(settings)))
    validation_errors.extend(validate_negative_strategy_evidence_map_probes(settings))

    print(f"primary={written.get('primary')}")
    print(f"records={written.get('records')}")
    print(f"rejections={written.get('rejections')}")
    print(f"dashboard_summary={written.get('dashboard_summary')}")
    print(f"events={written.get('events')}")
    print(f"status={bundle.primary.get('status')}")
    print(f"strategy_count={bundle.primary.get('strategy_count')}")
    print(f"evidence_backed_strategy_count={bundle.primary.get('evidence_backed_strategy_count')}")
    print(f"under_evidenced_strategy_count={bundle.primary.get('under_evidenced_strategy_count')}")
    print(f"all_strategy_cards_backed_or_labeled={bundle.primary.get('all_strategy_cards_backed_or_labeled')}")
    print(f"pattern_engine_v2_state={bundle.primary.get('pattern_engine_v2_state')}")
    print(f"strategy_hypothesis_creation_allowed={bundle.primary.get('strategy_hypothesis_creation_allowed')}")
    print(f"strategy_hypothesis_created={bundle.primary.get('strategy_hypothesis_created')}")
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
    print("qadam_strategy_evidence_map_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
