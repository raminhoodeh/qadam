"""Frozen matched market-only comparator, with no order authority."""

import math
from datetime import datetime

MARKET_BASELINE = {"version": "price-volatility.1", "minimum_absolute_move_pct": 0.05,
                   "volatility_required": True, "direction_rule": "sign_of_current_percent_move",
                   "capital_convention": "same_unit_notional_same_instrument_and_window",
                   "missing_data": "unavailable_not_zero", "paper_order_allowed": False}


def freeze_market_baseline(contract, evidence, instrument, *, decision_at):
    if (contract.get("market_baseline") or {}).get("version") != MARKET_BASELINE["version"]:
        return {"state": "not_preregistered", "available": False}
    value = (evidence.get("source_price_context") or {}).get("value") or {}
    rows = value.get("price_volume_records") or []
    row = next((row for row in rows if row.get("symbol") == instrument), {})
    move, vol = row.get("percent_move"), row.get("rolling_volatility_20d")
    try:
        at = datetime.fromisoformat(decision_at.replace("Z", "+00:00"))
        observed = datetime.fromisoformat(str(row.get("quote_observed_at") or row.get("observed_at")).replace("Z", "+00:00"))
        available = datetime.fromisoformat(str(row.get("available_at") or row.get("quote_observed_at")).replace("Z", "+00:00"))
        timely = bool(observed.tzinfo and available.tzinfo and at.tzinfo
                      and 0 <= (at-observed).total_seconds() <= 300 and observed <= available <= at)
    except (ValueError, TypeError, AttributeError):
        timely = False
    if (row.get("provider_backed") is not True
            or not timely or any(type(v) not in (int, float) or not math.isfinite(v) for v in (move, vol)) or vol <= 0):
        return {"state": "market_baseline_input_unavailable", "available": False,
                "contract": contract["market_baseline"]}
    direction = ("long" if move > 0 else "short") if abs(move) >= MARKET_BASELINE["minimum_absolute_move_pct"] else "abstain"
    return {"state": "frozen", "available": True, "direction": direction,
            "percent_move": move, "daily_volatility": vol, "contract": contract["market_baseline"],
            "observed_at": row.get("quote_observed_at") or row.get("observed_at"),
            "available_at": available.isoformat(), "provider": row.get("provider"),
            "paper_order_allowed": False}


def matched_baseline_outcome(frozen, market_return, cost_bps):
    if frozen.get("available") is not True:
        return {"market_baseline_comparison_available": False, "market_baseline_net_return": None}
    direction = frozen["direction"]
    net = 0.0 if direction == "abstain" else market_return * (1 if direction == "long" else -1) - cost_bps / 10000
    return {"market_baseline_comparison_available": True, "market_baseline_net_return": net,
            "market_baseline_costs_modelled": True, "market_baseline_same_event_window": True}
