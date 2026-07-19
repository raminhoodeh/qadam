#!/usr/bin/env python3
"""Build and validate RF-3 canonical contracts and artifact ownership."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_canonical_contracts import (  # noqa: E402
    CHECK_ARTIFACT,
    COMPATIBILITY_AUDIT_ARTIFACT,
    CONTRACT_REGISTRY_ARTIFACT,
    MIGRATION_STATUS_ARTIFACT,
    OWNERSHIP_REGISTRY_ARTIFACT,
    build_and_write_canonical_contracts,
)
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    bundle, checks, errors = build_and_write_canonical_contracts(settings)
    compatibility = bundle["compatibility"]
    print(f"contract_registry={runtime / CONTRACT_REGISTRY_ARTIFACT}")
    print(f"ownership_registry={runtime / OWNERSHIP_REGISTRY_ARTIFACT}")
    print(f"migration_status={runtime / MIGRATION_STATUS_ARTIFACT}")
    print(f"compatibility_audit={runtime / COMPATIBILITY_AUDIT_ARTIFACT}")
    print(f"checks_artifact={runtime / CHECK_ARTIFACT}")
    print(f"status={checks['status']}")
    print(f"canonical_contract_count={checks['canonical_contract_count']}")
    print(f"ownership_conflict_count={checks['ownership_conflict_count']}")
    print(f"compatibility_reader_count={compatibility['record_count']}")
    print(f"present_compatibility_artifact_count={compatibility['present_artifact_count']}")
    print(f"behavior_changed={checks['behavior_changed']}")
    print(f"broker_write_allowed={checks['authority']['broker_write_allowed']}")
    print(f"live_capital_enabled={checks['authority']['live_capital_enabled']}")
    print(f"validation_error_count={len(errors)}")
    if errors:
        for error in errors:
            print(f"error={error}")
        return 1
    print("qadam_canonical_contracts_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
