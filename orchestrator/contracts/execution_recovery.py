"""Narrow recovery classification; ownership conflicts never become retries."""

RECONCILIATION_PHASES = (
    "pre_paperops_submission", "post_paperops_submission", "incident_recovery", "immediate_post_entry",
)


def owner_expiry_freeze(reason: str) -> bool:
    return reason in {
        f"{phase}_reconciliation_owner_lease_expired"
        for phase in RECONCILIATION_PHASES
    }


def freeze_contract(reason: str) -> tuple[str, bool]:
    """Compatibility import of known causes; unknown errors never grant recovery.

    Recovery still requires current-owner, fresh, agreeing broker observations.
    This classifies a hold, not permission to submit an order.
    """
    from orchestrator.contracts.broker_history import history_allocation_freeze
    from orchestrator.contracts.storage_recovery import storage_reconciliation_freeze

    if history_allocation_freeze(reason):
        return "allocation_history_pending", True
    if storage_reconciliation_freeze(reason):
        return "storage_unavailable", True
    if owner_expiry_freeze(reason):
        return "owner_lease_expired", True
    if reason in {f"{phase}_paper_mirror_refresh_failed" for phase in RECONCILIATION_PHASES}:
        return "broker_read_unavailable", True
    if reason in {
        "broker_reconciliation_disagreement:paper_account_mirror_stale",
        "broker_reconciliation_disagreement:paper_account_mirror_missing",
    }:
        return "broker_read_unavailable", True
    if reason.startswith("ambiguous_order_submission:"):
        return "ambiguous_submission", True
    return "review_required", False
