"""One ordered qualitative-evidence pipeline feeding Qadam's canonical compiler."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_agent_reach_sandbox import (
    build_agent_reach_baseline,
    build_agent_reach_sandbox,
)
from orchestrator.qadam_external_acquisition import run_external_acquisition
from orchestrator.qadam_external_evidence_lake import build_external_evidence_lake
from orchestrator.qadam_external_origin_registry import build_external_origin_state
from orchestrator.qadam_functional_specialist_challenge import run_functional_specialist_challenge
from orchestrator.qadam_lane_conversion import build_lane_conversion
from orchestrator.qadam_lane_trigger_fast_path import run_lane_trigger_fast_path
from orchestrator.qadam_prediction_market_research import build_prediction_market_research
from orchestrator.qadam_qualitative_akber_bridge import build_qualitative_akber_bridge
from orchestrator.qadam_qualitative_claim_extraction import extract_qualitative_claims
from orchestrator.qadam_qualitative_evidence_graph import build_qualitative_evidence_graph
from orchestrator.qadam_qualitative_history import build_qualitative_history
from orchestrator.qadam_qualitative_pattern_lab import run_qualitative_pattern_lab
from orchestrator.qadam_qualitative_strategy_bridge import build_qualitative_strategy_bridge
from orchestrator.qadam_qualitative_common import now_iso, public_authority


StageFunction = Callable[[], tuple[Any, list[str]]]


def _stage(name: str, function: StageFunction) -> tuple[dict[str, Any], list[str]]:
    try:
        result, errors = function()
    except Exception as exc:  # The operator converts failures into repair records.
        return {
            "stage": name,
            "status": "failed",
            "error_class": type(exc).__name__,
            "error": str(exc),
        }, [f"{name}:{type(exc).__name__}:{exc}"]
    status = "passed" if not errors else "blocked"
    if isinstance(result, dict):
        status = str(
            result.get("status")
            or (result.get("summary") or {}).get("status")
            or (result.get("coverage") or {}).get("status")
            or status
        )
    return {
        "stage": name,
        "status": status,
        "validation_error_count": len(errors),
    }, list(errors)


def run_qualitative_evidence_pipeline(
    settings: Settings | None = None,
    *,
    allow_network: bool = False,
    run_fast_path: bool = True,
) -> tuple[dict[str, Any], list[str]]:
    stages: list[dict[str, Any]] = []
    errors: list[str] = []
    functions: list[tuple[str, StageFunction]] = [
        ("baseline", lambda: build_agent_reach_baseline(settings)),
        ("sandbox", lambda: build_agent_reach_sandbox(settings)),
        ("origins", lambda: build_external_origin_state(settings)),
        (
            "acquisition",
            lambda: run_external_acquisition(
                settings,
                allow_network=allow_network,
            ),
        ),
        ("evidence_lake", lambda: build_external_evidence_lake(settings)),
        ("claim_extraction", lambda: extract_qualitative_claims(settings)),
        ("claim_challenge", lambda: run_functional_specialist_challenge(settings)),
        ("temporal_graph", lambda: build_qualitative_evidence_graph(settings)),
        ("forward_labels", lambda: build_qualitative_history(settings)),
        ("pattern_lab", lambda: run_qualitative_pattern_lab(settings)),
        ("prediction_market", lambda: build_prediction_market_research(settings)),
        ("strategy_bridge", lambda: build_qualitative_strategy_bridge(settings)),
        ("akber_bridge", lambda: build_qualitative_akber_bridge(settings)),
        ("lane_conversion", lambda: build_lane_conversion(settings)),
    ]
    if run_fast_path:
        functions.append(
            (
                "same_generation_fast_path",
                lambda: run_lane_trigger_fast_path(
                    settings,
                    allow_network=allow_network,
                ),
            )
        )
    for name, function in functions:
        record, stage_errors = _stage(name, function)
        stages.append(record)
        errors.extend(stage_errors)

    unique_errors = sorted(set(errors))
    payload = {
        "schema_version": "qadam_qualitative_evidence_pipeline.v1",
        "artifact_type": "qadam_qualitative_evidence_pipeline_run",
        "generated_at": now_iso(),
        "status": "passed" if not unique_errors else "completed_with_typed_blocks",
        "network_enabled": allow_network,
        "fast_path_enabled": run_fast_path,
        "stage_count": len(stages),
        "stages": stages,
        "validation_errors": unique_errors,
        "direct_broker_call_made": False,
        "paper_order_created_count": 0,
        "authority": public_authority(),
    }
    return payload, unique_errors


__all__ = ["run_qualitative_evidence_pipeline"]
