from __future__ import annotations

from orchestrator.paperops_30_day_operations import (
    paperops_30_day_operations_public_status,
)


def test_empty_public_status_keeps_submit_regression_counters(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "orchestrator.paperops_30_day_operations.read_latest_paperops_30_day_operations",
        lambda _settings=None: {},
    )

    status = paperops_30_day_operations_public_status()

    assert status["status"] == "not_run"
    for field in (
        "paperops_submit_regression_guard_source_stale_after_post_count",
        "paperops_submit_regression_guard_fresh_submitted_ledger_collision_count",
        "paperops_submit_regression_guard_duplicate_misclassified_as_fresh_count",
        "paperops_submit_regression_guard_validation_error_count",
    ):
        assert status[field] == 0
