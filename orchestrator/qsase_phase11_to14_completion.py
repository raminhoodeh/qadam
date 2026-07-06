"""QSASE perfect-operation phases 11-14 completion layers.

These V2 layers complete the post-router operating loop:

- paper lifecycle and paper proof ledger eligibility,
- learning attribution and proposal queues,
- dashboard completion contract,
- Telegram summary boundary.

They are read-only, paper-only, proposal-first, and fail closed. They do not
create orders, broker writes, live-capital authority, proof credit, Telegram
commands, or policy mutations.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qsase_governance_safety_contract import universal_authority_flags

SCHEMA_VERSION = "qsase_phase11_to14_completion.v1"

PAPER_LIFECYCLE_V2_ARTIFACT = "qsase_paper_lifecycle_v2.json"
PAPER_LIFECYCLE_RECORDS_V2_ARTIFACT = "qsase_paper_lifecycle_records_v2.jsonl"
PROOF_LEDGER_V2_ARTIFACT = "qsase_proof_ledger_v2.json"
PROOF_LINEAGE_RECORDS_V2_ARTIFACT = "qsase_proof_lineage_records_v2.jsonl"
PAPER_LIFECYCLE_DASHBOARD_V2_ARTIFACT = "qsase_paper_lifecycle_v2_dashboard_summary.json"

LEARNING_ATTRIBUTION_V2_ARTIFACT = "qsase_learning_attribution_v2.json"
LEARNING_ATTRIBUTION_RECORDS_V2_ARTIFACT = "qsase_learning_attribution_records_v2.jsonl"
POLICY_PROPOSALS_V2_ARTIFACT = "qsase_policy_proposals_v2.jsonl"
LEARNING_ATTRIBUTION_DASHBOARD_V2_ARTIFACT = "qsase_learning_attribution_v2_dashboard_summary.json"

DASHBOARD_COMPLETION_V2_ARTIFACT = "qsase_dashboard_completion_v2.json"
DASHBOARD_ORDER_AUDIT_V2_ARTIFACT = "qsase_dashboard_order_audit_v2.json"
DASHBOARD_COMPLETION_DASHBOARD_V2_ARTIFACT = "qsase_dashboard_completion_v2_dashboard_summary.json"

TELEGRAM_SUMMARY_V2_ARTIFACT = "qsase_telegram_summary_v2.json"
TELEGRAM_CANDIDATES_V2_ARTIFACT = "qsase_telegram_summary_candidates_v2.json"
TELEGRAM_DEDUPE_V2_ARTIFACT = "qsase_telegram_dedupe_v2.jsonl"
TELEGRAM_RECEIPTS_V2_ARTIFACT = "qsase_telegram_delivery_receipts_v2.jsonl"
TELEGRAM_COMMUNICATIONS_MIRROR_V2_ARTIFACT = "qsase_telegram_communications_mirror_v2.json"
TELEGRAM_SUMMARY_DASHBOARD_V2_ARTIFACT = "qsase_telegram_summary_v2_dashboard_summary.json"

HISTORY_ARTIFACT = "qsase_phase11_to14_completion_history.jsonl"
EVENTS_ARTIFACT = "qsase_phase11_to14_completion_events.jsonl"
PHASE_STATUS_ARTIFACT = "qsase_phase_implementation_status.json"

PAPER_ORDERS_ARTIFACT = "paper_orders.jsonl"
PAPER_POSITIONS_ARTIFACT = "paper_positions.jsonl"
PAPER_CLOSED_TRADES_ARTIFACT = "paper_closed_trades.jsonl"
PAPEROPS_SUMMARY_ARTIFACT = "paperops_autonomous_pass_summary.json"
PAPEROPS_LIFECYCLE_POLLER_ARTIFACT = "paperops_paper_lifecycle_poller.json"
PAPEROPS_CLOSE_TO_LEDGER_ARTIFACT = "paperops_close_to_ledger.json"
PHASE0_PROOF_LINEAGE_ARTIFACT = "qsase_phase0_proof_lineage_audit.json"
PROOF_BOUNDARY_ARTIFACT = "qsase_proof_boundary_audit.json"
COMPONENT_ATTRIBUTION_ARTIFACT = "qsase_component_attribution_ledger.json"
COMPONENT_ATTRIBUTION_RECORDS_ARTIFACT = "qsase_component_attribution_ledger.jsonl"
SOURCE_TRUST_PROPOSALS_ARTIFACT = "qsase_source_trust_proposals.json"
STRATEGY_WEIGHT_PROPOSALS_ARTIFACT = "qsase_strategy_weight_proposals.json"
MODEL_WEIGHT_PROPOSALS_ARTIFACT = "qsase_model_weight_proposals.json"
FILTER_THRESHOLD_PROPOSALS_ARTIFACT = "qsase_filter_threshold_proposals.json"
LEARNING_APPROVAL_QUEUE_ARTIFACT = "qsase_learning_approval_queue.json"
SOURCE_RELIABILITY_ARTIFACT = "qsase_source_reliability.json"
DASHBOARD_STATUS_ARTIFACT = "qsase_dashboard_status.json"
DASHBOARD_PORTFOLIO_ARTIFACT = "qsase_dashboard_portfolio_value_series.json"
DASHBOARD_CURRENT_PORTFOLIO_ARTIFACT = "qsase_dashboard_current_portfolio.json"
DASHBOARD_TRADING_HISTORY_ARTIFACT = "qsase_dashboard_trading_history.json"
DASHBOARD_SOURCE_NETWORK_ARTIFACT = "qsase_dashboard_source_network.json"
DASHBOARD_STRATEGY_UNIVERSE_ARTIFACT = "qsase_dashboard_strategy_universe.json"
DASHBOARD_PATTERN_INTELLIGENCE_ARTIFACT = "qsase_pattern_intelligence.json"
DASHBOARD_TRADE_INTENTS_ARTIFACT = "qsase_dashboard_trade_intents.json"
DASHBOARD_LEARNING_LEDGER_ARTIFACT = "qsase_dashboard_learning_ledger.json"
DASHBOARD_ANTI_SLOP_ARTIFACT = "qsase_dashboard_anti_slop_audit.json"
EVIDENCE_QUALITY_ARTIFACT = "qsase_evidence_quality_engine.json"
ROUTER_V2_ARTIFACT = "qsase_strategy_router_v2.json"
PAPEROPS_HANDOFF_V2_ARTIFACT = "qsase_paperops_handoff_v2.json"
TELEGRAM_BOUNDARY_ARTIFACT = "qsase_telegram_notification_boundary.json"
TELEGRAM_CANDIDATES_ARTIFACT = "qsase_telegram_message_candidates.json"
TELEGRAM_DEDUPE_ARTIFACT = "qsase_telegram_dedupe_ledger.jsonl"
TELEGRAM_MIRROR_ARTIFACT = "qsase_telegram_dashboard_communications_mirror.json"

STALE_ACCEPTED_ORDER_SECONDS = 90 * 60

AUTHORITY_FLAGS = {
    "review_only": True,
    "paper_only": True,
    "proposal_first": True,
    "command_disabled": True,
    "trade_candidate_created": False,
    "qualified_setup_created": False,
    "risk_approval_created": False,
    "execution_approval_created": False,
    "paper_order_allowed": False,
    "paper_order_created": False,
    "paper_order_created_count": 0,
    "broker_write_allowed": False,
    "broker_write_count": 0,
    "live_broker_endpoint_allowed": False,
    "proof_credit_allowed": False,
    "paper_proof_ledger_credit_allowed": False,
    "paper_proof_ledger_credit_created": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "simulated_elapsed_time_allowed": False,
    "policy_mutation_created": False,
    "strategy_mutation_created": False,
    "source_trust_update_created": False,
    "model_weight_update_created": False,
    "filter_threshold_update_created": False,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
    "telegram_live_send_allowed": False,
    "live_capital_enabled": False,
}

FALSE_AUTHORITY_FIELDS = {key for key, value in AUTHORITY_FLAGS.items() if value is False}


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


def _jsonl_line(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True) + "\n"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    if limit is not None:
        lines = lines[-limit:]
    records: list[dict[str, Any]] = []
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


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_dump(payload), encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(_jsonl_line(record) for record in records), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(_jsonl_line(payload))


def _artifact_ref(filename: str) -> str:
    return f"data/runtime/{filename}"


def _hash_id(parts: list[Any], prefix: str) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}"


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


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


def _float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _parse_dt(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _load_context(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "runtime": runtime,
        "paper_orders": _read_jsonl(runtime / PAPER_ORDERS_ARTIFACT, limit=1000),
        "paper_positions": _read_jsonl(runtime / PAPER_POSITIONS_ARTIFACT, limit=1000),
        "paper_closed_trades": _read_jsonl(runtime / PAPER_CLOSED_TRADES_ARTIFACT, limit=1000),
        "paperops_summary": _read_json(runtime / PAPEROPS_SUMMARY_ARTIFACT),
        "paperops_lifecycle_poller": _read_json(runtime / PAPEROPS_LIFECYCLE_POLLER_ARTIFACT),
        "paperops_close_to_ledger": _read_json(runtime / PAPEROPS_CLOSE_TO_LEDGER_ARTIFACT),
        "phase0_proof_lineage": _read_json(runtime / PHASE0_PROOF_LINEAGE_ARTIFACT),
        "proof_boundary": _read_json(runtime / PROOF_BOUNDARY_ARTIFACT),
        "component_attribution": _read_json(runtime / COMPONENT_ATTRIBUTION_ARTIFACT),
        "component_records": _read_jsonl(runtime / COMPONENT_ATTRIBUTION_RECORDS_ARTIFACT, limit=2000),
        "source_trust_proposals": _read_json(runtime / SOURCE_TRUST_PROPOSALS_ARTIFACT),
        "strategy_weight_proposals": _read_json(runtime / STRATEGY_WEIGHT_PROPOSALS_ARTIFACT),
        "model_weight_proposals": _read_json(runtime / MODEL_WEIGHT_PROPOSALS_ARTIFACT),
        "filter_threshold_proposals": _read_json(runtime / FILTER_THRESHOLD_PROPOSALS_ARTIFACT),
        "learning_approval_queue": _read_json(runtime / LEARNING_APPROVAL_QUEUE_ARTIFACT),
        "source_reliability": _read_json(runtime / SOURCE_RELIABILITY_ARTIFACT),
        "dashboard_status": _read_json(runtime / DASHBOARD_STATUS_ARTIFACT),
        "dashboard_portfolio": _read_json(runtime / DASHBOARD_PORTFOLIO_ARTIFACT),
        "dashboard_current_portfolio": _read_json(runtime / DASHBOARD_CURRENT_PORTFOLIO_ARTIFACT),
        "dashboard_trading_history": _read_json(runtime / DASHBOARD_TRADING_HISTORY_ARTIFACT),
        "dashboard_source_network": _read_json(runtime / DASHBOARD_SOURCE_NETWORK_ARTIFACT),
        "dashboard_strategy_universe": _read_json(runtime / DASHBOARD_STRATEGY_UNIVERSE_ARTIFACT),
        "dashboard_pattern_intelligence": _read_json(runtime / DASHBOARD_PATTERN_INTELLIGENCE_ARTIFACT),
        "dashboard_trade_intents": _read_json(runtime / DASHBOARD_TRADE_INTENTS_ARTIFACT),
        "dashboard_learning_ledger": _read_json(runtime / DASHBOARD_LEARNING_LEDGER_ARTIFACT),
        "dashboard_anti_slop": _read_json(runtime / DASHBOARD_ANTI_SLOP_ARTIFACT),
        "evidence_quality": _read_json(runtime / EVIDENCE_QUALITY_ARTIFACT),
        "router_v2": _read_json(runtime / ROUTER_V2_ARTIFACT),
        "paperops_handoff_v2": _read_json(runtime / PAPEROPS_HANDOFF_V2_ARTIFACT),
        "telegram_boundary": _read_json(runtime / TELEGRAM_BOUNDARY_ARTIFACT),
        "telegram_candidates": _read_json(runtime / TELEGRAM_CANDIDATES_ARTIFACT),
        "telegram_dedupe": _read_jsonl(runtime / TELEGRAM_DEDUPE_ARTIFACT, limit=1000),
        "telegram_mirror": _read_json(runtime / TELEGRAM_MIRROR_ARTIFACT),
        "telegram_dedupe_v2": _read_jsonl(runtime / TELEGRAM_DEDUPE_V2_ARTIFACT, limit=1000),
    }


def _order_lifecycle_state(order: dict[str, Any], generated_at: datetime) -> dict[str, Any]:
    status = str(order.get("status") or "unknown").lower()
    submitted_at = _parse_dt(order.get("submitted_at"))
    age_seconds = int((generated_at - submitted_at).total_seconds()) if submitted_at else None
    filled_quantity = _float(order.get("filled_quantity"), 0.0)
    filled_at = _parse_dt(order.get("filled_at"))
    if filled_at or filled_quantity > 0:
        return {
            "lifecycle_state": "filled_waiting_position_or_close_reconciliation",
            "stale": False,
            "next_lifecycle_action": "reconcile_fill_against_positions_and_closed_trades",
            "age_seconds": age_seconds,
        }
    if status in {"new", "accepted", "pending_new", "open", "partially_filled"}:
        stale = age_seconds is not None and age_seconds > STALE_ACCEPTED_ORDER_SECONDS
        return {
            "lifecycle_state": "stale_accepted_order_review" if stale else "accepted_waiting_for_fill",
            "stale": stale,
            "next_lifecycle_action": (
                "no_action_review_only_cancel_replace_requires_operator"
                if stale
                else "continue_waiting_for_broker_fill"
            ),
            "age_seconds": age_seconds,
        }
    if status in {"canceled", "expired", "rejected"}:
        return {
            "lifecycle_state": f"terminal_{status}",
            "stale": False,
            "next_lifecycle_action": "record_terminal_state_no_broker_action",
            "age_seconds": age_seconds,
        }
    return {
        "lifecycle_state": "ambiguous_order_state",
        "stale": False,
        "next_lifecycle_action": "repair_missing_order_state",
        "age_seconds": age_seconds,
    }


def build_paper_lifecycle_and_proof_v2(
    context: dict[str, Any],
    generated_at: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    generated_dt = _parse_dt(generated_at) or _now()
    lifecycle_records: list[dict[str, Any]] = []
    for order in context["paper_orders"]:
        order_state = _order_lifecycle_state(order, generated_dt)
        lifecycle_records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qsase_paper_lifecycle_v2_record",
                "lifecycle_record_id": _hash_id([SCHEMA_VERSION, "order", order.get("order_id")], "qsase-lifecycle-v2"),
                "generated_at": generated_at,
                "source_record_type": "paper_order_mirror",
                "source_record_id": order.get("order_id"),
                "instrument": order.get("instrument"),
                "direction": order.get("direction"),
                "broker_status": order.get("status"),
                "lifecycle_state": order_state["lifecycle_state"],
                "stale": order_state["stale"],
                "age_seconds": order_state["age_seconds"],
                "stale_policy": {
                    "stale_after_seconds": STALE_ACCEPTED_ORDER_SECONDS,
                    "policy": order_state["next_lifecycle_action"],
                    "cancel_replace_allowed_by_v2": False,
                    "reason": "Phase 11 is lifecycle visibility only; cancel/replace requires the guarded downstream workflow and operator policy.",
                },
                "next_lifecycle_action": order_state["next_lifecycle_action"],
                "artifact_refs": [_artifact_ref(PAPER_ORDERS_ARTIFACT)],
                "authority": AUTHORITY_FLAGS,
                "paper_order_created": False,
                "broker_write_allowed": False,
                "proof_credit_allowed": False,
                "live_capital_enabled": False,
            }
        )
    for position in context["paper_positions"]:
        lifecycle_records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qsase_paper_lifecycle_v2_record",
                "lifecycle_record_id": _hash_id([SCHEMA_VERSION, "position", position.get("position_id") or position.get("instrument")], "qsase-lifecycle-v2"),
                "generated_at": generated_at,
                "source_record_type": "paper_position_mirror",
                "source_record_id": position.get("position_id") or position.get("instrument"),
                "instrument": position.get("instrument"),
                "broker_status": position.get("status", "open_position"),
                "lifecycle_state": "open_position",
                "stale": False,
                "stale_policy": {"policy": "monitor_position_until_exit_gate", "cancel_replace_allowed_by_v2": False},
                "next_lifecycle_action": "monitor_position_until_guarded_exit_or_close",
                "artifact_refs": [_artifact_ref(PAPER_POSITIONS_ARTIFACT)],
                "authority": AUTHORITY_FLAGS,
                "paper_order_created": False,
                "broker_write_allowed": False,
                "proof_credit_allowed": False,
                "live_capital_enabled": False,
            }
        )
    proof_records: list[dict[str, Any]] = []
    for trade in context["paper_closed_trades"]:
        postmortem_status = str(trade.get("postmortem_status") or "postmortem_missing")
        lifecycle_state = "closed_postmortem_complete" if postmortem_status == "postmortem_complete" else "closed_postmortem_due"
        lifecycle_records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qsase_paper_lifecycle_v2_record",
                "lifecycle_record_id": _hash_id([SCHEMA_VERSION, "closed", trade.get("trade_id")], "qsase-lifecycle-v2"),
                "generated_at": generated_at,
                "source_record_type": "paper_closed_trade_mirror",
                "source_record_id": trade.get("trade_id"),
                "instrument": trade.get("instrument"),
                "direction": trade.get("direction"),
                "broker_status": "closed",
                "lifecycle_state": lifecycle_state,
                "postmortem_status": postmortem_status,
                "stale": False,
                "stale_policy": {"policy": "postmortem_required_before_proof_eligibility", "cancel_replace_allowed_by_v2": False},
                "next_lifecycle_action": "complete_lineaged_postmortem" if postmortem_status != "postmortem_complete" else "audit_proof_lineage",
                "artifact_refs": [_artifact_ref(PAPER_CLOSED_TRADES_ARTIFACT)],
                "authority": AUTHORITY_FLAGS,
                "paper_order_created": False,
                "broker_write_allowed": False,
                "proof_credit_allowed": False,
                "live_capital_enabled": False,
            }
        )
        lineage_checks = {
            "research_goal_id": bool(trade.get("research_goal_id") or trade.get("source_intent_id")),
            "candidate_identity": bool(trade.get("candidate_identity") or trade.get("source_intent_id")),
            "risk_approval": bool(trade.get("risk_approval_id")),
            "staged_order": bool(trade.get("staged_order_id")),
            "submitted_order": bool(trade.get("source_order_ref") or trade.get("order_id")),
            "fill": bool(trade.get("entry_price") or trade.get("filled_at") or trade.get("opened_at")),
            "close": bool(trade.get("closed_at")),
            "postmortem": postmortem_status == "postmortem_complete",
        }
        missing = [key for key, passed in lineage_checks.items() if not passed]
        proof_records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qsase_proof_lineage_v2_record",
                "proof_lineage_record_id": _hash_id([SCHEMA_VERSION, "proof", trade.get("trade_id")], "qsase-proof-v2"),
                "generated_at": generated_at,
                "trade_id": trade.get("trade_id"),
                "instrument": trade.get("instrument"),
                "lineage_checks": lineage_checks,
                "missing_lineage": missing,
                "proof_eligible": not missing,
                "proof_rejection_reason": "none" if not missing else "missing_" + "_".join(missing[:4]),
                "paper_proof_ledger_credit_allowed": False,
                "paper_proof_ledger_credit_created": False,
                "backtest_shadow_or_synthetic_credit": False,
                "artifact_refs": [_artifact_ref(PAPER_CLOSED_TRADES_ARTIFACT), _artifact_ref(PHASE0_PROOF_LINEAGE_ARTIFACT)],
                "authority": AUTHORITY_FLAGS,
                "paper_order_created": False,
                "broker_write_allowed": False,
                "proof_credit_allowed": False,
                "live_capital_enabled": False,
            }
        )
    state_counts = Counter(record["lifecycle_state"] for record in lifecycle_records)
    ambiguous_count = state_counts.get("ambiguous_order_state", 0)
    stale_count = sum(1 for record in lifecycle_records if record.get("stale") is True)
    proof_eligible_count = sum(1 for record in proof_records if record["proof_eligible"])
    lifecycle_payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_paper_lifecycle_v2",
        "generated_at": generated_at,
        "status": "qsase_paper_lifecycle_v2_ready" if ambiguous_count == 0 else "qsase_paper_lifecycle_v2_needs_repair",
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "command_disabled": True,
        "proposal_first": True,
        "authority": universal_authority_flags(),
        "authority_flags": AUTHORITY_FLAGS,
        "paper_order_mirror_count": len(context["paper_orders"]),
        "open_position_mirror_count": len(context["paper_positions"]),
        "closed_paper_trade_count": len(context["paper_closed_trades"]),
        "lifecycle_record_count": len(lifecycle_records),
        "ambiguous_lifecycle_count": ambiguous_count,
        "stale_accepted_order_count": stale_count,
        "state_counts": dict(state_counts),
        "records_path": _artifact_ref(PAPER_LIFECYCLE_RECORDS_V2_ARTIFACT),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "boundary": "Lifecycle V2 explains paper order and trade state only. It cannot create, cancel, replace, close, or prove trades.",
    }
    proof_payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_proof_ledger_v2",
        "generated_at": generated_at,
        "status": "qsase_proof_ledger_v2_ready_with_eligible_records" if proof_eligible_count else "qsase_proof_ledger_v2_ready_no_eligible_proof",
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "command_disabled": True,
        "proposal_first": True,
        "authority": universal_authority_flags(),
        "authority_flags": AUTHORITY_FLAGS,
        "closed_paper_trade_count": len(context["paper_closed_trades"]),
        "proof_lineage_record_count": len(proof_records),
        "proof_eligible_count": proof_eligible_count,
        "proof_rejected_count": len(proof_records) - proof_eligible_count,
        "missing_lineage_counts": dict(Counter(reason for row in proof_records for reason in row["missing_lineage"])),
        "lineage_records_path": _artifact_ref(PROOF_LINEAGE_RECORDS_V2_ARTIFACT),
        "backtest_shadow_or_synthetic_proof_credit_count": 0,
        "paper_proof_ledger_credit_created": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "boundary": "Proof Ledger V2 can only audit eligibility. It cannot grant paper proof ledger credit.",
    }
    return lifecycle_payload, lifecycle_records, proof_payload, proof_records


def _proposal_records_from_artifact(payload: dict[str, Any], proposal_type: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for key, value in payload.items():
        if key.endswith("_proposals") and isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    records.append(item)
    if records:
        return records
    count = _int(payload.get("proposal_count"), 0) or _int(payload.get(f"{proposal_type}_proposal_count"), 0)
    return [
        {
            "proposal_id": _hash_id([proposal_type, payload.get("status"), index], "qsase-policy-proposal-v2"),
            "proposal_type": proposal_type,
            "proposal_state": "visible_pending_human_approval",
            "applied": False,
            "apply_allowed": False,
        }
        for index in range(count)
    ]


def build_learning_attribution_v2(
    context: dict[str, Any],
    proof_payload: dict[str, Any],
    generated_at: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    for source in context["component_records"]:
        component = _safe_dict(source.get("component_attribution"))
        helped = [key for key, item in component.items() if _safe_dict(item).get("contribution") == "helped"]
        hurt = [key for key, item in component.items() if _safe_dict(item).get("contribution") == "hurt"]
        blocked = [key for key, item in component.items() if _safe_dict(item).get("contribution") == "blocked"]
        records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qsase_learning_attribution_v2_record",
                "learning_attribution_v2_id": _hash_id([SCHEMA_VERSION, source.get("attribution_record_id")], "qsase-learning-v2"),
                "generated_at": generated_at,
                "source_attribution_record_id": source.get("attribution_record_id"),
                "outcome_class": source.get("evidence_class") or "unknown",
                "outcome_state": _safe_dict(source.get("outcome_summary")).get("outcome_state", source.get("evidence_class")),
                "causal_label": _safe_dict(source.get("causal_assessment")).get("label", "not_assessed"),
                "helped_components": helped,
                "hurt_components": hurt,
                "blocked_components": blocked,
                "proposal_type": _safe_dict(source.get("proposal")).get("proposal_type"),
                "proposal_applied": False,
                "human_approval_required": True,
                "authority": AUTHORITY_FLAGS,
                "paper_order_created": False,
                "broker_write_allowed": False,
                "proof_credit_allowed": False,
                "live_capital_enabled": False,
            }
        )
    proposal_sources = [
        ("source_trust", context["source_trust_proposals"]),
        ("strategy_weight", context["strategy_weight_proposals"]),
        ("model_routing", context["model_weight_proposals"]),
        ("akber_threshold", context["filter_threshold_proposals"]),
    ]
    proposals: list[dict[str, Any]] = []
    for proposal_type, payload in proposal_sources:
        for item in _proposal_records_from_artifact(payload, proposal_type):
            proposals.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "artifact_type": "qsase_policy_proposal_v2",
                    "policy_proposal_v2_id": str(item.get("proposal_id") or _hash_id([proposal_type, len(proposals)], "qsase-policy-proposal-v2")),
                    "generated_at": generated_at,
                    "proposal_type": proposal_type,
                    "proposal_state": item.get("proposal_state", "visible_pending_human_approval"),
                    "target_surface": item.get("target_surface", proposal_type),
                    "human_approval_required": True,
                    "applied": False,
                    "apply_allowed": False,
                    "policy_mutation_created": False,
                    "source_record": item,
                    "authority": AUTHORITY_FLAGS,
                }
            )
    source_reliability = _safe_dict(context.get("source_reliability"))
    outage_count = _int(source_reliability.get("outage_count"), 0)
    if outage_count:
        proposals.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qsase_policy_proposal_v2",
                "policy_proposal_v2_id": _hash_id(["data_source_repair", outage_count, source_reliability.get("generated_at")], "qsase-policy-proposal-v2"),
                "generated_at": generated_at,
                "proposal_type": "data_source_repair",
                "proposal_state": "visible_pending_human_approval",
                "target_surface": "source_reliability",
                "human_approval_required": True,
                "applied": False,
                "apply_allowed": False,
                "policy_mutation_created": False,
                "source_record": {"outage_count": outage_count, "status": source_reliability.get("status")},
                "authority": AUTHORITY_FLAGS,
            }
        )
    outcome_counts = Counter(row["outcome_class"] for row in records)
    causal_counts = Counter(row["causal_label"] for row in records)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_learning_attribution_v2",
        "generated_at": generated_at,
        "status": "qsase_learning_attribution_v2_ready_with_proposals",
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "command_disabled": True,
        "proposal_first": True,
        "authority": universal_authority_flags(),
        "authority_flags": AUTHORITY_FLAGS,
        "attribution_record_count": len(records),
        "outcome_class_counts": dict(outcome_counts),
        "causal_label_counts": dict(causal_counts),
        "policy_proposal_count": len(proposals),
        "source_trust_proposal_count": sum(1 for row in proposals if row["proposal_type"] == "source_trust"),
        "strategy_weight_proposal_count": sum(1 for row in proposals if row["proposal_type"] == "strategy_weight"),
        "akber_threshold_proposal_count": sum(1 for row in proposals if row["proposal_type"] == "akber_threshold"),
        "model_routing_proposal_count": sum(1 for row in proposals if row["proposal_type"] == "model_routing"),
        "data_source_repair_proposal_count": sum(1 for row in proposals if row["proposal_type"] == "data_source_repair"),
        "proof_eligible_count": proof_payload.get("proof_eligible_count"),
        "records_path": _artifact_ref(LEARNING_ATTRIBUTION_RECORDS_V2_ARTIFACT),
        "policy_proposals_path": _artifact_ref(POLICY_PROPOSALS_V2_ARTIFACT),
        "policy_mutation_created": False,
        "strategy_mutation_created": False,
        "source_trust_update_created": False,
        "model_weight_update_created": False,
        "filter_threshold_update_created": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "boundary": "Learning Attribution V2 explains outcomes and proposes repairs. It cannot apply policy changes without explicit approval.",
    }
    return payload, records, proposals


def build_dashboard_completion_v2(
    context: dict[str, Any],
    lifecycle_payload: dict[str, Any],
    proof_payload: dict[str, Any],
    learning_payload: dict[str, Any],
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    dashboard = _safe_dict(context.get("dashboard_status"))
    portfolio = _safe_dict(dashboard.get("dashboard_portfolio"))
    anti_slop = _safe_dict(context.get("dashboard_anti_slop"))
    source_network = _safe_dict(context.get("dashboard_source_network"))
    pattern_intelligence = _safe_dict(context.get("dashboard_pattern_intelligence"))
    trade_intents = _safe_dict(context.get("dashboard_trade_intents"))
    expected_order = [
        "portfolio_value",
        "current_portfolio",
        "trading_history",
        "hedge_fund_team",
        "source_intelligence_network",
        "trading_universe",
        "strategy_universe",
        "pattern_recognition_findings",
        "akber_filter_state",
        "trade_candidates",
        "router_paperops_decision",
        "learning_ledger",
        "telegram_summary",
    ]
    section_sources = {
        "portfolio_value": _artifact_ref(DASHBOARD_PORTFOLIO_ARTIFACT),
        "current_portfolio": _artifact_ref(DASHBOARD_CURRENT_PORTFOLIO_ARTIFACT),
        "trading_history": _artifact_ref(DASHBOARD_TRADING_HISTORY_ARTIFACT),
        "hedge_fund_team": "landing-page-repo/dashboard.js#renderQsaseHedgeFundTeam",
        "source_intelligence_network": _artifact_ref(DASHBOARD_SOURCE_NETWORK_ARTIFACT),
        "trading_universe": "landing-page-repo/dashboard.js#renderQsaseTradingUniverse",
        "strategy_universe": _artifact_ref(DASHBOARD_STRATEGY_UNIVERSE_ARTIFACT),
        "pattern_recognition_findings": _artifact_ref(DASHBOARD_PATTERN_INTELLIGENCE_ARTIFACT),
        "akber_filter_state": _artifact_ref(EVIDENCE_QUALITY_ARTIFACT),
        "trade_candidates": _artifact_ref(DASHBOARD_TRADE_INTENTS_ARTIFACT),
        "router_paperops_decision": _artifact_ref(ROUTER_V2_ARTIFACT),
        "learning_ledger": "landing-page-repo/dashboard.js#renderQsaseLearningLedger",
        "telegram_summary": "landing-page-repo/dashboard.js#renderQsaseTelegramSummary",
    }
    missing = [section for section, ref in section_sources.items() if ref.startswith("data/runtime/") and not (_runtime_dir() / ref.replace("data/runtime/", "")).exists()]
    portfolio_consistency = _safe_dict(portfolio.get("portfolio_consistency"))
    source_category_count = _int(source_network.get("category_row_count"), len(_safe_list(source_network.get("category_rows"))))
    source_row_count = _int(source_network.get("source_row_count"), len(_safe_list(source_network.get("source_rows"))))
    trading_universe_count = _int(dashboard.get("trading_universe_row_count"), 0)
    finding_count = _int(pattern_intelligence.get("finding_count"), len(_safe_list(pattern_intelligence.get("findings"))))
    order_audit = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_dashboard_order_audit_v2",
        "generated_at": generated_at,
        "expected_order": expected_order,
        "section_sources": section_sources,
        "missing_sections": missing,
        "order_passed": not missing,
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
    }
    stale_labeled_count = _int(dashboard.get("stale_labeled_count"), 0)
    blocker_count = 0
    if portfolio_consistency.get("status") != "ok":
        blocker_count += 1
    if anti_slop.get("status") != "anti_slop_passed":
        blocker_count += 1
    if missing:
        blocker_count += 1
    status = "qsase_dashboard_completion_v2_ready"
    if stale_labeled_count:
        status = "qsase_dashboard_completion_v2_ready_with_stale_labels"
    if blocker_count:
        status = "qsase_dashboard_completion_v2_needs_repair"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_dashboard_completion_v2",
        "generated_at": generated_at,
        "status": status,
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "command_disabled": True,
        "proposal_first": True,
        "authority": universal_authority_flags(),
        "authority_flags": AUTHORITY_FLAGS,
        "required_order": expected_order,
        "dashboard_order_passed": not missing,
        "missing_section_count": len(missing),
        "missing_sections": missing,
        "portfolio_consistency_status": portfolio_consistency.get("status"),
        "portfolio_value_latest": portfolio.get("current_value_gbp"),
        "chart_latest_value": portfolio_consistency.get("latest_chart_value"),
        "source_category_count": source_category_count,
        "source_row_count": source_row_count,
        "trading_universe_row_count": trading_universe_count,
        "pattern_finding_count": finding_count,
        "trade_intent_count": _int(trade_intents.get("intent_count"), len(_safe_list(trade_intents.get("rows")))),
        "paper_lifecycle_status": lifecycle_payload.get("status"),
        "proof_ledger_status": proof_payload.get("status"),
        "learning_attribution_status": learning_payload.get("status"),
        "anti_slop_status": anti_slop.get("status"),
        "anti_slop_error_count": _int(anti_slop.get("error_count"), 0),
        "stale_labeled_count": stale_labeled_count,
        "plain_english_translations_present": True,
        "hedge_fund_team_cards": [
            {"role": "Python COO", "summary": "Runs orchestration, checks, paper account mirrors, and guarded handoff discipline."},
            {"role": "Local LLM Research Analyst", "summary": "Compresses source observations into research context without broker authority."},
            {"role": "Frontier LLM Strategy Lead", "summary": "Challenges causal logic, alternative explanations, and strategy fit."},
            {"role": "Quantum Head of Quant", "summary": "Reviews nonlinear ambiguity and quantum/classical pattern evidence without approving trades."},
        ],
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "boundary": "Dashboard Completion V2 verifies public fund clarity only. It cannot create commands, orders, broker writes, proof credit, or live capital.",
    }
    return payload, order_audit


def _message_quality(body: str) -> dict[str, Any]:
    lower = body.lower()
    generic_hits = [
        phrase
        for phrase in ("codebase upgrade", "what changed", "why it matters", "ai-powered", "seamless", "game-changing")
        if phrase in lower
    ]
    harsh_hits = [phrase for phrase in ("failed", "slop", "nonsense", "broken") if phrase in lower]
    unsafe_hits = [phrase for phrase in ("/buy", "/sell", "submit order", "live capital") if phrase in lower]
    internal_hits = [phrase for phrase in ("qsase_", "paperops handoff", "degraded_command_failure") if phrase in lower]
    errors = []
    if len(body) > 240:
        errors.append("body_too_long")
    if generic_hits:
        errors.append("generic_language")
    if harsh_hits:
        errors.append("harsh_language")
    if unsafe_hits:
        errors.append("unsafe_command_or_authority_language")
    if internal_hits:
        errors.append("internal_only_language")
    return {
        "character_count": len(body),
        "line_count": len(body.splitlines()),
        "specificity_status": "specific" if not generic_hits else "generic",
        "human_style_status": "human" if not harsh_hits and len(body) <= 240 else "needs_edit",
        "generic_hits": generic_hits,
        "harsh_hits": harsh_hits,
        "unsafe_hits": unsafe_hits,
        "internal_hits": internal_hits,
        "errors": errors,
        "passed": not errors,
    }


def _candidate(message_class: str, event_id: str, body: str, generated_at: str, state: str = "active") -> dict[str, Any]:
    identity = {
        "message_class": message_class,
        "event_id": event_id,
        "state": state,
    }
    fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True).encode("utf-8")).hexdigest()
    quality = _message_quality(body)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_telegram_summary_candidate_v2",
        "message_candidate_v2_id": _hash_id([SCHEMA_VERSION, message_class, event_id], "qsase-telegram-v2"),
        "generated_at": generated_at,
        "message_class": message_class,
        "event_identity": identity,
        "event_fingerprint": fingerprint,
        "body": body,
        "quality": quality,
        "status": "message_ready_for_review" if quality["passed"] else "message_rejected_quality",
        "delivery": {
            "telegram_live_send_allowed": False,
            "live_send_attempted": False,
            "live_send_succeeded": False,
        },
        "authority": AUTHORITY_FLAGS,
        "paper_order_created": False,
        "broker_write_allowed": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
    }


def build_telegram_summary_v2(
    context: dict[str, Any],
    lifecycle_payload: dict[str, Any],
    proof_payload: dict[str, Any],
    learning_payload: dict[str, Any],
    dashboard_payload: dict[str, Any],
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    patterns = _safe_list(context["dashboard_pattern_intelligence"].get("findings"))
    top_pattern = patterns[0] if patterns else {}
    orders = context["paper_orders"]
    closed = context["paper_closed_trades"]
    latest_order = orders[0] if orders else {}
    latest_closed = closed[0] if closed else {}
    evidence = _safe_dict(context.get("evidence_quality"))
    router = _safe_dict(context.get("router_v2"))
    source_reliability = _safe_dict(context.get("source_reliability"))
    candidates = [
        _candidate(
            "pattern_found",
            str(top_pattern.get("pattern_id") or top_pattern.get("title") or "no_pattern"),
            f"Pattern found: {top_pattern.get('market_affected', 'market sleeve')} shows {top_pattern.get('stage_label', 'research evidence')}. Next: collect confirmation. No order.",
            generated_at,
        ),
        _candidate(
            "pattern_blocked",
            str(evidence.get("generated_at") or "evidence_hold"),
            f"Pattern held: {evidence.get('held_for_evidence_count', 0)} need stronger evidence; {evidence.get('paper_review_candidate_count', 0)} are tradeable now. No order.",
            generated_at,
        ),
        _candidate(
            "paper_review_candidate",
            str(router.get("generated_at") or "router_state"),
            f"Paper review: {router.get('paper_review_candidate_count', 0)} setup ready; {router.get('decision_count', 0)} reviewed. Next: wait for all gates. No order.",
            generated_at,
        ),
        _candidate(
            "paper_order_submitted",
            str(latest_order.get("order_id") or "no_order"),
            f"Paper order mirror: {latest_order.get('instrument', 'none')} is {latest_order.get('status', 'not active')}. Next: watch broker fill. No command.",
            generated_at,
        ),
        _candidate(
            "paper_fill",
            str(latest_order.get("order_id") or "no_fill"),
            f"Paper fill watch: {lifecycle_payload.get('state_counts', {}).get('filled_waiting_position_or_close_reconciliation', 0)} fills need reconciliation. No proof credit.",
            generated_at,
        ),
        _candidate(
            "paper_close",
            str(latest_closed.get("trade_id") or "no_close"),
            f"Paper close: {proof_payload.get('closed_paper_trade_count', 0)} closed trades; {proof_payload.get('proof_eligible_count', 0)} proof-eligible. No proof credit.",
            generated_at,
        ),
        _candidate(
            "learning_update",
            str(learning_payload.get("generated_at")),
            f"Learning update: {learning_payload.get('policy_proposal_count', 0)} proposals need review. Nothing was applied automatically.",
            generated_at,
        ),
        _candidate(
            "system_defect",
            str(source_reliability.get("generated_at") or dashboard_payload.get("generated_at")),
            f"System note: {source_reliability.get('outage_count', 0)} source issues and {dashboard_payload.get('stale_labeled_count', 0)} stale labels visible. No trade action.",
            generated_at,
        ),
    ]
    history = context.get("telegram_dedupe_v2", [])
    seen = {record.get("event_fingerprint") for record in history if record.get("event_fingerprint")}
    dedupe_records: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    ready_count = 0
    duplicate_count = 0
    quality_reject_count = 0
    for candidate in candidates:
        duplicate = candidate["event_fingerprint"] in seen
        if duplicate:
            candidate["status"] = "message_rejected_duplicate"
            duplicate_count += 1
        elif candidate["quality"]["passed"]:
            ready_count += 1
        else:
            quality_reject_count += 1
        dedupe_record = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": generated_at,
            "message_candidate_v2_id": candidate["message_candidate_v2_id"],
            "message_class": candidate["message_class"],
            "event_fingerprint": candidate["event_fingerprint"],
            "duplicate_suppressed": duplicate,
            "material_change_required_for_repeat": True,
            "message_status": candidate["status"],
        }
        dedupe_records.append(dedupe_record)
        receipts.append(
            {
                "schema_version": SCHEMA_VERSION,
                "generated_at": generated_at,
                "message_candidate_v2_id": candidate["message_candidate_v2_id"],
                "message_class": candidate["message_class"],
                "delivery_state": candidate["status"],
                "telegram_live_send_allowed": False,
                "live_send_attempted": False,
                "live_send_succeeded": False,
            }
        )
    candidate_payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_telegram_summary_candidates_v2",
        "generated_at": generated_at,
        "status": "qsase_telegram_summary_candidates_v2_ready",
        "candidate_count": len(candidates),
        "ready_count": ready_count,
        "duplicate_count": duplicate_count,
        "quality_reject_count": quality_reject_count,
        "candidates": candidates,
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
    }
    mirror = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_telegram_communications_mirror_v2",
        "generated_at": generated_at,
        "status": "qsase_telegram_communications_mirror_v2_ready",
        "latest_messages": [
            {
                "message_class": item["message_class"],
                "body": item["body"],
                "status": item["status"],
            }
            for item in candidates[:8]
        ],
        "telegram_live_send_allowed": False,
        "command_disabled": True,
        "public_safe": True,
        "read_only": True,
        "boundary": "Telegram Summary V2 is a public-safe mirror. It cannot receive commands or create trades.",
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_telegram_summary_v2",
        "generated_at": generated_at,
        "status": "qsase_telegram_summary_v2_ready" if quality_reject_count == 0 else "qsase_telegram_summary_v2_needs_copy_repair",
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "review_only": True,
        "command_disabled": True,
        "authority": universal_authority_flags(),
        "authority_flags": AUTHORITY_FLAGS,
        "message_candidate_count": len(candidates),
        "message_ready_count": ready_count,
        "message_rejected_duplicate_count": duplicate_count,
        "message_rejected_quality_count": quality_reject_count,
        "dedupe_record_count": len(dedupe_records),
        "delivery_receipt_count": len(receipts),
        "candidate_path": _artifact_ref(TELEGRAM_CANDIDATES_V2_ARTIFACT),
        "dedupe_path": _artifact_ref(TELEGRAM_DEDUPE_V2_ARTIFACT),
        "delivery_receipts_path": _artifact_ref(TELEGRAM_RECEIPTS_V2_ARTIFACT),
        "communications_mirror_path": _artifact_ref(TELEGRAM_COMMUNICATIONS_MIRROR_V2_ARTIFACT),
        "telegram_live_send_allowed": False,
        "telegram_command_path_enabled": False,
        "telegram_trade_command_enabled": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "boundary": "Telegram Summary V2 writes short review-only message candidates. It cannot create orders, approvals, broker writes, proof credit, or commands.",
    }
    return payload, candidate_payload, dedupe_records, receipts, mirror


def _dashboard_summary(payload: dict[str, Any], label: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": f"{label}_dashboard_summary",
        "generated_at": payload.get("generated_at"),
        "status": payload.get("status"),
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "summary_counts": {
            key: value
            for key, value in payload.items()
            if key.endswith("_count") and isinstance(value, int)
        },
        "paper_order_created_count": payload.get("paper_order_created_count", 0),
        "broker_write_count": payload.get("broker_write_count", 0),
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
    }


def build_phase11_to14_completion(settings: Settings | None = None) -> dict[str, Any]:
    context = _load_context(settings)
    generated_at = _iso(_now())
    lifecycle_payload, lifecycle_records, proof_payload, proof_records = build_paper_lifecycle_and_proof_v2(context, generated_at)
    learning_payload, learning_records, policy_proposals = build_learning_attribution_v2(context, proof_payload, generated_at)
    dashboard_payload, dashboard_order_audit = build_dashboard_completion_v2(
        context,
        lifecycle_payload,
        proof_payload,
        learning_payload,
        generated_at,
    )
    telegram_payload, telegram_candidates, telegram_dedupe, telegram_receipts, telegram_mirror = build_telegram_summary_v2(
        context,
        lifecycle_payload,
        proof_payload,
        learning_payload,
        dashboard_payload,
        generated_at,
    )
    return {
        "generated_at": generated_at,
        "lifecycle": (lifecycle_payload, lifecycle_records),
        "proof": (proof_payload, proof_records),
        "learning": (learning_payload, learning_records, policy_proposals),
        "dashboard": (dashboard_payload, dashboard_order_audit),
        "telegram": (telegram_payload, telegram_candidates, telegram_dedupe, telegram_receipts, telegram_mirror),
    }


def validate_payload(payload: dict[str, Any], expected_type: str) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if payload.get("artifact_type") != expected_type:
        errors.append("artifact_type_mismatch")
    for field in ("public_safe", "read_only", "command_disabled"):
        if payload.get(field) is not True:
            errors.append(f"{field}_must_be_true")
    for field in FALSE_AUTHORITY_FIELDS:
        if payload.get(field) is True:
            errors.append(f"{field}_must_not_be_true")
    if _int(payload.get("paper_order_created_count"), 0) != 0:
        errors.append("paper_order_created_count_must_be_zero")
    if _int(payload.get("broker_write_count"), 0) != 0:
        errors.append("broker_write_count_must_be_zero")
    if payload.get("proof_credit_allowed") is not False:
        errors.append("proof_credit_allowed_must_be_false")
    if payload.get("live_capital_enabled") is not False:
        errors.append("live_capital_enabled_must_be_false")
    return errors


def _phase_record(name: str, status: str, artifact_path: str, counts: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "artifact_path": artifact_path,
        "paper_only": True,
        "public_safe": True,
        "read_only": True,
        "proposal_first": True,
        "no_trade_candidates_created": True,
        "no_paper_orders_created": True,
        "no_broker_writes": True,
        "no_proof_credit_granted": True,
        "live_capital_enabled": False,
        **counts,
    }


def _update_phase_status(path: Path, bundle: dict[str, Any]) -> None:
    current = _read_json(path)
    phases = _safe_dict(current.get("phases"))
    lifecycle = bundle["lifecycle"][0]
    proof = bundle["proof"][0]
    learning = bundle["learning"][0]
    dashboard = bundle["dashboard"][0]
    telegram = bundle["telegram"][0]
    phases.update(
        {
            "perfect_operation_phase_11_paper_lifecycle_proof_v2": _phase_record(
                "Perfect Operation Phase 11: Paper Lifecycle And Proof Ledger V2",
                str(lifecycle.get("status")),
                _artifact_ref(PAPER_LIFECYCLE_V2_ARTIFACT),
                {
                    "lifecycle_record_count": lifecycle.get("lifecycle_record_count"),
                    "ambiguous_lifecycle_count": lifecycle.get("ambiguous_lifecycle_count"),
                    "stale_accepted_order_count": lifecycle.get("stale_accepted_order_count"),
                    "proof_ledger_status": proof.get("status"),
                    "proof_eligible_count": proof.get("proof_eligible_count"),
                    "proof_rejected_count": proof.get("proof_rejected_count"),
                },
            ),
            "perfect_operation_phase_12_learning_attribution_v2": _phase_record(
                "Perfect Operation Phase 12: Learning Attribution V2",
                str(learning.get("status")),
                _artifact_ref(LEARNING_ATTRIBUTION_V2_ARTIFACT),
                {
                    "attribution_record_count": learning.get("attribution_record_count"),
                    "policy_proposal_count": learning.get("policy_proposal_count"),
                    "policy_mutation_created": False,
                },
            ),
            "perfect_operation_phase_13_dashboard_completion_v2": _phase_record(
                "Perfect Operation Phase 13: Dashboard Completion V2",
                str(dashboard.get("status")),
                _artifact_ref(DASHBOARD_COMPLETION_V2_ARTIFACT),
                {
                    "dashboard_order_passed": dashboard.get("dashboard_order_passed"),
                    "portfolio_consistency_status": dashboard.get("portfolio_consistency_status"),
                    "anti_slop_error_count": dashboard.get("anti_slop_error_count"),
                    "stale_labeled_count": dashboard.get("stale_labeled_count"),
                },
            ),
            "perfect_operation_phase_14_telegram_summary_v2": _phase_record(
                "Perfect Operation Phase 14: Telegram Summary V2",
                str(telegram.get("status")),
                _artifact_ref(TELEGRAM_SUMMARY_V2_ARTIFACT),
                {
                    "message_candidate_count": telegram.get("message_candidate_count"),
                    "message_ready_count": telegram.get("message_ready_count"),
                    "message_rejected_duplicate_count": telegram.get("message_rejected_duplicate_count"),
                    "message_rejected_quality_count": telegram.get("message_rejected_quality_count"),
                    "telegram_live_send_allowed": False,
                },
            ),
        }
    )
    safety = {
        **_safe_dict(current.get("safety")),
        "phase11_to14_v2_outputs_are_review_only": True,
        "paper_only": True,
        "live_capital_enabled": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "telegram_command_path_enabled": False,
    }
    _write_json(
        path,
        {
            **current,
            "schema_version": current.get("schema_version", 1),
            "generated_at": bundle["generated_at"],
            "active_phase": "perfect_operation_phase_14_telegram_summary_v2",
            "phases": phases,
            "safety": safety,
        },
    )


def _write_phase_outputs(bundle: dict[str, Any], settings: Settings | None = None) -> dict[str, str]:
    runtime = _runtime_dir(settings)
    lifecycle_payload, lifecycle_records = bundle["lifecycle"]
    proof_payload, proof_records = bundle["proof"]
    learning_payload, learning_records, policy_proposals = bundle["learning"]
    dashboard_payload, dashboard_order_audit = bundle["dashboard"]
    telegram_payload, telegram_candidates, telegram_dedupe, telegram_receipts, telegram_mirror = bundle["telegram"]
    json_outputs = {
        PAPER_LIFECYCLE_V2_ARTIFACT: lifecycle_payload,
        PAPER_LIFECYCLE_DASHBOARD_V2_ARTIFACT: _dashboard_summary(lifecycle_payload, "qsase_paper_lifecycle_v2"),
        PROOF_LEDGER_V2_ARTIFACT: proof_payload,
        LEARNING_ATTRIBUTION_V2_ARTIFACT: learning_payload,
        LEARNING_ATTRIBUTION_DASHBOARD_V2_ARTIFACT: _dashboard_summary(learning_payload, "qsase_learning_attribution_v2"),
        DASHBOARD_COMPLETION_V2_ARTIFACT: dashboard_payload,
        DASHBOARD_ORDER_AUDIT_V2_ARTIFACT: dashboard_order_audit,
        DASHBOARD_COMPLETION_DASHBOARD_V2_ARTIFACT: _dashboard_summary(dashboard_payload, "qsase_dashboard_completion_v2"),
        TELEGRAM_SUMMARY_V2_ARTIFACT: telegram_payload,
        TELEGRAM_CANDIDATES_V2_ARTIFACT: telegram_candidates,
        TELEGRAM_COMMUNICATIONS_MIRROR_V2_ARTIFACT: telegram_mirror,
        TELEGRAM_SUMMARY_DASHBOARD_V2_ARTIFACT: _dashboard_summary(telegram_payload, "qsase_telegram_summary_v2"),
    }
    jsonl_outputs = {
        PAPER_LIFECYCLE_RECORDS_V2_ARTIFACT: lifecycle_records,
        PROOF_LINEAGE_RECORDS_V2_ARTIFACT: proof_records,
        LEARNING_ATTRIBUTION_RECORDS_V2_ARTIFACT: learning_records,
        POLICY_PROPOSALS_V2_ARTIFACT: policy_proposals,
        TELEGRAM_RECEIPTS_V2_ARTIFACT: telegram_receipts,
    }
    written: dict[str, str] = {}
    for filename, payload in json_outputs.items():
        path = runtime / filename
        _write_json(path, payload)
        written[filename] = str(path)
    for filename, records in jsonl_outputs.items():
        path = runtime / filename
        _write_jsonl(path, records)
        written[filename] = str(path)
    dedupe_path = runtime / TELEGRAM_DEDUPE_V2_ARTIFACT
    existing_dedupe = _read_jsonl(dedupe_path, limit=5000)
    _write_jsonl(dedupe_path, existing_dedupe + telegram_dedupe)
    written[TELEGRAM_DEDUPE_V2_ARTIFACT] = str(dedupe_path)
    event = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": bundle["generated_at"],
        "event": "qsase_phase11_to14_completion_written",
        "lifecycle_record_count": lifecycle_payload.get("lifecycle_record_count"),
        "proof_eligible_count": proof_payload.get("proof_eligible_count"),
        "policy_proposal_count": learning_payload.get("policy_proposal_count"),
        "dashboard_completion_status": dashboard_payload.get("status"),
        "telegram_ready_count": telegram_payload.get("message_ready_count"),
    }
    _append_jsonl(runtime / HISTORY_ARTIFACT, event)
    _append_jsonl(runtime / EVENTS_ARTIFACT, event)
    written[HISTORY_ARTIFACT] = str(runtime / HISTORY_ARTIFACT)
    written[EVENTS_ARTIFACT] = str(runtime / EVENTS_ARTIFACT)
    _update_phase_status(runtime / PHASE_STATUS_ARTIFACT, bundle)
    written[PHASE_STATUS_ARTIFACT] = str(runtime / PHASE_STATUS_ARTIFACT)
    return written


def build_and_write_phase11_to14_completion(settings: Settings | None = None) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    bundle = build_phase11_to14_completion(settings)
    errors: list[str] = []
    errors.extend(f"lifecycle:{error}" for error in validate_payload(bundle["lifecycle"][0], "qsase_paper_lifecycle_v2"))
    errors.extend(f"proof:{error}" for error in validate_payload(bundle["proof"][0], "qsase_proof_ledger_v2"))
    errors.extend(f"learning:{error}" for error in validate_payload(bundle["learning"][0], "qsase_learning_attribution_v2"))
    errors.extend(f"dashboard:{error}" for error in validate_payload(bundle["dashboard"][0], "qsase_dashboard_completion_v2"))
    errors.extend(f"telegram:{error}" for error in validate_payload(bundle["telegram"][0], "qsase_telegram_summary_v2"))
    written = _write_phase_outputs(bundle, settings)
    summary = {
        "generated_at": bundle["generated_at"],
        "lifecycle": bundle["lifecycle"][0],
        "proof": bundle["proof"][0],
        "learning": bundle["learning"][0],
        "dashboard": bundle["dashboard"][0],
        "telegram": bundle["telegram"][0],
    }
    return summary, written, sorted(set(errors))
