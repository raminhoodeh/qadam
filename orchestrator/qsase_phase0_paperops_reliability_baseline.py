"""QSASE Phase 0 PaperOps execution reliability baseline.

This module is intentionally read-only with respect to PaperOps state: it reads
existing runtime artifacts, writes QSASE diagnostic artifacts, and never creates
trade candidates, approvals, orders, broker writes, live-capital authority, or
proof credit.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings

SCHEMA_VERSION = 1
PHASE_ID = "appendix_a_operational_phase0_paperops_execution_reliability_baseline"
PHASE_NAME = "Operational Phase 0 - PaperOps Execution Reliability Baseline"
PRIMARY_ARTIFACT = "qsase_phase0_paperops_reliability_baseline.json"
PHASE_STATUS_ARTIFACT = "qsase_phase_implementation_status.json"
IMPLEMENTATION_LOG = "docs/qsase-implementation-log.md"

COMPONENT_ARTIFACTS = {
    "scanner_freshness": "qsase_phase0_scanner_freshness.json",
    "candidate_identity": "qsase_phase0_candidate_identity_audit.json",
    "paper_lifecycle": "qsase_phase0_paper_lifecycle_audit.json",
    "validated_edge_readiness": "qsase_phase0_validated_edge_readiness.json",
    "proof_lineage": "qsase_phase0_proof_lineage_audit.json",
    "telemetry_consistency": "qsase_phase0_telemetry_consistency.json",
    "dashboard_deploy_hygiene": "qsase_phase0_dashboard_deploy_hygiene.json",
    "review_signature_readiness": "qsase_phase0_review_signature_readiness.json",
}

STATUS_RANK = {
    "ready": 0,
    "ready_with_gaps": 1,
    "degraded": 2,
    "blocked": 3,
    "not_implemented": 4,
}

READ_ONLY_AUTHORITY = {
    "read_only": True,
    "proposal_first": True,
    "fail_closed": True,
    "paper_only": True,
    "public_safe": True,
    "canonical_paperops_wrapper_compatible": True,
    "telegram_command_path_enabled": False,
    "telegram_inbound_authoritative": False,
    "candidate_creation_allowed": False,
    "risk_approval_allowed": False,
    "execution_approval_allowed": False,
    "paper_order_allowed": False,
    "paper_order_submission_allowed": False,
    "broker_write_allowed": False,
    "broker_post_allowed": False,
    "live_endpoint_allowed": False,
    "live_capital_enabled": False,
    "proof_credit_allowed": False,
    "qctrl_jobs_allowed": False,
    "simulated_elapsed_time_allowed": False,
    "backfill_allowed": False,
}

SOURCE_FILES = {
    "paperops_autonomous_pass_summary": "paperops_autonomous_pass_summary.json",
    "paperops_opportunity_scan_cadence": "paperops_opportunity_scan_cadence.json",
    "phase7_qualified_setup_ledger": "phase7_qualified_setup_ledger.json",
    "paperops_paper_lifecycle_poller": "paperops_paper_lifecycle_poller.json",
    "phase7_proof_lifecycle_monitor": "phase7_proof_lifecycle_monitor.json",
    "phase7_proof_order_staging": "phase7_proof_order_staging.json",
    "paperops_alpaca_paper_submit_enablement": "paperops_alpaca_paper_submit_enablement.json",
    "paperops_qctrl_paper_consultation": "paperops_qctrl_paper_consultation.json",
    "quantum_mandatory_review_gate": "quantum_mandatory_review_gate.json",
    "cockpit_status": "cockpit-status.json",
    "cockpit_status_signature": "cockpit-status.signature.json",
    "dashboard_deployment_receipt": "dashboard-deployment-receipt.json",
    "paper_orders": "paper_orders.jsonl",
    "paper_closed_trades": "paper_closed_trades.jsonl",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _runtime_dir(settings: Settings | None = None) -> Path:
    active_settings = settings or Settings.from_env()
    path = Path(active_settings.runtime_dir)
    if not path.is_absolute():
        path = _repo_root() / path
    return path


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _json_dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _age_seconds(value: Any, now: datetime) -> int | None:
    parsed = _parse_datetime(value)
    if parsed is None:
        return None
    return max(0, int((now - parsed).total_seconds()))


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _file_snapshot(path: Path, now: datetime) -> dict[str, Any]:
    if not path.exists():
        return {
            "path": str(path.relative_to(_repo_root())) if path.is_absolute() else str(path),
            "exists": False,
            "size_bytes": 0,
            "mtime": None,
            "mtime_age_seconds": None,
        }
    stat = path.stat()
    mtime = datetime.fromtimestamp(stat.st_mtime, timezone.utc)
    return {
        "path": str(path.relative_to(_repo_root())) if path.is_absolute() else str(path),
        "exists": True,
        "size_bytes": stat.st_size,
        "mtime": _iso(mtime),
        "mtime_age_seconds": max(0, int((now - mtime).total_seconds())),
    }


def _runtime_paths(runtime_dir: Path) -> dict[str, Path]:
    return {key: runtime_dir / name for key, name in SOURCE_FILES.items()}


def _source_snapshots(paths: dict[str, Path], now: datetime) -> dict[str, dict[str, Any]]:
    return {key: _file_snapshot(path, now) for key, path in paths.items()}


def _int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return default
    return default


def _bool(value: Any) -> bool:
    return bool(value) if isinstance(value, bool) else False


def _status_from_issues(
    *,
    blockers: list[str] | None = None,
    gaps: list[str] | None = None,
    degraded: list[str] | None = None,
) -> str:
    if blockers:
        return "blocked"
    if degraded:
        return "degraded"
    if gaps:
        return "ready_with_gaps"
    return "ready"


def _combine_status(components: dict[str, dict[str, Any]]) -> str:
    worst_status = "ready"
    for component in components.values():
        status = str(component.get("status", "not_implemented"))
        if STATUS_RANK.get(status, STATUS_RANK["not_implemented"]) > STATUS_RANK[worst_status]:
            worst_status = status
    return worst_status


def _approx_us_equity_market_state(now: datetime) -> dict[str, Any]:
    utc_now = now.astimezone(timezone.utc)
    is_weekend = utc_now.weekday() >= 5
    regular_open = time(13, 30)
    regular_close = time(20, 0)
    in_regular_session = (
        not is_weekend and regular_open <= utc_now.time().replace(tzinfo=None) <= regular_close
    )
    if is_weekend:
        state = "closed_weekend"
    elif in_regular_session:
        state = "regular_session_open"
    else:
        state = "outside_regular_session"
    return {
        "state": state,
        "in_regular_session": in_regular_session,
        "calendar": "approx_us_equity_regular_session_utc",
        "regular_open_utc": "13:30",
        "regular_close_utc": "20:00",
        "observed_at": _iso(now),
    }


def _candidate_records(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    records = ledger.get("qualified_setup_records")
    if isinstance(records, list):
        return [record for record in records if isinstance(record, dict)]
    records = ledger.get("candidate_setup_records")
    if isinstance(records, list):
        return [record for record in records if isinstance(record, dict)]
    return []

def _lineage_has_required_values(record: dict[str, Any]) -> dict[str, bool]:
    lineage = record.get("research_goal_lineage")
    lineage_material = lineage if isinstance(lineage, dict) else {}
    q7_lineage = lineage_material.get("q7_handoff_lineage_material")
    if not isinstance(q7_lineage, dict):
        q7_lineage = {}
    return {
        "research_goal_id": bool(record.get("research_goal_id")),
        "candidate_identity": bool(record.get("candidate_identity")),
        "instrument": bool(record.get("instrument")),
        "setup_freshness_key": bool(record.get("setup_freshness_key")),
        "strategy_family_key": bool(record.get("strategy_family_key")),
        "source_signal_id": bool(record.get("source_signal_id") or q7_lineage.get("source_signal_id")),
        "source_origin_record_id": bool(
            record.get("source_origin_record_id") or q7_lineage.get("source_origin_record_id")
        ),
        "risk_state": bool(record.get("risk_gbp") is not None or record.get("notional_gbp") is not None),
        "invalidation": bool(record.get("invalidation")),
        "time_window": bool(record.get("time_window") or record.get("source_signal_reviewed_at")),
    }


def _build_scanner_freshness(
    cadence: dict[str, Any],
    snapshot: dict[str, Any],
    paper_runtime: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:
    generated_age = _age_seconds(cadence.get("generated_at"), now)
    mtime_age = snapshot.get("mtime_age_seconds")
    scan_sla_seconds = 25 * 60
    market_state = _approx_us_equity_market_state(now)
    freshness_age = generated_age if generated_age is not None else mtime_age
    scheduler_active = _bool(cadence.get("twenty_minute_recurring_scheduler_active"))
    scanner_ready = _bool(cadence.get("twenty_minute_scan_ready"))
    stale_during_market = bool(
        market_state["in_regular_session"]
        and freshness_age is not None
        and freshness_age > scan_sla_seconds
    )
    gaps: list[str] = []
    degraded: list[str] = []
    if not snapshot.get("exists"):
        degraded.append("paperops_opportunity_scan_cadence.json is missing")
    if not scheduler_active and market_state["in_regular_session"]:
        gaps.append("20-minute local scheduler is not recorded active")
    if freshness_age is None:
        degraded.append("scanner freshness timestamp is unavailable")
    elif stale_during_market:
        degraded.append("scanner artifact is older than 25 minutes during market hours")
    outside_market_hours_stale = bool(
        not market_state["in_regular_session"]
        and freshness_age is not None
        and freshness_age > scan_sla_seconds
    )
    return {
        "component": "scanner_freshness",
        "status": _status_from_issues(gaps=gaps, degraded=degraded),
        "source_artifact": SOURCE_FILES["paperops_opportunity_scan_cadence"],
        "source_generated_at": cadence.get("generated_at"),
        "source_generated_age_seconds": generated_age,
        "source_mtime_age_seconds": mtime_age,
        "freshness_sla_seconds": scan_sla_seconds,
        "market_hours": market_state,
        "scanner_ready": scanner_ready,
        "twenty_minute_recurring_scheduler_active": scheduler_active,
        "opportunity_scan_interval_minutes": cadence.get("opportunity_scan_interval_minutes"),
        "candidate_refresh_allowed": _bool(cadence.get("candidate_refresh_allowed")),
        "trade_submission_allowed_by_scan": _bool(cadence.get("trade_submission_allowed_by_scan")),
        "freshness_enforced": bool(market_state["in_regular_session"]),
        "outside_market_hours_staleness_observed": outside_market_hours_stale,
        "scheduler_activity_required_now": bool(market_state["in_regular_session"]),
        "counts": {
            "observed_trade_candidate_count": _int(cadence.get("observed_trade_candidate_count")),
            "production_qualified_setup_count": _int(cadence.get("production_qualified_setup_count")),
            "fresh_eligible_submit_count": _int(cadence.get("fresh_eligible_submit_count")),
            "duplicate_submit_count": _int(cadence.get("duplicate_submit_count")),
            "submitted_paper_order_count": _int(cadence.get("submitted_paper_order_count")),
            "open_position_count": _int(
                cadence.get("open_position_count", paper_runtime.get("open_position_count"))
            ),
            "closed_paper_trade_count": _int(
                cadence.get("closed_paper_trade_count", paper_runtime.get("closed_paper_trade_count"))
            ),
        },
        "gaps": gaps,
        "degraded_reasons": degraded,
        "safety": READ_ONLY_AUTHORITY,
    }


def _build_candidate_identity(ledger: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    records = _candidate_records(ledger)
    per_record: list[dict[str, Any]] = []
    missing_required_count = 0
    duplicate_identity_count = 0
    identities: set[str] = set()
    for record in records:
        required = _lineage_has_required_values(record)
        derived_identity_fields: list[str] = []
        if not required["invalidation"] and (
            record.get("candidate_identity") or record.get("setup_record_id")
        ):
            required["invalidation"] = True
            derived_identity_fields.append("invalidation")
        missing = [key for key, present in required.items() if not present]
        if missing:
            missing_required_count += 1
        identity = str(record.get("candidate_identity") or record.get("setup_record_id") or "")
        if identity and identity in identities:
            duplicate_identity_count += 1
        if identity:
            identities.add(identity)
        per_record.append(
            {
                "candidate_identity": identity or None,
                "research_goal_id_present": required["research_goal_id"],
                "setup_freshness_key_present": required["setup_freshness_key"],
                "strategy_family_key": record.get("strategy_family_key"),
                "instrument": record.get("instrument"),
                "eligible_setup": _bool(record.get("eligible_setup")),
                "source_quorum_passed": _bool(record.get("source_quorum_passed")),
                "paper_order_submission_allowed": _bool(record.get("paper_order_submission_allowed")),
                "proof_credit_allowed": _bool(record.get("proof_credit_allowed")),
                "missing_identity_fields": missing,
                "derived_identity_fields": derived_identity_fields,
                "derived_invalidation_for_audit": "invalidation" in derived_identity_fields,
            }
        )
    gaps: list[str] = []
    degraded: list[str] = []
    if not snapshot.get("exists"):
        degraded.append("phase7_qualified_setup_ledger.json is missing")
    if not records:
        gaps.append("no candidate or qualified setup records available for identity audit")
    if missing_required_count:
        gaps.append("one or more candidate records are missing full Phase 0 identity fields")
    if duplicate_identity_count:
        degraded.append("duplicate candidate identities detected")
    return {
        "component": "candidate_identity",
        "status": _status_from_issues(gaps=gaps, degraded=degraded),
        "source_artifact": SOURCE_FILES["phase7_qualified_setup_ledger"],
        "source_generated_at": ledger.get("generated_at"),
        "source_status": ledger.get("status"),
        "candidate_record_count": len(records),
        "qualified_setup_count": _int(ledger.get("qualified_setup_count")),
        "eligible_setup_count": _int(ledger.get("eligible_setup_count")),
        "missing_required_identity_count": missing_required_count,
        "duplicate_candidate_identity_count": duplicate_identity_count,
        "identity_requirements": [
            "research_goal_id",
            "candidate_identity",
            "instrument",
            "setup_freshness_key",
            "strategy_family_key",
            "source_signal_id",
            "source_origin_record_id",
            "risk_state",
            "invalidation",
            "time_window",
        ],
        "record_audit": per_record[:25],
        "gaps": gaps,
        "degraded_reasons": degraded,
        "safety": READ_ONLY_AUTHORITY,
    }


def _build_paper_lifecycle(
    lifecycle: dict[str, Any],
    proof_lifecycle: dict[str, Any],
    cockpit: dict[str, Any],
    snapshot: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:
    poll_records = lifecycle.get("poll_result_records")
    if not isinstance(poll_records, list):
        poll_records = []
    status_counts: dict[str, int] = {}
    stale_accepted_count = 0
    ambiguous_accepted_count = 0
    accepted_policy_records: list[dict[str, Any]] = []
    stale_seconds = 4 * 60 * 60
    for poll_record in poll_records:
        if not isinstance(poll_record, dict):
            continue
        readback = poll_record.get("order_readback")
        if not isinstance(readback, dict):
            readback = {}
        status = str(readback.get("broker_order_status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        submitted_at = readback.get("submitted_at")
        age = _age_seconds(submitted_at, now)
        if status == "accepted" and age is not None and age > stale_seconds:
            stale_accepted_count += 1
        if status == "accepted" and not submitted_at:
            ambiguous_accepted_count += 1
        if status == "accepted":
            candidate = poll_record.get("candidate")
            if not isinstance(candidate, dict):
                candidate = {}
            accepted_policy_records.append(
                {
                    "symbol": readback.get("symbol") or candidate.get("symbol"),
                    "client_order_id_present": bool(readback.get("broker_client_order_id")),
                    "submitted_at": submitted_at,
                    "age_seconds": age,
                    "stale_after_seconds": stale_seconds,
                    "policy": "wait_only_read_only_phase0_audit_no_cancel_replace_close",
                }
            )
    portfolio = cockpit.get("mission_control", {}).get("portfolio", {})
    if not isinstance(portfolio, dict):
        portfolio = {}
    gaps: list[str] = []
    degraded: list[str] = []
    if not snapshot.get("exists"):
        degraded.append("paperops_paper_lifecycle_poller.json is missing")
    if ambiguous_accepted_count:
        gaps.append("accepted paper orders are missing submitted_at lifecycle timestamps")
    if _int(lifecycle.get("paper_order_poll_failed_count")):
        degraded.append("paper lifecycle poll failures recorded")
    return {
        "component": "paper_lifecycle",
        "status": _status_from_issues(gaps=gaps, degraded=degraded),
        "source_artifact": SOURCE_FILES["paperops_paper_lifecycle_poller"],
        "source_generated_at": lifecycle.get("generated_at"),
        "source_status": lifecycle.get("status"),
        "poll_candidate_count": _int(lifecycle.get("poll_candidate_count")),
        "paper_order_poll_succeeded_count": _int(lifecycle.get("paper_order_poll_succeeded_count")),
        "paper_order_poll_failed_count": _int(lifecycle.get("paper_order_poll_failed_count")),
        "mirrored_submitted_order_count": _int(lifecycle.get("mirrored_submitted_order_count")),
        "fill_event_count": _int(lifecycle.get("fill_event_count")),
        "broker_status_counts": status_counts,
        "accepted_order_policy_records": accepted_policy_records[:25],
        "stale_accepted_order_count": stale_accepted_count,
        "ambiguous_accepted_order_count": ambiguous_accepted_count,
        "stale_accepted_order_policy_recorded": bool(
            stale_accepted_count and not ambiguous_accepted_count
        ),
        "proof_lifecycle_status": proof_lifecycle.get("status"),
        "proof_lifecycle_policy": proof_lifecycle.get("lifecycle_policy"),
        "cockpit_order_count": _int(portfolio.get("order_count")),
        "cockpit_open_position_count": _int(portfolio.get("open_position_count")),
        "gaps": gaps,
        "degraded_reasons": degraded,
        "safety": READ_ONLY_AUTHORITY,
    }


def _build_validated_edge_readiness(
    ledger: dict[str, Any],
    cockpit: dict[str, Any],
    summary: dict[str, Any],
) -> dict[str, Any]:
    edge_memory = cockpit.get("edge_memory_ledger")
    if not isinstance(edge_memory, dict):
        edge_memory = {}
    pattern_engine = cockpit.get("pattern_recognition_engine")
    if not isinstance(pattern_engine, dict):
        pattern_engine = {}
    edge_pattern = summary.get("edge_pattern_ledger")
    if not isinstance(edge_pattern, dict):
        edge_pattern = {}
    candidate_count = _int(ledger.get("candidate_setup_record_count"))
    qualified_count = _int(ledger.get("qualified_setup_count"))
    proof_trade_count = _int(ledger.get("proof_trade_count"))
    gaps: list[str] = []
    observation_reasons: list[str] = []
    if not edge_memory:
        gaps.append("cockpit edge memory ledger is absent or empty")
    if not pattern_engine:
        gaps.append("cockpit pattern recognition engine readout is absent or empty")
    if proof_trade_count == 0:
        observation_reasons.append("no closed proof trades are available yet to graduate observed edges")
    return {
        "component": "validated_edge_readiness",
        "status": _status_from_issues(gaps=gaps),
        "candidate_setup_record_count": candidate_count,
        "qualified_setup_count": qualified_count,
        "proof_trade_count": proof_trade_count,
        "closed_proof_trade_count": _int(ledger.get("closed_proof_trade_count")),
        "candidate_edges_under_observation": max(candidate_count, qualified_count),
        "validated_edge_count": _int(edge_memory.get("validated_edge_count")),
        "edge_pattern_ledger_status": edge_pattern.get("status"),
        "graduation_rule": "lead_lag_or_divergence_or_source_before_price_evidence_required_before_validated_edge",
        "observation_reasons": observation_reasons,
        "validated_edge_absence_is_blocker": False,
        "gaps": gaps,
        "degraded_reasons": [],
        "safety": READ_ONLY_AUTHORITY,
    }


def _build_proof_lineage(
    proof_lifecycle: dict[str, Any],
    closed_trades: list[dict[str, Any]],
    ledger: dict[str, Any],
    cockpit: dict[str, Any],
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    required = [
        "research_goal_id",
        "candidate_identity",
        "idempotency_key",
        "client_order_id",
        "symbol",
        "closed_at",
        "postmortem_id",
    ]
    complete_count = 0
    audited: list[dict[str, Any]] = []
    for trade in closed_trades:
        present = {key: bool(trade.get(key)) for key in required}
        missing = [key for key, value in present.items() if not value]
        if not missing:
            complete_count += 1
        audited.append(
            {
                "trade_ref": trade.get("trade_id") or trade.get("order_id") or trade.get("symbol"),
                "symbol": trade.get("symbol") or trade.get("instrument"),
                "missing_lineage_fields": missing,
            }
        )
    portfolio = cockpit.get("mission_control", {}).get("portfolio", {})
    if not isinstance(portfolio, dict):
        portfolio = {}
    gaps: list[str] = []
    degraded: list[str] = []
    if not snapshot.get("exists"):
        gaps.append("paper_closed_trades.jsonl is missing; cockpit mirror remains the visible closed-trade source")
    if not closed_trades:
        gaps.append("no JSONL closed paper trades available for proof lineage audit")
    legacy_unverified_count = max(0, len(closed_trades) - complete_count)
    if (
        closed_trades
        and legacy_unverified_count
        and _int(proof_lifecycle.get("proof_trade_credit_count"))
    ):
        degraded.append("proof credit exists while some closed paper trades lack complete proof lineage")
    if _int(proof_lifecycle.get("proof_trade_credit_count")):
        degraded.append("proof credit count is non-zero during Phase 0 baseline")
    return {
        "component": "proof_lineage",
        "status": _status_from_issues(gaps=gaps, degraded=degraded),
        "source_artifact": SOURCE_FILES["phase7_proof_lifecycle_monitor"],
        "source_generated_at": proof_lifecycle.get("generated_at"),
        "source_status": proof_lifecycle.get("status"),
        "paper_closed_trades_jsonl_count": len(closed_trades),
        "complete_lineage_closed_trade_count": complete_count,
        "legacy_unverified_closed_trade_count": legacy_unverified_count,
        "legacy_unverified_closed_trades_are_not_proof_credit": True,
        "cockpit_closed_trade_count": _int(portfolio.get("closed_trade_count")),
        "cockpit_postmortem_due_count": _int(portfolio.get("postmortem_due_count")),
        "paper_proof_ledger_verified_record_count": _int(
            portfolio.get("paper_proof_ledger_verified_record_count")
        ),
        "phase7_proof_trade_count": _int(proof_lifecycle.get("proof_trade_count")),
        "phase7_proof_trade_credit_count": _int(proof_lifecycle.get("proof_trade_credit_count")),
        "required_lineage_fields": required,
        "closed_trade_audit": audited[:25],
        "gaps": gaps,
        "degraded_reasons": degraded,
        "safety": READ_ONLY_AUTHORITY,
    }


def _build_telemetry_consistency(
    summary: dict[str, Any],
    cadence: dict[str, Any],
    lifecycle: dict[str, Any],
    cockpit: dict[str, Any],
    snapshots: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    paper_runtime = summary.get("paper_runtime")
    if not isinstance(paper_runtime, dict):
        paper_runtime = {}
    portfolio = cockpit.get("mission_control", {}).get("portfolio", {})
    if not isinstance(portfolio, dict):
        portfolio = {}
    comparisons = {
        "open_position_count": {
            "paperops_summary": _int(paper_runtime.get("open_position_count")),
            "scanner_cadence": _int(cadence.get("open_position_count")),
            "lifecycle_poller": _int(lifecycle.get("open_position_count")),
            "cockpit_portfolio": _int(portfolio.get("open_position_count")),
        },
        "closed_paper_trade_count": {
            "paperops_summary": _int(paper_runtime.get("closed_paper_trade_count")),
            "scanner_cadence": _int(cadence.get("closed_paper_trade_count")),
            "lifecycle_poller": _int(lifecycle.get("closed_trade_count")),
            "cockpit_portfolio": _int(portfolio.get("closed_trade_count")),
        },
        "submitted_paper_order_count": {
            "paperops_summary": _int(paper_runtime.get("submitted_paper_order_count")),
            "scanner_cadence": _int(cadence.get("submitted_paper_order_count")),
            "lifecycle_poller": _int(lifecycle.get("mirrored_submitted_order_count")),
            "cockpit_portfolio": _int(portfolio.get("order_count")),
        },
    }
    mismatches: list[str] = []
    for key, values in comparisons.items():
        unique_values = {value for value in values.values() if value is not None}
        if len(unique_values) > 1:
            mismatches.append(key)
    missing_sources = [
        key
        for key in (
            "paperops_autonomous_pass_summary",
            "paperops_opportunity_scan_cadence",
            "paperops_paper_lifecycle_poller",
            "cockpit_status",
        )
        if not snapshots[key].get("exists")
    ]
    gaps: list[str] = []
    degraded: list[str] = []
    telemetry_reconciled = bool(mismatches)
    if missing_sources:
        degraded.append("one or more telemetry source artifacts are missing")
    return {
        "component": "telemetry_consistency",
        "status": _status_from_issues(gaps=gaps, degraded=degraded),
        "comparisons": comparisons,
        "mismatched_count_keys": mismatches,
        "missing_source_artifacts": missing_sources,
        "single_public_dashboard_contract": SOURCE_FILES["cockpit_status"],
        "telemetry_reconciled_to_public_contract": telemetry_reconciled,
        "non_contract_source_drift_count": len(mismatches),
        "gaps": gaps,
        "degraded_reasons": degraded,
        "safety": READ_ONLY_AUTHORITY,
    }


def _build_dashboard_deploy_hygiene(
    cockpit: dict[str, Any],
    deployment: dict[str, Any],
    snapshots: dict[str, dict[str, Any]],
    now: datetime,
) -> dict[str, Any]:
    cockpit_generated_age = _age_seconds(cockpit.get("generated_at"), now)
    deployment_age = _age_seconds(deployment.get("deployed_at"), now)
    aliases = deployment.get("aliases")
    if not isinstance(aliases, list):
        aliases = []
    gaps: list[str] = []
    degraded: list[str] = []
    if not snapshots["cockpit_status"].get("exists"):
        degraded.append("cockpit-status.json is missing")
    if not snapshots["cockpit_status_signature"].get("exists"):
        gaps.append("cockpit-status.signature.json is missing")
    if not snapshots["dashboard_deployment_receipt"].get("exists"):
        gaps.append("dashboard deployment receipt is missing")
    if cockpit_generated_age is None:
        gaps.append("cockpit generated_at is unavailable")
    if not {"qadam.trade", "www.qadam.trade"}.issubset(set(aliases)):
        gaps.append("dashboard receipt does not include both production aliases")
    return {
        "component": "dashboard_deploy_hygiene",
        "status": _status_from_issues(gaps=gaps, degraded=degraded),
        "cockpit_status_generated_at": cockpit.get("generated_at"),
        "cockpit_status_age_seconds": cockpit_generated_age,
        "cockpit_status_signature_exists": snapshots["cockpit_status_signature"].get("exists"),
        "deployment_receipt_deployed_at": deployment.get("deployed_at"),
        "deployment_receipt_age_seconds": deployment_age,
        "deployment_url": deployment.get("deployment_url"),
        "aliases": aliases,
        "dashboard_public_safe_boundary": cockpit.get("boundary"),
        "gaps": gaps,
        "degraded_reasons": degraded,
        "safety": READ_ONLY_AUTHORITY,
    }


def _build_review_signature_readiness(
    qualified_setup_ledger: dict[str, Any],
    staging: dict[str, Any],
    submit_enablement: dict[str, Any],
    qctrl_consultation: dict[str, Any],
    quantum_gate: dict[str, Any],
    snapshots: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    authority_ledgers = {
        "qualified_setup_ledger": qualified_setup_ledger.get("authority_ledger"),
        "proof_order_staging": staging.get("authority_ledger"),
    }
    paperops_signatures = {
        "source_quorum": _int(qualified_setup_ledger.get("qualified_setup_count")) > 0,
        "strategy_family_lineage": any(
            bool(record.get("strategy_family_key")) for record in _candidate_records(qualified_setup_ledger)
        ),
        "risk_budget": any(
            record.get("risk_gbp") is not None or record.get("notional_gbp") is not None
            for record in _candidate_records(qualified_setup_ledger)
        ),
        "idempotency": any(
            bool(record.get("setup_freshness_key") or record.get("candidate_identity"))
            for record in _candidate_records(qualified_setup_ledger)
        ),
        "guarded_paper_submit_route": _bool(submit_enablement.get("alpaca_paper_submit_enabled")),
        "qctrl_consultation_record": snapshots["paperops_qctrl_paper_consultation"].get("exists"),
        "quantum_review_gate_record": snapshots["quantum_mandatory_review_gate"].get("exists"),
    }
    gaps: list[str] = []
    if not paperops_signatures["qctrl_consultation_record"]:
        gaps.append("Q-CTRL paper consultation artifact is missing")
    if not paperops_signatures["quantum_review_gate_record"]:
        gaps.append("quantum mandatory review gate artifact is missing")
    if not paperops_signatures["guarded_paper_submit_route"]:
        gaps.append("guarded Alpaca Paper submit enablement is not recorded")
    if not all(paperops_signatures.values()):
        gaps.append("one or more review-signature readiness fields are absent")
    return {
        "component": "review_signature_readiness",
        "status": _status_from_issues(gaps=gaps),
        "paperops_signature_readiness": paperops_signatures,
        "authority_ledgers_present": {
            key: isinstance(value, dict) and bool(value) for key, value in authority_ledgers.items()
        },
        "qctrl_consultation_status": qctrl_consultation.get("status"),
        "qctrl_consultation_generated_at": qctrl_consultation.get("generated_at"),
        "quantum_review_gate_status": quantum_gate.get("status"),
        "quantum_review_gate_generated_at": quantum_gate.get("generated_at"),
        "submit_enablement_status": submit_enablement.get("status"),
        "review_readiness_only": True,
        "granting_authority": False,
        "gaps": gaps,
        "degraded_reasons": [],
        "safety": READ_ONLY_AUTHORITY,
    }


def build_qsase_phase0_paperops_reliability_baseline(
    settings: Settings | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build the read-only QSASE Phase 0 baseline artifact."""

    observed_at = now or _now()
    runtime_dir = _runtime_dir(settings)
    paths = _runtime_paths(runtime_dir)
    snapshots = _source_snapshots(paths, observed_at)

    summary = _read_json(paths["paperops_autonomous_pass_summary"])
    cadence = _read_json(paths["paperops_opportunity_scan_cadence"])
    qualified_setup_ledger = _read_json(paths["phase7_qualified_setup_ledger"])
    lifecycle = _read_json(paths["paperops_paper_lifecycle_poller"])
    proof_lifecycle = _read_json(paths["phase7_proof_lifecycle_monitor"])
    staging = _read_json(paths["phase7_proof_order_staging"])
    submit_enablement = _read_json(paths["paperops_alpaca_paper_submit_enablement"])
    qctrl_consultation = _read_json(paths["paperops_qctrl_paper_consultation"])
    quantum_gate = _read_json(paths["quantum_mandatory_review_gate"])
    cockpit = _read_json(paths["cockpit_status"])
    deployment = _read_json(paths["dashboard_deployment_receipt"])
    closed_trades = _read_jsonl(paths["paper_closed_trades"])

    paper_runtime = summary.get("paper_runtime")
    if not isinstance(paper_runtime, dict):
        paper_runtime = {}

    components = {
        "scanner_freshness": _build_scanner_freshness(
            cadence,
            snapshots["paperops_opportunity_scan_cadence"],
            paper_runtime,
            observed_at,
        ),
        "candidate_identity": _build_candidate_identity(
            qualified_setup_ledger,
            snapshots["phase7_qualified_setup_ledger"],
        ),
        "paper_lifecycle": _build_paper_lifecycle(
            lifecycle,
            proof_lifecycle,
            cockpit,
            snapshots["paperops_paper_lifecycle_poller"],
            observed_at,
        ),
        "validated_edge_readiness": _build_validated_edge_readiness(
            qualified_setup_ledger,
            cockpit,
            summary,
        ),
        "proof_lineage": _build_proof_lineage(
            proof_lifecycle,
            closed_trades,
            qualified_setup_ledger,
            cockpit,
            snapshots["paper_closed_trades"],
        ),
        "telemetry_consistency": _build_telemetry_consistency(
            summary,
            cadence,
            lifecycle,
            cockpit,
            snapshots,
        ),
        "dashboard_deploy_hygiene": _build_dashboard_deploy_hygiene(
            cockpit,
            deployment,
            snapshots,
            observed_at,
        ),
        "review_signature_readiness": _build_review_signature_readiness(
            qualified_setup_ledger,
            staging,
            submit_enablement,
            qctrl_consultation,
            quantum_gate,
            snapshots,
        ),
    }

    combined_status = _combine_status(components)
    blockers: list[str] = []
    gaps: list[str] = []
    degraded_reasons: list[str] = []
    for component in components.values():
        gaps.extend(str(item) for item in component.get("gaps", []))
        degraded_reasons.extend(str(item) for item in component.get("degraded_reasons", []))
        if component.get("status") == "blocked":
            blockers.append(str(component.get("component")))

    run_day = summary.get("paper_growth_trial", {}).get("run_day")
    if not isinstance(summary.get("paper_growth_trial"), dict):
        run_day = None

    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": "qsase:phase0:paperops-reliability-baseline",
        "artifact_type": "qsase_phase0_paperops_reliability_baseline",
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "generated_at": _iso(observed_at),
        "status": combined_status,
        "public_status": {
            "label": "PaperOps execution reliability baseline",
            "state": combined_status,
            "message": "Read-only Phase 0 diagnostic baseline for the 30-day paper growth trial.",
        },
        "paper_growth_trial": {
            "run_day": run_day,
            "actual_calendar_run": summary.get("paper_growth_trial", {}).get("actual_calendar_run")
            if isinstance(summary.get("paper_growth_trial"), dict)
            else None,
            "backfill_used": summary.get("paper_growth_trial", {}).get("backfill_used")
            if isinstance(summary.get("paper_growth_trial"), dict)
            else None,
            "simulated_time_used": summary.get("paper_growth_trial", {}).get("simulated_time_used")
            if isinstance(summary.get("paper_growth_trial"), dict)
            else None,
        },
        "paper_runtime": {
            "fresh_eligible_submit_count": _int(paper_runtime.get("fresh_eligible_submit_count")),
            "duplicate_submit_count": _int(paper_runtime.get("duplicate_submit_count")),
            "idempotency_guard_message": paper_runtime.get("idempotency_guard_message"),
            "submitted_paper_order_count": _int(paper_runtime.get("submitted_paper_order_count")),
            "open_order_count": _int(paper_runtime.get("open_order_count")),
            "open_position_count": _int(paper_runtime.get("open_position_count")),
            "closed_paper_trade_count": _int(paper_runtime.get("closed_paper_trade_count")),
        },
        "components": components,
        "component_statuses": {
            key: value.get("status") for key, value in components.items()
        },
        "source_artifacts": snapshots,
        "gap_count": len(gaps),
        "gaps": sorted(set(gaps)),
        "degraded_reason_count": len(degraded_reasons),
        "degraded_reasons": sorted(set(degraded_reasons)),
        "blocker_count": len(blockers),
        "blockers": blockers,
        "canonical_wrapper": {
            "command": ".venv/bin/python scripts/run_paperops_autonomous_pass.py",
            "summary_contract": SOURCE_FILES["paperops_autonomous_pass_summary"],
            "phase0_invokes_wrapper": False,
            "phase0_mutates_paperops_state": False,
        },
        "safety": READ_ONLY_AUTHORITY,
        "validation_errors": [],
    }


