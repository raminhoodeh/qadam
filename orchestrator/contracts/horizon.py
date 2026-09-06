"""Frozen elapsed-time horizon semantics, shared by research and reporting."""

import re
from typing import Any


def _horizon_seconds(value: Any) -> int:
    normalized = str(value or "").strip().lower().replace("_forward", "")
    match = re.fullmatch(r"(\d+)\s*(m|min|h|hr|d|day|w|week)", normalized)
    if not match:
        raise ValueError("shadow_horizon_unsupported")
    amount = int(match.group(1))
    if amount <= 0:
        raise ValueError("shadow_horizon_non_positive")
    units = match.group(2)
    multiplier = {
        "m": 60,
        "min": 60,
        "h": 3600,
        "hr": 3600,
        "d": 86_400,
        "day": 86_400,
        "w": 604_800,
        "week": 604_800,
    }[units]
    return amount * multiplier
