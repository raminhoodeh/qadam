"""Same-generation dependency chain for active A4 paper-review nominations."""

from __future__ import annotations

from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_akber_filter_v3 import build_and_write_akber_filter_v3
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_forward_shadow import build_and_write_forward_shadow
from orchestrator.qadam_lane_conversion import build_lane_conversion
from orchestrator.qadam_qualitative_common import (
    LANE_FAST_PATH_ARTIFACT,
    now_iso,
    public_authority,
    runtime_dir,
)
from orchestrator.qadam_router_v3_paperops import build_and_write_router_v3
from orchestrator.qadam_tradeability_pipeline import build_and_write_tradeability_pipeline


def run_lane_trigger_fast_path(
    settings: Settings | None = None,
    *,
    allow_network: bool = False,
) -> tuple[dict[str, Any], list[str]]:
    conversion, conversion_errors = build_lane_conversion(settings)
    a4_count = int(conversion["funnel"].get("a4_nomination_count") or 0)
    stages: list[dict[str, Any]] = []
    errors = list(conversion_errors)
    if a4_count:
        pipeline, pipeline_checks, pipeline_errors = build_and_write_tradeability_pipeline(settings)
        stages.append({"stage": "canonical_tradeability", "status": pipeline_checks.get("status"), "count": pipeline_checks.get("envelope_count")})
        errors.extend(pipeline_errors)
        akber, akber_checks, akber_errors = build_and_write_akber_filter_v3(settings)
        stages.append({"stage": "akber", "status": akber_checks.get("status"), "count": akber_checks.get("result_count")})
        errors.extend(akber_errors)
        shadow, shadow_checks, shadow_errors = build_and_write_forward_shadow(settings, allow_network=allow_network, supervised_cycle=False)
        stages.append({"stage": "forward_shadow", "status": shadow_checks.get("status"), "count": shadow_checks.get("decision_count")})
        errors.extend(shadow_errors)
        router, router_checks, router_errors = build_and_write_router_v3(settings)
        stages.append({"stage": "router", "status": router_checks.get("status"), "count": router_checks.get("decision_count")})
        errors.extend(router_errors)
    status = {
        "schema_version": "qadam_lane_trigger_fast_path.v1",
        "artifact_type": "qadam_lane_trigger_fast_path_status",
        "generated_at": now_iso(),
        "status": "completed" if a4_count and not errors else "completed_with_typed_holds" if a4_count else "idle_no_a4_nomination",
        "a4_nomination_count": a4_count,
        "same_generation_chain_invoked": bool(a4_count),
        "network_requested": allow_network,
        "stages": stages,
        "validation_errors": sorted(set(errors)),
        "direct_broker_call_made": False,
        "paper_order_created_by_fast_path": False,
        "authority": public_authority(),
    }
    AtomicArtifactStore(runtime_dir(settings)).write_json(LANE_FAST_PATH_ARTIFACT, status)
    return status, sorted(set(errors))


__all__ = ["run_lane_trigger_fast_path"]
