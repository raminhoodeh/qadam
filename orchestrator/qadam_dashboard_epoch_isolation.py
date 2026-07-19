"""Verify that active dashboard execution records belong to one paper epoch."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    unique_errors,
    validate_authority,
)

SCHEMA_VERSION = "qadam_dashboard_epoch_isolation.v1"
ARTIFACT = "qadam_dashboard_epoch_isolation.json"

DASHBOARD_ARTIFACTS = (
    "qsase_dashboard_portfolio_value_series.json",
    "qsase_dashboard_current_portfolio.json",
    "qsase_dashboard_trading_history.json",
    "qsase_dashboard_status.json",
    "qadam_operator_dashboard_view_model.json",
    "cockpit-status.json",
    "qadam_paper_lifecycle_v3.json",
    "qadam_paper_trade_lineage.jsonl",
    "qadam_paper_postmortems_v3.jsonl",
    "qadam_paper_proof_eligibility.json",
    "qadam_paper_performance_summary.json",
    "qadam_learning_cycle_dashboard.json",
)
IDENTIFIER_KEYS = {
    "order_id",
    "trade_id",
    "position_id",
    "snapshot_id",
    "client_order_id",
}


def _collect_identifiers(value: Any, found: set[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in IDENTIFIER_KEYS and item:
                found.add(str(item))
            _collect_identifiers(item, found)
    elif isinstance(value, list):
        for item in value:
            _collect_identifiers(item, found)


def _archive_identifiers(runtime: Path) -> tuple[set[str], list[str]]:
    identifiers: set[str] = set()
    manifests: list[str] = []
    archive_root = runtime / "archive"
    if not archive_root.is_dir():
        return identifiers, manifests
    for manifest_path in sorted(archive_root.glob("*/manifest.json")):
        manifest = read_json(manifest_path)
        if manifest.get("record_origin") != "legacy_test":
            continue
        manifests.append(str(manifest_path))
        archive_dir = manifest_path.parent
        for relative in manifest.get("archived_files", []):
            path = archive_dir / str(relative)
            if path.suffix == ".json":
                _collect_identifiers(read_json(path), identifiers)
            elif path.suffix == ".jsonl":
                _collect_identifiers(read_jsonl(path), identifiers)
    return identifiers, manifests


def _dashboard_payloads(runtime: Path) -> dict[str, Any]:
    return {
        name: (
            read_jsonl(runtime / name)
            if Path(name).suffix == ".jsonl"
            else read_json(runtime / name)
        )
        for name in DASHBOARD_ARTIFACTS
    }


def build_dashboard_epoch_isolation(
    settings: Settings | None = None,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    epoch = read_json(runtime / "current_paper_epoch.json")
    clean = epoch.get("paper_epoch_kind") == "clean_operator_epoch"
    epoch_id = str(epoch.get("paper_epoch_id") or "")
    payloads = _dashboard_payloads(runtime)
    portfolio = payloads["qsase_dashboard_current_portfolio.json"]
    series = payloads["qsase_dashboard_portfolio_value_series.json"]
    history = payloads["qsase_dashboard_trading_history.json"]
    archived_ids, manifests = _archive_identifiers(runtime)
    rendered = json.dumps(payloads, sort_keys=True, separators=(",", ":"))
    leaked_ids = sorted(identifier for identifier in archived_ids if identifier in rendered)
    current_rows = [
        *portfolio.get("rows", []),
        *series.get("series", []),
        *history.get("rows", []),
    ]
    mismatched_rows = [
        {
            "row_type": row.get("row_type") or row.get("event_type") or "series_point",
            "record_id": row.get("order_id")
            or row.get("trade_id")
            or row.get("position_id")
            or row.get("timestamp"),
            "paper_epoch_id": row.get("paper_epoch_id"),
        }
        for row in current_rows
        if clean and row.get("paper_epoch_id") != epoch_id
    ]
    legacy_markers = rendered.count('"paper_epoch_kind":"legacy_test"') if clean else 0
    errors: list[str] = []
    if clean:
        contract = read_json(runtime / "qsase_dashboard_portfolio_value_series.json")
        if portfolio.get("paper_epoch_id") not in {None, epoch_id}:
            errors.append("dashboard_portfolio_epoch_id_mismatch")
        if mismatched_rows:
            errors.append("dashboard_execution_row_epoch_mismatch")
        if leaked_ids:
            errors.append("archived_testing_identifier_visible_in_dashboard")
        if legacy_markers:
            errors.append("legacy_testing_epoch_marker_visible_in_active_dashboard")
        if epoch.get("account_currency") != "USD":
            errors.append("clean_epoch_dashboard_currency_not_usd")
        if abs(float(epoch.get("starting_balance") or 0) - 100000.0) > 0.01:
            errors.append("clean_epoch_dashboard_starting_balance_not_100000")
        if contract.get("current_value") is None and contract.get("current_value_gbp") is None:
            errors.append("clean_epoch_dashboard_portfolio_value_missing")
        cockpit_epoch = payloads.get("cockpit-status.json", {}).get("paper_epoch", {})
        if cockpit_epoch.get("paper_epoch_id") != epoch_id:
            errors.append("cockpit_public_snapshot_epoch_id_mismatch")
        proof = payloads.get("qadam_paper_proof_eligibility.json", {})
        if proof.get("paper_epoch_id") not in {None, epoch_id}:
            errors.append("paper_proof_epoch_id_mismatch")
    errors = unique_errors(errors)
    result = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_dashboard_epoch_isolation",
        "generated_at": now_iso(),
        "status": (
            "passed"
            if clean and not errors
            else "not_applicable_legacy_testing_epoch"
            if not clean
            else "blocked"
        ),
        "implementation_valid": not errors,
        "clean_epoch_active": clean,
        "paper_epoch_id": epoch_id or None,
        "paper_epoch_kind": epoch.get("paper_epoch_kind") or "legacy_test",
        "current_execution_row_count": len(current_rows),
        "epoch_mismatched_row_count": len(mismatched_rows),
        "epoch_mismatched_rows": mismatched_rows[:25],
        "archive_manifest_count": len(manifests),
        "archive_identifier_count": len(archived_ids),
        "archived_identifier_leak_count": len(leaked_ids),
        "archived_identifier_leaks": leaked_ids[:25],
        "legacy_epoch_marker_count": legacy_markers,
        "dashboard_artifacts_checked": list(DASHBOARD_ARTIFACTS),
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "authority": authority_flags(),
    }
    AtomicArtifactStore(runtime).write_json(ARTIFACT, result)
    return result


def validate_dashboard_epoch_isolation(payload: dict[str, Any]) -> list[str]:
    errors = list(payload.get("validation_errors", []))
    if payload.get("clean_epoch_active") is True:
        if int(payload.get("archived_identifier_leak_count") or 0) != 0:
            errors.append("dashboard_archive_identifier_leak")
        if int(payload.get("epoch_mismatched_row_count") or 0) != 0:
            errors.append("dashboard_epoch_mismatched_rows")
    errors.extend(validate_authority(payload.get("authority", {}), prefix="dashboard_epoch"))
    return unique_errors(errors)


__all__ = [
    "ARTIFACT",
    "build_dashboard_epoch_isolation",
    "validate_dashboard_epoch_isolation",
]
