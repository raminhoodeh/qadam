"""Narrow recoverable storage incidents, not arbitrary control-plane errors."""

STORAGE_FREEZE_REASONS = frozenset({
    "pre_paperops_submission_reconciliation_storage_unavailable",
    "post_paperops_submission_reconciliation_storage_unavailable",
})


def storage_reconciliation_freeze(reason: str) -> bool:
    return reason in STORAGE_FREEZE_REASONS
