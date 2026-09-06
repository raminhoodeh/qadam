"""Prospective, read-only 20-session evaluation within the existing trial owner."""

from datetime import datetime, time, timezone
import json
from pathlib import Path
import sqlite3
from zoneinfo import ZoneInfo

from orchestrator.qadam_control_plane_store import ControlPlaneStore, DATABASE_NAME
from orchestrator.qadam_exchange_calendar import valid_calendar
from orchestrator.qadam_operator_ready_common import read_json, sha256_json
from orchestrator.qadam_outcome_attribution import _number, _time, cohort_metrics

VERSION = "qadam-paper-economic-review.v1"
TARGET = 20


def _metrics(runtime: Path, since: str, account: str, epoch: str) -> dict:
    database = runtime / DATABASE_NAME
    if not database.is_file():
        return {"available": False}
    with ControlPlaneStore(database, initialize=False).connect() as connection:
        hypotheses = [json.loads(row[0]) for row in connection.execute(
            "SELECT payload_json FROM hypotheses WHERE created_at>=?", (since,))]
        outcomes = [json.loads(row[0]) for row in connection.execute(
            "SELECT payload_json FROM outcomes WHERE observed_at>=?", (since,))]
        fills = [dict(row) for row in connection.execute(
            "SELECT quantity,price,payload_json FROM fills WHERE occurred_at>=?", (since,))]
    # Post-start exits of older positions are not new experiments.
    outcomes = [row for row in outcomes
                if row.get("broker_account_fingerprint") == account
                and row.get("paper_epoch_id") == epoch and row.get("allocations")
                and all(_time(lot.get("opened_at")) and _time(lot["opened_at"]) >= _time(since)
                        for lot in row["allocations"])]
    fills = [row for row in fills
             if (payload := json.loads(row["payload_json"])).get("broker_account_fingerprint") == account
             and payload.get("paper_epoch_id") == epoch]
    events = {row.get("economic_signal_identity_id") for row in hypotheses
              if row.get("economic_signal_identity_id") and row.get("active_paper_epoch_id") == epoch}
    completed = {row.get("independent_event_id") for row in outcomes
                 if row.get("attribution_status") == "exact_entry_decision"
                 and row.get("independent_event_id")}
    return {"available": True, "useful_opportunity_events": len(events),
            "opportunity_definition": "distinct canonical economic signal identities, not research scores",
            "independent_completed_experiments": len(completed),
            "filled_turnover_usd": sum(abs(row["quantity"] * row["price"]) for row in fills),
            "turnover_basis": "current-epoch provider cumulative fill aggregates",
            "outcome_comparison": cohort_metrics(outcomes),
            "human_intervention_count": None,
            "human_intervention_measurement": "not_completely_instrumented; never inferred as zero"}


