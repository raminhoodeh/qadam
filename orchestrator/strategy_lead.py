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

STRATEGY_LEAD_PACKET_SCHEMA_VERSION = 1


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


def build_strategy_lead_shadow_packet(
    assessment: dict[str, Any] | None,
    *,
    paper_account_context: dict[str, Any] | None = None,
) -> StrategyLeadShadowPacket:
    assessment = assessment or {}
    safe_paper_context = _safe_paper_account_context(paper_account_context)
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
) -> StrategyLeadShadowPacket:
    settings = settings or Settings.from_env()
    store = store or StrategyLeadShadowStore(settings=settings)
    packet = build_strategy_lead_shadow_packet(assessment, paper_account_context=paper_account_context)
    return store.write(packet, event_log=event_log)
