"""Strict canonical transaction models for trigger-to-outcome decisions."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from hashlib import sha256
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = "qadam_decision_transaction.v2"
LEGACY_SCHEMA_VERSIONS = {"qadam_decision_transaction.v1"}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Direction(StrEnum):
    LONG = "long"
    SHORT = "short"
    ABSTAIN = "abstain"


class GateState(StrEnum):
    PASS = "pass"
    HOLD = "hold"
    VETO = "veto"
    NOT_APPLICABLE = "not_applicable"


class GateSeverity(StrEnum):
    HARD = "hard"
    SOFT = "soft"
    DIAGNOSTIC = "diagnostic"


class RouterState(StrEnum):
    REJECT = "reject"
    WATCHLIST = "watchlist"
    SHADOW_ONLY = "shadow_only"
    HOLD = "hold"
    REPAIR_REQUESTED = "repair_requested"
    BLOCKED_SAFETY_BOUNDARY = "blocked_safety_boundary"
    PAPER_REVIEW_CANDIDATE = "paper_review_candidate"


class AuthorityBoundary(StrictModel):
    paper_only: Literal[True] = True
    live_capital_enabled: Literal[False] = False
    direct_broker_write_allowed: Literal[False] = False
    proof_credit_allowed: Literal[False] = False
    command_authority: Literal[False] = False


class PrimaryBlocker(StrictModel):
    blocker_code: str = Field(min_length=1)
    blocker_class: Literal[
        "investment",
        "market_session",
        "provider",
        "contract_defect",
        "risk",
        "duplicate",
        "safety",
        "none",
    ]
    summary: str = Field(min_length=1)
    retryable: bool
    dependent_consequences: tuple[str, ...] = ()


class ExecutionContext(StrictModel):
    context_id: str = Field(min_length=1)
    instrument: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    status: Literal[
        "market_closed",
        "quote_ready",
        "provider_rate_limited",
        "provider_degraded",
        "instrument_not_tradable",
        "spread_adverse",
        "execution_context_expired",
    ]
    observed_at: str
    expires_at: str
    bid: float | None = None
    ask: float | None = None
    midpoint: float | None = None
    spread_bps: float | None = None
    price: float | None = None
    volatility: float | None = None
    liquidity_proxy: float | None = None
    volume_or_flow: float | None = None
    provenance: dict[str, Any]

    @field_validator("observed_at", "expires_at")
    @classmethod
    def valid_timestamp(cls, value: str) -> str:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value

    @model_validator(mode="after")
    def quote_fields_match_status(self) -> "ExecutionContext":
        if self.status == "quote_ready":
            if self.bid is None or self.ask is None or self.midpoint is None:
                raise ValueError("quote_ready_requires_bid_ask_midpoint")
            if self.ask < self.bid:
                raise ValueError("quote_ask_below_bid")
        return self


class GateDecision(StrictModel):
    gate_decision_id: str = Field(min_length=1)
    gate_name: str = Field(min_length=1)
    sequence: int = Field(ge=0)
    state: GateState
    severity: GateSeverity
    measured_value: float | int | str | bool | None
    threshold: float | int | str | bool | None
    explanation: str = Field(min_length=1)
    size_haircut: float = Field(ge=0.0, le=1.0)
    evidence_ids: tuple[str, ...] = ()


class DecisionTransaction(StrictModel):
    schema_version: Literal["qadam_decision_transaction.v2"] = SCHEMA_VERSION
    decision_id: str = Field(min_length=1)
    generation_id: str = Field(min_length=1)
    candidate_identity: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    research_goal_id: str = Field(min_length=1)
    evidence_class: str = Field(min_length=1)
    strategy_id: str = Field(min_length=1)
    strategy_version: str = Field(min_length=1)
    instrument: str = Field(min_length=1)
    direction: Direction
    stage: str = Field(min_length=1)
    created_at: str
    updated_at: str
    trigger: dict[str, Any]
    economic_signal_identity_id: str | None = None
    evidence_digest: str | None = None
    decision_policy_versions: dict[str, str] = Field(default_factory=dict)
    market_judgment: dict[str, Any] = Field(default_factory=dict)
    uncertainty_actions: tuple[dict[str, Any], ...] = ()
    adaptive_size: dict[str, Any] = Field(default_factory=dict)
    delayed_entry: dict[str, Any] = Field(default_factory=dict)
    signal_lifecycle: dict[str, Any] = Field(default_factory=dict)
    execution_context: ExecutionContext | None = None
    gate_decisions: tuple[GateDecision, ...] = ()
    primary_blocker: PrimaryBlocker | None = None
    router_state: RouterState | None = None
    authority: AuthorityBoundary = AuthorityBoundary()

    @field_validator("created_at", "updated_at")
    @classmethod
    def valid_timestamp(cls, value: str) -> str:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value

    @model_validator(mode="after")
    def final_state_has_one_blocker(self) -> "DecisionTransaction":
        if self.router_state is not None:
            if self.router_state == RouterState.PAPER_REVIEW_CANDIDATE:
                if self.primary_blocker is not None and self.primary_blocker.blocker_class != "none":
                    raise ValueError("paper_candidate_cannot_have_blocker")
            elif self.primary_blocker is None:
                raise ValueError("terminal_non_candidate_requires_primary_blocker")
        combined_multiplier = self.adaptive_size.get("combined_multiplier")
        if combined_multiplier is not None and not 0.0 <= float(combined_multiplier) <= 1.0:
            raise ValueError("adaptive_size_multiplier_out_of_bounds")
        hard_ceiling = self.adaptive_size.get("hard_ceiling_usd")
        if hard_ceiling is not None and float(hard_ceiling) > 5_000.0:
            raise ValueError("adaptive_size_hard_ceiling_expanded")
        if self.delayed_entry.get("broker_write_allowed") not in {None, False}:
            raise ValueError("delayed_entry_cannot_write_broker")
        return self

    def payload_sha256(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return sha256(payload.encode("utf-8")).hexdigest()


def migrate_decision_transaction_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Upgrade a known legacy transaction without inventing decision facts."""

    migrated = dict(payload)
    schema_version = str(migrated.get("schema_version") or "")
    if schema_version == SCHEMA_VERSION:
        return migrated
    if schema_version not in LEGACY_SCHEMA_VERSIONS:
        raise ValueError(f"unknown_decision_transaction_schema:{schema_version or 'missing'}")
    migrated["schema_version"] = SCHEMA_VERSION
    migrated.setdefault("economic_signal_identity_id", None)
    migrated.setdefault("evidence_digest", None)
    migrated.setdefault("decision_policy_versions", {})
    migrated.setdefault("market_judgment", {})
    migrated.setdefault("uncertainty_actions", ())
    migrated.setdefault("adaptive_size", {})
    migrated.setdefault("delayed_entry", {})
    migrated.setdefault("signal_lifecycle", {})
    return migrated


