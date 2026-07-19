#!/usr/bin/env python3
"""Build and validate OR-3 provider-backed backfill preflight and manifests."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402
from orchestrator.qadam_provider_backfill import (  # noqa: E402
    CHECK_ARTIFACT,
    COVERAGE_ARTIFACT,
    DASHBOARD_ARTIFACT,
    ERRORS_ARTIFACT,
    PRICE_MANIFEST_ARTIFACT,
    SOURCE_MANIFEST_ARTIFACT,
    build_and_write_provider_backfill_baseline,
)


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    _coverage, checks, errors = build_and_write_provider_backfill_baseline(settings)
    for name in (
        SOURCE_MANIFEST_ARTIFACT,
        PRICE_MANIFEST_ARTIFACT,
        COVERAGE_ARTIFACT,
        ERRORS_ARTIFACT,
        DASHBOARD_ARTIFACT,
        CHECK_ARTIFACT,
    ):
        print(f"artifact={runtime / name}")
    print(f"status={checks['status']}")
    print(f"coverage_state={checks['coverage_state']}")
    print(f"implementation_ready={checks['implementation_ready']}")
    print(f"or3_acceptance_passed={checks['or3_acceptance_passed']}")
    print(
        "provider_history_acquisition_contract_complete="
        f"{checks['provider_history_acquisition_contract_complete']}"
    )
    print(f"empirical_provider_evidence_complete={checks['empirical_provider_evidence_complete']}")
    print(f"source_count={checks['source_count']}")
    print(f"instrument_count={checks['instrument_count']}")
    print(f"total_partition_count={checks['total_partition_count']}")
    print(f"completed_partition_count={checks['completed_partition_count']}")
    print(
        "unavailable_classified_partition_count="
        f"{checks['unavailable_classified_partition_count']}"
    )
    print(f"remaining_partition_count={checks['remaining_partition_count']}")
    print(f"provider_row_count={checks['provider_row_count']}")
    print(f"network_called_by_checker={checks['network_called_by_checker']}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
