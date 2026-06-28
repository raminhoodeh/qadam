#!/usr/bin/env python3
"""Validate and write QSASE Phase 0 PaperOps reliability baseline artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_phase0_paperops_reliability_baseline import (
    COMPONENT_ARTIFACTS,
    IMPLEMENTATION_LOG,
    PHASE_STATUS_ARTIFACT,
    PRIMARY_ARTIFACT,
    READ_ONLY_AUTHORITY,
    _runtime_dir,
    build_and_write_qsase_phase0_paperops_reliability_baseline,
    validate_negative_safety_probe,
    validate_qsase_phase0_paperops_reliability_baseline,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _component_artifact_is_valid(component_key: str, runtime_dir: Path, artifact: dict) -> list[str]:
    errors: list[str] = []
    component_path = runtime_dir / COMPONENT_ARTIFACTS[component_key]
    if not component_path.exists():
        return [f"{COMPONENT_ARTIFACTS[component_key]} was not written"]
    component_artifact = _load_json(component_path)
    component = artifact.get("components", {}).get(component_key)
    if not isinstance(component, dict):
        errors.append(f"primary artifact missing component {component_key}")
        return errors
    if component_artifact.get("status") != component.get("status"):
        errors.append(f"{component_key} component artifact status does not match primary artifact")
    if component_artifact.get("safety") != READ_ONLY_AUTHORITY:
        errors.append(f"{component_key} component artifact safety is not read-only")
    if component_artifact.get("component", {}).get("component") != component_key:
        errors.append(f"{component_key} component artifact does not identify its component")
    return errors


def run_component_check(component_key: str) -> int:
    if component_key not in COMPONENT_ARTIFACTS:
        print(f"unknown_component={component_key}")
        return 2

    settings = Settings.from_env()
    runtime_dir = _runtime_dir(settings)
    primary_path = runtime_dir / PRIMARY_ARTIFACT
    component_path = runtime_dir / COMPONENT_ARTIFACTS[component_key]
    if not primary_path.exists() or not component_path.exists():
        artifact, _, errors = build_and_write_qsase_phase0_paperops_reliability_baseline(
            settings,
            write_component_artifacts=True,
            write_phase_status=False,
            append_log=False,
        )
    else:
        artifact = _load_json(primary_path)
        errors = validate_qsase_phase0_paperops_reliability_baseline(artifact)

    errors.extend(_component_artifact_is_valid(component_key, runtime_dir, artifact))
    component = artifact.get("components", {}).get(component_key, {})
    print(f"component={component_key}")
    print(f"status={component.get('status')}")
    print(f"gap_count={len(component.get('gaps', [])) if isinstance(component, dict) else 0}")
    print(
        "degraded_reason_count="
        f"{len(component.get('degraded_reasons', [])) if isinstance(component, dict) else 0}"
    )
    if errors:
        for error in errors:
            print(f"error={error}")
        return 1
    print(f"qsase_phase0_{component_key}_check=ok")
    return 0


def main() -> int:
    settings = Settings.from_env()
    artifact, written, errors = build_and_write_qsase_phase0_paperops_reliability_baseline(
        settings,
        write_component_artifacts=True,
        write_phase_status=True,
        append_log=True,
    )

    runtime_dir = _runtime_dir(settings)
    primary_path = runtime_dir / PRIMARY_ARTIFACT
    phase_status_path = runtime_dir / PHASE_STATUS_ARTIFACT
    log_path = ROOT / IMPLEMENTATION_LOG

    validation_errors = list(errors)
    if not primary_path.exists():
        validation_errors.append(f"{PRIMARY_ARTIFACT} was not written")
    if not phase_status_path.exists():
        validation_errors.append(f"{PHASE_STATUS_ARTIFACT} was not written")
    if not log_path.exists():
        validation_errors.append(f"{IMPLEMENTATION_LOG} was not written")
    for component_key in COMPONENT_ARTIFACTS:
        validation_errors.extend(_component_artifact_is_valid(component_key, runtime_dir, artifact))
    validation_errors.extend(validate_negative_safety_probe())

    print(f"artifact={written.get('primary')}")
    print(f"phase_status={written.get('phase_status')}")
    print(f"implementation_log={written.get('implementation_log')}")
    print(f"status={artifact.get('status')}")
    print(f"gap_count={artifact.get('gap_count')}")
    print(f"degraded_reason_count={artifact.get('degraded_reason_count')}")
    print(f"blocker_count={artifact.get('blocker_count')}")
    for component_key, component_status in artifact.get("component_statuses", {}).items():
        print(f"component_status.{component_key}={component_status}")
    if validation_errors:
        for error in validation_errors:
            print(f"error={error}")
        return 1
    print("qsase_phase0_paperops_reliability_baseline_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
