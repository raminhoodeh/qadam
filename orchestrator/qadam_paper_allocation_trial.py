"""Explicit, account-bound paper sizing permission with a fixed seven-day expiry.

This is not a signal producer or an execution owner. Missing, stale, mismatched
or expired approval restores baseline sizing; it never creates an opportunity.
"""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import sqlite3

from orchestrator.config import Settings
from orchestrator.paths import project_root

POLICY_PATH = project_root() / "config/qadam_paper_allocation_trial.json"
SCHEMA = "qadam_paper_allocation_trial.v1"
RISK_OVERRIDES = {
    "maximum_concurrent_discovery_micro_positions": 16,
    "maximum_discovery_positions_per_correlated_cluster": 4,
    "max_gross_notional_pct_equity": 0.75,
    "max_new_notional_per_day_pct_equity": 0.75,
    "max_source_family_notional_pct_equity": 0.75,
    "max_high_correlation_notional_pct_equity": 0.20,
    "max_tail_stress_loss_pct_equity": 0.15,
    "max_trailing_drawdown_pct_equity": 0.60,
    "discovery_target_notional_usd": {
        "minimum": 500.0,
        "maximum": 5000.0,
        "minimum_is_not_a_forced_floor": True,
    },
}


def _now():
    return datetime.now(timezone.utc)


def _stamp(value):
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except (TypeError, ValueError):
        return None


def _read(path):
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def reviewed_trial(settings=None):
    """Return only the exact bounded policy authorised by the human operator."""
    settings = settings or Settings.from_env()
    if settings.mode != "paper" or settings.live_capital_enabled:
        return None
    policy = _read(POLICY_PATH)
    start, end = _stamp(policy.get("starts_at")), _stamp(policy.get("expires_at"))
    equity = policy.get("starting_equity_usd")
    if not (
        policy.get("schema_version") == SCHEMA
        and policy.get("status") == "active"
        and policy.get("approval_source") == "direct_user_request_2026-10-27"
        and policy.get("approved_drawdown_from_start") == 0.60
        and policy.get("paper_only") is True
        and policy.get("live_capital_enabled") is False
        and start
        and end
        and end - start == timedelta(days=7)
        and type(equity) in (int, float)
        and math.isfinite(equity)
        and equity > 0
        and policy.get("trial_id")
        and policy.get("paper_epoch_id")
        and policy.get("broker_account_fingerprint")
        and policy.get("risk_overrides") == RISK_OVERRIDES
        and policy.get("maximum_unestimated_notional_usd") == 5000.0
        and policy.get("maximum_unestimated_planned_loss_usd") == 125.0
    ):
        return None
    return {
        **policy,
        "approval_sha256": sha256(json.dumps(policy, sort_keys=True).encode()).hexdigest(),
    }


def trial_status(settings=None, *, at=None):
    settings = settings or Settings.from_env()
    trial = reviewed_trial(settings)
    if not trial:
        return {"state": "baseline", "active": False}
    now = _stamp(at) if at is not None else _now()
    result = {"trial_id": trial["trial_id"], "active": False, "state": "not_started"}
    if not now or now < _stamp(trial["starts_at"]):
        return result
    if now >= _stamp(trial["expires_at"]):
        return {**result, "state": "expired"}
    runtime = Path(settings.runtime_dir)
    mirror = _read(runtime / "alpaca_paper_mirror.json")
    snapshot = mirror.get("snapshot") or {}
    observed = _stamp(snapshot.get("observed_at"))
    if not (
        mirror.get("status") == "ok"
        and snapshot.get("mode") == "paper"
        and snapshot.get("account_currency") == "USD"
        and snapshot.get("paper_epoch_id") == trial["paper_epoch_id"]
        and snapshot.get("broker_account_fingerprint") == trial["broker_account_fingerprint"]
        and observed
        and 0 <= (_now() - observed).total_seconds() <= 180
        and type(snapshot.get("equity")) in (int, float)
        and math.isfinite(snapshot["equity"])
        and snapshot["equity"] >= 0
    ):
        return {**result, "state": "broker_truth_unavailable_or_mismatched"}
    database = runtime / "qadam-control-plane.sqlite3"
    if not database.is_file():
        return {**result, "state": "trial_ledger_unavailable"}
    if database.exists():
        try:
            with sqlite3.connect(
                database.resolve().as_uri() + "?mode=ro", uri=True, timeout=1
            ) as db:
                frozen = db.execute(
                    "SELECT 1 FROM operating_events WHERE aggregate_type='allocation_trial' "
                    "AND aggregate_id=? AND event_type='entry_freeze' LIMIT 1",
                    (trial["trial_id"],),
                ).fetchone()
            if frozen:
                return {**result, "state": "drawdown_frozen"}
        except sqlite3.Error:
            return {**result, "state": "trial_ledger_unavailable"}
    if snapshot["equity"] <= trial["starting_equity_usd"] * (
        1 - trial["approved_drawdown_from_start"]
    ):
        return {**result, "state": "drawdown_breached"}
    return {**result, "active": True, "state": "active", "policy": trial}


def active_trial(settings=None, *, at=None):
    status = trial_status(settings, at=at)
    return status.get("policy") if status["active"] else None


def apply_portfolio_trial(policy):
    trial = active_trial(at=policy.get("generated_at"))
    if trial:
        policy["allocation_trial"] = trial
        policy["risk_budget"].update(trial["risk_overrides"])
        policy["confidence_classes"]["experimental_discovery_micro"].update(
            risk_multiplier=1.0, uncertainty_haircut=0.50
        )
    return policy


