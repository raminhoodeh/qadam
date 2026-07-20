"""Guarded Fire Opal/IBM discovery backend for Quantum Edge Wave D.

Preparing a smoke manifest is local-only. Provider validation and hardware
submission require a separate, exact, single-use authorization contract and an
explicit gateway call. No function in this module runs on import.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Iterator, Protocol

import numpy as np

from orchestrator.config import Settings
from orchestrator.qadam_discovery_backend import (
    ClassicalDiscoveryResult,
    DiscoveryInputBatch,
    QuantumDiscoveryBackendResult,
    build_research_candidate,
    validate_discovery_input_batch,
    validate_discovery_result,
    validate_research_candidate,
)
from orchestrator.qadam_local_quantum_discovery import (
    LocalQuantumDiscoveryPolicy,
    analyze_fidelity_kernel,
    build_feature_map_circuits,
    nystrom_fidelity_pairs,
    reconstruct_nystrom_kernel,
    select_landmark_indices,
)
from orchestrator.qadam_quantum_discovery_evidence import stable_hash
from orchestrator.qadam_quantum_edge_governance import ZERO_AUTHORITY_FIELDS
from orchestrator.secrets import secret_value

POLICY_SCHEMA_VERSION = "qadam.FireOpalIbmBudgetPolicy.v1"
MANIFEST_SCHEMA_VERSION = "qadam.FireOpalIbmSmokeManifest.v1"
AUTHORIZATION_SCHEMA_VERSION = "qadam.FireOpalIbmExecutionAuthorization.v1"
STATE_SCHEMA_VERSION = "qadam.FireOpalIbmExperimentState.v1"
RECEIPT_SCHEMA_VERSION = "qadam.FireOpalIbmDiscoveryReceipt.v1"
PRIVATE_STATE_SCHEMA_VERSION = "qadam.FireOpalIbmPrivateState.v1"

PROVIDER_NAME = "qctrl_fire_opal_ibm"
EXPERIMENT_KIND = "nystrom_fidelity_kernel_smoke"
PENDING_PROVIDER_STATUSES = {"PENDING", "RECEIVED", "RETRY", "STARTED"}
TERMINAL_PROVIDER_STATUSES = {"SUCCESS", "FAILURE", "REVOKED"}

HARDWARE_ZERO_AUTHORITY_FIELDS = (
    *ZERO_AUTHORITY_FIELDS,
    "hardware_validation_allowed",
    "hardware_execution_authorized",
    "hardware_submission_allowed",
    "hardware_scheduler_enabled",
    "hardware_retry_allowed",
)

PUBLIC_FORBIDDEN_KEYS = {
    "action_id",
    "api_key",
    "approval_nonce",
    "backend_name",
    "circuits",
    "credentials",
    "instance",
    "provider_job_ids",
    "qasm_circuits",
    "raw_provider_response",
    "secret",
    "token",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_timestamp(value: str, *, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ValueError(f"{field_name}_invalid") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field_name}_timezone_missing")
    return parsed.astimezone(timezone.utc)


def _public_authority() -> dict[str, bool]:
    return {
        "research_candidate_creation_allowed": False,
        "quantum_research_candidate_allowed": False,
        **{field_name: False for field_name in HARDWARE_ZERO_AUTHORITY_FIELDS},
    }


def _backend_hash(backend_name: str) -> str:
    if not backend_name.strip():
        raise ValueError("fire_opal_backend_name_missing")
    return sha256(backend_name.encode("utf-8")).hexdigest()


def _action_hash(action_id: str) -> str:
    if not action_id.strip():
        raise ValueError("fire_opal_action_id_missing")
    return sha256(action_id.encode("utf-8")).hexdigest()


def _contains_forbidden_public_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in PUBLIC_FORBIDDEN_KEYS:
                return True
            if _contains_forbidden_public_key(child):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_forbidden_public_key(child) for child in value)
    return False


@dataclass(frozen=True, kw_only=True)
class FireOpalIbmBudgetPolicy:
    maximum_qubits: int = 8
    maximum_circuit_depth: int = 64
    maximum_circuits: int = 128
    shots_per_circuit: int = 256
    maximum_total_shots: int = 32_768
    maximum_qasm_bytes_per_circuit: int = 65_536
    maximum_total_qasm_bytes: int = 4_000_000
    maximum_submission_attempts: int = 1
    maximum_poll_failures: int = 3
    maximum_poll_count: int = 120
    maximum_wall_clock_seconds: int = 7_200
    maximum_provider_budget_usd: float = 10.0
    nystrom_ridge: float = 1e-8
    interaction_candidate_threshold: float = 0.25
    classical_rbf_gamma: float = 0.5
    random_seed: int = 1729

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": POLICY_SCHEMA_VERSION, **asdict(self)}

    @property
    def policy_hash(self) -> str:
        return stable_hash(self.to_dict())


def validate_budget_policy(policy: FireOpalIbmBudgetPolicy) -> None:
    if not 4 <= policy.maximum_qubits <= 8:
        raise ValueError("fire_opal_budget_qubits_invalid")
    if policy.maximum_circuit_depth <= 0 or policy.maximum_circuits <= 0:
        raise ValueError("fire_opal_budget_circuit_limits_invalid")
    if policy.shots_per_circuit <= 0 or policy.maximum_total_shots <= 0:
        raise ValueError("fire_opal_budget_shots_invalid")
    if (
        policy.maximum_qasm_bytes_per_circuit <= 0
        or policy.maximum_total_qasm_bytes <= 0
    ):
        raise ValueError("fire_opal_budget_qasm_size_invalid")
    if policy.maximum_submission_attempts != 1:
        raise ValueError("fire_opal_budget_submission_attempts_must_be_one")
    if policy.maximum_poll_failures <= 0 or policy.maximum_poll_count <= 0:
        raise ValueError("fire_opal_budget_poll_limits_invalid")
    if policy.maximum_wall_clock_seconds <= 0:
        raise ValueError("fire_opal_budget_wall_clock_invalid")
    if policy.maximum_provider_budget_usd <= 0:
        raise ValueError("fire_opal_budget_provider_cost_invalid")
    if policy.nystrom_ridge <= 0 or policy.classical_rbf_gamma <= 0:
        raise ValueError("fire_opal_budget_kernel_settings_invalid")
    if not 0 <= policy.interaction_candidate_threshold <= 1:
        raise ValueError("fire_opal_budget_candidate_threshold_invalid")
    if isinstance(policy.random_seed, bool) or policy.random_seed < 0:
        raise ValueError("fire_opal_budget_random_seed_invalid")


@dataclass(frozen=True, kw_only=True)
class PreparedFireOpalIbmManifest:
    manifest_id: str
    manifest_hash: str
    shared_manifest_hash: str
    discovery_batch_id: str
    classical_result_id: str
    classical_policy_hash: str
    local_quantum_result_id: str
    local_quantum_policy_hash: str
    local_quantum_kernel_hash: str
    policy_hash: str
    policy_contract: dict[str, Any]
    experiment_kind: str
    qasm_format: str
    row_count: int
    feature_count: int
    qubit_count: int
    landmark_indices: tuple[int, ...]
    circuit_pairs: tuple[tuple[int, int], ...]
    source_feature_circuit_hashes: tuple[str, ...]
    circuit_hashes: tuple[str, ...]
    circuit_depths: tuple[int, ...]
    circuit_depth_max: int
    circuit_count: int
    shots_per_circuit: int
    total_shots: int
    qasm_bytes_total: int
    local_qasm_validation_passed: bool
    prepared_at: str
    contract_fixture_only: bool

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            **asdict(self),
            "provider": PROVIDER_NAME,
            "status": "prepared_local_validation_passed",
            "provider_validation_required": True,
            "provider_validation_completed": False,
            "hardware_execution_authorized": False,
            "hardware_job_submitted": False,
            "hardware_experiment_completed": False,
            "secret_value_exposed": False,
            "raw_provider_response_persisted": False,
            "authority": _public_authority(),
        }


@dataclass(frozen=True, kw_only=True)
class PreparedFireOpalIbmBundle:
    manifest: PreparedFireOpalIbmManifest
    qasm_circuits: tuple[str, ...]

    def to_private_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PRIVATE_STATE_SCHEMA_VERSION,
            "manifest_hash": self.manifest.manifest_hash,
            "qasm_circuits": list(self.qasm_circuits),
            "lifecycle_status": "prepared",
            "submission_attempt_count": 0,
            "poll_count": 0,
            "poll_failure_count": 0,
            "action_id": None,
            "backend_name": None,
            "submitted_at": None,
            "updated_at": self.manifest.prepared_at,
        }


def _manifest_material(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: payload.get(key)
        for key in (
            "shared_manifest_hash",
            "discovery_batch_id",
            "classical_result_id",
            "classical_policy_hash",
            "local_quantum_result_id",
            "local_quantum_policy_hash",
            "local_quantum_kernel_hash",
            "policy_hash",
            "experiment_kind",
            "qasm_format",
            "row_count",
            "feature_count",
            "qubit_count",
            "landmark_indices",
            "circuit_pairs",
            "source_feature_circuit_hashes",
            "circuit_hashes",
            "circuit_depths",
            "circuit_depth_max",
            "circuit_count",
            "shots_per_circuit",
            "total_shots",
            "qasm_bytes_total",
            "local_qasm_validation_passed",
            "contract_fixture_only",
        )
    }


def _local_quantum_policy(payload: dict[str, Any]) -> LocalQuantumDiscoveryPolicy:
    fields = {
        key: value
        for key, value in payload.items()
        if key != "schema_version"
    }
    try:
        return LocalQuantumDiscoveryPolicy(**fields)
    except TypeError as exc:
        raise ValueError("fire_opal_local_quantum_policy_invalid") from exc


def _validated_result_payload(
    result: ClassicalDiscoveryResult | QuantumDiscoveryBackendResult | dict[str, Any],
) -> dict[str, Any]:
    payload = result.to_dict() if hasattr(result, "to_dict") else result
    if not isinstance(payload, dict):
        raise ValueError("fire_opal_discovery_result_not_object")
    errors = validate_discovery_result(payload)
    if errors:
        raise ValueError(f"fire_opal_discovery_result_invalid:{','.join(errors)}")
    return payload


def _overlap_circuit(left: Any, right: Any) -> Any:
    from qiskit import QuantumCircuit

    if left.num_qubits != right.num_qubits:
        raise ValueError("fire_opal_overlap_qubit_mismatch")
    circuit = QuantumCircuit(left.num_qubits)
    circuit.compose(left, inplace=True)
    circuit.compose(right.inverse(), inplace=True)
    circuit.measure_all()
    return circuit


def _serialize_and_validate_circuit(
    circuit: Any,
    *,
    policy: FireOpalIbmBudgetPolicy,
) -> tuple[str, int, int]:
    from qiskit import qasm2

    qasm = qasm2.dumps(circuit)
    encoded_size = len(qasm.encode("utf-8"))
    if encoded_size > policy.maximum_qasm_bytes_per_circuit:
        raise ValueError("fire_opal_qasm_circuit_size_exceeded")
    try:
        parsed = qasm2.loads(
            qasm,
            custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS,
        )
    except Exception as exc:  # noqa: BLE001 - parser error must become contract state.
        raise ValueError("fire_opal_qasm_parse_failed") from exc
    if parsed.num_qubits <= 0 or parsed.num_qubits > policy.maximum_qubits:
        raise ValueError("fire_opal_qasm_qubit_budget_exceeded")
    if parsed.num_clbits <= 0 or int(parsed.count_ops().get("measure", 0)) <= 0:
        raise ValueError("fire_opal_qasm_measurement_missing")
    depth = int(parsed.depth())
    if depth > policy.maximum_circuit_depth:
        raise ValueError("fire_opal_qasm_depth_budget_exceeded")
    if not qasm.startswith("OPENQASM 2.0;"):
        raise ValueError("fire_opal_qasm_format_invalid")
    return qasm, depth, encoded_size


def prepare_fire_opal_ibm_smoke_manifest(
    batch: DiscoveryInputBatch,
    *,
    matched_classical_result: ClassicalDiscoveryResult | dict[str, Any],
    local_quantum_result: QuantumDiscoveryBackendResult | dict[str, Any],
    policy: FireOpalIbmBudgetPolicy | None = None,
    prepared_at: str | None = None,
) -> PreparedFireOpalIbmBundle:
    """Prepare the exact local fidelity experiment for a later hardware run."""

    resolved_policy = policy or FireOpalIbmBudgetPolicy()
    validate_budget_policy(resolved_policy)
    batch_errors = validate_discovery_input_batch(batch.to_dict())
    if batch_errors:
        raise ValueError(f"fire_opal_batch_invalid:{','.join(batch_errors)}")
    classical = _validated_result_payload(matched_classical_result)
    local = _validated_result_payload(local_quantum_result)
    if classical.get("schema_version") != "qadam.ClassicalDiscoveryResult.v1":
        raise ValueError("fire_opal_classical_result_required")
    if local.get("schema_version") != "qadam.QuantumDiscoveryBackendResult.v1":
        raise ValueError("fire_opal_local_quantum_result_required")
    if classical.get("shared_manifest_hash") != batch.shared_manifest_hash:
        raise ValueError("fire_opal_classical_manifest_mismatch")
    if local.get("shared_manifest_hash") != batch.shared_manifest_hash:
        raise ValueError("fire_opal_local_manifest_mismatch")
    if local.get("matched_classical_result_id") != classical.get("result_id"):
        raise ValueError("fire_opal_matched_classical_result_mismatch")
    if local.get("matched_classical_policy_hash") != classical.get("policy_hash"):
        raise ValueError("fire_opal_matched_classical_policy_mismatch")
    if local.get("quantum_simulation_completed") is not True:
        raise ValueError("fire_opal_local_quantum_simulation_required")
    if local.get("classical_fallback_used") is not False:
        raise ValueError("fire_opal_classical_fallback_not_hardware_eligible")

    local_policy = _local_quantum_policy(local.get("policy_contract") or {})
    feature_circuits, qubit_count = build_feature_map_circuits(batch, local_policy)
    if qubit_count > resolved_policy.maximum_qubits:
        raise ValueError("fire_opal_manifest_qubit_budget_exceeded")
    from qiskit.qasm2 import dumps

    source_hashes = tuple(stable_hash(dumps(circuit)) for circuit in feature_circuits)
    if tuple(local.get("circuit_hashes") or ()) != source_hashes:
        raise ValueError("fire_opal_local_circuit_lineage_mismatch")
    landmarks = select_landmark_indices(
        len(feature_circuits), local_policy.maximum_landmarks
    )
    if len(landmarks) != int(local.get("landmark_count") or 0):
        raise ValueError("fire_opal_local_landmark_lineage_mismatch")
    pairs = nystrom_fidelity_pairs(len(feature_circuits), landmarks)
    if len(pairs) != int(local.get("circuit_evaluation_count") or 0):
        raise ValueError("fire_opal_local_evaluation_lineage_mismatch")
    if len(pairs) > resolved_policy.maximum_circuits:
        raise ValueError("fire_opal_manifest_circuit_budget_exceeded")

    qasm_circuits: list[str] = []
    depths: list[int] = []
    qasm_sizes: list[int] = []
    for left, right in pairs:
        qasm, depth, encoded_size = _serialize_and_validate_circuit(
            _overlap_circuit(feature_circuits[left], feature_circuits[right]),
            policy=resolved_policy,
        )
        qasm_circuits.append(qasm)
        depths.append(depth)
        qasm_sizes.append(encoded_size)
    qasm_total = sum(qasm_sizes)
    if qasm_total > resolved_policy.maximum_total_qasm_bytes:
        raise ValueError("fire_opal_manifest_total_qasm_budget_exceeded")
    total_shots = len(qasm_circuits) * resolved_policy.shots_per_circuit
    if total_shots > resolved_policy.maximum_total_shots:
        raise ValueError("fire_opal_manifest_total_shot_budget_exceeded")

    timestamp = prepared_at or _now_iso()
    _parse_timestamp(timestamp, field_name="fire_opal_prepared_at")
    material = {
        "shared_manifest_hash": batch.shared_manifest_hash,
        "discovery_batch_id": batch.batch_id,
        "classical_result_id": classical["result_id"],
        "classical_policy_hash": classical["policy_hash"],
        "local_quantum_result_id": local["result_id"],
        "local_quantum_policy_hash": local["policy_hash"],
        "local_quantum_kernel_hash": local["kernel_hash"],
        "policy_hash": resolved_policy.policy_hash,
        "experiment_kind": EXPERIMENT_KIND,
        "qasm_format": "openqasm_2",
        "row_count": len(batch.matrix),
        "feature_count": len(batch.feature_names),
        "qubit_count": qubit_count,
        "landmark_indices": landmarks,
        "circuit_pairs": pairs,
        "source_feature_circuit_hashes": source_hashes,
        "circuit_hashes": tuple(stable_hash(qasm) for qasm in qasm_circuits),
        "circuit_depths": tuple(depths),
        "circuit_depth_max": max(depths),
        "circuit_count": len(qasm_circuits),
        "shots_per_circuit": resolved_policy.shots_per_circuit,
        "total_shots": total_shots,
        "qasm_bytes_total": qasm_total,
        "local_qasm_validation_passed": True,
        "contract_fixture_only": batch.contract_fixture_only,
    }
    manifest_hash = stable_hash(material)
    manifest = PreparedFireOpalIbmManifest(
        manifest_id=f"fire-opal-ibm-smoke:{manifest_hash[:24]}",
        manifest_hash=manifest_hash,
        policy_contract=resolved_policy.to_dict(),
        prepared_at=timestamp,
        **material,
    )
    errors = validate_prepared_manifest(manifest.to_public_dict())
    if errors:
        raise ValueError(f"fire_opal_manifest_invalid:{','.join(errors)}")
    return PreparedFireOpalIbmBundle(
        manifest=manifest,
        qasm_circuits=tuple(qasm_circuits),
    )


def validate_prepared_manifest(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        errors.append("manifest_schema_invalid")
    if payload.get("provider") != PROVIDER_NAME:
        errors.append("manifest_provider_invalid")
    policy_payload = payload.get("policy_contract")
    if not isinstance(policy_payload, dict) or payload.get("policy_hash") != stable_hash(
        policy_payload
    ):
        errors.append("manifest_policy_hash_mismatch")
        policy = None
    else:
        try:
            policy = FireOpalIbmBudgetPolicy(
                **{
                    key: value
                    for key, value in policy_payload.items()
                    if key != "schema_version"
                }
            )
            validate_budget_policy(policy)
        except (TypeError, ValueError):
            errors.append("manifest_policy_invalid")
            policy = None
    expected_hash = stable_hash(_manifest_material(payload))
    if payload.get("manifest_hash") != expected_hash:
        errors.append("manifest_hash_mismatch")
    if payload.get("manifest_id") != f"fire-opal-ibm-smoke:{expected_hash[:24]}":
        errors.append("manifest_id_mismatch")
    circuit_count = int(payload.get("circuit_count") or 0)
    if circuit_count <= 0:
        errors.append("manifest_circuit_count_invalid")
    for key in ("circuit_pairs", "circuit_hashes", "circuit_depths"):
        value = payload.get(key)
        if not isinstance(value, (list, tuple)) or len(value) != circuit_count:
            errors.append(f"manifest_{key}_count_mismatch")
    row_count = int(payload.get("row_count") or 0)
    feature_count = int(payload.get("feature_count") or 0)
    landmarks = payload.get("landmark_indices")
    if row_count <= 0 or not 4 <= feature_count <= 10:
        errors.append("manifest_input_shape_invalid")
    if not isinstance(landmarks, (list, tuple)) or not landmarks:
        errors.append("manifest_landmarks_invalid")
    elif row_count > 0:
        try:
            expected_pairs = nystrom_fidelity_pairs(
                row_count,
                tuple(int(value) for value in landmarks),
            )
            actual_pairs = tuple(
                (int(pair[0]), int(pair[1])) for pair in payload.get("circuit_pairs", ())
            )
            if actual_pairs != expected_pairs:
                errors.append("manifest_circuit_pairs_invalid")
        except (TypeError, ValueError, IndexError):
            errors.append("manifest_circuit_pairs_invalid")
    source_hashes = payload.get("source_feature_circuit_hashes")
    if not isinstance(source_hashes, (list, tuple)) or len(source_hashes) != row_count:
        errors.append("manifest_source_circuit_hashes_invalid")
    if payload.get("experiment_kind") != EXPERIMENT_KIND:
        errors.append("manifest_experiment_kind_invalid")
    if payload.get("qasm_format") != "openqasm_2":
        errors.append("manifest_qasm_format_invalid")
    try:
        _parse_timestamp(str(payload.get("prepared_at") or ""), field_name="manifest_prepared_at")
    except ValueError:
        errors.append("manifest_prepared_at_invalid")
    if policy is not None:
        qubit_count = int(payload.get("qubit_count") or 0)
        depths = [int(value) for value in payload.get("circuit_depths", ())]
        if qubit_count <= 0 or qubit_count > policy.maximum_qubits:
            errors.append("manifest_qubit_budget_exceeded")
        if circuit_count > policy.maximum_circuits:
            errors.append("manifest_circuit_budget_exceeded")
        if depths and (
            max(depths) > policy.maximum_circuit_depth
            or int(payload.get("circuit_depth_max") or 0) != max(depths)
        ):
            errors.append("manifest_depth_budget_exceeded")
        if payload.get("shots_per_circuit") != policy.shots_per_circuit:
            errors.append("manifest_shots_policy_mismatch")
        if int(payload.get("total_shots") or 0) > policy.maximum_total_shots:
            errors.append("manifest_total_shot_budget_exceeded")
        if int(payload.get("qasm_bytes_total") or 0) > policy.maximum_total_qasm_bytes:
            errors.append("manifest_qasm_budget_exceeded")
    if payload.get("total_shots") != circuit_count * int(
        payload.get("shots_per_circuit") or 0
    ):
        errors.append("manifest_total_shots_mismatch")
    if payload.get("local_qasm_validation_passed") is not True:
        errors.append("manifest_local_validation_missing")
    for key in (
        "provider_validation_completed",
        "hardware_execution_authorized",
        "hardware_job_submitted",
        "hardware_experiment_completed",
        "secret_value_exposed",
        "raw_provider_response_persisted",
    ):
        if payload.get(key) is not False:
            errors.append(f"manifest_forbidden_state:{key}")
    authority = payload.get("authority", {})
    for key in HARDWARE_ZERO_AUTHORITY_FIELDS:
        if authority.get(key) is not False:
            errors.append(f"manifest_authority_escalated:{key}")
    if _contains_forbidden_public_key(payload):
        errors.append("manifest_forbidden_public_key")
    return sorted(set(errors))


@dataclass(frozen=True, kw_only=True)
class FireOpalIbmExecutionAuthorization:
    authorization_id: str
    manifest_hash: str
    backend_name_hash: str
    approved_circuit_count: int
    approved_shots_per_circuit: int
    approved_total_shots: int
    estimated_provider_cost_usd: float
    maximum_provider_cost_usd: float
    issued_at: str
    expires_at: str
    approval_nonce_hash: str
    operator_approved: bool
    provider_validation_allowed: bool
    hardware_submission_allowed: bool
    single_use: bool
    hardware_scheduler_enabled: bool = False

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "schema_version": AUTHORIZATION_SCHEMA_VERSION,
            **asdict(self),
            "trade_candidate_authority": False,
            "paper_order_allowed": False,
            "live_capital_enabled": False,
            "secret_value_exposed": False,
        }


def build_execution_authorization(
    manifest: PreparedFireOpalIbmManifest,
    *,
    backend_name: str,
    approval_nonce: str,
    estimated_provider_cost_usd: float,
    maximum_provider_cost_usd: float,
    issued_at: str,
    expires_at: str,
    explicit_operator_approval: bool,
) -> FireOpalIbmExecutionAuthorization:
    """Build an exact one-time authorization; this function performs no I/O."""

    if explicit_operator_approval is not True:
        raise PermissionError("fire_opal_explicit_operator_approval_required")
    if len(approval_nonce) < 16:
        raise ValueError("fire_opal_approval_nonce_too_short")
    issued = _parse_timestamp(issued_at, field_name="fire_opal_authorization_issued_at")
    expires = _parse_timestamp(expires_at, field_name="fire_opal_authorization_expires_at")
    if expires <= issued:
        raise ValueError("fire_opal_authorization_expiry_invalid")
    if estimated_provider_cost_usd < 0 or maximum_provider_cost_usd <= 0:
        raise ValueError("fire_opal_authorization_provider_cost_invalid")
    policy_cap = float(manifest.policy_contract["maximum_provider_budget_usd"])
    if maximum_provider_cost_usd > policy_cap:
        raise ValueError("fire_opal_authorization_provider_budget_exceeds_policy")
    if estimated_provider_cost_usd > maximum_provider_cost_usd:
        raise ValueError("fire_opal_authorization_estimate_exceeds_approval")

    backend_name_hash = _backend_hash(backend_name)
    nonce_hash = stable_hash(approval_nonce)
    material = {
        "manifest_hash": manifest.manifest_hash,
        "backend_name_hash": backend_name_hash,
        "approved_circuit_count": manifest.circuit_count,
        "approved_shots_per_circuit": manifest.shots_per_circuit,
        "approved_total_shots": manifest.total_shots,
        "estimated_provider_cost_usd": round(float(estimated_provider_cost_usd), 6),
        "maximum_provider_cost_usd": round(float(maximum_provider_cost_usd), 6),
        "issued_at": issued_at,
        "expires_at": expires_at,
        "approval_nonce_hash": nonce_hash,
        "operator_approved": True,
        "provider_validation_allowed": True,
        "hardware_submission_allowed": True,
        "single_use": True,
        "hardware_scheduler_enabled": False,
    }
    authorization_id = f"fire-opal-authorization:{stable_hash(material)[:24]}"
    authorization = FireOpalIbmExecutionAuthorization(
        authorization_id=authorization_id,
        **material,
    )
    validate_execution_authorization(
        authorization,
        manifest=manifest,
        backend_name=backend_name,
        approval_nonce=approval_nonce,
        now=issued,
    )
    return authorization


def validate_execution_authorization(
    authorization: FireOpalIbmExecutionAuthorization,
    *,
    manifest: PreparedFireOpalIbmManifest,
    backend_name: str,
    approval_nonce: str,
    now: datetime | None = None,
) -> None:
    payload = authorization.to_public_dict()
    if payload.get("schema_version") != AUTHORIZATION_SCHEMA_VERSION:
        raise ValueError("fire_opal_authorization_schema_invalid")
    authorization_material = asdict(authorization)
    authorization_material.pop("authorization_id", None)
    expected_id = f"fire-opal-authorization:{stable_hash(authorization_material)[:24]}"
    if authorization.authorization_id != expected_id:
        raise ValueError("fire_opal_authorization_id_mismatch")
    if authorization.manifest_hash != manifest.manifest_hash:
        raise PermissionError("fire_opal_authorization_manifest_mismatch")
    if authorization.backend_name_hash != _backend_hash(backend_name):
        raise PermissionError("fire_opal_authorization_backend_mismatch")
    if authorization.approval_nonce_hash != stable_hash(approval_nonce):
        raise PermissionError("fire_opal_authorization_nonce_mismatch")
    if authorization.operator_approved is not True:
        raise PermissionError("fire_opal_authorization_operator_approval_missing")
    if (
        authorization.provider_validation_allowed is not True
        or authorization.hardware_submission_allowed is not True
        or authorization.single_use is not True
        or authorization.hardware_scheduler_enabled is not False
    ):
        raise PermissionError("fire_opal_authorization_scope_invalid")
    if authorization.approved_circuit_count != manifest.circuit_count:
        raise PermissionError("fire_opal_authorization_circuit_count_mismatch")
    if authorization.approved_shots_per_circuit != manifest.shots_per_circuit:
        raise PermissionError("fire_opal_authorization_shots_mismatch")
    if authorization.approved_total_shots != manifest.total_shots:
        raise PermissionError("fire_opal_authorization_total_shots_mismatch")
    if authorization.maximum_provider_cost_usd > float(
        manifest.policy_contract["maximum_provider_budget_usd"]
    ):
        raise PermissionError("fire_opal_authorization_budget_exceeds_manifest")
    if authorization.estimated_provider_cost_usd > authorization.maximum_provider_cost_usd:
        raise PermissionError("fire_opal_authorization_estimate_exceeds_budget")
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    issued = _parse_timestamp(
        authorization.issued_at, field_name="fire_opal_authorization_issued_at"
    )
    expires = _parse_timestamp(
        authorization.expires_at, field_name="fire_opal_authorization_expires_at"
    )
    if current < issued or current >= expires:
        raise PermissionError("fire_opal_authorization_not_current")
    if _contains_forbidden_public_key(payload):
        raise ValueError("fire_opal_authorization_not_public_safe")


class FireOpalIbmGateway(Protocol):
    """Minimal provider surface used only after explicit authorization."""

    def validate_circuits(
        self,
        *,
        qasm_circuits: tuple[str, ...],
        backend_name: str,
    ) -> dict[str, Any]: ...

    def submit_circuits(
        self,
        *,
        qasm_circuits: tuple[str, ...],
        shots_per_circuit: int,
        backend_name: str,
    ) -> str: ...

    def job_status(self, *, action_id: str) -> str: ...

    def job_result(self, *, action_id: str) -> dict[str, Any]: ...


class FireOpalSdkIbmGateway:
    """Lazy Fire Opal SDK adapter. Construction performs no provider call."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self._fire_opal: Any | None = None
        self._credentials: dict[str, str] | None = None

    def _provider_session(self) -> tuple[Any, dict[str, str]]:
        if self._fire_opal is not None and self._credentials is not None:
            return self._fire_opal, self._credentials
        from orchestrator.quantum import _import_fireopal_without_update_check

        fire_opal = _import_fireopal_without_update_check()
        organization = (
            secret_value("QCTRL_ORGANIZATION_SLUG", self.settings)
            or self.settings.qctrl_organization_slug
        )
        if not organization:
            raise RuntimeError("fire_opal_organization_missing")
        fire_opal.configure_organization(organization)
        fire_opal.authenticate_qctrl_account(
            api_key=secret_value("QCTRL_API_KEY", self.settings)
        )
        credentials = fire_opal.credentials.make_credentials_for_ibm_cloud(
            token=secret_value("IBM_QUANTUM_TOKEN", self.settings),
            instance=secret_value("IBM_QUANTUM_INSTANCE", self.settings),
        )
        self._fire_opal = fire_opal
        self._credentials = credentials
        return fire_opal, credentials

    def validate_circuits(
        self,
        *,
        qasm_circuits: tuple[str, ...],
        backend_name: str,
    ) -> dict[str, Any]:
        fire_opal, credentials = self._provider_session()
        result = fire_opal.validate(
            circuits=list(qasm_circuits),
            credentials=credentials,
            backend_name=backend_name,
        )
        if not isinstance(result, dict):
            raise RuntimeError("fire_opal_validation_result_invalid")
        return result

    def submit_circuits(
        self,
        *,
        qasm_circuits: tuple[str, ...],
        shots_per_circuit: int,
        backend_name: str,
    ) -> str:
        fire_opal, credentials = self._provider_session()
        job = fire_opal.execute(
            circuits=list(qasm_circuits),
            shot_count=shots_per_circuit,
            credentials=credentials,
            backend_name=backend_name,
        )
        action_id = str(getattr(job, "action_id", "") or "")
        if not action_id:
            raise RuntimeError("fire_opal_submission_action_id_missing")
        return action_id

    def job_status(self, *, action_id: str) -> str:
        fire_opal, _credentials = self._provider_session()
        status = fire_opal.FireOpalJob(action_id=action_id).status()
        if not isinstance(status, dict):
            raise RuntimeError("fire_opal_job_status_invalid")
        return str(status.get("action_status") or "UNKNOWN").upper()

    def job_result(self, *, action_id: str) -> dict[str, Any]:
        fire_opal, _credentials = self._provider_session()
        result = fire_opal.FireOpalJob(action_id=action_id).result()
        if not isinstance(result, dict):
            raise RuntimeError("fire_opal_job_result_invalid")
        return result


