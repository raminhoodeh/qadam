"""Audited in-place amendment for Qadam's active experimental paper policy.

The amendment preserves the existing paper epoch and real trial calendar. It
does not recreate a launch approval, authorize an order, or enable live capital.
"""

from __future__ import annotations

from typing import Any, Mapping

from orchestrator.qadam_experimental_paper_policy import (
    DISCOVERY_MICRO_TIER,
    POLICY_VERSION,
    validate_policy,
)
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    sha256_json,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_wave_b_common import stable_id

SCHEMA_VERSION = "qadam_experimental_policy_amendment.v1"
AMENDMENT_ARTIFACT = "qadam_experimental_policy_amendment.json"
AMENDMENT_HISTORY_ARTIFACT = "qadam_experimental_policy_amendment_history.jsonl"


def build_policy_amendment(
    *,
    previous_policy: Mapping[str, Any],
    amended_policy: Mapping[str, Any],
    release_approval: Mapping[str, Any],
    paper_epoch: Mapping[str, Any],
    trial_calendar: Mapping[str, Any],
    previous_approval_sha256: str | None,
    explicit_operator_approval: bool,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated = generated_at or now_iso()
    from_version = str(previous_policy.get("policy_version") or "")
    epoch_id = str(paper_epoch.get("paper_epoch_id") or "")
    trial_started_at = str(trial_calendar.get("trial_started_at") or "")
    approved = bool(
        explicit_operator_approval
        and release_approval.get("experimental_paper_mandate_approved") is True
        and release_approval.get("live_capital_release") is False
        and release_approval.get("paper_epoch_id") == epoch_id
        and release_approval.get("policy_version") == from_version
        and paper_epoch.get("experimental_paper_release_policy_version")
        == from_version
        and paper_epoch.get("paper_growth_trial_started_at") == trial_started_at
        and trial_calendar.get("backfill_used") is False
        and trial_calendar.get("simulated_elapsed_time_used") is False
        and amended_policy.get("policy_version") == POLICY_VERSION
        and not validate_policy(amended_policy)
    )
    binding = {
        "from_policy_version": from_version,
        "to_policy_version": amended_policy.get("policy_version"),
        "paper_epoch_id": epoch_id,
        "trial_started_at": trial_started_at,
        "previous_release_approval_sha256": previous_approval_sha256,
        "discovery_micro_trade_ceiling_usd": amended_policy.get("risk", {}).get(
            "discovery_micro_trade_ceiling_usd"
        ),
        "maximum_concurrent_discovery_micro_positions": amended_policy.get(
            "risk", {}
        ).get("maximum_concurrent_discovery_micro_positions"),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_experimental_policy_amendment",
        "generated_at": generated,
        "status": "operator_approved" if approved else "blocked",
        "amendment_id": stable_id("experimental-policy-amendment", binding),
        "explicit_operator_approval": explicit_operator_approval,
        "operator_approved": approved,
        "binding_digest": sha256_json(binding),
        **binding,
        "experimental_tier_added": DISCOVERY_MICRO_TIER,
        "paper_route": amended_policy.get("route", {}).get("required"),
        "paper_trial_calendar_preserved": True,
        "paper_trial_calendar_reset": False,
        "paper_trial_calendar_advanced": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_granted_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }


def validate_policy_amendment(
    amendment: Mapping[str, Any],
    *,
    policy: Mapping[str, Any],
    release_approval: Mapping[str, Any],
    paper_epoch: Mapping[str, Any],
    trial_calendar: Mapping[str, Any],
    previous_approval_sha256: str | None,
) -> list[str]:
    errors: list[str] = []
    from_version = str(release_approval.get("policy_version") or "")
    epoch_id = str(paper_epoch.get("paper_epoch_id") or "")
    trial_started_at = str(trial_calendar.get("trial_started_at") or "")
    binding = {
        "from_policy_version": from_version,
        "to_policy_version": policy.get("policy_version"),
        "paper_epoch_id": epoch_id,
        "trial_started_at": trial_started_at,
        "previous_release_approval_sha256": previous_approval_sha256,
        "discovery_micro_trade_ceiling_usd": policy.get("risk", {}).get(
            "discovery_micro_trade_ceiling_usd"
        ),
        "maximum_concurrent_discovery_micro_positions": policy.get("risk", {}).get(
            "maximum_concurrent_discovery_micro_positions"
        ),
    }
    if amendment.get("status") != "operator_approved":
        errors.append("experimental_policy_amendment_not_approved")
    if amendment.get("explicit_operator_approval") is not True:
        errors.append("experimental_policy_amendment_explicit_approval_missing")
    if amendment.get("operator_approved") is not True:
        errors.append("experimental_policy_amendment_operator_approval_missing")
    for field, expected in binding.items():
        if amendment.get(field) != expected:
            errors.append(f"experimental_policy_amendment_binding_changed:{field}")
    if amendment.get("binding_digest") != sha256_json(binding):
        errors.append("experimental_policy_amendment_digest_changed")
    if paper_epoch.get("experimental_paper_release_policy_version") != from_version:
        errors.append("experimental_policy_amendment_epoch_origin_changed")
    if paper_epoch.get("paper_growth_trial_started_at") != trial_started_at:
        errors.append("experimental_policy_amendment_trial_start_changed")
    if amendment.get("paper_trial_calendar_reset") is not False:
        errors.append("experimental_policy_amendment_reset_calendar")
    if amendment.get("paper_trial_calendar_advanced") is not False:
        errors.append("experimental_policy_amendment_advanced_calendar")
    if trial_calendar.get("backfill_used") is not False or trial_calendar.get(
        "simulated_elapsed_time_used"
    ) is not False:
        errors.append("experimental_policy_amendment_calendar_fabricated")
    if amendment.get("paper_route") != "guarded_alpaca_paper_via_paperops":
        errors.append("experimental_policy_amendment_route_not_guarded")
    if amendment.get("live_capital_enabled") is not False:
        errors.append("experimental_policy_amendment_live_capital_enabled")
    for field in (
        "paper_order_created_count",
        "broker_write_count",
        "proof_credit_granted_count",
    ):
        if int(amendment.get(field) or 0) != 0:
            errors.append(f"experimental_policy_amendment_forbidden_count:{field}")
    errors.extend(validate_policy(policy))
    errors.extend(
        validate_authority(
            amendment.get("authority", {}), prefix="experimental_policy_amendment"
        )
    )
    return unique_errors(errors)


__all__ = [
    "AMENDMENT_ARTIFACT",
    "AMENDMENT_HISTORY_ARTIFACT",
    "SCHEMA_VERSION",
    "build_policy_amendment",
    "validate_policy_amendment",
]
