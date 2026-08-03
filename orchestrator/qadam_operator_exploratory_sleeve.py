"""Operator-directed, proof-ineligible exploratory paper basket contract.

This contract is intentionally separate from Qadam's autonomous strategy and
edge-promotion lanes. It can describe a bounded paper basket after explicit
operator approval, but the only broker-write implementation remains the
canonical PaperOps Alpaca paper module.
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = "qadam_operator_exploratory_sleeve.v1"
ARTIFACT_TYPE = "qadam_operator_exploratory_sleeve"
IDEMPOTENCY_NAMESPACE = "operator_exploratory_sleeve"
CLIENT_ORDER_PREFIX = "q7-operator-sleeve-"
MAXIMUM_LEG_COUNT = 5
MAXIMUM_GROSS_NOTIONAL_USD = 5_000.0
MAXIMUM_SPREAD_BPS = 50.0
MAXIMUM_QUOTE_AGE_SECONDS = 120.0
MINIMUM_ESTIMATED_LEG_NOTIONAL_USD = 250.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(payload: object) -> str:
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode(
            "utf-8"
        )
    ).hexdigest()


def _parse_timestamp(value: object) -> datetime | None:
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


def _market_records(packet: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for recent in packet.get("recent_packets", []) or []:
        if not isinstance(recent, Mapping):
            continue
        context = recent.get("price_volume_context")
        if not isinstance(context, Mapping):
            continue
        for record in context.get("records", []) or []:
            if not isinstance(record, Mapping):
                continue
            symbol = str(record.get("symbol") or "").upper().strip()
            if symbol:
                records[symbol] = dict(record)
    return records


def _quote_age_seconds(record: Mapping[str, Any], *, generated_at: str) -> float:
    observed = _parse_timestamp(record.get("quote_observed_at"))
    generated = _parse_timestamp(generated_at)
    if observed is None or generated is None:
        return float("inf")
    return max(0.0, (generated - observed).total_seconds())


def _select_market_record(
    requested: Mapping[str, Any],
    records: Mapping[str, dict[str, Any]],
    *,
    generated_at: str,
) -> tuple[str, dict[str, Any], str | None]:
    symbols = [
        str(requested.get("requested_symbol") or "").upper().strip(),
        *[
            str(symbol).upper().strip()
            for symbol in requested.get("approved_execution_proxies", []) or []
        ],
    ]
    seen: set[str] = set()
    rejected: list[str] = []
    for index, symbol in enumerate(symbols):
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        record = records.get(symbol)
        if not record:
            rejected.append(f"{symbol}:market_record_missing")
            continue
        quote_age = _quote_age_seconds(record, generated_at=generated_at)
        spread = float(record.get("spread_bps") or 0.0)
        price = float(record.get("current_price") or 0.0)
        volatility = float(record.get("rolling_volatility_20d") or 0.0)
        checks = {
            "provider_backed": record.get("provider_backed") is True,
            "read_only_market_data": record.get("read_only_market_data") is True,
            "quote_actionable": record.get("quote_actionable") is True,
            "regular_session_quote": record.get("quote_state")
            == "fresh_regular_session_quote",
            "quote_fresh": quote_age <= MAXIMUM_QUOTE_AGE_SECONDS,
            "spread_within_limit": 0.0 < spread <= MAXIMUM_SPREAD_BPS,
            "price_positive": price > 0.0,
            "volatility_positive": volatility > 0.0,
        }
        failed = [key for key, passed in checks.items() if not passed]
        if failed:
            rejected.append(f"{symbol}:" + ",".join(failed))
            continue
        selected = dict(record)
        selected["quote_age_seconds_at_build"] = round(quote_age, 3)
        selected["execution_checks"] = checks
        proxy_reason = None
        if index > 0:
            proxy_reason = (
                f"{requested.get('requested_symbol')} was replaced by approved liquid "
                f"proxy {symbol}: " + "; ".join(rejected)
            )
        return symbol, selected, proxy_reason
    raise ValueError("no_eligible_execution_symbol:" + ";".join(rejected))


def _whole_share_quantity(allocation_usd: float, price: float, *, side: str) -> int:
    quantity = math.floor(allocation_usd / price)
    if side == "sell" and quantity < 1:
        quantity = 1
    if quantity < 1:
        raise ValueError("allocation_below_one_whole_share")
    return quantity


def _exit_levels(price: float, daily_volatility: float, *, side: str) -> tuple[float, float]:
    stop_distance = max(price * daily_volatility, 0.02)
    target_distance = stop_distance * 1.5
    if side == "buy":
        stop_price = price - stop_distance
        target_price = price + target_distance
    else:
        stop_price = price + stop_distance
        target_price = price - target_distance
    return round(stop_price, 2), round(target_price, 2)


def build_operator_exploratory_sleeve(
    *,
    request_id: str,
    requested_legs: Iterable[Mapping[str, Any]],
    market_context_packet: Mapping[str, Any],
    explicit_operator_approval: bool,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated = generated_at or _now()
    records = _market_records(market_context_packet)
    legs: list[dict[str, Any]] = []
    build_errors: list[str] = []
    for sequence, requested in enumerate(requested_legs, start=1):
        try:
            side = str(requested.get("side") or "buy").lower().strip()
            if side not in {"buy", "sell"}:
                raise ValueError("side_invalid")
            allocation = float(requested.get("allocation_usd") or 0.0)
            if allocation <= 0.0:
                raise ValueError("allocation_not_positive")
            symbol, market, proxy_reason = _select_market_record(
                requested,
                records,
                generated_at=generated,
            )
            price = float(market["current_price"])
            volatility = float(market["rolling_volatility_20d"])
            quantity = _whole_share_quantity(allocation, price, side=side)
            estimated_notional = round(quantity * price, 2)
            stop_price, target_price = _exit_levels(price, volatility, side=side)
            identity_material = {
                "request_id": request_id,
                "sequence": sequence,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "evidence_class": "operator_exploratory_unvalidated",
            }
            digest = _sha256(identity_material)[:24]
            client_order_id = f"{CLIENT_ORDER_PREFIX}{digest}"[:48]
            legs.append(
                {
                    "sequence": sequence,
                    "leg_id": f"operator-exploratory-leg:{digest}",
                    "requested_exposure": str(requested.get("exposure") or "").strip(),
                    "requested_symbol": str(requested.get("requested_symbol") or "")
                    .upper()
                    .strip(),
                    "execution_symbol": symbol,
                    "approved_proxy_used": proxy_reason is not None,
                    "proxy_reason": proxy_reason,
                    "side": side,
                    "quantity": quantity,
                    "allocation_usd": allocation,
                    "estimated_entry_price": price,
                    "estimated_notional_usd": estimated_notional,
                    "rolling_volatility_20d": volatility,
                    "stop_loss_price": stop_price,
                    "take_profit_price": target_price,
                    "maximum_holding_sessions": 5,
                    "thesis": str(requested.get("thesis") or "").strip(),
                    "source_context": list(requested.get("source_context", []) or []),
                    "idempotency_namespace": IDEMPOTENCY_NAMESPACE,
                    "source_idempotency_key": client_order_id,
                    "client_order_id": client_order_id,
                    "market_snapshot": {
                        "provider": market.get("provider"),
                        "provider_label": market.get("provider_label"),
                        "provider_backed": market.get("provider_backed"),
                        "quote_state": market.get("quote_state"),
                        "quote_observed_at": market.get("quote_observed_at"),
                        "quote_age_seconds_at_build": market.get(
                            "quote_age_seconds_at_build"
                        ),
                        "spread_bps": market.get("spread_bps"),
                        "current_price": price,
                        "rolling_volatility_20d": volatility,
                        "volume": market.get("volume"),
                        "volume_ratio": market.get("volume_ratio"),
                    },
                    "order_request": {
                        "symbol": symbol,
                        "qty": str(quantity),
                        "side": side,
                        "type": "market",
                        "time_in_force": "day",
                        "order_class": "bracket",
                        "take_profit": {"limit_price": f"{target_price:.2f}"},
                        "stop_loss": {"stop_price": f"{stop_price:.2f}"},
                        "client_order_id": client_order_id,
                    },
                    "evidence_class": "operator_exploratory_unvalidated",
                    "edge_id": None,
                    "strategy_id": None,
                    "proof_credit_allowed": False,
                    "validated_edge_credit_allowed": False,
                    "paper_proof_ledger_credit_allowed": False,
                }
            )
        except (TypeError, ValueError) as exc:
            build_errors.append(f"leg_{sequence}:{exc}")

    gross = round(sum(float(leg["estimated_notional_usd"]) for leg in legs), 2)
    sleeve_material = {
        "request_id": request_id,
        "leg_ids": [leg["leg_id"] for leg in legs],
        "gross_notional_usd": gross,
    }
    artifact = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ARTIFACT_TYPE,
        "generated_at": generated,
        "status": "ready_for_guarded_paper_submission",
        "sleeve_id": f"operator-exploratory-sleeve:{_sha256(sleeve_material)[:24]}",
        "request_id": request_id,
        "purpose": "operator_directed_paper_execution_and_lifecycle_observation",
        "explicit_operator_approval": explicit_operator_approval,
        "operator_approval_scope": "this_exact_one_time_basket_only",
        "evidence_class": "operator_exploratory_unvalidated",
        "idempotency_namespace": IDEMPOTENCY_NAMESPACE,
        "leg_count": len(legs),
        "gross_notional_usd": gross,
        "maximum_gross_notional_usd": MAXIMUM_GROSS_NOTIONAL_USD,
        "legs": legs,
        "build_errors": build_errors,
        "live_capital_enabled": False,
        "paper_only": True,
        "broker_route": "guarded_alpaca_paper_via_paperops",
        "manual_broker_call_allowed": False,
        "proof_credit_allowed": False,
        "validated_edge_credit_allowed": False,
        "paper_proof_ledger_credit_allowed": False,
        "strategy_promotion_allowed": False,
        "learning_use": "execution_and_counterfactual_context_only",
    }
    errors = validate_operator_exploratory_sleeve(artifact)
    artifact["validation_errors"] = errors
    if errors:
        artifact["status"] = "blocked"
    return artifact


def validate_operator_exploratory_sleeve(artifact: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if artifact.get("schema_version") != SCHEMA_VERSION:
        errors.append("operator_sleeve_schema_version_invalid")
    if artifact.get("artifact_type") != ARTIFACT_TYPE:
        errors.append("operator_sleeve_artifact_type_invalid")
    if artifact.get("explicit_operator_approval") is not True:
        errors.append("operator_sleeve_explicit_approval_missing")
    if artifact.get("operator_approval_scope") != "this_exact_one_time_basket_only":
        errors.append("operator_sleeve_approval_scope_invalid")
    if artifact.get("paper_only") is not True:
        errors.append("operator_sleeve_not_paper_only")
    if artifact.get("live_capital_enabled") is not False:
        errors.append("operator_sleeve_live_capital_enabled")
    if artifact.get("broker_route") != "guarded_alpaca_paper_via_paperops":
        errors.append("operator_sleeve_route_invalid")
    if artifact.get("manual_broker_call_allowed") is not False:
        errors.append("operator_sleeve_manual_broker_call_allowed")
    for field in (
        "proof_credit_allowed",
        "validated_edge_credit_allowed",
        "paper_proof_ledger_credit_allowed",
        "strategy_promotion_allowed",
    ):
        if artifact.get(field) is not False:
            errors.append(f"operator_sleeve_forbidden:{field}")
    legs = artifact.get("legs")
    if not isinstance(legs, list):
        errors.append("operator_sleeve_legs_not_list")
        legs = []
    if not 1 <= len(legs) <= MAXIMUM_LEG_COUNT:
        errors.append("operator_sleeve_leg_count_out_of_bounds")
    if artifact.get("leg_count") != len(legs):
        errors.append("operator_sleeve_leg_count_mismatch")
    gross = round(sum(float(leg.get("estimated_notional_usd") or 0.0) for leg in legs), 2)
    if float(artifact.get("gross_notional_usd") or 0.0) != gross:
        errors.append("operator_sleeve_gross_notional_mismatch")
    if gross > MAXIMUM_GROSS_NOTIONAL_USD:
        errors.append("operator_sleeve_gross_notional_above_limit")
    if artifact.get("build_errors"):
        errors.append("operator_sleeve_build_errors_present")
    symbols: set[str] = set()
    client_order_ids: set[str] = set()
    for index, leg in enumerate(legs, start=1):
        if not isinstance(leg, Mapping):
            errors.append(f"operator_sleeve_leg_{index}_invalid")
            continue
        symbol = str(leg.get("execution_symbol") or "").upper().strip()
        client_order_id = str(leg.get("client_order_id") or "").strip()
        if not symbol:
            errors.append(f"operator_sleeve_leg_{index}_symbol_missing")
        if symbol in symbols:
            errors.append(f"operator_sleeve_duplicate_symbol:{symbol}")
        symbols.add(symbol)
        if not client_order_id.startswith(CLIENT_ORDER_PREFIX):
            errors.append(f"operator_sleeve_leg_{index}_client_id_invalid")
        if client_order_id in client_order_ids:
            errors.append(f"operator_sleeve_duplicate_client_id:{client_order_id}")
        client_order_ids.add(client_order_id)
        if leg.get("idempotency_namespace") != IDEMPOTENCY_NAMESPACE:
            errors.append(f"operator_sleeve_leg_{index}_namespace_invalid")
        if leg.get("source_idempotency_key") != client_order_id:
            errors.append(f"operator_sleeve_leg_{index}_source_key_mismatch")
        if str(leg.get("side") or "") not in {"buy", "sell"}:
            errors.append(f"operator_sleeve_leg_{index}_side_invalid")
        if int(leg.get("quantity") or 0) <= 0:
            errors.append(f"operator_sleeve_leg_{index}_quantity_invalid")
        if float(leg.get("estimated_notional_usd") or 0.0) < MINIMUM_ESTIMATED_LEG_NOTIONAL_USD:
            errors.append(f"operator_sleeve_leg_{index}_notional_too_small")
        market = leg.get("market_snapshot")
        market = market if isinstance(market, Mapping) else {}
        if market.get("provider_backed") is not True:
            errors.append(f"operator_sleeve_leg_{index}_market_not_provider_backed")
        if market.get("quote_state") != "fresh_regular_session_quote":
            errors.append(f"operator_sleeve_leg_{index}_quote_not_regular_session")
        if float(market.get("quote_age_seconds_at_build") or float("inf")) > MAXIMUM_QUOTE_AGE_SECONDS:
            errors.append(f"operator_sleeve_leg_{index}_quote_stale")
        spread = float(market.get("spread_bps") or 0.0)
        if not 0.0 < spread <= MAXIMUM_SPREAD_BPS:
            errors.append(f"operator_sleeve_leg_{index}_spread_invalid")
        request = leg.get("order_request")
        request = request if isinstance(request, Mapping) else {}
        if request.get("symbol") != symbol:
            errors.append(f"operator_sleeve_leg_{index}_request_symbol_mismatch")
        if request.get("client_order_id") != client_order_id:
            errors.append(f"operator_sleeve_leg_{index}_request_client_id_mismatch")
        if request.get("type") != "market" or request.get("time_in_force") != "day":
            errors.append(f"operator_sleeve_leg_{index}_order_contract_invalid")
        if request.get("order_class") != "bracket":
            errors.append(f"operator_sleeve_leg_{index}_bracket_missing")
        if not isinstance(request.get("take_profit"), Mapping):
            errors.append(f"operator_sleeve_leg_{index}_take_profit_missing")
        if not isinstance(request.get("stop_loss"), Mapping):
            errors.append(f"operator_sleeve_leg_{index}_stop_loss_missing")
        for field in (
            "proof_credit_allowed",
            "validated_edge_credit_allowed",
            "paper_proof_ledger_credit_allowed",
        ):
            if leg.get(field) is not False:
                errors.append(f"operator_sleeve_leg_{index}_forbidden:{field}")
    return sorted(set(errors))


__all__ = [
    "ARTIFACT_TYPE",
    "CLIENT_ORDER_PREFIX",
    "IDEMPOTENCY_NAMESPACE",
    "MAXIMUM_GROSS_NOTIONAL_USD",
    "SCHEMA_VERSION",
    "build_operator_exploratory_sleeve",
    "validate_operator_exploratory_sleeve",
]
