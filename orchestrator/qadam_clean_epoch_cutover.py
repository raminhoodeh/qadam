"""Transactional, fail-closed clean paper-epoch cutover.

The default interface is a dry-run.  Execution requires explicit operator
approval and fresh passing edge, shadow, soak, broker, lock, and service-pause
gates.  It writes only local paper-state artifacts and never calls a broker.
"""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
from typing import Any, Callable

from orchestrator.config import Settings
from orchestrator.paper_account import (
    AlpacaReadOnlyPaperMirror,
    PaperAccountMirrorStore,
    initial_paper_account_snapshot,
)
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    append_jsonl_durable,
    authority_flags,
    file_sha256,
    git_snapshot,
    now_iso,
    read_json,
    runtime_dir,
    sha256_json,
    unique_errors,
    write_json_atomic,
)
from orchestrator.qadam_experimental_paper_policy import POLICY_VERSION
from orchestrator.qadam_paper_epoch import (
    CLEAN_STARTING_EQUITY,
    CURRENT_EPOCH_ARTIFACT,
    EPOCH_REGISTRY_ARTIFACT,
    EXPERIMENTAL_EPOCH_KIND,
    PREVIOUS_EPOCH_ARTIFACT,
    PAPER_EXECUTION_ARTIFACTS,
    ArchiveResult,
    archive_testing_epoch,
    build_epoch_record,
    clear_archived_execution_artifacts,
    read_current_epoch,
    research_artifact_was_archived,
    write_current_epoch,
)

SCHEMA_VERSION = "qadam_clean_epoch_cutover.v1"
READINESS_ARTIFACT = "qadam_clean_epoch_cutover_readiness.json"
RECEIPT_ARTIFACT = "qadam_clean_epoch_cutover_receipt.json"
ROLLBACK_ARTIFACT = "qadam_clean_epoch_rollback_receipt.json"
DRY_RUN_ARTIFACT = "qadam_clean_epoch_cutover_dry_run.json"
LOCK_ARTIFACT = ".qadam-clean-epoch-cutover.lock"
EXPERIMENTAL_READINESS_ARTIFACT = "qadam_experimental_epoch_cutover_readiness.json"
EXPERIMENTAL_APPROVAL_ARTIFACT = "qadam_experimental_epoch_cutover_approval.json"
EXPERIMENTAL_APPROVAL_TTL_SECONDS = 900


