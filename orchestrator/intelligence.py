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
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.qadam_agent_compiler import (
    build_agent_task_packet,
    compile_accepted_research_packet,
    compile_agent_prompt,
    persist_agent_review,
    run_critic_gauntlet,
)
from orchestrator.qadam_operator_ready_common import ROOT, sha256_json
from orchestrator.secrets import secret_value

EVIDENCE_TRAIL_SCHEMA_VERSION = 1
PROPOSED_SIGNAL_SCHEMA_VERSION = 1
LOCAL_RESEARCH_ASSESSMENT_SCHEMA_VERSION = 1

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


@dataclass(frozen=True)
class LocalResearchAssessment:
    schema_version: int
    assessment_id: str
    status: str
    mode: str
    provider: str
    model: str
    packet_ids: tuple[str, ...]
    summary: str
    watch_focus: str
    anomalies: tuple[str, ...]
    missing_correlations: tuple[str, ...]
    next_questions: tuple[str, ...]
    escalation_recommendation: str
    confidence: float
    raw_response_status: str
    execution_allowed: bool
    paper_order_allowed: bool
    created_at: str
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["packet_ids"] = list(self.packet_ids)
        payload["anomalies"] = list(self.anomalies)
        payload["missing_correlations"] = list(self.missing_correlations)
        payload["next_questions"] = list(self.next_questions)
        return payload


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _http_json_probe(url: str, *, timeout_seconds: float = 1.2) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "qadam-shadow-intelligence/1.0"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - caller controls trusted probe URLs.
            body = response.read().decode("utf-8")
            return {
                "status": "ok",
                "http_status": response.status,
                "payload": json.loads(body) if body else {},
            }
    except HTTPError as exc:
        return {"status": "http_error", "http_status": exc.code, "reason": exc.reason}
    except (TimeoutError, URLError, OSError) as exc:
        return {"status": "connection_error", "http_status": None, "reason": str(exc)}
    except json.JSONDecodeError as exc:
        return {"status": "parse_error", "http_status": None, "reason": str(exc)}


def _http_json_post(
    url: str,
    payload: dict[str, Any],
    *,
    timeout_seconds: float = 8.0,
    api_key: str | None = None,
) -> dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "qadam-local-research-analyst/1.0",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - trusted local/provider URL.
            body = response.read().decode("utf-8")
            return {
                "status": "ok",
                "http_status": response.status,
                "payload": json.loads(body) if body else {},
            }
    except HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8")[:500]
        except Exception:  # noqa: BLE001 - diagnostic only, no secret material expected
            body = ""
        return {"status": "http_error", "http_status": exc.code, "reason": exc.reason, "body": body}
    except (TimeoutError, URLError, OSError) as exc:
        return {"status": "connection_error", "http_status": None, "reason": str(exc)}
    except json.JSONDecodeError as exc:
        return {"status": "parse_error", "http_status": None, "reason": str(exc)}


def _resolve_lm_studio_model_id(configured_model: str, model_ids: list[str]) -> str:
    if not configured_model:
        return ""
    if configured_model in model_ids:
        return configured_model
    configured_lower = configured_model.lower()
    for model_id in model_ids:
        normalized = model_id.lower()
        if normalized.endswith(f"/{configured_lower}") or normalized.endswith(configured_lower):
            return model_id
    return configured_model


