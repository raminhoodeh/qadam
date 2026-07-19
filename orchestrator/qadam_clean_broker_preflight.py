"""Read-only preflight for a new, empty US$100,000 Alpaca Paper account."""

from __future__ import annotations

from typing import Any, Callable

from orchestrator.config import Settings
from orchestrator.paper_account import AlpacaReadOnlyPaperMirror, alpaca_paper_mirror_status
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    runtime_dir,
    sha256_json,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_paper_epoch import (
    CLEAN_STARTING_EQUITY,
    broker_account_fingerprint,
    normalize_currency,
)

SCHEMA_VERSION = "qadam_clean_broker_account_preflight.v1"
ARTIFACT = "qadam_clean_broker_account_preflight.json"
TESTING_INVENTORY_ARTIFACT = "qadam_testing_epoch_inventory.json"
ALLOWED_EQUITY_TOLERANCE = 0.01


def _money(value: Any) -> float | None:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def build_clean_broker_preflight(
    *,
    settings: Settings | None = None,
    fetcher: Callable[[], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    active = settings or Settings.from_env()
    runtime = runtime_dir(active)
    store = AtomicArtifactStore(runtime)
    connection = alpaca_paper_mirror_status(active)
    inventory = read_json(runtime / TESTING_INVENTORY_ARTIFACT)
    errors: list[str] = []
    payload: dict[str, Any]
    try:
        fetch = fetcher or AlpacaReadOnlyPaperMirror(settings=active).fetch
        payload = fetch()
    except Exception as exc:  # noqa: BLE001 - preflight must materialize the blocker
        payload = {}
        errors.append(f"clean_broker_read_failed:{type(exc).__name__}")
    account = payload.get("account") if isinstance(payload.get("account"), dict) else {}
    positions = payload.get("positions") if isinstance(payload.get("positions"), list) else []
    orders = payload.get("orders") if isinstance(payload.get("orders"), list) else []
    fingerprint = broker_account_fingerprint(account)
    testing_fingerprint = str(inventory.get("broker_account_fingerprint") or "").strip() or None
    base_url = str(connection.get("base_url") or "")
    currency = normalize_currency(account.get("currency"))
    equity = _money(account.get("equity") or account.get("portfolio_value"))
    cash = _money(account.get("cash"))
    account_status = str(account.get("status") or "").strip().upper()
    clock = payload.get("clock") if isinstance(payload.get("clock"), dict) else {}
    history = (
        payload.get("portfolio_history")
        if isinstance(payload.get("portfolio_history"), dict)
        else {}
    )
    history_points = max(
        len(history.get("timestamp", [])) if isinstance(history.get("timestamp"), list) else 0,
        len(history.get("equity", [])) if isinstance(history.get("equity"), list) else 0,
    )
    is_paper_endpoint = "paper-api.alpaca.markets" in base_url.lower()
    is_new_account = bool(fingerprint and testing_fingerprint and fingerprint != testing_fingerprint)
    if connection.get("paper_mode") is not True or not is_paper_endpoint:
        errors.append("clean_broker_endpoint_is_not_alpaca_paper")
    if currency != "USD":
        errors.append("clean_broker_currency_is_not_usd")
    if equity is None or abs(equity - CLEAN_STARTING_EQUITY) > ALLOWED_EQUITY_TOLERANCE:
        errors.append("clean_broker_equity_is_not_100000_usd")
    if cash is None or abs(cash - CLEAN_STARTING_EQUITY) > ALLOWED_EQUITY_TOLERANCE:
        errors.append("clean_broker_cash_is_not_100000_usd")
    if account_status != "ACTIVE":
        errors.append("clean_broker_account_is_not_active")
    if positions:
        errors.append("clean_broker_has_open_positions")
    if orders:
        errors.append("clean_broker_has_order_history")
    if not fingerprint:
        errors.append("clean_broker_fingerprint_missing")
    if not testing_fingerprint:
        errors.append("testing_broker_fingerprint_missing")
    elif not is_new_account:
        errors.append("clean_broker_account_is_not_new")
    errors = unique_errors(errors)
    generated_at = now_iso()
    result = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_clean_broker_account_preflight",
        "generated_at": generated_at,
        "status": "passed_new_empty_paper_account" if not errors else "blocked",
        "preflight_passed": not errors,
        "provider": "alpaca",
        "account_mode": "paper" if is_paper_endpoint else "unknown_or_nonpaper",
        "paper_endpoint_verified": is_paper_endpoint,
        "provider_observed_at": generated_at,
        "provider_response_digest": sha256_json(payload) if payload else None,
        "account_status": account_status or "unknown",
        "account_currency": currency,
        "equity": equity,
        "cash": cash,
        "required_starting_equity": CLEAN_STARTING_EQUITY,
        "balance_tolerance": ALLOWED_EQUITY_TOLERANCE,
        "position_count": len(positions),
        "order_count": len(orders),
        "portfolio_history_point_count": history_points,
        "portfolio_history_checked": bool(history),
        "market_clock_checked": bool(clock),
        "broker_exception_count": 0 if payload else 1,
        "broker_account_fingerprint": fingerprint,
        "testing_account_fingerprint": testing_fingerprint,
        "account_fingerprint_is_new": is_new_account,
        "account_id_exported": False,
        "credentials_exported": False,
        "network_method": "GET_only",
        "readonly_paths": connection.get("readonly_paths", []),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "blocker_count": len(errors),
        "blockers": errors,
        "authority": authority_flags(),
        "boundary": (
            "Read-only new-account inspection. It cannot fund, clear, cancel, place, "
            "replace, or close an order and exports no credential or account identifier."
        ),
    }
    store.write_json(ARTIFACT, result)
    return result


def validate_clean_broker_preflight(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("preflight_passed") is True:
        if payload.get("paper_endpoint_verified") is not True:
            errors.append("clean_broker_passed_without_paper_endpoint")
        if payload.get("account_currency") != "USD":
            errors.append("clean_broker_passed_without_usd")
        if payload.get("account_status") != "ACTIVE":
            errors.append("clean_broker_passed_without_active_account")
        if int(payload.get("position_count") or 0) != 0:
            errors.append("clean_broker_passed_with_positions")
        if int(payload.get("order_count") or 0) != 0:
            errors.append("clean_broker_passed_with_orders")
        if payload.get("account_fingerprint_is_new") is not True:
            errors.append("clean_broker_passed_without_new_fingerprint")
        if not payload.get("provider_observed_at") or not payload.get(
            "provider_response_digest"
        ):
            errors.append("clean_broker_passed_without_provider_provenance")
    if payload.get("account_id_exported") is not False:
        errors.append("clean_broker_exported_account_id")
    if payload.get("credentials_exported") is not False:
        errors.append("clean_broker_exported_credentials")
    if int(payload.get("broker_write_count") or 0) != 0:
        errors.append("clean_broker_write_detected")
    errors.extend(validate_authority(payload.get("authority", {}), prefix="clean_broker"))
    return unique_errors(errors)


__all__ = [
    "ARTIFACT",
    "build_clean_broker_preflight",
    "validate_clean_broker_preflight",
]
