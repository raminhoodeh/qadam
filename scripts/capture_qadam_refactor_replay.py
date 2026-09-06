#!/usr/bin/env python3
"""Capture bounded private read-only replay inputs, never a new runtime owner.

This is an engineering snapshot, not fresh market evidence or certification.
No credentials, leases, production outbox or database are copied.
"""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from orchestrator.storage.history import read_jsonl_tail  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-runtime", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source, output = args.source_runtime.resolve(), args.output.resolve()
    if output == source or output.is_relative_to(source) or output.exists():
        parser.error("output must be a new directory outside production runtime")
    output.mkdir(mode=0o700, parents=True)
    runtime = output / "data" / "runtime"
    runtime.mkdir(parents=True)
    records, excluded, total = [], [], 0
    for path in sorted(source.iterdir(), key=lambda path: (path.suffix != ".json", path.name)):
        if not path.is_file() or path.is_symlink() or path.suffix not in {".json", ".jsonl"}:
            continue
        if any(word in path.name for word in ("secret", "token", "lease", "outbox", "maintenance", "request")):
            excluded.append({"file": path.name, "reason": "authority_or_private_configuration"})
            continue
        size = path.stat().st_size
        if size > 16 * 1024 * 1024 and path.suffix == ".json":
            excluded.append({"file": path.name, "reason": "size_budget"})
            continue
        try:
            if path.suffix == ".json":
                data = path.read_bytes()
                json.loads(data)
            else:
                # The legacy attribution journal contains individually large records.
                # Keep this exception bounded instead of silently omitting its view.
                budget = (2 * 1024 * 1024 if path.name == "qsase_component_attribution_ledger.jsonl"
                          else 128 * 1024)
                data = b"".join((json.dumps(row, sort_keys=True) + "\n").encode()
                                for row in read_jsonl_tail(path, limit=100, max_bytes=budget))
        except (OSError, ValueError):
            excluded.append({"file": path.name, "reason": "unreadable_or_exceeds_record_budget"})
            continue
        if total + len(data) > 128 * 1024 * 1024:
            excluded.append({"file": path.name, "reason": "total_budget"})
            continue
        (runtime / path.name).write_bytes(data)
        total += len(data)
        records.append({"file": path.name, "sha256": sha256(data).hexdigest(),
                        "bytes": len(data), "source_bytes": size,
                        "history_tail_only": path.suffix == ".jsonl"})
    manifest = {"fixture_only": True, "not_production_evidence": True,
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "files": records, "excluded": excluded, "bytes": total,
                "authority": "none", "coherent_database_snapshot": False,
                "source_json_generations_may_differ": True}
    (output / "capture-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"file_count": len(records), "excluded_count": len(excluded), "bytes": total,
                      "fixture_only": True, "output": str(output)}))


if __name__ == "__main__":
    main()