def apply_experimental_trial(policy):
    trial = active_trial(at=policy.get("generated_at"))
    if trial:
        policy["allocation_trial"] = trial
        for key in (
            "maximum_concurrent_discovery_micro_positions",
            "maximum_discovery_positions_per_correlated_cluster",
            "discovery_target_notional_usd",
        ):
            policy["risk"][key] = trial["risk_overrides"][key]
        policy["risk"]["discovery_micro_risk_multiplier"] = 1.0
        policy["risk"]["unestimated_discovery"].update(
            maximum_notional_usd=5000.0, maximum_loss_at_invalidation_usd=125.0
        )
    return policy


def discovery_limits(record=None):
    trial = active_trial()
    if (
        trial
        and (record or {}).get("allocation_trial_id") == trial["trial_id"]
        and (record or {}).get("allocation_trial_approval_sha256") == trial["approval_sha256"]
    ):
        return 5000.0, 125.0
    return 250.0, 5.0


def assert_entry_budget(
    connection, settings, *, trial_id, approval_sha256, instrument, side, notional, order_key
):
    """Reserve against held AND queued exposure inside the owner's transaction."""
    status = trial_status(settings)
    if trial_id and (not status["active"] or trial_id != status.get("trial_id")):
        raise ValueError("paper_allocation_trial_not_active")
    if trial_id and approval_sha256 != status.get("policy", {}).get("approval_sha256"):
        raise ValueError("paper_allocation_trial_approval_changed")
    if status["state"] in {
        "drawdown_breached",
        "drawdown_frozen",
        "broker_truth_unavailable_or_mismatched",
        "trial_ledger_unavailable",
    }:
        raise ValueError("paper_allocation_trial_entry_hold:" + status["state"])
    if not status["active"]:
        return
    snapshot = _read(Path(settings.runtime_dir) / "alpaca_paper_mirror.json")["snapshot"]
    equity, cash = float(snapshot["equity"]), snapshot.get("cash")
    if type(cash) not in (int, float) or not math.isfinite(cash):
        raise ValueError("paper_allocation_cash_unavailable")
    day = _now().date()
    first = None
    try:
        with (Path(settings.runtime_dir) / "paper_account_snapshots.jsonl").open() as history:
            for line in history:
                if str(day) not in line:
                    continue
                row = json.loads(line)
                stamp = _stamp(row.get("observed_at"))
                value = row.get("equity", row.get("equity_gbp"))
                if (
                    stamp
                    and stamp.date() == day
                    and stamp <= _now()
                    and row.get("paper_epoch_id") == status["policy"]["paper_epoch_id"]
                    and row.get("broker_account_fingerprint")
                    == status["policy"]["broker_account_fingerprint"]
                    and type(value) in (int, float)
                    and math.isfinite(value)
                    and value > 0
                    and (first is None or stamp < first[0])
                ):
                    first = stamp, value
    except (OSError, ValueError, TypeError):
        raise ValueError("paper_allocation_daily_baseline_unavailable") from None
    if first is None:
        raise ValueError("paper_allocation_daily_baseline_unavailable")
    if equity <= first[1] * 0.98:
        raise ValueError("paper_allocation_daily_loss_limit")
    universe = _read(Path(settings.runtime_dir) / "qsase_trading_universe.json")
    clusters = {
        row["symbol"]: row.get("market_family")
        for row in universe.get("instruments", [])
        if row.get("symbol")
    }
    target = clusters.get(instrument)
    if not target:
        raise ValueError("paper_allocation_cluster_unknown")
    gross = reserved_buys = cluster_gross = 0.0
    slots = cluster_slots = 0
    for row in connection.execute(
        "SELECT instrument,quantity,current_price FROM positions WHERE state='open'"
    ):
        cluster = clusters.get(row["instrument"])
        if not cluster or row["current_price"] is None:
            raise ValueError("paper_allocation_existing_exposure_unknown")
        value = abs(float(row["quantity"]) * float(row["current_price"]))
        if not math.isfinite(value) or value <= 0:
            raise ValueError("paper_allocation_existing_exposure_invalid")
        gross += value
        slots += 1
        if cluster == target:
            cluster_gross += value
            cluster_slots += 1
    for row in connection.execute(
        "SELECT order_key,instrument,side,payload_json FROM canonical_orders "
        "WHERE state IN ('prepared','submitting','submitted','new','accepted','pending_new','partially_filled') AND order_key<>?",
        (order_key,),
    ):
        payload = json.loads(row["payload_json"])
        if payload.get("purpose") != "canonical_position_entry":
            continue
        value = float((payload.get("candidate") or {}).get("notional_usd") or 0)
        cluster = clusters.get(row["instrument"])
        if not cluster or not math.isfinite(value) or value <= 0:
            raise ValueError("paper_allocation_pending_exposure_unknown")
        gross += value
        reserved_buys += value if row["side"] == "buy" else 0
        slots += 1
        if cluster == target:
            cluster_gross += value
            cluster_slots += 1
    if not 0 < notional <= min(5000.0, equity * 0.05) + 0.01:
        raise ValueError("paper_allocation_position_limit")
    if gross + notional > equity * 0.75 + 0.01:
        raise ValueError("paper_allocation_gross_limit")
    if cash - reserved_buys - (notional if side == "buy" else 0) < equity * 0.25 - 0.01:
        raise ValueError("paper_allocation_cash_reserve")
    if cluster_gross + notional > equity * 0.20 + 0.01:
        raise ValueError("paper_allocation_cluster_limit")
    if slots >= 16 or cluster_slots >= 4:
        raise ValueError("paper_allocation_position_count_limit")
