#!/usr/bin/env python3
"""Validate the installed and currently fresh Qadam reliability watchdog."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore  # noqa: E402
from orchestrator.qadam_operator_ready_common import read_json, runtime_dir  # noqa: E402
from orchestrator.qadam_reliability_critic import (  # noqa: E402
    installed_template_matches,
    launchd_job_state,
)
from orchestrator.qadam_reliability_watchdog import (  # noqa: E402
    CHECK_ARTIFACT,
    LAUNCHD_LABEL,
    LAUNCHD_TARGET,
    LAUNCHD_TEMPLATE,
    STATUS_ARTIFACT,
    STATUS_MAX_AGE_SECONDS,
    validate_reliability_watchdog_payload,
)


def _parse(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    status = read_json(runtime / STATUS_ARTIFACT)
    errors = validate_reliability_watchdog_payload(status)
    generated = _parse(status.get("generated_at"))
    age_seconds = (
        max(0.0, (datetime.now(timezone.utc) - generated).total_seconds())
        if generated
        else None
    )
    if age_seconds is None or age_seconds > STATUS_MAX_AGE_SECONDS:
        errors.append("reliability_watchdog_status_stale")
    if status.get("recovery_coverage_status") != "passed":
        errors.append("reliability_watchdog_recovery_coverage_blocked")
    launchd = launchd_job_state(LAUNCHD_LABEL)
    if not LAUNCHD_TARGET.exists():
        errors.append("reliability_watchdog_launchd_not_installed")
    if not installed_template_matches(LAUNCHD_TEMPLATE, LAUNCHD_TARGET):
        errors.append("reliability_watchdog_launchd_template_mismatch")
    if launchd.get("loaded") is not True:
        errors.append("reliability_watchdog_launchd_not_loaded")
    errors = sorted(set(errors))
    check = {
        "schema_version": "qadam_reliability_watchdog.v1",
        "artifact_type": "qadam_reliability_watchdog_checks",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if not errors else "blocked",
        "watchdog_status": status.get("status"),
        "watchdog_status_age_seconds": age_seconds,
        "launchd_installed": LAUNCHD_TARGET.exists(),
        "launchd_loaded": launchd.get("loaded") is True,
        "launchd_template_matches": installed_template_matches(
            LAUNCHD_TEMPLATE, LAUNCHD_TARGET
        ),
        "validation_errors": errors,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
    }
    AtomicArtifactStore(runtime).write_json(CHECK_ARTIFACT, check)
    print(f"qadam_reliability_watchdog_check={check['status']}")
    print(f"watchdog_status={check['watchdog_status']}")
    print(f"launchd_loaded={check['launchd_loaded']}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
