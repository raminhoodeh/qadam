"""PaperOps-3 read-only Alpaca paper lifecycle poller.

This stage is the broker readback layer after PaperOps-2. It only considers
orders that PaperOps-2 actually submitted to Alpaca paper, and it performs only
GET requests when the caller explicitly asks for polling. It writes a sanitized
PaperOps lifecycle readback artifact; it does not mutate broker state, place
orders, close positions, or grant Phase 7 proof credit.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.paperops_alpaca_paper_post import (
    PAPEROPS_ALPACA_POST_SCHEMA_VERSION,
    _endpoint_context,
    _headers,
    _orders_url,
    paperops_alpaca_paper_post_submission_ledger_path,
    read_latest_paperops_alpaca_paper_post,
    validate_paperops_alpaca_paper_post,
)
from orchestrator.paperops_paper_lifecycle_polling_enablement import (
    read_latest_paperops_paper_lifecycle_polling_enablement,
    validate_paperops_paper_lifecycle_polling_enablement,
)
from orchestrator.qadam_operator_exploratory_sleeve import (
    CLIENT_ORDER_PREFIX as OPERATOR_SLEEVE_CLIENT_ORDER_PREFIX,
    IDEMPOTENCY_NAMESPACE as OPERATOR_SLEEVE_IDEMPOTENCY_NAMESPACE,
)


PAPEROPS_LIFECYCLE_POLLER_SCHEMA_VERSION = 1
PAPEROPS_LIFECYCLE_POLLER_RUNTIME_ARTIFACT = "paperops_paper_lifecycle_poller.json"
PAPEROPS_LIFECYCLE_POLLER_HISTORY = "paperops_paper_lifecycle_poller_history.jsonl"
PAPEROPS_LIFECYCLE_POLLER_EVENT_LOG = "paperops_paper_lifecycle_poller_events.jsonl"
PAPEROPS_LIFECYCLE_POLLER_EVENT_TYPE = "paperops_paper_lifecycle_poller_recorded"
PAPEROPS_LIFECYCLE_POLLER_COMPONENT = "paperops_paper_lifecycle_poller"

PAPEROPS_LIFECYCLE_AUTHORITY_FALSE_FIELDS = (
    "execution_allowed",
    "paper_order_allowed",
    "broker_write_allowed",
    "broker_post_allowed",
    "alpaca_post_allowed",
    "order_cancel_allowed",
    "position_close_allowed",
    "position_resize_allowed",
    "prediction_market_write_allowed",
    "crypto_perps_write_allowed",
    "live_endpoint_allowed",
    "live_capital_enabled",
    "manual_trade_level_override_allowed",
    "phase7_proof_credit_allowed",
    "secret_value_exposed",
    "raw_broker_payload_stored",
    "raw_broker_payload_exposed",
    "authorization_header_exposed",
    "base_url_exposed",
    "broker_order_identifier_exposed",
)

PAPEROPS_LIFECYCLE_BOUNDARY = (
    "PaperOps-3 is a read-only Alpaca paper lifecycle poller. It may GET "
    "order and position state only for orders that PaperOps-2 successfully "
    "submitted to Alpaca paper, and only when the caller passes the explicit "
    "poll flag. It cannot call broker POST routes, cannot cancel, replace, "
    "close, or resize orders or positions, cannot call live endpoints, cannot "
    "use live capital, cannot expose secrets, raw broker payloads, base URLs, "
    "authorization headers, or raw broker identifiers, and cannot grant Phase "
    "7 proof credit."
)

PROHIBITED_VALUE_PATTERNS = (
    re.compile(r"ghp_[A-Za-z0-9_]{20,}"),
    re.compile(r"vcp_[A-Za-z0-9_]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"sb_secret_[0-9A-Za-z_-]{12,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"pref_agent_[0-9A-Za-z_-]{12,}"),
    re.compile(r"[0-9]{6,}:[A-Za-z0-9_-]{20,}"),
    re.compile(r"(ALPACA_API_KEY|ALPACA_API_SECRET)=[A-Za-z0-9_-]{8,}"),
)

READBACK_READY_STATUSES = frozenset(
    {
        "ready_no_submitted_paper_orders",
        "ready_pending_explicit_poll",
        "paper_lifecycle_poll_recorded",
    }
)

PAPEROPS_LIFECYCLE_ENABLEMENT_READY_STATUSES = frozenset(
    {
        "enabled_pending_submitted_paper_orders",
        "enabled_pending_explicit_poll",
    }
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def paperops_paper_lifecycle_poller_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PAPEROPS_LIFECYCLE_POLLER_RUNTIME_ARTIFACT,
        runtime / PAPEROPS_LIFECYCLE_POLLER_HISTORY,
        runtime / PAPEROPS_LIFECYCLE_POLLER_EVENT_LOG,
    )


def read_latest_paperops_paper_lifecycle_poller(
    settings: Settings | None = None,
) -> dict[str, Any]:
    output_path, _, _ = paperops_paper_lifecycle_poller_paths(settings)
    if not output_path.exists():
        return {}
    return _read_json(output_path)


def _contains_secret_shape(value: object) -> bool:
    text = json.dumps(value, sort_keys=True, default=str)
    return any(pattern.search(text) for pattern in PROHIBITED_VALUE_PATTERNS)


def _fingerprint(payload: dict[str, Any]) -> str:
    return sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _float_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _hash_identifier(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return sha256(text.encode("utf-8")).hexdigest()


def _orders_by_client_order_id_url(settings: Settings) -> str:
    return f"{_orders_url(settings)}:by_client_order_id"


def _positions_url(settings: Settings, symbol: str) -> str:
    orders_url = _orders_url(settings)
    base = orders_url.rsplit("/orders", 1)[0]
    return f"{base}/positions/{symbol.upper()}"


def _submission_ledger(settings: Settings) -> dict[str, Any]:
    return _read_json(paperops_alpaca_paper_post_submission_ledger_path(settings))


def _record_request_preview(record: dict[str, Any]) -> dict[str, Any]:
    request_preview = record.get("request_preview")
    return request_preview if isinstance(request_preview, dict) else {}


def _record_receipt(record: dict[str, Any]) -> dict[str, Any]:
    receipt = record.get("broker_receipt")
    return receipt if isinstance(receipt, dict) else {}


def _record_client_order_id(record: dict[str, Any]) -> str:
    request_preview = _record_request_preview(record)
    receipt = _record_receipt(record)
    return str(
        receipt.get("broker_client_order_id")
        or request_preview.get("client_order_id")
        or record.get("idempotency_key")
        or ""
    ).strip()


def _record_source_idempotency_key(record: dict[str, Any]) -> str:
    request_preview = _record_request_preview(record)
    return str(
        record.get("source_idempotency_key") or request_preview.get("source_idempotency_key") or ""
    ).strip()


def _ledger_confirms_submitted_record(
    record: dict[str, Any],
    *,
    submitted_client_order_ids: set[str],
    submitted_source_idempotency_keys: set[str],
) -> bool:
    client_order_id = _record_client_order_id(record)
    source_key = _record_source_idempotency_key(record)
    phase7_identity = (
        client_order_id.startswith("q7-6-stage-")
        and source_key.startswith("q7-6-stage-")
    )
    operator_sleeve_identity = (
        record.get("idempotency_namespace") == OPERATOR_SLEEVE_IDEMPOTENCY_NAMESPACE
        and client_order_id.startswith(OPERATOR_SLEEVE_CLIENT_ORDER_PREFIX)
        and source_key.startswith(OPERATOR_SLEEVE_CLIENT_ORDER_PREFIX)
    )
    return (
        (phase7_identity or operator_sleeve_identity)
        and client_order_id in submitted_client_order_ids
        and source_key in submitted_source_idempotency_keys
        and record.get("previously_submitted_to_alpaca_paper") is True
    )


def _source_record_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    ledger_confirmed = record.get("ledger_confirmed_submitted_paper_order") is True
    receipt = record.get("broker_receipt")
    receipt_present = isinstance(receipt, dict)
    if not isinstance(receipt, dict):
        receipt = {}
        if not ledger_confirmed:
            errors.append("source_broker_receipt_missing")
    request_preview = record.get("request_preview")
    if not isinstance(request_preview, dict):
        request_preview = {}
        errors.append("source_request_preview_missing")
    client_order_id = _record_client_order_id(record)
    source_idempotency_key = _record_source_idempotency_key(record)
    status = record.get("status")
    if status != "submitted_to_alpaca_paper" and not (
        ledger_confirmed and status == "blocked_duplicate_paper_submit"
    ):
        errors.append("source_status_not_submitted_to_alpaca_paper")
    if record.get("alpaca_paper_post_succeeded") is not True and not ledger_confirmed:
        errors.append("source_alpaca_paper_post_not_successful")
    namespace = record.get("idempotency_namespace")
    phase7_identity = (
        namespace == "phase7_demo_proof"
        and client_order_id.startswith("q7-6-stage-")
        and source_idempotency_key.startswith("q7-6-stage-")
    )
    operator_sleeve_identity = (
        namespace == OPERATOR_SLEEVE_IDEMPOTENCY_NAMESPACE
        and client_order_id.startswith(OPERATOR_SLEEVE_CLIENT_ORDER_PREFIX)
        and source_idempotency_key.startswith(OPERATOR_SLEEVE_CLIENT_ORDER_PREFIX)
        and record.get("evidence_class") == "operator_exploratory_unvalidated"
        and record.get("proof_credit_allowed") is False
    )
    if not (phase7_identity or operator_sleeve_identity):
        errors.append("source_idempotency_namespace_invalid")
    if not (
        client_order_id.startswith("q7-6-stage-")
        or client_order_id.startswith(OPERATOR_SLEEVE_CLIENT_ORDER_PREFIX)
    ):
        errors.append("source_client_order_id_invalid")
    if str(request_preview.get("client_order_id") or client_order_id) != client_order_id:
        errors.append("source_client_order_id_mismatch")
    if not (
        source_idempotency_key.startswith("q7-6-stage-")
        or source_idempotency_key.startswith(OPERATOR_SLEEVE_CLIENT_ORDER_PREFIX)
    ):
        errors.append("source_idempotency_key_invalid")
    if not str(receipt.get("broker_order_id_hash") or "").strip() and not ledger_confirmed:
        errors.append("source_broker_order_hash_missing")
    if not str(request_preview.get("symbol") or "").strip():
        errors.append("source_symbol_missing")
    if request_preview.get("method") != "POST":
        errors.append("source_request_preview_method_not_post")
    if request_preview.get("path") != "/v2/orders":
        errors.append("source_request_preview_path_not_orders")
    for key in (
        "raw_broker_payload_stored",
        "raw_broker_payload_exposed",
        "authorization_header_exposed",
        "base_url_exposed",
        "broker_order_identifier_exposed",
        "secret_value_exposed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "manual_trade_level_override_allowed",
    ):
        if record.get(key) is not False:
            errors.append(f"source_record_forbidden:{key}")
    if receipt_present or not ledger_confirmed:
        for key in (
            "broker_order_identifier_exposed",
            "raw_broker_payload_stored",
            "raw_broker_payload_exposed",
            "authorization_header_exposed",
            "base_url_exposed",
            "secret_value_exposed",
        ):
            if receipt.get(key) is not False:
                errors.append(f"source_receipt_forbidden:{key}")
    for key in (
        "base_url_exposed",
        "authorization_header_included",
        "raw_payload_exposed",
        "broker_identifier_exposed",
        "live_endpoint_allowed",
        "live_capital_enabled",
    ):
        if request_preview.get(key) is not False:
            errors.append(f"source_request_preview_forbidden:{key}")
    return sorted(set(errors))


def _source_record_to_poll_candidate(record: dict[str, Any]) -> dict[str, Any]:
    source_errors = _source_record_errors(record)
    receipt = _record_receipt(record)
    request_preview = _record_request_preview(record)
    client_order_id = _record_client_order_id(record)
    symbol = str(request_preview.get("symbol") or "").upper()
    return {
        "schema_version": PAPEROPS_LIFECYCLE_POLLER_SCHEMA_VERSION,
        "record_type": "paperops_paper_lifecycle_poll_candidate",
        "source_record_origin": record.get("source_record_origin"),
        "ledger_confirmed_submitted_paper_order": (
            record.get("ledger_confirmed_submitted_paper_order") is True
        ),
        "source_submit_record_artifact_id": record.get("source_submit_record_artifact_id"),
        "source_staged_order_artifact_id": record.get("source_staged_order_artifact_id"),
        "source_proof_order_id": record.get("source_proof_order_id"),
        "source_auto_approval_decision_id": record.get("source_auto_approval_decision_id"),
        "source_setup_record_id": record.get("source_setup_record_id"),
        "paperops_handoff_id": record.get("paperops_handoff_id"),
        "router_decision_id": record.get("router_decision_id"),
        "v3_consumption_receipt_id": record.get("v3_consumption_receipt_id"),
        "complete_v3_lineage": deepcopy(record.get("complete_v3_lineage") or {}),
        "accepted_v3_handoff_verified": (record.get("accepted_v3_handoff_verified") is True),
        "source_router_idempotency_key": record.get("source_router_idempotency_key"),
        "source_idempotency_key": record.get("source_idempotency_key"),
        "idempotency_key": record.get("idempotency_key"),
        "idempotency_namespace": record.get("idempotency_namespace"),
        "evidence_class": record.get("evidence_class"),
        "proof_credit_allowed": record.get("proof_credit_allowed"),
        "strategy_admission_allowed": record.get("strategy_admission_allowed"),
        "client_order_id": client_order_id,
        "client_order_id_hash": _hash_identifier(client_order_id),
        "broker_order_id_hash": receipt.get("broker_order_id_hash"),
        "source_broker_order_status": receipt.get("broker_order_status"),
        "symbol": symbol,
        "side": str(request_preview.get("side") or "").lower(),
        "qty": str(request_preview.get("qty") or ""),
        "order_type": str(request_preview.get("type") or "market").lower(),
        "time_in_force": str(request_preview.get("time_in_force") or "day").lower(),
        "poll_method": "GET",
        "poll_path_template": "/v2/orders:by_client_order_id",
        "position_poll_path_template": "/v2/positions/{symbol}",
        "source_record_errors": source_errors,
        "eligible_for_lifecycle_poll": not source_errors,
        "status": "eligible" if not source_errors else "blocked_source_contract",
        "base_url_exposed": False,
        "authorization_header_included": False,
        "authorization_header_exposed": False,
        "raw_broker_payload_stored": False,
        "raw_broker_payload_exposed": False,
        "broker_order_identifier_exposed": False,
        "secret_value_exposed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
    }


def _source_poll_records(
    source: dict[str, Any],
    *,
    settings: Settings,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    ledger = _submission_ledger(settings)
    submitted_client_order_ids = set(ledger.get("submitted_client_order_ids", []) or [])
    submitted_source_idempotency_keys = set(
        ledger.get("submitted_source_idempotency_keys", []) or []
    )
    records: list[dict[str, Any]] = []
    seen_client_order_ids: set[str] = set()
    selected_records = [
        record
        for record in source.get("selected_post_records", []) or []
        if isinstance(record, dict)
    ]
    for record in selected_records:
        enriched = deepcopy(record)
        enriched["source_record_origin"] = "paperops_2_selected_post_records"
        client_order_id = _record_client_order_id(enriched)
        if client_order_id and client_order_id in seen_client_order_ids:
            continue
        if client_order_id:
            seen_client_order_ids.add(client_order_id)
        records.append(enriched)
    recovered_count = 0
    for record in source.get("post_candidates", []) or []:
        if not isinstance(record, dict):
            continue
        if not _ledger_confirms_submitted_record(
            record,
            submitted_client_order_ids=submitted_client_order_ids,
            submitted_source_idempotency_keys=submitted_source_idempotency_keys,
        ):
            continue
        client_order_id = _record_client_order_id(record)
        if not client_order_id or client_order_id in seen_client_order_ids:
            continue
        seen_client_order_ids.add(client_order_id)
        enriched = deepcopy(record)
        enriched["source_record_origin"] = "paperops_2_submission_ledger_recovery"
        enriched["ledger_confirmed_submitted_paper_order"] = True
        records.append(enriched)
        recovered_count += 1
    durable_recovered_count = 0
    for record in ledger.get("submission_records", []) or []:
        if not isinstance(record, dict):
            continue
        client_order_id = _record_client_order_id(record)
        if not client_order_id or client_order_id in seen_client_order_ids:
            continue
        if not _ledger_confirms_submitted_record(
            record,
            submitted_client_order_ids=submitted_client_order_ids,
            submitted_source_idempotency_keys=submitted_source_idempotency_keys,
        ):
            continue
        seen_client_order_ids.add(client_order_id)
        enriched = deepcopy(record)
        enriched["source_record_origin"] = "paperops_2_durable_submission_identity"
        enriched["ledger_confirmed_submitted_paper_order"] = True
        records.append(enriched)
        durable_recovered_count += 1
    return records, {
        "source_selected_post_record_count": len(selected_records),
        "source_submission_ledger_client_order_id_count": len(submitted_client_order_ids),
        "source_submission_ledger_source_key_count": len(submitted_source_idempotency_keys),
        "source_submission_ledger_recovered_record_count": recovered_count,
        "source_durable_submission_identity_recovered_count": durable_recovered_count,
    }


def _source_poll_candidates(
    source: dict[str, Any],
    *,
    settings: Settings,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    records, stats = _source_poll_records(source, settings=settings)
    candidates = [_source_record_to_poll_candidate(record) for record in records]
    eligible = [candidate for candidate in candidates if candidate["eligible_for_lifecycle_poll"]]
    return candidates, eligible, stats


def _lifecycle_polling_enablement_ready(enablement: dict[str, Any]) -> bool:
    return (
        enablement.get("status") in PAPEROPS_LIFECYCLE_ENABLEMENT_READY_STATUSES
        and enablement.get("active_lifecycle_polling_enabled") is True
        and enablement.get("paper_lifecycle_polling_effective") is True
        and enablement.get("paper_endpoint_confirmed") is True
        and enablement.get("paperops_2_source_valid") is True
        and (
            enablement.get("paperops_2_paper_post_path_available") is True
            or enablement.get("operator_sleeve_read_only_polling_authorized") is True
        )
        and enablement.get("live_capital_enabled") is False
        and enablement.get("broker_post_allowed") is False
        and enablement.get("live_endpoint_allowed") is False
        and enablement.get("phase7_proof_credit_allowed") is False
        and _int(enablement.get("broker_get_called_count")) == 0
        and _int(enablement.get("live_endpoint_called_count")) == 0
        and _int(enablement.get("unsafe_write_counter_total")) == 0
        and not validate_paperops_paper_lifecycle_polling_enablement(enablement)
    )


def _sanitize_order_response(payload: dict[str, Any], *, polled_at: str) -> dict[str, Any]:
    broker_order_hash = _hash_identifier(payload.get("id"))
    status = str(payload.get("status") or "unknown")
    return {
        "record_type": "alpaca_paper_order_readback",
        "polled_at": polled_at,
        "broker_order_status": status,
        "broker_order_id_hash": broker_order_hash,
        "broker_client_order_id": payload.get("client_order_id"),
        "symbol": str(payload.get("symbol") or "").upper(),
        "side": str(payload.get("side") or "").lower(),
        "qty": _float_text(payload.get("qty")),
        "filled_qty": _float_text(payload.get("filled_qty")),
        "filled_avg_price": _float_text(payload.get("filled_avg_price")),
        "order_type": payload.get("type"),
        "time_in_force": payload.get("time_in_force"),
        "submitted_at": payload.get("submitted_at"),
        "filled_at": payload.get("filled_at"),
        "canceled_at": payload.get("canceled_at"),
        "expired_at": payload.get("expired_at"),
        "raw_broker_payload_stored": False,
        "raw_broker_payload_exposed": False,
        "broker_order_identifier_exposed": False,
        "authorization_header_exposed": False,
        "base_url_exposed": False,
        "secret_value_exposed": False,
    }


def _sanitize_position_response(payload: dict[str, Any], *, polled_at: str) -> dict[str, Any]:
    return {
        "record_type": "alpaca_paper_position_readback",
        "polled_at": polled_at,
        "position_asset_id_hash": _hash_identifier(payload.get("asset_id")),
        "symbol": str(payload.get("symbol") or "").upper(),
        "qty": _float_text(payload.get("qty")),
        "side": str(payload.get("side") or "long").lower(),
        "market_value": _float_text(payload.get("market_value")),
        "avg_entry_price": _float_text(payload.get("avg_entry_price")),
        "current_price": _float_text(payload.get("current_price")),
        "unrealized_pl": _float_text(payload.get("unrealized_pl")),
        "raw_broker_payload_stored": False,
        "raw_broker_payload_exposed": False,
        "broker_order_identifier_exposed": False,
        "authorization_header_exposed": False,
        "base_url_exposed": False,
        "secret_value_exposed": False,
    }


def _lifecycle_state_from_readback(
    order_readback: dict[str, Any],
    position_readback: dict[str, Any] | None,
) -> str:
    status = str(order_readback.get("broker_order_status") or "").lower()
    position_qty = _float_text((position_readback or {}).get("qty"))
    if status in {"new", "accepted", "pending_new", "partially_filled", "pending_replace"}:
        return "submitted_order"
    if status == "filled" and position_qty not in {None, "0", "0.0"}:
        return "open_position"
    if status in {"canceled", "expired", "rejected"}:
        return "terminal_order_no_proof"
    if status == "filled":
        return "filled_without_open_position_echo"
    return "broker_state_unknown"


def _poll_candidate(
    *,
    settings: Settings,
    candidate: dict[str, Any],
    timeout_seconds: float = 12.0,
) -> dict[str, Any]:
    polled_at = _now()
    try:
        import httpx
    except ImportError:
        return {
            "candidate": candidate,
            "order_get_attempted": False,
            "order_get_succeeded": False,
            "position_get_attempted": False,
            "position_get_succeeded": False,
            "sanitized_http_status": None,
            "failure_class": "missing_httpx",
            "failure_message_persisted": False,
            "order_readback": None,
            "position_readback": None,
        }

    try:
        with httpx.Client(timeout=timeout_seconds, follow_redirects=False) as client:
            response = client.get(
                _orders_by_client_order_id_url(settings),
                headers=_headers(settings),
                params={"client_order_id": candidate["client_order_id"]},
            )
            order_status_code = response.status_code
            if order_status_code < 200 or order_status_code >= 300:
                return {
                    "candidate": candidate,
                    "order_get_attempted": True,
                    "order_get_succeeded": False,
                    "position_get_attempted": False,
                    "position_get_succeeded": False,
                    "sanitized_http_status": order_status_code,
                    "failure_class": f"http_{order_status_code}",
                    "failure_message_persisted": False,
                    "order_readback": None,
                    "position_readback": None,
                }
            order_payload = response.json()
            if not isinstance(order_payload, dict):
                order_payload = {}
            order_readback = _sanitize_order_response(order_payload, polled_at=polled_at)
            position_readback: dict[str, Any] | None = None
            position_attempted = False
            position_succeeded = False
            if str(order_readback.get("broker_order_status") or "").lower() in {
                "filled",
                "partially_filled",
            } and candidate.get("symbol"):
                position_attempted = True
                position_response = client.get(
                    _positions_url(settings, str(candidate["symbol"])),
                    headers=_headers(settings),
                )
                if 200 <= position_response.status_code < 300:
                    position_payload = position_response.json()
                    if not isinstance(position_payload, dict):
                        position_payload = {}
                    position_readback = _sanitize_position_response(
                        position_payload,
                        polled_at=polled_at,
                    )
                    position_succeeded = True
            return {
                "candidate": candidate,
                "order_get_attempted": True,
                "order_get_succeeded": True,
                "position_get_attempted": position_attempted,
                "position_get_succeeded": position_succeeded,
                "sanitized_http_status": order_status_code,
                "failure_class": None,
                "failure_message_persisted": False,
                "order_readback": order_readback,
                "position_readback": position_readback,
            }
    except Exception as exc:  # noqa: BLE001 - persist sanitized class only.
        return {
            "candidate": candidate,
            "order_get_attempted": True,
            "order_get_succeeded": False,
            "position_get_attempted": False,
            "position_get_succeeded": False,
            "sanitized_http_status": None,
            "failure_class": type(exc).__name__,
            "failure_message_persisted": False,
            "order_readback": None,
            "position_readback": None,
        }


def _lifecycle_mirror_record(result: dict[str, Any]) -> dict[str, Any] | None:
    order_readback = result.get("order_readback")
    if not isinstance(order_readback, dict):
        return None
    candidate = result.get("candidate")
    if not isinstance(candidate, dict):
        candidate = {}
    position_readback = result.get("position_readback")
    if not isinstance(position_readback, dict):
        position_readback = None
    lifecycle_state = _lifecycle_state_from_readback(order_readback, position_readback)
    return {
        "record_type": "paperops_q7_lifecycle_readback_record",
        "lifecycle_state": lifecycle_state,
        "source_submit_record_artifact_id": candidate.get("source_submit_record_artifact_id"),
        "source_staged_order_artifact_id": candidate.get("source_staged_order_artifact_id"),
        "source_proof_order_id": candidate.get("source_proof_order_id"),
        "source_auto_approval_decision_id": candidate.get("source_auto_approval_decision_id"),
        "source_setup_record_id": candidate.get("source_setup_record_id"),
        "paperops_handoff_id": candidate.get("paperops_handoff_id"),
        "router_decision_id": candidate.get("router_decision_id"),
        "v3_consumption_receipt_id": candidate.get("v3_consumption_receipt_id"),
        "complete_v3_lineage": deepcopy(candidate.get("complete_v3_lineage") or {}),
        "accepted_v3_handoff_verified": (candidate.get("accepted_v3_handoff_verified") is True),
        "source_router_idempotency_key": candidate.get("source_router_idempotency_key"),
        "source_idempotency_key": candidate.get("source_idempotency_key"),
        "idempotency_key": candidate.get("idempotency_key"),
        "client_order_id_hash": candidate.get("client_order_id_hash"),
        "broker_order_id_hash": order_readback.get("broker_order_id_hash"),
        "broker_order_status": order_readback.get("broker_order_status"),
        "submitted_at": order_readback.get("submitted_at"),
        "filled_at": order_readback.get("filled_at"),
        "canceled_at": order_readback.get("canceled_at"),
        "expired_at": order_readback.get("expired_at"),
        "filled_avg_price": order_readback.get("filled_avg_price"),
        "symbol": order_readback.get("symbol") or candidate.get("symbol"),
        "filled_qty": order_readback.get("filled_qty"),
        "position_echo_present": position_readback is not None,
        "counts_as_phase7_proof_credit": False,
        "q7_lifecycle_mutation_performed": False,
        "postmortem_due_marker_created": False,
        "raw_broker_payload_exposed": False,
        "broker_order_identifier_exposed": False,
    }


def _unique_open_position_count(lifecycle_records: list[dict[str, Any]]) -> int:
    """Count current broker positions, not the historical fills behind them."""
    return len(
        {
            str(record.get("symbol") or "").upper()
            for record in lifecycle_records
            if record.get("lifecycle_state") == "open_position" and record.get("symbol")
        }
    )


def _status(
    *,
    settings: Settings,
    endpoint: dict[str, Any],
    source_present: bool,
    source_valid: bool,
    submitted_count: int,
    poll_requested: bool,
    poll_called_count: int,
    failed_count: int,
) -> str:
    if settings.mode != "paper":
        return "blocked_not_paper_mode"
    if settings.live_capital_enabled:
        return "blocked_live_capital_enabled"
    if endpoint["paper_endpoint_confirmed"] is not True:
        return "blocked_non_paper_endpoint"
    if not endpoint["alpaca_api_key_configured"] or not endpoint["alpaca_api_secret_configured"]:
        return "blocked_missing_alpaca_paper_credentials"
    if not source_present:
        return "blocked_missing_paperops_alpaca_post_source"
    if not source_valid:
        return "blocked_invalid_paperops_alpaca_post_source"
    if submitted_count < 1:
        return "ready_no_submitted_paper_orders"
    if not poll_requested:
        return "ready_pending_explicit_poll"
    if poll_called_count and failed_count:
        return "paper_lifecycle_poll_failed_sanitized"
    if poll_called_count:
        return "paper_lifecycle_poll_recorded"
    return "ready_pending_explicit_poll"


def build_paperops_paper_lifecycle_poller(
    settings: Settings | None = None,
    *,
    poll_paper_orders: bool = False,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    endpoint = _endpoint_context(settings)
    source = read_latest_paperops_alpaca_paper_post(settings)
    source_present = bool(source)
    source_validation_errors = validate_paperops_alpaca_paper_post(source) if source_present else []
    source_valid = source_present and not source_validation_errors
    all_candidates, eligible_candidates, source_poll_stats = _source_poll_candidates(
        source,
        settings=settings,
    )
    lifecycle_polling_enablement = read_latest_paperops_paper_lifecycle_polling_enablement(settings)
    lifecycle_polling_enablement_validation_errors = (
        validate_paperops_paper_lifecycle_polling_enablement(lifecycle_polling_enablement)
        if lifecycle_polling_enablement
        else ["paperops_lifecycle_polling_enablement_missing"]
    )
    lifecycle_polling_runtime_enabled = _lifecycle_polling_enablement_ready(
        lifecycle_polling_enablement
    )
    poll_preconditions = {
        "mode_is_paper": settings.mode == "paper",
        "live_capital_disabled": settings.live_capital_enabled is False,
        "alpaca_endpoint_classified_paper": endpoint["paper_endpoint_confirmed"] is True,
        "alpaca_paper_credentials_configured": endpoint["alpaca_api_key_configured"] is True
        and endpoint["alpaca_api_secret_configured"] is True,
        "paperops_2_source_present": source_present,
        "paperops_2_source_valid": source_valid,
        "pt6_active_lifecycle_polling_enabled": (
            lifecycle_polling_runtime_enabled if eligible_candidates else True
        ),
        "submitted_paper_order_present": bool(eligible_candidates),
    }
    poll_path_available = all(poll_preconditions.values())
    poll_results: list[dict[str, Any]] = []
    if poll_paper_orders and poll_path_available:
        poll_results = [
            _poll_candidate(settings=settings, candidate=candidate)
            for candidate in eligible_candidates
        ]
    lifecycle_records = [
        record
        for record in (_lifecycle_mirror_record(result) for result in poll_results)
        if record is not None
    ]
    order_poll_called_count = sum(
        1 for result in poll_results if result.get("order_get_attempted") is True
    )
    order_poll_succeeded_count = sum(
        1 for result in poll_results if result.get("order_get_succeeded") is True
    )
    position_poll_called_count = sum(
        1 for result in poll_results if result.get("position_get_attempted") is True
    )
    position_poll_succeeded_count = sum(
        1 for result in poll_results if result.get("position_get_succeeded") is True
    )
    failed_count = sum(
        1
        for result in poll_results
        if result.get("order_get_attempted") is True
        and result.get("order_get_succeeded") is not True
    )
    lifecycle_state_counts: dict[str, int] = {}
    for record in lifecycle_records:
        state = str(record.get("lifecycle_state") or "unknown")
        lifecycle_state_counts[state] = lifecycle_state_counts.get(state, 0) + 1
    status = _status(
        settings=settings,
        endpoint=endpoint,
        source_present=source_present,
        source_valid=source_valid,
        submitted_count=len(eligible_candidates),
        poll_requested=poll_paper_orders,
        poll_called_count=order_poll_called_count,
        failed_count=failed_count,
    )
    if eligible_candidates and not lifecycle_polling_runtime_enabled:
        status = "blocked_lifecycle_polling_not_enabled"
    artifact = {
        "schema_version": PAPEROPS_LIFECYCLE_POLLER_SCHEMA_VERSION,
        "artifact_type": "paperops_paper_lifecycle_poller",
        "artifact_id": "paperops:paper-lifecycle-poller:latest",
        "phase": "PaperOps",
        "stage": "PaperOps-3",
        "status": status,
        "generated_at": generated_at,
        "public_safe": True,
        "recorded": False,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_event_count": 0,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "runtime_artifact_path": None,
        "history_log_path": None,
        "mode": settings.mode,
        "paper_operational_enabled": settings.paper_operational_enabled,
        "alpaca_paper_submit_enabled": settings.alpaca_paper_submit_enabled,
        "live_capital_enabled": settings.live_capital_enabled,
        "poll_paper_orders_requested": poll_paper_orders,
        "explicit_poll_flag_required": True,
        "active_lifecycle_polling_enabled": lifecycle_polling_runtime_enabled,
        "lifecycle_polling_enablement_status": lifecycle_polling_enablement.get(
            "status",
            "missing",
        ),
        "lifecycle_polling_enablement_artifact_id": lifecycle_polling_enablement.get("artifact_id"),
        "lifecycle_polling_enablement_validation_error_count": len(
            lifecycle_polling_enablement_validation_errors
        ),
        "lifecycle_polling_enablement_validation_errors": (
            lifecycle_polling_enablement_validation_errors[:12]
        ),
        "paper_poll_path_available": poll_path_available,
        "poll_preconditions": poll_preconditions,
        "endpoint_classification": endpoint["endpoint_classification"],
        "paper_endpoint_confirmed": endpoint["paper_endpoint_confirmed"],
        "alpaca_paper_flag": endpoint["alpaca_paper_flag"],
        "alpaca_api_key_configured": endpoint["alpaca_api_key_configured"],
        "alpaca_api_secret_configured": endpoint["alpaca_api_secret_configured"],
        "source_paperops_2_schema_version": source.get("schema_version"),
        "source_paperops_2_artifact_present": source_present,
        "source_paperops_2_artifact_id": source.get("artifact_id"),
        "source_paperops_2_status": source.get("status", "missing"),
        "source_paperops_2_stage": source.get("stage"),
        "source_paperops_2_validation_error_count": len(source_validation_errors),
        "source_paperops_2_validation_errors": source_validation_errors[:12],
        "source_selected_post_record_count": source_poll_stats["source_selected_post_record_count"]
        if source_present
        else 0,
        "source_submission_ledger_client_order_id_count": source_poll_stats[
            "source_submission_ledger_client_order_id_count"
        ]
        if source_present
        else 0,
        "source_submission_ledger_source_key_count": source_poll_stats[
            "source_submission_ledger_source_key_count"
        ]
        if source_present
        else 0,
        "source_submission_ledger_recovered_record_count": source_poll_stats[
            "source_submission_ledger_recovered_record_count"
        ]
        if source_present
        else 0,
        "source_durable_submission_identity_recovered_count": source_poll_stats[
            "source_durable_submission_identity_recovered_count"
        ]
        if source_present
        else 0,
        "source_submitted_paper_order_count": len(eligible_candidates),
        "poll_candidate_count": len(eligible_candidates),
        "blocked_source_record_count": len(all_candidates) - len(eligible_candidates),
        "poll_candidate_records": all_candidates,
        "poll_result_records": [
            {
                "candidate": result.get("candidate"),
                "order_get_attempted": result.get("order_get_attempted"),
                "order_get_succeeded": result.get("order_get_succeeded"),
                "position_get_attempted": result.get("position_get_attempted"),
                "position_get_succeeded": result.get("position_get_succeeded"),
                "sanitized_http_status": result.get("sanitized_http_status"),
                "failure_class": result.get("failure_class"),
                "failure_message_persisted": result.get("failure_message_persisted"),
                "order_readback": result.get("order_readback"),
                "position_readback": result.get("position_readback"),
            }
            for result in poll_results
        ],
        "lifecycle_mirror_records": lifecycle_records,
        "paper_order_poll_called_count": order_poll_called_count,
        "paper_order_poll_succeeded_count": order_poll_succeeded_count,
        "paper_order_poll_failed_count": failed_count,
        "paper_position_poll_called_count": position_poll_called_count,
        "paper_position_poll_succeeded_count": position_poll_succeeded_count,
        "broker_get_called_count": order_poll_called_count + position_poll_called_count,
        "alpaca_paper_get_called_count": order_poll_called_count + position_poll_called_count,
        "broker_post_called_count": 0,
        "alpaca_post_called_count": 0,
        "order_cancel_called_count": 0,
        "position_close_called_count": 0,
        "position_resize_called_count": 0,
        "live_endpoint_called_count": 0,
        "live_capital_enabled_count": 0,
        "manual_trade_level_override_count": 0,
        "prediction_market_write_allowed_count": 0,
        "crypto_perps_write_allowed_count": 0,
        "phase7_proof_credit_allowed_count": 0,
        "broker_order_identifier_exposed_count": 0,
        "secret_value_exposed_count": 0,
        "raw_broker_payload_exposed_count": 0,
        "raw_broker_payload_stored_count": 0,
        "authorization_header_exposed_count": 0,
        "base_url_exposed_count": 0,
        "mirrored_submitted_order_count": lifecycle_state_counts.get("submitted_order", 0),
        # Several historical fills can resolve to the same current position.
        # Count unique live symbols rather than filled order records.
        "open_position_count": _unique_open_position_count(lifecycle_records),
        "closed_trade_count": lifecycle_state_counts.get("closed_trade", 0),
        "fill_event_count": sum(
            1
            for record in lifecycle_records
            if str(record.get("broker_order_status") or "").lower() == "filled"
        ),
        "postmortem_due_marker_created_count": 0,
        "q7_lifecycle_mutation_performed": False,
        "q7_lifecycle_target_artifact": "phase7_proof_lifecycle_monitor",
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "broker_post_allowed": False,
        "alpaca_post_allowed": False,
        "order_cancel_allowed": False,
        "position_close_allowed": False,
        "position_resize_allowed": False,
        "prediction_market_write_allowed": False,
        "crypto_perps_write_allowed": False,
        "live_endpoint_allowed": False,
        "manual_trade_level_override_allowed": False,
        "phase7_proof_credit_allowed": False,
        "secret_value_exposed": False,
        "raw_broker_payload_stored": False,
        "raw_broker_payload_exposed": False,
        "authorization_header_exposed": False,
        "base_url_exposed": False,
        "broker_order_identifier_exposed": False,
        "raw_broker_response_persisted": False,
        "broker_failure_message_persisted": False,
        "recommended_next_stage": (
            "PaperOps-4 paper exit path"
            if status in READBACK_READY_STATUSES
            else "Restore PaperOps-3 read-only lifecycle poller safety"
        ),
        "boundary": PAPEROPS_LIFECYCLE_BOUNDARY,
    }
    artifact["validation_errors"] = validate_paperops_paper_lifecycle_poller(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "invalid"
    return artifact


def _candidate_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("eligible_for_lifecycle_poll") is True:
        namespace = record.get("idempotency_namespace")
        phase7_identity = (
            namespace == "phase7_demo_proof"
            and str(record.get("client_order_id") or "").startswith("q7-6-stage-")
        )
        operator_sleeve_identity = (
            namespace == OPERATOR_SLEEVE_IDEMPOTENCY_NAMESPACE
            and str(record.get("client_order_id") or "").startswith(
                OPERATOR_SLEEVE_CLIENT_ORDER_PREFIX
            )
            and record.get("evidence_class") == "operator_exploratory_unvalidated"
            and record.get("proof_credit_allowed") is False
        )
        if not (phase7_identity or operator_sleeve_identity):
            errors.append("paperops_lifecycle_candidate_namespace_invalid")
        if not (phase7_identity or operator_sleeve_identity):
            errors.append("paperops_lifecycle_candidate_client_id_invalid")
        if (
            not str(record.get("broker_order_id_hash") or "").strip()
            and record.get("ledger_confirmed_submitted_paper_order") is not True
        ):
            errors.append("paperops_lifecycle_candidate_broker_hash_missing")
        # A successful submission can disappear from the latest PaperOps-2
        # projection after its candidate is consumed. The append-only ledger is
        # then the durable source of truth for both canonical and exploratory
        # paper orders, provided the identity checks above still pass.
        valid_ledger_origins = {
            "paperops_2_submission_ledger_recovery",
            "paperops_2_durable_submission_identity",
        }
        if (
            record.get("ledger_confirmed_submitted_paper_order") is True
            and record.get("source_record_origin") not in valid_ledger_origins
        ):
            errors.append("paperops_lifecycle_candidate_ledger_origin_invalid")
    else:
        if record.get("status") != "blocked_source_contract":
            errors.append("paperops_lifecycle_blocked_candidate_status_invalid")
        if not isinstance(record.get("source_record_errors"), list):
            errors.append("paperops_lifecycle_blocked_candidate_errors_missing")
    for key in (
        "base_url_exposed",
        "authorization_header_included",
        "authorization_header_exposed",
        "raw_broker_payload_stored",
        "raw_broker_payload_exposed",
        "broker_order_identifier_exposed",
        "secret_value_exposed",
        "live_endpoint_allowed",
        "live_capital_enabled",
    ):
        if record.get(key) is not False:
            errors.append(f"paperops_lifecycle_candidate_forbidden:{key}")
    return errors


def _result_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("failure_message_persisted") is not False:
        errors.append("paperops_lifecycle_failure_message_persisted")
    for section_key in ("order_readback", "position_readback"):
        section = record.get(section_key)
        if not isinstance(section, dict):
            continue
        for key in (
            "raw_broker_payload_stored",
            "raw_broker_payload_exposed",
            "broker_order_identifier_exposed",
            "authorization_header_exposed",
            "base_url_exposed",
            "secret_value_exposed",
        ):
            if section.get(key) is not False:
                errors.append(f"paperops_lifecycle_result_forbidden:{section_key}.{key}")
    return errors


def validate_paperops_paper_lifecycle_poller(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "alpaca_api_key_configured",
        "alpaca_api_secret_configured",
        "artifact_type",
        "active_lifecycle_polling_enabled",
        "base_url_exposed",
        "boundary",
        "broker_get_called_count",
        "broker_order_identifier_exposed",
        "broker_post_called_count",
        "closed_trade_count",
        "crypto_perps_write_allowed",
        "endpoint_classification",
        "event_log_required",
        "event_log_written",
        "explicit_poll_flag_required",
        "lifecycle_polling_enablement_status",
        "lifecycle_polling_enablement_validation_error_count",
        "live_capital_enabled",
        "live_endpoint_allowed",
        "mode",
        "open_position_count",
        "paper_endpoint_confirmed",
        "paper_order_poll_called_count",
        "paper_poll_path_available",
        "phase",
        "phase7_proof_credit_allowed",
        "poll_candidate_records",
        "poll_paper_orders_requested",
        "poll_result_records",
        "prediction_market_write_allowed",
        "public_safe",
        "q7_lifecycle_mutation_performed",
        "raw_broker_payload_exposed",
        "raw_broker_payload_stored",
        "recorded",
        "schema_version",
        "secret_value_exposed",
        "source_paperops_2_artifact_present",
        "source_paperops_2_status",
        "source_submitted_paper_order_count",
        "stage",
        "status",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("paperops_lifecycle_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PAPEROPS_LIFECYCLE_POLLER_SCHEMA_VERSION:
        errors.append("paperops_lifecycle_schema_version_mismatch")
    if artifact.get("artifact_type") != "paperops_paper_lifecycle_poller":
        errors.append("paperops_lifecycle_artifact_type_mismatch")
    if artifact.get("phase") != "PaperOps" or artifact.get("stage") != "PaperOps-3":
        errors.append("paperops_lifecycle_phase_stage_mismatch")
    if artifact.get("mode") != "paper":
        errors.append("paperops_lifecycle_mode_not_paper")
    if artifact.get("public_safe") is not True:
        errors.append("paperops_lifecycle_not_public_safe")
    for key in PAPEROPS_LIFECYCLE_AUTHORITY_FALSE_FIELDS:
        if artifact.get(key) is not False:
            errors.append(f"paperops_lifecycle_forbidden:{key}")
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "order_cancel_called_count",
        "position_close_called_count",
        "position_resize_called_count",
        "live_endpoint_called_count",
        "live_capital_enabled_count",
        "manual_trade_level_override_count",
        "prediction_market_write_allowed_count",
        "crypto_perps_write_allowed_count",
        "phase7_proof_credit_allowed_count",
        "broker_order_identifier_exposed_count",
        "secret_value_exposed_count",
        "raw_broker_payload_exposed_count",
        "raw_broker_payload_stored_count",
        "authorization_header_exposed_count",
        "base_url_exposed_count",
    ):
        if _int(artifact.get(key)) != 0:
            errors.append(f"paperops_lifecycle_unsafe_counter_nonzero:{key}")
    if artifact.get("explicit_poll_flag_required") is not True:
        errors.append("paperops_lifecycle_explicit_poll_flag_not_required")
    if artifact.get("q7_lifecycle_mutation_performed") is not False:
        errors.append("paperops_lifecycle_mutated_q7_directly")
    if _int(artifact.get("paper_order_poll_called_count")):
        if artifact.get("poll_paper_orders_requested") is not True:
            errors.append("paperops_lifecycle_poll_called_without_explicit_flag")
        if _int(artifact.get("source_submitted_paper_order_count")) < 1:
            errors.append("paperops_lifecycle_poll_called_without_submitted_source_order")
        if artifact.get("paper_endpoint_confirmed") is not True:
            errors.append("paperops_lifecycle_poll_called_without_paper_endpoint")
        if artifact.get("source_paperops_2_artifact_present") is not True:
            errors.append("paperops_lifecycle_poll_called_without_paperops_2_source")
        if artifact.get("source_paperops_2_validation_error_count") not in {0, None}:
            errors.append("paperops_lifecycle_poll_called_with_invalid_source")
        if artifact.get("active_lifecycle_polling_enabled") is not True:
            errors.append("paperops_lifecycle_poll_called_without_pt6_enablement")
    if (
        artifact.get("paper_endpoint_confirmed") is not True
        and artifact.get("paper_poll_path_available") is True
    ):
        errors.append("paperops_lifecycle_path_available_without_paper_endpoint")
    if artifact.get("status") == "ready_no_submitted_paper_orders" and _int(
        artifact.get("source_submitted_paper_order_count")
    ):
        errors.append("paperops_lifecycle_no_submitted_status_with_sources")
    if artifact.get("status") == "ready_pending_explicit_poll" and (
        artifact.get("poll_paper_orders_requested") is True
        or _int(artifact.get("source_submitted_paper_order_count")) < 1
    ):
        errors.append("paperops_lifecycle_pending_explicit_poll_state_invalid")
    if (
        _int(artifact.get("source_submitted_paper_order_count")) > 0
        and artifact.get("active_lifecycle_polling_enabled") is not True
        and artifact.get("status") != "blocked_lifecycle_polling_not_enabled"
    ):
        errors.append("paperops_lifecycle_submitted_source_without_pt6_enablement")
    if _int(artifact.get("paper_order_poll_succeeded_count")) > _int(
        artifact.get("paper_order_poll_called_count")
    ):
        errors.append("paperops_lifecycle_success_gt_called")
    if _int(artifact.get("paper_position_poll_succeeded_count")) > _int(
        artifact.get("paper_position_poll_called_count")
    ):
        errors.append("paperops_lifecycle_position_success_gt_called")
    candidates = artifact.get("poll_candidate_records", [])
    if not isinstance(candidates, list):
        errors.append("paperops_lifecycle_candidates_not_list")
        candidates = []
    results = artifact.get("poll_result_records", [])
    if not isinstance(results, list):
        errors.append("paperops_lifecycle_results_not_list")
        results = []
    eligible_candidates = [
        record
        for record in candidates
        if isinstance(record, dict) and record.get("eligible_for_lifecycle_poll") is True
    ]
    if _int(artifact.get("source_submitted_paper_order_count")) != len(eligible_candidates):
        errors.append("paperops_lifecycle_source_submitted_count_mismatch")
    if _int(artifact.get("poll_candidate_count")) != len(eligible_candidates):
        errors.append("paperops_lifecycle_candidate_count_mismatch")
    for record in candidates:
        if isinstance(record, dict):
            errors.extend(_candidate_errors(record))
        else:
            errors.append("paperops_lifecycle_candidate_invalid")
    for record in results:
        if isinstance(record, dict):
            errors.extend(_result_errors(record))
        else:
            errors.append("paperops_lifecycle_result_invalid")
    if artifact.get("recorded") is True and artifact.get("event_log_written") is not True:
        errors.append("paperops_lifecycle_event_log_missing")
    if (
        artifact.get("event_log_written") is True
        and _int(artifact.get("event_log_event_count")) < 1
    ):
        errors.append("paperops_lifecycle_event_log_count_invalid")
    if artifact.get("source_paperops_2_schema_version") not in {
        PAPEROPS_ALPACA_POST_SCHEMA_VERSION,
        None,
    }:
        errors.append("paperops_lifecycle_source_schema_version_mismatch")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "read-only Alpaca paper lifecycle poller",
        "PaperOps-2 successfully submitted",
        "explicit poll flag",
        "cannot call broker POST routes",
        "cannot call live endpoints",
        "cannot expose secrets",
        "cannot grant Phase 7 proof credit",
    ):
        if phrase not in boundary:
            errors.append("paperops_lifecycle_boundary_weak")
            break
    if _contains_secret_shape(artifact):
        errors.append("paperops_lifecycle_secret_shape_exposed")
    return sorted(set(errors))


def write_paperops_paper_lifecycle_poller(
    artifact: dict[str, Any],
    settings: Settings | None = None,
    *,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    settings = settings or Settings.from_env()
    output_path, history_path, default_event_path = paperops_paper_lifecycle_poller_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = deepcopy(artifact)
    written["recorded"] = True
    written["runtime_artifact_path"] = str(output_path)
    written["history_log_path"] = str(history_path)
    if record_event:
        event = EventLog(event_path, echo=False).write(
            PAPEROPS_LIFECYCLE_POLLER_EVENT_TYPE,
            PAPEROPS_LIFECYCLE_POLLER_COMPONENT,
            payload={
                "status": written["status"],
                "poll_paper_orders_requested": written["poll_paper_orders_requested"],
                "source_submitted_paper_order_count": written["source_submitted_paper_order_count"],
                "paper_order_poll_called_count": written["paper_order_poll_called_count"],
                "paper_position_poll_called_count": written["paper_position_poll_called_count"],
                "live_endpoint_called_count": written["live_endpoint_called_count"],
                "broker_post_called_count": written["broker_post_called_count"],
                "phase7_proof_credit_allowed": written["phase7_proof_credit_allowed"],
            },
        )
        written["event_log_written"] = True
        written["event_log_path"] = str(event_path)
        written["event_log_event_count"] = 1
        written["event_log_correlation_id"] = event.correlation_id
        written["event_log_created_at"] = event.created_at
    written["validation_errors"] = validate_paperops_paper_lifecycle_poller(written)
    if written["validation_errors"]:
        written["status"] = "invalid"
    output_path.write_text(
        json.dumps(written, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_record = {
        "schema_version": PAPEROPS_LIFECYCLE_POLLER_SCHEMA_VERSION,
        "artifact_id": written.get("artifact_id"),
        "status": written.get("status"),
        "recorded_at": _now(),
        "poll_paper_orders_requested": written.get("poll_paper_orders_requested"),
        "source_submitted_paper_order_count": written.get("source_submitted_paper_order_count"),
        "paper_order_poll_called_count": written.get("paper_order_poll_called_count"),
        "paper_position_poll_called_count": written.get("paper_position_poll_called_count"),
        "live_endpoint_called_count": written.get("live_endpoint_called_count"),
        "broker_post_called_count": written.get("broker_post_called_count"),
        "validation_error_count": len(written.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, written


def paperops_paper_lifecycle_poller_public_status(
    settings: Settings | None = None,
) -> dict[str, Any]:
    artifact = read_latest_paperops_paper_lifecycle_poller(settings)
    if not artifact:
        return {
            "schema_version": PAPEROPS_LIFECYCLE_POLLER_SCHEMA_VERSION,
            "status": "not_run",
            "stage": "PaperOps-3",
            "source_submitted_paper_order_count": 0,
            "active_lifecycle_polling_enabled": False,
            "lifecycle_polling_enablement_status": "not_run",
            "lifecycle_polling_enablement_validation_error_count": 0,
            "paper_order_poll_called_count": 0,
            "paper_position_poll_called_count": 0,
            "broker_get_called_count": 0,
            "broker_post_called_count": 0,
            "live_endpoint_called_count": 0,
            "live_capital_enabled": False,
            "phase7_proof_credit_allowed": False,
            "secret_value_exposed": False,
            "raw_broker_payload_exposed": False,
            "broker_order_identifier_exposed": False,
            "boundary": PAPEROPS_LIFECYCLE_BOUNDARY,
        }
    return {
        "schema_version": artifact.get("schema_version"),
        "status": artifact.get("status"),
        "stage": artifact.get("stage"),
        "poll_paper_orders_requested": artifact.get("poll_paper_orders_requested"),
        "active_lifecycle_polling_enabled": artifact.get("active_lifecycle_polling_enabled"),
        "lifecycle_polling_enablement_status": artifact.get("lifecycle_polling_enablement_status"),
        "lifecycle_polling_enablement_validation_error_count": artifact.get(
            "lifecycle_polling_enablement_validation_error_count",
            0,
        ),
        "paper_poll_path_available": artifact.get("paper_poll_path_available"),
        "endpoint_classification": artifact.get("endpoint_classification"),
        "paper_endpoint_confirmed": artifact.get("paper_endpoint_confirmed"),
        "alpaca_api_key_configured": artifact.get("alpaca_api_key_configured"),
        "alpaca_api_secret_configured": artifact.get("alpaca_api_secret_configured"),
        "source_paperops_2_status": artifact.get("source_paperops_2_status"),
        "source_paperops_2_validation_error_count": artifact.get(
            "source_paperops_2_validation_error_count",
            0,
        ),
        "source_submitted_paper_order_count": artifact.get(
            "source_submitted_paper_order_count",
            0,
        ),
        "poll_candidate_count": artifact.get("poll_candidate_count", 0),
        "paper_order_poll_called_count": artifact.get(
            "paper_order_poll_called_count",
            0,
        ),
        "paper_order_poll_succeeded_count": artifact.get(
            "paper_order_poll_succeeded_count",
            0,
        ),
        "paper_position_poll_called_count": artifact.get(
            "paper_position_poll_called_count",
            0,
        ),
        "broker_get_called_count": artifact.get("broker_get_called_count", 0),
        "broker_post_called_count": artifact.get("broker_post_called_count", 0),
        "live_endpoint_called_count": artifact.get("live_endpoint_called_count", 0),
        "mirrored_submitted_order_count": artifact.get("mirrored_submitted_order_count", 0),
        "open_position_count": artifact.get("open_position_count", 0),
        "closed_trade_count": artifact.get("closed_trade_count", 0),
        "postmortem_due_marker_created_count": artifact.get(
            "postmortem_due_marker_created_count",
            0,
        ),
        "q7_lifecycle_mutation_performed": artifact.get("q7_lifecycle_mutation_performed"),
        "live_capital_enabled": artifact.get("live_capital_enabled"),
        "phase7_proof_credit_allowed": artifact.get("phase7_proof_credit_allowed"),
        "secret_value_exposed": artifact.get("secret_value_exposed"),
        "raw_broker_payload_exposed": artifact.get("raw_broker_payload_exposed"),
        "broker_order_identifier_exposed": artifact.get("broker_order_identifier_exposed"),
        "boundary": artifact.get("boundary", PAPEROPS_LIFECYCLE_BOUNDARY),
    }
