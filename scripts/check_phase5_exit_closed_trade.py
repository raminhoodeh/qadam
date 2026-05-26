#!/usr/bin/env python3
"""Validate Q5E-7 guarded closed-trade lifecycle state."""

from __future__ import annotations

from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.cockpit_status import build_cockpit_status, export_cockpit_status  # noqa: E402
from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.paper_account import (  # noqa: E402
    POSTMORTEM_PENDING_MARKER_STATUS,
    ClosedPaperTrade,
    PaperAccountMirrorStore,
    PaperAccountSnapshot,
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
    PHASE5_POSITION_MONITOR_SCHEMA_VERSION,
    build_phase5_guarded_closed_trade,
    build_phase5_guarded_open_position,
    build_phase5_position_monitor,
    guarded_closed_trade_paths,
    guarded_open_position_paths,
    position_monitor_paths,
    validate_phase5_guarded_closed_trade,
    validate_phase5_guarded_open_position,
    validate_phase5_position_monitor_bundle,
    write_phase5_guarded_closed_trade,
    write_phase5_guarded_open_position,
    write_phase5_position_monitor,
)
from orchestrator.phase5_system_map import (  # noqa: E402
    validate_phase5_system_map_bundle,
    write_phase5_system_map,
)
from scripts.check_phase5_exit_open_position import (  # noqa: E402
    _mirror_open_position,
    _mirror_submitted_order,
)


def _target_record(bundle: dict, artifact_type: str) -> dict:
    for record in bundle.get("records", []):
        if isinstance(record, dict) and record.get("artifact_type") == artifact_type:
            return record
    return {}


def _append_closed_trade_snapshot(store: PaperAccountMirrorStore, settings: Settings) -> None:
    latest = store.latest_snapshot()
    positions = store.read_positions()
    closed_trades = store.read_closed_trades()
    due_count = sum(1 for trade in closed_trades if trade.postmortem_status == "postmortem_due")
    complete_count = sum(
        1 for trade in closed_trades if trade.postmortem_status == "postmortem_complete"
    )
    starting_balance = float(settings.trial_balance_gbp)
    snapshot = PaperAccountSnapshot(
        schema_version=1,
        snapshot_id=str(uuid4()),
        account_scope=getattr(latest, "account_scope", "first_release_gbp_1000_trial"),
        mode="paper",
        broker=getattr(latest, "broker", "local_mirror_pending_alpaca_readonly"),
        connection_status=getattr(
            latest,
            "connection_status",
            "local_mirror_not_broker_connected",
        ),
        starting_balance_gbp=getattr(latest, "starting_balance_gbp", starting_balance),
        current_balance_gbp=getattr(latest, "current_balance_gbp", starting_balance),
        cash_gbp=getattr(latest, "cash_gbp", starting_balance),
        equity_gbp=getattr(latest, "equity_gbp", starting_balance),
        peak_equity_gbp=getattr(latest, "peak_equity_gbp", starting_balance),
        realized_pnl_gbp=getattr(latest, "realized_pnl_gbp", 0.0),
        unrealized_pnl_gbp=0.0,
        drawdown_pct=getattr(latest, "drawdown_pct", 0.0),
        max_drawdown_pct=getattr(latest, "max_drawdown_pct", 0.0),
        live_capital_enabled=False,
        write_authority=False,
        open_position_count=len(positions),
        closed_trade_count=len(closed_trades),
        postmortem_due_count=due_count,
        postmortem_complete_count=complete_count,
        maturity_closed_trade_target=getattr(latest, "maturity_closed_trade_target", 100),
        maturity_closed_trade_count=len(closed_trades),
        timeline_status="q5e7_closed_trade_lifecycle_recorded",
        observed_at=str(
            closed_trades[-1].closed_at if closed_trades else getattr(latest, "observed_at", None)
        ),
        boundary=(
            "Q5E-7 read-only local mirror snapshot records a closed-trade "
            "lifecycle state only. No broker write path exists, and it grants "
            "no close, resize, cancel, replace, or live-capital authority."
        ),
    )
    store.write_snapshot(snapshot, log_event=True)


