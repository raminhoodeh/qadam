"""QSASE-13 Dashboard Visibility view model.

The dashboard view model mirrors QSASE and PaperOps runtime state as compact,
public-safe decision records. It is read-only: it cannot create trade intents,
qualified setups, approvals, paper orders, broker writes, proof credit, live
capital, or simulated 30-day paper growth trial progress.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qsase_governance_safety_contract import (
    PHASE_STATUS_ARTIFACT,
    universal_authority_flags,
)

SCHEMA_VERSION = "qsase_dashboard_view_model.v1"
PHASE_ID = "qsase_13_dashboard_visibility"
PHASE_NAME = "QSASE-13: Dashboard Visibility"
IMPLEMENTATION_LOG = "docs/qsase-implementation-log.md"

STATUS_ARTIFACT = "qsase_dashboard_status.json"
DECISION_RECORDS_ARTIFACT = "qsase_dashboard_decision_records.json"
SYSTEM_MAP_ARTIFACT = "qsase_dashboard_system_map.json"
PORTFOLIO_SERIES_ARTIFACT = "qsase_dashboard_portfolio_value_series.json"
CURRENT_PORTFOLIO_ARTIFACT = "qsase_dashboard_current_portfolio.json"
TRADING_HISTORY_ARTIFACT = "qsase_dashboard_trading_history.json"
SOURCE_NETWORK_ARTIFACT = "qsase_dashboard_source_network.json"
STRATEGY_UNIVERSE_ARTIFACT = "qsase_dashboard_strategy_universe.json"
PATTERN_LAB_ARTIFACT = "qsase_dashboard_pattern_lab.json"
TRADE_INTENTS_ARTIFACT = "qsase_dashboard_trade_intents.json"
LEARNING_LEDGER_ARTIFACT = "qsase_dashboard_learning_ledger.json"
REPAIR_QUEUE_ARTIFACT = "qsase_dashboard_repair_queue.json"
ANTI_SLOP_ARTIFACT = "qsase_dashboard_anti_slop_audit.json"
HISTORY_ARTIFACT = "qsase_dashboard_view_model_history.jsonl"
EVENTS_ARTIFACT = "qsase_dashboard_view_model_events.jsonl"

ALPACA_PAPER_MIRROR_ARTIFACT = "alpaca_paper_mirror.json"
ALPACA_PAPER_MIRROR_HISTORY_ARTIFACT = "alpaca_paper_mirror.jsonl"
PAPER_POSITIONS_ARTIFACT = "paper_positions.jsonl"
PAPER_ORDERS_ARTIFACT = "paper_orders.jsonl"
PAPER_CLOSED_TRADES_ARTIFACT = "paper_closed_trades.jsonl"
COCKPIT_STATUS_ARTIFACT = "cockpit-status.json"
SELF_MODEL_ARTIFACT = "qsase_self_model.json"
UNIVERSAL_MATRIX_ARTIFACT = "qsase_universal_source_price_matrix.json"
STRATEGY_FAMILY_MAP_ARTIFACT = "qsase_strategy_family_map.json"
STRATEGY_FOUNDRY_ARTIFACT = "qsase_strategy_hypotheses.json"
STRATEGY_HYPOTHESES_ARTIFACT = "qsase_strategy_hypotheses.jsonl"
REJECTED_STRATEGY_HYPOTHESES_ARTIFACT = "qsase_rejected_strategy_hypotheses.jsonl"
AKBER_FILTER_ARTIFACT = "qsase_akber_filter_integration.json"
AKBER_FILTER_RESULTS_ARTIFACT = "qsase_akber_filter_results.jsonl"
LINEAR_LAB_ARTIFACT = "qsase_linear_pattern_lab.json"
LINEAR_RESULTS_ARTIFACT = "qsase_linear_backtest_results.jsonl"
NONLINEAR_LAB_ARTIFACT = "qsase_nonlinear_quantum_pattern_lab.json"
NONLINEAR_RESULTS_ARTIFACT = "qsase_nonlinear_pattern_results.jsonl"
QUANTUM_REVIEWS_ARTIFACT = "qsase_quantum_pattern_reviews.jsonl"
ROUTER_ARTIFACT = "qsase_strategy_router_decisions.json"
ROUTER_DECISIONS_ARTIFACT = "qsase_strategy_router_decisions.jsonl"
PAPEROPS_GATE_ARTIFACT = "qsase_paperops_gate_interface.json"
PAPEROPS_GATE_RECORDS_ARTIFACT = "qsase_paperops_gate_interface.jsonl"
COMPONENT_ATTRIBUTION_LEDGER_ARTIFACT = "qsase_component_attribution_ledger.json"
LEARNING_LEDGER_RECORDS_ARTIFACT = "qsase_component_attribution_ledger.jsonl"
LEARNING_APPROVAL_QUEUE_ARTIFACT = "qsase_learning_approval_queue.json"
PAPEROPS_SUMMARY_ARTIFACT = "paperops_autonomous_pass_summary.json"

DASHBOARD_AUTHORITY_FLAGS = {
    "dashboard_read_only": True,
    "dashboard_mirror_only": True,
    "dashboard_command_disabled": True,
    "broker_write_allowed": False,
    "live_broker_endpoint_allowed": False,
    "paper_order_allowed": False,
    "paper_order_created": False,
    "qualified_setup_created": False,
    "trade_candidate_created": False,
    "trade_intent_created": False,
    "risk_approval_allowed": False,
    "risk_approval_created": False,
    "execution_approval_allowed": False,
    "execution_approval_created": False,
    "strategy_mutation_created": False,
    "source_trust_update_created": False,
    "model_weight_update_created": False,
    "filter_threshold_update_created": False,
    "proof_credit_allowed": False,
    "paper_proof_ledger_credit_allowed": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "simulated_elapsed_time_allowed": False,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
    "live_capital_enabled": False,
}

FALSE_AUTHORITY_FIELDS = {
    key for key, value in DASHBOARD_AUTHORITY_FLAGS.items() if value is False
}

REQUIRED_DECISION_RECORD_FIELDS = (
    "decision_record_id",
    "module",
    "state",
    "headline",
    "reason",
    "blocker",
    "next_allowed_action",
    "authority_boundary",
    "artifact_refs",
    "applied_change",
    "paper_order_created",
    "proof_credit_allowed",
    "live_capital_enabled",
)

GENERIC_AI_PHRASES = (
    "ai-powered",
    "cutting edge",
    "cutting-edge",
    "seamless",
    "holistic",
    "synergy",
    "synergise",
    "unlock potential",
    "revolutionary",
    "game-changing",
    "robust insights",
    "dynamic insights",
    "qadam learned",
    "transformative",
)

PROHIBITED_INTENT_LABELS = {"trade", "order", "approval", "qualified_setup", "paper_order"}

FRESHNESS_THRESHOLDS_SECONDS = {
    ALPACA_PAPER_MIRROR_ARTIFACT: 7200,
    PAPEROPS_SUMMARY_ARTIFACT: 7200,
    COCKPIT_STATUS_ARTIFACT: 7200,
    SELF_MODEL_ARTIFACT: 14400,
    ROUTER_ARTIFACT: 14400,
    PAPEROPS_GATE_ARTIFACT: 14400,
    COMPONENT_ATTRIBUTION_LEDGER_ARTIFACT: 14400,
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


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(_jsonl_line(payload))


def _hash_id(parts: list[Any], prefix: str) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}"


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


def _first_text(*values: Any, default: str = "not_recorded") -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _artifact_ref(filename: str, pointer: str | None = None) -> str:
    base = f"data/runtime/{filename}"
    return f"{base}#{pointer}" if pointer else base


def _dashboard_authority() -> dict[str, Any]:
    return dict(DASHBOARD_AUTHORITY_FLAGS)


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text).astimezone(timezone.utc)
    except ValueError:
        return None


def _file_snapshot(runtime_dir: Path, filename: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    path = runtime_dir / filename
    if not path.exists():
        return {
            "artifact": _artifact_ref(filename),
            "exists": False,
            "generated_at": None,
            "mtime": None,
            "age_seconds": None,
            "freshness_status": "missing",
            "staleness_label": "missing_input",
        }
    loaded = payload if payload is not None else _read_json(path)
    generated_at = loaded.get("generated_at") or loaded.get("snapshot", {}).get("observed_at") or loaded.get("observed_at")
    generated_dt = _parse_timestamp(generated_at)
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    reference_dt = generated_dt or mtime
    age_seconds = int((_now() - reference_dt).total_seconds())
    threshold = FRESHNESS_THRESHOLDS_SECONDS.get(filename, 21600)
    freshness_status = "fresh" if age_seconds <= threshold else "stale_labeled"
    return {
        "artifact": _artifact_ref(filename),
        "exists": True,
        "generated_at": generated_at,
        "mtime": _iso(mtime),
        "age_seconds": age_seconds,
        "freshness_threshold_seconds": threshold,
        "freshness_status": freshness_status,
        "staleness_label": "fresh" if freshness_status == "fresh" else f"stale_over_{threshold}_seconds",
    }


def _load_context(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    json_files = {
        "alpaca_mirror": ALPACA_PAPER_MIRROR_ARTIFACT,
        "cockpit_status": COCKPIT_STATUS_ARTIFACT,
        "self_model": SELF_MODEL_ARTIFACT,
        "universal_matrix": UNIVERSAL_MATRIX_ARTIFACT,
        "strategy_family_map": STRATEGY_FAMILY_MAP_ARTIFACT,
        "strategy_foundry": STRATEGY_FOUNDRY_ARTIFACT,
        "akber_filter": AKBER_FILTER_ARTIFACT,
        "linear_lab": LINEAR_LAB_ARTIFACT,
        "nonlinear_lab": NONLINEAR_LAB_ARTIFACT,
        "router": ROUTER_ARTIFACT,
        "paperops_gate": PAPEROPS_GATE_ARTIFACT,
        "learning_ledger": COMPONENT_ATTRIBUTION_LEDGER_ARTIFACT,
        "learning_approval_queue": LEARNING_APPROVAL_QUEUE_ARTIFACT,
        "paperops_summary": PAPEROPS_SUMMARY_ARTIFACT,
    }
    context: dict[str, Any] = {
        "runtime_dir": runtime,
        **{key: _read_json(runtime / filename) for key, filename in json_files.items()},
        "alpaca_history": _read_jsonl(runtime / ALPACA_PAPER_MIRROR_HISTORY_ARTIFACT, limit=120),
        "paper_positions": _read_jsonl(runtime / PAPER_POSITIONS_ARTIFACT, limit=100),
        "paper_orders": _read_jsonl(runtime / PAPER_ORDERS_ARTIFACT, limit=100),
        "paper_closed_trades": _read_jsonl(runtime / PAPER_CLOSED_TRADES_ARTIFACT, limit=100),
        "strategy_hypotheses": _read_jsonl(runtime / STRATEGY_HYPOTHESES_ARTIFACT, limit=100),
        "rejected_strategy_hypotheses": _read_jsonl(runtime / REJECTED_STRATEGY_HYPOTHESES_ARTIFACT, limit=100),
        "akber_results": _read_jsonl(runtime / AKBER_FILTER_RESULTS_ARTIFACT, limit=100),
        "linear_results": _read_jsonl(runtime / LINEAR_RESULTS_ARTIFACT, limit=100),
        "nonlinear_results": _read_jsonl(runtime / NONLINEAR_RESULTS_ARTIFACT, limit=100),
        "quantum_reviews": _read_jsonl(runtime / QUANTUM_REVIEWS_ARTIFACT, limit=100),
        "router_decisions": _read_jsonl(runtime / ROUTER_DECISIONS_ARTIFACT, limit=100),
        "paperops_gate_records": _read_jsonl(runtime / PAPEROPS_GATE_RECORDS_ARTIFACT, limit=100),
        "learning_records": _read_jsonl(runtime / LEARNING_LEDGER_RECORDS_ARTIFACT, limit=150),
    }
    context["input_snapshots"] = {
        key: _file_snapshot(runtime, filename, context.get(key)) for key, filename in json_files.items()
    }
    context["input_snapshots"]["alpaca_history"] = _file_snapshot(runtime, ALPACA_PAPER_MIRROR_HISTORY_ARTIFACT)
    context["input_snapshots"]["paper_positions"] = _file_snapshot(runtime, PAPER_POSITIONS_ARTIFACT)
    context["input_snapshots"]["paper_orders"] = _file_snapshot(runtime, PAPER_ORDERS_ARTIFACT)
    context["input_snapshots"]["paper_closed_trades"] = _file_snapshot(runtime, PAPER_CLOSED_TRADES_ARTIFACT)
    return context


def _decision_record(
    *,
    module: str,
    state: str,
    headline: str,
    reason: str,
    blocker: str,
    next_allowed_action: str,
    artifact_refs: list[str],
    strategy_family: str = "aggregate",
    evidence: list[str] | None = None,
) -> dict[str, Any]:
    record_id = _hash_id([SCHEMA_VERSION, module, state, headline, artifact_refs], "qsase-dashboard")
    return {
        "schema_version": SCHEMA_VERSION,
        "decision_record_id": record_id,
        "module": module,
        "state": state,
        "headline": headline[:120],
        "strategy_family": strategy_family,
        "evidence": (evidence or [])[:4],
        "reason": reason[:220],
        "blocker": blocker[:120],
        "next_allowed_action": next_allowed_action[:180],
        "authority_boundary": "read_only_dashboard_mirror_no_commands_no_orders_no_proof_no_live_capital",
        "artifact_refs": artifact_refs,
        "applied_change": False,
        "paper_order_created": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "authority": _dashboard_authority(),
    }


def _section_base(artifact_type: str, generated_at: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": artifact_type,
        "generated_at": generated_at,
        "public_safe": True,
        "command_disabled": True,
        "read_only": True,
        "paper_only": True,
        "authority": _dashboard_authority(),
    }


def build_portfolio_value_series(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    artifact = _section_base("qsase_dashboard_portfolio_value_series", generated_at)
    rows: list[dict[str, Any]] = []
    for item in context.get("alpaca_history", []):
        snapshot = item.get("snapshot", {})
        observed_at = snapshot.get("observed_at") or item.get("generated_at")
        value = snapshot.get("current_balance_gbp") or snapshot.get("equity_gbp") or item.get("snapshot", {}).get("source_equity")
        if value is None:
            continue
        rows.append(
            {
                "timestamp": observed_at,
                "portfolio_value": value,
                "equity": snapshot.get("equity_gbp"),
                "cash": snapshot.get("cash_gbp"),
                "display_currency": snapshot.get("display_currency") or item.get("display_currency"),
                "drawdown_pct": snapshot.get("drawdown_pct"),
                "read_only_source": _artifact_ref(ALPACA_PAPER_MIRROR_HISTORY_ARTIFACT),
            }
        )
    if not rows:
        mirror_snapshot = context.get("alpaca_mirror", {}).get("snapshot", {})
        if mirror_snapshot.get("current_balance_gbp") is not None:
            rows.append(
                {
                    "timestamp": mirror_snapshot.get("observed_at"),
                    "portfolio_value": mirror_snapshot.get("current_balance_gbp"),
                    "equity": mirror_snapshot.get("equity_gbp"),
                    "cash": mirror_snapshot.get("cash_gbp"),
                    "display_currency": mirror_snapshot.get("display_currency"),
                    "drawdown_pct": mirror_snapshot.get("drawdown_pct"),
                    "read_only_source": _artifact_ref(ALPACA_PAPER_MIRROR_ARTIFACT),
                }
            )
    artifact.update(
        {
            "status": "portfolio_value_series_available" if rows else "portfolio_value_series_unavailable",
            "line_graph_available": bool(rows),
            "unavailable_reason": None if rows else "alpaca_paper_mirror_history_missing_or_empty",
            "series_count": len(rows),
            "series": rows,
            "latest_value": rows[-1]["portfolio_value"] if rows else None,
            "artifact_refs": [_artifact_ref(ALPACA_PAPER_MIRROR_ARTIFACT), _artifact_ref(ALPACA_PAPER_MIRROR_HISTORY_ARTIFACT)],
            "write_authority": False,
        }
    )
    return artifact


def build_current_portfolio(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    artifact = _section_base("qsase_dashboard_current_portfolio", generated_at)
    rows = [
        {
            "row_type": "open_paper_position_mirror",
            "position_id": row.get("position_id"),
            "instrument": row.get("instrument"),
            "status": row.get("status"),
            "direction": row.get("direction"),
            "quantity": row.get("quantity"),
            "entry_price": row.get("entry_price"),
            "current_price": row.get("current_price"),
            "risk_size": row.get("risk_size_gbp"),
            "unrealized_pnl": row.get("unrealized_pnl_gbp"),
            "source_intent_id": row.get("source_intent_id"),
            "boundary": "read_only_paper_position_mirror_no_close_or_modify",
            "artifact_refs": [_artifact_ref(PAPER_POSITIONS_ARTIFACT)],
            "paper_order_created": False,
            "broker_write_allowed": False,
        }
        for row in context.get("paper_positions", [])
    ]
    artifact.update(
        {
            "status": "current_portfolio_present" if rows else "current_portfolio_explicitly_empty",
            "position_count": len(rows),
            "rows": rows,
            "explicitly_empty": not rows,
            "artifact_refs": [_artifact_ref(PAPER_POSITIONS_ARTIFACT), _artifact_ref(ALPACA_PAPER_MIRROR_ARTIFACT)],
        }
    )
    return artifact


def build_trading_history(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    artifact = _section_base("qsase_dashboard_trading_history", generated_at)
    closed_rows = [
        {
            "row_type": "closed_paper_trade_mirror",
            "trade_id": row.get("trade_id"),
            "instrument": row.get("instrument"),
            "direction": row.get("direction"),
            "opened_at": row.get("opened_at"),
            "closed_at": row.get("closed_at"),
            "realized_pnl": row.get("realized_pnl_gbp"),
            "postmortem_status": row.get("postmortem_status"),
            "source_intent_id": row.get("source_intent_id"),
            "boundary": "mirrored_closed_paper_trade_not_new_proof_credit",
            "artifact_refs": [_artifact_ref(PAPER_CLOSED_TRADES_ARTIFACT)],
        }
        for row in context.get("paper_closed_trades", [])[-50:]
    ]
    order_rows = [
        {
            "row_type": "paper_order_mirror_not_trade_intent",
            "order_id": row.get("order_id"),
            "instrument": row.get("instrument"),
            "direction": row.get("direction"),
            "status": row.get("status"),
            "submitted_at": row.get("submitted_at"),
            "filled_at": row.get("filled_at"),
            "filled_quantity": row.get("filled_quantity"),
            "boundary": "mirrored_order_only_no_create_cancel_replace_or_close",
            "artifact_refs": [_artifact_ref(PAPER_ORDERS_ARTIFACT)],
        }
        for row in context.get("paper_orders", [])[-30:]
    ]
    artifact.update(
        {
            "status": "trading_history_present" if closed_rows or order_rows else "trading_history_explicitly_empty",
            "closed_trade_row_count": len(closed_rows),
            "paper_order_mirror_row_count": len(order_rows),
            "rows": closed_rows + order_rows,
            "explicitly_empty": not (closed_rows or order_rows),
            "artifact_refs": [_artifact_ref(PAPER_CLOSED_TRADES_ARTIFACT), _artifact_ref(PAPER_ORDERS_ARTIFACT)],
        }
    )
    return artifact


def build_source_network(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    artifact = _section_base("qsase_dashboard_source_network", generated_at)
    source_universe = context.get("universal_matrix", {}).get("source_universe", {})
    trading_universe = context.get("universal_matrix", {}).get("trading_universe", {})
    family_payload = source_universe.get("source_families", {})
    category_rows = []
    if isinstance(family_payload, dict):
        for family, row in sorted(family_payload.items()):
            category_rows.append(
                {
                    "family": family,
                    "source_count": row.get("source_count"),
                    "fresh_count": row.get("fresh_count"),
                    "degraded_count": row.get("degraded_count"),
                    "credential_gated_count": row.get("credential_gated_count"),
                    "quorum_contributing_count": row.get("quorum_contributing_count"),
                    "state": "connected" if int(row.get("source_count") or 0) else "empty",
                    "artifact_refs": [_artifact_ref(UNIVERSAL_MATRIX_ARTIFACT, f"source_universe.source_families.{family}")],
                }
            )
    source_rows = [
        {
            "source_key": row.get("source_key"),
            "source_name": row.get("source_name"),
            "family": row.get("source_family"),
            "state": row.get("state"),
            "freshness_status": row.get("freshness_status"),
            "trust_posture": row.get("trust_posture"),
            "quorum_contribution": row.get("source_quorum_contribution", {}).get("can_contribute"),
            "credential_gated": row.get("credential_gated"),
            "trade_candidate_creation_allowed": False,
            "artifact_refs": [_artifact_ref(UNIVERSAL_MATRIX_ARTIFACT, f"source_universe.sources.{index}")],
        }
        for index, row in enumerate(_safe_list(source_universe.get("sources")))
    ]
    trading_rows = [
        {
            "instrument_id": row.get("instrument_id"),
            "symbol": row.get("symbol"),
            "display_name": row.get("display_name"),
            "market_family": row.get("market_family"),
            "paperability_state": row.get("paperability_state"),
            "paper_route_available": row.get("paper_route_available"),
            "qualified_setup_state": row.get("qualified_setup_state"),
            "live_route_enabled": False,
            "paper_order_allowed": False,
            "artifact_refs": [_artifact_ref(UNIVERSAL_MATRIX_ARTIFACT, f"trading_universe.instruments.{index}")],
        }
        for index, row in enumerate(_safe_list(trading_universe.get("instruments")))
    ]
    artifact.update(
        {
            "status": "source_network_visible" if category_rows and source_rows else "source_network_degraded",
            "category_row_count": len(category_rows),
            "source_row_count": len(source_rows),
            "trading_universe_row_count": len(trading_rows),
            "category_rows": category_rows,
            "source_rows": source_rows,
            "trading_universe_rows": trading_rows,
            "artifact_refs": [_artifact_ref(UNIVERSAL_MATRIX_ARTIFACT)],
        }
    )
    return artifact


def _strategy_family_from_router(row: dict[str, Any]) -> str:
    family = row.get("strategy_family")
    if isinstance(family, dict):
        return _first_text(family.get("primary_family"), family.get("mapped_existing_family"), default="unmapped_strategy_family")
    return _first_text(family, row.get("strategy_hypothesis_lineage", {}).get("strategy_family"), default="unmapped_strategy_family")


def build_strategy_universe(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    artifact = _section_base("qsase_dashboard_strategy_universe", generated_at)
    family_map = context.get("strategy_family_map", {})
    known_families = family_map.get("known_families", {}) if isinstance(family_map.get("known_families"), dict) else {}
    router_families = {_strategy_family_from_router(row) for row in context.get("router_decisions", [])}
    all_rows = []
    for family_id, family in sorted(known_families.items()):
        current_state = "currently_in_play_blocked_or_rejected" if family_id in router_families else "available_strategy_family"
        all_rows.append(
            {
                "strategy_family_id": family_id,
                "label": family.get("label") or family_id,
                "catalyst_class": family.get("catalyst_class"),
                "allowed_proxy_set": family.get("allowed_proxy_set", []),
                "source_keywords": family.get("source_keywords", []),
                "instrument_keywords": family.get("instrument_keywords", []),
                "current_state": current_state,
                "currently_in_play": family_id in router_families,
                "artifact_refs": [_artifact_ref(STRATEGY_FAMILY_MAP_ARTIFACT, f"known_families.{family_id}")],
            }
        )
    for family in sorted(router_families - set(known_families.keys())):
        all_rows.append(
            {
                "strategy_family_id": family,
                "label": family.replace("_", " ").title(),
                "catalyst_class": "router_discovered_or_unmapped",
                "allowed_proxy_set": [],
                "source_keywords": [],
                "instrument_keywords": [],
                "current_state": "currently_in_play_blocked_or_rejected",
                "currently_in_play": True,
                "artifact_refs": [_artifact_ref(ROUTER_DECISIONS_ARTIFACT)],
            }
        )
    in_play_rows = [row for row in all_rows if row["currently_in_play"]]
    artifact.update(
        {
            "status": "strategy_universe_visible" if all_rows else "strategy_universe_explicitly_empty",
            "all_strategy_count": len(all_rows),
            "currently_in_play_count": len(in_play_rows),
            "strategy_hypothesis_count": int(context.get("strategy_foundry", {}).get("strategy_hypothesis_count") or 0),
            "rejected_hypothesis_count": len(context.get("rejected_strategy_hypotheses", [])),
            "all_strategy_rows": all_rows,
            "currently_in_play_rows": in_play_rows,
            "artifact_refs": [_artifact_ref(STRATEGY_FAMILY_MAP_ARTIFACT), _artifact_ref(ROUTER_DECISIONS_ARTIFACT)],
        }
    )
    return artifact


def build_pattern_lab(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    artifact = _section_base("qsase_dashboard_pattern_lab", generated_at)
    linear_rows = [
        {
            "pattern_type": "linear",
            "pattern_id": row.get("linear_pattern_id"),
            "source_pattern_id": row.get("source_pattern_id"),
            "instrument": row.get("market_expression", {}).get("instrument"),
            "direction": row.get("market_expression", {}).get("direction"),
            "state": row.get("decision", {}).get("linear_status"),
            "score": row.get("linear_score"),
            "reason": row.get("decision", {}).get("reason"),
            "candidate_for_strategy_foundry": row.get("candidate_for_strategy_foundry"),
            "paper_order_allowed": False,
            "artifact_refs": [_artifact_ref(LINEAR_RESULTS_ARTIFACT, str(row.get("linear_pattern_id")))],
        }
        for row in context.get("linear_results", [])[:20]
    ]
    nonlinear_rows = [
        {
            "pattern_type": "nonlinear",
            "pattern_id": row.get("nonlinear_pattern_id"),
            "source_pattern_id": row.get("source_pattern_id"),
            "linear_pattern_id": row.get("source_linear_pattern_id"),
            "instrument": row.get("market_expression", {}).get("instrument"),
            "state": row.get("decision", {}).get("nonlinear_status"),
            "quantum_review_state": row.get("quantum_review_state"),
            "quantum_review_id": row.get("quantum_review_id"),
            "score": row.get("nonlinear_tests", {}).get("nonlinear_score"),
            "linear_baseline_beaten": row.get("nonlinear_tests", {}).get("linear_baseline_beaten"),
            "paper_order_allowed": False,
            "artifact_refs": [_artifact_ref(NONLINEAR_RESULTS_ARTIFACT, str(row.get("nonlinear_pattern_id")))],
        }
        for row in context.get("nonlinear_results", [])[:20]
    ]
    quantum_rows = [
        {
            "review_id": row.get("quantum_review_id"),
            "state": row.get("review_state"),
            "backend": row.get("backend"),
            "quantum_mode": row.get("quantum_mode"),
            "recommendation": row.get("recommendation"),
            "usefulness_class": row.get("quantum_usefulness", {}).get("usefulness_class"),
            "trade_confirmation": False,
            "artifact_refs": [_artifact_ref(QUANTUM_REVIEWS_ARTIFACT, str(row.get("quantum_review_id")))],
        }
        for row in context.get("quantum_reviews", [])[:20]
    ]
    artifact.update(
        {
            "status": "pattern_lab_visible" if linear_rows or nonlinear_rows else "pattern_lab_degraded",
            "linear_pattern_count": len(linear_rows),
            "nonlinear_pattern_count": len(nonlinear_rows),
            "quantum_review_count": len(quantum_rows),
            "linear_rows": linear_rows,
            "nonlinear_rows": nonlinear_rows,
            "quantum_rows": quantum_rows,
            "artifact_refs": [
                _artifact_ref(LINEAR_LAB_ARTIFACT),
                _artifact_ref(NONLINEAR_LAB_ARTIFACT),
                _artifact_ref(QUANTUM_REVIEWS_ARTIFACT),
            ],
        }
    )
    return artifact


def build_trade_intents(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    artifact = _section_base("qsase_dashboard_trade_intents", generated_at)
    rows = []
    for row in context.get("router_decisions", []):
        decision = row.get("decision", {})
        identity = row.get("candidate_identity", {})
        rows.append(
            {
                "row_type": "trade_intent_review_record",
                "intent_id": row.get("router_decision_id"),
                "strategy_family": _strategy_family_from_router(row),
                "candidate_identity_key": identity.get("candidate_identity_key"),
                "instrument": identity.get("instrument"),
                "thesis": identity.get("thesis"),
                "state": decision.get("router_output"),
                "reason": decision.get("reason"),
                "next_allowed_action": decision.get("next_required_action"),
                "source_quorum": row.get("gates", {}).get("source_quorum"),
                "akber_filter": row.get("gates", {}).get("akber_filter"),
                "quantum_review": row.get("gates", {}).get("quantum_review"),
                "paper_route": row.get("gates", {}).get("paper_route"),
                "is_trade": False,
                "is_order": False,
                "is_approval": False,
                "is_qualified_setup": False,
                "paper_order_created": False,
                "artifact_refs": [_artifact_ref(ROUTER_DECISIONS_ARTIFACT, str(row.get("router_decision_id")))],
            }
        )
    artifact.update(
        {
            "status": "trade_intents_visible" if rows else "trade_intents_explicitly_empty",
            "intent_count": len(rows),
            "rows": rows,
            "explicitly_empty": not rows,
            "rows_are_not_orders": True,
            "rows_are_not_approvals": True,
            "rows_are_not_qualified_setups": True,
            "artifact_refs": [_artifact_ref(ROUTER_DECISIONS_ARTIFACT), _artifact_ref(AKBER_FILTER_RESULTS_ARTIFACT)],
        }
    )
    return artifact


def build_learning_ledger(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    artifact = _section_base("qsase_dashboard_learning_ledger", generated_at)
    rows = [
        {
            "row_type": "learning_decision_record",
            "attribution_record_id": row.get("attribution_record_id"),
            "evidence_class": row.get("evidence_class"),
            "state": row.get("status"),
            "outcome": row.get("dashboard_decision_record", {}).get("outcome"),
            "cause": row.get("dashboard_decision_record", {}).get("cause"),
            "attribution": row.get("dashboard_decision_record", {}).get("attribution"),
            "proposal": row.get("dashboard_decision_record", {}).get("proposal"),
            "applied": False,
            "artifact_refs": [_artifact_ref(LEARNING_LEDGER_RECORDS_ARTIFACT, str(row.get("attribution_record_id")))],
        }
        for row in context.get("learning_records", [])[:30]
    ]
    ledger = context.get("learning_ledger", {})
    artifact.update(
        {
            "status": "learning_ledger_visible" if rows else "learning_ledger_explicitly_empty",
            "row_count": len(rows),
            "rows": rows,
            "attribution_record_count": ledger.get("attribution_record_count"),
            "active_proposal_count": ledger.get("active_proposal_count"),
            "applied_update_count": ledger.get("applied_update_count"),
            "artifact_refs": [_artifact_ref(COMPONENT_ATTRIBUTION_LEDGER_ARTIFACT), _artifact_ref(LEARNING_LEDGER_RECORDS_ARTIFACT)],
        }
    )
    return artifact


def build_repair_queue(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    artifact = _section_base("qsase_dashboard_repair_queue", generated_at)
    rows = []
    for item in _safe_list(context.get("self_model", {}).get("degraded_components")):
        rows.append(
            {
                "repair_queue_id": _hash_id([item.get("component"), item.get("reason")], "qsase-repair"),
                "source": "qsase_self_model",
                "component": item.get("component"),
                "state": "repair_or_review_needed",
                "reason": item.get("reason"),
                "severity": item.get("severity"),
                "next_allowed_action": "repair runtime artifact or source state, then rerun QSASE checks",
                "applied_strategy_change": False,
                "artifact_refs": [_artifact_ref(SELF_MODEL_ARTIFACT, "degraded_components")],
            }
        )
    approval_queue = context.get("learning_approval_queue", {})
    for item in _safe_list(approval_queue.get("queue_items"))[:20]:
        rows.append(
            {
                "repair_queue_id": item.get("approval_queue_id"),
                "source": "learning_approval_queue",
                "component": item.get("proposal_surface"),
                "state": item.get("review_state"),
                "reason": item.get("proposal_type"),
                "severity": "review",
                "next_allowed_action": "human or governance review required before any change",
                "applied_strategy_change": False,
                "artifact_refs": [_artifact_ref(LEARNING_APPROVAL_QUEUE_ARTIFACT, str(item.get("approval_queue_id")))],
            }
        )
    artifact.update(
        {
            "status": "repair_queue_visible" if rows else "repair_queue_explicitly_empty",
            "repair_queue_count": len(rows),
            "rows": rows,
            "artifact_refs": [_artifact_ref(SELF_MODEL_ARTIFACT), _artifact_ref(LEARNING_APPROVAL_QUEUE_ARTIFACT)],
        }
    )
    return artifact


def build_system_map(sections: dict[str, dict[str, Any]], generated_at: str) -> dict[str, Any]:
    artifact = _section_base("qsase_dashboard_system_map", generated_at)
    order = [
        "qsase_snapshot",
        "portfolio_value",
        "current_portfolio",
        "trading_history",
        "source_network",
        "strategy_universe",
        "pattern_lab",
        "trade_intents",
        "router_paperops_state",
        "learning_ledger",
        "repair_queue",
        "freshness",
    ]
    nodes = [
        {
            "node_id": key,
            "label": key.replace("_", " ").title(),
            "state": sections.get(key, {}).get("status", "visible"),
            "artifact_refs": sections.get(key, {}).get("artifact_refs", []),
            "overview_detail_level": "summary_only",
        }
        for key in order
    ]
    artifact.update(
        {
            "status": "system_map_visible",
            "node_count": len(nodes),
            "nodes": nodes,
            "edges": [
                {"from": order[index], "to": order[index + 1], "relationship": "dashboard_flow"}
                for index in range(len(order) - 1)
            ],
            "overview_detail_policy": {
                "detailed_ledgers_in_overview": False,
                "overview_uses_decision_records": True,
                "default_dashboard_keeps_core_sections_visible": True,
            },
            "artifact_refs": [artifact.get("artifact_refs") for artifact in sections.values() if artifact.get("artifact_refs")],
        }
    )
    return artifact


def build_decision_records(sections: dict[str, dict[str, Any]], context: dict[str, Any]) -> dict[str, Any]:
    generated_at = sections["qsase_snapshot"]["generated_at"]
    records = [
        _decision_record(
            module="qsase_snapshot",
            state=sections["qsase_snapshot"]["status"],
            headline="QSASE snapshot labels the current state.",
            reason=sections["qsase_snapshot"]["reason"],
            blocker=sections["qsase_snapshot"]["blocker"],
            next_allowed_action=sections["qsase_snapshot"]["next_allowed_action"],
            artifact_refs=[_artifact_ref(STATUS_ARTIFACT), _artifact_ref(SELF_MODEL_ARTIFACT)],
            evidence=["self-model", "router", "PaperOps", "learning ledger"],
        ),
        _decision_record(
            module="portfolio_value",
            state=sections["portfolio_value"]["status"],
            headline="Portfolio line graph is available.",
            reason="Read-only Alpaca paper mirror provides portfolio value points."
            if sections["portfolio_value"]["line_graph_available"]
            else sections["portfolio_value"]["unavailable_reason"],
            blocker="none" if sections["portfolio_value"]["line_graph_available"] else "portfolio_history_missing",
            next_allowed_action="render line graph from qsase_dashboard_portfolio_value_series",
            artifact_refs=sections["portfolio_value"]["artifact_refs"],
        ),
        _decision_record(
            module="source_network",
            state=sections["source_network"]["status"],
            headline="Source network exposes categories and sources.",
            reason=f"{sections['source_network']['category_row_count']} categories and {sections['source_network']['source_row_count']} source rows are visible.",
            blocker="credential_gated_sources_labeled"
            if any(row.get("credential_gated_count") for row in sections["source_network"].get("category_rows", []))
            else "none",
            next_allowed_action="render source categories, individual sources, and trading universe rows",
            artifact_refs=sections["source_network"]["artifact_refs"],
        ),
        _decision_record(
            module="strategy_universe",
            state=sections["strategy_universe"]["status"],
            headline="Strategy Universe separates all strategies from active reviews.",
            reason=f"{sections['strategy_universe']['all_strategy_count']} strategy families, {sections['strategy_universe']['currently_in_play_count']} currently in play.",
            blocker="no_paper_review_candidate" if sections["strategy_universe"]["currently_in_play_count"] else "none",
            next_allowed_action="show all strategy rows and current in-play rows separately",
            artifact_refs=sections["strategy_universe"]["artifact_refs"],
        ),
        _decision_record(
            module="pattern_lab",
            state=sections["pattern_lab"]["status"],
            headline="Pattern Lab separates linear and nonlinear evidence.",
            reason=f"{sections['pattern_lab']['linear_pattern_count']} linear rows and {sections['pattern_lab']['nonlinear_pattern_count']} nonlinear rows are visible.",
            blocker="quantum_review_is_research_only",
            next_allowed_action="render linear, nonlinear, and quantum review rows without trade authority",
            artifact_refs=sections["pattern_lab"]["artifact_refs"],
        ),
        _decision_record(
            module="trade_intents",
            state=sections["trade_intents"]["status"],
            headline="Trade intents are visible as review records.",
            reason=f"{sections['trade_intents']['intent_count']} router records are shown as intents, not orders.",
            blocker="router_or_akber_safety_boundary",
            next_allowed_action="show intent rows with source quorum, Akber, quantum, and route state",
            artifact_refs=sections["trade_intents"]["artifact_refs"],
        ),
        _decision_record(
            module="router_paperops",
            state=context.get("paperops_gate", {}).get("status", "not_recorded"),
            headline="PaperOps gate state is visible.",
            reason=_first_text(context.get("paperops_gate", {}).get("top_blocking_gate"), default="no paper handoff currently eligible"),
            blocker=_first_text(context.get("paperops_gate", {}).get("top_blocking_gate"), default="none"),
            next_allowed_action="wait for distinct paperable setup or rerun guarded PaperOps checks",
            artifact_refs=[_artifact_ref(ROUTER_ARTIFACT), _artifact_ref(PAPEROPS_GATE_ARTIFACT)],
        ),
        _decision_record(
            module="learning_ledger",
            state=sections["learning_ledger"]["status"],
            headline="Learning ledger is shown as attribution records.",
            reason=f"{sections['learning_ledger']['row_count']} learning rows are visible; applied updates remain zero.",
            blocker="approval_required_for_any_change",
            next_allowed_action="route proposals to review without mutating strategy, source, model, or filter state",
            artifact_refs=sections["learning_ledger"]["artifact_refs"],
        ),
        _decision_record(
            module="repair_queue",
            state=sections["repair_queue"]["status"],
            headline="Repair queue separates defects from strategy discipline.",
            reason=f"{sections['repair_queue']['repair_queue_count']} repair or approval rows are visible.",
            blocker="repair_or_review_needed" if sections["repair_queue"]["repair_queue_count"] else "none",
            next_allowed_action="repair runtime/source gaps or review proposals before any change",
            artifact_refs=sections["repair_queue"]["artifact_refs"],
        ),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_dashboard_decision_records",
        "generated_at": generated_at,
        "status": "decision_records_visible",
        "public_safe": True,
        "command_disabled": True,
        "read_only": True,
        "record_count": len(records),
        "records": records,
        "authority": _dashboard_authority(),
    }


def build_freshness_section(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    artifact = _section_base("qsase_dashboard_freshness", generated_at)
    rows = []
    for name, snapshot in sorted(context.get("input_snapshots", {}).items()):
        rows.append(
            {
                "input": name,
                "artifact": snapshot.get("artifact"),
                "exists": snapshot.get("exists"),
                "freshness_status": snapshot.get("freshness_status"),
                "staleness_label": snapshot.get("staleness_label"),
                "age_seconds": snapshot.get("age_seconds"),
                "generated_at": snapshot.get("generated_at"),
                "next_allowed_action": "refresh source artifact before presenting as current"
                if snapshot.get("freshness_status") == "stale_labeled"
                else "render with recorded timestamp",
            }
        )
    stale_count = sum(1 for row in rows if row["freshness_status"] == "stale_labeled")
    artifact.update(
        {
            "status": "freshness_visible_with_stale_labels" if stale_count else "freshness_visible",
            "freshness_row_count": len(rows),
            "stale_labeled_count": stale_count,
            "rows": rows,
            "artifact_refs": [_artifact_ref(STATUS_ARTIFACT)],
        }
    )
    return artifact


def _build_snapshot_section(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    self_model = context.get("self_model", {})
    router = context.get("router", {})
    paperops_gate = context.get("paperops_gate", {})
    learning = context.get("learning_ledger", {})
    reason = _first_text(
        router.get("why_not_trading_now", {}).get("reason"),
        self_model.get("why_not_trading_now", {}).get("reason"),
        paperops_gate.get("top_blocking_gate"),
        default="qsase_state_recorded",
    )
    blocker = _first_text(paperops_gate.get("top_blocking_gate"), self_model.get("status"), default="none")
    section = _section_base("qsase_dashboard_snapshot", generated_at)
    section.update(
        {
            "status": "qsase_dashboard_snapshot_visible",
            "state": "review_only",
            "reason": reason,
            "blocker": blocker,
            "next_allowed_action": "render decision records and wait for a fresh distinct paperable setup",
            "self_model_status": self_model.get("status"),
            "router_status": router.get("status"),
            "paperops_gate_status": paperops_gate.get("status"),
            "learning_ledger_status": learning.get("status"),
            "artifact_refs": [
                _artifact_ref(SELF_MODEL_ARTIFACT),
                _artifact_ref(ROUTER_ARTIFACT),
                _artifact_ref(PAPEROPS_GATE_ARTIFACT),
                _artifact_ref(COMPONENT_ATTRIBUTION_LEDGER_ARTIFACT),
            ],
        }
    )
    return section


def _generic_phrase_hits(text: str) -> list[str]:
    lowered = text.lower()
    return [phrase for phrase in GENERIC_AI_PHRASES if phrase in lowered]


def run_dashboard_anti_slop_checks(payload: dict[str, Any]) -> dict[str, Any]:
    generated_at = payload["generated_at"]
    errors: list[str] = []
    warnings: list[str] = []
    decision_records = payload.get("decision_records", {}).get("records", [])
    headlines = [record.get("headline") for record in decision_records]
    duplicate_headlines = [headline for headline, count in Counter(headlines).items() if headline and count > 1]
    for headline in duplicate_headlines:
        errors.append(f"duplicate_headline:{headline}")
    for record in decision_records:
        record_id = record.get("decision_record_id")
        for field in REQUIRED_DECISION_RECORD_FIELDS:
            if field not in record or record.get(field) in (None, "", []):
                errors.append(f"decision_record_{record_id}_missing_{field}")
        for field in ("headline", "reason", "next_allowed_action", "blocker"):
            hits = _generic_phrase_hits(str(record.get(field) or ""))
            for hit in hits:
                errors.append(f"decision_record_{record_id}_generic_phrase_{hit}")
        if len(str(record.get("headline") or "")) > 120:
            errors.append(f"decision_record_{record_id}_headline_too_long")
        if len(str(record.get("reason") or "")) > 220:
            errors.append(f"decision_record_{record_id}_reason_too_long")
        if len(str(record.get("next_allowed_action") or "")) > 180:
            errors.append(f"decision_record_{record_id}_next_action_too_long")
        for field in ("applied_change", "paper_order_created", "proof_credit_allowed", "live_capital_enabled"):
            if record.get(field) is not False:
                errors.append(f"decision_record_{record_id}_{field}_must_be_false")
        for field in FALSE_AUTHORITY_FIELDS:
            if record.get("authority", {}).get(field) is not False:
                errors.append(f"decision_record_{record_id}_authority_{field}_must_be_false")
    trade_intents = payload.get("trade_intents", {})
    for row in trade_intents.get("rows", []):
        row_text = " ".join(str(row.get(key) or "") for key in ("row_type", "state"))
        if any(label == row_text for label in PROHIBITED_INTENT_LABELS):
            errors.append(f"trade_intent_{row.get('intent_id')}_invalid_label")
        for field in ("is_trade", "is_order", "is_approval", "is_qualified_setup", "paper_order_created"):
            if row.get(field) is not False:
                errors.append(f"trade_intent_{row.get('intent_id')}_{field}_must_be_false")
    overview_policy = payload.get("system_map", {}).get("overview_detail_policy", {})
    if overview_policy.get("detailed_ledgers_in_overview") is not False:
        errors.append("overview_contains_detailed_ledgers")
    freshness = payload.get("freshness", {})
    for row in freshness.get("rows", []):
        if row.get("freshness_status") == "stale_labeled" and not row.get("staleness_label"):
            errors.append(f"freshness_{row.get('input')}_stale_without_label")
        if row.get("freshness_status") == "missing":
            warnings.append(f"freshness_{row.get('input')}_missing")
    for section_name in (
        "portfolio_value",
        "current_portfolio",
        "trading_history",
        "source_network",
        "strategy_universe",
        "pattern_lab",
        "trade_intents",
        "learning_ledger",
        "repair_queue",
    ):
        section = payload.get(section_name, {})
        if section.get("read_only") is not True or section.get("command_disabled") is not True:
            errors.append(f"{section_name}_read_only_boundary_missing")
        for field in FALSE_AUTHORITY_FIELDS:
            if section.get("authority", {}).get(field) is not False:
                errors.append(f"{section_name}_authority_{field}_must_be_false")
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_dashboard_anti_slop_audit",
        "generated_at": generated_at,
        "status": "anti_slop_passed" if not errors else "anti_slop_failed",
        "public_safe": True,
        "command_disabled": True,
        "read_only": True,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "checks": {
            "duplicate_headlines_rejected": True,
            "generic_ai_prose_rejected": True,
            "trade_intents_not_orders": True,
            "overview_detail_ledgers_excluded": True,
            "stale_state_labeled": True,
            "authority_drift_rejected": True,
        },
        "authority": _dashboard_authority(),
    }


def build_dashboard_view_model(settings: Settings | None = None) -> dict[str, Any]:
    context = _load_context(settings)
    generated_at = _iso(_now())
    sections: dict[str, dict[str, Any]] = {}
    sections["qsase_snapshot"] = _build_snapshot_section(context, generated_at)
    sections["portfolio_value"] = build_portfolio_value_series(context, generated_at)
    sections["current_portfolio"] = build_current_portfolio(context, generated_at)
    sections["trading_history"] = build_trading_history(context, generated_at)
    sections["source_network"] = build_source_network(context, generated_at)
    sections["strategy_universe"] = build_strategy_universe(context, generated_at)
    sections["pattern_lab"] = build_pattern_lab(context, generated_at)
    sections["trade_intents"] = build_trade_intents(context, generated_at)
    sections["learning_ledger"] = build_learning_ledger(context, generated_at)
    sections["repair_queue"] = build_repair_queue(context, generated_at)
    sections["freshness"] = build_freshness_section(context, generated_at)
    sections["router_paperops_state"] = {
        "status": context.get("paperops_gate", {}).get("status", "not_recorded"),
        "artifact_refs": [_artifact_ref(ROUTER_ARTIFACT), _artifact_ref(PAPEROPS_GATE_ARTIFACT)],
    }
    system_map = build_system_map(sections, generated_at)
    sections["system_map"] = system_map
    decision_records = build_decision_records(sections, context)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_dashboard_view_model",
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "generated_at": generated_at,
        "status": "qsase_dashboard_visibility_ready",
        "public_safe": True,
        "command_disabled": True,
        "read_only": True,
        "paper_only": True,
        "proposal_first": True,
        "default_dashboard_sections_visible": True,
        "overview_detail_policy": system_map["overview_detail_policy"],
        "portfolio_value_line_graph_state": sections["portfolio_value"]["status"],
        "current_portfolio_state": sections["current_portfolio"]["status"],
        "trading_history_state": sections["trading_history"]["status"],
        "source_network_state": sections["source_network"]["status"],
        "strategy_universe_state": sections["strategy_universe"]["status"],
        "pattern_lab_state": sections["pattern_lab"]["status"],
        "trade_intents_state": sections["trade_intents"]["status"],
        "learning_ledger_state": sections["learning_ledger"]["status"],
        "repair_queue_state": sections["repair_queue"]["status"],
        "freshness_state": sections["freshness"]["status"],
        "portfolio_value_series_count": sections["portfolio_value"]["series_count"],
        "current_position_count": sections["current_portfolio"]["position_count"],
        "trading_history_row_count": len(sections["trading_history"]["rows"]),
        "source_category_row_count": sections["source_network"]["category_row_count"],
        "source_row_count": sections["source_network"]["source_row_count"],
        "trading_universe_row_count": sections["source_network"]["trading_universe_row_count"],
        "all_strategy_count": sections["strategy_universe"]["all_strategy_count"],
        "currently_in_play_count": sections["strategy_universe"]["currently_in_play_count"],
        "linear_pattern_count": sections["pattern_lab"]["linear_pattern_count"],
        "nonlinear_pattern_count": sections["pattern_lab"]["nonlinear_pattern_count"],
        "trade_intent_count": sections["trade_intents"]["intent_count"],
        "learning_ledger_row_count": sections["learning_ledger"]["row_count"],
        "repair_queue_count": sections["repair_queue"]["repair_queue_count"],
        "stale_labeled_count": sections["freshness"]["stale_labeled_count"],
        "applied_change_count": 0,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "paper_growth_trial_calendar_advanced": False,
        "simulated_elapsed_time_allowed": False,
        "view_model_refs": {
            "decision_records": _artifact_ref(DECISION_RECORDS_ARTIFACT),
            "system_map": _artifact_ref(SYSTEM_MAP_ARTIFACT),
            "portfolio_value_series": _artifact_ref(PORTFOLIO_SERIES_ARTIFACT),
            "current_portfolio": _artifact_ref(CURRENT_PORTFOLIO_ARTIFACT),
            "trading_history": _artifact_ref(TRADING_HISTORY_ARTIFACT),
            "source_network": _artifact_ref(SOURCE_NETWORK_ARTIFACT),
            "strategy_universe": _artifact_ref(STRATEGY_UNIVERSE_ARTIFACT),
            "pattern_lab": _artifact_ref(PATTERN_LAB_ARTIFACT),
            "trade_intents": _artifact_ref(TRADE_INTENTS_ARTIFACT),
            "learning_ledger": _artifact_ref(LEARNING_LEDGER_ARTIFACT),
            "repair_queue": _artifact_ref(REPAIR_QUEUE_ARTIFACT),
            "anti_slop": _artifact_ref(ANTI_SLOP_ARTIFACT),
        },
        "qsase_snapshot": sections["qsase_snapshot"],
        "portfolio_value": sections["portfolio_value"],
        "current_portfolio": sections["current_portfolio"],
        "trading_history": sections["trading_history"],
        "source_network": sections["source_network"],
        "strategy_universe": sections["strategy_universe"],
        "pattern_lab": sections["pattern_lab"],
        "trade_intents": sections["trade_intents"],
        "learning_ledger": sections["learning_ledger"],
        "repair_queue": sections["repair_queue"],
        "freshness": sections["freshness"],
        "system_map": system_map,
        "decision_records": decision_records,
        "input_snapshots": context.get("input_snapshots", {}),
        "authority": universal_authority_flags(),
        "authority_flags": _dashboard_authority(),
    }
    anti_slop = run_dashboard_anti_slop_checks(payload)
    payload["anti_slop_audit"] = anti_slop
    if anti_slop["error_count"]:
        payload["status"] = "qsase_dashboard_visibility_blocked"
    elif payload["stale_labeled_count"]:
        payload["status"] = "qsase_dashboard_visibility_degraded"
    return payload


def _status_summary(payload: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "schema_version",
        "artifact_type",
        "phase_id",
        "phase_name",
        "generated_at",
        "status",
        "public_safe",
        "command_disabled",
        "read_only",
        "paper_only",
        "proposal_first",
        "default_dashboard_sections_visible",
        "overview_detail_policy",
        "portfolio_value_line_graph_state",
        "current_portfolio_state",
        "trading_history_state",
        "source_network_state",
        "strategy_universe_state",
        "pattern_lab_state",
        "trade_intents_state",
        "learning_ledger_state",
        "repair_queue_state",
        "freshness_state",
        "portfolio_value_series_count",
        "current_position_count",
        "trading_history_row_count",
        "source_category_row_count",
        "source_row_count",
        "trading_universe_row_count",
        "all_strategy_count",
        "currently_in_play_count",
        "linear_pattern_count",
        "nonlinear_pattern_count",
        "trade_intent_count",
        "learning_ledger_row_count",
        "repair_queue_count",
        "stale_labeled_count",
        "applied_change_count",
        "paper_order_created_count",
        "broker_write_count",
        "proof_credit_allowed",
        "live_capital_enabled",
        "paper_growth_trial_calendar_advanced",
        "simulated_elapsed_time_allowed",
        "view_model_refs",
        "authority",
        "authority_flags",
    )
    return {key: payload[key] for key in keys}


def load_dashboard_view_model(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    status = _read_json(runtime / STATUS_ARTIFACT)
    if not status:
        return {}
    status["decision_records"] = _read_json(runtime / DECISION_RECORDS_ARTIFACT)
    status["system_map"] = _read_json(runtime / SYSTEM_MAP_ARTIFACT)
    status["portfolio_value"] = _read_json(runtime / PORTFOLIO_SERIES_ARTIFACT)
    status["current_portfolio"] = _read_json(runtime / CURRENT_PORTFOLIO_ARTIFACT)
    status["trading_history"] = _read_json(runtime / TRADING_HISTORY_ARTIFACT)
    status["source_network"] = _read_json(runtime / SOURCE_NETWORK_ARTIFACT)
    status["strategy_universe"] = _read_json(runtime / STRATEGY_UNIVERSE_ARTIFACT)
    status["pattern_lab"] = _read_json(runtime / PATTERN_LAB_ARTIFACT)
    status["trade_intents"] = _read_json(runtime / TRADE_INTENTS_ARTIFACT)
    status["learning_ledger"] = _read_json(runtime / LEARNING_LEDGER_ARTIFACT)
    status["repair_queue"] = _read_json(runtime / REPAIR_QUEUE_ARTIFACT)
    status["anti_slop_audit"] = _read_json(runtime / ANTI_SLOP_ARTIFACT)
    return status


def validate_dashboard_view_model(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("artifact_type") != "qsase_dashboard_view_model":
        errors.append("artifact_type_invalid")
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if payload.get("status") not in {
        "qsase_dashboard_visibility_ready",
        "qsase_dashboard_visibility_degraded",
        "qsase_dashboard_visibility_blocked",
    }:
        errors.append("status_invalid")
    for key in ("public_safe", "command_disabled", "read_only", "paper_only", "proposal_first", "default_dashboard_sections_visible"):
        if payload.get(key) is not True:
            errors.append(f"{key}_must_be_true")
    for key in (
        "proof_credit_allowed",
        "live_capital_enabled",
        "paper_growth_trial_calendar_advanced",
        "simulated_elapsed_time_allowed",
    ):
        if payload.get(key) is not False:
            errors.append(f"{key}_must_be_false")
    for key in ("applied_change_count", "paper_order_created_count", "broker_write_count"):
        if int(payload.get(key, -1) or 0) != 0:
            errors.append(f"{key}_must_be_zero")
    if any(value is not False for value in payload.get("authority", {}).values()):
        errors.append("universal_authority_flags_must_all_be_false")
    for field in FALSE_AUTHORITY_FIELDS:
        if payload.get("authority_flags", {}).get(field) is not False:
            errors.append(f"dashboard_authority_{field}_must_be_false")
    if payload.get("portfolio_value", {}).get("line_graph_available") is not True and not payload.get("portfolio_value", {}).get("unavailable_reason"):
        errors.append("portfolio_value_line_graph_missing_without_reason")
    if not isinstance(payload.get("current_portfolio", {}).get("rows"), list):
        errors.append("current_portfolio_rows_missing")
    if not isinstance(payload.get("trading_history", {}).get("rows"), list):
        errors.append("trading_history_rows_missing")
    if int(payload.get("source_network", {}).get("category_row_count") or 0) <= 0:
        errors.append("source_category_rows_missing")
    if int(payload.get("source_network", {}).get("source_row_count") or 0) <= 0:
        errors.append("source_rows_missing")
    if int(payload.get("source_network", {}).get("trading_universe_row_count") or 0) <= 0:
        errors.append("trading_universe_rows_missing")
    if int(payload.get("strategy_universe", {}).get("all_strategy_count") or 0) <= 0:
        errors.append("strategy_universe_rows_missing")
    if "currently_in_play_rows" not in payload.get("strategy_universe", {}):
        errors.append("strategy_currently_in_play_rows_missing")
    if int(payload.get("pattern_lab", {}).get("linear_pattern_count") or 0) <= 0:
        errors.append("linear_pattern_rows_missing")
    if int(payload.get("pattern_lab", {}).get("nonlinear_pattern_count") or 0) <= 0:
        errors.append("nonlinear_pattern_rows_missing")
    if "rows" not in payload.get("trade_intents", {}):
        errors.append("trade_intent_rows_missing")
    for row in payload.get("trade_intents", {}).get("rows", []):
        for field in ("is_trade", "is_order", "is_approval", "is_qualified_setup", "paper_order_created"):
            if row.get(field) is not False:
                errors.append(f"trade_intent_{row.get('intent_id')}_{field}_must_be_false")
    if not payload.get("decision_records", {}).get("records"):
        errors.append("decision_records_missing")
    if payload.get("system_map", {}).get("overview_detail_policy", {}).get("detailed_ledgers_in_overview") is not False:
        errors.append("overview_contains_detailed_ledgers")
    if not payload.get("learning_ledger", {}).get("rows"):
        errors.append("learning_ledger_rows_missing")
    if "rows" not in payload.get("repair_queue", {}):
        errors.append("repair_queue_rows_missing")
    anti_slop = payload.get("anti_slop_audit", {})
    if anti_slop.get("status") != "anti_slop_passed":
        errors.extend(anti_slop.get("errors", []) or ["anti_slop_not_passed"])
    return sorted(set(errors))


def build_qsase_phase_implementation_status(payload: dict[str, Any]) -> dict[str, Any]:
    runtime_dir = _runtime_dir()
    existing = _read_json(runtime_dir / PHASE_STATUS_ARTIFACT)
    phases = existing.get("phases") if isinstance(existing.get("phases"), dict) else {}
    phases[PHASE_ID] = {
        "name": PHASE_NAME,
        "status": payload["status"],
        "artifact_path": f"data/runtime/{STATUS_ARTIFACT}",
        "decision_records_path": f"data/runtime/{DECISION_RECORDS_ARTIFACT}",
        "system_map_path": f"data/runtime/{SYSTEM_MAP_ARTIFACT}",
        "portfolio_value_series_path": f"data/runtime/{PORTFOLIO_SERIES_ARTIFACT}",
        "source_network_path": f"data/runtime/{SOURCE_NETWORK_ARTIFACT}",
        "strategy_universe_path": f"data/runtime/{STRATEGY_UNIVERSE_ARTIFACT}",
        "pattern_lab_path": f"data/runtime/{PATTERN_LAB_ARTIFACT}",
        "trade_intents_path": f"data/runtime/{TRADE_INTENTS_ARTIFACT}",
        "learning_ledger_path": f"data/runtime/{LEARNING_LEDGER_ARTIFACT}",
        "anti_slop_path": f"data/runtime/{ANTI_SLOP_ARTIFACT}",
        "portfolio_value_series_count": payload["portfolio_value_series_count"],
        "current_position_count": payload["current_position_count"],
        "trading_history_row_count": payload["trading_history_row_count"],
        "source_category_row_count": payload["source_category_row_count"],
        "source_row_count": payload["source_row_count"],
        "all_strategy_count": payload["all_strategy_count"],
        "currently_in_play_count": payload["currently_in_play_count"],
        "linear_pattern_count": payload["linear_pattern_count"],
        "nonlinear_pattern_count": payload["nonlinear_pattern_count"],
        "trade_intent_count": payload["trade_intent_count"],
        "learning_ledger_row_count": payload["learning_ledger_row_count"],
        "repair_queue_count": payload["repair_queue_count"],
        "anti_slop_error_count": payload["anti_slop_audit"]["error_count"],
        "paper_only": True,
        "read_only": True,
        "public_safe": True,
        "no_authority_created": True,
        "no_paper_orders_created": True,
        "no_broker_writes": True,
        "no_proof_credit_granted": True,
        "later_qsase_phases_implemented": False,
    }
    return {
        "schema_version": 1,
        "generated_at": payload["generated_at"],
        "active_phase": PHASE_ID,
        "phases": phases,
        "safety": payload["authority"],
    }


def _append_implementation_log(payload: dict[str, Any]) -> None:
    log_path = _repo_root() / IMPLEMENTATION_LOG
    log_path.parent.mkdir(parents=True, exist_ok=True)
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else "# QSASE Implementation Log\n"
    marker = f"<!-- {PHASE_ID} -->"
    entry = (
        f"{marker}\n"
        f"## QSASE-13: Dashboard Visibility\n\n"
        f"- Generated at: `{payload.get('generated_at')}`\n"
        f"- Status: `{payload.get('status')}`\n"
        f"- Runtime artifact: `data/runtime/{STATUS_ARTIFACT}`\n"
        f"- Portfolio series / positions / trading history rows: `{payload.get('portfolio_value_series_count')}` / `{payload.get('current_position_count')}` / `{payload.get('trading_history_row_count')}`\n"
        f"- Source categories / sources / trading universe rows: `{payload.get('source_category_row_count')}` / `{payload.get('source_row_count')}` / `{payload.get('trading_universe_row_count')}`\n"
        f"- Strategy families / in-play / linear / nonlinear / trade-intent rows: `{payload.get('all_strategy_count')}` / `{payload.get('currently_in_play_count')}` / `{payload.get('linear_pattern_count')}` / `{payload.get('nonlinear_pattern_count')}` / `{payload.get('trade_intent_count')}`\n"
        f"- Learning / repair / anti-slop errors: `{payload.get('learning_ledger_row_count')}` / `{payload.get('repair_queue_count')}` / `{payload.get('anti_slop_audit', {}).get('error_count')}`\n"
        f"- Safety: dashboard artifacts are read-only decision records; no commands, trade candidates, qualified setups, approvals, paper orders, broker writes, live capital, 30-day paper growth trial calendar advancement, or paper proof ledger credit created.\n"
    )
    if marker in existing:
        before = existing.split(marker, 1)[0].rstrip()
        updated = before + "\n\n" + entry
    elif existing.endswith("\n"):
        updated = existing + "\n" + entry
    else:
        updated = existing + "\n\n" + entry
    log_path.write_text(updated, encoding="utf-8")


def write_dashboard_view_model(
    payload: dict[str, Any],
    settings: Settings | None = None,
    *,
    append_history: bool = True,
    append_log: bool = True,
) -> dict[str, str]:
    runtime = _runtime_dir(settings)
    runtime.mkdir(parents=True, exist_ok=True)
    paths = {
        "status": runtime / STATUS_ARTIFACT,
        "decision_records": runtime / DECISION_RECORDS_ARTIFACT,
        "system_map": runtime / SYSTEM_MAP_ARTIFACT,
        "portfolio_value": runtime / PORTFOLIO_SERIES_ARTIFACT,
        "current_portfolio": runtime / CURRENT_PORTFOLIO_ARTIFACT,
        "trading_history": runtime / TRADING_HISTORY_ARTIFACT,
        "source_network": runtime / SOURCE_NETWORK_ARTIFACT,
        "strategy_universe": runtime / STRATEGY_UNIVERSE_ARTIFACT,
        "pattern_lab": runtime / PATTERN_LAB_ARTIFACT,
        "trade_intents": runtime / TRADE_INTENTS_ARTIFACT,
        "learning_ledger": runtime / LEARNING_LEDGER_ARTIFACT,
        "repair_queue": runtime / REPAIR_QUEUE_ARTIFACT,
        "anti_slop": runtime / ANTI_SLOP_ARTIFACT,
        "phase_status": runtime / PHASE_STATUS_ARTIFACT,
    }
    _write_json(paths["status"], _status_summary(payload))
    _write_json(paths["decision_records"], payload["decision_records"])
    _write_json(paths["system_map"], payload["system_map"])
    _write_json(paths["portfolio_value"], payload["portfolio_value"])
    _write_json(paths["current_portfolio"], payload["current_portfolio"])
    _write_json(paths["trading_history"], payload["trading_history"])
    _write_json(paths["source_network"], payload["source_network"])
    _write_json(paths["strategy_universe"], payload["strategy_universe"])
    _write_json(paths["pattern_lab"], payload["pattern_lab"])
    _write_json(paths["trade_intents"], payload["trade_intents"])
    _write_json(paths["learning_ledger"], payload["learning_ledger"])
    _write_json(paths["repair_queue"], payload["repair_queue"])
    _write_json(paths["anti_slop"], payload["anti_slop_audit"])
    _write_json(paths["phase_status"], build_qsase_phase_implementation_status(payload))
    written = {key: str(path) for key, path in paths.items()}
    if append_history:
        history_path = runtime / HISTORY_ARTIFACT
        events_path = runtime / EVENTS_ARTIFACT
        _append_jsonl(
            history_path,
            {
                "generated_at": payload["generated_at"],
                "status": payload["status"],
                "portfolio_value_series_count": payload["portfolio_value_series_count"],
                "source_row_count": payload["source_row_count"],
                "all_strategy_count": payload["all_strategy_count"],
                "trade_intent_count": payload["trade_intent_count"],
                "learning_ledger_row_count": payload["learning_ledger_row_count"],
                "anti_slop_error_count": payload["anti_slop_audit"]["error_count"],
                "no_authority_created": True,
            },
        )
        _append_jsonl(
            events_path,
            {
                "generated_at": payload["generated_at"],
                "event_type": "qsase_dashboard_view_model_written",
                "status": payload["status"],
                "public_safe": True,
                "read_only": True,
                "anti_slop_passed": payload["anti_slop_audit"]["error_count"] == 0,
            },
        )
        written["history"] = str(history_path)
        written["events"] = str(events_path)
    if append_log:
        _append_implementation_log(payload)
        written["implementation_log"] = str(_repo_root() / IMPLEMENTATION_LOG)
    return written


def build_and_write_dashboard_view_model(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    payload = build_dashboard_view_model(settings)
    errors = validate_dashboard_view_model(payload)
    written = write_dashboard_view_model(payload, settings)
    return payload, written, errors


def validate_dashboard_anti_slop(payload: dict[str, Any]) -> list[str]:
    audit = run_dashboard_anti_slop_checks(payload)
    return audit.get("errors", [])


def validate_negative_dashboard_view_model_probes() -> list[str]:
    base = build_dashboard_view_model()
    errors: list[str] = []
    duplicate_probe = copy.deepcopy(base)
    duplicate_probe["decision_records"]["records"][1]["headline"] = duplicate_probe["decision_records"]["records"][0]["headline"]
    duplicate_probe["anti_slop_audit"] = run_dashboard_anti_slop_checks(duplicate_probe)
    if not any("duplicate_headline" in error for error in validate_dashboard_view_model(duplicate_probe)):
        errors.append("negative_probe_failed_for_duplicate_headline")
    generic_probe = copy.deepcopy(base)
    generic_probe["decision_records"]["records"][0]["reason"] = "AI-powered seamless dynamic insights"
    generic_probe["anti_slop_audit"] = run_dashboard_anti_slop_checks(generic_probe)
    if not any("generic_phrase" in error for error in validate_dashboard_view_model(generic_probe)):
        errors.append("negative_probe_failed_for_generic_phrase")
    authority_probe = copy.deepcopy(base)
    authority_probe["trade_intents"]["rows"][0]["is_order"] = True
    authority_probe["anti_slop_audit"] = run_dashboard_anti_slop_checks(authority_probe)
    if not any("is_order" in error for error in validate_dashboard_view_model(authority_probe)):
        errors.append("negative_probe_failed_for_trade_intent_order_label")
    proof_probe = copy.deepcopy(base)
    proof_probe["proof_credit_allowed"] = True
    if not any("proof_credit_allowed" in error for error in validate_dashboard_view_model(proof_probe)):
        errors.append("negative_probe_failed_for_proof_credit")
    return errors


if __name__ == "__main__":
    artifact = build_dashboard_view_model()
    print(_json_dump(_status_summary(artifact)))
