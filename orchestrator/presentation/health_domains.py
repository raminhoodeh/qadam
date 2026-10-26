"""Current canonical health over legacy inventory labels; no permission changes."""

from orchestrator.contracts.timestamps import _parse_timestamp


def overlay_health_domains(domains, *, broker, operator, watchdog, as_of, runtime_state):
    now = _parse_timestamp(as_of)

    def fresh(value):
        stamp = _parse_timestamp(value)
        return bool(now and stamp and 0 <= (now-stamp).total_seconds() <= 180)

    by_id = {row["domain_id"]: row for row in domains}
    covered = set()
    age = broker.get("reconciliation_age_seconds")
    if type(age) in (float, int) and age >= 0:
        healthy = broker.get("status") == "healthy" and age <= 2400
        row = by_id["paper_broker"]
        row.update(canonical_probe_verified=True, status="Canonical reconciliation current" if healthy else "Canonical reconciliation needs attention",
                   tone="online" if healthy else "degraded", metric="Guarded paper route; canonical broker readback",
                   summary="Execution freezes, protection and actual broker-observation age come from the canonical ledger.",
                   last_checked_at=as_of, next_action="Continue guarded checks." if healthy else "Inspect canonical reconciliation blockers.",
                   components=[{"label": "Canonical broker reconciliation", "status": broker.get("status"),
                                "tone": "online" if healthy else "degraded",
                                "detail": f"Broker observation age {int(age)} seconds; no submission authority granted."},
                               {"label": "New paper-order permission", "status": "Subject to evidence and risk" if runtime_state == "paper-operational" else "Held by operating policy",
                                "tone": "pending" if runtime_state == "paper-operational" else "policy",
                                "detail": "Health is not permission to submit an order."}])
    identity = operator.get("build_identity") or {}
    current = identity.get("current") or {}
    assurance = watchdog.get("unattended_assurance") or {}
    same_release = bool(current.get("git_commit") and
        (assurance.get("release_identity") or {}).get("git_commit") == current["git_commit"])
    watchdog_current = bool(fresh(watchdog.get("observed_at") or assurance.get("observed_at")) and same_release)
    checks = assurance.get("checks") or {}
    if watchdog_current and isinstance(checks.get("trade_notification_monitor_current"), bool):
        healthy = checks["trade_notification_monitor_current"]
        by_id["communications"].update(canonical_probe_verified=True, status="Delivery monitor current" if healthy else "Delivery needs attention",
            tone="online" if healthy else "degraded", metric="Canonical trade-notification monitoring",
            summary="Current delivery monitoring is exported separately from trading decisions.",
            last_checked_at=assurance.get("observed_at"), next_action="Continue receipt monitoring." if healthy else "Inspect durable delivery receipts and retry state.",
            components=[{"label": "Trade notification delivery", "status": "Current" if healthy else "Needs attention",
                         "tone": "online" if healthy else "degraded", "detail": "Provider receipts, not a connectivity-only probe."}])
        covered.add("communications_delivery_health")
    if (fresh(operator.get("generated_at")) and watchdog_current
            and isinstance(checks.get("signed_public_status_current"), bool)):
        healthy = bool(identity.get("committed_release") is True and
            identity.get("running_build_matches_current") is True and
            (identity.get("running") or {}).get("git_commit") == current.get("git_commit") and
            current.get("dirty_worktree") is False and checks["signed_public_status_current"] is True)
        by_id["deployment"].update(canonical_probe_verified=True, status="Build and signed publication verified" if healthy else "Build or publication needs attention",
            tone="online" if healthy else "degraded", metric="Installed build and public-status parity",
            summary="Current reviewed build identity and signed publication receipts replace legacy release-policy labels.",
            observed_deployment_issue=not healthy, last_checked_at=operator.get("generated_at"),
            next_action="Continue release monitoring." if healthy else "Inspect build identity and signed-publication receipts.",
            components=[{"label": "Installed build and signed status", "status": "Verified" if healthy else "Needs attention",
                         "tone": "online" if healthy else "degraded",
                         "detail": "Current operator identity and public-safe status checks; not a profitability claim."}])
        covered.add("current_deployment_and_repository_drift")
    return covered
