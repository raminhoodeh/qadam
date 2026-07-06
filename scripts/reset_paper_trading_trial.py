#!/usr/bin/env python3
"""Reset Qadam's local paper-trading trial epoch.

This resets Qadam's own paper trial ledger and 30-day proof counter without
mutating live capital or calling broker write routes. Alpaca remains a paper
broker mirror; future read-only syncs are rebased through the reset epoch so
pre-reset paper orders do not count as current-trial trades.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
from uuid import uuid4
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.paper_account import (  # noqa: E402
    MATURITY_CLOSED_TRADE_TARGET,
    PAPER_ACCOUNT_SCHEMA_VERSION,
    PAPER_TRIAL_RESET_SCHEMA_VERSION,
    PaperAccountMirrorStore,
    PaperAccountSnapshot,
    _now,
    write_paper_trial_reset_epoch,
)
from orchestrator.paperops_30_day_operations import (  # noqa: E402
    build_paperops_30_day_operations,
    paperops_30_day_operations_paths,
    write_paperops_30_day_operations,
)
from orchestrator.phase7_demo_proof_run import (  # noqa: E402
    PHASE7_DEMO_PROOF_TIMEZONE,
    build_phase7_demo_proof_run,
    phase7_demo_proof_run_paths,
    write_phase7_demo_proof_run,
)
from orchestrator.release_contract import PAPER_ACCOUNT_SCOPE  # noqa: E402


ARCHIVE_RUNTIME_FILES = (
    "alpaca_paper_mirror.json",
    "paper_account_snapshots.jsonl",
    "paper_positions.jsonl",
    "paper_closed_trades.jsonl",
    "paper_orders.jsonl",
    "paperops_alpaca_paper_post.json",
    "paperops_alpaca_paper_post_submission_ledger.json",
    "paperops_paper_lifecycle_poller.json",
    "paper_lifecycle_portfolio_postmortem.json",
    "paper_live_certification.json",
    "paper_operational_readiness.json",
    "paperops_active_paper_trading_automation.json",
    "paperops_submit_regression_guard.json",
    "phase7_demo_proof_run.json",
    "paperops_30_day_operations.json",
    "phase7_certification.json",
    "phase7_guarded_alpaca_paper_submit_path.json",
    "phase7_proof_order_staging.json",
    "phase7_proof_lifecycle_monitor.json",
    "phase7_proof_postmortem_contract.json",
    "phase7_performance_evaluator.json",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--balance-gbp",
        type=float,
        default=100000.0,
        help="Fresh Qadam paper-trial balance. Default: 100000.",
    )
    parser.add_argument(
        "--start-date",
        default=None,
        help=(
            "Fresh 30-day counter start date in YYYY-MM-DD. Defaults to today's "
            f"date in {PHASE7_DEMO_PROOF_TIMEZONE}."
        ),
    )
    parser.add_argument(
        "--label",
        default="fresh_qadam_evolution_test",
        help="Human-readable reset label recorded in the epoch contract.",
    )
    return parser.parse_args()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _default_start_date() -> str:
    return _now_utc().astimezone(ZoneInfo(PHASE7_DEMO_PROOF_TIMEZONE)).date().isoformat()


def _archive_runtime(runtime: Path, reset_id: str) -> tuple[Path, list[str]]:
    archive_dir = runtime / "archive" / reset_id
    archive_dir.mkdir(parents=True, exist_ok=True)
    archived: list[str] = []
    for relative in ARCHIVE_RUNTIME_FILES:
        source = runtime / relative
        if not source.exists():
            continue
        target = archive_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        archived.append(relative)
    manifest = {
        "schema_version": PAPER_TRIAL_RESET_SCHEMA_VERSION,
        "artifact_type": "paper_trial_reset_archive_manifest",
        "reset_id": reset_id,
        "created_at": _now(),
        "archived_files": archived,
        "boundary": "Archive only. It preserves pre-reset paper artifacts and grants no trade authority.",
    }
    (archive_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return archive_dir, archived


def _clear_archived_runtime(runtime: Path, archived_files: list[str]) -> list[str]:
    cleared: list[str] = []
    for relative in archived_files:
        path = runtime / relative
        if not path.exists() or not path.is_file():
            continue
        path.unlink()
        cleared.append(relative)
    return cleared


def _write_fresh_paper_snapshot(
    *,
    store: PaperAccountMirrorStore,
    balance_gbp: float,
    reset_id: str,
) -> PaperAccountSnapshot:
    snapshot = PaperAccountSnapshot(
        schema_version=PAPER_ACCOUNT_SCHEMA_VERSION,
        snapshot_id=str(uuid4()),
        account_scope=PAPER_ACCOUNT_SCOPE,
        mode="paper",
        broker="local_trial_epoch",
        connection_status="local_trial_epoch_reset_pending_alpaca_readonly_sync",
        starting_balance_gbp=balance_gbp,
        current_balance_gbp=balance_gbp,
        cash_gbp=balance_gbp,
        equity_gbp=balance_gbp,
        peak_equity_gbp=balance_gbp,
        realized_pnl_gbp=0.0,
        unrealized_pnl_gbp=0.0,
        drawdown_pct=0.0,
        max_drawdown_pct=0.0,
        live_capital_enabled=False,
        write_authority=False,
        open_position_count=0,
        closed_trade_count=0,
        postmortem_due_count=0,
        postmortem_complete_count=0,
        maturity_closed_trade_target=MATURITY_CLOSED_TRADE_TARGET,
        maturity_closed_trade_count=0,
        timeline_status=f"trial_epoch_reset:{reset_id}",
        observed_at=_now(),
        boundary=(
            "Fresh Qadam paper-trial epoch initialized at the requested balance. "
            "This local reset does not enable live capital and does not perform "
            "broker writes."
        ),
    )
    store.replace_positions(())
    store.replace_orders(())
    store.replace_closed_trades(())
    store.write_snapshot(snapshot)
    return snapshot


def main() -> int:
    args = _parse_args()
    settings = Settings.from_env()
    runtime = Path(settings.runtime_dir)
    runtime.mkdir(parents=True, exist_ok=True)
    start_date = args.start_date or _default_start_date()
    reset_at = _now()
    reset_id = f"paper-trial-reset-{reset_at.replace(':', '').replace('+', 'Z')}"
    store = PaperAccountMirrorStore(settings=settings)
    latest = store.latest_snapshot()
    positions = store.read_positions()
    orders = store.read_orders()
    closed_trades = store.read_closed_trades()
    archive_dir, archived_files = _archive_runtime(runtime, reset_id)
    cleared_files = _clear_archived_runtime(runtime, archived_files)

    epoch = {
        "schema_version": PAPER_TRIAL_RESET_SCHEMA_VERSION,
        "artifact_type": "paper_trial_reset_epoch",
        "artifact_id": f"paper-trial-reset:{reset_id}",
        "reset_id": reset_id,
        "label": args.label,
        "reset_at": reset_at,
        "start_date": start_date,
        "trial_balance_gbp": round(float(args.balance_gbp), 2),
        "paper_account_scope": PAPER_ACCOUNT_SCOPE,
        "archive_path": str(archive_dir),
        "archived_file_count": len(archived_files),
        "archived_files": archived_files,
        "cleared_file_count": len(cleared_files),
        "cleared_files": cleared_files,
        "broker": getattr(latest, "broker", "unknown") if latest else "not_initialized",
        "broker_connection_status": (
            getattr(latest, "connection_status", "unknown") if latest else "not_initialized"
        ),
        "broker_equity_baseline_gbp": (
            getattr(latest, "equity_gbp", None) if latest else None
        ),
        "broker_cash_baseline_gbp": getattr(latest, "cash_gbp", None) if latest else None,
        "broker_open_position_count_at_reset": len(positions),
        "broker_open_position_symbols_at_reset": sorted(
            {position.instrument for position in positions if position.instrument}
        ),
        "broker_order_count_at_reset": len(orders),
        "broker_closed_trade_count_at_reset": len(closed_trades),
        "paper_30_day_counter_reset": True,
        "live_capital_enabled": False,
        "broker_write_performed": False,
        "boundary": (
            "Qadam local paper-trial reset: reset account view, proof counter, "
            "and active-trial trade history from this epoch. It does not call "
            "live endpoints, does not use live capital, and does not mutate the "
            "broker account."
        ),
    }
    epoch_path, epoch_history_path = write_paper_trial_reset_epoch(epoch, settings)
    snapshot = _write_fresh_paper_snapshot(
        store=store,
        balance_gbp=round(float(args.balance_gbp), 2),
        reset_id=reset_id,
    )

    phase7_artifact = build_phase7_demo_proof_run(
        settings=settings,
        start_date=start_date,
        reset=True,
    )
    _, _, phase7_event_log_path = phase7_demo_proof_run_paths(settings)
    _, _, _, phase7_written = write_phase7_demo_proof_run(
        phase7_artifact,
        settings=settings,
        record_event=True,
        event_log_path=phase7_event_log_path,
    )

    operations_artifact = build_paperops_30_day_operations(settings=settings)
    _, _, operations_event_log_path = paperops_30_day_operations_paths(settings)
    _, _, _, operations_written = write_paperops_30_day_operations(
        operations_artifact,
        settings=settings,
        record_event=True,
        event_log_path=operations_event_log_path,
    )

    print("paper_trial_reset_status=ok")
    print(f"paper_trial_reset_id={reset_id}")
    print(f"paper_trial_reset_epoch_path={epoch_path}")
    print(f"paper_trial_reset_epoch_history_path={epoch_history_path}")
    print(f"paper_trial_reset_archive_path={archive_dir}")
    print(f"paper_trial_reset_archived_file_count={len(archived_files)}")
    print(f"paper_trial_reset_cleared_file_count={len(cleared_files)}")
    print(f"paper_trial_reset_balance_gbp={snapshot.current_balance_gbp}")
    print(f"paper_trial_reset_start_date={start_date}")
    print(f"paper_trial_reset_active_day_number={phase7_written['active_day_number']}")
    print(f"paper_trial_reset_calendar_days_remaining={phase7_written['calendar_days_remaining']}")
    print(f"paper_trial_reset_phase7_30_day_run_complete={phase7_written['phase7_30_day_run_complete']}")
    print(f"paper_trial_reset_operations_active_day_number={operations_written['active_day_number']}")
    print(f"paper_trial_reset_operations_status={operations_written['status']}")
    print(f"paper_trial_reset_broker_write_performed={epoch['broker_write_performed']}")
    print(f"paper_trial_reset_live_capital_enabled={epoch['live_capital_enabled']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
