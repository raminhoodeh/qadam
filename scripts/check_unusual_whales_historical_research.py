#!/usr/bin/env python3
"""Offline contract check for the Unusual Whales research integration."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore  # noqa: E402
from orchestrator.qadam_operator_ready_common import authority_flags, now_iso, runtime_dir  # noqa: E402
from orchestrator.unusual_whales_adapter import (  # noqa: E402
    refresh_unusual_whales_public_artifacts,
    validate_unusual_whales_contract,
)
from world_monitor.source_registry import SOURCE_SPECS  # noqa: E402

CHECK_ARTIFACT = "unusual_whales_historical_research_checks.json"


def main() -> int:
    settings = Settings.from_env()
    status, feature_manifest = refresh_unusual_whales_public_artifacts(settings)
    errors = validate_unusual_whales_contract(status, feature_manifest)
    registry = next((source for source in SOURCE_SPECS if source.key == "unusual_whales"), None)
    if registry is None:
        errors.append("unusual_whales_source_registry_entry_missing")
    else:
        if registry.status != "intentionally_disabled":
            errors.append("unusual_whales_live_registry_unexpectedly_enabled")
        if registry.selection_status != "optional_disabled":
            errors.append("unusual_whales_live_selection_unexpectedly_enabled")
    checks = {
        "schema_version": "unusual_whales_historical_research_checks.v1",
        "artifact_type": "unusual_whales_historical_research_checks",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "adapter_implemented": status.get("adapter_implemented") is True,
        "network_called_by_checker": False,
        "access_state": status.get("status"),
        "access_expires_on": status.get("access_expires_on"),
        "credential_state": status.get("credential_state"),
        "backtest_feature_ready": feature_manifest.get("backtest_feature_ready") is True,
        "backtest_eligible_record_count": int(
            feature_manifest.get("backtest_eligible_record_count") or 0
        ),
        "live_source_registry_disabled": bool(
            registry
            and registry.status == "intentionally_disabled"
            and registry.selection_status == "optional_disabled"
        ),
        "source_quorum_allowed": False,
        "execution_allowed": False,
        "proof_credit_allowed": False,
        "secret_values_recorded": False,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    AtomicArtifactStore(runtime_dir(settings)).write_json(CHECK_ARTIFACT, checks)
    print(json.dumps(checks, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