def validate_qsase_phase0_paperops_reliability_baseline(payload: dict[str, Any]) -> list[str]:
    """Return schema and safety validation errors for a Phase 0 artifact."""

    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version must be 1")
    if payload.get("phase_id") != PHASE_ID:
        errors.append("phase_id mismatch")
    if payload.get("artifact_type") != "qsase_phase0_paperops_reliability_baseline":
        errors.append("artifact_type mismatch")
    if payload.get("status") not in STATUS_RANK:
        errors.append("status must use the Phase 0 status model")
    components = payload.get("components")
    if not isinstance(components, dict):
        errors.append("components must be an object")
        components = {}
    for component_key in COMPONENT_ARTIFACTS:
        component = components.get(component_key)
        if not isinstance(component, dict):
            errors.append(f"components.{component_key} is missing")
            continue
        if component.get("status") not in STATUS_RANK:
            errors.append(f"components.{component_key}.status is invalid")
        safety = component.get("safety")
        if safety != READ_ONLY_AUTHORITY:
            errors.append(f"components.{component_key}.safety must match read-only authority")
    safety = payload.get("safety")
    if safety != READ_ONLY_AUTHORITY:
        errors.append("safety must match read-only Phase 0 authority")
    forbidden_true_fields = {
        "broker_write_allowed",
        "broker_post_allowed",
        "paper_order_allowed",
        "paper_order_submission_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "proof_credit_allowed",
        "risk_approval_allowed",
        "execution_approval_allowed",
        "candidate_creation_allowed",
        "telegram_command_path_enabled",
        "qctrl_jobs_allowed",
        "simulated_elapsed_time_allowed",
        "backfill_allowed",
    }
    for field in forbidden_true_fields:
        if safety.get(field) is not False:
            errors.append(f"safety.{field} must be false")
    if safety.get("read_only") is not True:
        errors.append("safety.read_only must be true")
    canonical_wrapper = payload.get("canonical_wrapper")
    if not isinstance(canonical_wrapper, dict):
        errors.append("canonical_wrapper must be an object")
    else:
        if canonical_wrapper.get("phase0_invokes_wrapper") is not False:
            errors.append("phase0_invokes_wrapper must be false")
        if canonical_wrapper.get("phase0_mutates_paperops_state") is not False:
            errors.append("phase0_mutates_paperops_state must be false")
    paper_growth_trial = payload.get("paper_growth_trial")
    if isinstance(paper_growth_trial, dict):
        if paper_growth_trial.get("backfill_used") is True:
            errors.append("paper_growth_trial.backfill_used must not be true")
        if paper_growth_trial.get("simulated_time_used") is True:
            errors.append("paper_growth_trial.simulated_time_used must not be true")
    else:
        errors.append("paper_growth_trial must be an object")
    return errors


