"""Certify one typed contribution and disposition path for every Qadam lane."""

from __future__ import annotations

from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_evidence_contracts import (
    build_lane_contribution,
    lane_capability_index,
    validate_lane_contribution,
)
from orchestrator.qadam_lane_reachability import build_lane_reachability
from orchestrator.qadam_qualitative_common import (
    ALL_LANE_CERTIFICATION_ARTIFACT,
    LANE_AUTHORITY_ARTIFACT,
    LANE_BLOCKERS_ARTIFACT,
    LANE_CONTRIBUTIONS_ARTIFACT,
    LANE_FAST_PATH_ARTIFACT,
    LANE_FUNNEL_ARTIFACT,
    now_iso,
    public_authority,
    read_json,
    read_jsonl,
    runtime_dir,
)


def build_all_lane_conversion_certification(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    capabilities = lane_capability_index()
    reachability, reachability_errors = build_lane_reachability(settings)
    # Reachability converges the complete A4 chain. Read all mutable contracts
    # afterwards so this certificate describes one coherent generation.
    inventory = read_json(runtime / LANE_AUTHORITY_ARTIFACT)
    contributions = read_jsonl(runtime / LANE_CONTRIBUTIONS_ARTIFACT)
    funnel = read_json(runtime / LANE_FUNNEL_ARTIFACT)
    blockers = read_json(runtime / LANE_BLOCKERS_ARTIFACT)
    fast_path = read_json(runtime / LANE_FAST_PATH_ARTIFACT)
    errors = list(reachability_errors)

    capability_probe_errors: list[str] = []
    capability_probes = []
    state_by_tier = {
        "A0": "observed",
        "A1": "evidence_qualified",
        "A2": "pattern_nominated",
        "A3": "strategy_nominated",
        "A4": "paper_review_nominated",
        "A5": "held",
        "A6": "held",
    }
    for lane_id, capability in sorted(capabilities.items()):
        tier = str(capability.get("maximum_authority") or "")
        draft = (
            {"hypothesis_id": f"contract-probe:{lane_id}", "contract_probe_only": True}
            if tier in {"A3", "A4"}
            else None
        )
        probe = build_lane_contribution(
            lane_id=lane_id,
            contribution_state=state_by_tier.get(tier, "held"),
            authority_tier=tier,
            evidence_profile=str((capability.get("evidence_profiles") or ["contract_probe"])[0]),
            subject={"contract_probe_only": True, "lane_id": lane_id},
            evidence_refs=[f"contract-probe-evidence:{lane_id}"],
            generation_id=f"contract-probe-generation:{lane_id}",
            observed_at=now_iso(),
            expires_at=None,
            canonical_draft=draft,
        )
        probe_errors = validate_lane_contribution(probe)
        capability_probe_errors.extend(
            f"{lane_id}:{error}" for error in probe_errors
        )
        capability_probes.append(
            {
                "lane_id": lane_id,
                "maximum_authority": tier,
                "status": "passed" if not probe_errors else "blocked",
                "validation_errors": probe_errors,
            }
        )
    errors.extend(capability_probe_errors)

    if len(capabilities) != int(inventory.get("lane_count") or 0):
        errors.append("lane_inventory_count_mismatch")
    for contribution in contributions:
        errors.extend(validate_lane_contribution(contribution))
    if int(funnel.get("ownerless_blocker_count") or 0) != 0:
        errors.append("ownerless_lane_blocker_detected")
    if int(funnel.get("schema_invalid_contribution_count") or 0) != 0:
        errors.append("invalid_lane_contribution_detected")
    if fast_path.get("direct_broker_call_made") is not False:
        errors.append("lane_fast_path_direct_broker_call")
    if int(fast_path.get("paper_order_created_by_fast_path") or 0) != 0:
        errors.append("lane_fast_path_created_order")
    if reachability.get("status") != "passed":
        errors.append("lane_reachability_not_passed")
    if any(
        bool((row.get("authority") or {}).get("broker_write_allowed"))
        for row in contributions
    ):
        errors.append("research_lane_broker_authority_detected")

    lane_states = []
    contribution_by_lane: dict[str, list[dict[str, Any]]] = {}
    for row in contributions:
        contribution_by_lane.setdefault(str(row.get("lane_id")), []).append(row)
    blocker_rows = blockers.get("blockers") or []
    blocker_by_lane: dict[str, list[dict[str, Any]]] = {}
    for row in blocker_rows:
        if isinstance(row, dict):
            blocker_by_lane.setdefault(str(row.get("lane_id")), []).append(row)
    for lane_id, capability in sorted(capabilities.items()):
        rows = contribution_by_lane.get(lane_id, [])
        lane_states.append(
            {
                "lane_id": lane_id,
                "owner": capability.get("owner"),
                "implementation_state": capability.get("state"),
                "maximum_authority": capability.get("maximum_authority"),
                "contribution_count": len(rows),
                "current_contribution_states": sorted(
                    {str(row.get("contribution_state")) for row in rows}
                ),
                "typed_blocker_count": len(blocker_by_lane.get(lane_id, [])),
                "direct_broker_authority": False,
            }
        )

    unique_errors = sorted(set(errors))
    payload = {
        "schema_version": "qadam_all_lane_conversion_certification.v1",
        "artifact_type": "qadam_all_lane_conversion_certification",
        "generated_at": now_iso(),
        "status": "passed" if not unique_errors else "blocked",
        "implementation_complete": not unique_errors,
        "lane_count": len(capabilities),
        "implemented_lane_count": sum(
            str(row.get("implementation_state") or "").startswith("implemented")
            for row in lane_states
        ),
        "capability_probe_count": len(capability_probes),
        "capability_probe_passed_count": sum(
            row["status"] == "passed" for row in capability_probes
        ),
        "capability_probes": capability_probes,
        "current_contribution_count": len(contributions),
        "a4_nomination_count": int(funnel.get("a4_nomination_count") or 0),
        "same_generation_fast_path_status": fast_path.get("status"),
        "reachability_status": reachability.get("status"),
        "accepted_broker_disabled_handoff_count": reachability.get(
            "accepted_broker_disabled_handoff_count", 0
        ),
        "one_canonical_tradeability_compiler": True,
        "lane_states": lane_states,
        "validation_errors": unique_errors,
        "authority": public_authority(),
    }
    AtomicArtifactStore(runtime).write_json(ALL_LANE_CERTIFICATION_ARTIFACT, payload)
    return payload, unique_errors


__all__ = ["build_all_lane_conversion_certification"]
