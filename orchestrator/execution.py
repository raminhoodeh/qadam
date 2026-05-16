"""Execution venue registry.

The foundation phase exposes venue state but keeps every write path blocked.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

VenueMode = Literal["disabled", "read_only", "paper", "live_blocked", "live"]


@dataclass(frozen=True)
class ExecutionVenue:
    key: str
    name: str
    adapter: str
    mode: VenueMode
    first_release_allowed: bool
    account_scope: str
    network_scope: str
    credential_status: str
    permissions_status: str
    read_health: str
    write_health: str
    kill_switch_status: str
    last_reconciliation_at: str | None
    notes: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def default_execution_venues() -> tuple[ExecutionVenue, ...]:
    """Return the first foundation registry for future venue adapters."""
    return (
        ExecutionVenue(
            key="alpaca_paper",
            name="Alpaca Paper Account",
            adapter="alpaca",
            mode="disabled",
            first_release_allowed=True,
            account_scope="paper",
            network_scope="equities/options",
            credential_status="missing",
            permissions_status="not_checked",
            read_health="not_started",
            write_health="blocked_foundation_phase",
            kill_switch_status="armed",
            last_reconciliation_at=None,
            notes="Intended first-release paper venue once Phase 5 gates are built.",
        ),
        ExecutionVenue(
            key="prediction_market_router",
            name="Prediction Market Router",
            adapter="pmxt_polyrouter",
            mode="disabled",
            first_release_allowed=True,
            account_scope="paper_or_read_only_first",
            network_scope="polymarket/kalshi",
            credential_status="missing",
            permissions_status="not_checked",
            read_health="not_started",
            write_health="blocked_foundation_phase",
            kill_switch_status="armed",
            last_reconciliation_at=None,
            notes="Read-only market discovery comes before any guarded execution path.",
        ),
        ExecutionVenue(
            key="privex_base",
            name="PriveX Base Perps",
            adapter="privex",
            mode="live_blocked",
            first_release_allowed=False,
            account_scope="delegated_subaccount_required",
            network_scope="base:8453",
            credential_status="not_configured",
            permissions_status="not_checked",
            read_health="not_started",
            write_health="blocked_first_release",
            kill_switch_status="armed",
            last_reconciliation_at=None,
            notes="Optional later execution rail reference. Not part of the GBP 1000 v1 test run.",
        ),
        ExecutionVenue(
            key="privex_coti",
            name="PriveX COTI Perps",
            adapter="privex",
            mode="live_blocked",
            first_release_allowed=False,
            account_scope="delegated_subaccount_required",
            network_scope="coti:2632500",
            credential_status="not_configured",
            permissions_status="not_checked",
            read_health="not_started",
            write_health="blocked_first_release",
            kill_switch_status="armed",
            last_reconciliation_at=None,
            notes="Optional later execution rail reference. Requires explicit paper/sandbox approval.",
        ),
    )


def execution_registry() -> list[dict[str, object]]:
    return [venue.to_dict() for venue in default_execution_venues()]
