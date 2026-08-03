"""Guarded lifecycle manager for the one-time operator exploratory paper sleeve.

Price exits live at Alpaca as bracket children. This manager adds a bounded
time exit without granting Qadam general discretionary paper-order authority.
It can only cancel protective children and close an exact matching position
for the sleeve recorded in its durable operator approval contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.paperops_alpaca_paper_post import _endpoint_context, _headers, _orders_url
from orchestrator.qadam_operator_ready_common import (
    append_jsonl_durable,
    now_iso,
    read_json,
    write_json_atomic,
)


SCHEMA_VERSION = "qadam_operator_exploratory_exit_manager.v1"
APPROVAL_SCHEMA_VERSION = "qadam_operator_exploratory_exit_approval.v1"

SLEEVE_ARTIFACT = "qadam_operator_exploratory_sleeve.json"
SUBMISSION_ARTIFACT = "qadam_operator_exploratory_sleeve_submission.json"
APPROVAL_ARTIFACT = "qadam_operator_exploratory_exit_approval.json"
MANAGER_ARTIFACT = "qadam_operator_exploratory_exit_manager.json"
MANAGER_HISTORY = "qadam_operator_exploratory_exit_manager_history.jsonl"
ACTION_LEDGER = "qadam_operator_exploratory_exit_actions.jsonl"
EVENT_LEDGER = "qadam_operator_exploratory_exit_events.jsonl"

PAPER_API_HOST = "paper-api.alpaca.markets"
NEW_YORK = ZoneInfo("America/New_York")
TIME_EXIT_MINUTES_BEFORE_CLOSE = 30

OPEN_ORDER_STATES = frozenset(
    {
        "accepted",
        "calculated",
        "held",
        "new",
        "partially_filled",
        "pending_cancel",
        "pending_new",
        "pending_replace",
        "stopped",
    }
)
TERMINAL_ORDER_STATES = frozenset(
    {"canceled", "done_for_day", "expired", "filled", "rejected", "replaced", "suspended"}
)


class BrokerClient(Protocol):
    def snapshot(self, *, start: str, end: str, after: str) -> dict[str, Any]: ...

    def cancel_order(self, order_id: str) -> dict[str, Any]: ...

    def submit_oco(
        self,
        *,
        symbol: str,
        side: str,
        quantity: float,
        take_profit_price: float,
        stop_loss_price: float,
        client_order_id: str,
    ) -> dict[str, Any]: ...

    def close_position(self, symbol: str, quantity: float) -> dict[str, Any]: ...


class AlpacaPaperClientError(RuntimeError):
    """Sanitized broker transport error; response bodies are never persisted."""


@dataclass
class AlpacaPaperSleeveClient:
    settings: Settings
    timeout_seconds: float = 15.0

    def _base_url(self) -> str:
        return _orders_url(self.settings).rsplit("/orders", 1)[0]

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover - production dependency
            raise AlpacaPaperClientError("missing_httpx") from exc
        url = f"{self._base_url()}/{path.lstrip('/')}"
        try:
            with httpx.Client(timeout=self.timeout_seconds, follow_redirects=False) as client:
                response = client.request(
                    method,
                    url,
                    headers=_headers(self.settings),
                    params=params,
                    json=json_body,
                )
        except Exception as exc:  # noqa: BLE001 - persist only the class
            raise AlpacaPaperClientError(type(exc).__name__) from exc
        if not 200 <= response.status_code < 300:
            raise AlpacaPaperClientError(f"http_{response.status_code}")
        if response.status_code == 204 or not response.content:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise AlpacaPaperClientError("invalid_json_response") from exc

    def snapshot(self, *, start: str, end: str, after: str) -> dict[str, Any]:
        positions = self._request("GET", "positions")
        orders = self._request(
            "GET",
            "orders",
            params={
                "status": "all",
                "nested": "true",
                "limit": 500,
                "direction": "desc",
                "after": after,
            },
        )
        clock = self._request("GET", "clock")
        calendar = self._request("GET", "calendar", params={"start": start, "end": end})
        if not isinstance(positions, list) or not isinstance(orders, list):
            raise AlpacaPaperClientError("unexpected_broker_collection_shape")
        if not isinstance(clock, dict) or not isinstance(calendar, list):
            raise AlpacaPaperClientError("unexpected_broker_schedule_shape")
        return {
            "positions": positions,
            "orders": orders,
            "clock": clock,
            "calendar": calendar,
        }

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        self._request("DELETE", f"orders/{order_id}")
        return {"requested": True, "http_status": 204}

    def submit_oco(
        self,
        *,
        symbol: str,
        side: str,
        quantity: float,
        take_profit_price: float,
        stop_loss_price: float,
        client_order_id: str,
    ) -> dict[str, Any]:
        payload = self._request(
            "POST",
            "orders",
            json_body={
                "symbol": symbol.upper(),
                "side": side,
                "type": "limit",
                "qty": _quantity_text(quantity),
                "time_in_force": "gtc",
                "order_class": "oco",
                "client_order_id": client_order_id,
                "take_profit": {"limit_price": _price_text(take_profit_price)},
                "stop_loss": {"stop_price": _price_text(stop_loss_price)},
            },
        )
        payload = payload if isinstance(payload, dict) else {}
        return {
            "requested": True,
            "http_status": 200,
            "broker_order_id_hash": _hash_identifier(payload.get("id")),
            "broker_order_status": str(payload.get("status") or "") or None,
        }

    def close_position(self, symbol: str, quantity: float) -> dict[str, Any]:
        payload = self._request(
            "DELETE",
            f"positions/{symbol.upper()}",
            params={"qty": _quantity_text(quantity)},
        )
        payload = payload if isinstance(payload, dict) else {}
        return {
            "requested": True,
            "http_status": 200,
            "broker_order_id_hash": _hash_identifier(payload.get("id")),
            "broker_order_status": str(payload.get("status") or "") or None,
        }


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir).resolve()


def _hash_identifier(value: Any) -> str | None:
    text = str(value or "").strip()
    return sha256(text.encode("utf-8")).hexdigest() if text else None


def _material_hash(value: Any) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _parse_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _quantity_text(value: float) -> str:
    return f"{float(value):.8f}".rstrip("0").rstrip(".")


def _price_text(value: float) -> str:
    return f"{float(value):.2f}"


def _exit_oco_client_order_id(sleeve_id: str, leg_id: str) -> str:
    material = f"{sleeve_id}:{leg_id}:persistent-price-exit"
    return f"q7-operator-exit-{sha256(material.encode('utf-8')).hexdigest()[:24]}"


def _flatten_orders(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(order: dict[str, Any], parent_id: str | None = None) -> None:
        record = dict(order)
        legs = record.pop("legs", None)
        if parent_id and not record.get("parent_order_id"):
            record["parent_order_id"] = parent_id
        identity = str(record.get("id") or _material_hash(record))
        if identity not in seen:
            seen.add(identity)
            flattened.append(record)
        for leg in legs or []:
            if isinstance(leg, dict):
                add(leg, str(record.get("id") or "") or None)

    for order in orders:
        if isinstance(order, dict):
            add(order)
    return flattened


def _calendar_close(record: dict[str, Any]) -> datetime | None:
    day = str(record.get("date") or "").strip()
    close = str(record.get("close") or record.get("session_close") or "").strip()
    if not day or not close:
        return None
    try:
        return datetime.fromisoformat(f"{day}T{close}").replace(tzinfo=NEW_YORK)
    except ValueError:
        return None


def _time_exit_schedule(
    *,
    filled_at: datetime | None,
    maximum_holding_sessions: int,
    calendar: list[dict[str, Any]],
) -> dict[str, Any]:
    if filled_at is None:
        return {"status": "missing_fill_timestamp", "session_count": 0}
    fill_day = filled_at.astimezone(NEW_YORK).date()
    sessions: list[tuple[date, datetime]] = []
    for record in calendar:
        close = _calendar_close(record)
        if close is None:
            continue
        session_day = close.date()
        if session_day >= fill_day:
            sessions.append((session_day, close))
    sessions.sort(key=lambda value: value[0])
    if len(sessions) < maximum_holding_sessions:
        return {
            "status": "insufficient_broker_calendar",
            "session_count": len(sessions),
            "required_session_count": maximum_holding_sessions,
        }
    due_day, due_close = sessions[maximum_holding_sessions - 1]
    due_at = due_close - timedelta(minutes=TIME_EXIT_MINUTES_BEFORE_CLOSE)
    return {
        "status": "scheduled",
        "entry_session": sessions[0][0].isoformat(),
        "maximum_holding_sessions": maximum_holding_sessions,
        "time_exit_session": due_day.isoformat(),
        "regular_session_close_at": due_close.astimezone(timezone.utc).isoformat(),
        "time_exit_due_at": due_at.astimezone(timezone.utc).isoformat(),
        "minutes_before_close": TIME_EXIT_MINUTES_BEFORE_CLOSE,
        "session_count": len(sessions),
    }


def build_exit_approval(
    *,
    sleeve: dict[str, Any],
    submission: dict[str, Any],
    explicit_operator_approval: bool,
) -> dict[str, Any]:
    generated_at = now_iso()
    symbols = sorted(
        str(leg.get("execution_symbol") or "").upper()
        for leg in sleeve.get("legs") or []
        if str(leg.get("execution_symbol") or "").strip()
    )
    maximum_sessions = {
        str(leg.get("execution_symbol") or "").upper(): int(
            leg.get("maximum_holding_sessions") or 0
        )
        for leg in sleeve.get("legs") or []
        if str(leg.get("execution_symbol") or "").strip()
    }
    blockers: list[str] = []
    if not explicit_operator_approval:
        blockers.append("explicit_operator_exit_approval_missing")
    if sleeve.get("explicit_operator_approval") is not True:
        blockers.append("source_sleeve_operator_approval_missing")
    if sleeve.get("paper_only") is not True or sleeve.get("live_capital_enabled") is not False:
        blockers.append("source_sleeve_not_paper_only")
    if submission.get("status") != "submitted_to_alpaca_paper":
        blockers.append("source_sleeve_not_submitted")
    if submission.get("post_succeeded_count") != len(symbols) or not symbols:
        blockers.append("source_submission_not_complete")
    if submission.get("sleeve_id") != sleeve.get("sleeve_id"):
        blockers.append("source_sleeve_identity_mismatch")
    if any(value < 1 for value in maximum_sessions.values()):
        blockers.append("maximum_holding_sessions_invalid")
    return {
        "schema_version": APPROVAL_SCHEMA_VERSION,
        "artifact_type": "qadam_operator_exploratory_exit_approval",
        "generated_at": generated_at,
        "status": "approved" if not blockers else "blocked",
        "sleeve_id": sleeve.get("sleeve_id"),
        "operator_request_id": sleeve.get("request_id"),
        "approval_scope": "this_exact_submitted_operator_exploratory_sleeve_only",
        "explicit_operator_exit_approval": explicit_operator_approval,
        "approved_symbols": symbols,
        "maximum_holding_sessions_by_symbol": maximum_sessions,
        "allowed_broker_mutations": [
            "cancel_exact_sleeve_protective_exit",
            "submit_exact_closing_only_gtc_oco_protection",
            "close_exact_matching_sleeve_position_after_time_deadline",
        ],
        "price_exit_priority": "broker_side_take_profit_or_stop_loss_first",
        "time_exit_policy": (
            "If neither broker-side price exit closes the position first, cancel the exact "
            "remaining protective children and close the exact matching position beginning "
            f"{TIME_EXIT_MINUTES_BEFORE_CLOSE} minutes before the fifth trading-session close."
        ),
        "paper_only": True,
        "live_capital_enabled": False,
        "new_position_allowed": False,
        "position_increase_allowed": False,
        "strategy_promotion_allowed": False,
        "proof_credit_allowed": False,
        "paper_proof_ledger_credit_allowed": False,
        "blockers": sorted(set(blockers)),
    }


def validate_exit_approval(
    approval: dict[str, Any],
    sleeve: dict[str, Any],
    submission: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if approval.get("schema_version") != APPROVAL_SCHEMA_VERSION:
        errors.append("approval_schema_invalid")
    if approval.get("status") != "approved":
        errors.append("approval_not_approved")
    if approval.get("explicit_operator_exit_approval") is not True:
        errors.append("approval_not_explicit")
    if approval.get("sleeve_id") != sleeve.get("sleeve_id"):
        errors.append("approval_sleeve_identity_mismatch")
    if approval.get("sleeve_id") != submission.get("sleeve_id"):
        errors.append("approval_submission_identity_mismatch")
    expected = sorted(
        str(leg.get("execution_symbol") or "").upper()
        for leg in sleeve.get("legs") or []
    )
    if approval.get("approved_symbols") != expected:
        errors.append("approval_symbol_scope_mismatch")
    if approval.get("paper_only") is not True:
        errors.append("approval_not_paper_only")
    if approval.get("live_capital_enabled") is not False:
        errors.append("approval_live_capital_not_false")
    for key in (
        "new_position_allowed",
        "position_increase_allowed",
        "strategy_promotion_allowed",
        "proof_credit_allowed",
        "paper_proof_ledger_credit_allowed",
    ):
        if approval.get(key) is not False:
            errors.append(f"approval_forbidden_authority:{key}")
    return sorted(set(errors))


def _find_parent_order(
    orders: list[dict[str, Any]], client_order_id: str
) -> dict[str, Any] | None:
    matches = [
        order
        for order in orders
        if str(order.get("client_order_id") or "") == client_order_id
    ]
    matches.sort(
        key=lambda order: str(order.get("submitted_at") or order.get("created_at") or ""),
        reverse=True,
    )
    return matches[0] if matches else None


def _closing_side(direction: str) -> str:
    return "sell" if direction == "long" else "buy"


def _leg_state(
    *,
    leg: dict[str, Any],
    orders: list[dict[str, Any]],
    positions: dict[str, dict[str, Any]],
    calendar: list[dict[str, Any]],
    market_open: bool,
    now: datetime,
    exit_oco_client_order_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    symbol = str(leg.get("execution_symbol") or "").upper()
    client_order_id = str(leg.get("client_order_id") or "")
    parent = _find_parent_order(orders, client_order_id)
    parent_id = str((parent or {}).get("id") or "")
    opening_children = [
        order for order in orders if str(order.get("parent_order_id") or "") == parent_id
    ] if parent_id else []
    oco_parent = _find_parent_order(orders, exit_oco_client_order_id)
    oco_parent_id = str((oco_parent or {}).get("id") or "")
    oco_children = [
        order for order in orders if str(order.get("parent_order_id") or "") == oco_parent_id
    ] if oco_parent_id else []
    protection_orders = [*opening_children]
    if oco_parent is not None:
        protection_orders.append(oco_parent)
    protection_orders.extend(oco_children)
    position = positions.get(symbol)
    direction = "long" if str(leg.get("side") or "").lower() == "buy" else "short"
    expected_quantity = float(leg.get("quantity") or 0.0)
    actual_quantity = abs(_float((position or {}).get("qty")))
    actual_direction = str((position or {}).get("side") or "").lower()
    filled_at = _parse_datetime((parent or {}).get("filled_at"))
    schedule = _time_exit_schedule(
        filled_at=filled_at,
        maximum_holding_sessions=int(leg.get("maximum_holding_sessions") or 0),
        calendar=calendar,
    )
    due_at = _parse_datetime(schedule.get("time_exit_due_at"))
    time_exit_due = bool(due_at and now >= due_at)
    targets = [
        order
        for order in protection_orders
        if str(order.get("type") or order.get("order_type") or "").lower() == "limit"
    ]
    stops = [
        order
        for order in protection_orders
        if str(order.get("type") or order.get("order_type") or "").lower()
        in {"stop", "stop_limit"}
    ]
    active_children = [
        order
        for order in protection_orders
        if str(order.get("status") or "").lower() in OPEN_ORDER_STATES
    ]
    filled_children = [
        order
        for order in protection_orders
        if str(order.get("status") or "").lower() == "filled"
    ]
    pending_closes = [
        order
        for order in orders
        if str(order.get("symbol") or "").upper() == symbol
        and not order.get("parent_order_id")
        and str(order.get("client_order_id") or "") != client_order_id
        and str(order.get("client_order_id") or "") != exit_oco_client_order_id
        and str(order.get("side") or "").lower() == _closing_side(direction)
        and str(order.get("status") or "").lower() in OPEN_ORDER_STATES
    ]
    target_active_count = sum(
        str(order.get("status") or "").lower() in OPEN_ORDER_STATES for order in targets
    )
    stop_active_count = sum(
        str(order.get("status") or "").lower() in OPEN_ORDER_STATES for order in stops
    )
    active_time_in_force_values = sorted(
        {
            str(order.get("time_in_force") or "").lower()
            for order in active_children
            if str(order.get("time_in_force") or "").strip()
        }
    )
    persistent_protection = (
        target_active_count == 1
        and stop_active_count == 1
        and active_time_in_force_values == ["gtc"]
    )
    protective_cancel_pending = any(
        str(order.get("status") or "").lower() == "pending_cancel"
        for order in active_children
    )
    exact_position_match = bool(position) and (
        actual_direction == direction
        and abs(actual_quantity - expected_quantity) <= 1e-8
    )
    repair_reasons: list[str] = []
    if position and not exact_position_match:
        repair_reasons.append("position_no_longer_matches_exact_sleeve_scope")
    if position and parent is None:
        repair_reasons.append("opening_parent_order_missing")
    if schedule.get("status") != "scheduled":
        repair_reasons.append(str(schedule.get("status") or "time_exit_schedule_missing"))
    if position and len(targets) > 2:
        repair_reasons.append("duplicate_take_profit_orders")
    if position and len(stops) > 2:
        repair_reasons.append("duplicate_stop_loss_orders")

    if not position:
        state = "closed_by_price_exit" if filled_children else "closed_or_position_absent"
    elif repair_reasons:
        state = "repair_required"
    elif pending_closes:
        state = "time_exit_close_pending"
    elif time_exit_due and not market_open:
        state = "time_exit_due_waiting_market_open"
    elif time_exit_due and protective_cancel_pending:
        state = "time_exit_protection_cancel_pending"
    elif time_exit_due and active_children:
        state = "time_exit_due_cancel_protection"
    elif time_exit_due:
        state = "time_exit_due_close_ready"
    elif active_children and not persistent_protection:
        state = (
            "persistent_protection_rearm_cancel_pending"
            if protective_cancel_pending
            else "persistent_protection_rearm_cancel_required"
        )
    elif not active_children:
        state = "persistent_protection_rearm_submit_ready"
    else:
        state = "monitoring_price_and_time_exits"

    public = {
        "leg_id": leg.get("leg_id"),
        "symbol": symbol,
        "direction": direction,
        "expected_quantity": expected_quantity,
        "position_open": bool(position),
        "exact_position_match": exact_position_match if position else None,
        "state": state,
        "take_profit_price": leg.get("take_profit_price"),
        "stop_loss_price": leg.get("stop_loss_price"),
        "active_take_profit_count": target_active_count,
        "active_stop_loss_count": stop_active_count,
        "active_protective_exit_count": len(active_children),
        "active_time_in_force_values": active_time_in_force_values,
        "persistent_price_exit_protection": persistent_protection,
        "protective_cancel_pending": protective_cancel_pending,
        "filled_protective_exit_count": len(filled_children),
        "pending_time_exit_close_count": len(pending_closes),
        "opening_order_fingerprint": _hash_identifier(parent_id),
        "persistent_exit_order_fingerprint": _hash_identifier(oco_parent_id),
        "time_exit": schedule,
        "time_exit_due": time_exit_due,
        "market_open": market_open,
        "repair_reasons": sorted(set(repair_reasons)),
        "proof_credit_allowed": False,
    }
    private = {
        "parent": parent,
        "active_children": active_children,
        "position": position,
        "exit_oco_client_order_id": exit_oco_client_order_id,
    }
    return public, private


def _action_prewrite(
    *,
    event_log: EventLog,
    sleeve_id: str,
    leg: dict[str, Any],
    action: str,
    broker_identifier: str | None,
) -> str:
    event = event_log.write(
        "qadam_operator_exploratory_exit_prewrite",
        "qadam_operator_exploratory_exit_manager",
        {
            "schema_version": SCHEMA_VERSION,
            "sleeve_id": sleeve_id,
            "leg_id": leg.get("leg_id"),
            "symbol": leg.get("symbol"),
            "action": action,
            "broker_identifier_hash": _hash_identifier(broker_identifier),
            "paper_only": True,
            "live_capital_enabled": False,
            "new_position_allowed": False,
            "position_increase_allowed": False,
            "proof_credit_allowed": False,
        },
    )
    return str(event.correlation_id)


def _execute_due_actions(
    *,
    client: BrokerClient,
    sleeve_id: str,
    public_legs: list[dict[str, Any]],
    private_legs: dict[str, dict[str, Any]],
    event_log: EventLog,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for leg in public_legs:
        if leg.get("state") not in {
            "persistent_protection_rearm_cancel_required",
            "persistent_protection_rearm_submit_ready",
            "time_exit_due_cancel_protection",
            "time_exit_due_close_ready",
        }:
            continue
        private = private_legs[str(leg.get("leg_id"))]
        if leg["state"] in {
            "persistent_protection_rearm_cancel_required",
            "time_exit_due_cancel_protection",
        }:
            # Alpaca advanced-order groups are OCO: canceling one open child
            # cancels its sibling, avoiding two competing cancel requests.
            for child in private["active_children"][:1]:
                order_id = str(child.get("id") or "")
                if not order_id:
                    continue
                prewrite_id = _action_prewrite(
                    event_log=event_log,
                    sleeve_id=sleeve_id,
                    leg=leg,
                    action="cancel_exact_sleeve_protective_exit",
                    broker_identifier=order_id,
                )
                try:
                    result = client.cancel_order(order_id)
                    succeeded = result.get("requested") is True
                    failure_class = None
                except Exception as exc:  # noqa: BLE001 - sanitized class only
                    succeeded = False
                    failure_class = type(exc).__name__
                actions.append(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "artifact_type": "qadam_operator_exploratory_exit_action",
                        "generated_at": now_iso(),
                        "sleeve_id": sleeve_id,
                        "leg_id": leg.get("leg_id"),
                        "symbol": leg.get("symbol"),
                        "action": "cancel_exact_sleeve_protective_exit",
                        "broker_identifier_hash": _hash_identifier(order_id),
                        "event_log_prewrite_id": prewrite_id,
                        "broker_write_called": True,
                        "broker_write_succeeded": succeeded,
                        "failure_class": failure_class,
                        "paper_only": True,
                        "live_capital_enabled": False,
                        "proof_credit_allowed": False,
                    }
                )
        elif leg["state"] == "persistent_protection_rearm_submit_ready":
            prewrite_id = _action_prewrite(
                event_log=event_log,
                sleeve_id=sleeve_id,
                leg=leg,
                action="submit_exact_closing_only_gtc_oco_protection",
                broker_identifier=None,
            )
            try:
                result = client.submit_oco(
                    symbol=str(leg.get("symbol") or ""),
                    side=_closing_side(str(leg.get("direction") or "")),
                    quantity=float(leg.get("expected_quantity") or 0.0),
                    take_profit_price=float(leg.get("take_profit_price") or 0.0),
                    stop_loss_price=float(leg.get("stop_loss_price") or 0.0),
                    client_order_id=str(private.get("exit_oco_client_order_id") or ""),
                )
                succeeded = result.get("requested") is True
                failure_class = None
                order_hash = result.get("broker_order_id_hash")
                broker_status = result.get("broker_order_status")
            except Exception as exc:  # noqa: BLE001 - sanitized class only
                succeeded = False
                failure_class = type(exc).__name__
                order_hash = None
                broker_status = None
            actions.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "artifact_type": "qadam_operator_exploratory_exit_action",
                    "generated_at": now_iso(),
                    "sleeve_id": sleeve_id,
                    "leg_id": leg.get("leg_id"),
                    "symbol": leg.get("symbol"),
                    "action": "submit_exact_closing_only_gtc_oco_protection",
                    "broker_identifier_hash": order_hash,
                    "broker_order_status": broker_status,
                    "event_log_prewrite_id": prewrite_id,
                    "broker_write_called": True,
                    "broker_write_succeeded": succeeded,
                    "failure_class": failure_class,
                    "paper_only": True,
                    "live_capital_enabled": False,
                    "proof_credit_allowed": False,
                }
            )
        else:
            prewrite_id = _action_prewrite(
                event_log=event_log,
                sleeve_id=sleeve_id,
                leg=leg,
                action="close_exact_matching_sleeve_position_after_time_deadline",
                broker_identifier=None,
            )
            try:
                result = client.close_position(
                    str(leg.get("symbol") or ""), float(leg.get("expected_quantity") or 0.0)
                )
                succeeded = result.get("requested") is True
                failure_class = None
                order_hash = result.get("broker_order_id_hash")
                broker_status = result.get("broker_order_status")
            except Exception as exc:  # noqa: BLE001 - sanitized class only
                succeeded = False
                failure_class = type(exc).__name__
                order_hash = None
                broker_status = None
            actions.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "artifact_type": "qadam_operator_exploratory_exit_action",
                    "generated_at": now_iso(),
                    "sleeve_id": sleeve_id,
                    "leg_id": leg.get("leg_id"),
                    "symbol": leg.get("symbol"),
                    "action": "close_exact_matching_sleeve_position_after_time_deadline",
                    "broker_identifier_hash": order_hash,
                    "broker_order_status": broker_status,
                    "event_log_prewrite_id": prewrite_id,
                    "broker_write_called": True,
                    "broker_write_succeeded": succeeded,
                    "failure_class": failure_class,
                    "paper_only": True,
                    "live_capital_enabled": False,
                    "proof_credit_allowed": False,
                }
            )
    return actions


def _summary_status(
    *,
    blockers: list[str],
    legs: list[dict[str, Any]],
    actions: list[dict[str, Any]],
) -> str:
    if blockers:
        return "blocked"
    if any(leg.get("state") == "repair_required" for leg in legs):
        return "repair_required"
    if actions:
        return "risk_reduction_actions_requested"
    if legs and all(not leg.get("position_open") for leg in legs):
        return "complete_all_legs_closed"
    if any(leg.get("state") == "time_exit_due_waiting_market_open" for leg in legs):
        return "time_exit_due_waiting_market_open"
    if any(str(leg.get("state") or "").startswith("time_exit_due") for leg in legs):
        return "time_exit_due"
    if any(
        str(leg.get("state") or "").startswith("persistent_protection_rearm")
        for leg in legs
    ):
        return "persistent_protection_rearm_in_progress"
    return "monitoring_price_and_time_exits"


def build_operator_exploratory_exit_manager(
    settings: Settings | None = None,
    *,
    execute_due_exits: bool = False,
    broker_client: BrokerClient | None = None,
    current_time: datetime | None = None,
    event_log_path: str | Path | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    runtime = _runtime_dir(settings)
    generated_at = now_iso()
    now = current_time or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)
    sleeve = read_json(runtime / SLEEVE_ARTIFACT)
    submission = read_json(runtime / SUBMISSION_ARTIFACT)
    approval = read_json(runtime / APPROVAL_ARTIFACT)
    endpoint = _endpoint_context(settings)
    blockers = validate_exit_approval(approval, sleeve, submission)
    if settings.mode != "paper":
        blockers.append("mode_not_paper")
    if settings.live_capital_enabled:
        blockers.append("live_capital_enabled")
    if endpoint.get("paper_endpoint_confirmed") is not True:
        blockers.append("paper_endpoint_not_confirmed")
    if endpoint.get("alpaca_api_key_configured") is not True:
        blockers.append("alpaca_paper_key_missing")
    if endpoint.get("alpaca_api_secret_configured") is not True:
        blockers.append("alpaca_paper_secret_missing")
    blockers = sorted(set(blockers))

    legs: list[dict[str, Any]] = []
    private_legs: dict[str, dict[str, Any]] = {}
    actions: list[dict[str, Any]] = []
    broker_snapshot_status = "not_requested_blocked"
    market_open = False
    broker_failure_class: str | None = None
    if not blockers:
        client = broker_client or AlpacaPaperSleeveClient(settings)
        submission_time = _parse_datetime(submission.get("generated_at")) or now
        start_day = (submission_time - timedelta(days=2)).date().isoformat()
        end_day = (submission_time + timedelta(days=45)).date().isoformat()
        after = (submission_time - timedelta(days=1)).isoformat()
        try:
            snapshot = client.snapshot(start=start_day, end=end_day, after=after)
            broker_snapshot_status = "recorded"
            orders = _flatten_orders(
                [record for record in snapshot.get("orders") or [] if isinstance(record, dict)]
            )
            positions = {
                str(record.get("symbol") or "").upper(): record
                for record in snapshot.get("positions") or []
                if isinstance(record, dict)
            }
            calendar = [
                record for record in snapshot.get("calendar") or [] if isinstance(record, dict)
            ]
            market_open = snapshot.get("clock", {}).get("is_open") is True
            for source_leg in sleeve.get("legs") or []:
                public, private = _leg_state(
                    leg=source_leg,
                    orders=orders,
                    positions=positions,
                    calendar=calendar,
                    market_open=market_open,
                    now=now,
                    exit_oco_client_order_id=_exit_oco_client_order_id(
                        str(sleeve.get("sleeve_id") or ""),
                        str(source_leg.get("leg_id") or ""),
                    ),
                )
                legs.append(public)
                private_legs[str(public.get("leg_id"))] = private
            if execute_due_exits:
                event_log = EventLog(
                    Path(event_log_path) if event_log_path else runtime / EVENT_LEDGER,
                    echo=False,
                )
                actions = _execute_due_actions(
                    client=client,
                    sleeve_id=str(sleeve.get("sleeve_id") or ""),
                    public_legs=legs,
                    private_legs=private_legs,
                    event_log=event_log,
                )
        except Exception as exc:  # noqa: BLE001 - never persist provider text or payload
            broker_snapshot_status = "failed_sanitized"
            broker_failure_class = type(exc).__name__
            blockers.append("broker_snapshot_failed")

    blocker_set = sorted(set(blockers))
    status = _summary_status(blockers=blocker_set, legs=legs, actions=actions)
    material = {
        "status": status,
        "sleeve_id": sleeve.get("sleeve_id"),
        "legs": legs,
        "blockers": blocker_set,
        "actions": [
            {
                "leg_id": action.get("leg_id"),
                "action": action.get("action"),
                "broker_write_succeeded": action.get("broker_write_succeeded"),
                "failure_class": action.get("failure_class"),
            }
            for action in actions
        ],
    }
    artifact: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_exploratory_exit_manager",
        "generated_at": generated_at,
        "material_state_fingerprint": _material_hash(material),
        "status": status,
        "sleeve_id": sleeve.get("sleeve_id"),
        "operator_request_id": sleeve.get("request_id"),
        "approval_status": approval.get("status") or "missing",
        "execute_due_exits_requested": execute_due_exits,
        "broker_snapshot_status": broker_snapshot_status,
        "broker_failure_class": broker_failure_class,
        "market_open": market_open,
        "leg_count": len(legs),
        "open_position_count": sum(leg.get("position_open") is True for leg in legs),
        "protected_open_position_count": sum(
            leg.get("state") == "monitoring_price_and_time_exits" for leg in legs
        ),
        "closed_leg_count": sum(leg.get("position_open") is False for leg in legs),
        "time_exit_due_count": sum(leg.get("time_exit_due") is True for leg in legs),
        "repair_required_count": sum(leg.get("state") == "repair_required" for leg in legs),
        "broker_write_called_count": len(actions),
        "broker_write_succeeded_count": sum(
            action.get("broker_write_succeeded") is True for action in actions
        ),
        "protective_cancel_called_count": sum(
            action.get("action") == "cancel_exact_sleeve_protective_exit"
            for action in actions
        ),
        "persistent_protection_submit_called_count": sum(
            action.get("action") == "submit_exact_closing_only_gtc_oco_protection"
            for action in actions
        ),
        "position_close_called_count": sum(
            action.get("action")
            == "close_exact_matching_sleeve_position_after_time_deadline"
            for action in actions
        ),
        "legs": legs,
        "actions": actions,
        "blockers": blocker_set,
        "next_action": (
            "Monitor broker-side stops and targets; close any remaining exact sleeve "
            "position at its fifth-session deadline."
            if status == "monitoring_price_and_time_exits"
            else "No action; all sleeve positions are closed."
            if status == "complete_all_legs_closed"
            else "Resolve the recorded blocker without widening authority."
            if status in {"blocked", "repair_required"}
            else "Continue the guarded exit sequence on the next fresh broker snapshot."
        ),
        "price_exit_priority": "broker_side_take_profit_or_stop_loss_first",
        "time_exit_minutes_before_close": TIME_EXIT_MINUTES_BEFORE_CLOSE,
        "paper_only": True,
        "live_capital_enabled": False,
        "new_position_allowed": False,
        "position_increase_allowed": False,
        "strategy_promotion_allowed": False,
        "proof_credit_allowed": False,
        "paper_proof_ledger_credit_allowed": False,
        "raw_broker_payload_stored": False,
        "secret_value_exposed": False,
        "base_url_exposed": False,
        "authorization_header_exposed": False,
    }
    artifact["validation_errors"] = validate_operator_exploratory_exit_manager(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "invalid"
    return artifact


def validate_operator_exploratory_exit_manager(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if artifact.get("schema_version") != SCHEMA_VERSION:
        errors.append("manager_schema_invalid")
    if artifact.get("paper_only") is not True:
        errors.append("manager_not_paper_only")
    if artifact.get("live_capital_enabled") is not False:
        errors.append("manager_live_capital_not_false")
    for key in (
        "new_position_allowed",
        "position_increase_allowed",
        "strategy_promotion_allowed",
        "proof_credit_allowed",
        "paper_proof_ledger_credit_allowed",
        "raw_broker_payload_stored",
        "secret_value_exposed",
        "base_url_exposed",
        "authorization_header_exposed",
    ):
        if artifact.get(key) is not False:
            errors.append(f"manager_forbidden_state:{key}")
    actions = [record for record in artifact.get("actions") or [] if isinstance(record, dict)]
    if int(artifact.get("broker_write_called_count") or 0) != len(actions):
        errors.append("manager_broker_write_count_mismatch")
    allowed_actions = {
        "cancel_exact_sleeve_protective_exit",
        "submit_exact_closing_only_gtc_oco_protection",
        "close_exact_matching_sleeve_position_after_time_deadline",
    }
    for action in actions:
        if action.get("action") not in allowed_actions:
            errors.append("manager_unauthorized_action")
        if action.get("paper_only") is not True:
            errors.append("manager_action_not_paper_only")
        if action.get("live_capital_enabled") is not False:
            errors.append("manager_action_live_capital_not_false")
        if action.get("proof_credit_allowed") is not False:
            errors.append("manager_action_proof_credit_not_false")
        if not action.get("event_log_prewrite_id"):
            errors.append("manager_action_prewrite_missing")
    if actions and artifact.get("execute_due_exits_requested") is not True:
        errors.append("manager_write_without_explicit_execution_mode")
    if actions and artifact.get("approval_status") != "approved":
        errors.append("manager_write_without_durable_approval")
    text = json.dumps(artifact, sort_keys=True, default=str)
    if PAPER_API_HOST in text or "APCA-API" in text:
        errors.append("manager_endpoint_or_authorization_exposed")
    return sorted(set(errors))


def write_exit_approval(
    approval: dict[str, Any], settings: Settings | None = None
) -> Path:
    path = _runtime_dir(settings) / APPROVAL_ARTIFACT
    write_json_atomic(path, approval)
    return path


def write_operator_exploratory_exit_manager(
    artifact: dict[str, Any], settings: Settings | None = None
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    output = runtime / MANAGER_ARTIFACT
    history = runtime / MANAGER_HISTORY
    action_ledger = runtime / ACTION_LEDGER
    previous = read_json(output)
    write_json_atomic(output, artifact)
    if previous.get("material_state_fingerprint") != artifact.get("material_state_fingerprint"):
        append_jsonl_durable(history, artifact)
    for action in artifact.get("actions") or []:
        if isinstance(action, dict):
            append_jsonl_durable(action_ledger, action)
    return output, history, action_ledger
