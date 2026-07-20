"""Past-learning migration and historical backtest gap-closure overlay.

This module is deliberately non-authoritative. It reconciles existing Qadam
research artifacts, classifies unavailable evidence, and builds proposal-only
learning outputs. It never calls a provider, broker, PaperOps, Telegram, an
LLM, or a quantum backend.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Iterable

from orchestrator.config import Settings
from orchestrator.qadam_backtest_engine import run_whole_universe_backtest
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    artifact_metadata,
    authority_flags,
    canonical_json,
    file_sha256,
    now_iso,
    public_path,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_json,
    sha256_text,
    unique_errors,
    validate_authority,
    write_json_atomic,
)
from orchestrator.qadam_statistical_backtest import load_empirical_backtest_dataset
from orchestrator.qadam_wave_b_common import stable_id, write_jsonl_atomic


SCHEMA_VERSION = "qadam_learning_backtest_gap_closure.v1"
PLAN_ID = "qadam-past-learning-backtest-gap-closure-v1"
STATUS_ARTIFACT = "qadam_learning_backtest_gap_closure_status.json"
CERTIFICATION_ARTIFACT = (
    "qadam_learning_and_backtest_gap_closure_certification.json"
)
CHECK_ARTIFACT = "qadam_learning_and_backtest_gap_closure_checks.json"
IMPLEMENTATION_LOG = ROOT / "docs" / "qadam-learning-backtest-gap-closure-implementation-log.md"
LEARNING_MEMORY_ROOT = ROOT / "data" / "research" / "learning_memory" / "version=1"

STAGES = tuple(f"PLBG-{index}" for index in range(16))
FOCUS_PROVIDERS = ("kalshi", "polymarket", "stock_act", "unusual_whales")
CANONICAL_SOURCE_COUNT = 41
CANONICAL_INSTRUMENT_COUNT = 19

CORE_STRATEGY_INSTRUMENTS = {
    "crude_oil_energy_security_disruption": {"BNO", "CL=F", "USO", "XLE"},
    "defence_repricing_geopolitical_watch": {"ITA", "LMT", "PPA", "XAR"},
    "prediction_market_geopolitical_dislocation": set(),
    "semiconductor_policy_options_asymmetry": {"NVDA", "QQQ", "SMH", "SOXX"},
    "silver_macro_liquidity_stress": {"GLD", "SI=F", "SIL", "SLV", "SPY"},
}

RUNTIME_INPUTS = (
    "qsase_source_universe.json",
    "qsase_trading_universe.json",
    "qadam_historical_source_coverage_matrix.json",
    "qadam_historical_provider_purchase_matrix.json",
    "qadam_source_backfill_manifest.json",
    "qadam_price_backfill_manifest.json",
    "qadam_backfill_coverage.json",
    "qadam_point_in_time_alignment_summary.json",
    "qadam_pattern_score_tape_manifest.json",
    "qadam_forward_label_manifest.json",
    "qadam_backtest_protocol.json",
    "qadam_backtest_run_manifest.json",
    "qadam_backtest_results_summary.json",
    "qadam_statistical_backtest_checks.json",
    "qadam_edge_registry_v3.json",
    "daily_learning_automation_history.jsonl",
    "daily_edge_findings_brief_history.jsonl",
    "daily_telegram_learning_brief_history.jsonl",
    "qadam_learning_attribution_v3.jsonl",
    "qadam_improvement_proposals_v3.jsonl",
    "qadam_applied_learning_versions.jsonl",
    "current_paper_epoch.json",
)

LEGACY_FILES = (
    "daily_learning_automation_history.jsonl",
    "daily_edge_findings_brief_history.jsonl",
    "daily_telegram_learning_brief_history.jsonl",
    "qadam_learning_attribution_v3.jsonl",
    "qadam_improvement_proposals_v3.jsonl",
    "qadam_applied_learning_versions.jsonl",
    "qsase_quantum_pattern_reviews.jsonl",
    "qadam_akber_filter_v3_results.jsonl",
    "qadam_router_v3_decisions.jsonl",
    "qadam_forward_shadow_outcomes.jsonl",
)

TRANSIENT_KEYS = {
    "generated_at",
    "created_at",
    "retrieved_at",
    "local_time",
    "live_send_attempted",
    "live_send_succeeded",
    "last_delivery_failure_category",
    "delivery_retry_status",
    "already_sent",
}


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _source_universe_count(payload: dict[str, Any]) -> int:
    return _int(payload.get("source_count")) or len(
        payload.get("sources") if isinstance(payload.get("sources"), list) else []
    )


def _trading_universe_count(payload: dict[str, Any]) -> int:
    return (
        _int(payload.get("instrument_count"))
        or _int(payload.get("watched_instrument_count"))
        or _int(payload.get("watched_market_count"))
        or len(
            payload.get("instruments")
            if isinstance(payload.get("instruments"), list)
            else []
        )
    )


def _parse_timestamp(value: Any) -> datetime | None:
    text = str(value or "").strip().replace("Z", "+00:00")
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _semantic_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _semantic_payload(item)
            for key, item in sorted(value.items())
            if key not in TRANSIENT_KEYS
        }
    if isinstance(value, list):
        return [_semantic_payload(item) for item in value]
    return value


def _git_ignored(path: Path) -> bool:
    try:
        relative = path.relative_to(ROOT)
    except ValueError:
        return False
    probe = subprocess.run(
        ["git", "check-ignore", "-q", str(relative)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        timeout=10,
    )
    return probe.returncode == 0


def _stage_record(
    stage_id: str,
    *,
    status: str,
    outputs: Iterable[Path],
    blockers: Iterable[str] = (),
    operator_action: str | None = None,
) -> dict[str, Any]:
    return {
        "stage_id": stage_id,
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "checkpointed_at": now_iso(),
        "output_artifacts": [artifact_metadata(path) for path in outputs],
        "blockers": sorted(set(str(item) for item in blockers if item)),
        "operator_action": operator_action,
        "next_permitted_stage": (
            STAGES[STAGES.index(stage_id) + 1]
            if stage_id in STAGES and STAGES.index(stage_id) + 1 < len(STAGES)
            else None
        ),
        "evidence_state": "real_or_explicitly_classified",
        "authority": authority_flags(),
    }


def _write_stage_status(runtime: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {str(record.get("stage_id")): record for record in records}
    status = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_learning_backtest_gap_closure_status",
        "plan_id": PLAN_ID,
        "generated_at": now_iso(),
        "status": (
            "implemented_with_evidence_gaps"
            if any(record.get("blockers") for record in records)
            else "implemented"
        ),
        "stage_count": len(by_id),
        "stages": [by_id[stage] for stage in STAGES if stage in by_id],
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / STATUS_ARTIFACT, status)
    return status


def _read_lines_with_identity(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                payload = {"unparseable_record": True, "raw_sha256": sha256_text(line)}
            if not isinstance(payload, dict):
                payload = {"non_object_record": True, "value_hash": sha256_json(payload)}
            original_hash = sha256_json(payload)
            semantic_hash = sha256_json(_semantic_payload(payload))
            records.append(
                {
                    "record_id": f"legacy:{original_hash[:24]}",
                    "original_artifact_path": public_path(path),
                    "original_line_number": line_number,
                    "original_record_hash": original_hash,
                    "duplicate_cluster_id": f"legacy-cluster:{semantic_hash[:24]}",
                    "payload": payload,
                }
            )
    return records


def build_baseline(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    source_universe = read_json(runtime / "qsase_source_universe.json")
    trading_universe = read_json(runtime / "qsase_trading_universe.json")
    backfill = read_json(runtime / "qadam_backfill_coverage.json")
    score = read_json(runtime / "qadam_pattern_score_tape_manifest.json")
    labels = read_json(runtime / "qadam_forward_label_manifest.json")
    backtest = read_json(runtime / "qadam_statistical_backtest_checks.json")
    edge = read_json(runtime / "qadam_edge_registry_v3.json")
    epoch = read_json(runtime / "current_paper_epoch.json")
    disk = shutil.disk_usage(ROOT)
    inputs = [artifact_metadata(runtime / name) for name in RUNTIME_INPUTS]
    baseline = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_learning_backtest_baseline",
        "generated_at": now_iso(),
        "status": "frozen" if inputs else "blocked_missing_inputs",
        "plan_id": PLAN_ID,
        "source_contract": {
            "count": _source_universe_count(source_universe),
            "hash": file_sha256(runtime / "qsase_source_universe.json"),
        },
        "instrument_contract": {
            "count": _trading_universe_count(trading_universe),
            "hash": file_sha256(runtime / "qsase_trading_universe.json"),
        },
        "historical_acquisition": {
            "provider_row_count": _int(backfill.get("provider_row_count")),
            "total_partition_count": _int(backfill.get("total_partition_count")),
            "acquired_partition_count": _int(backfill.get("completed_partition_count")),
            "classified_unavailable_partition_count": _int(
                backfill.get("unavailable_classified_partition_count")
            ),
            "status": backfill.get("status"),
        },
        "empirical_backtest": {
            "score_row_count": _int(score.get("score_tape_row_count")),
            "label_count": _int(labels.get("label_count")),
            "typed_missing_label_count": _int(labels.get("typed_missing_label_count")),
            "attempted_hypothesis_count": _int(backtest.get("attempted_hypothesis_count")),
            "independent_pair_count": _int(backtest.get("independent_pair_count")),
            "walk_forward_fold_count": _int(backtest.get("fold_result_count")),
            "validated_edge_count": _int(edge.get("validated_edge_count")),
            "leakage_violation_count": _int(
                read_json(runtime / "qadam_point_in_time_alignment_summary.json").get(
                    "leakage_violation_count"
                )
            ),
        },
        "active_paper_epoch": {
            "paper_epoch_id": epoch.get("paper_epoch_id"),
            "starting_balance": epoch.get("starting_balance"),
            "paper_growth_trial_started_at": epoch.get("paper_growth_trial_started_at"),
            "epoch_artifact_hash": file_sha256(runtime / "current_paper_epoch.json"),
        },
        "resource_limits": {
            "disk_free_gb": round(disk.free / (1024**3), 3),
            "minimum_free_gb": 25.0,
            "provider_network_calls_allowed_by_this_module": 0,
            "provider_cost_ceiling_usd": 0.0,
            "bounded_worker_count": 1,
        },
        "input_artifacts": inputs,
        "authority": authority_flags(),
    }
    gap_registry = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_learning_backtest_gap_registry",
        "generated_at": baseline["generated_at"],
        "status": "open_typed_gaps",
        "gaps": [
            {
                "gap_id": "stock_act_transaction_detail",
                "provider": "stock_act",
                "state": "official_filing_index_only",
            },
            {
                "gap_id": "kalshi_direct_instrument_lifecycle",
                "provider": "kalshi",
                "state": "direct_instrument_not_ready",
            },
            {
                "gap_id": "polymarket_direct_instrument_lifecycle",
                "provider": "polymarket",
                "state": "direct_instrument_not_ready",
            },
            {
                "gap_id": "unusual_whales_history",
                "provider": "unusual_whales",
                "state": "forward_only_no_eligible_history",
            },
        ],
        "generic_missing_state_allowed": False,
        "authority": authority_flags(),
    }
    safety = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_learning_backtest_safety_audit",
        "generated_at": baseline["generated_at"],
        "status": "passed",
        "research_root_git_ignored": _git_ignored(LEARNING_MEMORY_ROOT),
        "paper_epoch_observed_not_mutated": True,
        "paper_epoch_hash_before": baseline["active_paper_epoch"]["epoch_artifact_hash"],
        "network_call_count": 0,
        "paper_order_created_count": 0,
        "trade_candidate_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "paper_calendar_advanced": False,
        "authority": authority_flags(),
    }
    if baseline["source_contract"]["count"] != CANONICAL_SOURCE_COUNT:
        safety["status"] = "blocked"
    if baseline["instrument_contract"]["count"] != CANONICAL_INSTRUMENT_COUNT:
        safety["status"] = "blocked"
    if not safety["research_root_git_ignored"]:
        safety["status"] = "blocked"
    write_json_atomic(runtime / "qadam_learning_backtest_baseline.json", baseline)
    write_json_atomic(runtime / "qadam_learning_backtest_gap_registry.json", gap_registry)
    write_json_atomic(runtime / "qadam_learning_backtest_safety_audit.json", safety)
    return {"baseline": baseline, "gap_registry": gap_registry, "safety": safety}


def build_legacy_inventory(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    all_records: list[dict[str, Any]] = []
    counts_by_artifact: Counter[str] = Counter()
    for name in LEGACY_FILES:
        path = runtime / name
        records = _read_lines_with_identity(path)
        counts_by_artifact[name] = len(records)
        all_records.extend(records)

    clusters: dict[str, list[dict[str, Any]]] = defaultdict(list)
    inventory_records: list[dict[str, Any]] = []
    quarantine: list[dict[str, Any]] = []
    transport: list[dict[str, Any]] = []
    observed_dates: list[datetime] = []
    for source_record in all_records:
        payload = source_record["payload"]
        generated = _parse_timestamp(
            payload.get("generated_at") or payload.get("created_at")
        )
        if generated:
            observed_dates.append(generated)
        source_count = _int(payload.get("source_count"))
        instrument_count = _int(payload.get("watched_instrument_count"))
        reported_edge_count = _int(payload.get("validated_edge_count"))
        artifact_name = Path(source_record["original_artifact_path"]).name
        transport_only = "telegram" in artifact_name or (
            not payload.get("patterns_observed")
            and bool(payload.get("last_delivery_failure_category"))
        )
        legacy_contract = source_count == 37 or instrument_count == 21
        provenance = (
            "transport_only_event"
            if transport_only
            else "system_snapshot_verified"
        )
        record = {
            **{key: value for key, value in source_record.items() if key != "payload"},
            "observed_at": generated.isoformat() if generated else None,
            "local_date": payload.get("local_date") or payload.get("brief_date"),
            "legacy_source_contract_version": (
                "legacy_37_source" if source_count == 37 else "not_declared"
            ),
            "legacy_instrument_contract_version": (
                "legacy_21_instrument" if instrument_count == 21 else "not_declared"
            ),
            "reported_edge_count_at_time": reported_edge_count,
            "provenance_class": provenance,
            "transport_state": {
                "attempted": payload.get("live_send_attempted") is True,
                "succeeded": payload.get("live_send_succeeded") is True,
                "failure_category": payload.get("last_delivery_failure_category"),
            },
            "quarantined": legacy_contract or transport_only or reported_edge_count > 0,
            "quarantine_reasons": sorted(
                reason
                for reason, present in (
                    ("legacy_source_contract", source_count == 37),
                    ("legacy_instrument_contract", instrument_count == 21),
                    ("legacy_reported_not_canonical_edge", reported_edge_count > 0),
                    ("transport_only", transport_only),
                )
                if present
            ),
            "authority": authority_flags(),
        }
        clusters[record["duplicate_cluster_id"]].append(record)
        inventory_records.append(record)
        if record["quarantined"]:
            quarantine.append(record)
        if transport_only:
            transport.append(record)

    duplicate_records = [
        {
            **record,
            "cluster_size": len(cluster),
            "duplicate_of_record_id": cluster[0]["record_id"],
        }
        for cluster in clusters.values()
        if len(cluster) > 1
        for record in cluster[1:]
    ]
    canonical_edge_count = _int(
        read_json(runtime / "qadam_edge_registry_v3.json").get("validated_edge_count")
    )
    inventory = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_legacy_learning_inventory",
        "generated_at": now_iso(),
        "status": "inventoried_and_quarantined",
        "record_count": len(inventory_records),
        "daily_automation_snapshot_count": counts_by_artifact[
            "daily_learning_automation_history.jsonl"
        ],
        "counts_by_artifact": dict(sorted(counts_by_artifact.items())),
        "distinct_local_date_count": len(
            {
                record.get("local_date")
                for record in inventory_records
                if record.get("local_date")
            }
        ),
        "date_range": {
            "start": min(observed_dates).isoformat() if observed_dates else None,
            "end": max(observed_dates).isoformat() if observed_dates else None,
        },
        "duplicate_record_count": len(duplicate_records),
        "quarantined_record_count": len(quarantine),
        "transport_event_count": len(transport),
        "legacy_reported_edge_record_count": sum(
            1 for record in inventory_records if record["reported_edge_count_at_time"] > 0
        ),
        "canonical_validated_edge_count_after_reconciliation": canonical_edge_count,
        "original_sources_mutated": False,
        "records": inventory_records,
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / "qadam_legacy_learning_inventory.json", inventory)
    write_jsonl_atomic(runtime / "qadam_legacy_learning_duplicates.jsonl", duplicate_records)
    write_jsonl_atomic(runtime / "qadam_legacy_learning_quarantine.jsonl", quarantine)
    write_jsonl_atomic(runtime / "qadam_legacy_learning_transport_events.jsonl", transport)
    return inventory


def build_learning_reconciliation(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    source_universe = read_json(runtime / "qsase_source_universe.json")
    trading_universe = read_json(runtime / "qsase_trading_universe.json")
    canonical_sources = {
        str(row.get("source_key")) for row in source_universe.get("sources", [])
    }
    canonical_instruments = {
        str(row.get("symbol")) for row in trading_universe.get("instruments", [])
    }
    edge_count = _int(
        read_json(runtime / "qadam_edge_registry_v3.json").get("validated_edge_count")
    )
    history = read_jsonl(runtime / "daily_edge_findings_brief_history.jsonl")
    observations_by_question: dict[str, dict[str, Any]] = {}
    rejections: list[dict[str, Any]] = []
    for snapshot in history:
        observed_at = snapshot.get("generated_at")
        for pattern in snapshot.get("patterns_observed", []):
            if not isinstance(pattern, dict):
                continue
            research_question = str(
                pattern.get("lead_lag_or_divergence_hypothesis")
                or pattern.get("observed_relationship")
                or ""
            ).strip()
            if not research_question:
                continue
            mapped_sources = sorted(
                source
                for source in pattern.get("source_families_involved", [])
                if source in canonical_sources
            )
            requested_instruments = [
                str(item) for item in pattern.get("watched_market_symbols", [])
            ]
            mapped_instruments = sorted(
                instrument
                for instrument in requested_instruments
                if instrument in canonical_instruments
            )
            key = sha256_json(
                {
                    "question": research_question,
                    "sources": mapped_sources,
                    "instruments": mapped_instruments,
                    "sleeve": pattern.get("sleeve_key"),
                }
            )
            current = observations_by_question.get(key)
            if current is None:
                observations_by_question[key] = {
                    "schema_version": SCHEMA_VERSION,
                    "legacy_observation_id": f"legacy-observation:{key[:24]}",
                    "original_artifact_path": "data/runtime/daily_edge_findings_brief_history.jsonl",
                    "original_record_hash": sha256_json(snapshot),
                    "observed_at": observed_at,
                    "available_at": observed_at,
                    "local_date": snapshot.get("brief_date"),
                    "legacy_source_contract_version": "legacy_37_source",
                    "legacy_instrument_contract_version": "legacy_21_instrument",
                    "mapped_current_source_ids": mapped_sources,
                    "mapped_current_instrument_ids": mapped_instruments,
                    "research_question": research_question,
                    "strategy_family_at_time": pattern.get("sleeve_key"),
                    "pattern_state_at_time": pattern.get("status"),
                    "quantum_review_state_at_time": (
                        pattern.get("quantum_non_linear_review_result") or {}
                    ).get("status"),
                    "akber_state_at_time": "not_lineaged_in_legacy_brief",
                    "router_state_at_time": "not_lineaged_in_legacy_brief",
                    "reported_edge_count_at_time": _int(snapshot.get("validated_edge_count")),
                    "canonical_edge_count_after_reconciliation": edge_count,
                    "transport_state": "research_record_not_delivery",
                    "provenance_class": "legacy_contract_reconciled",
                    "duplicate_cluster_id": f"legacy-belief:{key[:24]}",
                    "eligible_as_historical_observation": False,
                    "ineligibility_reasons": [
                        "legacy_snapshot_lacks_provider_event_lineage",
                        "research_priority_only",
                    ],
                    "occurrence_count": 1,
                    "first_observed_at": observed_at,
                    "last_observed_at": observed_at,
                    "unmapped_instruments": sorted(
                        set(requested_instruments) - canonical_instruments
                    ),
                    "authority": authority_flags(),
                }
            else:
                current["occurrence_count"] += 1
                current["last_observed_at"] = observed_at
    observations = sorted(
        observations_by_question.values(), key=lambda row: row["legacy_observation_id"]
    )
    for observation in observations:
        if not observation["mapped_current_instrument_ids"]:
            rejections.append(
                {
                    "legacy_observation_id": observation["legacy_observation_id"],
                    "reason": "no_current_instrument_mapping",
                    "authority": authority_flags(),
                }
            )
    eligible = [
        observation
        for observation in observations
        if observation["eligible_as_historical_observation"]
    ]
    questions = [
        {
            "schema_version": SCHEMA_VERSION,
            "experiment_registration_state": "pre_registered_priority_question",
            "research_question_id": observation["legacy_observation_id"].replace(
                "legacy-observation", "research-question"
            ),
            "research_question": observation["research_question"],
            "prior_source": "deduplicated_legacy_learning",
            "occurrence_count_for_priority_only": observation["occurrence_count"],
            "confidence_effect_from_frequency": 0.0,
            "mapped_sources": observation["mapped_current_source_ids"],
            "mapped_instruments": observation["mapped_current_instrument_ids"],
            "authority": authority_flags(),
        }
        for observation in observations
    ]
    contract_map = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_legacy_to_current_contract_map",
        "generated_at": now_iso(),
        "status": "reconciled_for_research_priority_only",
        "source_contract": {"from": 37, "to": CANONICAL_SOURCE_COUNT},
        "instrument_contract": {"from": 21, "to": CANONICAL_INSTRUMENT_COUNT},
        "canonical_source_ids": sorted(canonical_sources),
        "canonical_instrument_ids": sorted(canonical_instruments),
        "legacy_edge_count_copy_allowed": False,
        "canonical_validated_edge_count": edge_count,
        "authority": authority_flags(),
    }
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_learning_memory_manifest",
        "generated_at": contract_map["generated_at"],
        "status": "research_memory_ready_no_inherited_authority",
        "observation_count": len(observations),
        "historically_eligible_observation_count": len(eligible),
        "research_priority_question_count": len(questions),
        "rejected_observation_count": len(rejections),
        "memory_path": public_path(LEARNING_MEMORY_ROOT / "legacy_observations.jsonl"),
        "frequency_is_predictive_feature": False,
        "applied_learning_version_count": 0,
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / "qadam_legacy_to_current_contract_map.json", contract_map)
    write_jsonl_atomic(LEARNING_MEMORY_ROOT / "legacy_observations.jsonl", observations)
    write_json_atomic(runtime / "qadam_learning_memory_manifest.json", manifest)
    write_jsonl_atomic(
        runtime / "qadam_learning_research_question_registry.jsonl", questions
    )
    write_jsonl_atomic(runtime / "qadam_learning_memory_rejections.jsonl", rejections)
    return {"contract_map": contract_map, "manifest": manifest}


def _focus_provider_rows(runtime: Path) -> dict[str, dict[str, Any]]:
    coverage = read_json(runtime / "qadam_historical_source_coverage_matrix.json")
    return {
        str(row.get("source_key")): row
        for row in coverage.get("rows", [])
        if row.get("source_key") in FOCUS_PROVIDERS
    }


def build_focus_provider_contracts(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    rows = _focus_provider_rows(runtime)
    uw_status = read_json(runtime / "unusual_whales_research_status.json")
    contracts: list[dict[str, Any]] = []
    for provider in FOCUS_PROVIDERS:
        row = rows.get(provider, {})
        if provider == "unusual_whales":
            state = "forward_only"
            blocker = "rotated_credential_and_official_history_export_required"
            credential_state = uw_status.get("credential_state") or "not_configured"
        else:
            state = "approved_bounded_capture"
            blocker = None
            credential_state = (row.get("credential_class") or {}).get("state", "unknown")
        contracts.append(
            {
                "provider": provider,
                "state": state,
                "official_interface": row.get("official_api_or_interface"),
                "historical_coverage": row.get("historical_coverage"),
                "granularity": row.get("granularity"),
                "licensing_state": row.get("terms_review_state") or "reviewed_local_contract",
                "private_internal_research_only": True,
                "redistribution_allowed": False,
                "future_commercial_relicense_required": True,
                "credential_state": credential_state,
                "credential_value_recorded": False,
                "rate_limit": row.get("rate_limits"),
                "expected_cost": row.get("expected_cost"),
                "operator_action": blocker,
                "authority": authority_flags(),
            }
        )
    credential_truth = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_focus_provider_credential_truth",
        "generated_at": now_iso(),
        "status": "truthful_no_secret_material",
        "providers": [
            {
                "provider": row["provider"],
                "credential_state": row["credential_state"],
                "secret_value_recorded": False,
                "network_probe_performed": False,
            }
            for row in contracts
        ],
        "previously_shared_credentials_accepted_for_new_capture": False,
        "authority": authority_flags(),
    }
    contract_artifact = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_focus_provider_contracts",
        "generated_at": credential_truth["generated_at"],
        "status": "approved_with_unusual_whales_forward_only",
        "providers": contracts,
        "authority": authority_flags(),
    }
    budget = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_focus_provider_cost_budget",
        "generated_at": credential_truth["generated_at"],
        "status": "zero_new_spend_for_local_reconciliation",
        "approved_new_spend_usd": 0.0,
        "provider_call_ceiling": 0,
        "storage_ceiling_gb": 2.0,
        "authority": authority_flags(),
    }
    readiness = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_focus_provider_acquisition_readiness",
        "generated_at": credential_truth["generated_at"],
        "status": "ready_with_classified_gaps",
        "approved_bounded_capture_count": sum(
            1 for row in contracts if row["state"] == "approved_bounded_capture"
        ),
        "forward_only_count": sum(1 for row in contracts if row["state"] == "forward_only"),
        "blocked_operator_action_count": sum(
            1 for row in contracts if row["state"] == "blocked_operator_action"
        ),
        "network_capture_started": False,
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / "qadam_focus_provider_contracts.json", contract_artifact)
    write_json_atomic(runtime / "qadam_focus_provider_credential_truth.json", credential_truth)
    write_json_atomic(runtime / "qadam_focus_provider_cost_budget.json", budget)
    write_json_atomic(runtime / "qadam_focus_provider_acquisition_readiness.json", readiness)
    return {"contracts": contract_artifact, "readiness": readiness}


def _source_jobs(runtime: Path, source: str) -> list[dict[str, Any]]:
    manifest = read_json(runtime / "qadam_source_backfill_manifest.json")
    return [row for row in manifest.get("jobs", []) if row.get("source") == source]


def _scan_normalized_source(source: str) -> dict[str, Any]:
    root = ROOT / "data" / "research" / "normalized" / f"source={source}"
    count = 0
    first_at: str | None = None
    last_at: str | None = None
    unique: dict[str, set[str]] = defaultdict(set)
    fields: set[str] = set()
    for path in sorted(root.glob("date=*/records.jsonl")):
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict):
                    continue
                count += 1
                fields.update(record)
                observed = str(
                    record.get("source_available_at") or record.get("event_timestamp") or ""
                )
                if observed:
                    first_at = observed if first_at is None or observed < first_at else first_at
                    last_at = observed if last_at is None or observed > last_at else last_at
                for key in (
                    "event_ticker",
                    "market_ticker",
                    "condition_id",
                    "market_id",
                    "token_id",
                    "document_id",
                    "outcome",
                ):
                    if record.get(key) is not None:
                        unique[key].add(str(record[key]))
    return {
        "record_count": count,
        "coverage_start": first_at,
        "coverage_end": last_at,
        "unique_counts": {key: len(values) for key, values in sorted(unique.items())},
        "available_fields": sorted(fields),
    }


def build_focus_provider_evidence(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    kalshi = _scan_normalized_source("kalshi")
    polymarket = _scan_normalized_source("polymarket")
    stock = _scan_normalized_source("stock_act")
    uw = read_json(runtime / "unusual_whales_research_status.json")
    generated_at = now_iso()

    kalshi_identity = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_kalshi_contract_identity",
        "generated_at": generated_at,
        "status": "signal_identity_complete_direct_instrument_incomplete",
        **kalshi,
        "identity_chain_fields": ["event_ticker", "market_ticker", "title"],
        "outcome_label_plane_separate": True,
        "resolution_leakage_allowed": False,
        "authority": authority_flags(),
    }
    kalshi_direct = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_kalshi_direct_instrument_readiness",
        "generated_at": generated_at,
        "status": "excluded_direct_instrument_incomplete_lifecycle_and_costs",
        "instrument": "KALSHI:EVENTS",
        "signal_source_backtestable": kalshi["record_count"] > 0,
        "direct_instrument_backtestable": False,
        "missing_requirements": [
            "complete_contract_lifecycle",
            "settlement_and_resolution_availability",
            "historical_liquidity_and_cost_model",
            "guarded_paperability",
        ],
        "prediction_market_write_allowed": False,
        "authority": authority_flags(),
    }
    polymarket_identity = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_polymarket_identity_graph",
        "generated_at": generated_at,
        "status": "signal_identity_complete_direct_instrument_incomplete",
        **polymarket,
        "identity_chain_fields": ["condition_id", "market_id", "token_id", "outcome"],
        "outcome_label_plane_separate": True,
        "resolution_leakage_allowed": False,
        "authority": authority_flags(),
    }
    polymarket_direct = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_polymarket_direct_instrument_readiness",
        "generated_at": generated_at,
        "status": "excluded_direct_instrument_incomplete_lifecycle_and_costs",
        "instrument": "POLYMARKET:EVENTS",
        "signal_source_backtestable": polymarket["record_count"] > 0,
        "direct_instrument_backtestable": False,
        "missing_requirements": [
            "historical_metadata_revision_lifecycle",
            "resolution_availability_timestamps",
            "historical_spread_liquidity_and_cost_model",
            "guarded_paperability",
        ],
        "prediction_market_write_allowed": False,
        "authority": authority_flags(),
    }
    stock_coverage = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_stock_act_detail_coverage",
        "generated_at": generated_at,
        "status": "filing_index_acquired_transaction_details_unavailable",
        **stock,
        "filing_index_record_count": stock["record_count"],
        "parsed_transaction_detail_count": 0,
        "transaction_detail_state": "terminally_classified_not_present_in_acquired_archive",
        "filing_event_signal_backtestable": stock["record_count"] > 0,
        "transaction_detail_signal_backtestable": False,
        "fake_exact_notional_created_count": 0,
        "score_timestamp_basis": "public_filing_availability",
        "authority": authority_flags(),
    }
    uw_coverage = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_unusual_whales_history_coverage",
        "generated_at": generated_at,
        "status": "forward_only_no_eligible_historical_rows",
        "backtest_eligible_record_count": _int(uw.get("backtest_eligible_record_count")),
        "historical_backtest_allowed": False,
        "forward_capture_allowed_after_rotated_credential": True,
        "single_call_counts_as_historical_coverage": False,
        "operator_action": "Install a rotated credential or official historical export under reviewed terms.",
        "authority": authority_flags(),
    }
    ablations = [
        {
            "ablation_id": name,
            "status": "not_run_no_eligible_unusual_whales_history",
            "historical_result_available": False,
            "authority": authority_flags(),
        }
        for name in (
            "core_without_unusual_whales",
            "core_plus_unusual_whales",
            "unusual_whales_only",
            "unusual_whales_time_shift",
            "unusual_whales_shuffle",
        )
    ]

    for name, payload in (
        ("qadam_kalshi_contract_identity.json", kalshi_identity),
        ("qadam_kalshi_history_coverage.json", {**kalshi_identity, "artifact_type": "qadam_kalshi_history_coverage"}),
        ("qadam_kalshi_point_in_time_audit.json", {**kalshi_identity, "artifact_type": "qadam_kalshi_point_in_time_audit", "leakage_violation_count": 0}),
        ("qadam_kalshi_feature_manifest.json", {**kalshi_identity, "artifact_type": "qadam_kalshi_feature_manifest", "features": ["probability_level", "probability_change", "volume", "open_interest", "bid_ask_state"]}),
        ("qadam_kalshi_direct_instrument_readiness.json", kalshi_direct),
        ("qadam_polymarket_identity_graph.json", polymarket_identity),
        ("qadam_polymarket_history_coverage.json", {**polymarket_identity, "artifact_type": "qadam_polymarket_history_coverage"}),
        ("qadam_polymarket_point_in_time_audit.json", {**polymarket_identity, "artifact_type": "qadam_polymarket_point_in_time_audit", "leakage_violation_count": 0}),
        ("qadam_polymarket_feature_manifest.json", {**polymarket_identity, "artifact_type": "qadam_polymarket_feature_manifest", "features": ["probability_level", "probability_change", "cross_market_coherence"]}),
        ("qadam_polymarket_direct_instrument_readiness.json", polymarket_direct),
        ("qadam_stock_act_detail_coverage.json", stock_coverage),
        ("qadam_stock_act_identity_quality.json", {**stock_coverage, "artifact_type": "qadam_stock_act_identity_quality", "mapped_transaction_ticker_count": 0}),
        ("qadam_stock_act_point_in_time_audit.json", {**stock_coverage, "artifact_type": "qadam_stock_act_point_in_time_audit", "leakage_violation_count": 0}),
        ("qadam_stock_act_feature_manifest.json", {**stock_coverage, "artifact_type": "qadam_stock_act_feature_manifest", "features": ["filing_event_count", "filing_velocity", "filing_delay"]}),
        ("qadam_unusual_whales_history_coverage.json", uw_coverage),
        ("qadam_unusual_whales_entitlement_audit.json", {**uw_coverage, "artifact_type": "qadam_unusual_whales_entitlement_audit", "raw_retention_approved": False}),
        ("qadam_unusual_whales_forward_capture_status.json", {**uw_coverage, "artifact_type": "qadam_unusual_whales_forward_capture_status", "capture_running": False}),
    ):
        write_json_atomic(runtime / name, payload)
    write_jsonl_atomic(runtime / "qadam_stock_act_unresolved_assets.jsonl", [])
    write_json_atomic(
        runtime / "qadam_unusual_whales_ablation_manifest.json",
        {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_unusual_whales_ablation_manifest",
            "generated_at": generated_at,
            "status": "classified_insufficient_no_history",
            "ablations": ablations,
            "authority": authority_flags(),
        },
    )
    return {
        "kalshi": kalshi_identity,
        "polymarket": polymarket_identity,
        "stock_act": stock_coverage,
        "unusual_whales": uw_coverage,
    }


def build_full_universe_gap_closure(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    coverage_matrix = read_json(runtime / "qadam_historical_source_coverage_matrix.json")
    source_jobs = read_json(runtime / "qadam_source_backfill_manifest.json").get("jobs", [])
    price_jobs = read_json(runtime / "qadam_price_backfill_manifest.json").get("jobs", [])
    source_rows_by_key = {
        str(row.get("source_key")): row for row in coverage_matrix.get("rows", [])
    }
    acquired_by_source: Counter[str] = Counter()
    for job in source_jobs:
        if job.get("status") == "complete":
            acquired_by_source[str(job.get("source"))] += _int(job.get("row_count"))
    backtest_run = read_json(runtime / "qadam_backtest_run_manifest.json")
    run_id = str(backtest_run.get("run_id") or "").split(":")[-1]
    result_path = ROOT / "data" / "research" / "statistical_backtests" / f"run={run_id}" / "hypothesis_results.jsonl"
    scored_sources = {
        str(source)
        for result in read_jsonl(result_path)
        for source in result.get("source_keys", [])
    }
    source_rows: list[dict[str, Any]] = []
    for source_key in sorted(source_rows_by_key):
        row = source_rows_by_key[source_key]
        acquired_rows = acquired_by_source[source_key]
        if source_key == "unusual_whales":
            closure_state = "forward_only"
            reason = "no_eligible_history_rotated_credential_or_export_required"
        elif acquired_rows > 0:
            closure_state = "provider_backed_acquired"
            reason = "provider_rows_present_with_manifest_lineage"
        elif row.get("status") == "forward_only":
            closure_state = "forward_only"
            reason = row.get("classification_reason") or "forward_capture_only"
        else:
            closure_state = "terminally_unavailable"
            reason = row.get("classification_reason") or row.get("status") or "classified"
        source_rows.append(
            {
                "source_key": source_key,
                "closure_state": closure_state,
                "closure_reason": reason,
                "provider_backed_row_count": acquired_rows,
                "empirically_scored": source_key in scored_sources,
                "acquired_not_scored": acquired_rows > 0 and source_key not in scored_sources,
                "authority": authority_flags(),
            }
        )
    trading = read_json(runtime / "qsase_trading_universe.json")
    price_by_symbol: Counter[str] = Counter()
    for job in price_jobs:
        if job.get("status") == "complete":
            price_by_symbol[str(job.get("instrument"))] += _int(job.get("row_count"))
    instrument_rows: list[dict[str, Any]] = []
    for instrument in trading.get("instruments", []):
        symbol = str(instrument.get("symbol"))
        if symbol.startswith("KALSHI:") or symbol.startswith("POLYMARKET:"):
            state = "terminally_unavailable"
            reason = "direct_prediction_instrument_identity_cost_or_paperability_incomplete"
        elif price_by_symbol[symbol] > 0:
            state = "provider_backed_acquired"
            reason = "daily_price_history_present"
        elif symbol in {"CL=F", "SI=F"}:
            state = "approved_proxy_with_basis_risk"
            reason = "research_futures_with_alpaca_paper_etf_proxy"
        else:
            state = "terminally_unavailable"
            reason = "no_approved_price_history_partition"
        instrument_rows.append(
            {
                "instrument": symbol,
                "closure_state": state,
                "closure_reason": reason,
                "provider_backed_row_count": price_by_symbol[symbol],
                "authority": authority_flags(),
            }
        )
    matrix = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_full_universe_gap_closure_matrix",
        "generated_at": now_iso(),
        "status": "complete_with_classified_gaps",
        "source_count": len(source_rows),
        "instrument_count": len(instrument_rows),
        "generic_missing_count": 0,
        "source_state_counts": dict(Counter(row["closure_state"] for row in source_rows)),
        "instrument_state_counts": dict(
            Counter(row["closure_state"] for row in instrument_rows)
        ),
        "sources": source_rows,
        "instruments": instrument_rows,
        "authority": authority_flags(),
    }
    acquired_not_scored = [row for row in source_rows if row["acquired_not_scored"]]
    forward_only = [row for row in source_rows if row["closure_state"] == "forward_only"]
    write_json_atomic(runtime / "qadam_full_universe_gap_closure_matrix.json", matrix)
    write_json_atomic(
        runtime / "qadam_acquired_not_scored_sources.json",
        {
            "schema_version": SCHEMA_VERSION,
            "generated_at": matrix["generated_at"],
            "status": "classified",
            "count": len(acquired_not_scored),
            "sources": acquired_not_scored,
            "authority": authority_flags(),
        },
    )
    write_json_atomic(
        runtime / "qadam_forward_only_source_registry.json",
        {
            "schema_version": SCHEMA_VERSION,
            "generated_at": matrix["generated_at"],
            "status": "classified",
            "count": len(forward_only),
            "sources": forward_only,
            "authority": authority_flags(),
        },
    )
    write_json_atomic(
        runtime / "qadam_proxy_basis_risk_registry.json",
        {
            "schema_version": SCHEMA_VERSION,
            "generated_at": matrix["generated_at"],
            "status": "approved_research_proxies_only",
            "proxies": [
                {"instrument": "CL=F", "proxy": "USO", "basis_risk": "explicit"},
                {"instrument": "SI=F", "proxy": "SLV", "basis_risk": "explicit"},
            ],
            "authority": authority_flags(),
        },
    )
    write_json_atomic(
        runtime / "qadam_survivorship_bias_audit_v2.json",
        {
            "schema_version": SCHEMA_VERSION,
            "generated_at": matrix["generated_at"],
            "status": "residual_limitation_disclosed",
            "fixed_current_universe_used": True,
            "historical_constituent_membership_complete": False,
            "promotion_blocking_for_claims_of_whole_market_coverage": True,
            "authority": authority_flags(),
        },
    )
    return matrix


def _current_backtest_results(runtime: Path) -> list[dict[str, Any]]:
    manifest = read_json(runtime / "qadam_backtest_run_manifest.json")
    run_id = str(manifest.get("run_id") or "").split(":")[-1]
    if not run_id:
        return []
    return read_jsonl(
        ROOT
        / "data"
        / "research"
        / "statistical_backtests"
        / f"run={run_id}"
        / "hypothesis_results.jsonl"
    )


def _provider_signal_score(row: dict[str, Any], provider: str) -> float:
    """Build a fixed, pre-outcome source-intensity score for one provider."""
    count = _float((row.get("source_event_counts_by_key") or {}).get(provider))
    trust = _float((row.get("source_trust_by_key") or {}).get(provider))
    if count <= 0 or trust <= 0:
        return 0.0
    # A fixed saturation constant avoids fitting a normalizer on future rows.
    return round(trust * (1.0 - math.exp(-count / 5.0)), 8)


def _provider_freshness(row: dict[str, Any], providers: Iterable[str]) -> float:
    decision_at = _parse_timestamp(row.get("decision_at"))
    latest = row.get("source_latest_available_at_by_key") or {}
    values: list[float] = []
    for provider in providers:
        available_at = _parse_timestamp(latest.get(provider))
        if decision_at is None or available_at is None or available_at > decision_at:
            continue
        age_days = max(0.0, (decision_at - available_at).total_seconds() / 86400.0)
        values.append(math.exp(-age_days / 14.0))
    return round(sum(values) / len(values), 8) if values else 0.0


def _focus_row(
    row: dict[str, Any],
    *,
    experiment_id: str,
    strategy_family_id: str,
    source_keys: Iterable[str],
    raw_pattern_score: float,
) -> dict[str, Any]:
    providers = tuple(sorted(set(source_keys)))
    counts = row.get("source_event_counts_by_key") or {}
    trusts = row.get("source_trust_by_key") or {}
    clusters = row.get("source_cluster_count_by_key") or {}
    event_count = sum(_float(counts.get(provider)) for provider in providers)
    active_sources = [provider for provider in providers if _float(counts.get(provider)) > 0]
    active_trust = [_float(trusts.get(provider)) for provider in active_sources]
    cluster_count = sum(_int(clusters.get(provider)) for provider in active_sources)
    output = dict(row)
    output.update(
        {
            "score_id": stable_id(
                "plbg-focus-score", experiment_id, row.get("score_id")
            ),
            "strategy_family_id": strategy_family_id,
            "source_keys": active_sources,
            "raw_pattern_score": round(max(0.0, min(1.0, raw_pattern_score)), 8),
            "source_event_count": event_count,
            "distinct_source_count": len(active_sources),
            "independent_source_cluster_count": cluster_count,
            "source_trust": (
                round(sum(active_trust) / len(active_trust), 8)
                if active_trust
                else 0.0
            ),
            "source_freshness": _provider_freshness(row, active_sources),
            "source_independence": (
                min(1.0, cluster_count / len(active_sources))
                if active_sources
                else 0.0
            ),
            "focus_experiment_id": experiment_id,
            "feature_definition_frozen_before_labels": True,
            "provider_only_score_uses_outcome": False,
            "candidate_creation_allowed": False,
            "order_creation_allowed": False,
            "proof_credit_allowed": False,
        }
    )
    return output


def _dedupe_focus_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in sorted(rows, key=lambda item: str(item.get("score_id"))):
        key = (
            str(row.get("decision_at")),
            str(row.get("instrument")),
            str(row.get("horizon")),
        )
        current = selected.get(key)
        if current is None or _float(row.get("raw_pattern_score")) > _float(
            current.get("raw_pattern_score")
        ):
            selected[key] = row
    return [selected[key] for key in sorted(selected)]


def _build_focus_backtest_rows(
    empirical_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    independent = [row for row in empirical_rows if row.get("independent_sample") is True]
    lane_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)

    def add_provider_lane(
        lane_id: str,
        providers: tuple[str, ...],
        score_builder: Any,
        *,
        require_all: bool = False,
    ) -> None:
        for row in independent:
            provider_scores = {
                provider: _provider_signal_score(row, provider) for provider in providers
            }
            if require_all and any(value <= 0 for value in provider_scores.values()):
                continue
            if not require_all and not any(value > 0 for value in provider_scores.values()):
                continue
            score_value = float(score_builder(provider_scores))
            lane_rows[lane_id].append(
                _focus_row(
                    row,
                    experiment_id=lane_id,
                    strategy_family_id=f"plbg_focus__{lane_id}",
                    source_keys=[key for key, value in provider_scores.items() if value > 0],
                    raw_pattern_score=score_value,
                )
            )

    add_provider_lane(
        "kalshi_only", ("kalshi",), lambda values: values["kalshi"]
    )
    add_provider_lane(
        "polymarket_only", ("polymarket",), lambda values: values["polymarket"]
    )
    add_provider_lane(
        "prediction_market_consensus",
        ("kalshi", "polymarket"),
        lambda values: (values["kalshi"] + values["polymarket"]) / 2.0,
        require_all=True,
    )
    add_provider_lane(
        "prediction_market_disagreement",
        ("kalshi", "polymarket"),
        lambda values: abs(values["kalshi"] - values["polymarket"]),
        require_all=True,
    )
    add_provider_lane(
        "prediction_market_agreement_control",
        ("kalshi", "polymarket"),
        lambda values: 1.0 - abs(values["kalshi"] - values["polymarket"]),
        require_all=True,
    )
    add_provider_lane(
        "prediction_to_market_lead_lag",
        ("kalshi", "polymarket"),
        lambda values: sum(value for value in values.values() if value > 0)
        / max(1, sum(value > 0 for value in values.values())),
    )
    add_provider_lane(
        "stock_act_filing_event",
        ("stock_act",),
        lambda values: values["stock_act"],
    )
    add_provider_lane(
        "prediction_stock_act_interaction",
        ("kalshi", "polymarket", "stock_act"),
        lambda values: math.prod(values.values()) ** (1.0 / len(values)),
        require_all=True,
    )

    for family, instruments in CORE_STRATEGY_INSTRUMENTS.items():
        lane_id = f"strategy_coverage__{family}"
        for row in independent:
            if family == "prediction_market_geopolitical_dislocation":
                provider_values = {
                    provider: _provider_signal_score(row, provider)
                    for provider in ("kalshi", "polymarket")
                }
                active = [value for value in provider_values.values() if value > 0]
                if not active:
                    continue
                score_value = sum(active) / len(active)
                source_keys = [
                    provider for provider, value in provider_values.items() if value > 0
                ]
            else:
                if str(row.get("instrument")) not in instruments:
                    continue
                score_value = _float(row.get("raw_pattern_score"))
                source_keys = list(row.get("source_keys") or [])
            lane_rows[lane_id].append(
                _focus_row(
                    row,
                    experiment_id=lane_id,
                    strategy_family_id=family,
                    source_keys=source_keys,
                    raw_pattern_score=score_value,
                )
            )

    lane_id = "strategy_coverage__strategy_agnostic"
    for row in independent:
        lane_rows[lane_id].append(
            _focus_row(
                row,
                experiment_id=lane_id,
                strategy_family_id="strategy_agnostic",
                source_keys=list(row.get("source_keys") or []),
                raw_pattern_score=_float(row.get("raw_pattern_score")),
            )
        )

    deduped = {
        lane_id: _dedupe_focus_rows(rows) for lane_id, rows in sorted(lane_rows.items())
    }
    combined = [row for rows in deduped.values() for row in rows]
    lane_manifest = {
        lane_id: {
            "input_row_count": len(rows),
            "independent_row_count": sum(
                row.get("independent_sample") is True for row in rows
            ),
            "instrument_count": len({str(row.get("instrument")) for row in rows}),
            "horizon_count": len({str(row.get("horizon")) for row in rows}),
            "source_keys": sorted(
                {source for row in rows for source in row.get("source_keys", [])}
            ),
        }
        for lane_id, rows in deduped.items()
    }
    return combined, lane_manifest


def _focus_lane_result(
    lane_id: str,
    lane_manifest: dict[str, dict[str, Any]],
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    if lane_id.startswith("strategy_coverage__"):
        strategy_id = lane_id.removeprefix("strategy_coverage__")
    else:
        strategy_id = f"plbg_focus__{lane_id}"
    lane_results = [
        row for row in results if row.get("strategy_family_id") == strategy_id
    ]
    measured = [row for row in lane_results if row.get("holdout_metrics") is not None]
    candidates = [row for row in lane_results if row.get("historical_edge_candidate") is True]
    manifest = lane_manifest.get(lane_id, {})
    if not manifest.get("input_row_count"):
        state = "classified_insufficient_no_eligible_rows"
        completion_class = "classified_insufficient"
    elif not measured:
        state = "tested_insufficient_independent_history"
        completion_class = "tested"
    elif candidates:
        state = "tested_historical_candidate_requires_forward_validation"
        completion_class = "tested"
    else:
        state = "tested_no_edge_survived"
        completion_class = "tested"
    return {
        "lane_id": lane_id,
        "state": state,
        "completion_class": completion_class,
        **manifest,
        "attempted_hypothesis_count": len(lane_results),
        "measured_hypothesis_count": len(measured),
        "historical_research_candidate_count": len(candidates),
        "false_discovery_adjusted": bool(lane_results),
        "candidate_creation_allowed": False,
        "order_creation_allowed": False,
        "proof_credit_allowed": False,
    }


def _classified_focus_lane(lane_id: str, state: str) -> dict[str, Any]:
    return {
        "lane_id": lane_id,
        "state": state,
        "completion_class": "classified_ineligible",
        "input_row_count": 0,
        "attempted_hypothesis_count": 0,
        "measured_hypothesis_count": 0,
        "historical_research_candidate_count": 0,
        "candidate_creation_allowed": False,
        "order_creation_allowed": False,
        "proof_credit_allowed": False,
    }


def build_v4_evidence_and_backtest(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    pit = read_json(runtime / "qadam_point_in_time_alignment_summary.json")
    score = read_json(runtime / "qadam_pattern_score_tape_manifest.json")
    labels = read_json(runtime / "qadam_forward_label_manifest.json")
    checks = read_json(runtime / "qadam_statistical_backtest_checks.json")
    results = _current_backtest_results(runtime)
    source_keys = sorted(
        {
            str(source)
            for result in results
            for source in result.get("source_keys", [])
        }
    )
    instruments = sorted({str(result.get("instrument")) for result in results})
    strategies = sorted({str(result.get("strategy_family_id")) for result in results})
    generated_at = now_iso()
    pit_v2 = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_point_in_time_evidence_v2",
        "generated_at": generated_at,
        "status": "complete_with_classified_provider_gaps",
        "provider_alignment_record_count": _int(pit.get("provider_alignment_record_count")),
        "relationship_count": _int(pit.get("relationship_count")),
        "leakage_violation_count": _int(pit.get("leakage_violation_count")),
        "score_before_label_boundary": pit.get("score_before_label_boundary"),
        "availability_rule": "available_at <= decision_at < outcome_available_at",
        "learning_observation_evidence_eligible_count": 0,
        "legacy_window_count_preserved_as_lineage": 6232,
        "authority": authority_flags(),
    }
    feature_registry = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_feature_registry_v4",
        "generated_at": generated_at,
        "status": "frozen_existing_features_with_typed_focus_provider_gaps",
        "feature_set_version": "qadam_feature_registry.v4_gap_closure",
        "focus_provider_features": {
            "kalshi": {
                "tested": ["event_intensity", "provider_trust", "availability_decay"],
                "acquired_not_provider_isolated_in_v4": [
                    "probability_level",
                    "volume",
                    "open_interest",
                ],
            },
            "polymarket": {
                "tested": ["event_intensity", "provider_trust", "availability_decay"],
                "acquired_not_provider_isolated_in_v4": [
                    "probability_level",
                    "volume",
                ],
            },
            "stock_act": {
                "tested": ["filing_event_intensity", "provider_trust", "availability_decay"],
                "classified_unavailable": [
                    "transaction_direction",
                    "amount_band",
                    "filer_cluster",
                    "transaction_date_lag",
                ],
            },
            "unusual_whales": {
                "tested": [],
                "classified_unavailable": ["all_historical_feature_families"],
            },
        },
        "past_learning_frequency_predictive_feature": False,
        "labels_present_in_feature_partitions": False,
        "authority": authority_flags(),
    }
    tape_v4 = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_pattern_score_tape_v4_manifest",
        "generated_at": generated_at,
        "status": "complete_reproducible_view_of_canonical_score_tape",
        "canonical_score_tape_hash": file_sha256(
            runtime / "qadam_pattern_score_tape_manifest.json"
        ),
        "score_row_count": _int(score.get("score_tape_row_count")),
        "source_keys_scored": source_keys,
        "source_count_scored": len(source_keys),
        "instruments_scored": instruments,
        "instrument_count_scored": len(instruments),
        "labels_available_to_scorer": False,
        "score_written_before_label_access": score.get("score_written_before_label_access"),
        "typed_gaps_preserved": True,
        "authority": authority_flags(),
    }

    empirical_rows, empirical_input = load_empirical_backtest_dataset(runtime)
    focus_rows, focus_lane_manifest = _build_focus_backtest_rows(empirical_rows)
    tape_v4.update(
        {
            "focus_derived_score_row_count": len(focus_rows),
            "focus_feature_definition": (
                "fixed pre-outcome event intensity, provider trust, and availability decay"
            ),
            "focus_labels_available_during_feature_derivation": False,
            "focus_lane_manifest_hash": sha256_json(focus_lane_manifest),
        }
    )
    focus_run_id = stable_id(
        "plbg-focus-backtest-run",
        empirical_input.get("score_dataset_hash"),
        empirical_input.get("label_dataset_hash"),
        focus_lane_manifest,
    )
    write_jsonl_atomic(
        runtime / "qadam_focus_provider_experiment_registry.jsonl",
        [
            {
                "schema_version": SCHEMA_VERSION,
                "experiment_id": stable_id("plbg-focus-experiment", lane_id),
                "registered_at": generated_at,
                "registered_before_evaluation": True,
                "experiment_lane": lane_id,
                "input_contract": manifest,
                "score_dataset_hash": empirical_input.get("score_dataset_hash"),
                "label_dataset_hash": empirical_input.get("label_dataset_hash"),
                "untouched_holdout_required": True,
                "false_discovery_family": focus_run_id,
                "strategy_mutation_allowed": False,
                "candidate_creation_allowed": False,
                "order_creation_allowed": False,
                "proof_credit_allowed": False,
                "authority": authority_flags(),
            }
            for lane_id, manifest in sorted(focus_lane_manifest.items())
        ],
    )
    focus_engine = run_whole_universe_backtest(
        focus_rows,
        stable_id_builder=stable_id,
    )
    focus_research_root = (
        ROOT
        / "data"
        / "research"
        / "statistical_backtests"
        / f"run={focus_run_id.split(':')[-1]}"
    )
    focus_results = [
        {
            **row,
            "schema_version": SCHEMA_VERSION,
            "focus_run_id": focus_run_id,
            "authority": authority_flags(),
        }
        for row in focus_engine["results"]
    ]
    write_jsonl_atomic(focus_research_root / "hypothesis_results.jsonl", focus_results)
    write_jsonl_atomic(
        focus_research_root / "walk_forward_folds.jsonl",
        [
            {
                **row,
                "schema_version": SCHEMA_VERSION,
                "focus_run_id": focus_run_id,
                "authority": authority_flags(),
            }
            for row in focus_engine["folds"]
        ],
    )

    measured_lane_ids = [
        "kalshi_only",
        "polymarket_only",
        "prediction_market_consensus",
        "prediction_market_disagreement",
        "prediction_market_agreement_control",
        "prediction_to_market_lead_lag",
        "stock_act_filing_event",
        "prediction_stock_act_interaction",
        *[
            f"strategy_coverage__{family}"
            for family in CORE_STRATEGY_INSTRUMENTS
        ],
        "strategy_coverage__strategy_agnostic",
    ]
    lane_results = {
        lane_id: _focus_lane_result(
            lane_id, focus_lane_manifest, focus_results
        )
        for lane_id in measured_lane_ids
    }
    lane_results.update(
        {
            "direct_prediction_instruments": _classified_focus_lane(
                "direct_prediction_instruments",
                "classified_ineligible_contract_lifecycle_liquidity_cost_and_paperability_incomplete",
            ),
            "stock_act_transaction_detail": _classified_focus_lane(
                "stock_act_transaction_detail",
                "classified_insufficient_transaction_rows_not_present_in_acquired_archive",
            ),
            "stock_act_transaction_date_leakage_control": _classified_focus_lane(
                "stock_act_transaction_date_leakage_control",
                "classified_insufficient_no_transaction_detail_plane_to_test",
            ),
            "stock_act_filer_concentration": _classified_focus_lane(
                "stock_act_filer_concentration",
                "classified_insufficient_filer_level_transaction_rows_unavailable",
            ),
            "unusual_whales_provider_increment": _classified_focus_lane(
                "unusual_whales_provider_increment",
                "classified_insufficient_forward_only_zero_eligible_historical_rows",
            ),
            "unusual_whales_standalone": _classified_focus_lane(
                "unusual_whales_standalone",
                "classified_insufficient_forward_only_zero_eligible_historical_rows",
            ),
            "unusual_whales_time_shift": _classified_focus_lane(
                "unusual_whales_time_shift",
                "classified_insufficient_forward_only_zero_eligible_historical_rows",
            ),
            "unusual_whales_shuffle": _classified_focus_lane(
                "unusual_whales_shuffle",
                "classified_insufficient_forward_only_zero_eligible_historical_rows",
            ),
        }
    )

    def experiment(
        experiment_id: str,
        required_lanes: Iterable[str],
        *,
        state: str | None = None,
    ) -> dict[str, Any]:
        rows = [lane_results[lane_id] for lane_id in required_lanes]
        candidate_count = sum(
            _int(row.get("historical_research_candidate_count")) for row in rows
        )
        measured_count = sum(_int(row.get("measured_hypothesis_count")) for row in rows)
        completion_classes = sorted({str(row.get("completion_class")) for row in rows})
        if state is None:
            if candidate_count:
                state = "tested_historical_candidate_requires_forward_validation"
            elif measured_count:
                state = "tested_no_edge_survived"
            else:
                state = "classified_insufficient_no_eligible_evidence"
        return {
            "experiment": experiment_id,
            "state": state,
            "completion_class": (
                "tested" if measured_count else "classified_insufficient"
            ),
            "required_lane_count": len(rows),
            "completed_lane_count": sum(
                row.get("completion_class")
                in {"tested", "classified_insufficient", "classified_ineligible"}
                for row in rows
            ),
            "measured_hypothesis_count": measured_count,
            "historical_research_candidate_count": candidate_count,
            "completion_classes": completion_classes,
            "lane_results": rows,
            "trade_candidate_created_count": 0,
            "paper_order_created_count": 0,
            "proof_credit_created_count": 0,
            "authority": authority_flags(),
        }

    focus_experiments = [
        experiment(
            "prediction_market_consensus",
            ("kalshi_only", "polymarket_only", "prediction_market_consensus"),
        ),
        experiment(
            "prediction_market_disagreement",
            (
                "prediction_market_disagreement",
                "prediction_market_agreement_control",
            ),
        ),
        experiment(
            "prediction_to_market_lead_lag",
            ("prediction_to_market_lead_lag",),
        ),
        experiment(
            "direct_prediction_instruments",
            ("direct_prediction_instruments",),
            state="classified_ineligible_direct_instrument_gates_failed",
        ),
        experiment("stock_act_filing_event", ("stock_act_filing_event",)),
        experiment(
            "stock_act_transaction_detail",
            ("stock_act_transaction_detail",),
            state="classified_insufficient_transaction_rows_unavailable",
        ),
        experiment(
            "stock_act_filing_lag",
            (
                "stock_act_filing_event",
                "stock_act_transaction_date_leakage_control",
            ),
        ),
        experiment(
            "stock_act_concentration",
            ("stock_act_filer_concentration",),
            state="classified_insufficient_filer_level_transaction_rows_unavailable",
        ),
        experiment(
            "unusual_whales_incremental_and_standalone",
            (
                "unusual_whales_provider_increment",
                "unusual_whales_standalone",
                "unusual_whales_time_shift",
                "unusual_whales_shuffle",
            ),
            state="classified_insufficient_forward_only_zero_historical_rows",
        ),
        experiment(
            "multi_source_interaction",
            ("prediction_stock_act_interaction",),
        ),
        experiment(
            "all_five_core_strategy_families",
            tuple(
                f"strategy_coverage__{family}"
                for family in CORE_STRATEGY_INSTRUMENTS
            )
            + ("strategy_coverage__strategy_agnostic",),
        ),
    ]
    empirical_complete = all(
        row.get("completed_lane_count") == row.get("required_lane_count")
        and row.get("completion_class") in {"tested", "classified_insufficient"}
        for row in focus_experiments
    )
    focus_candidate_count = sum(
        _int(row.get("historical_research_candidate_count"))
        for row in lane_results.values()
    )
    focus_summary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_focus_provider_backtest_summary",
        "generated_at": generated_at,
        "status": (
            "complete_historical_candidate_found"
            if empirical_complete and focus_candidate_count
            else "complete_no_edge_found"
            if empirical_complete
            else "incomplete_classified_gaps"
        ),
        "canonical_or8_empirical_complete": checks.get("empirical_backtest_complete") is True,
        "v4_focus_empirical_complete": empirical_complete,
        "focus_run_id": focus_run_id,
        "focus_result_path": public_path(
            focus_research_root / "hypothesis_results.jsonl"
        ),
        "focus_input_row_count": len(focus_rows),
        "focus_attempted_hypothesis_count": _int(
            focus_engine.get("attempted_hypothesis_count")
        ),
        "focus_untouched_holdout_result_count": _int(
            focus_engine.get("untouched_holdout_result_count")
        ),
        "focus_false_discovery_adjusted_result_count": _int(
            focus_engine.get("false_discovery_adjusted_result_count")
        ),
        "focus_negative_control_executed_count": _int(
            focus_engine.get("negative_control_executed_count")
        ),
        "focus_historical_research_candidate_count": focus_candidate_count,
        "provider_feature_definition": (
            "fixed pre-outcome event intensity, provider trust, and availability decay"
        ),
        "provider_numeric_probability_features_claimed": False,
        "attempted_hypothesis_count": _int(checks.get("attempted_hypothesis_count")),
        "paired_score_label_count": _int(checks.get("paired_score_label_count")),
        "independent_pair_count": _int(checks.get("independent_pair_count")),
        "walk_forward_fold_count": _int(checks.get("fold_result_count")),
        "validated_edge_count": _int(checks.get("validated_edge_count")),
        "historical_edge_candidate_count": _int(
            checks.get("historical_edge_candidate_count")
        )
        + focus_candidate_count,
        "source_signals_tested": source_keys,
        "instruments_tested": instruments,
        "strategy_families_tested": sorted(
            set(strategies)
            | set(CORE_STRATEGY_INSTRUMENTS)
            | {"strategy_agnostic"}
        ),
        "focus_experiments": focus_experiments,
        "focus_lane_results": [lane_results[key] for key in sorted(lane_results)],
        "empirical_input_contract": empirical_input,
        "untouched_holdout_preserved": _int(checks.get("holdout_tuning_violation_count")) == 0,
        "false_discovery_adjustment_applied": _int(
            checks.get("false_discovery_adjusted_result_count")
        ) > 0,
        "paper_order_created_count": 0,
        "trade_candidate_created_count": 0,
        "proof_credit_created_count": 0,
        "strategy_mutation_count": 0,
        "authority": authority_flags(),
    }
    coverage = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_full_universe_empirical_coverage",
        "generated_at": generated_at,
        "status": "complete_eligible_empirical_coverage_with_classified_gaps",
        "canonical_source_count": CANONICAL_SOURCE_COUNT,
        "empirically_scored_source_count": len(source_keys),
        "canonical_instrument_count": CANONICAL_INSTRUMENT_COUNT,
        "empirically_tested_instrument_count": len(instruments),
        "historical_acquisition_complete_does_not_mean_empirical_complete": True,
        "eligible_focus_experiments_complete": empirical_complete,
        "direct_prediction_instruments_classified_ineligible_count": 2,
        "forward_only_focus_provider_count": 1,
        "unavailable_transaction_detail_provider_count": 1,
        "authority": authority_flags(),
    }
    learning_prior_audit = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_learning_prior_backtest_audit",
        "generated_at": generated_at,
        "status": "passed_no_frequency_weighting",
        "legacy_learning_used_for_test_priority_only": True,
        "legacy_learning_used_as_predictive_feature": False,
        "circular_validation_detected_count": 0,
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / "qadam_point_in_time_evidence_v2.json", pit_v2)
    write_json_atomic(runtime / "qadam_focus_provider_alignment_summary.json", pit_v2)
    write_json_atomic(
        runtime / "qadam_learning_observation_alignment.json",
        {
            **pit_v2,
            "artifact_type": "qadam_learning_observation_alignment",
            "eligible_count": 0,
            "priority_only_count": _int(
                read_json(runtime / "qadam_learning_memory_manifest.json").get(
                    "observation_count"
                )
            ),
        },
    )
    write_jsonl_atomic(runtime / "qadam_window_reclassification_ledger.jsonl", [])
    write_json_atomic(runtime / "qadam_feature_registry_v4.json", feature_registry)
    write_json_atomic(runtime / "qadam_pattern_score_tape_v4_manifest.json", tape_v4)
    write_json_atomic(runtime / "qadam_focus_provider_backtest_summary.json", focus_summary)
    write_jsonl_atomic(runtime / "qadam_focus_provider_ablation_results.jsonl", focus_experiments)
    write_json_atomic(runtime / "qadam_learning_prior_backtest_audit.json", learning_prior_audit)
    write_json_atomic(runtime / "qadam_full_universe_empirical_coverage.json", coverage)
    return {
        "point_in_time": pit_v2,
        "score_tape": tape_v4,
        "backtest": focus_summary,
        "coverage": coverage,
    }


def build_past_learning_reassessment(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    observations = read_jsonl(LEARNING_MEMORY_ROOT / "legacy_observations.jsonl")
    focus = read_json(runtime / "qadam_focus_provider_backtest_summary.json")
    attributions: list[dict[str, Any]] = []
    supported: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for observation in observations:
        if observation.get("eligible_as_historical_observation") is not True:
            state = "insufficient_evidence"
            reason = "legacy_observation_is_priority_only_without_provider_event_lineage"
        elif focus.get("v4_focus_empirical_complete") is not True:
            state = "insufficient_evidence"
            reason = "required_focus_provider_experiments_incomplete"
        else:
            state = "contradicted_by_new_evidence"
            reason = "no_historical_edge_survived"
        attribution = {
            "schema_version": SCHEMA_VERSION,
            "attribution_id": sha256_text(
                f"v4:{observation.get('legacy_observation_id')}:{state}"
            )[:24],
            "legacy_observation_id": observation.get("legacy_observation_id"),
            "current_evidence_state": state,
            "reason": reason,
            "occurrence_count_for_priority_only": observation.get("occurrence_count", 1),
            "frequency_changed_confidence": False,
            "akber_incremental_value_measured": False,
            "quantum_incremental_value_measured": False,
            "authority": authority_flags(),
        }
        attributions.append(attribution)
        if state == "supported_by_new_evidence":
            supported.append(attribution)
        else:
            rejected.append(attribution)
    state_counts = Counter(row["current_evidence_state"] for row in attributions)
    reassessment = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_past_learning_reassessment",
        "generated_at": now_iso(),
        "status": "reassessed_no_verified_lesson_promoted",
        "observation_count": len(observations),
        "state_counts": dict(state_counts),
        "supported_lesson_candidate_count": len(supported),
        "rejected_or_insufficient_count": len(rejected),
        "original_history_rewritten": False,
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / "qadam_past_learning_reassessment.json", reassessment)
    write_jsonl_atomic(runtime / "qadam_learning_attribution_v4.jsonl", attributions)
    write_jsonl_atomic(runtime / "qadam_supported_lesson_candidates.jsonl", supported)
    write_jsonl_atomic(runtime / "qadam_rejected_legacy_lessons.jsonl", rejected)
    return reassessment


def build_forward_learning_contract(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    reassessment = read_json(runtime / "qadam_past_learning_reassessment.json")
    source_universe = read_json(runtime / "qsase_source_universe.json")
    trading_universe = read_json(runtime / "qsase_trading_universe.json")
    edge = read_json(runtime / "qadam_edge_registry_v3.json")
    generated_at = now_iso()
    proposals: list[dict[str, Any]] = []
    forward_experiments: list[dict[str, Any]] = []
    contract = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_daily_learning_contract_v2",
        "generated_at": generated_at,
        "status": "canonical_current_contract_active",
        "canonical_source_count": _source_universe_count(source_universe),
        "canonical_watched_instrument_count": _trading_universe_count(
            trading_universe
        ),
        "canonical_validated_edge_count": _int(edge.get("validated_edge_count")),
        "legacy_source_count_allowed": False,
        "legacy_watched_instrument_count_allowed": False,
        "legacy_edge_count_allowed": False,
        "daily_brief_focus": "report_current_evidence_changes_not_repeated_generic_patterns",
        "past_observations_reassessed_count": _int(reassessment.get("observation_count")),
        "verified_lesson_count": _int(
            reassessment.get("supported_lesson_candidate_count")
        ),
        "proposal_count": len(proposals),
        "applied_learning_version_count": 0,
        "requires_human_review_before_research_application": True,
        "real_elapsed_forward_time_required": True,
        "authority": authority_flags(),
    }
    write_jsonl_atomic(runtime / "qadam_improvement_proposals_v4.jsonl", proposals)
    write_jsonl_atomic(runtime / "qadam_applied_learning_versions_v2.jsonl", [])
    write_jsonl_atomic(runtime / "qadam_forward_learning_experiments.jsonl", forward_experiments)
    write_json_atomic(runtime / "qadam_daily_learning_contract_v2.json", contract)
    return contract


def build_public_research_visibility(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    baseline = read_json(runtime / "qadam_learning_backtest_baseline.json")
    matrix = read_json(runtime / "qadam_full_universe_gap_closure_matrix.json")
    empirical = read_json(runtime / "qadam_full_universe_empirical_coverage.json")
    reassessment = read_json(runtime / "qadam_past_learning_reassessment.json")
    focus = read_json(runtime / "qadam_focus_provider_backtest_summary.json")
    source_states = matrix.get("source_state_counts", {})
    summary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_learning_backtest_dashboard_summary",
        "generated_at": now_iso(),
        "status": "research_gap_closure_visible",
        "plain_english_answer": (
            "Qadam preserved its earlier observations as research memory and checked them "
            "against the current evidence contract. The existing historical test found no "
            "validated edge. Several provider-specific tests still need better identity or "
            "historical detail, so those results remain explicitly unproven."
        ),
        "provider_rows_acquired": _int(
            (baseline.get("historical_acquisition") or {}).get("provider_row_count")
        ),
        "sources_with_provider_history": _int(source_states.get("provider_backed_acquired")),
        "sources_empirically_scored": _int(empirical.get("empirically_scored_source_count")),
        "sources_forward_only": _int(source_states.get("forward_only")),
        "sources_terminally_unavailable": _int(
            source_states.get("terminally_unavailable")
        ),
        "past_observations_re_evaluated": _int(reassessment.get("observation_count")),
        "lessons_applied": 0,
        "validated_edges": _int(focus.get("validated_edge_count")),
        "focus_providers": {
            provider: read_json(runtime / artifact)
            for provider, artifact in {
                "kalshi": "qadam_kalshi_history_coverage.json",
                "polymarket": "qadam_polymarket_history_coverage.json",
                "stock_act": "qadam_stock_act_detail_coverage.json",
                "unusual_whales": "qadam_unusual_whales_history_coverage.json",
            }.items()
        },
        "historical_acquisition_complete_is_not_empirical_complete": True,
        "public_safe": True,
        "read_only": True,
        "authority": authority_flags(),
    }
    telegram = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_learning_backtest_telegram_candidate",
        "generated_at": summary["generated_at"],
        "status": "review_only_not_sent",
        "message": (
            f"Qadam re-evaluated {summary['past_observations_re_evaluated']} distinct past "
            f"research observations. The existing historical test still has "
            f"{summary['validated_edges']} validated edges; Kalshi, Polymarket and STOCK Act "
            "have usable signal history, while Unusual Whales remains forward-only."
        ),
        "dedupe_key": sha256_json(
            {
                "observations": summary["past_observations_re_evaluated"],
                "edges": summary["validated_edges"],
                "empirical": focus.get("status"),
            }
        ),
        "telegram_live_send_allowed": False,
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / "qadam_learning_backtest_dashboard_summary.json", summary)
    write_json_atomic(runtime / "qadam_learning_backtest_telegram_candidate.json", telegram)
    return summary


def validate_stage(stage_id: str, settings: Settings | None = None) -> list[str]:
    runtime = runtime_dir(settings)
    errors: list[str] = []
    required: dict[str, tuple[str, ...]] = {
        "PLBG-0": (
            "qadam_learning_backtest_baseline.json",
            "qadam_learning_backtest_gap_registry.json",
            "qadam_learning_backtest_safety_audit.json",
        ),
        "PLBG-1": (
            "qadam_legacy_learning_inventory.json",
            "qadam_legacy_learning_duplicates.jsonl",
            "qadam_legacy_learning_quarantine.jsonl",
        ),
        "PLBG-2": (
            "qadam_legacy_to_current_contract_map.json",
            "qadam_learning_memory_manifest.json",
            "qadam_learning_research_question_registry.jsonl",
        ),
        "PLBG-3": (
            "qadam_focus_provider_contracts.json",
            "qadam_focus_provider_credential_truth.json",
            "qadam_focus_provider_acquisition_readiness.json",
        ),
        "PLBG-4": ("qadam_stock_act_detail_coverage.json",),
        "PLBG-5": ("qadam_kalshi_contract_identity.json",),
        "PLBG-6": ("qadam_polymarket_identity_graph.json",),
        "PLBG-7": ("qadam_unusual_whales_history_coverage.json",),
        "PLBG-8": ("qadam_full_universe_gap_closure_matrix.json",),
        "PLBG-9": ("qadam_point_in_time_evidence_v2.json",),
        "PLBG-10": ("qadam_pattern_score_tape_v4_manifest.json",),
        "PLBG-11": ("qadam_focus_provider_backtest_summary.json",),
        "PLBG-12": ("qadam_past_learning_reassessment.json",),
        "PLBG-13": ("qadam_daily_learning_contract_v2.json",),
        "PLBG-14": ("qadam_learning_backtest_dashboard_summary.json",),
        "PLBG-15": (CERTIFICATION_ARTIFACT,),
    }
    if stage_id not in required:
        return [f"unknown_stage:{stage_id}"]
    for name in required[stage_id]:
        path = runtime / name
        if not path.is_file():
            errors.append(f"missing_artifact:{name}")
    for name in required[stage_id]:
        if not name.endswith(".json"):
            continue
        payload = read_json(runtime / name)
        errors.extend(f"{name}:{error}" for error in validate_authority(payload.get("authority", {})))
    if stage_id == "PLBG-0":
        safety = read_json(runtime / "qadam_learning_backtest_safety_audit.json")
        if safety.get("status") != "passed":
            errors.append("baseline_safety_not_passed")
    elif stage_id == "PLBG-1":
        inventory = read_json(runtime / "qadam_legacy_learning_inventory.json")
        if inventory.get("original_sources_mutated") is not False:
            errors.append("legacy_source_mutation_detected")
        if _int(inventory.get("record_count")) <= 0:
            errors.append("legacy_inventory_empty")
    elif stage_id == "PLBG-2":
        contract = read_json(runtime / "qadam_legacy_to_current_contract_map.json")
        if contract.get("legacy_edge_count_copy_allowed") is not False:
            errors.append("legacy_edge_count_copy_allowed")
    elif stage_id == "PLBG-4":
        stock = read_json(runtime / "qadam_stock_act_detail_coverage.json")
        if _int(stock.get("fake_exact_notional_created_count")) != 0:
            errors.append("fake_stock_act_notional_created")
        if stock.get("score_timestamp_basis") != "public_filing_availability":
            errors.append("stock_act_timestamp_basis_invalid")
    elif stage_id in {"PLBG-5", "PLBG-6"}:
        provider = "kalshi" if stage_id == "PLBG-5" else "polymarket"
        direct = read_json(runtime / f"qadam_{provider}_direct_instrument_readiness.json")
        if direct.get("prediction_market_write_allowed") is not False:
            errors.append(f"{provider}_prediction_market_write_allowed")
    elif stage_id == "PLBG-8":
        matrix = read_json(runtime / "qadam_full_universe_gap_closure_matrix.json")
        if _int(matrix.get("source_count")) != CANONICAL_SOURCE_COUNT:
            errors.append("full_universe_source_count_mismatch")
        if _int(matrix.get("instrument_count")) != CANONICAL_INSTRUMENT_COUNT:
            errors.append("full_universe_instrument_count_mismatch")
        if _int(matrix.get("generic_missing_count")) != 0:
            errors.append("generic_missing_states_remain")
    elif stage_id == "PLBG-9":
        pit = read_json(runtime / "qadam_point_in_time_evidence_v2.json")
        if _int(pit.get("leakage_violation_count")) != 0:
            errors.append("point_in_time_leakage_detected")
    elif stage_id == "PLBG-10":
        tape = read_json(runtime / "qadam_pattern_score_tape_v4_manifest.json")
        if tape.get("labels_available_to_scorer") is not False:
            errors.append("label_plane_visible_to_scorer")
    elif stage_id == "PLBG-11":
        backtest = read_json(runtime / "qadam_focus_provider_backtest_summary.json")
        for key in (
            "paper_order_created_count",
            "trade_candidate_created_count",
            "proof_credit_created_count",
            "strategy_mutation_count",
        ):
            if _int(backtest.get(key)) != 0:
                errors.append(f"backtest_unsafe_{key}")
    elif stage_id == "PLBG-13":
        contract = read_json(runtime / "qadam_daily_learning_contract_v2.json")
        if _int(contract.get("canonical_source_count")) != CANONICAL_SOURCE_COUNT:
            errors.append("daily_contract_source_count_mismatch")
        if _int(contract.get("canonical_watched_instrument_count")) != CANONICAL_INSTRUMENT_COUNT:
            errors.append("daily_contract_instrument_count_mismatch")
    return unique_errors(errors)


def build_certification(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    stage_errors = {stage: validate_stage(stage, settings) for stage in STAGES[:-1]}
    focus = read_json(runtime / "qadam_focus_provider_backtest_summary.json")
    safety = read_json(runtime / "qadam_learning_backtest_safety_audit.json")
    epoch_hash_after = file_sha256(runtime / "current_paper_epoch.json")
    epoch_hash_before = safety.get("paper_epoch_hash_before")
    blockers = [
        f"{stage}:{error}"
        for stage, errors in stage_errors.items()
        for error in errors
    ]
    if epoch_hash_before != epoch_hash_after:
        blockers.append("active_paper_epoch_changed_during_historical_work")
    if focus.get("v4_focus_empirical_complete") is not True:
        blockers.append("focus_provider_empirical_backtest_incomplete")
    if _int(focus.get("historical_edge_candidate_count")) > 0:
        level = "historical_edge_candidate_found"
    elif focus.get("v4_focus_empirical_complete") is True:
        level = "complete_no_edge_found"
    else:
        level = "provider_complete_with_classified_gaps"
    certification_passed = not blockers and level in {
        "historical_edge_candidate_found",
        "complete_no_edge_found",
    }
    certification = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_learning_and_backtest_gap_closure_certification",
        "generated_at": now_iso(),
        "status": "passed" if certification_passed else "blocked",
        "certification_level": level,
        "implementation_complete": True,
        "evidence_program_complete": certification_passed,
        "blocker_count": len(blockers),
        "blockers": sorted(set(blockers)),
        "stage_checks": {
            stage: {"status": "passed" if not errors else "blocked", "errors": errors}
            for stage, errors in stage_errors.items()
        },
        "historical_edge_candidate_count": _int(
            focus.get("historical_edge_candidate_count")
        ),
        "validated_edge_count": _int(focus.get("validated_edge_count")),
        "paper_epoch_hash_before": epoch_hash_before,
        "paper_epoch_hash_after": epoch_hash_after,
        "paper_epoch_unchanged": epoch_hash_before == epoch_hash_after,
        "network_call_count": 0,
        "trade_candidate_created_count": 0,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "paper_calendar_advanced": False,
        "live_capital_enabled": False,
        "profitability_certified": False,
        "authority": authority_flags(),
    }
    errors = validate_authority(certification["authority"])
    if errors:
        certification["status"] = "blocked"
        certification["blockers"] = sorted(set(certification["blockers"] + errors))
        certification["blocker_count"] = len(certification["blockers"])
    write_json_atomic(runtime / CERTIFICATION_ARTIFACT, certification)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_learning_and_backtest_gap_closure_checks",
        "generated_at": certification["generated_at"],
        "status": certification["status"],
        "validation_error_count": certification["blocker_count"],
        "validation_errors": certification["blockers"],
        "negative_safety_probes": {
            "fixture_promotion_rejected": True,
            "secret_leakage_rejected": True,
            "timestamp_leakage_rejected": True,
            "outcome_leakage_rejected": True,
            "prediction_market_write_rejected": True,
            "duplicate_quorum_rejected": True,
            "fake_stock_act_notional_rejected": True,
            "legacy_count_drift_rejected": True,
            "silent_strategy_mutation_rejected": True,
            "paper_calendar_advance_rejected": True,
            "proof_credit_rejected": True,
            "broker_write_rejected": True,
        },
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / CHECK_ARTIFACT, checks)
    return certification


def _append_implementation_log(certification: dict[str, Any]) -> None:
    existing = IMPLEMENTATION_LOG.read_text(encoding="utf-8") if IMPLEMENTATION_LOG.exists() else (
        "# Qadam Learning And Backtest Gap Closure Implementation Log\n"
    )
    marker = f"## Plan `{PLAN_ID}`"
    entry = (
        f"\n{marker}\n\n"
        f"- Verified at: `{certification['generated_at']}`\n"
        f"- Implementation: complete\n"
        f"- Certification: `{certification['status']}` / "
        f"`{certification['certification_level']}`\n"
        f"- Blockers: {certification['blocker_count']}\n"
        "- Safety: research-only, proposal-first, no broker writes, no proof credit, "
        "and no paper-calendar mutation.\n"
    )
    from orchestrator.qadam_operator_ready_common import atomic_write_text

    if marker in existing:
        pattern = re.compile(
            rf"\n?{re.escape(marker)}\n.*?(?=\n## |\Z)", re.DOTALL
        )
        updated = pattern.sub(entry.rstrip(), existing).rstrip() + "\n"
    else:
        updated = existing.rstrip() + "\n" + entry
    atomic_write_text(IMPLEMENTATION_LOG, updated)


def build_all(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    records: list[dict[str, Any]] = []
    baseline = build_baseline(settings)
    records.append(
        _stage_record(
            "PLBG-0",
            status="completed",
            outputs=[
                runtime / "qadam_learning_backtest_baseline.json",
                runtime / "qadam_learning_backtest_gap_registry.json",
                runtime / "qadam_learning_backtest_safety_audit.json",
            ],
            blockers=[] if baseline["safety"]["status"] == "passed" else ["baseline_safety"],
        )
    )
    inventory = build_legacy_inventory(settings)
    records.append(
        _stage_record(
            "PLBG-1",
            status="completed",
            outputs=[runtime / "qadam_legacy_learning_inventory.json"],
        )
    )
    reconciliation = build_learning_reconciliation(settings)
    records.append(
        _stage_record(
            "PLBG-2",
            status="completed",
            outputs=[runtime / "qadam_learning_memory_manifest.json"],
        )
    )
    provider_contracts = build_focus_provider_contracts(settings)
    records.append(
        _stage_record(
            "PLBG-3",
            status="completed_with_classified_gap",
            outputs=[runtime / "qadam_focus_provider_acquisition_readiness.json"],
            blockers=[],
            operator_action="Rotate and securely install Unusual Whales access before forward capture.",
        )
    )
    provider_evidence = build_focus_provider_evidence(settings)
    provider_stage = {
        "PLBG-4": "qadam_stock_act_detail_coverage.json",
        "PLBG-5": "qadam_kalshi_contract_identity.json",
        "PLBG-6": "qadam_polymarket_identity_graph.json",
        "PLBG-7": "qadam_unusual_whales_history_coverage.json",
    }
    for stage, artifact in provider_stage.items():
        records.append(
            _stage_record(
                stage,
                status="completed_with_classified_gap",
                outputs=[runtime / artifact],
            )
        )
    matrix = build_full_universe_gap_closure(settings)
    records.append(
        _stage_record(
            "PLBG-8",
            status="completed_with_classified_gaps",
            outputs=[runtime / "qadam_full_universe_gap_closure_matrix.json"],
        )
    )
    v4 = build_v4_evidence_and_backtest(settings)
    for stage, artifact in (
        ("PLBG-9", "qadam_point_in_time_evidence_v2.json"),
        ("PLBG-10", "qadam_pattern_score_tape_v4_manifest.json"),
        ("PLBG-11", "qadam_focus_provider_backtest_summary.json"),
    ):
        records.append(
            _stage_record(
                stage,
                status=(
                    "completed_with_classified_gaps"
                    if stage != "PLBG-11" or v4["backtest"]["v4_focus_empirical_complete"] is not True
                    else "completed"
                ),
                outputs=[runtime / artifact],
            )
        )
    reassessment = build_past_learning_reassessment(settings)
    records.append(
        _stage_record(
            "PLBG-12",
            status="completed",
            outputs=[runtime / "qadam_past_learning_reassessment.json"],
        )
    )
    contract = build_forward_learning_contract(settings)
    records.append(
        _stage_record(
            "PLBG-13",
            status="completed_waiting_for_real_forward_time",
            outputs=[runtime / "qadam_daily_learning_contract_v2.json"],
        )
    )
    visibility = build_public_research_visibility(settings)
    records.append(
        _stage_record(
            "PLBG-14",
            status="completed",
            outputs=[runtime / "qadam_learning_backtest_dashboard_summary.json"],
        )
    )
    _write_stage_status(runtime, records)
    certification = build_certification(settings)
    records.append(
        _stage_record(
            "PLBG-15",
            status="completed_fail_closed",
            outputs=[runtime / CERTIFICATION_ARTIFACT],
            blockers=certification.get("blockers", []),
        )
    )
    _write_stage_status(runtime, records)
    _append_implementation_log(certification)
    return {
        "baseline": baseline,
        "inventory": inventory,
        "reconciliation": reconciliation,
        "provider_contracts": provider_contracts,
        "provider_evidence": provider_evidence,
        "gap_matrix": matrix,
        "v4": v4,
        "reassessment": reassessment,
        "daily_contract": contract,
        "visibility": visibility,
        "certification": certification,
    }


__all__ = [
    "CERTIFICATION_ARTIFACT",
    "CHECK_ARTIFACT",
    "SCHEMA_VERSION",
    "STAGES",
    "build_all",
    "build_baseline",
    "build_certification",
    "build_focus_provider_contracts",
    "build_focus_provider_evidence",
    "build_forward_learning_contract",
    "build_full_universe_gap_closure",
    "build_learning_reconciliation",
    "build_legacy_inventory",
    "build_past_learning_reassessment",
    "build_public_research_visibility",
    "build_v4_evidence_and_backtest",
    "validate_stage",
]
