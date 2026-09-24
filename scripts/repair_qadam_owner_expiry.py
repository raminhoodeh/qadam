#!/usr/bin/env python3
"""Explicit legacy-incident review with broker GETs only; never submits orders."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operating_ledger import OperatingLedger  # noqa: E402
from scripts.run_paperops_autonomous_pass import (  # noqa: E402
    _acquire_pass_lock, _refresh_and_reconcile_paper_mirror,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-incident-at", required=True, help="Exact execution_state.updated_at reviewed by the operator.")
    args = parser.parse_args()
    settings = Settings.from_env()
    if settings.live_capital_enabled or settings.mode != "paper":
        raise RuntimeError("owner_review_requires_paper_only")
    lock = _acquire_pass_lock(settings)
    if lock is None:
        raise RuntimeError("canonical_pass_already_running")
    ledger = OperatingLedger(settings)
    try:
        with ledger.execution_owner(f"owner-expiry-review:{os.getpid()}") as lease:
            previous = {key: os.environ.get(key) for key in lease.environment()}
            os.environ.update(lease.environment())
            try:
                for _ in range(2):
                    refresh, result = _refresh_and_reconcile_paper_mirror(
                        ledger, phase="owner_expiry_review", bootstrap=False, verify_recovery=False,
                    )
                    if refresh.returncode or result.get("status") != "passed":
                        raise RuntimeError("owner_review_broker_reconciliation_failed")
                receipt = ledger.review_legacy_owner_freeze(incident_at=args.review_incident_at)
                print(json.dumps(receipt, sort_keys=True))
            finally:
                for key, value in previous.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
    finally:
        lock.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