def _atomic_json_write(path: Path, payload: dict[str, Any], *, private: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.chmod(0o600 if private else 0o644)
    temporary.replace(path)
    path.chmod(0o600 if private else 0o644)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _initial_public_state(manifest: PreparedFireOpalIbmManifest) -> dict[str, Any]:
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "manifest": manifest.to_public_dict(),
        "manifest_hash": manifest.manifest_hash,
        "lifecycle_status": "prepared",
        "provider_validation_completed": False,
        "provider_validation_passed": False,
        "provider_validation_error_count": 0,
        "provider_validation_warning_count": 0,
        "provider_validation_receipt_hash": None,
        "hardware_execution_authorized": False,
        "hardware_job_submitted": False,
        "hardware_experiment_completed": False,
        "backend_name_hash": None,
        "authorization_id": None,
        "submission_attempt_count": 0,
        "provider_call_count": 0,
        "provider_action_id_hash": None,
        "provider_status": None,
        "poll_count": 0,
        "poll_failure_count": 0,
        "timed_out": False,
        "receipt": None,
        "receipt_hash": None,
        "failure_category": None,
        "failure_class": None,
        "failure_message_hash": None,
        "secret_value_exposed": False,
        "raw_provider_response_persisted": False,
        "hardware_scheduler_enabled": False,
        "trade_candidate_created": False,
        "paper_order_created": False,
        "live_capital_enabled": False,
        "authority": _public_authority(),
        "updated_at": manifest.prepared_at,
    }


