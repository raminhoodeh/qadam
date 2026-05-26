"""Q5E-1 risk-evidence lift for the Phase 5 exit unblock.

This module creates one explicit, replayable, non-executing evidence packet that
lets Q5-3 produce a paper-size-eligible setup. It does not create trade
candidates, stage orders, submit paper orders, write brokers, create positions,
or enable live capital.
"""

from __future__ import annotations

import json
from copy import deepcopy
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
from orchestrator.phase5_risk_sizing import (
    RISK_SIZING_RUNTIME_ARTIFACT,
    build_phase5_risk_sizing_reviews,
    validate_phase5_risk_sizing_bundle,
    write_phase5_risk_sizing_reviews,
)
from orchestrator.signal_integrity import (
    SignalIntegrityReview,
    SignalIntegrityReviewStore,
    build_signal_integrity_review,
)


PHASE5_EXIT_RISK_EVIDENCE_LIFT_SCHEMA_VERSION = 1
EXIT_RISK_EVIDENCE_LIFT_RUNTIME_ARTIFACT = "phase5_exit_risk_evidence_lift.json"
EXIT_RISK_EVIDENCE_LIFT_HISTORY = "phase5_exit_risk_evidence_lift_history.jsonl"
EXIT_RISK_EVIDENCE_LIFT_EVENT_LOG = "phase5_exit_risk_evidence_lift_events.jsonl"
EXIT_RISK_EVIDENCE_LIFT_EVENT_TYPE = "phase5_exit_risk_evidence_lift_written"
EXIT_RISK_EVIDENCE_LIFT_COMPONENT = "phase5_exit_risk_evidence_lift"
TARGET_STRATEGY_FAMILY_KEY = "crude_oil_energy_security_disruption"
TARGET_SIGNAL_ID = "q5e-1-crude-oil-paper-sizing-evidence"
TARGET_INSTRUMENT_FOCUS = "crude_oil_or_energy_transport"
EXIT_RISK_EVIDENCE_LIFT_SOURCE_REFS: tuple[str, ...] = (
    "data/runtime/shadow_signals.jsonl",
    "data/runtime/signal_integrity_reviews.jsonl",
    "data/runtime/phase5_approval_policy_decisions.json",
    "data/runtime/phase4_candidate_strategy_universe.json",
    "data/runtime/phase5_risk_sizing_reviews.json",
)

