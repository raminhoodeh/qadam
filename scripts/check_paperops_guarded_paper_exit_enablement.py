#!/usr/bin/env python3
"""Validate PT-7 guarded PaperOps paper-exit runtime enablement."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.paperops_guarded_paper_exit_enablement import (  # noqa: E402
    PAPEROPS_GUARDED_EXIT_ENABLEMENT_SCHEMA_VERSION,
    build_paperops_guarded_paper_exit_enablement,
    paperops_guarded_paper_exit_enablement_paths,
    validate_paperops_guarded_paper_exit_enablement,
    write_paperops_guarded_paper_exit_enablement,
)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_path = paperops_guarded_paper_exit_enablement_paths(
        settings
    )
    if event_path.exists():
        event_path.unlink()

    artifact = build_paperops_guarded_paper_exit_enablement(settings=settings)
    output_path, history_path, event_path, written = (
        write_paperops_guarded_paper_exit_enablement(
            artifact,
            settings=settings,
            record_event=True,
            event_log_path=event_path,
        )
    )
    validation_errors = validate_paperops_guarded_paper_exit_enablement(written)
    replay = EventLog(event_path, echo=False).replay()

    env_probe = deepcopy(written)
    env_probe["env_file_edited"] = True
    env_errors = validate_paperops_guarded_paper_exit_enablement(env_probe)

    execute_probe = deepcopy(written)
    execute_probe["execute_exit_requested"] = True
    execute_errors = validate_paperops_guarded_paper_exit_enablement(execute_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_errors = validate_paperops_guarded_paper_exit_enablement(
        live_capital_probe
    )

    close_probe = deepcopy(written)
    close_probe["position_close_allowed"] = True
    close_probe["paper_position_close_called_count"] = 1
    close_probe["unsafe_write_counter_total"] = 1
    close_errors = validate_paperops_guarded_paper_exit_enablement(close_probe)

    broker_probe = deepcopy(written)
    broker_probe["broker_write_allowed"] = True
    broker_probe["broker_post_allowed"] = True
    broker_probe["unsafe_write_counter_total"] = 1
    broker_errors = validate_paperops_guarded_paper_exit_enablement(broker_probe)

    live_endpoint_probe = deepcopy(written)
    live_endpoint_probe["live_endpoint_allowed"] = True
    live_endpoint_probe["live_endpoint_called_count"] = 1
    live_endpoint_probe["unsafe_write_counter_total"] = 1
    live_endpoint_errors = validate_paperops_guarded_paper_exit_enablement(
        live_endpoint_probe
    )

    proof_probe = deepcopy(written)
    proof_probe["phase7_proof_credit_allowed"] = True
    proof_errors = validate_paperops_guarded_paper_exit_enablement(proof_probe)

    forced_probe = deepcopy(written)
    forced_probe["forced_trades_allowed"] = True
    forced_errors = validate_paperops_guarded_paper_exit_enablement(forced_probe)

    secret_probe = deepcopy(written)
    secret_probe["secret_value_exposed"] = True
    secret_errors = validate_paperops_guarded_paper_exit_enablement(secret_probe)

    path_without_open_probe = deepcopy(written)
    path_without_open_probe["paper_exit_path_available"] = True
    path_without_open_probe["paperops_3_open_position_count"] = 0
    path_without_open_errors = validate_paperops_guarded_paper_exit_enablement(
        path_without_open_probe
    )

    print(f"paperops_guarded_exit_enablement_status={written['status']}")
    print(
        "paperops_guarded_exit_enablement_schema_version="
        f"{PAPEROPS_GUARDED_EXIT_ENABLEMENT_SCHEMA_VERSION}"
    )
    print(f"paperops_guarded_exit_enablement_artifact_path={output_path}")
    print(f"paperops_guarded_exit_enablement_history_path={history_path}")
    print(f"paperops_guarded_exit_enablement_event_log_path={event_path}")
    print(f"paperops_guarded_exit_enablement_mode={written['mode']}")
    print(
        "paperops_guarded_exit_enablement_enabled="
        f"{written['guarded_paper_exit_enabled']}"
    )
    print(
        "paperops_guarded_exit_enablement_effective="
        f"{written['alpaca_paper_exit_effective']}"
    )
    print(
        "paperops_guarded_exit_enablement_settings_flag="
        f"{written['settings_alpaca_paper_exit_enabled']}"
    )
    print(
        "paperops_guarded_exit_enablement_runtime_override="
        f"{written['runtime_artifact_override_enabled']}"
    )
    print(
        "paperops_guarded_exit_enablement_env_file_edited="
        f"{written['env_file_edited']}"
    )
    print(
        "paperops_guarded_exit_enablement_path_available="
        f"{written['paper_exit_path_available']}"
    )
    print(
        "paperops_guarded_exit_enablement_idle_until_open_position="
        f"{written['paper_exit_idle_until_open_position']}"
    )
    print(
        "paperops_guarded_exit_enablement_explicit_exit_flag_required="
        f"{written['explicit_exit_flag_required']}"
    )
    print(
        "paperops_guarded_exit_enablement_execute_exit_requested="
        f"{written['execute_exit_requested']}"
    )
    print(
        "paperops_guarded_exit_enablement_lifecycle_polling_status="
        f"{written['lifecycle_polling_enablement_status']}"
    )
    print(
        "paperops_guarded_exit_enablement_lifecycle_polling_ready="
        f"{written['lifecycle_polling_enablement_ready']}"
    )
    print(
        "paperops_guarded_exit_enablement_paperops3_status="
        f"{written['paperops_3_status']}"
    )
    print(
        "paperops_guarded_exit_enablement_paperops3_source_valid="
        f"{written['paperops_3_source_valid']}"
    )
    print(
        "paperops_guarded_exit_enablement_paperops3_open_position_count="
        f"{written['paperops_3_open_position_count']}"
    )
    print(
        "paperops_guarded_exit_enablement_endpoint_classification="
        f"{written['endpoint_classification']}"
    )
    print(
        "paperops_guarded_exit_enablement_paper_endpoint_confirmed="
        f"{written['paper_endpoint_confirmed']}"
    )
    print(
        "paperops_guarded_exit_enablement_key_configured="
        f"{written['alpaca_api_key_configured']}"
    )
    print(
        "paperops_guarded_exit_enablement_secret_configured="
        f"{written['alpaca_api_secret_configured']}"
    )
    print(
        "paperops_guarded_exit_enablement_close_called_count="
        f"{written['paper_position_close_called_count']}"
    )
    print(
        "paperops_guarded_exit_enablement_live_endpoint_called_count="
        f"{written['live_endpoint_called_count']}"
    )
    print(
        "paperops_guarded_exit_enablement_live_capital_enabled="
        f"{written['live_capital_enabled']}"
    )
    print(
        "paperops_guarded_exit_enablement_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(
        "paperops_guarded_exit_enablement_forced_trades_allowed="
        f"{written['forced_trades_allowed']}"
    )
    print(
        "paperops_guarded_exit_enablement_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(f"paperops_guarded_exit_enablement_event_log_events={replay['total_events']}")
    print(
        "paperops_guarded_exit_enablement_blockers="
        f"{','.join(written['blockers'])}"
    )
    print(f"paperops_guarded_exit_enablement_validation_errors={validation_errors}")

    if validation_errors:
        errors.append(f"PT-7 validation failed: {validation_errors}")
    if replay["total_events"] != 1:
        errors.append("PT-7 event log did not record exactly one event")
    if written["status"] not in {
        "enabled_pending_open_position_readback",
        "enabled_pending_explicit_exit",
    }:
        errors.append("PT-7 did not enable the guarded paper exit path")
    if written["guarded_paper_exit_enabled"] is not True:
        errors.append("PT-7 guarded exit flag is not true")
    if written["alpaca_paper_exit_effective"] is not True:
        errors.append("PT-7 effective exit flag is not true")
    if written["settings_alpaca_paper_exit_enabled"] is not False:
        errors.append("PT-7 expected runtime override instead of env flag")
    if written["runtime_artifact_override_enabled"] is not True:
        errors.append("PT-7 runtime override is not active")
    if written["env_file_edited"] is not False:
        errors.append("PT-7 edited the environment file")
    if written["explicit_exit_flag_required"] is not True:
        errors.append("PT-7 did not require explicit exit handoff")
    if written["execute_exit_requested"] is not False:
        errors.append("PT-7 requested an exit directly")
    if written["lifecycle_polling_enablement_ready"] is not True:
        errors.append("PT-7 did not see ready PT-6 lifecycle polling enablement")
    if written["paperops_3_source_valid"] is not True:
        errors.append("PT-7 did not see a valid PaperOps-3 readback source")
    if written["paperops_3_open_position_count"] == 0:
        if written["paper_exit_path_available"] is not False:
            errors.append("PT-7 exposed exit path without an open position readback")
        if written["paper_exit_idle_until_open_position"] is not True:
            errors.append("PT-7 did not mark exit path idle while no open position exists")
    if written["paper_position_close_called_count"]:
        errors.append("PT-7 closed a paper position directly")
    if written["live_endpoint_called_count"]:
        errors.append("PT-7 called a live endpoint")
    if written["live_capital_enabled"] is not False:
        errors.append("PT-7 enabled live capital")
    if written["phase7_proof_credit_allowed"] is not False:
        errors.append("PT-7 granted Phase 7 proof credit")
    if written["forced_trades_allowed"] is not False:
        errors.append("PT-7 allowed forced trades")
    if "paperops_guarded_exit_enablement_forbidden:env_file_edited" not in env_errors:
        errors.append("env-file probe was not rejected")
    if (
        "paperops_guarded_exit_enablement_forbidden:execute_exit_requested"
        not in execute_errors
    ):
        errors.append("execute-exit probe was not rejected")
    if (
        "paperops_guarded_exit_enablement_forbidden:live_capital_enabled"
        not in live_capital_errors
    ):
        errors.append("live-capital probe was not rejected")
    if (
        "paperops_guarded_exit_enablement_forbidden:position_close_allowed"
        not in close_errors
    ):
        errors.append("close-authority probe was not rejected")
    if (
        "paperops_guarded_exit_enablement_unsafe_counter_nonzero:"
        "paper_position_close_called_count"
        not in close_errors
    ):
        errors.append("close-counter probe was not rejected")
    if (
        "paperops_guarded_exit_enablement_forbidden:broker_post_allowed"
        not in broker_errors
    ):
        errors.append("broker-authority probe was not rejected")
    if (
        "paperops_guarded_exit_enablement_forbidden:live_endpoint_allowed"
        not in live_endpoint_errors
    ):
        errors.append("live-endpoint authority probe was not rejected")
    if (
        "paperops_guarded_exit_enablement_unsafe_counter_nonzero:live_endpoint_called_count"
        not in live_endpoint_errors
    ):
        errors.append("live-endpoint counter probe was not rejected")
    if (
        "paperops_guarded_exit_enablement_forbidden:phase7_proof_credit_allowed"
        not in proof_errors
    ):
        errors.append("proof-credit probe was not rejected")
    if "paperops_guarded_exit_enablement_forbidden:forced_trades_allowed" not in forced_errors:
        errors.append("forced-trade probe was not rejected")
    if "paperops_guarded_exit_enablement_forbidden:secret_value_exposed" not in secret_errors:
        errors.append("secret-exposure probe was not rejected")
    if (
        "paperops_guarded_exit_enablement_path_without_open_position"
        not in path_without_open_errors
    ):
        errors.append("path-without-open-position probe was not rejected")

    if errors:
        print("paperops_guarded_paper_exit_enablement_check=failed")
        for error in errors:
            print(f"error={error}")
        return 1
    print("paperops_guarded_paper_exit_enablement_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
