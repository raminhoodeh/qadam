#!/usr/bin/env python3
"""Validate Q5E-5 submitted paper-order and broker-receipt state."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.cockpit_status import build_cockpit_status, export_cockpit_status  # noqa: E402
from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.paper_account import (  # noqa: E402
    PaperAccountMirrorStore,
    PaperOrder,
    ensure_d6_paper_account_mirror,
)
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
    PHASE5_PAPER_SUBMIT_ENABLEMENT_SCHEMA_VERSION,
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
    build_phase5_position_monitor,
    position_monitor_paths,
    validate_phase5_position_monitor_bundle,
    write_phase5_position_monitor,
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


def _mirror_submitted_order(receipt: dict, settings: Settings) -> PaperOrder:
    ensure_d6_paper_account_mirror(settings)
    store = PaperAccountMirrorStore(settings=settings)
    existing_positions = store.read_positions()
    existing_q5e6_position = next(
        (
            position
            for position in existing_positions
            if str(position.source_intent_id) == str(receipt["submitted_order_ref"])
            and str(position.position_id).startswith("q5e6-open-position-")
        ),
        None,
    )
    existing_order = next(
        (
            order
            for order in store.read_orders()
            if str(order.order_id) == str(receipt["submitted_order_ref"])
        ),
        None,
    )
    quantity = float(receipt["quantity"])
    filled_avg_price = (
        round(float(receipt["notional_gbp"]) / quantity, 6)
        if existing_q5e6_position is not None and quantity
        else None
    )
    existing_orders = tuple(
        order
        for order in store.read_orders()
        if not str(order.order_id).startswith("q5e5-paper-order-")
        and str(order.order_id) != "None"
        and "Q5E-5 mirrors" not in str(order.boundary)
    )
    order = PaperOrder(
        schema_version=1,
        order_id=str(receipt["submitted_order_ref"]),
        status="filled" if existing_q5e6_position is not None else str(receipt["order_status_for_mirror"]),
        instrument=str(receipt["instrument"]),
        direction=str(receipt["side"]),
        quantity=quantity,
        notional_gbp=float(receipt["notional_gbp"]),
        order_type=str(receipt["order_type"]),
        limit_price=None,
        submitted_at=receipt["submitted_at"],
        filled_at=(
            getattr(existing_q5e6_position, "opened_at", None)
            or getattr(existing_order, "filled_at", None)
            if existing_q5e6_position is not None
            else None
        ),
        filled_quantity=quantity if existing_q5e6_position is not None else 0.0,
        filled_avg_price=filled_avg_price,
        execution_allowed=False,
        paper_order_allowed=False,
        boundary=(
            "Q5E-5 mirrors a local guarded submitted paper order for lifecycle "
            "reconciliation only. It is not a broker POST result and grants no "
            "order create, cancel, replace, close, resize, or live-capital authority."
        ),
    )
    store.replace_orders(existing_orders + (order,))
    return order


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
    _, _, _, written_kill_bundle = write_phase5_kill_switch_ledger(
        build_phase5_kill_switch_ledger(settings=settings),
        settings=settings,
        record_event=True,
        event_log_path=kill_event_log_path,
    )
    kill_errors = validate_phase5_kill_switch_ledger(written_kill_bundle)

    _, _, adapter_event_log_path = phase5_execution_adapter_status_paths(settings)
    if adapter_event_log_path.exists():
        adapter_event_log_path.unlink()
    _, _, _, written_adapter_bundle = write_phase5_execution_adapter_status(
        build_phase5_execution_adapter_status(settings=settings),
        settings=settings,
        record_event=True,
        event_log_path=adapter_event_log_path,
    )
    adapter_errors = validate_phase5_execution_adapter_status_bundle(written_adapter_bundle)

    _, _, staging_event_log_path = phase5_paper_order_staging_paths(settings)
    if staging_event_log_path.exists():
        staging_event_log_path.unlink()
    _, _, _, written_staging_bundle = write_phase5_paper_order_staging_gate(
        build_phase5_paper_order_staging_gate(settings=settings),
        settings=settings,
        record_event=True,
        event_log_path=staging_event_log_path,
    )
    staging_errors = validate_phase5_paper_order_staging_bundle(written_staging_bundle)

    _, _, dry_run_event_log_path = phase5_alpaca_paper_dry_run_paths(settings)
    if dry_run_event_log_path.exists():
        dry_run_event_log_path.unlink()
    _, _, _, written_dry_run_bundle = write_phase5_alpaca_paper_dry_run(
        build_phase5_alpaca_paper_dry_run(settings=settings),
        settings=settings,
        record_event=True,
        event_log_path=dry_run_event_log_path,
    )
    dry_run_errors = validate_phase5_alpaca_paper_dry_run_bundle(written_dry_run_bundle)

    output_path, history_path, submit_event_log_path = paper_submit_enablement_paths(settings)
    if submit_event_log_path.exists():
        submit_event_log_path.unlink()
    _, _, _, written_submit_path_bundle = write_phase5_paper_submit_enablement_gate(
        build_phase5_paper_submit_enablement_gate(settings=settings),
        settings=settings,
        record_event=True,
        event_log_path=submit_event_log_path,
    )
    submit_path_errors = validate_phase5_paper_submit_enablement_bundle(written_submit_path_bundle)

    receipt_path, receipt_history_path, receipt_event_log_path = guarded_paper_submit_receipt_paths(
        settings
    )
    if receipt_event_log_path.exists():
        receipt_event_log_path.unlink()
    receipt_path, receipt_history_path, receipt_event_log_path, written_receipt = (
        write_phase5_guarded_paper_submit_receipt(
            build_phase5_guarded_paper_submit_receipt(settings=settings),
            settings=settings,
            record_event=True,
            event_log_path=receipt_event_log_path,
        )
    )
    receipt_errors = validate_phase5_guarded_paper_submit_receipt(written_receipt)
    mirrored_order = _mirror_submitted_order(written_receipt, settings)

    if submit_event_log_path.exists():
        submit_event_log_path.unlink()
    output_path, history_path, submit_event_log_path, written_submit_bundle = (
        write_phase5_paper_submit_enablement_gate(
            build_phase5_paper_submit_enablement_gate(settings=settings),
            settings=settings,
            record_event=True,
            event_log_path=submit_event_log_path,
        )
    )
    submit_errors = validate_phase5_paper_submit_enablement_bundle(written_submit_bundle)
    submit_replay = EventLog(submit_event_log_path, echo=False).replay()
    target = _target_record(written_submit_bundle)

    position_path, _, position_event_log_path = position_monitor_paths(settings)
    if position_event_log_path.exists():
        position_event_log_path.unlink()
    position_path, _, position_event_log_path, written_position = write_phase5_position_monitor(
        build_phase5_position_monitor(settings=settings),
        settings=settings,
        record_event=True,
        event_log_path=position_event_log_path,
    )
    position_errors = validate_phase5_position_monitor_bundle(written_position)

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
        ("q5_8_path", submit_path_errors),
        ("q5e_5_receipt", receipt_errors),
        ("q5_8", submit_errors),
        ("q5_11", position_errors),
        ("q5_13", system_map_errors),
        ("q5_14", drill_errors),
        ("q5_15", certification_errors),
    ):
        if validation_errors:
            errors.append(f"{label}_validation_errors:" + ",".join(validation_errors))
    if q5e1_artifact.get("paper_size_eligible_count", 0) < 1:
        errors.append("q5e_5_missing_q5e_1_eligible_setup")
    if written_staging_bundle.get("staged_order_count", 0) < 1:
        errors.append("q5e_5_missing_staged_order")
    if written_dry_run_bundle.get("dry_run_receipt_count", 0) < 1:
        errors.append("q5e_5_missing_dry_run_receipt")
    if written_submit_path_bundle.get("submit_path_available_count", 0) < 1:
        errors.append("q5e_5_missing_guarded_submit_path")
    if written_receipt.get("paper_order_submitted") is not True:
        errors.append("q5e_5_receipt_not_submitted")
    if written_receipt.get("broker_submit_receipt_created") is not True:
        errors.append("q5e_5_broker_receipt_missing")
    if written_receipt.get("broker_post_called") is not False:
        errors.append("q5e_5_broker_post_called")
    if written_receipt.get("alpaca_post_called") is not False:
        errors.append("q5e_5_alpaca_post_called")
    if written_receipt.get("live_capital_enabled") is not False:
        errors.append("q5e_5_live_capital_enabled")
    if not target:
        errors.append("q5e_5_target_submit_record_missing")
    if target:
        if target.get("status") != "submitted_paper_order":
            errors.append("q5e_5_target_status_not_submitted")
        if target.get("receipt_state") != "paper_submit_receipt_recorded":
            errors.append("q5e_5_target_receipt_state_invalid")
        if target.get("paper_order_submitted") is not True:
            errors.append("q5e_5_target_not_submitted")
        if target.get("broker_submit_receipt_created") is not True:
            errors.append("q5e_5_target_receipt_missing")
        if target.get("broker_post_called") is not False:
            errors.append("q5e_5_target_broker_post_called")
        if target.get("alpaca_post_called") is not False:
            errors.append("q5e_5_target_alpaca_post_called")
        if target.get("live_capital_enabled") is not False:
            errors.append("q5e_5_target_live_capital_enabled")
    if written_submit_bundle.get("paper_order_submitted_count") != 1:
        errors.append("q5e_5_submit_count_not_one")
    if written_submit_bundle.get("broker_submit_receipt_created_count") != 1:
        errors.append("q5e_5_receipt_count_not_one")
    if submit_replay["total_events"] != written_submit_bundle.get("submit_enablement_record_count"):
        errors.append("q5e_5_submit_event_log_count_mismatch")
    if mirrored_order.order_id != written_receipt.get("submitted_order_ref"):
        errors.append("q5e_5_mirrored_order_ref_mismatch")
    if written_position.get("submitted_order_count") != 1:
        errors.append("q5e_5_position_submitted_count_not_one")
    if written_position.get("mirrored_order_count") < 1:
        errors.append("q5e_5_position_mirrored_order_missing")
    open_position_progressed = int(written_position.get("open_position_count", 0) or 0) > 0
    if written_position.get("closed_trade_count") != 0:
        errors.append("q5e_5_closed_trade_premature")
    if written_position.get("postmortem_due_count") != 0:
        errors.append("q5e_5_postmortem_due_premature")
    if written_position.get("failed_reconciliation_count") != 0:
        errors.append("q5e_5_position_reconciliation_failed")
    if written_drill.get("submitted_paper_order_count") != 1:
        errors.append("q5e_5_drill_submitted_order_missing")
    if written_drill.get("broker_receipt_count") != 1:
        errors.append("q5e_5_drill_broker_receipt_missing")
    if "paper_order_submission_missing" in written_drill.get("blockers", []):
        errors.append("q5e_5_drill_still_missing_submission")
    if "submitted_order_not_mirrored" in written_drill.get("blockers", []):
        errors.append("q5e_5_drill_still_missing_mirror")
    expected_blockers = ["closed_trade_missing", "postmortem_due_missing"]
    if not open_position_progressed:
        expected_blockers.append("open_position_missing")
    for expected_blocker in expected_blockers:
        if expected_blocker not in written_drill.get("blockers", []):
            errors.append(f"q5e_5_drill_missing_expected_blocker:{expected_blocker}")
    if open_position_progressed and "open_position_missing" in written_drill.get("blockers", []):
        errors.append("q5e_5_drill_still_missing_open_position")
    if written_drill.get("phase5_paper_trade_drill_exit_gate_passed") is not False:
        errors.append("q5e_5_drill_exit_gate_opened")
    if written_certification.get("phase5_certified") is not False:
        errors.append("q5e_5_certification_opened")
    if written_certification.get("phase6_handoff_allowed") is not False:
        errors.append("q5e_5_phase6_handoff_opened")
    if written_system_map.get("guardrails", {}).get("submitted_order_count") != 1:
        errors.append("q5e_5_system_map_submitted_count_missing")
    if written_system_map.get("guardrails", {}).get("dashboard_claims_trading_now") is not False:
        errors.append("q5e_5_system_map_claims_trading_now")
    for label, bundle in (
        ("submit", written_submit_bundle),
        ("receipt", written_receipt),
        ("position", written_position),
        ("drill", written_drill),
        ("certification", written_certification),
    ):
        for key in (
            "broker_post_called_count",
            "alpaca_post_called_count",
            "live_endpoint_allowed_count",
            "live_capital_enabled_count",
            "prediction_market_write_allowed_count",
            "phase7_proof_credit_allowed_count",
        ):
            if int(bundle.get(key, 0) or 0) != 0:
                errors.append(f"q5e_5_{label}_unsafe_count_nonzero:{key}")

    print("phase5_exit_submitted_paper_order_status=" + written_receipt["status"])
    print(
        "phase5_exit_submitted_paper_order_schema_version="
        f"{PHASE5_PAPER_SUBMIT_ENABLEMENT_SCHEMA_VERSION}"
    )
    print(f"phase5_exit_submitted_paper_order_receipt_path={receipt_path}")
    print(f"phase5_exit_submitted_paper_order_receipt_history_path={receipt_history_path}")
    print(f"phase5_exit_submitted_paper_order_receipt_event_log_path={receipt_event_log_path}")
    print(f"phase5_exit_submitted_paper_order_submit_gate_path={output_path}")
    print(f"phase5_exit_submitted_paper_order_position_monitor_path={position_path}")
    print(f"phase5_exit_submitted_paper_order_drill_path={drill_path}")
    print(f"phase5_exit_submitted_paper_order_certification_path={certification_path}")
    print(f"phase5_exit_submitted_paper_order_system_map_path={system_map_path}")
    print(f"phase5_exit_submitted_paper_order_cockpit_runtime_path={cockpit_export['runtime_path']}")
    print(f"phase5_exit_submitted_paper_order_target_strategy_family_key={TARGET_STRATEGY_FAMILY_KEY}")
    print(f"phase5_exit_submitted_paper_order_submitted_order_ref={written_receipt.get('submitted_order_ref')}")
    print(f"phase5_exit_submitted_paper_order_broker_receipt_ref={written_receipt.get('broker_receipt_ref')}")
    print(f"phase5_exit_submitted_paper_order_receipt_state={written_receipt.get('broker_receipt_state')}")
    print(f"phase5_exit_submitted_paper_order_mirrored_order_status={mirrored_order.status}")
    print(f"phase5_exit_submitted_paper_order_submit_path_available_count={written_submit_bundle.get('submit_path_available_count')}")
    print(f"phase5_exit_submitted_paper_order_paper_order_submitted_count={written_submit_bundle.get('paper_order_submitted_count')}")
    print(f"phase5_exit_submitted_paper_order_broker_receipt_count={written_submit_bundle.get('broker_submit_receipt_created_count')}")
    print(f"phase5_exit_submitted_paper_order_broker_post_called_count={written_submit_bundle.get('broker_post_called_count')}")
    print(f"phase5_exit_submitted_paper_order_alpaca_post_called_count={written_submit_bundle.get('alpaca_post_called_count')}")
    print(f"phase5_exit_submitted_paper_order_position_submitted_order_count={written_position.get('submitted_order_count')}")
    print(f"phase5_exit_submitted_paper_order_position_mirrored_order_count={written_position.get('mirrored_order_count')}")
    print(f"phase5_exit_submitted_paper_order_open_position_count={written_position.get('open_position_count')}")
    print(f"phase5_exit_submitted_paper_order_closed_trade_count={written_position.get('closed_trade_count')}")
    print(f"phase5_exit_submitted_paper_order_postmortem_due_count={written_position.get('postmortem_due_count')}")
    print(f"phase5_exit_submitted_paper_order_drill_state={written_drill.get('paper_trade_drill_state')}")
    print(f"phase5_exit_submitted_paper_order_drill_blocker_count={written_drill.get('blocker_count')}")
    print(f"phase5_exit_submitted_paper_order_drill_exit_gate_passed={written_drill.get('phase5_paper_trade_drill_exit_gate_passed')}")
    print(f"phase5_exit_submitted_paper_order_phase5_certified={written_certification.get('phase5_certified')}")
    print(f"phase5_exit_submitted_paper_order_phase6_handoff_allowed={written_certification.get('phase6_handoff_allowed')}")
    print(f"phase5_exit_submitted_paper_order_live_capital_enabled_count={written_submit_bundle.get('live_capital_enabled_count')}")
    print("phase5_exit_submitted_paper_order_boundary=" + written_receipt["boundary"])

    if errors:
        for error in errors:
            print(f"phase5_exit_submitted_paper_order_error={error}")
        print("phase5_exit_submitted_paper_order_check=failed")
        return 1

    print("phase5_exit_submitted_paper_order_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
