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
from orchestrator.paper_account import paper_account_shadow_context
from orchestrator.paper_submit_receipt import run_paper_submit_receipt_contract
from orchestrator.postgres_store import durable_source_observation_replay
from orchestrator.risk_agent import run_risk_policy_router
from orchestrator.signal_integrity import run_signal_integrity_gate
from orchestrator.staged_paper_order import run_staged_paper_order_contract
from orchestrator.phase1_live_adapters import (
    fetch_phase1_live_adapter_live_sync,
    fetch_phase1_live_adapter_sample,
)
from orchestrator.strategy_lead import StrategyLeadShadowStore, queue_strategy_lead_shadow_packet

PHASE2_SHADOW_CYCLE_SCHEMA_VERSION = 1
DEFAULT_PHASE2_SOURCES = ("nasa_firms", "fred", "rss", "polymarket", "alpaca", "telegram")

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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sample_fetcher(source_key: str) -> Callable[[], dict[str, Any]]:
    fetchers: dict[str, Callable[[], dict[str, Any]]] = {
        "nasa_firms": lambda: fetch_nasa_firms_sample(days=1),
        "fred": lambda: fetch_fred_sample(series_ids=("DGS10", "DCOILWTICO", "VIXCLS")),
        "rss": lambda: fetch_rss_sample(keyword_filter=("oil", "semiconductor", "defence", "silver")),
    }
    if source_key in fetchers:
        return fetchers[source_key]
    return lambda: fetch_phase1_live_adapter_sample(source_key)


def _live_fetcher(source_key: str) -> Callable[[], dict[str, Any]]:
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
    durable_replay_result: dict[str, Any] | None = None
    durable_events_by_source: dict[str, list[dict[str, Any]]] = {}

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
                    )
                )
                continue

            events = envelope.get("events", [])
            event_records = [event for event in events if isinstance(event, dict)]
            degraded = bool(envelope.get("degraded"))
            degraded_reason = envelope.get("degraded_reason")

        source_packet_count = 0
        if not degraded:
            for event in event_records[: max(0, events_per_source)]:
                packet = create_shadow_triage_packet(
                    source_event_refs=(_event_ref(event),),
                    summary=_event_summary(event),
                    uncertainty=_uncertainty(event, degraded=degraded),
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
    strategy_store = StrategyLeadShadowStore(settings=settings)
    strategy_packet = queue_strategy_lead_shadow_packet(
        assessment,
        settings=settings,
        store=strategy_store,
        event_log=event_log,
        paper_account_context=paper_context,
    )

    source_degraded_count = sum(1 for result in source_results if result.degraded)
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
            "read-only context and cannot create signals, trade candidates, or orders."
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
            "execution_allowed": False,
            "paper_order_allowed": False,
            "report_path": str(report_path),
        },
    )
    return report | {"report_path": str(report_path)}
