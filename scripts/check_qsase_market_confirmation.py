#!/usr/bin/env python3
"""Validate and write QSASE market confirmation artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_market_confirmation import (
    AKBER_COMPLETENESS_ARTIFACT,
    DASHBOARD_SUMMARY_ARTIFACT,
    PACKETS_ARTIFACT,
    PRIMARY_ARTIFACT,
    REPAIR_QUEUE_ARTIFACT,
    _runtime_dir,
    build_and_write_market_confirmation,
    validate_market_confirmation,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def main() -> int:
    settings = Settings.from_env()
    payload, packets, written, errors = build_and_write_market_confirmation(settings)
    runtime = _runtime_dir(settings)
    validation_errors = list(errors)

    for filename in (
        PRIMARY_ARTIFACT,
        PACKETS_ARTIFACT,
        AKBER_COMPLETENESS_ARTIFACT,
        REPAIR_QUEUE_ARTIFACT,
        DASHBOARD_SUMMARY_ARTIFACT,
    ):
        if not (runtime / filename).exists():
            validation_errors.append(f"{filename}_missing")

    loaded = _load_json(runtime / PRIMARY_ARTIFACT)
    written_packets = _read_jsonl(runtime / PACKETS_ARTIFACT)
    validation_errors.extend(validate_market_confirmation(loaded, written_packets))
    if len(written_packets) != payload.get("packet_count"):
        validation_errors.append("written_packet_count_mismatch")

    print(f"artifact={written.get('primary')}")
    print(f"packets={written.get('packets')}")
    print(f"akber_input_completeness={written.get('akber_input_completeness')}")
    print(f"repair_queue={written.get('repair_queue')}")
    print(f"dashboard_summary={written.get('dashboard_summary')}")
    print(f"status={payload.get('status')}")
    print(f"packet_count={payload.get('packet_count')}")
    print(f"complete_packet_count={payload.get('complete_packet_count')}")
    print(f"incomplete_packet_count={payload.get('incomplete_packet_count')}")
    print(f"repair_request_count={payload.get('repair_request_count')}")
    print(f"akber_missing_context_count={payload.get('akber_missing_context_count')}")
    print(f"paper_order_created_count={payload.get('paper_order_created_count')}")
    print(f"broker_write_allowed={payload.get('broker_write_allowed')}")
    print(f"live_capital_enabled={payload.get('live_capital_enabled')}")
    for key, value in payload.get("missing_input_counts", {}).items():
        print(f"missing_input={key}:{value}")
    for blocker in payload.get("blockers", []):
        print(f"blocker={blocker}")

    if validation_errors:
        for error in sorted(set(validation_errors)):
            print(f"error={error}")
        return 1
    print("qsase_market_confirmation_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

