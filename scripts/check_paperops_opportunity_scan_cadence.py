#!/usr/bin/env python3
"""Validate PaperOps opportunity scan cadence."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.paperops_opportunity_scan_cadence import (  # noqa: E402
    PAPEROPS_OPPORTUNITY_SCAN_CADENCE_SCHEMA_VERSION,
    build_paperops_opportunity_scan_cadence,
    paperops_opportunity_scan_cadence_paths,
    validate_paperops_opportunity_scan_cadence,
    write_paperops_opportunity_scan_cadence,
)


def main() -> int:
    settings = Settings.from_env()
    output_path, history_path, event_log_path = paperops_opportunity_scan_cadence_paths(
        settings
    )
    if event_log_path.exists():
        event_log_path.unlink()

    artifact = build_paperops_opportunity_scan_cadence(settings=settings)
    output_path, history_path, event_log_path, written = (
        write_paperops_opportunity_scan_cadence(
            artifact,
            settings=settings,
            record_event=True,
            event_log_path=event_log_path,
        )
    )
    validation_errors = validate_paperops_opportunity_scan_cadence(written)
    replay = EventLog(event_log_path, echo=False).replay()

    bad_interval_probe = deepcopy(written)
    bad_interval_probe["opportunity_scan_interval_minutes"] = 60
    bad_interval_errors = validate_paperops_opportunity_scan_cadence(
        bad_interval_probe
    )

    scan_submit_probe = deepcopy(written)
    scan_submit_probe["trade_submission_allowed_by_scan"] = True
    scan_submit_errors = validate_paperops_opportunity_scan_cadence(scan_submit_probe)

    force_probe = deepcopy(written)
    force_probe["forced_trades_allowed"] = True
    force_errors = validate_paperops_opportunity_scan_cadence(force_probe)

    unsafe_probe = deepcopy(written)
    unsafe_probe["broker_post_called_count"] = 1
    unsafe_probe["alpaca_post_called_count"] = 1
    unsafe_probe["live_endpoint_called_count"] = 1
    unsafe_probe["unsafe_write_counter_total"] = 3
    unsafe_errors = validate_paperops_opportunity_scan_cadence(unsafe_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_errors = validate_paperops_opportunity_scan_cadence(
        live_capital_probe
    )

    proof_probe = deepcopy(written)
    proof_probe["phase7_proof_credit_allowed"] = True
    proof_errors = validate_paperops_opportunity_scan_cadence(proof_probe)

    event_probe = deepcopy(written)
    event_probe["event_log_written"] = False
    event_probe["event_log_event_count"] = 0
    event_errors = validate_paperops_opportunity_scan_cadence(event_probe)

    print(f"paperops_opportunity_scan_cadence_status={written['status']}")
    print(
        "paperops_opportunity_scan_cadence_schema_version="
        f"{PAPEROPS_OPPORTUNITY_SCAN_CADENCE_SCHEMA_VERSION}"
    )
    print(f"paperops_opportunity_scan_cadence_artifact_path={output_path}")
    print(f"paperops_opportunity_scan_cadence_history_path={history_path}")
    print(f"paperops_opportunity_scan_cadence_event_log_path={event_log_path}")
    print(
        "paperops_opportunity_scan_cadence_event_log_events="
        f"{replay['total_events']}"
    )
    print(
        "paperops_opportunity_scan_cadence_interval_minutes="
        f"{written['opportunity_scan_interval_minutes']}"
    )
    print(
        "paperops_opportunity_scan_cadence_frequency_per_hour="
        f"{written['opportunity_scan_frequency_per_hour']}"
    )
    print(
        "paperops_opportunity_scan_cadence_model_review_interval_minutes="
        f"{written['model_review_interval_minutes']}"
    )
    print(
        "paperops_opportunity_scan_cadence_submit_runner_interval_minutes="
        f"{written['paper_submit_runner_interval_minutes']}"
    )
    print(
        "paperops_opportunity_scan_cadence_scan_ready="
        f"{written['twenty_minute_scan_ready']}"
    )
    print(
        "paperops_opportunity_scan_cadence_recurring_active="
        f"{written['twenty_minute_recurring_scheduler_active']}"
    )
    print(
        "paperops_opportunity_scan_cadence_scheduler_status="
        f"{written['recurring_scheduler_status']}"
    )
    print(
        "paperops_opportunity_scan_cadence_codex_minute_cron_supported="
        f"{written['codex_cron_minute_interval_supported']}"
    )
    print(
        "paperops_opportunity_scan_cadence_hourly_runner_active="
        f"{written['hourly_paperops_runner_active']}"
    )
    print(
        "paperops_opportunity_scan_cadence_hourly_runner_rrule="
        f"{written['hourly_paperops_runner_rrule']}"
    )
    print(
        "paperops_opportunity_scan_cadence_fresh_eligible_submit_count="
        f"{written['fresh_eligible_submit_count']}"
    )
    print(
        "paperops_opportunity_scan_cadence_duplicate_submit_count="
        f"{written['duplicate_submit_count']}"
    )
    print(
        "paperops_opportunity_scan_cadence_qualified_setup_count="
        f"{written['production_qualified_setup_count']}"
    )
    print(
        "paperops_opportunity_scan_cadence_trade_candidate_count="
        f"{written['observed_trade_candidate_count']}"
    )
    print(
        "paperops_opportunity_scan_cadence_submitted_paper_order_count="
        f"{written['submitted_paper_order_count']}"
    )
    print(
        "paperops_opportunity_scan_cadence_escalation_recommended="
        f"{written['escalation_to_hourly_runner_recommended']}"
    )
    print(
        "paperops_opportunity_scan_cadence_submission_allowed_by_scan="
        f"{written['trade_submission_allowed_by_scan']}"
    )
    print(
        "paperops_opportunity_scan_cadence_forced_trades_allowed="
        f"{written['forced_trades_allowed']}"
    )
    print(
        "paperops_opportunity_scan_cadence_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(
        "paperops_opportunity_scan_cadence_recommended_next_action="
        f"{written['recommended_next_action']}"
    )
    print(
        "paperops_opportunity_scan_cadence_validation_error_count="
        f"{len(validation_errors)}"
    )
    print(
        "paperops_opportunity_scan_cadence_bad_interval_guarded="
        f"{bool(bad_interval_errors)}"
    )
    print(
        "paperops_opportunity_scan_cadence_scan_submit_guarded="
        f"{bool(scan_submit_errors)}"
    )
    print(f"paperops_opportunity_scan_cadence_force_guarded={bool(force_errors)}")
    print(f"paperops_opportunity_scan_cadence_unsafe_guarded={bool(unsafe_errors)}")
    print(
        "paperops_opportunity_scan_cadence_live_capital_guarded="
        f"{bool(live_capital_errors)}"
    )
    print(f"paperops_opportunity_scan_cadence_proof_guarded={bool(proof_errors)}")
    print(f"paperops_opportunity_scan_cadence_event_guarded={bool(event_errors)}")
    print("paperops_opportunity_scan_cadence_check=ok")

    errors: list[str] = []
    if validation_errors:
        errors.extend(validation_errors)
    if replay["total_events"] != 1:
        errors.append("expected_one_event")
    if not bad_interval_errors:
        errors.append("bad_interval_not_guarded")
    if not scan_submit_errors:
        errors.append("scan_submit_not_guarded")
    if not force_errors:
        errors.append("force_not_guarded")
    if not unsafe_errors:
        errors.append("unsafe_not_guarded")
    if not live_capital_errors:
        errors.append("live_capital_not_guarded")
    if not proof_errors:
        errors.append("proof_not_guarded")
    if not event_errors:
        errors.append("event_log_not_guarded")
    if written["trade_submission_allowed_by_scan"] is not False:
        errors.append("scan_allowed_trade_submission")
    if written["opportunity_scan_interval_minutes"] != 20:
        errors.append("wrong_scan_interval")
    if written["forced_trades_allowed"] is not False:
        errors.append("forced_trade_policy_failed")

    if errors:
        for error in errors:
            print(f"error={error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
