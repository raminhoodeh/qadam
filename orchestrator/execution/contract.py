"""Reviewed database policy and fenced per-pass authority, not scheduler JSON."""

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
import sqlite3

from orchestrator.execution.ledger import (
    EXECUTION_LEASE_NAME, EXECUTION_OWNER_ID_ENV, EXECUTION_OWNER_TOKEN_ENV,
    ExecutionOwnerError, OperatingLedger, _event, execution_owner_process_state,
)

POLICY_ID = "canonical_paper_execution"
ROOT = Path(__file__).resolve().parents[2]
CODE_PATHS = (
    "scripts/run_paperops_autonomous_pass.py", "scripts/check_qadam_execution_contract.py",
    "scripts/run_active_paper_trading_automation.py", "orchestrator/execution/contract.py",
    "orchestrator/execution/ledger.py", "orchestrator/execution/ownership.py",
    "orchestrator/execution/candidate_selection.py", "orchestrator/execution/entry_quote.py",
    "orchestrator/paperops_autonomous_pass.py", "orchestrator/qadam_canonical_exit_engine.py",
    "orchestrator/paperops_active_paper_trading_automation.py",
    "orchestrator/paperops_alpaca_paper_post.py",
    "orchestrator/contracts/execution_recovery.py", "orchestrator/contracts/broker_history.py",
    "orchestrator/contracts/storage_recovery.py", "orchestrator/qadam_control_plane_migrations.py",
    "scripts/reconcile_qadam_paper_execution.py",
    "orchestrator/qadam_paper_allocation_trial.py", "config/qadam_paper_allocation_trial.json",
    "orchestrator/qadam_portfolio_risk_engine.py", "orchestrator/qadam_experimental_paper_policy.py",
    "orchestrator/qadam_router_v3_paperops.py", "orchestrator/research/foundry.py",
    "orchestrator/qadam_strategy_foundry_v4.py", "orchestrator/qadam_discovery_micro_conversion.py",
    "orchestrator/qadam_experimental_policy_amendment.py",
)


def _encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _digest(value):
    return sha256(_encoded(value).encode()).hexdigest()


def code_digest():
    return _digest({name: sha256((ROOT / name).read_bytes()).hexdigest() for name in CODE_PATHS})


def approve_execution_policy(settings, *, reviewed=False):
    """Explicit deployment operation; preserve the already approved paper epoch."""
    if not reviewed or settings.mode != "paper" or settings.live_capital_enabled:
        raise ExecutionOwnerError("reviewed_paper_policy_required")
    runtime = Path(settings.runtime_dir)
    def read(name):
        return json.loads((runtime / name).read_text())
    release = read("qadam_experimental_paper_release_readiness.json")
    epoch = read("current_paper_epoch.json")
    lock = read("qadam_long_backtest_lock.json")
    epoch_id = epoch.get("paper_epoch_id")
    checks = (
        bool(epoch_id), release.get("status") == "experimental_paper_release_effective",
        release.get("experimental_paper_release_effective") is True,
        release.get("experimental_paper_release_ready") is True, not release.get("blockers"),
        release.get("canonical_wrapper") == "scripts/run_paperops_autonomous_pass.py",
        release.get("paper_epoch_id") == epoch_id,
        epoch.get("paper_epoch_kind") == "clean_experimental_operator_epoch",
        epoch.get("paper_growth_trial_calendar_started") is True,
        epoch.get("paper_growth_trial_state") == "active_real_calendar",
        epoch.get("simulated_elapsed_time") is False,
        epoch.get("paper_growth_trial_calendar_backfilled") is False,
        lock.get("status") == "released", lock.get("paperops_watch_only_mode") is False,
        lock.get("release_mode") == "explicit_operator_approved_experimental_paper_epoch",
        lock.get("release_approval_epoch_id") == epoch_id,
    )
    if not all(checks):
        raise ExecutionOwnerError("approved_paper_epoch_contract_invalid")
    # Import the approval once. Mutable diagnostic status and lease projections
    # are deliberately absent from all subsequent execution decisions.
    payload = {"version": "execution-runtime-policy.1", "paper_epoch_id": epoch_id,
               "code_digest": code_digest(), "entries_enabled": True, "care_enabled": True,
               "paper_only": True, "live_capital_enabled": False}
    ledger = OperatingLedger(settings)
    stamp = datetime.now(timezone.utc).isoformat()
    with ledger.store.transaction() as db:
        prior = db.execute("SELECT generation,payload_sha256 FROM execution_runtime_policy WHERE policy_id=?", (POLICY_ID,)).fetchone()
        digest = _digest(payload)
        if prior and prior["payload_sha256"] == digest:
            return {"status": "already_reviewed", "generation": prior["generation"], **payload}
        active = db.execute("SELECT owner_id FROM execution_owner_leases WHERE state='active'").fetchall()
        if any(execution_owner_process_state(row["owner_id"]) != "dead" for row in active):
            raise ExecutionOwnerError("execution_policy_change_requires_drained_owner")
        generation = int(prior["generation"]) + 1 if prior else 1
        db.execute("INSERT INTO execution_runtime_policy VALUES (?,?,?,?,?) ON CONFLICT(policy_id) DO UPDATE SET "
                   "generation=excluded.generation,payload_json=excluded.payload_json,payload_sha256=excluded.payload_sha256,reviewed_at=excluded.reviewed_at",
                   (POLICY_ID, generation, _encoded(payload), digest, stamp))
        _event(db, aggregate_type="execution_policy", aggregate_id=POLICY_ID,
               event_type="reviewed_policy_installed", payload={**payload, "generation": generation}, created_at=stamp)
    return {"status": "reviewed_policy_installed", "generation": generation, **payload}


