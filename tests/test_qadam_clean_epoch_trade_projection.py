from __future__ import annotations

from types import SimpleNamespace

from orchestrator.cockpit_status import _legacy_fixture_trade_intent


def test_legacy_d5_fixture_is_identified_for_clean_epoch_projection() -> None:
    fixture = SimpleNamespace(
        source_type="d5_contract_fixture",
        tags=("d5_fixture", "paper_mode"),
    )
    current = SimpleNamespace(
        source_type="qadam_strategy_foundry_v3",
        tags=("paper_only",),
    )

    assert _legacy_fixture_trade_intent(fixture) is True
    assert _legacy_fixture_trade_intent(current) is False
