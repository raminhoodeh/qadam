from __future__ import annotations

from dataclasses import replace

from orchestrator.config import Settings
from orchestrator.qadam_state_root import build_state_root_preflight


def test_local_ignored_state_root_supports_atomic_replace_and_locks(tmp_path) -> None:
    settings = replace(
        Settings.from_env(),
        state_root=str(tmp_path),
        runtime_dir=str(tmp_path / "runtime"),
        data_root=str(tmp_path),
    )
    result = build_state_root_preflight(settings)
    assert result["atomic_replace_supported"] is True
    assert result["advisory_lock_supported"] is True
    assert result["cloud_placeholder_detected"] is False
    assert result["paper_order_created_count"] == 0
