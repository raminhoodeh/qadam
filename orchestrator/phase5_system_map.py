"""Q5-13 functional system map dashboard contract.

This module turns the public-safe cockpit state into an explicit system-map
artifact. The dashboard can render these lanes and nodes directly, which keeps
the visible cockpit map aligned with backend status instead of browser-side
inference.
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT


PHASE5_SYSTEM_MAP_SCHEMA_VERSION = 1
SYSTEM_MAP_RUNTIME_ARTIFACT = "phase5_system_map.json"
SYSTEM_MAP_HISTORY = "phase5_system_map_history.jsonl"
SYSTEM_MAP_EVENT_LOG = "phase5_system_map_events.jsonl"
SYSTEM_MAP_EVENT_TYPE = "phase5_system_map_written"
SYSTEM_MAP_COMPONENT = "phase5_system_map"

SYSTEM_MAP_BOUNDARY = (
    "Q5-13 Functional System Map is a public-safe dashboard contract. It can "
    "display backend Layer B state, source posture, blockers, and paper "
    "lifecycle state, but it cannot approve trades, place orders, call brokers "
    "or venues, mutate kill switches, send live alerts, and cannot enable live "
    "capital."
)

REQUIRED_NODE_KEYS: tuple[str, ...] = (
    "watching",
    "yahoo_finance",
    "tradingview_mcp",
    "bookmap_local_bridge",
    "preference_mcp",
    "event_log",
    "live_bridge",
    "worldview",
    "research_analyst",
    "strategy_lead",
    "head_of_quant",
    "shadow_intelligence",
    "signal_integrity_gate",
    "approval_policy_router",
    "risk_agent",
    "kill_switch_ledger",
    "execution_adapter_status",
    "execution_policy",
    "staged_order_contract",
    "broker_reconciliation",
    "paper_submit_receipt",
    "prediction_market_adapter",
    "trade_layer",
    "paper_account",
    "position_monitor",
    "postmortem_loop",
    "telegram_notifier",
    "signal_review",
    "fund_manager_forum",
)

LAYER_B_NODE_KEYS: tuple[str, ...] = (
    "approval_policy_router",
    "risk_agent",
    "kill_switch_ledger",
    "execution_adapter_status",
    "staged_order_contract",
    "paper_submit_receipt",
    "prediction_market_adapter",
    "telegram_notifier",
    "position_monitor",
    "signal_review",
)

AUTHORITY_FIELDS: tuple[str, ...] = (
    "trade_approval_control_enabled",
    "order_place_control_enabled",
    "broker_write_allowed",
    "prediction_market_write_allowed",
    "kill_switch_mutation_authority",
    "live_capital_enabled",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _get(payload: dict[str, Any], path: str, default: Any = None) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict):
            return default
        current = current.get(part)
    if current is None or current == "":
        return default
    return current


def _count_signal_chain_status(
    payload: dict[str, Any],
    step_key: str,
    target_status: str,
) -> int:
    records = _get(payload, "phase5_signal_review.records", []) or []
    if not isinstance(records, list):
        return 0
    count = 0
    for record in records:
        if not isinstance(record, dict):
            continue
        chain = record.get("decision_chain", {})
        if not isinstance(chain, dict):
            continue
        step = chain.get(step_key, {})
        if isinstance(step, dict) and step.get("backend_status") == target_status:
            count += 1
    return count


def _node(
    payload: dict[str, Any],
    *,
    key: str,
    label: str,
    lane: str,
    backend_status_path: str,
    current_process: str,
    authority: str,
    role: str,
    input_text: str,
    output_text: str,
    handoff: str,
    counts: dict[str, Any] | None = None,
    blockers: list[str] | None = None,
    backend_status: Any = None,
) -> dict[str, Any]:
    status = backend_status if backend_status is not None else _get(payload, backend_status_path, "not_exported")
    normalized_status = str(status)
    return {
        "key": key,
        "label": label,
        "lane": lane,
        "role": role,
        "input": input_text,
        "output": output_text,
        "handoff": handoff,
        "backend_status_path": backend_status_path,
        "backend_status": normalized_status,
        "display_status": normalized_status,
        "current_process": current_process,
        "authority": authority,
        "counts": counts or {},
        "blockers": blockers or [],
        "ui_inferred": False,
        "public_safe": True,
        **{field: False for field in AUTHORITY_FIELDS},
    }


def _lanes() -> list[dict[str, Any]]:
    return [
        {
            "key": "observation",
            "title": "Observation",
            "summary": "Canonical and supplemental inputs enter as observations only.",
            "handoff": "Observed facts must be logged before they count.",
            "tone": "online",
            "node_keys": ["watching", "yahoo_finance", "tradingview_mcp", "bookmap_local_bridge", "preference_mcp"],
        },
        {
            "key": "coo_memory",
            "title": "COO Memory",
            "summary": "The orchestrator records state and exposes a safe cockpit mirror.",
            "handoff": "Logged state becomes dashboard state and research input.",
            "tone": "online",
            "node_keys": ["event_log", "live_bridge"],
        },
        {
            "key": "research",
            "title": "Research",
            "summary": "Private priors and models shape questions without execution authority.",
            "handoff": "Research outputs become challenge notes and evidence packets.",
            "tone": "pending",
            "node_keys": [
                "worldview",
                "research_analyst",
                "strategy_lead",
                "head_of_quant",
                "shadow_intelligence",
                "signal_integrity_gate",
            ],
        },
        {
            "key": "quant_risk",
            "title": "Quant + Risk",
            "summary": "Layer B gates expose approval, risk, kill-switch, and venue state.",
            "handoff": "Only passed gates can become paper-trial state.",
            "tone": "blocked",
            "node_keys": [
                "approval_policy_router",
                "risk_agent",
                "kill_switch_ledger",
                "execution_adapter_status",
                "execution_policy",
            ],
        },
        {
            "key": "paper_trial",
            "title": "Paper Trial",
            "summary": "Paper lifecycle state stays blocked until explicit submit approval exists.",
            "handoff": "Closed paper outcomes and lessons return to memory.",
            "tone": "online",
            "node_keys": [
                "staged_order_contract",
                "broker_reconciliation",
                "paper_submit_receipt",
                "prediction_market_adapter",
                "trade_layer",
                "paper_account",
                "position_monitor",
                "postmortem_loop",
            ],
        },
        {
            "key": "members",
            "title": "Members",
            "summary": "Founding Fund Managers see alerts, Signal Review, and governance notes.",
            "handoff": "Human notes improve the system without creating broker authority.",
            "tone": "pending",
            "node_keys": ["telegram_notifier", "signal_review", "fund_manager_forum"],
        },
    ]


def _build_nodes(payload: dict[str, Any]) -> list[dict[str, Any]]:
    watching = _get(payload, "watching", []) or []
    trade_layer = _get(payload, "trade_layer", {}) or {}
    notes = _get(payload, "fund_manager_notes", {}) or {}
    observed = trade_layer.get("watching", []) if isinstance(trade_layer, dict) else []
    candidates = trade_layer.get("candidates", []) if isinstance(trade_layer, dict) else []
    blocked = trade_layer.get("blocked", []) if isinstance(trade_layer, dict) else []
    return [
        _node(
            payload,
            key="watching",
            label="Watched Sources",
            lane="Observation",
            backend_status_path="durable_ingestion.replay_status",
            current_process=(
                f"{len(watching)} public-safe sources; "
                f"{_get(payload, 'durable_ingestion.replayed_source_count', 0)}/"
                f"{_get(payload, 'durable_ingestion.expected_source_count', EXPECTED_SOURCE_COUNT)} "
                "canonical replay coverage"
            ),
            authority="observation_only",
            role="Source desks",
            input_text="Feeds, alerts, charts, and replayed observations",
            output_text="Public-safe observed facts",
            handoff="observed facts",
            counts={
                "source_count": len(watching),
                "canonical_expected": _get(payload, "durable_ingestion.expected_source_count", 0),
                "canonical_replayed": _get(payload, "durable_ingestion.replayed_source_count", 0),
            },
        ),
        _node(
            payload,
            key="yahoo_finance",
            label="Yahoo Finance Supplemental",
            lane="Observation",
            backend_status_path="yahoo_finance.status",
            current_process=(
                "supplemental market confirmation only; "
                f"{_get(payload, 'yahoo_finance.symbol_allowlist_count', 0)} symbols allowlisted"
            ),
            authority="read_only_supplemental",
            role="Market context",
            input_text="Quote, volume, options, news, sector, and session context",
            output_text="Supplemental market confirmation",
            handoff="market context",
            counts={"symbol_allowlist_count": _get(payload, "yahoo_finance.symbol_allowlist_count", 0)},
        ),
        _node(
            payload,
            key="tradingview_mcp",
            label="TradingView MCP Technical",
            lane="Observation",
            backend_status_path="tradingview_mcp.status",
            current_process=(
                "read-only technical analysis; "
                f"{_get(payload, 'tradingview_mcp.technical_context_count', 0)} contexts"
            ),
            authority="read_only_supplemental",
            role="Technical context",
            input_text="Market structure, indicators, volatility, and support/resistance context",
            output_text="Supplemental technical confirmation",
            handoff="technical context",
            counts={
                "technical_context_count": _get(payload, "tradingview_mcp.technical_context_count", 0),
                "obvious_context_count": _get(
                    payload,
                    "tradingview_mcp.obvious_technical_context_count",
                    0,
                ),
            },
        ),
        _node(
            payload,
            key="bookmap_local_bridge",
            label="Bookmap Local Orderflow",
            lane="Observation",
            backend_status_path="bookmap_local_bridge.status",
            current_process=(
                "local read-only orderflow; "
                f"{_get(payload, 'bookmap_local_bridge.orderflow_context_count', 0)} contexts"
            ),
            authority="read_only_supplemental",
            role="Orderflow context",
            input_text="Local order book, liquidity, absorption, imbalance, and range context",
            output_text="Supplemental orderflow confirmation",
            handoff="orderflow context",
            counts={
                "orderflow_context_count": _get(payload, "bookmap_local_bridge.orderflow_context_count", 0),
                "obvious_context_count": _get(
                    payload,
                    "bookmap_local_bridge.obvious_orderflow_context_count",
                    0,
                ),
            },
        ),
        _node(
            payload,
            key="preference_mcp",
            label="Preference/PREF MCP",
            lane="Observation",
            backend_status_path="preference_mcp.status",
            current_process=(
                f"{_get(payload, 'preference_mcp.approved_domain_pack_count', 0)} domain packs; "
                f"promoted sources {_get(payload, 'preference_mcp.source_promotion_promoted_decision_count', 0)}"
            ),
            authority="supplemental_challenge_only",
            role="Supplemental data plane",
            input_text="Prediction-market and real-world signal context",
            output_text="Provenance-gated challenge context",
            handoff="challenge context",
            counts={
                "domain_pack_count": _get(payload, "preference_mcp.approved_domain_pack_count", 0),
                "promoted_source_count": _get(
                    payload,
                    "preference_mcp.source_promotion_promoted_decision_count",
                    0,
                ),
            },
        ),
        _node(
            payload,
            key="event_log",
            label="Event Log",
            lane="COO Memory",
            backend_status_path="modules.event_log.status",
            backend_status=_module_status(payload, "event_log", "online"),
            current_process="records local audit trail and Event Log artifacts",
            authority="source_of_truth",
            role="COO memory",
            input_text="Material module events",
            output_text="Replayable audit trail",
            handoff="logged state",
            counts={"process_event_count": len(_get(payload, "process_console", []) or [])},
        ),
        _node(
            payload,
            key="live_bridge",
            label="Secure Live Bridge",
            lane="COO Memory",
            backend_status_path="live_bridge.status",
            current_process=(
                f"{'/'.join(_get(payload, 'live_bridge.allowed_methods', []) or [])} status only; "
                f"fallback {_get(payload, 'live_bridge.static_fallback', 'static snapshot')}"
            ),
            authority="read_only",
            role="qadam.trade API",
            input_text="Sanitized cockpit status",
            output_text="Authenticated public-safe dashboard state",
            handoff="public-safe dashboard state",
        ),
        _node(
            payload,
            key="worldview",
            label="Worldview Lens",
            lane="Research",
            backend_status_path="decision_philosophy.status",
            current_process=(
                f"{_get(payload, 'decision_philosophy.foundational_prior_count', 0)} "
                "private priors shaping questions, not evidence"
            ),
            authority="prior_only",
            role="Private Edge Layer",
            input_text="Private worldview priors",
            output_text="Sharper questions",
            handoff="questions, not evidence",
        ),
        _node(
            payload,
            key="research_analyst",
            label="Research Analyst",
            lane="Research",
            backend_status_path="modules.research_analyst.status",
            backend_status=_module_status(payload, "research_analyst", "pending"),
            current_process=_module_process(payload, "research_analyst", "Waiting for local triage heartbeat"),
            authority="non_executable",
            role="Research desk",
            input_text="Noisy observations",
            output_text="Shadow analysis",
            handoff="shadow analysis",
        ),
        _node(
            payload,
            key="strategy_lead",
            label="Strategy Lead",
            lane="Research",
            backend_status_path="modules.strategy_lead.status",
            backend_status=_module_status(payload, "strategy_lead", "pending"),
            current_process=_module_process(payload, "strategy_lead", "Waiting for evidence packets"),
            authority="non_executable",
            role="Strategy desk",
            input_text="Evidence packets",
            output_text="Challenge notes",
            handoff="challenge notes",
        ),
        _node(
            payload,
            key="head_of_quant",
            label="Head of Quant",
            lane="Research",
            backend_status_path="quantum_oracle.status",
            current_process=(
                f"{_get(payload, 'quantum_oracle.latest_backend', 'classical_fallback')} "
                f"latest recommendation {_get(payload, 'quantum_oracle.latest_recommendation', 'not_run')}"
            ),
            authority="non_executable",
            role="Quant desk",
            input_text="Bounded scenarios",
            output_text="Oracle check",
            handoff="bounded oracle check",
        ),
        _node(
            payload,
            key="shadow_intelligence",
            label="Shadow Intelligence",
            lane="Research",
            backend_status_path="modules.shadow_intelligence.status",
            backend_status=_module_status(payload, "shadow_intelligence", "pending"),
            current_process=_module_process(payload, "shadow_intelligence", "Hypotheses remain non-executable"),
            authority="shadow_only",
            role="Research queue",
            input_text="Model packets",
            output_text="Hypotheses",
            handoff="hypothesis package",
        ),
        _node(
            payload,
            key="signal_integrity_gate",
            label="Signal Integrity Gate",
            lane="Research",
            backend_status_path="signal_integrity.status",
            backend_status=_get(payload, "cognition.signal_integrity.status", "pending"),
            current_process=(
                f"{_get(payload, 'cognition.signal_integrity.review_count', 0)} reviews; "
                f"{_count_signal_chain_status(payload, 'signal_integrity', 'hold_for_corroboration')} Q5 records held"
            ),
            authority="non_executable",
            role="Signal Auditor",
            input_text="Shadow signals and source evidence",
            output_text="Block, hold, or pass-to-risk state",
            handoff="block or hold",
        ),
        _node(
            payload,
            key="approval_policy_router",
            label="Approval Policy Router",
            lane="Quant + Risk",
            backend_status_path="phase5_signal_review.status",
            current_process=(
                f"{_get(payload, 'phase5_signal_review.signal_review_record_count', 0)} "
                f"decisions visible; {_count_signal_chain_status(payload, 'approval_policy', 'eligible')} eligible"
            ),
            authority="policy_display_only",
            role="Policy gate",
            input_text="Approved-shadow strategy toggles",
            output_text="Replayable approval-policy decisions",
            handoff="policy decision",
            counts={"eligible_count": _count_signal_chain_status(payload, "approval_policy", "eligible")},
        ),
        _node(
            payload,
            key="risk_agent",
            label="Risk Agent",
            lane="Quant + Risk",
            backend_status_path="phase5_signal_review.status",
            current_process=(
                f"{_count_signal_chain_status(payload, 'risk_agent', 'blocked')} blocked "
                f"risk reviews; paper size eligible {_get(payload, 'phase5_paper_order_staging_gate.paper_size_eligible_count', 0)}"
            ),
            authority="risk_display_only",
            role="Risk desk",
            input_text="Policy decisions and source posture",
            output_text="Paper sizing eligibility",
            handoff="risk gate",
        ),
        _node(
            payload,
            key="kill_switch_ledger",
            label="Kill-Switch Ledger",
            lane="Quant + Risk",
            backend_status_path="phase5_kill_switch_ledger.status",
            current_process=(
                f"{_get(payload, 'phase5_kill_switch_ledger.switch_count', 0)} switches; "
                f"{_get(payload, 'phase5_kill_switch_ledger.blocking_switch_count', 0)} blocking"
            ),
            authority="block_only_no_mutation",
            role="Kill-switch ledger",
            input_text="Global, strategy, venue, model, and source scopes",
            output_text="Fail-closed block state",
            handoff="kill-switch hold",
        ),
        _node(
            payload,
            key="execution_adapter_status",
            label="Execution Adapter Status",
            lane="Quant + Risk",
            backend_status_path="phase5_execution_adapter_status.status",
            current_process=(
                f"{_get(payload, 'phase5_execution_adapter_status.adapter_status_count', 0)} venues; "
                f"{_get(payload, 'phase5_execution_adapter_status.read_allowed_count', 0)} read allowed; "
                f"{_get(payload, 'phase5_execution_adapter_status.downstream_staging_allowed_count', 0)} staging allowed"
            ),
            authority="read_only_venue_status",
            role="Venue status",
            input_text="Broker and venue readiness",
            output_text="Read-only venue status",
            handoff="venue state",
        ),
        _node(
            payload,
            key="execution_policy",
            label="Execution Policy",
            lane="Quant + Risk",
            backend_status_path="modules.execution_policy.status",
            backend_status=_module_status(payload, "execution_policy", "blocked"),
            current_process=_module_process(payload, "execution_policy", "Checking kill switches without order authority"),
            authority="write_blocked",
            role="Execution policy",
            input_text="Risk review and kill-switch state",
            output_text="Execution block state",
            handoff="execution blocked",
        ),
        _node(
            payload,
            key="staged_order_contract",
            label="Staged Order Contract",
            lane="Paper Trial",
            backend_status_path="phase5_paper_order_staging_gate.status",
            current_process=(
                f"{_get(payload, 'phase5_paper_order_staging_gate.staged_order_count', 0)} staged; "
                f"{_get(payload, 'phase5_paper_order_staging_gate.blocked_count', 0)} blocked"
            ),
            authority="no_order_creation",
            role="Paper gate",
            input_text="Risk and execution-policy decisions",
            output_text="Blocked staged-order state",
            handoff="staging blocked",
        ),
        _node(
            payload,
            key="broker_reconciliation",
            label="Broker Reconciliation",
            lane="Paper Trial",
            backend_status_path="modules.broker_reconciliation.status",
            backend_status=_module_status(payload, "broker_reconciliation", "blocked"),
            current_process=_module_process(
                payload,
                "broker_reconciliation",
                "Read-only broker echo and reconciliation checks",
            ),
            authority="read_only_broker_reconciliation",
            role="Broker gate",
            input_text="Staged order reviews",
            output_text="Broker echo checks",
            handoff="submit blocked",
        ),
        _node(
            payload,
            key="paper_submit_receipt",
            label="Paper Submit Receipt",
            lane="Paper Trial",
            backend_status_path="phase5_paper_submit_enablement_gate.status",
            current_process=(
                f"{_get(payload, 'phase5_paper_submit_enablement_gate.submit_path_available_count', 0)} "
                f"submit paths; approval {_get(payload, 'phase5_paper_submit_enablement_gate.paper_submit_approval_state', 'missing')}"
            ),
            authority="guarded_path_disabled",
            role="Broker submit gate",
            input_text="Staged paper-order gate state",
            output_text="Paper-submit availability",
            handoff="paper submit blocked",
        ),
        _node(
            payload,
            key="prediction_market_adapter",
            label="Prediction-Market Adapter",
            lane="Paper Trial",
            backend_status_path="phase5_prediction_market_adapter.status",
            current_process=(
                f"{_get(payload, 'phase5_prediction_market_adapter.prediction_market_route_count', 0)} routes; "
                f"{_get(payload, 'phase5_prediction_market_adapter.prediction_market_write_allowed_count', 0)} writes allowed"
            ),
            authority="read_only_context",
            role="Prediction-market context",
            input_text="Polymarket, Kalshi, and supplemental context",
            output_text="Read-only route state",
            handoff="context only",
        ),
        _node(
            payload,
            key="trade_layer",
            label="Trade Layer",
            lane="Paper Trial",
            backend_status_path="trade_layer.store_status",
            current_process=f"{len(observed)} observed; {len(candidates)} candidates; {len(blocked)} blocked",
            authority="write_blocked",
            role="Paper desk",
            input_text="Approved intents",
            output_text="Paper states",
            handoff="paper state",
            counts={
                "observed_signal_count": len(observed),
                "candidate_count": len(candidates),
                "blocked_count": len(blocked),
            },
        ),
        _node(
            payload,
            key="paper_account",
            label="Paper Account Mirror",
            lane="Paper Trial",
            backend_status_path="capital.mirror_status",
            current_process=(
                f"GBP {_get(payload, 'capital.current_balance_gbp', 0)} current; "
                f"{_get(payload, 'capital.open_position_count', 0)} open; "
                f"{_get(payload, 'capital.closed_trade_count', 0)} closed"
            ),
            authority="read_only",
            role="Money mirror",
            input_text="Paper broker state",
            output_text="Balances and positions",
            handoff="closed paper outcomes",
        ),
        _node(
            payload,
            key="position_monitor",
            label="Position Monitor",
            lane="Paper Trial",
            backend_status_path="phase5_position_monitor.status",
            current_process=(
                f"{_get(payload, 'phase5_position_monitor.submitted_order_count', 0)} submitted; "
                f"{_get(payload, 'phase5_position_monitor.open_position_count', 0)} open; "
                f"{_get(payload, 'phase5_position_monitor.closed_trade_count', 0)} closed"
            ),
            authority="read_only_position_state",
            role="Lifecycle monitor",
            input_text="Submitted paper orders and paper-account mirror",
            output_text="Position lifecycle state",
            handoff="position state",
        ),
        _node(
            payload,
            key="postmortem_loop",
            label="Postmortem Loop",
            lane="Paper Trial",
            backend_status_path="capital.closed_trade_count",
            backend_status="waiting",
            current_process=(
                f"{_get(payload, 'capital.postmortem_due_count', 0)} due; "
                f"{_get(payload, 'capital.postmortem_complete_count', 0)} complete"
            ),
            authority="after_action_review",
            role="Learning loop",
            input_text="Closed paper trades",
            output_text="Lessons and weight updates",
            handoff="lessons return to memory",
        ),
        _node(
            payload,
            key="telegram_notifier",
            label="Telegram Bot / Notifier",
            lane="Members",
            backend_status_path="phase5_telegram_notifier.status",
            current_process=(
                f"{_get(payload, 'phase5_telegram_notifier.queued_dry_run_alert_count', 0)} dry-run queued; "
                f"send gate {_get(payload, 'phase5_telegram_notifier.telegram_send_gate', 'disabled')}"
            ),
            authority="dry_run_notify_only",
            role="Member communications",
            input_text="Backend state events",
            output_text="Dry-run notifications",
            handoff="member visibility",
        ),
        _node(
            payload,
            key="signal_review",
            label="Signal Review",
            lane="Members",
            backend_status_path="phase5_signal_review.status",
            current_process=(
                f"{_get(payload, 'phase5_signal_review.signal_review_record_count', 0)} reviews; "
                f"{_get(payload, 'phase5_signal_review.decision_chain_count', 0)} backend decision steps"
            ),
            authority="governance_event_log_only",
            role="Governance desk",
            input_text="Backend decision chain",
            output_text="Governance comments and kill-switch action intents",
            handoff="governance notes",
        ),
        _node(
            payload,
            key="fund_manager_forum",
            label="Fund Manager Forum",
            lane="Members",
            backend_status_path="fund_manager_notes.status",
            current_process=(
                f"{notes.get('comment_count', 0) if isinstance(notes, dict) else 0} governance notes"
            ),
            authority="governance_only",
            role="Governance desk",
            input_text="Member comments",
            output_text="Improvement notes",
            handoff="improvement notes",
        ),
    ]


def _module(payload: dict[str, Any], key: str) -> dict[str, Any]:
    modules = _get(payload, "modules", []) or []
    if not isinstance(modules, list):
        return {}
    for module in modules:
        if isinstance(module, dict) and module.get("key") == key:
            return module
    return {}


def _module_status(payload: dict[str, Any], key: str, default: str) -> str:
    return str(_module(payload, key).get("status") or default)


def _module_process(payload: dict[str, Any], key: str, default: str) -> str:
    return str(_module(payload, key).get("current_process") or default)


def _source_posture(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "canonical": {
            "status": _get(payload, "durable_ingestion.replay_status", "unknown"),
            "expected_source_count": _get(
                payload,
                "durable_ingestion.expected_source_count",
                EXPECTED_SOURCE_COUNT,
            ),
            "replayed_source_count": _get(payload, "durable_ingestion.replayed_source_count", 0),
            "missing_source_count": _get(payload, "durable_ingestion.missing_source_count", 0),
            "authority": "canonical_replay_required",
        },
        "yahoo_finance": {
            "status": _get(payload, "yahoo_finance.status", "not_exported"),
            "role": _get(
                payload,
                "phase5_layer_b_readiness.yahoo_finance_role",
                "supplemental_market_confirmation_only",
            ),
            "enabled": bool(_get(payload, "yahoo_finance.enabled", False)),
            "authority": "supplemental_market_confirmation_only",
        },
        "preference_mcp": {
            "status": _get(payload, "preference_mcp.status", "not_exported"),
            "provenance_status": _get(payload, "preference_mcp.provenance_status", "not_run"),
            "source_36": bool(_get(payload, "phase5_layer_b_readiness.preference_mcp_source_36", False)),
            "source_quorum_credit_allowed": bool(
                _get(payload, "preference_mcp.source_quorum_credit_allowed", False)
            ),
            "promoted_source_count": _get(
                payload,
                "preference_mcp.source_promotion_promoted_decision_count",
                0,
            ),
            "authority": "supplemental_challenge_only",
        },
        "tradingview_mcp": {
            "status": _get(payload, "tradingview_mcp.status", "not_exported"),
            "role": _get(
                payload,
                "tradingview_mcp.technical_confirmation_role",
                "supplemental_technical_confirmation_only",
            ),
            "source_quorum_credit_allowed": bool(
                _get(payload, "tradingview_mcp.source_quorum_credit_allowed", False)
            ),
            "trade_candidate_creation_allowed": bool(
                _get(payload, "tradingview_mcp.trade_candidate_creation_allowed", False)
            ),
            "authority": "supplemental_technical_confirmation_only",
        },
        "bookmap_local_bridge": {
            "status": _get(payload, "bookmap_local_bridge.status", "not_exported"),
            "role": _get(
                payload,
                "bookmap_local_bridge.orderflow_confirmation_role",
                "supplemental_orderflow_confirmation_only",
            ),
            "source_quorum_credit_allowed": bool(
                _get(payload, "bookmap_local_bridge.source_quorum_credit_allowed", False)
            ),
            "trade_candidate_creation_allowed": bool(
                _get(payload, "bookmap_local_bridge.trade_candidate_creation_allowed", False)
            ),
            "bookmap_order_injection_allowed": bool(
                _get(payload, "bookmap_local_bridge.bookmap_order_injection_allowed", False)
            ),
            "bookmap_trading_mode_allowed": bool(
                _get(payload, "bookmap_local_bridge.bookmap_trading_mode_allowed", False)
            ),
            "authority": "supplemental_orderflow_confirmation_only",
        },
    }


def _guardrails(payload: dict[str, Any]) -> dict[str, Any]:
    submitted = int(_get(payload, "phase5_position_monitor.submitted_order_count", 0) or 0)
    open_positions = int(_get(payload, "phase5_position_monitor.open_position_count", 0) or 0)
    closed_trades = int(_get(payload, "phase5_position_monitor.closed_trade_count", 0) or 0)
    trading_state_present = bool(submitted or open_positions or closed_trades)
    return {
        "mode": _get(payload, "mode", "paper"),
        "live_capital_enabled": bool(_get(payload, "capital.live_capital_enabled", False)),
        "phase5_orchestration_start_allowed": bool(
            _get(payload, "phase5_layer_b_readiness.phase5_orchestration_start_allowed", False)
        ),
        "paper_submit_path_available_count": int(
            _get(payload, "phase5_paper_submit_enablement_gate.submit_path_available_count", 0) or 0
        ),
        "paper_submit_approval_state": _get(
            payload,
            "phase5_paper_submit_enablement_gate.paper_submit_approval_state",
            "missing",
        ),
        "submitted_order_count": submitted,
        "open_position_count": open_positions,
        "closed_trade_count": closed_trades,
        "trading_state_present": trading_state_present,
        "dashboard_may_claim_trading": trading_state_present,
        "dashboard_claims_trading_now": False,
        "boundary": (
            "Dashboard may say Qadam is trading only when submitted, open, or "
            "closed paper lifecycle state exists in the backend."
        ),
    }


def build_phase5_system_map(
    payload: dict[str, Any],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated = generated_at or str(payload.get("generated_at") or _now())
    nodes = _build_nodes(payload)
    lanes = _lanes()
    source_posture = _source_posture(payload)
    guardrails = _guardrails(payload)
    unsafe_control_count = sum(
        1
        for node in nodes
        for field in AUTHORITY_FIELDS
        if node.get(field) is True
    )
    if guardrails.get("live_capital_enabled") is True:
        unsafe_control_count += 1
    if guardrails.get("phase5_orchestration_start_allowed") is True:
        unsafe_control_count += 1
    bundle = {
        "schema_version": PHASE5_SYSTEM_MAP_SCHEMA_VERSION,
        "artifact_type": "phase5_system_map",
        "artifact_id": "phase5:q5-13:functional-system-map-dashboard",
        "phase": "Q5",
        "stage": "Q5-13",
        "status": "ok",
        "generated_at": generated,
        "public_safe": True,
        "recorded": False,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_event_count": 0,
        "node_count": len(nodes),
        "lane_count": len(lanes),
        "layer_b_node_count": sum(1 for node in nodes if node["key"] in LAYER_B_NODE_KEYS),
        "required_node_keys": list(REQUIRED_NODE_KEYS),
        "layer_b_node_keys": list(LAYER_B_NODE_KEYS),
        "backend_parity_check_count": len(nodes),
        "backend_parity_error_count": 0,
        "unsafe_control_count": unsafe_control_count,
        "ui_inferred_node_count": sum(1 for node in nodes if node.get("ui_inferred") is not False),
        "source_posture": source_posture,
        "guardrails": guardrails,
        "nodes": nodes,
        "lanes": lanes,
        "boundary": SYSTEM_MAP_BOUNDARY,
        **{field: False for field in AUTHORITY_FIELDS},
    }
    bundle["validation_errors"] = validate_phase5_system_map_bundle(bundle)
    bundle["validation_error_count"] = len(bundle["validation_errors"])
    bundle["status"] = "ok" if not bundle["validation_errors"] else "error"
    return bundle


def _apply_recording_state(
    bundle: dict[str, Any],
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    output = deepcopy(bundle)
    runtime_path, _, _ = phase5_system_map_paths(settings)
    runtime = _read_json(runtime_path)
    if not runtime:
        output["validation_errors"] = validate_phase5_system_map_bundle(output)
        output["validation_error_count"] = len(output["validation_errors"])
        output["status"] = "ok" if not output["validation_errors"] else "error"
        return output
    output["recorded"] = runtime.get("status") == "ok"
    output["event_log_written"] = runtime.get("event_log_written") is True
    output["event_log_event_count"] = int(runtime.get("event_log_event_count", 0) or 0)
    output["validation_errors"] = validate_phase5_system_map_bundle(output)
    output["validation_error_count"] = len(output["validation_errors"])
    output["status"] = "ok" if not output["validation_errors"] else "error"
    return output


def phase5_system_map_public_status(
    payload: dict[str, Any],
    *,
    settings: Settings | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return _apply_recording_state(
        build_phase5_system_map(payload, generated_at=generated_at),
        settings=settings,
    )


def validate_phase5_system_map_bundle(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "phase",
        "stage",
        "status",
        "generated_at",
        "public_safe",
        "event_log_required",
        "event_log_written",
        "node_count",
        "lane_count",
        "layer_b_node_count",
        "backend_parity_check_count",
        "backend_parity_error_count",
        "unsafe_control_count",
        "ui_inferred_node_count",
        "source_posture",
        "guardrails",
        "nodes",
        "lanes",
        "boundary",
    }
    missing = sorted(required_fields - set(bundle))
    if missing:
        errors.append("system_map_missing_fields:" + ",".join(missing))
    if bundle.get("schema_version") != PHASE5_SYSTEM_MAP_SCHEMA_VERSION:
        errors.append("system_map_schema_version_mismatch")
    if bundle.get("artifact_type") != "phase5_system_map":
        errors.append("system_map_artifact_type_mismatch")
    if bundle.get("phase") != "Q5" or bundle.get("stage") != "Q5-13":
        errors.append("system_map_phase_stage_mismatch")
    if bundle.get("public_safe") is not True:
        errors.append("system_map_public_safe_not_true")
    nodes = bundle.get("nodes", [])
    lanes = bundle.get("lanes", [])
    if not isinstance(nodes, list):
        errors.append("system_map_nodes_not_list")
        nodes = []
    if not isinstance(lanes, list):
        errors.append("system_map_lanes_not_list")
        lanes = []
    if bundle.get("node_count") != len(nodes):
        errors.append("system_map_node_count_mismatch")
    if bundle.get("lane_count") != len(lanes):
        errors.append("system_map_lane_count_mismatch")
    node_keys = [node.get("key") for node in nodes if isinstance(node, dict)]
    missing_nodes = sorted(set(REQUIRED_NODE_KEYS) - set(node_keys))
    if missing_nodes:
        errors.append("system_map_required_nodes_missing:" + ",".join(missing_nodes))
    if len(node_keys) != len(set(node_keys)):
        errors.append("system_map_duplicate_node_keys")
    lane_node_keys: list[str] = []
    for lane in lanes:
        if not isinstance(lane, dict):
            errors.append("system_map_lane_not_dict")
            continue
        lane_node_keys.extend(lane.get("node_keys", []))
    missing_from_lanes = sorted(set(node_keys) - set(lane_node_keys))
    if missing_from_lanes:
        errors.append("system_map_nodes_missing_from_lanes:" + ",".join(missing_from_lanes))
    for node in nodes:
        if not isinstance(node, dict):
            errors.append("system_map_node_not_dict")
            continue
        key = str(node.get("key") or "unknown")
        if node.get("backend_status") != node.get("display_status"):
            errors.append(f"system_map_node_status_mismatch:{key}")
        if node.get("ui_inferred") is not False:
            errors.append(f"system_map_node_ui_inferred:{key}")
        if node.get("public_safe") is not True:
            errors.append(f"system_map_node_not_public_safe:{key}")
        if not str(node.get("backend_status_path") or "").strip():
            errors.append(f"system_map_node_backend_path_missing:{key}")
        for field in AUTHORITY_FIELDS:
            if node.get(field) is not False:
                errors.append(f"system_map_node_authority_enabled:{key}:{field}")
    if bundle.get("backend_parity_error_count") != 0:
        errors.append("system_map_backend_parity_errors")
    if bundle.get("ui_inferred_node_count") != 0:
        errors.append("system_map_ui_inferred_nodes")
    if bundle.get("unsafe_control_count") != 0:
        errors.append("system_map_unsafe_controls")
    if bundle.get("layer_b_node_count") != len(LAYER_B_NODE_KEYS):
        errors.append("system_map_layer_b_node_count_mismatch")
    posture = bundle.get("source_posture", {})
    if not isinstance(posture, dict):
        errors.append("system_map_source_posture_invalid")
    else:
        canonical = posture.get("canonical", {})
        yahoo = posture.get("yahoo_finance", {})
        preference = posture.get("preference_mcp", {})
        tradingview = posture.get("tradingview_mcp", {})
        bookmap = posture.get("bookmap_local_bridge", {})
        if canonical.get("expected_source_count") != EXPECTED_SOURCE_COUNT:
            errors.append("system_map_canonical_source_count_mismatch")
        if yahoo.get("role") != "supplemental_market_confirmation_only":
            errors.append("system_map_yahoo_role_invalid")
        if tradingview.get("role") != "supplemental_technical_confirmation_only":
            errors.append("system_map_tradingview_mcp_role_invalid")
        if tradingview.get("source_quorum_credit_allowed") is not False:
            errors.append("system_map_tradingview_mcp_source_quorum_enabled")
        if tradingview.get("trade_candidate_creation_allowed") is not False:
            errors.append("system_map_tradingview_mcp_candidate_creation_enabled")
        if bookmap.get("role") != "supplemental_orderflow_confirmation_only":
            errors.append("system_map_bookmap_role_invalid")
        if bookmap.get("source_quorum_credit_allowed") is not False:
            errors.append("system_map_bookmap_source_quorum_enabled")
        if bookmap.get("trade_candidate_creation_allowed") is not False:
            errors.append("system_map_bookmap_candidate_creation_enabled")
        if bookmap.get("bookmap_order_injection_allowed") is not False:
            errors.append("system_map_bookmap_injection_enabled")
        if bookmap.get("bookmap_trading_mode_allowed") is not False:
            errors.append("system_map_bookmap_trading_mode_enabled")
        if preference.get("source_36") is not False:
            errors.append("system_map_preference_source_36")
        if preference.get("source_quorum_credit_allowed") is not False:
            errors.append("system_map_preference_source_quorum_credit_enabled")
    guardrails = bundle.get("guardrails", {})
    if not isinstance(guardrails, dict):
        errors.append("system_map_guardrails_invalid")
    else:
        if guardrails.get("mode") != "paper":
            errors.append("system_map_mode_not_paper")
        if guardrails.get("live_capital_enabled") is not False:
            errors.append("system_map_live_capital_enabled")
        if guardrails.get("phase5_orchestration_start_allowed") is not False:
            errors.append("system_map_orchestration_start_allowed")
        if guardrails.get("dashboard_claims_trading_now") is True and not guardrails.get(
            "trading_state_present"
        ):
            errors.append("system_map_claims_trading_without_backend_state")
    if bundle.get("event_log_written") is True and bundle.get("event_log_event_count") != 1:
        errors.append("system_map_event_log_count_mismatch")
    boundary = str(bundle.get("boundary") or "")
    if "cannot approve trades" not in boundary or "cannot enable live capital" not in boundary:
        errors.append("system_map_boundary_weak")
    return sorted(set(errors))


def attach_phase5_system_map_event_log(
    bundle: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], tuple[EventLogEntry, ...]]:
    output = deepcopy(bundle)
    log_path = Path(event_log_path or (_runtime_dir(settings) / SYSTEM_MAP_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        SYSTEM_MAP_EVENT_TYPE,
        SYSTEM_MAP_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "node_count": output.get("node_count"),
            "lane_count": output.get("lane_count"),
            "layer_b_node_count": output.get("layer_b_node_count"),
            "backend_parity_error_count": output.get("backend_parity_error_count"),
            "unsafe_control_count": output.get("unsafe_control_count"),
            "dashboard_claims_trading_now": output.get("guardrails", {}).get(
                "dashboard_claims_trading_now"
            ),
            "live_capital_enabled": output.get("guardrails", {}).get("live_capital_enabled"),
            "boundary": output.get("boundary"),
        },
    )
    output["recorded"] = True
    output["event_log_written"] = True
    output["event_log_event_count"] = 1
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_created_at"] = entry.created_at
    output["validation_errors"] = validate_phase5_system_map_bundle(output)
    output["validation_error_count"] = len(output["validation_errors"])
    output["status"] = "ok" if not output["validation_errors"] else "error"
    return output, (entry,)


def phase5_system_map_paths(settings: Settings | None = None) -> tuple[Path, Path, Path]:
    runtime_dir = _runtime_dir(settings)
    return (
        runtime_dir / SYSTEM_MAP_RUNTIME_ARTIFACT,
        runtime_dir / SYSTEM_MAP_HISTORY,
        runtime_dir / SYSTEM_MAP_EVENT_LOG,
    )


def write_phase5_system_map(
    bundle: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(bundle)
    output_path, history_path, default_event_path = phase5_system_map_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase5_system_map_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase5_system_map_bundle(output)
        output["validation_error_count"] = len(output["validation_errors"])
        output["status"] = "ok" if not output["validation_errors"] else "error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase5_system_map_bundle(output)
    output["validation_error_count"] = len(output["validation_errors"])
    output["status"] = "ok" if not output["validation_errors"] else "error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE5_SYSTEM_MAP_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "node_count": output.get("node_count"),
        "lane_count": output.get("lane_count"),
        "layer_b_node_count": output.get("layer_b_node_count"),
        "backend_parity_error_count": output.get("backend_parity_error_count"),
        "unsafe_control_count": output.get("unsafe_control_count"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
