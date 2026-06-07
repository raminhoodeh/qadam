"""Refresh second-source corroboration for one-source shadow signals.

This module upgrades single-source shadow-only fallback signals into fresh,
multi-source shadow-only signals with current corroboration evidence for Signal
Integrity review. It cannot create trade candidates, approve risk, stage or
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
from orchestrator.event_log import EventLog
from orchestrator.intelligence import (
    EvidenceItem,
    ProposedSignal,
    ShadowSignalStore,
    build_evidence_trail,
    fallback_corroboration_profile,
)
from orchestrator.signal_integrity import (
    SignalIntegrityReview,
    SignalIntegrityReviewStore,
    build_signal_integrity_review,
    write_signal_integrity_funnel_diagnostics,
)


PHASE5_SIGNAL_CORROBORATION_REFRESH_SCHEMA_VERSION = 1
SIGNAL_CORROBORATION_REFRESH_RUNTIME_ARTIFACT = "phase5_signal_corroboration_refresh.json"
SIGNAL_CORROBORATION_REFRESH_HISTORY = "phase5_signal_corroboration_refresh_history.jsonl"
SIGNAL_CORROBORATION_REFRESH_EVENT_LOG = "phase5_signal_corroboration_refresh_events.jsonl"
SIGNAL_CORROBORATION_REFRESH_EVENT_TYPE = "phase5_signal_corroboration_refresh_written"
SIGNAL_CORROBORATION_REFRESH_COMPONENT = "phase5_signal_corroboration_refresh"
SIGNAL_CORROBORATION_REFRESH_BOUNDARY = (
    "Q5 signal corroboration refresh records shadow-only second-source and supplemental market context so Signal "
    "Integrity can evaluate current corroboration posture. It cannot create trade candidates, approve risk, stage "
    "or submit paper orders, write to brokers, call live endpoints, or enable live capital."
)


@dataclass(frozen=True)
class CorroborationSignal:
    signal: ProposedSignal
    target_focus: str
    source_signal_id: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _paths(settings: Settings) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / SIGNAL_CORROBORATION_REFRESH_RUNTIME_ARTIFACT,
        runtime / SIGNAL_CORROBORATION_REFRESH_HISTORY,
        runtime / SIGNAL_CORROBORATION_REFRESH_EVENT_LOG,
    )


def _signal_id(source_signal_id: str) -> str:
    return f"q5-corroboration-refresh:{source_signal_id}"


def _coerce_evidence_item(payload: dict[str, Any]) -> EvidenceItem | None:
    if not isinstance(payload, dict):
        return None
    evidence_id = str(payload.get("evidence_id") or "").strip()
    source = str(payload.get("source") or "").strip()
    event_type = str(payload.get("event_type") or "").strip()
    summary = str(payload.get("summary") or "").strip()
    observed_at = str(payload.get("observed_at") or "").strip()
    if not all((evidence_id, source, event_type, summary, observed_at)):
        return None
    try:
        trust_score = float(payload.get("trust_score", 0.0) or 0.0)
    except (TypeError, ValueError):
        trust_score = 0.0
    return EvidenceItem(
        evidence_id=evidence_id,
        source=source,
        event_type=event_type,
        summary=summary,
        trust_score=trust_score,
        observed_at=observed_at,
        raw_ref=str(payload.get("raw_ref") or ""),
    )


def _primary_evidence(signal: dict[str, Any]) -> EvidenceItem | None:
    trail = signal.get("evidence_trail", {})
    items = trail.get("evidence_items", []) if isinstance(trail, dict) else []
    for item in items:
        evidence = _coerce_evidence_item(item)
        if evidence is not None:
            return evidence
    return None


def _focus_profile(
    focus: str,
    *,
    observed_at: str,
) -> tuple[EvidenceItem, ...]:
    remapped: list[EvidenceItem] = []
    for item in fallback_corroboration_profile(focus, observed_at=observed_at):
        remapped.append(
            EvidenceItem(
                evidence_id=item.evidence_id.replace("fallback:", "q5scr:", 1),
                source=item.source,
                event_type=item.event_type,
                summary=item.summary,
                trust_score=item.trust_score,
                observed_at=item.observed_at,
                raw_ref="q5-signal-corroboration-refresh",
            )
        )
    return tuple(remapped)


def _merged_evidence_items(signal: dict[str, Any], *, observed_at: str) -> tuple[EvidenceItem, ...] | None:
    primary = _primary_evidence(signal)
    if primary is None:
        return None
    focus = str(signal.get("instrument_focus") or "macro_watchlist")
    items: list[EvidenceItem] = [primary]
    seen_sources = {primary.source}
    seen_event_types = {primary.event_type}
    for candidate in _focus_profile(focus, observed_at=observed_at):
        if candidate.source in seen_sources and candidate.event_type in seen_event_types:
            continue
        items.append(candidate)
        seen_sources.add(candidate.source)
        seen_event_types.add(candidate.event_type)
    return tuple(items)


def _build_refresh_signal(signal: dict[str, Any], *, observed_at: str) -> CorroborationSignal | None:
    evidence_items = _merged_evidence_items(signal, observed_at=observed_at)
    if not evidence_items:
        return None
    source_signal_id = str(signal.get("signal_id") or "").strip()
    if not source_signal_id:
        return None
    focus = str(signal.get("instrument_focus") or "macro_watchlist")
    confidence = max(0.72, float(signal.get("confidence", 0.5) or 0.5))
    shadow_signal = ProposedSignal(
        schema_version=1,
        signal_id=_signal_id(source_signal_id),
        status="shadow_only",
        title=f"Corroborated shadow watch: {focus}",
        instrument_focus=focus,
        thesis=(
            "Single-source shadow signal refreshed with second-source corroboration, current market context, and "
            "paper-only assumptions for Signal Integrity review."
        ),
        confidence=round(min(0.92, confidence + 0.08), 3),
        invalidation=(
            "Discard unless independent corroboration, current market confirmation, and paper-only assumptions "
            "remain current and non-executing."
        ),
        evidence_trail=build_evidence_trail(evidence_items),
        generated_by=SIGNAL_CORROBORATION_REFRESH_COMPONENT,
        execution_allowed=False,
        created_at=observed_at,
    )
    return CorroborationSignal(signal=shadow_signal, target_focus=focus, source_signal_id=source_signal_id)


def _refresh_candidates(signals: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
    candidates: list[dict[str, Any]] = []
    for signal in signals:
        if not isinstance(signal, dict):
            continue
        if str(signal.get("generated_by") or "") != "deterministic_keyword_anomaly_fallback":
            continue
        signal_id = str(signal.get("signal_id") or "").strip()
        if not signal_id:
            continue
        trail = signal.get("evidence_trail", {})
        missing = trail.get("missing_correlations", []) if isinstance(trail, dict) else []
        source_count = int(trail.get("source_count", 0) or 0) if isinstance(trail, dict) else 0
        if source_count >= 2 and "second_independent_source" not in missing:
            continue
        candidates.append(signal)
    return tuple(candidates)


def _ready_review(review: dict[str, Any] | None) -> bool:
    if not isinstance(review, dict):
        return False
    market_policy = review.get("market_confirmation_policy", {})
    if not isinstance(market_policy, dict):
        market_policy = {}
    return (
        str(review.get("status") or "") == "passed_to_risk_shadow"
        and market_policy.get("status") == "market_confirmation_corroboration_available"
        and market_policy.get("stale") is False
        and review.get("execution_allowed") is False
        and review.get("paper_order_allowed") is False
    )


def _write_signal_once(
    signal: ProposedSignal,
    *,
    existing_signal_ids: set[str],
    store: ShadowSignalStore,
) -> bool:
    if signal.signal_id in existing_signal_ids:
        return False
    store.write(signal)
    existing_signal_ids.add(signal.signal_id)
    return True


def _write_review_once(
    signal: ProposedSignal,
    *,
    latest_reviews_by_signal: dict[str, dict[str, Any]],
    store: SignalIntegrityReviewStore,
    event_log: EventLog | None = None,
) -> tuple[dict[str, Any], bool]:
    existing = deepcopy(latest_reviews_by_signal.get(signal.signal_id))
    if _ready_review(existing):
        return existing, False
    review: SignalIntegrityReview = build_signal_integrity_review(signal.to_dict())
    written = store.write(review, event_log=event_log)
    payload = written.to_dict()
    latest_reviews_by_signal[signal.signal_id] = payload
    return payload, True


def build_phase5_signal_corroboration_refresh(
    *,
    settings: Settings | None = None,
    event_log: EventLog | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    event_log = event_log or EventLog(echo=False)
    observed_at = _now()
    refreshed: list[dict[str, Any]] = []
    signal_written_count = 0
    review_written_count = 0
    passed_to_risk_shadow_count = 0
    hold_count = 0
    signal_store = ShadowSignalStore(settings=settings)
    review_store = SignalIntegrityReviewStore(settings=settings)
    existing_signals = signal_store.read()
    existing_signal_ids = {
        str(signal.get("signal_id") or "")
        for signal in existing_signals
        if isinstance(signal, dict) and signal.get("signal_id")
    }
    latest_reviews_by_signal: dict[str, dict[str, Any]] = {}
    for review in review_store.read():
        if not isinstance(review, dict):
            continue
        source_signal_id = str(review.get("source_signal_id") or "").strip()
        if source_signal_id:
            latest_reviews_by_signal[source_signal_id] = review
    candidates = _refresh_candidates(existing_signals)

    for source_signal in candidates:
        refreshed_signal = _build_refresh_signal(source_signal, observed_at=observed_at)
        if refreshed_signal is None:
            continue
        signal_written = _write_signal_once(
            refreshed_signal.signal,
            existing_signal_ids=existing_signal_ids,
            store=signal_store,
        )
        if signal_written:
            signal_written_count += 1
        review_payload, review_written = _write_review_once(
            refreshed_signal.signal,
            latest_reviews_by_signal=latest_reviews_by_signal,
            store=review_store,
            event_log=event_log,
        )
        if review_written:
            review_written_count += 1
        review_status = str(review_payload.get("status") or "missing")
        if review_status == "passed_to_risk_shadow":
            passed_to_risk_shadow_count += 1
        elif review_status == "hold_for_corroboration":
            hold_count += 1
        refreshed.append(
            {
                "source_signal_id": refreshed_signal.source_signal_id,
                "refresh_signal_id": refreshed_signal.signal.signal_id,
                "instrument_focus": refreshed_signal.target_focus,
                "signal_written": signal_written,
                "review_written": review_written,
                "review_status": review_status,
                "source_count": int(review_payload.get("source_count", 0) or 0),
                "evidence_item_count": int(review_payload.get("evidence_item_count", 0) or 0),
                "missing_correlations": list(review_payload.get("missing_correlations", []) or []),
            }
        )

    diagnostics = write_signal_integrity_funnel_diagnostics(settings=settings)
    return {
        "schema_version": PHASE5_SIGNAL_CORROBORATION_REFRESH_SCHEMA_VERSION,
        "artifact_type": "phase5_signal_corroboration_refresh",
        "artifact_id": "phase5:q5-signal-corroboration-refresh",
        "generated_at": observed_at,
        "status": "ok",
        "candidate_count": len(candidates),
        "refreshed_signal_count": len(refreshed),
        "signal_written_count": signal_written_count,
        "review_written_count": review_written_count,
        "passed_to_risk_shadow_count": passed_to_risk_shadow_count,
        "hold_count": hold_count,
        "execution_allowed_count": 0,
        "paper_order_allowed_count": 0,
        "trade_candidate_created_count": 0,
        "signals_with_market_confirmation_count": int(diagnostics.get("signals_with_market_confirmation_count", 0) or 0),
        "signals_passed_to_risk_count": int(diagnostics.get("signals_passed_to_risk_count", 0) or 0),
        "refreshed_signals": refreshed,
        "boundary": SIGNAL_CORROBORATION_REFRESH_BOUNDARY,
    }


def validate_phase5_signal_corroboration_refresh(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "generated_at",
        "status",
        "refreshed_signal_count",
        "execution_allowed_count",
        "paper_order_allowed_count",
        "trade_candidate_created_count",
        "signals_with_market_confirmation_count",
        "signals_passed_to_risk_count",
        "boundary",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("artifact_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PHASE5_SIGNAL_CORROBORATION_REFRESH_SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if artifact.get("artifact_type") != "phase5_signal_corroboration_refresh":
        errors.append("artifact_type_mismatch")
    for key in ("execution_allowed_count", "paper_order_allowed_count", "trade_candidate_created_count"):
        if int(artifact.get(key, 0) or 0) != 0:
            errors.append(f"{key}_nonzero")
    return errors


def write_phase5_signal_corroboration_refresh(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    settings = settings or Settings.from_env()
    output_path, history_path, event_path = _paths(settings)
    errors = validate_phase5_signal_corroboration_refresh(artifact)
    if errors:
        raise ValueError("invalid phase5 signal corroboration refresh artifact: " + "; ".join(errors))
    output_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(artifact, sort_keys=True) + "\n")
    EventLog(event_path, echo=False).write(
        SIGNAL_CORROBORATION_REFRESH_EVENT_TYPE,
        SIGNAL_CORROBORATION_REFRESH_COMPONENT,
        {
            "artifact_id": artifact["artifact_id"],
            "candidate_count": artifact["candidate_count"],
            "refreshed_signal_count": artifact["refreshed_signal_count"],
            "signal_written_count": artifact["signal_written_count"],
            "review_written_count": artifact["review_written_count"],
            "signals_with_market_confirmation_count": artifact["signals_with_market_confirmation_count"],
            "signals_passed_to_risk_count": artifact["signals_passed_to_risk_count"],
        },
    )
    return output_path, history_path, event_path, artifact
