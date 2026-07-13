"""Shared deterministic primitives for operator-ready research Wave B."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from orchestrator.qadam_operator_ready_common import atomic_write_text, canonical_json

WAVE_B_SCHEMA_VERSION = "qadam_operator_ready_wave_b.v1"

STRATEGY_HYPOTHESES: dict[str, dict[str, str]] = {
    "crude_oil_energy_security_disruption": {
        "direction": "upside_under_confirmed_disruption",
        "horizon": "3d_forward",
    },
    "defence_repricing_geopolitical_watch": {
        "direction": "upside_under_confirmed_repricing",
        "horizon": "5d_forward",
    },
    "prediction_market_geopolitical_dislocation": {
        "direction": "two_sided_probability_dislocation",
        "horizon": "event_expiry",
    },
    "semiconductor_policy_options_asymmetry": {
        "direction": "conditional_policy_asymmetry",
        "horizon": "5d_forward",
    },
    "silver_macro_liquidity_stress": {
        "direction": "upside_under_confirmed_liquidity_stress",
        "horizon": "5d_forward",
    },
}


def stable_id(prefix: str, *parts: Any) -> str:
    material = canonical_json(list(parts))
    return f"{prefix}:{hashlib.sha256(material.encode('utf-8')).hexdigest()[:24]}"


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return round(max(lower, min(upper, value)), 8)


def safe_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def record_set_hash(records: Iterable[dict[str, Any]]) -> str:
    material = "\n".join(canonical_json(record) for record in records)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def write_jsonl_atomic(path: Path, records: Iterable[dict[str, Any]]) -> None:
    text = "".join(json.dumps(record, sort_keys=True, default=str) + "\n" for record in records)
    atomic_write_text(path, text)


def contains_forbidden_key(payload: Any, forbidden: set[str]) -> bool:
    if isinstance(payload, dict):
        if set(payload).intersection(forbidden):
            return True
        return any(contains_forbidden_key(value, forbidden) for value in payload.values())
    if isinstance(payload, list):
        return any(contains_forbidden_key(value, forbidden) for value in payload)
    return False
