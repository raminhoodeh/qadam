from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_evidence_contracts import (
    build_lane_contribution,
    lane_capability_index,
    validate_lane_contribution,
)
from orchestrator.qadam_lane_conversion import build_lane_conversion
import orchestrator.qadam_lane_reachability as lane_reachability
import orchestrator.qadam_lane_trigger_fast_path as lane_fast_path


def _settings(tmp_path: Path) -> Settings:
    return replace(Settings.from_env(), runtime_dir=str(tmp_path))


def test_lane_registry_assigns_stage_authority_not_broker_authority() -> None:
    lanes = lane_capability_index()
    assert lanes["strategy_informed"]["maximum_authority"] == "A4"
    assert lanes["strategy_agnostic"]["maximum_authority"] == "A4"
    assert lanes["qualitative_agent_reach"]["maximum_authority"] == "A2"
    assert lanes["portfolio_risk_router"]["maximum_authority"] == "A5"
    assert lanes["guarded_paperops"]["maximum_authority"] == "A6"
    assert all(row["direct_broker_authority"] is False for row in lanes.values())


def test_research_lane_cannot_escalate_itself_to_governance() -> None:
    record = build_lane_contribution(
        lane_id="qualitative_agent_reach",
        contribution_state="paper_review_nominated",
        authority_tier="A5",
        evidence_profile="qualitative_context_catalyst",
        subject={"hypothesis_id": "probe"},
        evidence_refs=["evidence:probe"],
        generation_id="generation:probe",
        observed_at="2026-08-15T00:00:00+00:00",
        expires_at=None,
        canonical_draft={"hypothesis_id": "probe"},
    )
    assert "lane_contribution_authority_exceeds_capability" in validate_lane_contribution(record)


def test_validated_qualitative_draft_uses_strategy_lane_for_a4(
    tmp_path: Path,
) -> None:
    store = AtomicArtifactStore(tmp_path)
    store.write_jsonl("qadam_strategy_drafts_v3.jsonl", [])
    store.write_jsonl("qadam_qualitative_claims.jsonl", [])
    store.write_jsonl("qadam_qualitative_pattern_candidates.jsonl", [])
    store.write_json(
        "qadam_prediction_market_research.json",
        {"generated_at": "2026-08-15T00:00:00+00:00", "disagreements": []},
    )
    canonical_draft = {
        "hypothesis_id": "strategy-hypothesis:qualitative-probe",
        "generated_at": "2026-08-15T00:00:00+00:00",
        "candidate_identity_material": {"candidate_identity_id": "candidate:probe"},
        "strategy_mapping": {"strategy_family_id": "crude_oil_energy_security_disruption"},
        "instrument_proxy_mapping": {"execution_proxy": "USO"},
        "direction_horizon": {"direction": "long", "horizon": "3d_forward"},
        "freshness": {"latest_supporting_sample": "2026-08-15T00:00:00+00:00"},
    }
    store.write_jsonl(
        "qadam_qualitative_strategy_impacts.jsonl",
        [
            {
                "pattern_id": "pattern:probe",
                "core_family_refinement": "crude_oil_energy_security_disruption",
                "canonical_draft": canonical_draft,
            }
        ],
    )
    result, errors = build_lane_conversion(_settings(tmp_path))
    assert errors == []
    promoted = next(
        row
        for row in result["contributions"]
        if row.get("subject", {}).get("hypothesis_id") == canonical_draft["hypothesis_id"]
    )
    assert promoted["lane_id"] == "strategy_informed"
    assert promoted["authority_tier"] == "A4"
    assert validate_lane_contribution(promoted) == []


def test_reachability_converges_a4_chain_before_reading_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    settings = _settings(tmp_path)
    contribution = build_lane_contribution(
        lane_id="strategy_informed",
        contribution_state="paper_review_nominated",
        authority_tier="A4",
        evidence_profile="validated_pattern",
        subject={"hypothesis_id": "strategy-hypothesis:probe"},
        evidence_refs=["evidence:probe"],
        generation_id="generation:probe",
        observed_at="2026-08-15T00:00:00+00:00",
        expires_at=None,
        canonical_draft={"hypothesis_id": "strategy-hypothesis:probe"},
    )
    calls: list[str] = []

    def _converge(*_args, **_kwargs):
        calls.append("fast_path")
        store = AtomicArtifactStore(tmp_path)
        store.write_jsonl("qadam_lane_contributions.jsonl", [contribution])
        store.write_jsonl(
            "qadam_tradeability_envelopes.jsonl",
            [{"identity": {"hypothesis_id": "strategy-hypothesis:probe"}}],
        )
        store.write_jsonl(
            "qadam_akber_filter_v3_results.jsonl",
            [{"hypothesis_id": "strategy-hypothesis:probe"}],
        )
        store.write_jsonl(
            "qadam_forward_shadow_decisions.jsonl",
            [{"hypothesis_id": "strategy-hypothesis:probe"}],
        )
        store.write_jsonl(
            "qadam_router_v3_decisions.jsonl",
            [{"hypothesis_id": "strategy-hypothesis:probe", "paperops_handoff_allowed": False}],
        )
        return {"status": "completed"}, []

    monkeypatch.setattr(lane_fast_path, "run_lane_trigger_fast_path", _converge)
    monkeypatch.setattr(
        lane_reachability,
        "build_and_write_golden_journeys",
        lambda *_args, **_kwargs: (
            {"status": "passed", "journey_count": 1, "passed_count": 1},
            {"status": "passed"},
            [],
        ),
    )
    monkeypatch.setattr(
        lane_reachability,
        "build_and_write_reachability_canary",
        lambda *_args, **_kwargs: (
            {"status": "passed"},
            {"status": "passed", "accepted_broker_disabled_handoff_count": 1},
            [],
        ),
    )

    result, errors = lane_reachability.build_lane_reachability(settings)

    assert calls == ["fast_path"]
    assert errors == []
    assert result["a4_reached_envelope_count"] == 1
    assert result["a4_reached_akber_count"] == 1
    assert result["a4_reached_shadow_count"] == 1
    assert result["a4_reached_router_count"] == 1
