from __future__ import annotations

from dataclasses import replace

from orchestrator.config import Settings
from scripts.run_paperops_autonomous_pass import _acquire_pass_lock


def test_canonical_pass_lock_rejects_overlapping_runner(tmp_path) -> None:
    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path))
    first = _acquire_pass_lock(settings)
    assert first is not None
    try:
        assert _acquire_pass_lock(settings) is None
    finally:
        first.close()

    second = _acquire_pass_lock(settings)
    assert second is not None
    second.close()