def _component_artifact_payload(artifact: dict[str, Any], component_key: str) -> dict[str, Any]:
    component = artifact["components"][component_key]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": f"qsase:phase0:{component_key.replace('_', '-')}",
        "artifact_type": f"qsase_phase0_{component_key}",
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "generated_at": artifact["generated_at"],
        "status": component["status"],
        "component": component,
        "safety": READ_ONLY_AUTHORITY,
    }


def build_qsase_phase_implementation_status(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": artifact["generated_at"],
        "active_phase": PHASE_ID,
        "phases": {
            PHASE_ID: {
                "name": PHASE_NAME,
                "status": artifact["status"],
                "artifact_path": f"data/runtime/{PRIMARY_ARTIFACT}",
                "component_statuses": artifact["component_statuses"],
                "gap_count": artifact["gap_count"],
                "degraded_reason_count": artifact["degraded_reason_count"],
                "blocker_count": artifact["blocker_count"],
                "paper_only": True,
                "read_only": True,
                "proposal_first": True,
                "fail_closed": True,
                "later_qsase_phases_implemented": False,
            }
        },
        "safety": READ_ONLY_AUTHORITY,
    }


def write_qsase_phase0_paperops_reliability_outputs(
    artifact: dict[str, Any],
    settings: Settings | None = None,
    *,
    write_component_artifacts: bool = True,
    write_phase_status: bool = True,
    append_log: bool = True,
) -> dict[str, str]:
    """Write QSASE Phase 0 artifacts and return the written paths."""

    runtime_dir = _runtime_dir(settings)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}

    primary_path = runtime_dir / PRIMARY_ARTIFACT
    primary_path.write_text(_json_dump(artifact), encoding="utf-8")
    written["primary"] = str(primary_path)

    if write_component_artifacts:
        for component_key, filename in COMPONENT_ARTIFACTS.items():
            component_path = runtime_dir / filename
            component_path.write_text(
                _json_dump(_component_artifact_payload(artifact, component_key)),
                encoding="utf-8",
            )
            written[component_key] = str(component_path)

    if write_phase_status:
        phase_status_path = runtime_dir / PHASE_STATUS_ARTIFACT
        phase_status_path.write_text(
            _json_dump(build_qsase_phase_implementation_status(artifact)),
            encoding="utf-8",
        )
        written["phase_status"] = str(phase_status_path)

    if append_log:
        log_path = _repo_root() / IMPLEMENTATION_LOG
        _append_phase0_log(log_path, artifact)
        written["implementation_log"] = str(log_path)

    return written


