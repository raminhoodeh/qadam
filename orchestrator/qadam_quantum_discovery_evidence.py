"""Leakage-safe point-in-time evidence contracts for Quantum Edge Wave B."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

from orchestrator.config import Settings

SCHEMA_VERSION = "qadam_quantum_point_in_time_evidence.v1"
SPLIT_SCHEMA_VERSION = "qadam_quantum_chronological_split.v1"
FOUNDATION_SCHEMA_VERSION = "qadam_quantum_evidence_foundation.v1"
FOUNDATION_ARTIFACT = "qadam_quantum_point_in_time_evidence.json"

ALIGNMENT_ARTIFACT = "qadam_point_in_time_alignment_summary.json"
LEAKAGE_ARTIFACT = "qadam_leakage_audit_v2.json"
BACKFILL_COVERAGE_ARTIFACT = "qadam_backfill_coverage.json"
SOURCE_BACKFILL_MANIFEST = "qadam_source_backfill_manifest.json"
PRICE_BACKFILL_MANIFEST = "qadam_price_backfill_manifest.json"

EVIDENCE_DOMAINS = {
    "source_observations": "immutable provider payload references and timestamps",
    "discovery_features": "label-blind feature values available at the research cutoff",
    "future_labels": "separate outcomes attached only after discovery",
    "generated_views": "derived summaries that cannot become source evidence",
    "proof_eligible_evidence": "independently validated evidence promoted by a later gate",
}

FORBIDDEN_DISCOVERY_KEYS = {
    "actual_outcome",
    "future_label",
    "future_return",
    "label",
    "outcome",
    "outcome_available_at",
    "price_after",
    "realized_outcome",
    "return_1d",
    "return_3d",
    "return_5d",
    "return_10d",
    "return_20d",
    "return_30d",
    "target",
}

ZERO_AUTHORITY_FIELDS = (
    "quantum_research_candidate_allowed",
    "validated_edge_creation_allowed",
    "strategy_hypothesis_creation_allowed",
    "trade_candidate_creation_allowed",
    "risk_approval_allowed",
    "position_sizing_allowed",
    "execution_approval_allowed",
    "execution_allowed",
    "paper_order_allowed",
    "broker_write_allowed",
    "proof_credit_allowed",
    "paper_proof_ledger_credit_allowed",
    "live_capital_enabled",
)


def evidence_authority() -> dict[str, bool]:
    return {
        "read_only": True,
        "research_only": True,
        **{field_name: False for field_name in ZERO_AUTHORITY_FIELDS},
    }


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def immutable_content_hash(value: Any) -> str:
    if isinstance(value, bytes):
        material = value
    elif isinstance(value, str):
        material = value.encode("utf-8")
    else:
        material = canonical_json(value).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def parse_timestamp(value: Any, *, field_name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing_timestamp:{field_name}")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid_timestamp:{field_name}") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"timezone_required:{field_name}")
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _contains_forbidden_key(value: Any) -> bool:
    if isinstance(value, dict):
        if FORBIDDEN_DISCOVERY_KEYS.intersection(value):
            return True
        return any(_contains_forbidden_key(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_forbidden_key(item) for item in value)
    return False


def _runtime_dir(settings: Settings | None = None) -> Path:
    active = settings or Settings.from_env()
    path = Path(active.runtime_dir)
    if path.is_absolute():
        return path
    return Path(__file__).resolve().parents[1] / path


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp_path.replace(path)
    return path


@dataclass(frozen=True, kw_only=True)
class PointInTimeFeature:
    """One immutable, label-blind feature known at a historical cutoff."""

    record_id: str
    provider: str
    source_key: str
    source_artifact_ref: str
    source_artifact_hash: str
    event_time: str
    publication_time: str
    ingestion_time: str
    available_at: str
    source_vintage: str
    market_symbol: str
    market_timestamp: str
    as_of: str
    feature_name: str
    feature_value: float | None
    missingness_reason: str | None
    parser_version: str
    evidence_domain: str = "discovery_features"
    future_labels_present: bool = False
    proof_eligible: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            **asdict(self),
            "authority": evidence_authority(),
        }


def _feature_identity_material(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: payload.get(key)
        for key in (
            "provider",
            "source_key",
            "source_artifact_ref",
            "source_artifact_hash",
            "event_time",
            "publication_time",
            "ingestion_time",
            "available_at",
            "source_vintage",
            "market_symbol",
            "market_timestamp",
            "as_of",
            "feature_name",
            "feature_value",
            "missingness_reason",
            "parser_version",
            "evidence_domain",
        )
    }


def build_point_in_time_feature(
    *,
    provider: str,
    source_key: str,
    source_artifact_ref: str,
    raw_content: Any,
    event_time: str,
    publication_time: str,
    ingestion_time: str,
    source_vintage: str,
    market_symbol: str,
    market_timestamp: str,
    as_of: str,
    feature_name: str,
    feature_value: float | int | None,
    parser_version: str,
    missingness_reason: str | None = None,
) -> PointInTimeFeature:
    for field_name, value in (
        ("provider", provider),
        ("source_key", source_key),
        ("source_artifact_ref", source_artifact_ref),
        ("market_symbol", market_symbol),
        ("feature_name", feature_name),
        ("parser_version", parser_version),
    ):
        if not str(value).strip():
            raise ValueError(f"missing_field:{field_name}")
    if _contains_forbidden_key(raw_content):
        raise ValueError("future_label_key_in_source_content")

    event = parse_timestamp(event_time, field_name="event_time")
    publication = parse_timestamp(publication_time, field_name="publication_time")
    ingestion = parse_timestamp(ingestion_time, field_name="ingestion_time")
    vintage = parse_timestamp(source_vintage, field_name="source_vintage")
    market = parse_timestamp(market_timestamp, field_name="market_timestamp")
    cutoff = parse_timestamp(as_of, field_name="as_of")
    available = max(publication, ingestion)

    if event > publication:
        raise ValueError("event_after_publication")
    if publication > ingestion:
        raise ValueError("publication_after_ingestion")
    if available > cutoff:
        raise ValueError("source_available_after_cutoff")
    if vintage > cutoff:
        raise ValueError("source_vintage_after_cutoff")
    if market > cutoff:
        raise ValueError("market_timestamp_after_cutoff")

    resolved_value: float | None
    if feature_value is None:
        if not str(missingness_reason or "").strip():
            raise ValueError("missing_feature_requires_reason")
        resolved_value = None
    else:
        if isinstance(feature_value, bool):
            raise ValueError("feature_value_not_numeric")
        resolved_value = float(feature_value)
        if not math.isfinite(resolved_value):
            raise ValueError("feature_value_not_finite")
        if missingness_reason is not None:
            raise ValueError("present_feature_cannot_have_missingness_reason")

    base = {
        "provider": provider,
        "source_key": source_key,
        "source_artifact_ref": source_artifact_ref,
        "source_artifact_hash": immutable_content_hash(raw_content),
        "event_time": _iso(event),
        "publication_time": _iso(publication),
        "ingestion_time": _iso(ingestion),
        "available_at": _iso(available),
        "source_vintage": _iso(vintage),
        "market_symbol": market_symbol,
        "market_timestamp": _iso(market),
        "as_of": _iso(cutoff),
        "feature_name": feature_name,
        "feature_value": resolved_value,
        "missingness_reason": missingness_reason,
        "parser_version": parser_version,
        "evidence_domain": "discovery_features",
    }
    feature = PointInTimeFeature(
        record_id=f"pit-feature:{stable_hash(base)[:24]}",
        **base,
    )
    errors = validate_point_in_time_feature(feature.to_dict())
    if errors:
        raise ValueError(f"invalid_point_in_time_feature:{','.join(errors)}")
    return feature


def validate_point_in_time_feature(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_invalid")
    if payload.get("evidence_domain") != "discovery_features":
        errors.append("evidence_domain_invalid")
    if payload.get("future_labels_present") is not False:
        errors.append("future_labels_present")
    if payload.get("proof_eligible") is not False:
        errors.append("proof_eligibility_escalated")
    if _contains_forbidden_key(payload):
        errors.append("future_label_key_present")

    try:
        event = parse_timestamp(payload.get("event_time"), field_name="event_time")
        publication = parse_timestamp(
            payload.get("publication_time"), field_name="publication_time"
        )
        ingestion = parse_timestamp(payload.get("ingestion_time"), field_name="ingestion_time")
        available = parse_timestamp(payload.get("available_at"), field_name="available_at")
        vintage = parse_timestamp(payload.get("source_vintage"), field_name="source_vintage")
        market = parse_timestamp(payload.get("market_timestamp"), field_name="market_timestamp")
        cutoff = parse_timestamp(payload.get("as_of"), field_name="as_of")
    except ValueError as exc:
        errors.append(str(exc))
    else:
        if event > publication:
            errors.append("event_after_publication")
        if publication > ingestion:
            errors.append("publication_after_ingestion")
        if available != max(publication, ingestion):
            errors.append("available_at_not_publication_ingestion_max")
        if available > cutoff:
            errors.append("source_available_after_cutoff")
        if vintage > cutoff:
            errors.append("source_vintage_after_cutoff")
        if market > cutoff:
            errors.append("market_timestamp_after_cutoff")

    value = payload.get("feature_value")
    missing_reason = payload.get("missingness_reason")
    if value is None and not str(missing_reason or "").strip():
        errors.append("missing_feature_requires_reason")
    if value is not None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            errors.append("feature_value_not_numeric")
        elif not math.isfinite(float(value)):
            errors.append("feature_value_not_finite")
        if missing_reason is not None:
            errors.append("present_feature_has_missingness_reason")

    expected_id = f"pit-feature:{stable_hash(_feature_identity_material(payload))[:24]}"
    if payload.get("record_id") != expected_id:
        errors.append("record_id_hash_mismatch")
    if len(str(payload.get("source_artifact_hash") or "")) != 64:
        errors.append("source_artifact_hash_invalid")

    authority = payload.get("authority")
    if not isinstance(authority, dict):
        errors.append("authority_missing")
    else:
        if authority.get("read_only") is not True or authority.get("research_only") is not True:
            errors.append("research_boundary_missing")
        for field_name in ZERO_AUTHORITY_FIELDS:
            if authority.get(field_name) is not False:
                errors.append(f"authority_escalated:{field_name}")
    return sorted(set(errors))


def build_chronological_split(
    records: Iterable[PointInTimeFeature | dict[str, Any]],
    *,
    outcome_window_seconds: int,
    embargo_seconds: int,
    train_fraction: float = 0.6,
    validation_fraction: float = 0.2,
) -> dict[str, Any]:
    if outcome_window_seconds <= 0 or embargo_seconds < 0:
        raise ValueError("split_window_invalid")
    if not 0 < train_fraction < 1 or not 0 < validation_fraction < 1:
        raise ValueError("split_fraction_invalid")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("split_fraction_sum_invalid")

    payloads = [record.to_dict() if isinstance(record, PointInTimeFeature) else record for record in records]
    if len(payloads) < 8:
        raise ValueError("at_least_eight_records_required")
    for payload in payloads:
        errors = validate_point_in_time_feature(payload)
        if errors:
            raise ValueError(f"split_input_invalid:{','.join(errors)}")

    ordered = sorted(
        payloads,
        key=lambda item: (
            parse_timestamp(item["as_of"], field_name="as_of"),
            str(item["record_id"]),
        ),
    )
    count = len(ordered)
    train_end = max(2, int(count * train_fraction))
    validation_end = max(train_end + 1, int(count * (train_fraction + validation_fraction)))
    if validation_end >= count:
        validation_end = count - 1

    train_candidates = ordered[:train_end]
    validation_candidates = ordered[train_end:validation_end]
    holdout_candidates = ordered[validation_end:]
    if not validation_candidates or not holdout_candidates:
        raise ValueError("split_partition_empty")

    horizon = timedelta(seconds=outcome_window_seconds)
    first_validation = parse_timestamp(
        validation_candidates[0]["as_of"], field_name="validation_start"
    )
    first_holdout = parse_timestamp(holdout_candidates[0]["as_of"], field_name="holdout_start")
    train = [
        item
        for item in train_candidates
        if parse_timestamp(item["as_of"], field_name="train_as_of") + horizon
        < first_validation
    ]
    purged_train = [item for item in train_candidates if item not in train]
    validation = [
        item
        for item in validation_candidates
        if parse_timestamp(item["as_of"], field_name="validation_as_of") + horizon
        < first_holdout
    ]
    purged_validation = [item for item in validation_candidates if item not in validation]
    embargo_cutoff = parse_timestamp(
        validation_candidates[-1]["as_of"], field_name="validation_end"
    ) + timedelta(seconds=embargo_seconds)
    holdout = [
        item
        for item in holdout_candidates
        if parse_timestamp(item["as_of"], field_name="holdout_as_of") > embargo_cutoff
    ]
    embargoed_holdout = [item for item in holdout_candidates if item not in holdout]
    if not train or not validation or not holdout:
        raise ValueError("purge_or_embargo_emptied_partition")

    def ids(items: list[dict[str, Any]]) -> list[str]:
        return [str(item["record_id"]) for item in items]

    partition_ids = {
        "train": ids(train),
        "validation": ids(validation),
        "untouched_holdout": ids(holdout),
        "purged_train": ids(purged_train),
        "purged_validation": ids(purged_validation),
        "embargoed_holdout": ids(embargoed_holdout),
    }
    identity_material = {
        "partition_ids": partition_ids,
        "outcome_window_seconds": outcome_window_seconds,
        "embargo_seconds": embargo_seconds,
        "train_fraction": train_fraction,
        "validation_fraction": validation_fraction,
    }
    split_identity = f"chronological-split:{stable_hash(identity_material)[:24]}"
    return {
        "schema_version": SPLIT_SCHEMA_VERSION,
        "status": "chronological_split_ready",
        "split_identity": split_identity,
        "partition_ids": partition_ids,
        "partition_counts": {key: len(value) for key, value in partition_ids.items()},
        "ordered_record_ids": [item["record_id"] for item in ordered],
        "outcome_window_seconds": outcome_window_seconds,
        "purge_applied": bool(purged_train or purged_validation),
        "embargo_seconds": embargo_seconds,
        "embargo_applied": bool(embargoed_holdout),
        "train_fraction": train_fraction,
        "validation_fraction": validation_fraction,
        "labels_present": False,
        "dataset_hash": stable_hash([item["record_id"] for item in ordered]),
        "authority": evidence_authority(),
    }


def validate_chronological_split(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SPLIT_SCHEMA_VERSION:
        errors.append("split_schema_invalid")
    if payload.get("status") != "chronological_split_ready":
        errors.append("split_not_ready")
    if payload.get("labels_present") is not False:
        errors.append("split_contains_labels")
    partitions = payload.get("partition_ids")
    if not isinstance(partitions, dict):
        errors.append("split_partitions_missing")
    else:
        primary = [
            set(partitions.get(name, []))
            for name in ("train", "validation", "untouched_holdout")
        ]
        if not all(primary):
            errors.append("split_primary_partition_empty")
        if primary[0] & primary[1] or primary[0] & primary[2] or primary[1] & primary[2]:
            errors.append("split_primary_partition_overlap")
        all_ids = [item for values in partitions.values() for item in values]
        if len(all_ids) != len(set(all_ids)):
            errors.append("split_record_reused")
        identity_material = {
            "partition_ids": partitions,
            "outcome_window_seconds": payload.get("outcome_window_seconds"),
            "embargo_seconds": payload.get("embargo_seconds"),
            "train_fraction": payload.get("train_fraction", 0.6),
            "validation_fraction": payload.get("validation_fraction", 0.2),
        }
        expected_identity = f"chronological-split:{stable_hash(identity_material)[:24]}"
        if payload.get("split_identity") != expected_identity:
            errors.append("split_identity_hash_mismatch")
    ordered_record_ids = payload.get("ordered_record_ids")
    if not isinstance(ordered_record_ids, list) or payload.get("dataset_hash") != stable_hash(
        ordered_record_ids
    ):
        errors.append("split_dataset_hash_mismatch")
    authority = payload.get("authority", {})
    for field_name in ZERO_AUTHORITY_FIELDS:
        if authority.get(field_name) is not False:
            errors.append(f"split_authority_escalated:{field_name}")
    return sorted(set(errors))


def _manifest_status_counts(payload: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    jobs = payload.get("jobs")
    if not isinstance(jobs, list):
        return counts
    for job in jobs:
        if not isinstance(job, dict):
            continue
        status = str(job.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def build_point_in_time_foundation(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    alignment = _read_json(runtime / ALIGNMENT_ARTIFACT)
    leakage = _read_json(runtime / LEAKAGE_ARTIFACT)
    coverage = _read_json(runtime / BACKFILL_COVERAGE_ARTIFACT)
    source_manifest = _read_json(runtime / SOURCE_BACKFILL_MANIFEST)
    price_manifest = _read_json(runtime / PRICE_BACKFILL_MANIFEST)

    blockers: list[str] = []
    if not alignment:
        blockers.append("point_in_time_alignment_artifact_missing")
    if int(alignment.get("leakage_violation_count") or 0) > 0:
        blockers.append("point_in_time_leakage_detected")
    if int(alignment.get("eligible_forward_score_input_count") or 0) <= 0:
        blockers.append("no_eligible_point_in_time_windows")
    if not coverage:
        blockers.append("provider_backfill_coverage_missing")
    if not source_manifest:
        blockers.append("source_backfill_manifest_missing")
    if not price_manifest:
        blockers.append("price_backfill_manifest_missing")
    if not leakage:
        blockers.append("leakage_audit_missing")
    if int(coverage.get("provider_row_count") or 0) <= 0:
        blockers.append("provider_backfill_has_no_rows")
    if int(coverage.get("completed_partition_count") or 0) <= 0:
        blockers.append("provider_backfill_has_no_completed_partitions")
    if coverage.get("provider_history_certified_complete") is not True:
        blockers.append("provider_history_not_certified_complete")
    if int(leakage.get("leakage_violation_count") or 0) > 0:
        blockers.append("leakage_audit_failed")

    unique_blockers = sorted(set(blockers))
    return {
        "schema_version": FOUNDATION_SCHEMA_VERSION,
        "status": (
            "point_in_time_evidence_ready"
            if not unique_blockers
            else "point_in_time_contract_ready_evidence_maturing"
        ),
        "implementation_contract_ready": True,
        "empirical_evidence_ready": not unique_blockers,
        "evidence_domains": dict(EVIDENCE_DOMAINS),
        "timestamp_semantics": [
            "event_time",
            "publication_time",
            "ingestion_time",
            "available_at",
            "source_vintage",
            "market_timestamp",
            "as_of",
        ],
        "alignment_truth": {
            "status": alignment.get("status", "missing"),
            "relationship_count": int(alignment.get("relationship_count") or 0),
            "classified_window_count": int(alignment.get("classified_window_count") or 0),
            "eligible_point_in_time_window_count": int(
                alignment.get("eligible_forward_score_input_count") or 0
            ),
            "leakage_violation_count": int(alignment.get("leakage_violation_count") or 0),
        },
        "provider_history_truth": {
            "status": coverage.get("status", "missing"),
            "total_partition_count": int(coverage.get("total_partition_count") or 0),
            "completed_partition_count": int(coverage.get("completed_partition_count") or 0),
            "remaining_partition_count": int(coverage.get("remaining_partition_count") or 0),
            "provider_row_count": int(coverage.get("provider_row_count") or 0),
            "provider_history_certified_complete": (
                coverage.get("provider_history_certified_complete") is True
            ),
            "source_manifest_status": source_manifest.get("status", "missing"),
            "source_job_status_counts": _manifest_status_counts(source_manifest),
            "price_manifest_status": price_manifest.get("status", "missing"),
            "price_job_status_counts": _manifest_status_counts(price_manifest),
        },
        "leakage_truth": {
            "status": leakage.get("status", "missing"),
            "input_record_count": int(leakage.get("input_record_count") or 0),
            "leakage_violation_count": int(leakage.get("leakage_violation_count") or 0),
            "forward_labels_separate": (
                leakage.get("forward_label_requires_outcome_available_strictly_after_decision")
                is True
            ),
        },
        "blockers": unique_blockers,
        "invented_evidence_count": 0,
        "future_labels_available_to_discovery": False,
        "authority": evidence_authority(),
        "boundary": (
            "This foundation may classify and freeze historical research evidence. "
            "It cannot invent missing provider history, expose future outcomes to discovery, "
            "create candidates or strategies, approve risk or execution, or create orders."
        ),
    }


def validate_point_in_time_foundation(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != FOUNDATION_SCHEMA_VERSION:
        errors.append("foundation_schema_invalid")
    if payload.get("implementation_contract_ready") is not True:
        errors.append("foundation_contract_not_ready")
    if payload.get("invented_evidence_count") != 0:
        errors.append("invented_evidence_present")
    if payload.get("future_labels_available_to_discovery") is not False:
        errors.append("future_labels_exposed")
    if payload.get("evidence_domains") != EVIDENCE_DOMAINS:
        errors.append("evidence_domains_invalid")
    if payload.get("empirical_evidence_ready") is True and payload.get("blockers"):
        errors.append("empirical_ready_with_blockers")
    if payload.get("empirical_evidence_ready") is False and not payload.get("blockers"):
        errors.append("empirical_blocked_without_reason")
    authority = payload.get("authority", {})
    for field_name in ZERO_AUTHORITY_FIELDS:
        if authority.get(field_name) is not False:
            errors.append(f"foundation_authority_escalated:{field_name}")
    return sorted(set(errors))


def write_point_in_time_foundation(
    payload: dict[str, Any], settings: Settings | None = None
) -> Path:
    errors = validate_point_in_time_foundation(payload)
    if errors:
        raise ValueError(f"point_in_time_foundation_invalid:{','.join(errors)}")
    return _write_json_atomic(_runtime_dir(settings) / FOUNDATION_ARTIFACT, payload)
