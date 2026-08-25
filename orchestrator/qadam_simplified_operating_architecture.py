"""Certify Qadam's simplified, paper-only operating architecture."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping

from orchestrator.config import Settings
from orchestrator.qadam_control_plane_store import ControlPlaneStore
from orchestrator.qadam_operator_ready_common import atomic_write_text, runtime_dir


SCHEMA_VERSION = "qadam_simplified_operating_architecture.v1"
RUNTIME_ARTIFACT = "qadam_simplified_operating_architecture_certification.json"
REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_LABEL = "com.qadam.operator"
AUXILIARY_LABEL = "com.qadam.operator-exploratory-exit-manager"
MAX_RUNTIME_AGE_SECONDS = 10_800


def _now() -> datetime:
    return datetime.now(timezone.utc)


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


def _source(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _service_loaded(label: str) -> bool:
    result = subprocess.run(
        ["launchctl", "print", f"gui/{Path.home().stat().st_uid}/{label}"],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return result.returncode == 0


def inspect_execution_services() -> dict[str, Any]:
    launch_agents = Path.home() / "Library" / "LaunchAgents"
    return {
        "canonical_operator_installed": (launch_agents / f"{CANONICAL_LABEL}.plist").is_file(),
        "canonical_operator_running": _service_loaded(CANONICAL_LABEL),
        "auxiliary_operator_installed": (launch_agents / f"{AUXILIARY_LABEL}.plist").is_file(),
        "auxiliary_operator_running": _service_loaded(AUXILIARY_LABEL),
    }


def _latest_payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    row = sorted(rows, key=lambda item: str(item.get("created_at") or ""))[-1]
    payload = row.get("payload")
    result = dict(payload) if isinstance(payload, Mapping) else {}
    if row.get("created_at") and not result.get("created_at"):
        result["created_at"] = row["created_at"]
    return result


def _fresh(payload: Mapping[str, Any], *, now: datetime) -> bool:
    generated = _parse(payload.get("generated_at") or payload.get("created_at"))
    return bool(
        generated
        and 0 <= (now - generated).total_seconds() <= MAX_RUNTIME_AGE_SECONDS
    )


def _check(key: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"key": key, "passed": bool(passed), "detail": detail}


def build_simplified_operating_architecture_certification(
    settings: Settings | None = None,
    *,
    service_state: Mapping[str, Any] | None = None,
    require_fresh_runtime: bool = True,
    current_time: datetime | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    now = (current_time or _now()).astimezone(timezone.utc)
    store = ControlPlaneStore.from_settings(settings)
    integrity = store.integrity_report()
    execution_state = store.read_table("execution_state")
    execution_state = execution_state[0] if execution_state else {"frozen": 1}
    leases = store.read_table("execution_owner_leases")
    active_leases = [
        row
        for row in leases
        if row.get("state") == "active" and (_parse(row.get("expires_at")) or now) > now
    ]
    repairs = [
        row for row in store.read_table("repair_requests") if row.get("status") == "open"
    ]
    orders = store.read_table("canonical_orders")
    positions = store.read_table("positions")
    exits = {str(row.get("exit_plan_id")) for row in store.read_table("exit_plans")}
    latest_reconciliation = _latest_payload(store.read_table("reconciliation_runs"))
    latest_liveness = _latest_payload(store.read_table("liveness_cycles"))
    services = dict(service_state or inspect_execution_services())

    ledger_source = _source("orchestrator/qadam_operating_ledger.py")
    entry_source = _source("orchestrator/paperops_alpaca_paper_post.py")
    exit_source = _source("orchestrator/paperops_paper_exit_path.py")
    wrapper_source = _source("orchestrator/paperops_autonomous_pass.py")
    legacy_exit_source = _source(
        "orchestrator/qadam_operator_exploratory_exit_manager.py"
    )
    auxiliary_plist_source = _source(
        "ops/launchd/com.qadam.operator-exploratory-exit-manager.plist.template"
    )
    active_without_exit = [
        row
        for row in orders
        if row.get("state") in {"prepared", "submitting", "submitted", "accepted", "partially_filled"}
        and str(row.get("exit_plan_id")) not in exits
    ]
    open_position_without_exit = [
        row
        for row in positions
        if row.get("state") == "open" and str(row.get("exit_plan_id")) not in exits
    ]
    actionable_exit_ids = {
        str(row.get("exit_plan_id"))
        for row in store.read_table("exit_plans")
        if float(row.get("stop_price") or 0) > 0
        and float(row.get("take_profit_price") or 0) > 0
        and int(row.get("maximum_holding_sessions") or 0) > 0
        and str(row.get("invalidation") or "").strip()
    }
    open_position_without_actionable_exit = [
        row
        for row in positions
        if row.get("state") == "open"
        and str(row.get("exit_plan_id")) not in actionable_exit_ids
    ]
    lane_values = {str(row.get("trading_lane")) for row in orders + positions}
    lane_values.discard("")
    runtime_is_fresh = (
        _fresh(latest_reconciliation, now=now) and _fresh(latest_liveness, now=now)
        if require_fresh_runtime
        else True
    )
    liveness_explained = bool(latest_liveness) and latest_liveness.get("status") != (
        "degraded_unexplained_stoppage"
    ) and all(
        row.get("final_state") and row.get("reason")
        for row in latest_liveness.get("setup_outcomes", [])
        if isinstance(row, Mapping)
    )

    checks = [
        _check("one_durable_transactional_ledger", integrity.get("status") == "passed", "SQLite integrity, migrations and foreign keys pass."),
        _check("one_execution_owner_lease", len(active_leases) <= 1, f"{len(active_leases)} active execution leases."),
        _check("canonical_operator_is_only_service", services.get("canonical_operator_installed") is True and services.get("canonical_operator_running") is True and services.get("auxiliary_operator_installed") is False and services.get("auxiliary_operator_running") is False, "Canonical operator is running and the auxiliary writer is absent."),
        _check("legacy_exit_writer_retired", "legacy_exit_execution_retired_use_canonical_exit_engine" in legacy_exit_source and "--execute-due-paper-exits" not in auxiliary_plist_source, "The legacy exit monitor cannot execute production broker writes."),
        _check("broker_writes_require_owner", "assert_execution_owner" in entry_source and "assert_execution_owner" in exit_source, "Entry and exit broker writes require the canonical lease."),
        _check("canonical_exit_in_wrapper", "check_qadam_canonical_exit_engine.py" in wrapper_source, "The canonical pass owns due exits."),
        _check("two_trading_lanes_only", lane_values.issubset({"validated", "discovery"}) and 'return "validated"' in ledger_source and 'return "discovery"' in ledger_source, f"Observed lanes: {sorted(lane_values)}."),
        _check("evidence_fit_hard_requirements", all(token in ledger_source for token in ("direction_missing", "invalidation_missing", "risk_reference_missing")) and all(token in entry_source for token in ("regular_session_open", "asset_active_and_tradable", "broker_reads_succeeded")), "Direction, invalidation, risk, tradability, market session and broker truth are hard requirements."),
        _check("optional_evidence_does_not_become_hard_veto", "optional_volume_context" not in ledger_source and "optional_sentiment_context" not in ledger_source, "Optional context is not required by the transactional entry prewrite."),
        _check("portfolio_risk_approval_required", "canonical_risk_decision_missing" in ledger_source and "canonical_risk_notional_exceeded" in ledger_source, "Every entry consumes an approved portfolio-risk notional."),
        _check("every_active_order_has_exit", not active_without_exit, f"{len(active_without_exit)} active orders lack an exit plan."),
        _check("every_open_position_has_exit", not open_position_without_exit, f"{len(open_position_without_exit)} open positions lack an exit plan."),
        _check("every_open_position_has_actionable_exit", not open_position_without_actionable_exit, f"{len(open_position_without_actionable_exit)} open positions lack a stop, target, holding period or invalidation."),
        _check("continuous_reconciliation_passed", latest_reconciliation.get("status") == "passed", str(latest_reconciliation.get("phase") or "No reconciliation recorded.")),
        _check("execution_not_frozen", int(execution_state.get("frozen") or 0) == 0, str(execution_state.get("reason") or "No reconciliation freeze.")),
        _check("operational_liveness_explained", liveness_explained, str(latest_liveness.get("status") or "No liveness cycle recorded.")),
        _check("runtime_evidence_fresh", runtime_is_fresh, "Reconciliation and liveness are within the freshness window."),
        _check("repair_queue_clear", not repairs, f"{len(repairs)} open canonical repair requests."),
        _check("paper_only_boundary", settings.mode == "paper" and settings.live_capital_enabled is False, "Paper mode is active and live capital is disabled."),
    ]
    blockers = [str(row["key"]) for row in checks if row["passed"] is not True]
    artifact = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_simplified_operating_architecture_certification",
        "generated_at": now.isoformat(),
        "status": "passed" if not blockers else "blocked",
        "checks": checks,
        "check_count": len(checks),
        "passed_check_count": len(checks) - len(blockers),
        "blockers": blockers,
        "database_schema_version": integrity.get("applied_database_schema_version"),
        "transaction_counts": integrity.get("counts", {}),
        "latest_reconciliation": latest_reconciliation,
        "latest_liveness": latest_liveness,
        "service_state": services,
        "execution_frozen": int(execution_state.get("frozen") or 0) == 1,
        "paper_only": True,
        "live_capital_enabled": False,
        "profit_guaranteed": False,
        "daily_trade_guaranteed": False,
    }
    return artifact


def write_simplified_operating_architecture_certification(
    artifact: Mapping[str, Any], settings: Settings | None = None
) -> Path:
    destination = runtime_dir(settings) / RUNTIME_ARTIFACT
    atomic_write_text(destination, json.dumps(dict(artifact), indent=2, sort_keys=True) + "\n")
    return destination


def validate_simplified_operating_architecture_certification(
    artifact: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    if artifact.get("paper_only") is not True:
        errors.append("architecture_not_paper_only")
    if artifact.get("live_capital_enabled") is not False:
        errors.append("architecture_live_capital_enabled")
    if artifact.get("status") != "passed":
        errors.extend(str(item) for item in artifact.get("blockers", []))
    return sorted(set(errors))


__all__ = [
    "RUNTIME_ARTIFACT",
    "build_simplified_operating_architecture_certification",
    "validate_simplified_operating_architecture_certification",
    "write_simplified_operating_architecture_certification",
]
