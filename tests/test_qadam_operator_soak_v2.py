from __future__ import annotations

from orchestrator.qadam_operator_soak_v2 import validate_operator_soak_v2
from orchestrator.qadam_operator_ready_common import authority_flags


def test_soak_cannot_pass_with_fewer_than_seven_real_sessions() -> None:
    soak = {
        "soak_complete": True,
        "completed_real_session_count": 1,
        "simulated_elapsed_time_used": False,
        "authority": authority_flags(),
    }
    release = {
        "release_candidate": False,
        "release_automatically_applied": False,
        "authority": authority_flags(),
    }
    assert "operator_soak_passed_without_seven_real_sessions" in validate_operator_soak_v2(
        soak, release
    )


def test_release_cannot_bypass_incomplete_soak() -> None:
    soak = {
        "soak_complete": False,
        "completed_real_session_count": 1,
        "simulated_elapsed_time_used": False,
        "authority": authority_flags(),
    }
    release = {
        "release_candidate": True,
        "release_automatically_applied": False,
        "authority": authority_flags(),
    }
    assert "paper_release_candidate_without_soak" in validate_operator_soak_v2(
        soak, release
    )
