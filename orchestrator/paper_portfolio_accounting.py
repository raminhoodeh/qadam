"""Account-scoped equity history and signed position reconciliation (read-only)."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def finite_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _number(row: dict, *keys: str) -> float | None:
    return next((n for key in keys if (n := finite_number(row.get(key))) is not None), None)


def _time(value: Any) -> datetime | None:
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp
    except ValueError:
        return None


def scoped_account_history(rows: list[dict], reference: dict) -> list[dict]:
    cutoff = _time(reference.get("observed_at"))
    identity = ("paper_epoch_id", "broker_account_fingerprint", "account_currency", "record_origin")
    scoped = []
    for row in rows:
        if any(row.get(key) != reference.get(key) for key in identity):
            continue
        stamp = _time(row.get("observed_at"))
        if stamp is None or (cutoff and stamp > cutoff):
            continue
        scoped.append(row)
    return sorted(scoped, key=lambda row: _time(row["observed_at"]))


def equity_history_metrics(rows: list[dict], reference: dict) -> dict:
    equity = _number(reference, "equity", "equity_gbp", "current_balance_gbp")
    if equity is None or equity < 0:
        raise ValueError("account_equity_missing_or_invalid")
    history = scoped_account_history(rows, reference)
    baseline = _number(reference, "starting_balance", "starting_balance_gbp")
    if baseline is None:
        baseline = _number(history[0], "equity", "equity_gbp") if history else equity
    if baseline is None or baseline <= 0:
        raise ValueError("account_equity_baseline_missing_or_invalid")
    peak, maximum = baseline, 0.0
    # Persisted peaks/maxima survive retention and restart; actual historical
    # equity also repairs the old producer's current-only high-water mark.
    for row in [*history, reference]:
        value = _number(row, "equity", "equity_gbp", "current_balance_gbp")
        if value is None or value < 0:
            raise ValueError("account_history_equity_invalid")
        carried_peak = _number(row, "peak_equity", "peak_equity_gbp") or 0.0
        carried_max = _number(row, "max_drawdown_pct") or 0.0
        if not 0 <= carried_max <= 100:
            raise ValueError("account_history_drawdown_invalid")
        peak = max(peak, value, carried_peak)
        maximum = max(maximum, carried_max, (peak - value) / peak * 100)
    return {
        "version": 1,
        "peak_equity": round(peak, 2),
        "drawdown_pct": round((peak - equity) / peak * 100, 6),
        "max_drawdown_pct": round(maximum, 6),
        "history_observation_count": len(history),
        "history_start": history[0].get("observed_at") if history else reference.get("observed_at"),
        "scope": "same_paper_epoch_account_currency_and_origin",
    }


def signed_position_value(row: dict) -> float | None:
    value = _number(row, "market_value", "market_value_gbp", "current_value_gbp", "current_value", "risk_size_gbp")
    qty = _number(row, "qty", "quantity")
    direction = str(row.get("direction") or row.get("side") or "").lower()
    short = direction in {"short", "sell"} or (qty is not None and qty < 0)
    if value is None:
        price = _number(row, "current_price")
        if qty is None or price is None:
            return None
        value = qty * price
    if short:
        return -abs(value)
    return value


def cash_position_reconciliation(account: dict, positions: list[dict]) -> dict:
    equity = _number(account, "equity", "equity_gbp", "portfolio_value", "current_balance_gbp")
    cash = _number(account, "cash", "cash_gbp")
    values = [signed_position_value(row) for row in positions]
    if equity is None or cash is None or any(value is None for value in values):
        return {"status": "unavailable", "reason": "cash_equity_or_position_value_missing"}
    signed = sum(values)
    gross = sum(abs(value) for value in values)
    delta = round(equity - cash - signed, 2)
    # A disclosed small asynchronous mark difference is not missing broker truth.
    # Larger differences require refresh/review rather than invented balancing cash.
    tolerance = round(max(1.0, gross * 0.0001), 2)
    return {
        "status": "matched" if abs(delta) <= 0.01 else "within_mark_tolerance" if abs(delta) <= tolerance else "mismatch",
        "account_equity": equity,
        "cash": cash,
        "signed_position_value": round(signed, 2),
        "gross_position_value": round(gross, 2),
        "cash_plus_positions": round(cash + signed, 2),
        "unreconciled_difference": delta,
        "tolerance": tolerance,
        "reason": "Separate broker account and position reads; difference disclosed, not attributed to a proven cause.",
    }


def accounting_snapshot_health(rows: list[dict], reference: dict) -> dict:
    errors = []
    try:
        metrics = equity_history_metrics(rows, reference)
        for field, keys in (
            ("peak_equity", ("peak_equity", "peak_equity_gbp")),
            ("drawdown_pct", ("drawdown_pct",)),
            ("max_drawdown_pct", ("max_drawdown_pct",)),
        ):
            reported = _number(reference, *keys)
            if reported is None or abs(reported - metrics[field]) > 0.00001:
                errors.append(f"historical_{field}_mismatch")
        reconciliation = (reference.get("portfolio_accounting") or {}).get("cash_position_reconciliation") or {}
        if reconciliation.get("status") not in {"matched", "within_mark_tolerance"}:
            errors.append("cash_position_reconciliation_unconfirmed")
        else:
            equity = _number(reference, "equity", "equity_gbp", "current_balance_gbp")
            cash = _number(reference, "cash", "cash_gbp")
            signed = finite_number(reconciliation.get("signed_position_value"))
            gross = finite_number(reconciliation.get("gross_position_value"))
            if cash is None or signed is None or gross is None or gross < abs(signed) - 0.01:
                errors.append("cash_position_reconciliation_values_invalid")
            else:
                difference = round(equity - cash - signed, 2)
                tolerance = round(max(1.0, gross * 0.0001), 2)
                expected = {
                    "account_equity": equity, "cash": cash,
                    "cash_plus_positions": round(cash + signed, 2),
                    "unreconciled_difference": difference, "tolerance": tolerance,
                }
                status = "matched" if abs(difference) <= 0.01 else "within_mark_tolerance" if abs(difference) <= tolerance else "mismatch"
                if status != reconciliation.get("status") or any(
                    (value := finite_number(reconciliation.get(field))) is None
                    or abs(value - expected_value) > 0.00001
                    for field, expected_value in expected.items()
                ):
                    errors.append("cash_position_reconciliation_arithmetic_mismatch")
    except ValueError as exc:
        errors.append(str(exc))
    return {"healthy": not errors, "status": "passed" if not errors else "needs_attention", "errors": errors}


def portfolio_accounting_health(runtime: Path) -> dict:
    try:
        reference = json.loads((runtime / "alpaca_paper_mirror.json").read_text())["snapshot"]
        with (runtime / "paper_account_snapshots.jsonl").open() as handle:
            rows = [json.loads(line) for line in handle if line.strip()]
        return accounting_snapshot_health(rows, reference)
    except (OSError, ValueError, KeyError, TypeError):
        return {"healthy": False, "status": "unavailable", "errors": ["portfolio_accounting_evidence_unavailable"]}
