#!/usr/bin/env python3
"""Validate the latest hedge-fund team health artifact without running models."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_hedge_fund_team_health import (  # noqa: E402
    HEALTH_MAX_AGE_SECONDS,
    STATUS_ARTIFACT,
    validate_hedge_fund_team_health,
)
from orchestrator.qadam_operator_ready_common import read_json, runtime_dir  # noqa: E402


def _age_seconds(value: str | None) -> float | None:
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds())


def main() -> int:
    payload = read_json(runtime_dir() / STATUS_ARTIFACT)
    errors = validate_hedge_fund_team_health(payload) if payload else ["team_health_missing"]
    age = _age_seconds(payload.get("generated_at")) if payload else None
    if age is None or age > HEALTH_MAX_AGE_SECONDS:
        errors.append("team_health_stale")
    if payload.get("status") != "passed":
        errors.append("team_health_not_passed")
    errors = sorted(set(errors))
    print(f"qadam_team_health_check={'ok' if not errors else 'failed'}")
    print(f"qadam_team_health_check_age_seconds={age}")
    print(f"qadam_team_health_check_error_count={len(errors)}")
    for error in errors:
        print(f"qadam_team_health_check_error={error}")
    print("qadam_team_health_check_paper_order_created_count=0")
    print("qadam_team_health_check_broker_write_count=0")
    print("qadam_team_health_check_live_capital_enabled=false")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
