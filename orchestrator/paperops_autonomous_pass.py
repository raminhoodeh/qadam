"""Canonical summary for one guarded PaperOps autonomous pass."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from orchestrator.config import Settings
from orchestrator.paper_account import OPEN_ORDER_STATUSES, PaperAccountMirrorStore
from orchestrator.paperops_closed_trade_funnel import (
    build_paperops_closed_trade_funnel,
    validate_paperops_closed_trade_funnel,
)
from orchestrator.paperops_close_to_ledger import (
    build_paperops_close_to_ledger,
    validate_paperops_close_to_ledger,
)
from orchestrator.paperops_submit_regression_guard import (
    build_paperops_submit_regression_guard,
    validate_paperops_submit_regression_guard,
)
from orchestrator.paperops_source_gap_visibility import (
    build_paperops_source_gap_visibility,
    validate_paperops_source_gap_visibility,
)


PAPEROPS_AUTONOMOUS_PASS_SCHEMA_VERSION = 1
PAPEROPS_AUTONOMOUS_PASS_RUNTIME_ARTIFACT = "paperops_autonomous_pass_summary.json"

COMMAND_SEQUENCE: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("telegram_inbound", ("scripts/poll_telegram_inbound_intake.py",)),
    (
        "first_week_trade_mandate",
        ("scripts/check_paperops_first_week_paper_trade_mandate.py",),
    ),
    ("paper_ops_cycle", ("scripts/check_paper_operational_cycle.py",)),
    ("submit_regression_guard", ("scripts/check_paperops_submit_regression_guard.py",)),
    ("active_automation_check", ("scripts/check_paperops_active_paper_trading_automation.py",)),
    (
        "active_automation_execute",
        ("scripts/run_active_paper_trading_automation.py", "--execute-paper-automation"),
    ),
    ("cockpit_notification", ("scripts/check_paperops_cockpit_notification_upgrade.py",)),
    ("paperops_30_day_operations", ("scripts/check_paperops_30_day_operations.py",)),
    ("cockpit_status_pre_certification", ("scripts/check_cockpit_status.py",)),
    (
        "rs10_final_paper_autonomy",
        ("scripts/check_rs10_final_paper_autonomy_certification.py",),
    ),
    ("paper_live_certification", ("scripts/check_paper_live_certification.py",)),
    ("source_gap_visibility", ("scripts/check_paperops_source_gap_visibility.py",)),
    ("paper_closeout", ("scripts/check_qadam_paper_closeout.py",)),
    ("cockpit_status", ("scripts/check_cockpit_status.py",)),
)

OPTIONAL_COVERAGE_GAP_KEYS = {
    "ais_credential_missing",
    "ais_maritime_credential_missing",
    "aviationstack_api_key_missing",
    "comtrade_api_key_missing",
    "kalshi_credentials_missing",
    "reddit_credentials_missing",
    "stock_act_api_key_missing",
    "stock_act_capitol_trades_api_key_missing",
    "twitter_x_bearer_token_missing",
    "un_comtrade_api_key_missing",
    "unusual_whales_api_key_missing",
    "wingbits_api_key_missing",
}

SELF_HEAL_REPAIR_SCOPE = "paperops_repo_artifact_repair_only"
SELF_HEAL_FORBIDDEN_ACTIONS = (
    "force_trades",
    "edit_secrets_or_env",
    "load_live_credentials",
    "enable_live_capital",
    "call_live_broker_endpoints",
    "bypass_qctrl",
    "submit_outside_guarded_alpaca_paper_route",
    "grant_proof_credit",
    "enable_telegram_commands",
)
SELF_HEAL_REPAIR_PROMPT = (
    "Run a Qadam PaperOps self-heal repair pass. Read "
    "data/runtime/paperops_autonomous_pass_summary.json first and use its "
    "failed_commands, blockers, validation_errors, command_results[].parsed, "
    "stdout_tail, and stderr_tail as the source of truth. Apply the narrowest "
    "repo or runtime-artifact fix needed to clear the failure. Preserve the "
    "actual 30-day paper growth trial calendar; do not backfill, simulate time, "
    "force trades, edit secrets or .env files, load live credentials, enable "
    "live capital, call live broker endpoints, bypass Q-CTRL, grant proof "
    "credit, enable Telegram commands, or submit outside the guarded Alpaca "
    "Paper route. After the fix, rerun exactly `.venv/bin/python "
    "scripts/run_paperops_autonomous_pass.py` and report only from "
    "data/runtime/paperops_autonomous_pass_summary.json."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def runtime_summary_path(settings: Settings | None = None) -> Path:
    settings = settings or Settings.from_env()
    return Path(settings.runtime_dir) / PAPEROPS_AUTONOMOUS_PASS_RUNTIME_ARTIFACT


def parse_key_value_output(output: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in output.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def run_command_sequence(
    *,
    repo_root: Path,
    python_executable: str | None = None,
    timeout_seconds: int = 180,
) -> list[dict[str, Any]]:
    executable = python_executable or sys.executable
    results: list[dict[str, Any]] = []
    for label, command in COMMAND_SEQUENCE:
        completed = subprocess.run(
            [executable, *command],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        results.append(
            {
                "label": label,
                "command": [executable, *command],
                "returncode": completed.returncode,
                "ok": completed.returncode == 0,
                "parsed": parse_key_value_output(stdout),
                "stdout_tail": stdout.splitlines()[-20:],
                "stderr_tail": stderr.splitlines()[-20:],
            }
        )
    return results


def _by_label(command_results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(result.get("label")): result for result in command_results}


def _parsed(command_results: list[dict[str, Any]], label: str) -> dict[str, str]:
    result = _by_label(command_results).get(label, {})
    parsed = result.get("parsed", {})
    return parsed if isinstance(parsed, dict) else {}


def _value(
    command_results: list[dict[str, Any]],
    candidates: tuple[tuple[str, str], ...],
    default: Any = None,
) -> Any:
    for label, key in candidates:
        value = _parsed(command_results, label).get(key)
        if value not in {None, ""}:
            return value
    return default


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _csv(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return [item for item in str(value or "").split(",") if item]


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


def _paper_mirror_runtime() -> dict[str, Any]:
    try:
        store = PaperAccountMirrorStore()
        latest = store.latest_snapshot()
        positions = store.read_positions()
        closed_trades = store.read_closed_trades()
        orders = store.read_orders()
    except Exception as exc:  # noqa: BLE001 - summary should degrade, not crash.
        return {
            "status": "unavailable",
            "error": exc.__class__.__name__,
            "open_position_count": 0,
            "closed_paper_trade_count": 0,
            "paper_order_count": 0,
            "open_order_count": 0,
            "order_status_counts": {},
            "current_balance_gbp": None,
            "observed_at": None,
        }
    order_status_counts: dict[str, int] = {}
    for order in orders:
        status = str(order.status or "unknown").lower()
        order_status_counts[status] = order_status_counts.get(status, 0) + 1
    open_order_count = sum(
        count
        for status, count in order_status_counts.items()
        if status in OPEN_ORDER_STATUSES
    )
    return {
        "status": "ok",
        "open_position_count": len(positions),
        "closed_paper_trade_count": len(closed_trades),
        "paper_order_count": len(orders),
        "open_order_count": open_order_count,
        "order_status_counts": order_status_counts,
        "current_balance_gbp": latest.current_balance_gbp if latest else None,
        "observed_at": latest.observed_at if latest else None,
    }


def _status(command_results: list[dict[str, Any]], blockers: list[str]) -> str:
    command_failures = [
        str(result.get("label"))
        for result in command_results
        if result.get("returncode") not in {0, None}
    ]
    closeout_status = _value(
        command_results,
        (("paper_closeout", "qadam_paper_closeout_status"),),
        "missing",
    )
    cycle_status = _value(
        command_results,
        (("paper_ops_cycle", "paper_ops_cycle_check_status"),),
        "missing",
    )
    fresh_submit_count = _int(
        _value(
            command_results,
            (
                ("active_automation_execute", "paperops_active_runner_fresh_submit_count"),
                (
                    "active_automation_check",
                    "paperops_active_automation_paperops2_fresh_eligible_submit_record_count",
                ),
            ),
        )
    )
    if blockers or closeout_status != "ready":
        return "blocked"
    if command_failures:
        return "degraded_command_failure"
    if cycle_status == "paper_cycle_full_paper_operational_ready" and fresh_submit_count == 0:
        return "ready_idle"
    if cycle_status == "paper_cycle_full_paper_operational_ready":
        return "ready_actionable"
    return "degraded"


def _self_healing_request(summary: dict[str, Any]) -> dict[str, Any]:
    failed_commands = list(summary.get("failed_commands") or [])
    blockers = list(summary.get("blockers") or [])
    validation_errors = list(summary.get("validation_errors") or [])
    status = str(summary.get("status") or "missing")
    closeout_status = str(summary.get("states", {}).get("closeout_status") or "missing")
    trigger_reasons: list[str] = []
    if status not in {"ready_idle", "ready_actionable"}:
        trigger_reasons.append(f"status:{status}")
    if failed_commands:
        trigger_reasons.append("failed_commands:" + ",".join(failed_commands))
    if blockers:
        trigger_reasons.append("blockers:" + ",".join(blockers))
    if validation_errors:
        trigger_reasons.append("validation_errors:" + ",".join(validation_errors))
    if closeout_status != "ready":
        trigger_reasons.append(f"closeout_status:{closeout_status}")
    needs_repair = bool(trigger_reasons)
    return {
        "enabled": True,
        "needs_repair": needs_repair,
        "codex_reprompt_required": needs_repair,
        "status": "repair_requested" if needs_repair else "no_repair_needed",
        "trigger_reasons": trigger_reasons,
        "failed_commands": failed_commands,
        "blockers": blockers,
        "validation_errors": validation_errors,
        "repair_scope": SELF_HEAL_REPAIR_SCOPE,
        "forbidden_actions": list(SELF_HEAL_FORBIDDEN_ACTIONS),
        "repair_prompt": SELF_HEAL_REPAIR_PROMPT if needs_repair else None,
        "boundary": (
            "Self-healing is limited to Codex repo and runtime-artifact repair. "
            "It cannot create trade authority, force paper orders, bypass guards, "
            "enable live capital, write secrets, or grant proof credit."
        ),
    }


def build_paperops_autonomous_pass_summary(
    command_results: list[dict[str, Any]],
    *,
    generated_at: str | None = None,
    summary_path: str | Path | None = None,
) -> dict[str, Any]:
    generated = generated_at or now_utc()
    mirror_runtime = _paper_mirror_runtime()
    required_gaps = _csv(
        _value(command_results, (("paper_closeout", "qadam_paper_closeout_required_gaps"),), "")
    )
    cycle_blockers = _csv(
        _value(command_results, (("paper_ops_cycle", "paper_ops_cycle_check_blockers"),), "")
    )
    operations_blockers = _csv(
        _value(
            command_results,
            (("paperops_30_day_operations", "paperops_30_day_operations_blockers"),),
            "",
        )
    )
    blockers = _unique([*required_gaps, *cycle_blockers, *operations_blockers])
    optional_gaps = _unique(
        [
            *_csv(
                _value(
                    command_results,
                    (("paper_closeout", "qadam_paper_closeout_optional_gaps"),),
                    "",
                )
            ),
            *_csv(
                _value(
                    command_results,
                    (
                        (
                            "source_gap_visibility",
                            "paperops_source_gap_visibility_optional_gap_keys",
                        ),
                    ),
                    "",
                )
            )
        ]
    )
    fresh_submit_count = _int(
        _value(
            command_results,
            (
                ("active_automation_execute", "paperops_active_runner_fresh_submit_count"),
                (
                    "active_automation_check",
                    "paperops_active_automation_paperops2_fresh_eligible_submit_record_count",
                ),
            ),
        )
    )
    duplicate_submit_count = _int(
        _value(
            command_results,
            (
                ("active_automation_execute", "paperops_active_runner_duplicate_submit_count"),
                (
                    "active_automation_check",
                    "paperops_active_automation_paperops2_duplicate_submit_record_count",
                ),
            ),
        )
    )
    submitted_paper_order_count = _int(
        _value(
            command_results,
            (
                (
                    "active_automation_execute",
                    "paperops_active_runner_submitted_paper_order_count",
                ),
                (
                    "paperops_30_day_operations",
                    "paperops_30_day_operations_submitted_paper_order_count",
                ),
                (
                    "paper_ops_cycle",
                    "paper_ops_cycle_check_submitted_paper_order_count",
                ),
            ),
        )
    )
    active_automation_state = str(
        _value(
            command_results,
            (
                ("active_automation_execute", "paperops_active_runner_status"),
                ("active_automation_check", "paperops_active_automation_status"),
            ),
            "missing",
        )
    )
    idle_reason = _value(
        command_results,
        (
            ("active_automation_execute", "paperops_active_runner_idle_reason"),
            ("active_automation_check", "paperops_active_automation_idle_reason"),
        ),
        None,
    )
    if active_automation_state == "active_automation_enabled_idle" and not idle_reason:
        idle_reason = "no_fresh_eligible_candidate"
    if (
        active_automation_state == "active_automation_enabled_idle"
        and _int(mirror_runtime.get("open_order_count")) > 0
    ):
        idle_reason = "open_orders_pending_fill"
    idempotency_guard_message = None
    if duplicate_submit_count:
        idempotency_guard_message = (
            "idempotency guard active: existing paper submit already recorded"
        )
    submit_regression_guard = build_paperops_submit_regression_guard()
    source_gap_visibility = build_paperops_source_gap_visibility()

    summary = {
        "schema_version": PAPEROPS_AUTONOMOUS_PASS_SCHEMA_VERSION,
        "artifact_type": "paperops_autonomous_pass_summary",
        "artifact_id": "paperops:autonomous-pass:latest",
        "generated_at": generated,
        "public_safe": True,
        "summary_path": str(summary_path) if summary_path else None,
        "user_facing_terms": {
            "trial": "30-day paper growth trial",
            "ledger": "paper proof ledger",
        },
        "status": None,
        "command_count": len(command_results),
        "command_passed_count": sum(1 for result in command_results if result.get("ok") is True),
        "command_failed_count": sum(1 for result in command_results if result.get("ok") is not True),
        "failed_commands": [
            str(result.get("label"))
            for result in command_results
            if result.get("ok") is not True
        ],
        "paper_growth_trial": {
            "run_id": _value(
                command_results,
                (("paperops_30_day_operations", "paperops_30_day_operations_run_id"),),
            ),
            "run_state": _value(
                command_results,
                (("paperops_30_day_operations", "paperops_30_day_operations_run_state"),),
            ),
            "run_day": _int(
                _value(
                    command_results,
                    (
                        (
                            "paperops_30_day_operations",
                            "paperops_30_day_operations_active_day_number",
                        ),
                        (
                            "paper_live_certification",
                            "paper_live_certification_phase7_active_day_number",
                        ),
                    ),
                )
            ),
            "completed_calendar_day_count": _int(
                _value(
                    command_results,
                    (
                        (
                            "paperops_30_day_operations",
                            "paperops_30_day_operations_completed_calendar_day_count",
                        ),
                    ),
                )
            ),
            "calendar_days_remaining": _int(
                _value(
                    command_results,
                    (
                        (
                            "paperops_30_day_operations",
                            "paperops_30_day_operations_calendar_days_remaining",
                        ),
                    ),
                )
            ),
            "actual_calendar_run": _bool(
                _value(
                    command_results,
                    (
                        (
                            "paperops_30_day_operations",
                            "paperops_30_day_operations_actual_calendar_run",
                        ),
                    ),
                )
            ),
            "backfill_used": _bool(
                _value(
                    command_results,
                    (("paperops_30_day_operations", "paperops_30_day_operations_backfill_used"),),
                )
            ),
            "simulated_time_used": _bool(
                _value(
                    command_results,
                    (
                        (
                            "paperops_30_day_operations",
                            "paperops_30_day_operations_simulated_time_used",
                        ),
                    ),
                )
            ),
            "no_forced_trades": _bool(
                _value(
                    command_results,
                    (
                        ("paperops_30_day_operations", "paperops_30_day_operations_no_forced_trades"),
                    ),
                )
            ),
        },
        "paper_proof_ledger": {
            "qualified_setup_count": _int(
                _value(
                    command_results,
                    (
                        (
                            "paperops_30_day_operations",
                            "paperops_30_day_operations_qualified_setup_count",
                        ),
                        ("paper_ops_cycle", "paper_ops_cycle_check_qualified_setup_count"),
                    ),
                )
            ),
            "submitted_paper_order_count": _int(
                _value(
                    command_results,
                    (
                        (
                            "paperops_30_day_operations",
                            "paperops_30_day_operations_submitted_paper_order_count",
                        ),
                        ("paper_ops_cycle", "paper_ops_cycle_check_submitted_paper_order_count"),
                    ),
                )
            ),
            "closed_proof_trade_count": _int(
                _value(
                    command_results,
                    (
                        (
                            "paperops_30_day_operations",
                            "paperops_30_day_operations_closed_proof_trade_count",
                        ),
                        ("paper_ops_cycle", "paper_ops_cycle_check_closed_proof_trade_count"),
                    ),
                )
            ),
            "no_trade_rationale": _value(
                command_results,
                (
                    (
                        "paperops_30_day_operations",
                        "paperops_30_day_operations_no_trade_rationale",
                    ),
                ),
            ),
        },
        "paper_runtime": {
            "fresh_eligible_submit_count": fresh_submit_count,
            "duplicate_submit_count": duplicate_submit_count,
            "submitted_paper_order_count": submitted_paper_order_count,
            "idle_reason": idle_reason,
            "idempotency_guard_message": idempotency_guard_message,
            "open_position_count": max(
                _int(mirror_runtime.get("open_position_count")),
                _int(
                    _value(
                        command_results,
                        (
                            ("cockpit_status", "cockpit_status_paper_open_position_count"),
                            ("active_automation_check", "paperops_active_automation_paperops3_open_position_count"),
                        ),
                    )
                ),
            ),
            "closed_paper_trade_count": max(
                _int(mirror_runtime.get("closed_paper_trade_count")),
                _int(
                    _value(
                        command_results,
                        (("cockpit_status", "cockpit_status_paper_closed_trade_count"),),
                    )
                ),
            ),
            "paper_order_count": max(
                _int(mirror_runtime.get("paper_order_count")),
                _int(
                    _value(command_results, (("cockpit_status", "cockpit_status_paper_order_count"),))
                ),
            ),
            "open_order_count": _int(mirror_runtime.get("open_order_count")),
            "order_status_counts": mirror_runtime.get("order_status_counts", {}),
            "paper_mirror_observed_at": mirror_runtime.get("observed_at"),
            "paper_mirror_status": mirror_runtime.get("status"),
        },
        "first_week_paper_trade_mandate": {
            "status": _value(
                command_results,
                (
                    (
                        "active_automation_execute",
                        "paperops_active_runner_first_week_mandate_status",
                    ),
                    (
                        "active_automation_check",
                        "paperops_active_automation_first_week_mandate_status",
                    ),
                    (
                        "first_week_trade_mandate",
                        "paperops_first_week_trade_mandate_status",
                    ),
                ),
                "missing",
            ),
            "active": _bool(
                _value(
                    command_results,
                    (
                        (
                            "active_automation_execute",
                            "paperops_active_runner_first_week_mandate_active",
                        ),
                        (
                            "active_automation_check",
                            "paperops_active_automation_first_week_mandate_active",
                        ),
                        (
                            "first_week_trade_mandate",
                            "paperops_first_week_trade_mandate_active",
                        ),
                    ),
                    "False",
                )
            ),
            "day_number": _int(
                _value(
                    command_results,
                    (
                        (
                            "active_automation_execute",
                            "paperops_active_runner_first_week_mandate_day_number",
                        ),
                        (
                            "active_automation_check",
                            "paperops_active_automation_first_week_mandate_day_number",
                        ),
                        (
                            "first_week_trade_mandate",
                            "paperops_first_week_trade_mandate_day_number",
                        ),
                    ),
                )
            ),
            "daily_target_trade_count": _int(
                _value(
                    command_results,
                    (
                        (
                            "active_automation_execute",
                            "paperops_active_runner_first_week_mandate_daily_target_trade_count",
                        ),
                        (
                            "active_automation_check",
                            "paperops_active_automation_first_week_mandate_daily_target_trade_count",
                        ),
                        (
                            "first_week_trade_mandate",
                            "paperops_first_week_trade_mandate_daily_target_trade_count",
                        ),
                    ),
                )
            ),
            "minimum_notional_usd": float(
                _value(
                    command_results,
                    (
                        (
                            "active_automation_execute",
                            "paperops_active_runner_first_week_mandate_minimum_notional_usd",
                        ),
                        (
                            "active_automation_check",
                            "paperops_active_automation_first_week_mandate_minimum_notional_usd",
                        ),
                        (
                            "first_week_trade_mandate",
                            "paperops_first_week_trade_mandate_minimum_notional_usd",
                        ),
                    ),
                    "0",
                )
                or 0
            ),
            "daily_ready_submit_count": _int(
                _value(
                    command_results,
                    (
                        (
                            "active_automation_execute",
                            "paperops_active_runner_first_week_mandate_daily_ready_submit_count",
                        ),
                        (
                            "active_automation_check",
                            "paperops_active_automation_first_week_mandate_daily_ready_submit_count",
                        ),
                        (
                            "first_week_trade_mandate",
                            "paperops_first_week_trade_mandate_daily_ready_submit_count",
                        ),
                    ),
                )
            ),
            "daily_submitted_count": _int(
                _value(
                    command_results,
                    (
                        (
                            "active_automation_execute",
                            "paperops_active_runner_first_week_mandate_daily_submitted_count",
                        ),
                        (
                            "active_automation_check",
                            "paperops_active_automation_first_week_mandate_daily_submitted_count",
                        ),
                        (
                            "first_week_trade_mandate",
                            "paperops_first_week_trade_mandate_daily_submitted_count",
                        ),
                    ),
                )
            ),
        },
        "telegram_inbound": {
            "record_count": _int(
                _value(command_results, (("telegram_inbound", "telegram_inbound_poll_record_count"),))
            ),
            "world_event_datapoint_count": _int(
                _value(
                    command_results,
                    (("telegram_inbound", "telegram_inbound_poll_world_event_datapoint_count"),),
                )
            ),
            "strategy_consideration_count": _int(
                _value(
                    command_results,
                    (
                        (
                            "telegram_inbound",
                            "telegram_inbound_poll_strategy_consideration_count",
                        ),
                    ),
                )
            ),
            "boundary": _value(
                command_results,
                (("telegram_inbound", "telegram_inbound_poll_boundary"),),
            ),
        },
        "states": {
            "paper_ops_cycle_state": _value(
                command_results,
                (("paper_ops_cycle", "paper_ops_cycle_check_status"),),
                "missing",
            ),
            "paper_ops_cycle_contract_check": _value(
                command_results,
                (("paper_ops_cycle", "paper_operational_cycle_contract_check"),),
                "missing",
            ),
            "active_automation_state": active_automation_state,
            "paper_live_certification_state": _value(
                command_results,
                (("paper_live_certification", "paper_live_certification_status"),),
                "missing",
            ),
            "closeout_status": _value(
                command_results,
                (("paper_closeout", "qadam_paper_closeout_status"),),
                "missing",
            ),
            "cockpit_mirror_state": _value(
                command_results,
                (("cockpit_status", "cockpit_status_mission_control_status"),),
                "missing",
            ),
            "cockpit_paper_mirror_state": _value(
                command_results,
                (("cockpit_status", "cockpit_status_paper_mirror_status"),),
                "missing",
            ),
            "quantum_provider_diagnostic_state": _value(
                command_results,
                (("paper_closeout", "qadam_paper_closeout_fire_opal_ibm_status"),),
                "missing",
            ),
        },
        "safety": {
            "live_capital_enabled": _bool(
                _value(
                    command_results,
                    (
                        ("paperops_30_day_operations", "paperops_30_day_operations_live_capital_enabled"),
                        ("cockpit_status", "cockpit_status_live_capital_enabled"),
                    ),
                    "False",
                )
            ),
            "phase7_proof_credit_allowed": _bool(
                _value(
                    command_results,
                    (
                        (
                            "paperops_30_day_operations",
                            "paperops_30_day_operations_phase7_proof_credit_allowed",
                        ),
                    ),
                    "False",
                )
            ),
            "broker_post_called_count": _int(
                _value(command_results, (("paper_ops_cycle", "paper_ops_cycle_check_broker_post_called_count"),))
            ),
            "alpaca_post_called_count": _int(
                _value(command_results, (("paper_ops_cycle", "paper_ops_cycle_check_alpaca_post_called_count"),))
            ),
            "notification_live_send_allowed_count": _int(
                _value(
                    command_results,
                    (
                        (
                            "cockpit_notification",
                            "paperops_cockpit_notification_upgrade_notification_live_send_allowed_count",
                        ),
                    ),
                )
            ),
            "command_path_enabled_count": _int(
                _value(
                    command_results,
                    (
                        (
                            "cockpit_notification",
                            "paperops_cockpit_notification_upgrade_notification_command_path_enabled_count",
                        ),
                    ),
                )
            ),
        },
        "blockers": blockers,
        "blocker_count": len(blockers),
        "optional_gaps": optional_gaps,
        "optional_gap_count": len(optional_gaps),
        "optional_coverage_gaps": [
            gap for gap in optional_gaps if gap in OPTIONAL_COVERAGE_GAP_KEYS
        ],
        "source_gap_visibility": source_gap_visibility,
        "submit_regression_guard": submit_regression_guard,
        "command_results": command_results,
    }
    summary["paper_runtime"]["submitted_paper_order_count"] = max(
        _int(summary["paper_runtime"].get("submitted_paper_order_count")),
        _int(summary["first_week_paper_trade_mandate"].get("daily_submitted_count")),
    )
    summary["close_to_ledger"] = build_paperops_close_to_ledger(
        generated_at=generated,
    )
    summary["paper_proof_ledger"]["closed_proof_trade_count"] = max(
        _int(summary["paper_proof_ledger"].get("closed_proof_trade_count")),
        _int(summary["close_to_ledger"].get("closed_proof_trade_count")),
    )
    summary["closed_trade_funnel"] = build_paperops_closed_trade_funnel(
        generated_at=generated,
        paper_runtime=summary["paper_runtime"],
        paper_proof_ledger=summary["paper_proof_ledger"],
    )
    summary["status"] = _status(command_results, blockers)
    summary["automation_report_lines"] = [
        f"30-day paper growth trial day {summary['paper_growth_trial']['run_day']} is {summary['status']}.",
        (
            "Paper proof ledger has "
            f"{summary['paper_proof_ledger']['qualified_setup_count']} qualified setups, "
            f"{summary['paper_proof_ledger']['submitted_paper_order_count']} submitted paper orders, "
            f"and {summary['paper_proof_ledger']['closed_proof_trade_count']} closed proof trades."
        ),
        (
            "Active paper runner is idle: daily paper target met."
            if idle_reason == "daily_paper_trade_target_met"
            else "Active paper runner is waiting on open Alpaca paper orders to fill."
            if idle_reason == "open_orders_pending_fill"
            else "Active paper runner is idle: no fresh eligible candidate."
            if idle_reason == "no_fresh_eligible_candidate"
            else f"Active paper runner state is {active_automation_state}."
        ),
        (
            "First-week paper mandate: "
            f"{summary['first_week_paper_trade_mandate']['daily_submitted_count']}/"
            f"{summary['first_week_paper_trade_mandate']['daily_target_trade_count']} "
            "paper orders submitted today at "
            f"USD {summary['first_week_paper_trade_mandate']['minimum_notional_usd']:.0f} "
            "minimum notional."
        ),
        (
            "Closed paper trade funnel is blocked at "
            f"{summary['closed_trade_funnel']['blocked_stage'] or 'none'}: "
            f"{summary['closed_trade_funnel']['next_required_action']}"
        ),
        (
            "Submit-side guard is "
            f"{summary['submit_regression_guard']['status']} with "
            f"{summary['submit_regression_guard']['fresh_eligible_submit_record_count']} "
            "fresh eligible submits and "
            f"{summary['submit_regression_guard']['duplicate_submit_record_count']} "
            "idempotency-held duplicates."
        ),
        (
            "Source gaps are explicit: "
            f"{summary['source_gap_visibility']['optional_gap_count']} optional, "
            f"{summary['source_gap_visibility']['trade_blocking_source_gap_count']} "
            "trade-blocking."
        ),
    ]
    if _int(summary["paper_runtime"].get("open_order_count")):
        summary["automation_report_lines"].append(
            "Paper broker mirror has "
            f"{summary['paper_runtime']['open_order_count']} open orders pending fill; "
            "closed-trade count moves only after Alpaca fills them."
        )
    summary["validation_errors"] = validate_paperops_autonomous_pass_summary(summary)
    summary["validation_error_count"] = len(summary["validation_errors"])
    if summary["validation_errors"] and summary["status"] == "ready_idle":
        summary["status"] = "degraded"
    summary["self_healing"] = _self_healing_request(summary)
    if summary["self_healing"]["needs_repair"]:
        summary["automation_report_lines"].append(
            "Self-heal repair requested for the next automation pass."
        )
    return summary


def validate_paperops_autonomous_pass_summary(summary: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if summary.get("schema_version") != PAPEROPS_AUTONOMOUS_PASS_SCHEMA_VERSION:
        errors.append("paperops_autonomous_pass_schema_version_mismatch")
    if summary.get("public_safe") is not True:
        errors.append("paperops_autonomous_pass_not_public_safe")
    if summary.get("safety", {}).get("live_capital_enabled") is not False:
        errors.append("paperops_autonomous_pass_live_capital_enabled")
    if summary.get("safety", {}).get("phase7_proof_credit_allowed") is not False:
        errors.append("paperops_autonomous_pass_proof_credit_allowed")
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "notification_live_send_allowed_count",
        "command_path_enabled_count",
    ):
        if _int(summary.get("safety", {}).get(key)) != 0:
            errors.append(f"paperops_autonomous_pass_unsafe_counter_nonzero:{key}")
    optional_gaps = set(summary.get("optional_gaps", []) or [])
    blockers = set(summary.get("blockers", []) or [])
    if blockers & OPTIONAL_COVERAGE_GAP_KEYS:
        errors.append("paperops_autonomous_pass_optional_gap_promoted_to_blocker")
    if not set(summary.get("optional_coverage_gaps", []) or []).issubset(optional_gaps):
        errors.append("paperops_autonomous_pass_optional_coverage_gap_mismatch")
    source_gap_visibility = summary.get("source_gap_visibility")
    if not isinstance(source_gap_visibility, dict):
        errors.append("paperops_autonomous_pass_source_gap_visibility_missing")
    else:
        for error in validate_paperops_source_gap_visibility(source_gap_visibility):
            errors.append(f"paperops_autonomous_pass_source_gap_visibility:{error}")
        source_optional = set(source_gap_visibility.get("optional_gap_keys", []) or [])
        if not source_optional.issubset(optional_gaps):
            errors.append("paperops_autonomous_pass_source_gap_optional_missing")
        if blockers & source_optional:
            errors.append("paperops_autonomous_pass_source_gap_promoted_to_blocker")
        if _int(source_gap_visibility.get("required_gap_count")) != 0:
            errors.append("paperops_autonomous_pass_source_gap_required_nonzero")
        if _int(source_gap_visibility.get("trade_blocking_source_gap_count")) != 0:
            errors.append("paperops_autonomous_pass_source_gap_trade_blocking")
        if _int(source_gap_visibility.get("silent_blocker_count")) != 0:
            errors.append("paperops_autonomous_pass_source_gap_silent_blocker")
        if _int(source_gap_visibility.get("blocker_count")) != 0:
            errors.append("paperops_autonomous_pass_source_gap_blocker_nonzero")
    funnel = summary.get("closed_trade_funnel")
    if not isinstance(funnel, dict):
        errors.append("paperops_autonomous_pass_closed_trade_funnel_missing")
    else:
        for error in validate_paperops_closed_trade_funnel(funnel):
            errors.append(f"paperops_autonomous_pass_closed_trade_funnel:{error}")
    close_to_ledger = summary.get("close_to_ledger")
    if not isinstance(close_to_ledger, dict):
        errors.append("paperops_autonomous_pass_close_to_ledger_missing")
    else:
        for error in validate_paperops_close_to_ledger(close_to_ledger):
            errors.append(f"paperops_autonomous_pass_close_to_ledger:{error}")
    submit_regression_guard = summary.get("submit_regression_guard")
    if not isinstance(submit_regression_guard, dict):
        errors.append("paperops_autonomous_pass_submit_regression_guard_missing")
    else:
        for error in validate_paperops_submit_regression_guard(submit_regression_guard):
            errors.append(f"paperops_autonomous_pass_submit_regression_guard:{error}")
        if submit_regression_guard.get("status") not in {
            "healthy_idle_idempotency_guarded",
            "healthy_idle_no_fresh_submit",
            "ready_fresh_submit_consistent",
        }:
            errors.append("paperops_autonomous_pass_submit_regression_guard_not_ready")
        if _int(submit_regression_guard.get("blocker_count")) != 0:
            errors.append("paperops_autonomous_pass_submit_regression_guard_blocked")
        for key in (
            "source_stale_after_post_tolerance_count",
            "fresh_submitted_ledger_collision_count",
            "duplicate_misclassified_as_fresh_count",
            "live_endpoint_called_count",
            "broker_post_called_count",
            "broker_write_allowed_count",
        ):
            if _int(submit_regression_guard.get(key)) != 0:
                errors.append(
                    f"paperops_autonomous_pass_submit_regression_counter_nonzero:{key}"
                )
        paper_runtime = summary.get("paper_runtime", {})
        if _int(
            submit_regression_guard.get("fresh_eligible_submit_record_count")
        ) != _int(paper_runtime.get("fresh_eligible_submit_count")):
            errors.append("paperops_autonomous_pass_submit_regression_fresh_mismatch")
        if _int(
            submit_regression_guard.get("duplicate_submit_record_count")
        ) != _int(paper_runtime.get("duplicate_submit_count")):
            errors.append("paperops_autonomous_pass_submit_regression_duplicate_mismatch")
    first_week = summary.get("first_week_paper_trade_mandate", {})
    if first_week.get("active") is True:
        if _int(first_week.get("daily_target_trade_count")) != 3:
            errors.append("paperops_autonomous_pass_first_week_target_invalid")
        if float(first_week.get("minimum_notional_usd") or 0) < 6000:
            errors.append("paperops_autonomous_pass_first_week_notional_invalid")
        if _int(first_week.get("daily_submitted_count")) > _int(
            first_week.get("daily_target_trade_count")
        ):
            errors.append("paperops_autonomous_pass_first_week_oversubmitted")
    if summary.get("states", {}).get("paper_ops_cycle_contract_check") == "ok":
        if summary.get("states", {}).get("paper_ops_cycle_state") == (
            "paper_cycle_full_paper_operational_ready"
        ) and summary.get("blocker_count") != 0:
            errors.append("paperops_autonomous_pass_ready_cycle_with_blockers")
    report_text = "\n".join(summary.get("automation_report_lines", []) or [])
    if "Phase 7" in report_text:
        errors.append("paperops_autonomous_pass_report_uses_phase7_wording")
    if "30-day paper growth trial" not in report_text:
        errors.append("paperops_autonomous_pass_missing_paper_growth_trial_wording")
    if "Paper proof ledger" not in report_text:
        errors.append("paperops_autonomous_pass_missing_paper_proof_ledger_wording")
    if (
        summary.get("states", {}).get("active_automation_state")
        == "active_automation_enabled_idle"
        and summary.get("paper_runtime", {}).get("fresh_eligible_submit_count") == 0
        and summary.get("paper_runtime", {}).get("idle_reason")
        not in {
            "no_fresh_eligible_candidate",
            "daily_paper_trade_target_met",
            "open_orders_pending_fill",
        }
    ):
        errors.append("paperops_autonomous_pass_missing_idle_reason")
    return sorted(set(errors))


def write_paperops_autonomous_pass_summary(
    summary: dict[str, Any],
    *,
    settings: Settings | None = None,
    path: str | Path | None = None,
) -> Path:
    output_path = Path(path or runtime_summary_path(settings))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary["summary_path"] = str(output_path)
    output_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path