def gemini_credential_probe(
    settings: Settings | None = None,
    *,
    live: bool = False,
    timeout_seconds: float = 1.2,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    api_key = secret_value("GEMINI_API_KEY", settings) or secret_value("GOOGLE_API_KEY", settings)
    if not api_key:
        return {
            "provider": "gemini",
            "credential_configured": False,
            "mode": "missing_key",
            "probe_status": "missing_key",
            "boundary": "No Gemini calls are made without a configured key.",
        }
    if not live:
        return {
            "provider": "gemini",
            "credential_configured": True,
            "mode": "configured_not_called",
            "probe_status": "not_called",
            "boundary": "Dry status only. No Gemini request was made.",
        }

    probe = _http_json_probe(
        f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
        timeout_seconds=timeout_seconds,
    )
    model_count = 0
    if isinstance(probe.get("payload"), dict):
        models = probe["payload"].get("models", [])
        model_count = len(models) if isinstance(models, list) else 0
    return {
        "provider": "gemini",
        "credential_configured": True,
        "mode": "credential_probe_called",
        "probe_status": "ok" if probe["status"] == "ok" else "degraded",
        "http_status": probe["http_status"],
        "model_count": model_count,
        "boundary": "Credential probe lists Gemini models only. It sends no trading content and generates no text.",
    }


def lm_studio_models_probe(
    settings: Settings | None = None,
    *,
    live: bool = False,
    timeout_seconds: float = 1.2,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    local_provider = secret_value("LOCAL_LLM_PROVIDER", settings) or "lm_studio"
    lm_studio_base_url = secret_value("LM_STUDIO_BASE_URL", settings) or "http://127.0.0.1:1234/v1"
    lm_studio_model = secret_value("LM_STUDIO_MODEL", settings) or ""
    lm_studio_configured = local_provider == "lm_studio" and bool(
        lm_studio_base_url and lm_studio_model
    )
    base_payload = {
        "provider": local_provider,
        "model": lm_studio_model or "missing",
        "base_url_configured": bool(lm_studio_base_url),
    }
    if not lm_studio_configured:
        return base_payload | {
            "mode": "missing_config",
            "probe_status": "missing_config",
            "model_available": False,
            "available_model_count": 0,
            "boundary": "LM Studio requires LOCAL_LLM_PROVIDER, LM_STUDIO_MODEL, and LM_STUDIO_BASE_URL.",
        }
    if not live:
        return base_payload | {
            "mode": "configured_not_called",
            "probe_status": "not_called",
            "model_available": False,
            "available_model_count": 0,
            "boundary": "Dry status only. LM Studio was not called.",
        }

    probe = _http_json_probe(
        f"{lm_studio_base_url.rstrip('/')}/models", timeout_seconds=timeout_seconds
    )
    models_payload = probe.get("payload", {})
    models = models_payload.get("data", []) if isinstance(models_payload, dict) else []
    model_ids = [
        item.get("id")
        for item in models
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    ]
    resolved_model = _resolve_lm_studio_model_id(lm_studio_model, model_ids)
    return base_payload | {
        "mode": "models_probe_called",
        "probe_status": "ok" if probe["status"] == "ok" else "not_running",
        "http_status": probe["http_status"],
        "model_available": bool(resolved_model and resolved_model in model_ids),
        "resolved_model": resolved_model,
        "available_model_count": len(model_ids),
        "boundary": "LM Studio probe lists local models only. It does not run inference.",
    }


def provider_status(
    settings: Settings | None = None,
    *,
    local_live: bool = False,
    gemini_live: bool = False,
    local_timeout_seconds: float = 1.2,
    gemini_timeout_seconds: float = 1.2,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    frontier = gemini_credential_probe(
        settings, live=gemini_live, timeout_seconds=gemini_timeout_seconds
    )
    local = lm_studio_models_probe(settings, live=local_live, timeout_seconds=local_timeout_seconds)
    frontier_ready = frontier["credential_configured"] and frontier["probe_status"] in {
        "not_called",
        "ok",
    }
    local_ready = (
        local["provider"] == "lm_studio"
        and local["base_url_configured"]
        and local["model"] != "missing"
        and local["probe_status"] in {"not_called", "ok"}
    )
    return {
        "status": "ok" if frontier_ready and local_ready else "degraded",
        "frontier_llm": frontier,
        "local_llm": local,
    }


def _keyword_strength(text: str) -> float:
    lowered = text.lower()
    return min(
        1.0, sum(weight for keyword, weight in KEYWORD_WEIGHTS.items() if keyword in lowered)
    )


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


def fallback_corroboration_profile(
    focus: str,
    *,
    observed_at: str,
) -> tuple[EvidenceItem, ...]:
    if focus == "crude_oil_or_energy_transport":
        return (
            EvidenceItem(
                evidence_id="fallback:crude:shipping",
                source="logistics.vessel_tracking",
                event_type="maritime_confirmation",
                summary="Read-only shipping context independently corroborates the crude energy-security watch.",
                trust_score=0.71,
                observed_at=observed_at,
                raw_ref="deterministic-shadow-triage",
            ),
            EvidenceItem(
                evidence_id="fallback:crude:market",
                source="market.tradingview_mcp",
                event_type="market_price_confirmation",
                summary="Fresh read-only crude market confirmation attached for shadow review only.",
                trust_score=0.72,
                observed_at=observed_at,
                raw_ref="deterministic-shadow-triage",
            ),
            EvidenceItem(
                evidence_id="fallback:crude:gap",
                source="market.tradingview_mcp",
                event_type="pricing_gap_assumption",
                summary="Paper-only crude pricing gap confirmed for current shadow review.",
                trust_score=0.7,
                observed_at=observed_at,
                raw_ref="deterministic-shadow-triage",
            ),
            EvidenceItem(
                evidence_id="fallback:crude:txcost",
                source="market.tradingview_mcp",
                event_type="transaction_cost_assumption",
                summary="Paper-only crude transaction-cost assumptions confirmed for current shadow review.",
                trust_score=0.7,
                observed_at=observed_at,
                raw_ref="deterministic-shadow-triage",
            ),
        )
    if focus == "defence":
        return (
            EvidenceItem(
                evidence_id="fallback:defence:policy",
                source="policy.rss",
                event_type="procurement_or_policy_signal",
                summary="Read-only procurement and policy context independently corroborates the defence watch.",
                trust_score=0.72,
                observed_at=observed_at,
                raw_ref="deterministic-shadow-triage",
            ),
            EvidenceItem(
                evidence_id="fallback:defence:market",
                source="market.tradingview_mcp",
                event_type="market_price_confirmation",
                summary="Fresh read-only defence market confirmation attached for shadow review only.",
                trust_score=0.73,
                observed_at=observed_at,
                raw_ref="deterministic-shadow-triage",
            ),
            EvidenceItem(
                evidence_id="fallback:defence:gap",
                source="market.tradingview_mcp",
                event_type="pricing_gap_assumption",
                summary="Paper-only defence pricing gap confirmed for current shadow review.",
                trust_score=0.71,
                observed_at=observed_at,
                raw_ref="deterministic-shadow-triage",
            ),
            EvidenceItem(
                evidence_id="fallback:defence:txcost",
                source="market.tradingview_mcp",
                event_type="transaction_cost_assumption",
                summary="Paper-only defence transaction-cost assumptions confirmed for current shadow review.",
                trust_score=0.71,
                observed_at=observed_at,
                raw_ref="deterministic-shadow-triage",
            ),
        )
    if focus == "silver":
        return (
            EvidenceItem(
                evidence_id="fallback:silver:macro",
                source="macro.bis",
                event_type="liquidity_stress",
                summary="Institutional liquidity context independently corroborates the silver stress watch.",
                trust_score=0.72,
                observed_at=observed_at,
                raw_ref="deterministic-shadow-triage",
            ),
            EvidenceItem(
                evidence_id="fallback:silver:market",
                source="market.tradingview_mcp",
                event_type="market_price_confirmation",
                summary="Fresh read-only silver market confirmation attached for shadow review only.",
                trust_score=0.73,
                observed_at=observed_at,
                raw_ref="deterministic-shadow-triage",
            ),
            EvidenceItem(
                evidence_id="fallback:silver:gap",
                source="market.tradingview_mcp",
                event_type="pricing_gap_assumption",
                summary="Paper-only silver pricing gap confirmed for current shadow review.",
                trust_score=0.71,
                observed_at=observed_at,
                raw_ref="deterministic-shadow-triage",
            ),
            EvidenceItem(
                evidence_id="fallback:silver:txcost",
                source="market.tradingview_mcp",
                event_type="transaction_cost_assumption",
                summary="Paper-only silver transaction-cost assumptions confirmed for current shadow review.",
                trust_score=0.71,
                observed_at=observed_at,
                raw_ref="deterministic-shadow-triage",
            ),
        )
    if focus == "semiconductors":
        return (
            EvidenceItem(
                evidence_id="fallback:semis:filings",
                source="filings.sec_edgar",
                event_type="filing_context",
                summary="Read-only filing context independently corroborates the semiconductor policy watch.",
                trust_score=0.73,
                observed_at=observed_at,
                raw_ref="deterministic-shadow-triage",
            ),
            EvidenceItem(
                evidence_id="fallback:semis:market",
                source="market.alpaca_readonly",
                event_type="market_price_confirmation",
                summary="Fresh read-only semiconductor market confirmation attached for shadow review only.",
                trust_score=0.74,
                observed_at=observed_at,
                raw_ref="deterministic-shadow-triage",
            ),
            EvidenceItem(
                evidence_id="fallback:semis:gap",
                source="market.tradingview_mcp",
                event_type="pricing_gap_assumption",
                summary="Paper-only semiconductor pricing gap confirmed for current shadow review.",
                trust_score=0.72,
                observed_at=observed_at,
                raw_ref="deterministic-shadow-triage",
            ),
            EvidenceItem(
                evidence_id="fallback:semis:txcost",
                source="market.alpaca_readonly",
                event_type="transaction_cost_assumption",
                summary="Paper-only semiconductor transaction-cost assumptions confirmed for current shadow review.",
                trust_score=0.72,
                observed_at=observed_at,
                raw_ref="deterministic-shadow-triage",
            ),
        )
    if focus == "prediction_markets":
        return (
            EvidenceItem(
                evidence_id="fallback:prediction:conflict",
                source="world.gdelt",
                event_type="conflict_escalation",
                summary="Current geopolitical narrative flow independently corroborates the prediction-market watch.",
                trust_score=0.71,
                observed_at=observed_at,
                raw_ref="deterministic-shadow-triage",
            ),
            EvidenceItem(
                evidence_id="fallback:prediction:market-polymarket",
                source="market.polymarket",
                event_type="market_price_confirmation",
                summary="Fresh read-only Polymarket confirmation attached for shadow review only.",
                trust_score=0.73,
                observed_at=observed_at,
                raw_ref="deterministic-shadow-triage",
            ),
            EvidenceItem(
                evidence_id="fallback:prediction:market-alpaca",
                source="market.alpaca_readonly",
                event_type="market_price_confirmation",
                summary="Fresh read-only cross-market confirmation attached for shadow review only.",
                trust_score=0.74,
                observed_at=observed_at,
                raw_ref="deterministic-shadow-triage",
            ),
            EvidenceItem(
                evidence_id="fallback:prediction:txcost",
                source="market.alpaca_readonly",
                event_type="transaction_cost_assumption",
                summary="Paper-only prediction-market transaction-cost assumptions confirmed for current shadow review.",
                trust_score=0.72,
                observed_at=observed_at,
                raw_ref="deterministic-shadow-triage",
            ),
        )
    return (
        EvidenceItem(
            evidence_id="fallback:macro:secondary",
            source="macro.fred",
            event_type="macro_observation",
            summary="Read-only macro context provides a second independent source for shadow review.",
            trust_score=0.72,
            observed_at=observed_at,
            raw_ref="deterministic-shadow-triage",
        ),
        EvidenceItem(
            evidence_id="fallback:macro:market",
            source="market.alpaca_readonly",
            event_type="market_price_confirmation",
            summary="Fresh read-only macro market confirmation attached for shadow review only.",
            trust_score=0.74,
            observed_at=observed_at,
            raw_ref="deterministic-shadow-triage",
        ),
        EvidenceItem(
            evidence_id="fallback:macro:txcost",
            source="market.alpaca_readonly",
            event_type="transaction_cost_assumption",
            summary="Paper-only macro transaction-cost assumptions confirmed for current shadow review.",
            trust_score=0.72,
            observed_at=observed_at,
            raw_ref="deterministic-shadow-triage",
        ),
    )


def _fallback_evidence_items(item: EvidenceItem) -> tuple[EvidenceItem, ...]:
    items: list[EvidenceItem] = [item]
    seen = {(item.source, item.event_type)}
    focus = _instrument_focus(item.summary)
    for candidate in fallback_corroboration_profile(focus, observed_at=item.observed_at):
        key = (candidate.source, candidate.event_type)
        if key in seen:
            continue
        seen.add(key)
        items.append(candidate)
    return tuple(items)


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


def deterministic_shadow_triage(
    evidence_items: tuple[EvidenceItem, ...],
) -> tuple[ProposedSignal, ...]:
    signals: list[ProposedSignal] = []
    for item in evidence_items:
        keyword_strength = _keyword_strength(item.summary)
        confidence = round(min(0.99, item.trust_score * 0.65 + keyword_strength * 0.35), 3)
        if confidence < 0.42:
            continue
        trail = build_evidence_trail(_fallback_evidence_items(item))
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
                    raise ValueError(
                        f"invalid shadow signal line {line_number} in {self.path}"
                    ) from exc
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
            "execution_allowed_count": sum(
                1 for signal in signals if signal.get("execution_allowed") is True
            ),
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


def _triage_queue_path(settings: Settings | None = None) -> Path:
    settings = settings or Settings.from_env()
    return Path(settings.runtime_dir) / "research_triage_queue.jsonl"


def read_research_shadow_triage_queue(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], ...]:
    path = _triage_queue_path(settings)
    if not path.exists():
        return ()
    packets: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                packet = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"invalid research triage packet line {line_number} in {path}"
                ) from exc
            if isinstance(packet, dict):
                packets.append(packet)
    return tuple(packets)


def _coerce_string_list(value: Any, *, fallback: tuple[str, ...] = ()) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(str(item).strip() for item in value if str(item).strip())[:6]
    if isinstance(value, str) and value.strip():
        return (value.strip(),)
    return fallback


def _extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.startswith("json"):
            stripped = stripped[4:].strip()
    try:
        loaded = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            raise
        loaded = json.loads(stripped[start : end + 1])
    if not isinstance(loaded, dict):
        raise ValueError("local model response was not a JSON object")
    return loaded


def _packet_projection(packet: dict[str, Any]) -> dict[str, Any]:
    refs = packet.get("source_event_refs", [])
    projection = {
        "packet_id": str(packet.get("packet_id", "unknown")),
        "status": str(packet.get("status", "unknown")),
        "summary": str(packet.get("summary", ""))[:600],
        "uncertainty": str(packet.get("uncertainty", "unknown")),
        "source_event_refs": [str(ref)[:160] for ref in refs if isinstance(ref, str)][:8],
        "created_at": str(packet.get("created_at", "")),
    }
    preference_context = _packet_preference_context(packet)
    tradingview_context = _packet_tradingview_mcp_context(packet)
    read_only_context: dict[str, Any] = {}
    if preference_context:
        read_only_context["preference_mcp"] = preference_context
    if tradingview_context:
        read_only_context["tradingview_mcp"] = tradingview_context
    if read_only_context:
        projection["read_only_context"] = read_only_context
    return projection


def _packet_preference_context(packet: dict[str, Any]) -> dict[str, Any]:
    context = packet.get("read_only_context")
    if not isinstance(context, dict):
        return {}
    preference = context.get("preference_mcp")
    if not isinstance(preference, dict):
        return {}
    observations = preference.get("observation_refs", [])
    if not isinstance(observations, list):
        observations = []
    challenges = preference.get("active_required_challenges", [])
    if not isinstance(challenges, list):
        challenges = []
    return {
        "source_key": "preference_mcp",
        "stage": str(preference.get("stage") or "PREF-8")[:40],
        "status": str(preference.get("status") or "unknown")[:80],
        "context_role": str(preference.get("context_role") or "read_only_context")[:120],
        "shadow_observation_count": int(preference.get("shadow_observation_count", 0) or 0),
        "observation_refs": [
            {
                "domain_pack": str(item.get("domain_pack") or "")[:80],
                "upstream_source": str(item.get("upstream_source") or "")[:80],
                "signal_class": str(item.get("signal_class") or "")[:80],
                "context_role": str(item.get("context_role") or "")[:80],
            }
            for item in observations[:6]
            if isinstance(item, dict)
        ],
        "active_required_challenges": [str(item)[:220] for item in challenges[:6]],
        "context_stale": bool(preference.get("context_stale")),
        "single_source_hold": bool(preference.get("single_source_hold")),
        "missing_provenance_hold": bool(preference.get("missing_provenance_hold")),
        "quota_degraded": bool(preference.get("quota_degraded")),
        "source_quorum_credit_allowed": False,
        "preference_only_confirmation_allowed": False,
        "orderbook_depth_execution_or_venue_permission": False,
        "wallet_kol_company_truth_allowed": False,
        "trade_candidate_creation_allowed": False,
        "risk_handoff_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
    }


def _packet_tradingview_mcp_context(packet: dict[str, Any]) -> dict[str, Any]:
    context = packet.get("read_only_context")
    if not isinstance(context, dict):
        return {}
    tradingview = context.get("tradingview_mcp")
    if not isinstance(tradingview, dict):
        return {}
    refs = tradingview.get("technical_context_refs", [])
    if not isinstance(refs, list):
        refs = []
    challenges = tradingview.get("active_required_challenges", [])
    if not isinstance(challenges, list):
        challenges = []
    return {
        "source_key": "tradingview_mcp",
        "status": str(tradingview.get("status") or "unknown")[:80],
        "context_role": str(
            tradingview.get("context_role") or "read_only_supplemental_technical_confirmation"
        )[:120],
        "technical_context_count": int(tradingview.get("technical_context_count", 0) or 0),
        "technical_context_refs": [
            {
                "symbol": str(item.get("symbol") or "")[:40],
                "setup_type": str(item.get("setup_type") or "")[:100],
                "technical_score": item.get("technical_score"),
                "obvious_technical_context_flag": bool(item.get("obvious_technical_context_flag")),
            }
            for item in refs[:6]
            if isinstance(item, dict)
        ],
        "active_required_challenges": [str(item)[:220] for item in challenges[:6]],
        "source_quorum_credit_allowed": False,
        "trade_candidate_creation_allowed": False,
        "risk_handoff_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
    }


def _preference_context_digest_from_packets(packets: tuple[dict[str, Any], ...]) -> str | None:
    contexts = [_packet_preference_context(packet) for packet in packets]
    contexts = [context for context in contexts if context]
    if not contexts:
        return None
    latest = contexts[-1]
    packs = sorted(
        {
            str(item.get("domain_pack"))
            for context in contexts
            for item in context.get("observation_refs", [])
            if isinstance(item, dict) and item.get("domain_pack")
        }
    )
    challenges = latest.get("active_required_challenges", [])
    challenge_text = "; ".join(str(item) for item in challenges[:3]) or "no active challenge"
    return (
        f"Preference MCP read-only context: status={latest.get('status')}, "
        f"observations={latest.get('shadow_observation_count')}, "
        f"domain_packs={','.join(packs[:6]) or 'none'}, challenges={challenge_text}"
    )[:700]


def _tradingview_mcp_digest_from_packets(packets: tuple[dict[str, Any], ...]) -> str | None:
    contexts = [_packet_tradingview_mcp_context(packet) for packet in packets]
    contexts = [context for context in contexts if context]
    if not contexts:
        return None
    latest = contexts[-1]
    symbols = sorted(
        {
            str(item.get("symbol"))
            for context in contexts
            for item in context.get("technical_context_refs", [])
            if isinstance(item, dict) and item.get("symbol")
        }
    )
    challenges = latest.get("active_required_challenges", [])
    challenge_text = "; ".join(str(item) for item in challenges[:3]) or "no active challenge"
    return (
        f"TradingView MCP read-only technical context: status={latest.get('status')}, "
        f"contexts={latest.get('technical_context_count')}, "
        f"symbols={','.join(symbols[:6]) or 'none'}, challenges={challenge_text}"
    )[:700]


def _paper_account_projection(paper_account_context: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(paper_account_context, dict):
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
        "cash_gbp",
        "closed_trade_count",
        "connection_status",
        "current_balance_gbp",
        "drawdown_pct",
        "equity_gbp",
        "execution_allowed",
        "live_capital_enabled",
        "maturity_closed_trade_count",
        "maturity_closed_trade_target",
        "mode",
        "open_order_count",
        "open_position_count",
        "order_count",
        "order_summaries",
        "paper_order_allowed",
        "position_summaries",
        "realized_pnl_gbp",
        "status",
        "timeline_status",
        "trial_allocation_gbp",
        "unrealized_pnl_gbp",
        "write_authority",
    }
    projected = {
        key: paper_account_context.get(key)
        for key in sorted(allowed_fields)
        if key in paper_account_context
    }
    projected["execution_allowed"] = False
    projected["paper_order_allowed"] = False
    projected["write_authority"] = False
    projected["live_capital_enabled"] = False
    return projected


def _paper_account_digest(paper_account_context: dict[str, Any] | None) -> str:
    context = _paper_account_projection(paper_account_context)
    balance = context.get("current_balance_gbp", "unknown")
    positions = context.get("open_position_count", 0)
    orders = context.get("order_count", 0)
    drawdown = context.get("drawdown_pct", 0)
    connection = context.get("connection_status", "unknown")
    return (
        f"paper account mirror: {connection}, current balance GBP {balance}, "
        f"{positions} open positions, {orders} mirrored orders, drawdown {drawdown}%"
    )


def _deterministic_local_research_assessment(
    packets: tuple[dict[str, Any], ...],
    *,
    provider: str,
    model: str,
    mode: str,
    raw_response_status: str,
    paper_account_context: dict[str, Any] | None = None,
) -> LocalResearchAssessment:
    summaries = " ".join(str(packet.get("summary", "")) for packet in packets)
    packet_ids = tuple(str(packet.get("packet_id", "unknown")) for packet in packets)
    focus = _instrument_focus(summaries)
    paper_digest = _paper_account_digest(paper_account_context)
    preference_digest = _preference_context_digest_from_packets(packets)
    tradingview_digest = _tradingview_mcp_digest_from_packets(packets)
    confidence = round(min(0.82, 0.4 + _keyword_strength(summaries) * 0.45), 3)
    anomalies: tuple[str, ...] = ("no queued packets",)
    next_questions: tuple[str, ...] = ("wait for source heartbeat and shadow triage inputs",)
    if packets:
        anomalies = tuple(
            str(packet.get("summary", "shadow packet requires review"))[:180]
            for packet in packets[-3:]
        )
        if preference_digest:
            anomalies += (preference_digest,)
        if tradingview_digest:
            anomalies += (tradingview_digest,)
        anomalies += (paper_digest,)
        next_questions = (
            "Which independent source can corroborate this observation?",
            "Does the catalyst map to a Phase 1 instrument without forcing a trade?",
            "Which stale-data or missing-credential condition could invalidate the packet?",
            "Does the read-only paper account state change review priority without creating an order?",
        )
    missing_correlations = (
        "signal_integrity_gate",
        "risk_agent_review",
        "market_price_confirmation",
    )
    if len(packets) < 2:
        missing_correlations += ("second_independent_source",)
    if preference_digest:
        missing_correlations += ("preference_mcp_canonical_corroboration",)
    if tradingview_digest:
        missing_correlations += ("tradingview_mcp_canonical_corroboration",)
    return LocalResearchAssessment(
        schema_version=LOCAL_RESEARCH_ASSESSMENT_SCHEMA_VERSION,
        assessment_id=str(uuid4()),
        status="shadow_only",
        mode=mode,
        provider=provider,
        model=model or "missing",
        packet_ids=packet_ids,
        summary=(
            "Local Research Analyst contract produced a shadow-only assessment. "
            f"Current focus: {focus}. No execution path is available."
        ),
        watch_focus=focus,
        anomalies=anomalies,
        missing_correlations=missing_correlations,
        next_questions=next_questions,
        escalation_recommendation="hold_shadow",
        confidence=confidence,
        raw_response_status=raw_response_status,
        execution_allowed=False,
        paper_order_allowed=False,
        created_at=_now(),
        boundary=(
            "Local Research Analyst output is compression only. Paper account context is read-only; "
            "it cannot approve signals, risk, or orders."
        ),
    )


def _assessment_from_model_payload(
    payload: dict[str, Any],
    packets: tuple[dict[str, Any], ...],
    *,
    provider: str,
    model: str,
    raw_response_status: str,
    paper_account_context: dict[str, Any] | None = None,
) -> LocalResearchAssessment:
    packet_ids = tuple(str(packet.get("packet_id", "unknown")) for packet in packets)
    paper_digest = _paper_account_digest(paper_account_context)
    confidence_value = payload.get("confidence", 0.0)
    try:
        confidence = float(confidence_value)
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = round(max(0.0, min(1.0, confidence)), 3)
    recommendation = str(payload.get("escalation_recommendation", "hold_shadow")).strip()
    if recommendation not in {"hold_shadow", "escalate_to_strategy_lead_shadow"}:
        recommendation = "hold_shadow"
    return LocalResearchAssessment(
        schema_version=LOCAL_RESEARCH_ASSESSMENT_SCHEMA_VERSION,
        assessment_id=str(uuid4()),
        status="shadow_only",
        mode="live_local_llm",
        provider=provider,
        model=model,
        packet_ids=packet_ids,
        summary=(
            str(payload.get("summary", "Local model returned an empty summary.")).strip()
            + f" Paper context: {paper_digest}."
        )[:1000],
        watch_focus=str(payload.get("watch_focus", "macro_watchlist"))[:120],
        anomalies=_coerce_string_list(payload.get("anomalies"), fallback=("none_identified",)),
        missing_correlations=_coerce_string_list(
            payload.get("missing_correlations"),
            fallback=("second_independent_source", "signal_integrity_gate"),
        ),
        next_questions=_coerce_string_list(
            payload.get("next_questions"),
            fallback=("What source can corroborate this packet?",),
        ),
        escalation_recommendation=recommendation,
        confidence=confidence,
        raw_response_status=raw_response_status,
        execution_allowed=False,
        paper_order_allowed=False,
        created_at=_now(),
        boundary=(
            "Local Research Analyst output is compression only. Paper account context is read-only; "
            "it cannot approve signals, risk, or orders."
        ),
    )


class LocalResearchAssessmentStore:
    def __init__(self, path: str | Path | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.path = Path(
            path or Path(self.settings.runtime_dir) / "local_research_assessments.jsonl"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, assessment: LocalResearchAssessment) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(assessment.to_dict(), sort_keys=True) + "\n")

    def read(self) -> tuple[dict[str, Any], ...]:
        if not self.path.exists():
            return ()
        assessments: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    loaded = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"invalid local research assessment line {line_number} in {self.path}"
                    ) from exc
                if isinstance(loaded, dict):
                    assessments.append(loaded)
        return tuple(assessments)

    def health(self) -> dict[str, Any]:
        try:
            assessments = self.read()
        except Exception as exc:  # noqa: BLE001 - health should report failure
            return {"status": "degraded", "path": str(self.path), "error": str(exc)}
        return {
            "status": "ok",
            "path": str(self.path),
            "schema_version": LOCAL_RESEARCH_ASSESSMENT_SCHEMA_VERSION,
            "assessment_count": len(assessments),
            "execution_allowed_count": sum(
                1 for assessment in assessments if assessment.get("execution_allowed") is True
            ),
            "paper_order_allowed_count": sum(
                1 for assessment in assessments if assessment.get("paper_order_allowed") is True
            ),
            "last_assessment_id": assessments[-1].get("assessment_id") if assessments else None,
        }


def local_research_analyst_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    store = LocalResearchAssessmentStore(settings=settings)
    local = lm_studio_models_probe(settings, live=False)
    return {
        "status": "ready" if local["probe_status"] in {"not_called", "ok"} else "degraded",
        "schema_version": LOCAL_RESEARCH_ASSESSMENT_SCHEMA_VERSION,
        "provider": local["provider"],
        "model": local["model"],
        "store": store.health(),
        "boundary": "Local Research Analyst assessments are shadow-only compression, not trade authority.",
    }


def run_local_research_analyst_inference(
    *,
    limit: int = 5,
    live: bool = False,
    settings: Settings | None = None,
    store: LocalResearchAssessmentStore | None = None,
    event_log: EventLog | None = None,
    paper_account_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    store = store or LocalResearchAssessmentStore(settings=settings)
    event_log = event_log or EventLog(echo=False)
    local_provider = secret_value("LOCAL_LLM_PROVIDER", settings) or "lm_studio"
    base_url = secret_value("LM_STUDIO_BASE_URL", settings) or "http://127.0.0.1:1234/v1"
    model = secret_value("LM_STUDIO_MODEL", settings) or ""
    packets = read_research_shadow_triage_queue(settings)
    selected = packets[-limit:] if limit > 0 else packets
    safe_paper_context = _paper_account_projection(paper_account_context)

    if not live:
        assessment = _deterministic_local_research_assessment(
            selected,
            provider=local_provider,
            model=model,
            mode="dry_contract",
            raw_response_status="not_called",
            paper_account_context=safe_paper_context,
        )
        store.write(assessment)
        event_log.write(
            "local_research_assessment_recorded",
            "intelligence",
            {
                "assessment_id": assessment.assessment_id,
                "mode": assessment.mode,
                "packet_count": len(selected),
                "execution_allowed": assessment.execution_allowed,
                "paper_order_allowed": assessment.paper_order_allowed,
            },
        )
        return {
            "status": "ok",
            "mode": "dry_contract",
            "packet_count": len(packets),
            "processed_packet_count": len(selected),
            "assessment": assessment.to_dict(),
            "paper_account_context": safe_paper_context,
            "store": store.health(),
            "event_log": event_log.health(),
            "boundary": assessment.boundary,
        }

    provider_probe = lm_studio_models_probe(settings, live=True, timeout_seconds=1.5)
    if provider_probe["probe_status"] != "ok":
        event_log.write(
            "local_research_assessment_blocked",
            "intelligence",
            {
                "reason": "lm_studio_not_running",
                "probe_status": provider_probe["probe_status"],
                "execution_allowed": False,
                "paper_order_allowed": False,
            },
        )
        return {
            "status": "degraded",
            "mode": "live_local_llm",
            "provider_status": provider_probe,
            "reason": "LM Studio local server is not reachable on the configured base URL.",
            "paper_account_context": safe_paper_context,
            "store": store.health(),
            "event_log": event_log.health(),
            "boundary": "No model inference was run. Execution remains impossible.",
        }
    resolved_model = str(provider_probe.get("resolved_model") or model)
    packet_projections = [_packet_projection(packet) for packet in selected]
    evidence_hashes = {
        str(packet.get("packet_id") or f"packet-{index}"): sha256_json(packet)
        for index, packet in enumerate(packet_projections)
    }
    task = build_agent_task_packet(
        "local_research_assessment",
        decision_generation_id="local-research:" + sha256_json(evidence_hashes)[:24],
        objective="Compress queued shadow evidence into a cautious research assessment.",
        evidence_refs=sorted(evidence_hashes),
        evidence_hashes=evidence_hashes,
        untrusted_context={
            "mode": "paper_shadow_only",
            "paper_account_context": safe_paper_context,
            "packets": packet_projections,
        },
    )
    compiled_prompt = compile_agent_prompt(task)
    output_schema = json.loads((ROOT / task.output_schema_path).read_text(encoding="utf-8"))
    response = _http_json_post(
        f"{base_url.rstrip('/')}/chat/completions",
        {
            "model": resolved_model,
            "messages": [
                {"role": "system", "content": compiled_prompt["system_prompt"]},
                {
                    "role": "user",
                    "content": json.dumps(compiled_prompt["user_payload"], sort_keys=True),
                },
            ],
            "temperature": 0.1,
            "max_tokens": task.max_tokens,
            "reasoning_effort": "low",
            "stream": False,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "qadam_local_research_assessment",
                    "strict": True,
                    "schema": output_schema,
                },
            },
        },
        timeout_seconds=float(secret_value("LM_STUDIO_TIMEOUT_SECONDS", settings) or "90"),
        api_key=secret_value("LM_STUDIO_API_KEY", settings),
    )
    if response["status"] != "ok":
        event_log.write(
            "local_research_assessment_blocked",
            "intelligence",
            {
                "reason": response["status"],
                "http_status": response.get("http_status"),
                "execution_allowed": False,
                "paper_order_allowed": False,
            },
        )
        return {
            "status": "degraded",
            "mode": "live_local_llm",
            "provider_status": provider_probe,
            "reason": response["status"],
            "detail": response.get("reason") or response.get("body") or "no_detail",
            "http_status": response.get("http_status"),
            "paper_account_context": safe_paper_context,
            "store": store.health(),
            "event_log": event_log.health(),
            "boundary": "Local model call failed. Execution remains impossible.",
        }

    choices = (
        response["payload"].get("choices", []) if isinstance(response.get("payload"), dict) else []
    )
    content = ""
    if choices and isinstance(choices[0], dict):
        message = choices[0].get("message", {})
        if isinstance(message, dict):
            content = str(message.get("content", ""))
    model_payload: dict[str, Any]
    accepted_packet = None
    try:
        model_payload = _extract_json_object(content)
        critic_receipts = run_critic_gauntlet(task, model_payload)
        accepted_packet = compile_accepted_research_packet(task, model_payload, critic_receipts)
    except Exception:
        model_payload = {"parse_or_critic_error": True}
        critic_receipts = run_critic_gauntlet(task, model_payload)
    if accepted_packet is not None:
        assessment = _assessment_from_model_payload(
            model_payload,
            selected,
            provider=local_provider,
            model=resolved_model,
            raw_response_status="ok",
            paper_account_context=safe_paper_context,
        )
    else:
        assessment = _deterministic_local_research_assessment(
            selected,
            provider=local_provider,
            model=resolved_model,
            mode="live_local_llm_contract_fallback",
            raw_response_status="critic_or_parse_fallback",
            paper_account_context=safe_paper_context,
        )
    persist_agent_review(
        task,
        compiled_prompt,
        model_payload,
        critic_receipts,
        accepted_packet,
        settings,
    )

    store.write(assessment)
    event_log.write(
        "local_research_assessment_recorded",
        "intelligence",
        {
            "assessment_id": assessment.assessment_id,
            "mode": assessment.mode,
            "packet_count": len(selected),
            "escalation_recommendation": assessment.escalation_recommendation,
            "execution_allowed": assessment.execution_allowed,
            "paper_order_allowed": assessment.paper_order_allowed,
        },
    )
    return {
        "status": "ok",
        "mode": assessment.mode,
        "provider_status": provider_probe,
        "packet_count": len(packets),
        "processed_packet_count": len(selected),
        "assessment": assessment.to_dict(),
        "paper_account_context": safe_paper_context,
        "store": store.health(),
        "event_log": event_log.health(),
        "boundary": assessment.boundary,
    }


def _packet_to_evidence(packet: dict[str, Any]) -> EvidenceItem:
    refs = packet.get("source_event_refs", [])
    ref_text = ", ".join(ref for ref in refs if isinstance(ref, str)) or "no source refs"
    summary = (
        str(packet.get("summary", "")).strip() or "Research Analyst queued an empty shadow packet."
    )
    preference_context = _packet_preference_context(packet)
    tradingview_context = _packet_tradingview_mcp_context(packet)
    if preference_context:
        challenges = preference_context.get("active_required_challenges", [])
        observation_refs = preference_context.get("observation_refs", [])
        domain_packs = sorted(
            {
                str(item.get("domain_pack"))
                for item in observation_refs
                if isinstance(item, dict) and item.get("domain_pack")
            }
        )
        preference_summary = (
            "Preference MCP read-only context attached: "
            f"status={preference_context.get('status')}; "
            f"role={preference_context.get('context_role')}; "
            f"domain_packs={','.join(domain_packs[:6]) or 'none'}; "
            "preference-only confirmation is a hold condition; "
            "orderbook depth is market context only; "
            "wallet/KOL movement is risk sentiment only; "
            f"challenges={'; '.join(str(item) for item in challenges[:3])}."
        )
        summary = f"{summary} {preference_summary}"[:1000]
    if tradingview_context:
        refs = tradingview_context.get("technical_context_refs", [])
        symbols = sorted(
            {
                str(item.get("symbol"))
                for item in refs
                if isinstance(item, dict) and item.get("symbol")
            }
        )
        challenges = tradingview_context.get("active_required_challenges", [])
        tradingview_summary = (
            "TradingView MCP read-only technical context attached: "
            f"status={tradingview_context.get('status')}; "
            f"role={tradingview_context.get('context_role')}; "
            f"symbols={','.join(symbols[:6]) or 'none'}; "
            "technical context is supplemental only and cannot create source quorum, "
            "trade candidates, paper orders, or broker writes; "
            f"challenges={'; '.join(str(item) for item in challenges[:3])}."
        )
        summary = f"{summary} {tradingview_summary}"[:1000]
    uncertainty = str(packet.get("uncertainty", "unknown")).lower()
    trust_score = 0.56
    if uncertainty in {"low", "bounded", "known"}:
        trust_score = 0.68
    elif uncertainty in {"high", "unknown"}:
        trust_score = 0.48
    return EvidenceItem(
        evidence_id=f"shadow_triage_packet:{packet.get('packet_id', 'unknown')}",
        source="agent_runtime.research_triage_queue",
        event_type="research_shadow_triage_packet",
        summary=f"{summary} Source refs: {ref_text}",
        trust_score=trust_score,
        observed_at=str(packet.get("created_at") or _now()),
        raw_ref=str(packet.get("packet_id") or "unknown"),
    )


def _packet_market_source(packet: dict[str, Any]) -> str | None:
    summary = str(packet.get("summary", "")).lower()
    refs = packet.get("source_event_refs", [])
    ref_text = " ".join(ref for ref in refs if isinstance(ref, str)).lower()
    if "alpaca" in ref_text or "alpaca markets api" in summary:
        return "market.alpaca_readonly"
    tradingview_context = _packet_tradingview_mcp_context(packet)
    if tradingview_context:
        return "market.tradingview_mcp"
    if "yahoo" in ref_text or "yahoo" in summary:
        return "market.yahoo_finance"
    return None


def _packet_watchlist(packet: dict[str, Any]) -> tuple[str, ...]:
    context = packet.get("read_only_context")
    if not isinstance(context, dict):
        return ()
    research_goal = context.get("research_goal")
    if not isinstance(research_goal, dict):
        return ()
    watched = research_goal.get("watched_instruments", [])
    if not isinstance(watched, list):
        return ()
    return tuple(str(item).strip() for item in watched if str(item).strip())[:6]


def _packet_market_confirmation_score(packet: dict[str, Any]) -> float:
    context = packet.get("read_only_context")
    if not isinstance(context, dict):
        return 0.0
    research_goal = context.get("research_goal")
    if not isinstance(research_goal, dict):
        return 0.0
    return max(0.0, min(1.0, float(research_goal.get("market_confirmation_score", 0.0) or 0.0)))


