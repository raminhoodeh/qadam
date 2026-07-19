#!/usr/bin/env python3
"""Build and validate OR-16 paper lifecycle, proof, and attribution."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402
from orchestrator.qadam_paper_lineage_and_proof import (  # noqa: E402
    ATTRIBUTION_ARTIFACT,
    CHECK_ARTIFACT,
    LIFECYCLE_ARTIFACT,
    LINEAGE_ARTIFACT,
    PERFORMANCE_ARTIFACT,
    POSTMORTEMS_ARTIFACT,
    PROOF_ARTIFACT,
    build_and_write_paper_lineage_and_proof,
)


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    _state, checks, errors = build_and_write_paper_lineage_and_proof(settings)
    for name in (
        LIFECYCLE_ARTIFACT,
        LINEAGE_ARTIFACT,
        POSTMORTEMS_ARTIFACT,
        PROOF_ARTIFACT,
        ATTRIBUTION_ARTIFACT,
        PERFORMANCE_ARTIFACT,
        CHECK_ARTIFACT,
    ):
        print(f"artifact={runtime / name}")
    for key in (
        "status",
        "implementation_ready",
        "broker_record_count",
        "ambiguous_order_count",
        "reconciliation_required_count",
        "every_record_has_origin_class",
        "qadam_origin_complete_lineage_count",
        "qadam_origin_verified_closed_trade_count",
        "accepted_v3_handoff_count",
        "durable_submission_identity_count",
        "mirror_only_historical_record_count",
        "proof_eligible_count",
        "mirror_record_backfill_proof_credit_count",
        "proof_credit_created_count",
        "learning_attribution_record_count",
        "applied_learning_update_count",
        "paper_order_created_count",
        "broker_write_count",
    ):
        print(f"{key}={checks[key]}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
