"""Shared input, candidate, and result contracts for Quantum Edge Wave C."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol

import numpy as np

from orchestrator.qadam_quantum_discovery_evidence import stable_hash
from orchestrator.qadam_quantum_discovery_manifest import (
    QuantumDiscoveryWindow,
    validate_quantum_discovery_window,
)
from orchestrator.qadam_quantum_edge_governance import (
    ZERO_AUTHORITY_FIELDS,
    quantum_research_authority,
)

BATCH_SCHEMA_VERSION = "qadam.DiscoveryInputBatch.v1"
CANDIDATE_SCHEMA_VERSION = "qadam.DiscoveryResearchCandidate.v1"
CLASSICAL_RESULT_SCHEMA_VERSION = "qadam.ClassicalDiscoveryResult.v1"
QUANTUM_RESULT_SCHEMA_VERSION = "qadam.QuantumDiscoveryBackendResult.v1"

MIN_BATCH_ROWS = 8
MAX_BATCH_ROWS = 256


def _downstream_authority(*, quantum_candidate_allowed: bool) -> dict[str, bool]:
    authority = quantum_research_authority()
    authority["quantum_research_candidate_allowed"] = quantum_candidate_allowed
    authority["research_candidate_creation_allowed"] = True
    authority["candidate_persistence_allowed"] = False
    return authority


@dataclass(frozen=True, kw_only=True)
class DiscoveryInputBatch:
    batch_id: str
    shared_manifest_hash: str
    market_sleeve: str
    target_instrument: str
    feature_names: tuple[str, ...]
    matrix: tuple[tuple[float, ...], ...]
    missingness_masks: tuple[tuple[int, ...], ...]
    window_manifest_hashes: tuple[str, ...]
    window_ids: tuple[str, ...]
    feature_schema_version: str
    chronological_split_identity: str
    encoding_version: str
    random_seed: int
    contract_fixture_only: bool
    labels_present: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": BATCH_SCHEMA_VERSION,
            **asdict(self),
            "authority": {
                "read_only": True,
                "research_only": True,
                **{field_name: False for field_name in ZERO_AUTHORITY_FIELDS},
            },
        }


def _batch_material(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: payload.get(key)
        for key in (
            "market_sleeve",
            "target_instrument",
            "feature_names",
            "matrix",
            "missingness_masks",
            "window_manifest_hashes",
            "window_ids",
            "feature_schema_version",
            "chronological_split_identity",
            "encoding_version",
            "random_seed",
            "contract_fixture_only",
            "labels_present",
        )
    }


def build_discovery_input_batch(
    windows: list[QuantumDiscoveryWindow | dict[str, Any]],
) -> DiscoveryInputBatch:
    if not MIN_BATCH_ROWS <= len(windows) <= MAX_BATCH_ROWS:
        raise ValueError("discovery_batch_row_count_unsupported")
    payloads = [window.to_dict() if isinstance(window, QuantumDiscoveryWindow) else window for window in windows]
    for payload in payloads:
        errors = validate_quantum_discovery_window(payload)
        if errors:
            raise ValueError(f"discovery_batch_window_invalid:{','.join(errors)}")

    first = payloads[0]
    invariant_fields = (
        "market_sleeve",
        "target_instrument",
        "feature_names",
        "feature_schema_version",
        "chronological_split_identity",
        "encoding_version",
        "random_seed",
        "contract_fixture_only",
    )
    for field_name in invariant_fields:
        if any(payload.get(field_name) != first.get(field_name) for payload in payloads[1:]):
            raise ValueError(f"discovery_batch_invariant_mismatch:{field_name}")
    if any(payload.get("labels_present") is not False for payload in payloads):
        raise ValueError("discovery_batch_labels_present")

    ordered = sorted(payloads, key=lambda payload: (str(payload["as_of"]), str(payload["window_id"])))
    material: dict[str, Any] = {
        "market_sleeve": first["market_sleeve"],
        "target_instrument": first["target_instrument"],
        "feature_names": tuple(first["feature_names"]),
        "matrix": tuple(tuple(float(value) for value in payload["normalized_features"]) for payload in ordered),
        "missingness_masks": tuple(tuple(int(value) for value in payload["missingness_mask"]) for payload in ordered),
        "window_manifest_hashes": tuple(str(payload["manifest_hash"]) for payload in ordered),
        "window_ids": tuple(str(payload["window_id"]) for payload in ordered),
        "feature_schema_version": first["feature_schema_version"],
        "chronological_split_identity": first["chronological_split_identity"],
        "encoding_version": first["encoding_version"],
        "random_seed": int(first["random_seed"]),
        "contract_fixture_only": first["contract_fixture_only"] is True,
        "labels_present": False,
    }
    shared_manifest_hash = stable_hash(_batch_material(material))
    batch = DiscoveryInputBatch(
        batch_id=f"discovery-batch:{shared_manifest_hash[:24]}",
        shared_manifest_hash=shared_manifest_hash,
        **material,
    )
    errors = validate_discovery_input_batch(batch.to_dict())
    if errors:
        raise ValueError(f"discovery_batch_invalid:{','.join(errors)}")
    return batch


def validate_discovery_input_batch(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != BATCH_SCHEMA_VERSION:
        errors.append("batch_schema_invalid")
    matrix = payload.get("matrix")
    names = payload.get("feature_names")
    masks = payload.get("missingness_masks")
    if not isinstance(matrix, (list, tuple)) or not MIN_BATCH_ROWS <= len(matrix) <= MAX_BATCH_ROWS:
        errors.append("batch_row_count_unsupported")
        matrix = []
    if not isinstance(names, (list, tuple)) or not 4 <= len(names) <= 10:
        errors.append("batch_feature_count_unsupported")
        names = []
    if not isinstance(masks, (list, tuple)) or len(masks) != len(matrix):
        errors.append("batch_missingness_masks_invalid")
        masks = []
    for row_index, row in enumerate(matrix):
        if not isinstance(row, (list, tuple)) or len(row) != len(names):
            errors.append(f"batch_row_shape_invalid:{row_index}")
            continue
        if not all(np.isfinite(float(value)) for value in row):
            errors.append(f"batch_row_not_finite:{row_index}")
    for row_index, mask in enumerate(masks):
        if not isinstance(mask, (list, tuple)) or len(mask) != len(names):
            errors.append(f"batch_mask_shape_invalid:{row_index}")
        elif any(value not in (0, 1) for value in mask):
            errors.append(f"batch_mask_value_invalid:{row_index}")
    if payload.get("labels_present") is not False:
        errors.append("batch_labels_present")
    expected_hash = stable_hash(_batch_material(payload))
    if payload.get("shared_manifest_hash") != expected_hash:
        errors.append("batch_manifest_hash_mismatch")
    if payload.get("batch_id") != f"discovery-batch:{expected_hash[:24]}":
        errors.append("batch_id_hash_mismatch")
    authority = payload.get("authority", {})
    for field_name in ZERO_AUTHORITY_FIELDS:
        if authority.get(field_name) is not False:
            errors.append(f"batch_authority_escalated:{field_name}")
    return sorted(set(errors))


def build_research_candidate(
    *,
    batch: DiscoveryInputBatch,
    discovery_origin: str,
    method: str,
    feature_pair: tuple[str, str],
    structural_score: float,
    question: str,
) -> dict[str, Any]:
    if discovery_origin not in {"classical_discovery", "quantum_assisted_discovery"}:
        raise ValueError("candidate_discovery_origin_invalid")
    if len(feature_pair) != 2 or feature_pair[0] == feature_pair[1]:
        raise ValueError("candidate_feature_pair_invalid")
    score = float(structural_score)
    if not 0 <= score <= 1:
        raise ValueError("candidate_structural_score_invalid")
    identity = stable_hash(
        {
            "manifest": batch.shared_manifest_hash,
            "origin": discovery_origin,
            "method": method,
            "feature_pair": feature_pair,
            "question": question,
        }
    )
    payload = {
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "candidate_id": f"discovery-candidate:{identity[:24]}",
        "shared_manifest_hash": batch.shared_manifest_hash,
        "market_sleeve": batch.market_sleeve,
        "target_instrument": batch.target_instrument,
        "discovery_origin": discovery_origin,
        "validation_contribution": "not_tested",
        "lifecycle_state": "candidate_relationship",
        "method": method,
        "feature_pair": list(feature_pair),
        "structural_score": round(score, 12),
        "research_question": question,
        "contract_fixture_only": batch.contract_fixture_only,
        "candidate_persistence_allowed": not batch.contract_fixture_only,
        "validated_edge_created": False,
        "strategy_hypothesis_created": False,
        "trade_candidate_created": False,
        "paper_order_created": False,
        "proof_eligible": False,
        "authority": _downstream_authority(
            quantum_candidate_allowed=discovery_origin == "quantum_assisted_discovery"
        ),
    }
    errors = validate_research_candidate(payload)
    if errors:
        raise ValueError(f"discovery_candidate_invalid:{','.join(errors)}")
    return payload


def validate_research_candidate(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != CANDIDATE_SCHEMA_VERSION:
        errors.append("candidate_schema_invalid")
    origin = payload.get("discovery_origin")
    if origin not in {"classical_discovery", "quantum_assisted_discovery"}:
        errors.append("candidate_origin_invalid")
    if payload.get("validation_contribution") != "not_tested":
        errors.append("candidate_self_validation_attempted")
    if payload.get("lifecycle_state") != "candidate_relationship":
        errors.append("candidate_lifecycle_invalid")
    if payload.get("contract_fixture_only") is True and payload.get(
        "candidate_persistence_allowed"
    ) is not False:
        errors.append("fixture_candidate_persistence_allowed")
    for field_name in (
        "validated_edge_created",
        "strategy_hypothesis_created",
        "trade_candidate_created",
        "paper_order_created",
        "proof_eligible",
    ):
        if payload.get(field_name) is not False:
            errors.append(f"candidate_downstream_state_created:{field_name}")
    authority = payload.get("authority", {})
    if authority.get("research_candidate_creation_allowed") is not True:
        errors.append("candidate_research_authority_missing")
    expected_quantum = origin == "quantum_assisted_discovery"
    if authority.get("quantum_research_candidate_allowed") is not expected_quantum:
        errors.append("candidate_quantum_authority_mismatch")
    for field_name in ZERO_AUTHORITY_FIELDS:
        if field_name == "quantum_research_candidate_allowed":
            continue
        if authority.get(field_name) is not False:
            errors.append(f"candidate_authority_escalated:{field_name}")
    return sorted(set(errors))


@dataclass(frozen=True, kw_only=True)
class ClassicalDiscoveryResult:
    result_id: str
    shared_manifest_hash: str
    backend_name: str
    execution_mode: str
    policy_hash: str
    policy_contract: dict[str, Any]
    method_results: tuple[dict[str, Any], ...]
    matched_quantum_methods: tuple[dict[str, str], ...]
    research_candidates: tuple[dict[str, Any], ...]
    contract_fixture_only: bool
    labels_present: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CLASSICAL_RESULT_SCHEMA_VERSION,
            **asdict(self),
            "discovery_origin": "classical_discovery",
            "validated_edge_created": False,
            "strategy_hypothesis_created": False,
            "trade_candidate_created": False,
            "paper_order_created": False,
            "hardware_experiment_completed": False,
            "authority": _downstream_authority(quantum_candidate_allowed=False),
        }


@dataclass(frozen=True, kw_only=True)
class QuantumDiscoveryBackendResult:
    result_id: str
    shared_manifest_hash: str
    backend_name: str
    execution_mode: str
    simulation_mode: str
    policy_hash: str
    policy_contract: dict[str, Any]
    matched_classical_result_id: str
    matched_classical_policy_hash: str
    kernel_hash: str | None
    kernel_shape: tuple[int, int]
    circuit_hashes: tuple[str, ...]
    qubit_count: int
    circuit_depth_max: int
    shots: int | None
    landmark_count: int
    circuit_evaluation_count: int
    quantum_simulation_completed: bool
    quantum_execution_claim: bool
    classical_fallback_used: bool
    method_results: tuple[dict[str, Any], ...]
    research_candidates: tuple[dict[str, Any], ...]
    contract_fixture_only: bool
    blocker: str | None
    labels_present: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": QUANTUM_RESULT_SCHEMA_VERSION,
            **asdict(self),
            "discovery_origin": "quantum_assisted_discovery",
            "hardware_execution_authorized": False,
            "hardware_experiment_completed": False,
            "provider_call_attempted": False,
            "validated_edge_created": False,
            "strategy_hypothesis_created": False,
            "trade_candidate_created": False,
            "paper_order_created": False,
            "proof_eligible": False,
            "authority": _downstream_authority(
                quantum_candidate_allowed=self.quantum_simulation_completed
            ),
        }


def validate_discovery_result(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    schema = payload.get("schema_version")
    if schema not in {CLASSICAL_RESULT_SCHEMA_VERSION, QUANTUM_RESULT_SCHEMA_VERSION}:
        errors.append("result_schema_invalid")
    if payload.get("labels_present") is not False:
        errors.append("result_labels_present")
    if not str(payload.get("shared_manifest_hash") or ""):
        errors.append("result_manifest_hash_missing")
    policy_contract = payload.get("policy_contract")
    if not isinstance(policy_contract, dict):
        errors.append("result_policy_contract_missing")
    elif payload.get("policy_hash") != stable_hash(policy_contract):
        errors.append("result_policy_hash_mismatch")
    candidates = payload.get("research_candidates")
    if not isinstance(candidates, (list, tuple)):
        errors.append("result_candidates_invalid")
    else:
        for candidate in candidates:
            if not isinstance(candidate, dict):
                errors.append("result_candidate_not_object")
            else:
                errors.extend(validate_research_candidate(candidate))
                if candidate.get("shared_manifest_hash") != payload.get("shared_manifest_hash"):
                    errors.append("result_candidate_manifest_mismatch")
    for field_name in (
        "validated_edge_created",
        "strategy_hypothesis_created",
        "trade_candidate_created",
        "paper_order_created",
        "hardware_experiment_completed",
    ):
        if payload.get(field_name) is not False:
            errors.append(f"result_downstream_state_created:{field_name}")
    if schema == QUANTUM_RESULT_SCHEMA_VERSION:
        if not str(payload.get("matched_classical_result_id") or ""):
            errors.append("result_matched_classical_id_missing")
        if not str(payload.get("matched_classical_policy_hash") or ""):
            errors.append("result_matched_classical_policy_missing")
        if payload.get("hardware_execution_authorized") is not False:
            errors.append("result_hardware_authority_escalated")
        if payload.get("provider_call_attempted") is not False:
            errors.append("result_provider_call_attempted")
        if payload.get("quantum_simulation_completed") is not True and payload.get(
            "quantum_execution_claim"
        ) is not False:
            errors.append("result_false_quantum_claim")
        if payload.get("classical_fallback_used") is True and payload.get(
            "quantum_execution_claim"
        ) is not False:
            errors.append("result_fallback_mislabeled_quantum")
    authority = payload.get("authority", {})
    for field_name in ZERO_AUTHORITY_FIELDS:
        if field_name == "quantum_research_candidate_allowed":
            continue
        if authority.get(field_name) is not False:
            errors.append(f"result_authority_escalated:{field_name}")
    return sorted(set(errors))


class QuantumDiscoveryBackend(Protocol):
    key: str

    def run(
        self,
        batch: DiscoveryInputBatch,
        *,
        mode: str,
        shots: int | None = None,
        matched_classical_result: ClassicalDiscoveryResult | dict[str, Any],
    ) -> QuantumDiscoveryBackendResult: ...
