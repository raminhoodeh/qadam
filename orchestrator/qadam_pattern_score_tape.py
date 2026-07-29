"""OR-6 provider-backed, immutable historical Pattern Score V3 tape."""

from __future__ import annotations

from collections import Counter, defaultdict
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import shutil
from statistics import fmean, pstdev
import tempfile
import time
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    authority_flags,
    canonical_json,
    file_sha256,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_text,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_pattern_score_v3 import score_pattern_feature_vector
from orchestrator.qadam_wave_b_common import (
    contains_forbidden_key,
    parse_timestamp,
    record_set_hash,
    safe_float,
    stable_id,
    write_jsonl_atomic,
)

SCHEMA_VERSION = "qadam_pattern_score_tape.v2"
PHASE_ID = "OR-6"

MANIFEST_ARTIFACT = "qadam_pattern_score_tape_manifest.json"
PROGRESS_ARTIFACT = "qadam_pattern_score_tape_progress.json"
QUALITY_ARTIFACT = "qadam_pattern_score_tape_quality.json"
CHECK_ARTIFACT = "qadam_pattern_score_tape_checks.json"

SCORE_PRIMARY_ARTIFACT = "qadam_pattern_score_v3.json"
SCORE_RECORDS_ARTIFACT = "qadam_pattern_score_v3_records.jsonl"
PROVIDER_ALIGNMENT_ARTIFACT = "qadam_provider_point_in_time_alignment.json"
SOURCE_UNIVERSE_ARTIFACT = "qsase_source_universe.json"
TRADING_UNIVERSE_ARTIFACT = "qsase_trading_universe.json"
ELIGIBILITY_ARTIFACT = "qadam_relationship_eligibility_graph.jsonl"
UNUSUAL_WHALES_FEATURE_MANIFEST_ARTIFACT = (
    "unusual_whales_backtest_feature_manifest.json"
)

RESEARCH_TAPE_ROOT = ROOT / "data" / "research" / "pattern_score_tape"
INPUT_SNAPSHOT_CAPTURE_ATTEMPTS = 3
INPUT_SNAPSHOT_CONTRACT_VERSION = "qadam_pattern_score_input_snapshot.v1"
REQUIRED_INPUT_ARTIFACTS = (
    SCORE_RECORDS_ARTIFACT,
    SCORE_PRIMARY_ARTIFACT,
    PROVIDER_ALIGNMENT_ARTIFACT,
    SOURCE_UNIVERSE_ARTIFACT,
    TRADING_UNIVERSE_ARTIFACT,
    ELIGIBILITY_ARTIFACT,
)
OPTIONAL_INPUT_ARTIFACTS = (UNUSUAL_WHALES_FEATURE_MANIFEST_ARTIFACT,)
FORBIDDEN_TAPE_KEYS = {
    "forward_return",
    "gross_return",
    "net_return",
    "price_after",
    "outcome",
    "label",
    "max_favorable_excursion",
    "max_adverse_excursion",
    "realized_return",
}
FUTURE_ONLY_ALIGNMENT_KEYS = {
    "available_horizons",
    "future_horizon_availability",
    "future_label_values_included",
}
SAFE_SNAPSHOT_KEYS = {
    "source_event_count",
    "source_numeric_feature_means",
    "source_record_type_counts",
    "first_event_at",
    "last_event_at",
    "baseline_price_observed_at",
    "baseline_price_available_at",
    "baseline_close",
    "baseline_volume",
}
MAPPING_STRENGTH = {
    "causal_strategy_mapping": 1.0,
    "broad_discovery_mapping": 0.5,
    "negative_control": 0.0,
}


class ScoreTapeInputSnapshotRace(ValueError):
    """Raised when a producer changes an input while it is being pinned."""


class ScoreTapeInputIntegrityHold(ValueError):
    """Raised when stable pinned inputs disagree with their declared lineage."""


