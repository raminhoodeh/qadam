"""Incident-only quarantine for pending Alpaca Paper orders.

The normal order lifecycle owns order creation and cancellation. This module is
deliberately narrower: it cancels only open orders created after an explicit
incident cutoff, only on the configured Alpaca Paper endpoint, and records a
sanitized audit trail without broker identifiers or credentials.
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Protocol

from orchestrator.config import Settings
from orchestrator.paperops_alpaca_paper_post import (
    _endpoint_context,
    _headers,
    _paper_api_url,
)
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import append_jsonl_durable


ARTIFACT = "qadam_pending_order_quarantine.json"
HISTORY = "qadam_pending_order_quarantine_history.jsonl"
OPEN_ORDER_STATES = frozenset(
    {"accepted", "new", "pending_new", "partially_filled", "pending_replace"}
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _hash_identifier(value: Any) -> str | None:
    text = str(value or "").strip()
    return sha256(text.encode("utf-8")).hexdigest() if text else None


class PendingOrderClient(Protocol):
    def list_open_orders(self) -> list[dict[str, Any]]: ...

    def cancel_order(self, order_id: str) -> None: ...


class AlpacaPaperPendingOrderClient:
    def __init__(self, settings: Settings, *, timeout_seconds: float = 15.0) -> None:
        self.settings = settings
        self.timeout_seconds = timeout_seconds

    def list_open_orders(self) -> list[dict[str, Any]]:
        import httpx

        with httpx.Client(timeout=self.timeout_seconds, follow_redirects=False) as client:
            response = client.get(
                _paper_api_url(self.settings, "orders"),
                headers=_headers(self.settings),
                params={"status": "open", "limit": 500, "nested": "true"},
            )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("alpaca_open_orders_shape_invalid")
        return [record for record in payload if isinstance(record, dict)]

    def cancel_order(self, order_id: str) -> None:
        import httpx

        with httpx.Client(timeout=self.timeout_seconds, follow_redirects=False) as client:
            response = client.delete(
                _paper_api_url(self.settings, f"orders/{order_id}"),
                headers=_headers(self.settings),
            )
        if response.status_code not in {200, 204, 404, 422}:
            response.raise_for_status()


def _selected_orders(
    orders: list[dict[str, Any]], *, incident_started_at: str
) -> list[dict[str, Any]]:
    cutoff = _parse_timestamp(incident_started_at)
    if cutoff is None:
        raise ValueError("incident_started_at_invalid")
    selected: list[dict[str, Any]] = []
    for order in orders:
        status = str(order.get("status") or "").lower()
        created = _parse_timestamp(order.get("created_at") or order.get("submitted_at"))
        if status not in OPEN_ORDER_STATES or created is None or created < cutoff:
            continue
        if not str(order.get("id") or "").strip():
            continue
        selected.append(order)
    return sorted(
        selected,
        key=lambda record: (
            str(record.get("created_at") or record.get("submitted_at") or ""),
            str(record.get("symbol") or ""),
        ),
    )


def quarantine_pending_paper_orders(
    settings: Settings | None = None,
    *,
    incident_id: str,
    incident_started_at: str,
    execute: bool = False,
    client: PendingOrderClient | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    incident_id = incident_id.strip()
    if not incident_id:
        raise ValueError("incident_id_required")
    endpoint = _endpoint_context(settings)
    boundary_checks = {
        "mode_is_paper": settings.mode == "paper",
        "live_capital_disabled": settings.live_capital_enabled is False,
        "paper_endpoint_confirmed": endpoint.get("paper_endpoint_confirmed") is True,
        "paper_credentials_configured": (
            endpoint.get("alpaca_api_key_configured") is True
            and endpoint.get("alpaca_api_secret_configured") is True
        ),
    }
    if not all(boundary_checks.values()):
        raise PermissionError("paper_order_quarantine_boundary_failed")

    broker = client or AlpacaPaperPendingOrderClient(settings)
    selected = _selected_orders(
        broker.list_open_orders(), incident_started_at=incident_started_at
    )
    actions: list[dict[str, Any]] = []
    for order in selected:
        order_id = str(order["id"])
        state = "planned"
        failure_class: str | None = None
        if execute:
            try:
                broker.cancel_order(order_id)
                state = "cancel_requested"
            except Exception as exc:  # noqa: BLE001 - persist the class only.
                state = "cancel_failed"
                failure_class = type(exc).__name__
        actions.append(
            {
                "broker_order_id_hash": _hash_identifier(order_id),
                "client_order_id_hash": _hash_identifier(order.get("client_order_id")),
                "symbol": str(order.get("symbol") or "").upper(),
                "side": str(order.get("side") or "").lower(),
                "order_type": str(order.get("type") or "").lower(),
                "time_in_force": str(order.get("time_in_force") or "").lower(),
                "created_at": order.get("created_at") or order.get("submitted_at"),
                "state": state,
                "failure_class": failure_class,
            }
        )

    failed = [record for record in actions if record["state"] == "cancel_failed"]
    generated_at = _now()
    artifact = {
        "schema_version": 1,
        "artifact_type": "qadam_pending_order_quarantine",
        "incident_id": incident_id,
        "generated_at": generated_at,
        "incident_started_at": incident_started_at,
        "status": (
            "quarantine_failed"
            if failed
            else "cancel_requests_submitted"
            if execute
            else "dry_run_ready"
        ),
        "execute_requested": execute,
        "selected_open_order_count": len(selected),
        "cancel_requested_count": sum(
            record["state"] == "cancel_requested" for record in actions
        ),
        "cancel_failed_count": len(failed),
        "symbol_counts": {
            symbol: sum(record["symbol"] == symbol for record in actions)
            for symbol in sorted({record["symbol"] for record in actions if record["symbol"]})
        },
        "actions": actions,
        "boundary_checks": boundary_checks,
        "paper_only": True,
        "live_capital_enabled": False,
        "raw_broker_identifier_stored": False,
        "secret_value_exposed": False,
        "reason": "Quarantine pending orders created during the 2026-08-24 verification incident.",
    }
    runtime = Path(settings.runtime_dir).resolve()
    AtomicArtifactStore(runtime).write_json(ARTIFACT, artifact)
    append_jsonl_durable(runtime / HISTORY, artifact)
    return artifact
