from __future__ import annotations

from orchestrator.qadam_operator_ready_common import authority_flags
from orchestrator.qadam_strategy_translation import (
    build_strategy_translation_from_inputs,
    resolve_direction,
    validate_strategy_translation,
)

NOW = "2026-08-08T12:00:00+00:00"


def _score(**overrides):
    row = {
        "score_id": "score:semis",
        "strategy_family_id": "semiconductor_policy_options_asymmetry",
        "strategy_agnostic": False,
        "instrument": "SMH",
        "horizon_hypothesis": "5d_forward",
        "direction_hypothesis": "conditional_policy_asymmetry",
        "negative_control": False,
    }
    row.update(overrides)
    return row


def _event(direction="negative_for_strategy_expression"):
    return {
        "trigger_id": "trigger:semis",
        "trigger_state": "active",
        "sample_or_fixture": False,
        "strategy_family_id": "semiconductor_policy_options_asymmetry",
        "affected_instruments": ["SMH"],
        "direction_clue": direction,
        "available_at": NOW,
        "invalidation_clues": ["event reverses"],
        "authority": authority_flags(),
    }


def test_conditional_semiconductor_direction_resolves_from_current_event() -> None:
    result = resolve_direction(_score(), [_event()], [], [], generated_at=NOW)
    assert result["raw_research_direction"] == "conditional_policy_asymmetry"
    assert result["actionable_direction"] == "short"
    assert result["evidence_ids"] == ["trigger:semis"]


def test_inactive_silver_regime_abstains_instead_of_guessing_long() -> None:
    score = _score(
        score_id="score:silver",
        strategy_family_id="silver_macro_liquidity_stress",
        instrument="SIL",
        direction_hypothesis="upside_under_confirmed_liquidity_stress",
    )
    regime = {
        "regime_id": "regime:silver",
        "strategy_family_id": "silver_macro_liquidity_stress",
        "regime_state": "inactive",
        "direction_clue": "long",
        "available_at": NOW,
    }
    result = resolve_direction(score, [], [regime], [], generated_at=NOW)
    assert result["actionable_direction"] == "abstain_direction_unresolved"
    assert "inactive" in result["explanation"]


def test_negative_controls_never_resolve_or_form_strategies() -> None:
    score = _score(negative_control=True)
    state = build_strategy_translation_from_inputs(
        [score],
        [_event()],
        [],
        [],
        {"strategies": []},
        {"instruments": []},
        {"strategies": []},
        generated_at=NOW,
    )
    assert state["resolutions"] == []
    assert state["formations"] == []
    assert (
        "negative_control_cannot_resolve_direction_or_form_strategy"
        in state["rejections"][0]["reasons"]
    )
    assert validate_strategy_translation(state) == []