class FireOpalIbmExperimentStore:
    """Durable public/private state with a per-manifest process claim."""

    def __init__(self, runtime_dir: str | Path) -> None:
        self.root = Path(runtime_dir) / "qadam_fire_opal_ibm_discovery"

    def public_path(self, manifest_hash: str) -> Path:
        return self.root / f"{manifest_hash[:24]}.public.json"

    def private_path(self, manifest_hash: str) -> Path:
        return self.root / f".{manifest_hash[:24]}.private.json"

    def claim_path(self, manifest_hash: str) -> Path:
        return self.root / f".{manifest_hash[:24]}.claim"

    def write_prepared(self, bundle: PreparedFireOpalIbmBundle) -> tuple[Path, Path]:
        public_payload = bundle.manifest.to_public_dict()
        errors = validate_prepared_manifest(public_payload)
        if errors:
            raise ValueError(f"fire_opal_manifest_invalid:{','.join(errors)}")
        existing_private = self.read_private(bundle.manifest.manifest_hash)
        if existing_private:
            if existing_private.get("manifest_hash") != bundle.manifest.manifest_hash:
                raise ValueError("fire_opal_private_manifest_mismatch")
            existing_qasm = tuple(existing_private.get("qasm_circuits") or ())
            if existing_qasm != bundle.qasm_circuits:
                raise ValueError("fire_opal_private_qasm_mismatch")
            return (
                self.public_path(bundle.manifest.manifest_hash),
                self.private_path(bundle.manifest.manifest_hash),
            )
        public_state = _initial_public_state(bundle.manifest)
        validate_public_state(public_state)
        _atomic_json_write(
            self.private_path(bundle.manifest.manifest_hash),
            bundle.to_private_dict(),
            private=True,
        )
        _atomic_json_write(
            self.public_path(bundle.manifest.manifest_hash),
            public_state,
            private=False,
        )
        return (
            self.public_path(bundle.manifest.manifest_hash),
            self.private_path(bundle.manifest.manifest_hash),
        )

    def read_public(self, manifest_hash: str) -> dict[str, Any]:
        return _read_json(self.public_path(manifest_hash))

    def read_private(self, manifest_hash: str) -> dict[str, Any]:
        return _read_json(self.private_path(manifest_hash))

    def write_public(self, manifest_hash: str, payload: dict[str, Any]) -> Path:
        validate_public_state(payload)
        path = self.public_path(manifest_hash)
        _atomic_json_write(path, payload, private=False)
        return path

    def write_private(self, manifest_hash: str, payload: dict[str, Any]) -> Path:
        validate_private_state(payload, manifest_hash=manifest_hash)
        path = self.private_path(manifest_hash)
        _atomic_json_write(path, payload, private=True)
        return path

    @contextmanager
    def claim(self, manifest_hash: str) -> Iterator[None]:
        path = self.claim_path(manifest_hash)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise RuntimeError("fire_opal_manifest_already_claimed") from exc
        try:
            os.write(descriptor, manifest_hash.encode("utf-8"))
            os.close(descriptor)
            yield
        finally:
            try:
                os.close(descriptor)
            except OSError:
                pass
            try:
                path.unlink()
            except FileNotFoundError:
                pass