class PaperOpsHandoffRecord(StrictModel):
    schema_version: Literal["qadam_paperops_handoff_record.v1"] = (
        "qadam_paperops_handoff_record.v1"
    )
    handoff_id: str = Field(min_length=1)
    decision_id: str = Field(min_length=1)
    candidate_identity: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    route: Literal["guarded_alpaca_paper_only"]
    state: Literal["accepted_for_paperops_review", "consumed", "rejected", "duplicate"]
    created_at: str
    payload: dict[str, Any]
    economic_signal_identity_id: str | None = None
    evidence_digest: str | None = None
    evidence_size_multiplier: float = Field(default=1.0, ge=0.0, le=1.0)
    authority: AuthorityBoundary = AuthorityBoundary()


class LifecycleEventRecord(StrictModel):
    schema_version: Literal["qadam_lifecycle_event_record.v1"] = (
        "qadam_lifecycle_event_record.v1"
    )
    event_id: str = Field(min_length=1)
    trade_id: str = Field(min_length=1)
    handoff_id: str | None
    state: Literal[
        "submitted",
        "accepted",
        "partial_fill",
        "filled",
        "cancelled",
        "rejected",
        "expired",
        "open",
        "exit_planned",
        "closed",
        "postmortem_complete",
    ]
    observed_at: str
    payload: dict[str, Any]
    proof_eligible: Literal[False] = False


class OrderEvent(StrictModel):
    schema_version: Literal["qadam_order_event.v1"] = "qadam_order_event.v1"
    event_id: str = Field(min_length=1)
    handoff_id: str | None
    broker_order_id_hash: str | None
    event_type: Literal[
        "submitted",
        "accepted",
        "partial_fill",
        "filled",
        "cancelled",
        "rejected",
        "expired",
        "reconciled",
    ]
    observed_at: str
    payload: dict[str, Any]
    authority: AuthorityBoundary = AuthorityBoundary()


class TradeOutcome(StrictModel):
    schema_version: Literal["qadam_trade_outcome.v1"] = "qadam_trade_outcome.v1"
    outcome_id: str = Field(min_length=1)
    trade_id: str = Field(min_length=1)
    handoff_id: str | None
    state: Literal["open", "closed", "cancelled", "rejected", "expired"]
    observed_at: str
    realized_pnl: float | None = None
    lineage_complete: bool
    proof_eligible: Literal[False] = False
    payload: dict[str, Any]


def transaction_schema() -> dict[str, Any]:
    return DecisionTransaction.model_json_schema()


__all__ = [
    "AuthorityBoundary",
    "DecisionTransaction",
    "Direction",
    "ExecutionContext",
    "GateDecision",
    "GateSeverity",
    "GateState",
    "LifecycleEventRecord",
    "LEGACY_SCHEMA_VERSIONS",
    "OrderEvent",
    "PaperOpsHandoffRecord",
    "PrimaryBlocker",
    "RouterState",
    "TradeOutcome",
    "migrate_decision_transaction_payload",
    "transaction_schema",
]
