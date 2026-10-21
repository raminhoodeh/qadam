#!/usr/bin/env python3
"""Validate the current fenced paper execution contract; no scheduler qualification."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orchestrator.config import Settings  # noqa: E402
from orchestrator.execution.contract import approve_execution_policy, execution_contract_status  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install-reviewed-policy", action="store_true")
    args = parser.parse_args()
    settings = Settings.from_env()
    if args.install_reviewed_policy:
        result = approve_execution_policy(settings, reviewed=True)
        print("execution_policy_status=" + result["status"])
        return 0
    status = execution_contract_status(settings, require_entry=True)
    print("execution_contract_source=canonical_database_contract")
    print("execution_contract_status=" + status["status"])
    print("execution_contract_blockers=" + ",".join(status["blockers"]))
    print("paperops_active_automation_validation_errors=[]")
    print("paperops_active_automation_owner_blockers=" + ",".join(status["blockers"]))
    if status["active"]:
        print("paperops_active_automation_status=canonical_execution_contract_ready")
        return 0
    transient = set(status["blockers"]) <= {"execution_owner_unavailable", "execution_contract_not_bound"}
    print("qadam_failure_class=" + ("dependency_unavailable" if transient else "safety_violation"))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