def validate_private_state(payload: dict[str, Any], *, manifest_hash: str) -> None:
    if payload.get("schema_version") != PRIVATE_STATE_SCHEMA_VERSION:
        raise ValueError("fire_opal_private_state_schema_invalid")
    if payload.get("manifest_hash") != manifest_hash:
        raise ValueError("fire_opal_private_state_manifest_mismatch")
    qasm = payload.get("qasm_circuits")
    if not isinstance(qasm, list) or not qasm:
        raise ValueError("fire_opal_private_state_qasm_missing")
    action_id = payload.get("action_id")
    if action_id is not None and (not isinstance(action_id, str) or not action_id):
        raise ValueError("fire_opal_private_state_action_invalid")
    backend_name = payload.get("backend_name")
    if backend_name is not None and (
        not isinstance(backend_name, str) or not backend_name
    ):
        raise ValueError("fire_opal_private_state_backend_invalid")
    if (action_id is None) != (backend_name is None):
        raise ValueError("fire_opal_private_state_provider_identity_incomplete")
    for key in (
        "submission_attempt_count",
        "poll_count",
        "poll_failure_count",
    ):
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"fire_opal_private_state_counter_invalid:{key}")
    if payload.get("lifecycle_status") not in {
        "prepared",
        "provider_validation_in_progress",
        "provider_validation_failed",
        "provider_validation_rejected",
        "submission_in_progress",
        "submission_ambiguous_requires_reconciliation",
        "submitted",
        "provider_pending",
        "provider_success_result_pending",
        "timed_out_provider_job_may_continue",
        "poll_failed_retryable",
        "poll_failure_budget_exhausted",
        "provider_terminal_failure",
        "provider_status_unknown",
        "result_retrieval_failed",
        "completed",
    }:
        raise ValueError("fire_opal_private_state_lifecycle_invalid")


