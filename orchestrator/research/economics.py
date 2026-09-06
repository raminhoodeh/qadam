"""Receipt-backed research economics; association is not marginal trading value."""

from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import sqlite3


def _stamp(value):
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return stamp.astimezone(timezone.utc) if stamp.tzinfo else None
    except ValueError:
        return None


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def record_expense(store, receipt: dict) -> bool:
    """Import an operator-supplied reconciled USD receipt into the existing ledger.

    Estimates and unknown bills are not expenses of zero. Corrections are new
    receipts referring to the superseded ID; the original is never overwritten.
    """
    required = ("receipt_id", "component_id", "category", "period_start", "period_end", "source_reference")
    if any(not isinstance(receipt.get(key), str) or not receipt[key] for key in required):
        raise ValueError("expense_receipt_incomplete")
    if receipt["category"] not in {"subscription", "model_api", "quantum", "data_api"}:
        raise ValueError("expense_category_invalid")
    start, end = _stamp(receipt["period_start"]), _stamp(receipt["period_end"])
    now = datetime.now(timezone.utc)
    if not start or not end or not start < end or start > now:
        raise ValueError("expense_period_invalid")
    if (receipt.get("currency") != "USD" or receipt.get("basis") != "reconciled_provider_receipt"
            or not _number(receipt.get("amount_usd")) or receipt["amount_usd"] < 0):
        raise ValueError("expense_requires_actual_usd_receipt")
    payload = {key: receipt[key] for key in (*required, "amount_usd", "currency", "basis")}
    payload["supersedes_receipt_id"] = receipt.get("supersedes_receipt_id")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    digest = sha256(encoded.encode()).hexdigest()
    event_id = "research-expense:" + sha256(payload["receipt_id"].encode()).hexdigest()
    with store.transaction() as connection:
        if payload["supersedes_receipt_id"]:
            prior = "research-expense:" + sha256(str(payload["supersedes_receipt_id"]).encode()).hexdigest()
            row = connection.execute("SELECT payload_json FROM operating_events WHERE event_id=?", (prior,)).fetchone()
            if not row or json.loads(row[0])["component_id"] != payload["component_id"] or prior == event_id:
                raise ValueError("expense_correction_reference_invalid")
            # Competing revisions are ambiguous, never two bill reductions.
            for other in connection.execute("SELECT event_id,payload_json FROM operating_events WHERE aggregate_type='research_expense'"):
                if other[0] != event_id and json.loads(other[1]).get("supersedes_receipt_id") == payload["supersedes_receipt_id"]:
                    raise ValueError("expense_correction_already_superseded")
        return store._insert_immutable(connection, table="operating_events", identity_column="event_id",
            identity=event_id, columns=("event_id", "aggregate_type", "aggregate_id", "event_type",
                "payload_json", "payload_sha256", "created_at"),
            values=(event_id, "research_expense", payload["component_id"], "receipt_reconciled",
                    encoded, digest, now.isoformat()), payload_sha256=digest)


