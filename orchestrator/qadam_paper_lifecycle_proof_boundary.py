"""Paper lifecycle and proof boundary for Qadam next-generation Phase 10.

This module audits mirrored paper orders, positions, and closed paper trades.
It makes every lifecycle state explicit and keeps proof eligibility separate
from proof credit. Backtests, shadows, mirrored-only fills, and incomplete
lineage records cannot receive paper proof ledger credit.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings

SCHEMA_VERSION = "qadam_paper_lifecycle_proof_boundary.v1"
PHASE_ID = "qadam_next_generation_phase_10_paper_lifecycle_proof_boundary"

PRIMARY_ARTIFACT = "qadam_paper_lifecycle_v2.json"
LIFECYCLE_RECORDS_ARTIFACT = "qadam_paper_lifecycle_v2_records.jsonl"
PROOF_BOUNDARY_ARTIFACT = "qadam_paper_proof_boundary_audit.json"
PROOF_RECORDS_ARTIFACT = "qadam_paper_proof_boundary_records.jsonl"
DASHBOARD_SUMMARY_ARTIFACT = "qadam_paper_lifecycle_v2_dashboard_summary.json"
EVENTS_ARTIFACT = "qadam_paper_lifecycle_v2_events.jsonl"

PAPER_ORDERS_ARTIFACT = "paper_orders.jsonl"
PAPER_POSITIONS_ARTIFACT = "paper_positions.jsonl"
PAPER_CLOSED_TRADES_ARTIFACT = "paper_closed_trades.jsonl"
PAPEROPS_SUMMARY_ARTIFACT = "paperops_autonomous_pass_summary.json"
PAPEROPS_LIFECYCLE_POLLER_ARTIFACT = "paperops_paper_lifecycle_poller.json"
PAPEROPS_CLOSE_TO_LEDGER_ARTIFACT = "paperops_close_to_ledger.json"
ROUTER_V2_ARTIFACT = "qadam_router_v2_paperops_handoff.json"
ROUTER_V2_DECISIONS_ARTIFACT = "qadam_router_v2_decisions.jsonl"
PAPEROPS_HANDOFF_V2_ARTIFACT = "qadam_paperops_handoff_v2_records.jsonl"

STALE_ACCEPTED_ORDER_SECONDS = 90 * 60

LIFECYCLE_STATES = {
    "submitted",
    "accepted",
    "filled",
    "open",
    "stale",
    "cancel_replace_needed",
    "closed",
    "postmortem_due",
    "proof_eligible",
    "proof_rejected",
}

OPEN_ORDER_STATUSES = {"accepted", "new", "open", "pending_new", "pending", "submitted"}
CLOSED_ORDER_STATUSES = {"filled", "canceled", "cancelled", "expired", "rejected", "closed"}

AUTHORITY_FLAGS = {
    "read_only": True,
    "paper_only": True,
    "proposal_first": True,
    "lifecycle_audit_only": True,
    "proof_boundary_audit_only": True,
    "trade_candidate_creation_allowed": False,
    "trade_candidate_created": False,
    "qualified_setup_created": False,
    "risk_approval_created": False,
    "execution_allowed": False,
    "execution_approval_created": False,
    "paper_order_allowed": False,
    "paper_order_created": False,
    "paper_order_created_count": 0,
    "order_cancel_allowed": False,
    "order_replace_allowed": False,
    "position_close_allowed": False,
    "broker_write_allowed": False,
    "broker_write_count": 0,
    "live_broker_endpoint_allowed": False,
    "live_capital_enabled": False,
    "proof_credit_allowed": False,
    "paper_proof_ledger_write_allowed": False,
    "paper_proof_ledger_credit_allowed": False,
    "paper_proof_ledger_credit_created": False,
    "backtest_shadow_or_synthetic_credit_allowed": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "paper_growth_trial_calendar_advanced": False,
    "simulated_elapsed_time_allowed": False,
    "strategy_mutation_allowed": False,
    "strategy_mutation_created": False,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
}

FORBIDDEN_TRUE_FIELDS = tuple(
    key for key, value in AUTHORITY_FLAGS.items() if value is False
)
FORBIDDEN_NONZERO_FIELDS = tuple(
    key for key, value in AUTHORITY_FLAGS.items() if isinstance(value, int) and value == 0
)


@dataclass(frozen=True)
class PaperLifecycleProofBundle:
    primary: dict[str, Any]
    lifecycle_records: list[dict[str, Any]]
    proof_boundary: dict[str, Any]
    proof_records: list[dict[str, Any]]
    dashboard_summary: dict[str, Any]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _runtime_dir(settings: Settings | None = None) -> Path:
    active_settings = settings or Settings.from_env()
    path = Path(active_settings.runtime_dir)
    if not path.is_absolute():
        path = _repo_root() / path
    return path


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _now()).astimezone(timezone.utc).isoformat()


def _json_dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _jsonl_line(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True) + "\n"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    if limit is not None:
        lines = lines[-limit:]
    records: list[dict[str, Any]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_dump(payload), encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(_jsonl_line(record) for record in records), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(_jsonl_line(payload))


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_dt(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _hash_id(prefix: str, parts: list[Any]) -> str:
    payload = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}:{digest}"


def _authority() -> dict[str, Any]:
    return dict(AUTHORITY_FLAGS)


def _artifact_ref(filename: str, pointer: str | None = None) -> str:
    base = f"data/runtime/{filename}"
    return f"{base}#{pointer}" if pointer else base


def _load_context(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "runtime_dir": runtime,
        "paper_orders": _read_jsonl(runtime / PAPER_ORDERS_ARTIFACT, limit=2000),
        "paper_positions": _read_jsonl(runtime / PAPER_POSITIONS_ARTIFACT, limit=2000),
        "paper_closed_trades": _read_jsonl(runtime / PAPER_CLOSED_TRADES_ARTIFACT, limit=2000),
        "paperops_summary": _read_json(runtime / PAPEROPS_SUMMARY_ARTIFACT),
        "paperops_lifecycle_poller": _read_json(runtime / PAPEROPS_LIFECYCLE_POLLER_ARTIFACT),
        "paperops_close_to_ledger": _read_json(runtime / PAPEROPS_CLOSE_TO_LEDGER_ARTIFACT),
        "router_v2": _read_json(runtime / ROUTER_V2_ARTIFACT),
        "router_v2_decisions": _read_jsonl(runtime / ROUTER_V2_DECISIONS_ARTIFACT, limit=2000),
        "paperops_handoff_v2": _read_jsonl(runtime / PAPEROPS_HANDOFF_V2_ARTIFACT, limit=2000),
    }


def _trade_key(record: dict[str, Any]) -> str:
    return str(record.get("trade_id") or record.get("order_id") or record.get("source_order_ref") or "").strip()


def _order_key(record: dict[str, Any]) -> str:
    return str(record.get("order_id") or record.get("client_order_id") or record.get("idempotency_key") or "").strip()


def _closed_trade_by_order_id(closed_trades: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for trade in closed_trades:
        key = _trade_key(trade)
        if key:
            indexed[key] = trade
    return indexed


def _proof_lineage_checks(trade: dict[str, Any], matched_order: dict[str, Any] | None = None) -> dict[str, bool]:
    matched_order = matched_order or {}
    return {
        "real_closed_paper_trade": bool(trade.get("trade_id") and trade.get("closed_at") and trade.get("instrument")),
        "not_backtest_shadow_or_synthetic": "backtest" not in str(trade.get("boundary") or "").lower()
        and "shadow" not in str(trade.get("boundary") or "").lower()
        and trade.get("synthetic") is not True,
        "research_goal_lineage": bool(trade.get("research_goal_id") or trade.get("source_intent_id")),
        "candidate_identity": bool(trade.get("candidate_identity_id") or trade.get("candidate_identity") or trade.get("source_intent_id")),
        "router_or_paperops_handoff_lineage": bool(trade.get("router_decision_id") or trade.get("paperops_handoff_id") or trade.get("source_intent_id")),
        "submitted_order_lineage": bool(trade.get("source_order_ref") or trade.get("order_id") or matched_order.get("order_id")),
        "fill_lineage": bool(trade.get("opened_at") or trade.get("filled_at") or matched_order.get("filled_at") or matched_order.get("filled_avg_price")),
        "close_lineage": bool(trade.get("closed_at")),
        "postmortem_complete": str(trade.get("postmortem_status") or "").lower() == "postmortem_complete",
    }


def _proof_state(trade: dict[str, Any], matched_order: dict[str, Any] | None = None) -> tuple[str, dict[str, bool], list[str]]:
    checks = _proof_lineage_checks(trade, matched_order)
    missing = [key for key, passed in checks.items() if not passed]
    return ("proof_eligible" if not missing else "proof_rejected", checks, missing)


def _order_lifecycle_state(
    order: dict[str, Any],
    matched_trade: dict[str, Any] | None,
    generated_dt: datetime,
) -> tuple[str, str, bool, int | None]:
    status = str(order.get("status") or "").lower()
    submitted_at = _parse_dt(order.get("submitted_at"))
    age_seconds = int((generated_dt - submitted_at).total_seconds()) if submitted_at else None
    filled = bool(order.get("filled_at") or _safe_float(order.get("filled_quantity")) > 0 or status == "filled")
    if matched_trade:
        proof_lifecycle_state, _, _ = _proof_state(matched_trade, order)
        if proof_lifecycle_state == "proof_eligible":
            return "proof_eligible", "audit_real_closed_trade_for_paper_proof_ledger_review", False, age_seconds
        if str(matched_trade.get("postmortem_status") or "").lower() != "postmortem_complete":
            return "postmortem_due", "complete_lineaged_postmortem_before_proof_review", False, age_seconds
        return "proof_rejected", "repair_missing_lineage_before_proof_review", False, age_seconds
    if filled:
        return "filled", "reconcile_fill_to_open_position_or_closed_trade", False, age_seconds
    if status in {"new", "pending_new", "pending"}:
        return "submitted", "continue_waiting_for_broker_acceptance_or_fill", False, age_seconds
    if status in OPEN_ORDER_STATUSES:
        stale = age_seconds is not None and age_seconds > STALE_ACCEPTED_ORDER_SECONDS
        if stale:
            return "stale", "cancel_replace_needed_review_only_no_broker_action", True, age_seconds
        return "accepted", "continue_waiting_for_broker_fill", False, age_seconds
    if status in CLOSED_ORDER_STATUSES:
        return "closed", "record_terminal_order_state_no_broker_action", False, age_seconds
    return "cancel_replace_needed", "repair_unknown_order_status_before_any_action", False, age_seconds


def _lifecycle_order_record(
    order: dict[str, Any],
    matched_trade: dict[str, Any] | None,
    generated_at: str,
    generated_dt: datetime,
) -> dict[str, Any]:
    state, next_action, stale, age_seconds = _order_lifecycle_state(order, matched_trade, generated_dt)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_paper_lifecycle_v2_record",
        "phase_id": PHASE_ID,
        "lifecycle_record_id": _hash_id("qadam-paper-lifecycle-v2", ["order", _order_key(order)]),
        "generated_at": generated_at,
        "source_record_type": "paper_order_mirror",
        "source_record_id": _order_key(order),
        "instrument": order.get("instrument") or order.get("symbol"),
        "direction": order.get("direction") or order.get("side"),
        "broker_status": order.get("status"),
        "lifecycle_state": state,
        "matched_closed_trade_id": matched_trade.get("trade_id") if matched_trade else None,
        "ambiguous_state": False,
        "stale": stale,
        "age_seconds": age_seconds,
        "stale_policy": {
            "stale_after_seconds": STALE_ACCEPTED_ORDER_SECONDS,
            "policy": next_action,
            "cancel_replace_allowed_by_phase_10": False,
            "broker_write_allowed": False,
        },
        "next_lifecycle_action": next_action,
        "paper_order_created": False,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "authority": _authority(),
        "artifact_refs": [_artifact_ref(PAPER_ORDERS_ARTIFACT, _order_key(order))],
    }


def _lifecycle_position_record(position: dict[str, Any], generated_at: str) -> dict[str, Any]:
    symbol = str(position.get("instrument") or position.get("symbol") or "").strip()
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_paper_lifecycle_v2_record",
        "phase_id": PHASE_ID,
        "lifecycle_record_id": _hash_id("qadam-paper-lifecycle-v2", ["position", symbol, position.get("position_id")]),
        "generated_at": generated_at,
        "source_record_type": "paper_position_mirror",
        "source_record_id": position.get("position_id") or symbol,
        "instrument": symbol,
        "broker_status": position.get("status", "open_position"),
        "lifecycle_state": "open",
        "ambiguous_state": False,
        "stale": False,
        "stale_policy": {
            "policy": "monitor_open_position_until_guarded_exit_or_close",
            "position_close_allowed_by_phase_10": False,
            "broker_write_allowed": False,
        },
        "next_lifecycle_action": "monitor_open_position_until_guarded_exit_or_close",
        "paper_order_created": False,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "authority": _authority(),
        "artifact_refs": [_artifact_ref(PAPER_POSITIONS_ARTIFACT, symbol)],
    }


def _proof_record(
    trade: dict[str, Any],
    matched_order: dict[str, Any] | None,
    generated_at: str,
) -> dict[str, Any]:
    state, checks, missing = _proof_state(trade, matched_order)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_paper_proof_boundary_record",
        "phase_id": PHASE_ID,
        "proof_boundary_record_id": _hash_id("qadam-paper-proof-boundary-v2", ["proof", _trade_key(trade)]),
        "generated_at": generated_at,
        "trade_id": trade.get("trade_id"),
        "instrument": trade.get("instrument"),
        "closed_at": trade.get("closed_at"),
        "postmortem_status": trade.get("postmortem_status"),
        "proof_state": state,
        "proof_eligible": state == "proof_eligible",
        "proof_rejected": state == "proof_rejected",
        "lineage_checks": checks,
        "missing_lineage": missing,
        "proof_rejection_reason": "none" if not missing else "missing_" + "_".join(missing[:5]),
        "real_closed_paper_trade_required": True,
        "complete_lineage_required": True,
        "backtest_shadow_or_synthetic_credit": False,
        "paper_proof_ledger_credit_allowed": False,
        "paper_proof_ledger_credit_created": False,
        "proof_credit_allowed": False,
        "paper_order_created": False,
        "broker_write_count": 0,
        "authority": _authority(),
        "artifact_refs": [_artifact_ref(PAPER_CLOSED_TRADES_ARTIFACT, _trade_key(trade))],
    }


def _lifecycle_closed_trade_record(proof_record: dict[str, Any], generated_at: str) -> dict[str, Any]:
    if proof_record.get("proof_state") == "proof_eligible":
        state = "proof_eligible"
        next_action = "audit_for_paper_proof_ledger_review_no_credit_created"
    elif "postmortem_complete" in proof_record.get("missing_lineage", []):
        state = "postmortem_due"
        next_action = "complete_postmortem_before_proof_review"
    else:
        state = "proof_rejected"
        next_action = "repair_missing_lineage_before_proof_review"
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_paper_lifecycle_v2_record",
        "phase_id": PHASE_ID,
        "lifecycle_record_id": _hash_id("qadam-paper-lifecycle-v2", ["closed", proof_record.get("trade_id")]),
        "generated_at": generated_at,
        "source_record_type": "paper_closed_trade_mirror",
        "source_record_id": proof_record.get("trade_id"),
        "instrument": proof_record.get("instrument"),
        "broker_status": "closed",
        "lifecycle_state": state,
        "proof_state": proof_record.get("proof_state"),
        "ambiguous_state": False,
        "stale": False,
        "stale_policy": {
            "policy": "postmortem_and_complete_lineage_required_before_proof",
            "broker_write_allowed": False,
        },
        "next_lifecycle_action": next_action,
        "paper_order_created": False,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "authority": _authority(),
        "artifact_refs": [_artifact_ref(PAPER_CLOSED_TRADES_ARTIFACT, str(proof_record.get("trade_id")))],
    }


def build_paper_lifecycle_proof_boundary(settings: Settings | None = None) -> PaperLifecycleProofBundle:
    generated_at = _iso()
    generated_dt = _parse_dt(generated_at) or _now()
    context = _load_context(settings)
    closed_by_id = _closed_trade_by_order_id(context["paper_closed_trades"])
    orders_by_id = {_order_key(order): order for order in context["paper_orders"] if _order_key(order)}

    lifecycle_records: list[dict[str, Any]] = []
    for order in context["paper_orders"]:
        lifecycle_records.append(
            _lifecycle_order_record(
                order,
                closed_by_id.get(_order_key(order)),
                generated_at,
                generated_dt,
            )
        )
    for position in context["paper_positions"]:
        lifecycle_records.append(_lifecycle_position_record(position, generated_at))

    proof_records = [
        _proof_record(trade, orders_by_id.get(_trade_key(trade)), generated_at)
        for trade in context["paper_closed_trades"]
    ]
    lifecycle_records.extend(_lifecycle_closed_trade_record(record, generated_at) for record in proof_records)

    state_counts = Counter(str(record.get("lifecycle_state") or "unknown") for record in lifecycle_records)
    stale_accepted_order_count = sum(1 for record in lifecycle_records if record.get("lifecycle_state") == "stale")
    cancel_replace_needed_count = sum(1 for record in lifecycle_records if record.get("lifecycle_state") == "cancel_replace_needed")
    ambiguous_count = sum(
        1
        for record in lifecycle_records
        if record.get("ambiguous_state") is True or record.get("lifecycle_state") not in LIFECYCLE_STATES
    )
    proof_eligible_count = sum(1 for record in proof_records if record.get("proof_eligible") is True)
    proof_rejected_count = sum(1 for record in proof_records if record.get("proof_rejected") is True)
    missing_lineage_counts = Counter(reason for record in proof_records for reason in _safe_list(record.get("missing_lineage")))
    backtest_shadow_or_synthetic_credit_count = sum(
        1 for record in proof_records if record.get("backtest_shadow_or_synthetic_credit") is True
    )
    primary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_paper_lifecycle_v2",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "paper_lifecycle_v2_ready" if ambiguous_count == 0 else "paper_lifecycle_v2_repair_required",
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "proposal_first": True,
        "paper_order_mirror_count": len(context["paper_orders"]),
        "open_position_mirror_count": len(context["paper_positions"]),
        "closed_paper_trade_count": len(context["paper_closed_trades"]),
        "lifecycle_record_count": len(lifecycle_records),
        "ambiguous_lifecycle_count": ambiguous_count,
        "no_paper_order_ambiguous": ambiguous_count == 0,
        "stale_accepted_order_count": stale_accepted_order_count,
        "cancel_replace_needed_count": cancel_replace_needed_count,
        "state_counts": dict(state_counts),
        "stale_accepted_order_policy": {
            "stale_after_seconds": STALE_ACCEPTED_ORDER_SECONDS,
            "policy": "stale accepted orders are labelled stale or cancel_replace_needed for review only; Phase 10 cannot cancel or replace.",
            "cancel_replace_allowed_by_phase_10": False,
        },
        "paper_order_created": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "artifact_refs": {
            "lifecycle_records": LIFECYCLE_RECORDS_ARTIFACT,
            "proof_boundary": PROOF_BOUNDARY_ARTIFACT,
            "proof_records": PROOF_RECORDS_ARTIFACT,
        },
        "authority": _authority(),
    }
    proof_boundary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_paper_proof_boundary_audit",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "paper_proof_boundary_ready",
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "proposal_first": True,
        "closed_paper_trade_count": len(context["paper_closed_trades"]),
        "proof_record_count": len(proof_records),
        "proof_eligible_count": proof_eligible_count,
        "proof_rejected_count": proof_rejected_count,
        "missing_lineage_counts": dict(missing_lineage_counts),
        "real_closed_paper_trade_required": True,
        "complete_lineage_required": True,
        "proof_credit_requires_real_closed_trade_with_complete_lineage": True,
        "backtest_shadow_or_synthetic_proof_credit_count": backtest_shadow_or_synthetic_credit_count,
        "paper_proof_ledger_credit_created": False,
        "paper_proof_ledger_credit_allowed": False,
        "proof_credit_allowed": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "artifact_refs": {"proof_records": PROOF_RECORDS_ARTIFACT},
        "authority": _authority(),
    }
    dashboard_summary = _dashboard_summary(primary, proof_boundary, generated_at)
    return PaperLifecycleProofBundle(
        primary=primary,
        lifecycle_records=lifecycle_records,
        proof_boundary=proof_boundary,
        proof_records=proof_records,
        dashboard_summary=dashboard_summary,
    )


def _dashboard_summary(primary: dict[str, Any], proof_boundary: dict[str, Any], generated_at: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_paper_lifecycle_v2_dashboard_summary",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": primary.get("status"),
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "paper_order_mirror_count": primary.get("paper_order_mirror_count"),
        "open_position_mirror_count": primary.get("open_position_mirror_count"),
        "closed_paper_trade_count": primary.get("closed_paper_trade_count"),
        "lifecycle_record_count": primary.get("lifecycle_record_count"),
        "ambiguous_lifecycle_count": primary.get("ambiguous_lifecycle_count"),
        "no_paper_order_ambiguous": primary.get("no_paper_order_ambiguous"),
        "stale_accepted_order_count": primary.get("stale_accepted_order_count"),
        "cancel_replace_needed_count": primary.get("cancel_replace_needed_count"),
        "state_counts": primary.get("state_counts"),
        "proof_boundary_state": proof_boundary.get("status"),
        "proof_eligible_count": proof_boundary.get("proof_eligible_count"),
        "proof_rejected_count": proof_boundary.get("proof_rejected_count"),
        "proof_credit_requires_real_closed_trade_with_complete_lineage": proof_boundary.get("proof_credit_requires_real_closed_trade_with_complete_lineage"),
        "backtest_shadow_or_synthetic_proof_credit_count": proof_boundary.get("backtest_shadow_or_synthetic_proof_credit_count"),
        "paper_proof_ledger_credit_allowed": False,
        "proof_credit_allowed": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "message": (
            "Paper lifecycle states are explicit. Paper proof ledger credit requires a real closed paper trade "
            "with complete lineage and postmortem; mirrored-only or incomplete records remain proof-rejected."
        ),
        "authority": _authority(),
    }


def write_paper_lifecycle_proof_boundary(bundle: PaperLifecycleProofBundle, settings: Settings | None = None) -> dict[str, str]:
    runtime = _runtime_dir(settings)
    paths = {
        "primary": runtime / PRIMARY_ARTIFACT,
        "lifecycle_records": runtime / LIFECYCLE_RECORDS_ARTIFACT,
        "proof_boundary": runtime / PROOF_BOUNDARY_ARTIFACT,
        "proof_records": runtime / PROOF_RECORDS_ARTIFACT,
        "dashboard_summary": runtime / DASHBOARD_SUMMARY_ARTIFACT,
        "events": runtime / EVENTS_ARTIFACT,
    }
    _write_json(paths["primary"], bundle.primary)
    _write_jsonl(paths["lifecycle_records"], bundle.lifecycle_records)
    _write_json(paths["proof_boundary"], bundle.proof_boundary)
    _write_jsonl(paths["proof_records"], bundle.proof_records)
    _write_json(paths["dashboard_summary"], bundle.dashboard_summary)
    _append_jsonl(
        paths["events"],
        {
            "schema_version": SCHEMA_VERSION,
            "phase_id": PHASE_ID,
            "event_type": "paper_lifecycle_proof_boundary_written",
            "generated_at": bundle.primary.get("generated_at"),
            "status": bundle.primary.get("status"),
            "ambiguous_lifecycle_count": bundle.primary.get("ambiguous_lifecycle_count"),
            "proof_eligible_count": bundle.proof_boundary.get("proof_eligible_count"),
            "proof_rejected_count": bundle.proof_boundary.get("proof_rejected_count"),
            "paper_order_created": False,
            "broker_write_count": 0,
            "proof_credit_allowed": False,
            "authority": _authority(),
        },
    )
    return {key: str(path) for key, path in paths.items()}


def build_and_write_paper_lifecycle_proof_boundary(settings: Settings | None = None) -> tuple[PaperLifecycleProofBundle, dict[str, str]]:
    bundle = build_paper_lifecycle_proof_boundary(settings)
    written = write_paper_lifecycle_proof_boundary(bundle, settings)
    return bundle, written


def _validate_authority(payload: dict[str, Any], prefix: str) -> list[str]:
    errors: list[str] = []
    authority = _safe_dict(payload.get("authority"))
    for key, expected in AUTHORITY_FLAGS.items():
        if authority.get(key) != expected:
            errors.append(f"{prefix}_{key}_authority_invalid")
    for field in FORBIDDEN_TRUE_FIELDS:
        if payload.get(field) is True:
            errors.append(f"{prefix}_{field}_must_not_be_true")
    for field in FORBIDDEN_NONZERO_FIELDS:
        if _safe_int(payload.get(field), 0) != 0:
            errors.append(f"{prefix}_{field}_must_be_zero")
    return errors


def validate_lifecycle_record(record: dict[str, Any], prefix: str) -> list[str]:
    errors: list[str] = []
    if record.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{prefix}_schema_version_invalid")
    if record.get("phase_id") != PHASE_ID:
        errors.append(f"{prefix}_phase_id_invalid")
    if record.get("lifecycle_state") not in LIFECYCLE_STATES:
        errors.append(f"{prefix}_lifecycle_state_invalid")
    if record.get("ambiguous_state") is not False:
        errors.append(f"{prefix}_ambiguous_state_must_be_false")
    if record.get("paper_order_created") is not False:
        errors.append(f"{prefix}_paper_order_created_must_be_false")
    if record.get("proof_credit_allowed") is not False:
        errors.append(f"{prefix}_proof_credit_allowed_must_be_false")
    errors.extend(_validate_authority(record, prefix))
    return errors


def validate_proof_record(record: dict[str, Any], prefix: str) -> list[str]:
    errors: list[str] = []
    if record.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{prefix}_schema_version_invalid")
    if record.get("phase_id") != PHASE_ID:
        errors.append(f"{prefix}_phase_id_invalid")
    checks = _safe_dict(record.get("lineage_checks"))
    missing = _safe_list(record.get("missing_lineage"))
    expected_missing = [key for key, passed in checks.items() if passed is not True]
    if sorted(missing) != sorted(expected_missing):
        errors.append(f"{prefix}_missing_lineage_mismatch")
    if record.get("proof_eligible") is True and missing:
        errors.append(f"{prefix}_proof_eligible_with_missing_lineage")
    if record.get("proof_eligible") is True and checks.get("real_closed_paper_trade") is not True:
        errors.append(f"{prefix}_proof_eligible_without_real_closed_trade")
    if record.get("backtest_shadow_or_synthetic_credit") is not False:
        errors.append(f"{prefix}_synthetic_credit_must_be_false")
    if record.get("paper_proof_ledger_credit_allowed") is not False:
        errors.append(f"{prefix}_paper_proof_ledger_credit_allowed_must_be_false")
    if record.get("proof_credit_allowed") is not False:
        errors.append(f"{prefix}_proof_credit_allowed_must_be_false")
    errors.extend(_validate_authority(record, prefix))
    return errors


def validate_paper_lifecycle_proof_boundary_bundle(bundle: PaperLifecycleProofBundle | dict[str, Any]) -> list[str]:
    if isinstance(bundle, PaperLifecycleProofBundle):
        primary = bundle.primary
        lifecycle_records = bundle.lifecycle_records
        proof_boundary = bundle.proof_boundary
        proof_records = bundle.proof_records
        dashboard = bundle.dashboard_summary
    else:
        primary = _safe_dict(bundle.get("primary"))
        lifecycle_records = _safe_list(bundle.get("lifecycle_records"))
        proof_boundary = _safe_dict(bundle.get("proof_boundary"))
        proof_records = _safe_list(bundle.get("proof_records"))
        dashboard = _safe_dict(bundle.get("dashboard_summary"))
    errors: list[str] = []
    if primary.get("schema_version") != SCHEMA_VERSION:
        errors.append("primary_schema_version_invalid")
    if primary.get("phase_id") != PHASE_ID:
        errors.append("primary_phase_id_invalid")
    if primary.get("artifact_type") != "qadam_paper_lifecycle_v2":
        errors.append("primary_artifact_type_invalid")
    if primary.get("status") != "paper_lifecycle_v2_ready":
        errors.append("primary_status_not_ready")
    if primary.get("no_paper_order_ambiguous") is not True:
        errors.append("paper_order_ambiguous_state_present")
    if _safe_int(primary.get("ambiguous_lifecycle_count")) != 0:
        errors.append("ambiguous_lifecycle_count_nonzero")
    if len(lifecycle_records) != _safe_int(primary.get("lifecycle_record_count")):
        errors.append("lifecycle_record_count_mismatch")
    if proof_boundary.get("artifact_type") != "qadam_paper_proof_boundary_audit":
        errors.append("proof_boundary_artifact_type_invalid")
    if proof_boundary.get("proof_credit_requires_real_closed_trade_with_complete_lineage") is not True:
        errors.append("proof_boundary_requirement_missing")
    if _safe_int(proof_boundary.get("backtest_shadow_or_synthetic_proof_credit_count")) != 0:
        errors.append("synthetic_proof_credit_count_nonzero")
    if len(proof_records) != _safe_int(proof_boundary.get("proof_record_count")):
        errors.append("proof_record_count_mismatch")
    if dashboard.get("artifact_type") != "qadam_paper_lifecycle_v2_dashboard_summary":
        errors.append("dashboard_artifact_type_invalid")
    for index, record in enumerate(lifecycle_records, start=1):
        errors.extend(validate_lifecycle_record(record, f"lifecycle_{index}"))
    for index, record in enumerate(proof_records, start=1):
        errors.extend(validate_proof_record(record, f"proof_{index}"))
    for payload, prefix in (
        (primary, "primary"),
        (proof_boundary, "proof_boundary"),
        (dashboard, "dashboard"),
    ):
        errors.extend(_validate_authority(payload, prefix))
    return errors


def validate_negative_paper_lifecycle_proof_boundary_probes(settings: Settings | None = None) -> list[str]:
    bundle = build_paper_lifecycle_proof_boundary(settings)
    errors: list[str] = []
    if not bundle.lifecycle_records or not bundle.proof_records:
        return ["negative_probe_skipped_missing_lifecycle_or_proof_records"]
    unsafe_lifecycle = json.loads(json.dumps(bundle.lifecycle_records[0]))
    unsafe_lifecycle["ambiguous_state"] = True
    if not validate_lifecycle_record(unsafe_lifecycle, "negative_lifecycle"):
        errors.append("negative_probe_failed_for_ambiguous_lifecycle")

    unsafe_order = json.loads(json.dumps(bundle.lifecycle_records[0]))
    unsafe_order["paper_order_created"] = True
    unsafe_order["authority"]["paper_order_created"] = True
    if not validate_lifecycle_record(unsafe_order, "negative_order"):
        errors.append("negative_probe_failed_for_order_boundary")

    unsafe_proof = json.loads(json.dumps(bundle.proof_records[0]))
    unsafe_proof["proof_eligible"] = True
    unsafe_proof["proof_state"] = "proof_eligible"
    if not validate_proof_record(unsafe_proof, "negative_proof"):
        errors.append("negative_probe_failed_for_incomplete_lineage_proof")

    unsafe_credit = json.loads(json.dumps(bundle.proof_records[0]))
    unsafe_credit["paper_proof_ledger_credit_allowed"] = True
    unsafe_credit["authority"]["paper_proof_ledger_credit_allowed"] = True
    if not validate_proof_record(unsafe_credit, "negative_credit"):
        errors.append("negative_probe_failed_for_proof_credit_boundary")
    return errors


def load_paper_lifecycle_proof_boundary(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "primary": _read_json(runtime / PRIMARY_ARTIFACT),
        "lifecycle_records": _read_jsonl(runtime / LIFECYCLE_RECORDS_ARTIFACT),
        "proof_boundary": _read_json(runtime / PROOF_BOUNDARY_ARTIFACT),
        "proof_records": _read_jsonl(runtime / PROOF_RECORDS_ARTIFACT),
        "dashboard_summary": _read_json(runtime / DASHBOARD_SUMMARY_ARTIFACT),
    }
