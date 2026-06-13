"""Public-safe PaperOps closed-trade funnel diagnostics."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.paper_account import OPEN_ORDER_STATUSES, PaperAccountMirrorStore
from orchestrator.paperops_close_to_ledger import (
    build_paperops_close_to_ledger,
    validate_paperops_close_to_ledger,
)
from orchestrator.paperops_lifecycle_mirror_freshness import (
    build_paperops_lifecycle_mirror_freshness,
)


PAPEROPS_CLOSED_TRADE_FUNNEL_SCHEMA_VERSION = 1
PAPEROPS_CLOSED_TRADE_FUNNEL_BOUNDARY = (
    "Read-only closed paper trade funnel diagnostic. It cannot submit, close, "
    "cancel, resize, approve, or grant paper proof ledger credit."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings) -> Path:
    return Path(settings.runtime_dir)


def _read_runtime_json(settings: Settings, name: str) -> dict[str, Any]:
    path = _runtime_dir(settings) / name
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _paper_mirror_counts(settings: Settings) -> dict[str, Any]:
    try:
        store = PaperAccountMirrorStore(settings=settings)
        latest = store.latest_snapshot()
        positions = store.read_positions()
        closed_trades = store.read_closed_trades()
        orders = store.read_orders()
    except Exception as exc:  # noqa: BLE001 - diagnostics should degrade, not crash.
        return {
            "paper_mirror_status": "unavailable",
            "paper_mirror_error": exc.__class__.__name__,
            "paper_mirror_observed_at": None,
            "open_position_count": 0,
            "closed_paper_trade_count": 0,
            "paper_order_count": 0,
            "filled_order_count": 0,
            "open_order_count": 0,
        }
    order_status_counts: dict[str, int] = {}
    for order in orders:
        status = str(order.status or "unknown").lower()
        order_status_counts[status] = order_status_counts.get(status, 0) + 1
    return {
        "paper_mirror_status": "ok",
        "paper_mirror_error": None,
        "paper_mirror_observed_at": latest.observed_at if latest else None,
        "open_position_count": len(positions),
        "closed_paper_trade_count": len(closed_trades),
        "paper_order_count": len(orders),
        "filled_order_count": _int(order_status_counts.get("filled")),
        "open_order_count": sum(
            count
            for status, count in order_status_counts.items()
            if status in OPEN_ORDER_STATUSES
        ),
    }


def _stage(
    key: str,
    label: str,
    count: int,
    *,
    ready: bool,
    source_status: str | None = None,
    detail: str | None = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "ready": ready,
        "count": count,
        "source_status": source_status,
        "detail": detail,
    }


def _blocked_stage(stage_records: list[dict[str, Any]]) -> str | None:
    for record in stage_records:
        if record.get("ready") is not True:
            return str(record.get("key"))
    return None


def _status(blocked_stage: str | None) -> str:
    if blocked_stage is None:
        return "closed_trade_funnel_complete"
    return f"blocked_{blocked_stage}"


def _next_required_action(
    *,
    blocked_stage: str | None,
    exit_path: dict[str, Any],
    lifecycle_poller: dict[str, Any],
    close_to_ledger: dict[str, Any] | None = None,
) -> str:
    close_to_ledger = close_to_ledger or {}
    if blocked_stage == "setup":
        return "Wait for a distinct qualified paper setup."
    if blocked_stage == "submit":
        return "Submit the qualified setup only through the guarded Alpaca Paper route."
    if blocked_stage == "fill":
        return "Poll Alpaca paper order lifecycle until submitted paper orders fill."
    if blocked_stage == "open_position_readback":
        return "Refresh paper lifecycle polling and paper-account mirror readback."
    if blocked_stage == "exit_candidate":
        if exit_path.get("status") == "blocked_paper_position_preflight_readback_failed":
            return "Refresh current Alpaca Paper position readback before selecting an exit candidate."
        if _int(exit_path.get("suppressed_pending_close_request_exit_candidate_count")) >= 1:
            return "Wait for lifecycle refresh to confirm the guarded paper close before selecting another exit candidate."
        return "Build a guarded paper exit candidate from current open-position readback."
    if blocked_stage == "close_attempt":
        return "Run guarded PaperOps-4 paper close execution when explicitly enabled."
    if blocked_stage == "close_receipt":
        failure = _last_close_failure(exit_path)
        if failure:
            return f"Resolve guarded PaperOps-4 close failure before ledger credit: {failure}."
        return "Record a successful guarded Alpaca Paper close receipt."
    if blocked_stage == "lifecycle_mirror_freshness":
        return "Refresh PaperOps-3 lifecycle polling and the paper-account mirror after the guarded close receipt."
    if blocked_stage == "postmortem_marker":
        if close_to_ledger.get("status") == "blocked_research_goal_lineage_missing":
            return "Attach distinct Research Goal lineage before creating the latest guarded-close postmortem marker."
        if close_to_ledger.get("status") == "waiting_lifecycle_mirror_refresh":
            return "Refresh PaperOps-3 lifecycle polling and the paper-account mirror before creating the latest guarded-close postmortem marker."
        return "Create the postmortem due marker after verified paper close receipt."
    if blocked_stage == "paper_proof_ledger_credit":
        if close_to_ledger.get("status") != "paper_proof_ledger_recorded":
            return "Record the latest guarded close in the paper proof ledger only after verified close, fresh lifecycle/mirror state, lineage, and postmortem marker evidence."
        return "Credit the paper proof ledger only after verified close and postmortem evidence."
    if lifecycle_poller.get("status") in {"not_run", "ready_pending_explicit_poll"}:
        return "Run paper lifecycle polling to refresh the funnel."
    return "Closed paper trade funnel is complete for the current verified record set."


def _last_close_failure(exit_path: dict[str, Any]) -> str | None:
    records = exit_path.get("selected_exit_records")
    if not isinstance(records, list) or not records:
        return None
    if any(
        isinstance(record, dict)
        and (
            record.get("status") == "paper_exit_close_recorded"
            or record.get("paper_position_close_succeeded") is True
        )
        for record in records
    ):
        return None
    record = next((item for item in records if isinstance(item, dict)), None)
    if not isinstance(record, dict):
        return None
    failure_class = str(record.get("broker_failure_class") or "").strip()
    http_status = record.get("sanitized_http_status")
    if failure_class and http_status:
        if failure_class == f"http_{http_status}":
            return failure_class
        return f"{failure_class} http_{http_status}"
    if failure_class:
        return failure_class
    if http_status:
        return f"http_{http_status}"
    return None


def build_paperops_closed_trade_funnel(
    settings: Settings | None = None,
    *,
    generated_at: str | None = None,
    paper_runtime: dict[str, Any] | None = None,
    paper_proof_ledger: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated = generated_at or _now()
    runtime = paper_runtime or {}
    proof = paper_proof_ledger or {}
    mirror = _paper_mirror_counts(settings)
    paperops_30_day = _read_runtime_json(settings, "paperops_30_day_operations.json")
    paperops_2 = _read_runtime_json(settings, "paperops_alpaca_paper_post.json")
    paperops_3 = _read_runtime_json(settings, "paperops_paper_lifecycle_poller.json")
    paperops_7 = _read_runtime_json(settings, "paperops_guarded_paper_exit_enablement.json")
    paperops_4 = _read_runtime_json(settings, "paperops_paper_exit_path.json")
    postmortem = _read_runtime_json(settings, "paper_lifecycle_portfolio_postmortem.json")
    freshness = build_paperops_lifecycle_mirror_freshness(
        settings=settings,
        exit_path=paperops_4,
        lifecycle_poller=paperops_3,
        generated_at=generated,
    )
    close_to_ledger = build_paperops_close_to_ledger(
        settings=settings,
        exit_path=paperops_4,
        lifecycle_poller=paperops_3,
        generated_at=generated,
    )

    qualified_setup_count = max(
        _int(proof.get("qualified_setup_count")),
        _int(paperops_30_day.get("qualified_setup_count")),
    )
    submitted_paper_order_count = max(
        _int(runtime.get("submitted_paper_order_count")),
        _int(proof.get("submitted_paper_order_count")),
        _int(paperops_30_day.get("submitted_paper_order_count")),
        _int(paperops_2.get("alpaca_paper_post_succeeded_count")),
    )
    filled_order_count = max(
        _int(mirror.get("filled_order_count")),
        _int((runtime.get("order_status_counts") or {}).get("filled"))
        if isinstance(runtime.get("order_status_counts"), dict)
        else 0,
        _int(paperops_3.get("paper_order_poll_succeeded_count")),
    )
    open_position_readback_count = max(
        _int(runtime.get("open_position_count")),
        _int(mirror.get("open_position_count")),
        _int(paperops_3.get("open_position_count")),
        _int(paperops_7.get("paperops_3_open_position_count")),
        _int(paperops_4.get("open_position_readback_count")),
    )
    eligible_exit_record_count = _int(paperops_4.get("eligible_exit_record_count"))
    latest_close_receipt_present = bool(
        freshness.get("latest_successful_close_requested_at")
    )
    close_attempt_count = max(
        _int(paperops_4.get("paper_position_close_called_count")),
        1 if latest_close_receipt_present else 0,
    )
    close_receipt_count = max(
        _int(paperops_4.get("paper_position_close_succeeded_count")),
        _int(paperops_4.get("broker_close_receipt_created_count")),
        1 if latest_close_receipt_present else 0,
    )
    lifecycle_mirror_freshness_count = (
        1
        if close_receipt_count < 1
        or freshness.get("fresh_after_latest_close") is True
        else 0
    )
    postmortem_marker_count = _int(
        close_to_ledger.get("postmortem_due_marker_created_count")
    )
    closed_proof_trade_count = _int(close_to_ledger.get("closed_proof_trade_count"))

    stage_records = [
        _stage(
            "setup",
            "Qualified paper setup",
            qualified_setup_count,
            ready=qualified_setup_count > 0,
            source_status=str(paperops_30_day.get("status") or "missing"),
        ),
        _stage(
            "submit",
            "Guarded Alpaca Paper submit",
            submitted_paper_order_count,
            ready=submitted_paper_order_count > 0,
            source_status=str(paperops_2.get("status") or "missing"),
        ),
        _stage(
            "fill",
            "Paper order fill",
            filled_order_count,
            ready=filled_order_count > 0,
            source_status=str(paperops_3.get("status") or "missing"),
        ),
        _stage(
            "open_position_readback",
            "Open-position readback",
            open_position_readback_count,
            ready=open_position_readback_count > 0,
            source_status=str(paperops_7.get("status") or "missing"),
        ),
        _stage(
            "exit_candidate",
            "Guarded paper exit candidate",
            eligible_exit_record_count,
            ready=eligible_exit_record_count > 0,
            source_status=str(paperops_4.get("status") or "missing"),
        ),
        _stage(
            "close_attempt",
            "Guarded paper close attempt",
            close_attempt_count,
            ready=close_attempt_count > 0,
            source_status=str(paperops_4.get("status") or "missing"),
        ),
        _stage(
            "close_receipt",
            "Guarded paper close receipt",
            close_receipt_count,
            ready=close_receipt_count > 0,
            source_status=str(paperops_4.get("status") or "missing"),
            detail=_last_close_failure(paperops_4),
        ),
        _stage(
            "lifecycle_mirror_freshness",
            "Lifecycle and mirror freshness",
            lifecycle_mirror_freshness_count,
            ready=lifecycle_mirror_freshness_count > 0,
            source_status=str(freshness.get("status") or "missing"),
            detail=freshness.get("latest_successful_close_requested_at"),
        ),
        _stage(
            "postmortem_marker",
            "Postmortem due marker",
            postmortem_marker_count,
            ready=postmortem_marker_count > 0,
            source_status=str(postmortem.get("status") or "missing"),
        ),
        _stage(
            "paper_proof_ledger_credit",
            "Paper proof ledger credit",
            closed_proof_trade_count,
            ready=closed_proof_trade_count > 0,
            source_status=str(paperops_30_day.get("status") or "missing"),
        ),
    ]
    blocked_stage = _blocked_stage(stage_records)
    status = _status(blocked_stage)

    return {
        "schema_version": PAPEROPS_CLOSED_TRADE_FUNNEL_SCHEMA_VERSION,
        "artifact_type": "paperops_closed_trade_funnel",
        "artifact_id": "paperops:closed-trade-funnel:latest",
        "generated_at": generated,
        "public_safe": True,
        "status": status,
        "blocked_stage": blocked_stage,
        "next_required_action": _next_required_action(
            blocked_stage=blocked_stage,
            exit_path=paperops_4,
            lifecycle_poller=paperops_3,
            close_to_ledger=close_to_ledger,
        ),
        "counts": {
            "qualified_setup_count": qualified_setup_count,
            "submitted_paper_order_count": submitted_paper_order_count,
            "filled_order_count": filled_order_count,
            "open_position_readback_count": open_position_readback_count,
            "eligible_exit_record_count": eligible_exit_record_count,
            "paper_close_attempt_count": close_attempt_count,
            "paper_close_receipt_count": close_receipt_count,
            "lifecycle_mirror_freshness_count": lifecycle_mirror_freshness_count,
            "postmortem_marker_count": postmortem_marker_count,
            "closed_proof_trade_count": closed_proof_trade_count,
            "mirror_closed_paper_trade_count": max(
                _int(runtime.get("closed_paper_trade_count")),
                _int(mirror.get("closed_paper_trade_count")),
            ),
        },
        "source_statuses": {
            "paper_mirror": str(mirror.get("paper_mirror_status") or "missing"),
            "paper_mirror_observed_at": mirror.get("paper_mirror_observed_at"),
            "paperops_2_submit": str(paperops_2.get("status") or "missing"),
            "paperops_3_lifecycle": str(paperops_3.get("status") or "missing"),
            "paperops_7_exit_enablement": str(paperops_7.get("status") or "missing"),
            "paperops_4_exit_path": str(paperops_4.get("status") or "missing"),
            "paper_lifecycle_postmortem": str(postmortem.get("status") or "missing"),
            "paperops_30_day_operations": str(paperops_30_day.get("status") or "missing"),
            "paperops_lifecycle_mirror_freshness": str(
                freshness.get("status") or "missing"
            ),
            "paperops_close_to_ledger": str(close_to_ledger.get("status") or "missing"),
        },
        "lifecycle_mirror_freshness": freshness,
        "close_to_ledger": close_to_ledger,
        "latest_failure": {
            "stage": "close_receipt" if _last_close_failure(paperops_4) else None,
            "class": _last_close_failure(paperops_4),
            "paperops_4_status": paperops_4.get("status"),
        },
        "stage_records": stage_records,
        "live_capital_enabled": False,
        "live_endpoint_called_count": max(
            _int(paperops_2.get("live_endpoint_called_count")),
            _int(paperops_3.get("live_endpoint_called_count")),
            _int(paperops_4.get("live_endpoint_called_count")),
        ),
        "broker_post_called_count": max(
            _int(paperops_3.get("broker_post_called_count")),
            _int(paperops_4.get("broker_post_called_count")),
        ),
        "phase7_proof_credit_allowed": False,
        "boundary": PAPEROPS_CLOSED_TRADE_FUNNEL_BOUNDARY,
    }


def validate_paperops_closed_trade_funnel(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if artifact.get("schema_version") != PAPEROPS_CLOSED_TRADE_FUNNEL_SCHEMA_VERSION:
        errors.append("paperops_closed_trade_funnel_schema_version_mismatch")
    if artifact.get("artifact_type") != "paperops_closed_trade_funnel":
        errors.append("paperops_closed_trade_funnel_artifact_type_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("paperops_closed_trade_funnel_not_public_safe")
    if artifact.get("live_capital_enabled") is not False:
        errors.append("paperops_closed_trade_funnel_live_capital_enabled")
    if artifact.get("phase7_proof_credit_allowed") is not False:
        errors.append("paperops_closed_trade_funnel_proof_credit_allowed")
    if _int(artifact.get("live_endpoint_called_count")) != 0:
        errors.append("paperops_closed_trade_funnel_live_endpoint_called")
    if _int(artifact.get("broker_post_called_count")) != 0:
        errors.append("paperops_closed_trade_funnel_broker_post_called")
    close_to_ledger = artifact.get("close_to_ledger")
    if not isinstance(close_to_ledger, dict):
        errors.append("paperops_closed_trade_funnel_close_to_ledger_missing")
    else:
        for error in validate_paperops_close_to_ledger(close_to_ledger):
            errors.append(f"paperops_closed_trade_funnel_close_to_ledger:{error}")
    stage_records = artifact.get("stage_records")
    if not isinstance(stage_records, list) or len(stage_records) != 10:
        errors.append("paperops_closed_trade_funnel_stage_records_invalid")
    blocked_stage = artifact.get("blocked_stage")
    if blocked_stage is not None and not any(
        isinstance(record, dict) and record.get("key") == blocked_stage
        for record in stage_records or []
    ):
        errors.append("paperops_closed_trade_funnel_blocked_stage_unknown")
    return sorted(set(errors))
