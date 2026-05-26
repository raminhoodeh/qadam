"""Canonical active-release operating facts for Qadam."""

from __future__ import annotations

PAPER_ACCOUNT_BALANCE_GBP = 100_000
PAPER_ACCOUNT_SCOPE = "first_release_gbp_100000_paper"
PAPER_OPERATIONAL_MAX_NOTIONAL_GBP = 1_000

PHASE7_HARNESS_DAY_COUNT = 30
PHASE7_WEEKLY_PROOF_TRADE_TARGET = 3
PHASE7_MATURE_CLOSED_TRADE_BENCHMARK = 100

LIVE_CAPITAL_ENABLED = False

PAPER_ACCOUNT_CAPITAL_POLICY = (
    "The first-release paper account has GBP 100,000 available. "
    "Any GBP 1,000 value is a separate single-order/notional risk cap, "
    "not the account balance."
)