def bind_execution_contract(ledger, *, scope):
    if scope not in {"entries_and_care", "care_only"}:
        raise ExecutionOwnerError("execution_scope_invalid")
    owner = ledger.assert_execution_owner()
    with ledger.store.transaction() as db:
        policy = db.execute("SELECT * FROM execution_runtime_policy WHERE policy_id=?", (POLICY_ID,)).fetchone()
        if not policy:
            raise ExecutionOwnerError("execution_policy_not_reviewed")
        payload = json.loads(policy["payload_json"])
        if (_digest(payload) != policy["payload_sha256"] or payload.get("code_digest") != code_digest()
                or payload.get("paper_only") is not True or payload.get("live_capital_enabled") is not False):
            raise ExecutionOwnerError("execution_policy_identity_mismatch")
        bound = {"policy_generation": policy["generation"], "policy_sha256": policy["payload_sha256"],
                 "paper_epoch_id": payload["paper_epoch_id"], "scope": scope}
        _event(db, aggregate_type="execution_contract", aggregate_id=owner["owner_id"],
               event_type="pass_bound", payload=bound)
    return bound


def execution_contract_status(settings, *, require_entry=False):
    """Read one SQLite snapshot. Never acquire a lease or grant missing authority."""
    blockers = []
    owner_id = os.getenv(EXECUTION_OWNER_ID_ENV, "")
    token = os.getenv(EXECUTION_OWNER_TOKEN_ENV, "")
    payload, bound = {}, {}
    db = None
    if settings.mode != "paper" or settings.live_capital_enabled:
        blockers.append("execution_paper_boundary_invalid")
    try:
        path = Path(settings.runtime_dir) / "qadam-control-plane.sqlite3"
        db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("BEGIN")
        policy = db.execute("SELECT * FROM execution_runtime_policy WHERE policy_id=?", (POLICY_ID,)).fetchone()
        lease = db.execute("SELECT * FROM execution_owner_leases WHERE lease_name=?", (EXECUTION_LEASE_NAME,)).fetchone()
        event = db.execute("SELECT payload_json,payload_sha256 FROM operating_events WHERE aggregate_type='execution_contract' "
                           "AND aggregate_id=? AND event_type='pass_bound' ORDER BY created_at DESC LIMIT 1", (owner_id,)).fetchone()
        if not policy:
            blockers.append("execution_policy_not_reviewed")
        else:
            payload = json.loads(policy["payload_json"])
            if _digest(payload) != policy["payload_sha256"] or payload.get("code_digest") != code_digest():
                blockers.append("execution_policy_identity_mismatch")
            if payload.get("paper_only") is not True or payload.get("live_capital_enabled") is not False:
                blockers.append("execution_paper_boundary_invalid")
        valid_lease = False
        if lease and owner_id and token:
            expiry = datetime.fromisoformat(lease["expires_at"])
            if (lease["owner_id"] != owner_id
                    or not secrets.compare_digest(lease["token_sha256"], sha256(token.encode()).hexdigest())):
                blockers.append("execution_owner_fencing_invalid")
            valid_lease = (lease["state"] == "active" and lease["owner_id"] == owner_id
                and secrets.compare_digest(lease["token_sha256"], sha256(token.encode()).hexdigest())
                and expiry.tzinfo is not None and expiry > datetime.now(timezone.utc)
                and execution_owner_process_state(owner_id) == "alive")
        if not valid_lease:
            blockers.append("execution_owner_unavailable")
        if event and policy:
            bound = json.loads(event["payload_json"])
            if (_digest(bound) != event["payload_sha256"] or bound.get("policy_generation") != policy["generation"]
                    or bound.get("policy_sha256") != policy["payload_sha256"]
                    or bound.get("paper_epoch_id") != payload.get("paper_epoch_id")):
                blockers.append("execution_contract_binding_invalid")
        else:
            blockers.append("execution_contract_not_bound")
        if bound.get("scope") not in {"care_only", "entries_and_care"} or payload.get("care_enabled") is not True:
            blockers.append("execution_scope_invalid")
        entry_allowed = bound.get("scope") == "entries_and_care" and payload.get("entries_enabled") is True
        if require_entry and not entry_allowed:
            blockers.append("execution_entry_scope_denied")
    except (OSError, sqlite3.Error, ValueError, TypeError, KeyError, AttributeError):
        blockers.append("execution_contract_unreadable")
        entry_allowed = False
    finally:
        if db is not None:
            db.close()
    return {"active": not blockers, "status": "active" if not blockers else "blocked",
            "source": "canonical_database_contract", "owner": "qadam_operator_service" if not blockers else "none",
            "blockers": sorted(set(blockers)), "checks": {"database_execution_contract": not blockers},
            "entry_allowed": not blockers and entry_allowed, "care_allowed": not blockers,
            "canonical_wrapper": "scripts/run_paperops_autonomous_pass.py", "cadence_seconds": 30,
            "current_state": "fenced_execution_pass" if not blockers else "blocked",
            "paper_epoch_id": payload.get("paper_epoch_id"), "scope": bound.get("scope"),
            "paper_only": True, "live_capital_enabled": False}


def require_execution_contract(settings, *, require_entry=False):
    status = execution_contract_status(settings, require_entry=require_entry)
    if not status["active"]:
        raise ExecutionOwnerError("execution_contract_blocked:" + ",".join(status["blockers"]))
    return status
