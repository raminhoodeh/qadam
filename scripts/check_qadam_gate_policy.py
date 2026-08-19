#!/usr/bin/env python3
# ruff: noqa: E402
"""Validate CATC evidence-fit gates and bounded soft-evidence haircuts."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_gate_policy import evaluate_gate_inputs, load_gate_policy, resolved_profile
from orchestrator.qadam_operator_ready_common import now_iso, runtime_dir, write_json_atomic


def main() -> int:
    policy = load_gate_policy()
    producers = policy.get("measurement_producers") or {}
    errors = []
    profile_results = {}
    for profile_id in policy.get("profiles", {}):
        profile = resolved_profile(profile_id)
        missing_producers = [
            rule
            for rule in [*profile.get("hard_rules", []), *(profile.get("soft_rules") or {})]
            if rule not in producers
        ]
        if missing_producers:
            errors.extend(f"measurement_producer_missing:{profile_id}:{rule}" for rule in missing_producers)
        measurements = {rule: True for rule in profile.get("hard_rules", [])}
        measurements.update({rule: None for rule in (profile.get("soft_rules") or {})})
        decisions, multiplier = evaluate_gate_inputs(
            profile_id, measurements, decision_id=f"gate-policy-check:{profile_id}"
        )
        if any(row.severity.value == "soft" and row.state.value == "veto" for row in decisions):
            errors.append(f"soft_rule_vetoed:{profile_id}")
        if not 0 < multiplier <= 1:
            errors.append(f"size_multiplier_invalid:{profile_id}:{multiplier}")
        profile_results[profile_id] = {
            "hard_rule_count": len(profile.get("hard_rules", [])),
            "soft_rule_count": len(profile.get("soft_rules") or {}),
            "all_soft_missing_size_multiplier": multiplier,
            "base_notional_ceiling_usd": profile.get("base_notional_ceiling_usd"),
        }
    if policy.get("threshold_mutation_authority") != "none":
        errors.append("threshold_mutation_authority_enabled")
    if policy.get("automatic_live_promotion_allowed") is not False:
        errors.append("automatic_live_promotion_enabled")
    payload = {
        "schema_version": "qadam_gate_policy_checks.v1",
        "artifact_type": "qadam_gate_policy_checks",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "profiles": profile_results,
        "validation_errors": errors,
        "hard_safety_weakened": False,
        "soft_evidence_absence_veto_count": 0,
        "maximum_paper_notional_usd": max(
            int(row.get("base_notional_ceiling_usd") or 0)
            for row in profile_results.values()
        ),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
    }
    write_json_atomic(runtime_dir() / "qadam_gate_policy_checks.json", payload)
    print(f"qadam_gate_policy_status={payload['status']}")
    print(f"profile_count={len(profile_results)}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
