"""Canonical public-safe evidence packet normalization.

This module is a read-only boundary layer. It accepts evidence trails, adapter
evidence items, or already-normalized packet-shaped dicts and emits one stable
dashboard/API packet shape. It never grants source quorum, signal approval,
risk handoff, order authority, broker writes, performance credit, quantum job
authority, or live capital.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from statistics import fmean
from typing import Any, Iterable

from orchestrator.intelligence import EvidenceItem


EVIDENCE_PACKET_NORMALIZATION_SCHEMA_VERSION = 1
EVIDENCE_PACKET_NORMALIZATION_VERSION = "epn_2026_06_14"

EVIDENCE_PACKET_BOUNDARY = (
    "Factual evidence packet only. It can support review but cannot create "
    "trade ideas, orders, broker writes, or performance credit. It cannot "
    "create a trade idea or order."
)

EVIDENCE_ITEM_BOUNDARY = (
    "Evidence item only. It can support research review after corroboration, "
    "but cannot create source quorum, trade ideas, risk approval, orders, "
    "broker writes, or live capital."
)

AUTHORITY_FALSE_FIELDS: tuple[str, ...] = (
    "source_quorum_credit_allowed",
    "risk_handoff_allowed",
    "trade_candidate_creation_allowed",
    "execution_allowed",
    "paper_order_allowed",
    "broker_write_allowed",
    "performance_credit_allowed",
    "quantum_job_authority",
    "live_capital_enabled",
)

ITEM_AUTHORITY_FALSE_FIELDS: tuple[str, ...] = (
    "source_quorum_credit_allowed",
    "trade_candidate_creation_allowed",
    "execution_allowed",
    "paper_order_allowed",
    "broker_write_allowed",
    "live_capital_enabled",
)

SECRET_LIKE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\d{6,}:[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bvcp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"\bsb_secret_[0-9A-Za-z_-]{12,}\b"),
    re.compile(r"\b[A-Za-z0-9_-]{40,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b"),
)
LOCAL_PATH_PATTERN = re.compile(r"/Users/[^ \"'\n\r]+")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _coerce_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, EvidenceItem):
        return value.to_dict()
    if is_dataclass(value):
        raw = asdict(value)
        return raw if isinstance(raw, dict) else {}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        try:
            raw = value.to_dict()
        except Exception:  # noqa: BLE001 - normalization must fail closed
            return {}
        return raw if isinstance(raw, dict) else {}
    return {}


def _safe_text(value: Any, fallback: str = "", *, limit: int = 600) -> str:
    text = str(value if value is not None else fallback)
    text = LOCAL_PATH_PATTERN.sub("[local-path-redacted]", text)
    for pattern in SECRET_LIKE_PATTERNS:
        text = pattern.sub("[secret-redacted]", text)
    text = " ".join(text.split())
    return text[:limit]


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = fallback
    return round(max(0.0, min(1.0, number)), 3)


def _safe_list(value: Any, *, limit: int = 12) -> list[Any]:
    if isinstance(value, tuple | list):
        return list(value)[:limit]
    return []


def _stable_id(prefix: str, values: Iterable[Any]) -> str:
    digest = hashlib.sha256(
        "|".join(_safe_text(value, limit=220) for value in values).encode("utf-8")
    ).hexdigest()[:24]
    return f"{prefix}:{digest}"


def normalize_evidence_item(item: Any, *, source_key: str = "") -> dict[str, Any]:
    """Normalize one evidence item and strip raw/private references."""

    raw = _coerce_dict(item)
    evidence_id = _safe_text(raw.get("evidence_id") or raw.get("id") or "unknown", limit=160)
    source = _safe_text(raw.get("source") or source_key or "unknown_source", limit=120)
    event_type = _safe_text(raw.get("event_type") or raw.get("type") or "evidence_context", limit=120)
    summary = _safe_text(raw.get("summary") or "Evidence context recorded.", limit=900)
    observed_at = _safe_text(raw.get("observed_at") or raw.get("created_at") or _now(), limit=80)
    normalized = {
        "schema_version": EVIDENCE_PACKET_NORMALIZATION_SCHEMA_VERSION,
        "evidence_id": evidence_id,
        "source": source,
        "source_key": _safe_text(source_key or source.split(".")[-1] or source, limit=80),
        "event_type": event_type,
        "summary": summary,
        "trust_score": _safe_float(raw.get("trust_score"), 0.0),
        "observed_at": observed_at,
        "evidence_role": "factual_evidence_item",
        "public_safe": True,
        "boundary": EVIDENCE_ITEM_BOUNDARY,
    }
    for field in ITEM_AUTHORITY_FALSE_FIELDS:
        normalized[field] = False
    return normalized


def _packet_items_from_input(value: Any) -> tuple[dict[str, Any], ...]:
    raw = _coerce_dict(value)
    if "evidence_trail" in raw and isinstance(raw.get("evidence_trail"), dict):
        return tuple(_safe_list(raw["evidence_trail"].get("evidence_items"), limit=24))
    if "evidence_items" in raw:
        return tuple(_safe_list(raw.get("evidence_items"), limit=24))
    if "items" in raw:
        return tuple(_safe_list(raw.get("items"), limit=24))
    if isinstance(value, tuple | list):
        return tuple(value[:24])
    return ()


def normalize_evidence_packet(
    value: Any,
    *,
    signal_id: str | None = None,
    trail_id: str | None = None,
    packet_type: str = "factual_evidence_packet",
    packet_role: str = "research_review_evidence",
    source_key: str = "",
    summary: str | None = None,
    missing_correlations: Iterable[Any] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Normalize a signal, trail, evidence-item list, or packet-shaped dict."""

    raw = _coerce_dict(value)
    trail = raw.get("evidence_trail") if isinstance(raw.get("evidence_trail"), dict) else raw
    raw_items = _packet_items_from_input(value)
    items = [normalize_evidence_item(item, source_key=source_key) for item in raw_items]
    trust_scores = [float(item.get("trust_score", 0.0) or 0.0) for item in items]
    sources = sorted({str(item.get("source")) for item in items if item.get("source")})
    resolved_signal_id = _safe_text(signal_id or raw.get("signal_id") or raw.get("source_signal_id") or "unlinked_signal", limit=120)
    resolved_trail_id = _safe_text(
        trail_id or trail.get("trail_id") or raw.get("trail_id") or _stable_id("evidence_trail", [resolved_signal_id, *[item.get("evidence_id") for item in items]]),
        limit=160,
    )
    resolved_created_at = _safe_text(
        created_at or trail.get("created_at") or raw.get("created_at") or _now(),
        limit=80,
    )
    resolved_missing = [
        _safe_text(item, limit=120)
        for item in (
            list(missing_correlations)
            if missing_correlations is not None
            else _safe_list(trail.get("missing_correlations") or raw.get("missing_correlations"), limit=12)
        )
        if _safe_text(item, limit=120)
    ][:12]
    packet_summary = _safe_text(
        summary
        or raw.get("summary")
        or raw.get("thesis")
        or (items[0].get("summary") if items else "No evidence items exported."),
        limit=900,
    )
    normalized = {
        "schema_version": EVIDENCE_PACKET_NORMALIZATION_SCHEMA_VERSION,
        "normalization_version": EVIDENCE_PACKET_NORMALIZATION_VERSION,
        "status": "evidence_recorded" if items else "pending_evidence_items",
        "packet_id": _stable_id("evidence_packet", [resolved_signal_id, resolved_trail_id, *[item.get("evidence_id") for item in items]]),
        "signal_id": resolved_signal_id,
        "trail_id": resolved_trail_id,
        "packet_type": _safe_text(packet_type, "factual_evidence_packet", limit=100),
        "packet_role": _safe_text(packet_role, "research_review_evidence", limit=100),
        "source_key": _safe_text(source_key or raw.get("source_key") or "mixed_sources", limit=80),
        "source_count": int(trail.get("source_count") or raw.get("source_count") or len(sources)),
        "item_count": len(items),
        "sources": sources,
        "items": items,
        "min_trust_score": _safe_float(
            trail.get("min_trust_score") if trail.get("min_trust_score") is not None else (min(trust_scores) if trust_scores else 0.0),
            0.0,
        ),
        "average_trust_score": _safe_float(
            trail.get("average_trust_score")
            if trail.get("average_trust_score") is not None
            else (fmean(trust_scores) if trust_scores else 0.0),
            0.0,
        ),
        "missing_correlations": resolved_missing,
        "summary": packet_summary,
        "created_at": resolved_created_at,
        "public_safe": True,
        "boundary": EVIDENCE_PACKET_BOUNDARY,
    }
    for field in AUTHORITY_FALSE_FIELDS:
        normalized[field] = False
    return normalized


