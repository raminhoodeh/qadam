"""Layered market judgment and adaptive paper-trading projections.

This module does not add decision or execution authority.  It translates the
canonical tradeability envelope into typed consequences that existing Akber,
risk, Router, and PaperOps stages can consume.  Runtime artifacts are public-
safe projections of the same canonical record.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from statistics import median
import subprocess
from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_gate_policy import resolved_profile
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_json,
    unique_errors,
)

SCHEMA_VERSION = "qadam_layered_market_judgment.v1"
POLICY_VERSION = "qadam-layered-market-judgment.2-bounded-unknown-expectancy"

BASELINE_ARTIFACT = "qadam_layered_judgment_baseline.json"
ALIAS_REGISTRY_ARTIFACT = "qadam_strategy_alias_registry.json"
ACTIVITY_BASELINE_ARTIFACT = "qadam_activity_quality_baseline.json"
FIELD_OWNERSHIP_ARTIFACT = "qadam_decision_field_ownership.json"
PROVIDER_CAPABILITIES_ARTIFACT = "qadam_provider_feature_capabilities.json"
TRADER_PRIOR_ARTIFACT = "qadam_trader_prior_registry.jsonl"
JUDGMENTS_ARTIFACT = "qadam_layered_market_judgments.jsonl"
UNCERTAINTY_ACTIONS_ARTIFACT = "qadam_uncertainty_actions.jsonl"
DELAYED_ENTRY_ARTIFACT = "qadam_delayed_entry_queue.json"
ACTIVITY_HEALTH_ARTIFACT = "qadam_activity_quality_health.json"
DASHBOARD_ARTIFACT = "qadam_layered_market_judgment_dashboard.json"
CHECK_ARTIFACT = "qadam_layered_market_judgment_checks.json"
CERTIFICATION_ARTIFACT = "qadam_layered_market_judgment_certification.json"
CANARY_SESSIONS_ARTIFACT = "qadam_layered_market_judgment_canary_sessions.jsonl"
CHALLENGER_ATTRIBUTION_ARTIFACT = "qadam_layered_akber_challenger_attribution.json"
TELEGRAM_PROJECTION_ARTIFACT = "qadam_layered_market_judgment_telegram.json"

HARD_TRADE_CEILING_USD = 5_000.0
CANARY_SESSION_TARGET = 5
CANARY_CAPTURE_TARGET = 0.90
CANARY_MAX_DECISION_LATENCY_SECONDS = 20 * 60

# The operator dependency graph already prevents this service from running when
# its real decision inputs are unavailable.  Restrict the in-artifact health
# check to those upstream services so a service can recover from its own open
# circuit and presentation-only failures cannot block trading research.
DECISION_DEPENDENCY_SERVICE_IDS = frozenset(
    {
        "canonical_tradeability",
        "forward_shadow",
    }
)

STRATEGY_ALIASES = {
    "crude_oil_energy_security_disruption": "crude_oil_energy_security_disruption",
    "defence_geopolitical_repricing": "defence_repricing_geopolitical_watch",
    "defence_repricing_geopolitical_watch": "defence_repricing_geopolitical_watch",
    "event_probability_dislocation": "prediction_market_geopolitical_dislocation",
    "prediction_market_geopolitical_dislocation": "prediction_market_geopolitical_dislocation",
    "semiconductor_policy_asymmetry": "semiconductor_policy_options_asymmetry",
    "semiconductor_policy_options_asymmetry": "semiconductor_policy_options_asymmetry",
    "silver_macro_liquidity_stress": "silver_macro_liquidity_stress",
    "power_grid_scarcity_congestion": "power_scarcity_congestion",
    "power_scarcity_congestion": "power_scarcity_congestion",
}

STRATEGY_PROFILES = {
    "crude_oil_energy_security_disruption": "event_catalyst",
    "defence_repricing_geopolitical_watch": "event_catalyst",
    "semiconductor_policy_options_asymmetry": "event_catalyst",
    "silver_macro_liquidity_stress": "regime_state",
    "power_scarcity_congestion": "regime_state",
    "prediction_market_geopolitical_dislocation": "market_dislocation",
}

STRATEGY_MECHANISMS = {
    "crude_oil_energy_security_disruption": (
        "Physical supply disruption and geopolitical risk can reprice crude-oil and energy proxies."
    ),
    "defence_repricing_geopolitical_watch": (
        "Conflict, policy, contract and capacity evidence can change expected defence demand."
    ),
    "semiconductor_policy_options_asymmetry": (
        "Policy, capacity constraints and participation can make semiconductor pricing adjust unevenly."
    ),
    "silver_macro_liquidity_stress": (
        "Rates, dollar liquidity and commodity stress can change silver relative to gold and risk assets."
    ),
    "prediction_market_geopolitical_dislocation": (
        "Comparable event probabilities can diverge from listed-market pricing before one side reprices."
    ),
    "power_scarcity_congestion": (
        "Load, weather, outages and congestion can alter scarcity economics and listed utility proxies."
    ),
}

FIELD_OWNERS = {
    "source_price_context": ("qadam_decision_evidence_packets", "evidence_generation"),
    "fresh_catalyst": ("qadam_trigger_factory", "current_trigger"),
    "technical_confirmation": ("market_context_packet", "market_context"),
    "volume_or_flow_confirmation": ("market_context_packet", "market_context"),
    "volatility_context": ("market_context_packet", "market_context"),
    "pricing_gap_evidence": ("market_context_packet", "market_context"),
    "nonlinear_quantum_review": ("qadam_nonlinear_quantum_value", "research_review"),
    "risk_reward_context": ("qadam_forward_shadow", "economics"),
    "invalidation_clarity": ("qadam_strategy_translation", "risk_definition"),
    "liquidity_and_spread": ("qadam_execution_context", "execution_context"),
    "paperability_proxy": ("qadam_instrument_role_registry", "instrument_mapping"),
    "portfolio_risk": ("qadam_portfolio_risk_engine", "portfolio_risk"),
    "router_state": ("qadam_router_v3_paperops", "router"),
}

SOFT_EVIDENCE_FIELDS = {
    "technical_confirmation": "technical_confirmation",
    "volume_or_flow_confirmation": "volume_or_flow_confirmation",
    "nonlinear_quantum_review": "nonlinear_quantum_review",
    "pricing_gap_evidence": "technical_confirmation",
}
HARD_CONTEXT_FIELDS = {
    "source_price_context",
    "fresh_catalyst",
    "risk_reward_context",
    "invalidation_clarity",
    "paperability_proxy",
}
REFRESHABLE_EXECUTION_FIELDS = {"liquidity_and_spread"}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class UncertaintyActionType(StrEnum):
    HARD_STOP = "hard_stop"
    ADVERSE_VETO = "adverse_veto"
    REFRESH_AND_RETRY = "refresh_and_retry"
    DELAY_UNTIL_MARKET_WINDOW = "delay_until_market_window"
    SOFT_SIZE_HAIRCUT = "soft_size_haircut"
    TWO_SIDED_SHADOW = "two_sided_shadow"
    WATCHLIST_INACTIVE = "watchlist_inactive"
    REPAIR_REQUIRED = "repair_required"


class UncertaintyAction(StrictModel):
    action_id: str
    judgment_id: str
    field_id: str
    evidence_state: str
    action: UncertaintyActionType
    owner: str
    reason: str
    retry_at: str | None = None
    expires_at: str | None = None
    applied_multiplier: float = Field(default=1.0, ge=0.0, le=1.0)
    can_veto: bool
    authority: dict[str, Any] = Field(default_factory=authority_flags)

    @model_validator(mode="after")
    def validate_boundaries(self) -> "UncertaintyAction":
        if self.action == UncertaintyActionType.SOFT_SIZE_HAIRCUT and self.can_veto:
            raise ValueError("soft_evidence_cannot_veto")
        if self.action in {
            UncertaintyActionType.HARD_STOP,
            UncertaintyActionType.ADVERSE_VETO,
        } and self.applied_multiplier != 1.0:
            raise ValueError("hard_action_cannot_be_size_haircut")
        return self


class AdaptiveSizeDecision(StrictModel):
    policy_version: str = POLICY_VERSION
    base_notional_usd: float | None = Field(default=None, ge=0.0)
    multiplier_components: dict[str, float]
    combined_multiplier: float = Field(ge=0.0, le=1.0)
    proposed_notional_before_rounding_usd: float | None = Field(default=None, ge=0.0)
    proposed_notional_after_rounding_usd: float | None = Field(default=None, ge=0.0)
    binding_limit: str | None = None
    expected_loss_at_invalidation_usd: float | None = Field(default=None, ge=0.0)
    smaller_experiment_reason: str | None = None
    hard_ceiling_usd: float = Field(default=HARD_TRADE_CEILING_USD, le=HARD_TRADE_CEILING_USD)


class MarketJudgmentEnvelope(StrictModel):
    schema_version: str = SCHEMA_VERSION
    artifact_type: str = "qadam_market_judgment_envelope"
    judgment_id: str
    decision_id: str
    generation_id: str
    economic_signal_identity_id: str
    strategy_family_id: str
    execution_proxy: str
    strategy_version_id: str | None
    research_goal_id: str
    structural_thesis: dict[str, Any]
    regime_state: dict[str, Any]
    participation_state: dict[str, Any]
    volatility_state: dict[str, Any]
    long_path: dict[str, Any]
    short_path: dict[str, Any]
    wait_path: dict[str, Any]
    selected_path: str
    selected_path_reason: str
    evidence_ids: tuple[str, ...]
    observed_at: str
    published_at: str | None = None
    available_at: str
    expires_at: str | None
    provider_states: dict[str, str]
    missingness_assessment: tuple[UncertaintyAction, ...]
    primary_consequence: str
    adaptive_size: AdaptiveSizeDecision
    expected_return_class: str
    evidence_digest: str
    authority: dict[str, Any] = Field(default_factory=authority_flags)

    @model_validator(mode="after")
    def validate_authority_boundary(self) -> "MarketJudgmentEnvelope":
        if self.authority.get("broker_write_allowed") is not False:
            raise ValueError("market_judgment_broker_authority_forbidden")
        if self.authority.get("live_capital_enabled") is not False:
            raise ValueError("market_judgment_live_capital_forbidden")
        return self


def canonical_strategy_id(strategy_id: Any) -> str:
    normalized = str(strategy_id or "").strip().lower()
    return STRATEGY_ALIASES.get(normalized, normalized)


def evidence_profile_for_strategy(strategy_id: Any, fallback: str = "discovery_micro") -> str:
    return STRATEGY_PROFILES.get(canonical_strategy_id(strategy_id), fallback)


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


def _next_market_window(value: str) -> str:
    current = _parse_timestamp(value) or datetime.now(timezone.utc)
    candidate = current.replace(hour=13, minute=30, second=0, microsecond=0)
    if candidate <= current:
        candidate += timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return candidate.isoformat()


def _stable_id(prefix: str, material: Any) -> str:
    return f"{prefix}:{sha256_json(material)[:24]}"


def _evidence_items(envelope: dict[str, Any]) -> dict[str, dict[str, Any]]:
    profile = envelope.get("evidence_profile")
    profile = profile if isinstance(profile, dict) else {}
    evidence = profile.get("evidence")
    return evidence if isinstance(evidence, dict) else {}


def _field_owner(field_id: str) -> str:
    return FIELD_OWNERS.get(field_id, ("unowned", "contract_repair"))[0]


def _classify_missing_field(
    *,
    judgment_id: str,
    field_id: str,
    item: dict[str, Any],
    session_state: str,
    expires_at: str | None,
    generated_at: str,
    profile: dict[str, Any],
) -> UncertaintyAction:
    state = str(item.get("state") or "missing")
    owner = _field_owner(field_id)
    action = UncertaintyActionType.REPAIR_REQUIRED
    can_veto = True
    multiplier = 1.0
    retry_at: str | None = None
    reason = f"{field_id} has no classified evidence action."
    if state == "adverse":
        action = UncertaintyActionType.ADVERSE_VETO
        reason = f"{field_id} contains explicit adverse evidence."
    elif field_id in SOFT_EVIDENCE_FIELDS:
        rule = SOFT_EVIDENCE_FIELDS[field_id]
        multiplier = float((profile.get("soft_rules") or {}).get(rule, 0.85))
        action = UncertaintyActionType.SOFT_SIZE_HAIRCUT
        can_veto = False
        reason = f"Optional {field_id} is unavailable; reduce size instead of rejecting the setup."
    elif field_id in REFRESHABLE_EXECUTION_FIELDS:
        if any(token in session_state.lower() for token in ("closed", "outside", "inactive")):
            action = UncertaintyActionType.DELAY_UNTIL_MARKET_WINDOW
            retry_at = _next_market_window(generated_at)
            reason = f"{field_id} is required at execution time and will be measured at the next market window."
        else:
            action = UncertaintyActionType.REFRESH_AND_RETRY
            retry_at = (_parse_timestamp(generated_at) + timedelta(minutes=5)).isoformat()
            reason = f"{field_id} is refreshable current-market evidence; retry the owning provider."
        can_veto = False
    elif field_id in HARD_CONTEXT_FIELDS or field_id == "volatility_context":
        action = UncertaintyActionType.HARD_STOP
        reason = f"Required {field_id} is unavailable, so bounded paper risk cannot yet be established."
    return UncertaintyAction(
        action_id=_stable_id(
            "uncertainty-action",
            {"judgment_id": judgment_id, "field_id": field_id, "state": state, "action": action},
        ),
        judgment_id=judgment_id,
        field_id=field_id,
        evidence_state=state,
        action=action,
        owner=owner,
        reason=reason,
        retry_at=retry_at,
        expires_at=expires_at,
        applied_multiplier=multiplier,
        can_veto=can_veto,
    )


def _session_state(envelope_market: dict[str, Any], evidence: dict[str, dict[str, Any]]) -> str:
    direct = str(envelope_market.get("session_state") or "")
    if direct and direct != "unavailable":
        return direct
    participation = evidence.get("volume_or_flow_confirmation", {})
    value = participation.get("value") if isinstance(participation, dict) else None
    records = value.get("price_volume_records") if isinstance(value, dict) else []
    for record in records or []:
        if isinstance(record, dict) and record.get("session_state"):
            return str(record["session_state"])
    return direct or "unavailable"


def build_market_judgment(
    envelope: dict[str, Any],
    *,
    economic_signal_identity_id: str | None = None,
) -> MarketJudgmentEnvelope:
    """Translate one canonical tradeability envelope into layered judgment."""

    identity = envelope.get("identity") if isinstance(envelope.get("identity"), dict) else {}
    generation = envelope.get("generation") if isinstance(envelope.get("generation"), dict) else {}
    strategy = envelope.get("strategy") if isinstance(envelope.get("strategy"), dict) else {}
    pattern = envelope.get("pattern") if isinstance(envelope.get("pattern"), dict) else {}
    direction = envelope.get("direction") if isinstance(envelope.get("direction"), dict) else {}
    trigger = envelope.get("current_trigger") if isinstance(envelope.get("current_trigger"), dict) else {}
    market = envelope.get("market_context") if isinstance(envelope.get("market_context"), dict) else {}
    economics = envelope.get("economics") if isinstance(envelope.get("economics"), dict) else {}
    invalidation = envelope.get("invalidation") if isinstance(envelope.get("invalidation"), dict) else {}
    completeness = envelope.get("completeness") if isinstance(envelope.get("completeness"), dict) else {}
    evidence = _evidence_items(envelope)
    generated_at = str(generation.get("decision_at") or envelope.get("generated_at") or now_iso())
    expires_at = trigger.get("expires_at")
    canonical_strategy = canonical_strategy_id(strategy.get("strategy_family_id"))
    profile_id = evidence_profile_for_strategy(
        canonical_strategy,
        str((envelope.get("evidence_profile") or {}).get("profile_id") or "discovery_micro"),
    )
    profile = resolved_profile(profile_id)
    session_state = _session_state(market, evidence)
    signal_material = {
        "strategy_family_id": canonical_strategy,
        "research_goal_id": identity.get("research_goal_id"),
        "pattern_relationship_id": pattern.get("pattern_relationship_id"),
        "instrument": market.get("execution_proxy") or market.get("observed_instrument"),
        "horizon": pattern.get("horizon"),
        "direction": direction.get("state"),
    }
    signal_id = economic_signal_identity_id or _stable_id("economic-signal", signal_material)
    judgment_id = _stable_id(
        "market-judgment",
        {"signal": signal_id, "generation": generation.get("decision_generation_id")},
    )
    missing_fields = unique_errors(
        [
            *list(completeness.get("missing_field_ids") or []),
            *list(completeness.get("unavailable_field_ids") or []),
            *list(completeness.get("structurally_uncollectable_field_ids") or []),
        ]
    )
    actions = [
        _classify_missing_field(
            judgment_id=judgment_id,
            field_id=str(field_id),
            item=evidence.get(str(field_id), {}),
            session_state=session_state,
            expires_at=str(expires_at) if expires_at else None,
            generated_at=generated_at,
            profile=profile,
        )
        for field_id in missing_fields
    ]
    for field_id in completeness.get("adverse_field_ids") or []:
        if field_id not in missing_fields:
            actions.append(
                _classify_missing_field(
                    judgment_id=judgment_id,
                    field_id=str(field_id),
                    item={"state": "adverse"},
                    session_state=session_state,
                    expires_at=str(expires_at) if expires_at else None,
                    generated_at=generated_at,
                    profile=profile,
                )
            )
    if trigger.get("state") == "inactive" or trigger.get("active") is False:
        actions.append(
            UncertaintyAction(
                action_id=_stable_id("uncertainty-action", {"judgment": judgment_id, "trigger": "inactive"}),
                judgment_id=judgment_id,
                field_id="fresh_catalyst",
                evidence_state="inactive",
                action=UncertaintyActionType.WATCHLIST_INACTIVE,
                owner="qadam_trigger_factory",
                reason="The thesis remains researchable, but the current activation trigger is inactive.",
                expires_at=str(expires_at) if expires_at else None,
                can_veto=False,
            )
        )

    unestimated_discovery = bool(
        economics.get("source_method") == "bounded_loss_discovery_experiment"
        and economics.get("net_expectancy") is None
        and strategy.get("evidence_class") == "experimental_unvalidated"
        and strategy.get("experimental_tier") == "discovery_micro"
    )
    if unestimated_discovery:
        actions.append(UncertaintyAction(
            action_id=_stable_id("uncertainty-action", {"judgment": judgment_id, "expectancy": "unknown"}),
            judgment_id=judgment_id, field_id="unestimated_expectancy",
            evidence_state="unavailable", action=UncertaintyActionType.SOFT_SIZE_HAIRCUT,
            owner="qadam_portfolio_risk_engine", applied_multiplier=0.5,
            reason="Unknown expectancy limits this to a smaller, loss-bounded paper experiment.",
            can_veto=False,
        ))
    component_map = {
        action.field_id: action.applied_multiplier
        for action in actions
        if action.action == UncertaintyActionType.SOFT_SIZE_HAIRCUT
    }
    multiplier = 1.0
    for value in component_map.values():
        multiplier *= value
    if component_map:
        multiplier = max(float(profile.get("minimum_size_multiplier") or 0.0), multiplier)
    if unestimated_discovery:
        multiplier = min(multiplier, 0.5)
    multiplier = min(1.0, max(0.0, multiplier))

    action_types = {action.action for action in actions}
    if UncertaintyActionType.REPAIR_REQUIRED in action_types:
        primary_consequence = "repair_required"
    elif action_types.intersection({UncertaintyActionType.HARD_STOP, UncertaintyActionType.ADVERSE_VETO}):
        primary_consequence = "hard_hold_or_veto"
    elif action_types.intersection(
        {UncertaintyActionType.REFRESH_AND_RETRY, UncertaintyActionType.DELAY_UNTIL_MARKET_WINDOW}
    ):
        primary_consequence = "delayed_entry"
    elif UncertaintyActionType.WATCHLIST_INACTIVE in action_types:
        primary_consequence = "watchlist"
    elif component_map:
        primary_consequence = "reduced_size"
    else:
        primary_consequence = "full_size_eligible_for_next_gate"

    direction_state = str(direction.get("state") or "unresolved")
    selected_path = direction_state if direction_state in {"long", "short"} else "wait"
    if primary_consequence in {"delayed_entry", "watchlist", "hard_hold_or_veto", "repair_required"}:
        selected_path = "wait"
    invalidation_conditions = list(invalidation.get("conditions") or [])
    evidence_ids = tuple(
        sorted(
            {
                str(source_ref)
                for item in evidence.values()
                if isinstance(item, dict)
                for source_ref in item.get("source_refs") or []
                if source_ref
            }
        )
    )
    provider_states: dict[str, str] = {}
    for field_id, item in evidence.items():
        if not isinstance(item, dict):
            continue
        provider = str(item.get("provider") or field_id)
        provider_states[provider] = str(item.get("state") or "missing")
    source_method = str(economics.get("source_method") or "unavailable")
    evidence_label = str(economics.get("evidence_label") or "unavailable")
    if unestimated_discovery:
        return_class = "unestimated_discovery_experiment"
    elif evidence_label == "validated":
        return_class = "validated_estimate"
    elif economics.get("net_expectancy") is not None and source_method != "unavailable":
        return_class = "provisional_empirical_estimate"
    elif economics.get("positive_after_costs") is True:
        return_class = "scenario_bound_estimate"
    else:
        return_class = "unavailable"
    structural = {
        "thesis_id": _stable_id("structural-thesis", {"strategy": canonical_strategy, "version": identity.get("strategy_version_id")}),
        "mechanism": strategy.get("mechanism")
        or STRATEGY_MECHANISMS.get(canonical_strategy),
        "falsifier": strategy.get("falsifier"),
        "horizon": pattern.get("horizon"),
        "inference_only": True,
        "research_score": pattern.get("research_score"),
        "research_score_is_probability": False,
    }
    participation_item = evidence.get("volume_or_flow_confirmation", {})
    volatility_item = evidence.get("volatility_context", {})
    regime_state = {
        "state": "measured" if evidence.get("source_price_context", {}).get("available") is True else "under_evidenced",
        "provider_fact_ids": list(evidence.get("source_price_context", {}).get("source_refs") or []),
        "directional_signal": False,
    }
    participation_state = {
        "state": participation_item.get("state", "missing"),
        "value": participation_item.get("value"),
        "interpretation": "Participation evidence may confirm timing; low volume alone does not determine direction.",
        "directional_signal_by_itself": False,
    }
    volatility_state = {
        "state": volatility_item.get("state", "missing"),
        "value": volatility_item.get("value"),
        "interpretation": "Volatility estimates expected movement, not direction.",
        "directional_signal_by_itself": False,
    }
    long_path = {
        "activation": "Current long trigger, positive after-cost economics, and executable paper context.",
        "active": selected_path == "long",
        "invalidation": invalidation_conditions,
        "entry_style": "reduced_size" if multiplier < 1.0 else "current_market_context",
    }
    short_path = {
        "activation": "Current short trigger, positive after-cost economics, and executable paper context.",
        "active": selected_path == "short",
        "invalidation": invalidation_conditions,
        "entry_style": "reduced_size" if multiplier < 1.0 else "current_market_context",
    }
    wait_path = {
        "activation": primary_consequence,
        "active": selected_path == "wait",
        "next_actions": [action.action.value for action in actions],
    }
    digest_material = {
        "signal": signal_material,
        "evidence": evidence,
        "policy_version": POLICY_VERSION,
        "actions": [action.model_dump(mode="json") for action in actions],
    }
    return MarketJudgmentEnvelope(
        judgment_id=judgment_id,
        decision_id=str(envelope.get("envelope_id") or judgment_id),
        generation_id=str(generation.get("decision_generation_id") or "generation-unknown"),
        economic_signal_identity_id=signal_id,
        strategy_family_id=canonical_strategy,
        execution_proxy=str(market.get("execution_proxy") or ""),
        strategy_version_id=identity.get("strategy_version_id"),
        research_goal_id=str(identity.get("research_goal_id") or "research-goal-unknown"),
        structural_thesis=structural,
        regime_state=regime_state,
        participation_state=participation_state,
        volatility_state=volatility_state,
        long_path=long_path,
        short_path=short_path,
        wait_path=wait_path,
        selected_path=selected_path,
        selected_path_reason=(
            f"The current consequence is {primary_consequence.replace('_', ' ')}; "
            "the selected path does not create execution authority."
        ),
        evidence_ids=evidence_ids,
        observed_at=str(trigger.get("observed_at") or generated_at),
        published_at=(
            str(trigger.get("published_at")) if trigger.get("published_at") else None
        ),
        available_at=generated_at,
        expires_at=str(expires_at) if expires_at else None,
        provider_states=provider_states,
        missingness_assessment=tuple(actions),
        primary_consequence=primary_consequence,
        adaptive_size=AdaptiveSizeDecision(
            multiplier_components=component_map,
            combined_multiplier=round(multiplier, 6),
            smaller_experiment_reason=(
                "Bounded optional-evidence uncertainty reduces paper size instead of discarding the setup."
                if multiplier < 1.0
                else None
            ),
        ),
        expected_return_class=return_class,
        evidence_digest=sha256_json(digest_material),
    )


def trader_prior_records(generated_at: str) -> list[dict[str, Any]]:
    claim = (
        "An apparently overheated market can keep edging higher when participation is weak, "
        "implied volatility is low, and there are few active sellers; uncertainty should often "
        "change timing or size rather than automatically vetoing the setup."
    )
    material = {"author": "Akber", "claim": claim, "version": 1}
    recorded_at = _parse_timestamp(generated_at) or datetime.now(timezone.utc)
    return [
        {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_trader_prior",
            "prior_id": _stable_id("trader-prior", material),
            "version": 1,
            "author": "Akber",
            "recorded_at": generated_at,
            "claim": claim,
            "economic_mechanism": (
                "Participation, breadth, volatility pricing, and catalyst timing may explain why "
                "a structurally stretched market does not reverse immediately."
            ),
            "applicable_instruments": ["SPY", "QQQ", "SMH", "SOXX", "NVDA"],
            "applicable_regimes": ["narrow_breadth", "low_participation", "low_implied_volatility"],
            "expected_path": "sideways_or_modest_pullback_before_catalyst_dependent_continuation",
            "observable_confirmations": [
                "breadth_and_constituent_contribution",
                "relative_strength",
                "realised_and_implied_volatility",
                "volume_or_flow",
            ],
            "falsifiers": [
                "broad_high-volume_breakdown",
                "negative_after-cost_expectancy",
                "thesis_invalidation",
            ],
            "expiry": (recorded_at + timedelta(days=90)).isoformat(),
            "review_date": (recorded_at + timedelta(days=30)).isoformat(),
            "confidence": "qualitative_prior_pending_provider_evidence",
            "evidence_required_before_influence": [
                "provider_backed_breadth",
                "provider_backed_participation",
                "current_execution_context",
            ],
            "cannot_satisfy_source_quorum_alone": True,
            "cannot_create_candidate": True,
            "cannot_create_order": True,
            "policy_mutation_allowed": False,
            "authority": authority_flags(),
        }
    ]


def _order_timestamp(row: dict[str, Any]) -> datetime | None:
    return _parse_timestamp(
        row.get("filled_at") or row.get("submitted_at") or row.get("created_at") or row.get("generated_at")
    )


def _window_metrics(
    orders: Iterable[dict[str, Any]],
    *,
    start: datetime,
    now: datetime,
) -> dict[str, Any]:
    rows = [row for row in orders if (_order_timestamp(row) or datetime.min.replace(tzinfo=timezone.utc)) >= start]
    submitted = [row for row in rows if row.get("submitted_at") or row.get("status")]
    filled = [row for row in rows if str(row.get("status") or "").lower() in {"filled", "partially_filled"}]
    entries = [
        row
        for row in filled
        if str(row.get("position_intent") or "")
        in {"buy_to_open", "sell_to_open", "sell_short"}
        or (
            not row.get("position_intent")
            and not row.get("protective_exit_leg")
            and str(row.get("direction") or "").lower() == "buy"
        )
    ]
    exits = [
        row
        for row in filled
        if str(row.get("position_intent") or "") in {"sell_to_close", "buy_to_close"}
        or (not row.get("position_intent") and row.get("protective_exit_leg") is True)
    ]
    signal_ids = {
        str(row.get("economic_signal_identity_id") or row.get("decision_id") or row.get("client_order_id") or "")
        for row in entries
        if row.get("economic_signal_identity_id") or row.get("decision_id") or row.get("client_order_id")
    }
    by_signal: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_signal_digest: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in entries:
        key = str(row.get("economic_signal_identity_id") or row.get("decision_id") or "")
        if key:
            by_signal[key].append(row)
            digest = str(row.get("evidence_digest") or "legacy_digest_unknown")
            by_signal_digest[(key, digest)].append(row)
    same_signal_reentries = sum(max(0, len(group) - 1) for group in by_signal.values())
    unchanged_signal_reentries = sum(
        max(0, len(group) - 1) for group in by_signal_digest.values()
    )
    evidence_changed_reentries = max(0, same_signal_reentries - unchanged_signal_reentries)
    duplicate_ids = len(submitted) - len(
        {
            str(row.get("order_id") or row.get("client_order_id") or sha256_json(row))
            for row in submitted
        }
    )
    holding_times = []
    for row in exits:
        opened = _parse_timestamp(row.get("opened_at"))
        closed = _order_timestamp(row)
        if opened and closed and closed >= opened:
            holding_times.append((closed - opened).total_seconds())
    return {
        "start": start.isoformat(),
        "end": now.isoformat(),
        "raw_order_records": len(rows),
        "submitted_orders": len(submitted),
        "filled_orders": len(filled),
        "entries": len(entries),
        "exits": len(exits),
        "distinct_economic_hypotheses": len(signal_ids),
        "entry_signal_identity_ids": sorted(signal_ids),
        "distinct_instruments": len({str(row.get("instrument") or "") for row in rows if row.get("instrument")}),
        "distinct_correlated_clusters": len({str(row.get("correlated_cluster") or "") for row in rows if row.get("correlated_cluster")}),
        "completed_round_trips": min(len(entries), len(exits)),
        "same_signal_reentries": same_signal_reentries,
        "unchanged_signal_reentries": unchanged_signal_reentries,
        "evidence_changed_reentries": evidence_changed_reentries,
        "duplicate_or_rejected_writes": duplicate_ids
        + sum(str(row.get("status") or "").lower() in {"rejected", "duplicate"} for row in rows),
        "average_holding_seconds": round(sum(holding_times) / len(holding_times), 3) if holding_times else None,
        "median_holding_seconds": round(median(holding_times), 3) if holding_times else None,
        "realized_pnl_usd": round(sum(float(row.get("realized_pnl") or 0.0) for row in rows), 4),
        "unrealized_pnl_usd": round(sum(float(row.get("unrealized_pnl") or 0.0) for row in rows), 4),
    }


def _git_build_state() -> dict[str, Any]:
    root = runtime_dir().parents[1]
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        code_diff = subprocess.run(
            [
                "git",
                "diff",
                "--quiet",
                "HEAD",
                "--",
                "config",
                "orchestrator",
                "schemas",
                "scripts",
            ],
            cwd=root,
            check=False,
            capture_output=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "code_matches_commit": False}
    return {"commit": commit or None, "code_matches_commit": code_diff.returncode == 0}


def _record_canary_session_if_eligible(
    runtime,
    *,
    generated_at: str,
    validation_errors: list[str],
    activity: dict[str, Any],
) -> list[dict[str, Any]]:
    records = read_jsonl(runtime / CANARY_SESSIONS_ARTIFACT)
    clock = read_json(runtime / "qadam_market_clock_truth.json")
    build = _git_build_state()
    now = _parse_timestamp(generated_at) or datetime.now(timezone.utc)
    clock_at = _parse_timestamp(clock.get("generated_at"))
    clock_age = (now - clock_at).total_seconds() if clock_at else None
    eligible = (
        not validation_errors
        and build.get("code_matches_commit") is True
        and bool(build.get("commit"))
        and clock.get("provider_backed") is True
        and clock.get("sample_or_fixture") is False
        and clock.get("provider_fresh") is True
        and clock.get("is_open") is True
        and str(clock.get("session_phase") or "") == "regular"
        and clock_age is not None
        and 0 <= clock_age <= 180
    )
    market_date = str(clock.get("session_date") or "")
    commit = str(build.get("commit") or "")
    duplicate = any(
        row.get("market_date") == market_date and row.get("build_commit") == commit
        for row in records
    )
    if eligible and market_date and not duplicate:
        records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_layered_market_judgment_canary_session",
                "recorded_at": generated_at,
                "market_date": market_date,
                "session_phase": "regular",
                "provider": clock.get("provider"),
                "provider_clock_generated_at": clock.get("generated_at"),
                "build_commit": commit,
                "exact_build": True,
                "real_market_time_only": True,
                "backfilled": False,
                "activity_health": activity.get("status"),
                "eligible_setups_seen": activity.get("eligible_setups_seen", 0),
                "eligible_setups_submitted": activity.get("eligible_setups_submitted", 0),
                "eligible_setups_missed_due_to_internal_defects": activity.get(
                    "eligible_setups_missed_due_to_internal_defects", 0
                ),
                "eligible_opportunity_capture_rate": activity.get(
                    "eligible_opportunity_capture_rate"
                ),
                "median_setup_to_decision_seconds": activity.get(
                    "median_setup_to_decision_seconds"
                ),
                "duplicate_or_rejected_writes": (
                    (activity.get("windows") or {}).get("current_market_day", {}).get(
                        "duplicate_or_rejected_writes", 0
                    )
                ),
                "unchanged_signal_reentries": (
                    (activity.get("windows") or {}).get("current_market_day", {}).get(
                        "unchanged_signal_reentries", 0
                    )
                ),
                "authority": authority_flags(),
            }
        )
        AtomicArtifactStore(runtime).write_jsonl(CANARY_SESSIONS_ARTIFACT, records)
    return records


def _build_challenger_attribution(
    judgments: list[dict[str, Any]],
    *,
    generated_at: str,
) -> dict[str, Any]:
    records = []
    for judgment in judgments:
        consequence = str(judgment.get("primary_consequence") or "unknown")
        records.append(
            {
                "economic_signal_identity_id": judgment.get(
                    "economic_signal_identity_id"
                ),
                "strategy_family_id": judgment.get("strategy_family_id"),
                "layered_akber_consequence": consequence,
                "literal_akber_counterfactual": (
                    "hold_on_any_missing_field"
                    if judgment.get("missingness_assessment")
                    else "continue_to_existing_gates"
                ),
                "no_akber_counterfactual": "research_only_not_authorized",
                "outcome_state": "awaiting_forward_outcome",
                "paper_order_created": False,
                "proof_credit_allowed": False,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_layered_akber_challenger_attribution",
        "generated_at": generated_at,
        "status": "research_only",
        "record_count": len(records),
        "records": records,
        "canonical_policy": "layered_akber",
        "challenger_policies": ["literal_akber", "no_akber_baseline"],
        "policy_mutation_created": False,
        "execution_authority_created": False,
        "authority": authority_flags(),
    }


def _build_telegram_projection(
    judgments: list[dict[str, Any]],
    previous: dict[str, Any],
    *,
    generated_at: str,
) -> dict[str, Any]:
    current = judgments[0] if judgments else {}
    consequence = str(current.get("primary_consequence") or "no_current_setup")
    instrument = str(current.get("execution_proxy") or "the paper proxy")
    multiplier = float(
        (current.get("adaptive_size") or {}).get("combined_multiplier") or 1.0
    )
    if consequence == "reduced_size":
        message = (
            f"Qadam advanced a reduced-size {instrument} paper review. Optional "
            f"confirmation reduced the maximum proposed size by {round((1 - multiplier) * 100)}%. "
            "Akber, portfolio risk and Router still decide whether it reaches PaperOps."
        )
    elif consequence == "delayed_entry":
        message = (
            f"Qadam delayed the {instrument} setup until current execution data can be measured. "
            "The thesis remains under review; no order was created by this delay record."
        )
    elif consequence == "watchlist":
        message = (
            f"Qadam kept the {instrument} thesis on its watchlist because the current trigger "
            "is inactive. No order was created."
        )
    elif consequence == "full_size_eligible_for_next_gate":
        message = (
            f"Qadam advanced the {instrument} setup without an evidence haircut. It still must "
            "pass portfolio risk, Router and guarded PaperOps before any paper order."
        )
    elif consequence in {"hard_hold_or_veto", "repair_required"}:
        message = (
            f"Qadam stopped the {instrument} setup because its current evidence could not bound "
            "risk safely. The dashboard records the exact blocker."
        )
    else:
        message = "No current layered market-judgment decision is available."
    fingerprint = sha256_json(
        {
            "signal": current.get("economic_signal_identity_id"),
            "digest": current.get("evidence_digest"),
            "consequence": consequence,
            "message": message,
        }
    )
    duplicate = fingerprint == str(previous.get("material_fingerprint") or "")
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_layered_market_judgment_telegram_projection",
        "generated_at": generated_at,
        "status": "duplicate_suppressed" if duplicate else "material_candidate",
        "message": message,
        "material_fingerprint": fingerprint,
        "send_candidate": bool(current) and not duplicate,
        "deduplicated": duplicate,
        "public_safe": True,
        "review_only": True,
        "command_disabled": True,
        "telegram_live_send_allowed": False,
        "paper_order_created": False,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "authority": authority_flags(),
    }


def build_activity_quality(
    orders: list[dict[str, Any]],
    router_decisions: list[dict[str, Any]],
    delayed_queue: dict[str, Any],
    *,
    generated_at: str,
) -> dict[str, Any]:
    current = _parse_timestamp(generated_at) or datetime.now(timezone.utc)
    market_day_start = current.replace(hour=0, minute=0, second=0, microsecond=0)
    windows = {
        "trailing_24_hours": _window_metrics(orders, start=current - timedelta(hours=24), now=current),
        "current_market_day": _window_metrics(orders, start=market_day_start, now=current),
        "five_market_days": _window_metrics(orders, start=current - timedelta(days=7), now=current),
        "thirty_calendar_days": _window_metrics(orders, start=current - timedelta(days=30), now=current),
    }
    eligible_states = {
        "paper-review-candidate",
        "experimental-paper-review-candidate",
        "validated_paper_review_candidate",
        "experimental_paper_review_candidate",
    }
    eligible = [
        row for row in router_decisions if row.get("final_state") in eligible_states
    ]
    submitted_signal_ids = {
        str(row.get("economic_signal_identity_id") or "")
        for row in orders
        if row.get("economic_signal_identity_id")
        and (row.get("submitted_at") or row.get("order_id") or row.get("client_order_id"))
    }
    eligible_signal_ids = {
        str(row.get("economic_signal_identity_id") or "")
        for row in eligible
        if row.get("economic_signal_identity_id")
    }
    eligible_submitted = len(eligible_signal_ids.intersection(submitted_signal_ids))
    decision_latencies = []
    for row in router_decisions:
        judgment = row.get("market_judgment")
        judgment = judgment if isinstance(judgment, dict) else {}
        available_at = _parse_timestamp(judgment.get("available_at"))
        decided_at = _parse_timestamp(row.get("generated_at"))
        if available_at and decided_at and decided_at >= available_at:
            decision_latencies.append((decided_at - available_at).total_seconds())
    delayed = list(delayed_queue.get("records") or [])
    defects = [row for row in router_decisions if row.get("final_state") == "repair-requested"]
    current_window = windows["trailing_24_hours"]
    churn = (
        current_window["unchanged_signal_reentries"] > 0
        or current_window["duplicate_or_rejected_writes"] > 0
    )
    risk_paused = any(
        row.get("final_state") == "blocked-safety-boundary"
        or row.get("primary_root_cause") in {"drawdown_breach", "daily_loss_gate_breached"}
        for row in router_decisions
    )
    execution_degraded = any(
        row.get("final_state") == "repair-requested"
        and str(row.get("primary_root_cause") or "").startswith(("provider", "execution"))
        for row in router_decisions
    )
    if risk_paused:
        state = "risk_paused"
    elif churn:
        state = "churn_warning"
    elif execution_degraded:
        state = "execution_degraded"
    elif eligible and not current_window["entries"]:
        state = "conversion_degraded"
    elif defects:
        state = "conversion_degraded"
    elif current_window["entries"] or current_window["exits"]:
        state = "active_healthy"
    elif delayed:
        state = "healthy_idle_no_qualified_trigger"
    else:
        state = "healthy_idle_no_qualified_trigger"
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_activity_quality_snapshot",
        "generated_at": generated_at,
        "status": state,
        "windows": windows,
        "eligible_setups_seen": len(eligible),
        "eligible_setups_submitted": eligible_submitted,
        "eligible_opportunity_capture_rate": (
            round(eligible_submitted / len(eligible), 6) if eligible else None
        ),
        "eligible_opportunity_capture_state": (
            "measured" if eligible else "not_applicable_no_eligible_setups"
        ),
        "median_setup_to_decision_seconds": (
            round(median(decision_latencies), 3) if decision_latencies else None
        ),
        "eligible_setups_missed_due_to_internal_defects": len(defects),
        "legitimate_hard_stops": sum(row.get("final_state") == "reject" for row in router_decisions),
        "delayed_entry_queue_count": len(delayed),
        "churn_warning": churn,
        "raw_order_count_is_independent_trade_count": False,
        "authority": authority_flags(),
    }


def build_delayed_entry_queue(
    judgments: list[dict[str, Any]],
    existing: dict[str, Any],
    *,
    generated_at: str,
) -> dict[str, Any]:
    now = _parse_timestamp(generated_at) or datetime.now(timezone.utc)
    existing_by_signal = {
        str(row.get("economic_signal_identity_id")): row
        for row in existing.get("records", [])
        if isinstance(row, dict) and row.get("economic_signal_identity_id")
    }
    records: list[dict[str, Any]] = []
    for judgment in judgments:
        actions = judgment.get("missingness_assessment") or []
        queued_actions = [
            row
            for row in actions
            if row.get("action") in {"refresh_and_retry", "delay_until_market_window"}
        ]
        if not queued_actions:
            continue
        signal_id = str(judgment.get("economic_signal_identity_id") or "")
        prior = existing_by_signal.get(signal_id, {})
        expires = _parse_timestamp(judgment.get("expires_at"))
        if expires and expires <= now:
            continue
        retry_values = [
            _parse_timestamp(row.get("retry_at")) for row in queued_actions if row.get("retry_at")
        ]
        retry_values = [value for value in retry_values if value is not None]
        retry_count = int(prior.get("retry_count") or 0)
        prior_retry_at = _parse_timestamp(prior.get("retry_at"))
        retry_due = bool(prior_retry_at and prior_retry_at <= now)
        if retry_due:
            retry_count = min(6, retry_count + 1)
        refresh_retry = any(
            row.get("action") == "refresh_and_retry" for row in queued_actions
        )
        retry_at = min(retry_values) if retry_values else now
        if refresh_retry and retry_due:
            retry_at = now + timedelta(minutes=min(60, 5 * (2**retry_count)))
        record = {
            "schema_version": SCHEMA_VERSION,
            "queue_id": prior.get("queue_id") or _stable_id("delayed-entry", signal_id),
            "economic_signal_identity_id": signal_id,
            "judgment_id": judgment.get("judgment_id"),
            "generation_id": judgment.get("generation_id"),
            "evidence_digest": judgment.get("evidence_digest"),
            "state": "retry_exhausted" if retry_count >= 6 else "pending_refresh",
            "created_at": prior.get("created_at") or generated_at,
            "updated_at": generated_at,
            "retry_at": retry_at.isoformat(),
            "expires_at": judgment.get("expires_at"),
            "retry_count": retry_count,
            "maximum_retry_count": 6,
            "bounded_exponential_backoff": True,
            "owners": sorted({str(row.get("owner") or "") for row in queued_actions}),
            "reasons": [str(row.get("reason") or "") for row in queued_actions],
            "idempotency_material": _stable_id(
                "delayed-entry-idempotency",
                {"signal": signal_id, "digest": judgment.get("evidence_digest")},
            ),
            "paper_order_allowed": False,
            "broker_write_allowed": False,
            "authority": authority_flags(),
        }
        records.append(record)
    records.sort(key=lambda row: (str(row.get("retry_at")), str(row.get("queue_id"))))
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_delayed_entry_queue",
        "generated_at": generated_at,
        "status": "pending_refresh" if records else "empty",
        "record_count": len(records),
        "records": records,
        "restart_safe": True,
        "duplicate_write_allowed": False,
        "broker_write_allowed": False,
        "authority": authority_flags(),
    }


def _provider_capabilities(generated_at: str, runtime) -> dict[str, Any]:
    source_registry = read_json(runtime / "qadam_source_capability_registry.json")
    providers = source_registry.get("sources") or source_registry.get("records") or []
    rows = []
    for provider in providers:
        if not isinstance(provider, dict):
            continue
        provider_id = str(
            provider.get("source_key")
            or provider.get("source_id")
            or provider.get("provider_id")
            or provider.get("key")
            or ""
        )
        operating_state = str(
            provider.get("operating_state") or provider.get("status") or "unavailable"
        ).lower()
        freshness = str(provider.get("live_freshness") or "unknown").lower()
        reason = str(provider.get("status_reason") or "")
        role = str(provider.get("live_decision_role") or "")
        provider_backed_current = provider.get("provider_backed_current") is True
        historical_usable = provider.get("historical_alpha_usable") is True
        fixture_backed = (
            provider.get("sample_or_fixture") is True
            or provider.get("fixture_backed") is True
        )
        if fixture_backed:
            state = "unavailable"
        elif provider_id in {
            "tradingview_mcp",
            "tradingview_paid_alerts",
            "yahoo_finance",
            "yahoo_finance_or_tradingview",
        } or "supplemental" in role:
            state = "supplemental"
        elif provider_backed_current and freshness == "stale":
            state = "stale"
        elif provider_backed_current:
            state = "live"
        elif "rate" in operating_state and "limit" in operating_state:
            state = "rate_limited"
        elif historical_usable:
            state = "historical_only"
        elif any(token in reason.lower() for token in ("license", "entitle", "subscription")):
            state = "not_entitled"
        else:
            state = "unavailable"
        rows.append(
            {
                "provider_id": provider_id,
                "provider_name": provider.get("source_name") or provider_id,
                "source_family": provider.get("source_family"),
                "status": state,
                "source_operating_state": operating_state,
                "source_freshness": freshness,
                "status_reason": reason,
                "live": state == "live",
                "historical_only": state == "historical_only",
                "supplemental": state == "supplemental",
                "fixture_backed": fixture_backed,
                "provider_backed_current": provider_backed_current,
                "historical_alpha_usable": historical_usable,
            }
        )
    by_id = {str(row.get("provider_id") or ""): row for row in rows}

    def feature(
        feature_id: str,
        providers: list[str],
        *,
        required_for: str,
        implemented_state: str | None = None,
        coverage_scope: str = "declared_provider_scope",
    ) -> dict[str, Any]:
        candidates = [by_id[provider_id] for provider_id in providers if provider_id in by_id]
        states = [str(row.get("status") or "unavailable") for row in candidates]
        precedence = (
            "live",
            "historical_only",
            "supplemental",
            "stale",
            "rate_limited",
            "not_entitled",
            "unavailable",
        )
        state = implemented_state or next(
            (candidate for candidate in precedence if candidate in states), "unavailable"
        )
        return {
            "feature_id": feature_id,
            "status": state,
            "provider_ids": providers,
            "required_for": required_for,
            "coverage_scope": coverage_scope,
            "fixture_can_satisfy_live_evidence": False,
        }

    features = [
        feature(
            "earnings_transcripts",
            ["rss", "sec_edgar"],
            required_for="structural_context",
            implemented_state="supplemental",
            coverage_scope="filings_and_feed_context_not_full_transcript_tone",
        ),
        feature("market_volume", ["alpaca"], required_for="participation"),
        feature("relative_strength", ["alpaca"], required_for="tactical_confirmation"),
        feature("realized_volatility", ["alpaca"], required_for="volatility_context"),
        feature(
            "market_breadth",
            ["alpaca", "yahoo_finance"],
            required_for="optional_confirmation",
            implemented_state="supplemental",
            coverage_scope="watched_universe_not_full_index_constituents",
        ),
        feature(
            "constituent_contribution",
            ["alpaca", "yahoo_finance"],
            required_for="optional_confirmation",
            implemented_state="unavailable",
            coverage_scope="no_complete_live_index_constituent_panel",
        ),
        feature("implied_volatility_and_skew", ["unusual_whales"], required_for="options_dependent_mechanisms"),
        feature("options_flow", ["unusual_whales"], required_for="optional_confirmation"),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_provider_feature_capabilities",
        "generated_at": generated_at,
        "status": "truthful_capability_projection",
        "provider_count": len(rows),
        "providers": rows,
        "feature_count": len(features),
        "features": features,
        "required_states": [
            "live",
            "stale",
            "rate_limited",
            "unavailable",
            "historical_only",
            "supplemental",
            "not_entitled",
        ],
        "tradingview_role": "supplemental_only",
        "fixture_can_satisfy_live_evidence": False,
        "authority": authority_flags(),
    }


def _alias_registry(generated_at: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_strategy_alias_registry",
        "generated_at": generated_at,
        "aliases": STRATEGY_ALIASES,
        "canonical_profiles": STRATEGY_PROFILES,
        "unresolved_alias_count": 0,
        "authority": authority_flags(),
    }


def _field_ownership(generated_at: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_decision_field_ownership",
        "generated_at": generated_at,
        "fields": {
            field_id: {
                "producer": owner,
                "domain": domain,
                "canonical_owner_count": 1,
                "freshness_rule": "decision_time" if domain in {"current_trigger", "market_context", "execution_context"} else "generation_bound",
            }
            for field_id, (owner, domain) in FIELD_OWNERS.items()
        },
        "parallel_authority_allowed": False,
        "authority": authority_flags(),
    }


def validate_layered_state(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    alias = state.get("alias_registry", {})
    if alias.get("unresolved_alias_count") != 0:
        errors.append("strategy_aliases_unresolved")
    if canonical_strategy_id("semiconductor_policy_asymmetry") != "semiconductor_policy_options_asymmetry":
        errors.append("semiconductor_alias_not_reconciled")
    for strategy_id in STRATEGY_PROFILES:
        try:
            resolved_profile(STRATEGY_PROFILES[strategy_id])
        except ValueError as exc:
            errors.append(str(exc))
    for judgment in state.get("judgments", []):
        try:
            parsed = MarketJudgmentEnvelope.model_validate(judgment)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"market_judgment_invalid:{exc}")
            continue
        if parsed.adaptive_size.combined_multiplier > 1.0:
            errors.append("adaptive_multiplier_increases_size")
        actions_by_field = Counter(action.field_id for action in parsed.missingness_assessment)
        if any(count > 1 for count in actions_by_field.values()):
            errors.append(f"missing_field_has_multiple_primary_actions:{parsed.judgment_id}")
    queue = state.get("delayed_queue", {})
    if queue.get("broker_write_allowed") is not False:
        errors.append("delayed_queue_broker_authority_enabled")
    if any(row.get("paper_order_allowed") is not False for row in queue.get("records", [])):
        errors.append("delayed_queue_order_authority_enabled")
    activity = state.get("activity", {})
    if activity.get("raw_order_count_is_independent_trade_count") is not False:
        errors.append("raw_orders_misrepresented_as_trades")
    ownership = state.get("field_ownership", {}).get("fields", {})
    if any(row.get("canonical_owner_count") != 1 for row in ownership.values()):
        errors.append("decision_field_owner_count_invalid")
    capabilities = state.get("provider_capabilities", {})
    providers = capabilities.get("providers") or []
    allowed_provider_states = set(capabilities.get("required_states") or [])
    provider_ids = [str(row.get("provider_id") or "") for row in providers]
    if len(providers) != 41 or len(set(provider_ids)) != 41 or not all(provider_ids):
        errors.append("provider_capability_registry_identity_invalid")
    if any(str(row.get("status") or "") not in allowed_provider_states for row in providers):
        errors.append("provider_capability_state_invalid")
    if any(row.get("fixture_backed") is True and row.get("live") is True for row in providers):
        errors.append("fixture_provider_marked_live")
    signal_ids = state.get("signal_identity_chain", {})
    populated_signal_ids = {value for value in signal_ids.values() if value}
    if len(populated_signal_ids) > 1:
        errors.append("economic_signal_identity_mismatch")
    operator_health = state.get("operator_health", {})
    if int(operator_health.get("decision_dependency_open_circuit_count") or 0) > 0:
        errors.append("decision_dependency_circuit_open")
    if (
        int(
            operator_health.get(
                "decision_dependency_open_repair_request_count"
            )
            or 0
        )
        > 0
    ):
        errors.append("decision_dependency_repair_request_open")
    return unique_errors(errors)


def _operator_health_snapshot(
    circuit_state: dict[str, Any],
    repair_state: dict[str, Any],
) -> dict[str, Any]:
    services = circuit_state.get("services") or {}
    dependency_circuits = sorted(
        service_id
        for service_id in DECISION_DEPENDENCY_SERVICE_IDS
        if str((services.get(service_id) or {}).get("state") or "").lower()
        in {"open", "half_open"}
    )
    dependency_repairs = sorted(
        {
            str((request.get("evidence") or {}).get("service_id") or "")
            for request in repair_state.get("requests") or []
            if str(request.get("state") or "repair_requested").lower()
            not in {"closed", "dismissed", "resolved"}
            and str((request.get("evidence") or {}).get("service_id") or "")
            in DECISION_DEPENDENCY_SERVICE_IDS
        }
    )
    global_circuit_count = int(circuit_state.get("open_circuit_count") or 0)
    global_repair_count = int(repair_state.get("open_request_count") or 0)
    return {
        "open_circuit_count": global_circuit_count,
        "open_repair_request_count": global_repair_count,
        "decision_dependency_service_ids": sorted(DECISION_DEPENDENCY_SERVICE_IDS),
        "decision_dependency_open_circuit_count": len(dependency_circuits),
        "decision_dependency_open_circuit_service_ids": dependency_circuits,
        "decision_dependency_open_repair_request_count": len(dependency_repairs),
        "decision_dependency_open_repair_service_ids": dependency_repairs,
        "non_blocking_open_circuit_count": max(
            0, global_circuit_count - len(dependency_circuits)
        ),
        "non_blocking_open_repair_request_count": max(
            0, global_repair_count - len(dependency_repairs)
        ),
    }


def build_layered_market_judgment_state(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    generated_at = now_iso()
    envelopes = read_jsonl(runtime / "qadam_tradeability_envelopes.jsonl")
    chronological_judgments = []
    for envelope in envelopes:
        embedded = envelope.get("market_judgment")
        if isinstance(embedded, dict) and embedded.get("judgment_id"):
            chronological_judgments.append(embedded)
        else:
            chronological_judgments.append(
                build_market_judgment(envelope).model_dump(mode="json")
            )
    judgments = list(reversed(chronological_judgments))
    existing_queue = read_json(runtime / DELAYED_ENTRY_ARTIFACT)
    delayed_queue = build_delayed_entry_queue(judgments, existing_queue, generated_at=generated_at)
    orders = read_jsonl(runtime / "paper_orders.jsonl")
    router_decisions = read_jsonl(runtime / "qadam_router_v3_decisions.jsonl")
    activity = build_activity_quality(
        orders,
        router_decisions,
        delayed_queue,
        generated_at=generated_at,
    )
    alias_registry = _alias_registry(generated_at)
    field_ownership = _field_ownership(generated_at)
    provider_capabilities = _provider_capabilities(generated_at, runtime)
    priors = trader_prior_records(generated_at)
    envelope_signal_id = str(
        ((envelopes[-1].get("market_judgment") or {}).get("economic_signal_identity_id"))
        if envelopes
        else ""
    )
    current_hypothesis_id = str(
        ((envelopes[-1].get("identity") or {}).get("hypothesis_id"))
        if envelopes
        else ""
    )
    current_generation_id = str(
        ((envelopes[-1].get("generation") or {}).get("decision_generation_id"))
        if envelopes
        else ""
    )
    akber_rows = read_jsonl(runtime / "qadam_akber_filter_v3_results.jsonl")
    shadow_rows = read_jsonl(runtime / "qadam_forward_shadow_decisions.jsonl")
    risk_rows = read_jsonl(runtime / "qadam_position_size_proposals.jsonl")
    router_rows = read_jsonl(runtime / "qadam_router_v3_decisions.jsonl")

    def matching_signal_id(rows: list[dict[str, Any]]) -> str:
        matching = [
            row
            for row in rows
            if str(row.get("hypothesis_id") or row.get("strategy_hypothesis_id") or "")
            == current_hypothesis_id
            and (
                not row.get("decision_generation_id")
                or not current_generation_id
                or str(row.get("decision_generation_id")) == current_generation_id
            )
        ]
        return str(
            (matching[-1].get("economic_signal_identity_id") if matching else "") or ""
        )

    circuit_state = read_json(runtime / "qadam_operator_circuit_breakers.json")
    repair_state = read_json(runtime / "qadam_operator_repair_queue.json")
    operator_health = _operator_health_snapshot(circuit_state, repair_state)
    state = {
        "alias_registry": alias_registry,
        "field_ownership": field_ownership,
        "provider_capabilities": provider_capabilities,
        "trader_priors": priors,
        "judgments": judgments,
        "uncertainty_actions": [
            action
            for judgment in judgments
            for action in judgment.get("missingness_assessment", [])
        ],
        "delayed_queue": delayed_queue,
        "activity": activity,
        "signal_identity_chain": {
            "envelope": envelope_signal_id,
            "akber": matching_signal_id(akber_rows),
            "shadow": matching_signal_id(shadow_rows),
            "risk": matching_signal_id(risk_rows),
            "router": matching_signal_id(router_rows),
        },
        "operator_health": operator_health,
    }
    errors = validate_layered_state(state)
    canary_sessions = _record_canary_session_if_eligible(
        runtime,
        generated_at=generated_at,
        validation_errors=errors,
        activity=activity,
    )
    build_state = _git_build_state()
    distinct_sessions = {
        str(row.get("market_date"))
        for row in canary_sessions
        if row.get("market_date")
        and row.get("exact_build") is True
        and row.get("build_commit") == build_state.get("commit")
    }
    current_build_sessions = [
        row
        for row in canary_sessions
        if row.get("exact_build") is True
        and row.get("build_commit") == build_state.get("commit")
    ]
    canary_eligible_seen = sum(
        int(row.get("eligible_setups_seen") or 0) for row in current_build_sessions
    )
    canary_eligible_submitted = sum(
        int(row.get("eligible_setups_submitted") or 0) for row in current_build_sessions
    )
    canary_capture_rate = (
        round(canary_eligible_submitted / canary_eligible_seen, 6)
        if canary_eligible_seen
        else None
    )
    canary_latencies = [
        float(row.get("median_setup_to_decision_seconds"))
        for row in current_build_sessions
        if row.get("median_setup_to_decision_seconds") is not None
    ]
    canary_median_latency = round(median(canary_latencies), 3) if canary_latencies else None
    canary_duplicate_writes = sum(
        int(row.get("duplicate_or_rejected_writes") or 0) for row in current_build_sessions
    )
    canary_unchanged_reentries = sum(
        int(row.get("unchanged_signal_reentries") or 0) for row in current_build_sessions
    )
    canary_internal_defect_misses = sum(
        int(row.get("eligible_setups_missed_due_to_internal_defects") or 0)
        for row in current_build_sessions
    )
    canary_quality_passed = (
        canary_duplicate_writes == 0
        and canary_unchanged_reentries == 0
        and canary_internal_defect_misses == 0
        and (canary_capture_rate is None or canary_capture_rate >= CANARY_CAPTURE_TARGET)
        and (
            canary_median_latency is None
            or canary_median_latency <= CANARY_MAX_DECISION_LATENCY_SECONDS
        )
    )
    challenger = _build_challenger_attribution(judgments, generated_at=generated_at)
    telegram = _build_telegram_projection(
        judgments,
        read_json(runtime / TELEGRAM_PROJECTION_ARTIFACT),
        generated_at=generated_at,
    )
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_layered_market_judgment_checks",
        "generated_at": generated_at,
        "status": "passed" if not errors else "blocked",
        "implementation_ready": not errors,
        "judgment_count": len(judgments),
        "uncertainty_action_count": len(state["uncertainty_actions"]),
        "delayed_entry_count": delayed_queue.get("record_count", 0),
        "activity_health": activity.get("status"),
        "canary_session_count": len(distinct_sessions),
        "canary_session_target": CANARY_SESSION_TARGET,
        "canary_eligible_setup_count": canary_eligible_seen,
        "canary_submitted_setup_count": canary_eligible_submitted,
        "canary_eligible_opportunity_capture_rate": canary_capture_rate,
        "canary_capture_target": CANARY_CAPTURE_TARGET,
        "canary_median_setup_to_decision_seconds": canary_median_latency,
        "canary_max_decision_latency_seconds": CANARY_MAX_DECISION_LATENCY_SECONDS,
        "canary_duplicate_write_count": canary_duplicate_writes,
        "canary_unchanged_signal_reentry_count": canary_unchanged_reentries,
        "canary_internal_defect_miss_count": canary_internal_defect_misses,
        "canary_quality_passed": canary_quality_passed,
        "observation_ready": (
            not errors
            and len(distinct_sessions) >= CANARY_SESSION_TARGET
            and canary_quality_passed
        ),
        "live_capital_enabled": False,
        "paper_only": True,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "validation_errors": errors,
        "signal_identity_chain": state["signal_identity_chain"],
        "signal_identity_consistent": len(
            {
                value
                for value in state["signal_identity_chain"].values()
                if value
            }
        )
        <= 1,
        "open_circuit_count": operator_health["open_circuit_count"],
        "open_repair_request_count": operator_health["open_repair_request_count"],
        "decision_dependency_open_circuit_count": operator_health[
            "decision_dependency_open_circuit_count"
        ],
        "decision_dependency_open_repair_request_count": operator_health[
            "decision_dependency_open_repair_request_count"
        ],
        "non_blocking_open_circuit_count": operator_health[
            "non_blocking_open_circuit_count"
        ],
        "non_blocking_open_repair_request_count": operator_health[
            "non_blocking_open_repair_request_count"
        ],
        "authority": authority_flags(),
    }
    baseline = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_layered_judgment_baseline",
        "generated_at": generated_at,
        "source_universe_count": 41,
        "trading_universe_count": 19,
        "strategy_family_count": len(STRATEGY_PROFILES),
        "absolute_trade_ceiling_usd": HARD_TRADE_CEILING_USD,
        "current_activity": activity,
        "canonical_decision_transaction": True,
        "parallel_execution_lane_created": False,
        "authority": authority_flags(),
    }
    dashboard = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_layered_market_judgment_dashboard",
        "generated_at": generated_at,
        "status": checks["status"],
        "public_safe": True,
        "activity_health": activity.get("status"),
        "activity": activity,
        "judgment_count": len(judgments),
        "consequence_counts": dict(Counter(row.get("primary_consequence") for row in judgments)),
        "current_judgments": judgments[:12],
        "delayed_entry_count": delayed_queue.get("record_count", 0),
        "delayed_entries": delayed_queue.get("records", [])[:12],
        "challenger_attribution": challenger,
        "trader_prior_count": len(priors),
        "active_trader_prior_count": sum(
            str(row.get("state") or "").lower() in {"active", "approved"}
            for row in priors
        ),
        "telegram_projection": telegram,
        "plain_english_summary": (
            "Qadam now distinguishes hard danger from bounded uncertainty. Optional missing evidence reduces size; execution-only gaps are retried; hard risk failures still stop the setup."
        ),
        "read_only": True,
        "command_disabled": True,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    certification = {
        **checks,
        "artifact_type": "qadam_layered_market_judgment_certification",
        "certification_state": (
            "observation_ready"
            if checks["observation_ready"]
            else "implementation_ready_canary_pending"
            if not errors
            else "blocked"
        ),
        "five_real_market_sessions_cannot_be_backfilled": True,
        "rollout_blockers": unique_errors(
            [
                *errors,
                *(
                    ["five_distinct_real_market_sessions_pending"]
                    if len(distinct_sessions) < CANARY_SESSION_TARGET
                    else []
                ),
                *(
                    ["five_session_canary_quality_target_not_met"]
                    if len(distinct_sessions) >= CANARY_SESSION_TARGET
                    and not canary_quality_passed
                    else []
                ),
            ]
        ),
    }
    state.update(
        {
            "baseline": baseline,
            "dashboard": dashboard,
            "checks": checks,
            "certification": certification,
            "challenger": challenger,
            "telegram": telegram,
        }
    )
    return state


def build_and_write_layered_market_judgment(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    state = build_layered_market_judgment_state(settings)
    store = AtomicArtifactStore(runtime)
    store.write_json(BASELINE_ARTIFACT, state["baseline"])
    store.write_json(ALIAS_REGISTRY_ARTIFACT, state["alias_registry"])
    store.write_json(ACTIVITY_BASELINE_ARTIFACT, state["activity"])
    store.write_json(FIELD_OWNERSHIP_ARTIFACT, state["field_ownership"])
    store.write_json(PROVIDER_CAPABILITIES_ARTIFACT, state["provider_capabilities"])
    store.write_jsonl(TRADER_PRIOR_ARTIFACT, state["trader_priors"])
    store.write_jsonl(JUDGMENTS_ARTIFACT, state["judgments"])
    store.write_jsonl(UNCERTAINTY_ACTIONS_ARTIFACT, state["uncertainty_actions"])
    store.write_json(DELAYED_ENTRY_ARTIFACT, state["delayed_queue"])
    store.write_json(ACTIVITY_HEALTH_ARTIFACT, state["activity"])
    store.write_json(DASHBOARD_ARTIFACT, state["dashboard"])
    store.write_json(CHALLENGER_ATTRIBUTION_ARTIFACT, state["challenger"])
    store.write_json(TELEGRAM_PROJECTION_ARTIFACT, state["telegram"])
    store.write_json(CHECK_ARTIFACT, state["checks"])
    store.write_json(CERTIFICATION_ARTIFACT, state["certification"])
    return state, state["checks"], list(state["checks"]["validation_errors"])


__all__ = [
    "ACTIVITY_HEALTH_ARTIFACT",
    "ALIAS_REGISTRY_ARTIFACT",
    "CERTIFICATION_ARTIFACT",
    "CHECK_ARTIFACT",
    "DASHBOARD_ARTIFACT",
    "DELAYED_ENTRY_ARTIFACT",
    "JUDGMENTS_ARTIFACT",
    "MarketJudgmentEnvelope",
    "UncertaintyAction",
    "UncertaintyActionType",
    "build_activity_quality",
    "build_and_write_layered_market_judgment",
    "build_layered_market_judgment_state",
    "build_market_judgment",
    "canonical_strategy_id",
    "evidence_profile_for_strategy",
    "validate_layered_state",
]
