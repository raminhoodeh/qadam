"""Frozen shared experiment manifests for Quantum Edge Wave B."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from pathlib import Path
from typing import Any, Iterable

from orchestrator.config import Settings
from orchestrator.qadam_quantum_discovery_evidence import (
    FORBIDDEN_DISCOVERY_KEYS,
    ZERO_AUTHORITY_FIELDS,
    _runtime_dir,
    _write_json_atomic,
    canonical_json,
    evidence_authority,
    parse_timestamp,
    stable_hash,
)

NORMALIZER_SCHEMA_VERSION = "qadam_quantum_training_normalizer.v1"
WINDOW_SCHEMA_VERSION = "qadam.QuantumDiscoveryWindow.v1"
CONTRACT_SCHEMA_VERSION = "qadam_quantum_shared_manifest_contract.v1"
CONTRACT_ARTIFACT = "qadam_quantum_discovery_manifest_contract.json"

MIN_FEATURES = 6
MAX_FEATURES = 10
DEFAULT_MAX_MISSING_FRACTION = 0.25


def _contains_forbidden_key(value: Any) -> bool:
    if isinstance(value, dict):
        if FORBIDDEN_DISCOVERY_KEYS.intersection(value):
            return True
        return any(_contains_forbidden_key(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_forbidden_key(item) for item in value)
    return False


def _finite_or_none(value: Any, *, field_name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"feature_not_numeric:{field_name}")
    resolved = float(value)
    if not math.isfinite(resolved):
        raise ValueError(f"feature_not_finite:{field_name}")
    return resolved


def _normalizer_material(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: payload.get(key)
        for key in (
            "schema_version",
            "feature_names",
            "means",
            "scales",
            "constant_features",
            "missing_value_policy",
            "fit_scope",
            "training_split_identity",
            "training_dataset_hash",
            "feature_schema_version",
        )
    }


def fit_training_normalizer(
    rows: Iterable[dict[str, Any]],
    *,
    feature_names: Iterable[str],
    training_split_identity: str,
    feature_schema_version: str,
) -> dict[str, Any]:
    names = tuple(str(name) for name in feature_names)
    if not MIN_FEATURES <= len(names) <= MAX_FEATURES:
        raise ValueError("normalizer_feature_dimension_unsupported")
    if len(names) != len(set(names)) or any(not name.strip() for name in names):
        raise ValueError("normalizer_feature_names_invalid")
    if not training_split_identity.startswith("chronological-split:"):
        raise ValueError("normalizer_training_split_identity_invalid")
    if not feature_schema_version.strip():
        raise ValueError("normalizer_feature_schema_missing")

    ordered_rows = sorted(
        list(rows),
        key=lambda row: (str(row.get("as_of") or ""), canonical_json(row.get("features", {}))),
    )
    if len(ordered_rows) < 2:
        raise ValueError("normalizer_requires_two_training_rows")
    if _contains_forbidden_key(ordered_rows):
        raise ValueError("normalizer_future_label_contamination")

    values_by_feature: dict[str, list[float]] = {name: [] for name in names}
    normalized_rows: list[dict[str, Any]] = []
    for row in ordered_rows:
        if row.get("partition") != "train":
            raise ValueError("normalizer_fit_scope_not_train_only")
        as_of = parse_timestamp(row.get("as_of"), field_name="normalizer_row_as_of")
        features = row.get("features")
        if not isinstance(features, dict) or set(features) != set(names):
            raise ValueError("normalizer_feature_schema_mismatch")
        normalized_features: dict[str, float | None] = {}
        for name in names:
            value = _finite_or_none(features.get(name), field_name=name)
            normalized_features[name] = value
            if value is not None:
                values_by_feature[name].append(value)
        normalized_rows.append(
            {
                "partition": "train",
                "as_of": as_of.isoformat(),
                "features": normalized_features,
            }
        )

    means: dict[str, float] = {}
    scales: dict[str, float] = {}
    constant_features: list[str] = []
    for name in names:
        values = values_by_feature[name]
        if len(values) < 2:
            raise ValueError(f"normalizer_insufficient_training_values:{name}")
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        scale = math.sqrt(variance)
        if scale <= 1e-12:
            scale = 1.0
            constant_features.append(name)
        means[name] = round(mean, 12)
        scales[name] = round(scale, 12)

    payload = {
        "schema_version": NORMALIZER_SCHEMA_VERSION,
        "feature_names": list(names),
        "means": means,
        "scales": scales,
        "constant_features": sorted(constant_features),
        "missing_value_policy": "zero_after_training_standardization_with_explicit_mask",
        "fit_scope": "train_only",
        "training_split_identity": training_split_identity,
        "training_dataset_hash": stable_hash(normalized_rows),
        "feature_schema_version": feature_schema_version,
        "authority": evidence_authority(),
    }
    payload["normalizer_hash"] = stable_hash(_normalizer_material(payload))
    errors = validate_training_normalizer(payload)
    if errors:
        raise ValueError(f"normalizer_invalid:{','.join(errors)}")
    return payload


def validate_training_normalizer(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != NORMALIZER_SCHEMA_VERSION:
        errors.append("normalizer_schema_invalid")
    names = payload.get("feature_names")
    if not isinstance(names, list) or not MIN_FEATURES <= len(names) <= MAX_FEATURES:
        errors.append("normalizer_feature_dimension_unsupported")
        names = []
    if len(names) != len(set(names)):
        errors.append("normalizer_feature_names_duplicate")
    if payload.get("fit_scope") != "train_only":
        errors.append("normalizer_not_train_only")
    if payload.get("missing_value_policy") != (
        "zero_after_training_standardization_with_explicit_mask"
    ):
        errors.append("normalizer_missing_value_policy_invalid")
    if not str(payload.get("feature_schema_version") or "").strip():
        errors.append("normalizer_feature_schema_missing")
    if not str(payload.get("training_split_identity") or "").startswith(
        "chronological-split:"
    ):
        errors.append("normalizer_split_identity_invalid")
    for field_name in ("means", "scales"):
        values = payload.get(field_name)
        if not isinstance(values, dict) or set(values) != set(names):
            errors.append(f"normalizer_{field_name}_invalid")
        elif any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            for value in values.values()
        ):
            errors.append(f"normalizer_{field_name}_not_finite")
    for name, scale in (payload.get("scales") or {}).items():
        if not isinstance(scale, (int, float)) or float(scale) <= 0:
            errors.append(f"normalizer_scale_invalid:{name}")
    if payload.get("normalizer_hash") != stable_hash(_normalizer_material(payload)):
        errors.append("normalizer_hash_mismatch")
    authority = payload.get("authority", {})
    for field_name in ZERO_AUTHORITY_FIELDS:
        if authority.get(field_name) is not False:
            errors.append(f"normalizer_authority_escalated:{field_name}")
    return sorted(set(errors))


@dataclass(frozen=True, kw_only=True)
class QuantumDiscoveryWindow:
    window_id: str
    as_of: str
    market_sleeve: str
    target_instrument: str
    feature_names: tuple[str, ...]
    raw_feature_values: tuple[float | None, ...]
    normalized_features: tuple[float, ...]
    missingness_mask: tuple[int, ...]
    feature_lineage: tuple[dict[str, Any], ...]
    source_artifact_references: tuple[dict[str, str], ...]
    feature_schema_version: str
    encoding_version: str
    chronological_split_identity: str
    dataset_hash: str
    normalizer_hash: str
    manifest_hash: str
    random_seed: int
    maximum_input_age_seconds: int
    maximum_missing_fraction: float
    labels_present: bool = False
    contract_fixture_only: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": WINDOW_SCHEMA_VERSION,
            **asdict(self),
            "consumer_manifest_hashes": {
                "classical_discovery": self.manifest_hash,
                "quantum_assisted_discovery": self.manifest_hash,
            },
            "authority": evidence_authority(),
        }


def _dataset_material(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "as_of": payload.get("as_of"),
        "target_instrument": payload.get("target_instrument"),
        "feature_names": payload.get("feature_names"),
        "raw_feature_values": payload.get("raw_feature_values"),
        "feature_lineage": payload.get("feature_lineage"),
    }


def _window_manifest_material(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: payload.get(key)
        for key in (
            "as_of",
            "market_sleeve",
            "target_instrument",
            "feature_names",
            "raw_feature_values",
            "normalized_features",
            "missingness_mask",
            "feature_lineage",
            "source_artifact_references",
            "feature_schema_version",
            "encoding_version",
            "chronological_split_identity",
            "dataset_hash",
            "normalizer_hash",
            "random_seed",
            "maximum_input_age_seconds",
            "maximum_missing_fraction",
            "labels_present",
            "contract_fixture_only",
        )
    }


def build_quantum_discovery_window(
    *,
    as_of: str,
    market_sleeve: str,
    target_instrument: str,
    feature_values: dict[str, float | int | None],
    feature_lineage: dict[str, dict[str, Any]],
    normalizer: dict[str, Any],
    encoding_version: str,
    random_seed: int,
    maximum_input_age_seconds: int,
    max_missing_fraction: float = DEFAULT_MAX_MISSING_FRACTION,
    contract_fixture_only: bool = False,
) -> QuantumDiscoveryWindow:
    normalizer_errors = validate_training_normalizer(normalizer)
    if normalizer_errors:
        raise ValueError(f"window_normalizer_invalid:{','.join(normalizer_errors)}")
    cutoff = parse_timestamp(as_of, field_name="window_as_of")
    names = tuple(str(name) for name in normalizer["feature_names"])
    if set(feature_values) != set(names) or set(feature_lineage) != set(names):
        raise ValueError("window_feature_schema_mismatch")
    if not market_sleeve.strip() or not target_instrument.strip():
        raise ValueError("window_market_identity_missing")
    if not encoding_version.strip():
        raise ValueError("window_encoding_version_missing")
    if isinstance(random_seed, bool) or not isinstance(random_seed, int) or random_seed < 0:
        raise ValueError("window_random_seed_invalid")
    if maximum_input_age_seconds <= 0:
        raise ValueError("window_maximum_input_age_invalid")
    if not 0 <= max_missing_fraction < 1:
        raise ValueError("window_missing_fraction_policy_invalid")
    if _contains_forbidden_key({"values": feature_values, "lineage": feature_lineage}):
        raise ValueError("window_future_label_contamination")

    raw_values: list[float | None] = []
    normalized_values: list[float] = []
    missingness_mask: list[int] = []
    lineage_records: list[dict[str, Any]] = []
    source_refs: dict[tuple[str, str], dict[str, str]] = {}
    for name in names:
        value = _finite_or_none(feature_values[name], field_name=name)
        lineage = feature_lineage[name]
        if not isinstance(lineage, dict):
            raise ValueError(f"window_lineage_invalid:{name}")
        missing_reason = lineage.get("missingness_reason")
        if value is None:
            if not str(missing_reason or "").strip():
                raise ValueError(f"window_missing_reason_required:{name}")
            raw_values.append(None)
            normalized_values.append(0.0)
            missingness_mask.append(1)
            lineage_records.append(
                {
                    "feature_name": name,
                    "source_key": lineage.get("source_key"),
                    "artifact_ref": None,
                    "artifact_hash": None,
                    "available_at": None,
                    "missingness_reason": str(missing_reason),
                }
            )
            continue

        artifact_ref = str(lineage.get("artifact_ref") or "")
        artifact_hash = str(lineage.get("artifact_hash") or "")
        source_key = str(lineage.get("source_key") or "")
        if not artifact_ref or len(artifact_hash) != 64 or not source_key:
            raise ValueError(f"window_lineage_incomplete:{name}")
        available_at = parse_timestamp(
            lineage.get("available_at"), field_name=f"feature_available_at:{name}"
        )
        if available_at > cutoff:
            raise ValueError(f"window_feature_available_after_cutoff:{name}")
        age_seconds = (cutoff - available_at).total_seconds()
        if age_seconds > maximum_input_age_seconds:
            raise ValueError(f"window_feature_stale:{name}")

        mean = float(normalizer["means"][name])
        scale = float(normalizer["scales"][name])
        raw_values.append(value)
        normalized_values.append(round((value - mean) / scale, 12))
        missingness_mask.append(0)
        lineage_record = {
            "feature_name": name,
            "source_key": source_key,
            "artifact_ref": artifact_ref,
            "artifact_hash": artifact_hash,
            "available_at": available_at.isoformat(),
            "missingness_reason": None,
        }
        lineage_records.append(lineage_record)
        source_refs[(artifact_ref, artifact_hash)] = {
            "artifact_ref": artifact_ref,
            "artifact_hash": artifact_hash,
        }

    missing_fraction = sum(missingness_mask) / len(missingness_mask)
    if missing_fraction > max_missing_fraction:
        raise ValueError("window_excessive_missingness")

    payload: dict[str, Any] = {
        "as_of": cutoff.isoformat(),
        "market_sleeve": market_sleeve,
        "target_instrument": target_instrument,
        "feature_names": list(names),
        "raw_feature_values": raw_values,
        "normalized_features": normalized_values,
        "missingness_mask": missingness_mask,
        "feature_lineage": lineage_records,
        "source_artifact_references": [source_refs[key] for key in sorted(source_refs)],
        "feature_schema_version": normalizer["feature_schema_version"],
        "encoding_version": encoding_version,
        "chronological_split_identity": normalizer["training_split_identity"],
        "normalizer_hash": normalizer["normalizer_hash"],
        "random_seed": random_seed,
        "maximum_input_age_seconds": maximum_input_age_seconds,
        "maximum_missing_fraction": max_missing_fraction,
        "labels_present": False,
        "contract_fixture_only": contract_fixture_only,
    }
    payload["dataset_hash"] = stable_hash(_dataset_material(payload))
    manifest_hash = stable_hash(_window_manifest_material(payload))
    window = QuantumDiscoveryWindow(
        window_id=f"quantum-discovery-window:{manifest_hash[:24]}",
        manifest_hash=manifest_hash,
        **{
            **payload,
            "feature_names": tuple(payload["feature_names"]),
            "raw_feature_values": tuple(payload["raw_feature_values"]),
            "normalized_features": tuple(payload["normalized_features"]),
            "missingness_mask": tuple(payload["missingness_mask"]),
            "feature_lineage": tuple(payload["feature_lineage"]),
            "source_artifact_references": tuple(payload["source_artifact_references"]),
        },
    )
    errors = validate_quantum_discovery_window(window.to_dict())
    if errors:
        raise ValueError(f"quantum_discovery_window_invalid:{','.join(errors)}")
    return window


def validate_quantum_discovery_window(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != WINDOW_SCHEMA_VERSION:
        errors.append("window_schema_invalid")
    names = payload.get("feature_names")
    if not isinstance(names, (list, tuple)) or not MIN_FEATURES <= len(names) <= MAX_FEATURES:
        errors.append("window_feature_dimension_unsupported")
        names = []
    for field_name in ("raw_feature_values", "normalized_features", "missingness_mask"):
        values = payload.get(field_name)
        if not isinstance(values, (list, tuple)) or len(values) != len(names):
            errors.append(f"window_{field_name}_length_invalid")
    mask = payload.get("missingness_mask") or []
    if any(value not in (0, 1) for value in mask):
        errors.append("window_missingness_mask_invalid")
    if payload.get("labels_present") is not False:
        errors.append("window_labels_present")
    if not str(payload.get("feature_schema_version") or "").strip():
        errors.append("window_feature_schema_missing")
    if not str(payload.get("encoding_version") or "").strip():
        errors.append("window_encoding_version_missing")
    random_seed = payload.get("random_seed")
    if isinstance(random_seed, bool) or not isinstance(random_seed, int) or random_seed < 0:
        errors.append("window_random_seed_invalid")
    raw_values = payload.get("raw_feature_values") or []
    normalized_values = payload.get("normalized_features") or []
    if len(raw_values) == len(mask) == len(normalized_values):
        for index, (raw_value, normalized_value, missing) in enumerate(
            zip(raw_values, normalized_values, mask, strict=True)
        ):
            if (raw_value is None) is not (missing == 1):
                errors.append(f"window_missingness_value_mismatch:{index}")
            if missing == 1 and normalized_value != 0.0:
                errors.append(f"window_missing_value_not_zero_encoded:{index}")
    maximum_missing_fraction = payload.get("maximum_missing_fraction")
    if not isinstance(maximum_missing_fraction, (int, float)) or not 0 <= float(
        maximum_missing_fraction
    ) < 1:
        errors.append("window_missing_fraction_policy_invalid")
    elif mask and sum(mask) / len(mask) > float(maximum_missing_fraction):
        errors.append("window_excessive_missingness")
    if _contains_forbidden_key(payload.get("feature_lineage", [])):
        errors.append("window_future_label_contamination")
    if not str(payload.get("chronological_split_identity") or "").startswith(
        "chronological-split:"
    ):
        errors.append("window_split_identity_invalid")
    try:
        cutoff = parse_timestamp(payload.get("as_of"), field_name="window_as_of")
    except ValueError as exc:
        errors.append(str(exc))
        cutoff = None
    maximum_age = payload.get("maximum_input_age_seconds")
    if not isinstance(maximum_age, int) or isinstance(maximum_age, bool) or maximum_age <= 0:
        errors.append("window_maximum_input_age_invalid")
    lineage = payload.get("feature_lineage")
    if not isinstance(lineage, (list, tuple)) or len(lineage) != len(names):
        errors.append("window_feature_lineage_invalid")
    elif cutoff is not None and isinstance(maximum_age, int):
        for item in lineage:
            if not isinstance(item, dict):
                errors.append("window_feature_lineage_item_invalid")
                continue
            if item.get("missingness_reason"):
                continue
            artifact_hash = str(item.get("artifact_hash") or "")
            if len(artifact_hash) != 64 or not str(item.get("artifact_ref") or ""):
                errors.append(f"window_lineage_hash_or_ref_invalid:{item.get('feature_name')}")
            try:
                available_at = parse_timestamp(
                    item.get("available_at"),
                    field_name=f"feature_available_at:{item.get('feature_name')}",
                )
            except ValueError as exc:
                errors.append(str(exc))
                continue
            if available_at > cutoff:
                errors.append(f"window_feature_available_after_cutoff:{item.get('feature_name')}")
            elif (cutoff - available_at).total_seconds() > maximum_age:
                errors.append(f"window_feature_stale:{item.get('feature_name')}")
    if payload.get("dataset_hash") != stable_hash(_dataset_material(payload)):
        errors.append("window_dataset_hash_mismatch")
    expected_manifest_hash = stable_hash(_window_manifest_material(payload))
    if payload.get("manifest_hash") != expected_manifest_hash:
        errors.append("window_manifest_hash_mismatch")
    if payload.get("window_id") != f"quantum-discovery-window:{expected_manifest_hash[:24]}":
        errors.append("window_id_hash_mismatch")
    consumers = payload.get("consumer_manifest_hashes")
    if consumers != {
        "classical_discovery": expected_manifest_hash,
        "quantum_assisted_discovery": expected_manifest_hash,
    }:
        errors.append("window_consumer_hash_divergence")
    authority = payload.get("authority", {})
    for field_name in ZERO_AUTHORITY_FIELDS:
        if authority.get(field_name) is not False:
            errors.append(f"window_authority_escalated:{field_name}")
    return sorted(set(errors))


def _contract_fixture() -> tuple[dict[str, Any], QuantumDiscoveryWindow]:
    names = (
        "source_density",
        "source_agreement",
        "price_momentum",
        "realized_volatility",
        "route_stress",
        "macro_surprise",
    )
    rows = []
    for index in range(6):
        rows.append(
            {
                "partition": "train",
                "as_of": f"2025-01-0{index + 1}T12:00:00+00:00",
                "features": {
                    name: round((position + 1) * 0.1 + index * 0.01, 4)
                    for position, name in enumerate(names)
                },
            }
        )
    split_identity = "chronological-split:" + stable_hash(["wave-b-contract-fixture"])[:24]
    normalizer = fit_training_normalizer(
        rows,
        feature_names=names,
        training_split_identity=split_identity,
        feature_schema_version="quantum-discovery-features.v1",
    )
    feature_values = {
        name: round((position + 1) * 0.12, 4) for position, name in enumerate(names)
    }
    feature_lineage = {
        name: {
            "source_key": f"contract-source-{position + 1}",
            "artifact_ref": f"contract://wave-b/{name}",
            "artifact_hash": stable_hash({"fixture": name}),
            "available_at": "2025-01-07T11:00:00+00:00",
            "missingness_reason": None,
        }
        for position, name in enumerate(names)
    }
    window = build_quantum_discovery_window(
        as_of="2025-01-07T12:00:00+00:00",
        market_sleeve="crude_oil",
        target_instrument="BNO",
        feature_values=feature_values,
        feature_lineage=feature_lineage,
        normalizer=normalizer,
        encoding_version="rotation-feature-map.v1",
        random_seed=1729,
        maximum_input_age_seconds=86_400,
        contract_fixture_only=True,
    )
    return normalizer, window


def build_shared_manifest_contract(
    *,
    empirical_evidence_ready: bool,
    empirical_blockers: Iterable[str],
) -> dict[str, Any]:
    normalizer, window = _contract_fixture()
    duplicate = build_quantum_discovery_window(
        as_of=window.as_of,
        market_sleeve=window.market_sleeve,
        target_instrument=window.target_instrument,
        feature_values=dict(zip(window.feature_names, window.raw_feature_values, strict=True)),
        feature_lineage={item["feature_name"]: item for item in window.feature_lineage},
        normalizer=normalizer,
        encoding_version=window.encoding_version,
        random_seed=window.random_seed,
        maximum_input_age_seconds=window.maximum_input_age_seconds,
        contract_fixture_only=True,
    )
    deterministic = duplicate.manifest_hash == window.manifest_hash
    blockers = sorted(set(str(item) for item in empirical_blockers if str(item)))
    return {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "status": (
            "shared_manifest_ready"
            if empirical_evidence_ready and deterministic
            else "shared_manifest_contract_ready_evidence_maturing"
        ),
        "implementation_contract_ready": deterministic,
        "empirical_manifest_ready": empirical_evidence_ready and deterministic,
        "empirical_blockers": blockers,
        "normalizer_contract": normalizer,
        "contract_fixture_window": window.to_dict(),
        "contract_fixture_only": True,
        "deterministic_rebuild_passed": deterministic,
        "classical_quantum_manifest_hash_equal": (
            window.to_dict()["consumer_manifest_hashes"]["classical_discovery"]
            == window.to_dict()["consumer_manifest_hashes"]["quantum_assisted_discovery"]
        ),
        "future_labels_available_to_manifest": False,
        "hardware_job_authorized": False,
        "authority": evidence_authority(),
        "boundary": (
            "The fixture proves the manifest contract only. It is not empirical evidence, "
            "a quantum result, a validated edge, a strategy, or a trade."
        ),
    }


def validate_shared_manifest_contract(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != CONTRACT_SCHEMA_VERSION:
        errors.append("shared_manifest_schema_invalid")
    if payload.get("implementation_contract_ready") is not True:
        errors.append("shared_manifest_contract_not_ready")
    if payload.get("contract_fixture_only") is not True:
        errors.append("shared_manifest_fixture_not_labeled")
    if payload.get("deterministic_rebuild_passed") is not True:
        errors.append("shared_manifest_not_deterministic")
    if payload.get("classical_quantum_manifest_hash_equal") is not True:
        errors.append("shared_manifest_lane_hash_divergence")
    if payload.get("future_labels_available_to_manifest") is not False:
        errors.append("shared_manifest_future_labels_exposed")
    if payload.get("hardware_job_authorized") is not False:
        errors.append("shared_manifest_hardware_authority_escalated")
    normalizer = payload.get("normalizer_contract")
    if not isinstance(normalizer, dict):
        errors.append("shared_manifest_normalizer_missing")
    else:
        errors.extend(validate_training_normalizer(normalizer))
    window = payload.get("contract_fixture_window")
    if not isinstance(window, dict):
        errors.append("shared_manifest_window_missing")
    else:
        errors.extend(validate_quantum_discovery_window(window))
    if payload.get("empirical_manifest_ready") is True and payload.get("empirical_blockers"):
        errors.append("shared_manifest_empirical_ready_with_blockers")
    authority = payload.get("authority", {})
    for field_name in ZERO_AUTHORITY_FIELDS:
        if authority.get(field_name) is not False:
            errors.append(f"shared_manifest_authority_escalated:{field_name}")
    return sorted(set(errors))


def write_shared_manifest_contract(
    payload: dict[str, Any], settings: Settings | None = None
) -> Path:
    errors = validate_shared_manifest_contract(payload)
    if errors:
        raise ValueError(f"shared_manifest_contract_invalid:{','.join(errors)}")
    return _write_json_atomic(_runtime_dir(settings) / CONTRACT_ARTIFACT, payload)
