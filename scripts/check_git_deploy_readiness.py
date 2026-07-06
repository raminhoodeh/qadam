#!/usr/bin/env python3
"""Validate and write Qadam git/deploy readiness artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qadam_git_deploy_readiness import (
    LIVE_DEPLOY_CLOSURE_ARTIFACT,
    PRIMARY_ARTIFACT,
    _runtime_dir,
    build_and_write_git_deploy_readiness,
    validate_git_deploy_readiness,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    settings = Settings.from_env()
    payload, written, errors = build_and_write_git_deploy_readiness(settings)
    runtime_dir = _runtime_dir(settings)
    validation_errors = list(errors)

    for filename in (PRIMARY_ARTIFACT, LIVE_DEPLOY_CLOSURE_ARTIFACT):
        if not (runtime_dir / filename).exists():
            validation_errors.append(f"{filename}_missing")

    loaded = _load_json(runtime_dir / PRIMARY_ARTIFACT)
    validation_errors.extend(validate_git_deploy_readiness(loaded))
    if loaded.get("generated_at") != payload.get("generated_at"):
        validation_errors.append("written_generated_at_mismatch")

    print(f"artifact={written.get('primary')}")
    print(f"closure={written.get('closure')}")
    print(f"status={payload.get('status')}")
    print(f"deployment_closure_passed={payload.get('deployment_closure_passed')}")
    print(f"blocker_count={payload.get('blocker_count')}")
    print(f"root_ahead_count={payload.get('root_repo', {}).get('ahead_count')}")
    print(f"dashboard_ahead_count={payload.get('dashboard_repo', {}).get('ahead_count')}")
    print(f"root_remote_probe_ok={payload.get('root_repo', {}).get('remote_read_probe', {}).get('ok')}")
    print(f"dashboard_remote_probe_ok={payload.get('dashboard_repo', {}).get('remote_read_probe', {}).get('ok')}")
    print(f"deploy_receipt_present={payload.get('deploy_closure', {}).get('deploy_receipt_present')}")
    for blocker in payload.get("blockers", []):
        print(f"blocker={blocker}")

    if validation_errors:
        for error in sorted(set(validation_errors)):
            print(f"error={error}")
        return 1
    print("git_deploy_readiness_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

