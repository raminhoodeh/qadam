from __future__ import annotations

from orchestrator.qadam_clean_epoch_operating import (
    validate_clean_epoch_operating_status,
)
from orchestrator.qadam_operator_ready_common import authority_flags


def _payload() -> dict[str, object]:
    return {
        "post_launch_monitoring_active": False,
        "paper_epoch_kind": "legacy_test",
        "epoch_mismatched_lineage_count": 0,
        "proof_epoch_leak_count": 0,
        "unsafe_applied_improvement_count": 0,
        "proof_credit_created_count": 0,
        "forced_trade_allowed": False,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }


def test_prelaunch_monitor_state_is_valid() -> None:
    assert validate_clean_epoch_operating_status(_payload()) == []


def test_proof_epoch_leak_fails_closed() -> None:
    payload = _payload()
    payload["proof_epoch_leak_count"] = 1
    assert (
        "clean_epoch_operating_forbidden_count:proof_epoch_leak_count"
        in validate_clean_epoch_operating_status(payload)
    )
