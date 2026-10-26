from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from orchestrator.presentation.health_domains import overlay_health_domains


@pytest.mark.parametrize("fault", [None, "old", "future", "other_release", "frozen", "stale_broker", "build_drift", "delivery"])
def test_current_canonical_probes_replace_legacy_monitoring_labels_without_greenwashing(fault):
    now = datetime.now(timezone.utc)
    domains = [{"domain_id": name, "tone": "unmonitored", "status": "Unknown"}
               for name in ("host", "paper_broker", "communications", "deployment")]
    operator = {"generated_at": now.isoformat(), "build_identity": {
        "committed_release": True, "running_build_matches_current": True,
        "current": {"git_commit": "reviewed", "dirty_worktree": False},
        "running": {"git_commit": "reviewed"}}}
    watchdog = {"unattended_assurance": {"observed_at": now.isoformat(),
        "release_identity": {"git_commit": "reviewed"},
        "checks": {"trade_notification_monitor_current": True, "signed_public_status_current": True}}}
    broker = {"status": "healthy", "reconciliation_age_seconds": 10}
    if fault in {"old", "future"}:
        watchdog["unattended_assurance"]["observed_at"] = (now + timedelta(seconds=1 if fault == "future" else -181)).isoformat()
    elif fault == "other_release":
        watchdog["unattended_assurance"]["release_identity"]["git_commit"] = "other"
    elif fault == "frozen":
        broker["status"] = "degraded"
    elif fault == "stale_broker":
        broker["reconciliation_age_seconds"] = 2401
    elif fault == "build_drift":
        operator["build_identity"]["running_build_matches_current"] = False
    elif fault == "delivery":
        watchdog["unattended_assurance"]["checks"]["trade_notification_monitor_current"] = False
    inputs = deepcopy((operator, watchdog, broker))
    covered = overlay_health_domains(domains, broker=broker, operator=operator, watchdog=watchdog,
                                    as_of=now.isoformat(), runtime_state="paper-operational")
    rows = {row["domain_id"]: row for row in domains}
    assert rows["host"]["tone"] == "unmonitored"
    assert rows["paper_broker"]["tone"] == ("degraded" if fault in {"frozen", "stale_broker"} else "online")
    if fault in {"old", "future", "other_release"}:
        assert not covered
        assert rows["communications"]["tone"] == rows["deployment"]["tone"] == "unmonitored"
    else:
        assert len(covered) == 2
        assert rows["communications"]["tone"] == ("degraded" if fault == "delivery" else "online")
        assert rows["deployment"]["tone"] == ("degraded" if fault == "build_drift" else "online")
    assert inputs == (operator, watchdog, broker)
    assert "Paused by policy" not in str(rows["paper_broker"])
