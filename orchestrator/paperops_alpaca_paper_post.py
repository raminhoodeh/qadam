"""PaperOps-2 explicit Alpaca paper POST gate.

This stage is the first real broker-write boundary for PaperOps, but it is
still paper-only and opt-in. The default builder evaluates readiness without
performing a network call. A POST can only happen when the caller passes the
explicit execution flag, Qadam is in paper mode, live capital is disabled, the
Alpaca endpoint is classified as paper, paper credentials are configured, and a
Q7 guarded submit record, PT-4 staged order, or first-week paper-only mandate
record is eligible.
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
from orchestrator.paper_account import ALPACA_PAPER_BASE_URL
from orchestrator.paperops_alpaca_paper_submit_enablement import (
    build_paperops_alpaca_paper_submit_enablement,
    read_latest_paperops_alpaca_paper_submit_enablement,
    validate_paperops_alpaca_paper_submit_enablement,
)
from orchestrator.paperops_auto_approval_staged_order import (
    read_latest_paperops_auto_approval_staged_order,
    validate_paperops_auto_approval_staged_order,
)
from orchestrator.paperops_first_week_paper_trade_mandate import (
    MANDATE_IDEMPOTENCY_NAMESPACE,
    MANDATE_ID_PREFIX,
    MANDATE_MIN_NOTIONAL_USD,
    build_first_week_paper_trade_mandate,
    read_latest_first_week_paper_trade_mandate,
    validate_first_week_paper_trade_mandate,
)
from orchestrator.phase7_guarded_alpaca_paper_submit import (
    build_phase7_guarded_alpaca_paper_submit_path,
    phase7_guarded_alpaca_submit_paths,
    validate_phase7_guarded_alpaca_paper_submit_path,
)
from orchestrator.secrets import secret_status, secret_value


PAPEROPS_ALPACA_POST_SCHEMA_VERSION = 1
PAPEROPS_ALPACA_POST_RUNTIME_ARTIFACT = "paperops_alpaca_paper_post.json"
PAPEROPS_ALPACA_POST_HISTORY = "paperops_alpaca_paper_post_history.jsonl"
PAPEROPS_ALPACA_POST_EVENT_LOG = "paperops_alpaca_paper_post_events.jsonl"
PAPEROPS_ALPACA_POST_SUBMISSION_LEDGER = (
    "paperops_alpaca_paper_post_submission_ledger.json"
)
PAPEROPS_ALPACA_POST_EVENT_TYPE = "paperops_alpaca_paper_post_recorded"
PAPEROPS_ALPACA_POST_PREWRITE_EVENT_TYPE = "paperops_alpaca_paper_post_prewrite"
PAPEROPS_ALPACA_POST_COMPONENT = "paperops_alpaca_paper_post"

PAPEROPS_ALPACA_POST_AUTHORITY_FALSE_FIELDS = (
    "execution_allowed",
    "paper_order_allowed",
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

PAPEROPS_ALPACA_POST_BOUNDARY = (
    "PaperOps-2 is the explicit Alpaca paper-only POST gate. It may call "
    "Alpaca /v2/orders only when QADAM_MODE=paper, live capital is disabled, "
    "QADAM_ALPACA_PAPER_SUBMIT_ENABLED=true or PT-5 runtime PaperOps "
    "enablement is recorded, the endpoint is classified as paper, paper API "
    "credentials are configured, a PT-4 staged paper order, Q7 guarded "
    "submit record, or first-week paper mandate record exists, the source "
    "Event Log prewrite exists, a pre-trade snapshot exists, the idempotency "
    "key is either phase7_demo_proof scoped or first-week mandate scoped, and "
    "the caller passes the explicit submit flag. It cannot call live "
    "endpoints, cannot use live credentials, cannot submit non-Q7/PaperOps "
    "orders, cannot submit prediction-market or crypto-perps orders, cannot "
    "expose secrets or raw broker payloads, cannot grant Phase 7 proof "
    "credit, and cannot enable live capital."
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

PAPEROPS_ALPACA_PAPER_PROXY_SYMBOLS = {
    "crude_oil": "USO",
    "defence": "ITA",
    "semiconductors": "SMH",
    "silver": "SLV",
}
PAPEROPS_ALPACA_PAPER_SETUP_PREFIXES = {
    "crude_oil": ("crude_oil_",),
    "defence": ("defence_",),
    "semiconductors": ("semiconductor_", "semiconductors_"),
    "silver": ("silver_",),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def paperops_alpaca_paper_post_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PAPEROPS_ALPACA_POST_RUNTIME_ARTIFACT,
        runtime / PAPEROPS_ALPACA_POST_HISTORY,
        runtime / PAPEROPS_ALPACA_POST_EVENT_LOG,
    )


def paperops_alpaca_paper_post_submission_ledger_path(
    settings: Settings | None = None,
) -> Path:
    return _runtime_dir(settings) / PAPEROPS_ALPACA_POST_SUBMISSION_LEDGER


def read_latest_paperops_alpaca_paper_post(
    settings: Settings | None = None,
) -> dict[str, Any]:
    output_path, _, _ = paperops_alpaca_paper_post_paths(settings)
    if not output_path.exists():
        return {}
    return _read_json(output_path)


def _submitted_candidate_keys_from_artifact(
    artifact: dict[str, Any],
) -> tuple[set[str], set[str]]:
    client_order_ids: set[str] = set()
    source_idempotency_keys: set[str] = set()
    if artifact.get("status") != "submitted_to_alpaca_paper":
        return client_order_ids, source_idempotency_keys
    for record in artifact.get("selected_post_records", []) or []:
        if not isinstance(record, dict):
            continue
        if record.get("alpaca_paper_post_succeeded") is not True:
            continue
        client_order_id = str(record.get("idempotency_key") or "").strip()
        source_key = str(record.get("source_idempotency_key") or "").strip()
        if client_order_id:
            client_order_ids.add(client_order_id)
        if source_key:
            source_idempotency_keys.add(source_key)
    return client_order_ids, source_idempotency_keys


def _submitted_candidate_keys_from_lifecycle_artifact(
    artifact: dict[str, Any],
) -> tuple[set[str], set[str]]:
    client_order_ids: set[str] = set()
    source_idempotency_keys: set[str] = set()
    for result in artifact.get("poll_result_records", []) or []:
        if not isinstance(result, dict):
            continue
        if result.get("order_get_succeeded") is not True:
            continue
        if not isinstance(result.get("order_readback"), dict):
            continue
        record = result.get("candidate")
        if not isinstance(record, dict):
            continue
        client_order_id = str(
            result["order_readback"].get("broker_client_order_id")
            or record.get("client_order_id")
            or record.get("idempotency_key")
            or ""
        ).strip()
        source_key = str(record.get("source_idempotency_key") or "").strip()
        if client_order_id:
            client_order_ids.add(client_order_id)
        if source_key:
            source_idempotency_keys.add(source_key)
    return client_order_ids, source_idempotency_keys


def _submission_ledger(settings: Settings) -> dict[str, Any]:
    path = paperops_alpaca_paper_post_submission_ledger_path(settings)
    payload = _read_json(path)
    current_client_ids, current_source_keys = _submitted_candidate_keys_from_artifact(
        read_latest_paperops_alpaca_paper_post(settings)
    )
    lifecycle_client_ids, lifecycle_source_keys = (
        _submitted_candidate_keys_from_lifecycle_artifact(
            _read_json(_runtime_dir(settings) / "paperops_paper_lifecycle_poller.json")
        )
    )
    client_ids = set(payload.get("submitted_client_order_ids", []) or [])
    source_keys = set(payload.get("submitted_source_idempotency_keys", []) or [])
    client_ids.update(current_client_ids)
    source_keys.update(current_source_keys)
    client_ids.update(lifecycle_client_ids)
    source_keys.update(lifecycle_source_keys)
    return {
        "schema_version": PAPEROPS_ALPACA_POST_SCHEMA_VERSION,
        "artifact_type": "paperops_alpaca_paper_post_submission_ledger",
        "artifact_id": "paperops:alpaca-paper-post:submission-ledger",
        "submitted_client_order_ids": sorted(client_ids),
        "submitted_source_idempotency_keys": sorted(source_keys),
    }


def _write_submission_ledger(
    artifact: dict[str, Any],
    settings: Settings,
) -> None:
    client_ids, source_keys = _submitted_candidate_keys_from_artifact(artifact)
    existing = _submission_ledger(settings)
    client_ids.update(existing.get("submitted_client_order_ids", []) or [])
    source_keys.update(existing.get("submitted_source_idempotency_keys", []) or [])
    if not client_ids and not source_keys:
        return
    path = paperops_alpaca_paper_post_submission_ledger_path(settings)
    path.write_text(
        json.dumps(
            {
                "schema_version": PAPEROPS_ALPACA_POST_SCHEMA_VERSION,
                "artifact_type": "paperops_alpaca_paper_post_submission_ledger",
                "artifact_id": "paperops:alpaca-paper-post:submission-ledger",
                "updated_at": _now(),
                "public_safe": True,
                "submitted_client_order_ids": sorted(client_ids),
                "submitted_source_idempotency_keys": sorted(source_keys),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


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


def _bool(value: Any) -> bool:
    return value is True or str(value).strip().lower() in {"1", "true", "yes", "on"}


def _quantity_string(value: Any) -> str:
    try:
        return f"{float(value or 0.0):.8f}"
    except (TypeError, ValueError):
        return "0.00000000"


def _endpoint_context(settings: Settings) -> dict[str, Any]:
    paper_flag = (secret_value("ALPACA_PAPER", settings) or "true").strip().lower()
    endpoint = (
        secret_value("ALPACA_ENDPOINT", settings)
        or secret_value("ALPACA_BASE_URL", settings)
        or ALPACA_PAPER_BASE_URL
    ).rstrip("/")
    endpoint_is_paper = (
        paper_flag != "false"
        and endpoint.startswith("https://paper-api.alpaca.markets")
        and "paper-api.alpaca.markets" in endpoint
    )
    key_ready = secret_status("ALPACA_API_KEY", settings)
    secret_ready = secret_status("ALPACA_API_SECRET", settings)
    return {
        "alpaca_api_key_configured": key_ready.configured,
        "alpaca_api_secret_configured": secret_ready.configured,
        "alpaca_paper_flag": paper_flag != "false",
        "endpoint_classification": (
            "alpaca_paper_endpoint" if endpoint_is_paper else "blocked_non_paper_endpoint"
        ),
        "paper_endpoint_confirmed": endpoint_is_paper,
        "base_url_exposed": False,
        "authorization_header_exposed": False,
        "secret_value_exposed": False,
    }


def _orders_url(settings: Settings) -> str:
    endpoint = (
        secret_value("ALPACA_ENDPOINT", settings)
        or secret_value("ALPACA_BASE_URL", settings)
        or ALPACA_PAPER_BASE_URL
    ).rstrip("/")
    if endpoint.endswith("/v2"):
        return f"{endpoint}/orders"
    return f"{endpoint}/v2/orders"


def _headers(settings: Settings) -> dict[str, str]:
    api_key = secret_value("ALPACA_API_KEY", settings)
    api_secret = secret_value("ALPACA_API_SECRET", settings)
    if not api_key or not api_secret:
        raise PermissionError("missing Alpaca paper credentials")
    return {
        "APCA-API-KEY-ID": api_key,
        "APCA-API-SECRET-KEY": api_secret,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Qadam/0.1 paperops-alpaca-paper-post",
    }


def _source_guarded_submit(settings: Settings) -> dict[str, Any]:
    submit_path, _, _ = phase7_guarded_alpaca_submit_paths(settings)
    if submit_path.exists():
        return _read_json(submit_path)
    return build_phase7_guarded_alpaca_paper_submit_path(settings=settings)


def _source_pt4_staged_order(settings: Settings) -> dict[str, Any]:
    return read_latest_paperops_auto_approval_staged_order(settings)


def _source_first_week_mandate(settings: Settings) -> dict[str, Any]:
    artifact = read_latest_first_week_paper_trade_mandate(settings)
    if artifact:
        return artifact
    return build_first_week_paper_trade_mandate(settings=settings)


def _source_submit_enablement(settings: Settings) -> dict[str, Any]:
    enablement = read_latest_paperops_alpaca_paper_submit_enablement(settings)
    if enablement:
        return enablement
    return build_paperops_alpaca_paper_submit_enablement(settings=settings)


def _runtime_submit_enabled(enablement: dict[str, Any]) -> bool:
    return (
        enablement.get("status") == "enabled_pending_explicit_submit"
        and enablement.get("paper_submit_runtime_enablement_enabled") is True
        and enablement.get("alpaca_paper_submit_effective") is True
        and enablement.get("paper_post_path_available") is True
        and enablement.get("explicit_submit_flag_required") is True
        and _int(enablement.get("broker_post_called_count")) == 0
        and _int(enablement.get("alpaca_post_called_count")) == 0
        and _int(enablement.get("live_endpoint_called_count")) == 0
        and not validate_paperops_alpaca_paper_submit_enablement(enablement)
    )


def _alpaca_symbol_for_record(record: dict[str, Any]) -> tuple[str, str]:
    request = record.get("submit_request_payload")
    if not isinstance(request, dict):
        request = {}
    explicit_symbol = str(
        record.get("symbol") or record.get("alpaca_symbol") or request.get("symbol") or ""
    ).upper()
    if explicit_symbol:
        return explicit_symbol, "source_record_symbol"
    instrument = _instrument_for_record(record)
    mapped = PAPEROPS_ALPACA_PAPER_PROXY_SYMBOLS.get(instrument, "")
    if mapped:
        return mapped, "paperops_proxy_symbol_map"
    return "", "missing_symbol_mapping"


def _instrument_for_record(record: dict[str, Any]) -> str:
    explicit = str(record.get("instrument") or "").strip().lower()
    if explicit:
        return explicit
    request = record.get("submit_request_payload")
    if isinstance(request, dict):
        request_instrument = str(request.get("instrument") or "").strip().lower()
        if request_instrument:
            return request_instrument
    for key in ("source_setup_record_id", "setup_id", "source_staged_order_artifact_id"):
        raw = str(record.get(key) or "").strip().lower()
        if not raw:
            continue
        tail = raw.rsplit(":", 1)[-1]
        for instrument, prefixes in PAPEROPS_ALPACA_PAPER_SETUP_PREFIXES.items():
            if any(tail.startswith(prefix) for prefix in prefixes):
                return instrument
    return ""


def _source_record_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    request = record.get("submit_request_payload", {})
    symbol, _ = _alpaca_symbol_for_record(record)
    if not isinstance(request, dict):
        request = {}
        errors.append("source_request_payload_missing")
    pre_trade_snapshot = record.get("pre_trade_snapshot")
    if record.get("status") != "submitted":
        errors.append("source_status_not_submitted")
    if record.get("selected_venue") != "alpaca_paper":
        errors.append("source_venue_not_alpaca_paper")
    if record.get("idempotency_namespace") != "phase7_demo_proof":
        errors.append("source_idempotency_namespace_not_phase7")
    if not str(record.get("idempotency_key") or "").startswith("q7-6-stage-"):
        errors.append("source_idempotency_key_not_phase7")
    if not str(record.get("event_log_prewrite_ref") or "").strip():
        errors.append("source_event_log_prewrite_ref_missing")
    if not isinstance(pre_trade_snapshot, dict) or not pre_trade_snapshot:
        errors.append("source_pre_trade_snapshot_missing")
    if request.get("endpoint_classification") != "alpaca_paper_endpoint":
        errors.append("source_endpoint_not_paper")
    if not symbol:
        errors.append("source_alpaca_symbol_missing")
    for key in (
        "authorization_header_included",
        "base_url_exposed",
        "raw_payload_exposed",
        "broker_identifier_exposed",
        "post_call_performed",
        "live_endpoint_allowed",
        "live_capital_enabled",
    ):
        if request.get(key) is not False:
            errors.append(f"source_request_forbidden:{key}")
    for key in (
        "broker_post_called",
        "alpaca_post_called",
        "external_broker_post_performed",
        "broker_write_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "prediction_market_write_allowed",
        "crypto_perps_write_allowed",
        "phase7_proof_credit_allowed",
        "manual_trade_level_override_allowed",
        "broker_order_identifier_exposed",
        "secret_value_exposed",
        "raw_payload_exposed",
        "authorization_header_exposed",
        "base_url_exposed",
    ):
        if record.get(key) is not False:
            errors.append(f"source_record_forbidden:{key}")
    return sorted(set(errors))


def _pt4_record_errors(record: dict[str, Any], *, source: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    pre_trade_snapshot = record.get("pre_trade_snapshot")
    symbol, _ = _alpaca_symbol_for_record(record)
    if source.get("status") != "staged_paper_order_ready":
        errors.append("pt4_source_status_not_ready")
    if source.get("ready_for_paperops2_submit") is not True:
        errors.append("pt4_source_not_ready_for_paperops2")
    if validate_paperops_auto_approval_staged_order(source):
        errors.append("pt4_source_validation_errors")
    if record.get("status") != "staged":
        errors.append("pt4_record_status_not_staged")
    if record.get("ready_for_paperops2_submit") is not True:
        errors.append("pt4_record_not_ready_for_paperops2")
    if record.get("selected_venue") != "alpaca_paper":
        errors.append("pt4_record_venue_not_alpaca_paper")
    if record.get("idempotency_namespace") != "phase7_demo_proof":
        errors.append("pt4_record_idempotency_namespace_not_phase7")
    if not str(record.get("idempotency_key") or "").startswith("q7-6-stage-"):
        errors.append("pt4_record_idempotency_key_not_phase7")
    if not str(record.get("event_log_prewrite_ref") or "").strip():
        errors.append("pt4_record_event_log_prewrite_ref_missing")
    if record.get("event_log_prewrite_written") is not True:
        errors.append("pt4_record_event_log_prewrite_not_written")
    if not isinstance(pre_trade_snapshot, dict) or not pre_trade_snapshot:
        errors.append("pt4_record_pre_trade_snapshot_missing")
    if not symbol:
        errors.append("pt4_record_alpaca_symbol_missing")
    if str(record.get("side") or "").lower() not in {"buy", "sell"}:
        errors.append("pt4_record_side_invalid")
    try:
        if float(record.get("quantity") or 0.0) <= 0:
            errors.append("pt4_record_quantity_not_positive")
    except (TypeError, ValueError):
        errors.append("pt4_record_quantity_invalid")
    if str(record.get("order_type") or "").lower() not in {"market", "limit"}:
        errors.append("pt4_record_order_type_invalid")
    if str(record.get("time_in_force") or "").lower() not in {"day", "gtc"}:
        errors.append("pt4_record_time_in_force_invalid")
    for key in (
        "paper_submit_allowed",
        "paper_order_submission_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "broker_write_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "proof_credit_allowed",
        "phase7_proof_credit_allowed",
        "manual_trade_level_override_allowed",
        "secret_value_exposed",
        "raw_payload_exposed",
    ):
        if record.get(key) is not False and key in record:
            errors.append(f"pt4_record_forbidden:{key}")
    return sorted(set(errors))


def _client_order_id(source_idempotency_key: str) -> str:
    if source_idempotency_key.startswith(MANDATE_ID_PREFIX):
        return source_idempotency_key[:48]
    digest = sha256(source_idempotency_key.encode("utf-8")).hexdigest()[:24]
    return f"q7-6-stage-{digest}"


def _request_preview(record: dict[str, Any]) -> dict[str, Any]:
    request = record.get("submit_request_payload", {})
    if not isinstance(request, dict):
        request = {}
    source_key = str(record.get("idempotency_key") or "")
    symbol, symbol_source = _alpaca_symbol_for_record(record)
    request_symbol = str(request.get("symbol") or "").upper()
    return {
        "request_type": "paperops_alpaca_paper_order_post",
        "method": "POST",
        "path": "/v2/orders",
        "symbol": request_symbol or symbol,
        "symbol_source": "source_request_symbol" if request_symbol else symbol_source,
        "instrument": _instrument_for_record(record) or None,
        "qty": str(request.get("qty") or ""),
        "side": str(request.get("side") or "").lower(),
        "type": str(request.get("type") or "market").lower(),
        "time_in_force": str(request.get("time_in_force") or "day").lower(),
        "client_order_id": _client_order_id(source_key),
        "source_idempotency_key": source_key,
        "idempotency_namespace": record.get("idempotency_namespace"),
        "base_url_exposed": False,
        "authorization_header_included": False,
        "raw_payload_exposed": False,
        "broker_identifier_exposed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
    }


def _pt4_request_preview(record: dict[str, Any]) -> dict[str, Any]:
    source_key = str(record.get("idempotency_key") or "")
    symbol, symbol_source = _alpaca_symbol_for_record(record)
    return {
        "request_type": "paperops_alpaca_paper_order_post",
        "method": "POST",
        "path": "/v2/orders",
        "symbol": symbol,
        "symbol_source": symbol_source,
        "instrument": record.get("instrument"),
        "qty": _quantity_string(record.get("quantity")),
        "side": str(record.get("side") or "").lower(),
        "type": str(record.get("order_type") or "market").lower(),
        "time_in_force": str(record.get("time_in_force") or "day").lower(),
        "client_order_id": _client_order_id(source_key),
        "source_idempotency_key": source_key,
        "idempotency_namespace": record.get("idempotency_namespace"),
        "base_url_exposed": False,
        "authorization_header_included": False,
        "raw_payload_exposed": False,
        "broker_identifier_exposed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
    }


def _mandate_record_errors(record: dict[str, Any], *, source: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    pre_trade_snapshot = record.get("pre_trade_snapshot")
    if source.get("status") not in {
        "active_ready_for_paper_orders",
        "active_daily_target_met",
    }:
        errors.append("mandate_source_status_not_active")
    if validate_first_week_paper_trade_mandate(source):
        errors.append("mandate_source_validation_errors")
    if record.get("status") != "ready_for_paperops2_submit":
        errors.append("mandate_record_not_ready_for_paperops2")
    if record.get("ready_for_paperops2_submit") is not True:
        errors.append("mandate_record_ready_flag_false")
    if record.get("selected_venue") != "alpaca_paper":
        errors.append("mandate_record_venue_not_alpaca_paper")
    if record.get("idempotency_namespace") != MANDATE_IDEMPOTENCY_NAMESPACE:
        errors.append("mandate_record_idempotency_namespace_invalid")
    if not str(record.get("idempotency_key") or "").startswith(MANDATE_ID_PREFIX):
        errors.append("mandate_record_idempotency_key_invalid")
    if not str(record.get("event_log_prewrite_ref") or "").strip():
        errors.append("mandate_record_event_log_prewrite_ref_missing")
    if record.get("event_log_prewrite_written") is not True:
        errors.append("mandate_record_event_log_prewrite_not_written")
    if not isinstance(pre_trade_snapshot, dict) or not pre_trade_snapshot:
        errors.append("mandate_record_pre_trade_snapshot_missing")
    if not str(record.get("alpaca_symbol") or record.get("instrument") or "").strip():
        errors.append("mandate_record_symbol_missing")
    if str(record.get("side") or "").lower() not in {"buy", "sell"}:
        errors.append("mandate_record_side_invalid")
    try:
        if float(record.get("notional_usd") or 0.0) < MANDATE_MIN_NOTIONAL_USD:
            errors.append("mandate_record_notional_below_minimum")
    except (TypeError, ValueError):
        errors.append("mandate_record_notional_invalid")
    if str(record.get("order_type") or "").lower() != "market":
        errors.append("mandate_record_order_type_invalid")
    if str(record.get("time_in_force") or "").lower() != "day":
        errors.append("mandate_record_time_in_force_invalid")
    for key in (
        "broker_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "proof_credit_allowed",
        "paper_growth_proof_credit_allowed",
        "secret_value_exposed",
        "raw_payload_exposed",
    ):
        if record.get(key) is not False and key in record:
            errors.append(f"mandate_record_forbidden:{key}")
    return sorted(set(errors))


def _mandate_request_preview(record: dict[str, Any]) -> dict[str, Any]:
    source_key = str(record.get("idempotency_key") or "")
    return {
        "request_type": "paperops_alpaca_paper_order_post",
        "method": "POST",
        "path": "/v2/orders",
        "symbol": str(record.get("alpaca_symbol") or record.get("instrument") or "").upper(),
        "symbol_source": "first_week_paper_trade_mandate",
        "instrument": record.get("instrument"),
        "qty": "",
        "notional": f"{float(record.get('notional_usd') or 0.0):.2f}",
        "notional_currency": "USD",
        "side": str(record.get("side") or "").lower(),
        "type": str(record.get("order_type") or "market").lower(),
        "time_in_force": str(record.get("time_in_force") or "day").lower(),
        "client_order_id": _client_order_id(source_key),
        "source_idempotency_key": source_key,
        "idempotency_namespace": record.get("idempotency_namespace"),
        "base_url_exposed": False,
        "authorization_header_included": False,
        "raw_payload_exposed": False,
        "broker_identifier_exposed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
    }


def _alpaca_post_body(preview: dict[str, Any]) -> dict[str, str]:
    body = {
        "symbol": str(preview.get("symbol") or ""),
        "side": str(preview.get("side") or ""),
        "type": str(preview.get("type") or ""),
        "time_in_force": str(preview.get("time_in_force") or ""),
        "client_order_id": str(preview.get("client_order_id") or ""),
    }
    if str(preview.get("notional") or "").strip():
        body["notional"] = str(preview.get("notional") or "")
    else:
        body["qty"] = str(preview.get("qty") or "")
    return body


def _source_record_to_submit_candidate(record: dict[str, Any]) -> dict[str, Any]:
    source_errors = _source_record_errors(record)
    preview = _request_preview(record)
    source_key = str(record.get("idempotency_key") or "")
    pre_trade_snapshot = record.get("pre_trade_snapshot")
    snapshot_fingerprint = (
        _fingerprint(pre_trade_snapshot) if isinstance(pre_trade_snapshot, dict) else None
    )
    return {
        "schema_version": PAPEROPS_ALPACA_POST_SCHEMA_VERSION,
        "record_type": "paperops_alpaca_paper_post_candidate",
        "source_family": "phase7_guarded_submit_record",
        "source_phase": "Q7",
        "source_submit_record_artifact_id": record.get("artifact_id"),
        "source_staged_order_artifact_id": record.get("source_staged_order_artifact_id"),
        "source_proof_order_id": record.get("source_proof_order_id"),
        "source_auto_approval_decision_id": record.get("source_auto_approval_decision_id"),
        "source_setup_record_id": record.get("source_setup_record_id"),
        "paperops_source_setup_record_id": record.get("paperops_source_setup_record_id"),
        "research_goal_id": record.get("research_goal_id"),
        "research_goal_lineage": deepcopy(record.get("research_goal_lineage") or {}),
        "candidate_identity": record.get("candidate_identity"),
        "signal_evidence_lineage_key": record.get("signal_evidence_lineage_key"),
        "source_signal_id": record.get("source_signal_id"),
        "source_signal_review_id": record.get("source_signal_review_id"),
        "source_signal_reviewed_at": record.get("source_signal_reviewed_at"),
        "source_signal_status": record.get("source_signal_status"),
        "setup_freshness_key": record.get("setup_freshness_key"),
        "source_idempotency_key": source_key,
        "idempotency_key": preview["client_order_id"],
        "idempotency_namespace": record.get("idempotency_namespace"),
        "source_event_log_prewrite_ref": record.get("event_log_prewrite_ref"),
        "source_pre_trade_snapshot_present": isinstance(pre_trade_snapshot, dict)
        and bool(pre_trade_snapshot),
        "source_pre_trade_snapshot_fingerprint": snapshot_fingerprint,
        "selected_venue": "alpaca_paper",
        "endpoint_classification": "alpaca_paper_endpoint",
        "instrument": _instrument_for_record(record) or None,
        "alpaca_symbol": preview["symbol"],
        "alpaca_symbol_source": preview["symbol_source"],
        "request_preview": preview,
        "request_fingerprint": _fingerprint(preview),
        "source_record_errors": source_errors,
        "eligible_for_paper_post": not source_errors,
        "status": "eligible" if not source_errors else "blocked_source_contract",
        "broker_post_called": False,
        "alpaca_paper_post_called": False,
        "alpaca_paper_post_succeeded": False,
        "raw_broker_payload_stored": False,
        "raw_broker_payload_exposed": False,
        "authorization_header_exposed": False,
        "base_url_exposed": False,
        "broker_order_identifier_exposed": False,
        "secret_value_exposed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "manual_trade_level_override_allowed": False,
    }


def _pt4_record_to_submit_candidate(
    record: dict[str, Any],
    *,
    source: dict[str, Any],
) -> dict[str, Any]:
    source_errors = _pt4_record_errors(record, source=source)
    preview = _pt4_request_preview(record)
    source_key = str(record.get("idempotency_key") or "")
    pre_trade_snapshot = record.get("pre_trade_snapshot")
    snapshot_fingerprint = (
        _fingerprint(pre_trade_snapshot) if isinstance(pre_trade_snapshot, dict) else None
    )
    return {
        "schema_version": PAPEROPS_ALPACA_POST_SCHEMA_VERSION,
        "record_type": "paperops_alpaca_paper_post_candidate",
        "source_family": "paperops_pt4_staged_order",
        "source_phase": "PT-4",
        "source_submit_record_artifact_id": None,
        "source_staged_order_artifact_id": record.get("artifact_id"),
        "source_pt4_artifact_id": source.get("artifact_id"),
        "source_proof_order_id": record.get("proof_order_id"),
        "source_auto_approval_decision_id": record.get("source_auto_approval_decision_id"),
        "source_setup_record_id": record.get("source_setup_record_id"),
        "source_idempotency_key": source_key,
        "idempotency_key": preview["client_order_id"],
        "idempotency_namespace": record.get("idempotency_namespace"),
        "source_event_log_prewrite_ref": record.get("event_log_prewrite_ref"),
        "source_pre_trade_snapshot_present": isinstance(pre_trade_snapshot, dict)
        and bool(pre_trade_snapshot),
        "source_pre_trade_snapshot_fingerprint": snapshot_fingerprint,
        "selected_venue": "alpaca_paper",
        "endpoint_classification": "alpaca_paper_endpoint",
        "instrument": record.get("instrument"),
        "alpaca_symbol": preview["symbol"],
        "alpaca_symbol_source": preview["symbol_source"],
        "request_preview": preview,
        "request_fingerprint": _fingerprint(preview),
        "source_record_errors": source_errors,
        "eligible_for_paper_post": not source_errors,
        "status": "eligible" if not source_errors else "blocked_source_contract",
        "broker_post_called": False,
        "alpaca_paper_post_called": False,
        "alpaca_paper_post_succeeded": False,
        "raw_broker_payload_stored": False,
        "raw_broker_payload_exposed": False,
        "authorization_header_exposed": False,
        "base_url_exposed": False,
        "broker_order_identifier_exposed": False,
        "secret_value_exposed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "manual_trade_level_override_allowed": False,
    }


def _mandate_record_to_submit_candidate(
    record: dict[str, Any],
    *,
    source: dict[str, Any],
) -> dict[str, Any]:
    source_errors = _mandate_record_errors(record, source=source)
    preview = _mandate_request_preview(record)
    source_key = str(record.get("idempotency_key") or "")
    pre_trade_snapshot = record.get("pre_trade_snapshot")
    snapshot_fingerprint = (
        _fingerprint(pre_trade_snapshot) if isinstance(pre_trade_snapshot, dict) else None
    )
    return {
        "schema_version": PAPEROPS_ALPACA_POST_SCHEMA_VERSION,
        "record_type": "paperops_alpaca_paper_post_candidate",
        "source_family": "paperops_first_week_paper_trade_mandate",
        "source_phase": "PaperOps-first-week",
        "source_submit_record_artifact_id": None,
        "source_staged_order_artifact_id": record.get("artifact_id"),
        "source_first_week_mandate_artifact_id": source.get("artifact_id"),
        "source_proof_order_id": None,
        "source_auto_approval_decision_id": record.get("source_auto_approval_decision_id"),
        "source_setup_record_id": record.get("source_setup_record_id"),
        "source_idempotency_key": source_key,
        "idempotency_key": preview["client_order_id"],
        "idempotency_namespace": record.get("idempotency_namespace"),
        "source_event_log_prewrite_ref": record.get("event_log_prewrite_ref"),
        "source_pre_trade_snapshot_present": isinstance(pre_trade_snapshot, dict)
        and bool(pre_trade_snapshot),
        "source_pre_trade_snapshot_fingerprint": snapshot_fingerprint,
        "selected_venue": "alpaca_paper",
        "endpoint_classification": "alpaca_paper_endpoint",
        "instrument": record.get("instrument"),
        "alpaca_symbol": preview["symbol"],
        "alpaca_symbol_source": preview["symbol_source"],
        "paper_trade_mandate_day_number": record.get("day_number"),
        "paper_trade_mandate_daily_slot": record.get("daily_slot"),
        "minimum_notional_usd": record.get("minimum_notional_usd"),
        "notional_usd": record.get("notional_usd"),
        "request_preview": preview,
        "request_fingerprint": _fingerprint(preview),
        "source_record_errors": source_errors,
        "eligible_for_paper_post": not source_errors,
        "status": "eligible" if not source_errors else "blocked_source_contract",
        "broker_post_called": False,
        "alpaca_paper_post_called": False,
        "alpaca_paper_post_succeeded": False,
        "raw_broker_payload_stored": False,
        "raw_broker_payload_exposed": False,
        "authorization_header_exposed": False,
        "base_url_exposed": False,
        "broker_order_identifier_exposed": False,
        "secret_value_exposed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "manual_trade_level_override_allowed": False,
    }


def _eligible_submit_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [candidate for candidate in candidates if candidate["eligible_for_paper_post"]]


def _q7_candidates(source_submit: dict[str, Any]) -> list[dict[str, Any]]:
    records = [
        record
        for record in source_submit.get("submit_records", []) or []
        if isinstance(record, dict)
    ]
    return [_source_record_to_submit_candidate(record) for record in records]


def _pt4_candidates(source_pt4: dict[str, Any]) -> list[dict[str, Any]]:
    records = [
        record
        for record in source_pt4.get("staged_order_records", []) or []
        if isinstance(record, dict)
    ]
    return [
        _pt4_record_to_submit_candidate(record, source=source_pt4)
        for record in records
    ]


def _mandate_candidates(source_mandate: dict[str, Any]) -> list[dict[str, Any]]:
    records = [
        record
        for record in source_mandate.get("mandate_records", []) or []
        if isinstance(record, dict)
        and record.get("ready_for_paperops2_submit") is True
    ]
    return [
        _mandate_record_to_submit_candidate(record, source=source_mandate)
        for record in records
    ]


def _sanitize_broker_success(response_payload: dict[str, Any], *, submitted_at: str) -> dict[str, Any]:
    broker_id = str(response_payload.get("id") or "")
    return {
        "receipt_type": "alpaca_paper_order_submit_receipt",
        "receipt_state": "submitted_to_alpaca_paper",
        "submitted_at": submitted_at,
        "broker_order_status": response_payload.get("status"),
        "broker_client_order_id": response_payload.get("client_order_id"),
        "broker_order_id_hash": sha256(broker_id.encode("utf-8")).hexdigest()
        if broker_id
        else None,
        "broker_order_identifier_exposed": False,
        "raw_broker_payload_stored": False,
        "raw_broker_payload_exposed": False,
        "authorization_header_exposed": False,
        "base_url_exposed": False,
        "secret_value_exposed": False,
    }


def _post_to_alpaca_paper(
    *,
    settings: Settings,
    request_preview: dict[str, Any],
    timeout_seconds: float = 12.0,
) -> dict[str, Any]:
    try:
        import httpx
    except ImportError as exc:
        return {
            "post_attempted": False,
            "post_succeeded": False,
            "failure_class": "missing_httpx",
            "failure_message_persisted": False,
            "sanitized_http_status": None,
            "receipt": None,
            "exception": exc,
        }

    submitted_at = _now()
    try:
        with httpx.Client(timeout=timeout_seconds, follow_redirects=False) as client:
            response = client.post(
                _orders_url(settings),
                headers=_headers(settings),
                json=_alpaca_post_body(request_preview),
            )
        status_code = response.status_code
        if status_code < 200 or status_code >= 300:
            return {
                "post_attempted": True,
                "post_succeeded": False,
                "failure_class": f"http_{status_code}",
                "failure_message_persisted": False,
                "sanitized_http_status": status_code,
                "receipt": None,
                "exception": None,
            }
        payload = response.json()
        if not isinstance(payload, dict):
            payload = {}
        return {
            "post_attempted": True,
            "post_succeeded": True,
            "failure_class": None,
            "failure_message_persisted": False,
            "sanitized_http_status": status_code,
            "receipt": _sanitize_broker_success(payload, submitted_at=submitted_at),
            "exception": None,
        }
    except Exception as exc:  # noqa: BLE001 - artifact must persist sanitized failure class only.
        return {
            "post_attempted": True,
            "post_succeeded": False,
            "failure_class": type(exc).__name__,
            "failure_message_persisted": False,
            "sanitized_http_status": None,
            "receipt": None,
            "exception": None,
        }


def _precondition_records(
    settings: Settings,
    endpoint: dict[str, Any],
    *,
    effective_submit_enabled: bool,
    runtime_submit_enabled: bool,
) -> list[dict[str, Any]]:
    return [
        {
            "key": "mode_is_paper",
            "passed": settings.mode == "paper",
            "detail": f"mode={settings.mode}",
        },
        {
            "key": "live_capital_disabled",
            "passed": settings.live_capital_enabled is False,
            "detail": f"live_capital_enabled={settings.live_capital_enabled}",
        },
        {
            "key": "paper_submit_flag_enabled",
            "passed": effective_submit_enabled is True,
            "detail": (
                "QADAM_ALPACA_PAPER_SUBMIT_ENABLED or "
                f"PT-5 runtime enablement={runtime_submit_enabled}"
            ),
        },
        {
            "key": "alpaca_endpoint_classified_paper",
            "passed": endpoint["paper_endpoint_confirmed"] is True,
            "detail": endpoint["endpoint_classification"],
        },
        {
            "key": "alpaca_paper_credentials_configured",
            "passed": endpoint["alpaca_api_key_configured"] is True
            and endpoint["alpaca_api_secret_configured"] is True,
            "detail": (
                f"key={endpoint['alpaca_api_key_configured']}; "
                f"secret={endpoint['alpaca_api_secret_configured']}"
            ),
        },
    ]


def _status(
    *,
    settings: Settings,
    endpoint: dict[str, Any],
    effective_submit_enabled: bool,
    eligible_count: int,
    duplicate_count: int,
    execute_post: bool,
    post_result: dict[str, Any] | None,
) -> str:
    if settings.mode != "paper":
        return "blocked_not_paper_mode"
    if settings.live_capital_enabled:
        return "blocked_live_capital_enabled"
    if not effective_submit_enabled:
        return "disabled_pending_enablement"
    if endpoint["paper_endpoint_confirmed"] is not True:
        return "blocked_non_paper_endpoint"
    if not endpoint["alpaca_api_key_configured"] or not endpoint["alpaca_api_secret_configured"]:
        return "blocked_missing_alpaca_paper_credentials"
    if eligible_count < 1:
        if duplicate_count >= 1:
            return "ready_no_fresh_eligible_order"
        return "ready_no_eligible_order"
    if not execute_post:
        return "ready_pending_explicit_execute"
    if post_result and post_result.get("post_succeeded") is True:
        return "submitted_to_alpaca_paper"
    return "broker_post_failed_sanitized"


def build_paperops_alpaca_paper_post(
    settings: Settings | None = None,
    *,
    execute_post: bool = False,
    event_log_path: str | Path | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    endpoint = _endpoint_context(settings)
    source_submit = _source_guarded_submit(settings)
    source_pt4 = _source_pt4_staged_order(settings)
    source_mandate = _source_first_week_mandate(settings)
    submit_enablement = _source_submit_enablement(settings)
    runtime_submit_enabled = _runtime_submit_enabled(submit_enablement)
    effective_submit_enabled = (
        settings.alpaca_paper_submit_enabled or runtime_submit_enabled
    )
    source_validation_errors = validate_phase7_guarded_alpaca_paper_submit_path(source_submit)
    source_pt4_validation_errors = validate_paperops_auto_approval_staged_order(source_pt4)
    source_mandate_validation_errors = validate_first_week_paper_trade_mandate(
        source_mandate
    )
    submit_enablement_validation_errors = (
        validate_paperops_alpaca_paper_submit_enablement(submit_enablement)
    )
    q7_candidates = _q7_candidates(source_submit)
    pt4_candidates = _pt4_candidates(source_pt4)
    mandate_candidates = _mandate_candidates(source_mandate)
    all_candidates = mandate_candidates + pt4_candidates + q7_candidates
    source_eligible_candidates = _eligible_submit_candidates(all_candidates)
    submitted_ledger = _submission_ledger(settings)
    submitted_client_order_ids = set(
        submitted_ledger.get("submitted_client_order_ids", []) or []
    )
    submitted_source_idempotency_keys = set(
        submitted_ledger.get("submitted_source_idempotency_keys", []) or []
    )
    for candidate in source_eligible_candidates:
        previously_submitted = (
            str(candidate.get("idempotency_key") or "") in submitted_client_order_ids
            or str(candidate.get("source_idempotency_key") or "")
            in submitted_source_idempotency_keys
        )
        candidate["previously_submitted_to_alpaca_paper"] = previously_submitted
        candidate["fresh_for_paper_post"] = not previously_submitted
        if previously_submitted:
            candidate["status"] = "blocked_duplicate_paper_submit"
    eligible_candidates = [
        candidate
        for candidate in source_eligible_candidates
        if candidate.get("fresh_for_paper_post") is True
    ]
    duplicate_submit_candidates = [
        candidate
        for candidate in source_eligible_candidates
        if candidate.get("previously_submitted_to_alpaca_paper") is True
    ]
    selected_candidate = eligible_candidates[0] if eligible_candidates else None
    preconditions = _precondition_records(
        settings,
        endpoint,
        effective_submit_enabled=effective_submit_enabled,
        runtime_submit_enabled=runtime_submit_enabled,
    )
    precondition_failures = [
        record["key"] for record in preconditions if record.get("passed") is not True
    ]
    post_path_available = not precondition_failures
    post_result: dict[str, Any] | None = None
    prewrite_entry_ref: str | None = None
    prewrite_event_count = 0

    if execute_post and post_path_available and selected_candidate is not None:
        event_path = Path(
            event_log_path or (_runtime_dir(settings) / PAPEROPS_ALPACA_POST_EVENT_LOG)
        )
        prewrite = EventLog(event_path, echo=False).write(
            PAPEROPS_ALPACA_POST_PREWRITE_EVENT_TYPE,
            PAPEROPS_ALPACA_POST_COMPONENT,
            payload={
                "status": "prewrite_before_alpaca_paper_post",
                "source_submit_record_artifact_id": selected_candidate.get(
                    "source_submit_record_artifact_id"
                ),
                "source_staged_order_artifact_id": selected_candidate.get(
                    "source_staged_order_artifact_id"
                ),
                "source_event_log_prewrite_ref": selected_candidate.get(
                    "source_event_log_prewrite_ref"
                ),
                "idempotency_namespace": selected_candidate.get("idempotency_namespace"),
                "source_idempotency_key": selected_candidate.get("source_idempotency_key"),
                "client_order_id": selected_candidate.get("idempotency_key"),
                "request_fingerprint": selected_candidate.get("request_fingerprint"),
                "endpoint_classification": endpoint["endpoint_classification"],
                "live_endpoint_allowed": False,
                "live_capital_enabled": False,
            },
        )
        prewrite_entry_ref = prewrite.correlation_id
        prewrite_event_count = 1
        post_result = _post_to_alpaca_paper(
            settings=settings,
            request_preview=selected_candidate["request_preview"],
        )
        selected_candidate = deepcopy(selected_candidate)
        selected_candidate["paperops_event_log_prewrite_written"] = True
        selected_candidate["paperops_event_log_prewrite_ref"] = prewrite_entry_ref
        selected_candidate["broker_post_called"] = post_result["post_attempted"]
        selected_candidate["alpaca_paper_post_called"] = post_result["post_attempted"]
        selected_candidate["alpaca_paper_post_succeeded"] = post_result["post_succeeded"]
        selected_candidate["sanitized_http_status"] = post_result["sanitized_http_status"]
        selected_candidate["broker_failure_class"] = post_result["failure_class"]
        selected_candidate["broker_failure_message_persisted"] = False
        selected_candidate["broker_receipt"] = post_result["receipt"]
        selected_candidate["status"] = (
            "submitted_to_alpaca_paper"
            if post_result["post_succeeded"]
            else "broker_post_failed_sanitized"
        )

    submitted_records = [selected_candidate] if selected_candidate is not None else []
    post_attempted = bool(post_result and post_result.get("post_attempted"))
    post_succeeded = bool(post_result and post_result.get("post_succeeded"))
    status = _status(
        settings=settings,
        endpoint=endpoint,
        effective_submit_enabled=effective_submit_enabled,
        eligible_count=len(eligible_candidates),
        duplicate_count=len(duplicate_submit_candidates),
        execute_post=execute_post,
        post_result=post_result,
    )
    pre_trade_snapshot_present_count = sum(
        1 for candidate in eligible_candidates if candidate["source_pre_trade_snapshot_present"]
    )
    source_event_log_prewrite_present_count = sum(
        1
        for candidate in eligible_candidates
        if str(candidate.get("source_event_log_prewrite_ref") or "").strip()
    )
    artifact = {
        "schema_version": PAPEROPS_ALPACA_POST_SCHEMA_VERSION,
        "artifact_type": "paperops_alpaca_paper_post",
        "artifact_id": "paperops:alpaca-paper-post:latest",
        "phase": "PaperOps",
        "stage": "PaperOps-2",
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
        "alpaca_paper_submit_enabled": effective_submit_enabled,
        "settings_alpaca_paper_submit_enabled": settings.alpaca_paper_submit_enabled,
        "runtime_alpaca_paper_submit_enabled": runtime_submit_enabled,
        "submit_enablement_status": submit_enablement.get("status", "missing"),
        "submit_enablement_artifact_id": submit_enablement.get("artifact_id"),
        "submit_enablement_validation_error_count": len(
            submit_enablement_validation_errors
        ),
        "submit_enablement_validation_errors": submit_enablement_validation_errors[:12],
        "submit_enablement_runtime_override_enabled": (
            submit_enablement.get("runtime_artifact_override_enabled") is True
        ),
        "submit_enablement_explicit_submit_flag_required": (
            submit_enablement.get("explicit_submit_flag_required") is True
        ),
        "live_capital_enabled": settings.live_capital_enabled,
        "execute_post_requested": execute_post,
        "explicit_submit_flag_required": True,
        "paper_post_path_available": post_path_available,
        "post_path_method": "POST",
        "post_path_template": "/v2/orders",
        "endpoint_classification": endpoint["endpoint_classification"],
        "paper_endpoint_confirmed": endpoint["paper_endpoint_confirmed"],
        "alpaca_paper_flag": endpoint["alpaca_paper_flag"],
        "alpaca_api_key_configured": endpoint["alpaca_api_key_configured"],
        "alpaca_api_secret_configured": endpoint["alpaca_api_secret_configured"],
        "precondition_records": preconditions,
        "precondition_failure_count": len(precondition_failures),
        "precondition_failures": precondition_failures,
        "source_guarded_submit_artifact_id": source_submit.get("artifact_id"),
        "source_guarded_submit_status": source_submit.get("status"),
        "source_guarded_submit_validation_error_count": len(source_validation_errors),
        "source_guarded_submit_validation_errors": source_validation_errors[:12],
        "source_guarded_submit_record_count": len(q7_candidates),
        "source_pt4_staged_order_artifact_id": source_pt4.get("artifact_id"),
        "source_pt4_staged_order_status": source_pt4.get("status"),
        "source_pt4_ready_for_paperops2_submit": (
            source_pt4.get("ready_for_paperops2_submit") is True
        ),
        "source_pt4_staged_order_count": len(pt4_candidates),
        "source_pt4_staged_order_validation_error_count": len(
            source_pt4_validation_errors
        ),
        "source_pt4_staged_order_validation_errors": source_pt4_validation_errors[:12],
        "source_first_week_mandate_artifact_id": source_mandate.get("artifact_id"),
        "source_first_week_mandate_status": source_mandate.get("status"),
        "source_first_week_mandate_active": source_mandate.get("active") is True,
        "source_first_week_mandate_day_number": source_mandate.get("day_number", 0),
        "source_first_week_mandate_daily_target_trade_count": source_mandate.get(
            "daily_target_trade_count",
            0,
        ),
        "source_first_week_mandate_minimum_notional_usd": source_mandate.get(
            "minimum_notional_usd",
            0,
        ),
        "source_first_week_mandate_daily_ready_submit_count": source_mandate.get(
            "daily_ready_submit_count",
            0,
        ),
        "source_first_week_mandate_daily_submitted_count": source_mandate.get(
            "daily_submitted_count",
            0,
        ),
        "source_first_week_mandate_validation_error_count": len(
            source_mandate_validation_errors
        ),
        "source_first_week_mandate_validation_errors": (
            source_mandate_validation_errors[:12]
        ),
        "source_first_week_mandate_candidate_count": len(mandate_candidates),
        "source_submit_record_count": len(all_candidates),
        "source_eligible_submit_record_count": len(source_eligible_candidates),
        "eligible_submit_record_count": len(eligible_candidates),
        "fresh_eligible_submit_record_count": len(eligible_candidates),
        "duplicate_submit_record_count": len(duplicate_submit_candidates),
        "submitted_client_order_id_count": len(submitted_client_order_ids),
        "submitted_source_idempotency_key_count": len(
            submitted_source_idempotency_keys
        ),
        "idempotency_ledger_active": True,
        "blocked_source_record_count": len(all_candidates) - len(eligible_candidates),
        "selected_submit_record_count": len(submitted_records),
        "selected_source_family": (
            selected_candidate.get("source_family") if selected_candidate else None
        ),
        "selected_source_phase": (
            selected_candidate.get("source_phase") if selected_candidate else None
        ),
        "source_event_log_prewrite_present_count": source_event_log_prewrite_present_count,
        "pre_trade_snapshot_present_count": pre_trade_snapshot_present_count,
        "paperops_event_log_prewrite_required": bool(execute_post and selected_candidate),
        "paperops_event_log_prewrite_written": prewrite_entry_ref is not None,
        "paperops_event_log_prewrite_ref": prewrite_entry_ref,
        "paperops_event_log_prewrite_count": prewrite_event_count,
        "post_candidates": all_candidates,
        "selected_post_records": submitted_records,
        "alpaca_paper_post_called_count": 1 if post_attempted else 0,
        "alpaca_paper_post_succeeded_count": 1 if post_succeeded else 0,
        "alpaca_paper_post_failed_count": 1 if post_attempted and not post_succeeded else 0,
        "broker_post_called_count": 1 if post_attempted else 0,
        "broker_submit_receipt_created_count": 1 if post_succeeded else 0,
        "unsafe_live_endpoint_called_count": 0,
        "live_endpoint_called_count": 0,
        "live_capital_enabled_count": 0,
        "manual_trade_level_override_count": 0,
        "prediction_market_write_allowed_count": 0,
        "crypto_perps_write_allowed_count": 0,
        "phase7_proof_credit_allowed_count": 0,
        "broker_order_identifier_exposed_count": 0,
        "secret_value_exposed_count": 0,
        "raw_broker_payload_exposed_count": 0,
        "authorization_header_exposed_count": 0,
        "base_url_exposed_count": 0,
        "execution_allowed": False,
        "paper_order_allowed": False,
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
        "raw_broker_payload_stored_count": 0,
        "recommended_next_stage": (
            "PaperOps-3 paper lifecycle poller"
            if status == "submitted_to_alpaca_paper"
            else "Wait for eligible PT-4/Q7 staged paper order and explicit paper-submit execution"
        ),
        "boundary": PAPEROPS_ALPACA_POST_BOUNDARY,
    }
    artifact["validation_errors"] = validate_paperops_alpaca_paper_post(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "invalid"
    return artifact


def _record_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    preview = record.get("request_preview", {})
    if not isinstance(preview, dict):
        errors.append("paperops_alpaca_record_request_preview_missing")
        preview = {}
    eligible = record.get("eligible_for_paper_post") is True
    if not eligible:
        if record.get("status") != "blocked_source_contract":
            errors.append("paperops_alpaca_blocked_record_status_invalid")
        if not isinstance(record.get("source_record_errors"), list):
            errors.append("paperops_alpaca_blocked_record_errors_missing")
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
                errors.append(f"paperops_alpaca_record_forbidden:{key}")
        for key in (
            "base_url_exposed",
            "authorization_header_included",
            "raw_payload_exposed",
            "broker_identifier_exposed",
            "live_endpoint_allowed",
            "live_capital_enabled",
        ):
            if preview.get(key) is not False:
                errors.append(f"paperops_alpaca_record_preview_forbidden:{key}")
        return errors
    if record.get("selected_venue") != "alpaca_paper":
        errors.append("paperops_alpaca_record_venue_invalid")
    if record.get("endpoint_classification") != "alpaca_paper_endpoint":
        errors.append("paperops_alpaca_record_endpoint_invalid")
    source_family = record.get("source_family")
    namespace = record.get("idempotency_namespace")
    source_key = str(record.get("source_idempotency_key") or "")
    client_key = str(record.get("idempotency_key") or "")
    if source_family not in {
        "phase7_guarded_submit_record",
        "paperops_pt4_staged_order",
        "paperops_first_week_paper_trade_mandate",
    }:
        errors.append("paperops_alpaca_record_source_family_invalid")
    if source_family == "paperops_first_week_paper_trade_mandate":
        if namespace != MANDATE_IDEMPOTENCY_NAMESPACE:
            errors.append("paperops_alpaca_record_namespace_invalid")
        if not source_key.startswith(MANDATE_ID_PREFIX):
            errors.append("paperops_alpaca_record_source_idempotency_invalid")
        if not client_key.startswith(MANDATE_ID_PREFIX):
            errors.append("paperops_alpaca_record_client_id_invalid")
        if float(record.get("notional_usd") or 0.0) < MANDATE_MIN_NOTIONAL_USD:
            errors.append("paperops_alpaca_record_mandate_notional_too_small")
        if float(preview.get("notional") or 0.0) < MANDATE_MIN_NOTIONAL_USD:
            errors.append("paperops_alpaca_record_preview_notional_too_small")
    else:
        if namespace != "phase7_demo_proof":
            errors.append("paperops_alpaca_record_namespace_invalid")
        if not source_key.startswith("q7-6-stage-"):
            errors.append("paperops_alpaca_record_source_idempotency_invalid")
        if not client_key.startswith("q7-6-stage-"):
            errors.append("paperops_alpaca_record_client_id_invalid")
    if not str(record.get("source_event_log_prewrite_ref") or "").strip():
        errors.append("paperops_alpaca_record_source_prewrite_missing")
    if record.get("source_pre_trade_snapshot_present") is not True:
        errors.append("paperops_alpaca_record_pre_trade_snapshot_missing")
    if not str(preview.get("symbol") or "").strip():
        errors.append("paperops_alpaca_record_symbol_missing")
    if record.get("request_fingerprint") != _fingerprint(preview):
        errors.append("paperops_alpaca_record_request_fingerprint_mismatch")
    for key in (
        "base_url_exposed",
        "authorization_header_included",
        "raw_payload_exposed",
        "broker_identifier_exposed",
        "live_endpoint_allowed",
        "live_capital_enabled",
    ):
        if preview.get(key) is not False:
            errors.append(f"paperops_alpaca_record_preview_forbidden:{key}")
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
            errors.append(f"paperops_alpaca_record_forbidden:{key}")
    if record.get("alpaca_paper_post_succeeded") is True:
        receipt = record.get("broker_receipt")
        if not isinstance(receipt, dict):
            errors.append("paperops_alpaca_record_success_receipt_missing")
            receipt = {}
        if not str(receipt.get("broker_order_id_hash") or "").strip():
            errors.append("paperops_alpaca_record_broker_order_hash_missing")
        for key in (
            "broker_order_identifier_exposed",
            "raw_broker_payload_stored",
            "raw_broker_payload_exposed",
            "authorization_header_exposed",
            "base_url_exposed",
            "secret_value_exposed",
        ):
            if receipt.get(key) is not False:
                errors.append(f"paperops_alpaca_record_receipt_forbidden:{key}")
    return errors


def validate_paperops_alpaca_paper_post(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "alpaca_api_key_configured",
        "alpaca_api_secret_configured",
        "alpaca_paper_post_called_count",
        "alpaca_paper_post_succeeded_count",
        "alpaca_paper_submit_enabled",
        "artifact_type",
        "base_url_exposed",
        "boundary",
        "broker_order_identifier_exposed",
        "broker_order_identifier_exposed_count",
        "broker_post_called_count",
        "crypto_perps_write_allowed",
        "endpoint_classification",
        "event_log_required",
        "event_log_written",
        "execute_post_requested",
        "explicit_submit_flag_required",
        "fresh_eligible_submit_record_count",
        "duplicate_submit_record_count",
        "idempotency_ledger_active",
        "live_capital_enabled",
        "live_endpoint_allowed",
        "mode",
        "paper_endpoint_confirmed",
        "paper_post_path_available",
        "paperops_event_log_prewrite_written",
        "phase",
        "phase7_proof_credit_allowed",
        "post_candidates",
        "prediction_market_write_allowed",
        "public_safe",
        "raw_broker_payload_exposed",
        "raw_broker_payload_stored",
        "recorded",
        "schema_version",
        "secret_value_exposed",
        "selected_post_records",
        "source_eligible_submit_record_count",
        "source_event_log_prewrite_present_count",
        "stage",
        "status",
        "submitted_client_order_id_count",
        "submitted_source_idempotency_key_count",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("paperops_alpaca_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PAPEROPS_ALPACA_POST_SCHEMA_VERSION:
        errors.append("paperops_alpaca_schema_version_mismatch")
    if artifact.get("artifact_type") != "paperops_alpaca_paper_post":
        errors.append("paperops_alpaca_artifact_type_mismatch")
    if artifact.get("phase") != "PaperOps" or artifact.get("stage") != "PaperOps-2":
        errors.append("paperops_alpaca_phase_stage_mismatch")
    if artifact.get("mode") != "paper":
        errors.append("paperops_alpaca_mode_not_paper")
    if artifact.get("public_safe") is not True:
        errors.append("paperops_alpaca_not_public_safe")
    for key in PAPEROPS_ALPACA_POST_AUTHORITY_FALSE_FIELDS:
        if artifact.get(key) is not False:
            errors.append(f"paperops_alpaca_forbidden:{key}")
    for key in (
        "unsafe_live_endpoint_called_count",
        "live_endpoint_called_count",
        "live_capital_enabled_count",
        "manual_trade_level_override_count",
        "prediction_market_write_allowed_count",
        "crypto_perps_write_allowed_count",
        "phase7_proof_credit_allowed_count",
        "broker_order_identifier_exposed_count",
        "secret_value_exposed_count",
        "raw_broker_payload_exposed_count",
        "authorization_header_exposed_count",
        "base_url_exposed_count",
        "raw_broker_payload_stored_count",
    ):
        if _int(artifact.get(key)) != 0:
            errors.append(f"paperops_alpaca_unsafe_counter_nonzero:{key}")
    if artifact.get("explicit_submit_flag_required") is not True:
        errors.append("paperops_alpaca_explicit_submit_flag_not_required")
    if artifact.get("endpoint_classification") != "alpaca_paper_endpoint":
        if _int(artifact.get("alpaca_paper_post_called_count")) != 0:
            errors.append("paperops_alpaca_post_called_without_paper_endpoint")
    if artifact.get("paper_endpoint_confirmed") is not True:
        if artifact.get("paper_post_path_available") is True:
            errors.append("paperops_alpaca_path_available_without_paper_endpoint")
    if artifact.get("alpaca_paper_submit_enabled") is not True:
        if _int(artifact.get("alpaca_paper_post_called_count")) != 0:
            errors.append("paperops_alpaca_post_called_without_flag")
        if artifact.get("status") not in {
            "disabled_pending_enablement",
            "blocked_not_paper_mode",
            "blocked_live_capital_enabled",
            "invalid",
        }:
            errors.append("paperops_alpaca_disabled_status_invalid")
    if (
        artifact.get("status") == "ready_no_fresh_eligible_order"
        and _int(artifact.get("duplicate_submit_record_count")) < 1
    ):
        errors.append("paperops_alpaca_no_fresh_without_duplicate")
    if artifact.get("execute_post_requested") is not True:
        if _int(artifact.get("alpaca_paper_post_called_count")) != 0:
            errors.append("paperops_alpaca_post_called_without_explicit_execute")
    if _int(artifact.get("alpaca_paper_post_called_count")):
        if artifact.get("execute_post_requested") is not True:
            errors.append("paperops_alpaca_called_without_execute")
        if artifact.get("alpaca_paper_submit_enabled") is not True:
            errors.append("paperops_alpaca_called_without_submit_flag")
        if artifact.get("paper_endpoint_confirmed") is not True:
            errors.append("paperops_alpaca_called_without_paper_endpoint")
        if artifact.get("paperops_event_log_prewrite_written") is not True:
            errors.append("paperops_alpaca_called_without_paperops_prewrite")
        if _int(artifact.get("source_event_log_prewrite_present_count")) < 1:
            errors.append("paperops_alpaca_called_without_source_prewrite")
        if _int(artifact.get("pre_trade_snapshot_present_count")) < 1:
            errors.append("paperops_alpaca_called_without_pre_trade_snapshot")
        if _int(artifact.get("eligible_submit_record_count")) < 1:
            errors.append("paperops_alpaca_called_without_eligible_order")
    if _int(artifact.get("alpaca_paper_post_succeeded_count")):
        if artifact.get("status") != "submitted_to_alpaca_paper":
            errors.append("paperops_alpaca_success_status_invalid")
        if _int(artifact.get("broker_submit_receipt_created_count")) < 1:
            errors.append("paperops_alpaca_success_without_receipt")
    if _int(artifact.get("alpaca_paper_post_succeeded_count")) > _int(
        artifact.get("alpaca_paper_post_called_count")
    ):
        errors.append("paperops_alpaca_success_gt_called")
    if artifact.get("idempotency_ledger_active") is not True:
        errors.append("paperops_alpaca_idempotency_ledger_inactive")
    records = artifact.get("post_candidates", [])
    selected = artifact.get("selected_post_records", [])
    if not isinstance(records, list):
        errors.append("paperops_alpaca_post_candidates_not_list")
        records = []
    if not isinstance(selected, list):
        errors.append("paperops_alpaca_selected_records_not_list")
        selected = []
    if artifact.get("source_submit_record_count") != len(records):
        errors.append("paperops_alpaca_source_record_count_mismatch")
    source_eligible_records = [
        record
        for record in records
        if isinstance(record, dict) and record.get("eligible_for_paper_post") is True
    ]
    fresh_eligible_records = [
        record
        for record in source_eligible_records
        if record.get("fresh_for_paper_post") is True
    ]
    duplicate_records = [
        record
        for record in source_eligible_records
        if record.get("previously_submitted_to_alpaca_paper") is True
    ]
    if artifact.get("source_eligible_submit_record_count") != len(source_eligible_records):
        errors.append("paperops_alpaca_source_eligible_count_mismatch")
    if artifact.get("eligible_submit_record_count") != len(fresh_eligible_records):
        errors.append("paperops_alpaca_eligible_count_mismatch")
    if artifact.get("fresh_eligible_submit_record_count") != len(fresh_eligible_records):
        errors.append("paperops_alpaca_fresh_eligible_count_mismatch")
    if artifact.get("duplicate_submit_record_count") != len(duplicate_records):
        errors.append("paperops_alpaca_duplicate_count_mismatch")
    for record in duplicate_records:
        if record.get("status") != "blocked_duplicate_paper_submit":
            errors.append("paperops_alpaca_duplicate_status_invalid")
        if record.get("fresh_for_paper_post") is not False:
            errors.append("paperops_alpaca_duplicate_marked_fresh")
    for record in records + selected:
        if isinstance(record, dict):
            errors.extend(_record_errors(record))
        else:
            errors.append("paperops_alpaca_record_invalid")
    if artifact.get("recorded") is True and artifact.get("event_log_written") is not True:
        errors.append("paperops_alpaca_event_log_missing")
    if artifact.get("event_log_written") is True and _int(artifact.get("event_log_event_count")) < 1:
        errors.append("paperops_alpaca_event_log_count_invalid")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "explicit Alpaca paper-only POST gate",
        "QADAM_ALPACA_PAPER_SUBMIT_ENABLED=true",
        "explicit submit flag",
        "cannot call live endpoints",
        "cannot expose secrets or raw broker payloads",
        "cannot enable live capital",
    ):
        if phrase not in boundary:
            errors.append("paperops_alpaca_boundary_weak")
            break
    if _contains_secret_shape(artifact):
        errors.append("paperops_alpaca_secret_shape_exposed")
    return sorted(set(errors))


def write_paperops_alpaca_paper_post(
    artifact: dict[str, Any],
    settings: Settings | None = None,
    *,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    settings = settings or Settings.from_env()
    output_path, history_path, default_event_path = paperops_alpaca_paper_post_paths(
        settings
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = deepcopy(artifact)
    written["recorded"] = True
    written["runtime_artifact_path"] = str(output_path)
    written["history_log_path"] = str(history_path)
    if record_event:
        event = EventLog(event_path, echo=False).write(
            PAPEROPS_ALPACA_POST_EVENT_TYPE,
            PAPEROPS_ALPACA_POST_COMPONENT,
            payload={
                "status": written["status"],
                "execute_post_requested": written["execute_post_requested"],
                "settings_alpaca_paper_submit_enabled": written[
                    "settings_alpaca_paper_submit_enabled"
                ],
                "runtime_alpaca_paper_submit_enabled": written[
                    "runtime_alpaca_paper_submit_enabled"
                ],
                "paper_post_path_available": written["paper_post_path_available"],
                "eligible_submit_record_count": written["eligible_submit_record_count"],
                "fresh_eligible_submit_record_count": written.get(
                    "fresh_eligible_submit_record_count"
                ),
                "duplicate_submit_record_count": written.get(
                    "duplicate_submit_record_count"
                ),
                "selected_source_family": written.get("selected_source_family"),
                "alpaca_paper_post_called_count": written[
                    "alpaca_paper_post_called_count"
                ],
                "alpaca_paper_post_succeeded_count": written[
                    "alpaca_paper_post_succeeded_count"
                ],
                "live_endpoint_called_count": written["live_endpoint_called_count"],
                "live_capital_enabled": written["live_capital_enabled"],
            },
        )
        written["event_log_written"] = True
        written["event_log_path"] = str(event_path)
        written["event_log_event_count"] = int(
            written.get("paperops_event_log_prewrite_count", 0) or 0
        ) + 1
        written["event_log_correlation_id"] = event.correlation_id
        written["event_log_created_at"] = event.created_at
    written["validation_errors"] = validate_paperops_alpaca_paper_post(written)
    if written["validation_errors"]:
        written["status"] = "invalid"
    output_path.write_text(
        json.dumps(written, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_submission_ledger(written, settings)
    history_record = {
        "schema_version": PAPEROPS_ALPACA_POST_SCHEMA_VERSION,
        "artifact_id": written.get("artifact_id"),
        "status": written.get("status"),
        "recorded_at": _now(),
        "alpaca_paper_submit_enabled": written.get("alpaca_paper_submit_enabled"),
        "settings_alpaca_paper_submit_enabled": written.get(
            "settings_alpaca_paper_submit_enabled"
        ),
        "runtime_alpaca_paper_submit_enabled": written.get(
            "runtime_alpaca_paper_submit_enabled"
        ),
        "execute_post_requested": written.get("execute_post_requested"),
        "paper_post_path_available": written.get("paper_post_path_available"),
        "eligible_submit_record_count": written.get("eligible_submit_record_count"),
        "fresh_eligible_submit_record_count": written.get(
            "fresh_eligible_submit_record_count"
        ),
        "duplicate_submit_record_count": written.get("duplicate_submit_record_count"),
        "selected_source_family": written.get("selected_source_family"),
        "alpaca_paper_post_called_count": written.get("alpaca_paper_post_called_count"),
        "alpaca_paper_post_succeeded_count": written.get(
            "alpaca_paper_post_succeeded_count"
        ),
        "live_endpoint_called_count": written.get("live_endpoint_called_count"),
        "live_capital_enabled": written.get("live_capital_enabled"),
        "validation_error_count": len(written.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, written


def paperops_alpaca_paper_post_public_status(
    settings: Settings | None = None,
) -> dict[str, Any]:
    artifact = read_latest_paperops_alpaca_paper_post(settings)
    if not artifact:
        return {
            "schema_version": PAPEROPS_ALPACA_POST_SCHEMA_VERSION,
            "status": "not_run",
            "stage": "PaperOps-2",
            "alpaca_paper_submit_enabled": False,
            "settings_alpaca_paper_submit_enabled": False,
            "runtime_alpaca_paper_submit_enabled": False,
            "submit_enablement_status": "not_run",
            "submit_enablement_runtime_override_enabled": False,
            "paper_post_path_available": False,
            "eligible_submit_record_count": 0,
            "selected_source_family": None,
            "source_pt4_staged_order_count": 0,
            "source_first_week_mandate_status": "not_run",
            "source_first_week_mandate_active": False,
            "source_first_week_mandate_daily_target_trade_count": 0,
            "source_first_week_mandate_minimum_notional_usd": 0,
            "source_first_week_mandate_daily_ready_submit_count": 0,
            "source_first_week_mandate_daily_submitted_count": 0,
            "alpaca_paper_post_called_count": 0,
            "alpaca_paper_post_succeeded_count": 0,
            "live_endpoint_called_count": 0,
            "live_capital_enabled": False,
            "secret_value_exposed": False,
            "raw_broker_payload_exposed": False,
            "broker_order_identifier_exposed": False,
            "boundary": PAPEROPS_ALPACA_POST_BOUNDARY,
        }
    return {
        "schema_version": artifact.get("schema_version"),
        "status": artifact.get("status"),
        "stage": artifact.get("stage"),
        "alpaca_paper_submit_enabled": artifact.get("alpaca_paper_submit_enabled"),
        "settings_alpaca_paper_submit_enabled": artifact.get(
            "settings_alpaca_paper_submit_enabled"
        ),
        "runtime_alpaca_paper_submit_enabled": artifact.get(
            "runtime_alpaca_paper_submit_enabled"
        ),
        "submit_enablement_status": artifact.get("submit_enablement_status"),
        "submit_enablement_runtime_override_enabled": artifact.get(
            "submit_enablement_runtime_override_enabled"
        ),
        "paper_post_path_available": artifact.get("paper_post_path_available"),
        "endpoint_classification": artifact.get("endpoint_classification"),
        "paper_endpoint_confirmed": artifact.get("paper_endpoint_confirmed"),
        "alpaca_api_key_configured": artifact.get("alpaca_api_key_configured"),
        "alpaca_api_secret_configured": artifact.get("alpaca_api_secret_configured"),
        "execute_post_requested": artifact.get("execute_post_requested"),
        "eligible_submit_record_count": artifact.get("eligible_submit_record_count", 0),
        "selected_submit_record_count": artifact.get("selected_submit_record_count", 0),
        "selected_source_family": artifact.get("selected_source_family"),
        "selected_source_phase": artifact.get("selected_source_phase"),
        "source_pt4_staged_order_count": artifact.get(
            "source_pt4_staged_order_count",
            0,
        ),
        "source_first_week_mandate_status": artifact.get(
            "source_first_week_mandate_status",
            "not_run",
        ),
        "source_first_week_mandate_active": artifact.get(
            "source_first_week_mandate_active",
            False,
        ),
        "source_first_week_mandate_day_number": artifact.get(
            "source_first_week_mandate_day_number",
            0,
        ),
        "source_first_week_mandate_daily_target_trade_count": artifact.get(
            "source_first_week_mandate_daily_target_trade_count",
            0,
        ),
        "source_first_week_mandate_minimum_notional_usd": artifact.get(
            "source_first_week_mandate_minimum_notional_usd",
            0,
        ),
        "source_first_week_mandate_daily_ready_submit_count": artifact.get(
            "source_first_week_mandate_daily_ready_submit_count",
            0,
        ),
        "source_first_week_mandate_daily_submitted_count": artifact.get(
            "source_first_week_mandate_daily_submitted_count",
            0,
        ),
        "source_first_week_mandate_candidate_count": artifact.get(
            "source_first_week_mandate_candidate_count",
            0,
        ),
        "source_event_log_prewrite_present_count": artifact.get(
            "source_event_log_prewrite_present_count",
            0,
        ),
        "pre_trade_snapshot_present_count": artifact.get(
            "pre_trade_snapshot_present_count",
            0,
        ),
        "paperops_event_log_prewrite_written": artifact.get(
            "paperops_event_log_prewrite_written"
        ),
        "alpaca_paper_post_called_count": artifact.get(
            "alpaca_paper_post_called_count",
            0,
        ),
        "alpaca_paper_post_succeeded_count": artifact.get(
            "alpaca_paper_post_succeeded_count",
            0,
        ),
        "live_endpoint_called_count": artifact.get("live_endpoint_called_count", 0),
        "live_capital_enabled": artifact.get("live_capital_enabled"),
        "secret_value_exposed": artifact.get("secret_value_exposed"),
        "raw_broker_payload_exposed": artifact.get("raw_broker_payload_exposed"),
        "broker_order_identifier_exposed": artifact.get(
            "broker_order_identifier_exposed"
        ),
        "boundary": artifact.get("boundary", PAPEROPS_ALPACA_POST_BOUNDARY),
    }
