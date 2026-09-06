"""Bounded recent-history reads; no whole-file load for a small tail query."""

import json
from pathlib import Path
from typing import Any, BinaryIO


class HistoryReadLimitError(ValueError):
    """The requested history exceeds its explicit byte budget."""


def tail_lines(
    source: BinaryIO, limit: int, *, max_bytes: int = 32 * 1024 * 1024,
    block_bytes: int = 64 * 1024,
) -> list[bytes]:
    if limit < 0 or max_bytes <= 0 or block_bytes <= 0:
        raise ValueError("invalid_history_read_budget")
    if limit == 0:
        return []
    end = source.seek(0, 2)
    chunks = []
    size = 0
    newline_count = 0
    while end > 0 and newline_count <= limit:
        count = min(end, block_bytes, max_bytes - size)
        if count <= 0:
            raise HistoryReadLimitError("history_tail_exceeds_byte_budget")
        end -= count
        source.seek(end)
        chunk = source.read(count)
        if len(chunk) != count:
            raise OSError("history_changed_during_read")
        chunks.append(chunk)
        size += count
        newline_count += chunk.count(b"\n")
    return b"".join(reversed(chunks)).splitlines()[-limit:]


def read_jsonl_tail(path: Path, limit: int, *, max_bytes: int = 32 * 1024 * 1024) -> list[dict[str, Any]]:
    with path.open("rb") as source:
        lines = tail_lines(source, limit, max_bytes=max_bytes)
    rows = []
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            # An incomplete append cannot become a completed history record.
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows
