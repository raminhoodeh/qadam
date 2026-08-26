#!/usr/bin/env python3
"""Validate Qadam's scheduled read-only Telegram group interface."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_ready_common import (  # noqa: E402
    read_json,
    read_jsonl,
    runtime_dir,
    write_json_atomic,
)
from orchestrator.qadam_reliability_critic import (  # noqa: E402
    installed_template_matches,
    launchd_job_state,
)
from orchestrator.qadam_telegram_readonly_interface import (  # noqa: E402
    CHECK_ARTIFACT,
    QUERY_NAMES,
    RESPONSE_LEDGER_ARTIFACT,
    SCHEMA_VERSION,
    STATUS_ARTIFACT,
    validate_interface_status,
)

LAUNCHD_LABEL = "com.qadam.telegram-readonly-interface"
LAUNCHD_TEMPLATE = ROOT / "ops" / "launchd" / f"{LAUNCHD_LABEL}.plist.template"
LAUNCHD_TARGET = Path.home() / "Library" / "LaunchAgents" / f"{LAUNCHD_LABEL}.plist"
MAX_STATUS_AGE_SECONDS = 180


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
    errors = validate_interface_status(status)
    generated = _parse(status.get("generated_at"))
    age_seconds = (
        max(0.0, (datetime.now(timezone.utc) - generated).total_seconds())
        if generated
        else None
    )
    if age_seconds is None or age_seconds > MAX_STATUS_AGE_SECONDS:
        errors.append("telegram_readonly_interface_status_stale")
    if status.get("status") != "ready":
        errors.append("telegram_readonly_interface_not_ready")
    if status.get("commands_registered") is not True:
        errors.append("telegram_readonly_interface_commands_not_registered")
    if status.get("available_queries") != list(QUERY_NAMES):
        errors.append("telegram_readonly_interface_query_contract_mismatch")
    launchd = launchd_job_state(LAUNCHD_LABEL)
    if not LAUNCHD_TARGET.exists():
        errors.append("telegram_readonly_interface_launchd_not_installed")
    template_matches = installed_template_matches(LAUNCHD_TEMPLATE, LAUNCHD_TARGET)
    if not template_matches:
        errors.append("telegram_readonly_interface_launchd_template_mismatch")
    if launchd.get("loaded") is not True:
        errors.append("telegram_readonly_interface_launchd_not_loaded")
    ledger = read_jsonl(runtime / RESPONSE_LEDGER_ARTIFACT, limit=2_000)
    for row in ledger:
        authority = row.get("authority") if isinstance(row.get("authority"), dict) else {}
        for field in (
            "telegram_command_authority",
            "trade_candidate_creation_allowed",
            "strategy_mutation_allowed",
            "risk_approval_allowed",
            "execution_approval_allowed",
            "paper_order_allowed",
            "broker_write_allowed",
            "proof_credit_allowed",
            "quantum_job_allowed",
            "code_edit_allowed",
            "live_capital_enabled",
        ):
            if authority.get(field) is not False:
                errors.append(f"telegram_readonly_interface_ledger_unsafe_authority:{field}")
    errors = sorted(set(errors))
    check = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_telegram_readonly_interface_checks",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if not errors else "blocked",
        "status_age_seconds": age_seconds,
        "launchd_installed": LAUNCHD_TARGET.exists(),
        "launchd_loaded": launchd.get("loaded") is True,
        "launchd_template_matches": template_matches,
        "commands_registered": status.get("commands_registered") is True,
        "available_query_count": len(status.get("available_queries") or []),
        "response_ledger_count": len(ledger),
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "read_only": True,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "live_capital_enabled": False,
    }
    write_json_atomic(runtime / CHECK_ARTIFACT, check)
    print(f"qadam_telegram_readonly_interface_check={check['status']}")
    print(f"qadam_telegram_readonly_interface_status_age_seconds={age_seconds}")
    print(f"qadam_telegram_readonly_interface_launchd_loaded={check['launchd_loaded']}")
    print(
        "qadam_telegram_readonly_interface_commands_registered="
        f"{check['commands_registered']}"
    )
    print(f"qadam_telegram_readonly_interface_validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
