from __future__ import annotations

from pathlib import Path

from orchestrator.config import Settings
from orchestrator.qadam_control_plane_bridge import (
    persist_handoff_consumption,
    persist_router_state,
)
from orchestrator.qadam_control_plane_store import ControlPlaneStore


def _settings(tmp_path: Path) -> Settings:
    base = Settings.from_env()
    return Settings(**{**base.__dict__, "runtime_dir": str(tmp_path), "state_root": str(tmp_path)})


def _router_state() -> dict:
    generated = "2026-08-19T14:00:00+00:00"
    return {
        "setups": [
            {
                "setup_id": "setup-1",
                "strategy_family_id": "defence_repricing_geopolitical_watch",
                "research_goal_id": "goal-1",
            }
        ],
        "decisions": [
            {
                "router_decision_id": "decision-1",
                "setup_id": "setup-1",
                "hypothesis_id": "hypothesis-1",
                "evidence_class": "experimental_unvalidated",
                "candidate_identity_id": "candidate-1",
                "decision_generation_id": "generation-1",
                "lineage": {"research_goal_id": "goal-1", "strategy_version_id": "v1"},
                "instrument": "XAR",
                "execution_symbol": "XAR",
                "direction": "long",
                "final_state": "experimental-paper-review-candidate",
                "final_reason": "Every gate passed.",
                "primary_root_cause": None,
                "repair_reasons": [],
                "hard_vetoes": [],
                "hold_reasons": [],
                "gate_snapshot": {
                    "source_quorum_passed": True,
                    "duplicate_exposure_conflict": False,
                    "drawdown_context_complete": True,
                    "drawdown_breached": False,
                    "qctrl_state": "pass",
                    "instrument_paperable": True,
                    "route": "guarded_alpaca_paper_via_paperops",
                    "shadow_promotion_ready": True,
                    "risk_proposal_complete": True,
                    "decision_time_shadow_snapshot_ready": True,
                    "research_lock_release_effective": True,
                },
                "idempotency_material": {"idempotency_key": "key-1"},
                "generated_at": generated,
            }
        ],
    }


def test_router_and_handoff_are_durable_across_empty_cycle(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    state = _router_state()
    assert persist_router_state(state, settings)["status"] == "passed"
    handoff = {
        "paperops_handoff_id": "handoff-1",
        "router_decision_id": "decision-1",
        "candidate_identity_id": "candidate-1",
        "idempotency_material": {"idempotency_key": "key-1"},
    }
    consumer = {
        "accepted_handoffs": [
            {
                "generated_at": "2026-08-19T14:00:01+00:00",
                "source_handoff": handoff,
            }
        ],
        "receipts": [
            {
                "consumption_receipt_id": "receipt-1",
                "paperops_handoff_id": "handoff-1",
                "accepted": True,
                "status": "accepted_for_guarded_paperops_sequence",
                "generated_at": "2026-08-19T14:00:01+00:00",
            }
        ],
    }
    assert persist_handoff_consumption(consumer, settings)["status"] == "passed"
    assert persist_handoff_consumption({"accepted_handoffs": [], "receipts": []}, settings)[
        "status"
    ] == "passed"
    store = ControlPlaneStore.from_settings(settings)
    assert len(store.read_table("handoffs")) == 1
    assert len(store.read_table("handoff_receipts")) == 1
    assert (tmp_path / "qadam_paperops_handoff_v3_accepted.jsonl").read_text().strip()
