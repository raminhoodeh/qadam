"""Prove all-lane reachability without creating a broker write."""

from __future__ import annotations

from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_evidence_contracts import validate_lane_contribution
from orchestrator.qadam_qualitative_common import (
    LANE_CONTRIBUTIONS_ARTIFACT,
    LANE_REACHABILITY_ARTIFACT,
    now_iso,
    public_authority,
    read_jsonl,
    runtime_dir,
)
from orchestrator.qadam_tradeability_reliability import (
    build_and_write_golden_journeys,
    build_and_write_reachability_canary,
)


def _ids(rows: list[dict[str, Any]], key: str) -> set[str]:
    return {str(row.get(key)) for row in rows if row.get(key)}


def build_lane_reachability(
    settings: Settings | None = None,
    *,
    ensure_same_generation: bool = True,
) -> tuple[dict[str, Any], list[str]]:
    if ensure_same_generation:
        # A validator must not depend on the order in which other checks last ran.
        # Rebuild the canonical A4 dependency chain before reading its artifacts.
        from orchestrator.qadam_lane_trigger_fast_path import run_lane_trigger_fast_path

        run_lane_trigger_fast_path(settings, allow_network=False)
    runtime = runtime_dir(settings)
    contributions = read_jsonl(runtime / LANE_CONTRIBUTIONS_ARTIFACT)
    envelopes = read_jsonl(runtime / "qadam_tradeability_envelopes.jsonl")
    akber = read_jsonl(runtime / "qadam_akber_filter_v3_results.jsonl")
    shadow = read_jsonl(runtime / "qadam_forward_shadow_decisions.jsonl")
    router = read_jsonl(runtime / "qadam_router_v3_decisions.jsonl")
    golden, golden_checks, golden_errors = build_and_write_golden_journeys(settings)
    canary, canary_checks, canary_errors = build_and_write_reachability_canary(settings)

    errors: list[str] = []
    for contribution in contributions:
        errors.extend(validate_lane_contribution(contribution))
    a4 = [
        row
        for row in contributions
        if row.get("authority_tier") == "A4"
        and row.get("contribution_state") == "paper_review_nominated"
        and isinstance(row.get("canonical_draft"), dict)
    ]
    hypothesis_ids = {
        str(row["canonical_draft"].get("hypothesis_id"))
        for row in a4
        if row["canonical_draft"].get("hypothesis_id")
    }
    envelope_ids = {
        str((row.get("identity") or {}).get("hypothesis_id") or row.get("hypothesis_id"))
        for row in envelopes
    }
    akber_ids = _ids(akber, "hypothesis_id")
    shadow_ids = _ids(shadow, "hypothesis_id")
    router_ids = _ids(router, "hypothesis_id")

    missing_envelope = sorted(hypothesis_ids - envelope_ids)
    missing_akber = sorted(hypothesis_ids - akber_ids)
    missing_router = sorted(hypothesis_ids - router_ids)
    if missing_envelope:
        errors.append("a4_nomination_missing_canonical_envelope")
    if missing_akber:
        errors.append("a4_nomination_missing_akber_disposition")
    if missing_router:
        errors.append("a4_nomination_missing_router_disposition")
    if golden_checks.get("status") != "passed":
        errors.extend(golden_errors or ["lane_golden_journeys_not_passed"])
    if canary_checks.get("status") != "passed":
        errors.extend(canary_errors or ["broker_disabled_reachability_not_passed"])

    unique_errors = sorted(set(errors))
    payload = {
        "schema_version": "qadam_lane_reachability.v1",
        "artifact_type": "qadam_lane_reachability_canary",
        "generated_at": now_iso(),
        "status": "passed" if not unique_errors else "blocked",
        "a4_nomination_count": len(a4),
        "a4_hypothesis_ids": sorted(hypothesis_ids),
        "a4_reached_envelope_count": len(hypothesis_ids & envelope_ids),
        "a4_reached_akber_count": len(hypothesis_ids & akber_ids),
        "a4_reached_shadow_count": len(hypothesis_ids & shadow_ids),
        "a4_reached_router_count": len(hypothesis_ids & router_ids),
        "a4_router_disposition_required": True,
        "a4_router_pass_required": False,
        "golden_journey_status": golden.get("status"),
        "golden_journey_count": golden.get("journey_count", 0),
        "golden_journey_passed_count": golden.get("passed_count", 0),
        "broker_disabled_canary_status": canary.get("status"),
        "accepted_broker_disabled_handoff_count": canary_checks.get(
            "accepted_broker_disabled_handoff_count", 0
        ),
        "real_current_paperops_handoff_count": sum(
            row.get("paperops_handoff_allowed") is True for row in router
        ),
        "test_namespace_only": True,
        "broker_disabled": True,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "validation_errors": unique_errors,
        "authority": public_authority(),
    }
    AtomicArtifactStore(runtime).write_json(LANE_REACHABILITY_ARTIFACT, payload)
    return payload, unique_errors


__all__ = ["build_lane_reachability"]
