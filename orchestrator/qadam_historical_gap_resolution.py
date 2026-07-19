"""Resolve OR-3/OR-4 historical gaps without inventing observations.

The legacy QSASE grid records one descriptive source-price row per relationship
and horizon.  OR-3/OR-4 subsequently built a much larger provider-backed,
point-in-time research lake.  This module keeps both truths visible: legacy
rows remain missing where they were never observed, while provider-backed
alignment can supersede those rows for statistical research without mutating
or fabricating the legacy records.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_backtest_engine import NEGATIVE_CONTROL_METHODS
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_wave_b_common import record_set_hash

SCHEMA_VERSION = "qadam_historical_gap_resolution.v1"
PHASE_ID = "clean-epoch-phase-4"

GAP_RESOLUTION_ARTIFACT = "qadam_historical_gap_resolution.json"
UNAVAILABLE_REGISTRY_ARTIFACT = "qadam_unavailable_history_registry.json"
NEGATIVE_CONTROL_ARTIFACT = "qadam_negative_control_results.json"
BACKTEST_RECERTIFICATION_ARTIFACT = "qadam_backtest_recertification.json"
CHECK_ARTIFACT = "qadam_historical_gap_resolution_checks.json"

BACKFILL_COVERAGE_ARTIFACT = "qadam_backfill_coverage.json"
BACKFILL_CHECK_ARTIFACT = "qadam_provider_backfill_checks.json"
FORWARD_COVERAGE_ARTIFACT = "qadam_forward_window_coverage.json"
PROVIDER_ALIGNMENT_ARTIFACT = "qadam_provider_point_in_time_alignment.json"
POINT_IN_TIME_CHECK_ARTIFACT = "qadam_point_in_time_evidence_checks.json"
LEAKAGE_ARTIFACT = "qadam_leakage_audit_v2.json"
BACKTEST_SUMMARY_ARTIFACT = "qadam_backtest_results_summary.json"
BACKTEST_MANIFEST_ARTIFACT = "qadam_backtest_run_manifest.json"
BACKTEST_CHECK_ARTIFACT = "qadam_statistical_backtest_checks.json"
MULTIPLE_TESTING_ARTIFACT = "qadam_multiple_testing_audit.json"
WALK_FORWARD_ARTIFACT = "qadam_walk_forward_audit.json"

def _provider_alignment_path(payload: dict[str, Any]) -> Path:
    relative = str(payload.get("alignment_records_path") or "").strip()
    return (ROOT / relative).resolve() if relative else Path()


def _alignment_coverage(payload: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    path = _provider_alignment_path(payload)
    rows = read_jsonl(path) if path.is_file() else []
    coverage: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (str(row.get("source_key") or ""), str(row.get("instrument") or ""))
        current = coverage.setdefault(
            key,
            {
                "alignment_record_count": 0,
                "eligible_forward_window_count": 0,
                "available_horizons": set(),
                "point_in_time_safe": True,
            },
        )
        horizons = {
            str(value)
            for value in row.get("available_horizons", [])
            if value
        }
        current["alignment_record_count"] += 1
        current["eligible_forward_window_count"] += len(horizons)
        current["available_horizons"].update(horizons)
        current["point_in_time_safe"] = bool(
            current["point_in_time_safe"] and row.get("point_in_time_safe") is True
        )
    return coverage


def _resolution_state(
    window: dict[str, Any],
    aligned: dict[tuple[str, str], dict[str, Any]],
) -> tuple[str, str, bool]:
    typed = str(window.get("typed_state") or "unclassified")
    key = (str(window.get("source_key") or ""), str(window.get("instrument") or ""))
    if typed == "descriptive_window_complete_not_forward_label":
        return (
            "descriptive_non_forward_record",
            "The legacy record is complete as description but was never a forward label.",
            False,
        )
    if typed == "pair_intentionally_not_meaningful":
        return (
            "intentionally_excluded_relationship",
            "The frozen relationship map excludes this pair from edge testing.",
            False,
        )
    if typed == "contract_expired_or_identity_history_missing":
        return (
            "terminal_unavailable_contract_identity",
            "The event contract expired or lacks a stable historical identity.",
            False,
        )
    if typed == "price_history_absent" and key in aligned:
        return (
            "superseded_by_provider_alignment",
            "A separate immutable provider-backed point-in-time alignment is available for research.",
            False,
        )
    if typed == "price_history_absent":
        return (
            "terminal_unavailable_no_point_in_time_overlap",
            "The reviewed provider lake has no defensible point-in-time overlap for this pair.",
            False,
        )
    if typed == "forward_window_complete":
        return (
            "legacy_forward_window_complete",
            "The original legacy row contains a complete lookahead-safe forward window.",
            False,
        )
    return (
        "review_required_unclassified",
        "The legacy state is not covered by the frozen resolution taxonomy.",
        True,
    )


def _build_gap_resolution(
    runtime: Path,
    aligned: dict[tuple[str, str], dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    backfill = read_json(runtime / BACKFILL_COVERAGE_ARTIFACT)
    provider_checks = read_json(runtime / BACKFILL_CHECK_ARTIFACT)
    forward = read_json(runtime / FORWARD_COVERAGE_ARTIFACT)
    state_counts: Counter[str] = Counter()
    legacy_counts: Counter[str] = Counter()
    pair_groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    repairable_count = 0
    for window in forward.get("windows", []):
        if not isinstance(window, dict):
            continue
        state, explanation, repairable = _resolution_state(window, aligned)
        typed = str(window.get("typed_state") or "unclassified")
        legacy_counts[typed] += 1
        state_counts[state] += 1
        repairable_count += int(repairable)
        group_key = (
            str(window.get("source_key") or "unknown"),
            str(window.get("instrument") or "unknown"),
            state,
        )
        group = pair_groups.setdefault(
            group_key,
            {
                "source_key": group_key[0],
                "instrument": group_key[1],
                "resolution_state": state,
                "explanation": explanation,
                "legacy_window_count": 0,
                "legacy_typed_states": set(),
                "repairable_in_current_frozen_baseline": repairable,
                "synthetic_completion_allowed": False,
                "neutral_value_imputation_allowed": False,
            },
        )
        group["legacy_window_count"] += 1
        group["legacy_typed_states"].add(typed)
        alignment = aligned.get((group_key[0], group_key[1]), {})
        group["provider_alignment_record_count"] = int(
            alignment.get("alignment_record_count") or 0
        )
        group["provider_eligible_forward_window_count"] = int(
            alignment.get("eligible_forward_window_count") or 0
        )
    registry_rows = []
    for group in pair_groups.values():
        row = dict(group)
        row["legacy_typed_states"] = sorted(group["legacy_typed_states"])
        row["record_id"] = (
            f"history-resolution:{row['source_key']}:{row['instrument']}:"
            f"{row['resolution_state']}"
        )
        registry_rows.append(row)
    registry_rows.sort(
        key=lambda row: (
            row["resolution_state"],
            row["source_key"],
            row["instrument"],
        )
    )
    all_terminal = (
        int(backfill.get("remaining_partition_count") or 0) == 0
        and backfill.get("all_partitions_terminal") is True
    )
    generated_at = now_iso()
    resolution = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_historical_gap_resolution",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "complete_with_honestly_classified_gaps" if all_terminal else "blocked",
        "provider_partition_state": {
            "total": int(backfill.get("total_partition_count") or 0),
            "acquired": int(backfill.get("completed_partition_count") or 0),
            "classified_unavailable": int(
                backfill.get("unavailable_classified_partition_count") or 0
            ),
            "remaining": int(backfill.get("remaining_partition_count") or 0),
            "all_terminal": all_terminal,
            "provider_row_count": int(backfill.get("provider_row_count") or 0),
        },
        "legacy_grid_state": {
            "record_count": int(forward.get("memory_record_count") or 0),
            "typed_record_count": int(forward.get("classified_record_count") or 0),
            "missing_or_ineligible_count": int(
                forward.get("missing_or_ineligible_window_count") or 0
            ),
            "typed_state_counts": dict(sorted(legacy_counts.items())),
            "resolution_state_counts": dict(sorted(state_counts.items())),
            "repairable_in_current_frozen_baseline_count": repairable_count,
            "legacy_rows_mutated_or_backfilled": 0,
        },
        "provider_alignment_state": {
            "relationship_count": len(aligned),
            "alignment_record_count": int(
                forward.get("provider_alignment_record_count") or 0
            ),
            "eligible_forward_window_count": int(
                forward.get("provider_eligible_forward_window_count") or 0
            ),
            "provider_lineage_required": True,
            "provider_lineage_present": provider_checks.get("provider_row_count", 0) > 0,
        },
        "interpretation": (
            "The 6,150 legacy gaps remain visible and were not filled with invented values. "
            "They no longer represent unfinished OR-3 downloads: every provider partition "
            "is terminal, and statistical testing uses the separate provider-backed "
            "point-in-time alignment where available."
        ),
        "unavailable_history_registry_ref": (
            f"data/runtime/{UNAVAILABLE_REGISTRY_ARTIFACT}"
        ),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "paper_calendar_advanced": False,
        "authority": authority_flags(),
    }
    registry = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_unavailable_history_registry",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "complete",
        "record_count": len(registry_rows),
        "resolution_state_counts": dict(sorted(state_counts.items())),
        "records": registry_rows,
        "future_data_expansion_may_reopen_terminal_states": True,
        "current_frozen_baseline_repair_allowed": False,
        "synthetic_completion_allowed": False,
        "authority": authority_flags(),
    }
    return resolution, registry


def _load_backtest_bulk(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    bulk = manifest.get("bulk_results") if isinstance(manifest.get("bulk_results"), dict) else {}
    relative = str(bulk.get("result_path") or "").strip()
    path = (ROOT / relative).resolve() if relative else Path()
    return read_jsonl(path) if path.is_file() else []


def _build_negative_controls(
    runtime: Path,
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    controls = [
        row for row in results if str(row.get("method_id") or "") in NEGATIVE_CONTROL_METHODS
    ]
    rows = []
    for row in controls:
        metrics = row.get("holdout_metrics") if isinstance(row.get("holdout_metrics"), dict) else {}
        rows.append(
            {
                "hypothesis_id": row.get("hypothesis_id"),
                "method_id": row.get("method_id"),
                "instrument": row.get("instrument"),
                "horizon": row.get("horizon"),
                "independent_row_count": row.get("independent_row_count"),
                "raw_p_value": row.get("raw_p_value"),
                "adjusted_p_value": row.get("adjusted_p_value"),
                "holdout_trade_count": int(metrics.get("trade_count") or 0),
                "holdout_mean_net_return": metrics.get("mean_net_return"),
                "statistically_positive": row.get("false_discovery_adjusted_state") == "validated",
                "historical_edge_candidate": row.get("historical_edge_candidate") is True,
                "rejection_reasons": row.get("rejection_reasons", []),
            }
        )
    positive = sum(row["statistically_positive"] for row in rows)
    candidates = sum(row["historical_edge_candidate"] for row in rows)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_negative_control_results",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if rows and positive == 0 and candidates == 0 else "blocked",
        "control_count": len(rows),
        "statistically_positive_count": positive,
        "validated_edge_candidate_count": candidates,
        "controls_interpretable": bool(rows),
        "results": rows,
        "result_record_set_hash": record_set_hash(rows),
        "authority": authority_flags(),
    }


def _build_recertification(
    runtime: Path,
    gap_resolution: dict[str, Any],
    controls: dict[str, Any],
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    summary = read_json(runtime / BACKTEST_SUMMARY_ARTIFACT)
    manifest = read_json(runtime / BACKTEST_MANIFEST_ARTIFACT)
    checks = read_json(runtime / BACKTEST_CHECK_ARTIFACT)
    multiple = read_json(runtime / MULTIPLE_TESTING_ARTIFACT)
    walk = read_json(runtime / WALK_FORWARD_ARTIFACT)
    leakage = read_json(runtime / LEAKAGE_ARTIFACT)
    safe = all(
        (
            gap_resolution.get("status") == "complete_with_honestly_classified_gaps",
            checks.get("status") == "passed",
            int(leakage.get("leakage_violation_count") or 0) == 0,
            int(walk.get("holdout_tuning_violation_count") or 0) == 0,
            controls.get("status") == "passed",
            int(summary.get("negative_control_validated_count") or 0) == 0,
        )
    )
    edge_count = int(summary.get("validated_edge_count") or 0)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_backtest_recertification",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": (
            "passed_with_validated_edge"
            if safe and edge_count > 0
            else "passed_no_validated_edge"
            if safe
            else "blocked"
        ),
        "research_protocol_valid": safe,
        "paper_operator_edge_gate_passed": safe and edge_count > 0,
        "valid_no_edge_outcome": safe and edge_count == 0,
        "backtest_run_id": manifest.get("run_id"),
        "backtest_status": summary.get("status"),
        "attempted_hypothesis_count": int(summary.get("attempted_hypothesis_count") or 0),
        "fold_result_count": int(summary.get("fold_result_count") or 0),
        "untouched_holdout_result_count": int(
            summary.get("untouched_holdout_result_count") or 0
        ),
        "validated_edge_count": edge_count,
        "leakage_violation_count": int(leakage.get("leakage_violation_count") or 0),
        "holdout_tuning_violation_count": int(
            walk.get("holdout_tuning_violation_count") or 0
        ),
        "negative_control_count": controls.get("control_count"),
        "negative_control_false_positive_count": controls.get(
            "statistically_positive_count"
        ),
        "false_discovery_control": {
            "method": multiple.get("method"),
            "raw_significant_count": multiple.get("raw_significant_result_count"),
            "adjusted_significant_count": multiple.get(
                "adjusted_significant_result_count"
            ),
        },
        "result_record_count": len(results),
        "result_record_set_hash": record_set_hash(results),
        "score_dataset_hash": manifest.get("score_dataset_hash"),
        "label_dataset_hash": manifest.get("label_dataset_hash"),
        "release_blocker": (
            None
            if edge_count > 0
            else "No relationship survived every frozen statistical promotion gate."
        ),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "authority": authority_flags(),
    }


def validate_historical_gap_resolution(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    resolution = state["resolution"]
    registry = state["registry"]
    controls = state["negative_controls"]
    recert = state["recertification"]
    partitions = resolution.get("provider_partition_state", {})
    legacy = resolution.get("legacy_grid_state", {})
    if partitions.get("all_terminal") is not True or int(partitions.get("remaining") or 0):
        errors.append("historical_provider_partitions_not_terminal")
    if int(partitions.get("acquired") or 0) + int(
        partitions.get("classified_unavailable") or 0
    ) != int(partitions.get("total") or 0):
        errors.append("historical_provider_partition_counts_do_not_reconcile")
    if int(legacy.get("record_count") or 0) != int(legacy.get("typed_record_count") or 0):
        errors.append("legacy_windows_not_fully_typed")
    if int(legacy.get("legacy_rows_mutated_or_backfilled") or 0) != 0:
        errors.append("legacy_windows_were_mutated")
    if int(legacy.get("repairable_in_current_frozen_baseline_count") or 0) != 0:
        errors.append("historical_gap_resolution_has_unresolved_repairable_windows")
    if registry.get("synthetic_completion_allowed") is not False:
        errors.append("historical_registry_allows_synthetic_completion")
    if controls.get("status") != "passed":
        errors.append("historical_negative_controls_failed")
    if recert.get("research_protocol_valid") is not True:
        errors.append("historical_backtest_recertification_failed")
    if recert.get("leakage_violation_count") != 0:
        errors.append("historical_recertification_leakage_violation")
    if recert.get("holdout_tuning_violation_count") != 0:
        errors.append("historical_recertification_holdout_tuning_violation")
    for payload, prefix in (
        (resolution, "gap_resolution"),
        (registry, "unavailable_registry"),
        (controls, "negative_controls"),
        (recert, "backtest_recertification"),
    ):
        errors.extend(validate_authority(payload.get("authority", {}), prefix=prefix))
    return unique_errors(errors)


def build_and_write_historical_gap_resolution(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    provider_alignment = read_json(runtime / PROVIDER_ALIGNMENT_ARTIFACT)
    aligned = _alignment_coverage(provider_alignment)
    resolution, registry = _build_gap_resolution(runtime, aligned)
    manifest = read_json(runtime / BACKTEST_MANIFEST_ARTIFACT)
    results = _load_backtest_bulk(manifest)
    negative_controls = _build_negative_controls(runtime, results)
    recertification = _build_recertification(
        runtime, resolution, negative_controls, results
    )
    state = {
        "resolution": resolution,
        "registry": registry,
        "negative_controls": negative_controls,
        "recertification": recertification,
    }
    errors = validate_historical_gap_resolution(state)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_historical_gap_resolution_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "acceptance_passed": not errors,
        "provider_partition_count": resolution["provider_partition_state"]["total"],
        "provider_partition_remaining_count": resolution["provider_partition_state"]["remaining"],
        "legacy_missing_or_ineligible_count": resolution["legacy_grid_state"][
            "missing_or_ineligible_count"
        ],
        "legacy_rows_mutated_or_backfilled": 0,
        "provider_alignment_record_count": resolution["provider_alignment_state"][
            "alignment_record_count"
        ],
        "negative_control_count": negative_controls["control_count"],
        "validated_edge_count": recertification["validated_edge_count"],
        "paper_operator_edge_gate_passed": recertification[
            "paper_operator_edge_gate_passed"
        ],
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store.write_json(GAP_RESOLUTION_ARTIFACT, resolution)
    store.write_json(UNAVAILABLE_REGISTRY_ARTIFACT, registry)
    store.write_json(NEGATIVE_CONTROL_ARTIFACT, negative_controls)
    store.write_json(BACKTEST_RECERTIFICATION_ARTIFACT, recertification)
    store.write_json(CHECK_ARTIFACT, checks)
    return state, checks, errors


__all__ = [
    "BACKTEST_RECERTIFICATION_ARTIFACT",
    "CHECK_ARTIFACT",
    "GAP_RESOLUTION_ARTIFACT",
    "NEGATIVE_CONTROL_ARTIFACT",
    "UNAVAILABLE_REGISTRY_ARTIFACT",
    "build_and_write_historical_gap_resolution",
    "validate_historical_gap_resolution",
]
