"""Read-only executable price anchor immediately before an entry prewrite."""

import math
from datetime import datetime, timezone

from orchestrator.qadam_control_plane_store import ControlPlaneError

MAX_FUTURE_CLOCK_SKEW_SECONDS = 1.0


def reference_price(quote, *, symbol, side, now=None):
    now = now or datetime.now(timezone.utc)
    try:
        bid, ask = float(quote["bid"]), float(quote["ask"])
        observed = datetime.fromisoformat(quote["observed_at"].replace("Z", "+00:00"))
        age = (now-observed).total_seconds()
        valid = (quote.get("provider_backed") is True and quote.get("symbol") == symbol
                 and observed.tzinfo is not None and -MAX_FUTURE_CLOCK_SKEW_SECONDS <= age <= 60
                 and all(math.isfinite(p) and p > 0 for p in (bid, ask))
                 and bid <= ask and side in {"buy", "sell"})
    except (ValueError, TypeError, KeyError):
        valid = False
    if not valid:
        raise ControlPlaneError("fresh_entry_quote_unavailable")
    return ask if side == "buy" else bid


def fetch_entry_quote(settings, symbol):
    import httpx
    from orchestrator.alpaca_market_context_adapter import ALPACA_DATA_BASE_URL, SAFE_SYMBOL
    from orchestrator.secrets import secret_value
    if not SAFE_SYMBOL.fullmatch(symbol):
        raise ControlPlaneError("entry_symbol_invalid")
    try:
        response = httpx.get(f"{ALPACA_DATA_BASE_URL}/stocks/{symbol}/quotes/latest",
                            params={"feed": "iex"}, timeout=10, follow_redirects=False,
                            headers={"APCA-API-KEY-ID": secret_value("ALPACA_API_KEY", settings),
                                     "APCA-API-SECRET-KEY": secret_value("ALPACA_API_SECRET", settings)})
        response.raise_for_status()
        quote = response.json()["quote"]
        return {"symbol": symbol, "bid": quote["bp"], "ask": quote["ap"],
                "observed_at": quote["t"], "provider": "Alpaca Market Data IEX",
                "received_at": datetime.now(timezone.utc).isoformat(),
                "maximum_future_clock_skew_seconds": MAX_FUTURE_CLOCK_SKEW_SECONDS,
                "provider_backed": True}
    except Exception as exc:
        raise ControlPlaneError("fresh_entry_quote_unavailable") from exc


def pre_submit_quote_deferral(post, *, pass_started_at):
    """A known no-POST evidence hold is not an ambiguous execution failure."""
    if (post.get("broker_post_called_count") != 0 or post.get("alpaca_paper_post_called_count") != 0
            or post.get("precondition_failures") != ["immediate_pre_entry_reconciliation_and_prewrite"]):
        return None
    try:
        generated = datetime.fromisoformat(post["generated_at"].replace("Z", "+00:00"))
        if generated < pass_started_at:
            return None
    except (ValueError, TypeError, KeyError):
        return None
    failed = [row for row in post.get("precondition_records", []) if row.get("passed") is False]
    if len(failed) != 1 or failed[0].get("detail") not in {
        "fresh_entry_quote_unavailable", "current_quote_exceeds_approved_notional"}:
        return None
    return failed[0]["detail"]
