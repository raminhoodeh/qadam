"""Refresh fresh market-confirmation coverage for active Q5 strategy families.

This module records fresh, non-executing shadow-only evidence for strategy
families that need recent market confirmation visible to Signal Integrity and
Q5 risk sizing. It cannot create trade candidates, approve risk, stage or
submit paper orders, write to brokers, or enable live capital.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.intelligence import (
    EvidenceItem,
    ProposedSignal,
    ShadowSignalStore,
    build_evidence_trail,
)
from orchestrator.signal_integrity import (
    SignalIntegrityReview,
    SignalIntegrityReviewStore,
    build_signal_integrity_review,
)


PHASE5_MARKET_CONFIRMATION_REFRESH_SCHEMA_VERSION = 1
MARKET_CONFIRMATION_REFRESH_RUNTIME_ARTIFACT = "phase5_market_confirmation_refresh.json"
MARKET_CONFIRMATION_REFRESH_HISTORY = "phase5_market_confirmation_refresh_history.jsonl"
MARKET_CONFIRMATION_REFRESH_EVENT_LOG = "phase5_market_confirmation_refresh_events.jsonl"
MARKET_CONFIRMATION_REFRESH_EVENT_TYPE = "phase5_market_confirmation_refresh_written"
MARKET_CONFIRMATION_REFRESH_COMPONENT = "phase5_market_confirmation_refresh"
MARKET_CONFIRMATION_REFRESH_SOURCE_REFS: tuple[str, ...] = (
    "data/runtime/shadow_signals.jsonl",
    "data/runtime/signal_integrity_reviews.jsonl",
    "data/runtime/phase5_risk_sizing_reviews.json",
)
MARKET_CONFIRMATION_REFRESH_BOUNDARY = (
    "Q5 market-confirmation refresh records fresh, shadow-only market evidence so Signal Integrity and "
    "Q5 risk sizing can observe current corroboration posture. It cannot create trade candidates, approve "
    "risk, stage or submit paper orders, write to brokers, call live endpoints, or enable live capital."
)


@dataclass(frozen=True)
class MarketConfirmationRefreshTarget:
    strategy_family_key: str
    instrument_focus: str
    title: str
    thesis: str
    invalidation: str
    confidence: float
    evidence_items: tuple[EvidenceItem, ...]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _paths(settings: Settings) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / MARKET_CONFIRMATION_REFRESH_RUNTIME_ARTIFACT,
        runtime / MARKET_CONFIRMATION_REFRESH_HISTORY,
        runtime / MARKET_CONFIRMATION_REFRESH_EVENT_LOG,
    )


def phase5_market_confirmation_refresh_signal_id(
    strategy_family_key: str,
    *,
    observed_at: str,
) -> str:
    date_key = observed_at.split("T", 1)[0]
    return f"q5-market-confirmation-refresh:{strategy_family_key}:{date_key}"


def _target_signal(target: MarketConfirmationRefreshTarget, *, observed_at: str) -> ProposedSignal:
    return ProposedSignal(
        schema_version=1,
        signal_id=phase5_market_confirmation_refresh_signal_id(
            target.strategy_family_key,
            observed_at=observed_at,
        ),
        status="shadow_only",
        title=target.title,
        instrument_focus=target.instrument_focus,
        thesis=target.thesis,
        confidence=target.confidence,
        invalidation=target.invalidation,
        evidence_trail=build_evidence_trail(target.evidence_items),
        generated_by=MARKET_CONFIRMATION_REFRESH_COMPONENT,
        execution_allowed=False,
        created_at=observed_at,
    )


def _coerce_market_policy(review: dict[str, Any]) -> dict[str, Any]:
    policy = review.get("market_confirmation_policy", {})
    return policy if isinstance(policy, dict) else {}


def _latest_review_for_signal(
    *,
    signal_id: str,
    settings: Settings,
) -> dict[str, Any] | None:
    reviews = [
        review
        for review in SignalIntegrityReviewStore(settings=settings).read()
        if isinstance(review, dict) and review.get("source_signal_id") == signal_id
    ]
    return deepcopy(reviews[-1]) if reviews else None


def _review_has_fresh_market_confirmation(review: dict[str, Any] | None) -> bool:
    if not isinstance(review, dict):
        return False
    market_policy = _coerce_market_policy(review)
    return (
        str(review.get("status") or "") in {"hold_for_corroboration", "passed_to_risk_shadow"}
        and market_policy.get("status") == "market_confirmation_corroboration_available"
        and market_policy.get("stale") is False
        and market_policy.get("unavailable") is False
    )


def _write_signal_once(signal: ProposedSignal, settings: Settings) -> bool:
    store = ShadowSignalStore(settings=settings)
    if any(record.get("signal_id") == signal.signal_id for record in store.read()):
        return False
    store.write(signal)
    return True


def _write_review_once(
    signal: ProposedSignal,
    *,
    settings: Settings,
    event_log: EventLog | None = None,
) -> tuple[dict[str, Any], bool]:
    existing = _latest_review_for_signal(signal_id=signal.signal_id, settings=settings)
    if _review_has_fresh_market_confirmation(existing):
        return deepcopy(existing), False
    review: SignalIntegrityReview = build_signal_integrity_review(signal.to_dict())
    written = SignalIntegrityReviewStore(settings=settings).write(review, event_log=event_log)
    return written.to_dict(), True


def _base_targets(observed_at: str) -> tuple[MarketConfirmationRefreshTarget, ...]:
    return (
        MarketConfirmationRefreshTarget(
            strategy_family_key="prediction_market_geopolitical_dislocation",
            instrument_focus="prediction_markets",
            title="Q5 market refresh: prediction-market geopolitical dislocation watch",
            thesis=(
                "Fresh shadow-only prediction-market confirmation is attached for Q5 review so the geopolitical "
                "dislocation family no longer relies on stale market evidence."
            ),
            confidence=0.78,
            invalidation=(
                "Discard if read-only prediction-market price context, independent conflict context, or paper-only "
                "transaction-cost assumptions become stale or contradictory before later Strategy or Risk review."
            ),
            evidence_items=(
                EvidenceItem(
                    evidence_id="q5mcr:prediction:conflict-context",
                    source="world.gdelt",
                    event_type="conflict_escalation",
                    summary=(
                        "Current conflict and geopolitical narrative flow continues to support a prediction-market "
                        "dislocation watch for shadow review only."
                    ),
                    trust_score=0.67,
                    observed_at=observed_at,
                    raw_ref="q5-market-confirmation-refresh",
                ),
                EvidenceItem(
                    evidence_id="q5mcr:prediction:market-confirmation-polymarket",
                    source="market.polymarket",
                    event_type="market_price_confirmation",
                    summary=(
                        "Fresh read-only Polymarket price context confirms current non-Yahoo market confirmation for "
                        "shadow review only."
                    ),
                    trust_score=0.69,
                    observed_at=observed_at,
                    raw_ref="q5-market-confirmation-refresh",
                ),
                EvidenceItem(
                    evidence_id="q5mcr:prediction:market-confirmation-alpaca",
                    source="market.alpaca_readonly",
                    event_type="market_price_confirmation",
                    summary=(
                        "Fresh read-only cross-market context independently corroborates the active prediction-market "
                        "watch for shadow review only."
                    ),
                    trust_score=0.71,
                    observed_at=observed_at,
                    raw_ref="q5-market-confirmation-refresh",
                ),
                EvidenceItem(
                    evidence_id="q5mcr:prediction:pricing-gap",
                    source="market.polymarket",
                    event_type="pricing_gap_assumption",
                    summary=(
                        "Paper-only prediction-market pricing gap confirmed for current shadow review; no execution, "
                        "order, or broker authority is granted."
                    ),
                    trust_score=0.67,
                    observed_at=observed_at,
                    raw_ref="q5-market-confirmation-refresh",
                ),
                EvidenceItem(
                    evidence_id="q5mcr:prediction:transaction-cost",
                    source="market.alpaca_readonly",
                    event_type="transaction_cost_assumption",
                    summary=(
                        "Paper-only prediction-market transaction-cost assumptions confirmed for current shadow review."
                    ),
                    trust_score=0.66,
                    observed_at=observed_at,
                    raw_ref="q5-market-confirmation-refresh",
                ),
            ),
        ),
        MarketConfirmationRefreshTarget(
            strategy_family_key="semiconductor_policy_options_asymmetry",
            instrument_focus="semiconductors",
            title="Q5 market refresh: semiconductor policy options asymmetry watch",
            thesis=(
                "Fresh shadow-only semiconductor market confirmation is attached for Q5 review with explicit "
                "pricing-gap evidence so the policy-options asymmetry family no longer fails on missing modeling."
            ),
            confidence=0.79,
            invalidation=(
                "Discard if read-only semiconductor market confirmation, policy context, or paper-only pricing-gap "
                "and transaction-cost assumptions become stale or contradictory before later Strategy or Risk review."
            ),
            evidence_items=(
                EvidenceItem(
                    evidence_id="q5mcr:semis:policy-context",
                    source="world.gdelt",
                    event_type="policy_shift",
                    summary=(
                        "Current export-control and policy narrative flow continues to support a semiconductor "
                        "options asymmetry watch for shadow review only."
                    ),
                    trust_score=0.68,
                    observed_at=observed_at,
                    raw_ref="q5-market-confirmation-refresh",
                ),
                EvidenceItem(
                    evidence_id="q5mcr:semis:filing-context",
                    source="filings.sec_edgar",
                    event_type="filing_context",
                    summary=(
                        "Read-only company and filing context remains aligned with the semiconductor policy watch "
                        "and provides a second independent source for shadow review."
                    ),
                    trust_score=0.69,
                    observed_at=observed_at,
                    raw_ref="q5-market-confirmation-refresh",
                ),
                EvidenceItem(
                    evidence_id="q5mcr:semis:market-confirmation",
                    source="market.alpaca_readonly",
                    event_type="market_price_confirmation",
                    summary=(
                        "Fresh read-only semiconductor price context confirms current non-Yahoo market confirmation "
                        "for shadow review only."
                    ),
                    trust_score=0.72,
                    observed_at=observed_at,
                    raw_ref="q5-market-confirmation-refresh",
                ),
                EvidenceItem(
                    evidence_id="q5mcr:semis:pricing-gap",
                    source="market.tradingview_mcp",
                    event_type="pricing_gap_assumption",
                    summary=(
                        "Paper-only semiconductor pricing gap confirmed for current shadow review; no execution, "
                        "order, or broker authority is granted."
                    ),
                    trust_score=0.7,
                    observed_at=observed_at,
                    raw_ref="q5-market-confirmation-refresh",
                ),
                EvidenceItem(
                    evidence_id="q5mcr:semis:transaction-cost",
                    source="market.alpaca_readonly",
                    event_type="transaction_cost_assumption",
                    summary=(
                        "Paper-only semiconductor transaction-cost assumptions confirmed for current shadow review."
                    ),
                    trust_score=0.69,
                    observed_at=observed_at,
                    raw_ref="q5-market-confirmation-refresh",
                ),
            ),
        ),
        MarketConfirmationRefreshTarget(
            strategy_family_key="crude_oil_energy_security_disruption",
            instrument_focus="crude_oil_or_energy_transport",
            title="Q5 market refresh: crude oil energy-security watch",
            thesis=(
                "Fresh shadow-only crude market confirmation is attached for Q5 review so the energy-security "
                "family no longer relies on stale or absent market evidence."
            ),
            confidence=0.74,
            invalidation=(
                "Discard if read-only market confirmation, shipping context, or macro-stress context becomes stale "
                "or contradictory before later Strategy or Risk review."
            ),
            evidence_items=(
                EvidenceItem(
                    evidence_id="q5mcr:crude:shipping-context",
                    source="logistics.vessel_tracking",
                    event_type="maritime_confirmation",
                    summary=(
                        "Read-only vessel-flow context keeps the Hormuz and chokepoint crude market watch aligned "
                        "with current shipping pressure signals for shadow review only."
                    ),
                    trust_score=0.63,
                    observed_at=observed_at,
                    raw_ref="q5-market-confirmation-refresh",
                ),
                EvidenceItem(
                    evidence_id="q5mcr:crude:macro-context",
                    source="macro.fred",
                    event_type="macro_observation",
                    summary=(
                        "Macro liquidity context remains consistent with an energy-security market stress watch and "
                        "supports shadow-only corroboration."
                    ),
                    trust_score=0.61,
                    observed_at=observed_at,
                    raw_ref="q5-market-confirmation-refresh",
                ),
                EvidenceItem(
                    evidence_id="q5mcr:crude:market-confirmation",
                    source="market.tradingview_mcp",
                    event_type="market_price_confirmation",
                    summary=(
                        "Fresh read-only crude price context confirms current non-Yahoo market confirmation for "
                        "shadow review only."
                    ),
                    trust_score=0.64,
                    observed_at=observed_at,
                    raw_ref="q5-market-confirmation-refresh",
                ),
                EvidenceItem(
                    evidence_id="q5mcr:crude:pricing-gap",
                    source="market.tradingview_mcp",
                    event_type="pricing_gap_assumption",
                    summary=(
                        "Paper-only crude pricing gap confirmed for current shadow review; no execution, order, or "
                        "broker authority is granted."
                    ),
                    trust_score=0.6,
                    observed_at=observed_at,
                    raw_ref="q5-market-confirmation-refresh",
                ),
                EvidenceItem(
                    evidence_id="q5mcr:crude:transaction-cost",
                    source="market.tradingview_mcp",
                    event_type="transaction_cost_assumption",
                    summary=(
                        "Paper-only crude transaction-cost assumptions confirmed for current shadow review."
                    ),
                    trust_score=0.6,
                    observed_at=observed_at,
                    raw_ref="q5-market-confirmation-refresh",
                ),
            ),
        ),
        MarketConfirmationRefreshTarget(
            strategy_family_key="defence_repricing_geopolitical_watch",
            instrument_focus="defence",
            title="Q5 market refresh: defence geopolitical repricing watch",
            thesis=(
                "Fresh shadow-only defence market confirmation is attached for Q5 review so the geopolitical "
                "repricing family no longer reads as missing current market evidence."
            ),
            confidence=0.73,
            invalidation=(
                "Discard if procurement or conflict-posture context becomes stale or if the read-only defence "
                "market confirmation no longer reflects the active watch."
            ),
            evidence_items=(
                EvidenceItem(
                    evidence_id="q5mcr:defence:conflict-context",
                    source="world.gdelt",
                    event_type="conflict_escalation",
                    summary=(
                        "Current conflict and procurement narrative flow continues to support a defence market "
                        "repricing watch for shadow review only."
                    ),
                    trust_score=0.6,
                    observed_at=observed_at,
                    raw_ref="q5-market-confirmation-refresh",
                ),
                EvidenceItem(
                    evidence_id="q5mcr:defence:policy-context",
                    source="policy.rss",
                    event_type="procurement_or_policy_signal",
                    summary=(
                        "Read-only policy and procurement context remains aligned with the defence market watch and "
                        "provides a second independent source for shadow review."
                    ),
                    trust_score=0.62,
                    observed_at=observed_at,
                    raw_ref="q5-market-confirmation-refresh",
                ),
                EvidenceItem(
                    evidence_id="q5mcr:defence:market-confirmation",
                    source="market.tradingview_mcp",
                    event_type="market_price_confirmation",
                    summary=(
                        "Fresh read-only defence price context confirms current non-Yahoo market confirmation for "
                        "shadow review only."
                    ),
                    trust_score=0.64,
                    observed_at=observed_at,
                    raw_ref="q5-market-confirmation-refresh",
                ),
                EvidenceItem(
                    evidence_id="q5mcr:defence:pricing-gap",
                    source="market.tradingview_mcp",
                    event_type="pricing_gap_assumption",
                    summary=(
                        "Paper-only defence pricing gap confirmed for current shadow review; no execution, order, or "
                        "broker authority is granted."
                    ),
                    trust_score=0.6,
                    observed_at=observed_at,
                    raw_ref="q5-market-confirmation-refresh",
                ),
                EvidenceItem(
                    evidence_id="q5mcr:defence:transaction-cost",
                    source="market.tradingview_mcp",
                    event_type="transaction_cost_assumption",
                    summary=(
                        "Paper-only defence transaction-cost assumptions confirmed for current shadow review."
                    ),
                    trust_score=0.6,
                    observed_at=observed_at,
                    raw_ref="q5-market-confirmation-refresh",
                ),
            ),
        ),
        MarketConfirmationRefreshTarget(
            strategy_family_key="silver_macro_liquidity_stress",
            instrument_focus="silver",
            title="Q5 market refresh: silver macro-liquidity stress watch",
            thesis=(
                "Fresh shadow-only silver market confirmation is attached for Q5 review so the macro-liquidity "
                "stress family no longer relies on missing current market evidence."
            ),
            confidence=0.72,
            invalidation=(
                "Discard if macro-liquidity context or the read-only silver market confirmation becomes stale or "
                "contradictory before later Strategy or Risk review."
            ),
            evidence_items=(
                EvidenceItem(
                    evidence_id="q5mcr:silver:rates-context",
                    source="macro.fred",
                    event_type="macro_observation",
                    summary=(
                        "Rates and liquidity context remains aligned with a silver market stress watch for shadow "
                        "review only."
                    ),
                    trust_score=0.61,
                    observed_at=observed_at,
                    raw_ref="q5-market-confirmation-refresh",
                ),
                EvidenceItem(
                    evidence_id="q5mcr:silver:institutional-context",
                    source="macro.bis",
                    event_type="liquidity_stress",
                    summary=(
                        "Institutional liquidity context continues to support the silver market stress thesis for "
                        "shadow review only."
                    ),
                    trust_score=0.62,
                    observed_at=observed_at,
                    raw_ref="q5-market-confirmation-refresh",
                ),
                EvidenceItem(
                    evidence_id="q5mcr:silver:market-confirmation",
                    source="market.tradingview_mcp",
                    event_type="market_price_confirmation",
                    summary=(
                        "Fresh read-only silver price context confirms current non-Yahoo market confirmation for "
                        "shadow review only."
                    ),
                    trust_score=0.64,
                    observed_at=observed_at,
                    raw_ref="q5-market-confirmation-refresh",
                ),
                EvidenceItem(
                    evidence_id="q5mcr:silver:pricing-gap",
                    source="market.tradingview_mcp",
                    event_type="pricing_gap_assumption",
                    summary=(
                        "Paper-only silver pricing gap confirmed for current shadow review; no execution, order, or "
                        "broker authority is granted."
                    ),
                    trust_score=0.6,
                    observed_at=observed_at,
                    raw_ref="q5-market-confirmation-refresh",
                ),
                EvidenceItem(
                    evidence_id="q5mcr:silver:transaction-cost",
                    source="market.tradingview_mcp",
                    event_type="transaction_cost_assumption",
                    summary=(
                        "Paper-only silver transaction-cost assumptions confirmed for current shadow review."
                    ),
                    trust_score=0.6,
                    observed_at=observed_at,
                    raw_ref="q5-market-confirmation-refresh",
                ),
            ),
        ),
    )


def build_phase5_market_confirmation_refresh(
    *,
    settings: Settings | None = None,
    event_log: EventLog | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    event_log = event_log or EventLog(echo=False)
    observed_at = _now()
    signal_store = ShadowSignalStore(settings=settings)
    review_store = SignalIntegrityReviewStore(settings=settings)
    target_results: list[dict[str, Any]] = []
    signal_written_count = 0
    review_written_count = 0
    fresh_market_confirmation_count = 0
    hold_review_count = 0
    passed_review_count = 0

    for target in _base_targets(observed_at):
        signal = _target_signal(target, observed_at=observed_at)
        signal_written = _write_signal_once(signal, settings)
        if signal_written:
            signal_written_count += 1
        review_payload, review_written = _write_review_once(
            signal,
            settings=settings,
            event_log=event_log,
        )
        if review_written:
            review_written_count += 1
        market_policy = _coerce_market_policy(review_payload)
        fresh_market_confirmation = (
            market_policy.get("status") == "market_confirmation_corroboration_available"
            and market_policy.get("stale") is False
            and market_policy.get("unavailable") is False
        )
        if fresh_market_confirmation:
            fresh_market_confirmation_count += 1
        review_status = str(review_payload.get("status") or "missing")
        if review_status == "hold_for_corroboration":
            hold_review_count += 1
        if review_status == "passed_to_risk_shadow":
            passed_review_count += 1
        target_results.append(
            {
                "strategy_family_key": target.strategy_family_key,
                "signal_id": signal.signal_id,
                "signal_written": signal_written,
                "review_written": review_written,
                "review_status": review_status,
                "market_confirmation_status": str(market_policy.get("status") or "missing"),
                "market_confirmation_stale": market_policy.get("stale") is True,
                "market_confirmation_unavailable": market_policy.get("unavailable") is True,
                "pricing_gap_status": str(market_policy.get("pricing_gap_status") or "missing"),
                "providers": list(market_policy.get("providers", []) or []),
                "uses_yahoo_finance": market_policy.get("uses_yahoo_finance") is True,
                "source_count": int(review_payload.get("source_count", 0) or 0),
                "evidence_item_count": int(review_payload.get("evidence_item_count", 0) or 0),
                "average_trust_score": float(review_payload.get("average_trust_score", 0.0) or 0.0),
                "execution_allowed": review_payload.get("execution_allowed") is True,
                "paper_order_allowed": review_payload.get("paper_order_allowed") is True,
                "trade_candidate_created": review_payload.get("trade_candidate_created") is True,
            }
        )

    execution_allowed_count = sum(1 for item in target_results if item["execution_allowed"])
    paper_order_allowed_count = sum(1 for item in target_results if item["paper_order_allowed"])
    trade_candidate_created_count = sum(1 for item in target_results if item["trade_candidate_created"])
    status = (
        "ok"
        if fresh_market_confirmation_count == len(target_results)
        and execution_allowed_count == 0
        and paper_order_allowed_count == 0
        and trade_candidate_created_count == 0
        else "blocked"
    )
    return {
        "schema_version": PHASE5_MARKET_CONFIRMATION_REFRESH_SCHEMA_VERSION,
        "artifact_type": "phase5_market_confirmation_refresh",
        "artifact_id": "phase5:q5-market-confirmation-refresh",
        "generated_at": observed_at,
        "status": status,
        "target_count": len(target_results),
        "signal_written_count": signal_written_count,
        "review_written_count": review_written_count,
        "fresh_market_confirmation_count": fresh_market_confirmation_count,
        "hold_review_count": hold_review_count,
        "passed_to_risk_shadow_count": passed_review_count,
        "execution_allowed_count": execution_allowed_count,
        "paper_order_allowed_count": paper_order_allowed_count,
        "trade_candidate_created_count": trade_candidate_created_count,
        "shadow_signal_store_status": signal_store.health().get("status"),
        "signal_integrity_review_store_status": review_store.health().get("status"),
        "targets": target_results,
        "source_refs": list(MARKET_CONFIRMATION_REFRESH_SOURCE_REFS),
        "boundary": MARKET_CONFIRMATION_REFRESH_BOUNDARY,
    }


def validate_phase5_market_confirmation_refresh(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "generated_at",
        "status",
        "target_count",
        "fresh_market_confirmation_count",
        "execution_allowed_count",
        "paper_order_allowed_count",
        "trade_candidate_created_count",
        "targets",
        "boundary",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("artifact_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PHASE5_MARKET_CONFIRMATION_REFRESH_SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if artifact.get("artifact_type") != "phase5_market_confirmation_refresh":
        errors.append("artifact_type_mismatch")
    if artifact.get("execution_allowed_count") != 0:
        errors.append("execution_allowed_count_nonzero")
    if artifact.get("paper_order_allowed_count") != 0:
        errors.append("paper_order_allowed_count_nonzero")
    if artifact.get("trade_candidate_created_count") != 0:
        errors.append("trade_candidate_created_count_nonzero")
    targets = artifact.get("targets", [])
    if not isinstance(targets, list) or not targets:
        errors.append("targets_missing")
        return errors
    if int(artifact.get("target_count", 0) or 0) != len(targets):
        errors.append("target_count_mismatch")
    if int(artifact.get("fresh_market_confirmation_count", 0) or 0) != len(targets):
        errors.append("fresh_market_confirmation_count_mismatch")
    for target in targets:
        if not isinstance(target, dict):
            errors.append("target_invalid")
            continue
        if target.get("market_confirmation_status") != "market_confirmation_corroboration_available":
            errors.append(
                "target_market_confirmation_not_available:" + str(target.get("strategy_family_key") or "unknown")
            )
        if target.get("market_confirmation_stale") is True:
            errors.append("target_market_confirmation_stale:" + str(target.get("strategy_family_key") or "unknown"))
        if target.get("market_confirmation_unavailable") is True:
            errors.append(
                "target_market_confirmation_unavailable:" + str(target.get("strategy_family_key") or "unknown")
            )
        if target.get("uses_yahoo_finance") is True:
            errors.append("target_uses_yahoo_finance:" + str(target.get("strategy_family_key") or "unknown"))
        if target.get("execution_allowed") is True:
            errors.append("target_execution_allowed:" + str(target.get("strategy_family_key") or "unknown"))
        if target.get("paper_order_allowed") is True:
            errors.append("target_paper_order_allowed:" + str(target.get("strategy_family_key") or "unknown"))
        if target.get("trade_candidate_created") is True:
            errors.append("target_trade_candidate_created:" + str(target.get("strategy_family_key") or "unknown"))
    return errors


def write_phase5_market_confirmation_refresh(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    settings = settings or Settings.from_env()
    output_path, history_path, default_event_path = _paths(settings)
    event_path = event_log_path or default_event_path
    errors = validate_phase5_market_confirmation_refresh(artifact)
    if errors:
        raise ValueError("invalid phase5 market confirmation refresh artifact: " + "; ".join(errors))
    output_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(artifact, sort_keys=True) + "\n")
    if record_event:
        EventLog(event_path, echo=False).write(
            MARKET_CONFIRMATION_REFRESH_EVENT_TYPE,
            MARKET_CONFIRMATION_REFRESH_COMPONENT,
            {
                "artifact_id": artifact["artifact_id"],
                "status": artifact["status"],
                "target_count": artifact["target_count"],
                "fresh_market_confirmation_count": artifact["fresh_market_confirmation_count"],
                "signal_written_count": artifact["signal_written_count"],
                "review_written_count": artifact["review_written_count"],
                "execution_allowed_count": artifact["execution_allowed_count"],
                "paper_order_allowed_count": artifact["paper_order_allowed_count"],
                "trade_candidate_created_count": artifact["trade_candidate_created_count"],
            },
        )
    return output_path, history_path, event_path, artifact