def _relative_or_name(path: Path, *, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return path.name


def _copy_small_snapshot_input(source: Path, target: Path) -> dict[str, Any]:
    """Copy one control artifact and prove that the source stayed unchanged."""
    if not source.is_file():
        raise ScoreTapeInputIntegrityHold(
            f"score_tape_input_snapshot_integrity_hold:missing:{source.name}"
        )
    before = source.stat()
    before_hash = file_sha256(source)
    if not before_hash:
        raise ScoreTapeInputIntegrityHold(
            f"score_tape_input_snapshot_integrity_hold:unreadable:{source.name}"
        )
    shutil.copy2(source, target)
    after = source.stat()
    after_hash = file_sha256(source)
    pinned_hash = file_sha256(target)
    if (
        before.st_ino != after.st_ino
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or before_hash != after_hash
        or pinned_hash != before_hash
    ):
        raise ScoreTapeInputSnapshotRace(
            f"score_tape_input_snapshot_unstable:{source.name}"
        )
    return {
        "name": source.name,
        "size_bytes": target.stat().st_size,
        "sha256": pinned_hash,
        "capture_mode": "copied_control_artifact",
    }


def _pin_atomic_alignment(source: Path, target: Path) -> dict[str, Any]:
    """Pin the large alignment inode while its producer may publish a successor."""
    if not source.is_file():
        raise ScoreTapeInputIntegrityHold(
            "score_tape_input_snapshot_integrity_hold:missing:provider_alignment_records"
        )
    before = source.stat()
    try:
        os.link(source, target)
        capture_mode = "hardlink_to_atomic_generation"
    except OSError:
        shutil.copy2(source, target)
        capture_mode = "copied_alignment_fallback"
    pinned_hash = file_sha256(target)
    if not pinned_hash:
        raise ScoreTapeInputIntegrityHold(
            "score_tape_input_snapshot_integrity_hold:unreadable:provider_alignment_records"
        )
    return {
        "name": "provider_alignment_records.jsonl",
        "size_bytes": target.stat().st_size,
        "sha256": pinned_hash,
        "capture_mode": capture_mode,
        "source_inode_at_capture": before.st_ino,
    }


def _capture_score_tape_input_snapshot_once(
    runtime: Path,
    snapshot_path: Path,
    *,
    root: Path,
    attempt: int,
) -> dict[str, Any]:
    paths: dict[str, Path | None] = {}
    files: list[dict[str, Any]] = []
    for artifact in REQUIRED_INPUT_ARTIFACTS:
        source = runtime / artifact
        target = snapshot_path / artifact
        record = _copy_small_snapshot_input(source, target)
        record["source_path"] = _relative_or_name(source, root=root)
        paths[artifact] = target
        files.append(record)
    for artifact in OPTIONAL_INPUT_ARTIFACTS:
        source = runtime / artifact
        if not source.is_file():
            paths[artifact] = None
            files.append(
                {
                    "name": artifact,
                    "source_path": _relative_or_name(source, root=root),
                    "present": False,
                    "optional": True,
                }
            )
            continue
        target = snapshot_path / artifact
        record = _copy_small_snapshot_input(source, target)
        record.update(
            {
                "source_path": _relative_or_name(source, root=root),
                "present": True,
                "optional": True,
            }
        )
        paths[artifact] = target
        files.append(record)

    manifest = read_json(paths[PROVIDER_ALIGNMENT_ARTIFACT])
    alignment_relative = str(manifest.get("alignment_records_path") or "")
    alignment_source = root / alignment_relative
    pinned_alignment = snapshot_path / "provider_alignment_records.jsonl"
    alignment_record = _pin_atomic_alignment(alignment_source, pinned_alignment)
    alignment_record["source_path"] = _relative_or_name(alignment_source, root=root)
    paths["provider_alignment_records"] = pinned_alignment
    files.append(alignment_record)

    expected_alignment_sha = str(manifest.get("alignment_records_sha256") or "")
    if (
        manifest.get("status") != "provider_alignment_ready"
        or not expected_alignment_sha
        or alignment_record["sha256"] != expected_alignment_sha
    ):
        raise ScoreTapeInputSnapshotRace(
            "score_tape_input_snapshot_unstable:provider_alignment_generation"
        )

    identity = {
        "contract_version": INPUT_SNAPSHOT_CONTRACT_VERSION,
        "files": {
            str(record.get("name")): record.get("sha256")
            for record in files
            if record.get("sha256")
        },
    }
    return {
        "contract_version": INPUT_SNAPSHOT_CONTRACT_VERSION,
        "snapshot_id": "score-input-snapshot:"
        + sha256_text(canonical_json(identity))[:24],
        "capture_attempt": attempt,
        "capture_attempt_limit": INPUT_SNAPSHOT_CAPTURE_ATTEMPTS,
        "pinned_during_execution": True,
        "source_changed_during_capture": False,
        "alignment_generation_verified": True,
        "temporary_copy_removed_after_execution": True,
        "files": files,
        "paths": paths,
        "alignment_source_path": alignment_source,
    }


@contextmanager
def pinned_score_tape_inputs(
    runtime: Path,
    *,
    root: Path | None = None,
    capture_attempts: int = INPUT_SNAPSHOT_CAPTURE_ATTEMPTS,
):
    """Yield one internally consistent, immutable input view for a score run."""
    root = (root or ROOT).resolve()
    RESEARCH_TAPE_ROOT.mkdir(parents=True, exist_ok=True)
    attempts = max(1, int(capture_attempts))
    last_race: ScoreTapeInputSnapshotRace | None = None
    for attempt in range(1, attempts + 1):
        temporary = tempfile.TemporaryDirectory(
            prefix=".input-snapshot-",
            dir=RESEARCH_TAPE_ROOT,
        )
        snapshot_path = Path(temporary.name)
        try:
            snapshot = _capture_score_tape_input_snapshot_once(
                runtime,
                snapshot_path,
                root=root,
                attempt=attempt,
            )
        except ScoreTapeInputSnapshotRace as exc:
            temporary.cleanup()
            last_race = exc
            if attempt < attempts:
                time.sleep(min(0.05 * (2 ** (attempt - 1)), 0.2))
                continue
            raise
        except BaseException:
            temporary.cleanup()
            raise
        try:
            yield snapshot
        finally:
            temporary.cleanup()
        return
    if last_race is not None:
        raise last_race


def _slug(value: Any) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "_", str(value or "unknown"))
    return normalized.strip("_").lower() or "unknown"


def _mean(values: list[float], default: float = 0.0) -> float:
    return round(fmean(values), 10) if values else default


def _safe_numeric_map(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, float] = {}
    for key, raw in sorted(value.items()):
        key_text = str(key)
        if key_text in FORBIDDEN_TAPE_KEYS or key_text.startswith(
            ("future_", "outcome_", "label_")
        ):
            continue
        if isinstance(raw, bool):
            continue
        try:
            result[key_text] = float(raw)
        except (TypeError, ValueError):
            continue
    return result


def historical_scoring_input(record: dict[str, Any]) -> dict[str, Any]:
    """Whitelist only information available at the historical decision time."""
    if record.get("future_label_values_included") is not False:
        raise ValueError("historical_alignment_future_label_boundary_invalid")
    if record.get("point_in_time_safe") is not True:
        raise ValueError("historical_alignment_not_point_in_time_safe")
    if record.get("score_before_label_boundary") is not True:
        raise ValueError("historical_alignment_score_before_label_boundary_missing")

    decision = parse_timestamp(record.get("decision_at"))
    source_available = parse_timestamp(record.get("source_available_at"))
    snapshot = record.get("feature_snapshot")
    if decision is None or source_available is None or not isinstance(snapshot, dict):
        raise ValueError("historical_alignment_required_timestamp_or_snapshot_missing")
    if source_available > decision:
        raise ValueError("historical_alignment_source_available_after_decision")
    if contains_forbidden_key(snapshot, FORBIDDEN_TAPE_KEYS):
        raise ValueError("historical_alignment_snapshot_contains_label_fields")

    baseline_available = parse_timestamp(snapshot.get("baseline_price_available_at"))
    if baseline_available is None or baseline_available > decision:
        raise ValueError("historical_alignment_market_available_after_decision")
    baseline_close = safe_float(snapshot.get("baseline_close"), -1.0)
    if baseline_close <= 0:
        raise ValueError("historical_alignment_baseline_price_invalid")

    safe_snapshot = {
        key: snapshot.get(key)
        for key in SAFE_SNAPSHOT_KEYS
        if key in snapshot
    }
    safe_snapshot["source_numeric_feature_means"] = _safe_numeric_map(
        safe_snapshot.get("source_numeric_feature_means")
    )
    record_types = safe_snapshot.get("source_record_type_counts")
    if not isinstance(record_types, dict):
        record_types = {}
    safe_snapshot["source_record_type_counts"] = {
        str(key): int(value)
        for key, value in sorted(record_types.items())
        if not isinstance(value, bool)
        and isinstance(value, (int, float))
    }
    provenance = record.get("provenance")
    safe_provenance = {
        key: provenance.get(key)
        for key in (
            "source_partition_paths",
            "price_partition_path",
            "price_provider",
            "price_availability_policy",
        )
        if isinstance(provenance, dict) and key in provenance
    }
    return {
        "alignment_record_id": record.get("alignment_record_id"),
        "relationship_id": record.get("relationship_id"),
        "source_key": str(record.get("source_key") or "unknown"),
        "instrument": str(record.get("instrument") or "unknown"),
        "mapping_class": str(record.get("mapping_class") or "unknown"),
        "negative_control": bool(
            record.get("negative_control") is True
            or record.get("mapping_class") == "negative_control"
        ),
        "source_available_at": source_available.isoformat(),
        "decision_at": decision.isoformat(),
        "feature_snapshot": safe_snapshot,
        "provenance": safe_provenance,
    }


