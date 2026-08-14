"""Canonical strategy-to-decision intermediate representation.

The envelope is a paper-only compilation artifact. It normalizes strategy
drafts and same-generation decision evidence so Akber and downstream readers
do not need to rediscover fields from competing JSON shapes.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from orchestrator.qadam_akber_filter_v3 import (
    DISCOVERY_MICRO_CONFIRMATION_ALTERNATIVES,
    DISCOVERY_MICRO_REQUIRED_FIELDS,
)
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    sha256_json,
    unique_errors,
    validate_authority,
)

SCHEMA_VERSION = "qadam.tradeability-envelope.v1"
ARTIFACT_TYPE = "qadam_tradeability_envelope"
ENVELOPES_ARTIFACT = "qadam_tradeability_envelopes.jsonl"
REGISTRY_ARTIFACT = "qadam_tradeability_envelope_registry.json"
REJECTIONS_ARTIFACT = "qadam_tradeability_envelope_rejections.jsonl"
CHECK_ARTIFACT = "qadam_tradeability_envelope_checks.json"
SCHEMA_PATH = Path("schemas/qadam.tradeability-envelope.v1.schema.json")

CONTEXT_FIELD_IDS = (
    "source_price_context",
    "fresh_catalyst",
    "technical_confirmation",
    "volume_or_flow_confirmation",
    "volatility_context",
    "pricing_gap_evidence",
    "nonlinear_quantum_review",
    "risk_reward_context",
    "invalidation_clarity",
    "liquidity_and_spread",
    "paperability_proxy",
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DirectionState(StrEnum):
    LONG = "long"
    SHORT = "short"
    UNRESOLVED = "unresolved"


class EvidenceState(StrEnum):
    AVAILABLE = "available"
    INACTIVE = "inactive"
    MISSING = "missing"
    STALE = "stale"
    UNAVAILABLE = "unavailable"
    ADVERSE = "adverse"
    NOT_APPLICABLE = "not_applicable"
    STRUCTURALLY_UNCOLLECTABLE = "structurally_uncollectable"


class BlockerClass(StrEnum):
    NONE = "none"
    CURRENT_MARKET_CONTEXT = "current_market_context"
    CURRENT_TRIGGER_INACTIVE = "current_trigger_inactive"
    ADVERSE_EVIDENCE = "adverse_evidence"
    CONTRACT_DEFECT = "contract_defect"
    PROVIDER_OUTAGE = "provider_outage"
    CLOSED_MARKET = "closed_market"
    RISK = "risk"
    ROUTE = "route"


class Identity(StrictModel):
    hypothesis_id: str
    candidate_identity_id: str
    research_goal_id: str
    strategy_version_id: str | None
    schema_version: str = SCHEMA_VERSION


class Generation(StrictModel):
    decision_generation_id: str
    generated_at: datetime
    decision_at: datetime
    input_hashes: dict[str, str]
    source_generation_ids: dict[str, str] = Field(default_factory=dict)
    mixed_generation_join: bool = False


class ProvenanceRecord(StrictModel):
    source_ref: str
    provider: str | None
    observed_at: datetime | None
    available_at: datetime | None
    parser_version: str | None
    origin_class: str
    trust_state: str
    fixture_backed: bool = False


class Pattern(StrictModel):
    pattern_relationship_id: str
    score_id: str
    method_id: str | None
    research_score: float | None
    score_is_probability: bool = False
    horizon: str


class Strategy(StrictModel):
    strategy_family_id: str
    strategy_label: str
    evidence_class: str
    experimental_tier: str | None
    mechanism: str
    falsifier: str
    entry_concept: str
    exit_concept: str
    execution_proxy: str


class Direction(StrictModel):
    state: DirectionState
    resolution_id: str | None
    evidence_refs: tuple[str, ...] = ()
    explanation: str


class EvidenceItem(StrictModel):
    field_id: str
    state: EvidenceState
    available: bool
    value: Any = None
    observed_at: datetime | None = None
    provider: str | None = None
    source_refs: tuple[str, ...] = ()
    provenance_complete: bool = False
    fixture_backed: bool = False
    reason: str = ""

    @model_validator(mode="after")
    def validate_available_state(self) -> "EvidenceItem":
        if self.available and self.state != EvidenceState.AVAILABLE:
            raise ValueError("available_evidence_state_mismatch")
        if self.available and (self.fixture_backed or not self.provenance_complete):
            raise ValueError("available_evidence_provenance_invalid")
        return self


class EvidenceBundle(StrictModel):
    source_price_context: EvidenceItem
    fresh_catalyst: EvidenceItem
    technical_confirmation: EvidenceItem
    volume_or_flow_confirmation: EvidenceItem
    volatility_context: EvidenceItem
    pricing_gap_evidence: EvidenceItem
    nonlinear_quantum_review: EvidenceItem
    risk_reward_context: EvidenceItem
    invalidation_clarity: EvidenceItem
    liquidity_and_spread: EvidenceItem
    paperability_proxy: EvidenceItem


class EvidenceProfile(StrictModel):
    profile_id: str
    evidence_class: str
    required_field_ids: tuple[str, ...]
    confirmation_alternative_ids: tuple[str, ...]
    evidence: EvidenceBundle


class CurrentTrigger(StrictModel):
    state: EvidenceState
    active: bool
    observed_at: datetime | None
    expires_at: datetime | None
    source_refs: tuple[str, ...]
    source_keys: tuple[str, ...]


class MarketContext(StrictModel):
    observed_instrument: str
    execution_proxy: str
    session_state: str
    quote_actionable: bool
    current_price: float | None
    volatility: float | None
    spread_bps: float | None
    liquidity_available: bool


class Economics(StrictModel):
    gross_expectancy: float | None
    expected_costs: float | None
    net_expectancy: float | None
    uncertainty: float | None
    source_method: str
    evidence_label: Literal["validated", "provisional", "unavailable"]
    positive_after_costs: bool | None


class Invalidation(StrictModel):
    conditions: tuple[str, ...]
    current_price: float | None
    invalidation_price: float | None
    lifecycle_response: str


class RiskPreconditions(StrictModel):
    expected_reward_to_risk: float | None
    maximum_notional_usd: float | None
    maximum_loss_usd: float | None
    cluster: str
    basis_risk: str
    duplicate_exposure_check_required: bool = True
    daily_drawdown_check_required: bool = True


class AgentContribution(StrictModel):
    packet_id: str
    role: str
    task_type: str
    model_id: str
    prompt_hash: str
    output_hash: str


class CriticReceipt(StrictModel):
    receipt_id: str
    critic_type: str
    verdict: Literal["accept", "revise", "reject", "operator_action_required"]
    predicate_ids: tuple[str, ...]
    artifact_hash: str


class Completeness(StrictModel):
    required_field_ids: tuple[str, ...]
    present_field_ids: tuple[str, ...]
    missing_field_ids: tuple[str, ...]
    unavailable_field_ids: tuple[str, ...]
    adverse_field_ids: tuple[str, ...]
    structurally_uncollectable_field_ids: tuple[str, ...]
    substitutions: dict[str, str] = Field(default_factory=dict)


class Routing(StrictModel):
    compiled_state: str
    blocker_class: BlockerClass
    blocker_codes: tuple[str, ...]
    next_stage: str
    order_created: bool = False
    handoff_created: bool = False


class TradeabilityEnvelope(StrictModel):
    schema_version: Literal[SCHEMA_VERSION] = SCHEMA_VERSION
    artifact_type: Literal[ARTIFACT_TYPE] = ARTIFACT_TYPE
    envelope_id: str
    generated_at: datetime
    public_safe: bool = True
    paper_only: bool = True
    source_draft_ref: str
    source_draft_hash: str
    identity: Identity
    generation: Generation
    authority: dict[str, bool | int]
    provenance: tuple[ProvenanceRecord, ...]
    pattern: Pattern
    strategy: Strategy
    direction: Direction
    evidence_profile: EvidenceProfile
    current_trigger: CurrentTrigger
    market_context: MarketContext
    economics: Economics
    invalidation: Invalidation
    risk_preconditions: RiskPreconditions
    agent_contributions: tuple[AgentContribution, ...] = ()
    critic_receipts: tuple[CriticReceipt, ...] = ()
    completeness: Completeness
    routing: Routing

    @field_validator("authority")
    @classmethod
    def validate_paper_authority(cls, value: dict[str, bool | int]) -> dict[str, bool | int]:
        errors = validate_authority(value, prefix="tradeability_envelope")
        if errors:
            raise ValueError(";".join(errors))
        return value

    @model_validator(mode="after")
    def validate_boundaries(self) -> "TradeabilityEnvelope":
        if not self.paper_only:
            raise ValueError("tradeability_envelope_not_paper_only")
        if self.generation.mixed_generation_join:
            raise ValueError("tradeability_envelope_mixed_generation")
        if self.routing.order_created or self.routing.handoff_created:
            raise ValueError("tradeability_envelope_created_downstream_authority")
        if self.completeness.structurally_uncollectable_field_ids and (
            self.routing.blocker_class != BlockerClass.CONTRACT_DEFECT
        ):
            raise ValueError("uncollectable_field_not_contract_defect")
        return self


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _evidence_state(record: dict[str, Any]) -> EvidenceState:
    state = str(record.get("state") or record.get("freshness_state") or "").lower()
    if record.get("fixture_backed") is True:
        return EvidenceState.MISSING
    if record.get("available") is True:
        return EvidenceState.AVAILABLE
    if "stale" in state:
        return EvidenceState.STALE
    if any(token in state for token in ("adverse", "veto", "unsafe", "invalid")):
        return EvidenceState.ADVERSE
    if any(token in state for token in ("inactive", "closed", "outside")):
        return EvidenceState.INACTIVE
    if any(token in state for token in ("unavailable", "unsupported", "dependency_missing")):
        return EvidenceState.UNAVAILABLE
    if state == "not_applicable":
        return EvidenceState.NOT_APPLICABLE
    if state == "structurally_uncollectable":
        return EvidenceState.STRUCTURALLY_UNCOLLECTABLE
    return EvidenceState.MISSING


def _evidence_item(field_id: str, record: Any) -> EvidenceItem:
    row = record if isinstance(record, dict) else {}
    state = _evidence_state(row)
    available = state == EvidenceState.AVAILABLE
    details = row.get("details") if isinstance(row.get("details"), dict) else {}
    return EvidenceItem(
        field_id=field_id,
        state=state,
        available=available,
        value=row.get("value"),
        observed_at=_parse_timestamp(row.get("observed_at") or row.get("available_at")),
        provider=str(row.get("provider") or details.get("provider") or "") or None,
        source_refs=tuple(str(value) for value in row.get("source_refs", []) if value),
        provenance_complete=bool(
            row.get("provenance_complete") is True
            or (
                available
                and row.get("fixture_backed") is not True
                and (row.get("provider") or row.get("origin_class") or row.get("source_refs"))
            )
        ),
        fixture_backed=bool(row.get("fixture_backed") is True),
        reason=str(row.get("reason") or ""),
    )


def _direction_state(value: Any) -> DirectionState:
    normalized = str(value or "").lower()
    if normalized == "long":
        return DirectionState.LONG
    if normalized == "short":
        return DirectionState.SHORT
    return DirectionState.UNRESOLVED


def _source_refs_from_hypothesis(hypothesis: dict[str, Any]) -> list[str]:
    pattern = hypothesis.get("pattern_lineage")
    pattern = pattern if isinstance(pattern, dict) else {}
    refs = [
        *pattern.get("fresh_support_sources", []),
        *pattern.get("fresh_trigger_sources", []),
        *pattern.get("fresh_quorum_sources", []),
    ]
    return sorted({str(value) for value in refs if value})


def _provenance_records(
    hypothesis: dict[str, Any], evidence: dict[str, EvidenceItem]
) -> tuple[ProvenanceRecord, ...]:
    records: list[ProvenanceRecord] = []
    for field_id, item in evidence.items():
        for source_ref in item.source_refs:
            records.append(
                ProvenanceRecord(
                    source_ref=source_ref,
                    provider=item.provider,
                    observed_at=item.observed_at,
                    available_at=item.observed_at,
                    parser_version=None,
                    origin_class="provider_current" if item.available else "qadam_runtime",
                    trust_state="verified" if item.provenance_complete else "unverified",
                    fixture_backed=item.fixture_backed,
                )
            )
    if not records:
        for source_ref in _source_refs_from_hypothesis(hypothesis):
            records.append(
                ProvenanceRecord(
                    source_ref=source_ref,
                    provider=None,
                    observed_at=None,
                    available_at=None,
                    parser_version=None,
                    origin_class="qadam_runtime",
                    trust_state="declared_not_currently_verified",
                    fixture_backed=False,
                )
            )
    deduped = {sha256_json(record.model_dump(mode="json")): record for record in records}
    return tuple(deduped[key] for key in sorted(deduped))


def compile_tradeability_envelope(
    hypothesis: dict[str, Any],
    packet: dict[str, Any],
    *,
    source_draft_ref: str,
    agent_contributions: list[dict[str, Any]] | None = None,
    critic_receipts: list[dict[str, Any]] | None = None,
    structurally_uncollectable_fields: list[str] | None = None,
) -> TradeabilityEnvelope:
    """Compile one legacy draft and one same-generation packet into v1."""

    generated_at = _parse_timestamp(packet.get("generated_at")) or datetime.now(timezone.utc)
    decision_at = _parse_timestamp(packet.get("decision_timestamp")) or generated_at
    context = packet.get("akber_context")
    context = context if isinstance(context, dict) else {}
    evidence_items = {
        field_id: _evidence_item(field_id, context.get(field_id))
        for field_id in CONTEXT_FIELD_IDS
    }
    evidence_bundle = EvidenceBundle(**evidence_items)
    pattern_lineage = hypothesis.get("pattern_lineage")
    pattern_lineage = pattern_lineage if isinstance(pattern_lineage, dict) else {}
    strategy_mapping = hypothesis.get("strategy_mapping")
    strategy_mapping = strategy_mapping if isinstance(strategy_mapping, dict) else {}
    direction_horizon = hypothesis.get("direction_horizon")
    direction_horizon = direction_horizon if isinstance(direction_horizon, dict) else {}
    mapping = hypothesis.get("instrument_proxy_mapping")
    mapping = mapping if isinstance(mapping, dict) else {}
    research_goal = hypothesis.get("research_goal_lineage")
    research_goal = research_goal if isinstance(research_goal, dict) else {}
    candidate = hypothesis.get("candidate_identity_material")
    candidate = candidate if isinstance(candidate, dict) else {}
    edge_range = hypothesis.get("expected_edge_range")
    edge_range = edge_range if isinstance(edge_range, dict) else {}
    risk = hypothesis.get("risk_concept")
    risk = risk if isinstance(risk, dict) else {}
    invalidation = hypothesis.get("invalidation_exit")
    invalidation = invalidation if isinstance(invalidation, dict) else {}
    entry = hypothesis.get("entry_concept")
    entry = entry if isinstance(entry, dict) else {}
    trigger = evidence_items["fresh_catalyst"]
    trigger_details = context.get("fresh_catalyst", {}).get("details", {})
    trigger_details = trigger_details if isinstance(trigger_details, dict) else {}
    market_session = packet.get("market_session")
    market_session = market_session if isinstance(market_session, dict) else {}
    liquidity = packet.get("liquidity_spread_and_adv")
    liquidity = liquidity if isinstance(liquidity, dict) else {}
    price_volatility = packet.get("current_price_and_volatility")
    price_volatility = price_volatility if isinstance(price_volatility, dict) else {}
    risk_details = context.get("risk_reward_context", {}).get("details", {})
    risk_details = risk_details if isinstance(risk_details, dict) else {}
    liquidity_details = context.get("liquidity_and_spread", {}).get("details", {})
    liquidity_details = liquidity_details if isinstance(liquidity_details, dict) else {}
    invalidation_details = context.get("invalidation_clarity", {}).get("details", {})
    invalidation_details = (
        invalidation_details if isinstance(invalidation_details, dict) else {}
    )
    discovery_micro = str(hypothesis.get("experimental_tier") or "") == "discovery_micro"
    required = tuple(
        str(value)
        for value in (
            packet.get("required_context_fields")
            or hypothesis.get("required_context_fields")
            or DISCOVERY_MICRO_REQUIRED_FIELDS
            if discovery_micro
            else CONTEXT_FIELD_IDS
        )
    )
    alternatives = tuple(
        str(value)
        for value in (
            hypothesis.get("confirmation_alternatives")
            or DISCOVERY_MICRO_CONFIRMATION_ALTERNATIVES
            if discovery_micro
            else ()
        )
    )
    present = tuple(sorted(field_id for field_id, item in evidence_items.items() if item.available))
    missing = tuple(
        sorted(
            field_id
            for field_id, item in evidence_items.items()
            if field_id in required and item.state in {EvidenceState.MISSING, EvidenceState.STALE}
        )
    )
    unavailable = tuple(
        sorted(
            field_id
            for field_id, item in evidence_items.items()
            if field_id in required and item.state == EvidenceState.UNAVAILABLE
        )
    )
    adverse = tuple(
        sorted(
            field_id
            for field_id, item in evidence_items.items()
            if item.state == EvidenceState.ADVERSE
        )
    )
    uncollectable = tuple(sorted(set(structurally_uncollectable_fields or [])))
    direction = _direction_state(direction_horizon.get("direction"))
    blocker_codes: list[str] = []
    if uncollectable:
        blocker_class = BlockerClass.CONTRACT_DEFECT
        blocker_codes.extend(f"structurally_uncollectable:{field}" for field in uncollectable)
    elif adverse:
        blocker_class = BlockerClass.ADVERSE_EVIDENCE
        blocker_codes.extend(f"adverse:{field}" for field in adverse)
    elif trigger.state == EvidenceState.INACTIVE:
        blocker_class = BlockerClass.CURRENT_TRIGGER_INACTIVE
        blocker_codes.append("current_trigger_inactive")
    elif missing or unavailable:
        blocker_class = BlockerClass.CURRENT_MARKET_CONTEXT
        blocker_codes.extend(f"missing:{field}" for field in (*missing, *unavailable))
    elif direction == DirectionState.UNRESOLVED:
        blocker_class = BlockerClass.CURRENT_MARKET_CONTEXT
        blocker_codes.append("direction_unresolved")
    else:
        blocker_class = BlockerClass.NONE
    evidence_label: Literal["validated", "provisional", "unavailable"]
    evidence_class = str(hypothesis.get("evidence_class") or "experimental_unvalidated")
    if edge_range.get("net_expectancy") is None:
        evidence_label = "unavailable"
    elif evidence_class == "validated_paper_strategy":
        evidence_label = "validated"
    else:
        evidence_label = "provisional"
    net_expectancy = _safe_float(
        risk_details.get("expected_net_return") or edge_range.get("net_expectancy")
    )
    source_draft_hash = sha256_json(hypothesis)
    envelope_material = {
        "hypothesis_id": hypothesis.get("hypothesis_id"),
        "candidate_identity_id": candidate.get("candidate_identity_id"),
        "decision_generation_id": packet.get("decision_generation_id"),
        "source_draft_hash": source_draft_hash,
    }
    envelope_id = "tradeability-envelope:" + sha256_json(envelope_material)[:24]
    result = TradeabilityEnvelope(
        envelope_id=envelope_id,
        generated_at=generated_at,
        source_draft_ref=source_draft_ref,
        source_draft_hash=source_draft_hash,
        identity=Identity(
            hypothesis_id=str(hypothesis.get("hypothesis_id") or ""),
            candidate_identity_id=str(candidate.get("candidate_identity_id") or ""),
            research_goal_id=str(research_goal.get("research_goal_id") or ""),
            strategy_version_id=str(hypothesis.get("strategy_version_id") or "") or None,
        ),
        generation=Generation(
            decision_generation_id=str(packet.get("decision_generation_id") or ""),
            generated_at=generated_at,
            decision_at=decision_at,
            input_hashes={
                str(key): str(value) for key, value in (packet.get("input_hashes") or {}).items()
            },
            source_generation_ids={
                "graph": str(pattern_lineage.get("graph_generation_id") or ""),
                "decision_packet": str(packet.get("decision_evidence_packet_id") or ""),
            },
            mixed_generation_join=bool(packet.get("mixed_generation_join") is True),
        ),
        authority=authority_flags(),
        provenance=_provenance_records(hypothesis, evidence_items),
        pattern=Pattern(
            pattern_relationship_id=str(pattern_lineage.get("pattern_relationship_id") or ""),
            score_id=str(pattern_lineage.get("score_id") or ""),
            method_id=str(pattern_lineage.get("method_id") or "") or None,
            research_score=_safe_float(pattern_lineage.get("raw_research_score")),
            score_is_probability=False,
            horizon=str(direction_horizon.get("horizon") or ""),
        ),
        strategy=Strategy(
            strategy_family_id=str(strategy_mapping.get("strategy_family_id") or ""),
            strategy_label=str(
                strategy_mapping.get("strategy_label")
                or strategy_mapping.get("strategy_family_id")
                or ""
            ),
            evidence_class=evidence_class,
            experimental_tier=str(hypothesis.get("experimental_tier") or "") or None,
            mechanism=str(
                hypothesis.get("catalyst_confirmation", {}).get("catalyst")
                or strategy_mapping.get("mechanism")
                or ""
            ),
            falsifier="; ".join(
                str(value) for value in invalidation.get("invalidation_conditions", []) if value
            ),
            entry_concept=str(entry.get("summary") or ""),
            exit_concept="; ".join(
                str(value) for value in invalidation.get("exit_conditions", []) if value
            ),
            execution_proxy=str(mapping.get("execution_proxy") or ""),
        ),
        direction=Direction(
            state=direction,
            resolution_id=str(direction_horizon.get("direction_resolution_id") or "") or None,
            evidence_refs=tuple(str(value) for value in trigger.source_refs),
            explanation=str(
                context.get("fresh_catalyst", {}).get("reason")
                or "Direction is compiled from the current strategy-specific evidence packet."
            ),
        ),
        evidence_profile=EvidenceProfile(
            profile_id=str(packet.get("evidence_profile") or "event_catalyst"),
            evidence_class=evidence_class,
            required_field_ids=required,
            confirmation_alternative_ids=alternatives,
            evidence=evidence_bundle,
        ),
        current_trigger=CurrentTrigger(
            state=trigger.state,
            active=bool(trigger.available),
            observed_at=trigger.observed_at,
            expires_at=_parse_timestamp(hypothesis.get("freshness", {}).get("expires_at")),
            source_refs=trigger.source_refs,
            source_keys=tuple(
                str(value) for value in trigger_details.get("fresh_trigger_sources", []) if value
            ),
        ),
        market_context=MarketContext(
            observed_instrument=str(mapping.get("observed_instrument") or ""),
            execution_proxy=str(mapping.get("execution_proxy") or ""),
            session_state=str(market_session.get("state") or "unavailable"),
            quote_actionable=bool(market_session.get("quote_actionable") is True),
            current_price=_safe_float(price_volatility.get("price")),
            volatility=_safe_float(
                context.get("volatility_context", {}).get("value")
                if not isinstance(context.get("volatility_context", {}).get("value"), dict)
                else context.get("volatility_context", {}).get("value", {}).get("volatility")
            ),
            spread_bps=_safe_float(
                liquidity.get("spread_bps") or liquidity_details.get("spread_bps")
            ),
            liquidity_available=evidence_items["liquidity_and_spread"].available,
        ),
        economics=Economics(
            gross_expectancy=_safe_float(edge_range.get("gross_expectancy")),
            expected_costs=_safe_float(risk_details.get("expected_costs")),
            net_expectancy=net_expectancy,
            uncertainty=_safe_float(edge_range.get("uncertainty")),
            source_method=str(edge_range.get("net_expectancy_source") or "unavailable"),
            evidence_label=evidence_label,
            positive_after_costs=(net_expectancy > 0) if net_expectancy is not None else None,
        ),
        invalidation=Invalidation(
            conditions=tuple(
                str(value) for value in invalidation.get("invalidation_conditions", []) if value
            ),
            current_price=_safe_float(invalidation_details.get("current_price")),
            invalidation_price=_safe_float(invalidation_details.get("invalidation_price")),
            lifecycle_response="exit_or_cancel_when_invalidation_is_observed",
        ),
        risk_preconditions=RiskPreconditions(
            expected_reward_to_risk=_safe_float(
                risk_details.get("reward_to_risk") or risk.get("expected_reward_to_risk")
            ),
            maximum_notional_usd=_safe_float(
                risk.get("maximum_notional_usd") or risk.get("absolute_notional_ceiling_usd")
            ),
            maximum_loss_usd=_safe_float(risk_details.get("maximum_loss_usd")),
            cluster=str(strategy_mapping.get("strategy_family_id") or "unknown"),
            basis_risk=str(mapping.get("proxy_basis") or "unknown"),
        ),
        agent_contributions=tuple(
            AgentContribution.model_validate(value) for value in (agent_contributions or [])
        ),
        critic_receipts=tuple(
            CriticReceipt.model_validate(value) for value in (critic_receipts or [])
        ),
        completeness=Completeness(
            required_field_ids=required,
            present_field_ids=present,
            missing_field_ids=missing,
            unavailable_field_ids=unavailable,
            adverse_field_ids=adverse,
            structurally_uncollectable_field_ids=uncollectable,
        ),
        routing=Routing(
            compiled_state=(
                "compiled_contract_defect"
                if blocker_class == BlockerClass.CONTRACT_DEFECT
                else "compiled_for_akber_review"
            ),
            blocker_class=blocker_class,
            blocker_codes=tuple(unique_errors(blocker_codes)),
            next_stage=(
                "engineering_repair"
                if blocker_class == BlockerClass.CONTRACT_DEFECT
                else "akber"
            ),
        ),
    )
    return result


def envelope_to_hypothesis_projection(
    envelope: TradeabilityEnvelope, source_hypothesis: dict[str, Any]
) -> dict[str, Any]:
    """Return the sole compatibility projection consumed by existing gates."""

    projected = deepcopy(source_hypothesis)
    projected.update(
        {
            "schema_version": "qadam_strategy_hypothesis_v3.canonical-envelope1",
            "artifact_type": "qadam_canonical_strategy_hypothesis_projection",
            "generated_at": envelope.generated_at.isoformat(),
            "tradeability_envelope_id": envelope.envelope_id,
            "tradeability_envelope_schema_version": envelope.schema_version,
            "decision_generation_id": envelope.generation.decision_generation_id,
            "source_draft_ref": envelope.source_draft_ref,
            "source_draft_hash": envelope.source_draft_hash,
            "authority": authority_flags(),
        }
    )
    projected.setdefault("direction_horizon", {})["direction"] = envelope.direction.state.value
    projected["direction_horizon"]["direction_resolution_id"] = envelope.direction.resolution_id
    projected.setdefault("expected_edge_range", {})["net_expectancy"] = (
        envelope.economics.net_expectancy
    )
    projected["expected_edge_range"]["net_expectancy_source"] = (
        envelope.economics.source_method
    )
    projected.setdefault("blocker_state", {})["contract_blockers"] = list(
        envelope.routing.blocker_codes
    )
    projected["blocker_state"]["tradeability_envelope_compiled"] = True
    return projected


def validate_envelope_dict(payload: dict[str, Any]) -> list[str]:
    try:
        TradeabilityEnvelope.model_validate(payload)
    except Exception as exc:  # Pydantic returns a structured diagnostic in the message.
        return [f"tradeability_envelope_invalid:{exc}"]
    return []


def envelope_schema() -> dict[str, Any]:
    return TradeabilityEnvelope.model_json_schema()


__all__ = [
    "ARTIFACT_TYPE",
    "CHECK_ARTIFACT",
    "CONTEXT_FIELD_IDS",
    "ENVELOPES_ARTIFACT",
    "REGISTRY_ARTIFACT",
    "REJECTIONS_ARTIFACT",
    "SCHEMA_PATH",
    "SCHEMA_VERSION",
    "TradeabilityEnvelope",
    "compile_tradeability_envelope",
    "envelope_schema",
    "envelope_to_hypothesis_projection",
    "validate_envelope_dict",
]
