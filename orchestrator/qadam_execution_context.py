"""Build typed decision-time market context from provider-backed read-only data."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_decision_transaction import ExecutionContext
from orchestrator.qadam_operator_ready_common import now_iso, read_json, runtime_dir

SCHEMA_VERSION = "qadam_execution_context_service.v1"
CONTEXT_ARTIFACT = "qadam_execution_contexts.jsonl"
SUMMARY_ARTIFACT = "qadam_execution_context_summary.json"
CHECK_ARTIFACT = "qadam_execution_context_checks.json"
MAX_CONTEXT_AGE_SECONDS = 120


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


def _context_id(symbol: str, observed_at: str, status: str) -> str:
    material = f"{symbol}:{observed_at}:{status}"
    return "execution-context:" + sha256(material.encode("utf-8")).hexdigest()[:24]


def _paperable_instruments(runtime) -> dict[str, bool]:
    registry = read_json(runtime / "qadam_instrument_role_registry.json")
    rows = registry.get("instruments") if isinstance(registry.get("instruments"), list) else []
    if rows:
        return {
            str(row.get("symbol") or "").upper(): (
                row.get("guarded_paper_route_confirmed") is True
            )
            for row in rows
            if isinstance(row, dict) and row.get("symbol")
        }
    universe = read_json(runtime / "qsase_trading_universe.json")
    return {
        str(row.get("symbol") or "").upper(): row.get("paper_route_available") is True
        for row in universe.get("instruments", [])
        if isinstance(row, dict) and row.get("symbol")
    }


def build_execution_contexts(
    settings: Settings | None = None,
    *,
    timestamp: datetime | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    current = timestamp or datetime.now(timezone.utc)
    packet = read_json(runtime / "market_context_packet.json")
    paperable = _paperable_instruments(runtime)
    recent = packet.get("recent_packets") if isinstance(packet.get("recent_packets"), list) else []
    records: dict[str, dict[str, Any]] = {}
    for current_packet in recent:
        if not isinstance(current_packet, dict):
            continue
        context = current_packet.get("price_volume_context")
        context = context if isinstance(context, dict) else {}
        for row in context.get("records", []):
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("symbol") or row.get("instrument_name") or "").upper()
            if symbol:
                records[symbol] = row

    contexts: list[dict[str, Any]] = []
    errors: list[str] = []
    for symbol in sorted(paperable):
        row = records.get(symbol)
        provider = str((row or {}).get("provider") or "registered_provider_unavailable")
        observed = _parse((row or {}).get("quote_observed_at")) or _parse(
            (row or {}).get("available_at")
        )
        observed_at = (observed or current).isoformat()
        expiry = (observed or current) + timedelta(seconds=MAX_CONTEXT_AGE_SECONDS)
        if not paperable[symbol]:
            status = "instrument_not_tradable"
        elif row is None or row.get("provider_backed") is not True:
            status = "provider_degraded"
        elif str(row.get("session_state") or "") != "regular_session":
            status = "market_closed"
        elif observed is None or (current - observed).total_seconds() > MAX_CONTEXT_AGE_SECONDS:
            status = "execution_context_expired"
        else:
            bid = row.get("bid")
            ask = row.get("ask")
            midpoint = row.get("midpoint")
            valid_quote = all(isinstance(value, (int, float)) and value > 0 for value in (bid, ask, midpoint))
            if not valid_quote or float(ask) < float(bid):
                status = "provider_degraded"
            else:
                spread_bps = (float(ask) - float(bid)) / float(midpoint) * 10_000
                status = "spread_adverse" if spread_bps > 100 else "quote_ready"
        bid_value = float(row["bid"]) if row and isinstance(row.get("bid"), (int, float)) and row["bid"] > 0 else None
        ask_value = float(row["ask"]) if row and isinstance(row.get("ask"), (int, float)) and row["ask"] > 0 else None
        midpoint_value = (
            float(row["midpoint"])
            if row and isinstance(row.get("midpoint"), (int, float)) and row["midpoint"] > 0
            else None
        )
        spread_bps_value = (
            round((ask_value - bid_value) / midpoint_value * 10_000, 6)
            if bid_value is not None and ask_value is not None and midpoint_value
            else None
        )
        try:
            context = ExecutionContext(
                context_id=_context_id(symbol, observed_at, status),
                instrument=symbol,
                provider=provider,
                status=status,
                observed_at=observed_at,
                expires_at=expiry.isoformat(),
                bid=bid_value,
                ask=ask_value,
                midpoint=midpoint_value,
                spread_bps=spread_bps_value,
                price=(
                    float(row["current_price"])
                    if row and isinstance(row.get("current_price"), (int, float))
                    else None
                ),
                volatility=(
                    float(row["rolling_volatility_20d"])
                    if row and isinstance(row.get("rolling_volatility_20d"), (int, float))
                    else None
                ),
                liquidity_proxy=(
                    float(row["average_daily_dollar_volume"])
                    if row and isinstance(row.get("average_daily_dollar_volume"), (int, float))
                    else None
                ),
                volume_or_flow=(
                    float(row["volume_ratio"])
                    if row and isinstance(row.get("volume_ratio"), (int, float))
                    else None
                ),
                provenance={
                    "artifact": "market_context_packet.json",
                    "provider_backed": bool((row or {}).get("provider_backed")),
                    "quote_actionable": bool((row or {}).get("quote_actionable")),
                    "source_generation_at": packet.get("generated_at"),
                    "paper_route_available": paperable[symbol],
                    "synthetic": False,
                },
            )
        except Exception as exc:  # noqa: BLE001 - schema failure is a contract defect
            errors.append(f"execution_context_schema:{symbol}:{type(exc).__name__}:{str(exc)[:200]}")
            continue
        contexts.append(context.model_dump(mode="json"))

    status_counts: dict[str, int] = {}
    for row in contexts:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
    summary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_execution_context_summary",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "instrument_count": len(contexts),
        "quote_ready_count": status_counts.get("quote_ready", 0),
        "status_counts": status_counts,
        "source_market_context_generated_at": packet.get("generated_at"),
        "maximum_context_age_seconds": MAX_CONTEXT_AGE_SECONDS,
        "synthetic_context_count": 0,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
    }
    return contexts, summary, errors


def build_and_write_execution_contexts(
    settings: Settings | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    contexts, summary, errors = build_execution_contexts(settings)
    store = AtomicArtifactStore(runtime)
    store.write_jsonl(CONTEXT_ARTIFACT, contexts)
    store.write_json(SUMMARY_ARTIFACT, summary)
    store.write_json(
        CHECK_ARTIFACT,
        {
            **summary,
            "artifact_type": "qadam_execution_context_checks",
            "validation_error_count": len(errors),
            "validation_errors": errors,
        },
    )
    return contexts, summary, errors


__all__ = ["build_and_write_execution_contexts", "build_execution_contexts"]