def score_tape_partition_id(score: dict[str, Any]) -> str:
    return stable_id(
        "score-tape-partition",
        score.get("strategy_family_id") or "strategy_agnostic",
        score.get("instrument"),
        str(score.get("scoring_as_of") or "historical_date_partition_pending")[:4],
        score.get("horizon_hypothesis"),
        score.get("model_version"),
        score.get("stage1_learning_input_version"),
    )


def build_score_tape_row(
    score_template: dict[str, Any],
    historical_feature_snapshot: dict[str, Any],
    *,
    scoring_as_of: str,
) -> dict[str, Any]:
    """Build a small unit-testable immutable row without score-side labels."""
    if contains_forbidden_key(score_template, FORBIDDEN_TAPE_KEYS):
        raise ValueError("score_template_contains_label_fields")
    if contains_forbidden_key(historical_feature_snapshot, FORBIDDEN_TAPE_KEYS):
        raise ValueError("historical_feature_snapshot_contains_label_fields")
    fingerprint = sha256_text(
        canonical_json(
            {
                "model_version": score_template.get("model_version"),
                "strategy_family_id": score_template.get("strategy_family_id"),
                "instrument": score_template.get("instrument"),
                "horizon": score_template.get("horizon_hypothesis"),
                "scoring_as_of": scoring_as_of,
                "historical_feature_snapshot": historical_feature_snapshot,
                "applied_learning_version_ids": score_template.get(
                    "applied_learning_version_ids", []
                ),
                "stage1_learning_input_version": score_template.get(
                    "stage1_learning_input_version"
                ),
            }
        )
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_pattern_score_tape_row",
        "score_id": stable_id("historical-pattern-score", fingerprint),
        "source_score_template_id": score_template.get("score_id"),
        "model_version": score_template.get("model_version"),
        "feature_set_version": score_template.get("feature_set_version"),
        "strategy_family_id": score_template.get("strategy_family_id"),
        "instrument": score_template.get("instrument"),
        "direction_hypothesis": score_template.get("direction_hypothesis"),
        "horizon_hypothesis": score_template.get("horizon_hypothesis"),
        "scoring_as_of": scoring_as_of,
        "feature_snapshot": historical_feature_snapshot,
        "input_fingerprint": fingerprint,
        "applied_learning_version_ids": score_template.get(
            "applied_learning_version_ids", []
        ),
        "stage1_learning_input_version": score_template.get(
            "stage1_learning_input_version"
        ),
        "immutable": True,
        "label_columns_present": False,
        "labels_accessed": False,
        "future_horizon_metadata_accessed": False,
        "frontier_llm_called": False,
        "candidate_creation_allowed": False,
        "order_creation_allowed": False,
        "authority": authority_flags(),
    }


def write_score_tape_partition(path: Path, rows: list[dict[str, Any]]) -> str:
    """Write once, or verify an identical completed partition during resume."""
    resolved = path.resolve()
    if not resolved.is_relative_to(RESEARCH_TAPE_ROOT.resolve()):
        raise ValueError("score_tape_path_outside_research_store")
    for row in rows:
        if contains_forbidden_key(row, FORBIDDEN_TAPE_KEYS):
            raise ValueError("score_tape_row_contains_label_fields")
    expected_hash = record_set_hash(rows)
    if resolved.exists():
        actual_hash = record_set_hash(read_jsonl(resolved))
        if actual_hash != expected_hash:
            raise ScoreTapeInputIntegrityHold(
                "completed_score_tape_partition_immutable_mismatch:"
                f"{resolved.name}:expected={expected_hash[:16]}:actual={actual_hash[:16]}"
            )
        return expected_hash
    write_jsonl_atomic(resolved, rows)
    return expected_hash


def _template_source_keys(template: dict[str, Any]) -> set[str]:
    return {
        str(row.get("source_key"))
        for row in template.get("feature_inputs", [])
        if isinstance(row, dict) and row.get("source_key")
    }


def _historical_market_context(
    price_points: dict[str, dict[str, dict[str, Any]]]
) -> dict[tuple[str, str], dict[str, Any]]:
    contexts: dict[tuple[str, str], dict[str, Any]] = {}
    for instrument, points_by_time in price_points.items():
        trailing_returns: list[float] = []
        trailing_volumes: list[float] = []
        previous_close: float | None = None
        for decision_at, point in sorted(points_by_time.items()):
            close = safe_float(point.get("baseline_close"), -1.0)
            volume = safe_float(point.get("baseline_volume"), -1.0)
            if previous_close and close > 0:
                trailing_returns.append((close / previous_close) - 1.0)
            if volume >= 0:
                trailing_volumes.append(volume)
            returns_20 = trailing_returns[-20:]
            volumes_20 = trailing_volumes[-20:]
            volatility = pstdev(returns_20) if len(returns_20) >= 20 else None
            volume_mean = fmean(volumes_20) if len(volumes_20) >= 20 else None
            volume_ratio = (
                volume / volume_mean
                if volume_mean is not None and volume_mean > 0 and volume >= 0
                else None
            )
            if volatility is None:
                regime = "insufficient_trailing_history"
            elif volatility < 0.012:
                regime = "calm"
            elif volatility < 0.03:
                regime = "normal"
            else:
                regime = "elevated_volatility"
            contexts[(instrument, decision_at)] = {
                "baseline_close": close,
                "baseline_volume": volume if volume >= 0 else None,
                "trailing_return_observation_count": len(returns_20),
                "trailing_volume_observation_count": len(volumes_20),
                "rolling_volatility_20_observation": (
                    round(volatility, 10) if volatility is not None else None
                ),
                "volume_relative_to_20_observation_mean": (
                    round(volume_ratio, 10) if volume_ratio is not None else None
                ),
                "regime_state": regime,
                "context_is_event_aligned_and_backward_looking": True,
            }
            if close > 0:
                previous_close = close
    return contexts


