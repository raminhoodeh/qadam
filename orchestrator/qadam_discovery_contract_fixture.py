"""Explicitly non-empirical fixtures for Wave C discovery infrastructure tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math

from orchestrator.qadam_discovery_backend import (
    DiscoveryInputBatch,
    build_discovery_input_batch,
)
from orchestrator.qadam_quantum_discovery_evidence import stable_hash
from orchestrator.qadam_quantum_discovery_manifest import (
    build_quantum_discovery_window,
    fit_training_normalizer,
)

FEATURE_NAMES = (
    "source_density",
    "source_agreement",
    "price_momentum",
    "realized_volatility",
    "route_stress",
    "macro_surprise",
)
FEATURE_SCHEMA_VERSION = "wave-c-nonlinear-contract-features.v1"
ENCODING_VERSION = "rotation-entanglement-feature-map.v1"
RANDOM_SEED = 1729


def _feature_values(index: int, *, null_dataset: bool = False) -> dict[str, float]:
    if null_dataset:
        return {name: 0.5 for name in FEATURE_NAMES}
    left = float((index // 2) % 2)
    right = float(index % 2)
    xor = float(int(left != right))
    drift = (index % 5) * 0.015
    return {
        "source_density": left + drift,
        "source_agreement": right - drift / 2,
        "price_momentum": xor + drift / 3,
        "realized_volatility": 0.2 + xor * 0.7 + drift,
        "route_stress": left * right + drift / 4,
        "macro_surprise": 0.5 + math.sin(index * 0.7) * 0.2,
    }


def _build_fixture_batch(*, null_dataset: bool) -> DiscoveryInputBatch:
    split_identity = "chronological-split:" + stable_hash(
        ["wave-c-nonlinear-contract-fixture"]
    )[:24]
    training_start = datetime(2024, 12, 1, 12, tzinfo=timezone.utc)
    training_rows = [
        {
            "partition": "train",
            "as_of": (training_start + timedelta(hours=index)).isoformat(),
            "features": _feature_values(index, null_dataset=null_dataset),
        }
        for index in range(24)
    ]
    normalizer = fit_training_normalizer(
        training_rows,
        feature_names=FEATURE_NAMES,
        training_split_identity=split_identity,
        feature_schema_version=FEATURE_SCHEMA_VERSION,
    )

    discovery_start = datetime(2025, 1, 1, 12, tzinfo=timezone.utc)
    windows = []
    for index in range(16):
        as_of = discovery_start + timedelta(hours=index)
        values = _feature_values(index + 24, null_dataset=null_dataset)
        lineage = {
            name: {
                "source_key": f"contract-fixture:{name}",
                "artifact_ref": f"contract://wave-c/{name}/{index}",
                "artifact_hash": stable_hash(
                    {"fixture": "wave-c", "feature": name, "index": index}
                ),
                "available_at": (as_of - timedelta(minutes=30)).isoformat(),
                "missingness_reason": None,
            }
            for name in FEATURE_NAMES
        }
        windows.append(
            build_quantum_discovery_window(
                as_of=as_of.isoformat(),
                market_sleeve="crude_oil",
                target_instrument="BNO",
                feature_values=values,
                feature_lineage=lineage,
                normalizer=normalizer,
                encoding_version=ENCODING_VERSION,
                random_seed=RANDOM_SEED,
                maximum_input_age_seconds=3_600,
                contract_fixture_only=True,
            )
        )
    return build_discovery_input_batch(windows)


def build_wave_c_contract_fixture_batch() -> DiscoveryInputBatch:
    return _build_fixture_batch(null_dataset=False)


def build_wave_c_null_fixture_batch() -> DiscoveryInputBatch:
    return _build_fixture_batch(null_dataset=True)
