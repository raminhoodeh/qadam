from __future__ import annotations

from copy import deepcopy

import pytest

from orchestrator.qadam_quantum_discovery_evidence import ZERO_AUTHORITY_FIELDS, stable_hash
from orchestrator.qadam_quantum_discovery_manifest import (
    build_quantum_discovery_window,
    build_shared_manifest_contract,
    fit_training_normalizer,
    validate_quantum_discovery_window,
    validate_shared_manifest_contract,
)

FEATURE_NAMES = (
    "source_density",
    "source_agreement",
    "price_momentum",
    "realized_volatility",
    "route_stress",
    "macro_surprise",
)
SPLIT_ID = "chronological-split:" + "a" * 24


def _normalizer():
    rows = [
        {
            "partition": "train",
            "as_of": f"2025-01-0{index + 1}T12:00:00+00:00",
            "features": {
                name: (position + 1) * 0.1 + index * 0.01
                for position, name in enumerate(FEATURE_NAMES)
            },
        }
        for index in range(6)
    ]
    return fit_training_normalizer(
        rows,
        feature_names=FEATURE_NAMES,
        training_split_identity=SPLIT_ID,
        feature_schema_version="features-test.v1",
    )


def _values():
    return {name: (position + 1) * 0.12 for position, name in enumerate(FEATURE_NAMES)}


def _lineage():
    return {
        name: {
            "source_key": f"source-{position + 1}",
            "artifact_ref": f"research://feature/{name}",
            "artifact_hash": stable_hash({"feature": name}),
            "available_at": "2025-01-07T11:00:00+00:00",
            "missingness_reason": None,
        }
        for position, name in enumerate(FEATURE_NAMES)
    }


def _window(**overrides):
    params = {
        "as_of": "2025-01-07T12:00:00+00:00",
        "market_sleeve": "crude_oil",
        "target_instrument": "BNO",
        "feature_values": _values(),
        "feature_lineage": _lineage(),
        "normalizer": _normalizer(),
        "encoding_version": "rotation-feature-map.v1",
        "random_seed": 1729,
        "maximum_input_age_seconds": 86_400,
        "contract_fixture_only": True,
    }
    params.update(overrides)
    return build_quantum_discovery_window(**params)


def test_training_normalizer_is_deterministic_and_train_only():
    first = _normalizer()
    second = _normalizer()

    assert first == second
    assert first["fit_scope"] == "train_only"
    assert first["training_split_identity"] == SPLIT_ID
    assert len(first["normalizer_hash"]) == 64
    assert all(first["authority"][field] is False for field in ZERO_AUTHORITY_FIELDS)

    contaminated = [
        {
            "partition": "validation",
            "as_of": "2025-01-01T12:00:00+00:00",
            "features": {name: 0.1 for name in FEATURE_NAMES},
        },
        {
            "partition": "train",
            "as_of": "2025-01-02T12:00:00+00:00",
            "features": {name: 0.2 for name in FEATURE_NAMES},
        },
    ]
    with pytest.raises(ValueError, match="train_only"):
        fit_training_normalizer(
            contaminated,
            feature_names=FEATURE_NAMES,
            training_split_identity=SPLIT_ID,
            feature_schema_version="features-test.v1",
        )


def test_training_normalizer_rejects_future_label_contamination():
    rows = [
        {
            "partition": "train",
            "as_of": f"2025-01-0{index + 1}T12:00:00+00:00",
            "features": {name: 0.1 + index for name in FEATURE_NAMES},
            "future_return": 0.5,
        }
        for index in range(2)
    ]
    with pytest.raises(ValueError, match="future_label_contamination"):
        fit_training_normalizer(
            rows,
            feature_names=FEATURE_NAMES,
            training_split_identity=SPLIT_ID,
            feature_schema_version="features-test.v1",
        )


def test_window_is_deterministic_and_shared_by_both_lanes():
    first = _window().to_dict()
    second = _window().to_dict()

    assert first == second
    assert first["consumer_manifest_hashes"] == {
        "classical_discovery": first["manifest_hash"],
        "quantum_assisted_discovery": first["manifest_hash"],
    }
    assert first["labels_present"] is False
    assert validate_quantum_discovery_window(first) == []


def test_window_rejects_excessive_missingness_and_stale_inputs():
    values = _values()
    lineage = _lineage()
    for name in FEATURE_NAMES[:2]:
        values[name] = None
        lineage[name] = {
            "source_key": None,
            "artifact_ref": None,
            "artifact_hash": None,
            "available_at": None,
            "missingness_reason": "provider_gap",
        }
    with pytest.raises(ValueError, match="excessive_missingness"):
        _window(feature_values=values, feature_lineage=lineage)

    stale_lineage = _lineage()
    stale_lineage[FEATURE_NAMES[0]]["available_at"] = "2025-01-01T00:00:00+00:00"
    with pytest.raises(ValueError, match="feature_stale"):
        _window(feature_lineage=stale_lineage)


def test_window_rejects_unsupported_feature_dimensions():
    rows = [
        {
            "partition": "train",
            "as_of": f"2025-01-0{index + 1}T12:00:00+00:00",
            "features": {f"feature_{position}": position + index for position in range(5)},
        }
        for index in range(2)
    ]
    with pytest.raises(ValueError, match="dimension_unsupported"):
        fit_training_normalizer(
            rows,
            feature_names=tuple(rows[0]["features"]),
            training_split_identity=SPLIT_ID,
            feature_schema_version="features-test.v1",
        )


def test_window_hash_tamper_and_authority_escalation_are_rejected():
    payload = _window().to_dict()
    tampered = deepcopy(payload)
    tampered["normalized_features"] = list(tampered["normalized_features"])
    tampered["normalized_features"][0] += 1
    assert "window_manifest_hash_mismatch" in validate_quantum_discovery_window(tampered)

    escalated = deepcopy(payload)
    escalated["authority"]["paper_order_allowed"] = True
    assert "window_authority_escalated:paper_order_allowed" in (
        validate_quantum_discovery_window(escalated)
    )


def test_shared_manifest_contract_labels_fixture_and_empirical_gap_honestly():
    contract = build_shared_manifest_contract(
        empirical_evidence_ready=False,
        empirical_blockers=["provider_backfill_has_no_rows"],
    )

    assert contract["implementation_contract_ready"] is True
    assert contract["empirical_manifest_ready"] is False
    assert contract["contract_fixture_only"] is True
    assert contract["hardware_job_authorized"] is False
    assert contract["empirical_blockers"] == ["provider_backfill_has_no_rows"]
    assert validate_shared_manifest_contract(contract) == []