def _build_historical_score_row(
    template: dict[str, Any],
    inputs: list[dict[str, Any]],
    *,
    source_trust: dict[str, float],
    relationship_by_id: dict[str, dict[str, Any]],
    market_context: dict[str, Any],
    paperability: dict[str, bool],
    alignment_sha256: str,
) -> dict[str, Any]:
    decision_at = str(inputs[0]["decision_at"])
    instrument = str(inputs[0]["instrument"])
    source_rows: list[dict[str, Any]] = []
    freshness_values: list[float] = []
    mapping_values: list[float] = []
    numeric_totals: defaultdict[str, list[float]] = defaultdict(list)
    record_type_counts: Counter[str] = Counter()
    event_count = 0
    for item in sorted(inputs, key=lambda row: str(row["alignment_record_id"])):
        relationship = relationship_by_id.get(str(item.get("relationship_id")), {})
        decision = parse_timestamp(decision_at)
        available = parse_timestamp(item.get("source_available_at"))
        age_days = (
            max(0.0, (decision - available).total_seconds() / 86_400.0)
            if decision is not None and available is not None
            else 7.0
        )
        freshness_values.append(max(0.0, 1.0 - min(age_days, 7.0) / 7.0))
        mapping_values.append(MAPPING_STRENGTH.get(item["mapping_class"], 0.0))
        snapshot = item["feature_snapshot"]
        item_event_count = max(1, int(snapshot.get("source_event_count") or 0))
        event_count += item_event_count
        for key, value in snapshot.get("source_numeric_feature_means", {}).items():
            numeric_totals[key].append(float(value))
        record_type_counts.update(snapshot.get("source_record_type_counts", {}))
        source_key = str(item["source_key"])
        source_rows.append(
            {
                "alignment_record_id": item.get("alignment_record_id"),
                "relationship_id": item.get("relationship_id"),
                "source_key": source_key,
                "source_available_at": item.get("source_available_at"),
                "trust_score": source_trust.get(source_key, 0.5),
                "mapping_class": item.get("mapping_class"),
                "source_independence_cluster_id": relationship.get(
                    "source_independence_cluster_id"
                ),
                "source_event_count": item_event_count,
            }
        )

    distinct_sources = {row["source_key"] for row in source_rows}
    clusters = {
        row["source_independence_cluster_id"]
        for row in source_rows
        if row.get("source_independence_cluster_id")
    }
    source_count = len(distinct_sources)
    independent_count = len(clusters) or source_count
    strategy_agnostic = template.get("strategy_agnostic") is True
    negative_control = bool(
        template.get("negative_control") is True
        or all(item.get("negative_control") is True for item in inputs)
    )
    features = {
        "source_trust": _mean(
            [source_trust.get(source, 0.5) for source in sorted(distinct_sources)]
        ),
        "source_freshness": _mean(freshness_values),
        "fresh_source_quorum": min(1.0, independent_count / 2.0),
        "source_independence": min(1.0, independent_count / max(source_count, 1)),
        "causal_mapping_strength": _mean(mapping_values),
        "current_market_price": float(market_context.get("baseline_close") is not None),
        "volatility_context": float(
            market_context.get("rolling_volatility_20_observation") is not None
        ),
        "volume_or_flow_context": float(
            market_context.get("volume_relative_to_20_observation_mean") is not None
        ),
        "paperability_context": float(paperability.get(instrument, False)),
        "strategy_fit": 0.0 if strategy_agnostic else 1.0,
        "negative_control": float(negative_control),
    }
    missing: list[str] = []
    if features["fresh_source_quorum"] < 1.0:
        missing.append("fresh_source_quorum")
    for feature in (
        "current_market_price",
        "volatility_context",
        "volume_or_flow_context",
    ):
        if not features[feature]:
            missing.append(feature)
    scored = score_pattern_feature_vector(
        features,
        missing_critical_features=missing,
        negative_control=negative_control,
    )
    strategy_id = template.get("strategy_family_id") or "strategy_agnostic"
    source_context = {
        "source_event_count": event_count,
        "distinct_source_count": source_count,
        "independent_source_cluster_count": independent_count,
        "source_numeric_feature_means": {
            key: _mean(values) for key, values in sorted(numeric_totals.items())
        },
        "source_record_type_counts": dict(sorted(record_type_counts.items())),
    }
    input_material = {
        "model_version": template.get("model_version"),
        "feature_set_version": template.get("feature_set_version"),
        "source_score_template_id": template.get("score_id"),
        "strategy_family_id": strategy_id,
        "instrument": instrument,
        "scoring_as_of": decision_at,
        "features": scored["features"],
        "source_context": source_context,
        "market_context": market_context,
        "source_rows": source_rows,
        "applied_learning_version_ids": template.get(
            "applied_learning_version_ids", []
        ),
        "stage1_learning_input_version": template.get(
            "stage1_learning_input_version"
        ),
        "alignment_sha256": alignment_sha256,
    }
    fingerprint = sha256_text(canonical_json(input_material))
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_pattern_score_tape_row",
        "phase_id": PHASE_ID,
        "score_id": stable_id(
            "historical-pattern-score",
            template.get("model_version"),
            fingerprint,
        ),
        "source_score_template_id": template.get("score_id"),
        "model_version": template.get("model_version"),
        "feature_set_version": template.get("feature_set_version"),
        "input_fingerprint": fingerprint,
        "upstream_alignment_sha256": alignment_sha256,
        "input_alignment_record_ids": [
            row["alignment_record_id"] for row in source_rows
        ],
        "strategy_family_id": strategy_id,
        "strategy_label": template.get("strategy_label"),
        "strategy_agnostic": strategy_agnostic,
        "negative_control": negative_control,
        "instrument": instrument,
        "market_family": template.get("market_family"),
        "direction_hypothesis": template.get("direction_hypothesis"),
        "horizon_hypothesis": template.get("horizon_hypothesis"),
        "scoring_as_of": decision_at,
        "decision_date": decision_at[:10],
        "regime_state": market_context.get("regime_state"),
        "features": scored["features"],
        "feature_inputs": source_rows,
        "historical_source_context": source_context,
        "historical_market_context": market_context,
        "component_contributions": scored["component_contributions"],
        "penalties": scored["penalties"],
        "gross_component_score": scored["gross_component_score"],
        "penalty_total": scored["penalty_total"],
        "raw_pattern_score": scored["raw_pattern_score"],
        "score_is_probability": False,
        "score_is_validated_edge": False,
        "score_state": (
            "scored_with_missing_context"
            if scored["missing_critical_features"]
            else "score_ready_for_or7_labeling"
        ),
        "confidence_state": scored["confidence_state"],
        "missing_critical_features": scored["missing_critical_features"],
        "permitted_next_action": (
            "retain_for_research_audit_and_or7_labeling"
            if scored["missing_critical_features"]
            else "expose_to_or7_labeler_research_only"
        ),
        "label_columns_present": False,
        "labels_accessed": False,
        "future_horizon_metadata_accessed": False,
        "frontier_llm_called": False,
        "local_llm_called": False,
        "candidate_creation_allowed": False,
        "order_creation_allowed": False,
        "applied_learning_version_ids": template.get(
            "applied_learning_version_ids", []
        ),
        "stage1_learning_input_version": template.get(
            "stage1_learning_input_version"
        ),
        "immutable": True,
        "authority_contract_ref": f"data/runtime/{MANIFEST_ARTIFACT}#authority",
    }


