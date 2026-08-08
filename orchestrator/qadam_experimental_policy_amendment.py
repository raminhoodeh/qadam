"""Audited in-place amendment for Qadam's active experimental paper policy.

The amendment preserves the existing paper epoch and real trial calendar. It
does not recreate a launch approval, authorize an order, or enable live capital.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

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

SCHEMA_VERSION = "qadam_experimental_policy_amendment.v3"
AMENDMENT_ARTIFACT = "qadam_experimental_policy_amendment.json"
AMENDMENT_HISTORY_ARTIFACT = "qadam_experimental_policy_amendment_history.jsonl"
POLICY_HISTORY_ARTIFACT = "qadam_experimental_paper_policy_history.jsonl"


def build_policy_amendment(
    *,
    previous_policy: Mapping[str, Any],
    amended_policy: Mapping[str, Any],
    release_approval: Mapping[str, Any],
    paper_epoch: Mapping[str, Any],
    trial_calendar: Mapping[str, Any],
    previous_approval_sha256: str | None,
    explicit_operator_approval: bool,
    previous_amendment: Mapping[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated = generated_at or now_iso()
    launch_version = str(release_approval.get("policy_version") or "")
    previous_version = str(previous_policy.get("policy_version") or "")
    supersedes_version = previous_version if previous_version != launch_version else None
    supersedes_amendment_id = (
        str((previous_amendment or {}).get("amendment_id") or "") or None
        if supersedes_version
        else None
    )
    epoch_id = str(paper_epoch.get("paper_epoch_id") or "")
    trial_started_at = str(trial_calendar.get("trial_started_at") or "")
    prior_policy_chain_valid = bool(
        not supersedes_version
        or (
            previous_amendment
            and previous_amendment.get("operator_approved") is True
            and previous_amendment.get("to_policy_version") == previous_version
            and previous_amendment.get("from_policy_version") == launch_version
            and previous_amendment.get("paper_epoch_id") == epoch_id
            and previous_amendment.get("trial_started_at") == trial_started_at
        )
    )
    approved = bool(
        explicit_operator_approval
        and prior_policy_chain_valid
        and release_approval.get("experimental_paper_mandate_approved") is True
        and release_approval.get("live_capital_release") is False
        and release_approval.get("paper_epoch_id") == epoch_id
        and launch_version
        and paper_epoch.get("experimental_paper_release_policy_version")
        == launch_version
        and paper_epoch.get("paper_growth_trial_started_at") == trial_started_at
        and trial_calendar.get("backfill_used") is False
        and trial_calendar.get("simulated_elapsed_time_used") is False
        and amended_policy.get("policy_version") == POLICY_VERSION
        and not validate_policy(amended_policy)
    )
    binding = {
        "from_policy_version": launch_version,
        "to_policy_version": amended_policy.get("policy_version"),
        "supersedes_policy_version": supersedes_version,
        "supersedes_amendment_id": supersedes_amendment_id,
        "superseded_policy_sha256": (
            sha256_json(previous_policy) if supersedes_version else None
        ),
        "paper_epoch_id": epoch_id,
        "trial_started_at": trial_started_at,
        "previous_release_approval_sha256": previous_approval_sha256,
        "portfolio_policy_version": amended_policy.get("risk", {}).get(
            "portfolio_policy_version"
        ),
        "discovery_micro_trade_ceiling_usd": amended_policy.get("risk", {}).get(
            "discovery_micro_trade_ceiling_usd"
        ),
        "maximum_concurrent_discovery_micro_positions": amended_policy.get(
            "risk", {}
        ).get("maximum_concurrent_discovery_micro_positions"),
        "discovery_micro_admission_digest": sha256_json(
            amended_policy.get("discovery_micro_admission", {})
        ),
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
    policy_history: Iterable[Mapping[str, Any]] = (),
) -> list[str]:
    errors: list[str] = []
    from_version = str(release_approval.get("policy_version") or "")
    epoch_id = str(paper_epoch.get("paper_epoch_id") or "")
    trial_started_at = str(trial_calendar.get("trial_started_at") or "")
    binding = {
        "from_policy_version": from_version,
        "to_policy_version": policy.get("policy_version"),
        "supersedes_policy_version": amendment.get("supersedes_policy_version"),
        "supersedes_amendment_id": amendment.get("supersedes_amendment_id"),
        "superseded_policy_sha256": amendment.get("superseded_policy_sha256"),
        "paper_epoch_id": epoch_id,
        "trial_started_at": trial_started_at,
        "previous_release_approval_sha256": previous_approval_sha256,
        "portfolio_policy_version": policy.get("risk", {}).get(
            "portfolio_policy_version"
        ),
        "discovery_micro_trade_ceiling_usd": policy.get("risk", {}).get(
            "discovery_micro_trade_ceiling_usd"
        ),
        "maximum_concurrent_discovery_micro_positions": policy.get("risk", {}).get(
            "maximum_concurrent_discovery_micro_positions"
        ),
        "discovery_micro_admission_digest": sha256_json(
            policy.get("discovery_micro_admission", {})
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
    supersedes_version = amendment.get("supersedes_policy_version")
    if supersedes_version:
        matching_history = [
            record
            for record in policy_history
            if record.get("policy_version") == supersedes_version
            and sha256_json(record) == amendment.get("superseded_policy_sha256")
        ]
        if not amendment.get("supersedes_amendment_id"):
            errors.append("experimental_policy_amendment_predecessor_missing")
        if not matching_history:
            errors.append("experimental_policy_amendment_predecessor_policy_missing")
        if supersedes_version == policy.get("policy_version"):
            errors.append("experimental_policy_amendment_self_supersession")
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
    "POLICY_HISTORY_ARTIFACT",
    "SCHEMA_VERSION",
    "build_policy_amendment",
    "validate_policy_amendment",
]