def _parse(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _fresh(payload: dict[str, Any], seconds: int = 1800) -> bool:
    generated = _parse(payload.get("generated_at"))
    if generated is None:
        return False
    return (datetime.now(timezone.utc) - generated).total_seconds() <= seconds


def _experimental_archive_id(inventory: dict[str, Any]) -> str:
    digest = str(inventory.get("inventory_digest") or "missing")[:16]
    epoch_id = str(inventory.get("paper_epoch_id") or "legacy-testing-epoch")
    safe_epoch = "".join(
        character for character in epoch_id if character.isalnum() or character in "-_"
    )
    return f"{safe_epoch}-archive-{digest}"


def prepare_experimental_testing_archive(
    settings: Settings | None = None,
) -> ArchiveResult:
    """Prepare, but do not activate, the immutable legacy execution archive."""

    from orchestrator.qadam_paper_epoch import build_testing_epoch_inventory

    inventory = build_testing_epoch_inventory(settings)
    archive = archive_testing_epoch(
        testing_epoch_id=_experimental_archive_id(inventory),
        settings=settings,
    )
    if research_artifact_was_archived(archive):
        raise RuntimeError("research artifact entered testing-epoch archive")
    return archive


def _experimental_archive_state(runtime: Path, inventory: dict[str, Any]) -> dict[str, Any]:
    archive_id = _experimental_archive_id(inventory)
    archive_dir = runtime / "archive" / archive_id
    manifest = read_json(archive_dir / "manifest.json")
    checksums = read_json(archive_dir / "checksums.json")
    rows = checksums.get("files") if isinstance(checksums.get("files"), list) else []
    digest = checksums.get("aggregate_digest")
    valid = bool(
        manifest.get("testing_epoch_id") == archive_id
        and manifest.get("checksums_digest") == digest
        and digest == sha256_json(rows)
    )
    if valid:
        expected = {
            str(row.get("artifact")): str(row.get("sha256"))
            for row in rows
            if isinstance(row, dict)
        }
        for relative in manifest.get("archived_files", []):
            if file_sha256(archive_dir / str(relative)) != expected.get(str(relative)):
                valid = False
                break
    return {
        "archive_id": archive_id,
        "archive_dir": archive_dir,
        "manifest": manifest,
        "checksums": checksums,
        "digest": digest,
        "valid": valid,
    }


def build_experimental_epoch_cutover_readiness(
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Build the edge-independent, broker-bound experimental cutover gate."""

    runtime = runtime_dir(settings)
    policy = read_json(runtime / "qadam_experimental_paper_policy.json")
    migration = read_json(runtime / "qadam_experimental_contract_migration.json")
    provider = read_json(runtime / "qadam_provider_backfill_checks.json")
    backtest = read_json(runtime / "qadam_statistical_backtest_checks.json")
    preflight = read_json(runtime / "qadam_clean_broker_account_preflight.json")
    quiescence = read_json(runtime / "qadam_clean_epoch_quiescence.json")
    lock = read_json(runtime / "qadam_long_backtest_lock.json")
    risk = read_json(runtime / "qadam_portfolio_risk_state.json")
    inventory = read_json(runtime / "qadam_testing_epoch_inventory.json")
    dashboard_receipt_path = runtime / "dashboard-deployment-receipt.json"
    archive = _experimental_archive_state(runtime, inventory)
    blockers: list[str] = []
    if policy.get("policy_version") != POLICY_VERSION:
        blockers.append("experimental_policy_not_frozen")
    if migration.get("status") != "passed_legacy_defaults_fail_closed":
        blockers.append("experimental_contract_migration_not_passed")
    if provider.get("status") != "passed" or provider.get("or3_acceptance_passed") is not True:
        blockers.append("provider_backfill_certification_not_passed")
    if backtest.get("status") != "passed" or backtest.get("empirical_backtest_complete") is not True:
        blockers.append("statistical_backtest_certification_not_passed")
    if preflight.get("preflight_passed") is not True or not _fresh(preflight, 300):
        blockers.append("fresh_clean_broker_account_preflight_not_passed")
    if quiescence.get("quiescent") is not True or not _fresh(quiescence, 300):
        blockers.append("clean_epoch_quiescence_not_fresh_or_not_passed")
    if not (
        lock.get("status") == "active"
        and lock.get("paperops_watch_only_mode") is True
    ):
        blockers.append("research_lock_not_active_watch_only")
    if risk.get("policy_version") != "qadam-paper-portfolio-risk.3-frozen-discovery-5k":
        blockers.append("portfolio_risk_policy_not_frozen")
    if float(risk.get("absolute_trade_ceiling_usd") or 0) != 5000.0:
        blockers.append("portfolio_risk_trade_ceiling_not_5000_usd")
    if not archive["valid"]:
        blockers.append("testing_epoch_archive_not_prepared_or_invalid")
    if not inventory.get("inventory_digest"):
        blockers.append("testing_epoch_inventory_missing")
    blockers = unique_errors(blockers)
    git = git_snapshot(Path(__file__).resolve().parents[1])
    binding = {
        "broker_account_fingerprint": preflight.get("broker_account_fingerprint"),
        "broker_provider_response_digest": preflight.get("provider_response_digest"),
        "archive_digest": archive["digest"],
        "inventory_digest": inventory.get("inventory_digest"),
        "policy_version": POLICY_VERSION,
        "risk_policy_version": risk.get("policy_version"),
        "code_commit": git.get("head"),
        "dashboard_release_sha256": file_sha256(dashboard_receipt_path),
    }
    payload = {
        "schema_version": "qadam_experimental_epoch_cutover_readiness.v1",
        "artifact_type": "qadam_experimental_epoch_cutover_readiness",
        "generated_at": now_iso(),
        "status": "ready_for_explicit_operator_approval" if not blockers else "blocked",
        "cutover_ready": not blockers,
        "requires_validated_edge": False,
        "requires_completed_forward_shadow": False,
        "requires_completed_soak": False,
        "clean_broker_preflight_passed": preflight.get("preflight_passed") is True,
        "clean_broker_account_fingerprint": preflight.get("broker_account_fingerprint"),
        "archive_id": archive["archive_id"],
        "archive_digest": archive["digest"],
        "policy_version": POLICY_VERSION,
        "starting_balance": CLEAN_STARTING_EQUITY,
        "account_currency": "USD",
        "binding": binding,
        "binding_digest": sha256_json(binding),
        "blocker_count": len(blockers),
        "blockers": blockers,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "paper_calendar_advanced": False,
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / EXPERIMENTAL_READINESS_ARTIFACT, payload)
    return payload


def build_experimental_epoch_cutover_approval(
    readiness: dict[str, Any],
    *,
    operator_approved: bool,
) -> dict[str, Any]:
    generated_at = now_iso()
    generated = _parse(generated_at)
    assert generated is not None
    expires_at = datetime.fromtimestamp(
        generated.timestamp() + EXPERIMENTAL_APPROVAL_TTL_SECONDS,
        tz=timezone.utc,
    ).isoformat()
    approved = bool(operator_approved and readiness.get("cutover_ready") is True)
    return {
        "schema_version": "qadam_experimental_epoch_cutover_approval.v1",
        "artifact_type": "qadam_experimental_epoch_cutover_approval",
        "generated_at": generated_at,
        "expires_at": expires_at,
        "status": "approved" if approved else "not_approved",
        "operator_approval_requested": operator_approved,
        "operator_approved": approved,
        "approval_rejected_by_safety_gates": bool(
            operator_approved and readiness.get("cutover_ready") is not True
        ),
        "binding": readiness.get("binding", {}),
        "binding_digest": readiness.get("binding_digest"),
        "policy_version": POLICY_VERSION,
        "paper_only": True,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }


def validate_experimental_epoch_cutover_approval(
    approval: dict[str, Any], readiness: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    if approval.get("operator_approved") is not True:
        errors.append("explicit_operator_cutover_approval_missing")
    expires_at = _parse(approval.get("expires_at"))
    if expires_at is None or expires_at <= datetime.now(timezone.utc):
        errors.append("experimental_cutover_approval_expired")
    if approval.get("binding_digest") != readiness.get("binding_digest"):
        errors.append("experimental_cutover_approval_binding_changed")
    if approval.get("policy_version") != POLICY_VERSION:
        errors.append("experimental_cutover_approval_policy_changed")
    if approval.get("live_capital_enabled") is not False:
        errors.append("experimental_cutover_approval_enabled_live_capital")
    return unique_errors(errors)


def build_clean_epoch_cutover_readiness(
    settings: Settings | None = None,
    *,
    require_service_paused: bool = False,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    cert = read_json(runtime / "qadam_operator_ready_edge_engine_certification.json")
    edge = read_json(runtime / "qadam_edge_registry_v3.json")
    shadow = read_json(runtime / "qadam_forward_shadow_checks.json")
    soak = read_json(runtime / "qadam_operator_soak_v2.json")
    if not soak:
        soak = read_json(runtime / "qadam_operator_soak_test.json")
    preflight = read_json(runtime / "qadam_clean_broker_account_preflight.json")
    lock = read_json(runtime / "qadam_long_backtest_lock.json")
    service = read_json(runtime / "qadam_operator_service_checks.json")
    blockers: list[str] = []
    if cert.get("certification_passed") is not True:
        blockers.append("operator_ready_certification_not_passed")
    if cert.get("paper_trial_resume_allowed") is not True:
        blockers.append("paper_trial_resume_not_allowed")
    if edge.get("paper_operator_edge_gate_passed") is not True:
        blockers.append("validated_edge_gate_not_passed")
    if shadow.get("promotion_ready") is not True:
        blockers.append("real_forward_shadow_not_promotion_ready")
    soak_complete = bool(
        soak.get("soak_complete") is True
        or soak.get("multi_session_soak_complete") is True
    )
    soak_sessions = int(
        soak.get("completed_real_session_count")
        or soak.get("real_elapsed_session_count")
        or 0
    )
    if not soak_complete or soak_sessions < 7:
        blockers.append("seven_real_session_soak_incomplete")
    if preflight.get("preflight_passed") is not True or not _fresh(preflight):
        blockers.append("fresh_clean_broker_account_preflight_not_passed")
    if not (
        lock.get("status") == "active"
        or lock.get("research_lock_active") is True
        or lock.get("watch_only") is True
    ):
        blockers.append("research_lock_not_active")
    service_running = service.get("service_running") is True
    if require_service_paused and service_running:
        blockers.append("operator_service_must_be_paused_at_checkpoint")
    blockers = unique_errors(blockers)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_clean_epoch_cutover_readiness",
        "generated_at": now_iso(),
        "status": "ready" if not blockers else "blocked",
        "cutover_ready": not blockers,
        "service_pause_required_for_execution": service_running,
        "operator_service_running": service_running,
        "research_lock_active": not any(
            blocker == "research_lock_not_active" for blocker in blockers
        ),
        "certification_passed": cert.get("certification_passed") is True,
        "paper_trial_resume_allowed": cert.get("paper_trial_resume_allowed") is True,
        "validated_edge_count": int(edge.get("validated_edge_count") or 0),
        "forward_shadow_promotion_ready": shadow.get("promotion_ready") is True,
        "real_soak_session_count": soak_sessions,
        "clean_broker_preflight_passed": preflight.get("preflight_passed") is True,
        "clean_broker_preflight_fresh": _fresh(preflight),
        "clean_broker_account_fingerprint": preflight.get(
            "broker_account_fingerprint"
        ),
        "starting_balance": CLEAN_STARTING_EQUITY,
        "account_currency": "USD",
        "blocker_count": len(blockers),
        "blockers": blockers,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "paper_calendar_advanced": False,
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / READINESS_ARTIFACT, payload)
    return payload


def build_cutover_dry_run(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    readiness = build_clean_epoch_cutover_readiness(
        settings, require_service_paused=False
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_clean_epoch_cutover_dry_run",
        "generated_at": now_iso(),
        "status": "would_be_ready_after_service_pause"
        if readiness.get("cutover_ready") is True
        else "blocked",
        "cutover_executed": False,
        "testing_epoch_archived": False,
        "active_epoch_pointer_changed": False,
        "execution_artifacts_cleared": False,
        "paper_calendar_advanced": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "readiness": readiness,
        "required_operator_action": (
            "Pause the supervised operator service at a checkpoint and run the explicit "
            "approved cutover command."
            if readiness.get("cutover_ready") is True
            else "Resolve every listed readiness blocker; do not reset the account."
        ),
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / DRY_RUN_ARTIFACT, payload)
    return payload


def _restore_archive(archive: ArchiveResult, runtime: Path) -> None:
    for relative in archive.copied_files:
        source = archive.archive_dir / relative
        target = runtime / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _write_clean_mirror(runtime: Path, snapshot: dict[str, Any]) -> None:
    store = AtomicArtifactStore(runtime)
    store.write_json(
        "alpaca_paper_mirror.json",
        {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "alpaca_paper_readonly_mirror",
            "generated_at": snapshot.get("observed_at") or now_iso(),
            "status": "clean_epoch_initialized_readonly",
            "snapshot": snapshot,
            "position_count": 0,
            "order_count": 0,
            "closed_trade_count": 0,
            "broker_exception_count": 0,
            "paper_order_created_count": 0,
            "broker_write_count": 0,
            "live_capital_enabled": False,
            "authority": authority_flags(),
        },
    )


def _rebuild_clean_epoch_projections(settings: Settings | None = None) -> None:
    """Rebuild execution-derived read models without altering research memory."""

    from orchestrator.cockpit_status import build_cockpit_status, write_cockpit_status
    from orchestrator.qadam_dashboard_epoch_isolation import (
        build_dashboard_epoch_isolation,
    )
    from orchestrator.qadam_improvement_pipeline_view_model import (
        build_and_write_improvement_pipeline_view_model,
    )
    from orchestrator.qadam_experimental_paper_trial import (
        build_and_write_experimental_paper_trial,
    )
    from orchestrator.qadam_learning_cycle_view_model import (
        build_and_write_learning_cycle_view_model,
    )
    from orchestrator.qadam_operator_dashboard import (
        build_and_write_operator_dashboard,
    )
    from orchestrator.qadam_paper_lineage_and_proof import (
        build_and_write_paper_lineage_and_proof,
    )
    from orchestrator.qsase_dashboard_view_model import (
        build_and_write_dashboard_view_model,
    )

    _lineage, _lineage_checks, lineage_errors = build_and_write_paper_lineage_and_proof(
        settings
    )
    if lineage_errors:
        raise RuntimeError("clean epoch lineage projection failed")
    _learning, _learning_checks, learning_errors = (
        build_and_write_learning_cycle_view_model(settings)
    )
    if learning_errors:
        raise RuntimeError("clean epoch learning projection failed")
    _improvements, _improvement_checks, improvement_errors = (
        build_and_write_improvement_pipeline_view_model(settings)
    )
    if improvement_errors:
        raise RuntimeError("clean epoch improvement projection failed")
    _trial, _outcomes, _trial_checks, trial_errors = (
        build_and_write_experimental_paper_trial(settings)
    )
    if trial_errors:
        raise RuntimeError("clean epoch experimental trial projection failed")
    _dashboard, _dashboard_checks, dashboard_errors = build_and_write_dashboard_view_model(
        settings
    )
    if dashboard_errors:
        raise RuntimeError("clean epoch QSASE dashboard projection failed")
    _operator, _operator_checks, operator_errors = build_and_write_operator_dashboard(
        settings
    )
    if operator_errors:
        raise RuntimeError("clean epoch operator dashboard projection failed")
    write_cockpit_status(build_cockpit_status(settings))
    epoch_isolation = build_dashboard_epoch_isolation(settings)
    if epoch_isolation.get("status") != "passed":
        raise RuntimeError("clean epoch dashboard isolation failed")


def execute_clean_epoch_cutover(
    *,
    operator_approved: bool,
    settings: Settings | None = None,
) -> dict[str, Any]:
    if not operator_approved:
        raise PermissionError("explicit clean-epoch cutover approval is required")
    runtime = runtime_dir(settings)
    readiness = build_clean_epoch_cutover_readiness(
        settings, require_service_paused=True
    )
    if readiness.get("cutover_ready") is not True:
        raise RuntimeError(
            "clean epoch cutover blocked: " + ",".join(readiness.get("blockers", []))
        )
    lock_path = runtime / LOCK_ARTIFACT
    descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.write(descriptor, now_iso().encode("utf-8"))
    os.close(descriptor)
    previous_epoch = read_current_epoch(settings)
    archive: ArchiveResult | None = None
    epoch: dict[str, Any] | None = None
    testing_epoch_id = "testing-epoch-" + now_iso().replace(":", "").replace("+", "")
    try:
        archive = archive_testing_epoch(
            testing_epoch_id=testing_epoch_id,
            settings=settings,
        )
        if research_artifact_was_archived(archive):
            raise RuntimeError("research artifact entered testing-epoch archive")
        epoch = build_epoch_record(
            epoch_kind="clean_operator_epoch",
            started_at=now_iso(),
            broker_account_fingerprint_value=readiness.get(
                "clean_broker_account_fingerprint"
            ),
            starting_equity=CLEAN_STARTING_EQUITY,
            currency="USD",
            label="Clean US$100,000 paper operator epoch",
            previous_epoch_id=previous_epoch.get("paper_epoch_id"),
        )
        write_current_epoch(epoch, settings=settings)
        cleared = clear_archived_execution_artifacts(archive, settings=settings)
        mirror_store = PaperAccountMirrorStore(settings=settings)
        mirror_store.replace_positions(())
        mirror_store.replace_closed_trades(())
        mirror_store.replace_orders(())
        snapshot = initial_paper_account_snapshot(settings)
        mirror_store.write_snapshot(snapshot, log_event=False)
        _write_clean_mirror(runtime, snapshot.to_dict())

        # Rebuild every execution-derived projection before the pointer is
        # accepted. Any failure falls through to the archive rollback below.
        from orchestrator.qadam_dashboard_epoch_isolation import (
            build_dashboard_epoch_isolation,
        )
        from orchestrator.cockpit_status import build_cockpit_status, write_cockpit_status
        from orchestrator.qadam_improvement_pipeline_view_model import (
            build_and_write_improvement_pipeline_view_model,
        )
        from orchestrator.qadam_learning_cycle_view_model import (
            build_and_write_learning_cycle_view_model,
        )
        from orchestrator.qadam_operator_dashboard import (
            build_and_write_operator_dashboard,
        )
        from orchestrator.qadam_paper_lineage_and_proof import (
            build_and_write_paper_lineage_and_proof,
        )
        from orchestrator.qsase_dashboard_view_model import (
            build_and_write_dashboard_view_model,
        )

        _lineage, _lineage_checks, lineage_errors = (
            build_and_write_paper_lineage_and_proof(settings)
        )
        if lineage_errors:
            raise RuntimeError("clean epoch lineage projection failed")
        _learning, _learning_checks, learning_errors = (
            build_and_write_learning_cycle_view_model(settings)
        )
        if learning_errors:
            raise RuntimeError("clean epoch learning projection failed")
        _improvements, _improvement_checks, improvement_errors = (
            build_and_write_improvement_pipeline_view_model(settings)
        )
        if improvement_errors:
            raise RuntimeError("clean epoch improvement projection failed")
        _dashboard, _dashboard_checks, dashboard_errors = (
            build_and_write_dashboard_view_model(settings)
        )
        if dashboard_errors:
            raise RuntimeError("clean epoch QSASE dashboard projection failed")
        _operator, _operator_checks, operator_errors = (
            build_and_write_operator_dashboard(settings)
        )
        if operator_errors:
            raise RuntimeError("clean epoch operator dashboard projection failed")
        write_cockpit_status(build_cockpit_status(settings))
        epoch_isolation = build_dashboard_epoch_isolation(settings)
        if epoch_isolation.get("status") != "passed":
            raise RuntimeError("clean epoch dashboard isolation failed")
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_clean_epoch_cutover_receipt",
            "generated_at": now_iso(),
            "status": "cutover_complete_watch_only",
            "cutover_executed": True,
            "testing_epoch_archived": True,
            "testing_epoch_id": testing_epoch_id,
            "archive_manifest_ref": str(archive.archive_dir / "manifest.json"),
            "archive_checksums_ref": str(archive.archive_dir / "checksums.json"),
            "archive_digest": archive.manifest.get("checksums_digest"),
            "cleared_execution_artifact_count": len(cleared),
            "paper_epoch_id": epoch.get("paper_epoch_id"),
            "paper_epoch_started_at": epoch.get("paper_epoch_started_at"),
            "starting_balance": CLEAN_STARTING_EQUITY,
            "account_currency": "USD",
            "open_position_count": 0,
            "order_count": 0,
            "closed_trade_count": 0,
            "paperops_watch_only": True,
            "research_lock_active": True,
            "paper_calendar_advanced": False,
            "paper_calendar_started_at": epoch.get("paper_epoch_started_at"),
            "paper_order_created_count": 0,
            "broker_write_count": 0,
            "live_capital_enabled": False,
            "authority": authority_flags(),
        }
        write_json_atomic(runtime / RECEIPT_ARTIFACT, receipt)
        return receipt
    except Exception as exc:
        if archive is not None:
            _restore_archive(archive, runtime)
        current_path = runtime / CURRENT_EPOCH_ARTIFACT
        if previous_epoch:
            write_json_atomic(current_path, previous_epoch)
        elif current_path.exists():
            current_path.unlink()
        rollback = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_clean_epoch_rollback_receipt",
            "generated_at": now_iso(),
            "status": "rolled_back",
            "error_type": type(exc).__name__,
            "previous_epoch_restored": bool(previous_epoch),
            "archive_restored": archive is not None,
            "paper_calendar_advanced": False,
            "paper_order_created_count": 0,
            "broker_write_count": 0,
            "live_capital_enabled": False,
            "authority": authority_flags(),
        }
        write_json_atomic(runtime / ROLLBACK_ARTIFACT, rollback)
        append_jsonl_durable(
            runtime / EPOCH_REGISTRY_ARTIFACT,
            {**rollback, "paper_epoch_id": None if epoch is None else epoch.get("paper_epoch_id")},
        )
        raise
    finally:
        lock_path.unlink(missing_ok=True)


def execute_experimental_epoch_cutover(
    *,
    operator_approved: bool,
    settings: Settings | None = None,
    mirror_syncer: Callable[[], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Activate a clean experimental epoch from a verified broker response."""

    if not operator_approved:
        raise PermissionError("explicit experimental clean-epoch cutover approval is required")
    runtime = runtime_dir(settings)
    readiness = build_experimental_epoch_cutover_readiness(settings)
    approval = build_experimental_epoch_cutover_approval(
        readiness,
        operator_approved=operator_approved,
    )
    write_json_atomic(runtime / EXPERIMENTAL_APPROVAL_ARTIFACT, approval)
    approval_errors = validate_experimental_epoch_cutover_approval(approval, readiness)
    blockers = unique_errors(list(readiness.get("blockers", [])) + approval_errors)
    if blockers:
        raise RuntimeError("experimental epoch cutover blocked: " + ",".join(blockers))

    lock_path = runtime / LOCK_ARTIFACT
    descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.write(descriptor, now_iso().encode("utf-8"))
    os.close(descriptor)
    previous_epoch = read_current_epoch(settings)
    previous_previous_epoch = read_json(runtime / PREVIOUS_EPOCH_ARTIFACT)
    archive: ArchiveResult | None = None
    epoch: dict[str, Any] | None = None
    try:
        archive = archive_testing_epoch(
            testing_epoch_id=str(readiness.get("archive_id")),
            settings=settings,
        )
        if archive.manifest.get("checksums_digest") != readiness.get("archive_digest"):
            raise RuntimeError("testing archive changed after approval")
        if research_artifact_was_archived(archive):
            raise RuntimeError("research artifact entered testing-epoch archive")
        activated_at = now_iso()
        epoch = build_epoch_record(
            epoch_kind=EXPERIMENTAL_EPOCH_KIND,
            started_at=activated_at,
            broker_account_fingerprint_value=readiness.get(
                "clean_broker_account_fingerprint"
            ),
            starting_equity=CLEAN_STARTING_EQUITY,
            currency="USD",
            label="Clean US$100,000 autonomous experimental paper epoch",
            previous_epoch_id=previous_epoch.get("paper_epoch_id"),
        )
        write_current_epoch(epoch, settings=settings)
        cleared = clear_archived_execution_artifacts(archive, settings=settings)
        sync = mirror_syncer or AlpacaReadOnlyPaperMirror(settings=settings).sync
        mirror_report = sync()
        snapshot = (
            mirror_report.get("snapshot")
            if isinstance(mirror_report.get("snapshot"), dict)
            else {}
        )
        observed_equity = float(
            snapshot.get("equity")
            or snapshot.get("current_balance")
            or snapshot.get("equity_gbp")
            or 0
        )
        mirror_blockers: list[str] = []
        if mirror_report.get("status") != "ok":
            mirror_blockers.append("initial_provider_backed_mirror_not_ok")
        if abs(observed_equity - CLEAN_STARTING_EQUITY) > 0.01:
            mirror_blockers.append("initial_provider_backed_mirror_not_100000_usd")
        if int(mirror_report.get("position_count") or 0) != 0:
            mirror_blockers.append("initial_provider_backed_mirror_has_positions")
        if int(mirror_report.get("order_count") or 0) != 0:
            mirror_blockers.append("initial_provider_backed_mirror_has_orders")
        if mirror_report.get("broker_account_fingerprint") != readiness.get(
            "clean_broker_account_fingerprint"
        ):
            mirror_blockers.append("initial_provider_backed_mirror_fingerprint_changed")
        if mirror_blockers:
            raise RuntimeError(",".join(mirror_blockers))

        _rebuild_clean_epoch_projections(settings)
        receipt = {
            "schema_version": "qadam_experimental_epoch_cutover.v1",
            "artifact_type": "qadam_clean_epoch_cutover_receipt",
            "generated_at": now_iso(),
            "status": "experimental_cutover_complete_watch_only",
            "cutover_executed": True,
            "cutover_mode": "experimental_unvalidated",
            "testing_epoch_archived": True,
            "testing_epoch_id": readiness.get("archive_id"),
            "archive_manifest_ref": str(archive.archive_dir / "manifest.json"),
            "archive_checksums_ref": str(archive.archive_dir / "checksums.json"),
            "archive_digest": archive.manifest.get("checksums_digest"),
            "cleared_execution_artifact_count": len(cleared),
            "paper_epoch_id": epoch.get("paper_epoch_id"),
            "paper_epoch_kind": EXPERIMENTAL_EPOCH_KIND,
            "paper_epoch_started_at": epoch.get("paper_epoch_started_at"),
            "starting_balance": CLEAN_STARTING_EQUITY,
            "account_currency": "USD",
            "broker_account_fingerprint": readiness.get(
                "clean_broker_account_fingerprint"
            ),
            "provider_backed_initial_mirror": True,
            "provider_mirror_observed_at": snapshot.get("observed_at"),
            "open_position_count": 0,
            "order_count": 0,
            "closed_trade_count": 0,
            "paperops_watch_only": True,
            "research_lock_active": True,
            "paper_calendar_advanced": False,
            "paper_calendar_started_at": None,
            "paper_trial_state": "not_started_waiting_for_guarded_release",
            "policy_version": POLICY_VERSION,
            "cutover_approval_binding_digest": approval.get("binding_digest"),
            "paper_order_created_count": 0,
            "broker_write_count": 0,
            "live_capital_enabled": False,
            "authority": authority_flags(),
        }
        write_json_atomic(runtime / RECEIPT_ARTIFACT, receipt)
        return receipt
    except Exception as exc:
        if archive is not None:
            archived_names = set(archive.copied_files)
            for relative in PAPER_EXECUTION_ARTIFACTS:
                active_path = runtime / relative
                if relative not in archived_names and active_path.is_file():
                    active_path.unlink()
            _restore_archive(archive, runtime)
        current_path = runtime / CURRENT_EPOCH_ARTIFACT
        if previous_epoch:
            write_json_atomic(current_path, previous_epoch)
        elif current_path.exists():
            current_path.unlink()
        previous_path = runtime / PREVIOUS_EPOCH_ARTIFACT
        if previous_previous_epoch:
            write_json_atomic(previous_path, previous_previous_epoch)
        elif previous_path.exists():
            previous_path.unlink()
        rollback = {
            "schema_version": "qadam_experimental_epoch_cutover.v1",
            "artifact_type": "qadam_clean_epoch_rollback_receipt",
            "generated_at": now_iso(),
            "status": "rolled_back",
            "cutover_mode": "experimental_unvalidated",
            "error_type": type(exc).__name__,
            "previous_epoch_restored": bool(previous_epoch),
            "archive_restored": archive is not None,
            "paper_calendar_advanced": False,
            "paper_order_created_count": 0,
            "broker_write_count": 0,
            "live_capital_enabled": False,
            "authority": authority_flags(),
        }
        write_json_atomic(runtime / ROLLBACK_ARTIFACT, rollback)
        append_jsonl_durable(
            runtime / EPOCH_REGISTRY_ARTIFACT,
            {
                **rollback,
                "paper_epoch_id": None if epoch is None else epoch.get("paper_epoch_id"),
            },
        )
        raise
    finally:
        lock_path.unlink(missing_ok=True)


__all__ = [
    "DRY_RUN_ARTIFACT",
    "EXPERIMENTAL_APPROVAL_ARTIFACT",
    "EXPERIMENTAL_READINESS_ARTIFACT",
    "READINESS_ARTIFACT",
    "RECEIPT_ARTIFACT",
    "ROLLBACK_ARTIFACT",
    "build_clean_epoch_cutover_readiness",
    "build_experimental_epoch_cutover_approval",
    "build_experimental_epoch_cutover_readiness",
    "build_cutover_dry_run",
    "execute_clean_epoch_cutover",
    "execute_experimental_epoch_cutover",
    "prepare_experimental_testing_archive",
    "validate_experimental_epoch_cutover_approval",
]