def _score_distribution(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scores = sorted(safe_float(row.get("raw_pattern_score")) for row in rows)
    if not scores:
        return {"count": 0, "minimum": None, "mean": None, "maximum": None}
    return {
        "count": len(scores),
        "minimum": round(scores[0], 8),
        "mean": round(fmean(scores), 8),
        "maximum": round(scores[-1], 8),
    }


def _drift_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_year: defaultdict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_year[str(row.get("decision_date") or "unknown")[:4]].append(
            safe_float(row.get("raw_pattern_score"))
        )
    yearly = [
        {"year": year, "count": len(values), "mean_score": round(fmean(values), 8)}
        for year, values in sorted(by_year.items())
    ]
    changes = [
        round(abs(current["mean_score"] - previous["mean_score"]), 8)
        for previous, current in zip(yearly, yearly[1:])
    ]
    maximum_change = max(changes, default=0.0)
    return {
        "method": "absolute_change_in_calendar_year_mean_score",
        "review_threshold": 0.15,
        "maximum_year_over_year_mean_change": maximum_change,
        "state": "review_required" if maximum_change > 0.15 else "within_guardrail",
        "yearly_score_distribution": yearly,
        "drift_is_research_diagnostic_not_trade_authority": True,
    }


def _load_alignment_groups(
    alignment_path: Path,
    templates: list[dict[str, Any]],
) -> tuple[
    dict[tuple[str, str], dict[str, Any]],
    dict[str, dict[str, dict[str, Any]]],
    list[dict[str, Any]],
    set[str],
    int,
]:
    agnostic_by_instrument: dict[str, dict[str, Any]] = {}
    controls_by_instrument: dict[str, dict[str, Any]] = {}
    configured_by_pair: defaultdict[tuple[str, str], list[dict[str, Any]]] = (
        defaultdict(list)
    )
    for template in templates:
        instrument = str(template.get("instrument") or "unknown")
        if template.get("negative_control") is True:
            controls_by_instrument[instrument] = template
        elif template.get("strategy_agnostic") is True:
            agnostic_by_instrument[instrument] = template
        else:
            for source_key in _template_source_keys(template):
                configured_by_pair[(instrument, source_key)].append(template)

    groups: dict[tuple[str, str], dict[str, Any]] = {}
    price_points: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    rejections: list[dict[str, Any]] = []
    consumed_alignment_ids: set[str] = set()
    input_count = 0
    with alignment_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            input_count += 1
            payload: Any = None
            try:
                payload = json.loads(line)
                safe_input = historical_scoring_input(payload)
            except (json.JSONDecodeError, ValueError) as exc:
                rejections.append(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "artifact_type": "qadam_pattern_score_tape_rejection",
                        "input_line_number": line_number,
                        "alignment_record_id": (
                            payload.get("alignment_record_id")
                            if isinstance(payload, dict)
                            else None
                        ),
                        "reason": str(exc),
                        "score_created": False,
                    }
                )
                continue
            instrument = safe_input["instrument"]
            decision_at = safe_input["decision_at"]
            snapshot = safe_input["feature_snapshot"]
            price_points[instrument].setdefault(
                decision_at,
                {
                    "baseline_close": snapshot.get("baseline_close"),
                    "baseline_volume": snapshot.get("baseline_volume"),
                },
            )
            if safe_input["negative_control"]:
                selected = [controls_by_instrument.get(instrument)]
            else:
                selected = [agnostic_by_instrument.get(instrument)]
                selected.extend(
                    configured_by_pair.get(
                        (instrument, safe_input["source_key"]), []
                    )
                )
            selected = [template for template in selected if template]
            if not selected:
                rejections.append(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "artifact_type": "qadam_pattern_score_tape_rejection",
                        "alignment_record_id": safe_input["alignment_record_id"],
                        "reason": "no_score_template_for_instrument_and_lane",
                        "score_created": False,
                    }
                )
                continue
            consumed_alignment_ids.add(str(safe_input["alignment_record_id"]))
            for template in selected:
                key = (str(template.get("score_id")), decision_at)
                group = groups.setdefault(
                    key,
                    {"template": template, "inputs": []},
                )
                group["inputs"].append(safe_input)
    return groups, price_points, rejections, consumed_alignment_ids, input_count


