"""PLBG-1 and PLBG-2 compatibility entrypoints."""

from orchestrator.qadam_learning_backtest_gap_closure import (
    build_learning_reconciliation,
    build_legacy_inventory,
)

__all__ = ["build_learning_reconciliation", "build_legacy_inventory"]
