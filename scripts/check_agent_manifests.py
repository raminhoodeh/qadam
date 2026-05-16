#!/usr/bin/env python3
"""Validate Qadam Phase 1E agent and skill manifests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.agent_registry import agent_registry_summary, validate_agent_os


def main() -> int:
    validation = validate_agent_os()
    summary = agent_registry_summary()

    print("agent_manifest_status=" + validation["status"])
    print(f"agent_manifest_schema_version={validation['schema_version']}")
    print(f"agent_manifest_agent_count={validation['agent_count']}")
    print(f"agent_manifest_expected_agent_count={validation['expected_agent_count']}")
    print(f"agent_manifest_skill_count={validation['skill_count']}")
    print(f"agent_manifest_expected_skill_count={validation['expected_skill_count']}")
    print(f"agent_manifest_tool_grant_count={validation['tool_grant_count']}")
    print(f"agent_manifest_secret_name_grant_count={validation['secret_name_grant_count']}")
    print(f"agent_manifest_error_count={len(validation['errors'])}")
    print(f"agent_manifest_warning_count={len(validation['warnings'])}")
    print(f"agent_manifest_boundary={summary['boundary']}")

    for error in validation["errors"]:
        print(f"agent_manifest_error={error}")
    for warning in validation["warnings"]:
        print(f"agent_manifest_warning={warning}")

    if validation["status"] != "ok":
        return 1
    if validation["agent_count"] != validation["expected_agent_count"]:
        print("agent_manifest_count_mismatch=true")
        return 1
    if validation["skill_count"] != validation["expected_skill_count"]:
        print("skill_bundle_count_mismatch=true")
        return 1

    print("agent_manifest_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
