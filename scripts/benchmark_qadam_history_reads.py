"""Offline R0/R3 history benchmark. No runtime, provider or broker access."""

import json
from math import ceil
from pathlib import Path
from statistics import median
import sys
from tempfile import TemporaryDirectory
import time
import tracemalloc

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from orchestrator.storage.history import tail_lines  # noqa: E402


class CountedReader:
    def __init__(self, source):
        self.source = source
        self.bytes_read = 0

    def read(self, count=-1):
        data = self.source.read(count)
        self.bytes_read += len(data)
        return data

    def seek(self, *args):
        return self.source.seek(*args)


def measure(function, path, expected):
    samples = []
    cpu_samples = []
    bytes_read = []
    peak = 0
    for _ in range(5):
        tracemalloc.start()
        started = time.perf_counter()
        cpu_started = time.process_time()
        with path.open("rb") as source:
            counted = CountedReader(source)
            result = function(counted)
        samples.append(time.perf_counter() - started)
        cpu_samples.append(time.process_time() - cpu_started)
        bytes_read.append(counted.bytes_read)
        peak = max(peak, tracemalloc.get_traced_memory()[1])
        tracemalloc.stop()
        assert result == expected
    return {"median_seconds": median(samples), "p95_seconds": sorted(samples)[ceil(len(samples)*.95)-1],
            "median_cpu_seconds": median(cpu_samples), "peak_traced_bytes": peak,
            "maximum_bytes_read": max(bytes_read), "samples": len(samples), "exact_output_matches": True}


def main():
    config = json.loads((Path(__file__).resolve().parents[1] / "config/qadam_refactor_boundaries.json").read_text())
    contract = config["bounded_history_read"]
    reports = []
    with TemporaryDirectory(prefix="qadam-history-load-") as directory:
        for count in contract["small_row_benchmark_sizes"]:
            path = Path(directory) / "history.jsonl"
            with path.open("wb") as target:
                for index in range(count):
                    target.write(json.dumps({"index": index, "message": "recorded fixture"}).encode() + b"\n")
            expected = [json.dumps({"index": i, "message": "recorded fixture"}).encode() for i in range(count-100, count)]
            old = measure(lambda source: source.read().splitlines()[-100:], path, expected)
            new = measure(lambda source: tail_lines(source, 100), path, expected)
            reports.append({"rows": count, "input_bytes": path.stat().st_size, "baseline": old, "bounded": new,
                "read_budget_passed": new["maximum_bytes_read"] <= contract["read_block_bytes"],
                "allocation_budget_passed": new["peak_traced_bytes"] <= contract["small_row_maximum_traced_bytes"]})
    passed = all(row["read_budget_passed"] and row["allocation_budget_passed"] for row in reports)
    print(json.dumps({"kind": "offline_engineering_benchmark", "production_writes": 0,
        "method": "1x/2x/10x disposable files; warm-cache local reads; five samples; nearest-rank p95",
        "memory_metric": "Python traced allocation, not process RSS", "passed": passed, "reports": reports}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
