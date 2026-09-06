"""Exact broker-order attribution. Missing fills or lineage remain unknown."""

from collections import defaultdict, deque
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping

from orchestrator.contracts.costs import cost_evidence


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
                "entry_notional": float(used * lot["price"]),
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
    attributed_lots = []
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
            attributed_lots.append({**allocation, "attribution_status": "missing_or_ambiguous_entry_decision"})
            continue
        decisions.append(dict(matches[0]))
        decision = dict(matches[0])
        thesis = json.loads(decision["payload_json"])
        lot = {
            **accounting, **allocation, "allocations": [allocation],
            "decision_id": decision["decision_id"],
            "strategy_id": thesis.get("strategy_id") or "strategy-unclassified",
            "strategy_version": thesis.get("strategy_version") or "unversioned",
            "trading_lane": decision["trading_lane"],
            "independent_event_id": thesis.get("economic_signal_identity_id"),
            "attribution_status": "exact_entry_decision", "eligible_for_promotion": False,
            "realized_pnl": allocation.get("gross_realized_pnl"),
            "outcome_lot_id": sha256(str((trade.get("trade_id"), digest, decision["decision_id"])).encode()).hexdigest(),
        }
        _apply_registered_paper_cost(connection, lot, thesis)
        attributed_lots.append(lot)
    payload["attributed_lots"] = attributed_lots
    identities = {row["decision_id"] for row in decisions}
    if len(decisions) != len(accounting.get("allocations", [])):
        return payload
    if len(identities) != 1:
        payload["attribution_status"] = "exact_entry_allocations" if attributed_lots else "missing_entry_history"
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
    _apply_registered_paper_cost(connection, payload, thesis)
    return payload


def _apply_registered_paper_cost(connection: Any, payload: dict, thesis: dict) -> None:
    """Use only a cost assumption registered before the actual decision and fill."""
    payload.update(costs_measured=False, net_return=None,
                   cost_basis="unavailable", benchmark_net_return=None,
                   benchmark_comparison_available=False,
                   benchmark_unavailable_reason="no_provider_matched_fill_window_benchmark")
    version = thesis.get("strategy_version")
    decision_at = _time(thesis.get("created_at"))
    opened = [_time(row.get("opened_at")) for row in payload.get("allocations", [])]
    if not version or not decision_at or not opened or any(stamp is None for stamp in opened):
        return
    registration = connection.execute(
        "SELECT payload_json,created_at FROM operating_events WHERE aggregate_type='strategy_version' "
        "AND aggregate_id=? AND event_type='strategy_definition_registered' ORDER BY created_at LIMIT 1",
        (version,),
    ).fetchone()
    if not registration:
        return
    registered = _time(registration["created_at"])
    if registered is None or registered > min(decision_at, *opened):
        return
    contract = json.loads(registration["payload_json"]).get("evaluation_contract") or {}
    cost = _number(contract.get("cost_bps"))
    notional, pnl = _number(payload.get("entry_notional")), _number(payload.get("realized_pnl"))
    if (payload.get("accounting_status") != "gross_reconstructed" or contract.get("version") != "matched-forward.1"
        or cost is None or cost < 0 or notional is None or notional <= 0 or pnl is None):
        return
    payload.update(
        net_return=float(pnl / notional - cost / Decimal(10000)),
        cost_bps=float(cost), cost_model_version=contract["version"], cost_basis="modelled",
        costs_are_modelled_not_live_execution_costs=True,
        cost_assumption_registered_at=registration["created_at"],
        cost_application="gross_paper_fills_minus_registered_cost_allowance",
        cost_limitation="Conservative allowance may overlap fill effects; not measured fees or live execution performance.",
        evaluation_contract=contract,
    )
    from orchestrator.storage.benchmarks import matched_fill_benchmark
    payload.update(matched_fill_benchmark(
        connection, min(opened).isoformat(), payload.get("closed_at"), cost_bps=float(cost)))


def learning_lots(outcomes: Iterable[dict]) -> list[dict]:
    """Expand derived lot attribution without duplicating aggregate broker P&L."""
    return [lot for row in outcomes for lot in (row.get("attributed_lots") or [row])]


def cohort_metrics(outcomes: list[dict]) -> dict:
    """Cluster repeated closes of one economic event; never count missing as zero."""
    independent: dict[str, list[dict]] = defaultdict(list)
    for row in learning_lots(outcomes):
        basis = cost_evidence(row)["state"]
        # A boolean alone is not provenance for a measured cost.
        costs_usable = basis == "measured" or (
            basis == "modelled" and row.get("cost_assumption_registered_at"))
        if (row.get("attribution_status") == "exact_entry_decision"
            and row.get("independent_event_id") and costs_usable
            and _number(row.get("net_return")) is not None
            and row.get("strategy_version") not in {None, "unversioned", "strategy-version-unclassified"}
            and row.get("broker_account_fingerprint") and row.get("paper_epoch_id")):
            key = str((row["broker_account_fingerprint"], row["paper_epoch_id"], row["strategy_version"],
                       row["independent_event_id"]))
            independent[key].append(row)
    # Partial exits are not independent trials. A weighted return is one observation.
    samples = []
    for rows in independent.values():
        if len({(row.get("cost_model_version"), row.get("costs_measured") is True) for row in rows}) != 1:
            continue
        weights = [_number(row.get("entry_notional")) for row in rows]
        if any(weight is None or weight <= 0 for weight in weights):
            continue
        total = sum(weights)
        value = sum(_number(row["net_return"]) * weight for row, weight in zip(rows, weights)) / total
        benchmarks = [_number(row.get("benchmark_net_return")) for row in rows]
        benchmark = (sum(v * w for v, w in zip(benchmarks, weights)) / total
                     if all(v is not None for v in benchmarks) else None)
        samples.append((value, benchmark, all(cost_evidence(row)["state"] == "measured" for row in rows)))
    count = len(samples)
    matched = [value - benchmark for value, benchmark, _ in samples if benchmark is not None]
    return {
        "raw_outcome_count": len(outcomes), "independent_outcome_count": count,
        "measured_event_count": sum(measured for _, _, measured in samples),
        "modelled_event_count": sum(not measured for _, _, measured in samples),
        "matched_benchmark_count": len(matched),
        "net_expectancy": float(sum(v for v, _, _ in samples) / count) if count else None,
        "no_trade_delta": float(sum(v for v, _, _ in samples) / count) if count else None,
        "benchmark_delta": float(sum(matched) / len(matched)) if matched else None,
        "units": "decimal_return_after_costs",
        "benchmark_comparison_available": count > 0 and len(matched) == count,
        "unresolved_outcome_count": sum(row.get("attribution_status") != "exact_entry_decision" for row in outcomes),
        "automatic_authority_mutation_allowed": False,
    }
