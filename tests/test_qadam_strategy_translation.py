from __future__ import annotations

from dataclasses import replace
import json

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import authority_flags
from orchestrator.qadam_strategy_translation import (
    build_strategy_translation_from_inputs,
    build_strategy_translation_state,
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


def _live_market_context(symbol="SMH", *, move=0.8, volume_ratio=1.1, actionable=True):
    return {
        "recent_packets": [
            {
                "packet_role": "universal_current_market_context",
                "price_volume_context": {
                    "records": [
                        {
                            "symbol": symbol,
                            "provider": "alpaca_market_data_v2_read_only",
                            "provider_backed": True,
                            "percent_move": move,
                            "volume_ratio": volume_ratio,
                            "quote_actionable": actionable,
                            "trade_actionable": False,
                            "session_state": "regular_session" if actionable else "outside_regular_session",
                            "quote_observed_at": NOW,
                        }
                    ]
                },
            }
        ]
    }


def test_conditional_semiconductor_direction_resolves_from_current_event() -> None:
    result = resolve_direction(_score(), [_event()], [], [], generated_at=NOW)
    assert result["raw_research_direction"] == "conditional_policy_asymmetry"
    assert result["actionable_direction"] == "short"
    assert result["evidence_ids"] == ["trigger:semis"]


def test_ambiguous_event_can_use_actionable_live_market_confirmation() -> None:
    result = resolve_direction(
        _score(),
        [_event("ambiguous")],
        [],
        [],
        generated_at=NOW,
        market_context=_live_market_context(),
    )
    assert result["actionable_direction"] == "long"
    assert result["resolver"] == "event_plus_live_market_confirmation_v1"
    assert result["market_confirmation"]["provider_backed"] is True
    assert len(result["evidence_ids"]) == 2


def test_runtime_builder_reads_live_market_context_artifact(tmp_path) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    settings = replace(Settings.from_env(), runtime_dir=str(runtime))
    (runtime / "qadam_pattern_score_v3_records.jsonl").write_text(
        json.dumps(_score()) + "\n", encoding="utf-8"
    )
    (runtime / "qadam_current_event_triggers.jsonl").write_text(
        json.dumps(_event("ambiguous")) + "\n", encoding="utf-8"
    )
    (runtime / "qadam_strategy_evidence_map_v3.json").write_text(
        json.dumps(
            {
                "strategies": [
                    {"strategy_family_id": "semiconductor_policy_options_asymmetry"}
                ]
            }
        ),
        encoding="utf-8",
    )
    (runtime / "qadam_instrument_role_registry.json").write_text(
        json.dumps({"instruments": [{"symbol": "SMH", "paperable": True}]}),
        encoding="utf-8",
    )
    (runtime / "market_context_packet.json").write_text(
        json.dumps(_live_market_context()), encoding="utf-8"
    )

    state = build_strategy_translation_state(settings)

    assert state["resolutions"][0]["actionable_direction"] == "long"


def test_ambiguous_event_cannot_use_out_of_session_market_move() -> None:
    result = resolve_direction(
        _score(),
        [_event("ambiguous")],
        [],
        [],
        generated_at=NOW,
        market_context=_live_market_context(actionable=False),
    )
    assert result["actionable_direction"] == "abstain_direction_unresolved"


def test_ambiguous_event_cannot_use_thin_live_volume() -> None:
    result = resolve_direction(
        _score(),
        [_event("ambiguous")],
        [],
        [],
        generated_at=NOW,
        market_context=_live_market_context(volume_ratio=0.2),
    )
    assert result["actionable_direction"] == "abstain_direction_unresolved"


def test_explicit_direction_conflict_with_live_market_move_abstains() -> None:
    result = resolve_direction(
        _score(direction_hypothesis="upside_under_confirmed_policy"),
        [_event("ambiguous")],
        [],
        [],
        generated_at=NOW,
        market_context=_live_market_context(move=-0.8),
    )
    assert result["actionable_direction"] == "abstain_direction_unresolved"
    assert "conflicts" in result["explanation"]


def test_ambiguous_event_is_scheduled_for_read_only_market_open_retry() -> None:
    state = build_strategy_translation_from_inputs(
        [_score()],
        [_event("ambiguous")],
        [],
        [],
        {"strategies": []},
        {"instruments": []},
        {"strategies": []},
        generated_at=NOW,
        market_context=_live_market_context(actionable=False),
        market_clock={"next_open": "2026-08-10T09:30:00-04:00"},
    )

    retry = state["retries"][0]
    assert retry["state"] == "scheduled_for_next_real_market_open"
    assert retry["retry_after"] == "2026-08-10T09:30:00-04:00"
    assert retry["automatic_retry_scope"] == "read_only_direction_re_evaluation"
    assert retry["broker_write_retry_allowed"] is False
    assert retry["paper_order_created"] is False


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