def build_report(*, hypotheses: list[dict], expenses: list[dict], ablations: list[dict],
                 selected_sources: list[str], as_of: str, inputs_complete: bool = True) -> dict:
    now = _stamp(as_of)
    if now is None:
        raise ValueError("economics_as_of_timezone_required")
    associations = defaultdict(set)
    for hypothesis in hypotheses:
        event = hypothesis.get("economic_signal_identity_id")
        if not event:
            continue
        for source in hypothesis.get("current_trigger_sources", []):
            if isinstance(source, str) and source:
                associations["source:" + source].add(event)
    components = set(associations) | {"source:" + key for key in selected_sources}
    components |= {"model:local_gemma", "model:frontier_gemini", "model:classical_quant", "model:ibm_quantum"}
    superseded = {row.get("supersedes_receipt_id") for row in expenses if row.get("supersedes_receipt_id")}
    current_expenses = []
    for row in expenses:
        start, end = _stamp(row.get("period_start")), _stamp(row.get("period_end"))
        if (row.get("receipt_id") in superseded or row.get("basis") != "reconciled_provider_receipt"
                or row.get("currency") != "USD" or not _number(row.get("amount_usd"))
                or row["amount_usd"] < 0 or not start or not end or not start <= now < end):
            continue
        current_expenses.append(row)
        components.add(row["component_id"])
    # An ablation is usable only if its frozen variants predate that event.
    matched = defaultdict(dict)
    excluded = 0
    for row in ablations:
        registered, entry, completed = (_stamp(row.get(key)) for key in ("registered_at", "event_available_at", "completed_at"))
        valid = (registered and entry and completed and registered <= entry <= completed <= now
                 and row.get("registration_receipt_verified") is True and row.get("provider_backed_outcome") is True
                 and row.get("same_event_same_window") is True and row.get("same_risk_budget") is True
                 and row.get("hypotheses_mutated") is False and row.get("holdout_reused") is False
                 and row.get("frozen_with_version") and row.get("frozen_without_version")
                 and row.get("component_id") and row.get("independent_event_id") and row.get("registration_id")
                 and _number(row.get("with_component_net_return")) and _number(row.get("without_component_net_return")))
        if not valid:
            excluded += 1
            continue
        key = (row["registration_id"], row["independent_event_id"])
        component = row["component_id"]
        previous = matched[component].get(key)
        if previous is not None and previous != row:
            matched[component][key] = {}
        elif previous is None:
            matched[component][key] = row
        components.add(component)
    rows = []
    for component in sorted(components):
        bills = [row for row in current_expenses if row["component_id"] == component]
        pairs = [row for row in matched[component].values() if row]
        # Different preregistrations are reported separately, not pooled into a
        # synthetic independent sample or used to tune the live policy.
        studies = []
        for registration in sorted({row["registration_id"] for row in pairs}):
            study = [row for row in pairs if row["registration_id"] == registration]
            deltas = [row["with_component_net_return"] - row["without_component_net_return"] for row in study]
            studies.append({"registration_id": registration, "independent_event_count": len(study),
                "mean_modelled_return_delta": sum(deltas) / len(deltas),
                "decision_change_count": sum(row.get("decision_changed") is True for row in study),
                "forecast_error_improvement": None, "promotion_authority": False})
        rows.append({"component_id": component, "associated_event_count": len(associations[component]),
            "association_is_incremental_value": False,
            "marginal_value_state": "paired_observations_available_for_review" if studies else "unproven_no_registered_paired_outcomes",
            "ablations": studies, "current_period_receipt_count": len(bills),
            "reconciled_period_expense_usd": sum(row["amount_usd"] for row in bills) if bills else None,
            "expense_periods": [{"start": row["period_start"], "end": row["period_end"]} for row in bills],
            "automatic_cancellation_or_budget_change": False})
    return {"schema_version": "qadam-research-economics.1", "generated_at": as_of,
        "status": "read_only_report" if inputs_complete else "incomplete_input_window",
        "input_window_complete": inputs_complete, "components": rows,
        "subscription_expense_usd": sum(row["amount_usd"] for row in current_expenses if row["category"] == "subscription")
            if any(row["category"] == "subscription" for row in current_expenses) else None,
        "model_expense_usd": sum(row["amount_usd"] for row in current_expenses if row["category"] == "model_api")
            if any(row["category"] == "model_api" for row in current_expenses) else None,
        "cost_state": "partial_receipts_not_total_operating_cost" if current_expenses else "not_reconciled_to_provider_bills",
        "excluded_ablation_count": excluded, "paper_pnl_is_cash_income": False,
        "automatic_budget_expansion": False, "paper_order_allowed": False}


def load_report(runtime: Path, *, selected_sources: list[str], as_of: str) -> dict:
    """Read bounded canonical records, without migration, credentials or broker I/O."""
    path = runtime / "qadam-control-plane.sqlite3"
    empty = dict(hypotheses=[], expenses=[], ablations=[], selected_sources=selected_sources, as_of=as_of)
    if not path.is_file():
        return build_report(**empty, inputs_complete=False)
    limit = 5000
    try:
        connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=1)
        try:
            connection.execute("PRAGMA query_only=ON")
            connection.execute("BEGIN")
            remaining_bytes, complete = 32 * 1024 * 1024, True
            def read_rows(sql):
                nonlocal remaining_bytes, complete
                rows = []
                for row in connection.execute(sql, (limit + 1,)):
                    length = len(row[0].encode())
                    if length > 262144 or length > remaining_bytes or len(rows) >= limit:
                        complete = False
                        break
                    remaining_bytes -= length
                    rows.append(json.loads(row[0]))
                return rows
            hypotheses = read_rows(
                "SELECT substr(payload_json,1,262145) FROM hypotheses ORDER BY rowid DESC LIMIT ?")
            expenses = read_rows(
                "SELECT substr(payload_json,1,262145) FROM operating_events WHERE aggregate_type='research_expense' ORDER BY created_at DESC LIMIT ?")
            # Absence of a registered paired-results producer is explicit. Model
            # narratives or a boolean in a runtime JSON cannot create ablation proof.
            report = build_report(hypotheses=hypotheses[:limit], expenses=expenses[:limit], ablations=[],
                selected_sources=selected_sources, as_of=as_of,
                inputs_complete=complete)
            return report
        finally:
            connection.close()
    except (sqlite3.Error, ValueError, TypeError, KeyError):
        return build_report(**empty, inputs_complete=False)
