from __future__ import annotations

from orchestrator.qadam_dashboard_epoch_isolation import (
    validate_dashboard_epoch_isolation,
)
from orchestrator.qadam_operator_ready_common import authority_flags


def test_legacy_epoch_is_not_falsely_treated_as_clean() -> None:
    payload = {
        "clean_epoch_active": False,
        "validation_errors": [],
        "archived_identifier_leak_count": 0,
        "epoch_mismatched_row_count": 0,
        "authority": authority_flags(),
    }
    assert validate_dashboard_epoch_isolation(payload) == []


def test_clean_epoch_identifier_leak_fails() -> None:
    payload = {
        "clean_epoch_active": True,
        "validation_errors": [],
        "archived_identifier_leak_count": 1,
        "epoch_mismatched_row_count": 0,
        "authority": authority_flags(),
    }
    assert "dashboard_archive_identifier_leak" in validate_dashboard_epoch_isolation(
        payload
    )
