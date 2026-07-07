#!/usr/bin/env python3
"""Build and validate Qadam Phase 11 Learning Attribution V2 artifacts."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qadam_learning_attribution_v2 import (
    DASHBOARD_SUMMARY_ARTIFACT,
    EVENTS_ARTIFACT,
    PRIMARY_ARTIFACT,
    PROPOSALS_ARTIFACT,
    PROPOSAL_RECORDS_ARTIFACT,
    RECORDS_ARTIFACT,
    _runtime_dir,
    build_and_write_learning_attribution_v2,
    load_learning_attribution_v2,
    validate_learning_attribution_v2_bundle,
    validate_negative_learning_attribution_v2_probes,
)


def main() -> int:
    settings = Settings.from_env()
    bundle, written = build_and_write_learning_attribution_v2(settings)
    runtime_dir = _runtime_dir(settings)

    validation_errors: list[str] = []
    for filename in (
        PRIMARY_ARTIFACT,
        RECORDS_ARTIFACT,
        PROPOSALS_ARTIFACT,
        PROPOSAL_RECORDS_ARTIFACT,
        DASHBOARD_SUMMARY_ARTIFACT,
        EVENTS_ARTIFACT,
    ):
        if not (runtime_dir / filename).exists():
            validation_errors.append(f"{filename}_missing")

    validation_errors.extend(validate_learning_attribution_v2_bundle(bundle))
    validation_errors.extend(validate_learning_attribution_v2_bundle(load_learning_attribution_v2(settings)))
    validation_errors.extend(validate_negative_learning_attribution_v2_probes())

    primary = bundle.primary
    proposals = bundle.proposals
    print(f"primary={written.get('primary')}")
    print(f"records={written.get('records')}")
    print(f"proposals={written.get('proposals')}")
    print(f"proposal_records={written.get('proposal_records')}")
    print(f"dashboard_summary={written.get('dashboard_summary')}")
    print(f"events={written.get('events')}")
    print(f"status={primary.get('status')}")
    print(f"attribution_record_count={primary.get('attribution_record_count')}")
    print(f"backtest_record_count={primary.get('backtest_record_count')}")
    print(f"shadow_record_count={primary.get('shadow_record_count')}")
    print(f"akber_record_count={primary.get('akber_record_count')}")
    print(f"router_record_count={primary.get('router_record_count')}")
    print(f"paperops_record_count={primary.get('paperops_record_count')}")
    print(f"missed_opportunity_record_count={primary.get('missed_opportunity_record_count')}")
    print(f"paper_trade_outcome_record_count={primary.get('paper_trade_outcome_record_count')}")
    print(f"proof_rejected_record_count={primary.get('proof_rejected_record_count')}")
    print(f"hold_record_count={primary.get('hold_record_count')}")
    print(f"veto_record_count={primary.get('veto_record_count')}")
    print(f"system_defect_record_count={primary.get('system_defect_record_count')}")
    print(f"outcome_type_counts={primary.get('outcome_type_counts')}")
    print(f"proposal_count={primary.get('proposal_count')}")
    print(f"proposal_type_counts={proposals.get('proposal_type_counts')}")
    print(f"proposal_applied_count={primary.get('proposal_applied_count')}")
    print(f"applied_update_count={primary.get('applied_update_count')}")
    print(f"authority_mutation_count={primary.get('authority_mutation_count')}")
    print(f"learning_outputs_are_proposals_only={primary.get('learning_outputs_are_proposals_only')}")
    print(f"paper_order_created_count={primary.get('paper_order_created_count')}")
    print(f"broker_write_count={primary.get('broker_write_count')}")
    print(f"proof_credit_allowed={primary.get('proof_credit_allowed')}")
    print(f"live_capital_enabled={primary.get('live_capital_enabled')}")
    if validation_errors:
        for error in validation_errors:
            print(f"error={error}")
        return 1
    print("qadam_learning_attribution_v2_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
