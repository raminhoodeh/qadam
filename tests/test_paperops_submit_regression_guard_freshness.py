from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from orchestrator.config import Settings
from orchestrator import paperops_submit_regression_guard as module


def test_guard_rebuilds_current_paperops_view_instead_of_reusing_latest(
    tmp_path: Path,
    monkeypatch,
) -> None:
    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path))
    calls: list[bool] = []

    def _build(*, settings: Settings, execute_post: bool):
        calls.append(execute_post)
        return {
            "artifact_id": "paperops-current",
            "status": "ready_pending_explicit_execute",
            "generated_at": "2026-08-19T16:00:00+00:00",
            "post_candidates": [],
            "source_eligible_submit_record_count": 0,
            "fresh_eligible_submit_record_count": 0,
            "duplicate_submit_record_count": 0,
            "idempotency_ledger_active": True,
            "live_capital_enabled": False,
            "live_endpoint_called_count": 0,
        }

    monkeypatch.setattr(module, "build_paperops_alpaca_paper_post", _build)
    monkeypatch.setattr(module, "validate_paperops_alpaca_paper_post", lambda _: [])
    monkeypatch.setattr(module, "_source_artifacts", lambda _: [])
    monkeypatch.setattr(
        module,
        "_submission_ledger",
        lambda _: {
            "submitted_client_order_ids": [],
            "submitted_source_idempotency_keys": [],
        },
    )

    artifact = module.build_paperops_submit_regression_guard(settings=settings)

    assert calls == [False]
    assert artifact["source_paperops2_artifact_id"] == "paperops-current"
    assert artifact["status"] == "healthy_idle_no_fresh_submit"
