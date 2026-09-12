#!/usr/bin/env python3
"""Run verified telemetry retention and optionally review a legacy storage freeze."""

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.execution.ledger import OperatingLedger  # noqa: E402
from orchestrator.qadam_operator_ready_common import read_json, runtime_dir  # noqa: E402
from orchestrator.qadam_storage_retention import run_storage_maintenance, validate_storage_status  # noqa: E402
from orchestrator.runtime.operator import reclassify_recorded_failures  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-legacy-freeze", action="store_true")
    args = parser.parse_args()
    runtime = runtime_dir(Settings.from_env())
    if args.review_legacy_freeze and read_json(runtime / "qadam_operator_maintenance_window.json").get("status") != "active":
        raise RuntimeError("legacy_storage_review_requires_maintenance_guard")
    status = run_storage_maintenance(runtime, force=True)
    errors = validate_storage_status(status)
    print(json.dumps({"storage_status": status["status"], "control_plane": status.get("control_plane"), "errors": errors}))
    if errors:
        return 1
    print(json.dumps({"reclassified": reclassify_recorded_failures(runtime)}))
    reviewed = False
    if args.review_legacy_freeze:
        ledger = OperatingLedger()
        with ledger.execution_owner(f"storage-review:{os.getpid()}") as lease:
            previous = {key: os.environ.get(key) for key in lease.environment()}
            os.environ.update(lease.environment())
            try:
                with (runtime / "qadam_operator_service_receipts.jsonl").open() as stream:
                    for line in stream:
                        receipt = json.loads(line)
                        if receipt.get("service_id") == "guarded_paperops" and receipt.get("state") == "failed":
                            if ledger.review_legacy_storage_freeze(receipt):
                                reviewed = True
                                break
            finally:
                for key, value in previous.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
    print(json.dumps({"legacy_storage_freeze_reviewed": reviewed, "broker_write_count": 0}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
