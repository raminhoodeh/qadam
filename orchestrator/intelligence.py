"""Phase 2 shadow intelligence contracts.

This layer is intentionally non-executing. It can assemble evidence trails and
shadow-only proposed signals, but it cannot route risk decisions or trades.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean
from typing import Any
from uuid import uuid4

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.secrets import secret_value

EVIDENCE_TRAIL_SCHEMA_VERSION = 1
PROPOSED_SIGNAL_SCHEMA_VERSION = 1

KEYWORD_WEIGHTS: dict[str, float] = {
    "oil": 0.22,
    "crude": 0.22,
    "hormuz": 0.30,
    "suez": 0.28,
    "red sea": 0.28,
    "shipping": 0.20,
    "thermal": 0.18,
    "anomaly": 0.18,
    "conflict": 0.22,
    "missile": 0.24,
    "semiconductor": 0.24,
    "chip": 0.20,
    "defence": 0.18,
    "defense": 0.18,
    "silver": 0.16,
    "prediction": 0.14,
    "kalshi": 0.14,
    "polymarket": 0.14,
}


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    source: str
    event_type: str
    summary: str
    trust_score: float
    observed_at: str
    raw_ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceTrail:
    schema_version: int
    trail_id: str
    evidence_items: tuple[EvidenceItem, ...]
    source_count: int
    min_trust_score: float
    average_trust_score: float
    missing_correlations: tuple[str, ...]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["evidence_items"] = [item.to_dict() for item in self.evidence_items]
        payload["missing_correlations"] = list(self.missing_correlations)
        return payload


@dataclass(frozen=True)
class ProposedSignal:
    schema_version: int
    signal_id: str
    status: str
    title: str
    instrument_focus: str
    thesis: str
    confidence: float
    invalidation: str
    evidence_trail: EvidenceTrail
    generated_by: str
    execution_allowed: bool
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["evidence_trail"] = self.evidence_trail.to_dict()
        return payload


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def provider_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    gemini_configured = bool(secret_value("GEMINI_API_KEY", settings) or secret_value("GOOGLE_API_KEY", settings))
    local_provider = secret_value("LOCAL_LLM_PROVIDER", settings) or "lm_studio"
    lm_studio_base_url = secret_value("LM_STUDIO_BASE_URL", settings) or "http://127.0.0.1:1234/v1"
    lm_studio_model = secret_value("LM_STUDIO_MODEL", settings) or ""
    lm_studio_configured = local_provider == "lm_studio" and bool(lm_studio_base_url and lm_studio_model)
    return {
        "status": "ok" if gemini_configured and lm_studio_configured else "degraded",
        "frontier_llm": {
            "provider": "gemini",
            "credential_configured": gemini_configured,
            "mode": "configured_not_called" if gemini_configured else "missing_key",
            "boundary": "No Gemini calls are made by Phase 2 status checks.",
        },
        "local_llm": {
            "provider": local_provider,
            "model": lm_studio_model or "missing",
            "base_url_configured": bool(lm_studio_base_url),
            "mode": "configured_not_called" if lm_studio_configured else "missing_config",
            "boundary": "LM Studio is not called until the user starts it and approves a local model check.",
        },
    }


def _keyword_strength(text: str) -> float:
    lowered = text.lower()
    return min(1.0, sum(weight for keyword, weight in KEYWORD_WEIGHTS.items() if keyword in lowered))


def _instrument_focus(text: str) -> str:
    lowered = text.lower()
    if any(term in lowered for term in ("oil", "crude", "hormuz", "suez", "red sea", "shipping")):
        return "crude_oil_or_energy_transport"
    if any(term in lowered for term in ("semiconductor", "chip", "taiwan", "export control")):
        return "semiconductors"
    if any(term in lowered for term in ("defence", "defense", "missile", "conflict")):
        return "defence"
    if "silver" in lowered:
        return "silver"
    if any(term in lowered for term in ("kalshi", "polymarket", "prediction")):
        return "prediction_markets"
    return "macro_watchlist"


def build_evidence_trail(evidence_items: tuple[EvidenceItem, ...]) -> EvidenceTrail:
    trust_scores = [item.trust_score for item in evidence_items] or [0.0]
    sources = {item.source for item in evidence_items}
    missing_correlations: list[str] = []
    source_text = " ".join(item.source for item in evidence_items)
    summary_text = " ".join(item.summary.lower() for item in evidence_items)
    if "nasa_firms" in source_text and "shipping" not in summary_text:
        missing_correlations.append("maritime_confirmation")
    if "gdelt" in source_text and "market" not in summary_text:
        missing_correlations.append("market_price_confirmation")
    if len(sources) < 2:
        missing_correlations.append("second_independent_source")
    return EvidenceTrail(
        schema_version=EVIDENCE_TRAIL_SCHEMA_VERSION,
        trail_id=str(uuid4()),
        evidence_items=evidence_items,
        source_count=len(sources),
        min_trust_score=round(min(trust_scores), 3),
        average_trust_score=round(fmean(trust_scores), 3),
        missing_correlations=tuple(missing_correlations),
        created_at=_now(),
    )


def deterministic_shadow_triage(evidence_items: tuple[EvidenceItem, ...]) -> tuple[ProposedSignal, ...]:
    signals: list[ProposedSignal] = []
    for item in evidence_items:
        keyword_strength = _keyword_strength(item.summary)
        confidence = round(min(0.99, item.trust_score * 0.65 + keyword_strength * 0.35), 3)
        if confidence < 0.42:
            continue
        trail = build_evidence_trail((item,))
        focus = _instrument_focus(item.summary)
        signals.append(
            ProposedSignal(
                schema_version=PROPOSED_SIGNAL_SCHEMA_VERSION,
                signal_id=str(uuid4()),
                status="shadow_only",
                title=f"Shadow watch: {focus}",
                instrument_focus=focus,
                thesis=f"Deterministic triage flagged this observation for review: {item.summary[:180]}",
                confidence=confidence,
                invalidation="Discard unless corroborated by an independent source and transaction-cost assumptions.",
                evidence_trail=trail,
                generated_by="deterministic_keyword_anomaly_fallback",
                execution_allowed=False,
                created_at=_now(),
            )
        )
    return tuple(signals)


def sample_evidence_items() -> tuple[EvidenceItem, ...]:
    now = _now()
    return (
        EvidenceItem(
            evidence_id="sample:nasa_firms:hormuz_thermal",
            source="physical.nasa_firms",
            event_type="physical_anomaly",
            summary="High-confidence thermal anomaly near the Strait of Hormuz energy corridor.",
            trust_score=0.88,
            observed_at=now,
            raw_ref="sample",
        ),
        EvidenceItem(
            evidence_id="sample:gdelt:chip_controls",
            source="conflict.gdelt",
            event_type="conflict_event",
            summary="Chip export controls become focus of renewed US China negotiations.",
            trust_score=0.65,
            observed_at=now,
            raw_ref="sample",
        ),
        EvidenceItem(
            evidence_id="sample:fred:macro",
            source="macro.fred",
            event_type="macro_observation",
            summary="Rates and crude context require macro review before any signal is promoted.",
            trust_score=0.78,
            observed_at=now,
            raw_ref="sample",
        ),
    )


class ShadowSignalStore:
    def __init__(self, path: str | Path | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.path = Path(path or Path(self.settings.runtime_dir) / "shadow_signals.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, signal: ProposedSignal) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(signal.to_dict(), sort_keys=True) + "\n")

    def read(self) -> tuple[dict[str, Any], ...]:
        if not self.path.exists():
            return ()
        signals: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    signals.append(json.loads(stripped))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid shadow signal line {line_number} in {self.path}") from exc
        return tuple(signals)

    def health(self) -> dict[str, Any]:
        try:
            signals = self.read()
        except Exception as exc:  # noqa: BLE001 - health should report failure
            return {"status": "degraded", "path": str(self.path), "error": str(exc)}
        return {
            "status": "ok",
            "path": str(self.path),
            "schema_version": PROPOSED_SIGNAL_SCHEMA_VERSION,
            "signal_count": len(signals),
            "execution_allowed_count": sum(1 for signal in signals if signal.get("execution_allowed") is True),
        }


def run_shadow_intelligence_sample(
    *,
    store: ShadowSignalStore | None = None,
    event_log: EventLog | None = None,
) -> dict[str, Any]:
    store = store or ShadowSignalStore()
    event_log = event_log or EventLog(echo=False)
    evidence = sample_evidence_items()
    signals = deterministic_shadow_triage(evidence)
    for signal in signals:
        store.write(signal)
        event_log.write(
            "shadow_signal_recorded",
            "intelligence",
            {
                "signal_id": signal.signal_id,
                "status": signal.status,
                "instrument_focus": signal.instrument_focus,
                "confidence": signal.confidence,
                "execution_allowed": signal.execution_allowed,
            },
        )
    return {
        "status": "ok",
        "schema_version": PROPOSED_SIGNAL_SCHEMA_VERSION,
        "evidence_count": len(evidence),
        "shadow_signal_count": len(signals),
        "execution_allowed_count": sum(1 for signal in signals if signal.execution_allowed),
        "provider_status": provider_status(),
        "store": store.health(),
        "event_log": event_log.health(),
        "boundary": "Shadow signals are non-executable and cannot reach broker or risk routing.",
    }


def shadow_intelligence_summary(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    store = ShadowSignalStore(settings=settings)
    providers = provider_status(settings)
    return {
        "status": "shadow_ready" if providers["status"] in {"ok", "degraded"} else "degraded",
        "schema_version": PROPOSED_SIGNAL_SCHEMA_VERSION,
        "store": store.health(),
        "provider_status": providers,
        "boundary": "Phase 2 shadow intelligence can propose review packets only; execution remains impossible.",
    }
