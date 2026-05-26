#!/usr/bin/env python3
"""Validate Q5E-4 guarded Alpaca paper-submit path exposure."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.cockpit_status import build_cockpit_status, export_cockpit_status  # noqa: E402
from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase5_alpaca_paper_dry_run import (  # noqa: E402
    build_phase5_alpaca_paper_dry_run,
    phase5_alpaca_paper_dry_run_paths,
    validate_phase5_alpaca_paper_dry_run_bundle,
    write_phase5_alpaca_paper_dry_run,
)
from orchestrator.phase5_certification import (  # noqa: E402
    build_phase5_certification,
    validate_phase5_certification,
    write_phase5_certification,
)
from orchestrator.phase5_execution_adapter_status import (  # noqa: E402
    build_phase5_execution_adapter_status,
    phase5_execution_adapter_status_paths,
    validate_phase5_execution_adapter_status_bundle,
    write_phase5_execution_adapter_status,
)
from orchestrator.phase5_exit_evidence_lift import (  # noqa: E402
    TARGET_STRATEGY_FAMILY_KEY,
    validate_phase5_exit_risk_evidence_lift,
    write_phase5_exit_risk_evidence_lift,
)
from orchestrator.phase5_kill_switch import (  # noqa: E402
    build_phase5_kill_switch_ledger,
    phase5_kill_switch_paths,
    validate_phase5_kill_switch_ledger,
    write_phase5_kill_switch_ledger,
)
from orchestrator.phase5_paper_order_staging import (  # noqa: E402
    build_phase5_paper_order_staging_gate,
    phase5_paper_order_staging_paths,
    validate_phase5_paper_order_staging_bundle,
    write_phase5_paper_order_staging_gate,
)
from orchestrator.phase5_paper_submit_enablement import (  # noqa: E402
    PAPER_SUBMIT_ENABLEMENT_ALLOWED_AUTHORITY_FIELDS,
    PAPER_SUBMIT_PATH_KEY,
    PHASE5_PAPER_SUBMIT_ENABLEMENT_SCHEMA_VERSION,
    build_phase5_paper_submit_enablement_gate,
    paper_submit_enablement_paths,
    validate_phase5_paper_submit_enablement_bundle,
    write_phase5_paper_submit_enablement_gate,
)
from orchestrator.phase5_paper_trade_drill import (  # noqa: E402
    build_phase5_paper_trade_drill,
    validate_phase5_paper_trade_drill_bundle,
    write_phase5_paper_trade_drill,
)
from orchestrator.phase5_system_map import (  # noqa: E402
    validate_phase5_system_map_bundle,
    write_phase5_system_map,
)


def _target_record(bundle: dict) -> dict:
    for record in bundle.get("records", []):
        if (
            isinstance(record, dict)
            and record.get("strategy_family_key") == TARGET_STRATEGY_FAMILY_KEY
        ):
            return record
    return {}


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()

    _, _, _, q5e1_artifact = write_phase5_exit_risk_evidence_lift(
        settings=settings,
        record_event=True,
    )
    q5e1_errors = validate_phase5_exit_risk_evidence_lift(q5e1_artifact)

    _, _, kill_event_log_path = phase5_kill_switch_paths(settings)
    if kill_event_log_path.exists():
        kill_event_log_path.unlink()
    kill_bundle = build_phase5_kill_switch_ledger(settings=settings)
    _, _, _, written_kill_bundle = write_phase5_kill_switch_ledger(
        kill_bundle,
        settings=settings,
        record_event=True,
        event_log_path=kill_event_log_path,
    )
    kill_errors = validate_phase5_kill_switch_ledger(written_kill_bundle)

    _, _, adapter_event_log_path = phase5_execution_adapter_status_paths(settings)
    if adapter_event_log_path.exists():
        adapter_event_log_path.unlink()
    adapter_bundle = build_phase5_execution_adapter_status(settings=settings)
    _, _, _, written_adapter_bundle = write_phase5_execution_adapter_status(
        adapter_bundle,
        settings=settings,
        record_event=True,
        event_log_path=adapter_event_log_path,
    )
    adapter_errors = validate_phase5_execution_adapter_status_bundle(written_adapter_bundle)

    _, _, staging_event_log_path = phase5_paper_order_staging_paths(settings)
    if staging_event_log_path.exists():
        staging_event_log_path.unlink()
    staging_bundle = build_phase5_paper_order_staging_gate(settings=settings)
    _, _, _, written_staging_bundle = write_phase5_paper_order_staging_gate(
        staging_bundle,
        settings=settings,
        record_event=True,
        event_log_path=staging_event_log_path,
    )
    staging_errors = validate_phase5_paper_order_staging_bundle(written_staging_bundle)

    _, _, dry_run_event_log_path = phase5_alpaca_paper_dry_run_paths(settings)
    if dry_run_event_log_path.exists():
        dry_run_event_log_path.unlink()
    dry_run_bundle = build_phase5_alpaca_paper_dry_run(settings=settings)
    _, _, _, written_dry_run_bundle = write_phase5_alpaca_paper_dry_run(
        dry_run_bundle,
        settings=settings,
        record_event=True,
        event_log_path=dry_run_event_log_path,
    )
    dry_run_errors = validate_phase5_alpaca_paper_dry_run_bundle(written_dry_run_bundle)

    output_path, history_path, submit_event_log_path = paper_submit_enablement_paths(settings)
    if submit_event_log_path.exists():
        submit_event_log_path.unlink()
    submit_bundle = build_phase5_paper_submit_enablement_gate(settings=settings)
    output_path, history_path, submit_event_log_path, written_submit_bundle = (
        write_phase5_paper_submit_enablement_gate(
            submit_bundle,
            settings=settings,
            record_event=True,
            event_log_path=submit_event_log_path,
        )
    )
    submit_errors = validate_phase5_paper_submit_enablement_bundle(written_submit_bundle)
    submit_replay = EventLog(submit_event_log_path, echo=False).replay()
    target = _target_record(written_submit_bundle)
    submit_path = target.get("submit_path", {}) if target else {}
    event_log_prewrite = target.get("event_log_prewrite", {}) if target else {}
    pre_trade_snapshot = target.get("pre_trade_snapshot", {}) if target else {}

    drill_path, _, _, written_drill = write_phase5_paper_trade_drill(
        build_phase5_paper_trade_drill(settings=settings),
        settings=settings,
        record_event=True,
    )
    drill_errors = validate_phase5_paper_trade_drill_bundle(written_drill)

    certification_path, _, _, written_certification = write_phase5_certification(
        build_phase5_certification(settings=settings),
        settings=settings,
        record_event=True,
    )
    certification_errors = validate_phase5_certification(written_certification)

    cockpit_before_system_map = build_cockpit_status(settings)
    system_map_path, _, _, written_system_map = write_phase5_system_map(
        cockpit_before_system_map["phase5_system_map"],
        settings=settings,
        record_event=True,
    )
    system_map_errors = validate_phase5_system_map_bundle(written_system_map)

    certification_path, _, _, written_certification = write_phase5_certification(
        build_phase5_certification(settings=settings),
        settings=settings,
        record_event=True,
    )
    certification_errors = validate_phase5_certification(written_certification)

    cockpit_export = export_cockpit_status(
        settings=settings,
        landing_repo_path=ROOT / "landing-page-repo",
    )

    for label, validation_errors in (
        ("q5e_1", q5e1_errors),
        ("q5_4", kill_errors),
        ("q5_5", adapter_errors),
        ("q5_6", staging_errors),
        ("q5_7", dry_run_errors),
        ("q5_8", submit_errors),
        ("q5_13", system_map_errors),
        ("q5_14", drill_errors),
        ("q5_15", certification_errors),
    ):
        if validation_errors:
            errors.append(f"{label}_validation_errors:" + ",".join(validation_errors))
    if q5e1_artifact.get("paper_size_eligible_count", 0) < 1:
        errors.append("q5e_4_missing_q5e_1_eligible_setup")
    if written_staging_bundle.get("staged_order_count", 0) < 1:
        errors.append("q5e_4_missing_q5e_2_staged_order")
    if written_dry_run_bundle.get("dry_run_receipt_count", 0) < 1:
        errors.append("q5e_4_missing_q5e_3_dry_run_receipt")
    if written_submit_bundle.get("submit_path_available_count", 0) < 1:
        errors.append("q5e_4_submit_path_not_available")
    if not target:
        errors.append("q5e_4_target_submit_record_missing")
    if target:
        if target.get("submit_path_available") is not True:
            errors.append("q5e_4_target_submit_path_unavailable")
        if target.get("paper_submit_gate_state") != "ready_for_guarded_paper_submit":
            errors.append("q5e_4_target_gate_state_not_ready")
        if target.get("paper_order_submitted") is True:
            if target.get("receipt_state") != "paper_submit_receipt_recorded":
                errors.append("q5e_4_target_submitted_receipt_state_invalid")
        elif target.get("receipt_state") != "paper_submit_gate_ready":
            errors.append("q5e_4_target_receipt_state_not_ready")
        if target.get("paper_submit_approval_present") is not True:
            errors.append("q5e_4_target_approval_missing")
        if target.get("idempotency_key_allocated_for_submit") is not True:
            errors.append("q5e_4_target_submit_idempotency_not_allocated")
        if event_log_prewrite.get("prewrite_complete") is not True:
            errors.append("q5e_4_target_event_prewrite_incomplete")
        if pre_trade_snapshot.get("captured") is not True:
            errors.append("q5e_4_target_pre_trade_snapshot_missing")
        if submit_path.get("path_key") != PAPER_SUBMIT_PATH_KEY:
            errors.append("q5e_4_target_submit_path_key_invalid")
        if submit_path.get("available") is not True:
            errors.append("q5e_4_target_submit_path_metadata_unavailable")
        if submit_path.get("adapter") != "alpaca":
            errors.append("q5e_4_target_submit_path_adapter_invalid")
        if submit_path.get("selected_venue") != "alpaca_paper":
            errors.append("q5e_4_target_submit_path_venue_invalid")
        if submit_path.get("http_method") != "POST":
            errors.append("q5e_4_target_submit_path_method_invalid")
        if submit_path.get("post_call_performed") is not False:
            errors.append("q5e_4_target_submit_path_post_performed")
        if submit_path.get("authorization_header_included") is not False:
            errors.append("q5e_4_target_submit_path_auth_header_included")
        if submit_path.get("base_url_exposed") is not False:
            errors.append("q5e_4_target_submit_path_base_url_exposed")
        for field in PAPER_SUBMIT_ENABLEMENT_ALLOWED_AUTHORITY_FIELDS:
            if target.get(field) is not True:
                errors.append(f"q5e_4_target_allowed_authority_missing:{field}")
        for field in (
            "broker_post_called",
            "alpaca_post_called",
            "position_created",
            "live_endpoint_allowed",
            "live_capital_enabled",
            "prediction_market_write_allowed",
            "crypto_perps_write_allowed",
        ):
            if target.get(field) is not False:
                errors.append(f"q5e_4_target_forbidden_field_enabled:{field}")
        if target.get("paper_order_submitted") is True:
            if target.get("broker_submit_receipt_created") is not True:
                errors.append("q5e_4_target_submitted_without_receipt")
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "live_capital_enabled_count",
        "live_endpoint_allowed_count",
        "prediction_market_write_allowed_count",
    ):
        if int(written_submit_bundle.get(key, 0) or 0) != 0:
            errors.append(f"q5e_4_boundary_count_not_zero:{key}")
    if written_submit_bundle.get("broker_submit_receipt_created_count") != written_submit_bundle.get(
        "paper_order_submitted_count"
    ):
        errors.append("q5e_4_receipt_count_mismatch")
    for key in (
        "execution_adapter_write_authority_count",
        "paper_execution_allowed_count",
        "paper_order_allowed_count",
        "paper_order_submission_allowed_count",
        "broker_write_allowed_count",
    ):
        if int(written_submit_bundle.get(key, 0) or 0) != int(
            written_submit_bundle.get("submit_path_available_count", 0) or 0
        ):
            errors.append(f"q5e_4_allowed_authority_count_mismatch:{key}")
    if submit_replay["total_events"] != written_submit_bundle.get("submit_enablement_record_count"):
        errors.append("q5e_4_submit_event_log_count_mismatch")
    if written_drill.get("paper_submit_path_available_count", 0) < 1:
        errors.append("q5e_4_drill_submit_path_not_visible")
    if written_drill.get("phase5_paper_trade_drill_exit_gate_passed") is not False:
        errors.append("q5e_4_drill_exit_gate_opened")
    if written_certification.get("phase5_certified") is not False:
        errors.append("q5e_4_certification_opened_without_lifecycle")
    if written_certification.get("phase6_handoff_allowed") is not False:
        errors.append("q5e_4_phase6_handoff_opened_without_lifecycle")

    print("phase5_exit_paper_submit_path_status=" + written_submit_bundle["status"])
    print(
        "phase5_exit_paper_submit_path_schema_version="
        f"{PHASE5_PAPER_SUBMIT_ENABLEMENT_SCHEMA_VERSION}"
    )
    print(f"phase5_exit_paper_submit_path_artifact_path={output_path}")
    print(f"phase5_exit_paper_submit_path_history_path={history_path}")
    print(f"phase5_exit_paper_submit_path_event_log_path={submit_event_log_path}")
    print(f"phase5_exit_paper_submit_path_system_map_path={system_map_path}")
    print(f"phase5_exit_paper_submit_path_drill_path={drill_path}")
    print(f"phase5_exit_paper_submit_path_certification_path={certification_path}")
    print(f"phase5_exit_paper_submit_path_cockpit_runtime_path={cockpit_export['runtime_path']}")
    print(f"phase5_exit_paper_submit_path_target_strategy_family_key={TARGET_STRATEGY_FAMILY_KEY}")
    print(
        "phase5_exit_paper_submit_path_source_request_preview_count="
        f"{written_submit_bundle['source_request_preview_count']}"
    )
    print(
        "phase5_exit_paper_submit_path_source_dry_run_receipt_count="
        f"{written_submit_bundle['source_dry_run_receipt_count']}"
    )
    print(
        "phase5_exit_paper_submit_path_available_count="
        f"{written_submit_bundle['submit_path_available_count']}"
    )
    print(
        "phase5_exit_paper_submit_path_target_record_present="
        f"{bool(target)}"
    )
    print(
        "phase5_exit_paper_submit_path_target_gate_state="
        f"{target.get('paper_submit_gate_state', 'missing')}"
    )
    print(
        "phase5_exit_paper_submit_path_target_receipt_state="
        f"{target.get('receipt_state', 'missing')}"
    )
    print(
        "phase5_exit_paper_submit_path_target_idempotency_allocated="
        f"{target.get('idempotency_key_allocated_for_submit', False)}"
    )
    print(
        "phase5_exit_paper_submit_path_target_event_prewrite_complete="
        f"{event_log_prewrite.get('prewrite_complete', False)}"
    )
    print(
        "phase5_exit_paper_submit_path_target_pre_trade_snapshot_captured="
        f"{pre_trade_snapshot.get('captured', False)}"
    )
    print(
        "phase5_exit_paper_submit_path_broker_write_allowed_count="
        f"{written_submit_bundle['broker_write_allowed_count']}"
    )
    print(
        "phase5_exit_paper_submit_path_broker_post_called_count="
        f"{written_submit_bundle['broker_post_called_count']}"
    )
    print(
        "phase5_exit_paper_submit_path_alpaca_post_called_count="
        f"{written_submit_bundle['alpaca_post_called_count']}"
    )
    print(
        "phase5_exit_paper_submit_path_paper_order_submitted_count="
        f"{written_submit_bundle['paper_order_submitted_count']}"
    )
    print(
        "phase5_exit_paper_submit_path_live_capital_enabled_count="
        f"{written_submit_bundle['live_capital_enabled_count']}"
    )
    print(
        "phase5_exit_paper_submit_path_drill_submit_path_available_count="
        f"{written_drill['paper_submit_path_available_count']}"
    )
    print(
        "phase5_exit_paper_submit_path_drill_exit_gate_passed="
        f"{written_drill['phase5_paper_trade_drill_exit_gate_passed']}"
    )
    print(
        "phase5_exit_paper_submit_path_phase5_certified="
        f"{written_certification['phase5_certified']}"
    )
    print(
        "phase5_exit_paper_submit_path_phase6_handoff_allowed="
        f"{written_certification['phase6_handoff_allowed']}"
    )
    print("phase5_exit_paper_submit_path_boundary=" + written_submit_bundle["boundary"])

    if errors:
        for error in errors:
            print(f"phase5_exit_paper_submit_path_error={error}")
        print("phase5_exit_paper_submit_path_check=failed")
        return 1

    print("phase5_exit_paper_submit_path_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
