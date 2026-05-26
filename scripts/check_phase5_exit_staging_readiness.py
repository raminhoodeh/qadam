#!/usr/bin/env python3
"""Validate Q5E-9 guarded execution-adapter staging readiness."""

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
    build_phase5_guarded_paper_submit_receipt,
    build_phase5_paper_submit_enablement_gate,
    guarded_paper_submit_receipt_paths,
    paper_submit_enablement_paths,
    validate_phase5_guarded_paper_submit_receipt,
    validate_phase5_paper_submit_enablement_bundle,
    write_phase5_guarded_paper_submit_receipt,
    write_phase5_paper_submit_enablement_gate,
)
from orchestrator.phase5_paper_trade_drill import (  # noqa: E402
    build_phase5_paper_trade_drill,
    validate_phase5_paper_trade_drill_bundle,
    write_phase5_paper_trade_drill,
)
from orchestrator.phase5_position_monitor import (  # noqa: E402
    build_phase5_guarded_closed_trade,
    build_phase5_guarded_open_position,
    build_phase5_guarded_postmortem_due,
    build_phase5_position_monitor,
    guarded_closed_trade_paths,
    guarded_open_position_paths,
    guarded_postmortem_due_paths,
    position_monitor_paths,
    validate_phase5_guarded_closed_trade,
    validate_phase5_guarded_open_position,
    validate_phase5_guarded_postmortem_due,
    validate_phase5_position_monitor_bundle,
    write_phase5_guarded_closed_trade,
    write_phase5_guarded_open_position,
    write_phase5_guarded_postmortem_due,
    write_phase5_position_monitor,
)
from orchestrator.phase5_system_map import (  # noqa: E402
    validate_phase5_system_map_bundle,
    write_phase5_system_map,
)
from scripts.check_phase5_exit_closed_trade import _mirror_closed_trade  # noqa: E402
from scripts.check_phase5_exit_open_position import (  # noqa: E402
    _mirror_open_position,
    _mirror_submitted_order,
)
from scripts.check_phase5_exit_postmortem_due import (  # noqa: E402
    _mirror_postmortem_due,
    _target_record,
)


def _unlink(path: Path) -> None:
    if path.exists():
        path.unlink()


def _venue_record(bundle: dict, venue_key: str) -> dict:
    for record in bundle.get("statuses", []):
        if isinstance(record, dict) and record.get("venue_key") == venue_key:
            return record
    return {}


def _append_validation_errors(
    errors: list[str],
    label: str,
    validation_errors: list[str],
) -> None:
    if validation_errors:
        errors.append(f"{label}_validation_errors:" + ",".join(validation_errors))


