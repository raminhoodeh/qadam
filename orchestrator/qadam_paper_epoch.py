"""Canonical paper-epoch identity, archive, and isolation helpers.

This module owns local paper-epoch bookkeeping only. It cannot call brokers,
create orders, release the research lock, or enable live capital.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Iterable, Mapping
from uuid import uuid4

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    append_jsonl_durable,
    artifact_metadata,
    authority_flags,
    file_sha256,
    git_snapshot,
    now_iso,
    public_path,
    read_json,
    sha256_json,
    validate_authority,
    write_json_atomic,
)

SCHEMA_VERSION = "qadam_paper_epoch.v2"
BASELINE_SCHEMA_VERSION = "qadam_clean_epoch_preflight.v1"
ARCHIVE_SCHEMA_VERSION = "qadam_paper_epoch_archive.v1"

CURRENT_EPOCH_ARTIFACT = "current_paper_epoch.json"
EPOCH_REGISTRY_ARTIFACT = "paper_epochs.jsonl"
PREVIOUS_EPOCH_ARTIFACT = "previous_paper_epoch.json"
PREFLIGHT_BASELINE_ARTIFACT = "qadam_clean_epoch_preflight_baseline.json"
DYNAMIC_STATUS_ARTIFACT = "qadam_clean_epoch_dynamic_status.json"
TESTING_INVENTORY_ARTIFACT = "qadam_testing_epoch_inventory.json"

USD = "USD"
CLEAN_STARTING_EQUITY = 100_000.0
CLEAN_EPOCH_KINDS = {
    "clean_operator_epoch",
    "clean_experimental_operator_epoch",
}
EXPERIMENTAL_EPOCH_KIND = "clean_experimental_operator_epoch"

PAPER_EXECUTION_ARTIFACTS = (
    "alpaca_paper_mirror.json",
    "alpaca_paper_mirror.jsonl",
    "paper_account_snapshots.jsonl",
    "paper_positions.jsonl",
    "paper_closed_trades.jsonl",
    "paper_orders.jsonl",
    "paperops_alpaca_paper_post.json",
    "paperops_alpaca_paper_post_submission_ledger.json",
    "paperops_paper_lifecycle_poller.json",
    "paper_lifecycle_portfolio_postmortem.json",
    "paper_live_certification.json",
    "paper_operational_readiness.json",
    "paperops_active_paper_trading_automation.json",
    "paperops_submit_regression_guard.json",
    "phase7_demo_proof_run.json",
    "paperops_30_day_operations.json",
    "phase7_certification.json",
    "phase7_guarded_alpaca_paper_submit_path.json",
    "phase7_proof_order_staging.json",
    "phase7_proof_lifecycle_monitor.json",
    "phase7_proof_postmortem_contract.json",
    "phase7_performance_evaluator.json",
    "qadam_paper_lifecycle_v3.json",
    "qadam_paper_lineage_audit.json",
    "qadam_paper_trade_lineage.jsonl",
    "qadam_paper_postmortems_v3.jsonl",
    "qadam_paper_proof_eligibility.json",
    "qadam_paper_performance_summary.json",
    "qadam_paper_lineage_and_proof_checks.json",
    "qadam_learning_attribution_v3.jsonl",
    "qadam_learning_cycle_dashboard.json",
    "qadam_learning_cycle_events.jsonl",
    "qadam_learning_cycle_checks.json",
    "qadam_improvement_pipeline_dashboard.json",
    "qadam_improvement_proposals_v3.jsonl",
    "qadam_improvement_pipeline_checks.json",
    "qadam_stage1_learning_input.json",
    "qadam_stage1_learning_handoffs.jsonl",
    "qadam_stage1_learning_input_checks.json",
    "qsase_dashboard_portfolio_value_series.json",
    "qsase_dashboard_current_portfolio.json",
    "qsase_dashboard_trading_history.json",
    "qsase_dashboard_status.json",
    "qadam_operator_dashboard_view_model.json",
    "qadam_operator_dashboard_freshness.json",
    "qadam_operator_dashboard_truth_audit.json",
    "qadam_operator_dashboard_checks.json",
    "cockpit-status.json",
)

RESEARCH_ARTIFACT_PREFIXES = (
    "qadam_pattern_",
    "qadam_backtest_",
    "qadam_statistical_",
    "qadam_edge_",
    "qadam_strategy_",
    "qadam_source_",
    "qadam_provider_",
    "qadam_point_in_time_",
    "qadam_forward_labels",
    "qadam_quantum_",
)


def _runtime(settings: Settings | None = None) -> Path:
    active = settings or Settings.from_env()
    path = Path(active.runtime_dir)
    if not path.is_absolute():
        path = ROOT / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _record_timestamp(record: Mapping[str, Any]) -> datetime | None:
    for key in (
        "observed_at",
        "submitted_at",
        "filled_at",
        "closed_at",
        "opened_at",
        "generated_at",
        "created_at",
        "updated_at",
    ):
        parsed = _parse_timestamp(record.get(key))
        if parsed is not None:
            return parsed
    snapshot = record.get("snapshot")
    if isinstance(snapshot, Mapping):
        return _record_timestamp(snapshot)
    return None


def normalize_currency(value: Any, default: str = USD) -> str:
    code = str(value or default).strip().upper()
    return code if len(code) == 3 and code.isalpha() else default


def canonical_money(
    record: Mapping[str, Any],
    canonical_key: str,
    *legacy_keys: str,
    default: float | None = None,
) -> float | None:
    for key in (canonical_key, *legacy_keys):
        value = record.get(key)
        if value is None or value == "":
            continue
        try:
            return round(float(value), 8)
        except (TypeError, ValueError):
            continue
    return default


def broker_account_fingerprint(account: Mapping[str, Any]) -> str | None:
    """Return a non-reversible identity proof without exporting account IDs."""

    identity = str(
        account.get("id")
        or account.get("account_id")
        or account.get("account_number")
        or ""
    ).strip()
    if not identity:
        return None
    material = {
        "identity": identity,
        "currency": normalize_currency(account.get("currency")),
        "status": str(account.get("status") or "unknown").lower(),
        "paper": bool(account.get("paper", True)),
    }
    digest = hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"sha256:{digest}"


def current_epoch_path(settings: Settings | None = None) -> Path:
    return _runtime(settings) / CURRENT_EPOCH_ARTIFACT


def read_current_epoch(settings: Settings | None = None) -> dict[str, Any]:
    return read_json(current_epoch_path(settings))


def active_epoch_id(settings: Settings | None = None) -> str | None:
    epoch = read_current_epoch(settings)
    value = str(epoch.get("paper_epoch_id") or "").strip()
    return value or None


def build_epoch_record(
    *,
    epoch_kind: str,
    started_at: str,
    broker_account_fingerprint_value: str | None,
    starting_equity: float = CLEAN_STARTING_EQUITY,
    currency: str = USD,
    label: str,
    previous_epoch_id: str | None = None,
    paper_epoch_id: str | None = None,
) -> dict[str, Any]:
    currency_code = normalize_currency(currency)
    if currency_code != USD:
        raise ValueError("clean paper epoch currency must be USD")
    if abs(float(starting_equity) - CLEAN_STARTING_EQUITY) > 0.01:
        raise ValueError("clean paper epoch must start at US$100,000")
    if _parse_timestamp(started_at) is None:
        raise ValueError("paper epoch started_at must be a timezone-aware timestamp")
    epoch_id = paper_epoch_id or f"paper-epoch-{uuid4()}"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_paper_epoch",
        "paper_epoch_id": epoch_id,
        "paper_epoch_kind": epoch_kind,
        "label": label,
        "paper_epoch_started_at": started_at,
        "account_currency": currency_code,
        "display_currency": currency_code,
        "starting_equity": round(float(starting_equity), 2),
        "starting_balance": round(float(starting_equity), 2),
        "broker_account_fingerprint": broker_account_fingerprint_value,
        "previous_epoch_id": previous_epoch_id,
        "record_origin": "qadam_epoch_contract",
        "eligible_for_current_dashboard": True,
        "eligible_for_paper_proof_ledger": False,
        "paper_growth_trial_calendar_started": epoch_kind == "clean_operator_epoch",
        "paper_growth_trial_state": (
            "not_started_waiting_for_guarded_release"
            if epoch_kind == EXPERIMENTAL_EPOCH_KIND
            else "started"
            if epoch_kind == "clean_operator_epoch"
            else "not_applicable"
        ),
        "paper_growth_trial_calendar_backfilled": False,
        "simulated_elapsed_time": False,
        "created_at": now_iso(),
        "authority": authority_flags(),
        "boundary": (
            "Paper-only epoch identity. It grants no broker write, order, risk, "
            "proof, live-capital, dashboard, Telegram, LLM, or quantum authority."
        ),
    }
    errors = validate_authority(payload["authority"], prefix="paper_epoch")
    if errors:
        raise ValueError(";".join(errors))
    payload["epoch_digest"] = sha256_json(
        {key: value for key, value in payload.items() if key != "epoch_digest"}
    )
    return payload


def write_current_epoch(
    epoch: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_previous: bool = True,
) -> tuple[Path, Path]:
    runtime = _runtime(settings)
    current_path = runtime / CURRENT_EPOCH_ARTIFACT
    previous = read_json(current_path)
    if record_previous and previous:
        write_json_atomic(runtime / PREVIOUS_EPOCH_ARTIFACT, previous)
    write_json_atomic(current_path, epoch)
    registry = runtime / EPOCH_REGISTRY_ARTIFACT
    append_jsonl_durable(registry, epoch)
    return current_path, registry


def record_matches_epoch(
    record: Mapping[str, Any],
    epoch: Mapping[str, Any] | None,
    *,
    permit_legacy_testing_records: bool = True,
) -> bool:
    """Return whether a paper record belongs to the active public epoch."""

    if not epoch:
        return permit_legacy_testing_records
    epoch_id = str(epoch.get("paper_epoch_id") or "").strip()
    if not epoch_id:
        return permit_legacy_testing_records
    record_epoch_id = str(record.get("paper_epoch_id") or "").strip()
    snapshot = record.get("snapshot")
    if not record_epoch_id and isinstance(snapshot, Mapping):
        record_epoch_id = str(snapshot.get("paper_epoch_id") or "").strip()
    if record_epoch_id:
        return record_epoch_id == epoch_id
    if not is_clean_epoch_kind(epoch.get("paper_epoch_kind")):
        return permit_legacy_testing_records
    started_at = _parse_timestamp(epoch.get("paper_epoch_started_at"))
    record_at = _record_timestamp(record)
    fingerprint = str(epoch.get("broker_account_fingerprint") or "").strip()
    record_fingerprint = str(record.get("broker_account_fingerprint") or "").strip()
    if fingerprint and record_fingerprint and fingerprint != record_fingerprint:
        return False
    return bool(started_at and record_at and record_at >= started_at)


def is_clean_epoch_kind(value: Any) -> bool:
    return str(value or "") in CLEAN_EPOCH_KINDS


def filter_current_epoch_records(
    records: Iterable[dict[str, Any]],
    *,
    settings: Settings | None = None,
    epoch: Mapping[str, Any] | None = None,
    permit_legacy_testing_records: bool = True,
) -> list[dict[str, Any]]:
    active = dict(epoch or read_current_epoch(settings))
    return [
        row
        for row in records
        if record_matches_epoch(
            row,
            active,
            permit_legacy_testing_records=permit_legacy_testing_records,
        )
    ]


def _count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        with path.open("r", encoding="utf-8") as handle:
            return sum(1 for line in handle if line.strip())
    except OSError:
        return 0


def build_testing_epoch_inventory(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime(settings)
    mirror = read_json(runtime / "alpaca_paper_mirror.json")
    snapshot = mirror.get("snapshot") if isinstance(mirror.get("snapshot"), dict) else {}
    current_epoch = read_current_epoch(settings)
    rows: list[dict[str, Any]] = []
    for relative in PAPER_EXECUTION_ARTIFACTS:
        path = runtime / relative
        metadata = artifact_metadata(path)
        metadata["record_count"] = _count_jsonl(path) if path.suffix == ".jsonl" else None
        rows.append(metadata)
    fingerprint = str(
        snapshot.get("broker_account_fingerprint")
        or mirror.get("broker_account_fingerprint")
        or current_epoch.get("broker_account_fingerprint")
        or ""
    ).strip() or None
    fingerprint_source = "paper_mirror_or_existing_epoch" if fingerprint else None
    if not fingerprint:
        preflight = read_json(runtime / "qadam_clean_broker_account_preflight.json")
        preflight_fingerprint = str(
            preflight.get("broker_account_fingerprint") or ""
        ).strip()
        clearly_existing_test_account = bool(
            preflight.get("preflight_passed") is False
            and (
                int(preflight.get("order_count") or 0) > 0
                or abs(
                    float(preflight.get("equity") or CLEAN_STARTING_EQUITY)
                    - CLEAN_STARTING_EQUITY
                )
                > 0.01
            )
        )
        if preflight_fingerprint and clearly_existing_test_account:
            fingerprint = preflight_fingerprint
            fingerprint_source = "get_only_preflight_of_confirmed_testing_account"
    payload = {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "artifact_type": "qadam_testing_epoch_inventory",
        "generated_at": now_iso(),
        "paper_epoch_id": current_epoch.get("paper_epoch_id") or "legacy-testing-epoch",
        "paper_epoch_kind": current_epoch.get("paper_epoch_kind") or "legacy_test",
        "broker_account_fingerprint": fingerprint,
        "broker_account_fingerprint_source": fingerprint_source,
        "broker": snapshot.get("broker") or mirror.get("broker"),
        "account_currency": normalize_currency(
            snapshot.get("account_currency") or mirror.get("account_currency") or USD
        ),
        "current_equity": canonical_money(
            snapshot,
            "equity",
            "current_balance",
            "equity_gbp",
            "current_balance_gbp",
        ),
        "cash": canonical_money(snapshot, "cash", "cash_gbp"),
        "open_position_count": int(mirror.get("position_count") or snapshot.get("open_position_count") or 0),
        "order_count": int(mirror.get("order_count") or 0),
        "closed_trade_count": int(mirror.get("closed_trade_count") or snapshot.get("closed_trade_count") or 0),
        "observed_at": snapshot.get("observed_at"),
        "artifact_count": len(rows),
        "existing_artifact_count": sum(1 for row in rows if row.get("exists") is True),
        "artifacts": rows,
        "inventory_digest": sha256_json(rows),
        "archive_created": False,
        "eligible_for_current_dashboard_after_cutover": False,
        "eligible_for_paper_proof_ledger": False,
        "authority": authority_flags(),
        "boundary": (
            "Read-only inventory of the testing epoch. The records remain active until "
            "a separately approved, checksummed clean-epoch cutover succeeds."
        ),
    }
    write_json_atomic(runtime / TESTING_INVENTORY_ARTIFACT, payload)
    return payload


def build_preflight_baseline(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime(settings)
    inventory = build_testing_epoch_inventory(settings)
    certification = read_json(runtime / "qadam_operator_ready_edge_engine_certification.json")
    service = read_json(runtime / "qadam_operator_service_checks.json")
    source = read_json(runtime / "qadam_source_operational_state.json")
    backfill = read_json(runtime / "qadam_provider_backfill_checks.json")
    backtest = read_json(runtime / "qadam_statistical_backtest_checks.json")
    dashboard = read_json(runtime / "qadam_operator_dashboard_freshness.json")
    lock = read_json(runtime / "qadam_long_backtest_lock.json")
    payload = {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "artifact_type": "qadam_clean_epoch_preflight_baseline",
        "generated_at": now_iso(),
        "status": "baseline_recorded",
        "git": git_snapshot(ROOT),
        "research_lock_active": (
            lock.get("research_lock_active") is True
            or lock.get("status") == "active"
            or lock.get("watch_only") is True
        ),
        "paperops_watch_only": service.get("paperops_watch_only") is True,
        "operator_service_running": service.get("service_running") is True,
        "certification_state": certification.get("certification_state"),
        "certification_passed": certification.get("certification_passed") is True,
        "paper_trial_resume_allowed": certification.get("paper_trial_resume_allowed") is True,
        "source_state": {
            "configured": source.get("configured_source_count"),
            "responding": source.get("responding_source_count"),
            "fresh_scoring_eligible": source.get("fresh_scoring_eligible_count"),
            "repair_requests": source.get("repair_request_count"),
        },
        "provider_backfill": {
            "status": backfill.get("status"),
            "completed_partitions": backfill.get("completed_partition_count"),
            "total_partitions": backfill.get("total_partition_count"),
            "classified_unavailable": backfill.get("unavailable_classified_count"),
            "provider_rows": backfill.get("provider_row_count"),
        },
        "backtest": {
            "status": backtest.get("status"),
            "empirical_backtest_complete": backtest.get("empirical_backtest_complete") is True,
            "fold_result_count": backtest.get("fold_result_count"),
            "holdout_result_count": backtest.get("untouched_holdout_result_count"),
            "negative_control_validated_count": backtest.get("negative_control_validated_count"),
            "validated_edge_count": backtest.get("validated_edge_count"),
        },
        "dashboard_freshness": {
            "status": dashboard.get("status"),
            "fresh_count": dashboard.get("fresh_count"),
            "stale_count": dashboard.get("stale_count"),
            "missing_count": dashboard.get("missing_count"),
        },
        "testing_epoch_inventory_ref": f"data/runtime/{TESTING_INVENTORY_ARTIFACT}",
        "testing_epoch_inventory_digest": inventory.get("inventory_digest"),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
        "boundary": (
            "Read-only Phase 0 baseline. It does not archive, clear, reset, release, "
            "trade, write to a broker, or advance the paper calendar."
        ),
    }
    write_json_atomic(runtime / PREFLIGHT_BASELINE_ARTIFACT, payload)
    status_payload = {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "artifact_type": "qadam_clean_epoch_dynamic_status",
        "generated_at": payload["generated_at"],
        "plan_state": "readiness_blocked"
        if payload["paper_trial_resume_allowed"] is not True
        else "paper_operator_ready",
        "current_phase": "Phase 0",
        "testing_epoch_archived": False,
        "clean_epoch_active": False,
        "paperops_watch_only": payload["paperops_watch_only"],
        "research_lock_active": payload["research_lock_active"],
        "next_required_action": "repair_certification_truth_and_freshness",
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / DYNAMIC_STATUS_ARTIFACT, status_payload)
    return payload


@dataclass(frozen=True)
class ArchiveResult:
    archive_dir: Path
    manifest: dict[str, Any]
    copied_files: tuple[str, ...]


def archive_testing_epoch(
    *,
    testing_epoch_id: str,
    settings: Settings | None = None,
) -> ArchiveResult:
    """Copy active execution artifacts to a checksummed immutable archive."""

    runtime = _runtime(settings)
    safe_epoch = "".join(character for character in testing_epoch_id if character.isalnum() or character in "-_")
    if not safe_epoch:
        raise ValueError("testing epoch ID is invalid")
    archive_root = runtime / "archive"
    archive_root.mkdir(parents=True, exist_ok=True)
    final_dir = archive_root / safe_epoch
    if final_dir.exists():
        manifest = read_json(final_dir / "manifest.json")
        checksums = read_json(final_dir / "checksums.json")
        rows = checksums.get("files") if isinstance(checksums.get("files"), list) else []
        if (
            manifest.get("testing_epoch_id") != safe_epoch
            or checksums.get("aggregate_digest") != sha256_json(rows)
            or manifest.get("checksums_digest") != checksums.get("aggregate_digest")
        ):
            raise ValueError(f"existing testing epoch archive is invalid: {final_dir}")
        copied = tuple(str(value) for value in manifest.get("archived_files", []))
        expected = {
            str(row.get("artifact")): str(row.get("sha256"))
            for row in rows
            if isinstance(row, dict)
        }
        for relative in copied:
            if file_sha256(final_dir / relative) != expected.get(relative):
                raise ValueError(f"existing archive file failed verification: {relative}")
        return ArchiveResult(final_dir, manifest, copied)
    temporary_dir = Path(tempfile.mkdtemp(prefix=f".{safe_epoch}.", dir=archive_root))
    copied: list[str] = []
    try:
        checksums: list[dict[str, Any]] = []
        for relative in PAPER_EXECUTION_ARTIFACTS:
            source = runtime / relative
            if not source.is_file():
                continue
            target = temporary_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            source_hash = file_sha256(source)
            target_hash = file_sha256(target)
            if not source_hash or source_hash != target_hash:
                raise OSError(f"archive checksum mismatch: {relative}")
            copied.append(relative)
            checksums.append(
                {
                    "artifact": relative,
                    "sha256": target_hash,
                    "size_bytes": target.stat().st_size,
                }
            )
        checksums_payload = {
            "schema_version": ARCHIVE_SCHEMA_VERSION,
            "artifact_type": "qadam_testing_epoch_archive_checksums",
            "testing_epoch_id": safe_epoch,
            "created_at": now_iso(),
            "files": checksums,
            "aggregate_digest": sha256_json(checksums),
        }
        write_json_atomic(temporary_dir / "checksums.json", checksums_payload)
        manifest = {
            "schema_version": ARCHIVE_SCHEMA_VERSION,
            "artifact_type": "qadam_testing_epoch_archive_manifest",
            "testing_epoch_id": safe_epoch,
            "created_at": now_iso(),
            "archived_file_count": len(copied),
            "archived_files": copied,
            "checksums_ref": "checksums.json",
            "checksums_digest": checksums_payload["aggregate_digest"],
            "record_origin": "legacy_test",
            "eligible_for_current_dashboard": False,
            "eligible_for_paper_proof_ledger": False,
            "paper_order_created_count": 0,
            "broker_write_count": 0,
            "live_capital_enabled": False,
            "authority": authority_flags(),
            "boundary": (
                "Immutable local audit archive. Archived test records cannot appear in "
                "the current dashboard or receive paper proof ledger credit."
            ),
        }
        write_json_atomic(temporary_dir / "manifest.json", manifest)
        write_json_atomic(
            temporary_dir / "archive_receipt.json",
            {
                "schema_version": ARCHIVE_SCHEMA_VERSION,
                "artifact_type": "qadam_testing_epoch_archive_receipt",
                "testing_epoch_id": safe_epoch,
                "created_at": manifest["created_at"],
                "status": "archive_verified",
                "archived_file_count": len(copied),
                "checksums_digest": checksums_payload["aggregate_digest"],
                "idempotent_reuse_allowed_only_after_full_verification": True,
                "eligible_for_current_dashboard": False,
                "eligible_for_paper_proof_ledger": False,
                "authority": authority_flags(),
            },
        )
        os.replace(temporary_dir, final_dir)
        return ArchiveResult(final_dir, manifest, tuple(copied))
    except Exception:
        shutil.rmtree(temporary_dir, ignore_errors=True)
        raise


def clear_archived_execution_artifacts(
    archive: ArchiveResult,
    *,
    settings: Settings | None = None,
) -> tuple[str, ...]:
    """Clear only files proven present in a verified archive."""

    runtime = _runtime(settings)
    checksum_payload = read_json(archive.archive_dir / "checksums.json")
    checksum_rows = checksum_payload.get("files") if isinstance(checksum_payload.get("files"), list) else []
    expected = {str(row.get("artifact")): str(row.get("sha256")) for row in checksum_rows if isinstance(row, dict)}
    if sha256_json(checksum_rows) != checksum_payload.get("aggregate_digest"):
        raise ValueError("archive aggregate digest is invalid")
    cleared: list[str] = []
    for relative in archive.copied_files:
        archived_path = archive.archive_dir / relative
        if file_sha256(archived_path) != expected.get(relative):
            raise ValueError(f"archive file failed verification: {relative}")
        active_path = runtime / relative
        if active_path.is_file():
            active_path.unlink()
            cleared.append(relative)
    return tuple(cleared)


def research_artifact_was_archived(archive: ArchiveResult) -> bool:
    return any(
        Path(relative).name.startswith(RESEARCH_ARTIFACT_PREFIXES)
        for relative in archive.copied_files
    )


__all__ = [
    "ARCHIVE_SCHEMA_VERSION",
    "CLEAN_STARTING_EQUITY",
    "CLEAN_EPOCH_KINDS",
    "CURRENT_EPOCH_ARTIFACT",
    "DYNAMIC_STATUS_ARTIFACT",
    "EPOCH_REGISTRY_ARTIFACT",
    "EXPERIMENTAL_EPOCH_KIND",
    "PAPER_EXECUTION_ARTIFACTS",
    "PREFLIGHT_BASELINE_ARTIFACT",
    "SCHEMA_VERSION",
    "TESTING_INVENTORY_ARTIFACT",
    "USD",
    "ArchiveResult",
    "active_epoch_id",
    "archive_testing_epoch",
    "broker_account_fingerprint",
    "build_epoch_record",
    "build_preflight_baseline",
    "build_testing_epoch_inventory",
    "canonical_money",
    "clear_archived_execution_artifacts",
    "filter_current_epoch_records",
    "is_clean_epoch_kind",
    "normalize_currency",
    "read_current_epoch",
    "record_matches_epoch",
    "research_artifact_was_archived",
    "write_current_epoch",
]