def _build_score_tape_state_from_snapshot(
    runtime: Path,
    input_snapshot: dict[str, Any],
) -> dict[str, Any]:
    paths = input_snapshot["paths"]
    templates = read_jsonl(paths[SCORE_RECORDS_ARTIFACT])
    score_primary = read_json(paths[SCORE_PRIMARY_ARTIFACT])
    alignment_manifest = read_json(paths[PROVIDER_ALIGNMENT_ARTIFACT])
    source_universe = read_json(paths[SOURCE_UNIVERSE_ARTIFACT])
    trading_universe = read_json(paths[TRADING_UNIVERSE_ARTIFACT])
    eligibility = read_jsonl(paths[ELIGIBILITY_ARTIFACT])
    unusual_whales_path = paths[UNUSUAL_WHALES_FEATURE_MANIFEST_ARTIFACT]
    unusual_whales = read_json(unusual_whales_path) if unusual_whales_path else {}

    alignment_path = paths["provider_alignment_records"]
    alignment_source_path = input_snapshot["alignment_source_path"]
    expected_alignment_sha = str(
        alignment_manifest.get("alignment_records_sha256") or ""
    )
    actual_alignment_sha = file_sha256(alignment_path) or ""
    if (
        alignment_manifest.get("status") != "provider_alignment_ready"
        or not alignment_path.is_file()
        or not expected_alignment_sha
        or actual_alignment_sha != expected_alignment_sha
    ):
        raise ValueError("provider_alignment_not_ready_or_checksum_mismatch")
    if not templates:
        raise ValueError("pattern_score_v3_templates_missing")

    groups, price_points, rejections, consumed_ids, input_count = (
        _load_alignment_groups(alignment_path, templates)
    )
    market_contexts = _historical_market_context(price_points)
    source_trust = {
        str(row.get("source_key")): safe_float(row.get("trust_score"), 0.5)
        for row in source_universe.get("sources", [])
        if isinstance(row, dict) and row.get("source_key")
    }
    relationship_by_id = {
        str(row.get("relationship_id")): row
        for row in eligibility
        if row.get("relationship_id")
    }
    paperability = {
        str(row.get("symbol")): row.get("paper_route_available") is True
        for row in trading_universe.get("instruments", [])
        if isinstance(row, dict) and row.get("symbol")
    }

    rows: list[dict[str, Any]] = []
    for group in groups.values():
        inputs = group["inputs"]
        context = market_contexts.get(
            (inputs[0]["instrument"], inputs[0]["decision_at"]),
            {"regime_state": "missing_market_context"},
        )
        rows.append(
            _build_historical_score_row(
                group["template"],
                inputs,
                source_trust=source_trust,
                relationship_by_id=relationship_by_id,
                market_context=context,
                paperability=paperability,
                alignment_sha256=actual_alignment_sha,
            )
        )
    rows.sort(
        key=lambda row: (
            row["scoring_as_of"],
            row["strategy_family_id"],
            row["instrument"],
            row["score_id"],
        )
    )

    partition_rows: defaultdict[tuple[str, str, str, str, str], list[dict[str, Any]]] = (
        defaultdict(list)
    )
    for row in rows:
        key = (
            str(row["strategy_family_id"]),
            str(row["instrument"]),
            str(row["decision_date"])[:4],
            str(row["horizon_hypothesis"]),
            str(row["model_version"]),
        )
        partition_rows[key].append(row)

    partitions: list[dict[str, Any]] = []
    completed_template_ids: set[str] = set()
    reused_count = 0
    for key, records in sorted(partition_rows.items()):
        strategy_id, instrument, year, horizon, model_version = key
        input_hash = record_set_hash(records)
        partition_id = stable_id(
            "score-tape-partition",
            strategy_id,
            instrument,
            year,
            horizon,
            model_version,
            actual_alignment_sha,
            input_hash,
        )
        path = (
            RESEARCH_TAPE_ROOT
            / f"model={_slug(model_version)}"
            / f"alignment={actual_alignment_sha[:16]}"
            / f"strategy={_slug(strategy_id)}"
            / f"instrument={_slug(instrument)}"
            / f"date={year}"
            / f"horizon={_slug(horizon)}"
            / f"partition={partition_id.split(':')[-1]}"
            / "scores.jsonl"
        )
        existed = path.exists()
        dataset_hash = write_score_tape_partition(path, records)
        reused_count += int(existed)
        completed_template_ids.update(
            str(row.get("source_score_template_id")) for row in records
        )
        partitions.append(
            {
                "partition_id": partition_id,
                "strategy_family_id": strategy_id,
                "strategy_agnostic": records[0].get("strategy_agnostic") is True,
                "negative_control": records[0].get("negative_control") is True,
                "instrument": instrument,
                "date_partition": year,
                "date_partition_granularity": "calendar_year",
                "horizon": horizon,
                "model_version": model_version,
                "feature_set_version": records[0].get("feature_set_version"),
                "upstream_alignment_sha256": actual_alignment_sha,
                "partition_input_hash": input_hash,
                "status": "complete",
                "dataset_path": str(path.relative_to(ROOT)),
                "dataset_sha256": file_sha256(path),
                "record_set_hash": dataset_hash,
                "row_count": len(records),
                "input_alignment_record_count": len(
                    {
                        alignment_id
                        for row in records
                        for alignment_id in row["input_alignment_record_ids"]
                    }
                ),
                "resume_cursor": {
                    "scoring_as_of": records[-1]["scoring_as_of"],
                    "score_id": records[-1]["score_id"],
                },
                "completed_partition_immutable": True,
                "reused_existing_partition": existed,
                "label_columns_allowed": False,
            }
        )

    for template in templates:
        template_id = str(template.get("score_id"))
        if template_id in completed_template_ids:
            continue
        negative_control = template.get("negative_control") is True
        partitions.append(
            {
                "partition_id": stable_id(
                    "score-tape-unavailable-partition",
                    template_id,
                    actual_alignment_sha,
                ),
                "source_score_template_id": template_id,
                "strategy_family_id": template.get("strategy_family_id")
                or "strategy_agnostic",
                "strategy_agnostic": template.get("strategy_agnostic") is True,
                "negative_control": negative_control,
                "instrument": template.get("instrument"),
                "date_partition": "unavailable",
                "date_partition_granularity": "calendar_year",
                "horizon": template.get("horizon_hypothesis"),
                "model_version": template.get("model_version"),
                "feature_set_version": template.get("feature_set_version"),
                "upstream_alignment_sha256": actual_alignment_sha,
                "status": (
                    "blocked_no_provider_negative_control_alignment"
                    if negative_control
                    else "blocked_no_provider_alignment"
                ),
                "dataset_path": None,
                "dataset_sha256": None,
                "record_set_hash": None,
                "row_count": 0,
                "input_alignment_record_count": 0,
                "resume_cursor": None,
                "completed_partition_immutable": False,
                "reused_existing_partition": False,
                "label_columns_allowed": False,
            }
        )
    partitions.sort(key=lambda row: str(row["partition_id"]))

    rejection_hash = record_set_hash(rejections)
    rejection_path = (
        RESEARCH_TAPE_ROOT
        / f"alignment={actual_alignment_sha[:16]}"
        / f"rejections={rejection_hash[:16]}"
        / "rejections.jsonl"
    )
    write_score_tape_partition(rejection_path, rejections)

    score_ids = [str(row["score_id"]) for row in rows]
    duplicate_count = len(score_ids) - len(set(score_ids))
    classified_input_count = len(consumed_ids) + len(rejections)
    coverage_ratio = classified_input_count / input_count if input_count else 0.0
    completed = [row for row in partitions if row["status"] == "complete"]
    blocked = [row for row in partitions if row["status"] != "complete"]
    empirical_complete = bool(
        rows
        and input_count > 0
        and coverage_ratio == 1.0
        and duplicate_count == 0
    )
    generated_at = now_iso()
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_pattern_score_tape_manifest",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": (
            "complete_with_classified_gaps"
            if empirical_complete
            else "evidence_maturing"
        ),
        "research_store": str(RESEARCH_TAPE_ROOT.relative_to(ROOT)),
        "model_version": score_primary.get("model_version"),
        "feature_set_version": score_primary.get("feature_set_version"),
        "upstream_alignment": {
            "manifest_ref": f"data/runtime/{PROVIDER_ALIGNMENT_ARTIFACT}",
            "records_path": str(alignment_source_path.relative_to(ROOT)),
            "records_sha256": actual_alignment_sha,
            "record_count": input_count,
        },
        "input_snapshot": {
            key: value
            for key, value in input_snapshot.items()
            if key not in {"paths", "alignment_source_path"}
        },
        "partition_dimensions": [
            "strategy_family_id",
            "instrument",
            "calendar_year",
            "horizon_hypothesis",
            "model_version",
            "upstream_alignment_sha256",
        ],
        "partition_count": len(partitions),
        "completed_partition_count": len(completed),
        "blocked_partition_count": len(blocked),
        "partitions": partitions,
        "score_tape_row_count": len(rows),
        "input_alignment_record_count": input_count,
        "classified_input_alignment_record_count": classified_input_count,
        "input_alignment_coverage_ratio": round(coverage_ratio, 10),
        "rejection_count": len(rejections),
        "rejection_dataset_path": str(rejection_path.relative_to(ROOT)),
        "rejection_dataset_sha256": file_sha256(rejection_path),
        "rejection_record_set_hash": rejection_hash,
        "resumable": True,
        "content_addressed_partitions": True,
        "completed_partitions_rewritten": False,
        "reused_completed_partition_count": reused_count,
        "score_written_before_label_access": True,
        "label_plane_available_to_runner": False,
        "scoring_input_contract": {
            "allowed_alignment_fields": [
                "alignment_record_id",
                "relationship_id",
                "source_key",
                "instrument",
                "mapping_class",
                "negative_control",
                "source_available_at",
                "decision_at",
                "feature_snapshot",
                "provenance",
            ],
            "ignored_future_only_fields": sorted(FUTURE_ONLY_ALIGNMENT_KEYS),
            "future_metadata_value_read_count": 0,
        },
        "applied_learning_version_ids": score_primary.get(
            "applied_learning_version_ids", []
        ),
        "stage1_learning_input_version": score_primary.get(
            "stage1_learning_input_version"
        ),
        "llm_cache_policy": {
            "cache_key": ["content_sha256", "prompt_version", "model_version"],
            "frontier_review_per_historical_row_allowed": False,
            "local_llm_extraction_required_for_this_tape": False,
        },
        "paperops_watch_only_mode": True,
        "authority": authority_flags(),
    }

    source_counts = Counter(
        source
        for row in rows
        for source in {
            input_row.get("source_key") for input_row in row.get("feature_inputs", [])
        }
        if source
    )
    quality = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_pattern_score_tape_quality",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "passed" if empirical_complete else "evidence_maturing",
        "score_tape_row_count": len(rows),
        "immutable_row_count": sum(row.get("immutable") is True for row in rows),
        "label_column_detected": any(
            contains_forbidden_key(row, FORBIDDEN_TAPE_KEYS) for row in rows
        ),
        "labels_accessed": False,
        "future_horizon_metadata_accessed": False,
        "future_metadata_value_read_count": 0,
        "duplicate_score_count": duplicate_count,
        "unscorable_or_rejected_input_count": len(rejections),
        "scored_with_missing_context_count": sum(
            row["score_state"] == "scored_with_missing_context" for row in rows
        ),
        "ready_for_or7_labeling_count": sum(
            row["score_state"] == "score_ready_for_or7_labeling" for row in rows
        ),
        "score_distribution": _score_distribution(rows),
        "score_distribution_drift": _drift_audit(rows),
        "coverage": {
            "input_alignment_record_count": input_count,
            "classified_input_alignment_record_count": classified_input_count,
            "input_alignment_coverage_ratio": round(coverage_ratio, 10),
            "source_counts": dict(sorted(source_counts.items())),
            "strategy_counts": dict(
                sorted(Counter(row["strategy_family_id"] for row in rows).items())
            ),
            "instrument_counts": dict(
                sorted(Counter(row["instrument"] for row in rows).items())
            ),
            "horizon_counts": dict(
                sorted(Counter(row["horizon_hypothesis"] for row in rows).items())
            ),
            "regime_counts": dict(
                sorted(Counter(row["regime_state"] for row in rows).items())
            ),
            "calendar_year_counts": dict(
                sorted(Counter(row["decision_date"][:4] for row in rows).items())
            ),
        },
        "paperops_watch_only_mode": True,
        "authority": authority_flags(),
    }
    unusual_count = int(
        unusual_whales.get("backtest_eligible_record_count") or 0
    )
    progress = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_pattern_score_tape_progress",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": manifest["status"],
        "partition_count": len(partitions),
        "completed_partition_count": len(completed),
        "remaining_partition_count": len(blocked),
        "score_tape_row_count": len(rows),
        "input_alignment_record_count": input_count,
        "input_alignment_record_processed_count": classified_input_count,
        "input_alignment_coverage_ratio": round(coverage_ratio, 10),
        "reused_completed_partition_count": reused_count,
        "resume_safe": True,
        "supplemental_feature_row_count": unusual_count,
        "optional_gaps": (
            [] if unusual_count else ["unusual_whales_historical_features_not_available"]
        ),
        "classified_data_gaps": [
            {
                "strategy_family_id": row["strategy_family_id"],
                "instrument": row["instrument"],
                "reason": row["status"],
            }
            for row in blocked
        ],
        "blockers": [] if empirical_complete else ["historical_score_tape_incomplete"],
        "paperops_watch_only_mode": True,
        "authority": authority_flags(),
    }
    return {
        "manifest": manifest,
        "progress": progress,
        "quality": quality,
        "rows": rows,
    }


