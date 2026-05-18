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
    lm_studio_configured = local_provider == "lm_studio" and bool(lm_studio_base_url and lm_studio_model)
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

    probe = _http_json_probe(f"{lm_studio_base_url.rstrip('/')}/models", timeout_seconds=timeout_seconds)
    models_payload = probe.get("payload", {})
    models = models_payload.get("data", []) if isinstance(models_payload, dict) else []
    model_ids = [item.get("id") for item in models if isinstance(item, dict) and isinstance(item.get("id"), str)]
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
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    frontier = gemini_credential_probe(settings, live=gemini_live)
    local = lm_studio_models_probe(settings, live=local_live)
    frontier_ready = frontier["credential_configured"] and frontier["probe_status"] in {"not_called", "ok"}
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


def _triage_queue_path(settings: Settings | None = None) -> Path:
    settings = settings or Settings.from_env()
    return Path(settings.runtime_dir) / "research_triage_queue.jsonl"


def read_research_shadow_triage_queue(settings: Settings | None = None) -> tuple[dict[str, Any], ...]:
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
                raise ValueError(f"invalid research triage packet line {line_number} in {path}") from exc
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
    return {
        "packet_id": str(packet.get("packet_id", "unknown")),
        "status": str(packet.get("status", "unknown")),
        "summary": str(packet.get("summary", ""))[:600],
        "uncertainty": str(packet.get("uncertainty", "unknown")),
        "source_event_refs": [str(ref)[:160] for ref in refs if isinstance(ref, str)][:8],
        "created_at": str(packet.get("created_at", "")),
    }


def _deterministic_local_research_assessment(
    packets: tuple[dict[str, Any], ...],
    *,
    provider: str,
    model: str,
    mode: str,
    raw_response_status: str,
) -> LocalResearchAssessment:
    summaries = " ".join(str(packet.get("summary", "")) for packet in packets)
    packet_ids = tuple(str(packet.get("packet_id", "unknown")) for packet in packets)
    focus = _instrument_focus(summaries)
    confidence = round(min(0.82, 0.4 + _keyword_strength(summaries) * 0.45), 3)
    anomalies: tuple[str, ...] = ("no queued packets",)
    next_questions: tuple[str, ...] = ("wait for source heartbeat and shadow triage inputs",)
    if packets:
        anomalies = tuple(
            str(packet.get("summary", "shadow packet requires review"))[:180]
            for packet in packets[-3:]
        )
        next_questions = (
            "Which independent source can corroborate this observation?",
            "Does the catalyst map to a Phase 1 instrument without forcing a trade?",
            "Which stale-data or missing-credential condition could invalidate the packet?",
        )
    missing_correlations = ("signal_integrity_gate", "risk_agent_review", "market_price_confirmation")
    if len(packets) < 2:
        missing_correlations += ("second_independent_source",)
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
        boundary="Local Research Analyst output is compression only. It cannot approve signals, risk, or orders.",
    )


def _assessment_from_model_payload(
    payload: dict[str, Any],
    packets: tuple[dict[str, Any], ...],
    *,
    provider: str,
    model: str,
    raw_response_status: str,
) -> LocalResearchAssessment:
    packet_ids = tuple(str(packet.get("packet_id", "unknown")) for packet in packets)
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
        summary=str(payload.get("summary", "Local model returned an empty summary."))[:1000],
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
        boundary="Local Research Analyst output is compression only. It cannot approve signals, risk, or orders.",
    )


class LocalResearchAssessmentStore:
    def __init__(self, path: str | Path | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.path = Path(path or Path(self.settings.runtime_dir) / "local_research_assessments.jsonl")
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
                    raise ValueError(f"invalid local research assessment line {line_number} in {self.path}") from exc
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
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    store = store or LocalResearchAssessmentStore(settings=settings)
    event_log = event_log or EventLog(echo=False)
    local_provider = secret_value("LOCAL_LLM_PROVIDER", settings) or "lm_studio"
    base_url = secret_value("LM_STUDIO_BASE_URL", settings) or "http://127.0.0.1:1234/v1"
    model = secret_value("LM_STUDIO_MODEL", settings) or ""
    packets = read_research_shadow_triage_queue(settings)
    selected = packets[-limit:] if limit > 0 else packets

    if not live:
        assessment = _deterministic_local_research_assessment(
            selected,
            provider=local_provider,
            model=model,
            mode="dry_contract",
            raw_response_status="not_called",
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
            "store": store.health(),
            "event_log": event_log.health(),
            "boundary": "No model inference was run. Execution remains impossible.",
        }
    resolved_model = str(provider_probe.get("resolved_model") or model)

    system_prompt = (
        "You are Qadam's local Research Analyst. Compress queued shadow packets into "
        "a cautious research assessment. Return valid JSON only. The first character "
        "must be { and the final character must be }. Do not wrap the JSON in Markdown. "
        "Do not include commentary before or after the JSON. Do not recommend orders, "
        "position sizes, approvals, or execution. Treat private world-view priors as "
        "hypotheses only. Use exactly these keys: summary string, watch_focus string, "
        "anomalies array of strings, missing_correlations array of strings, "
        "next_questions array of strings, escalation_recommendation either hold_shadow "
        "or escalate_to_strategy_lead_shadow, confidence number from 0 to 1."
    )
    user_payload = {
        "mode": "paper_shadow_only",
        "execution_allowed": False,
        "paper_order_allowed": False,
        "packets": [_packet_projection(packet) for packet in selected],
    }
    response = _http_json_post(
        f"{base_url.rstrip('/')}/chat/completions",
        {
            "model": resolved_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, sort_keys=True)},
            ],
            "temperature": 0.1,
            "max_tokens": 900,
            "stream": False,
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
            "store": store.health(),
            "event_log": event_log.health(),
            "boundary": "Local model call failed. Execution remains impossible.",
        }

    choices = response["payload"].get("choices", []) if isinstance(response.get("payload"), dict) else []
    content = ""
    if choices and isinstance(choices[0], dict):
        message = choices[0].get("message", {})
        if isinstance(message, dict):
            content = str(message.get("content", ""))
    try:
        model_payload = _extract_json_object(content)
        assessment = _assessment_from_model_payload(
            model_payload,
            selected,
            provider=local_provider,
            model=resolved_model,
            raw_response_status="ok",
        )
    except Exception:
        assessment = _deterministic_local_research_assessment(
            selected,
            provider=local_provider,
            model=resolved_model,
            mode="live_local_llm_parse_fallback",
            raw_response_status="parse_fallback",
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
        "store": store.health(),
        "event_log": event_log.health(),
        "boundary": assessment.boundary,
    }


def _packet_to_evidence(packet: dict[str, Any]) -> EvidenceItem:
    refs = packet.get("source_event_refs", [])
    ref_text = ", ".join(ref for ref in refs if isinstance(ref, str)) or "no source refs"
    summary = str(packet.get("summary", "")).strip() or "Research Analyst queued an empty shadow packet."
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
    evidence = tuple(_packet_to_evidence(packet) for packet in selected)
    signals = deterministic_shadow_triage(evidence)
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