def validate_public_state(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != STATE_SCHEMA_VERSION:
        raise ValueError("fire_opal_public_state_schema_invalid")
    manifest = payload.get("manifest")
    if not isinstance(manifest, dict):
        raise ValueError("fire_opal_public_state_manifest_missing")
    manifest_errors = validate_prepared_manifest(manifest)
    if manifest_errors:
        raise ValueError(
            f"fire_opal_public_state_manifest_invalid:{','.join(manifest_errors)}"
        )
    if payload.get("manifest_hash") != manifest.get("manifest_hash"):
        raise ValueError("fire_opal_public_state_manifest_hash_mismatch")
    if payload.get("lifecycle_status") not in {
        "prepared",
        "provider_validation_in_progress",
        "provider_validation_failed",
        "provider_validation_rejected",
        "submission_in_progress",
        "submission_ambiguous_requires_reconciliation",
        "submitted",
        "provider_pending",
        "provider_success_result_pending",
        "timed_out_provider_job_may_continue",
        "poll_failed_retryable",
        "poll_failure_budget_exhausted",
        "provider_terminal_failure",
        "provider_status_unknown",
        "result_retrieval_failed",
        "completed",
    }:
        raise ValueError("fire_opal_public_state_lifecycle_invalid")
    if payload.get("secret_value_exposed") is not False:
        raise ValueError("fire_opal_public_state_secret_exposed")
    if payload.get("raw_provider_response_persisted") is not False:
        raise ValueError("fire_opal_public_state_raw_response_persisted")
    if payload.get("hardware_scheduler_enabled") is not False:
        raise ValueError("fire_opal_public_state_scheduler_enabled")
    for key in ("trade_candidate_created", "paper_order_created", "live_capital_enabled"):
        if payload.get(key) is not False:
            raise ValueError(f"fire_opal_public_state_downstream_state:{key}")
    for key in (
        "submission_attempt_count",
        "provider_call_count",
        "poll_count",
        "poll_failure_count",
    ):
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"fire_opal_public_state_counter_invalid:{key}")
    if payload.get("hardware_job_submitted") is True:
        if not payload.get("provider_action_id_hash") or not payload.get(
            "backend_name_hash"
        ):
            raise ValueError("fire_opal_public_state_submission_lineage_missing")
    receipt = payload.get("receipt")
    if receipt is not None:
        if not isinstance(receipt, dict):
            raise ValueError("fire_opal_public_state_receipt_invalid")
        validate_hardware_receipt(receipt)
        if payload.get("receipt_hash") != receipt.get("receipt_hash"):
            raise ValueError("fire_opal_public_state_receipt_hash_mismatch")
        if payload.get("hardware_experiment_completed") is not True:
            raise ValueError("fire_opal_public_state_completion_fact_missing")
    elif payload.get("hardware_experiment_completed") is not False:
        raise ValueError("fire_opal_public_state_false_completion_claim")
    authority = payload.get("authority", {})
    for key in HARDWARE_ZERO_AUTHORITY_FIELDS:
        if authority.get(key) is not False:
            raise ValueError(f"fire_opal_public_state_authority_escalated:{key}")
    if _contains_forbidden_public_key(payload):
        raise ValueError("fire_opal_public_state_forbidden_key")


