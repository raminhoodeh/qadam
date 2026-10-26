#!/usr/bin/env python3
"""Reconcile canonical paper state while entries are held; broker GETs only."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.execution.ledger import OperatingLedger  # noqa: E402
from orchestrator.runtime.command import report_work_result  # noqa: E402
from orchestrator.qadam_operator_ready_common import now_iso  # noqa: E402
from scripts.run_paperops_autonomous_pass import (  # noqa: E402
    _acquire_pass_lock, _refresh_and_reconcile_paper_mirror,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-post-entry-incident-at", help="Explicit review of one exact legacy lost-cause incident.")
    args = parser.parse_args()
    settings = Settings.from_env()
    if settings.mode != "paper" or settings.live_capital_enabled:
        raise RuntimeError("reconciliation_requires_paper_only")
    lock = _acquire_pass_lock(settings)
    if lock is None:
        report_work_result({"status": "deferred_owner_busy", "reason": "canonical_pass_already_running"})
        return 0
    previous = {}
    try:
        ledger = OperatingLedger(settings)
        with ledger.execution_owner(f"paperops-autonomous-pass:{os.getpid()}:{uuid4().hex[:12]}") as lease:
            previous = {key: os.environ.get(key) for key in lease.environment()}
            os.environ.update(lease.environment())
            if args.review_post_entry_incident_at:
                ledger.review_legacy_post_entry_freeze(incident_at=args.review_post_entry_incident_at)
            results = []
            for _ in range(2):
                refresh, result = _refresh_and_reconcile_paper_mirror(
                    ledger, phase="incident_recovery", bootstrap=False, verify_recovery=False,
                )
                results.append(result)
                if refresh.returncode or result.get("status") != "passed":
                    break
            errors = list(results[-1].get("blockers") or [])
            state = ledger.execution_state()
            payload = {"generated_at": now_iso(),
                       "status": "reconciliation_completed" if not errors else "reconciliation_blocked",
                       "reconciliations": results, "execution_state": state,
                       "entries_remain_held": bool(state.get("frozen")),
                       "broker_write_count": 0, "new_entry_submission_count": 0,
                       "paper_only": True, "live_capital_enabled": False}
            report_work_result(payload, errors)
            print("paper_execution_reconciliation_status=" + payload["status"])
            if errors:
                print("qadam_failure_class=dependency_unavailable")
            return int(bool(errors))
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        lock.close()


if __name__ == "__main__":
    raise SystemExit(main())
