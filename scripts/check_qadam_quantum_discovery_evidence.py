#!/usr/bin/env python3
"""Verify Wave B point-in-time evidence and current empirical readiness."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_quantum_discovery_evidence import (  # noqa: E402
    build_chronological_split,
    build_point_in_time_feature,
    build_point_in_time_foundation,
    validate_chronological_split,
    validate_point_in_time_foundation,
    write_point_in_time_foundation,
)


def _contract_records() -> list[dict]:
    start = datetime(2025, 1, 1, 12, tzinfo=timezone.utc)
    records = []
    for index in range(20):
        cutoff = start + timedelta(days=index)
        feature = build_point_in_time_feature(
            provider="contract-fixture",
            source_key="wave-b-contract-source",
            source_artifact_ref=f"contract://wave-b/evidence/{index}",
            raw_content={"contract_fixture": index, "value": index / 10},
            event_time=(cutoff - timedelta(hours=3)).isoformat(),
            publication_time=(cutoff - timedelta(hours=2)).isoformat(),
            ingestion_time=(cutoff - timedelta(hours=1)).isoformat(),
            source_vintage=(cutoff - timedelta(hours=2)).isoformat(),
            market_symbol="BNO",
            market_timestamp=(cutoff - timedelta(minutes=30)).isoformat(),
            as_of=cutoff.isoformat(),
            feature_name="contract_feature",
            feature_value=index / 10,
            parser_version="contract-parser.v1",
        )
        records.append(feature.to_dict())
    return records


def main() -> int:
    split = build_chronological_split(
        _contract_records(),
        outcome_window_seconds=86_400,
        embargo_seconds=86_400,
    )
    split_errors = validate_chronological_split(split)
    foundation = build_point_in_time_foundation()
    foundation_errors = validate_point_in_time_foundation(foundation)
    artifact = write_point_in_time_foundation(foundation)

    print(f"quantum_evidence_status={foundation['status']}")
    print(f"quantum_evidence_artifact={artifact}")
    print(
        "quantum_evidence_empirical_ready="
        f"{foundation['empirical_evidence_ready']}"
    )
    print(
        "quantum_evidence_eligible_window_count="
        f"{foundation['alignment_truth']['eligible_point_in_time_window_count']}"
    )
    print(
        "quantum_evidence_provider_row_count="
        f"{foundation['provider_history_truth']['provider_row_count']}"
    )
    print(
        "quantum_evidence_leakage_violation_count="
        f"{foundation['leakage_truth']['leakage_violation_count']}"
    )
    print(f"quantum_evidence_blockers={foundation['blockers']}")
    print(f"quantum_evidence_split_identity={split['split_identity']}")
    print(f"quantum_evidence_split_counts={split['partition_counts']}")
    print(f"quantum_evidence_split_errors={split_errors}")
    print(f"quantum_evidence_foundation_errors={foundation_errors}")
    return 0 if not split_errors and not foundation_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