def validate_submission_readiness(
    readiness: dict[str, Any],
    *,
    backend_name: str,
) -> None:
    required_true = (
        "public_safe",
        "fire_opal_product_access_verified",
        "authenticated",
        "product_entitled",
        "backend_discovered",
        "circuit_validation_available",
    )
    for key in required_true:
        if readiness.get(key) is not True:
            raise PermissionError(f"fire_opal_readiness_blocked:{key}")
    if readiness.get("status") not in {"device_probe_recorded", "ready"}:
        raise PermissionError("fire_opal_readiness_status_not_submission_ready")
    supported = readiness.get("supported_device_name_hashes")
    if not isinstance(supported, list) or _backend_hash(backend_name) not in supported:
        raise PermissionError("fire_opal_backend_not_in_discovered_devices")
    for key in (
        "hardware_execution_authorized",
        "hardware_submission_allowed",
        "hardware_job_submitted",
        "hardware_scheduler_enabled",
        "execution_allowed",
        "paper_order_allowed",
    ):
        if readiness.get(key) is not False:
            raise PermissionError(f"fire_opal_readiness_authority_must_remain_false:{key}")
    if readiness.get("secret_value_exposed") is not False:
        raise ValueError("fire_opal_readiness_secret_exposed")
    if readiness.get("raw_provider_response_persisted") is not False:
        raise ValueError("fire_opal_readiness_raw_response_persisted")
    if _contains_forbidden_public_key(readiness):
        raise ValueError("fire_opal_readiness_forbidden_public_key")


def _sanitized_failure(exc: Exception) -> dict[str, str]:
    message = str(exc)
    return {
        "failure_category": "provider_operation_failed",
        "failure_class": type(exc).__name__,
        "failure_message_hash": sha256(message.encode("utf-8")).hexdigest(),
    }


def _sanitize_provider_validation(payload: dict[str, Any]) -> dict[str, Any]:
    results = payload.get("results")
    warnings = payload.get("warnings")
    errors = results if isinstance(results, list) else []
    warning_items = warnings if isinstance(warnings, list) else []
    return {
        "passed": len(errors) == 0,
        "error_count": len(errors),
        "warning_count": len(warning_items),
        "error_hashes": [stable_hash(str(item)) for item in errors],
        "warning_hashes": [stable_hash(str(item)) for item in warning_items],
    }


def _reconcile_public_submission_state(
    public: dict[str, Any],
    private: dict[str, Any],
) -> bool:
    """Repair a public mirror after private action persistence won a crash race."""

    action_id = private.get("action_id")
    backend_name = private.get("backend_name")
    if not isinstance(action_id, str) or not isinstance(backend_name, str):
        return False
    expected_action_hash = _action_hash(action_id)
    expected_backend_hash = _backend_hash(backend_name)
    changed = False
    repairs = {
        "lifecycle_status": "submitted",
        "hardware_job_submitted": True,
        "provider_action_id_hash": expected_action_hash,
        "backend_name_hash": expected_backend_hash,
        "provider_status": public.get("provider_status") or "SUBMITTED",
    }
    for key, value in repairs.items():
        if public.get(key) != value:
            public[key] = value
            changed = True
    return changed


