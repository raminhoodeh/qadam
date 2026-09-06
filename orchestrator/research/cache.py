"""Bounded advisory-only cache; reuse cannot refresh an evidence timestamp."""

from datetime import datetime, timezone
from contextlib import contextmanager
import fcntl
from pathlib import Path
import json

from orchestrator.qadam_operator_ready_common import read_json, sha256_json, write_json_atomic

INTERVAL_SECONDS = 10800


class AnalysisCache:
    def __init__(self, runtime: Path, role: str):
        if role not in {"local", "frontier"}:
            raise ValueError("unreviewed_analysis_cache_role")
        self.path = runtime / ".analysis_cache" / f"{role}.json"

    @contextmanager
    def single_flight(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.with_suffix(".lock").open("a+") as handle:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                yield False
                return
            try:
                yield True
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def key(self, inputs: dict, at: datetime) -> str:
        return sha256_json({"contract": "analysis-cache.1", "inputs": inputs,
                            "real_cycle_slot": int(at.timestamp()) // INTERVAL_SECONDS})

    def get(self, key: str, at: datetime) -> dict | None:
        if not self.path.is_file() or self.path.stat().st_size > 1024 * 1024:
            return None
        record = read_json(self.path)
        try:
            created = datetime.fromisoformat(record["cached_at"])
            age = (at - created).total_seconds()
        except (KeyError, TypeError, ValueError):
            return None
        if record.get("key") != key or not 0 <= age < INTERVAL_SECONDS:
            return None
        result = record.get("result")
        if not isinstance(result, dict):
            return None
        return {**result, "cache_hit": True, "cache_checked_at": at.isoformat(),
                "new_model_inference_performed": False}

    def put(self, key: str, result: dict) -> None:
        if result.get("status") not in {"ok", "accepted"}:
            return
        record = {"key": key, "cached_at": datetime.now(timezone.utc).isoformat(),
                  "result": result, "advisory_only": True}
        if len(json.dumps(record, ensure_ascii=True).encode()) > 1024 * 1024:
            return
        write_json_atomic(self.path, record)
