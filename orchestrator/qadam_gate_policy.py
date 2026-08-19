"""Evidence-fit hard, soft, and diagnostic gate policy."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from orchestrator.qadam_decision_transaction import GateDecision, GateSeverity, GateState

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "config" / "qadam_gate_policy.json"


def load_gate_policy() -> dict[str, Any]:
    payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if payload.get("paper_only") is not True or payload.get("live_capital_enabled") is not False:
        raise ValueError("unsafe_gate_policy_boundary")
    return payload


def resolved_profile(profile_id: str) -> dict[str, Any]:
    policy = load_gate_policy()
    profiles = policy.get("profiles", {})
    profile = dict(profiles.get(profile_id) or {})
    parent_id = profile.pop("inherits", None)
    if parent_id:
        parent = dict(profiles.get(parent_id) or {})
        parent_soft = dict(parent.get("soft_rules") or {})
        parent_soft.update(profile.get("soft_rules") or {})
        parent.update(profile)
        parent["soft_rules"] = parent_soft
        profile = parent
    if not profile:
        raise ValueError(f"unknown_gate_profile:{profile_id}")
    return profile


def evaluate_gate_inputs(
    profile_id: str,
    measurements: Mapping[str, Any],
    *,
    decision_id: str,
) -> tuple[list[GateDecision], float]:
    """Evaluate declared measurements without inventing missing evidence."""

    profile = resolved_profile(profile_id)
    decisions: list[GateDecision] = []
    multiplier = 1.0
    sequence = 0
    for rule in profile.get("hard_rules", []):
        raw = measurements.get(rule)
        state = GateState.PASS if raw is True else GateState.VETO if raw is False else GateState.HOLD
        decisions.append(
            GateDecision(
                gate_decision_id=f"{decision_id}:hard:{rule}",
                gate_name=str(rule),
                sequence=sequence,
                state=state,
                severity=GateSeverity.HARD,
                measured_value=raw if isinstance(raw, (float, int, str, bool)) else None,
                threshold=True,
                explanation=(
                    f"Required safety or tradeability condition '{rule}' passed."
                    if state == GateState.PASS
                    else f"Required safety or tradeability condition '{rule}' is not satisfied."
                ),
                size_haircut=1.0,
            )
        )
        sequence += 1
    for rule, haircut in (profile.get("soft_rules") or {}).items():
        raw = measurements.get(rule)
        present = raw is True
        applied = 1.0 if present else float(haircut)
        multiplier *= applied
        decisions.append(
            GateDecision(
                gate_decision_id=f"{decision_id}:soft:{rule}",
                gate_name=str(rule),
                sequence=sequence,
                state=GateState.PASS if present else GateState.HOLD,
                severity=GateSeverity.SOFT,
                measured_value=raw if isinstance(raw, (float, int, str, bool)) else None,
                threshold=True,
                explanation=(
                    f"Optional confirmation '{rule}' is present."
                    if present
                    else f"Optional confirmation '{rule}' is absent; size is reduced, not vetoed."
                ),
                size_haircut=applied,
            )
        )
        sequence += 1
    multiplier = max(float(profile.get("minimum_size_multiplier", 0.0)), multiplier)
    return decisions, round(multiplier, 6)


def hard_gate_failures(decisions: list[GateDecision]) -> list[str]:
    return [
        decision.gate_name
        for decision in decisions
        if decision.severity == GateSeverity.HARD and decision.state != GateState.PASS
    ]


__all__ = [
    "evaluate_gate_inputs",
    "hard_gate_failures",
    "load_gate_policy",
    "resolved_profile",
]