def submit_authorized_fire_opal_ibm_smoke(
    bundle: PreparedFireOpalIbmBundle,
    *,
    backend_name: str,
    authorization: FireOpalIbmExecutionAuthorization,
    approval_nonce: str,
    readiness: dict[str, Any],
    store: FireOpalIbmExperimentStore,
    gateway: FireOpalIbmGateway,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate and submit once; a crash-ambiguous attempt never auto-retries."""

    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    manifest = bundle.manifest
    validate_execution_authorization(
        authorization,
        manifest=manifest,
        backend_name=backend_name,
        approval_nonce=approval_nonce,
        now=current,
    )
    validate_submission_readiness(readiness, backend_name=backend_name)
    store.write_prepared(bundle)
    with store.claim(manifest.manifest_hash):
        private = store.read_private(manifest.manifest_hash)
        public = store.read_public(manifest.manifest_hash)
        validate_private_state(private, manifest_hash=manifest.manifest_hash)
        validate_public_state(public)
        if private.get("action_id"):
            if _reconcile_public_submission_state(public, private):
                public["updated_at"] = current.isoformat()
                store.write_public(manifest.manifest_hash, public)
            return public
        if private.get("lifecycle_status") == "submission_in_progress":
            raise RuntimeError("fire_opal_ambiguous_submission_requires_reconciliation")
        attempts = int(private.get("submission_attempt_count") or 0)
        maximum_attempts = int(manifest.policy_contract["maximum_submission_attempts"])
        if attempts >= maximum_attempts:
            raise RuntimeError("fire_opal_submission_attempt_budget_exhausted")

        private.update(
            {
                "lifecycle_status": "provider_validation_in_progress",
                "backend_name": None,
                "action_id": None,
                "submission_attempt_count": attempts,
                "updated_at": current.isoformat(),
            }
        )
        public.update(
            {
                "lifecycle_status": "provider_validation_in_progress",
                "backend_name_hash": _backend_hash(backend_name),
                "authorization_id": authorization.authorization_id,
                "hardware_execution_authorized": True,
                "provider_call_count": int(public.get("provider_call_count") or 0) + 1,
                "updated_at": current.isoformat(),
            }
        )
        store.write_private(manifest.manifest_hash, private)
        store.write_public(manifest.manifest_hash, public)

        try:
            raw_validation = gateway.validate_circuits(
                qasm_circuits=bundle.qasm_circuits,
                backend_name=backend_name,
            )
            validation = _sanitize_provider_validation(raw_validation)
        except Exception as exc:  # noqa: BLE001 - only hashes may persist publicly.
            public.update(
                {
                    "lifecycle_status": "provider_validation_failed",
                    "provider_validation_completed": False,
                    **_sanitized_failure(exc),
                    "updated_at": current.isoformat(),
                }
            )
            private.update(
                {
                    "lifecycle_status": "provider_validation_failed",
                    "updated_at": current.isoformat(),
                }
            )
            store.write_private(manifest.manifest_hash, private)
            store.write_public(manifest.manifest_hash, public)
            return public

        validation_hash = stable_hash(validation)
        public.update(
            {
                "provider_validation_completed": True,
                "provider_validation_passed": validation["passed"],
                "provider_validation_error_count": validation["error_count"],
                "provider_validation_warning_count": validation["warning_count"],
                "provider_validation_receipt_hash": validation_hash,
                "updated_at": current.isoformat(),
            }
        )
        if not validation["passed"]:
            public["lifecycle_status"] = "provider_validation_rejected"
            private["lifecycle_status"] = "provider_validation_rejected"
            private["updated_at"] = current.isoformat()
            store.write_private(manifest.manifest_hash, private)
            store.write_public(manifest.manifest_hash, public)
            return public

        attempt_id = stable_hash(
            {
                "manifest_hash": manifest.manifest_hash,
                "authorization_id": authorization.authorization_id,
                "attempt": attempts + 1,
            }
        )
        private.update(
            {
                "lifecycle_status": "submission_in_progress",
                "submission_attempt_count": attempts + 1,
                "submission_attempt_hash": attempt_id,
                "updated_at": current.isoformat(),
            }
        )
        public.update(
            {
                "lifecycle_status": "submission_in_progress",
                "submission_attempt_count": attempts + 1,
                "provider_call_count": int(public.get("provider_call_count") or 0) + 1,
                "updated_at": current.isoformat(),
            }
        )
        store.write_private(manifest.manifest_hash, private)
        store.write_public(manifest.manifest_hash, public)

        try:
            action_id = gateway.submit_circuits(
                qasm_circuits=bundle.qasm_circuits,
                shots_per_circuit=manifest.shots_per_circuit,
                backend_name=backend_name,
            )
        except Exception as exc:  # noqa: BLE001 - ambiguity must remain explicit.
            public.update(
                {
                    "lifecycle_status": "submission_ambiguous_requires_reconciliation",
                    **_sanitized_failure(exc),
                    "updated_at": current.isoformat(),
                }
            )
            private.update(
                {
                    "lifecycle_status": "submission_ambiguous_requires_reconciliation",
                    "updated_at": current.isoformat(),
                }
            )
            store.write_private(manifest.manifest_hash, private)
            store.write_public(manifest.manifest_hash, public)
            return public

        private.update(
            {
                "lifecycle_status": "submitted",
                "action_id": action_id,
                "backend_name": backend_name,
                "submitted_at": current.isoformat(),
                "updated_at": current.isoformat(),
            }
        )
        public.update(
            {
                "lifecycle_status": "submitted",
                "hardware_job_submitted": True,
                "provider_action_id_hash": _action_hash(action_id),
                "provider_status": "SUBMITTED",
                "updated_at": current.isoformat(),
            }
        )
        store.write_private(manifest.manifest_hash, private)
        store.write_public(manifest.manifest_hash, public)
        return public


def _distribution_zero_probability(
    distribution: dict[str, Any],
    *,
    qubit_count: int,
) -> float:
    if not isinstance(distribution, dict) or not distribution:
        raise ValueError("fire_opal_result_distribution_invalid")
    normalized: dict[str, float] = {}
    for raw_key, raw_value in distribution.items():
        key = str(raw_key).replace(" ", "")
        try:
            value = float(raw_value)
        except (TypeError, ValueError) as exc:
            raise ValueError("fire_opal_result_distribution_value_invalid") from exc
        if value < 0 or not np.isfinite(value):
            raise ValueError("fire_opal_result_distribution_value_invalid")
        normalized[key] = normalized.get(key, 0.0) + value
    total = sum(normalized.values())
    if total <= 0:
        raise ValueError("fire_opal_result_distribution_empty")
    zero_key = "0" * qubit_count
    return max(0.0, min(1.0, normalized.get(zero_key, 0.0) / total))


def _provider_job_id_hashes(payload: dict[str, Any]) -> list[str]:
    values = payload.get("provider_job_ids")
    if not isinstance(values, list):
        single = payload.get("provider_job_id")
        values = [single] if single else []
    return [sha256(str(value).encode("utf-8")).hexdigest() for value in values[:20]]


def _receipt_material(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key not in {"receipt_id", "receipt_hash", "schema_version"}
    }


def build_sanitized_hardware_receipt(
    *,
    bundle: PreparedFireOpalIbmBundle,
    batch: DiscoveryInputBatch,
    matched_classical_result: ClassicalDiscoveryResult | dict[str, Any],
    local_quantum_result: QuantumDiscoveryBackendResult | dict[str, Any],
    action_id: str,
    backend_name: str,
    raw_provider_result: dict[str, Any],
    completed_at: str,
) -> dict[str, Any]:
    """Convert Fire Opal counts into the same Nystrom kernel analysis as Wave C."""

    manifest = bundle.manifest
    if batch.shared_manifest_hash != manifest.shared_manifest_hash:
        raise ValueError("fire_opal_receipt_batch_manifest_mismatch")
    classical = _validated_result_payload(matched_classical_result)
    local = _validated_result_payload(local_quantum_result)
    if classical.get("result_id") != manifest.classical_result_id:
        raise ValueError("fire_opal_receipt_classical_result_mismatch")
    if local.get("result_id") != manifest.local_quantum_result_id:
        raise ValueError("fire_opal_receipt_local_result_mismatch")
    _parse_timestamp(completed_at, field_name="fire_opal_receipt_completed_at")
    raw_results = raw_provider_result.get("results")
    if not isinstance(raw_results, list) or len(raw_results) != manifest.circuit_count:
        raise ValueError("fire_opal_result_count_mismatch")
    pair_fidelities = {
        pair: _distribution_zero_probability(
            distribution,
            qubit_count=manifest.qubit_count,
        )
        for pair, distribution in zip(manifest.circuit_pairs, raw_results, strict=True)
    }
    policy = manifest.policy_contract
    kernel = reconstruct_nystrom_kernel(
        row_count=manifest.row_count,
        landmark_indices=manifest.landmark_indices,
        pair_fidelities=pair_fidelities,
        ridge=float(policy["nystrom_ridge"]),
    )
    interaction, spectral = analyze_fidelity_kernel(
        matrix=np.asarray(batch.matrix, dtype=float),
        feature_names=batch.feature_names,
        kernel=kernel,
        classical_gamma=float(policy["classical_rbf_gamma"]),
    )
    kernel_hash = stable_hash(np.round(kernel, 12).tolist())
    method_results = [
        {
            "method": "fire_opal_ibm_fidelity_kernel",
            "structural_score": round(float(np.mean(kernel)), 12),
            "kernel_hash": kernel_hash,
            "kernel_shape": list(kernel.shape),
            "landmark_count": len(manifest.landmark_indices),
            "matched_local_method": "fidelity_kernel",
            "matched_classical_method": "rbf_kernel_similarity",
        },
        spectral,
        interaction,
    ]
    candidates: list[dict[str, Any]] = []
    if interaction["structural_score"] >= float(
        policy["interaction_candidate_threshold"]
    ):
        pair = interaction["feature_pair"]
        candidates.append(
            build_research_candidate(
                batch=batch,
                discovery_origin="quantum_assisted_discovery",
                method="fire_opal_ibm_fidelity_interaction_scan",
                feature_pair=(str(pair[0]), str(pair[1])),
                structural_score=float(interaction["structural_score"]),
                question=(
                    f"Does IBM hardware preserve the nonlinear relationship between "
                    f"{pair[0]} and {pair[1]} for {batch.target_instrument}?"
                ),
            )
        )

    payload = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "manifest_hash": manifest.manifest_hash,
        "shared_manifest_hash": manifest.shared_manifest_hash,
        "provider": PROVIDER_NAME,
        "execution_mode": "qctrl_fire_opal_ibm_hardware",
        "experiment_kind": manifest.experiment_kind,
        "hardware_execution_authorized": True,
        "hardware_experiment_completed": True,
        "provider_call_attempted": True,
        "provider_action_id_hash": _action_hash(action_id),
        "provider_job_id_hashes": _provider_job_id_hashes(raw_provider_result),
        "backend_name_hash": _backend_hash(backend_name),
        "classical_result_id": manifest.classical_result_id,
        "classical_policy_hash": manifest.classical_policy_hash,
        "local_quantum_result_id": manifest.local_quantum_result_id,
        "local_quantum_policy_hash": manifest.local_quantum_policy_hash,
        "local_quantum_kernel_hash": manifest.local_quantum_kernel_hash,
        "hardware_kernel_hash": kernel_hash,
        "kernel_shape": list(kernel.shape),
        "pair_fidelity_hash": stable_hash(
            [
                {"pair": list(pair), "fidelity": round(value, 12)}
                for pair, value in sorted(pair_fidelities.items())
            ]
        ),
        "circuit_hashes": list(manifest.circuit_hashes),
        "qubit_count": manifest.qubit_count,
        "circuit_depth_max": manifest.circuit_depth_max,
        "circuit_count": manifest.circuit_count,
        "shots_per_circuit": manifest.shots_per_circuit,
        "total_shots": manifest.total_shots,
        "method_results": method_results,
        "research_candidates": candidates,
        "discovery_origin": "quantum_assisted_discovery",
        "validation_contribution": "not_tested",
        "contract_fixture_only": manifest.contract_fixture_only,
        "candidate_persistence_allowed": not manifest.contract_fixture_only,
        "validated_edge_created": False,
        "strategy_hypothesis_created": False,
        "trade_candidate_created": False,
        "risk_approval_created": False,
        "execution_approval_created": False,
        "paper_order_created": False,
        "proof_eligible": False,
        "completed_at": completed_at,
        "secret_value_exposed": False,
        "raw_provider_response_persisted": False,
        "authority": _public_authority(),
    }
    receipt_hash = stable_hash(_receipt_material(payload))
    payload["receipt_hash"] = receipt_hash
    payload["receipt_id"] = f"fire-opal-ibm-receipt:{receipt_hash[:24]}"
    validate_hardware_receipt(payload)
    return payload


def validate_hardware_receipt(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != RECEIPT_SCHEMA_VERSION:
        raise ValueError("fire_opal_receipt_schema_invalid")
    if payload.get("provider") != PROVIDER_NAME:
        raise ValueError("fire_opal_receipt_provider_invalid")
    expected_hash = stable_hash(_receipt_material(payload))
    if payload.get("receipt_hash") != expected_hash:
        raise ValueError("fire_opal_receipt_hash_mismatch")
    if payload.get("receipt_id") != f"fire-opal-ibm-receipt:{expected_hash[:24]}":
        raise ValueError("fire_opal_receipt_id_mismatch")
    for key in (
        "hardware_execution_authorized",
        "hardware_experiment_completed",
        "provider_call_attempted",
    ):
        if payload.get(key) is not True:
            raise ValueError(f"fire_opal_receipt_hardware_fact_missing:{key}")
    for key in (
        "manifest_hash",
        "shared_manifest_hash",
        "provider_action_id_hash",
        "backend_name_hash",
        "hardware_kernel_hash",
    ):
        value = payload.get(key)
        if not isinstance(value, str) or len(value) != 64:
            raise ValueError(f"fire_opal_receipt_hash_invalid:{key}")
    provider_job_hashes = payload.get("provider_job_id_hashes")
    if not isinstance(provider_job_hashes, list) or any(
        not isinstance(value, str) or len(value) != 64
        for value in provider_job_hashes
    ):
        raise ValueError("fire_opal_receipt_provider_job_hashes_invalid")
    if payload.get("contract_fixture_only") is True and payload.get(
        "candidate_persistence_allowed"
    ) is not False:
        raise ValueError("fire_opal_fixture_receipt_persistence_allowed")
    candidates = payload.get("research_candidates")
    if not isinstance(candidates, list):
        raise ValueError("fire_opal_receipt_candidates_invalid")
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise ValueError("fire_opal_receipt_candidate_not_object")
        errors = validate_research_candidate(candidate)
        if errors:
            raise ValueError(
                f"fire_opal_receipt_candidate_invalid:{','.join(errors)}"
            )
        if candidate.get("shared_manifest_hash") != payload.get(
            "shared_manifest_hash"
        ):
            raise ValueError("fire_opal_receipt_candidate_manifest_mismatch")
    if not isinstance(payload.get("method_results"), list):
        raise ValueError("fire_opal_receipt_methods_invalid")
    kernel_shape = payload.get("kernel_shape")
    if (
        not isinstance(kernel_shape, list)
        or len(kernel_shape) != 2
        or any(isinstance(value, bool) or not isinstance(value, int) for value in kernel_shape)
        or kernel_shape[0] <= 0
        or kernel_shape[0] != kernel_shape[1]
    ):
        raise ValueError("fire_opal_receipt_kernel_shape_invalid")
    for key in (
        "validated_edge_created",
        "strategy_hypothesis_created",
        "trade_candidate_created",
        "risk_approval_created",
        "execution_approval_created",
        "paper_order_created",
        "proof_eligible",
        "secret_value_exposed",
        "raw_provider_response_persisted",
    ):
        if payload.get(key) is not False:
            raise ValueError(f"fire_opal_receipt_forbidden_state:{key}")
    authority = payload.get("authority", {})
    for key in HARDWARE_ZERO_AUTHORITY_FIELDS:
        if authority.get(key) is not False:
            raise ValueError(f"fire_opal_receipt_authority_escalated:{key}")
    if _contains_forbidden_public_key(payload):
        raise ValueError("fire_opal_receipt_forbidden_public_key")


def poll_fire_opal_ibm_smoke(
    bundle: PreparedFireOpalIbmBundle,
    *,
    batch: DiscoveryInputBatch,
    matched_classical_result: ClassicalDiscoveryResult | dict[str, Any],
    local_quantum_result: QuantumDiscoveryBackendResult | dict[str, Any],
    store: FireOpalIbmExperimentStore,
    gateway: FireOpalIbmGateway,
    now: datetime | None = None,
    explicit_recovery: bool = False,
) -> dict[str, Any]:
    """Poll once. Polling never submits and may recover a completed action."""

    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    manifest = bundle.manifest
    with store.claim(manifest.manifest_hash):
        private = store.read_private(manifest.manifest_hash)
        public = store.read_public(manifest.manifest_hash)
        validate_private_state(private, manifest_hash=manifest.manifest_hash)
        validate_public_state(public)
        if public.get("receipt"):
            validate_hardware_receipt(public["receipt"])
            return public
        action_id = private.get("action_id")
        backend_name = private.get("backend_name")
        if not isinstance(action_id, str) or not isinstance(backend_name, str):
            raise RuntimeError("fire_opal_poll_requires_submitted_action")
        if _reconcile_public_submission_state(public, private):
            public["updated_at"] = current.isoformat()
            store.write_public(manifest.manifest_hash, public)
        if public.get("provider_action_id_hash") != _action_hash(action_id):
            raise ValueError("fire_opal_poll_action_hash_mismatch")
        if public.get("backend_name_hash") != _backend_hash(backend_name):
            raise ValueError("fire_opal_poll_backend_hash_mismatch")
        poll_count = int(private.get("poll_count") or 0)
        maximum_polls = int(manifest.policy_contract["maximum_poll_count"])
        if poll_count >= maximum_polls and explicit_recovery is not True:
            raise RuntimeError("fire_opal_poll_budget_exhausted")
        poll_failures = int(private.get("poll_failure_count") or 0)
        maximum_failures = int(manifest.policy_contract["maximum_poll_failures"])
        if poll_failures >= maximum_failures and explicit_recovery is not True:
            raise RuntimeError("fire_opal_poll_failure_budget_exhausted")
        submitted_at = _parse_timestamp(
            str(private.get("submitted_at") or ""),
            field_name="fire_opal_submitted_at",
        )
        elapsed_seconds = max(0.0, (current - submitted_at).total_seconds())
        timed_out = elapsed_seconds > float(
            manifest.policy_contract["maximum_wall_clock_seconds"]
        )
        private["poll_count"] = poll_count + 1
        private["updated_at"] = current.isoformat()
        public["poll_count"] = poll_count + 1
        public["provider_call_count"] = int(public.get("provider_call_count") or 0) + 1
        public["timed_out"] = timed_out
        public["updated_at"] = current.isoformat()

        try:
            provider_status = gateway.job_status(action_id=action_id).upper()
        except Exception as exc:  # noqa: BLE001 - poll failures remain sanitized.
            private["poll_failure_count"] = poll_failures + 1
            private["lifecycle_status"] = "poll_failed_retryable"
            public.update(
                {
                    "poll_failure_count": poll_failures + 1,
                    "lifecycle_status": "poll_failed_retryable",
                    **_sanitized_failure(exc),
                }
            )
            if poll_failures + 1 >= maximum_failures:
                private["lifecycle_status"] = "poll_failure_budget_exhausted"
                public["lifecycle_status"] = "poll_failure_budget_exhausted"
            store.write_private(manifest.manifest_hash, private)
            store.write_public(manifest.manifest_hash, public)
            return public

        public["provider_status"] = provider_status
        if provider_status in PENDING_PROVIDER_STATUSES:
            lifecycle = (
                "timed_out_provider_job_may_continue" if timed_out else "provider_pending"
            )
            private["lifecycle_status"] = lifecycle
            public["lifecycle_status"] = lifecycle
            store.write_private(manifest.manifest_hash, private)
            store.write_public(manifest.manifest_hash, public)
            return public
        if provider_status in {"FAILURE", "REVOKED"}:
            private["lifecycle_status"] = "provider_terminal_failure"
            public["lifecycle_status"] = "provider_terminal_failure"
            public["failure_category"] = f"provider_status_{provider_status.lower()}"
            store.write_private(manifest.manifest_hash, private)
            store.write_public(manifest.manifest_hash, public)
            return public
        if provider_status != "SUCCESS":
            private["lifecycle_status"] = "provider_status_unknown"
            public["lifecycle_status"] = "provider_status_unknown"
            public["failure_category"] = "provider_status_unknown"
            store.write_private(manifest.manifest_hash, private)
            store.write_public(manifest.manifest_hash, public)
            return public

        public["provider_call_count"] = int(public.get("provider_call_count") or 0) + 1
        try:
            raw_result = gateway.job_result(action_id=action_id)
            receipt = build_sanitized_hardware_receipt(
                bundle=bundle,
                batch=batch,
                matched_classical_result=matched_classical_result,
                local_quantum_result=local_quantum_result,
                action_id=action_id,
                backend_name=backend_name,
                raw_provider_result=raw_result,
                completed_at=current.isoformat(),
            )
        except Exception as exc:  # noqa: BLE001 - only failure hashes persist.
            private["poll_failure_count"] = poll_failures + 1
            private["lifecycle_status"] = "result_retrieval_failed"
            public.update(
                {
                    "poll_failure_count": poll_failures + 1,
                    "lifecycle_status": "result_retrieval_failed",
                    **_sanitized_failure(exc),
                }
            )
            store.write_private(manifest.manifest_hash, private)
            store.write_public(manifest.manifest_hash, public)
            return public

        private["lifecycle_status"] = "completed"
        private["updated_at"] = current.isoformat()
        public.update(
            {
                "lifecycle_status": "completed",
                "hardware_experiment_completed": True,
                "receipt": receipt,
                "receipt_hash": receipt["receipt_hash"],
                "failure_category": None,
                "failure_class": None,
                "failure_message_hash": None,
                "updated_at": current.isoformat(),
            }
        )
        store.write_private(manifest.manifest_hash, private)
        store.write_public(manifest.manifest_hash, public)
        return public
