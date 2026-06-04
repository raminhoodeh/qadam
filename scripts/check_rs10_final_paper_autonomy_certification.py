#!/usr/bin/env python3
"""Validate RS-10 final paper-autonomy certification."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.rs10_final_paper_autonomy_certification import (  # noqa: E402
    AUTHORITY_FIELDS,
    PUBLIC_STATUS_FIELDS,
    UNSAFE_COUNT_FIELDS,
    build_rs10_final_paper_autonomy_certification,
    rs10_final_paper_autonomy_paths,
    rs10_final_paper_autonomy_public_status,
    validate_rs10_final_paper_autonomy_certification,
    write_rs10_final_paper_autonomy_certification,
)


def _has_error(errors: list[str], prefix_or_exact: str) -> bool:
    return any(
        error == prefix_or_exact or error.startswith(prefix_or_exact)
        for error in errors
    )


def _assert_no_public_leak(value: Any, errors: list[str], path_label: str = "$") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            lowered = str(key).lower()
            if lowered in {
                "raw_payload",
                "private_payload",
                "broker_order_id",
                "external_order_id",
                "access_token",
                "refresh_token",
                "secret",
                "chat_id",
                "bot_token",
            }:
                errors.append(f"RS-10 public leak key at {path_label}.{key}")
            _assert_no_public_leak(nested, errors, f"{path_label}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _assert_no_public_leak(item, errors, f"{path_label}[{index}]")
        return
    if not isinstance(value, str):
        return
    lowered = value.lower()
    if value.startswith("/") or value.startswith("~") or (len(value) > 2 and value[1:3] == ":\\"):
        errors.append(f"RS-10 local path leaked at {path_label}")
    if any(marker in lowered for marker in ("api_key", "bearer ", "secret_", "token_", "token=", "secret=")):
        errors.append(f"RS-10 secret marker leaked at {path_label}")
    if any(marker in lowered for marker in ("broker_order_id", "external_order_id", "fill_id")):
        errors.append(f"RS-10 broker identifier leaked at {path_label}")


def main() -> int:
    settings = Settings.from_env()
    errors: list[str] = []
    output_path, history_path, event_log_path = rs10_final_paper_autonomy_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    artifact = build_rs10_final_paper_autonomy_certification(settings=settings)
    output_path, history_path, event_log_path, written = (
        write_rs10_final_paper_autonomy_certification(
            artifact,
            settings=settings,
            record_event=True,
            event_log_path=event_log_path,
        )
    )
    public_status = rs10_final_paper_autonomy_public_status(settings=settings)
    validation_errors = validate_rs10_final_paper_autonomy_certification(written)
    public_validation_errors = validate_rs10_final_paper_autonomy_certification(
        public_status
    )
    replay = EventLog(event_log_path, echo=False).replay()

    if validation_errors:
        errors.append("RS-10 validation errors: " + "; ".join(validation_errors))
    if public_validation_errors:
        errors.append(
            "RS-10 public validation errors: " + "; ".join(public_validation_errors)
        )
    if not output_path.exists():
        errors.append("RS-10 runtime artifact was not written")
    if not history_path.exists():
        errors.append("RS-10 history log was not written")
    if not event_log_path.exists():
        errors.append("RS-10 Event Log was not written")
    if replay.get("total_events") != 1:
        errors.append("RS-10 Event Log must contain exactly one event for this check")
    if written.get("phase") != "RS" or written.get("stage") != "RS-10":
        errors.append("RS-10 phase/stage mismatch")
    if written.get("status") not in {
        "certified_actionable",
        "certified_waiting_for_qualified_setup",
        "certified_idle",
    }:
        errors.append("RS-10 status is not a certified state")
    if written.get("final_paper_autonomy_certified") is not True:
        errors.append("RS-10 final paper autonomy is not certified")
    if written.get("guarded_paper_autonomy_allowed") is not True:
        errors.append("RS-10 guarded paper autonomy is not allowed")
    if written.get("multiple_paper_trades_per_day_allowed_when_gates_pass") is not True:
        errors.append("RS-10 multiple paper trades policy is disabled")
    if written.get("certification_blocker_count") != 0:
        errors.append("RS-10 certification blockers are present")
    if written.get("safety_blocker_count") != 0:
        errors.append("RS-10 safety blockers are present")
    if written.get("stale_blocker_in_current_count") != 0:
        errors.append("RS-10 stale blocker appears as current")
    if written.get("live_capital_enabled") is not False:
        errors.append("RS-10 live capital must remain disabled")
    if written.get("live_capital_blocked") is not True:
        errors.append("RS-10 live capital must remain explicitly blocked")
    if written.get("paper_submission_transport") != "paperops_guarded_alpaca_paper":
        errors.append("RS-10 paper submission transport mismatch")
    if written.get("daily_target_policy") != "minimum_not_ceiling":
        errors.append("RS-10 daily target policy mismatch")
    if int(written.get("opportunity_scan_interval_minutes") or 0) != 20:
        errors.append("RS-10 opportunity cadence should be 20 minutes")
    if int(written.get("max_guarded_submit_attempts_per_run") or 0) > 3:
        errors.append("RS-10 submit attempt cap is too high")
    if written.get("rate_limit_policy_present") is not True:
        errors.append("RS-10 rate-limit policy missing")
    if written.get("autonomy_currently_actionable") is True and not any(
        written.get(key) is True
        for key in (
            "paper_submit_currently_allowed",
            "paper_poll_currently_allowed",
            "paper_exit_currently_allowed",
        )
    ):
        errors.append("RS-10 is actionable without an allowed paper action")
    if (
        written.get("paper_submit_currently_allowed") is True
        and written.get("paperops_active_status") != "active_automation_ready_to_submit"
    ):
        errors.append("RS-10 invented paper submit authority")

    for field in AUTHORITY_FIELDS:
        if written.get(field) is not False:
            errors.append(f"RS-10 authority enabled: {field}")
    for field in UNSAFE_COUNT_FIELDS:
        if int(written.get(field) or 0) != 0:
            errors.append(f"RS-10 unsafe or exposure count nonzero: {field}")

    if set(public_status) - set(PUBLIC_STATUS_FIELDS):
        errors.append("RS-10 public status exposes non-public fields")
    if public_status.get("status") != written.get("status"):
        errors.append("RS-10 public status mismatch: status")
    if public_status.get("final_paper_autonomy_certified") != written.get(
        "final_paper_autonomy_certified"
    ):
        errors.append("RS-10 public status mismatch: certification")
    if public_status.get("guarded_paper_autonomy_allowed") != written.get(
        "guarded_paper_autonomy_allowed"
    ):
        errors.append("RS-10 public status mismatch: guarded autonomy")
    _assert_no_public_leak(public_status, errors, "$.rs10_final_paper_autonomy")

    live_probe = deepcopy(written)
    live_probe["live_capital_enabled"] = True
    live_probe["live_capital_blocked"] = False
    live_errors = validate_rs10_final_paper_autonomy_certification(live_probe)
    if not _has_error(live_errors, "rs10_authority_enabled:live_capital_enabled"):
        errors.append("RS-10 failed to reject live capital")
    if not _has_error(live_errors, "rs10_live_capital_not_blocked"):
        errors.append("RS-10 failed to require live-capital block")

    command_probe = deepcopy(written)
    command_probe["dashboard_command_authority"] = True
    command_probe["telegram_command_authority"] = True
    command_errors = validate_rs10_final_paper_autonomy_certification(command_probe)
    if not _has_error(command_errors, "rs10_authority_enabled:dashboard_command_authority"):
        errors.append("RS-10 failed to reject dashboard command authority")
    if not _has_error(command_errors, "rs10_authority_enabled:telegram_command_authority"):
        errors.append("RS-10 failed to reject Telegram command authority")

    model_probe = deepcopy(written)
    model_probe["local_llm_execution_authority"] = True
    model_probe["frontier_llm_execution_authority"] = True
    model_probe["quantum_execution_authority"] = True
    model_errors = validate_rs10_final_paper_autonomy_certification(model_probe)
    if not _has_error(model_errors, "rs10_authority_enabled:local_llm_execution_authority"):
        errors.append("RS-10 failed to reject local LLM execution authority")
    if not _has_error(model_errors, "rs10_authority_enabled:frontier_llm_execution_authority"):
        errors.append("RS-10 failed to reject frontier LLM execution authority")
    if not _has_error(model_errors, "rs10_authority_enabled:quantum_execution_authority"):
        errors.append("RS-10 failed to reject quantum execution authority")

    broker_probe = deepcopy(written)
    broker_probe["unmanaged_broker_write_allowed"] = True
    broker_probe["broker_post_allowed"] = True
    broker_probe["alpaca_post_allowed"] = True
    broker_probe["broker_post_called_count"] = 1
    broker_probe["unsafe_write_counter_total"] = 1
    broker_errors = validate_rs10_final_paper_autonomy_certification(broker_probe)
    if not _has_error(broker_errors, "rs10_authority_enabled:unmanaged_broker_write_allowed"):
        errors.append("RS-10 failed to reject unmanaged broker writes")
    if not _has_error(broker_errors, "rs10_unsafe_count_nonzero:broker_post_called_count"):
        errors.append("RS-10 failed to reject broker POST count")

    proof_probe = deepcopy(written)
    proof_probe["phase7_proof_credit_allowed"] = True
    proof_errors = validate_rs10_final_paper_autonomy_certification(proof_probe)
    if not _has_error(proof_errors, "rs10_authority_enabled:phase7_proof_credit_allowed"):
        errors.append("RS-10 failed to reject Phase 7 proof credit")

    stale_probe = deepcopy(written)
    stale_probe["stale_blocker_in_current_count"] = 1
    stale_errors = validate_rs10_final_paper_autonomy_certification(stale_probe)
    if not _has_error(stale_errors, "rs10_stale_blocker_in_current"):
        errors.append("RS-10 failed to reject stale current blocker")

    fake_submit_probe = deepcopy(written)
    fake_submit_probe["paper_submit_currently_allowed"] = True
    fake_submit_probe["autonomy_currently_actionable"] = True
    fake_submit_probe["paperops_active_status"] = "active_automation_enabled_idle"
    fake_submit_errors = validate_rs10_final_paper_autonomy_certification(
        fake_submit_probe
    )
    if not _has_error(fake_submit_errors, "rs10_submit_allowed_without_active_submit_status"):
        errors.append("RS-10 failed to reject fake current submit authority")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print("rs10_final_paper_autonomy_check=failed")
        return 1

    print("rs10_final_paper_autonomy_check=ok")
    print(f"rs10_status={written['status']}")
    print(f"rs10_final_paper_autonomy_certified={written['final_paper_autonomy_certified']}")
    print(f"rs10_guarded_paper_autonomy_allowed={written['guarded_paper_autonomy_allowed']}")
    print(f"rs10_autonomy_currently_actionable={written['autonomy_currently_actionable']}")
    print(f"rs10_current_blocker_count={written['current_blocker_count']}")
    print(f"rs10_current_blockers={','.join(written.get('current_blockers', []) or [])}")
    print(f"rs10_why_not_trading_now={written['why_not_trading_now']}")
    print(
        "rs10_multiple_paper_trades_per_day_allowed_when_gates_pass="
        f"{written['multiple_paper_trades_per_day_allowed_when_gates_pass']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
