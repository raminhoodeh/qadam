from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from orchestrator.runtime.unattended_assurance import build_unattended_assurance, assurance_brief

NOW = datetime(2026, 10, 21, 14, tzinfo=timezone.utc)


def snapshot():
    return {"operator": {"committed_release": True, "running_build_matches_current": True,
                "release_identity": {"git_commit": "reviewed-build", "service_contract_hash": "contract", "dependency_lock_digest": "deps"}},
            "control_plane": {"present": True, "execution_state": {"frozen": 0}, "latest_reconciliation": {"status": "passed"}},
            "recovery_coverage": {"status": "passed"}, "storage": {"write_services_allowed": True},
            "public_status_delivery": {"healthy": True}, "trade_messaging": {"healthy": True},
            "local_recovery_backup": {"fresh": True}}


def observe(previous=None, *, at=NOW, data=None, **kwargs):
    return build_unattended_assurance(data or snapshot(), previous=previous or {}, observed_at=at.isoformat(),
        **{"healthy": True, "owner_available": True, "recovery_active": False,
           "installation_valid": True, **kwargs})


def test_new_release_cannot_inherit_historical_healthy_soak():
    first = observe()
    assert first["status"] == "provisional_healthy"
    assert first["observed_healthy_seconds"] == 0
    assert first["consecutive_healthy_samples"] == 1
    previous = observe(first, at=NOW + timedelta(seconds=60))
    changed = snapshot()
    changed["operator"]["release_identity"]["git_commit"] = "new-build"
    restarted = observe(previous, data=changed, at=NOW + timedelta(seconds=120))
    assert restarted["observed_healthy_seconds"] == 0
    assert restarted["release_id"] != previous["release_id"]


@pytest.mark.parametrize("delta", [-1, 181, 3600, 86400])
def test_missing_or_reversed_time_cannot_be_backfilled(delta):
    restarted = observe(observe(), at=NOW + timedelta(seconds=delta))
    assert restarted["observed_healthy_seconds"] == 0
    assert restarted["status"] == "provisional_healthy"


def test_duplicate_observations_do_not_add_time_or_samples():
    first = observe()
    assert observe(first)["consecutive_healthy_samples"] == 1
    assert observe(first)["observed_healthy_seconds"] == 0


@pytest.mark.parametrize("path,value", [
    (("operator", "committed_release"), False),
    (("operator", "running_build_matches_current"), False),
    (("control_plane", "execution_state"), {"frozen": 1}),
    (("storage", "write_services_allowed"), False),
    (("public_status_delivery", "healthy"), False),
    (("trade_messaging", "healthy"), False),
    (("local_recovery_backup", "fresh"), False),
])
def test_unknown_or_degraded_infrastructure_resets_observation_streak(path, value):
    data = deepcopy(snapshot())
    data[path[0]][path[1]] = value
    failed = observe(observe(), data=data, at=NOW + timedelta(minutes=1))
    assert not failed["runtime_ready_now"]
    assert failed["status"] == "needs_attention"
    assert failed["observed_healthy_seconds"] == 0
    assert observe(failed, at=NOW + timedelta(minutes=2))["observed_healthy_seconds"] == 0


def test_24_hours_requires_actual_sequential_observations_not_an_old_timestamp():
    record = observe()
    for minute in range(1, 1441):
        record = observe(record, at=NOW + timedelta(minutes=minute))
    assert record["status"] == "observed_healthy_24h"
    assert record["observed_healthy_seconds"] == 86400
    assert record["consecutive_healthy_samples"] == 1441
    assert not record["permanent_success_guaranteed"]
    assert not record["profitability_certified"]
    assert not record["paper_order_allowed"]


def test_active_healing_is_not_silently_counted_as_a_healthy_release():
    record = observe(observe(), at=NOW + timedelta(minutes=1), recovery_active=True)
    assert record["status"] == "needs_attention"
    assert "recovery_complete" in record["blockers"]


@pytest.mark.parametrize("invalid", ["bad", None, True, float("nan"), float("inf"), -1, 999999999])
def test_malformed_prior_observation_resets_without_crashing_watchdog(invalid):
    previous = observe()
    previous["observed_healthy_seconds"] = invalid
    result = observe(previous, at=NOW + timedelta(seconds=60))
    assert result["observed_healthy_seconds"] == 0
    assert result["status"] == "provisional_healthy"


def test_telegram_brief_uses_only_fresh_same_release_observations():
    first = observe()
    assert "0.0/24" in assurance_brief(first, as_of=NOW.isoformat(), git_commit="reviewed-build")
    assert "not yet available" in assurance_brief(first, as_of=NOW.isoformat(), git_commit="different-build")
    assert "not yet available" in assurance_brief(first, as_of=(NOW + timedelta(hours=1)).isoformat(), git_commit="reviewed-build")
    assert "needs attention" in assurance_brief(observe(recovery_active=True), as_of=NOW.isoformat(), git_commit="reviewed-build")
