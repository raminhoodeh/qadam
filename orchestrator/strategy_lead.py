"""Strategy Lead shadow handoff records.

Phase 2 can prepare strategy-review packets for the frontier LLM role, but it
cannot ask for orders, risk approval, sizing, or execution. These records are a
queueable handoff format, not a trading decision.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from orchestrator.config import Settings
from orchestrator.event_log import EventLog

STRATEGY_LEAD_PACKET_SCHEMA_VERSION = 2


@dataclass(frozen=True)
class StrategyLeadShadowPacket:
    schema_version: int
    packet_id: str
    status: str
    source_assessment_id: str | None
    watch_focus: str
    research_summary: str
    anomalies: tuple[str, ...]
    missing_correlations: tuple[str, ...]
    strategy_questions: tuple[str, ...]
    worldview_lens_status: str
    source_context: dict[str, Any]
    strategy_review: dict[str, Any]
    blocked_by: tuple[str, ...]
    execution_allowed: bool
    paper_order_allowed: bool
    paper_account_context: dict[str, Any]
    created_at: str
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["anomalies"] = list(self.anomalies)
        payload["missing_correlations"] = list(self.missing_correlations)
        payload["strategy_questions"] = list(self.strategy_questions)
        payload["blocked_by"] = list(self.blocked_by)
        return payload


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_tuple(value: Any, *, fallback: tuple[str, ...] = ()) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(str(item).strip()[:240] for item in value if str(item).strip())[:8]
    if isinstance(value, tuple):
        return tuple(str(item).strip()[:240] for item in value if str(item).strip())[:8]
    if isinstance(value, str) and value.strip():
        return (value.strip()[:240],)
    return fallback


def _safe_paper_account_context(value: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {
            "status": "not_available",
            "execution_allowed": False,
            "paper_order_allowed": False,
            "write_authority": False,
            "live_capital_enabled": False,
            "boundary": "No paper account context was supplied.",
        }
    allowed_fields = {
        "account_scope",
        "broker",
        "boundary",
        "capital_policy",
        "closed_trade_count",
        "connection_status",
        "current_balance_gbp",
        "drawdown_pct",
        "execution_allowed",
        "live_capital_enabled",
        "maturity_closed_trade_count",
        "maturity_closed_trade_target",
        "mode",
        "open_order_count",
        "open_position_count",
        "order_count",
        "paper_order_allowed",
        "realized_pnl_gbp",
        "status",
        "timeline_status",
        "trial_allocation_gbp",
        "unrealized_pnl_gbp",
        "write_authority",
    }
    projected = {key: value.get(key) for key in sorted(allowed_fields) if key in value}
    projected["execution_allowed"] = False
    projected["paper_order_allowed"] = False
    projected["write_authority"] = False
    projected["live_capital_enabled"] = False
    return projected


def _safe_source_results(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in value[:12]:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "source_key": str(item.get("source_key") or "unknown_source")[:80],
                "status": str(item.get("status") or "unknown")[:40],
                "degraded": bool(item.get("degraded")),
                "degraded_reason": str(item.get("degraded_reason") or "")[:160] or None,
                "event_count": int(item.get("event_count", 0) or 0),
                "queued_packet_count": int(item.get("queued_packet_count", 0) or 0),
            }
        )
    return rows


def _safe_source_context(value: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {
            "status": "not_available",
            "mode": "not_available",
            "source_count": 0,
            "source_degraded_count": 0,
            "queued_packet_count": 0,
            "durable_replay_requested": False,
            "durable_replay_status": "not_requested",
            "durable_replay_contract_status": "not_requested",
            "durable_replay_replayed_source_count": 0,
            "durable_replay_missing_source_count": 0,
            "write_authority": False,
            "signal_authority": False,
            "order_authority": False,
            "boundary": "No source context was supplied to the Strategy Lead packet.",
        }
    projected = {
        "status": str(value.get("status") or "unknown")[:60],
        "mode": str(value.get("mode") or "unknown")[:60],
        "source_count": int(value.get("source_count", 0) or 0),
        "source_degraded_count": int(value.get("source_degraded_count", 0) or 0),
        "queued_packet_count": int(value.get("queued_packet_count", 0) or 0),
        "shadow_signal_count": int(value.get("shadow_signal_count", 0) or 0),
        "durable_replay_requested": bool(value.get("durable_replay_requested")),
        "durable_replay_status": str(value.get("durable_replay_status") or "not_requested")[:80],
        "durable_replay_contract_status": str(value.get("durable_replay_contract_status") or "not_requested")[:80],
        "durable_replay_observation_count": int(value.get("durable_replay_observation_count", 0) or 0),
        "durable_replay_replayed_source_count": int(value.get("durable_replay_replayed_source_count", 0) or 0),
        "durable_replay_missing_source_count": int(value.get("durable_replay_missing_source_count", 0) or 0),
        "source_results": _safe_source_results(value.get("source_results")),
        "write_authority": False,
        "signal_authority": False,
        "order_authority": False,
        "boundary": (
            "Source context is read-only evidence posture. It cannot create signals, "
            "trade candidates, orders, broker writes, or live-capital authority."
        ),
    }
    return projected


def _strategy_review(
    assessment: dict[str, Any],
    *,
    source_context: dict[str, Any],
    paper_account_context: dict[str, Any],
) -> dict[str, Any]:
    mode = str(source_context.get("mode") or "unknown")
    replay_complete = (
        mode == "durable_replay"
        and source_context.get("durable_replay_status") == "ok"
        and int(source_context.get("durable_replay_missing_source_count", 0) or 0) == 0
        and int(source_context.get("source_degraded_count", 0) or 0) == 0
    )
    queued = int(source_context.get("queued_packet_count", 0) or 0)
    shadow_signals = int(source_context.get("shadow_signal_count", 0) or 0)
    if replay_complete and queued >= 5:
        source_posture = "durable_replay_complete"
    elif queued:
        source_posture = "partial_shadow_context"
    else:
        source_posture = "waiting_for_shadow_context"
    evidence_pressure = "thin"
    if queued >= 8 or shadow_signals >= 3:
        evidence_pressure = "active_shadow_review"
    elif queued >= 4 or shadow_signals:
        evidence_pressure = "early_shadow_review"
    questions = list(
        _safe_tuple(
            assessment.get("next_questions"),
            fallback=("Which independent source can corroborate this assessment?",),
        )
    )
    if replay_complete:
        questions.extend(
            [
                "Which replayed source creates the strongest falsifiable catalyst?",
                "What live-source delta would invalidate this durable replay pattern?",
                "Which Phase 1 instrument is only a watchlist item, not an order?",
            ]
        )
    questions.append("Does paper account state change review priority without creating an order?")
    return {
        "review_mode": "durable_replay_shadow_review" if mode == "durable_replay" else "shadow_handoff_review",
        "source_posture": source_posture,
        "evidence_pressure": evidence_pressure,
        "source_count": source_context.get("source_count", 0),
        "queued_packet_count": queued,
        "shadow_signal_count": shadow_signals,
        "paper_context_status": paper_account_context.get("status", "unknown"),
        "paper_context_connection_status": paper_account_context.get("connection_status", "unknown"),
        "required_challenges": tuple(questions[:8]),
        "risk_handoff_allowed": False,
        "trade_candidate_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "boundary": (
            "Strategy Lead review is challenge-only. It may prioritize questions, "
            "but cannot approve risk, create trade candidates, submit paper orders, "
            "write to brokers, or enable live capital."
        ),
    }


def build_strategy_lead_shadow_packet(
    assessment: dict[str, Any] | None,
    *,
    paper_account_context: dict[str, Any] | None = None,
    source_context: dict[str, Any] | None = None,
) -> StrategyLeadShadowPacket:
    assessment = assessment or {}
    safe_paper_context = _safe_paper_account_context(paper_account_context)
    safe_source_context = _safe_source_context(source_context)
    watch_focus = str(assessment.get("watch_focus") or "macro_watchlist")[:120]
    missing = _safe_tuple(
        assessment.get("missing_correlations"),
        fallback=("second_independent_source", "signal_integrity_gate", "risk_agent_review"),
    )
    questions = _safe_tuple(
        assessment.get("next_questions"),
        fallback=(
            "Which independent source can corroborate this assessment?",
            "What invalidates this thesis before it becomes a proposed signal?",
            "What market price or probability gap would make this worth deeper review?",
        ),
    ) + ("Does current paper exposure change review priority without creating an order?",)
    review = _strategy_review(
        assessment,
        source_context=safe_source_context,
        paper_account_context=safe_paper_context,
    )
    return StrategyLeadShadowPacket(
        schema_version=STRATEGY_LEAD_PACKET_SCHEMA_VERSION,
        packet_id=str(uuid4()),
        status="queued_shadow_only",
        source_assessment_id=assessment.get("assessment_id"),
        watch_focus=watch_focus,
        research_summary=str(assessment.get("summary") or "No local Research Analyst assessment available.")[:1000],
        anomalies=_safe_tuple(assessment.get("anomalies"), fallback=("none_identified",)),
        missing_correlations=missing,
        strategy_questions=questions,
        worldview_lens_status="private_prior_only_not_evidence",
        source_context=safe_source_context,
        strategy_review=review,
        blocked_by=(
            "signal_integrity_gate_missing",
            "risk_agent_missing",
            "execution_policy_missing",
            "broker_write_route_absent",
            "paper_account_context_read_only",
        ),
        execution_allowed=False,
        paper_order_allowed=False,
        paper_account_context=safe_paper_context,
        created_at=_now(),
        boundary=(
            "Strategy Lead packet is a shadow handoff only. Paper account context is read-only; "
            "it cannot approve signals, risk, paper orders, or live execution."
        ),
    )


class StrategyLeadShadowStore:
    def __init__(self, path: str | Path | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.path = Path(path or Path(self.settings.runtime_dir) / "strategy_lead_shadow_packets.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, packet: StrategyLeadShadowPacket, *, event_log: EventLog | None = None) -> StrategyLeadShadowPacket:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(packet.to_dict(), sort_keys=True) + "\n")
        (event_log or EventLog(echo=False)).write(
            "strategy_lead_shadow_packet_queued",
            "strategy_lead",
            {
                "packet_id": packet.packet_id,
                "status": packet.status,
                "source_assessment_id": packet.source_assessment_id,
                "watch_focus": packet.watch_focus,
                "source_mode": packet.source_context.get("mode"),
                "source_posture": packet.strategy_review.get("source_posture"),
                "execution_allowed": packet.execution_allowed,
                "paper_order_allowed": packet.paper_order_allowed,
            },
        )
        return packet

    def read(self) -> tuple[dict[str, Any], ...]:
        if not self.path.exists():
            return ()
        packets: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    loaded = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid Strategy Lead packet line {line_number} in {self.path}") from exc
                if isinstance(loaded, dict):
                    packets.append(loaded)
        return tuple(packets)

    def health(self) -> dict[str, Any]:
        try:
            packets = self.read()
        except Exception as exc:  # noqa: BLE001 - health should report failure.
            return {"status": "degraded", "path": str(self.path), "error": str(exc)}
        return {
            "status": "ok",
            "schema_version": STRATEGY_LEAD_PACKET_SCHEMA_VERSION,
            "path": str(self.path),
            "packet_count": len(packets),
            "execution_allowed_count": sum(1 for packet in packets if packet.get("execution_allowed") is True),
            "paper_order_allowed_count": sum(1 for packet in packets if packet.get("paper_order_allowed") is True),
            "last_packet_id": packets[-1].get("packet_id") if packets else None,
            "boundary": "Strategy Lead packets are shadow-only and cannot route orders.",
        }


def queue_strategy_lead_shadow_packet(
    assessment: dict[str, Any] | None,
    *,
    settings: Settings | None = None,
    store: StrategyLeadShadowStore | None = None,
    event_log: EventLog | None = None,
    paper_account_context: dict[str, Any] | None = None,
    source_context: dict[str, Any] | None = None,
) -> StrategyLeadShadowPacket:
    settings = settings or Settings.from_env()
    store = store or StrategyLeadShadowStore(settings=settings)
    packet = build_strategy_lead_shadow_packet(
        assessment,
        paper_account_context=paper_account_context,
        source_context=source_context,
    )
    return store.write(packet, event_log=event_log)
