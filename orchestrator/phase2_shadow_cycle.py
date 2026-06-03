"""Phase 2 shadow-intelligence cycle.

This cycle pulls read-only source observations into the Research Analyst queue,
runs deterministic shadow triage, optionally calls the local LM Studio model,
and queues a Strategy Lead shadow handoff. It has no broker-write or execution
authority.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from orchestrator.adapters import (
    fetch_fred_live_sync,
    fetch_fred_sample,
    fetch_nasa_firms_live_sync,
    fetch_nasa_firms_sample,
    fetch_rss_live_sync,
    fetch_rss_sample,
)
from orchestrator.agent_runtime import create_shadow_triage_packet
from orchestrator.broker_reconciliation import run_broker_reconciliation_contract
from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.execution_policy import run_execution_policy_router
from orchestrator.intelligence import (
    run_local_research_analyst_inference,
    run_research_shadow_triage_queue,
)
from orchestrator.market_context import run_market_context_packet_cycle
from orchestrator.paper_account import paper_account_shadow_context
from orchestrator.paper_submit_receipt import run_paper_submit_receipt_contract
from orchestrator.postgres_store import durable_source_observation_replay
from orchestrator.preference_mcp_shadow_context import (
    build_preference_shadow_context,
    preference_shadow_packet_context,
    write_preference_shadow_context,
)
from orchestrator.research_goal import ResearchGoal, ResearchGoalStore, research_goal_summary
from orchestrator.risk_agent import run_risk_policy_router
from orchestrator.signal_integrity import run_signal_integrity_gate
from orchestrator.staged_paper_order import run_staged_paper_order_contract
from orchestrator.strategy_research_intake import strategy_research_decision_context
from orchestrator.phase1_live_adapters import (
    fetch_phase1_live_adapter_live_sync,
    fetch_phase1_live_adapter_sample,
)
from orchestrator.strategy_lead import StrategyLeadShadowStore, queue_strategy_lead_shadow_packet
from orchestrator.tradingview_mcp_adapter import (
    fetch_tradingview_mcp_live,
    fetch_tradingview_mcp_sample,
    tradingview_mcp_adapter_status,
    tradingview_mcp_packet_context,
)
from orchestrator.yahoo_finance_adapter import fetch_yahoo_finance_live, fetch_yahoo_finance_sample

PHASE2_SHADOW_CYCLE_SCHEMA_VERSION = 1
DEFAULT_PHASE2_SOURCES = ("nasa_firms", "fred", "rss", "polymarket", "alpaca", "telegram")
SUPPLEMENTAL_PHASE2_SOURCES = {
    "yahoo_finance": "supplemental_market_confirmation",
    "tradingview_mcp": "supplemental_technical_confirmation",
}

SECRET_LIKE_PATTERNS = (
    re.compile(r"\d{6,}:[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bvcp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"\bsb_secret_[0-9A-Za-z_-]{12,}\b"),
    re.compile(r"\b[A-Za-z0-9_-]{40,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b"),
)


@dataclass(frozen=True)
class SourceCycleResult:
    source_key: str
    status: str
    degraded: bool
    degraded_reason: str | None
    event_count: int
    queued_packet_count: int
    research_goal_count: int = 0
    context_role: str = "canonical_phase2_source"
    signal_authority: bool = False
    order_authority: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sample_fetcher(source_key: str) -> Callable[[], dict[str, Any]]:
    if source_key == "yahoo_finance":
        return lambda: fetch_yahoo_finance_sample()
    if source_key == "tradingview_mcp":
        return lambda: fetch_tradingview_mcp_sample()
    fetchers: dict[str, Callable[[], dict[str, Any]]] = {
        "nasa_firms": lambda: fetch_nasa_firms_sample(days=1),
        "fred": lambda: fetch_fred_sample(series_ids=("DGS10", "DCOILWTICO", "VIXCLS")),
        "rss": lambda: fetch_rss_sample(keyword_filter=("oil", "semiconductor", "defence", "silver")),
    }
    if source_key in fetchers:
        return fetchers[source_key]
    return lambda: fetch_phase1_live_adapter_sample(source_key)


def _live_fetcher(source_key: str) -> Callable[[], dict[str, Any]]:
    if source_key == "yahoo_finance":
        return lambda: fetch_yahoo_finance_live()
    if source_key == "tradingview_mcp":
        return lambda: fetch_tradingview_mcp_live()
    fetchers: dict[str, Callable[[], dict[str, Any]]] = {
        "nasa_firms": lambda: fetch_nasa_firms_live_sync(days=1),
        "fred": lambda: fetch_fred_live_sync(series_ids=("DGS10", "DCOILWTICO", "VIXCLS"), limit=20),
        "rss": lambda: fetch_rss_live_sync(keyword_filter=("oil", "semiconductor", "defence", "silver")),
    }
    if source_key in fetchers:
        return fetchers[source_key]
    return lambda: fetch_phase1_live_adapter_live_sync(source_key)


def _event_ref(event: dict[str, Any]) -> str:
    source = str(event.get("source") or "unknown_source")[:80]
    event_id = str(event.get("event_id") or "unknown_event")[:120]
    return f"{source}:{event_id}"


def _event_summary(event: dict[str, Any]) -> str:
    summary = str(event.get("normalised_summary") or "").strip()
    if summary:
        return summary[:600]
    raw = event.get("raw_payload")
    if isinstance(raw, dict):
        for key in ("title", "summary", "question", "ticker"):
            value = raw.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()[:600]
    return "Read-only source observation requires shadow review."


def _research_goal_packet_context(goal: ResearchGoal | dict[str, Any]) -> dict[str, Any]:
    payload = goal.to_dict() if isinstance(goal, ResearchGoal) else goal
    return {
        "goal_id": payload.get("goal_id"),
        "status": payload.get("status"),
        "origin": payload.get("origin"),
        "hypothesis": payload.get("hypothesis"),
        "market_channel": payload.get("market_channel"),
        "watched_instruments": list(payload.get("watched_instruments", []))[:6],
        "required_sources": list(payload.get("required_sources", []))[:8],
        "minimum_source_quorum": int(payload.get("minimum_source_quorum", 2) or 2),
        "worldview_lens": payload.get("worldview_lens"),
        "akber_stage": payload.get("akber_stage"),
        "missing_corroboration": list(payload.get("missing_corroboration", []))[:8],
        "source_quorum_score": payload.get("source_quorum_score"),
        "market_confirmation_score": payload.get("market_confirmation_score"),
        "latency_freshness_score": payload.get("latency_freshness_score"),
        "priority_score": payload.get("priority_score"),
        "priority_label": payload.get("priority_label"),
        "candidate_ready_blockers": list(payload.get("candidate_ready_blockers", []))[:8],
        "expires_at": payload.get("expires_at"),
        "stale": bool(payload.get("stale")),
        "expired": bool(payload.get("expired")),
        "owner_agent": payload.get("owner_agent"),
        "next_handoff": payload.get("next_handoff"),
        "execution_allowed": False,
        "paper_order_allowed": False,
        "trade_candidate_creation_allowed": False,
        "risk_handoff_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
        "boundary": payload.get("boundary"),
    }


def _durable_observation_to_event(observation: dict[str, Any]) -> dict[str, Any]:
    payload = observation.get("payload")
    if not isinstance(payload, dict):
        payload = {}
    source_key = str(observation.get("source_key") or "unknown_source")
    observed_at = str(observation.get("observed_at") or "unknown_time")
    source_name = str(observation.get("source_name") or source_key)
    pipeline = str(observation.get("pipeline") or "unknown_pipeline")
    mode = str(observation.get("mode") or "unknown_mode")
    adapter_status = str(observation.get("adapter_status") or "unknown_status")
    trust_score = observation.get("trust_score", 0)
    summary = str(payload.get("normalised_summary") or payload.get("summary") or "").strip()
    if not summary:
        summary = (
            f"Durable replay observation from {source_name}: pipeline={pipeline}, "
            f"mode={mode}, adapter_status={adapter_status}, observed_at={observed_at}."
        )
    return {
        "event_id": f"durable_replay:{source_key}:{observed_at}",
        "source": f"durable.{source_key}",
        "trust_score_at_ingestion": trust_score,
        "event_type": "durable_source_observation",
        "raw_payload": {
            "source_key": source_key,
            "source_name": source_name,
            "pipeline": pipeline,
            "tier": observation.get("tier"),
            "mode": mode,
            "adapter_status": adapter_status,
            "latency_ms": observation.get("latency_ms"),
            "payload": payload,
        },
        "normalised_summary": summary[:600],
        "coordinates": None,
        "ingested_at": observed_at,
        "linked_catalyst_id": None,
    }


def _uncertainty(event: dict[str, Any], *, degraded: bool) -> str:
    if degraded:
        return "high"
    trust = event.get("trust_score_at_ingestion", 0)
    try:
        score = float(trust)
    except (TypeError, ValueError):
        score = 0
    if score >= 0.75:
        return "bounded"
    if score >= 0.55:
        return "medium"
    return "high"


def _contains_secret_like_value(payload: Any) -> bool:
    encoded = json.dumps(payload, sort_keys=True, default=str)
    return any(pattern.search(encoded) for pattern in SECRET_LIKE_PATTERNS)


def _write_report(settings: Settings, report: dict[str, Any]) -> Path:
    if _contains_secret_like_value(report):
        raise ValueError("Phase 2 shadow-cycle report contains a secret-like value")
    output_path = Path(settings.runtime_dir) / "phase2_shadow_cycle.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    history_path = Path(settings.runtime_dir) / "phase2_shadow_cycle.jsonl"
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(report, sort_keys=True) + "\n")
    return output_path


def run_phase2_shadow_cycle(
    *,
    sources: tuple[str, ...] = DEFAULT_PHASE2_SOURCES,
    live_sources: bool = False,
    durable_replay: bool = False,
    live_local_llm: bool = False,
    events_per_source: int = 3,
    research_limit: int = 8,
    settings: Settings | None = None,
    event_log: EventLog | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    event_log = event_log or EventLog(echo=False)
    source_results: list[SourceCycleResult] = []
    queued_packet_count = 0
    research_goal_recorded_count = 0
    durable_replay_result: dict[str, Any] | None = None
    durable_events_by_source: dict[str, list[dict[str, Any]]] = {}
    research_goal_store = ResearchGoalStore(settings=settings)
    preference_shadow_context = build_preference_shadow_context(
        settings=settings,
        event_log=event_log,
        record_event=True,
    )
    write_preference_shadow_context(preference_shadow_context, settings=settings)
    preference_packet_context = {
        "preference_mcp": preference_shadow_packet_context(preference_shadow_context)
    }
    tradingview_mcp_context = tradingview_mcp_packet_context(settings)
    strategy_research_context = strategy_research_decision_context(settings)

    if durable_replay:
        durable_replay_result = durable_source_observation_replay(
            source_keys=sources,
            per_source=max(1, events_per_source),
            settings=settings,
        )
        for observation in durable_replay_result.get("observations", []):
            if isinstance(observation, dict):
                source_key = str(observation.get("source_key") or "unknown_source")
                durable_events_by_source.setdefault(source_key, []).append(_durable_observation_to_event(observation))

    for source_key in sources:
        if durable_replay:
            event_records = durable_events_by_source.get(source_key, [])
            replay_status = str((durable_replay_result or {}).get("replay_status") or "unknown")
            degraded = not event_records
            degraded_reason = None if event_records else f"durable_replay_{replay_status}_missing_source"
        else:
            try:
                envelope = (_live_fetcher(source_key) if live_sources else _sample_fetcher(source_key))()
            except Exception as exc:  # noqa: BLE001 - source failure must degrade, not stop the cycle.
                source_results.append(
                    SourceCycleResult(
                        source_key=source_key,
                        status="degraded",
                        degraded=True,
                        degraded_reason=f"fetch_error:{exc.__class__.__name__}",
                        event_count=0,
                        queued_packet_count=0,
                        research_goal_count=0,
                        context_role=SUPPLEMENTAL_PHASE2_SOURCES.get(source_key, "canonical_phase2_source"),
                        signal_authority=False,
                        order_authority=False,
                    )
                )
                continue

            events = envelope.get("events", [])
            event_records = [event for event in events if isinstance(event, dict)]
            degraded = bool(envelope.get("degraded"))
            degraded_reason = envelope.get("degraded_reason")

        source_packet_count = 0
        source_research_goal_count = 0
        if not degraded:
            for event in event_records[: max(0, events_per_source)]:
                event_ref = _event_ref(event)
                event_summary = _event_summary(event)
                research_goal = research_goal_store.add_from_observation(
                    summary=event_summary,
                    source_event_refs=(event_ref,),
                    origin=(
                        "durable_replay"
                        if durable_replay
                        else ("live_source" if live_sources else "sample_source")
                    ),
                    observed_at=event.get("ingested_at"),
                    event_log=event_log,
                )
                research_goal_context = _research_goal_packet_context(research_goal)
                source_research_goal_count += 1
                research_goal_recorded_count += 1
                packet_context = dict(preference_packet_context)
                packet_context["research_goal"] = research_goal_context
                if source_key == "tradingview_mcp":
                    packet_context["tradingview_mcp"] = tradingview_mcp_context
                packet = create_shadow_triage_packet(
                    source_event_refs=(event_ref,),
                    summary=event_summary,
                    uncertainty=_uncertainty(event, degraded=degraded),
                    read_only_context=packet_context,
                    settings=settings,
                    event_log=event_log,
                )
                if packet:
                    source_packet_count += 1
                    queued_packet_count += 1

        source_results.append(
            SourceCycleResult(
                source_key=source_key,
                status="degraded" if degraded else "ok",
                degraded=degraded,
                degraded_reason=degraded_reason,
                event_count=len(event_records),
                queued_packet_count=source_packet_count,
                research_goal_count=source_research_goal_count,
                context_role=SUPPLEMENTAL_PHASE2_SOURCES.get(source_key, "canonical_phase2_source"),
                signal_authority=False,
                order_authority=False,
            )
        )

    paper_context = paper_account_shadow_context(settings)
    triage_result = run_research_shadow_triage_queue(limit=research_limit, settings=settings, event_log=event_log)
    integrity_result = run_signal_integrity_gate(limit=research_limit, settings=settings, event_log=event_log)
    risk_result = run_risk_policy_router(limit=research_limit, settings=settings, event_log=event_log)
    execution_policy_result = run_execution_policy_router(limit=research_limit, settings=settings, event_log=event_log)
    staged_order_result = run_staged_paper_order_contract(limit=research_limit, settings=settings, event_log=event_log)
    broker_reconciliation_result = run_broker_reconciliation_contract(
        limit=research_limit,
        settings=settings,
        event_log=event_log,
    )
    paper_submit_receipt_result = run_paper_submit_receipt_contract(
        limit=research_limit,
        settings=settings,
        event_log=event_log,
    )
    local_result = run_local_research_analyst_inference(
        limit=research_limit,
        live=live_local_llm,
        settings=settings,
        event_log=event_log,
        paper_account_context=paper_context,
    )
    assessment = local_result.get("assessment") if isinstance(local_result.get("assessment"), dict) else None
    durable_replay_summary = durable_replay_result or {
        "status": "not_requested",
        "contract_status": "not_requested",
        "replay_status": "not_requested",
        "observation_count": 0,
        "replayed_source_count": 0,
        "missing_source_count": 0,
        "write_authority": False,
        "signal_authority": False,
        "order_authority": False,
    }
    source_degraded_count = sum(1 for result in source_results if result.degraded)
    research_goal_hardening = research_goal_store.harden_lifecycle(event_log=event_log)
    research_goal_status = research_goal_summary(settings=settings, limit=8)
    research_goal_authority_counts = research_goal_status.get("authority_counts", {})
    market_context = run_market_context_packet_cycle(
        settings=settings,
        limit=research_limit,
        source_results=[result.to_dict() for result in source_results],
        durable_replay_summary=durable_replay_summary,
        event_log=event_log,
    )
    market_context_authority_counts = market_context.get("authority_counts", {})
    strategy_source_context = {
        "status": "ok" if not source_degraded_count else "degraded",
        "mode": "durable_replay" if durable_replay else ("live_sources" if live_sources else "sample_sources"),
        "source_count": len(sources),
        "source_results": [result.to_dict() for result in source_results],
        "supplemental_market_confirmation_count": sum(
            1 for result in source_results if result.context_role == "supplemental_market_confirmation"
        ),
        "supplemental_market_confirmation_authority": False,
        "preference_mcp_shadow_context": preference_packet_context["preference_mcp"],
        "preference_mcp_shadow_context_status": preference_shadow_context.get("status"),
        "preference_mcp_shadow_context_role": preference_shadow_context.get("context_role"),
        "preference_mcp_shadow_observation_count": preference_shadow_context.get(
            "shadow_observation_count",
            0,
        ),
        "preference_mcp_active_required_challenge_count": preference_shadow_context.get(
            "active_required_challenge_count",
            0,
        ),
        "preference_mcp_source_quorum_credit_allowed": False,
        "preference_mcp_trade_candidate_creation_allowed": False,
        "preference_mcp_risk_handoff_allowed": False,
        "preference_mcp_execution_allowed": False,
        "preference_mcp_broker_write_allowed": False,
        "tradingview_mcp_technical_context": tradingview_mcp_context,
        "tradingview_mcp_status": tradingview_mcp_context.get("status"),
        "tradingview_mcp_context_role": tradingview_mcp_context.get("context_role"),
        "tradingview_mcp_technical_context_count": tradingview_mcp_context.get(
            "technical_context_count",
            0,
        ),
        "tradingview_mcp_active_required_challenge_count": len(
            tradingview_mcp_context.get("active_required_challenges", [])
            if isinstance(tradingview_mcp_context.get("active_required_challenges"), list)
            else []
        ),
        "tradingview_mcp_source_quorum_credit_allowed": False,
        "tradingview_mcp_trade_candidate_creation_allowed": False,
        "tradingview_mcp_risk_handoff_allowed": False,
        "tradingview_mcp_execution_allowed": False,
        "tradingview_mcp_paper_order_allowed": False,
        "tradingview_mcp_broker_write_allowed": False,
        "strategy_research_intake": strategy_research_context,
        "strategy_research_intake_status": strategy_research_context.get("status"),
        "strategy_research_candidate_count": strategy_research_context.get("candidate_count", 0),
        "strategy_research_challenge_count": strategy_research_context.get(
            "strategy_lead_challenge_count",
            0,
        ),
        "strategy_research_trade_candidate_creation_allowed": False,
        "strategy_research_risk_handoff_allowed": False,
        "strategy_research_execution_allowed": False,
        "strategy_research_paper_order_allowed": False,
        "strategy_research_broker_write_allowed": False,
        "research_goal_lifecycle": research_goal_status,
        "research_goal_hardening": research_goal_hardening,
        "research_goal_hardening_version": research_goal_status.get("hardening_version"),
        "research_goal_candidate_ready_count": research_goal_status.get("candidate_ready_goal_count", 0),
        "research_goal_closed_no_trade_count": research_goal_status.get("closed_no_trade_goal_count", 0),
        "research_goal_stale_goal_count": research_goal_status.get("stale_goal_count", 0),
        "research_goal_expired_goal_count": research_goal_status.get("expired_goal_count", 0),
        "research_goal_average_priority_score": research_goal_status.get("average_priority_score", 0.0),
        "research_goal_by_priority_label": research_goal_status.get("by_priority_label", {}),
        "research_goal_status": research_goal_status.get("status", "unknown"),
        "research_goal_schema_version": research_goal_status.get("schema_version"),
        "research_goal_record_count": research_goal_status.get("goal_record_count", 0),
        "research_goal_active_count": research_goal_status.get("active_goal_count", 0),
        "research_goal_created_or_updated_count": research_goal_recorded_count,
        "research_goal_by_status": research_goal_status.get("by_status", {}),
        "research_goal_by_market_channel": research_goal_status.get("by_market_channel", {}),
        "research_goal_recent_goals": research_goal_status.get("recent_goals", []),
        "research_goal_execution_allowed_count": research_goal_authority_counts.get("execution_allowed", 0),
        "research_goal_paper_order_allowed_count": research_goal_authority_counts.get("paper_order_allowed", 0),
        "research_goal_trade_candidate_creation_allowed_count": research_goal_authority_counts.get(
            "trade_candidate_creation_allowed",
            0,
        ),
        "research_goal_risk_handoff_allowed_count": research_goal_authority_counts.get("risk_handoff_allowed", 0),
        "research_goal_broker_write_allowed_count": research_goal_authority_counts.get("broker_write_allowed", 0),
        "research_goal_live_capital_enabled_count": research_goal_authority_counts.get("live_capital_enabled", 0),
        "market_context": market_context,
        "market_context_status": market_context.get("status", "unknown"),
        "market_context_packet_version": market_context.get("packet_version"),
        "market_context_packet_count": market_context.get("packet_count", 0),
        "market_context_ready_count": market_context.get("context_ready_count", 0),
        "market_context_hold_count": market_context.get("hold_for_context_count", 0),
        "market_context_average_source_quality_score": market_context.get("average_source_quality_score", 0.0),
        "market_context_average_trust_score": market_context.get("average_trust_score", 0.0),
        "market_context_yahoo_finance_status": market_context.get("yahoo_finance_status"),
        "market_context_tradingview_mcp_status": market_context.get("tradingview_mcp_status"),
        "market_context_paper_account_context_status": market_context.get("paper_account_context_status"),
        "market_context_execution_allowed_count": market_context_authority_counts.get("execution_allowed", 0),
        "market_context_paper_order_allowed_count": market_context_authority_counts.get("paper_order_allowed", 0),
        "market_context_trade_candidate_creation_allowed_count": market_context_authority_counts.get(
            "trade_candidate_creation_allowed",
            0,
        ),
        "market_context_risk_handoff_allowed_count": market_context_authority_counts.get("risk_handoff_allowed", 0),
        "market_context_broker_write_allowed_count": market_context_authority_counts.get("broker_write_allowed", 0),
        "market_context_live_capital_enabled_count": market_context_authority_counts.get("live_capital_enabled", 0),
        "market_context_source_quorum_credit_allowed_count": market_context_authority_counts.get(
            "source_quorum_credit_allowed",
            0,
        ),
        "source_degraded_count": source_degraded_count,
        "queued_packet_count": queued_packet_count,
        "shadow_signal_count": triage_result.get("shadow_signal_count", 0),
        "durable_replay_requested": durable_replay,
        "durable_replay_status": durable_replay_summary.get("status"),
        "durable_replay_contract_status": durable_replay_summary.get("contract_status"),
        "durable_replay_observation_count": durable_replay_summary.get("observation_count", 0),
        "durable_replay_replayed_source_count": durable_replay_summary.get("replayed_source_count", 0),
        "durable_replay_missing_source_count": durable_replay_summary.get("missing_source_count", 0),
        "write_authority": False,
        "signal_authority": False,
        "order_authority": False,
    }
    strategy_store = StrategyLeadShadowStore(settings=settings)
    strategy_packet = queue_strategy_lead_shadow_packet(
        assessment,
        settings=settings,
        store=strategy_store,
        event_log=event_log,
        paper_account_context=paper_context,
        source_context=strategy_source_context,
    )

    report = {
        "schema_version": PHASE2_SHADOW_CYCLE_SCHEMA_VERSION,
        "status": (
            "ok"
            if local_result.get("status") == "ok"
            and not source_degraded_count
            and durable_replay_summary.get("replay_status") not in {"offline", "missing_tables", "unavailable"}
            else "degraded"
        ),
        "mode": "durable_replay" if durable_replay else ("live_sources" if live_sources else "sample_sources"),
        "live_local_llm": live_local_llm,
        "source_count": len(sources),
        "source_results": [result.to_dict() for result in source_results],
        "source_degraded_count": source_degraded_count,
        "supplemental_market_confirmation_count": strategy_source_context[
            "supplemental_market_confirmation_count"
        ],
        "supplemental_market_confirmation_authority": strategy_source_context[
            "supplemental_market_confirmation_authority"
        ],
        "preference_mcp_shadow_context_status": strategy_source_context[
            "preference_mcp_shadow_context_status"
        ],
        "preference_mcp_shadow_context_role": strategy_source_context[
            "preference_mcp_shadow_context_role"
        ],
        "preference_mcp_shadow_observation_count": strategy_source_context[
            "preference_mcp_shadow_observation_count"
        ],
        "preference_mcp_active_required_challenge_count": strategy_source_context[
            "preference_mcp_active_required_challenge_count"
        ],
        "preference_mcp_quota_degraded": preference_shadow_context.get("quota_degraded"),
        "preference_mcp_context_stale": preference_shadow_context.get("context_stale"),
        "preference_mcp_single_source_hold": preference_shadow_context.get("single_source_hold"),
        "preference_mcp_missing_provenance_hold": preference_shadow_context.get(
            "missing_provenance_hold"
        ),
        "preference_mcp_source_quorum_credit_allowed": strategy_source_context[
            "preference_mcp_source_quorum_credit_allowed"
        ],
        "preference_mcp_trade_candidate_creation_allowed": strategy_source_context[
            "preference_mcp_trade_candidate_creation_allowed"
        ],
        "preference_mcp_risk_handoff_allowed": strategy_source_context[
            "preference_mcp_risk_handoff_allowed"
        ],
        "preference_mcp_execution_allowed": strategy_source_context[
            "preference_mcp_execution_allowed"
        ],
        "preference_mcp_broker_write_allowed": strategy_source_context[
            "preference_mcp_broker_write_allowed"
        ],
        "preference_mcp_shadow_context": preference_packet_context["preference_mcp"],
        "tradingview_mcp_adapter_status": tradingview_mcp_adapter_status(settings).get("status"),
        "tradingview_mcp_status": strategy_source_context["tradingview_mcp_status"],
        "tradingview_mcp_context_role": strategy_source_context["tradingview_mcp_context_role"],
        "tradingview_mcp_technical_context_count": strategy_source_context[
            "tradingview_mcp_technical_context_count"
        ],
        "tradingview_mcp_active_required_challenge_count": strategy_source_context[
            "tradingview_mcp_active_required_challenge_count"
        ],
        "tradingview_mcp_source_quorum_credit_allowed": strategy_source_context[
            "tradingview_mcp_source_quorum_credit_allowed"
        ],
        "tradingview_mcp_trade_candidate_creation_allowed": strategy_source_context[
            "tradingview_mcp_trade_candidate_creation_allowed"
        ],
        "tradingview_mcp_risk_handoff_allowed": strategy_source_context[
            "tradingview_mcp_risk_handoff_allowed"
        ],
        "tradingview_mcp_execution_allowed": strategy_source_context[
            "tradingview_mcp_execution_allowed"
        ],
        "tradingview_mcp_paper_order_allowed": strategy_source_context[
            "tradingview_mcp_paper_order_allowed"
        ],
        "tradingview_mcp_broker_write_allowed": strategy_source_context[
            "tradingview_mcp_broker_write_allowed"
        ],
        "tradingview_mcp_technical_context": tradingview_mcp_context,
        "strategy_research_intake_status": strategy_source_context[
            "strategy_research_intake_status"
        ],
        "strategy_research_candidate_count": strategy_source_context[
            "strategy_research_candidate_count"
        ],
        "strategy_research_challenge_count": strategy_source_context[
            "strategy_research_challenge_count"
        ],
        "strategy_research_trade_candidate_creation_allowed": strategy_source_context[
            "strategy_research_trade_candidate_creation_allowed"
        ],
        "strategy_research_risk_handoff_allowed": strategy_source_context[
            "strategy_research_risk_handoff_allowed"
        ],
        "strategy_research_execution_allowed": strategy_source_context[
            "strategy_research_execution_allowed"
        ],
        "strategy_research_paper_order_allowed": strategy_source_context[
            "strategy_research_paper_order_allowed"
        ],
        "strategy_research_broker_write_allowed": strategy_source_context[
            "strategy_research_broker_write_allowed"
        ],
        "strategy_research_intake": strategy_research_context,
        "research_goal_status": strategy_source_context["research_goal_status"],
        "research_goal_schema_version": strategy_source_context["research_goal_schema_version"],
        "research_goal_record_count": strategy_source_context["research_goal_record_count"],
        "research_goal_active_count": strategy_source_context["research_goal_active_count"],
        "research_goal_created_or_updated_count": strategy_source_context[
            "research_goal_created_or_updated_count"
        ],
        "research_goal_by_status": strategy_source_context["research_goal_by_status"],
        "research_goal_by_market_channel": strategy_source_context["research_goal_by_market_channel"],
        "research_goal_recent_goals": strategy_source_context["research_goal_recent_goals"],
        "research_goal_execution_allowed_count": strategy_source_context[
            "research_goal_execution_allowed_count"
        ],
        "research_goal_paper_order_allowed_count": strategy_source_context[
            "research_goal_paper_order_allowed_count"
        ],
        "research_goal_trade_candidate_creation_allowed_count": strategy_source_context[
            "research_goal_trade_candidate_creation_allowed_count"
        ],
        "research_goal_risk_handoff_allowed_count": strategy_source_context[
            "research_goal_risk_handoff_allowed_count"
        ],
        "research_goal_broker_write_allowed_count": strategy_source_context[
            "research_goal_broker_write_allowed_count"
        ],
        "research_goal_live_capital_enabled_count": strategy_source_context[
            "research_goal_live_capital_enabled_count"
        ],
        "research_goal_lifecycle": research_goal_status,
        "research_goal_hardening": research_goal_hardening,
        "research_goal_hardening_version": strategy_source_context["research_goal_hardening_version"],
        "research_goal_candidate_ready_count": strategy_source_context["research_goal_candidate_ready_count"],
        "research_goal_closed_no_trade_count": strategy_source_context["research_goal_closed_no_trade_count"],
        "research_goal_stale_goal_count": strategy_source_context["research_goal_stale_goal_count"],
        "research_goal_expired_goal_count": strategy_source_context["research_goal_expired_goal_count"],
        "research_goal_average_priority_score": strategy_source_context["research_goal_average_priority_score"],
        "research_goal_by_priority_label": strategy_source_context["research_goal_by_priority_label"],
        "market_context_status": strategy_source_context["market_context_status"],
        "market_context_packet_version": strategy_source_context["market_context_packet_version"],
        "market_context_packet_count": strategy_source_context["market_context_packet_count"],
        "market_context_ready_count": strategy_source_context["market_context_ready_count"],
        "market_context_hold_count": strategy_source_context["market_context_hold_count"],
        "market_context_average_source_quality_score": strategy_source_context[
            "market_context_average_source_quality_score"
        ],
        "market_context_average_trust_score": strategy_source_context["market_context_average_trust_score"],
        "market_context_yahoo_finance_status": strategy_source_context["market_context_yahoo_finance_status"],
        "market_context_tradingview_mcp_status": strategy_source_context["market_context_tradingview_mcp_status"],
        "market_context_paper_account_context_status": strategy_source_context[
            "market_context_paper_account_context_status"
        ],
        "market_context_execution_allowed_count": strategy_source_context[
            "market_context_execution_allowed_count"
        ],
        "market_context_paper_order_allowed_count": strategy_source_context[
            "market_context_paper_order_allowed_count"
        ],
        "market_context_trade_candidate_creation_allowed_count": strategy_source_context[
            "market_context_trade_candidate_creation_allowed_count"
        ],
        "market_context_risk_handoff_allowed_count": strategy_source_context[
            "market_context_risk_handoff_allowed_count"
        ],
        "market_context_broker_write_allowed_count": strategy_source_context[
            "market_context_broker_write_allowed_count"
        ],
        "market_context_live_capital_enabled_count": strategy_source_context[
            "market_context_live_capital_enabled_count"
        ],
        "market_context_source_quorum_credit_allowed_count": strategy_source_context[
            "market_context_source_quorum_credit_allowed_count"
        ],
        "market_context": market_context,
        "queued_packet_count": queued_packet_count,
        "durable_replay_requested": durable_replay,
        "durable_replay_status": durable_replay_summary.get("status"),
        "durable_replay_contract_status": durable_replay_summary.get("contract_status"),
        "durable_replay_observation_count": durable_replay_summary.get("observation_count", 0),
        "durable_replay_replayed_source_count": durable_replay_summary.get("replayed_source_count", 0),
        "durable_replay_missing_source_count": durable_replay_summary.get("missing_source_count", 0),
        "durable_replay_write_authority": durable_replay_summary.get("write_authority"),
        "durable_replay_signal_authority": durable_replay_summary.get("signal_authority"),
        "durable_replay_order_authority": durable_replay_summary.get("order_authority"),
        "shadow_signal_count": triage_result.get("shadow_signal_count", 0),
        "signal_integrity_status": integrity_result.get("status"),
        "signal_integrity_review_count": integrity_result.get("review_count", 0),
        "signal_integrity_blocked_count": integrity_result.get("blocked_count", 0),
        "signal_integrity_hold_count": integrity_result.get("hold_count", 0),
        "signal_integrity_passed_to_risk_shadow_count": integrity_result.get("passed_to_risk_shadow_count", 0),
        "signal_integrity_trade_candidate_created_count": integrity_result.get("trade_candidate_created_count", 0),
        "risk_agent_status": risk_result.get("status"),
        "risk_agent_review_count": risk_result.get("review_count", 0),
        "risk_agent_blocked_count": risk_result.get("blocked_count", 0),
        "risk_agent_policy_hold_count": risk_result.get("policy_hold_count", 0),
        "risk_agent_shadow_ready_count": risk_result.get("risk_shadow_ready_count", 0),
        "risk_agent_execution_allowed_count": risk_result.get("execution_allowed_count", 0),
        "risk_agent_paper_order_allowed_count": risk_result.get("paper_order_allowed_count", 0),
        "risk_agent_order_created_count": risk_result.get("order_created_count", 0),
        "risk_agent_broker_write_allowed_count": risk_result.get("broker_write_allowed_count", 0),
        "execution_policy_status": execution_policy_result.get("status"),
        "execution_policy_review_count": execution_policy_result.get("review_count", 0),
        "execution_policy_blocked_by_policy_count": execution_policy_result.get("blocked_by_policy_count", 0),
        "execution_policy_kill_switch_hold_count": execution_policy_result.get("kill_switch_hold_count", 0),
        "execution_policy_paper_order_shadow_ready_count": execution_policy_result.get("paper_order_shadow_ready_count", 0),
        "execution_policy_execution_allowed_count": execution_policy_result.get("execution_allowed_count", 0),
        "execution_policy_staged_paper_order_allowed_count": execution_policy_result.get(
            "staged_paper_order_allowed_count",
            0,
        ),
        "execution_policy_paper_order_created_count": execution_policy_result.get("paper_order_created_count", 0),
        "execution_policy_broker_write_allowed_count": execution_policy_result.get("broker_write_allowed_count", 0),
        "execution_policy_live_capital_enabled_count": execution_policy_result.get("live_capital_enabled_count", 0),
        "staged_paper_order_status": staged_order_result.get("status"),
        "staged_paper_order_review_count": staged_order_result.get("review_count", 0),
        "staged_paper_order_blocked_before_staging_count": staged_order_result.get("blocked_before_staging_count", 0),
        "staged_paper_order_reconciliation_hold_count": staged_order_result.get("reconciliation_hold_count", 0),
        "staged_paper_order_disabled_contract_hold_count": staged_order_result.get("disabled_contract_hold_count", 0),
        "staged_paper_order_execution_allowed_count": staged_order_result.get("execution_allowed_count", 0),
        "staged_paper_order_created_count": staged_order_result.get("staged_paper_order_created_count", 0),
        "staged_paper_order_submittable_count": staged_order_result.get("paper_order_submittable_count", 0),
        "staged_paper_order_broker_write_allowed_count": staged_order_result.get("broker_write_allowed_count", 0),
        "staged_paper_order_live_capital_enabled_count": staged_order_result.get("live_capital_enabled_count", 0),
        "broker_reconciliation_status": broker_reconciliation_result.get("status"),
        "broker_reconciliation_review_count": broker_reconciliation_result.get("review_count", 0),
        "broker_reconciliation_blocked_before_count": broker_reconciliation_result.get(
            "blocked_before_broker_reconciliation_count",
            0,
        ),
        "broker_reconciliation_route_closed_count": broker_reconciliation_result.get("broker_route_closed_count", 0),
        "broker_reconciliation_contract_hold_count": broker_reconciliation_result.get(
            "reconciliation_contract_hold_count",
            0,
        ),
        "broker_reconciliation_idempotency_key_allocated_count": broker_reconciliation_result.get(
            "idempotency_key_allocated_count",
            0,
        ),
        "broker_reconciliation_event_log_prewrite_created_count": broker_reconciliation_result.get(
            "event_log_prewrite_created_count",
            0,
        ),
        "broker_reconciliation_pre_trade_snapshot_created_count": broker_reconciliation_result.get(
            "pre_trade_snapshot_created_count",
            0,
        ),
        "broker_reconciliation_duplicate_order_guard_ready_count": broker_reconciliation_result.get(
            "duplicate_order_guard_ready_count",
            0,
        ),
        "broker_reconciliation_broker_echo_verified_count": broker_reconciliation_result.get(
            "broker_echo_verified_count",
            0,
        ),
        "broker_reconciliation_post_submit_reconciliation_ready_count": broker_reconciliation_result.get(
            "post_submit_reconciliation_ready_count",
            0,
        ),
        "broker_reconciliation_postmortem_link_ready_count": broker_reconciliation_result.get(
            "postmortem_link_ready_count",
            0,
        ),
        "broker_reconciliation_paper_order_submit_allowed_count": broker_reconciliation_result.get(
            "paper_order_submit_allowed_count",
            0,
        ),
        "broker_reconciliation_broker_write_allowed_count": broker_reconciliation_result.get(
            "broker_write_allowed_count",
            0,
        ),
        "broker_reconciliation_live_capital_enabled_count": broker_reconciliation_result.get(
            "live_capital_enabled_count",
            0,
        ),
        "paper_submit_receipt_status": paper_submit_receipt_result.get("status"),
        "paper_submit_receipt_review_count": paper_submit_receipt_result.get("review_count", 0),
        "paper_submit_receipt_blocked_before_count": paper_submit_receipt_result.get(
            "blocked_before_dry_run_submit_count",
            0,
        ),
        "paper_submit_receipt_dry_run_blocked_count": paper_submit_receipt_result.get(
            "dry_run_receipt_blocked_count",
            0,
        ),
        "paper_submit_receipt_dry_run_ready_count": paper_submit_receipt_result.get(
            "dry_run_receipt_ready_count",
            0,
        ),
        "paper_submit_receipt_dry_run_created_count": paper_submit_receipt_result.get(
            "dry_run_receipt_created_count",
            0,
        ),
        "paper_submit_receipt_paper_order_submitted_count": paper_submit_receipt_result.get(
            "paper_order_submitted_count",
            0,
        ),
        "paper_submit_receipt_broker_post_called_count": paper_submit_receipt_result.get(
            "broker_post_called_count",
            0,
        ),
        "paper_submit_receipt_broker_write_allowed_count": paper_submit_receipt_result.get(
            "broker_write_allowed_count",
            0,
        ),
        "paper_submit_receipt_live_capital_enabled_count": paper_submit_receipt_result.get(
            "live_capital_enabled_count",
            0,
        ),
        "local_research_status": local_result.get("status"),
        "local_research_mode": local_result.get("mode"),
        "local_research_assessment_id": assessment.get("assessment_id") if assessment else None,
        "local_research_execution_allowed": bool(assessment.get("execution_allowed")) if assessment else False,
        "local_research_paper_order_allowed": bool(assessment.get("paper_order_allowed")) if assessment else False,
        "paper_account_context_status": paper_context.get("status"),
        "paper_account_connection_status": paper_context.get("connection_status"),
        "paper_account_current_balance_gbp": paper_context.get("current_balance_gbp"),
        "paper_account_order_count": paper_context.get("order_count"),
        "paper_account_open_position_count": paper_context.get("open_position_count"),
        "paper_account_write_authority": paper_context.get("write_authority"),
        "paper_account_live_capital_enabled": paper_context.get("live_capital_enabled"),
        "strategy_lead_packet_id": strategy_packet.packet_id,
        "strategy_lead_status": strategy_packet.status,
        "strategy_lead_execution_allowed": strategy_packet.execution_allowed,
        "strategy_lead_paper_order_allowed": strategy_packet.paper_order_allowed,
        "strategy_lead_source_mode": strategy_packet.source_context.get("mode"),
        "strategy_lead_source_posture": strategy_packet.strategy_review.get("source_posture"),
        "strategy_lead_review_mode": strategy_packet.strategy_review.get("review_mode"),
        "strategy_lead_evidence_pressure": strategy_packet.strategy_review.get("evidence_pressure"),
        "strategy_lead_required_challenge_count": len(strategy_packet.strategy_review.get("required_challenges", [])),
        "strategy_lead_preference_mcp_context_status": strategy_packet.strategy_review.get(
            "preference_mcp_context_status"
        ),
        "strategy_lead_preference_mcp_challenge_count": strategy_packet.strategy_review.get(
            "preference_mcp_challenge_count",
            0,
        ),
        "strategy_lead_strategy_research_context_status": strategy_packet.strategy_review.get(
            "strategy_research_context_status"
        ),
        "strategy_lead_strategy_research_candidate_count": strategy_packet.strategy_review.get(
            "strategy_research_candidate_count",
            0,
        ),
        "strategy_lead_strategy_research_challenge_count": strategy_packet.strategy_review.get(
            "strategy_research_challenge_count",
            0,
        ),
        "strategy_lead_risk_handoff_allowed": strategy_packet.strategy_review.get("risk_handoff_allowed"),
        "strategy_lead_trade_candidate_allowed": strategy_packet.strategy_review.get("trade_candidate_allowed"),
        "strategy_lead_store": strategy_store.health(),
        "boundary": (
            "Phase 2 shadow cycle feeds observations into Research Analyst and "
            "Strategy Lead queues only. Signal Integrity Gate can block or hold "
            "shadow signals. Risk Agent policy review is read-only, so execution "
            "and paper orders remain impossible. Execution Policy and kill-switch "
            "review is also read-only, and staged paper-order checks can only "
            "describe blocked hypothetical staging. Broker reconciliation checks "
            "can only describe read-only submit prerequisites. Paper-submit receipt "
            "checks are dry-run only and cannot call brokers. Durable replay is "
            "read-only context and cannot create signals, trade candidates, or orders. "
            "Research Goals are pre-signal organization records only; they can carry "
            "hypotheses, missing corroboration, and handoff context, but cannot create "
            "trade candidates, risk approvals, paper orders, broker writes, quantum "
            "hardware submissions, or live capital. "
            "Preference/PREF MCP context is read-only challenge material only; it cannot "
            "satisfy source quorum or move anything to risk, execution, paper order, "
            "broker write, or live capital."
        ),
    }
    report_path = _write_report(settings, report)
    event_log.write(
        "phase2_shadow_cycle_completed",
        "intelligence",
        {
            "status": report["status"],
            "mode": report["mode"],
            "queued_packet_count": queued_packet_count,
            "durable_replay_requested": durable_replay,
            "durable_replay_status": report["durable_replay_status"],
            "durable_replay_replayed_source_count": report["durable_replay_replayed_source_count"],
            "shadow_signal_count": report["shadow_signal_count"],
            "signal_integrity_review_count": report["signal_integrity_review_count"],
            "risk_agent_review_count": report["risk_agent_review_count"],
            "execution_policy_review_count": report["execution_policy_review_count"],
            "staged_paper_order_review_count": report["staged_paper_order_review_count"],
            "broker_reconciliation_review_count": report["broker_reconciliation_review_count"],
            "paper_submit_receipt_review_count": report["paper_submit_receipt_review_count"],
            "strategy_lead_packet_id": strategy_packet.packet_id,
            "strategy_lead_source_mode": report["strategy_lead_source_mode"],
            "strategy_lead_source_posture": report["strategy_lead_source_posture"],
            "preference_mcp_shadow_context_status": report["preference_mcp_shadow_context_status"],
            "preference_mcp_shadow_observation_count": report[
                "preference_mcp_shadow_observation_count"
            ],
            "preference_mcp_trade_candidate_creation_allowed": False,
            "strategy_research_intake_status": report["strategy_research_intake_status"],
            "strategy_research_candidate_count": report["strategy_research_candidate_count"],
            "strategy_research_trade_candidate_creation_allowed": False,
            "research_goal_active_count": report["research_goal_active_count"],
            "research_goal_created_or_updated_count": report["research_goal_created_or_updated_count"],
            "research_goal_trade_candidate_creation_allowed_count": report[
                "research_goal_trade_candidate_creation_allowed_count"
            ],
            "market_context_packet_count": report["market_context_packet_count"],
            "market_context_average_source_quality_score": report[
                "market_context_average_source_quality_score"
            ],
            "market_context_trade_candidate_creation_allowed_count": report[
                "market_context_trade_candidate_creation_allowed_count"
            ],
            "execution_allowed": False,
            "paper_order_allowed": False,
            "report_path": str(report_path),
        },
    )
    return report | {"report_path": str(report_path)}
