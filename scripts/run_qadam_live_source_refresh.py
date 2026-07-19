#!/usr/bin/env python3
"""Refresh only due read-only source adapters and preserve observation provenance."""

from __future__ import annotations

import argparse
from dataclasses import fields
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import authority_flags, now_iso, read_json, write_json_atomic
from scripts.check_phase1_live_source_hardening import (
    LiveSourceValidation,
    PROMOTED_SOURCE_KEYS,
    _contains_secret_like_value,
    build_report_from_validations,
    validate_source,
    write_report,
)
from world_monitor.source_registry import SOURCE_SPECS

SCHEMA_VERSION = "qadam_live_source_scheduler.v1"
STATE_ARTIFACT = "qadam_live_source_scheduler.json"
RECEIPT_ARTIFACT = "qadam_live_source_refresh_receipt.json"


def _parse(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _cadence_seconds(value: str) -> int:
    text = value.lower()
    if "weekly" in text:
        return 7 * 86400
    if "daily" in text:
        return 86400
    if "6 hours" in text:
        return 6 * 3600
    if "3 hours" in text:
        return 3 * 3600
    if "hourly" in text:
        return 3600
    if "30 minutes" in text or "20-30" in text:
        return 1800
    if "15 minutes" in text:
        return 900
    if "10 minutes" in text:
        return 600
    if "5 minutes" in text or "1-5 minutes" in text:
        return 300
    if "real-time" in text or "5 seconds" in text or "derived" in text:
        return 300
    return 3600


def _validation_from_dict(payload: dict[str, Any]) -> LiveSourceValidation | None:
    required = {field.name for field in fields(LiveSourceValidation)}
    if not required.issubset(payload):
        return None
    return LiveSourceValidation(**{key: payload[key] for key in required})


def run_refresh(*, max_sources: int = 10, force_all: bool = False) -> dict[str, Any]:
    settings = Settings.from_env()
    runtime = Path(settings.runtime_dir)
    if not runtime.is_absolute():
        runtime = ROOT / runtime
    runtime.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    checked_at = now.isoformat()
    spec_by_key = {spec.key: spec for spec in SOURCE_SPECS}
    previous_report = read_json(runtime / "phase1_live_source_validation.json")
    previous = {
        row.get("source_key"): row
        for row in previous_report.get("validations", [])
        if isinstance(row, dict) and row.get("source_key")
    }
    due: list[tuple[float, str]] = []
    for source_key in PROMOTED_SOURCE_KEYS:
        prior = previous.get(source_key, {})
        last_checked = _parse(prior.get("checked_at"))
        cadence = _cadence_seconds(spec_by_key[source_key].cadence)
        overdue = float("inf") if last_checked is None else (now - last_checked).total_seconds() - cadence
        if force_all or last_checked is None or overdue >= 0:
            due.append((overdue, source_key))
    due.sort(key=lambda item: (-item[0], item[1]))
    selected = [source_key for _overdue, source_key in due[: max(1, max_sources)]]

    validations: dict[str, LiveSourceValidation] = {}
    for source_key, row in previous.items():
        restored = _validation_from_dict(row)
        if restored is not None:
            validations[source_key] = restored
    for source_key in selected:
        validations[source_key] = validate_source(
            source_key,
            settings=settings,
            live=True,
            checked_at=checked_at,
        )

    ordered = tuple(
        validations[source_key]
        for source_key in PROMOTED_SOURCE_KEYS
        if source_key in validations
    )
    report = build_report_from_validations(ordered, checked_at=checked_at, live=True)
    report["scheduler"] = {
        "selected_source_count": len(selected),
        "selected_sources": selected,
        "due_source_count_before_run": len(due),
        "remaining_due_source_count": max(0, len(due) - len(selected)),
        "force_all": force_all,
    }
    if _contains_secret_like_value(report):
        raise ValueError("live source refresh report contains a secret-like value")
    write_report(settings, report)

    state = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_live_source_scheduler",
        "generated_at": now_iso(),
        "status": "active",
        "selected_source_count": len(selected),
        "selected_sources": selected,
        "due_source_count_before_run": len(due),
        "remaining_due_source_count": max(0, len(due) - len(selected)),
        "tracked_source_count": len(ordered),
        "provider_backed_freshness_evidence_count": report[
            "provider_backed_freshness_evidence_count"
        ],
        "sample_fixture_count": report["sample_fixture_count"],
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / STATE_ARTIFACT, state)
    receipt = {
        **state,
        "artifact_type": "qadam_live_source_refresh_receipt",
        "degraded_source_count": report["degraded_count"],
        "missing_credentials_count": report["missing_credentials_count"],
        "boundary": (
            "Read-only due-source refresh. Health checks and fixtures never count "
            "as fresh evidence, source quorum, candidates, orders, or proof."
        ),
    }
    write_json_atomic(runtime / RECEIPT_ARTIFACT, receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-sources", type=int, default=10)
    parser.add_argument("--force-all", action="store_true")
    args = parser.parse_args()
    receipt = run_refresh(max_sources=args.max_sources, force_all=args.force_all)
    print(f"live_source_refresh_status={receipt['status']}")
    print(f"live_source_refresh_selected={receipt['selected_source_count']}")
    print(f"live_source_refresh_remaining_due={receipt['remaining_due_source_count']}")
    print(
        "live_source_refresh_provider_backed_evidence="
        f"{receipt['provider_backed_freshness_evidence_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
