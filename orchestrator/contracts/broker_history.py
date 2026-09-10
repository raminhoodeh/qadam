"""Narrow recovery classification; never permission to submit or unfreeze."""


def history_allocation_only(blockers: list[str]) -> bool:
    return bool(blockers) and all(
        str(item).startswith("position_entry_allocation_unresolved:")
        and bool(str(item).split(":", 1)[1])
        for item in blockers
    )


def history_allocation_freeze(reason: str) -> bool:
    prefix = "broker_reconciliation_disagreement:"
    return reason.startswith(prefix) and history_allocation_only(
        reason.removeprefix(prefix).split(",")
    )
