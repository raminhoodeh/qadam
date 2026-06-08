"""PaperOps-4 guarded Alpaca paper exit path.

This stage defines the paper-only close/exit boundary after PaperOps-3 has
read back an open paper position. It is disabled by default. A close request can
only reach Alpaca paper when the PaperOps-4 flag is enabled, Qadam is in paper
mode, live capital is disabled, the endpoint is classified as Alpaca paper, the
source lifecycle readback contains an open position, an Event Log prewrite is
recorded, and the caller passes an explicit CLI execution flag.
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
from orchestrator.paper_account import PaperAccountMirrorStore
from orchestrator.paperops_alpaca_paper_post import _endpoint_context, _headers, _orders_url
from orchestrator.paperops_paper_lifecycle_poller import (
    PAPEROPS_LIFECYCLE_POLLER_SCHEMA_VERSION,
    read_latest_paperops_paper_lifecycle_poller,
    validate_paperops_paper_lifecycle_poller,
)
from orchestrator.paperops_guarded_paper_exit_enablement import (
    PAPEROPS_GUARDED_EXIT_ENABLEMENT_READY_STATUSES,
    read_latest_paperops_guarded_paper_exit_enablement,
    validate_paperops_guarded_paper_exit_enablement,
)


PAPEROPS_EXIT_PATH_SCHEMA_VERSION = 1
PAPEROPS_EXIT_PATH_RUNTIME_ARTIFACT = "paperops_paper_exit_path.json"
PAPEROPS_EXIT_PATH_HISTORY = "paperops_paper_exit_path_history.jsonl"
PAPEROPS_EXIT_PATH_EVENT_LOG = "paperops_paper_exit_path_events.jsonl"
PAPEROPS_EXIT_PATH_EVENT_TYPE = "paperops_paper_exit_path_recorded"
PAPEROPS_EXIT_PATH_PREWRITE_EVENT_TYPE = "paperops_paper_exit_path_prewrite"
PAPEROPS_EXIT_PATH_COMPONENT = "paperops_paper_exit_path"

PAPEROPS_EXIT_AUTHORITY_FALSE_FIELDS = (
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

PAPEROPS_EXIT_BOUNDARY = (
    "PaperOps-4 is the guarded Alpaca paper-only exit path. It may close a "
    "paper position only when QADAM_ALPACA_PAPER_EXIT_ENABLED=true or PT-7 "
    "guarded paper-exit runtime enablement is recorded, QADAM_MODE=paper, live "
    "capital is disabled, the endpoint is classified as Alpaca paper, paper "
    "credentials are configured, PaperOps-3 has a valid open-position readback, "
    "an Event Log prewrite is recorded, and the caller passes the explicit "
    "paper-exit CLI flag. It cannot call live endpoints, cannot use live "
    "credentials, cannot cancel or resize orders, cannot write "
    "prediction-market or crypto-perps orders, cannot expose secrets, raw "
    "broker payloads, base URLs, authorization headers, or raw broker "
    "identifiers, cannot grant Phase 7 proof credit, and cannot enable live "
    "capital."
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

EXIT_READY_STATUSES = frozenset(
    {
        "ready_no_exit_candidate",
        "ready_pending_explicit_execute",
        "paper_exit_close_recorded",
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


def paperops_paper_exit_path_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PAPEROPS_EXIT_PATH_RUNTIME_ARTIFACT,
        runtime / PAPEROPS_EXIT_PATH_HISTORY,
        runtime / PAPEROPS_EXIT_PATH_EVENT_LOG,
    )


def read_latest_paperops_paper_exit_path(settings: Settings | None = None) -> dict[str, Any]:
    output_path, _, _ = paperops_paper_exit_path_paths(settings)
    if not output_path.exists():
        return {}
    return _read_json(output_path)


def _contains_secret_shape(value: object) -> bool:
    text = json.dumps(value, sort_keys=True, default=str)
    return any(pattern.search(text) for pattern in PROHIBITED_VALUE_PATTERNS)


def _fingerprint(payload: dict[str, Any]) -> str:
    return sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _hash_identifier(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return sha256(text.encode("utf-8")).hexdigest()


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _close_position_url(settings: Settings, symbol: str) -> str:
    orders_url = _orders_url(settings)
    base = orders_url.rsplit("/orders", 1)[0]
    return f"{base}/positions/{symbol.upper()}"


def _source_record_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("record_type") != "paperops_q7_lifecycle_readback_record":
        errors.append("source_record_type_invalid")
    if record.get("lifecycle_state") != "open_position":
        errors.append("source_lifecycle_state_not_open_position")
    if record.get("position_echo_present") is not True:
        errors.append("source_position_echo_missing")
    if not str(record.get("symbol") or "").strip():
        errors.append("source_symbol_missing")
    if not str(record.get("broker_order_id_hash") or "").strip():
        errors.append("source_broker_order_hash_missing")
    if not str(record.get("client_order_id_hash") or "").strip():
        errors.append("source_client_order_hash_missing")
    if record.get("counts_as_phase7_proof_credit") is not False:
        errors.append("source_phase7_proof_credit_not_false")
    if record.get("q7_lifecycle_mutation_performed") is not False:
        errors.append("source_q7_lifecycle_mutation_not_false")
    if record.get("postmortem_due_marker_created") is not False:
        errors.append("source_postmortem_marker_not_false")
    for key in ("raw_broker_payload_exposed", "broker_order_identifier_exposed"):
        if record.get(key) is not False:
            errors.append(f"source_record_forbidden:{key}")
    return sorted(set(errors))


def _source_record_to_exit_candidate(record: dict[str, Any]) -> dict[str, Any]:
    errors = _source_record_errors(record)
    symbol = str(record.get("symbol") or "").upper()
    request_preview = {
        "request_type": "paperops_alpaca_paper_position_close",
        "method": "DELETE",
        "path": "/v2/positions/{symbol}",
        "symbol": symbol,
        "source_lifecycle_state": record.get("lifecycle_state"),
        "client_order_id_hash": record.get("client_order_id_hash"),
        "broker_order_id_hash": record.get("broker_order_id_hash"),
        "base_url_exposed": False,
        "authorization_header_included": False,
        "raw_payload_exposed": False,
        "broker_identifier_exposed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
    }
    return {
        "schema_version": PAPEROPS_EXIT_PATH_SCHEMA_VERSION,
        "record_type": "paperops_paper_exit_candidate",
        "exit_intent_id": (
            "paperops-exit:"
            f"{symbol.lower() or 'unknown'}:"
            f"{str(record.get('client_order_id_hash') or 'unknown')[:12]}"
        ),
        "source_lifecycle_record_type": record.get("record_type"),
        "source_lifecycle_state": record.get("lifecycle_state"),
        "source_submit_record_artifact_id": record.get("source_submit_record_artifact_id"),
        "source_staged_order_artifact_id": record.get("source_staged_order_artifact_id"),
        "source_proof_order_id": record.get("source_proof_order_id"),
        "source_auto_approval_decision_id": record.get("source_auto_approval_decision_id"),
        "source_setup_record_id": record.get("source_setup_record_id"),
        "client_order_id_hash": record.get("client_order_id_hash"),
        "broker_order_id_hash": record.get("broker_order_id_hash"),
        "symbol": symbol,
        "filled_qty": record.get("filled_qty"),
        "exit_action": "close_paper_position",
        "exit_method": "DELETE",
        "exit_path_template": "/v2/positions/{symbol}",
        "request_preview": request_preview,
        "request_fingerprint": _fingerprint(request_preview),
        "source_record_errors": errors,
        "eligible_for_paper_exit": not errors,
        "status": "eligible" if not errors else "blocked_source_contract",
        "base_url_exposed": False,
        "authorization_header_included": False,
        "authorization_header_exposed": False,
        "raw_broker_payload_stored": False,
        "raw_broker_payload_exposed": False,
        "broker_order_identifier_exposed": False,
        "secret_value_exposed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "manual_trade_level_override_allowed": False,
    }


def _source_exit_candidates(source: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records = [
        record
        for record in source.get("lifecycle_mirror_records", []) or []
        if isinstance(record, dict)
    ]
    candidates = [_source_record_to_exit_candidate(record) for record in records]
    eligible = [candidate for candidate in candidates if candidate["eligible_for_paper_exit"]]
    return candidates, eligible


def _mirror_position_to_exit_candidate(
    position: Any,
    *,
    pending_close_symbols: set[str],
) -> dict[str, Any]:
    symbol = str(getattr(position, "instrument", "") or "").upper()
    position_id = getattr(position, "position_id", None)
    position_hash = _hash_identifier(f"paper-mirror:{symbol}:{position_id}")
    request_preview = {
        "request_type": "paperops_alpaca_paper_position_close",
        "method": "DELETE",
        "path": "/v2/positions/{symbol}",
        "symbol": symbol,
        "source_lifecycle_state": "open_position",
        "source_record_type": "alpaca_paper_mirror_position",
        "client_order_id_hash": position_hash,
        "broker_order_id_hash": position_hash,
        "base_url_exposed": False,
        "authorization_header_included": False,
        "raw_payload_exposed": False,
        "broker_identifier_exposed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
    }
    errors = []
    if not symbol:
        errors.append("source_symbol_missing")
    if getattr(position, "status", None) != "open_position":
        errors.append("source_lifecycle_state_not_open_position")
    if not position_hash:
        errors.append("source_position_hash_missing")
    if symbol in pending_close_symbols:
        errors.append("source_pending_close_order_exists")
    return {
        "schema_version": PAPEROPS_EXIT_PATH_SCHEMA_VERSION,
        "record_type": "paperops_paper_exit_candidate",
        "exit_intent_id": f"paperops-exit:{symbol.lower() or 'unknown'}:{str(position_hash or 'unknown')[:12]}",
        "source_lifecycle_record_type": "alpaca_paper_mirror_position",
        "source_lifecycle_state": "open_position",
        "source_submit_record_artifact_id": None,
        "source_staged_order_artifact_id": None,
        "source_proof_order_id": None,
        "source_auto_approval_decision_id": None,
        "source_setup_record_id": None,
        "client_order_id_hash": position_hash,
        "broker_order_id_hash": position_hash,
        "symbol": symbol,
        "filled_qty": getattr(position, "quantity", None),
        "exit_action": "close_paper_position",
        "exit_method": "DELETE",
        "exit_path_template": "/v2/positions/{symbol}",
        "request_preview": request_preview,
        "request_fingerprint": _fingerprint(request_preview),
        "source_record_errors": errors,
        "eligible_for_paper_exit": not errors,
        "status": "eligible" if not errors else "blocked_source_contract",
        "base_url_exposed": False,
        "authorization_header_included": False,
        "authorization_header_exposed": False,
        "raw_broker_payload_stored": False,
        "raw_broker_payload_exposed": False,
        "broker_order_identifier_exposed": False,
        "secret_value_exposed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "manual_trade_level_override_allowed": False,
    }


def _mirror_position_exit_candidates(
    settings: Settings,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    try:
        store = PaperAccountMirrorStore(settings=settings)
        positions = store.read_positions()
        orders = store.read_orders()
    except Exception:  # noqa: BLE001 - exit gate must fail closed on corrupt mirror.
        return [], [], "mirror_unavailable"
    pending_close_symbols = {
        str(getattr(order, "instrument", "") or "").upper()
        for order in orders
        if str(getattr(order, "direction", "") or "").lower() == "sell"
        and str(getattr(order, "status", "") or "").lower()
        in {"new", "accepted", "pending_new", "partially_filled"}
    }
    candidates = [
        _mirror_position_to_exit_candidate(
            position,
            pending_close_symbols=pending_close_symbols,
        )
        for position in positions
    ]
    eligible = [candidate for candidate in candidates if candidate["eligible_for_paper_exit"]]
    return candidates, eligible, "mirror_available"


def _sanitize_close_receipt(payload: dict[str, Any] | list[Any], *, closed_at: str) -> dict[str, Any]:
    if isinstance(payload, dict):
        order_payload = payload
    elif isinstance(payload, list) and payload and isinstance(payload[0], dict):
        order_payload = payload[0]
    else:
        order_payload = {}
    return {
        "receipt_type": "alpaca_paper_position_close_receipt",
        "receipt_state": "paper_position_close_requested",
        "closed_at": closed_at,
        "broker_order_status": order_payload.get("status"),
        "broker_client_order_id_hash": _hash_identifier(order_payload.get("client_order_id")),
        "broker_order_id_hash": _hash_identifier(order_payload.get("id")),
        "symbol": str(order_payload.get("symbol") or "").upper() or None,
        "side": str(order_payload.get("side") or "").lower() or None,
        "qty": str(order_payload.get("qty") or "") or None,
        "broker_order_identifier_exposed": False,
        "raw_broker_payload_stored": False,
        "raw_broker_payload_exposed": False,
        "authorization_header_exposed": False,
        "base_url_exposed": False,
        "secret_value_exposed": False,
    }


def _close_alpaca_paper_position(
    *,
    settings: Settings,
    candidate: dict[str, Any],
    timeout_seconds: float = 12.0,
) -> dict[str, Any]:
    try:
        import httpx
    except ImportError as exc:
        return {
            "close_attempted": False,
            "close_succeeded": False,
            "failure_class": "missing_httpx",
            "failure_message_persisted": False,
            "sanitized_http_status": None,
            "receipt": None,
            "exception": exc,
        }

    closed_at = _now()
    try:
        with httpx.Client(timeout=timeout_seconds, follow_redirects=False) as client:
            response = client.delete(
                _close_position_url(settings, str(candidate["symbol"])),
                headers=_headers(settings),
            )
        status_code = response.status_code
        if status_code < 200 or status_code >= 300:
            return {
                "close_attempted": True,
                "close_succeeded": False,
                "failure_class": f"http_{status_code}",
                "failure_message_persisted": False,
                "sanitized_http_status": status_code,
                "receipt": None,
                "exception": None,
            }
        payload = response.json()
        if not isinstance(payload, (dict, list)):
            payload = {}
        return {
            "close_attempted": True,
            "close_succeeded": True,
            "failure_class": None,
            "failure_message_persisted": False,
            "sanitized_http_status": status_code,
            "receipt": _sanitize_close_receipt(payload, closed_at=closed_at),
            "exception": None,
        }
    except Exception as exc:  # noqa: BLE001 - persist sanitized class only.
        return {
            "close_attempted": True,
            "close_succeeded": False,
            "failure_class": type(exc).__name__,
            "failure_message_persisted": False,
            "sanitized_http_status": None,
            "receipt": None,
            "exception": None,
        }


def _status(
    *,
    settings: Settings,
    paper_exit_effective: bool,
    endpoint: dict[str, Any],
    source_present: bool,
    source_valid: bool,
    eligible_count: int,
    execute_exit: bool,
    close_result: dict[str, Any] | None,
) -> str:
    if settings.mode != "paper":
        return "blocked_not_paper_mode"
    if settings.live_capital_enabled:
        return "blocked_live_capital_enabled"
    if not paper_exit_effective:
        return "disabled_pending_enablement"
    if endpoint["paper_endpoint_confirmed"] is not True:
        return "blocked_non_paper_endpoint"
    if not endpoint["alpaca_api_key_configured"] or not endpoint["alpaca_api_secret_configured"]:
        return "blocked_missing_alpaca_paper_credentials"
    if not source_present:
        return "blocked_missing_paper_lifecycle_source"
    if not source_valid:
        return "blocked_invalid_paper_lifecycle_source"
    if eligible_count < 1:
        return "ready_no_exit_candidate"
    if not execute_exit:
        return "ready_pending_explicit_execute"
    if close_result and close_result.get("close_succeeded") is True:
        return "paper_exit_close_recorded"
    return "paper_exit_close_failed_sanitized"


def build_paperops_paper_exit_path(
    settings: Settings | None = None,
    *,
    execute_exit: bool = False,
    event_log_path: str | Path | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    endpoint = _endpoint_context(settings)
    exit_enablement = read_latest_paperops_guarded_paper_exit_enablement(settings)
    exit_enablement_validation_errors = (
        validate_paperops_guarded_paper_exit_enablement(exit_enablement)
        if exit_enablement
        else []
    )
    runtime_exit_enabled = (
        exit_enablement.get("status") in PAPEROPS_GUARDED_EXIT_ENABLEMENT_READY_STATUSES
        and exit_enablement.get("guarded_paper_exit_enabled") is True
        and exit_enablement.get("alpaca_paper_exit_effective") is True
        and exit_enablement.get("live_capital_enabled") is False
        and exit_enablement.get("phase7_proof_credit_allowed") is False
        and _int(exit_enablement.get("paper_position_close_called_count")) == 0
        and _int(exit_enablement.get("live_endpoint_called_count")) == 0
        and _int(exit_enablement.get("unsafe_write_counter_total")) == 0
        and not exit_enablement_validation_errors
    )
    paper_exit_effective = settings.alpaca_paper_exit_enabled or runtime_exit_enabled
    source = read_latest_paperops_paper_lifecycle_poller(settings)
    source_present = bool(source)
    source_validation_errors = (
        validate_paperops_paper_lifecycle_poller(source) if source_present else []
    )
    source_valid = source_present and not source_validation_errors
    source_candidates, source_eligible_candidates = _source_exit_candidates(source)
    mirror_candidates, mirror_eligible_candidates, mirror_source_status = (
        _mirror_position_exit_candidates(settings)
    )
    eligible_candidates = source_eligible_candidates or mirror_eligible_candidates
    all_candidates = source_candidates + mirror_candidates
    selected_candidate = eligible_candidates[0] if eligible_candidates else None
    source_or_mirror_present = source_present or bool(mirror_candidates)
    source_or_mirror_valid = (source_valid if source_present else True) and (
        mirror_source_status == "mirror_available" or not mirror_candidates
    )
    preconditions = {
        "mode_is_paper": settings.mode == "paper",
        "live_capital_disabled": settings.live_capital_enabled is False,
        "paper_exit_flag_enabled": paper_exit_effective is True,
        "settings_paper_exit_flag_or_pt7_runtime_enablement": paper_exit_effective is True,
        "alpaca_endpoint_classified_paper": endpoint["paper_endpoint_confirmed"] is True,
        "alpaca_paper_credentials_configured": endpoint["alpaca_api_key_configured"] is True
        and endpoint["alpaca_api_secret_configured"] is True,
        "paperops_3_or_paper_mirror_source_present": source_or_mirror_present,
        "paperops_3_or_paper_mirror_source_valid": source_or_mirror_valid,
        "open_position_readback_present": selected_candidate is not None,
    }
    precondition_failures = [
        key for key, passed in preconditions.items() if passed is not True
    ]
    exit_path_available = not precondition_failures
    close_result: dict[str, Any] | None = None
    prewrite_entry_ref: str | None = None
    prewrite_event_count = 0

    if execute_exit and exit_path_available and selected_candidate is not None:
        event_path = Path(event_log_path or (_runtime_dir(settings) / PAPEROPS_EXIT_PATH_EVENT_LOG))
        prewrite = EventLog(event_path, echo=False).write(
            PAPEROPS_EXIT_PATH_PREWRITE_EVENT_TYPE,
            PAPEROPS_EXIT_PATH_COMPONENT,
            payload={
                "status": "prewrite_before_alpaca_paper_position_close",
                "exit_intent_id": selected_candidate.get("exit_intent_id"),
                "source_proof_order_id": selected_candidate.get("source_proof_order_id"),
                "source_staged_order_artifact_id": selected_candidate.get(
                    "source_staged_order_artifact_id"
                ),
                "symbol": selected_candidate.get("symbol"),
                "request_fingerprint": selected_candidate.get("request_fingerprint"),
                "endpoint_classification": endpoint["endpoint_classification"],
                "live_endpoint_allowed": False,
                "live_capital_enabled": False,
            },
        )
        prewrite_entry_ref = prewrite.correlation_id
        prewrite_event_count = 1
        close_result = _close_alpaca_paper_position(
            settings=settings,
            candidate=selected_candidate,
        )
        selected_candidate = deepcopy(selected_candidate)
        selected_candidate["paperops_exit_event_log_prewrite_written"] = True
        selected_candidate["paperops_exit_event_log_prewrite_ref"] = prewrite_entry_ref
        selected_candidate["paper_position_close_called"] = close_result["close_attempted"]
        selected_candidate["paper_position_close_succeeded"] = close_result["close_succeeded"]
        selected_candidate["sanitized_http_status"] = close_result["sanitized_http_status"]
        selected_candidate["broker_failure_class"] = close_result["failure_class"]
        selected_candidate["broker_failure_message_persisted"] = False
        selected_candidate["broker_close_receipt"] = close_result["receipt"]
        selected_candidate["status"] = (
            "paper_exit_close_recorded"
            if close_result["close_succeeded"]
            else "paper_exit_close_failed_sanitized"
        )

    close_attempted = bool(close_result and close_result.get("close_attempted"))
    close_succeeded = bool(close_result and close_result.get("close_succeeded"))
    status = _status(
        settings=settings,
        paper_exit_effective=paper_exit_effective,
        endpoint=endpoint,
        source_present=source_or_mirror_present,
        source_valid=source_or_mirror_valid,
        eligible_count=len(eligible_candidates),
        execute_exit=execute_exit,
        close_result=close_result,
    )
    selected_records = [selected_candidate] if selected_candidate is not None else []
    artifact = {
        "schema_version": PAPEROPS_EXIT_PATH_SCHEMA_VERSION,
        "artifact_type": "paperops_paper_exit_path",
        "artifact_id": "paperops:paper-exit-path:latest",
        "phase": "PaperOps",
        "stage": "PaperOps-4",
        "status": status,
        "generated_at": generated_at,
        "public_safe": True,
        "recorded": False,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_event_count": prewrite_event_count,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "runtime_artifact_path": None,
        "history_log_path": None,
        "mode": settings.mode,
        "paper_operational_enabled": settings.paper_operational_enabled,
        "alpaca_paper_exit_enabled": paper_exit_effective,
        "alpaca_paper_exit_effective": paper_exit_effective,
        "settings_alpaca_paper_exit_enabled": settings.alpaca_paper_exit_enabled,
        "runtime_alpaca_paper_exit_enabled": runtime_exit_enabled,
        "runtime_artifact_override_enabled": (
            runtime_exit_enabled and not settings.alpaca_paper_exit_enabled
        ),
        "paper_exit_runtime_enablement_status": exit_enablement.get(
            "status",
            "missing",
        ),
        "paper_exit_runtime_enablement_validation_error_count": len(
            exit_enablement_validation_errors
        ),
        "paper_exit_runtime_enablement_path_available": (
            exit_enablement.get("paper_exit_path_available") is True
        ),
        "paper_exit_runtime_enablement_idle_until_open_position": (
            exit_enablement.get("paper_exit_idle_until_open_position") is True
        ),
        "paper_exit_runtime_enablement_open_position_count": _int(
            exit_enablement.get("paperops_3_open_position_count")
        ),
        "paper_exit_runtime_enablement_close_called_count": _int(
            exit_enablement.get("paper_position_close_called_count")
        ),
        "paper_exit_runtime_enablement_live_endpoint_called_count": _int(
            exit_enablement.get("live_endpoint_called_count")
        ),
        "paper_exit_runtime_enablement_unsafe_write_counter_total": _int(
            exit_enablement.get("unsafe_write_counter_total")
        ),
        "live_capital_enabled": settings.live_capital_enabled,
        "execute_exit_requested": execute_exit,
        "explicit_exit_flag_required": True,
        "paper_exit_path_available": exit_path_available,
        "exit_path_method": "DELETE",
        "exit_path_template": "/v2/positions/{symbol}",
        "endpoint_classification": endpoint["endpoint_classification"],
        "paper_endpoint_confirmed": endpoint["paper_endpoint_confirmed"],
        "alpaca_paper_flag": endpoint["alpaca_paper_flag"],
        "alpaca_api_key_configured": endpoint["alpaca_api_key_configured"],
        "alpaca_api_secret_configured": endpoint["alpaca_api_secret_configured"],
        "precondition_records": [
            {"key": key, "passed": passed} for key, passed in preconditions.items()
        ],
        "precondition_failure_count": len(precondition_failures),
        "precondition_failures": precondition_failures,
        "source_paperops_3_schema_version": source.get("schema_version"),
        "source_paperops_3_artifact_present": source_present,
        "source_paperops_3_artifact_id": source.get("artifact_id"),
        "source_paperops_3_status": source.get("status", "missing"),
        "source_paperops_3_stage": source.get("stage"),
        "source_paperops_3_validation_error_count": len(source_validation_errors),
        "source_paperops_3_validation_errors": source_validation_errors[:12],
        "source_lifecycle_record_count": len(
            [record for record in source.get("lifecycle_mirror_records", []) or [] if isinstance(record, dict)]
        )
        if source_present
        else 0,
        "paper_account_mirror_position_source_status": mirror_source_status,
        "paper_account_mirror_open_position_count": len(mirror_candidates),
        "paper_account_mirror_eligible_exit_count": len(mirror_eligible_candidates),
        "open_position_readback_count": len(eligible_candidates),
        "eligible_exit_record_count": len(eligible_candidates),
        "blocked_source_record_count": len(all_candidates) - len(eligible_candidates),
        "exit_candidates": all_candidates,
        "selected_exit_records": selected_records,
        "paperops_exit_event_log_prewrite_required": bool(execute_exit and selected_candidate),
        "paperops_exit_event_log_prewrite_written": prewrite_entry_ref is not None,
        "paperops_exit_event_log_prewrite_ref": prewrite_entry_ref,
        "paperops_exit_event_log_prewrite_count": prewrite_event_count,
        "paper_position_close_called_count": 1 if close_attempted else 0,
        "paper_position_close_succeeded_count": 1 if close_succeeded else 0,
        "paper_position_close_failed_count": 1 if close_attempted and not close_succeeded else 0,
        "alpaca_paper_close_called_count": 1 if close_attempted else 0,
        "broker_write_called_count": 1 if close_attempted else 0,
        "broker_close_receipt_created_count": 1 if close_succeeded else 0,
        "broker_post_called_count": 0,
        "alpaca_post_called_count": 0,
        "order_cancel_called_count": 0,
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
        "q7_lifecycle_mutation_performed": False,
        "postmortem_due_marker_created_count": 0,
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
            "PaperOps-5 notification and review"
            if status in EXIT_READY_STATUSES
            else "Wait for PaperOps-3 open-position readback and explicit paper-exit enablement"
        ),
        "boundary": PAPEROPS_EXIT_BOUNDARY,
    }
    artifact["validation_errors"] = validate_paperops_paper_exit_path(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "invalid"
    return artifact


def _candidate_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    preview = record.get("request_preview", {})
    if not isinstance(preview, dict):
        errors.append("paperops_exit_candidate_request_preview_missing")
        preview = {}
    if record.get("eligible_for_paper_exit") is True:
        if record.get("source_lifecycle_state") != "open_position":
            errors.append("paperops_exit_candidate_state_invalid")
        if not str(record.get("symbol") or "").strip():
            errors.append("paperops_exit_candidate_symbol_missing")
        if not str(record.get("client_order_id_hash") or "").strip():
            errors.append("paperops_exit_candidate_client_hash_missing")
        if not str(record.get("broker_order_id_hash") or "").strip():
            errors.append("paperops_exit_candidate_broker_hash_missing")
        if record.get("request_fingerprint") != _fingerprint(preview):
            errors.append("paperops_exit_candidate_request_fingerprint_mismatch")
    else:
        if record.get("status") != "blocked_source_contract":
            errors.append("paperops_exit_blocked_candidate_status_invalid")
        if not isinstance(record.get("source_record_errors"), list):
            errors.append("paperops_exit_blocked_candidate_errors_missing")
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
        "manual_trade_level_override_allowed",
    ):
        if record.get(key) is not False:
            errors.append(f"paperops_exit_candidate_forbidden:{key}")
    for key in (
        "base_url_exposed",
        "authorization_header_included",
        "raw_payload_exposed",
        "broker_identifier_exposed",
        "live_endpoint_allowed",
        "live_capital_enabled",
    ):
        if preview.get(key) is not False:
            errors.append(f"paperops_exit_candidate_preview_forbidden:{key}")
    receipt = record.get("broker_close_receipt")
    if isinstance(receipt, dict):
        for key in (
            "broker_order_identifier_exposed",
            "raw_broker_payload_stored",
            "raw_broker_payload_exposed",
            "authorization_header_exposed",
            "base_url_exposed",
            "secret_value_exposed",
        ):
            if receipt.get(key) is not False:
                errors.append(f"paperops_exit_receipt_forbidden:{key}")
    return errors


def validate_paperops_paper_exit_path(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "alpaca_api_key_configured",
        "alpaca_api_secret_configured",
        "alpaca_paper_exit_effective",
        "alpaca_paper_exit_enabled",
        "artifact_type",
        "base_url_exposed",
        "boundary",
        "broker_order_identifier_exposed",
        "broker_post_called_count",
        "broker_write_called_count",
        "crypto_perps_write_allowed",
        "endpoint_classification",
        "event_log_required",
        "event_log_written",
        "execute_exit_requested",
        "explicit_exit_flag_required",
        "exit_candidates",
        "live_capital_enabled",
        "live_endpoint_allowed",
        "mode",
        "open_position_readback_count",
        "paper_endpoint_confirmed",
        "paper_exit_path_available",
        "paper_position_close_called_count",
        "phase",
        "phase7_proof_credit_allowed",
        "prediction_market_write_allowed",
        "public_safe",
        "q7_lifecycle_mutation_performed",
        "raw_broker_payload_exposed",
        "raw_broker_payload_stored",
        "recorded",
        "runtime_alpaca_paper_exit_enabled",
        "runtime_artifact_override_enabled",
        "schema_version",
        "secret_value_exposed",
        "selected_exit_records",
        "settings_alpaca_paper_exit_enabled",
        "source_paperops_3_artifact_present",
        "source_paperops_3_status",
        "stage",
        "status",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("paperops_exit_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PAPEROPS_EXIT_PATH_SCHEMA_VERSION:
        errors.append("paperops_exit_schema_version_mismatch")
    if artifact.get("artifact_type") != "paperops_paper_exit_path":
        errors.append("paperops_exit_artifact_type_mismatch")
    if artifact.get("phase") != "PaperOps" or artifact.get("stage") != "PaperOps-4":
        errors.append("paperops_exit_phase_stage_mismatch")
    if artifact.get("mode") != "paper":
        errors.append("paperops_exit_mode_not_paper")
    if artifact.get("public_safe") is not True:
        errors.append("paperops_exit_not_public_safe")
    for key in PAPEROPS_EXIT_AUTHORITY_FALSE_FIELDS:
        if artifact.get(key) is not False:
            errors.append(f"paperops_exit_forbidden:{key}")
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "order_cancel_called_count",
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
        "postmortem_due_marker_created_count",
        "paper_exit_runtime_enablement_close_called_count",
        "paper_exit_runtime_enablement_live_endpoint_called_count",
        "paper_exit_runtime_enablement_unsafe_write_counter_total",
    ):
        if _int(artifact.get(key)) != 0:
            errors.append(f"paperops_exit_unsafe_counter_nonzero:{key}")
    if artifact.get("alpaca_paper_exit_enabled") is not artifact.get(
        "alpaca_paper_exit_effective"
    ):
        errors.append("paperops_exit_effective_flag_mismatch")
    if artifact.get("alpaca_paper_exit_enabled") is True:
        if (
            artifact.get("settings_alpaca_paper_exit_enabled") is not True
            and artifact.get("runtime_alpaca_paper_exit_enabled") is not True
        ):
            errors.append("paperops_exit_enabled_without_settings_or_runtime")
        if (
            artifact.get("settings_alpaca_paper_exit_enabled") is not True
            and artifact.get("runtime_artifact_override_enabled") is not True
        ):
            errors.append("paperops_exit_runtime_override_false")
    if artifact.get("explicit_exit_flag_required") is not True:
        errors.append("paperops_exit_explicit_flag_not_required")
    if artifact.get("q7_lifecycle_mutation_performed") is not False:
        errors.append("paperops_exit_q7_lifecycle_mutation_performed")
    if artifact.get("alpaca_paper_exit_enabled") is not True:
        if _int(artifact.get("paper_position_close_called_count")) != 0:
            errors.append("paperops_exit_called_without_flag")
        if artifact.get("status") not in {
            "disabled_pending_enablement",
            "blocked_not_paper_mode",
            "blocked_live_capital_enabled",
            "invalid",
        }:
            errors.append("paperops_exit_disabled_status_invalid")
    if artifact.get("execute_exit_requested") is not True:
        if _int(artifact.get("paper_position_close_called_count")) != 0:
            errors.append("paperops_exit_called_without_explicit_execute")
    if _int(artifact.get("paper_position_close_called_count")):
        if artifact.get("execute_exit_requested") is not True:
            errors.append("paperops_exit_close_called_without_execute")
        if artifact.get("alpaca_paper_exit_enabled") is not True:
            errors.append("paperops_exit_close_called_without_flag")
        if artifact.get("paper_endpoint_confirmed") is not True:
            errors.append("paperops_exit_close_called_without_paper_endpoint")
        if artifact.get("paperops_exit_event_log_prewrite_written") is not True:
            errors.append("paperops_exit_close_called_without_prewrite")
        if _int(artifact.get("eligible_exit_record_count")) < 1:
            errors.append("paperops_exit_close_called_without_candidate")
        if artifact.get("source_paperops_3_validation_error_count") not in {0, None}:
            errors.append("paperops_exit_close_called_with_invalid_source")
    if _int(artifact.get("paper_position_close_succeeded_count")) > _int(
        artifact.get("paper_position_close_called_count")
    ):
        errors.append("paperops_exit_success_gt_called")
    if artifact.get("paper_endpoint_confirmed") is not True and artifact.get(
        "paper_exit_path_available"
    ) is True:
        errors.append("paperops_exit_path_available_without_paper_endpoint")
    if artifact.get("status") == "ready_no_exit_candidate" and _int(
        artifact.get("eligible_exit_record_count")
    ):
        errors.append("paperops_exit_no_candidate_status_with_candidate")
    if artifact.get("status") == "ready_pending_explicit_execute" and (
        artifact.get("execute_exit_requested") is True
        or _int(artifact.get("eligible_exit_record_count")) < 1
    ):
        errors.append("paperops_exit_pending_execute_state_invalid")
    candidates = artifact.get("exit_candidates", [])
    selected = artifact.get("selected_exit_records", [])
    if not isinstance(candidates, list):
        errors.append("paperops_exit_candidates_not_list")
        candidates = []
    if not isinstance(selected, list):
        errors.append("paperops_exit_selected_records_not_list")
        selected = []
    eligible_candidates = [
        record
        for record in candidates
        if isinstance(record, dict) and record.get("eligible_for_paper_exit") is True
    ]
    if _int(artifact.get("eligible_exit_record_count")) != len(eligible_candidates):
        errors.append("paperops_exit_eligible_count_mismatch")
    for record in candidates + selected:
        if isinstance(record, dict):
            errors.extend(_candidate_errors(record))
        else:
            errors.append("paperops_exit_candidate_invalid")
    if artifact.get("recorded") is True and artifact.get("event_log_written") is not True:
        errors.append("paperops_exit_event_log_missing")
    if artifact.get("event_log_written") is True and _int(artifact.get("event_log_event_count")) < 1:
        errors.append("paperops_exit_event_log_count_invalid")
    if artifact.get("source_paperops_3_schema_version") not in {
        PAPEROPS_LIFECYCLE_POLLER_SCHEMA_VERSION,
        None,
    }:
        errors.append("paperops_exit_source_schema_version_mismatch")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "guarded Alpaca paper-only exit path",
        "QADAM_ALPACA_PAPER_EXIT_ENABLED=true",
        "Event Log prewrite",
        "explicit paper-exit CLI flag",
        "cannot call live endpoints",
        "cannot cancel or resize orders",
        "cannot expose secrets",
        "cannot grant Phase 7 proof credit",
    ):
        if phrase not in boundary:
            errors.append("paperops_exit_boundary_weak")
            break
    if _contains_secret_shape(artifact):
        errors.append("paperops_exit_secret_shape_exposed")
    return sorted(set(errors))


def write_paperops_paper_exit_path(
    artifact: dict[str, Any],
    settings: Settings | None = None,
    *,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    settings = settings or Settings.from_env()
    output_path, history_path, default_event_path = paperops_paper_exit_path_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = deepcopy(artifact)
    written["recorded"] = True
    written["runtime_artifact_path"] = str(output_path)
    written["history_log_path"] = str(history_path)
    if record_event:
        event = EventLog(event_path, echo=False).write(
            PAPEROPS_EXIT_PATH_EVENT_TYPE,
            PAPEROPS_EXIT_PATH_COMPONENT,
            payload={
                "status": written["status"],
                "execute_exit_requested": written["execute_exit_requested"],
                "alpaca_paper_exit_effective": written["alpaca_paper_exit_effective"],
                "runtime_alpaca_paper_exit_enabled": written[
                    "runtime_alpaca_paper_exit_enabled"
                ],
                "paper_exit_path_available": written["paper_exit_path_available"],
                "eligible_exit_record_count": written["eligible_exit_record_count"],
                "paper_position_close_called_count": written[
                    "paper_position_close_called_count"
                ],
                "paper_position_close_succeeded_count": written[
                    "paper_position_close_succeeded_count"
                ],
                "live_endpoint_called_count": written["live_endpoint_called_count"],
                "phase7_proof_credit_allowed": written["phase7_proof_credit_allowed"],
            },
        )
        written["event_log_written"] = True
        written["event_log_path"] = str(event_path)
        written["event_log_event_count"] = int(
            written.get("paperops_exit_event_log_prewrite_count", 0) or 0
        ) + 1
        written["event_log_correlation_id"] = event.correlation_id
        written["event_log_created_at"] = event.created_at
    written["validation_errors"] = validate_paperops_paper_exit_path(written)
    if written["validation_errors"]:
        written["status"] = "invalid"
    output_path.write_text(
        json.dumps(written, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_record = {
        "schema_version": PAPEROPS_EXIT_PATH_SCHEMA_VERSION,
        "artifact_id": written.get("artifact_id"),
        "status": written.get("status"),
        "recorded_at": _now(),
        "alpaca_paper_exit_enabled": written.get("alpaca_paper_exit_enabled"),
        "settings_alpaca_paper_exit_enabled": written.get(
            "settings_alpaca_paper_exit_enabled"
        ),
        "runtime_alpaca_paper_exit_enabled": written.get(
            "runtime_alpaca_paper_exit_enabled"
        ),
        "execute_exit_requested": written.get("execute_exit_requested"),
        "eligible_exit_record_count": written.get("eligible_exit_record_count"),
        "paper_position_close_called_count": written.get(
            "paper_position_close_called_count"
        ),
        "paper_position_close_succeeded_count": written.get(
            "paper_position_close_succeeded_count"
        ),
        "live_endpoint_called_count": written.get("live_endpoint_called_count"),
        "validation_error_count": len(written.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, written


def paperops_paper_exit_path_public_status(
    settings: Settings | None = None,
) -> dict[str, Any]:
    artifact = read_latest_paperops_paper_exit_path(settings)
    if not artifact:
        return {
            "schema_version": PAPEROPS_EXIT_PATH_SCHEMA_VERSION,
            "status": "not_run",
            "stage": "PaperOps-4",
            "alpaca_paper_exit_enabled": False,
            "alpaca_paper_exit_effective": False,
            "settings_alpaca_paper_exit_enabled": False,
            "runtime_alpaca_paper_exit_enabled": False,
            "runtime_artifact_override_enabled": False,
            "paper_exit_runtime_enablement_status": "not_run",
            "paper_exit_runtime_enablement_validation_error_count": 0,
            "paper_exit_runtime_enablement_path_available": False,
            "paper_exit_runtime_enablement_idle_until_open_position": False,
            "paper_exit_path_available": False,
            "eligible_exit_record_count": 0,
            "paper_position_close_called_count": 0,
            "paper_position_close_succeeded_count": 0,
            "broker_write_called_count": 0,
            "broker_post_called_count": 0,
            "order_cancel_called_count": 0,
            "position_resize_called_count": 0,
            "live_endpoint_called_count": 0,
            "live_capital_enabled": False,
            "phase7_proof_credit_allowed": False,
            "secret_value_exposed": False,
            "raw_broker_payload_exposed": False,
            "broker_order_identifier_exposed": False,
            "boundary": PAPEROPS_EXIT_BOUNDARY,
        }
    return {
        "schema_version": artifact.get("schema_version"),
        "status": artifact.get("status"),
        "stage": artifact.get("stage"),
        "alpaca_paper_exit_enabled": artifact.get("alpaca_paper_exit_enabled"),
        "alpaca_paper_exit_effective": artifact.get("alpaca_paper_exit_effective"),
        "settings_alpaca_paper_exit_enabled": artifact.get(
            "settings_alpaca_paper_exit_enabled"
        ),
        "runtime_alpaca_paper_exit_enabled": artifact.get(
            "runtime_alpaca_paper_exit_enabled"
        ),
        "runtime_artifact_override_enabled": artifact.get(
            "runtime_artifact_override_enabled"
        ),
        "paper_exit_runtime_enablement_status": artifact.get(
            "paper_exit_runtime_enablement_status"
        ),
        "paper_exit_runtime_enablement_validation_error_count": artifact.get(
            "paper_exit_runtime_enablement_validation_error_count",
            0,
        ),
        "paper_exit_runtime_enablement_path_available": artifact.get(
            "paper_exit_runtime_enablement_path_available"
        ),
        "paper_exit_runtime_enablement_idle_until_open_position": artifact.get(
            "paper_exit_runtime_enablement_idle_until_open_position"
        ),
        "execute_exit_requested": artifact.get("execute_exit_requested"),
        "paper_exit_path_available": artifact.get("paper_exit_path_available"),
        "endpoint_classification": artifact.get("endpoint_classification"),
        "paper_endpoint_confirmed": artifact.get("paper_endpoint_confirmed"),
        "alpaca_api_key_configured": artifact.get("alpaca_api_key_configured"),
        "alpaca_api_secret_configured": artifact.get("alpaca_api_secret_configured"),
        "source_paperops_3_status": artifact.get("source_paperops_3_status"),
        "source_paperops_3_validation_error_count": artifact.get(
            "source_paperops_3_validation_error_count",
            0,
        ),
        "open_position_readback_count": artifact.get("open_position_readback_count", 0),
        "eligible_exit_record_count": artifact.get("eligible_exit_record_count", 0),
        "paperops_exit_event_log_prewrite_written": artifact.get(
            "paperops_exit_event_log_prewrite_written"
        ),
        "paper_position_close_called_count": artifact.get(
            "paper_position_close_called_count",
            0,
        ),
        "paper_position_close_succeeded_count": artifact.get(
            "paper_position_close_succeeded_count",
            0,
        ),
        "broker_write_called_count": artifact.get("broker_write_called_count", 0),
        "broker_post_called_count": artifact.get("broker_post_called_count", 0),
        "order_cancel_called_count": artifact.get("order_cancel_called_count", 0),
        "position_resize_called_count": artifact.get("position_resize_called_count", 0),
        "live_endpoint_called_count": artifact.get("live_endpoint_called_count", 0),
        "q7_lifecycle_mutation_performed": artifact.get("q7_lifecycle_mutation_performed"),
        "postmortem_due_marker_created_count": artifact.get(
            "postmortem_due_marker_created_count",
            0,
        ),
        "live_capital_enabled": artifact.get("live_capital_enabled"),
        "phase7_proof_credit_allowed": artifact.get("phase7_proof_credit_allowed"),
        "secret_value_exposed": artifact.get("secret_value_exposed"),
        "raw_broker_payload_exposed": artifact.get("raw_broker_payload_exposed"),
        "broker_order_identifier_exposed": artifact.get(
            "broker_order_identifier_exposed"
        ),
        "boundary": artifact.get("boundary", PAPEROPS_EXIT_BOUNDARY),
    }