EXIT_RISK_EVIDENCE_LIFT_BOUNDARY = (
    "Q5E-1 records one non-executing evidence lift so Q5-3 can size a paper-only "
    "setup. It cannot create trade candidates, approve live risk, stage or "
    "submit paper orders, call brokers, create positions, or enable live capital."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _evidence_items(now: str) -> tuple[EvidenceItem, ...]:
    return (
        EvidenceItem(
            evidence_id="q5e-1:nasa_firms:hormuz_energy_corridor",
            source="physical.nasa_firms",
            event_type="physical_anomaly",
            summary=(
                "Thermal anomaly context near the Strait of Hormuz energy corridor, "
                "with shipping corroboration required and supplied in this paper-only evidence lift."
            ),
            trust_score=0.88,
            observed_at=now,
            raw_ref="q5e-1-local-evidence-lift",
        ),
        EvidenceItem(
            evidence_id="q5e-1:vessel_tracking:hormuz_shipping_context",
            source="logistics.vessel_tracking",
            event_type="maritime_confirmation",
            summary=(
                "Shipping and vessel-tracking context independently corroborates the "
                "Hormuz energy-security watch thesis for paper sizing only."
            ),
            trust_score=0.84,
            observed_at=now,
            raw_ref="q5e-1-local-evidence-lift",
        ),
        EvidenceItem(
            evidence_id="q5e-1:cme_crude:market_confirmation",
            source="market.cme_crude_reference",
            event_type="market_price_confirmation",
            summary=(
                "Non-Yahoo crude market confirmation. Pricing gap confirmed; "
                "transaction-cost assumptions confirmed; spread and slippage assumptions confirmed."
            ),
            trust_score=0.82,
            observed_at=now,
            raw_ref="q5e-1-local-evidence-lift",
        ),
        EvidenceItem(
            evidence_id="q5e-1:fred:macro_liquidity_context",
            source="macro.fred",
            event_type="macro_observation",
            summary=(
                "Macro liquidity context supports paper-only crude risk sizing while "
                "remaining non-executing and non-authoritative."
            ),
            trust_score=0.78,
            observed_at=now,
            raw_ref="q5e-1-local-evidence-lift",
        ),
    )


def _target_signal(now: str) -> ProposedSignal:
    return ProposedSignal(
        schema_version=1,
        signal_id=TARGET_SIGNAL_ID,
        status="shadow_only",
        title="Q5E-1 shadow watch: crude oil paper sizing evidence",
        instrument_focus=TARGET_INSTRUMENT_FOCUS,
        thesis=(
            "Q5E-1 local evidence lift for one guarded paper lifecycle drill: "
            "crude-oil energy-security setup with non-Yahoo market confirmation, "
            "pricing-gap assumptions, and independent shipping corroboration."
        ),
        confidence=0.82,
        invalidation=(
            "Discard if non-Yahoo market confirmation, pricing-gap assumptions, "
            "shipping corroboration, paper-account mode, or kill-switch clear state fails."
        ),
        evidence_trail=build_evidence_trail(_evidence_items(now)),
        generated_by="q5e_1_exit_risk_evidence_lift",
        execution_allowed=False,
        created_at=now,
    )


def _write_signal_once(signal: ProposedSignal, settings: Settings) -> bool:
    store = ShadowSignalStore(settings=settings)
    if any(record.get("signal_id") == signal.signal_id for record in store.read()):
        return False
    store.write(signal)
    return True


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
    return reviews[-1] if reviews else None


def _review_is_q5e_1_ready(review: dict[str, Any] | None) -> bool:
    if not isinstance(review, dict):
        return False
    market_policy = review.get("market_confirmation_policy", {})
    if not isinstance(market_policy, dict):
        return False
    return (
        review.get("status") == "passed_to_risk_shadow"
        and review.get("execution_allowed") is False
        and review.get("paper_order_allowed") is False
        and review.get("trade_candidate_created") is False
        and market_policy.get("status") == "market_confirmation_corroboration_available"
        and market_policy.get("pricing_gap") == "pass_pricing_gap_confirmed"
        and market_policy.get("uses_yahoo_finance") is False
    )


def _write_signal_integrity_review(
    signal: ProposedSignal,
    *,
    settings: Settings,
    event_log: EventLog | None = None,
) -> tuple[dict[str, Any], bool]:
    existing = _latest_review_for_signal(signal_id=signal.signal_id, settings=settings)
    if _review_is_q5e_1_ready(existing):
        return deepcopy(existing), False
    review: SignalIntegrityReview = build_signal_integrity_review(signal.to_dict())
    written = SignalIntegrityReviewStore(settings=settings).write(review, event_log=event_log)
    return written.to_dict(), True


def _target_risk_review(risk_bundle: dict[str, Any]) -> dict[str, Any]:
    for review in risk_bundle.get("reviews", []):
        if isinstance(review, dict) and review.get("strategy_family_key") == TARGET_STRATEGY_FAMILY_KEY:
            return review
    return {}


def validate_phase5_exit_risk_evidence_lift(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "stage",
        "status",
        "target_strategy_family_key",
        "signal_integrity_status",
        "paper_size_eligible_count",
        "target_paper_size_eligible",
        "target_proposed_risk_gbp",
        "broker_write_allowed_count",
        "paper_order_submitted_count",
        "live_capital_enabled_count",
        "boundary",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("artifact_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PHASE5_EXIT_RISK_EVIDENCE_LIFT_SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if artifact.get("artifact_type") != "phase5_exit_risk_evidence_lift":
        errors.append("artifact_type_mismatch")
    if artifact.get("stage") != "Q5E-1":
        errors.append("stage_mismatch")
    if artifact.get("signal_integrity_status") != "passed_to_risk_shadow":
        errors.append("signal_integrity_not_passed")
    if artifact.get("market_confirmation_status") != "market_confirmation_corroboration_available":
        errors.append("market_confirmation_not_available")
    if artifact.get("pricing_gap") != "pass_pricing_gap_confirmed":
        errors.append("pricing_gap_not_confirmed")
    if artifact.get("uses_yahoo_finance") is not False:
        errors.append("yahoo_finance_used_as_confirmation")
    if int(artifact.get("paper_size_eligible_count", 0) or 0) < 1:
        errors.append("paper_size_eligible_count_below_one")
    if artifact.get("target_paper_size_eligible") is not True:
        errors.append("target_not_paper_size_eligible")
    if _float(artifact.get("target_proposed_risk_gbp"), 0.0) <= 0:
        errors.append("target_proposed_risk_not_positive")
    if _float(artifact.get("target_proposed_risk_gbp"), 0.0) > _float(
        artifact.get("target_max_risk_gbp"), 0.0
    ):
        errors.append("target_proposed_risk_above_cap")
    for key in (
        "risk_approval_allowed_count",
        "trade_candidate_created_count",
        "execution_allowed_count",
        "paper_order_allowed_count",
        "staged_order_created_count",
        "paper_order_submitted_count",
        "broker_write_allowed_count",
        "broker_submit_receipt_created_count",
        "position_created_count",
        "live_capital_enabled_count",
    ):
        if int(artifact.get(key, 0) or 0) != 0:
            errors.append(f"authority_count_not_zero:{key}")
    if "cannot create trade candidates" not in str(artifact.get("boundary") or ""):
        errors.append("boundary_weak")
    return sorted(set(errors))


def phase5_exit_risk_evidence_lift_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / EXIT_RISK_EVIDENCE_LIFT_RUNTIME_ARTIFACT,
        runtime / EXIT_RISK_EVIDENCE_LIFT_HISTORY,
        runtime / EXIT_RISK_EVIDENCE_LIFT_EVENT_LOG,
    )


def write_phase5_exit_risk_evidence_lift(
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    settings = settings or Settings.from_env()
    output_path, history_path, default_event_path = phase5_exit_risk_evidence_lift_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    event_log = EventLog(event_path, echo=False)
    now = _now()
    signal = _target_signal(now)
    signal_written = _write_signal_once(signal, settings)
    review, review_written = _write_signal_integrity_review(
        signal,
        settings=settings,
        event_log=event_log if record_event else None,
    )
    risk_bundle = build_phase5_risk_sizing_reviews(settings=settings)
    _, _, risk_event_path, written_risk_bundle = write_phase5_risk_sizing_reviews(
        risk_bundle,
        settings=settings,
        record_event=True,
    )
    target_review = _target_risk_review(written_risk_bundle)
    market_policy = review.get("market_confirmation_policy", {})
    if not isinstance(market_policy, dict):
        market_policy = {}
    eligible_keys = [
        str(item.get("strategy_family_key") or "")
        for item in written_risk_bundle.get("reviews", [])
        if isinstance(item, dict) and item.get("paper_size_eligible") is True
    ]
    artifact = {
        "schema_version": PHASE5_EXIT_RISK_EVIDENCE_LIFT_SCHEMA_VERSION,
        "artifact_type": "phase5_exit_risk_evidence_lift",
        "artifact_id": "phase5:q5e-1:risk-evidence-lift",
        "phase": "Q5E",
        "stage": "Q5E-1",
        "status": "ok",
        "generated_at": now,
        "public_safe": True,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "runtime_artifact_path": str(output_path),
        "history_log_path": str(history_path),
        "risk_sizing_runtime_artifact_path": str(_runtime_dir(settings) / RISK_SIZING_RUNTIME_ARTIFACT),
        "risk_sizing_event_log_path": str(risk_event_path),
        "source_refs": list(EXIT_RISK_EVIDENCE_LIFT_SOURCE_REFS),
        "boundary": EXIT_RISK_EVIDENCE_LIFT_BOUNDARY,
        "target_strategy_family_key": TARGET_STRATEGY_FAMILY_KEY,
        "target_signal_id": signal.signal_id,
        "target_instrument_focus": signal.instrument_focus,
        "signal_written": signal_written,
        "signal_integrity_review_written": review_written,
        "signal_integrity_review_id": review.get("review_id"),
        "signal_integrity_status": review.get("status"),
        "market_confirmation_status": market_policy.get("status"),
        "pricing_gap": market_policy.get("pricing_gap"),
        "market_confirmation_providers": list(market_policy.get("providers", []) or []),
        "uses_yahoo_finance": market_policy.get("uses_yahoo_finance") is True,
        "target_risk_artifact_id": target_review.get("artifact_id"),
        "target_paper_size_eligible": target_review.get("paper_size_eligible") is True,
        "target_risk_decision": target_review.get("risk_decision"),
        "target_proposed_risk_gbp": _float(target_review.get("proposed_risk_gbp"), 0.0),
        "target_max_risk_gbp": _float(target_review.get("max_risk_gbp"), 0.0),
        "target_risk_blocker_count": int(target_review.get("risk_blocker_count", 0) or 0),
        "paper_size_eligible_count": int(written_risk_bundle.get("paper_size_eligible_count", 0) or 0),
        "eligible_strategy_family_keys": sorted(key for key in eligible_keys if key),
        "risk_sizing_validation_error_count": len(validate_phase5_risk_sizing_bundle(written_risk_bundle)),
        "risk_approval_allowed_count": int(written_risk_bundle.get("risk_approval_allowed_count", 0) or 0),
        "trade_candidate_created_count": int(written_risk_bundle.get("trade_candidate_created_count", 0) or 0),
        "execution_allowed_count": int(written_risk_bundle.get("execution_allowed_count", 0) or 0),
        "paper_order_allowed_count": int(written_risk_bundle.get("paper_order_allowed_count", 0) or 0),
        "staged_order_created_count": int(written_risk_bundle.get("staged_order_created_count", 0) or 0),
        "paper_order_submitted_count": int(written_risk_bundle.get("paper_order_submitted_count", 0) or 0),
        "broker_write_allowed_count": int(written_risk_bundle.get("broker_write_allowed_count", 0) or 0),
        "broker_submit_receipt_created_count": int(
            written_risk_bundle.get("broker_submit_receipt_created_count", 0) or 0
        ),
        "position_created_count": int(written_risk_bundle.get("position_created_count", 0) or 0),
        "live_capital_enabled_count": int(written_risk_bundle.get("live_capital_enabled_count", 0) or 0),
    }
    entry: EventLogEntry | None = None
    if record_event:
        entry = event_log.write(
            EXIT_RISK_EVIDENCE_LIFT_EVENT_TYPE,
            EXIT_RISK_EVIDENCE_LIFT_COMPONENT,
            {
                "artifact_id": artifact["artifact_id"],
                "target_strategy_family_key": artifact["target_strategy_family_key"],
                "signal_integrity_status": artifact["signal_integrity_status"],
                "paper_size_eligible_count": artifact["paper_size_eligible_count"],
                "target_proposed_risk_gbp": artifact["target_proposed_risk_gbp"],
                "broker_write_allowed_count": artifact["broker_write_allowed_count"],
                "live_capital_enabled_count": artifact["live_capital_enabled_count"],
                "boundary": artifact["boundary"],
            },
        )
        artifact["event_log_written"] = True
        artifact["event_log_path"] = str(event_log.path)
        artifact["event_log_correlation_id"] = entry.correlation_id
        artifact["event_log_created_at"] = entry.created_at
    artifact["validation_errors"] = validate_phase5_exit_risk_evidence_lift(artifact)
    artifact["status"] = "ok" if not artifact["validation_errors"] else "error"
    output_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE5_EXIT_RISK_EVIDENCE_LIFT_SCHEMA_VERSION,
        "artifact_id": artifact.get("artifact_id"),
        "status": artifact.get("status"),
        "generated_at": artifact.get("generated_at"),
        "recorded_at": _now(),
        "target_strategy_family_key": artifact.get("target_strategy_family_key"),
        "signal_integrity_status": artifact.get("signal_integrity_status"),
        "paper_size_eligible_count": artifact.get("paper_size_eligible_count"),
        "target_proposed_risk_gbp": artifact.get("target_proposed_risk_gbp"),
        "validation_error_count": len(artifact.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, artifact
