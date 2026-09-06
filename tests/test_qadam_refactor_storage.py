from concurrent.futures import ThreadPoolExecutor
import gzip
import json
from threading import Event

import pytest

from orchestrator import qadam_storage_retention as retention
from orchestrator.qadam_operator_ready_common import append_jsonl_durable
from orchestrator.runtime.builds import reviewed_source_state, _digest


def test_archive_failure_keeps_original_live_history(tmp_path, monkeypatch):
    path = tmp_path / "history.jsonl"
    for index in range(4):
        append_jsonl_durable(path, {"index": index})
    original = path.read_bytes()
    monkeypatch.setattr(retention, "_hash_stream", lambda _: "corrupt")
    with pytest.raises(RuntimeError, match="verification_failed"):
        retention._rotate_jsonl_prefix(tmp_path, path, retain_lines=2)
    assert path.read_bytes() == original


def test_append_during_rotation_is_not_lost(tmp_path, monkeypatch):
    path = tmp_path / "history.jsonl"
    for index in range(4):
        append_jsonl_durable(path, {"index": index})
    verifying, release = Event(), Event()
    original = retention._hash_stream

    def verify(stream):
        verifying.set()
        assert release.wait(5)
        return original(stream)

    monkeypatch.setattr(retention, "_hash_stream", verify)
    with ThreadPoolExecutor(max_workers=2) as pool:
        rotate = pool.submit(retention._rotate_jsonl_prefix, tmp_path, path, retain_lines=2)
        assert verifying.wait(5)
        append = pool.submit(append_jsonl_durable, path, {"index": 4})
        release.set()
        rotate.result(timeout=5)
        append.result(timeout=5)
    archived = b"".join(gzip.decompress(archive.read_bytes()) for archive in sorted(tmp_path.rglob("*.gz")))
    assert [json.loads(line)["index"] for line in (archived + path.read_bytes()).splitlines()] == list(range(5))


def test_nested_code_and_policy_change_identity_but_runtime_data_does_not(tmp_path):
    source = tmp_path / "orchestrator" / "nested" / "module.py"
    source.parent.mkdir(parents=True)
    source.write_text("x = 1\n")
    policy = tmp_path / "config" / "policy.json"
    policy.parent.mkdir()
    policy.write_text('{"version": 1}')
    before = reviewed_source_state(tmp_path)
    misses = _digest.cache_info().misses
    assert reviewed_source_state(tmp_path) == before
    assert _digest.cache_info().misses == misses
    runtime = tmp_path / "data" / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "data.json").write_text('{}')
    assert reviewed_source_state(tmp_path) == before
    source.write_text("x = 2\n")
    assert reviewed_source_state(tmp_path) != before
    after = reviewed_source_state(tmp_path)
    policy.write_text('{"version": 2}')
    assert reviewed_source_state(tmp_path) != after