def build_score_tape_state(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    with pinned_score_tape_inputs(runtime) as input_snapshot:
        return _build_score_tape_state_from_snapshot(runtime, input_snapshot)


def validate_score_tape_state(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    manifest = state["manifest"]
    progress = state["progress"]
    quality = state["quality"]
    rows = state.get("rows", [])
    partitions = manifest.get("partitions", [])
    input_snapshot = manifest.get("input_snapshot", {})
    identifiers = [record.get("partition_id") for record in partitions]
    if not partitions:
        errors.append("score_tape_partition_manifest_empty")
    if len(identifiers) != len(set(identifiers)):
        errors.append("score_tape_partition_ids_duplicate")
    if not rows:
        errors.append("score_tape_rows_empty")
    if manifest.get("score_written_before_label_access") is not True:
        errors.append("score_tape_score_label_order_not_enforced")
    if manifest.get("label_plane_available_to_runner") is not False:
        errors.append("score_tape_label_plane_exposed")
    if manifest.get("completed_partitions_rewritten") is not False:
        errors.append("score_tape_completed_partition_rewritten")
    if input_snapshot.get("pinned_during_execution") is not True:
        errors.append("score_tape_input_snapshot_not_pinned")
    if input_snapshot.get("alignment_generation_verified") is not True:
        errors.append("score_tape_input_snapshot_alignment_unverified")
    if input_snapshot.get("source_changed_during_capture") is not False:
        errors.append("score_tape_input_snapshot_capture_race_present")
    if not input_snapshot.get("snapshot_id"):
        errors.append("score_tape_input_snapshot_identity_missing")
    if quality.get("label_column_detected") is not False:
        errors.append("score_tape_label_contamination")
    if quality.get("labels_accessed") is not False:
        errors.append("score_tape_labels_accessed")
    if quality.get("future_horizon_metadata_accessed") is not False:
        errors.append("score_tape_future_horizon_metadata_accessed")
    if quality.get("duplicate_score_count") != 0:
        errors.append("score_tape_duplicate_scores")
    if manifest.get("input_alignment_coverage_ratio") != 1.0:
        errors.append("score_tape_input_alignment_not_fully_classified")
    if progress.get("score_tape_row_count") != len(rows):
        errors.append("score_tape_progress_row_count_mismatch")
    for row in rows:
        if contains_forbidden_key(row, FORBIDDEN_TAPE_KEYS):
            errors.append(f"score_tape_row_contains_label:{row.get('score_id')}")
            continue
        contributions = sum(
            safe_float(value)
            for value in row.get("component_contributions", {}).values()
        )
        penalties = sum(
            safe_float(value) for value in row.get("penalties", {}).values()
        )
        expected_score = max(0.0, min(1.0, contributions - penalties))
        if abs(expected_score - safe_float(row.get("raw_pattern_score"))) > 1e-7:
            errors.append(f"score_tape_component_sum_mismatch:{row.get('score_id')}")
        if row.get("label_columns_present") is not False:
            errors.append(f"score_tape_label_flag_invalid:{row.get('score_id')}")
        if row.get("candidate_creation_allowed") is not False:
            errors.append(f"score_tape_candidate_authority_present:{row.get('score_id')}")
        if row.get("order_creation_allowed") is not False:
            errors.append(f"score_tape_order_authority_present:{row.get('score_id')}")
    for partition in partitions:
        if partition.get("status") != "complete":
            continue
        path = ROOT / str(partition.get("dataset_path") or "")
        if not path.is_file():
            errors.append(f"score_tape_partition_missing:{partition.get('partition_id')}")
        elif file_sha256(path) != partition.get("dataset_sha256"):
            errors.append(
                f"score_tape_partition_checksum_mismatch:{partition.get('partition_id')}"
            )
    for payload, prefix in (
        (manifest, "score_tape_manifest"),
        (progress, "score_tape_progress"),
        (quality, "score_tape_quality"),
    ):
        errors.extend(validate_authority(payload.get("authority", {}), prefix=prefix))
    return unique_errors(errors)


def build_and_write_pattern_score_tape(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    try:
        state = build_score_tape_state(settings)
        errors = validate_score_tape_state(state)
    except (OSError, ValueError) as exc:
        generated_at = now_iso()
        state = {
            "manifest": {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_pattern_score_tape_manifest",
                "phase_id": PHASE_ID,
                "generated_at": generated_at,
                "status": "blocked",
                "partition_count": 0,
                "completed_partition_count": 0,
                "partitions": [],
                "score_tape_row_count": 0,
                "paperops_watch_only_mode": True,
                "authority": authority_flags(),
            },
            "progress": {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_pattern_score_tape_progress",
                "phase_id": PHASE_ID,
                "generated_at": generated_at,
                "status": "blocked",
                "score_tape_row_count": 0,
                "blockers": [str(exc)],
                "paperops_watch_only_mode": True,
                "authority": authority_flags(),
            },
            "quality": {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_pattern_score_tape_quality",
                "phase_id": PHASE_ID,
                "generated_at": generated_at,
                "status": "blocked",
                "score_tape_row_count": 0,
                "label_column_detected": False,
                "labels_accessed": False,
                "future_horizon_metadata_accessed": False,
                "duplicate_score_count": 0,
                "paperops_watch_only_mode": True,
                "authority": authority_flags(),
            },
            "rows": [],
        }
        errors = [str(exc)]
    store.write_json(MANIFEST_ARTIFACT, state["manifest"])
    store.write_json(PROGRESS_ARTIFACT, state["progress"])
    store.write_json(QUALITY_ARTIFACT, state["quality"])
    empirical_complete = (
        state["manifest"].get("status") == "complete_with_classified_gaps"
    )
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_pattern_score_tape_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors and empirical_complete else "blocked",
        "acceptance_passed": not errors and empirical_complete,
        "implementation_ready": not errors,
        "empirical_score_tape_complete": empirical_complete,
        "partition_count": state["manifest"].get("partition_count", 0),
        "completed_partition_count": state["manifest"].get(
            "completed_partition_count", 0
        ),
        "score_tape_row_count": state["progress"].get("score_tape_row_count", 0),
        "input_alignment_record_count": state["progress"].get(
            "input_alignment_record_count", 0
        ),
        "input_alignment_coverage_ratio": state["progress"].get(
            "input_alignment_coverage_ratio", 0.0
        ),
        "upstream_alignment_sha256": state["manifest"].get(
            "upstream_alignment", {}
        ).get("records_sha256"),
        "input_snapshot_id": state["manifest"].get("input_snapshot", {}).get(
            "snapshot_id"
        ),
        "input_snapshot_pinned": state["manifest"].get("input_snapshot", {}).get(
            "pinned_during_execution"
        )
        is True,
        "input_snapshot_alignment_verified": state["manifest"]
        .get("input_snapshot", {})
        .get("alignment_generation_verified")
        is True,
        "label_column_detected": state["quality"].get(
            "label_column_detected", False
        ),
        "labels_accessed": state["quality"].get("labels_accessed", False),
        "future_horizon_metadata_accessed": state["quality"].get(
            "future_horizon_metadata_accessed", False
        ),
        "duplicate_score_count": state["quality"].get(
            "duplicate_score_count", 0
        ),
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "broker_write_count": 0,
        "paper_order_created_count": 0,
        "proof_credit_created_count": 0,
        "paper_growth_trial_calendar_advanced": False,
        "paperops_watch_only_mode": True,
        "authority": authority_flags(),
    }
    store.write_json(CHECK_ARTIFACT, checks)
    return state, checks, errors
