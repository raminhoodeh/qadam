"""RS-6 paper lifecycle, portfolio, and postmortem hardening.

This contract joins the read-only paper-account mirror with postmortem and
proof-ledger state. It is intentionally audit-only: it can explain portfolio
value provenance and postmortem coverage, but it cannot create, modify, close,
or approve trades.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.paper_account import PaperAccountMirrorStore
from orchestrator.release_contract import PAPER_ACCOUNT_SCOPE


PAPER_LIFECYCLE_PORTFOLIO_POSTMORTEM_SCHEMA_VERSION = 1
PAPER_LIFECYCLE_PORTFOLIO_POSTMORTEM_RUNTIME_ARTIFACT = (
    "paper_lifecycle_portfolio_postmortem.json"
)
PAPER_LIFECYCLE_PORTFOLIO_POSTMORTEM_HISTORY = (
    "paper_lifecycle_portfolio_postmortem_history.jsonl"
)
PAPER_LIFECYCLE_PORTFOLIO_POSTMORTEM_EVENT_LOG = (
    "paper_lifecycle_portfolio_postmortem_events.jsonl"
)
PAPER_LIFECYCLE_PORTFOLIO_POSTMORTEM_EVENT_TYPE = (
    "paper_lifecycle_portfolio_postmortem_recorded"
)
PAPER_LIFECYCLE_PORTFOLIO_POSTMORTEM_COMPONENT = (
    "paper_lifecycle_portfolio_postmortem"
)

ALLOWED_POSTMORTEM_STATUSES = {
    "postmortem_pending_marker",
    "postmortem_due",
    "postmortem_complete",
}

RS6_PUBLIC_STATUS_FIELDS = {
    "schema_version",
    "status",
    "generated_at",
    "account_scope",
    "portfolio_value_source",
    "portfolio_value_broker_account_derived",
    "balance_ticker_source",
    "balance_ticker_broker_account_derived",
    "paper_account_connection_status",
    "current_balance_gbp",
    "equity_gbp",
    "cash_gbp",
    "realized_pnl_gbp",
    "unrealized_pnl_gbp",
    "drawdown_pct",
    "open_position_count",
    "order_count",
    "closed_trade_count",
    "closed_trade_postmortem_coverage_count",
    "closed_trade_missing_postmortem_count",
    "postmortem_due_count",
    "postmortem_complete_count",
    "recent_closed_trade_postmortem_records",
    "paper_proof_ledger_uses_verified_lifecycle_only",
    "paper_proof_ledger_verified_record_count",
    "phase7_closed_proof_trade_count",
    "mirror_trade_counted_for_proof_count",
    "proof_ledger_status",
    "validation_error_count",
    "public_safe",
    "live_capital_enabled",
    "write_authority",
    "broker_write_allowed",
    "paper_order_allowed",
    "boundary",
}

RS6_BOUNDARY = (
    "RS-6 is a read-only lifecycle, portfolio, and postmortem audit contract. "
    "It can mirror paper-account state, require local postmortem markers, and "
    "separate proof-ledger credit from mirror-only trades, but it cannot place, "
    "modify, cancel, close, resize, or approve broker orders, cannot enable "
    "live capital, and cannot grant proof credit."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _paper_lifecycle_portfolio_postmortem_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PAPER_LIFECYCLE_PORTFOLIO_POSTMORTEM_RUNTIME_ARTIFACT,
        runtime / PAPER_LIFECYCLE_PORTFOLIO_POSTMORTEM_HISTORY,
        runtime / PAPER_LIFECYCLE_PORTFOLIO_POSTMORTEM_EVENT_LOG,
    )


def _source_artifact_newer_than_status(
    *,
    settings: Settings,
    status_path: Path,
) -> bool:
    if not status_path.exists():
        return True
    runtime = _runtime_dir(settings)
    try:
        status_mtime = status_path.stat().st_mtime
    except OSError:
        return True
    source_paths = (
        runtime / "alpaca_paper_mirror.json",
        runtime / "paper_account_snapshots.jsonl",
        runtime / "paper_positions.jsonl",
        runtime / "paper_closed_trades.jsonl",
        runtime / "paper_orders.jsonl",
    )
    for source_path in source_paths:
        try:
            if source_path.exists() and source_path.stat().st_mtime > status_mtime:
                return True
        except OSError:
            continue
    return False


def _phase7_lifecycle(settings: Settings) -> dict[str, Any]:
    return _read_json(_runtime_dir(settings) / "phase7_proof_lifecycle_monitor.json")


def _phase7_postmortem(settings: Settings) -> dict[str, Any]:
    return _read_json(_runtime_dir(settings) / "phase7_proof_postmortem_contract.json")


def _phase6_certification(settings: Settings) -> dict[str, Any]:
    return _read_json(_runtime_dir(settings) / "phase6_certification.json")


def _paperops_lifecycle_poller(settings: Settings) -> dict[str, Any]:
    return _read_json(_runtime_dir(settings) / "paperops_paper_lifecycle_poller.json")


def _safe_order_map(orders: tuple[Any, ...]) -> dict[str, Any]:
    return {str(order.order_id): order for order in orders}


def _closed_trade_postmortem_records(
    *,
    closed_trades: tuple[Any, ...],
    orders_by_id: dict[str, Any],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for trade in closed_trades:
        trade_id = str(trade.trade_id)
        status = str(trade.postmortem_status or "missing")
        order = orders_by_id.get(trade_id)
        qadam_originated = bool(trade.source_intent_id)
        records.append(
            {
                "trade_id": trade_id,
                "instrument": trade.instrument,
                "direction": trade.direction,
                "closed_at": trade.closed_at,
                "realized_pnl_gbp": trade.realized_pnl_gbp,
                "postmortem_status": status,
                "postmortem_required": True,
                "postmortem_record_present": status in ALLOWED_POSTMORTEM_STATUSES,
                "qadam_originated": qadam_originated,
                "link_status": (
                    "qadam_lineage_available"
                    if qadam_originated
                    else "external_mirror_missing_qadam_lineage"
                ),
                "research_goal_ref": None,
                "hypothesis_ref": None,
                "candidate_ref": trade.source_intent_id,
                "market_context_packet_ref": None,
                "risk_packet_ref": None,
                "paper_order_ref": order.order_id if order is not None else None,
                "broker_receipt_ref": order.order_id if order is not None else None,
                "position_fill_ref": order.order_id if order is not None else None,
                "boundary": (
                    "Closed paper trade is mirrored for lifecycle/postmortem audit only. "
                    "Mirror lineage does not create proof credit or execution authority."
                ),
            }
        )
    return records


def build_paper_lifecycle_portfolio_postmortem(
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    store = PaperAccountMirrorStore(settings=settings)
    latest = store.latest_snapshot()
    positions = store.read_positions()
    orders = store.read_orders()
    closed_trades = store.read_closed_trades()
    orders_by_id = _safe_order_map(orders)
    phase7_lifecycle = _phase7_lifecycle(settings)
    phase7_postmortem = _phase7_postmortem(settings)
    phase6_certification = _phase6_certification(settings)
    paperops_lifecycle = _paperops_lifecycle_poller(settings)

    generated_at = _now()
    postmortem_records = _closed_trade_postmortem_records(
        closed_trades=closed_trades,
        orders_by_id=orders_by_id,
    )
    missing_postmortem_count = sum(
        1 for record in postmortem_records if not record["postmortem_record_present"]
    )
    due_count = sum(
        1 for record in postmortem_records if record["postmortem_status"] == "postmortem_due"
    )
    complete_count = sum(
        1
        for record in postmortem_records
        if record["postmortem_status"] == "postmortem_complete"
    )
    connection_status = (
        latest.connection_status if latest is not None else "missing_paper_account_snapshot"
    )
    broker_connected = connection_status == "alpaca_paper_readonly_connected"
    portfolio_value_source = (
        "alpaca_paper_account_mirror"
        if broker_connected
        else "local_paper_account_snapshot"
        if latest is not None
        else "missing_snapshot"
    )
    proof_verified_count = _int(phase7_lifecycle.get("closed_proof_trade_count"))
    artifact = {
        "schema_version": PAPER_LIFECYCLE_PORTFOLIO_POSTMORTEM_SCHEMA_VERSION,
        "status": "ok",
        "generated_at": generated_at,
        "account_scope": latest.account_scope if latest is not None else PAPER_ACCOUNT_SCOPE,
        "portfolio_value_source": portfolio_value_source,
        "portfolio_value_broker_account_derived": broker_connected,
        "balance_ticker_source": (
            "paper_account_snapshot.current_balance_gbp"
            if latest is not None
            else "not_available"
        ),
        "balance_ticker_broker_account_derived": broker_connected,
        "paper_account_connection_status": connection_status,
        "broker": latest.broker if latest is not None else "missing",
        "current_balance_gbp": latest.current_balance_gbp if latest is not None else None,
        "equity_gbp": latest.equity_gbp if latest is not None else None,
        "cash_gbp": latest.cash_gbp if latest is not None else None,
        "realized_pnl_gbp": latest.realized_pnl_gbp if latest is not None else 0,
        "unrealized_pnl_gbp": latest.unrealized_pnl_gbp if latest is not None else 0,
        "drawdown_pct": latest.drawdown_pct if latest is not None else 0,
        "open_position_count": len(positions),
        "order_count": len(orders),
        "closed_trade_count": len(closed_trades),
        "closed_trade_postmortem_coverage_count": len(postmortem_records)
        - missing_postmortem_count,
        "closed_trade_missing_postmortem_count": missing_postmortem_count,
        "postmortem_due_count": due_count,
        "postmortem_complete_count": complete_count,
        "closed_trade_postmortem_coverage_satisfied": missing_postmortem_count == 0,
        "closed_trade_order_link_present_count": sum(
            1 for record in postmortem_records if record["paper_order_ref"]
        ),
        "closed_trade_postmortem_records": postmortem_records,
        "recent_closed_trade_postmortem_records": postmortem_records[:8],
        "phase6_certification_status": phase6_certification.get("status", "missing"),
        "phase6_unresolved_postmortem_count": _int(
            phase6_certification.get("unresolved_postmortem_count")
        ),
        "phase6_postmortem_explicitly_deferred_count": _int(
            phase6_certification.get("postmortem_explicitly_deferred_count")
        ),
        "phase7_lifecycle_status": phase7_lifecycle.get("status", "missing"),
        "phase7_closed_proof_trade_count": proof_verified_count,
        "phase7_postmortem_status": phase7_postmortem.get("status", "missing"),
        "phase7_postmortem_due_count": _int(phase7_postmortem.get("postmortem_due_count")),
        "paperops_lifecycle_poller_status": paperops_lifecycle.get("status", "missing"),
        "paperops_lifecycle_readback_records": _int(
            paperops_lifecycle.get("lifecycle_readback_records")
        ),
        "paper_proof_ledger_uses_verified_lifecycle_only": True,
        "paper_proof_ledger_verified_record_count": proof_verified_count,
        "mirror_trade_counted_for_proof_count": 0,
        "proof_ledger_status": "verified_lifecycle_only",
        "proof_ledger_policy": {
            "phase7_verified_lifecycle_required": True,
            "mirror_only_closed_trades_count_as_proof": False,
            "phase5_or_external_mirror_trades_count_as_phase7_proof": False,
            "proof_credit_allowed": False,
            "proof_credit_granted_count": 0,
        },
        "acceptance": {
            "dashboard_balance_ticker_broker_account_derived": broker_connected,
            "closed_paper_trades_require_postmortem_records": True,
            "closed_paper_trades_have_postmortem_markers": missing_postmortem_count == 0,
            "proof_ledger_uses_verified_lifecycle_records_only": True,
            "mirror_trades_do_not_count_for_proof": True,
        },
        "latest_snapshot_present": latest is not None,
        "public_safe": True,
        "live_capital_enabled": False,
        "write_authority": False,
        "broker_write_allowed": False,
        "paper_order_allowed": False,
        "validation_errors": [],
        "validation_error_count": 0,
        "boundary": RS6_BOUNDARY,
    }
    errors = validate_paper_lifecycle_portfolio_postmortem(artifact)
    artifact["validation_errors"] = errors
    artifact["validation_error_count"] = len(errors)
    artifact["status"] = (
        "ok"
        if not errors
        else "degraded_missing_snapshot"
        if "latest_snapshot_missing" in errors
        else "degraded"
    )
    return artifact


def validate_paper_lifecycle_portfolio_postmortem(
    artifact: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if artifact.get("schema_version") != PAPER_LIFECYCLE_PORTFOLIO_POSTMORTEM_SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("not_public_safe")
    for field in (
        "live_capital_enabled",
        "write_authority",
        "broker_write_allowed",
        "paper_order_allowed",
    ):
        if artifact.get(field) is not False:
            errors.append(f"{field}_enabled")
    if artifact.get("latest_snapshot_present") is not True:
        errors.append("latest_snapshot_missing")
    if artifact.get("portfolio_value_source") == "display_inferred":
        errors.append("portfolio_value_display_inferred")
    if artifact.get("paper_account_connection_status") == "alpaca_paper_readonly_connected":
        if artifact.get("portfolio_value_broker_account_derived") is not True:
            errors.append("portfolio_value_not_broker_account_derived")
        if artifact.get("balance_ticker_broker_account_derived") is not True:
            errors.append("balance_ticker_not_broker_account_derived")
    records = artifact.get("closed_trade_postmortem_records", [])
    if not isinstance(records, list):
        errors.append("closed_trade_postmortem_records_not_list")
        records = []
    closed_trade_count = _int(artifact.get("closed_trade_count"))
    if closed_trade_count != len(records):
        errors.append("closed_trade_postmortem_record_count_mismatch")
    missing_count = sum(
        1 for record in records if not record.get("postmortem_record_present")
    )
    if missing_count != _int(artifact.get("closed_trade_missing_postmortem_count")):
        errors.append("closed_trade_missing_postmortem_count_mismatch")
    coverage_count = sum(
        1 for record in records if record.get("postmortem_record_present") is True
    )
    if coverage_count != _int(artifact.get("closed_trade_postmortem_coverage_count")):
        errors.append("closed_trade_postmortem_coverage_count_mismatch")
    for record in records:
        status = record.get("postmortem_status")
        if status not in ALLOWED_POSTMORTEM_STATUSES:
            errors.append(f"invalid_postmortem_status:{record.get('trade_id', 'unknown')}")
        if record.get("postmortem_required") is not True:
            errors.append(f"postmortem_not_required:{record.get('trade_id', 'unknown')}")
        if not record.get("paper_order_ref"):
            errors.append(f"paper_order_ref_missing:{record.get('trade_id', 'unknown')}")
    if closed_trade_count and artifact.get("closed_trade_postmortem_coverage_satisfied") is not True:
        errors.append("closed_trade_postmortem_coverage_not_satisfied")
    if artifact.get("paper_proof_ledger_uses_verified_lifecycle_only") is not True:
        errors.append("proof_ledger_not_lifecycle_only")
    if _int(artifact.get("mirror_trade_counted_for_proof_count")) != 0:
        errors.append("mirror_trade_counted_for_proof")
    if _int(artifact.get("paper_proof_ledger_verified_record_count")) != _int(
        artifact.get("phase7_closed_proof_trade_count")
    ):
        errors.append("proof_ledger_verified_count_mismatch")
    acceptance = artifact.get("acceptance", {})
    if not isinstance(acceptance, dict):
        errors.append("acceptance_not_dict")
        acceptance = {}
    for field in (
        "closed_paper_trades_require_postmortem_records",
        "closed_paper_trades_have_postmortem_markers",
        "proof_ledger_uses_verified_lifecycle_records_only",
        "mirror_trades_do_not_count_for_proof",
    ):
        if acceptance.get(field) is not True:
            errors.append(f"acceptance_failed:{field}")
    if "read-only" not in str(artifact.get("boundary", "")):
        errors.append("boundary_missing_read_only")
    if "cannot place" not in str(artifact.get("boundary", "")):
        errors.append("boundary_missing_no_place")
    return sorted(set(errors))


def write_paper_lifecycle_portfolio_postmortem(
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    artifact = build_paper_lifecycle_portfolio_postmortem(settings=settings)
    runtime_path, history_path, event_log_path = _paper_lifecycle_portfolio_postmortem_paths(
        settings
    )
    artifact["runtime_artifact"] = (
        f"data/runtime/{PAPER_LIFECYCLE_PORTFOLIO_POSTMORTEM_RUNTIME_ARTIFACT}"
    )
    artifact["history_artifact"] = (
        f"data/runtime/{PAPER_LIFECYCLE_PORTFOLIO_POSTMORTEM_HISTORY}"
    )
    artifact["event_log_artifact"] = (
        f"data/runtime/{PAPER_LIFECYCLE_PORTFOLIO_POSTMORTEM_EVENT_LOG}"
    )
    _write_json(runtime_path, artifact)
    _append_jsonl(history_path, artifact)
    event_log = EventLog(path=event_log_path, echo=False)
    entry = event_log.write(
        PAPER_LIFECYCLE_PORTFOLIO_POSTMORTEM_EVENT_TYPE,
        PAPER_LIFECYCLE_PORTFOLIO_POSTMORTEM_COMPONENT,
        {
            "status": artifact["status"],
            "closed_trade_count": artifact["closed_trade_count"],
            "closed_trade_postmortem_coverage_count": artifact[
                "closed_trade_postmortem_coverage_count"
            ],
            "paper_proof_ledger_verified_record_count": artifact[
                "paper_proof_ledger_verified_record_count"
            ],
            "mirror_trade_counted_for_proof_count": artifact[
                "mirror_trade_counted_for_proof_count"
            ],
            "validation_error_count": artifact["validation_error_count"],
        },
    )
    artifact["event_log_written"] = True
    artifact["event_log_event_count"] = 1
    artifact["event_log_created_at"] = entry.created_at
    artifact["event_log_correlation_id"] = entry.correlation_id
    _write_json(runtime_path, artifact)
    return artifact


def paper_lifecycle_portfolio_postmortem_status(
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    runtime_path, _, _ = _paper_lifecycle_portfolio_postmortem_paths(settings)
    if runtime_path.exists() and not _source_artifact_newer_than_status(
        settings=settings,
        status_path=runtime_path,
    ):
        payload = _read_json(runtime_path)
        if payload:
            return payload
    return write_paper_lifecycle_portfolio_postmortem(settings=settings)


def paper_lifecycle_portfolio_postmortem_public_status(
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    artifact = paper_lifecycle_portfolio_postmortem_status(settings=settings)
    return {field: artifact.get(field) for field in sorted(RS6_PUBLIC_STATUS_FIELDS)}
