#!/usr/bin/env python3
"""Build and validate Qadam Phase 10 paper lifecycle and proof boundary."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qadam_paper_lifecycle_proof_boundary import (
    DASHBOARD_SUMMARY_ARTIFACT,
    EVENTS_ARTIFACT,
    LIFECYCLE_RECORDS_ARTIFACT,
    PRIMARY_ARTIFACT,
    PROOF_BOUNDARY_ARTIFACT,
    PROOF_RECORDS_ARTIFACT,
    _runtime_dir,
    build_and_write_paper_lifecycle_proof_boundary,
    load_paper_lifecycle_proof_boundary,
    validate_negative_paper_lifecycle_proof_boundary_probes,
    validate_paper_lifecycle_proof_boundary_bundle,
)


def main() -> int:
    settings = Settings.from_env()
    bundle, written = build_and_write_paper_lifecycle_proof_boundary(settings)
    runtime_dir = _runtime_dir(settings)

    validation_errors: list[str] = []
    for filename in (
        PRIMARY_ARTIFACT,
        LIFECYCLE_RECORDS_ARTIFACT,
        PROOF_BOUNDARY_ARTIFACT,
        PROOF_RECORDS_ARTIFACT,
        DASHBOARD_SUMMARY_ARTIFACT,
        EVENTS_ARTIFACT,
    ):
        if not (runtime_dir / filename).exists():
            validation_errors.append(f"{filename}_missing")

    validation_errors.extend(validate_paper_lifecycle_proof_boundary_bundle(bundle))
    validation_errors.extend(validate_paper_lifecycle_proof_boundary_bundle(load_paper_lifecycle_proof_boundary(settings)))
    validation_errors.extend(validate_negative_paper_lifecycle_proof_boundary_probes(settings))

    primary = bundle.primary
    proof = bundle.proof_boundary
    print(f"primary={written.get('primary')}")
    print(f"lifecycle_records={written.get('lifecycle_records')}")
    print(f"proof_boundary={written.get('proof_boundary')}")
    print(f"proof_records={written.get('proof_records')}")
    print(f"dashboard_summary={written.get('dashboard_summary')}")
    print(f"events={written.get('events')}")
    print(f"status={primary.get('status')}")
    print(f"paper_order_mirror_count={primary.get('paper_order_mirror_count')}")
    print(f"open_position_mirror_count={primary.get('open_position_mirror_count')}")
    print(f"closed_paper_trade_count={primary.get('closed_paper_trade_count')}")
    print(f"lifecycle_record_count={primary.get('lifecycle_record_count')}")
    print(f"ambiguous_lifecycle_count={primary.get('ambiguous_lifecycle_count')}")
    print(f"no_paper_order_ambiguous={primary.get('no_paper_order_ambiguous')}")
    print(f"stale_accepted_order_count={primary.get('stale_accepted_order_count')}")
    print(f"cancel_replace_needed_count={primary.get('cancel_replace_needed_count')}")
    print(f"state_counts={primary.get('state_counts')}")
    print(f"proof_boundary_status={proof.get('status')}")
    print(f"proof_record_count={proof.get('proof_record_count')}")
    print(f"proof_eligible_count={proof.get('proof_eligible_count')}")
    print(f"proof_rejected_count={proof.get('proof_rejected_count')}")
    print(
        "proof_credit_requires_real_closed_trade_with_complete_lineage="
        f"{proof.get('proof_credit_requires_real_closed_trade_with_complete_lineage')}"
    )
    print(f"backtest_shadow_or_synthetic_proof_credit_count={proof.get('backtest_shadow_or_synthetic_proof_credit_count')}")
    print(f"paper_proof_ledger_credit_allowed={proof.get('paper_proof_ledger_credit_allowed')}")
    print(f"paper_proof_ledger_credit_created={proof.get('paper_proof_ledger_credit_created')}")
    print(f"paper_order_created_count={proof.get('paper_order_created_count')}")
    print(f"broker_write_count={proof.get('broker_write_count')}")
    print(f"live_capital_enabled={proof.get('live_capital_enabled')}")
    print(f"proof_credit_allowed={proof.get('proof_credit_allowed')}")
    if validation_errors:
        for error in validation_errors:
            print(f"error={error}")
        return 1
    print("qadam_paper_lifecycle_proof_boundary_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
