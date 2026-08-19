from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from orchestrator.config import Settings
from orchestrator.qadam_catc_audits import audit_atomic_decisions
from orchestrator.qadam_control_plane_store import ControlPlaneStore
from orchestrator.qadam_decision_transaction import (
    DecisionTransaction,
    Direction,
    GateDecision,
    GateSeverity,
    GateState,
    PrimaryBlocker,
    RouterState,
)


def _settings(tmp_path: Path) -> Settings:
    base = Settings.from_env()
    return Settings(**{**base.__dict__, "runtime_dir": str(tmp_path), "state_root": str(tmp_path)})


def test_atomic_audit_validates_sqlite_json_at_the_persistence_boundary(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    timestamp = datetime.now(timezone.utc).isoformat()
    transaction = DecisionTransaction(
        decision_id="decision-1",
        generation_id="generation-1",
        candidate_identity="candidate-1",
        idempotency_key="idempotency-1",
        research_goal_id="goal-1",
        evidence_class="experimental_unvalidated",
        strategy_id="strategy-1",
        strategy_version="v1",
        instrument="XAR",
        direction=Direction.LONG,
        stage="router_terminal",
        created_at=timestamp,
        updated_at=timestamp,
        trigger={"trigger_id": "trigger-1"},
        gate_decisions=(
            GateDecision(
                gate_decision_id="gate-1",
                gate_name="source_quorum_passed",
                sequence=0,
                state=GateState.HOLD,
                severity=GateSeverity.HARD,
                measured_value=False,
                threshold=True,
                explanation="Required source quorum is not yet complete.",
                size_haircut=1.0,
                evidence_ids=("evidence-1",),
            ),
        ),
        primary_blocker=PrimaryBlocker(
            blocker_code="source_quorum_incomplete",
            blocker_class="investment",
            summary="Required source quorum is not yet complete.",
            retryable=True,
            dependent_consequences=("risk_review_not_reached",),
        ),
        router_state=RouterState.HOLD,
    )
    ControlPlaneStore.from_settings(settings).create_decision(transaction)

    result = audit_atomic_decisions(settings)

    assert result["status"] == "passed"
    assert result["stored_decision_count"] == 1
    assert result["decision_generation_count"] == 1
    assert result["validation_errors"] == []
