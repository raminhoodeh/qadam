"""Local Trade Intent Store.

D5 records trade ideas as explicit local state. These records are not broker
orders and cannot become executable without later Risk Agent and venue gates.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from orchestrator.config import Settings
from orchestrator.event_log import EventLog

TRADE_INTENT_SCHEMA_VERSION = 1

TRADE_STATES = {
    "observed_signal",
    "hypothesis",
    "candidate",
    "blocked",
    "risk_review",
    "staged_paper_order",
    "submitted_paper_order",
    "open_position",
    "exit_planned",
    "closed_trade",
    "postmortem_due",
    "postmortem_complete",
}

EXECUTION_STATES = {
    "staged_paper_order",
    "submitted_paper_order",
    "open_position",
    "exit_planned",
    "closed_trade",
}


@dataclass(frozen=True)
class TradeIntent:
    schema_version: int
    intent_id: str
    status: str
    instrument: str
    direction: str
    venue: str
    strategy: str
    catalyst: str
    evidence_summary: str
    probability_estimate: float | None
    market_implied_probability: float | None
    price_gap: str
    proposed_entry: str
    invalidation: str
    holding_window: str
    risk_size_gbp: float
    risk_size_pct: float
    risk_state: str
    blocked_reason: str
    execution_allowed: bool
    paper_order_allowed: bool
    source_signal_id: str | None
    source_type: str
    akber_filter: dict[str, str]
    risk_checks: dict[str, str]
    tags: tuple[str, ...]
    created_at: str
    updated_at: str
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["tags"] = list(self.tags)
        return payload


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _status_bucket(intent: TradeIntent) -> str:
    if intent.status in {"candidate", "risk_review"}:
        return "candidates"
    if intent.status == "blocked":
        return "blocked"
    if intent.status == "staged_paper_order":
        return "staged_orders"
    if intent.status == "submitted_paper_order":
        return "submitted_orders"
    if intent.status in {"open_position", "exit_planned"}:
        return "open_positions"
    if intent.status == "closed_trade":
        return "closed_trades"
    if intent.status == "postmortem_due":
        return "postmortems_due"
    if intent.status == "postmortem_complete":
        return "postmortems_complete"
    return "watching"


def validate_trade_intent(intent: TradeIntent) -> None:
    if intent.schema_version != TRADE_INTENT_SCHEMA_VERSION:
        raise ValueError("trade intent schema version mismatch")
    if intent.status not in TRADE_STATES:
        raise ValueError(f"invalid trade intent status: {intent.status}")
    for field_name in (
        "intent_id",
        "instrument",
        "direction",
        "venue",
        "strategy",
        "catalyst",
        "evidence_summary",
        "proposed_entry",
        "invalidation",
        "holding_window",
        "risk_state",
        "source_type",
        "boundary",
    ):
        if not str(getattr(intent, field_name)).strip():
            raise ValueError(f"trade intent missing required field: {field_name}")
    if intent.status == "blocked" and not intent.blocked_reason:
        raise ValueError("blocked trade intent requires blocked_reason")
    if intent.risk_size_gbp < 0 or intent.risk_size_pct < 0:
        raise ValueError("trade intent risk size cannot be negative")
    if intent.probability_estimate is not None and not 0 <= intent.probability_estimate <= 1:
        raise ValueError("probability_estimate must be between 0 and 1")
    if intent.market_implied_probability is not None and not 0 <= intent.market_implied_probability <= 1:
        raise ValueError("market_implied_probability must be between 0 and 1")
    if intent.status not in EXECUTION_STATES and intent.execution_allowed:
        raise ValueError("non-execution trade states cannot allow execution")
    if intent.status not in {"staged_paper_order", "submitted_paper_order"} and intent.paper_order_allowed:
        raise ValueError("paper orders are allowed only for staged/submitted paper-order states")


class TradeIntentStore:
    def __init__(self, path: str | Path | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.path = Path(path or Path(self.settings.runtime_dir) / "trade_candidates.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def add_intent(self, intent: TradeIntent, *, log_event: bool = True) -> TradeIntent:
        validate_trade_intent(intent)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(intent.to_dict(), sort_keys=True) + "\n")
        if log_event:
            EventLog(echo=False).write(
                event_type="trade_intent_recorded",
                component="trade_intent",
                payload={
                    "intent_id": intent.intent_id,
                    "status": intent.status,
                    "instrument": intent.instrument,
                    "direction": intent.direction,
                    "execution_allowed": intent.execution_allowed,
                    "paper_order_allowed": intent.paper_order_allowed,
                    "boundary": intent.boundary,
                },
            )
        return intent

    def add(
        self,
        *,
        status: str,
        instrument: str,
        direction: str,
        venue: str,
        strategy: str,
        catalyst: str,
        evidence_summary: str,
        probability_estimate: float | None,
        market_implied_probability: float | None,
        price_gap: str,
        proposed_entry: str,
        invalidation: str,
        holding_window: str,
        risk_size_gbp: float,
        risk_size_pct: float,
        risk_state: str,
        blocked_reason: str = "",
        execution_allowed: bool = False,
        paper_order_allowed: bool = False,
        source_signal_id: str | None = None,
        source_type: str = "manual_or_local",
        akber_filter: dict[str, str] | None = None,
        risk_checks: dict[str, str] | None = None,
        tags: tuple[str, ...] = (),
        intent_id: str | None = None,
        boundary: str = "Trade intent only. Not an order and not a recommendation.",
        log_event: bool = True,
    ) -> TradeIntent:
        created_at = _now()
        intent = TradeIntent(
            schema_version=TRADE_INTENT_SCHEMA_VERSION,
            intent_id=intent_id or str(uuid4()),
            status=status,
            instrument=instrument,
            direction=direction,
            venue=venue,
            strategy=strategy,
            catalyst=catalyst,
            evidence_summary=evidence_summary,
            probability_estimate=probability_estimate,
            market_implied_probability=market_implied_probability,
            price_gap=price_gap,
            proposed_entry=proposed_entry,
            invalidation=invalidation,
            holding_window=holding_window,
            risk_size_gbp=risk_size_gbp,
            risk_size_pct=risk_size_pct,
            risk_state=risk_state,
            blocked_reason=blocked_reason,
            execution_allowed=execution_allowed,
            paper_order_allowed=paper_order_allowed,
            source_signal_id=source_signal_id,
            source_type=source_type,
            akber_filter=akber_filter or {},
            risk_checks=risk_checks or {},
            tags=tuple(tag.strip() for tag in tags if tag.strip()),
            created_at=created_at,
            updated_at=created_at,
            boundary=boundary,
        )
        return self.add_intent(intent, log_event=log_event)

    def read_intents(self, limit: int | None = None) -> tuple[TradeIntent, ...]:
        if not self.path.exists():
            return ()

        intents: list[TradeIntent] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    payload = json.loads(stripped)
                    payload["tags"] = tuple(payload.get("tags", ()))
                    intents.append(TradeIntent(**payload))
                except (TypeError, json.JSONDecodeError) as exc:
                    raise ValueError(f"invalid trade intent line {line_number} in {self.path}") from exc
        if limit is not None:
            intents = intents[-limit:]
        for intent in intents:
            validate_trade_intent(intent)
        return tuple(intents)

    def health(self) -> dict[str, Any]:
        try:
            intents = self.read_intents()
        except Exception as exc:  # noqa: BLE001 - health should report the failure
            return {
                "status": "degraded",
                "schema_version": TRADE_INTENT_SCHEMA_VERSION,
                "error": str(exc),
            }
        counts = Counter(intent.status for intent in intents)
        return {
            "status": "ok",
            "schema_version": TRADE_INTENT_SCHEMA_VERSION,
            "intent_count": len(intents),
            "by_status": dict(sorted(counts.items())),
            "execution_allowed_count": sum(1 for intent in intents if intent.execution_allowed),
            "paper_order_allowed_count": sum(1 for intent in intents if intent.paper_order_allowed),
            "boundary": "Local trade intent store only. No broker order path exists in D5.",
        }


def ensure_d5_sample_trade_intents(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    store = TradeIntentStore(settings=settings)
    existing_ids = {intent.intent_id for intent in store.read_intents()}
    created: list[str] = []
    boundary = "D5 local test record only. Not an order, not advice, and no broker route exists."

    if "d5-sample-candidate-crude-oil" not in existing_ids:
        store.add(
            intent_id="d5-sample-candidate-crude-oil",
            status="candidate",
            instrument="USO options watch",
            direction="long_volatility",
            venue="paper_options_watchlist",
            strategy="Akber 6-step catalyst-volatility",
            catalyst="Energy transport disruption shadow hypothesis from physical and conflict source queues.",
            evidence_summary=(
                "Shadow evidence exists, but Signal Integrity Gate, Strategy Lead review, "
                "and Risk Agent sizing are not complete."
            ),
            probability_estimate=0.54,
            market_implied_probability=0.47,
            price_gap="+7pp estimated edge pending Black-Scholes Gap report",
            proposed_entry="Wait for IV percentile below 20 and structural break above prior-week range.",
            invalidation=(
                "Discard if a second independent source does not confirm the catalyst "
                "or crude volatility expands before entry."
            ),
            holding_window="7-14 days after verified catalyst",
            risk_size_gbp=0,
            risk_size_pct=0,
            risk_state="not_reviewed_by_risk_agent",
            source_signal_id="d5-local-fixture",
            source_type="d5_contract_fixture",
            akber_filter={
                "low_volatility": "pending_iv_check",
                "options_distribution_gap": "pending_black_scholes_gap",
                "catalyst_identification": "shadow_evidence_exists",
                "technical_setup": "pending_entry_zone",
                "obv_volume": "pending_volume_confirmation",
                "approval_policy": "not_reached",
            },
            risk_checks={
                "signal_approval": "not_reached",
                "hard_caps": "not_reviewed",
                "broker_heartbeat": "blocked_no_broker_write",
                "event_log": "available",
                "kill_switch": "no_execution_path",
            },
            tags=("d5_fixture", "paper_mode", "candidate"),
            boundary=boundary,
        )
        created.append("d5-sample-candidate-crude-oil")

    if "d5-sample-blocked-semiconductor" not in existing_ids:
        store.add(
            intent_id="d5-sample-blocked-semiconductor",
            status="blocked",
            instrument="Semiconductor basket watch",
            direction="long_semiconductor_volatility",
            venue="paper_options_watchlist",
            strategy="Akber 6-step catalyst-volatility",
            catalyst="Semiconductor export-control narrative without enough dated corroboration.",
            evidence_summary=(
                "One narrative input exists, but there is no dated catalyst, no options "
                "distribution gap, and no volume confirmation."
            ),
            probability_estimate=0.38,
            market_implied_probability=None,
            price_gap="unknown_no_options_gap",
            proposed_entry="none",
            invalidation="Blocked until dated catalyst, second source, and volume confirmation exist.",
            holding_window="none",
            risk_size_gbp=0,
            risk_size_pct=0,
            risk_state="blocked_before_risk_agent",
            blocked_reason="insufficient_independent_corroboration",
            source_signal_id="d5-local-fixture",
            source_type="d5_contract_fixture",
            akber_filter={
                "low_volatility": "not_checked",
                "options_distribution_gap": "missing",
                "catalyst_identification": "failed_no_dated_catalyst",
                "technical_setup": "not_reached",
                "obv_volume": "not_reached",
                "approval_policy": "not_reached",
            },
            risk_checks={
                "signal_approval": "not_reached",
                "hard_caps": "not_reviewed",
                "broker_heartbeat": "blocked_no_broker_write",
                "event_log": "available",
                "kill_switch": "no_execution_path",
            },
            tags=("d5_fixture", "paper_mode", "blocked"),
            boundary=boundary,
        )
        created.append("d5-sample-blocked-semiconductor")

    intents = store.read_intents()
    return {
        "status": "ok",
        "created_count": len(created),
        "created_intent_ids": created,
        "intent_count": len(intents),
        "candidate_count": sum(1 for intent in intents if _status_bucket(intent) == "candidates"),
        "blocked_count": sum(1 for intent in intents if intent.status == "blocked"),
        "execution_allowed_count": sum(1 for intent in intents if intent.execution_allowed),
        "paper_order_allowed_count": sum(1 for intent in intents if intent.paper_order_allowed),
        "boundary": "D5 creates local intent records only. It does not create broker orders.",
    }


def trade_intent_summary(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    store = TradeIntentStore(settings=settings)
    health = store.health()
    intents = store.read_intents() if health["status"] == "ok" else ()
    buckets = Counter(_status_bucket(intent) for intent in intents)
    return {
        "status": health["status"],
        "schema_version": TRADE_INTENT_SCHEMA_VERSION,
        "intent_count": len(intents),
        "candidate_count": buckets.get("candidates", 0),
        "blocked_count": buckets.get("blocked", 0),
        "staged_order_count": buckets.get("staged_orders", 0),
        "submitted_order_count": buckets.get("submitted_orders", 0),
        "open_position_count": buckets.get("open_positions", 0),
        "closed_trade_count": buckets.get("closed_trades", 0),
        "postmortem_due_count": buckets.get("postmortems_due", 0),
        "execution_allowed_count": health.get("execution_allowed_count", 0),
        "paper_order_allowed_count": health.get("paper_order_allowed_count", 0),
        "boundary": health.get("boundary", "No trade intent store is available."),
    }