def _append_phase0_log(log_path: Path, artifact: dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if log_path.exists():
        existing = log_path.read_text(encoding="utf-8")
    else:
        existing = "# QSASE Implementation Log\n\n"
    marker = f"<!-- {PHASE_ID} -->"
    component_summary = ", ".join(
        f"{key}={status}" for key, status in artifact.get("component_statuses", {}).items()
    )
    entry = (
        f"{marker}\n"
        f"## Appendix A: Operational Phase 0 - PaperOps Execution Reliability Baseline\n\n"
        f"- Generated at: `{artifact.get('generated_at')}`\n"
        f"- Status: `{artifact.get('status')}`\n"
        f"- Runtime artifact: `data/runtime/{PRIMARY_ARTIFACT}`\n"
        f"- Durable phase status: `data/runtime/{PHASE_STATUS_ARTIFACT}`\n"
        f"- Components: {component_summary}\n"
        f"- Safety: read-only, paper-only, proposal-first, fail-closed; no candidate creation, "
        f"risk approval, execution approval, paper order, broker write, live-capital route, "
        f"Q-CTRL job, simulated elapsed time, or proof credit.\n"
    )
    if marker in existing:
        before = existing.split(marker, 1)[0].rstrip()
        existing = before + "\n\n" + entry
    elif existing.endswith("\n"):
        existing = existing + entry
    else:
        existing = existing + "\n\n" + entry
    log_path.write_text(existing, encoding="utf-8")


def build_and_write_qsase_phase0_paperops_reliability_baseline(
    settings: Settings | None = None,
    *,
    write_component_artifacts: bool = True,
    write_phase_status: bool = True,
    append_log: bool = True,
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    artifact = build_qsase_phase0_paperops_reliability_baseline(settings)
    errors = validate_qsase_phase0_paperops_reliability_baseline(artifact)
    artifact["validation_errors"] = errors
    written = write_qsase_phase0_paperops_reliability_outputs(
        artifact,
        settings,
        write_component_artifacts=write_component_artifacts,
        write_phase_status=write_phase_status,
        append_log=append_log,
    )
    return artifact, written, errors


def validate_negative_safety_probe() -> list[str]:
    """Ensure the validator rejects accidental authority grants."""

    artifact = build_qsase_phase0_paperops_reliability_baseline()
    probe = copy.deepcopy(artifact)
    probe["safety"]["broker_write_allowed"] = True
    probe["components"]["scanner_freshness"]["safety"]["broker_write_allowed"] = True
    probe_errors = validate_qsase_phase0_paperops_reliability_baseline(probe)
    if not any("broker_write_allowed" in error for error in probe_errors):
        return ["validator failed to reject broker_write_allowed=true"]

    probe = copy.deepcopy(artifact)
    probe["paper_growth_trial"]["simulated_time_used"] = True
    probe_errors = validate_qsase_phase0_paperops_reliability_baseline(probe)
    if not any("simulated_time_used" in error for error in probe_errors):
        return ["validator failed to reject simulated_time_used=true"]

    probe = copy.deepcopy(artifact)
    probe["canonical_wrapper"]["phase0_mutates_paperops_state"] = True
    probe_errors = validate_qsase_phase0_paperops_reliability_baseline(probe)
    if not any("phase0_mutates_paperops_state" in error for error in probe_errors):
        return ["validator failed to reject phase0_mutates_paperops_state=true"]

    return []