def advance_review(previous: dict, *, current: datetime, policy_digest: str,
                   mirror: dict, soak: dict, metrics: dict) -> dict:
    """Count only sessions sampled prospectively; faults cannot disappear as skipped days."""
    current = current.astimezone(timezone.utc)
    stamp = current.isoformat()
    snapshot = mirror.get("snapshot") or {}
    binding = {"policy_digest": policy_digest,
               "broker_account_fingerprint": mirror.get("broker_account_fingerprint"),
               "paper_epoch_id": mirror.get("paper_epoch_id")}
    result = json.loads(json.dumps(previous)) if previous.get("version") == VERSION else {
        "version": VERSION, "registered_at": stamp, "binding": binding,
        "target_sessions": TARGET, "reliability_sessions_required_first": 5,
        "sessions": {}, "activated_at": None, "baseline": None,
        "trade_quota": None, "broker_write_count": 0, "automatic_risk_increase_allowed": False,
        "validated_edge_credit_allowed": False,
    }
    result["generated_at"] = stamp
    if result["binding"] != binding:
        result["status"] = "requires_new_policy_or_account_evaluation"
        return result
    calendar = mirror.get("market_calendar") or {}
    eastern = current.astimezone(ZoneInfo("America/New_York"))
    today = eastern.date().isoformat()
    provider_session = next((row for row in calendar.get("sessions", [])
                             if row.get("date") == today), None) if valid_calendar(calendar, current) else None
    opening = closing = None
    if provider_session:
        opening, closing = [datetime.combine(eastern.date(), time.fromisoformat(provider_session[key]),
                                             ZoneInfo("America/New_York")) for key in ("open", "close")]
    observed = _time(snapshot.get("observed_at"))
    equity, cash = _number(snapshot.get("equity")), _number(snapshot.get("cash"))
    fresh = bool(observed and 0 <= (current - observed).total_seconds() <= 600
                 and snapshot.get("broker_reconciliation_status") == "ok"
                 and equity is not None and equity > 0 and cash is not None)
    during = bool(opening and opening <= current <= closing)
    if not result["activated_at"]:
        ready = (soak.get("schema_version") == "qadam_catc_real_market_soak.v2"
                 and soak.get("observation_ready") is True)
        if not ready or not during or not fresh or not metrics.get("available"):
            result["status"] = "waiting_for_five_verified_sessions_then_next_observed_open"
            result["sessions_completed"] = 0
            return result
        result["activated_at"] = stamp
        result["baseline"] = {"observed_at": stamp, "equity_usd": float(equity),
                              "cash_usd": float(cash), "metrics": metrics,
                              "basis": "frozen start state, not a retrospectively selected profitable period"}
    sessions = result["sessions"]
    for row in sessions.values():
        if current > _time(row["closes_at"]):
            row["completed"] = True
    completed = sum(row["completed"] for row in sessions.values())
    if during and completed < TARGET:
        row = sessions.setdefault(today, {"first_observed_at": stamp,
            "closes_at": closing.isoformat(), "completed": False,
            "provider_session": provider_session, "equity_high_usd": None,
            "equity_low_usd": None, "last_equity_usd": None, "maximum_deployed_usd": None,
            "sampled_drawdown": None, "measurement_gaps": [], "backfilled": False})
        row["last_observed_at"] = stamp
        if fresh:
            value = float(equity)
            high = max(value, row["equity_high_usd"] or value)
            row["equity_high_usd"] = high
            row["equity_low_usd"] = min(value, row["equity_low_usd"] or value)
            row["sampled_drawdown"] = max(row["sampled_drawdown"] or 0, (high-value)/high)
            row["last_equity_usd"] = value
            row["maximum_deployed_usd"] = max(row["maximum_deployed_usd"] or 0, float(equity-cash))
        elif "broker_snapshot_missing_or_stale" not in row["measurement_gaps"]:
            row["measurement_gaps"].append("broker_snapshot_missing_or_stale")
        if not metrics.get("available") and "canonical_metrics_unavailable" not in row["measurement_gaps"]:
            row["measurement_gaps"].append("canonical_metrics_unavailable")
        row["metrics"] = metrics
    result["sessions_completed"] = sum(row["completed"] for row in sessions.values())
    finished = result["sessions_completed"] >= TARGET
    baseline = result["baseline"]
    samples = [row for _, row in sorted(sessions.items()) if row.get("last_equity_usd") is not None]
    peak, drawdown = baseline["equity_usd"], 0.0
    for row in samples:
        # Per-session intraday drawdown is known; ordering across high/low is not invented.
        drawdown = max(drawdown, row["sampled_drawdown"] or 0,
                       max(0, (peak-row["equity_low_usd"])/peak))
        peak = max(peak, row["equity_high_usd"])
    final_metrics = samples[-1].get("metrics", {}) if samples else {}
    outcome = final_metrics.get("outcome_comparison") or {}
    result["comparison"] = {
        "baseline": baseline, "current": final_metrics,
        "sampled_account_return": (samples[-1]["last_equity_usd"]/baseline["equity_usd"]-1) if samples else None,
        "account_return_is_strategy_return": False,
        "cash_flow_adjustment_available": False,
        "sampled_maximum_drawdown": drawdown if samples else None,
        "peak_deployed_capital_usd": max((r["maximum_deployed_usd"] for r in samples), default=None),
        "net_experiment_return": outcome.get("net_expectancy"),
        "benchmark_excess": outcome.get("benchmark_delta"),
        "human_interventions": None,
    }
    result["status"] = "review_due" if finished else "collecting_real_sessions"
    result["recommendation"] = (
        "do_not_expand; improve_evidence_or_register_a_new_research_programme"
        if finished and (not outcome.get("independent_outcome_count")
                         or (outcome.get("benchmark_delta") or 0) <= 0)
        else "maintain_approved_limits; await_independent_economic_review")
    result["measurement_limits"] = [
        "Observed sessions are not continuous uptime proof; outages and absent sessions remain gaps.",
        "Paper account change includes pre-existing positions; missing costs or benchmarks remain unknown.",
        "No assumption of zero human interventions or cash transfers; no automatic capital expansion.",
    ]
    return result


def economic_review(runtime: Path, policy_binding: dict) -> dict:
    previous = read_json(runtime / "qadam_active_discovery_trial_status.json").get("economic_evaluation") or {}
    current = datetime.now(timezone.utc)
    mirror = read_json(runtime / "alpaca_paper_mirror.json")
    since = previous.get("activated_at") or current.isoformat()
    try:
        metrics = _metrics(runtime, since, mirror.get("broker_account_fingerprint"), mirror.get("paper_epoch_id"))
    except sqlite3.Error as error:
        metrics = {"available": False, "error_class": type(error).__name__}
    return advance_review(previous, current=current, policy_digest=sha256_json(policy_binding),
                          mirror=mirror, soak=read_json(runtime / "qadam_catc_real_market_soak.json"),
                          metrics=metrics)