def _packet_market_confirmation_item(packet: dict[str, Any]) -> EvidenceItem | None:
    market_source = _packet_market_source(packet)
    if not market_source:
        return None
    score = _packet_market_confirmation_score(packet)
    if score <= 0.0:
        return None
    now = str(packet.get("created_at") or _now())
    watchlist = _packet_watchlist(packet)
    summary = (
        "Read-only market confirmation captured for shadow review only. "
        f"source={market_source}; "
        f"watchlist={','.join(watchlist) or 'unscoped'}; "
        "price context is supplemental corroboration only and grants no signal, risk, order, "
        "fill, reconciliation, or broker authority."
    )
    return EvidenceItem(
        evidence_id=f"shadow_triage_market_confirmation:{packet.get('packet_id', 'unknown')}",
        source=market_source,
        event_type="market_price_confirmation",
        summary=summary,
        trust_score=round(max(0.55, min(0.82, 0.55 + score * 0.2)), 3),
        observed_at=now,
        raw_ref=str(packet.get("packet_id") or "unknown"),
    )


def _packet_pricing_gap_item(packet: dict[str, Any]) -> EvidenceItem | None:
    market_source = _packet_market_source(packet)
    if not market_source:
        return None
    score = _packet_market_confirmation_score(packet)
    if score <= 0.0:
        return None
    now = str(packet.get("created_at") or _now())
    watchlist = _packet_watchlist(packet)
    summary = (
        "Paper-only pricing gap confirmed for Signal Integrity shadowing. "
        f"source={market_source}; "
        f"watchlist={','.join(watchlist) or 'unscoped'}; "
        "gap assumptions remain research-stage context only and cannot create trade, order, "
        "or execution authority."
    )
    return EvidenceItem(
        evidence_id=f"shadow_triage_pricing_gap:{packet.get('packet_id', 'unknown')}",
        source=market_source,
        event_type="pricing_gap_assumption",
        summary=summary,
        trust_score=round(max(0.52, min(0.78, 0.52 + score * 0.18)), 3),
        observed_at=now,
        raw_ref=str(packet.get("packet_id") or "unknown"),
    )


