#!/usr/bin/env python3
"""Report whether Qadam is finished enough to run unattended paper mode.

This check is intentionally public-safe. It reports configured/missing states
only, never secret values, and it never calls broker live endpoints or submits
orders.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.paperops_active_paper_trading_automation import (  # noqa: E402
    build_paperops_active_paper_trading_automation,
    validate_paperops_active_paper_trading_automation,
)
from orchestrator.paperops_source_gap_visibility import (  # noqa: E402
    build_paperops_source_gap_visibility,
    validate_paperops_source_gap_visibility,
)
from orchestrator.quantum import (  # noqa: E402
    qctrl_fire_opal_ibm_readiness,
    validate_qctrl_fire_opal_ibm_readiness,
)
from orchestrator.secrets import secret_status  # noqa: E402
from orchestrator.system_state import module_map  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-telegram-live",
        action="store_true",
        help="Treat live Telegram notifications as required instead of optional.",
    )
    return parser.parse_args()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _bool_text(value: object) -> str:
    return "True" if value is True else "False"


def _module_status(modules: list[dict[str, str]], key: str) -> str:
    for module in modules:
        if module.get("key") == key:
            return module.get("status", "missing")
    return "missing"


def main() -> int:
    args = _parse_args()
    settings = Settings.from_env()
    runtime = Path(settings.runtime_dir)
    required_gaps: list[str] = []
    optional_gaps: list[str] = []

    paper_live = _read_json(runtime / "paper_live_certification.json")
    paper_cycle = _read_json(runtime / "paper_operational_cycle.json")
    qctrl_access = _read_json(runtime / "paper_live_qctrl_product_access.json")
    active_runner = build_paperops_active_paper_trading_automation(settings=settings)
    active_runner_errors = validate_paperops_active_paper_trading_automation(active_runner)
    source_gaps = build_paperops_source_gap_visibility(settings=settings)
    source_gap_errors = validate_paperops_source_gap_visibility(source_gaps)
    fire_opal = qctrl_fire_opal_ibm_readiness(settings=settings)
    validate_qctrl_fire_opal_ibm_readiness(fire_opal)
    modules = module_map(settings=settings)

    if paper_live.get("paper_live_certified") is not True:
        required_gaps.append("paper_live_not_certified")
    if paper_live.get("paper_live_operation_allowed") is not True:
        required_gaps.append("paper_live_operation_not_allowed")
    if paper_live.get("paper_live_unattended_execution_delegation_enabled") is not True:
        required_gaps.append("paper_live_unattended_delegation_not_enabled")
    paper_cycle_status = (
        paper_cycle.get("paper_operational_cycle_status")
        or paper_cycle.get("status")
    )
    if paper_cycle_status != "paper_cycle_full_paper_operational_ready":
        required_gaps.append("paper_operational_cycle_not_ready")
    if active_runner.get("unattended_paper_execution_delegation_enabled") is not True:
        required_gaps.append("active_runner_unattended_not_armed")
    if active_runner_errors:
        required_gaps.append("active_runner_validation_errors")
    if active_runner.get("automation_active") is not True:
        required_gaps.append("hourly_automation_not_active")
    if active_runner.get("automation_hourly") is not True:
        required_gaps.append("hourly_automation_not_hourly")
    if active_runner.get("automation_prompt_active_trade_bound") is not True:
        required_gaps.append("hourly_automation_prompt_not_bound")
    if active_runner.get("paperops2_idempotency_ledger_active") is not True:
        required_gaps.append("paper_submit_idempotency_ledger_not_active")
    if qctrl_access.get("status") != "qctrl_paper_consultation_ready":
        required_gaps.append("qctrl_paper_consultation_not_ready")
    if fire_opal.get("status") == "ready_for_explicit_device_probe":
        optional_gaps.append("fire_opal_ibm_device_probe_not_recorded")
    elif fire_opal.get("status") == "blocked_provider_probe_failed":
        optional_gaps.append(
            f"fire_opal_ibm_provider_probe_failed:{fire_opal.get('provider_failure_category') or 'unknown'}"
        )
    elif fire_opal.get("status") not in {"device_probe_submitted", "ready"}:
        optional_gaps.append(f"quantum_provider_diagnostic:{fire_opal.get('status')}")
    optional_gaps.extend(source_gaps.get("optional_gap_keys", []) or [])
    if source_gap_errors:
        required_gaps.append("source_gap_visibility_validation_errors")
    if int(source_gaps.get("required_gap_count", 0) or 0):
        required_gaps.append("source_gap_visibility_required_source_gap")
    if int(source_gaps.get("trade_blocking_source_gap_count", 0) or 0):
        required_gaps.append("source_gap_visibility_trade_blocking_source_gap")
    if int(source_gaps.get("silent_blocker_count", 0) or 0):
        required_gaps.append("source_gap_visibility_silent_blocker")
    telegram_paper_trade_live_ready = (
        settings.telegram_trade_group_notifications_enabled is True
        and settings.telegram_trade_group_notifications_dry_run is False
        and secret_status("TELEGRAM_BOT_TOKEN", settings).configured is True
        and secret_status("TELEGRAM_GROUP_CHAT_ID", settings).configured is True
    )
    if telegram_paper_trade_live_ready is not True:
        gap = "telegram_paper_trade_live_notifications_not_enabled"
        if args.require_telegram_live:
            required_gaps.append(gap)
        else:
            optional_gaps.append(gap)
    if _module_status(modules, "research_analyst") not in {"shadow_ready", "registered"}:
        required_gaps.append("local_research_analyst_not_ready")
    if _module_status(modules, "strategy_lead") not in {"shadow_ready", "registered"}:
        required_gaps.append("strategy_lead_not_ready")

    print("qadam_paper_closeout_status=" + ("ready" if not required_gaps else "blocked"))
    print(f"qadam_paper_closeout_required_gap_count={len(required_gaps)}")
    print(f"qadam_paper_closeout_optional_gap_count={len(optional_gaps)}")
    print(f"qadam_paper_closeout_required_gaps={','.join(required_gaps)}")
    print(f"qadam_paper_closeout_optional_gaps={','.join(optional_gaps)}")
    print(
        "qadam_paper_closeout_source_gap_visibility_status="
        f"{source_gaps.get('status')}"
    )
    print(
        "qadam_paper_closeout_source_gap_policy_status="
        f"{source_gaps.get('source_gap_policy_status')}"
    )
    print(
        "qadam_paper_closeout_source_gap_optional_count="
        f"{source_gaps.get('optional_gap_count')}"
    )
    print(
        "qadam_paper_closeout_source_gap_optional_keys="
        f"{','.join(source_gaps.get('optional_gap_keys', []) or [])}"
    )
    print(
        "qadam_paper_closeout_source_gap_required_count="
        f"{source_gaps.get('required_gap_count')}"
    )
    print(
        "qadam_paper_closeout_source_gap_trade_blocking_count="
        f"{source_gaps.get('trade_blocking_source_gap_count')}"
    )
    print(
        "qadam_paper_closeout_source_gap_silent_blocker_count="
        f"{source_gaps.get('silent_blocker_count')}"
    )
    print(
        "qadam_paper_closeout_source_gap_blocker_count="
        f"{source_gaps.get('blocker_count')}"
    )
    print(
        "qadam_paper_closeout_source_gap_validation_error_count="
        f"{len(source_gap_errors)}"
    )
    print(f"qadam_paper_closeout_paper_live_certified={_bool_text(paper_live.get('paper_live_certified'))}")
    print(
        "qadam_paper_closeout_operation_allowed="
        f"{_bool_text(paper_live.get('paper_live_operation_allowed'))}"
    )
    print(
        "qadam_paper_closeout_unattended_delegation="
        f"{_bool_text(paper_live.get('paper_live_unattended_execution_delegation_enabled'))}"
    )
    print(
        "qadam_paper_closeout_active_runner_status="
        f"{active_runner.get('status')}"
    )
    print(
        "qadam_paper_closeout_active_runner_reason="
        f"{active_runner.get('unattended_paper_execution_delegation_reason')}"
    )
    print(
        "qadam_paper_closeout_active_runner_idle_reason="
        f"{active_runner.get('idle_reason') or ''}"
    )
    print(
        "qadam_paper_closeout_idempotency_guard_message="
        f"{active_runner.get('idempotency_guard_message') or ''}"
    )
    print(
        "qadam_paper_closeout_fresh_submit_count="
        f"{active_runner.get('paperops2_fresh_eligible_submit_record_count')}"
    )
    print(
        "qadam_paper_closeout_duplicate_submit_count="
        f"{active_runner.get('paperops2_duplicate_submit_record_count')}"
    )
    print(
        "qadam_paper_closeout_idempotency_ledger_active="
        f"{_bool_text(active_runner.get('paperops2_idempotency_ledger_active'))}"
    )
    print(
        "qadam_paper_closeout_telegram_paper_trade_live_notifications_ready="
        f"{_bool_text(telegram_paper_trade_live_ready)}"
    )
    print(f"qadam_paper_closeout_fire_opal_ibm_status={fire_opal.get('status')}")
    print(
        "qadam_paper_closeout_ibm_token_configured="
        f"{_bool_text(fire_opal.get('ibm_quantum_token_configured'))}"
    )
    print(
        "qadam_paper_closeout_ibm_instance_configured="
        f"{_bool_text(fire_opal.get('ibm_quantum_instance_configured'))}"
    )
    print(
        "qadam_paper_closeout_secret_value_exposed="
        f"{_bool_text(False)}"
    )

    return 0 if not required_gaps else 1


if __name__ == "__main__":
    raise SystemExit(main())
