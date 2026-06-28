#!/usr/bin/env python3
"""Validate QSASE recursive improvement remains proposal-only."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_end_to_end_certification import build_recursive_improvement_contract_audit


def main() -> int:
    settings = Settings.from_env()
    audit = build_recursive_improvement_contract_audit(settings)

    print(f"status={audit.get('status')}")
    print(f"proposal_artifact_count={audit.get('proposal_artifact_count')}")
    print(f"present_proposal_artifact_count={audit.get('present_proposal_artifact_count')}")
    print(f"active_proposal_count={audit.get('active_proposal_count')}")
    print(f"applied_update_count={audit.get('applied_update_count')}")
    print(f"approval_required_count={audit.get('approval_required_count')}")
    print(f"proposal_only={audit.get('proposal_only')}")
    if audit.get("errors"):
        for error in audit["errors"]:
            print(f"error={error}")
        return 1
    print("qsase_recursive_improvement_contract_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