def normalize_signal_evidence_packet(signal: dict[str, Any]) -> dict[str, Any]:
    return normalize_evidence_packet(
        signal,
        signal_id=str(signal.get("signal_id") or "unlinked_signal"),
        packet_type="shadow_signal_evidence_packet",
        packet_role="hypothesis_supporting_evidence",
        source_key="shadow_signal_store",
        summary=signal.get("thesis") or signal.get("title"),
    )


def normalize_adapter_evidence_packet(
    *,
    source_key: str,
    evidence_items: Iterable[Any],
    packet_type: str,
    context_role: str,
    status: str = "evidence_recorded",
    summary: str = "",
    created_at: str | None = None,
) -> dict[str, Any]:
    packet = normalize_evidence_packet(
        list(evidence_items),
        signal_id=f"{source_key}_supplemental_context",
        packet_type=packet_type,
        packet_role=context_role,
        source_key=source_key,
        summary=summary or f"{source_key} supplemental evidence context.",
        created_at=created_at,
    )
    packet["status"] = _safe_text(status or packet["status"], limit=100)
    return packet


def validate_normalized_evidence_packet(packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version",
        "normalization_version",
        "status",
        "packet_id",
        "signal_id",
        "trail_id",
        "packet_type",
        "packet_role",
        "source_key",
        "source_count",
        "item_count",
        "sources",
        "items",
        "min_trust_score",
        "average_trust_score",
        "missing_correlations",
        "summary",
        "created_at",
        "public_safe",
        "boundary",
    }
    missing = sorted(required - set(packet))
    errors.extend(f"missing_field:{field}" for field in missing)
    if packet.get("schema_version") != EVIDENCE_PACKET_NORMALIZATION_SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if packet.get("public_safe") is not True:
        errors.append("public_safe_not_true")
    if not isinstance(packet.get("items"), list) or not packet.get("items"):
        errors.append("items_empty")
    if int(packet.get("item_count", 0) or 0) != len(packet.get("items", [])):
        errors.append("item_count_mismatch")
    if "cannot create trade ideas, orders, broker writes, or performance credit" not in str(packet.get("boundary", "")):
        errors.append("packet_boundary_weak")
    if "cannot create a trade idea or order" not in str(packet.get("boundary", "")):
        errors.append("packet_trade_boundary_weak")
    for field in AUTHORITY_FALSE_FIELDS:
        if packet.get(field) is not False:
            errors.append(f"authority_enabled:{field}")
    for item in packet.get("items", []):
        if not isinstance(item, dict):
            errors.append("item_not_object")
            continue
        for field in ("evidence_id", "source", "event_type", "summary", "trust_score", "observed_at", "public_safe"):
            if field not in item:
                errors.append(f"item_missing_field:{field}")
        if "raw_ref" in item:
            errors.append("raw_ref_leaked")
        if item.get("public_safe") is not True:
            errors.append("item_public_safe_not_true")
        for field in ITEM_AUTHORITY_FALSE_FIELDS:
            if item.get(field) is not False:
                errors.append(f"item_authority_enabled:{field}")
    return errors


