#!/usr/bin/env python3
"""Independently validate the scheduled Qadam reliability critic."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore  # noqa: E402
from orchestrator.qadam_operator_ready_common import (  # noqa: E402
    authority_flags,
    read_json,
    runtime_dir,
)
from orchestrator.qadam_reliability_critic import (  # noqa: E402
    CHECK_ARTIFACT,
    CRITIC_MAX_AGE_SECONDS,
    LAUNCHD_LABEL,
    LAUNCHD_TARGET,
    LAUNCHD_TEMPLATE,
    STATUS_ARTIFACT,
    build_reliability_snapshot,
    classify_reliability_snapshot,
    installed_template_matches,
    launchd_job_state,
    validate_reliability_critic_payload,
)


def _parse(value: object) -> datetime | None:
    try:
        result = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    status = read_json(runtime / STATUS_ARTIFACT)
    errors = validate_reliability_critic_payload(status)
    generated = _parse(status.get("generated_at"))
    age_seconds = (
        max(0.0, (datetime.now(timezone.utc) - generated).total_seconds())
        if generated
        else None
    )
    if age_seconds is None or age_seconds > CRITIC_MAX_AGE_SECONDS:
        errors.append("reliability_critic_status_stale")
    launchd = launchd_job_state(LAUNCHD_LABEL)
    if not LAUNCHD_TARGET.exists():
        errors.append("reliability_critic_launchd_not_installed")
    if not installed_template_matches(LAUNCHD_TEMPLATE, LAUNCHD_TARGET):
        errors.append("reliability_critic_launchd_template_mismatch")
    if launchd.get("loaded") is not True:
        errors.append("reliability_critic_launchd_not_loaded")
    snapshot = build_reliability_snapshot(settings)
    classification = classify_reliability_snapshot(snapshot)
    if classification.get("healthy") is not True:
        errors.extend(
            f"current_runtime:{item.get('code')}"
            for item in classification.get("blockers", [])
        )
    errors = sorted(set(errors))
    check = {
        "schema_version": "qadam_reliability_critic.v1",
        "artifact_type": "qadam_reliability_critic_checks",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if not errors else "blocked",
        "critic_status_age_seconds": age_seconds,
        "launchd_installed": LAUNCHD_TARGET.exists(),
        "launchd_loaded": launchd.get("loaded") is True,
        "launchd_template_matches": installed_template_matches(
            LAUNCHD_TEMPLATE, LAUNCHD_TARGET
        ),
        "current_operating_state": classification.get("state"),
        "current_runtime_healthy": classification.get("healthy") is True,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    AtomicArtifactStore(runtime).write_json(CHECK_ARTIFACT, check)
    print(f"qadam_reliability_critic_check={check['status']}")
    print(f"qadam_reliability_critic_launchd_installed={check['launchd_installed']}")
    print(f"qadam_reliability_critic_launchd_loaded={check['launchd_loaded']}")
    print(
        "qadam_reliability_critic_launchd_template_matches="
        f"{check['launchd_template_matches']}"
    )
    print(f"qadam_reliability_critic_current_state={check['current_operating_state']}")
    print(f"qadam_reliability_critic_validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
