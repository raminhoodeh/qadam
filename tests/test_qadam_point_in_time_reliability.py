from __future__ import annotations

import errno
from pathlib import Path

from orchestrator.qadam_point_in_time_evidence import _read_jsonl_partition


def test_partition_read_retries_transient_filesystem_deadlock(
    tmp_path,
    monkeypatch,
) -> None:
    path = tmp_path / "records.jsonl"
    path.write_text('{"row":1}\n', encoding="utf-8")
    original_open = Path.open
    attempts = 0

    def flaky_open(self, *args, **kwargs):
        nonlocal attempts
        if self == path and attempts == 0:
            attempts += 1
            raise OSError(errno.EDEADLK, "Resource deadlock avoided")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", flaky_open)
    assert _read_jsonl_partition(path) == [{"row": 1}]
    assert attempts == 1


def test_partition_read_does_not_hide_nonretryable_error(tmp_path, monkeypatch) -> None:
    path = tmp_path / "records.jsonl"
    path.write_text('{"row":1}\n', encoding="utf-8")
    original_open = Path.open

    def denied_open(self, *args, **kwargs):
        if self == path:
            raise OSError(errno.EACCES, "Permission denied")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", denied_open)
    try:
        _read_jsonl_partition(path)
    except OSError as exc:
        assert exc.errno == errno.EACCES
    else:
        raise AssertionError("nonretryable partition error must remain visible")
