#!/usr/bin/env python3
"""Build and validate Qadam next-generation Phase 9 Router V2 and PaperOps handoff."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qadam_router_v2_paperops_handoff import (
    DASHBOARD_SUMMARY_ARTIFACT,
    DECISIONS_ARTIFACT,
    EVENTS_ARTIFACT,
    HANDOFF_RECORDS_ARTIFACT,
    PRIMARY_ARTIFACT,
    REJECTED_HANDOFFS_ARTIFACT,
    SCOREBOARD_ARTIFACT,
    WHY_NOT_TRADING_NOW_ARTIFACT,
    _runtime_dir,
    build_and_write_router_v2_paperops_handoff,
    load_router_v2_paperops_handoff,
    validate_negative_router_v2_paperops_handoff_probes,
    validate_router_v2_paperops_handoff_bundle,
)


def main() -> int:
    settings = Settings.from_env()
    bundle, written = build_and_write_router_v2_paperops_handoff(settings)
    runtime_dir = _runtime_dir(settings)

    validation_errors: list[str] = []
    for filename in (
        PRIMARY_ARTIFACT,
        DECISIONS_ARTIFACT,
        HANDOFF_RECORDS_ARTIFACT,
        REJECTED_HANDOFFS_ARTIFACT,
        WHY_NOT_TRADING_NOW_ARTIFACT,
        SCOREBOARD_ARTIFACT,
        DASHBOARD_SUMMARY_ARTIFACT,
        EVENTS_ARTIFACT,
    ):
        if not (runtime_dir / filename).exists():
            validation_errors.append(f"{filename}_missing")

    validation_errors.extend(validate_router_v2_paperops_handoff_bundle(bundle))
    validation_errors.extend(validate_router_v2_paperops_handoff_bundle(load_router_v2_paperops_handoff(settings)))
    validation_errors.extend(validate_negative_router_v2_paperops_handoff_probes(settings))

    primary = bundle.primary
    print(f"primary={written.get('primary')}")
    print(f"decisions={written.get('decisions')}")
    print(f"handoff_records={written.get('handoff_records')}")
    print(f"rejected_handoffs={written.get('rejected_handoffs')}")
    print(f"why_not_trading_now={written.get('why_not_trading_now')}")
    print(f"scoreboard={written.get('scoreboard')}")
    print(f"dashboard_summary={written.get('dashboard_summary')}")
    print(f"events={written.get('events')}")
    print(f"status={primary.get('status')}")
    print(f"setup_count={primary.get('setup_count')}")
    print(f"decision_count={primary.get('decision_count')}")
    print(f"setup_without_decision_count={primary.get('setup_without_decision_count')}")
    print(f"duplicate_decision_count={primary.get('duplicate_decision_count')}")
    print(f"invalid_final_state_count={primary.get('invalid_final_state_count')}")
    print(f"all_setups_have_exactly_one_final_state={primary.get('all_setups_have_exactly_one_final_state')}")
    print(f"final_state_counts={primary.get('final_state_counts')}")
    print(f"paper_review_candidate_count={primary.get('paper_review_candidate_count')}")
    print(f"clean_paper_review_candidate_count={primary.get('clean_paper_review_candidate_count')}")
    print(f"handoff_record_count={primary.get('handoff_record_count')}")
    print(f"rejected_handoff_count={primary.get('rejected_handoff_count')}")
    print(
        "only_clean_paper_review_candidates_reach_paperops="
        f"{primary.get('only_clean_paper_review_candidates_reach_paperops')}"
    )
    print(f"duplicate_idempotency_count={primary.get('duplicate_idempotency_count')}")
    print(f"duplicate_exposure_count={primary.get('duplicate_exposure_count')}")
    print(f"idempotency_material_count={primary.get('idempotency_material_count')}")
    print(f"why_not_trading_now_reason={primary.get('why_not_trading_now_reason')}")
    print(f"paper_order_created={primary.get('paper_order_created')}")
    print(f"paper_order_created_count={primary.get('paper_order_created_count')}")
    print(f"qualified_setup_created={primary.get('qualified_setup_created')}")
    print(f"broker_write_count={primary.get('broker_write_count')}")
    print(f"live_capital_enabled={primary.get('live_capital_enabled')}")
    print(f"proof_credit_allowed={primary.get('proof_credit_allowed')}")
    print(f"paper_proof_ledger_credit_allowed={primary.get('paper_proof_ledger_credit_allowed')}")
    print(f"paper_growth_trial_calendar_advanced={primary.get('paper_growth_trial_calendar_advanced')}")
    if validation_errors:
        for error in validation_errors:
            print(f"error={error}")
        return 1
    print("qadam_router_v2_paperops_handoff_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
