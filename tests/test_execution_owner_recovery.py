from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from orchestrator.config import Settings
from scripts.run_paperops_autonomous_pass import _reconciliation_failure_reason
import orchestrator.execution.ledger as mod


@pytest.mark.parametrize("detail,recoverable", [
    ("canonical_execution_owner_lease_invalid:lease_fresh", True),
    ("canonical_execution_owner_lease_invalid:token_matches,lease_fresh", False),
    ("canonical_execution_owner_lease_invalid:owner_matches", False),
    ("canonical_execution_owner_lease_missing", False),
    ("execution_owner_busy:someone", False),
])
def test_only_expiry_is_recoverable(detail, recoverable):
    reason = _reconciliation_failure_reason("post_paperops_submission", mod.ExecutionOwnerError(detail))
    assert mod.OperatingLedger._recoverable_freeze(reason) is recoverable


def _incident(tmp_path, monkeypatch, *, reason=None, expires=True, released=True):
    clock = [datetime(2026, 9, 24, 12, tzinfo=timezone.utc)]
    monkeypatch.setattr(mod, "_now", lambda: clock[0])
    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path), state_root=str(tmp_path), mode="paper", live_capital_enabled=False)
    ledger = mod.OperatingLedger(settings)
    old = ledger.acquire_execution_owner("old-owner", ttl_seconds=60 if expires else 7200)
    clock[0] += timedelta(seconds=61)
    ledger.set_execution_frozen(reason=reason or "post_paperops_submission_reconciliation_failed:ExecutionOwnerError")
    incident_at = ledger.execution_state()["updated_at"]
    clock[0] += timedelta(seconds=9)
    if released:
        ledger.release_execution_owner(old)
    clock[0] += timedelta(hours=3)
    lease = ledger.acquire_execution_owner("review-owner")
    for key, value in lease.environment().items():
        monkeypatch.setenv(key, value)
    return ledger, clock, incident_at


def _check(ledger, clock, *, positions=0, blockers=None, observation=None):
    clock[0] += timedelta(seconds=1)
    return ledger.record_direct_reconciliation(
        phase="owner_expiry_review", expected={"active_order_count": 0},
        observed={"position_count": positions, "open_order_count": 0,
                  "mirror_observed_at": observation or clock[0].isoformat(),
                  "position_protection_digest": "flat-protection"}, blockers=blockers or [],
    )


def test_explicit_review_requires_two_fresh_flat_observations(tmp_path, monkeypatch):
    ledger, clock, incident = _incident(tmp_path, monkeypatch)
    _check(ledger, clock)
    with pytest.raises(mod.ControlPlaneError, match="two_matching"):
        ledger.review_legacy_owner_freeze(incident_at=incident)
    assert ledger.execution_state()["frozen"] == 1
    _check(ledger, clock)
    receipt = ledger.review_legacy_owner_freeze(incident_at=incident)
    assert ledger.execution_state()["frozen"] == 0
    assert len(receipt["reconciliation_ids"]) == 2
    assert receipt["broker_write_count"] == 0


@pytest.mark.parametrize("case", ["manual", "wrong_incident", "not_expired", "not_released", "position", "failed", "stale", "repeated_observation", "later_hold"])
def test_review_does_not_clear_unproven_incidents(tmp_path, monkeypatch, case):
    ledger, clock, incident = _incident(
        tmp_path, monkeypatch, expires=case != "not_expired", released=case != "not_released",
        reason="operator_manual_stop" if case == "manual" else None,
    )
    observation = clock[0].isoformat() if case == "repeated_observation" else None
    for _ in range(2):
        _check(ledger, clock, positions=int(case == "position"),
               blockers=["mismatch"] if case == "failed" else [], observation=observation)
    if case == "stale":
        clock[0] += timedelta(seconds=181)
    if case == "later_hold":
        ledger.set_execution_frozen(reason="operator_manual_stop")
    with pytest.raises(mod.ControlPlaneError):
        ledger.review_legacy_owner_freeze(incident_at="wrong" if case == "wrong_incident" else incident)
    assert ledger.execution_state()["frozen"] == 1


def test_typed_expiry_self_recovers_only_after_two_matching_reads(tmp_path, monkeypatch):
    ledger, clock, _ = _incident(tmp_path, monkeypatch, reason="post_paperops_submission_reconciliation_owner_lease_expired")
    _check(ledger, clock)
    assert ledger.execution_state()["frozen"] == 1
    _check(ledger, clock)
    assert ledger.execution_state()["frozen"] == 0
