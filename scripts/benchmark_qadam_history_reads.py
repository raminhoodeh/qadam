"""Offline R0/R3 history benchmark. No runtime, provider or broker access."""

import io
import json
from pathlib import Path
from statistics import median
import sys
import time
import tracemalloc

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from orchestrator.storage.history import tail_lines  # noqa: E402


def measure(function, data):
    samples = []
    peak = 0
    for _ in range(5):
        tracemalloc.start()
        started = time.perf_counter()
        result = function(data)
        samples.append(time.perf_counter() - started)
        peak = max(peak, tracemalloc.get_traced_memory()[1])
        tracemalloc.stop()
        assert len(result) == 100
    return {"median_seconds": median(samples), "peak_traced_bytes": peak, "samples": len(samples)}


def main():
    reports = []
    for count in (10_000, 20_000, 100_000):
        data = b'{"index":123,"message":"recorded fixture"}\n' * count
        old = measure(lambda b: b.decode().splitlines()[-100:], data)
        new = measure(lambda b: tail_lines(io.BytesIO(b), 100), data)
        reports.append({"rows": count, "input_bytes": len(data), "baseline": old, "bounded": new})
    print(json.dumps({"kind": "offline_engineering_benchmark", "production_writes": 0, "reports": reports}, indent=2))


if __name__ == "__main__":
    main()
