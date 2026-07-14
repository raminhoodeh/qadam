from __future__ import annotations

import json

from scripts.check_cockpit_status import _long_backtest_watch_only_lock_active


def test_long_backtest_lock_uses_configured_runtime(monkeypatch, tmp_path) -> None:
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    (runtime_dir / "qadam_long_backtest_lock.json").write_text(
        json.dumps(
            {
                "lock_type": "qadam_next_generation_whole_universe_backfill_backtest",
                "status": "active",
                "paperops_autonomous_runner_paused": True,
                "paperops_watch_only_mode": True,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("QADAM_RUNTIME_DIR", str(runtime_dir))

    assert _long_backtest_watch_only_lock_active() is True