def _assert_zero_counts(errors: list[str], label: str, bundle: dict, keys: tuple[str, ...]) -> None:
    for key in keys:
        if int(bundle.get(key, 0) or 0) != 0:
            errors.append(f"{label}_unsafe_count_nonzero:{key}")


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()

    _, _, _, q5e1_artifact = write_phase5_exit_risk_evidence_lift(
        settings=settings,
        record_event=True,
    )
    q5e1_errors = validate_phase5_exit_risk_evidence_lift(q5e1_artifact)

    _, _, kill_event_log_path = phase5_kill_switch_paths(settings)
    _unlink(kill_event_log_path)
    _, _, _, written_kill_bundle = write_phase5_kill_switch_ledger(
        build_phase5_kill_switch_ledger(settings=settings),
        settings=settings,
        record_event=True,
        event_log_path=kill_event_log_path,
    )
    kill_errors = validate_phase5_kill_switch_ledger(written_kill_bundle)

    _, _, staging_event_log_path = phase5_paper_order_staging_paths(settings)
    _unlink(staging_event_log_path)
    _, _, _, written_staging_bundle = write_phase5_paper_order_staging_gate(
        build_phase5_paper_order_staging_gate(settings=settings),
        settings=settings,
        record_event=True,
        event_log_path=staging_event_log_path,
    )
    staging_errors = validate_phase5_paper_order_staging_bundle(written_staging_bundle)

    _, _, dry_run_event_log_path = phase5_alpaca_paper_dry_run_paths(settings)
    _unlink(dry_run_event_log_path)
    _, _, _, written_dry_run_bundle = write_phase5_alpaca_paper_dry_run(
        build_phase5_alpaca_paper_dry_run(settings=settings),
        settings=settings,
        record_event=True,
        event_log_path=dry_run_event_log_path,
    )
    dry_run_errors = validate_phase5_alpaca_paper_dry_run_bundle(written_dry_run_bundle)

    submit_path, _, submit_event_log_path = paper_submit_enablement_paths(settings)
    _unlink(submit_event_log_path)
    _, _, _, written_submit_path_bundle = write_phase5_paper_submit_enablement_gate(
        build_phase5_paper_submit_enablement_gate(settings=settings),
        settings=settings,
        record_event=True,
        event_log_path=submit_event_log_path,
    )
    submit_path_errors = validate_phase5_paper_submit_enablement_bundle(
        written_submit_path_bundle
    )

    receipt_path, _, receipt_event_log_path = guarded_paper_submit_receipt_paths(settings)
    _unlink(receipt_event_log_path)
    _, _, _, written_receipt = write_phase5_guarded_paper_submit_receipt(
        build_phase5_guarded_paper_submit_receipt(settings=settings),
        settings=settings,
        record_event=True,
        event_log_path=receipt_event_log_path,
    )
    receipt_errors = validate_phase5_guarded_paper_submit_receipt(written_receipt)
    _mirror_submitted_order(written_receipt, settings)

    _unlink(submit_event_log_path)
    submit_path, _, submit_event_log_path, written_submit_bundle = (
        write_phase5_paper_submit_enablement_gate(
            build_phase5_paper_submit_enablement_gate(settings=settings),
            settings=settings,
            record_event=True,
            event_log_path=submit_event_log_path,
        )
    )
    submit_errors = validate_phase5_paper_submit_enablement_bundle(written_submit_bundle)
    submit_replay = EventLog(submit_event_log_path, echo=False).replay()

    open_path, _, open_event_log_path = guarded_open_position_paths(settings)
    _unlink(open_event_log_path)
    open_path, _, _, written_open_position = write_phase5_guarded_open_position(
        build_phase5_guarded_open_position(settings=settings),
        settings=settings,
        record_event=True,
        event_log_path=open_event_log_path,
    )
    open_position_errors = validate_phase5_guarded_open_position(written_open_position)
    _, mirrored_position = _mirror_open_position(written_open_position, settings)

    closed_path, _, closed_event_log_path = guarded_closed_trade_paths(settings)
    _unlink(closed_event_log_path)
    closed_path, _, _, written_closed_trade = write_phase5_guarded_closed_trade(
        build_phase5_guarded_closed_trade(settings=settings),
        settings=settings,
        record_event=True,
        event_log_path=closed_event_log_path,
    )
    closed_trade_errors = validate_phase5_guarded_closed_trade(written_closed_trade)
    mirrored_closed_trade = None
    if written_closed_trade.get("status") == "closed_trade":
        mirrored_closed_trade = _mirror_closed_trade(written_closed_trade, settings)
    closed_lifecycle_ready = written_closed_trade.get("status") == "closed_trade"

    postmortem_path, _, postmortem_event_log_path = guarded_postmortem_due_paths(settings)
    _unlink(postmortem_event_log_path)
    postmortem_path, _, _, written_postmortem = write_phase5_guarded_postmortem_due(
        build_phase5_guarded_postmortem_due(settings=settings),
        settings=settings,
        record_event=True,
        event_log_path=postmortem_event_log_path,
    )
    postmortem_errors = validate_phase5_guarded_postmortem_due(written_postmortem)
    mirrored_due_trade = None
    if written_postmortem.get("status") == "postmortem_due":
        mirrored_due_trade = _mirror_postmortem_due(written_postmortem, settings)

    position_path, _, position_event_log_path = position_monitor_paths(settings)
    _unlink(position_event_log_path)
    position_path, _, _, written_position = write_phase5_position_monitor(
        build_phase5_position_monitor(settings=settings),
        settings=settings,
        record_event=True,
        event_log_path=position_event_log_path,
    )
    position_errors = validate_phase5_position_monitor_bundle(written_position)
    position_record = _target_record(written_position, "position_state")
    closed_record = _target_record(written_position, "closed_trade_summary")

    adapter_path, _, adapter_event_log_path = phase5_execution_adapter_status_paths(settings)
    _unlink(adapter_event_log_path)
    adapter_path, _, adapter_event_log_path, written_adapter_bundle = (
        write_phase5_execution_adapter_status(
            build_phase5_execution_adapter_status(settings=settings),
            settings=settings,
            record_event=True,
            event_log_path=adapter_event_log_path,
        )
    )
    adapter_errors = validate_phase5_execution_adapter_status_bundle(written_adapter_bundle)
    adapter_replay = EventLog(adapter_event_log_path, echo=False).replay()
    alpaca_record = _venue_record(written_adapter_bundle, "alpaca_paper")

    cockpit_before_system_map = build_cockpit_status(settings)
    system_map_path, _, _, written_system_map = write_phase5_system_map(
        cockpit_before_system_map["phase5_system_map"],
        settings=settings,
        record_event=True,
    )
    system_map_errors = validate_phase5_system_map_bundle(written_system_map)

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

    cockpit_with_certification = build_cockpit_status(settings)
    system_map_path, _, _, written_system_map = write_phase5_system_map(
        cockpit_with_certification["phase5_system_map"],
        settings=settings,
        record_event=True,
    )
    system_map_errors = validate_phase5_system_map_bundle(written_system_map)

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
        ("q5_8_path", submit_path_errors),
        ("q5e_5_receipt", receipt_errors),
        ("q5_8", submit_errors),
        ("q5e_7_closed_trade", closed_trade_errors),
        ("q5e_8_postmortem_due", postmortem_errors),
        ("q5_11", position_errors),
        ("q5_13", system_map_errors),
        ("q5_14", drill_errors),
        ("q5_15", certification_errors),
    ):
        _append_validation_errors(errors, label, validation_errors)
    if open_position_errors and not closed_lifecycle_ready:
        _append_validation_errors(errors, "q5e_6_open_position", open_position_errors)

    if q5e1_artifact.get("paper_size_eligible_count", 0) < 1:
        errors.append("q5e_9_missing_q5e_1_eligible_setup")
    if written_staging_bundle.get("staged_order_count", 0) < 1:
        errors.append("q5e_9_missing_staged_order")
    if written_dry_run_bundle.get("dry_run_receipt_count", 0) < 1:
        errors.append("q5e_9_missing_dry_run_receipt")
    if written_submit_path_bundle.get("submit_path_available_count", 0) < 1:
        errors.append("q5e_9_missing_guarded_submit_path")
    if written_submit_bundle.get("paper_order_submitted_count") != 1:
        errors.append("q5e_9_submit_count_not_one")
    if written_submit_bundle.get("broker_submit_receipt_created_count") != 1:
        errors.append("q5e_9_receipt_count_not_one")
    if submit_replay["total_events"] != written_submit_bundle.get("submit_enablement_record_count"):
        errors.append("q5e_9_submit_event_log_count_mismatch")
    if written_closed_trade.get("status") != "closed_trade":
        errors.append("q5e_9_closed_trade_artifact_not_closed")
    if written_postmortem.get("status") != "postmortem_due":
        errors.append("q5e_9_postmortem_artifact_not_due")
    if written_postmortem.get("postmortem_due_marker_created") is not True:
        errors.append("q5e_9_postmortem_marker_not_created")
    if mirrored_position.status != "open_position" and not closed_lifecycle_ready:
        errors.append("q5e_9_position_not_open_before_close")
    if mirrored_closed_trade is None:
        errors.append("q5e_9_closed_trade_not_mirrored")
    if mirrored_due_trade is None:
        errors.append("q5e_9_postmortem_due_not_mirrored")
    elif mirrored_due_trade.postmortem_status != "postmortem_due":
        errors.append("q5e_9_mirrored_trade_not_due")
    if written_position.get("submitted_order_count") != 1:
        errors.append("q5e_9_position_submitted_count_not_one")
    if written_position.get("mirrored_order_count") != 1:
        errors.append("q5e_9_position_mirrored_count_not_one")
    if written_position.get("closed_trade_count") != 1:
        errors.append("q5e_9_position_closed_count_not_one")
    if written_position.get("postmortem_due_count") != 1:
        errors.append("q5e_9_position_postmortem_due_count_not_one")
    if written_position.get("failed_reconciliation_count") != 0:
        errors.append("q5e_9_position_reconciliation_failed")
    if position_record.get("status") != "closed_trade":
        errors.append("q5e_9_position_record_not_closed")
    if closed_record.get("status") != "closed_trade":
        errors.append("q5e_9_closed_record_not_closed")
    if closed_record.get("postmortem_status") != "postmortem_due":
        errors.append("q5e_9_closed_record_postmortem_status_invalid")
    if written_adapter_bundle.get("downstream_staging_allowed_count") != 1:
        errors.append("q5e_9_adapter_downstream_staging_count_not_one")
    if adapter_replay["total_events"] != written_adapter_bundle.get("adapter_status_count"):
        errors.append("q5e_9_adapter_event_log_count_mismatch")
    if alpaca_record.get("status") != "eligible":
        errors.append("q5e_9_alpaca_adapter_not_eligible")
    if alpaca_record.get("downstream_staging_allowed") is not True:
        errors.append("q5e_9_alpaca_downstream_staging_not_allowed")
    if alpaca_record.get("staging_readiness_scope") != "guarded_q5e_lifecycle_readiness":
        errors.append("q5e_9_alpaca_staging_scope_invalid")
    if alpaca_record.get("guarded_postmortem_due_ready") is not True:
        errors.append("q5e_9_alpaca_postmortem_due_not_ready")
    if alpaca_record.get("reconciliation_ready_for_submit") is not False:
        errors.append("q5e_9_alpaca_reconciliation_ready_for_submit")
    if "execution_adapter_not_staging_ready" in written_drill.get("blockers", []):
        errors.append("q5e_9_drill_still_missing_execution_adapter")
    if written_drill.get("blocker_count") != 0:
        errors.append("q5e_9_drill_blockers_present")
    if written_drill.get("paper_trade_drill_complete") is not True:
        errors.append("q5e_9_drill_not_complete")
    if written_drill.get("phase5_paper_trade_drill_exit_gate_passed") is not True:
        errors.append("q5e_9_drill_exit_gate_not_passed")
    if written_drill.get("submitted_paper_order_count") != 1:
        errors.append("q5e_9_drill_submitted_order_missing")
    if written_drill.get("position_open_lifecycle_satisfied") is not True:
        errors.append("q5e_9_drill_open_lifecycle_not_satisfied")
    if written_drill.get("closed_trade_count") != 1:
        errors.append("q5e_9_drill_closed_trade_missing")
    if written_drill.get("postmortem_due_count") != 1:
        errors.append("q5e_9_drill_postmortem_due_missing")
    if written_certification.get("status") != "eligible":
        errors.append("q5e_9_certification_not_eligible")
    if written_certification.get("phase5_certified") is not True:
        errors.append("q5e_9_phase5_not_certified")
    if written_certification.get("phase5_exit_gate") is not True:
        errors.append("q5e_9_phase5_exit_gate_not_open")
    if written_certification.get("phase6_handoff_allowed") is not True:
        errors.append("q5e_9_phase6_handoff_not_allowed")
    if written_certification.get("phase7_planning_allowed") is not True:
        errors.append("q5e_9_phase7_planning_not_allowed")
    if written_certification.get("phase7_proof_credit_allowed") is not False:
        errors.append("q5e_9_phase7_proof_credit_allowed")
    if written_certification.get("certification_blocker_count") != 0:
        errors.append("q5e_9_certification_blockers_present")
    if written_certification.get("input_gate_blocked_count") != 0:
        errors.append("q5e_9_certification_input_gates_blocked")

    _assert_zero_counts(
        errors,
        "q5e_9_adapter",
        written_adapter_bundle,
        (
            "execution_adapter_write_authority_count",
            "paper_order_staging_allowed_count",
            "paper_order_submission_allowed_count",
            "paper_order_allowed_count",
            "broker_write_allowed_count",
            "broker_post_called_count",
            "broker_submit_receipt_created_count",
            "prediction_market_write_allowed_count",
            "crypto_perps_write_allowed_count",
            "live_endpoint_allowed_count",
            "live_capital_enabled_count",
        ),
    )
    for label, bundle in (
        ("submit", written_submit_bundle),
        ("open", written_open_position),
        ("closed", written_closed_trade),
        ("postmortem", written_postmortem),
        ("position", written_position),
        ("drill", written_drill),
        ("certification", written_certification),
    ):
        _assert_zero_counts(
            errors,
            f"q5e_9_{label}",
            bundle,
            (
                "broker_post_called_count",
                "alpaca_post_called_count",
                "live_endpoint_allowed_count",
                "live_capital_enabled_count",
                "prediction_market_write_allowed_count",
                "phase7_proof_credit_allowed_count",
            ),
        )

    print("phase5_exit_staging_readiness_status=" + str(alpaca_record.get("status")))
    print(f"phase5_exit_staging_readiness_target_strategy_family_key={TARGET_STRATEGY_FAMILY_KEY}")
    print(f"phase5_exit_staging_readiness_adapter_path={adapter_path}")
    print(f"phase5_exit_staging_readiness_submit_gate_path={submit_path}")
    print(f"phase5_exit_staging_readiness_receipt_path={receipt_path}")
    print(f"phase5_exit_staging_readiness_open_position_path={open_path}")
    print(f"phase5_exit_staging_readiness_closed_trade_path={closed_path}")
    print(f"phase5_exit_staging_readiness_postmortem_path={postmortem_path}")
    print(f"phase5_exit_staging_readiness_position_monitor_path={position_path}")
    print(f"phase5_exit_staging_readiness_system_map_path={system_map_path}")
    print(f"phase5_exit_staging_readiness_drill_path={drill_path}")
    print(f"phase5_exit_staging_readiness_certification_path={certification_path}")
    print(f"phase5_exit_staging_readiness_cockpit_runtime_path={cockpit_export['runtime_path']}")
    print(
        "phase5_exit_staging_readiness_downstream_staging_allowed_count="
        f"{written_adapter_bundle.get('downstream_staging_allowed_count')}"
    )
    print(
        "phase5_exit_staging_readiness_alpaca_staging_readiness_scope="
        f"{alpaca_record.get('staging_readiness_scope')}"
    )
    print(
        "phase5_exit_staging_readiness_guarded_postmortem_due_ready="
        f"{alpaca_record.get('guarded_postmortem_due_ready')}"
    )
    print(
        "phase5_exit_staging_readiness_broker_post_called_count="
        f"{written_submit_bundle.get('broker_post_called_count')}"
    )
    print(
        "phase5_exit_staging_readiness_alpaca_post_called_count="
        f"{written_submit_bundle.get('alpaca_post_called_count')}"
    )
    print(
        "phase5_exit_staging_readiness_position_closed_trade_count="
        f"{written_position.get('closed_trade_count')}"
    )
    print(
        "phase5_exit_staging_readiness_position_postmortem_due_count="
        f"{written_position.get('postmortem_due_count')}"
    )
    print(
        "phase5_exit_staging_readiness_drill_blocker_count="
        f"{written_drill.get('blocker_count')}"
    )
    print(
        "phase5_exit_staging_readiness_drill_complete="
        f"{written_drill.get('paper_trade_drill_complete')}"
    )
    print(
        "phase5_exit_staging_readiness_drill_exit_gate_passed="
        f"{written_drill.get('phase5_paper_trade_drill_exit_gate_passed')}"
    )
    print(
        "phase5_exit_staging_readiness_phase5_certified="
        f"{written_certification.get('phase5_certified')}"
    )
    print(
        "phase5_exit_staging_readiness_phase6_handoff_allowed="
        f"{written_certification.get('phase6_handoff_allowed')}"
    )
    print(
        "phase5_exit_staging_readiness_phase7_planning_allowed="
        f"{written_certification.get('phase7_planning_allowed')}"
    )
    print(
        "phase5_exit_staging_readiness_phase7_proof_credit_allowed="
        f"{written_certification.get('phase7_proof_credit_allowed')}"
    )
    print(
        "phase5_exit_staging_readiness_live_capital_enabled_count="
        f"{written_certification.get('live_capital_enabled_count')}"
    )

    if errors:
        for error in errors:
            print(f"phase5_exit_staging_readiness_error={error}")
        print("phase5_exit_staging_readiness_check=failed")
        return 1

    print("phase5_exit_staging_readiness_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
