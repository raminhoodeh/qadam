import io
import json

import pytest

from orchestrator.storage.history import HistoryReadLimitError, read_jsonl_tail, tail_lines


class CountedReader(io.BytesIO):
    read_bytes = 0

    def read(self, count=-1):
        result = super().read(count)
        self.read_bytes += len(result)
        return result


@pytest.mark.parametrize("count", [10_000, 20_000, 100_000])
def test_tail_read_cost_does_not_scale_with_total_history(count):
    source = CountedReader(b'{"value":123}\n' * count)
    assert len(tail_lines(source, 100)) == 100
    assert source.read_bytes <= 64 * 1024


@pytest.mark.parametrize("ending", ["", "\n", "\n\n"])
def test_tail_matches_existing_line_selection(tmp_path, ending):
    path = tmp_path / "history.jsonl"
    content = "\n".join(json.dumps({"index": i, "text": "caf\u00e9"}) for i in range(500)) + ending
    path.write_text(content)
    expected = [json.loads(x) for x in content.splitlines()[-100:] if x.strip()]
    assert read_jsonl_tail(path, 100) == expected


def test_invalid_partial_tail_and_non_records_are_not_evidence(tmp_path):
    path = tmp_path / "history.jsonl"
    path.write_text('{"index":1}\nnull\n[1]\n{"index":')
    assert read_jsonl_tail(path, 5) == [{"index": 1}]


def test_oversized_request_is_explicit_not_silent_empty_history():
    with pytest.raises(HistoryReadLimitError):
        tail_lines(io.BytesIO(b"x" * 1024), 1, max_bytes=100, block_bytes=20)


def test_zero_and_negative_limits():
    assert tail_lines(io.BytesIO(b"one\n"), 0) == []
    with pytest.raises(ValueError):
        tail_lines(io.BytesIO(), -1)
