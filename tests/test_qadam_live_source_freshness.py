from __future__ import annotations

from orchestrator.qsase_universal_source_price_matrix import _timestamp_for_source
from scripts.run_qadam_live_source_refresh import _cadence_seconds


def test_health_check_timestamp_cannot_masquerade_as_source_evidence():
    assert (
        _timestamp_for_source(
            {"checked_at": "2026-07-18T12:00:00+00:00"},
            "2026-07-18T12:00:01+00:00",
        )
        == ""
    )


def test_provider_observation_timestamp_is_accepted_as_evidence():
    observed_at = "2026-07-18T12:00:00+00:00"
    assert _timestamp_for_source({"provider_observation_at": observed_at}, "ignored") == observed_at


def test_live_source_scheduler_uses_bounded_provider_cadences():
    assert _cadence_seconds("5 minutes during market hours") == 300
    assert _cadence_seconds("hourly") == 3600
    assert _cadence_seconds("weekly or event-driven") == 7 * 86400
