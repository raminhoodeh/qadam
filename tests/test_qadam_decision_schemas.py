from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from orchestrator.qadam_decision_transaction import (
    DecisionTransaction,
    Direction,
    ExecutionContext,
)


def test_strict_transaction_rejects_undeclared_fields() -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    with pytest.raises(ValidationError, match="extra_forbidden"):
        DecisionTransaction.model_validate(
            {
                "decision_id": "decision-1",
                "generation_id": "generation-1",
                "candidate_identity": "candidate-1",
                "idempotency_key": "key-1",
                "research_goal_id": "goal-1",
                "evidence_class": "discovery_micro",
                "strategy_id": "strategy-1",
                "strategy_version": "v1",
                "instrument": "SPY",
                "direction": Direction.LONG,
                "stage": "trigger_compiled",
                "created_at": timestamp,
                "updated_at": timestamp,
                "trigger": {},
                "implicit_default": True,
            }
        )


def test_quote_ready_requires_bid_ask_and_midpoint() -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    with pytest.raises(ValidationError, match="quote_ready_requires_bid_ask_midpoint"):
        ExecutionContext(
            context_id="context-1",
            instrument="SPY",
            provider="alpaca_paper_market_data",
            status="quote_ready",
            observed_at=timestamp,
            expires_at=timestamp,
            provenance={"provider_backed": True},
        )