def _mirror_closed_trade(artifact: dict, settings: Settings) -> ClosedPaperTrade:
    ensure_d6_paper_account_mirror(settings)
    store = PaperAccountMirrorStore(settings=settings)
    trade = ClosedPaperTrade(
        schema_version=1,
        trade_id=str(artifact["closed_trade_ref"]),
        instrument=str(artifact["instrument"]),
        direction=str(artifact["side"]),
        entry_price=artifact.get("entry_price"),
        exit_price=artifact.get("exit_price"),
        realized_pnl_gbp=float(artifact["realized_pnl_gbp"]),
        r_multiple=float(artifact["r_multiple"]),
        close_reason=str(artifact["close_reason"]),
        opened_at=artifact.get("opened_at"),
        closed_at=artifact.get("closed_at"),
        postmortem_status=str(artifact["postmortem_status"]),
        source_intent_id=str(artifact["source_order_ref"]),
        boundary=(
            "Q5E-7 records a local guarded closed-trade lifecycle state. It is "
            "not a broker close, does not grant close/resize/cancel/replace "
            "authority, and cannot enable live capital."
        ),
    )
    existing_positions = tuple(
        position
        for position in store.read_positions()
        if str(position.position_id) != str(artifact["source_position_ref"])
        and str(position.source_intent_id) != str(artifact["source_order_ref"])
        and "Q5E-6 records" not in str(position.boundary)
    )
    existing_trades = tuple(
        existing
        for existing in store.read_closed_trades()
        if str(existing.trade_id) != str(trade.trade_id)
        and str(existing.source_intent_id) != str(trade.source_intent_id)
        and "Q5E-7 records" not in str(existing.boundary)
    )
    store.replace_positions(existing_positions)
    store.replace_closed_trades(existing_trades + (trade,))
    _append_closed_trade_snapshot(store, settings)
    return trade


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

    receipt_path, _, receipt_event_log_path = guarded_paper_submit_receipt_paths(settings)
    if receipt_event_log_path.exists():
        receipt_event_log_path.unlink()
    _, _, _, written_receipt = write_phase5_guarded_paper_submit_receipt(
        build_phase5_guarded_paper_submit_receipt(settings=settings),
        settings=settings,
        record_event=True,
        event_log_path=receipt_event_log_path,
    )
    receipt_errors = validate_phase5_guarded_paper_submit_receipt(written_receipt)
    _mirror_submitted_order(written_receipt, settings)

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

    open_path, _, open_event_log_path = guarded_open_position_paths(settings)
    if open_event_log_path.exists():
        open_event_log_path.unlink()
    open_path, _, open_event_log_path, written_open_position = write_phase5_guarded_open_position(
        build_phase5_guarded_open_position(settings=settings),
        settings=settings,
        record_event=True,
        event_log_path=open_event_log_path,
    )
    open_position_errors = validate_phase5_guarded_open_position(written_open_position)
    _, mirrored_position = _mirror_open_position(written_open_position, settings)

    closed_path, closed_history_path, closed_event_log_path = guarded_closed_trade_paths(settings)
    if closed_event_log_path.exists():
        closed_event_log_path.unlink()
    closed_path, closed_history_path, closed_event_log_path, written_closed_trade = (
        write_phase5_guarded_closed_trade(
            build_phase5_guarded_closed_trade(settings=settings),
            settings=settings,
            record_event=True,
            event_log_path=closed_event_log_path,
        )
    )
    closed_trade_errors = validate_phase5_guarded_closed_trade(written_closed_trade)
    mirrored_closed_trade = None
    if written_closed_trade.get("status") == "closed_trade":
        mirrored_closed_trade = _mirror_closed_trade(written_closed_trade, settings)
    closed_lifecycle_ready = written_closed_trade.get("status") == "closed_trade"

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
    position_record = _target_record(written_position, "position_state")
    closed_record = _target_record(written_position, "closed_trade_summary")

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
        ("q5e_7_closed_trade", closed_trade_errors),
        ("q5_11", position_errors),
        ("q5_13", system_map_errors),
        ("q5_14", drill_errors),
        ("q5_15", certification_errors),
    ):
        if validation_errors:
            errors.append(f"{label}_validation_errors:" + ",".join(validation_errors))
    if open_position_errors and not closed_lifecycle_ready:
        errors.append("q5e_6_open_position_validation_errors:" + ",".join(open_position_errors))
    if q5e1_artifact.get("paper_size_eligible_count", 0) < 1:
        errors.append("q5e_7_missing_q5e_1_eligible_setup")
    if written_staging_bundle.get("staged_order_count", 0) < 1:
        errors.append("q5e_7_missing_staged_order")
    if written_dry_run_bundle.get("dry_run_receipt_count", 0) < 1:
        errors.append("q5e_7_missing_dry_run_receipt")
    if written_submit_path_bundle.get("submit_path_available_count", 0) < 1:
        errors.append("q5e_7_missing_guarded_submit_path")
    if written_submit_bundle.get("paper_order_submitted_count") != 1:
        errors.append("q5e_7_submit_count_not_one")
    if written_submit_bundle.get("broker_submit_receipt_created_count") != 1:
        errors.append("q5e_7_receipt_count_not_one")
    if submit_replay["total_events"] != written_submit_bundle.get("submit_enablement_record_count"):
        errors.append("q5e_7_submit_event_log_count_mismatch")
    if written_open_position.get("status") != "open_position" and not closed_lifecycle_ready:
        errors.append("q5e_7_open_position_artifact_not_open")
    if mirrored_position.status != "open_position" and not closed_lifecycle_ready:
        errors.append("q5e_7_position_not_open_before_close")
    if written_closed_trade.get("status") != "closed_trade":
        errors.append("q5e_7_closed_trade_artifact_not_closed")
    if written_closed_trade.get("closed_trade_created") is not True:
        errors.append("q5e_7_closed_trade_not_created")
    if written_closed_trade.get("source_order_ref") != written_open_position.get("source_order_ref"):
        errors.append("q5e_7_source_order_ref_mismatch")
    if written_closed_trade.get("source_position_ref") != written_open_position.get("position_ref"):
        errors.append("q5e_7_source_position_ref_mismatch")
    if mirrored_closed_trade is None:
        errors.append("q5e_7_closed_trade_not_mirrored")
    elif mirrored_closed_trade.postmortem_status != POSTMORTEM_PENDING_MARKER_STATUS:
        errors.append("q5e_7_postmortem_marker_premature")
    if (
        mirrored_closed_trade is not None
        and mirrored_closed_trade.source_intent_id != written_closed_trade.get("source_order_ref")
    ):
        errors.append("q5e_7_closed_trade_source_ref_mismatch")
    if written_position.get("submitted_order_count") != 1:
        errors.append("q5e_7_position_submitted_count_not_one")
    if written_position.get("mirrored_order_count") != 1:
        errors.append("q5e_7_position_mirrored_count_not_one")
    if written_position.get("open_position_count") != 0:
        errors.append("q5e_7_position_open_count_not_zero")
    if written_position.get("closed_trade_count") != 1:
        errors.append("q5e_7_position_closed_count_not_one")
    if written_position.get("postmortem_due_count") != 0:
        errors.append("q5e_7_postmortem_due_premature")
    if written_position.get("failed_reconciliation_count") != 0:
        errors.append("q5e_7_position_reconciliation_failed")
    if position_record.get("status") != "closed_trade":
        errors.append("q5e_7_position_record_not_closed")
    if position_record.get("lifecycle_state") != "closed_trade":
        errors.append("q5e_7_position_record_lifecycle_not_closed")
    if closed_record.get("status") != "closed_trade":
        errors.append("q5e_7_closed_record_not_closed")
    if closed_record.get("postmortem_status") != POSTMORTEM_PENDING_MARKER_STATUS:
        errors.append("q5e_7_closed_record_postmortem_status_invalid")
    if written_drill.get("closed_trade_count") != 1:
        errors.append("q5e_7_drill_closed_trade_missing")
    if "closed_trade_missing" in written_drill.get("blockers", []):
        errors.append("q5e_7_drill_still_missing_closed_trade")
    if "open_position_missing" in written_drill.get("blockers", []):
        errors.append("q5e_7_drill_regressed_open_position")
    if "postmortem_due_missing" not in written_drill.get("blockers", []):
        errors.append("q5e_7_drill_missing_postmortem_due_blocker")
    if written_drill.get("phase5_paper_trade_drill_exit_gate_passed") is not False:
        errors.append("q5e_7_drill_exit_gate_opened")
    if written_certification.get("closed_trade_count") != 1:
        errors.append("q5e_7_certification_closed_trade_missing")
    if "closed_trade_missing" in written_certification.get("certification_blockers", []):
        errors.append("q5e_7_certification_still_missing_closed_trade")
    if "open_position_missing" in written_certification.get("certification_blockers", []):
        errors.append("q5e_7_certification_regressed_open_position")
    if "postmortem_due_missing" not in written_certification.get("certification_blockers", []):
        errors.append("q5e_7_certification_missing_postmortem_due_blocker")
    if written_certification.get("phase5_certified") is not False:
        errors.append("q5e_7_certification_opened")
    if written_certification.get("phase6_handoff_allowed") is not False:
        errors.append("q5e_7_phase6_handoff_opened")
    if written_system_map.get("guardrails", {}).get("closed_trade_count") != 1:
        errors.append("q5e_7_system_map_closed_trade_count_missing")
    if written_system_map.get("guardrails", {}).get("dashboard_claims_trading_now") is not False:
        errors.append("q5e_7_system_map_claims_trading_now")
    for label, bundle in (
        ("submit", written_submit_bundle),
        ("open", written_open_position),
        ("closed", written_closed_trade),
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
                errors.append(f"q5e_7_{label}_unsafe_count_nonzero:{key}")

    print("phase5_exit_closed_trade_status=" + written_closed_trade["status"])
    print(f"phase5_exit_closed_trade_schema_version={PHASE5_POSITION_MONITOR_SCHEMA_VERSION}")
    print(f"phase5_exit_closed_trade_artifact_path={closed_path}")
    print(f"phase5_exit_closed_trade_history_path={closed_history_path}")
    print(f"phase5_exit_closed_trade_event_log_path={closed_event_log_path}")
    print(f"phase5_exit_closed_trade_open_position_path={open_path}")
    print(f"phase5_exit_closed_trade_receipt_path={receipt_path}")
    print(f"phase5_exit_closed_trade_submit_gate_path={output_path}")
    print(f"phase5_exit_closed_trade_position_monitor_path={position_path}")
    print(f"phase5_exit_closed_trade_drill_path={drill_path}")
    print(f"phase5_exit_closed_trade_certification_path={certification_path}")
    print(f"phase5_exit_closed_trade_system_map_path={system_map_path}")
    print(f"phase5_exit_closed_trade_cockpit_runtime_path={cockpit_export['runtime_path']}")
    print(f"phase5_exit_closed_trade_target_strategy_family_key={TARGET_STRATEGY_FAMILY_KEY}")
    print(f"phase5_exit_closed_trade_source_order_ref={written_closed_trade.get('source_order_ref')}")
    print(f"phase5_exit_closed_trade_source_position_ref={written_closed_trade.get('source_position_ref')}")
    print(f"phase5_exit_closed_trade_closed_trade_ref={written_closed_trade.get('closed_trade_ref')}")
    print(f"phase5_exit_closed_trade_postmortem_status={written_closed_trade.get('postmortem_status')}")
    print(f"phase5_exit_closed_trade_submit_path_available_count={written_submit_bundle.get('submit_path_available_count')}")
    print(f"phase5_exit_closed_trade_paper_order_submitted_count={written_submit_bundle.get('paper_order_submitted_count')}")
    print(f"phase5_exit_closed_trade_broker_receipt_count={written_submit_bundle.get('broker_submit_receipt_created_count')}")
    print(f"phase5_exit_closed_trade_broker_post_called_count={written_submit_bundle.get('broker_post_called_count')}")
    print(f"phase5_exit_closed_trade_alpaca_post_called_count={written_submit_bundle.get('alpaca_post_called_count')}")
    print(f"phase5_exit_closed_trade_position_submitted_order_count={written_position.get('submitted_order_count')}")
    print(f"phase5_exit_closed_trade_position_mirrored_order_count={written_position.get('mirrored_order_count')}")
    print(f"phase5_exit_closed_trade_open_position_count={written_position.get('open_position_count')}")
    print(f"phase5_exit_closed_trade_closed_trade_count={written_position.get('closed_trade_count')}")
    print(f"phase5_exit_closed_trade_postmortem_due_count={written_position.get('postmortem_due_count')}")
    print(f"phase5_exit_closed_trade_drill_state={written_drill.get('paper_trade_drill_state')}")
    print(f"phase5_exit_closed_trade_drill_blocker_count={written_drill.get('blocker_count')}")
    print(f"phase5_exit_closed_trade_drill_exit_gate_passed={written_drill.get('phase5_paper_trade_drill_exit_gate_passed')}")
    print(f"phase5_exit_closed_trade_phase5_certified={written_certification.get('phase5_certified')}")
    print(f"phase5_exit_closed_trade_phase6_handoff_allowed={written_certification.get('phase6_handoff_allowed')}")
    print(f"phase5_exit_closed_trade_live_capital_enabled_count={written_closed_trade.get('live_capital_enabled_count')}")
    print("phase5_exit_closed_trade_boundary=" + written_closed_trade["boundary"])

    if errors:
        for error in errors:
            print(f"phase5_exit_closed_trade_error={error}")
        print("phase5_exit_closed_trade_check=failed")
        return 1

    print("phase5_exit_closed_trade_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
