from __future__ import annotations

from orchestrator.qadam_clean_epoch_certification import (
    validate_clean_epoch_certification,
)
from orchestrator.qadam_operator_ready_common import authority_flags


def test_certification_cannot_pass_without_edge_and_clean_epoch() -> None:
    state = {
        "certification": {
            "operational_launch_ready": True,
            "validated_edge_count": 0,
            "clean_epoch_active": False,
            "testing_epoch_archived": False,
            "thresholds_relaxed_to_force_edge": False,
            "paper_calendar_advanced": False,
            "authority": authority_flags(),
        },
        "dynamic_status": {"authority": authority_flags()},
    }
    errors = validate_clean_epoch_certification(state)
    assert "clean_epoch_certified_without_validated_edge" in errors
    assert "clean_epoch_certified_without_clean_epoch" in errors
    assert "clean_epoch_certified_without_testing_archive" in errors


def test_blocked_state_is_valid_when_thresholds_remain_frozen() -> None:
    state = {
        "certification": {
            "operational_launch_ready": False,
            "validated_edge_count": 0,
            "clean_epoch_active": False,
            "testing_epoch_archived": False,
            "thresholds_relaxed_to_force_edge": False,
            "paper_calendar_advanced": False,
            "authority": authority_flags(),
        },
        "dynamic_status": {"authority": authority_flags()},
    }
    assert validate_clean_epoch_certification(state) == []
