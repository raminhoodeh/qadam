"""Narrow recovery classification; ownership conflicts never become retries."""

RECONCILIATION_PHASES = ("pre_paperops_submission", "post_paperops_submission")


def owner_expiry_freeze(reason: str) -> bool:
    return reason in {
        f"{phase}_reconciliation_owner_lease_expired"
        for phase in RECONCILIATION_PHASES
    }
