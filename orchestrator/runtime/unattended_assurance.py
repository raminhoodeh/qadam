"""Release-specific observed health, never trading or indefinite-success authority."""

from datetime import datetime
from hashlib import sha256
import json
import math

OBSERVATION_WINDOW_SECONDS = 24 * 60 * 60
MAX_OBSERVATION_GAP_SECONDS = 180


def _time(value):
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return stamp if stamp.tzinfo else None
    except ValueError:
        return None


def assurance_brief(report, *, as_of, git_commit):
    now, stamp = _time(as_of), _time(report.get("observed_at"))
    if (not now or not stamp or not git_commit or not 0 <= (now - stamp).total_seconds() <= MAX_OBSERVATION_GAP_SECONDS
            or (report.get("release_identity") or {}).get("git_commit") != git_commit):
        return "Unattended health: current-build observations are not yet available."
    if report.get("runtime_ready_now") is not True:
        return "Unattended health: needs attention; the current-build operating checks are incomplete."
    seconds = report.get("observed_healthy_seconds")
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 <= seconds <= OBSERVATION_WINDOW_SECONDS:
        return "Unattended health: the observation record needs verification."
    if seconds >= OBSERVATION_WINDOW_SECONDS:
        return "Unattended health: 24 hours of healthy observations on this build; ongoing monitoring remains active."
    return f"Unattended health: healthy now; {seconds / 3600:.1f}/24 hours observed on this build."


def build_unattended_assurance(snapshot, *, healthy, owner_available, recovery_active,
                               installation_valid, previous, observed_at):
    operator = snapshot.get("operator") or {}
    identity = operator.get("release_identity") or {}
    release_fields = ("git_commit", "service_contract_hash", "dependency_lock_digest")
    release_known = all(isinstance(identity.get(key), str) and identity[key] for key in release_fields)
    release_id = sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest() if release_known else None
    control = snapshot.get("control_plane") or {}
    reconciliation = control.get("latest_reconciliation") or {}
    broker_observed = _time(reconciliation.get("mirror_observed_at"))
    observed = _time(observed_at)
    broker_age = (observed - broker_observed).total_seconds() if observed and broker_observed else None
    checks = {
        "runtime_classification_healthy": healthy is True,
        "owner_available": owner_available is True,
        "reviewed_launchd_contracts": installation_valid is True,
        "reviewed_release_identity": bool(release_known and operator.get("committed_release") is True
            and operator.get("running_build_matches_current") is True),
        "recovery_complete": recovery_active is False,
        "recovery_coverage": (snapshot.get("recovery_coverage") or {}).get("status") == "passed",
        "broker_reconciled": bool(control.get("present") and not control.get("read_error")
            and (control.get("execution_state") or {}).get("frozen") == 0
            and reconciliation.get("status") == "passed" and not reconciliation.get("blockers")
            and broker_age is not None and 0 <= broker_age <= 2400),
        "disk_writes_safe": (snapshot.get("storage") or {}).get("write_services_allowed") is True,
        "signed_public_status_current": (snapshot.get("public_status_delivery") or {}).get("healthy") is True,
        "trade_notification_monitor_current": (snapshot.get("trade_messaging") or {}).get("healthy") is True,
        "local_recovery_backup_current": (snapshot.get("local_recovery_backup") or {}).get("fresh") is True,
    }
    now, before = _time(observed_at), _time(previous.get("observed_at"))
    valid_clock = now is not None
    checks["observation_clock_verified"] = valid_clock
    ready = all(checks.values())
    gap = (now - before).total_seconds() if now and before else None
    prior_seconds, prior_samples = previous.get("observed_healthy_seconds"), previous.get("consecutive_healthy_samples")
    prior_valid = (type(prior_seconds) in (int, float) and math.isfinite(prior_seconds)
        and 0 <= prior_seconds <= OBSERVATION_WINDOW_SECONDS and type(prior_samples) is int
        and 0 < prior_samples <= 1_000_000)
    continuity = bool(ready and previous.get("runtime_ready_now") is True
        and previous.get("release_id") == release_id and gap is not None
        and 0 <= gap <= MAX_OBSERVATION_GAP_SECONDS and prior_valid)
    # Accumulate only observed, bounded intervals. Missing hours, a laptop
    # restart, clock reversal or a new build cannot be backfilled into a soak.
    seconds = min(OBSERVATION_WINDOW_SECONDS, prior_seconds + gap) if continuity else 0.0
    samples = min(1_000_000, prior_samples + int(gap > 0)) if continuity else int(ready)
    return {
        "schema_version": "unattended-runtime-assurance.1", "observed_at": observed_at,
        "release_id": release_id, "release_identity": identity,
        "runtime_ready_now": ready,
        "status": "needs_attention" if not ready else "observed_healthy_24h" if seconds >= OBSERVATION_WINDOW_SECONDS
            else "provisional_healthy",
        "checks": checks, "blockers": sorted(key for key, value in checks.items() if not value),
        "observed_healthy_seconds": seconds, "consecutive_healthy_samples": samples,
        "observation_target_seconds": OBSERVATION_WINDOW_SECONDS,
        "maximum_gap_seconds": MAX_OBSERVATION_GAP_SECONDS,
        "historical_or_simulated_time_credit": False, "permanent_success_guaranteed": False,
        "profitability_certified": False, "paper_order_allowed": False,
        "trade_count_is_not_health": True,
        "host_requirements": ["powered_and_awake", "user_session_available", "network_available",
                              "provider_and_broker_access", "sufficient_storage"],
        "host_power_loss_requires_external_monitor_or_always_on_host": True,
    }