def evidence_packet_normalization_summary(packets: Iterable[dict[str, Any]]) -> dict[str, Any]:
    packet_list = list(packets)
    validation_errors = [
        f"{packet.get('packet_id', packet.get('trail_id', 'unknown'))}:{error}"
        for packet in packet_list
        for error in validate_normalized_evidence_packet(packet)
    ]
    authority_leak_count = sum(
        1
        for packet in packet_list
        for field in AUTHORITY_FALSE_FIELDS
        if packet.get(field) is not False
    ) + sum(
        1
        for packet in packet_list
        for item in packet.get("items", [])
        if isinstance(item, dict)
        for field in ITEM_AUTHORITY_FALSE_FIELDS
        if item.get(field) is not False
    )
    raw_ref_leak_count = sum(
        1
        for packet in packet_list
        for item in packet.get("items", [])
        if isinstance(item, dict) and "raw_ref" in item
    )
    return {
        "schema_version": EVIDENCE_PACKET_NORMALIZATION_SCHEMA_VERSION,
        "normalization_version": EVIDENCE_PACKET_NORMALIZATION_VERSION,
        "status": "ok" if not validation_errors else "degraded",
        "normalized_packet_count": len(packet_list),
        "normalized_item_count": sum(len(packet.get("items", [])) for packet in packet_list),
        "authority_leak_count": authority_leak_count,
        "raw_ref_leak_count": raw_ref_leak_count,
        "validation_error_count": len(validation_errors),
        "validation_errors": validation_errors[:20],
        "public_safe": True,
        "boundary": (
            "Evidence packet normalization is read-only. It strips raw refs, "
            "normalizes source evidence, and cannot create source quorum, trade "
            "ideas, risk approval, orders, broker writes, quantum jobs, "
            "performance credit, or live capital."
        ),
    }
