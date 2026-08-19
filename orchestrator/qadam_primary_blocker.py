"""Collapse dependent failures into one truthful primary decision blocker."""

from __future__ import annotations

from typing import Any, Iterable

from orchestrator.qadam_decision_transaction import PrimaryBlocker

PRECEDENCE = {
    "safety": 0,
    "duplicate": 1,
    "risk": 2,
    "contract_defect": 3,
    "market_session": 4,
    "provider": 5,
    "investment": 6,
    "none": 99,
}


def choose_primary_blocker(blockers: Iterable[dict[str, Any]]) -> PrimaryBlocker | None:
    normalized = [row for row in blockers if row and row.get("blocker_code")]
    if not normalized:
        return None
    selected = min(
        normalized,
        key=lambda row: (
            PRECEDENCE.get(str(row.get("blocker_class") or "investment"), 50),
            str(row.get("blocker_code")),
        ),
    )
    dependent = [
        str(row.get("blocker_code"))
        for row in normalized
        if row is not selected and row.get("blocker_code")
    ]
    return PrimaryBlocker(
        blocker_code=str(selected["blocker_code"]),
        blocker_class=str(selected.get("blocker_class") or "investment"),
        summary=str(selected.get("summary") or selected["blocker_code"]),
        retryable=bool(selected.get("retryable")),
        dependent_consequences=tuple(dict.fromkeys(dependent)),
    )


def blocker_from_execution_status(status: str) -> dict[str, Any] | None:
    mapping = {
        "market_closed": (
            "market_closed",
            "market_session",
            "The paper market is closed; this setup can be reconsidered before its trigger expires.",
            True,
        ),
        "provider_rate_limited": (
            "quote_provider_rate_limited",
            "provider",
            "The current quote provider is rate limited after bounded retries.",
            True,
        ),
        "provider_degraded": (
            "quote_provider_degraded",
            "provider",
            "Current execution measurements could not be retrieved from a provider-backed source.",
            True,
        ),
        "instrument_not_tradable": (
            "paper_proxy_unavailable",
            "investment",
            "No approved guarded Alpaca Paper proxy exists for this instrument.",
            False,
        ),
        "spread_adverse": (
            "current_spread_adverse",
            "investment",
            "The measured spread is too wide for the expected paper-trade edge.",
            True,
        ),
        "execution_context_expired": (
            "execution_context_expired",
            "provider",
            "The current quote expired before the decision reached the Router.",
            True,
        ),
    }
    row = mapping.get(status)
    if row is None:
        return None
    code, blocker_class, summary, retryable = row
    return {
        "blocker_code": code,
        "blocker_class": blocker_class,
        "summary": summary,
        "retryable": retryable,
    }


__all__ = ["blocker_from_execution_status", "choose_primary_blocker"]
