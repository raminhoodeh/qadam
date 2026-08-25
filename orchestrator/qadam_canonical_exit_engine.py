"""Evaluate and execute pre-armed exits through the canonical paper owner."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any

from orchestrator.config import Settings
from orchestrator.paper_account import sync_alpaca_paper_account_readonly
from orchestrator.paperops_alpaca_paper_post import _live_paper_order_exposure_guard
from orchestrator.paperops_paper_exit_path import _close_alpaca_paper_position
from orchestrator.qadam_control_plane_store import ControlPlaneError
from orchestrator.qadam_operating_ledger import OperatingLedger
from orchestrator.qadam_operator_ready_common import atomic_write_text, runtime_dir


SCHEMA_VERSION = "qadam_canonical_exit_engine.v1"
RUNTIME_ARTIFACT = "qadam_canonical_exit_engine.json"
HISTORY_ARTIFACT = "qadam_canonical_exit_engine_history.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_canonical_exit_engine(
    settings: Settings | None = None,
    *,
    execute_due_exits: bool = False,
    current_time: datetime | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    ledger = OperatingLedger(settings)
    if execute_due_exits:
        ledger.assert_execution_owner()
        ledger.require_execution_available()
    candidates = ledger.due_exit_candidates(current_time=current_time)
    actions: list[dict[str, Any]] = []
    blockers: list[str] = []
    waiting_market_open_count = 0
    for candidate in candidates:
        request_preview = {
            "symbol": candidate["symbol"],
            "side": candidate["exit_side"],
            "qty": str(candidate["quantity"]),
            "client_order_id": f"qadam-exit-{candidate['exit_plan_id'][-24:]}",
        }
        guard = _live_paper_order_exposure_guard(
            settings=settings,
            request_preview=request_preview,
        )
        if guard.get("checks", {}).get("regular_session_open") is not True:
            waiting_market_open_count += 1
            actions.append(
                {
                    "position_key": candidate["position_key"],
                    "symbol": candidate["symbol"],
                    "trigger": candidate["trigger"],
                    "status": "due_waiting_market_open",
                    "broker_write_count": 0,
                }
            )
            continue
        if guard.get("status") != "passed":
            blockers.append(
                f"exit_guard:{candidate['symbol']}:{guard.get('failure_class') or 'blocked'}"
            )
            actions.append(
                {
                    "position_key": candidate["position_key"],
                    "symbol": candidate["symbol"],
                    "trigger": candidate["trigger"],
                    "status": "blocked_exit_guard",
                    "broker_write_count": 0,
                }
            )
            continue
        if not execute_due_exits:
            actions.append(
                {
                    "position_key": candidate["position_key"],
                    "symbol": candidate["symbol"],
                    "trigger": candidate["trigger"],
                    "status": "due_not_executed",
                    "broker_write_count": 0,
                }
            )
            continue
        try:
            mirror_report = sync_alpaca_paper_account_readonly(settings)
            if mirror_report.get("status") != "ok":
                raise ControlPlaneError("alpaca_paper_readonly_refresh_failed")
            pre_reconciliation = ledger.sync_paper_mirror(
                phase=f"pre_exit:{candidate['symbol']}",
                bootstrap=False,
            )
            if pre_reconciliation.get("status") != "passed":
                blockers.extend(pre_reconciliation.get("blockers", []))
                actions.append(
                    {
                        "position_key": candidate["position_key"],
                        "symbol": candidate["symbol"],
                        "trigger": candidate["trigger"],
                        "status": "blocked_pre_exit_reconciliation",
                        "broker_write_count": 0,
                    }
                )
                continue
            prepared = ledger.prepare_exit_order(candidate)
            ledger.mark_order_submitting(str(prepared["order_key"]))
        except Exception as exc:  # noqa: BLE001 - fail closed and expose class only.
            failure = str(exc).split(":", 1)[0]
            blockers.append(f"exit_prewrite:{candidate['symbol']}:{failure}")
            ledger.record_direct_reconciliation(
                phase=f"pre_exit:{candidate['symbol']}",
                expected={"broker_truth_and_prewrite": "required"},
                observed={"broker_truth_and_prewrite": "unavailable"},
                blockers=[failure or type(exc).__name__],
            )
            actions.append(
                {
                    "position_key": candidate["position_key"],
                    "symbol": candidate["symbol"],
                    "trigger": candidate["trigger"],
                    "status": "blocked_exit_prewrite",
                    "failure_class": failure,
                    "broker_write_count": 0,
                }
            )
            continue
        result = _close_alpaca_paper_position(
            settings=settings,
            candidate=candidate,
        )
        ledger.record_exit_result(
            order_key=str(prepared["order_key"]),
            candidate=candidate,
            succeeded=result.get("close_succeeded") is True,
            receipt=result.get("receipt") if isinstance(result.get("receipt"), dict) else None,
            failure_class=str(result.get("failure_class") or "") or None,
        )
        post_reconciliation_status = "not_attempted"
        if result.get("close_attempted") is True:
            try:
                mirror_report = sync_alpaca_paper_account_readonly(settings)
                if mirror_report.get("status") != "ok":
                    raise ControlPlaneError("alpaca_paper_readonly_refresh_failed")
                post_reconciliation = ledger.sync_paper_mirror(
                    phase=f"post_exit:{candidate['symbol']}",
                    bootstrap=False,
                )
                post_reconciliation_status = str(
                    post_reconciliation.get("status") or "blocked"
                )
                if post_reconciliation_status != "passed":
                    blockers.extend(post_reconciliation.get("blockers", []))
            except Exception as exc:  # noqa: BLE001 - fail closed and expose class only.
                failure = str(exc).split(":", 1)[0]
                post_reconciliation_status = "blocked"
                blockers.append(
                    f"exit_post_reconciliation:{candidate['symbol']}:{failure}"
                )
                ledger.record_direct_reconciliation(
                    phase=f"post_exit:{candidate['symbol']}",
                    expected={"broker_readback": "required"},
                    observed={"broker_readback": "unavailable"},
                    blockers=[failure],
                )
        actions.append(
            {
                "position_key": candidate["position_key"],
                "symbol": candidate["symbol"],
                "trigger": candidate["trigger"],
                "status": "close_requested"
                if result.get("close_succeeded") is True
                else "close_failed",
                "failure_class": result.get("failure_class"),
                "post_reconciliation_status": post_reconciliation_status,
                "broker_write_count": 1 if result.get("close_attempted") is True else 0,
            }
        )
    close_requested_count = sum(
        action["status"] == "close_requested" for action in actions
    )
    artifact = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_canonical_exit_engine",
        "generated_at": _now(),
        "status": "blocked" if blockers else "close_requested" if close_requested_count else (
            "due_waiting_market_open" if waiting_market_open_count else "monitoring"
        ),
        "execute_due_exits_requested": execute_due_exits,
        "candidate_count": len(candidates),
        "close_requested_count": close_requested_count,
        "waiting_market_open_count": waiting_market_open_count,
        "blockers": sorted(set(blockers)),
        "actions": actions,
        "paper_only": True,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
    }
    destination = runtime_dir(settings) / RUNTIME_ARTIFACT
    atomic_write_text(destination, json.dumps(artifact, indent=2, sort_keys=True) + "\n")
    history = runtime_dir(settings) / HISTORY_ARTIFACT
    with history.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(artifact, sort_keys=True) + "\n")
        handle.flush()
    return artifact


def validate_canonical_exit_engine(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if artifact.get("paper_only") is not True:
        errors.append("canonical_exit_not_paper_only")
    if artifact.get("live_capital_enabled") is not False:
        errors.append("canonical_exit_live_capital_enabled")
    if artifact.get("proof_credit_allowed") is not False:
        errors.append("canonical_exit_proof_credit_allowed")
    if int(artifact.get("close_requested_count") or 0) > int(
        artifact.get("candidate_count") or 0
    ):
        errors.append("canonical_exit_close_count_exceeds_candidates")
    return errors


__all__ = [
    "RUNTIME_ARTIFACT",
    "SCHEMA_VERSION",
    "build_canonical_exit_engine",
    "validate_canonical_exit_engine",
]
