"""Stable owner alias for Qadam's blinded functional specialist challenges.

The specialists challenge a grounded claim from distinct functional viewpoints.
Their outputs are advisory model records, never independent source evidence.
"""

from __future__ import annotations

from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_qualitative_claim_challenge import (
    PERSPECTIVES,
    challenge_qualitative_claims,
)


def run_functional_specialist_challenge(
    settings: Settings | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    return challenge_qualitative_claims(settings)


__all__ = ["PERSPECTIVES", "run_functional_specialist_challenge"]
