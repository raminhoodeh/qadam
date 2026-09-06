"""Explicit cost provenance for paper research; numeric presence is not measurement."""

import math
from typing import Any, Mapping


def cost_evidence(record: Mapping[str, Any]) -> dict[str, Any]:
    value = record.get("cost_bps")
    finite = isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0
    modelled = record.get("costs_are_modelled_not_live_execution_costs") is True
    measured = record.get("costs_measured") is True and bool(record.get("cost_measurement_source"))
    version = record.get("cost_model_version")
    if modelled and measured:
        state, reason = "unavailable", "conflicting_cost_provenance"
    elif finite and modelled and version:
        state, reason = "modelled", None
    elif finite and measured:
        state, reason = "measured", None
    else:
        state, reason = "unavailable", "missing_or_invalid_cost_provenance"
    return {"state": state, "cost_bps": value if finite else None,
            "cost_model_version": version, "cost_measurement_source": record.get("cost_measurement_source"),
            "reason": reason, "live_performance_proven": False}
