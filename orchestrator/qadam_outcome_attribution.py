"""Exact broker-order attribution. Missing fills or lineage remain unknown."""

from collections import defaultdict, deque
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping


def _number(value: Any) -> Decimal | None:
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def _time(value: Any) -> datetime | None:
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except ValueError:
        return None


def reconstruct_order_history(orders: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """FIFO reconstruction from provider order aggregates, never symbol-last-order.

    These are gross accounting estimates, not fee-adjusted investment evidence.
    Unmatched closes contaminate that inventory until a complete history is supplied.
    """
    queues: dict[tuple, deque] = defaultdict(deque)
    unresolved: set[tuple] = set()
    result = {}
    records = [dict(row) for row in orders if _time(row.get("filled_at"))]
    records.sort(key=lambda row: (_time(row["filled_at"]), str(row.get("order_id"))))
    seen = set()
    for row in records:
        order_id = str(row.get("order_id") or "")
        if not order_id or order_id in seen:
            continue
        seen.add(order_id)
        intent = str(row.get("position_intent") or "").lower()
        side = str(row.get("direction") or "").lower()
        short = intent in {"sell_to_open", "buy_to_close"}
        closing = intent in {"sell_to_close", "buy_to_close"} or (
            side == "sell" and intent != "sell_to_open"
        )
        key = (row.get("broker_account_fingerprint"), row.get("paper_epoch_id"),
               row.get("instrument"), short)
        qty = _number(row.get("filled_quantity"))
        price = _number(row.get("filled_avg_price"))
        if qty is None or qty <= 0 or price is None or price <= 0:
            unresolved.add(key)
            continue
        if not closing:
            if side not in {"buy", "sell"}:
                unresolved.add(key)
                continue
            queues[key].append({"order": row, "remaining": qty, "price": price})
            continue
        remaining = qty
        allocations = []
        pnl = Decimal(0)
        entry_notional = Decimal(0)
        while remaining > 0 and queues[key]:
            lot = queues[key][0]
            used = min(remaining, lot["remaining"])
            delta = used * (price - lot["price"]) * (-1 if short else 1)
            pnl += delta
            entry_notional += used * lot["price"]
            allocations.append({
                "entry_order_id": lot["order"]["order_id"],
                "entry_client_order_id": lot["order"].get("client_order_id"),
                "entry_broker_order_id_hash": lot["order"].get("broker_order_id_hash"),
                "opened_at": lot["order"]["filled_at"],
                "quantity": float(used), "gross_realized_pnl": float(delta),
            })
            remaining -= used
            lot["remaining"] -= used
            if lot["remaining"] == 0:
                queues[key].popleft()
        if remaining:
            unresolved.add(key)
        complete = remaining == 0 and key not in unresolved
        result[order_id] = {
            "close_order_id": order_id,
            "closed_at": row["filled_at"],
            "account_currency": row.get("account_currency", "USD"),
            "paper_epoch_id": row.get("paper_epoch_id"),
            "broker_account_fingerprint": row.get("broker_account_fingerprint"),
            "accounting_status": "gross_reconstructed" if complete else "missing_entry_history",
            "realized_pnl": float(pnl) if complete else None,
            "entry_notional": float(entry_notional) if complete else None,
            "gross_return": float(pnl / entry_notional) if complete and entry_notional else None,
            "net_return": None, "costs_measured": False,
            "measurement_source": "provider_filled_order_aggregate_fifo",
            "allocations": allocations,
            "eligible_for_promotion": False,
        }
    inventory = []
    for key, lots in queues.items():
        if not lots:
            continue
        inventory.append({
            "broker_account_fingerprint": key[0], "paper_epoch_id": key[1],
            "instrument": key[2], "short": key[3], "complete": key not in unresolved,
            "quantity": float(sum(lot["remaining"] for lot in lots)),
            "entry_orders": [{**lot["order"], "remaining_quantity": float(lot["remaining"])} for lot in lots],
        })
    return {"closed": result, "open": inventory}


def reconstruct_closed_orders(orders: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    return reconstruct_order_history(orders)["closed"]


def attributed_outcome(connection: Any, trade: Mapping[str, Any], accounting: dict | None) -> dict:
    payload = {**dict(trade), **(accounting or {})}
    payload.update({"attribution_version": 2, "attribution_status": "unresolved",
                    "decision_id": None, "strategy_id": "strategy-unclassified",
                    "strategy_version": "unversioned", "trading_lane": "discovery",
                    "independent_event_id": None, "eligible_for_promotion": False})
    if accounting is None:
        payload.update(realized_pnl=None, accounting_status="missing_entry_history",
                       costs_measured=False, net_return=None)
        return payload
    decisions = []
    for allocation in accounting.get("allocations", []):
        digest = allocation.get("entry_broker_order_id_hash") or sha256(
            str(allocation["entry_order_id"]).encode()
        ).hexdigest()
        matches = connection.execute(
            "SELECT DISTINCT d.decision_id,d.payload_json,o.trading_lane FROM canonical_orders o "
            "JOIN decision_transactions d ON d.decision_id=o.decision_id "
            "WHERE (o.broker_order_id_hash=? OR o.order_key=?)",
            (digest, allocation.get("entry_client_order_id")),
        ).fetchall()
        if len(matches) != 1:
            payload["attribution_status"] = "missing_or_ambiguous_entry_decision"
            return payload
        decisions.append(dict(matches[0]))
    identities = {row["decision_id"] for row in decisions}
    if len(identities) != 1:
        payload["attribution_status"] = "multiple_entry_decisions_require_fill_allocation"
        return payload
    decision = decisions[0]
    thesis = json.loads(decision["payload_json"])
    payload.update(
        decision_id=decision["decision_id"], strategy_id=thesis.get("strategy_id") or "strategy-unclassified",
        strategy_version=thesis.get("strategy_version") or "unversioned",
        trading_lane=decision["trading_lane"],
        independent_event_id=thesis.get("economic_signal_identity_id"),
        attribution_status="exact_entry_decision",
    )
    return payload


def cohort_metrics(outcomes: list[dict]) -> dict:
    """Cluster repeated closes of one economic event; never count missing as zero."""
    independent: dict[str, list[dict]] = defaultdict(list)
    for row in outcomes:
        if (row.get("attribution_status") == "exact_entry_decision"
            and row.get("independent_event_id") and row.get("costs_measured") is True
            and _number(row.get("net_return")) is not None
            and row.get("strategy_version") not in {None, "unversioned", "strategy-version-unclassified"}
            and row.get("broker_account_fingerprint") and row.get("paper_epoch_id")):
            key = str((row["broker_account_fingerprint"], row["paper_epoch_id"], row["independent_event_id"]))
            independent[key].append(row)
    # Partial exits are not independent trials. A weighted return is one observation.
    samples = []
    for rows in independent.values():
        weights = [_number(row.get("entry_notional")) for row in rows]
        if any(weight is None or weight <= 0 for weight in weights):
            continue
        total = sum(weights)
        value = sum(_number(row["net_return"]) * weight for row, weight in zip(rows, weights)) / total
        benchmarks = [_number(row.get("benchmark_net_return")) for row in rows]
        benchmark = (sum(v * w for v, w in zip(benchmarks, weights)) / total
                     if all(v is not None for v in benchmarks) else None)
        samples.append((value, benchmark))
    count = len(samples)
    matched = [value - benchmark for value, benchmark in samples if benchmark is not None]
    return {
        "raw_outcome_count": len(outcomes), "independent_outcome_count": count,
        "measured_event_count": count, "matched_benchmark_count": len(matched),
        "net_expectancy": float(sum(v for v, _ in samples) / count) if count else None,
        "no_trade_delta": float(sum(v for v, _ in samples) / count) if count else None,
        "benchmark_delta": float(sum(matched) / len(matched)) if matched else None,
        "units": "decimal_return_after_costs",
        "benchmark_comparison_available": count > 0 and len(matched) == count,
        "unresolved_outcome_count": sum(row.get("attribution_status") != "exact_entry_decision" for row in outcomes),
        "automatic_authority_mutation_allowed": False,
    }