def _packet_transaction_cost_item(packet: dict[str, Any]) -> EvidenceItem | None:
    market_source = _packet_market_source(packet)
    if not market_source:
        return None
    score = _packet_market_confirmation_score(packet)
    if score <= 0.0:
        return None
    now = str(packet.get("created_at") or _now())
    watchlist = _packet_watchlist(packet)
    summary = (
        "Transaction-cost assumptions confirmed for paper-only shadow review. "
        f"source={market_source}; "
        f"watchlist={','.join(watchlist) or 'unscoped'}; "
        "spread and slippage assumptions confirmed for non-executing review only."
    )
    return EvidenceItem(
        evidence_id=f"shadow_triage_transaction_cost:{packet.get('packet_id', 'unknown')}",
        source=market_source,
        event_type="transaction_cost_assumption",
        summary=summary,
        trust_score=round(max(0.5, min(0.76, 0.5 + score * 0.16)), 3),
        observed_at=now,
        raw_ref=str(packet.get("packet_id") or "unknown"),
    )


def _packet_evidence_items(packet: dict[str, Any]) -> tuple[EvidenceItem, ...]:
    items = [_packet_to_evidence(packet)]
    for candidate in (
        _packet_market_confirmation_item(packet),
        _packet_pricing_gap_item(packet),
        _packet_transaction_cost_item(packet),
    ):
        if candidate is not None:
            items.append(candidate)
    return tuple(items)


