#!/usr/bin/env python3
"""Validate and write QSASE-2 universal source-price matrix artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_universal_source_price_matrix import (
    DASHBOARD_SUMMARY_ARTIFACT,
    EVENTS_ARTIFACT,
    HISTORY_ARTIFACT,
    PRIMARY_ARTIFACT,
    SOURCE_PRICE_EDGES_ARTIFACT,
    SOURCE_UNIVERSE_ARTIFACT,
    TRADING_UNIVERSE_ARTIFACT,
    _read_jsonl,
    _runtime_dir,
    build_and_write_qsase_universal_source_price_matrix,
    validate_negative_matrix_probes,
    validate_qsase_universal_source_price_matrix,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    settings = Settings.from_env()
    payload, edges, written, errors = build_and_write_qsase_universal_source_price_matrix(settings)
    runtime_dir = _runtime_dir(settings)

    validation_errors = list(errors)
    for filename in (
        PRIMARY_ARTIFACT,
        SOURCE_UNIVERSE_ARTIFACT,
        TRADING_UNIVERSE_ARTIFACT,
        SOURCE_PRICE_EDGES_ARTIFACT,
        EVENTS_ARTIFACT,
        HISTORY_ARTIFACT,
        DASHBOARD_SUMMARY_ARTIFACT,
    ):
        path = runtime_dir / filename
        if not path.exists():
            validation_errors.append(f"{filename}_missing")

    primary = _load_json(runtime_dir / PRIMARY_ARTIFACT)
    edge_rows = _read_jsonl(runtime_dir / SOURCE_PRICE_EDGES_ARTIFACT)
    if primary.get("generated_at") != payload.get("generated_at"):
        validation_errors.append("written_primary_generated_at_mismatch")
    if len(edge_rows) != payload.get("source_price_edge_count"):
        validation_errors.append("written_edge_count_mismatch")
    validation_errors.extend(validate_qsase_universal_source_price_matrix(primary, edge_rows))
    validation_errors.extend(validate_negative_matrix_probes())

    print(f"artifact={written.get('matrix')}")
    print(f"source_universe={written.get('source_universe')}")
    print(f"trading_universe={written.get('trading_universe')}")
    print(f"source_price_edges={written.get('source_price_edges')}")
    print(f"dashboard_summary={written.get('dashboard_summary')}")
    print(f"phase_status={written.get('phase_status')}")
    print(f"implementation_log={written.get('implementation_log')}")
    print(f"status={payload.get('status')}")
    print(f"source_count={payload.get('source_universe', {}).get('source_count')}")
    print(f"watched_market_count={payload.get('trading_universe', {}).get('watched_market_count')}")
    print(f"source_price_edge_count={payload.get('source_price_edge_count')}")
    print(f"credential_gated_source_count={payload.get('source_universe', {}).get('credential_gated_source_count')}")
    print(f"paperable_instrument_count={payload.get('trading_universe', {}).get('market_count_with_paper_route_availability')}")
    if validation_errors:
        for error in validation_errors:
            print(f"error={error}")
        return 1
    print("qsase_universal_source_price_matrix_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
