#!/usr/bin/env python3
"""Validate Q5E-6 guarded open-position lifecycle state."""

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
    PaperAccountMirrorStore,
    PaperAccountSnapshot,
    PaperOrder,
    PaperPosition,
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
    build_phase5_guarded_open_position,
    build_phase5_position_monitor,
    guarded_open_position_paths,
    position_monitor_paths,
    validate_phase5_guarded_open_position,
    validate_phase5_position_monitor_bundle,
    write_phase5_guarded_open_position,
    write_phase5_position_monitor,
)
from orchestrator.phase5_system_map import (  # noqa: E402
    validate_phase5_system_map_bundle,
    write_phase5_system_map,
)
from orchestrator.release_contract import PAPER_ACCOUNT_SCOPE  # noqa: E402


def _target_record(bundle: dict) -> dict:
    for record in bundle.get("records", []):
        if not isinstance(record, dict):
            continue
        if record.get("strategy_family_key") == TARGET_STRATEGY_FAMILY_KEY:
            return record
        if (
            record.get("artifact_type") == "position_state"
            and str(record.get("source_order_ref") or "").endswith(TARGET_STRATEGY_FAMILY_KEY)
        ):
            return record
    return {}


def _mirror_submitted_order(receipt: dict, settings: Settings) -> PaperOrder:
    ensure_d6_paper_account_mirror(settings)
    store = PaperAccountMirrorStore(settings=settings)
    existing_orders = tuple(
        order
        for order in store.read_orders()
        if not str(order.order_id).startswith("q5e5-paper-order-")
        and str(order.order_id) != "None"
        and "Q5E-5 mirrors" not in str(order.boundary)
        and "Q5E-6 advances" not in str(order.boundary)
    )
    order = PaperOrder(
        schema_version=1,
        order_id=str(receipt["submitted_order_ref"]),
        status=str(receipt["order_status_for_mirror"]),
        instrument=str(receipt["instrument"]),
        direction=str(receipt["side"]),
        quantity=float(receipt["quantity"]),
        notional_gbp=float(receipt["notional_gbp"]),
        order_type=str(receipt["order_type"]),
        limit_price=None,
        submitted_at=receipt["submitted_at"],
        filled_at=None,
        filled_quantity=0.0,
        filled_avg_price=None,
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


def _append_open_position_snapshot(store: PaperAccountMirrorStore, settings: Settings) -> None:
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
        account_scope=getattr(latest, "account_scope", PAPER_ACCOUNT_SCOPE),
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
        maturity_closed_trade_count=getattr(latest, "maturity_closed_trade_count", len(closed_trades)),
        timeline_status="q5e6_open_position_lifecycle_recorded",
        observed_at=str(positions[-1].opened_at if positions else getattr(latest, "observed_at", None)),
        boundary=(
            "Q5E-6 read-only local mirror snapshot records an open-position "
            "lifecycle state only. No broker write path exists, and it grants "
            "no close, resize, cancel, replace, or live-capital authority."
        ),
    )
    store.write_snapshot(snapshot, log_event=True)


