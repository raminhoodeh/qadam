"""Project the authoritative paper-control state from Qadam's durable ledger.

This replaces legacy scheduler and certification artifacts as PaperOps
authority. Compatibility fields remain available to older summary readers, but
the decision is made from the released paper epoch, the canonical execution
lease, broker reconciliation, and SQLite integrity.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping
from zoneinfo import ZoneInfo

from orchestrator.config import Settings
from orchestrator.paper_account import PaperAccountMirrorStore
from orchestrator.qadam_control_plane_store import ControlPlaneStore
from orchestrator.qadam_operating_ledger import ExecutionOwnerError, OperatingLedger
from orchestrator.qadam_operator_ready_common import atomic_write_text, runtime_dir


SCHEMA_VERSION = "qadam_canonical_paper_control.v1"
RUNTIME_ARTIFACT = "qadam_canonical_paper_control.json"
CANONICAL_WRAPPER = "scripts/run_paperops_autonomous_pass.py"
EPOCH_KIND = "clean_experimental_operator_epoch"
LOCK_RELEASE_MODE = "explicit_operator_approved_experimental_paper_epoch"
MAX_RECONCILIATION_AGE_SECONDS = 300
MAX_MIRROR_AGE_SECONDS = 300


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


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


def _latest_payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    row = max(rows, key=lambda item: str(item.get("created_at") or ""))
    payload = row.get("payload")
    result = dict(payload) if isinstance(payload, Mapping) else {}
    result.setdefault("created_at", row.get("created_at"))
    return result


def _age_seconds(value: Any, now: datetime) -> float | None:
    observed = _parse(value)
    if observed is None:
        return None
    return max(0.0, (now - observed).total_seconds())


def _trial_calendar(epoch: Mapping[str, Any], now: datetime) -> dict[str, Any]:
    started = _parse(
        epoch.get("paper_growth_trial_started_at")
        or epoch.get("paper_epoch_started_at")
        or epoch.get("created_at")
    )
    if started is None:
        return {
            "run_day": 0,
            "completed_calendar_day_count": 0,
            "calendar_days_remaining": 30,
        }
    dubai = ZoneInfo("Asia/Dubai")
    elapsed = max(0, (now.astimezone(dubai).date() - started.astimezone(dubai).date()).days)
    return {
        "run_day": elapsed + 1,
        "completed_calendar_day_count": elapsed,
        "calendar_days_remaining": max(0, 30 - elapsed),
    }


def build_canonical_paper_control(
    settings: Settings | None = None,
    *,
    current_time: datetime | None = None,
    require_execution_owner: bool = True,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    now = (current_time or datetime.now(timezone.utc)).astimezone(timezone.utc)
    runtime = runtime_dir(settings)
    release = _read_json(runtime / "qadam_experimental_paper_release_readiness.json")
    epoch = _read_json(runtime / "current_paper_epoch.json")
    lock = _read_json(runtime / "qadam_long_backtest_lock.json")
    store = ControlPlaneStore.from_settings(settings)
    ledger = OperatingLedger(settings)
    integrity = store.integrity_report()
    execution_state = ledger.execution_state()
    reconciliation = _latest_payload(store.read_table("reconciliation_runs"))
    reconciliation_age = _age_seconds(
        reconciliation.get("generated_at") or reconciliation.get("created_at"), now
    )
    try:
        mirror = PaperAccountMirrorStore(settings=settings).latest_snapshot()
    except Exception:  # noqa: BLE001 - publish state, never provider payload.
        mirror = None
    mirror_age = _age_seconds(mirror.observed_at if mirror else None, now)
    try:
        owner = ledger.assert_execution_owner() if require_execution_owner else None
        owner_error = None
    except ExecutionOwnerError as exc:
        owner = None
        owner_error = str(exc).split(":", 1)[0]

    release_epoch_id = str(release.get("paper_epoch_id") or "")
    epoch_id = str(epoch.get("paper_epoch_id") or "")
    checks = {
        "paper_mode": settings.mode == "paper",
        "live_capital_disabled": settings.live_capital_enabled is False,
        "release_effective": (
            release.get("status") == "experimental_paper_release_effective"
            and release.get("experimental_paper_release_effective") is True
            and release.get("experimental_paper_release_ready") is True
            and not (release.get("blockers") or [])
        ),
        "canonical_wrapper_exact": release.get("canonical_wrapper") == CANONICAL_WRAPPER,
        "clean_epoch_active": (
            epoch.get("paper_epoch_kind") == EPOCH_KIND
            and epoch.get("paper_growth_trial_calendar_started") is True
            and epoch.get("paper_growth_trial_state") == "active_real_calendar"
            and epoch.get("paper_growth_trial_calendar_backfilled") is False
            and epoch.get("simulated_elapsed_time") is False
        ),
        "epoch_binding_exact": bool(epoch_id) and epoch_id == release_epoch_id,
        "research_lock_released": (
            lock.get("status") == "released"
            and lock.get("paperops_watch_only_mode") is False
            and lock.get("release_mode") == LOCK_RELEASE_MODE
            and lock.get("release_approval_epoch_id") == epoch_id
        ),
        "ledger_integrity": integrity.get("status") == "passed",
        "execution_owner_active": owner is not None if require_execution_owner else True,
        "execution_not_frozen": int(execution_state.get("frozen") or 0) == 0,
        "reconciliation_passed": reconciliation.get("status") == "passed",
        "reconciliation_fresh": (
            reconciliation_age is not None
            and reconciliation_age <= MAX_RECONCILIATION_AGE_SECONDS
        ),
        "paper_mirror_fresh": mirror_age is not None and mirror_age <= MAX_MIRROR_AGE_SECONDS,
    }
    blockers = sorted(key for key, passed in checks.items() if not passed)
    calendar = _trial_calendar(epoch, now)
    counts = integrity.get("counts") if isinstance(integrity.get("counts"), dict) else {}
    handoffs = store.read_table("handoffs")
    accepted_handoffs = [
        row for row in handoffs if row.get("state") == "accepted_for_paperops_review"
    ]
    artifact = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_canonical_paper_control",
        "generated_at": now.isoformat(),
        "status": "canonical_paper_control_ready" if not blockers else "blocked",
        "checks": checks,
        "blockers": blockers,
        "blocker_count": len(blockers),
        "authoritative_store": "qadam-control-plane.sqlite3",
        "canonical_wrapper": CANONICAL_WRAPPER,
        "paper_epoch_id": epoch_id,
        "paper_growth_trial": {
            "run_id": epoch_id,
            "run_state": epoch.get("paper_growth_trial_state"),
            **calendar,
            "actual_calendar_run": True,
            "backfill_used": False,
            "simulated_time_used": False,
        },
        "accepted_handoff_count": len(accepted_handoffs),
        "canonical_order_count": int(counts.get("canonical_orders") or 0),
        "open_position_count": len(
            [row for row in store.read_table("positions") if row.get("state") == "open"]
        ),
        "latest_reconciliation": reconciliation,
        "reconciliation_age_seconds": reconciliation_age,
        "paper_mirror_observed_at": mirror.observed_at if mirror else None,
        "paper_mirror_age_seconds": mirror_age,
        "execution_frozen": int(execution_state.get("frozen") or 0) == 1,
        "execution_freeze_reason": execution_state.get("reason"),
        "execution_owner_id": owner.get("owner_id") if owner else None,
        "execution_owner_error": owner_error,
        "paper_only": True,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "profit_guaranteed": False,
        "daily_trade_guaranteed": False,
    }
    return artifact


def validate_canonical_paper_control(artifact: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if artifact.get("schema_version") != SCHEMA_VERSION:
        errors.append("canonical_paper_control_schema_mismatch")
    if artifact.get("authoritative_store") != "qadam-control-plane.sqlite3":
        errors.append("canonical_paper_control_wrong_store")
    if artifact.get("canonical_wrapper") != CANONICAL_WRAPPER:
        errors.append("canonical_paper_control_wrong_wrapper")
    if artifact.get("paper_only") is not True:
        errors.append("canonical_paper_control_not_paper_only")
    if artifact.get("live_capital_enabled") is not False:
        errors.append("canonical_paper_control_live_capital_enabled")
    if artifact.get("proof_credit_allowed") is not False:
        errors.append("canonical_paper_control_proof_credit_allowed")
    if artifact.get("status") != "canonical_paper_control_ready":
        errors.extend(str(item) for item in artifact.get("blockers", []))
    return sorted(set(errors))


def write_canonical_paper_control(
    artifact: Mapping[str, Any], settings: Settings | None = None
) -> Path:
    destination = runtime_dir(settings) / RUNTIME_ARTIFACT
    atomic_write_text(destination, json.dumps(dict(artifact), indent=2, sort_keys=True) + "\n")
    return destination


__all__ = [
    "RUNTIME_ARTIFACT",
    "build_canonical_paper_control",
    "validate_canonical_paper_control",
    "write_canonical_paper_control",
]