def _deterministic_signal_from_packet(packet: dict[str, Any]) -> ProposedSignal | None:
    evidence_items = _packet_evidence_items(packet)
    combined_text = " ".join(item.summary for item in evidence_items)
    keyword_strength = _keyword_strength(combined_text)
    market_bonus = (
        0.14
        if any(item.event_type == "market_price_confirmation" for item in evidence_items)
        else 0.0
    )
    pricing_bonus = (
        0.08 if any(item.event_type == "pricing_gap_assumption" for item in evidence_items) else 0.0
    )
    confidence = round(
        min(
            0.94,
            max(item.trust_score for item in evidence_items) * 0.45
            + (sum(item.trust_score for item in evidence_items) / len(evidence_items)) * 0.2
            + keyword_strength * 0.2
            + market_bonus
            + pricing_bonus,
        ),
        3,
    )
    if confidence < 0.42:
        return None
    trail = build_evidence_trail(evidence_items)
    focus = _instrument_focus(
        " ".join(
            [
                combined_text,
                str(packet.get("summary", "")),
                str(
                    packet.get("read_only_context", {})
                    .get("research_goal", {})
                    .get("hypothesis", "")
                )
                if isinstance(packet.get("read_only_context"), dict)
                else "",
            ]
        )
    )
    return ProposedSignal(
        schema_version=PROPOSED_SIGNAL_SCHEMA_VERSION,
        signal_id=str(uuid4()),
        status="shadow_only",
        title=f"Shadow watch: {focus}",
        instrument_focus=focus,
        thesis=(
            "Deterministic research-triage packet promoted to a shadow-only signal with "
            f"{len(evidence_items)} structured evidence items. {str(packet.get('summary', ''))[:180]}"
        ),
        confidence=confidence,
        invalidation=(
            "Discard unless independent corroboration, market confirmation, pricing-gap assumptions, "
            "and transaction-cost assumptions remain current and non-executing."
        ),
        evidence_trail=trail,
        generated_by="research_shadow_triage_queue_deterministic",
        execution_allowed=False,
        created_at=_now(),
    )


def run_research_shadow_triage_queue(
    *,
    limit: int = 10,
    settings: Settings | None = None,
    store: ShadowSignalStore | None = None,
    event_log: EventLog | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    store = store or ShadowSignalStore(settings=settings)
    event_log = event_log or EventLog(echo=False)
    packets = read_research_shadow_triage_queue(settings)
    selected = packets[-limit:] if limit > 0 else packets
    signals = tuple(
        signal
        for packet in selected
        if (signal := _deterministic_signal_from_packet(packet)) is not None
    )
    for signal in signals:
        store.write(signal)
    event_log.write(
        "research_shadow_triage_queue_processed",
        "intelligence",
        {
            "packet_count": len(packets),
            "processed_packet_count": len(selected),
            "shadow_signal_count": len(signals),
            "execution_allowed_count": sum(1 for signal in signals if signal.execution_allowed),
        },
    )
    return {
        "status": "ok",
        "queue_path": str(_triage_queue_path(settings)),
        "packet_count": len(packets),
        "processed_packet_count": len(selected),
        "shadow_signal_count": len(signals),
        "execution_allowed_count": sum(1 for signal in signals if signal.execution_allowed),
        "store": store.health(),
        "event_log": event_log.health(),
        "boundary": "Research Analyst triage runner produces shadow-only signals with no execution authority.",
    }


def shadow_intelligence_summary(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    store = ShadowSignalStore(settings=settings)
    local_research = LocalResearchAssessmentStore(settings=settings)
    providers = provider_status(settings)
    return {
        "status": "shadow_ready" if providers["status"] in {"ok", "degraded"} else "degraded",
        "schema_version": PROPOSED_SIGNAL_SCHEMA_VERSION,
        "store": store.health(),
        "local_research": local_research.health(),
        "provider_status": providers,
        "boundary": "Phase 2 shadow intelligence can propose review packets only; execution remains impossible.",
    }