def _mirror_open_position(artifact: dict, settings: Settings) -> tuple[PaperOrder, PaperPosition]:
    ensure_d6_paper_account_mirror(settings)
    store = PaperAccountMirrorStore(settings=settings)
    quantity = float(artifact["quantity"])
    entry_price = artifact.get("entry_price")
    order = PaperOrder(
        schema_version=1,
        order_id=str(artifact["source_order_ref"]),
        status=str(artifact["order_status_for_mirror"]),
        instrument=str(artifact["instrument"]),
        direction=str(artifact["side"]),
        quantity=quantity,
        notional_gbp=float(artifact["notional_gbp"]),
        order_type="market",
        limit_price=None,
        submitted_at=artifact.get("opened_at"),
        filled_at=artifact.get("opened_at"),
        filled_quantity=quantity,
        filled_avg_price=float(entry_price) if entry_price is not None else None,
        execution_allowed=False,
        paper_order_allowed=False,
        boundary=(
            "Q5E-6 advances the local submitted paper order to filled/open-position "
            "lifecycle state for reconciliation only. It is not a broker fill and "
            "grants no order create, cancel, replace, close, resize, or live-capital "
            "authority."
        ),
    )
    position = PaperPosition(
        schema_version=1,
        position_id=str(artifact["position_ref"]),
        status="open_position",
        instrument=str(artifact["instrument"]),
        direction=str(artifact["side"]),
        quantity=quantity,
        entry_price=float(entry_price) if entry_price is not None else None,
        current_price=float(entry_price) if entry_price is not None else None,
        unrealized_pnl_gbp=0.0,
        risk_size_gbp=float(artifact["risk_size_gbp"]),
        opened_at=artifact.get("opened_at"),
        invalidation="q5e6_guarded_lifecycle_only_close_blocked_until_q5e7",
        source_intent_id=str(artifact["source_order_ref"]),
        boundary=(
            "Q5E-6 records a local guarded open-position lifecycle state. It cannot "
            "close, resize, cancel, replace, call brokers, or enable live capital."
        ),
    )
    existing_orders = tuple(
        existing
        for existing in store.read_orders()
        if str(existing.order_id) != str(order.order_id)
        and "Q5E-6 advances" not in str(existing.boundary)
    )
    existing_positions = tuple(
        existing
        for existing in store.read_positions()
        if str(existing.position_id) != str(position.position_id)
        and str(existing.source_intent_id) != str(position.source_intent_id)
        and "Q5E-6 records" not in str(existing.boundary)
    )
    store.replace_orders(existing_orders + (order,))
    store.replace_positions(existing_positions + (position,))
    _append_open_position_snapshot(store, settings)
    return order, position


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

    open_path, open_history_path, open_event_log_path = guarded_open_position_paths(settings)
    if open_event_log_path.exists():
        open_event_log_path.unlink()
    open_path, open_history_path, open_event_log_path, written_open_position = (
        write_phase5_guarded_open_position(
            build_phase5_guarded_open_position(settings=settings),
            settings=settings,
            record_event=True,
            event_log_path=open_event_log_path,
        )
    )
    open_position_errors = validate_phase5_guarded_open_position(written_open_position)
    filled_order, mirrored_position = _mirror_open_position(written_open_position, settings)

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
    position_record = _target_record(written_position)

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
        ("q5e_6_open_position", open_position_errors),
        ("q5_11", position_errors),
        ("q5_13", system_map_errors),
        ("q5_14", drill_errors),
        ("q5_15", certification_errors),
    ):
        if validation_errors:
            errors.append(f"{label}_validation_errors:" + ",".join(validation_errors))
    if q5e1_artifact.get("paper_size_eligible_count", 0) < 1:
        errors.append("q5e_6_missing_q5e_1_eligible_setup")
    if written_staging_bundle.get("staged_order_count", 0) < 1:
        errors.append("q5e_6_missing_staged_order")
    if written_dry_run_bundle.get("dry_run_receipt_count", 0) < 1:
        errors.append("q5e_6_missing_dry_run_receipt")
    if written_submit_path_bundle.get("submit_path_available_count", 0) < 1:
        errors.append("q5e_6_missing_guarded_submit_path")
    if written_submit_bundle.get("paper_order_submitted_count") != 1:
        errors.append("q5e_6_submit_count_not_one")
    if written_submit_bundle.get("broker_submit_receipt_created_count") != 1:
        errors.append("q5e_6_receipt_count_not_one")
    if submit_replay["total_events"] != written_submit_bundle.get("submit_enablement_record_count"):
        errors.append("q5e_6_submit_event_log_count_mismatch")
    if written_open_position.get("status") != "open_position":
        errors.append("q5e_6_open_position_artifact_not_open")
    if written_open_position.get("open_position_created") is not True:
        errors.append("q5e_6_open_position_not_created")
    if written_open_position.get("source_order_ref") != written_receipt.get("submitted_order_ref"):
        errors.append("q5e_6_source_order_ref_mismatch")
    if filled_order.status != "filled":
        errors.append("q5e_6_order_not_filled_in_mirror")
    if mirrored_position.status != "open_position":
        errors.append("q5e_6_position_not_open_in_mirror")
    if mirrored_position.source_intent_id != written_open_position.get("source_order_ref"):
        errors.append("q5e_6_position_source_ref_mismatch")
    if written_position.get("submitted_order_count") != 1:
        errors.append("q5e_6_position_submitted_count_not_one")
    if written_position.get("mirrored_order_count") != 1:
        errors.append("q5e_6_position_mirrored_count_not_one")
    if written_position.get("open_position_count") != 1:
        errors.append("q5e_6_position_open_count_not_one")
    if written_position.get("closed_trade_count") != 0:
        errors.append("q5e_6_closed_trade_premature")
    if written_position.get("postmortem_due_count") != 0:
        errors.append("q5e_6_postmortem_due_premature")
    if written_position.get("failed_reconciliation_count") != 0:
        errors.append("q5e_6_position_reconciliation_failed")
    if position_record.get("status") != "open_position":
        errors.append("q5e_6_position_record_not_open")
    if position_record.get("lifecycle_state") != "open_position":
        errors.append("q5e_6_position_record_lifecycle_not_open")
    if written_drill.get("open_position_count") != 1:
        errors.append("q5e_6_drill_open_position_missing")
    if "open_position_missing" in written_drill.get("blockers", []):
        errors.append("q5e_6_drill_still_missing_open_position")
    for expected_blocker in ("closed_trade_missing", "postmortem_due_missing"):
        if expected_blocker not in written_drill.get("blockers", []):
            errors.append(f"q5e_6_drill_missing_expected_blocker:{expected_blocker}")
    if written_drill.get("phase5_paper_trade_drill_exit_gate_passed") is not False:
        errors.append("q5e_6_drill_exit_gate_opened")
    if written_certification.get("phase5_certified") is not False:
        errors.append("q5e_6_certification_opened")
    if written_certification.get("phase6_handoff_allowed") is not False:
        errors.append("q5e_6_phase6_handoff_opened")
    if written_system_map.get("guardrails", {}).get("open_position_count") != 1:
        errors.append("q5e_6_system_map_open_position_count_missing")
    if written_system_map.get("guardrails", {}).get("dashboard_claims_trading_now") is not False:
        errors.append("q5e_6_system_map_claims_trading_now")
    for label, bundle in (
        ("submit", written_submit_bundle),
        ("open", written_open_position),
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
                errors.append(f"q5e_6_{label}_unsafe_count_nonzero:{key}")

    print("phase5_exit_open_position_status=" + written_open_position["status"])
    print(f"phase5_exit_open_position_schema_version={PHASE5_POSITION_MONITOR_SCHEMA_VERSION}")
    print(f"phase5_exit_open_position_artifact_path={open_path}")
    print(f"phase5_exit_open_position_history_path={open_history_path}")
    print(f"phase5_exit_open_position_event_log_path={open_event_log_path}")
    print(f"phase5_exit_open_position_receipt_path={receipt_path}")
    print(f"phase5_exit_open_position_submit_gate_path={output_path}")
    print(f"phase5_exit_open_position_position_monitor_path={position_path}")
    print(f"phase5_exit_open_position_drill_path={drill_path}")
    print(f"phase5_exit_open_position_certification_path={certification_path}")
    print(f"phase5_exit_open_position_system_map_path={system_map_path}")
    print(f"phase5_exit_open_position_cockpit_runtime_path={cockpit_export['runtime_path']}")
    print(f"phase5_exit_open_position_target_strategy_family_key={TARGET_STRATEGY_FAMILY_KEY}")
    print(f"phase5_exit_open_position_source_order_ref={written_open_position.get('source_order_ref')}")
    print(f"phase5_exit_open_position_position_ref={written_open_position.get('position_ref')}")
    print(f"phase5_exit_open_position_order_status_for_mirror={filled_order.status}")
    print(f"phase5_exit_open_position_position_status_for_mirror={mirrored_position.status}")
    print(f"phase5_exit_open_position_submit_path_available_count={written_submit_bundle.get('submit_path_available_count')}")
    print(f"phase5_exit_open_position_paper_order_submitted_count={written_submit_bundle.get('paper_order_submitted_count')}")
    print(f"phase5_exit_open_position_broker_receipt_count={written_submit_bundle.get('broker_submit_receipt_created_count')}")
    print(f"phase5_exit_open_position_broker_post_called_count={written_submit_bundle.get('broker_post_called_count')}")
    print(f"phase5_exit_open_position_alpaca_post_called_count={written_submit_bundle.get('alpaca_post_called_count')}")
    print(f"phase5_exit_open_position_position_submitted_order_count={written_position.get('submitted_order_count')}")
    print(f"phase5_exit_open_position_position_mirrored_order_count={written_position.get('mirrored_order_count')}")
    print(f"phase5_exit_open_position_open_position_count={written_position.get('open_position_count')}")
    print(f"phase5_exit_open_position_closed_trade_count={written_position.get('closed_trade_count')}")
    print(f"phase5_exit_open_position_postmortem_due_count={written_position.get('postmortem_due_count')}")
    print(f"phase5_exit_open_position_drill_state={written_drill.get('paper_trade_drill_state')}")
    print(f"phase5_exit_open_position_drill_blocker_count={written_drill.get('blocker_count')}")
    print(f"phase5_exit_open_position_drill_exit_gate_passed={written_drill.get('phase5_paper_trade_drill_exit_gate_passed')}")
    print(f"phase5_exit_open_position_phase5_certified={written_certification.get('phase5_certified')}")
    print(f"phase5_exit_open_position_phase6_handoff_allowed={written_certification.get('phase6_handoff_allowed')}")
    print(f"phase5_exit_open_position_live_capital_enabled_count={written_open_position.get('live_capital_enabled_count')}")
    print("phase5_exit_open_position_boundary=" + written_open_position["boundary"])

    if errors:
        for error in errors:
            print(f"phase5_exit_open_position_error={error}")
        print("phase5_exit_open_position_check=failed")
        return 1

    print("phase5_exit_open_position_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
