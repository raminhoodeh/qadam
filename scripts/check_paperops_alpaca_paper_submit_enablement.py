#!/usr/bin/env python3
"""Validate PT-5 Alpaca paper-submit runtime enablement."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.paperops_alpaca_paper_submit_enablement import (  # noqa: E402
    PAPEROPS_ALPACA_SUBMIT_ENABLEMENT_SCHEMA_VERSION,
    build_paperops_alpaca_paper_submit_enablement,
    paperops_alpaca_paper_submit_enablement_paths,
    validate_paperops_alpaca_paper_submit_enablement,
    write_paperops_alpaca_paper_submit_enablement,
)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_path = (
        paperops_alpaca_paper_submit_enablement_paths(settings)
    )
    if event_path.exists():
        event_path.unlink()

    artifact = build_paperops_alpaca_paper_submit_enablement(settings=settings)
    output_path, history_path, event_path, written = (
        write_paperops_alpaca_paper_submit_enablement(
            artifact,
            settings=settings,
            record_event=True,
            event_log_path=event_path,
        )
    )
    validation_errors = validate_paperops_alpaca_paper_submit_enablement(written)
    replay = EventLog(event_path, echo=False).replay()

    env_probe = deepcopy(written)
    env_probe["env_file_edited"] = True
    env_errors = validate_paperops_alpaca_paper_submit_enablement(env_probe)

    execute_probe = deepcopy(written)
    execute_probe["execute_post_requested"] = True
    execute_errors = validate_paperops_alpaca_paper_submit_enablement(execute_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_errors = validate_paperops_alpaca_paper_submit_enablement(
        live_capital_probe
    )

    broker_probe = deepcopy(written)
    broker_probe["broker_post_allowed"] = True
    broker_probe["broker_post_called_count"] = 1
    broker_probe["unsafe_write_counter_total"] = 1
    broker_errors = validate_paperops_alpaca_paper_submit_enablement(broker_probe)

    alpaca_probe = deepcopy(written)
    alpaca_probe["alpaca_post_allowed"] = True
    alpaca_probe["alpaca_post_called_count"] = 1
    alpaca_probe["unsafe_write_counter_total"] = 1
    alpaca_errors = validate_paperops_alpaca_paper_submit_enablement(alpaca_probe)

    live_endpoint_probe = deepcopy(written)
    live_endpoint_probe["live_endpoint_allowed"] = True
    live_endpoint_probe["live_endpoint_called_count"] = 1
    live_endpoint_probe["unsafe_write_counter_total"] = 1
    live_endpoint_errors = validate_paperops_alpaca_paper_submit_enablement(
        live_endpoint_probe
    )

    proof_probe = deepcopy(written)
    proof_probe["phase7_proof_credit_allowed"] = True
    proof_errors = validate_paperops_alpaca_paper_submit_enablement(proof_probe)

    forced_probe = deepcopy(written)
    forced_probe["forced_trades_allowed"] = True
    forced_errors = validate_paperops_alpaca_paper_submit_enablement(forced_probe)

    secret_probe = deepcopy(written)
    secret_probe["secret_value_exposed"] = True
    secret_errors = validate_paperops_alpaca_paper_submit_enablement(secret_probe)

    print(f"paperops_alpaca_submit_enablement_status={written['status']}")
    print(
        "paperops_alpaca_submit_enablement_schema_version="
        f"{PAPEROPS_ALPACA_SUBMIT_ENABLEMENT_SCHEMA_VERSION}"
    )
    print(f"paperops_alpaca_submit_enablement_artifact_path={output_path}")
    print(f"paperops_alpaca_submit_enablement_history_path={history_path}")
    print(f"paperops_alpaca_submit_enablement_event_log_path={event_path}")
    print(f"paperops_alpaca_submit_enablement_mode={written['mode']}")
    print(
        "paperops_alpaca_submit_enablement_runtime_enabled="
        f"{written['paper_submit_runtime_enablement_enabled']}"
    )
    print(
        "paperops_alpaca_submit_enablement_effective="
        f"{written['alpaca_paper_submit_effective']}"
    )
    print(
        "paperops_alpaca_submit_enablement_settings_flag="
        f"{written['settings_alpaca_paper_submit_enabled']}"
    )
    print(
        "paperops_alpaca_submit_enablement_runtime_override="
        f"{written['runtime_artifact_override_enabled']}"
    )
    print(
        "paperops_alpaca_submit_enablement_env_file_edited="
        f"{written['env_file_edited']}"
    )
    print(
        "paperops_alpaca_submit_enablement_path_available="
        f"{written['paper_post_path_available']}"
    )
    print(
        "paperops_alpaca_submit_enablement_explicit_submit_flag_required="
        f"{written['explicit_submit_flag_required']}"
    )
    print(
        "paperops_alpaca_submit_enablement_execute_post_requested="
        f"{written['execute_post_requested']}"
    )
    print(f"paperops_alpaca_submit_enablement_pt3_status={written['pt3_status']}")
    print(f"paperops_alpaca_submit_enablement_pt3_path_ready={written['pt3_path_ready']}")
    print(
        "paperops_alpaca_submit_enablement_pt3_qualified_setup_count="
        f"{written['pt3_qualified_setup_count']}"
    )
    print(f"paperops_alpaca_submit_enablement_pt4_status={written['pt4_status']}")
    print(
        "paperops_alpaca_submit_enablement_pt4_ready_for_paperops2="
        f"{written['pt4_ready_for_paperops2_submit']}"
    )
    print(
        "paperops_alpaca_submit_enablement_pt4_staged_order_count="
        f"{written['pt4_staged_order_count']}"
    )
    print(
        "paperops_alpaca_submit_enablement_endpoint_classification="
        f"{written['endpoint_classification']}"
    )
    print(
        "paperops_alpaca_submit_enablement_paper_endpoint_confirmed="
        f"{written['paper_endpoint_confirmed']}"
    )
    print(
        "paperops_alpaca_submit_enablement_key_configured="
        f"{written['alpaca_api_key_configured']}"
    )
    print(
        "paperops_alpaca_submit_enablement_secret_configured="
        f"{written['alpaca_api_secret_configured']}"
    )
    print(
        "paperops_alpaca_submit_enablement_broker_post_called_count="
        f"{written['broker_post_called_count']}"
    )
    print(
        "paperops_alpaca_submit_enablement_alpaca_post_called_count="
        f"{written['alpaca_post_called_count']}"
    )
    print(
        "paperops_alpaca_submit_enablement_live_endpoint_called_count="
        f"{written['live_endpoint_called_count']}"
    )
    print(
        "paperops_alpaca_submit_enablement_live_capital_enabled="
        f"{written['live_capital_enabled']}"
    )
    print(
        "paperops_alpaca_submit_enablement_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(
        "paperops_alpaca_submit_enablement_forced_trades_allowed="
        f"{written['forced_trades_allowed']}"
    )
    print(
        "paperops_alpaca_submit_enablement_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(f"paperops_alpaca_submit_enablement_event_log_events={replay['total_events']}")
    print(f"paperops_alpaca_submit_enablement_blocker_count={written['blocker_count']}")
    print(
        "paperops_alpaca_submit_enablement_blockers="
        f"{','.join(written['blockers'])}"
    )
    print(f"paperops_alpaca_submit_enablement_validation_errors={validation_errors}")

    if validation_errors:
        errors.append(f"PT-5 validation failed: {validation_errors}")
    if replay["total_events"] != 1:
        errors.append("PT-5 event log did not record exactly one event")
    if written["status"] != "enabled_pending_explicit_submit":
        errors.append("PT-5 did not enable Alpaca paper submit path")
    if written["paper_submit_runtime_enablement_enabled"] is not True:
        errors.append("PT-5 runtime enablement is not true")
    if written["alpaca_paper_submit_effective"] is not True:
        errors.append("PT-5 effective submit flag is not true")
    if written["settings_alpaca_paper_submit_enabled"] is not False:
        errors.append("PT-5 expected runtime override instead of env flag")
    if written["runtime_artifact_override_enabled"] is not True:
        errors.append("PT-5 runtime override is not active")
    if written["env_file_edited"] is not False:
        errors.append("PT-5 edited the environment file")
    if written["paper_post_path_available"] is not True:
        errors.append("PT-5 did not expose the paper post path")
    if written["explicit_submit_flag_required"] is not True:
        errors.append("PT-5 did not require explicit submit flag")
    if written["execute_post_requested"] is not False:
        errors.append("PT-5 requested a broker POST")
    if written["pt4_ready_for_paperops2_submit"] is not True:
        errors.append("PT-5 did not see a PT-4 staged order handoff")
    if written["pt4_staged_order_count"] < 1:
        errors.append("PT-5 did not see a staged paper order")
    if written["broker_post_called_count"] or written["alpaca_post_called_count"]:
        errors.append("PT-5 called a broker")
    if written["live_endpoint_called_count"]:
        errors.append("PT-5 called a live endpoint")
    if written["live_capital_enabled"] is not False:
        errors.append("PT-5 enabled live capital")
    if written["phase7_proof_credit_allowed"] is not False:
        errors.append("PT-5 granted Phase 7 proof credit")
    if written["forced_trades_allowed"] is not False:
        errors.append("PT-5 allowed forced trades")
    if "paperops_alpaca_submit_enablement_forbidden:env_file_edited" not in env_errors:
        errors.append("env-file probe was not rejected")
    if "paperops_alpaca_submit_enablement_forbidden:execute_post_requested" not in execute_errors:
        errors.append("execute-post probe was not rejected")
    if (
        "paperops_alpaca_submit_enablement_forbidden:live_capital_enabled"
        not in live_capital_errors
    ):
        errors.append("live-capital probe was not rejected")
    if "paperops_alpaca_submit_enablement_forbidden:broker_post_allowed" not in broker_errors:
        errors.append("broker authority probe was not rejected")
    if (
        "paperops_alpaca_submit_enablement_unsafe_counter_nonzero:broker_post_called_count"
        not in broker_errors
    ):
        errors.append("broker counter probe was not rejected")
    if "paperops_alpaca_submit_enablement_forbidden:alpaca_post_allowed" not in alpaca_errors:
        errors.append("Alpaca authority probe was not rejected")
    if (
        "paperops_alpaca_submit_enablement_unsafe_counter_nonzero:alpaca_post_called_count"
        not in alpaca_errors
    ):
        errors.append("Alpaca counter probe was not rejected")
    if "paperops_alpaca_submit_enablement_forbidden:live_endpoint_allowed" not in live_endpoint_errors:
        errors.append("live-endpoint authority probe was not rejected")
    if (
        "paperops_alpaca_submit_enablement_unsafe_counter_nonzero:live_endpoint_called_count"
        not in live_endpoint_errors
    ):
        errors.append("live-endpoint counter probe was not rejected")
    if (
        "paperops_alpaca_submit_enablement_forbidden:phase7_proof_credit_allowed"
        not in proof_errors
    ):
        errors.append("proof-credit probe was not rejected")
    if "paperops_alpaca_submit_enablement_forbidden:forced_trades_allowed" not in forced_errors:
        errors.append("forced-trade probe was not rejected")
    if "paperops_alpaca_submit_enablement_forbidden:secret_value_exposed" not in secret_errors:
        errors.append("secret-exposure probe was not rejected")

    if errors:
        print("paperops_alpaca_submit_enablement_check=failed")
        for error in errors:
            print(f"error={error}")
        return 1
    print("paperops_alpaca_submit_enablement_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
