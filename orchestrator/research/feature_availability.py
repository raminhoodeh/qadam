"""Explain feature production separately from catalogue/provider health."""

from datetime import datetime, timezone
import math


def feature_availability(market_context, symbols, *, now=None):
    now = now or datetime.now(timezone.utc)
    records = {str(row.get("symbol")): row
               for packet in (market_context or {}).get("recent_packets", [])
               if packet.get("packet_role") == "universal_current_market_context"
               for row in (packet.get("price_volume_context") or {}).get("records", [])}
    contracts = {"price": ("current_price", "quote"), "spread": ("spread_bps", "quote"),
                 "liquidity": ("average_daily_dollar_volume", "history"),
                 "volatility": ("rolling_volatility_20d", "history")}
    output = []
    for symbol in sorted(set(symbols)):
        row = records.get(symbol, {})
        fields = {}
        for name, (field, timing) in contracts.items():
            value = row.get(field)
            numeric = type(value) in (int, float) and math.isfinite(value) and (value >= 0 if name == "spread" else value > 0)
            observed = row.get("quote_observed_at") if timing == "quote" else row.get("bars_observed_at") or row.get("observed_at")
            try:
                at = datetime.fromisoformat(str(observed).replace("Z", "+00:00"))
                age = (now-at).total_seconds()
                fresh = at.tzinfo is not None and 0 <= age <= (300 if timing == "quote" else 4*86400)
            except (ValueError, TypeError):
                fresh = False
            produced = numeric and row.get("provider_backed") is True
            fields[name] = {"state": "available" if produced and fresh else "stale" if produced else "collection_or_feature_production_missing",
                            "producer": "alpaca_market_context_adapter.fetch_alpaca_market_context",
                            "provider": "Alpaca Market Data IEX", "field": field, "observed_at": observed,
                            "available_at": row.get("available_at"), "entitlement": "existing_IEX_access",
                            "freshness_limit_seconds": 300 if timing == "quote" else 4*86400,
                            "fallback": "hold_this_playbook_not_other_strategies",
                            "available_timestamp_missing": not bool(row.get("available_at"))}
        output.append({"symbol": symbol, "features": fields,
                       "causal_trigger": {"producer": "qadam_trigger_factory", "state": "requires_instrument_relevant_typed_trigger_not_source_health"},
                       "direction": {"producer": "qadam_direction_resolution", "state": "requires_signed_current_resolution"},
                       "unsupported_optional_features": ["provider_features_without_current_entitlement"],
                       "feature_health_is_not_entry_authority": True})
    return output
