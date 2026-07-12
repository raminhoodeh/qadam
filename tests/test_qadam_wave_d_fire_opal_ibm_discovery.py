from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import json
import stat
from typing import Any

import pytest

from orchestrator import qadam_fire_opal_ibm_discovery as fire_opal_discovery
from orchestrator.qadam_classical_discovery import run_classical_discovery
from orchestrator.qadam_discovery_contract_fixture import (
    build_wave_c_contract_fixture_batch,
)
from orchestrator.qadam_fire_opal_ibm_discovery import (
    FireOpalIbmBudgetPolicy,
    FireOpalIbmExperimentStore,
    FireOpalSdkIbmGateway,
    build_execution_authorization,
    poll_fire_opal_ibm_smoke,
    prepare_fire_opal_ibm_smoke_manifest,
    submit_authorized_fire_opal_ibm_smoke,
    validate_execution_authorization,
    validate_hardware_receipt,
    validate_prepared_manifest,
    validate_public_state,
)
from orchestrator.qadam_local_quantum_discovery import (
    QiskitLocalQuantumDiscoveryBackend,
)
from orchestrator.qadam_quantum_discovery_evidence import stable_hash

PREPARED_AT = "2026-07-12T00:00:00+00:00"
ISSUED_AT = "2026-07-12T01:00:00+00:00"
EXPIRES_AT = "2026-07-12T03:00:00+00:00"
SUBMIT_NOW = datetime(2026, 7, 12, 2, 0, tzinfo=timezone.utc)
BACKEND_NAME = "ibm_contract_fixture"
APPROVAL_NONCE = "wave-d-unit-test-approval-nonce"


class FakeGateway:
    def __init__(
        self,
        *,
        validation: dict[str, Any] | None = None,
        statuses: list[str | Exception] | None = None,
        result: dict[str, Any] | Exception | None = None,
        submit_error: Exception | None = None,
    ) -> None:
        self.validation = validation or {"results": [], "warnings": []}
        self.statuses = list(statuses or ["STARTED"])
        self.result_payload = result or {"results": []}
        self.submit_error = submit_error
        self.validate_calls = 0
        self.submit_calls = 0
        self.status_calls = 0
        self.result_calls = 0

    def validate_circuits(self, **_kwargs: Any) -> dict[str, Any]:
        self.validate_calls += 1
        return self.validation

    def submit_circuits(self, **_kwargs: Any) -> str:
        self.submit_calls += 1
        if self.submit_error is not None:
            raise self.submit_error
        return "123456"

    def job_status(self, **_kwargs: Any) -> str:
        self.status_calls += 1
        value = self.statuses.pop(0) if self.statuses else "STARTED"
        if isinstance(value, Exception):
            raise value
        return value

    def job_result(self, **_kwargs: Any) -> dict[str, Any]:
        self.result_calls += 1
        if isinstance(self.result_payload, Exception):
            raise self.result_payload
        return self.result_payload


def _wave_d_fixture(tmp_path, *, policy: FireOpalIbmBudgetPolicy | None = None):
    batch = build_wave_c_contract_fixture_batch()
    classical = run_classical_discovery(batch)
    local = QiskitLocalQuantumDiscoveryBackend().run(
        batch,
        mode="ideal",
        matched_classical_result=classical,
    )
    bundle = prepare_fire_opal_ibm_smoke_manifest(
        batch,
        matched_classical_result=classical,
        local_quantum_result=local,
        policy=policy,
        prepared_at=PREPARED_AT,
    )
    store = FireOpalIbmExperimentStore(tmp_path)
    return batch, classical, local, bundle, store


def _authorization(bundle):
    return build_execution_authorization(
        bundle.manifest,
        backend_name=BACKEND_NAME,
        approval_nonce=APPROVAL_NONCE,
        estimated_provider_cost_usd=1.25,
        maximum_provider_cost_usd=2.0,
        issued_at=ISSUED_AT,
        expires_at=EXPIRES_AT,
        explicit_operator_approval=True,
    )


def _readiness(*, ready: bool = True) -> dict[str, Any]:
    return {
        "status": "device_probe_recorded",
        "public_safe": True,
        "fire_opal_product_access_verified": True,
        "authenticated": ready,
        "product_entitled": True,
        "backend_discovered": True,
        "circuit_validation_available": True,
        "supported_device_name_hashes": [
            sha256(BACKEND_NAME.encode("utf-8")).hexdigest()
        ],
        "hardware_execution_authorized": False,
        "hardware_submission_allowed": False,
        "hardware_job_submitted": False,
        "hardware_scheduler_enabled": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "secret_value_exposed": False,
        "raw_provider_response_persisted": False,
    }


def _ideal_provider_result(bundle) -> dict[str, Any]:
    from qiskit import qasm2
    from qiskit.quantum_info import Statevector

    results: list[dict[str, int]] = []
    shots = bundle.manifest.shots_per_circuit
    zero_key = "0" * bundle.manifest.qubit_count
    other_key = "1" * bundle.manifest.qubit_count
    for qasm in bundle.qasm_circuits:
        circuit = qasm2.loads(
            qasm,
            custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS,
        )
        circuit.remove_final_measurements(inplace=True)
        zero_probability = float(
            Statevector.from_instruction(circuit).probabilities_dict().get(zero_key, 0.0)
        )
        zero_count = min(shots, max(0, round(zero_probability * shots)))
        distribution = {zero_key: zero_count}
        if zero_count < shots:
            distribution[other_key] = shots - zero_count
        results.append(distribution)
    return {
        "results": results,
        "provider_job_ids": ["raw-provider-job-id-must-not-persist"],
        "execution_metadata": {"backend_name": BACKEND_NAME},
        "credentials": {"token": "must-not-persist"},
    }


def test_prepared_manifest_is_deterministic_qasm_valid_and_authority_free(tmp_path):
    _batch, _classical, _local, bundle, store = _wave_d_fixture(tmp_path)
    second = prepare_fire_opal_ibm_smoke_manifest(
        _batch,
        matched_classical_result=_classical,
        local_quantum_result=_local,
        prepared_at="2026-07-12T00:01:00+00:00",
    )

    assert bundle.manifest.manifest_hash == second.manifest.manifest_hash
    assert bundle.manifest.circuit_count == 100
    assert bundle.manifest.qubit_count == 6
    assert bundle.manifest.circuit_depth_max == 19
    assert bundle.manifest.total_shots == 25_600
    assert len(set(bundle.manifest.circuit_pairs)) == 100
    assert validate_prepared_manifest(bundle.manifest.to_public_dict()) == []
    assert bundle.manifest.to_public_dict()["hardware_job_submitted"] is False
    assert "qasm_circuits" not in json.dumps(bundle.manifest.to_public_dict())

    public_path, private_path = store.write_prepared(bundle)
    validate_public_state(store.read_public(bundle.manifest.manifest_hash))
    assert stat.S_IMODE(private_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(public_path.stat().st_mode) == 0o644
    assert "qasm_circuits" not in public_path.read_text(encoding="utf-8")


def test_preparation_rejects_lineage_and_every_hardware_budget(tmp_path):
    batch, classical, local, _bundle, _store = _wave_d_fixture(tmp_path)
    broken_hashes = ("tampered", *local.circuit_hashes[1:])
    with pytest.raises(ValueError, match="local_circuit_lineage_mismatch"):
        prepare_fire_opal_ibm_smoke_manifest(
            batch,
            matched_classical_result=classical,
            local_quantum_result=replace(local, circuit_hashes=broken_hashes),
            prepared_at=PREPARED_AT,
        )
    with pytest.raises(ValueError, match="circuit_budget_exceeded"):
        prepare_fire_opal_ibm_smoke_manifest(
            batch,
            matched_classical_result=classical,
            local_quantum_result=local,
            policy=FireOpalIbmBudgetPolicy(maximum_circuits=99),
            prepared_at=PREPARED_AT,
        )
    with pytest.raises(ValueError, match="depth_budget_exceeded"):
        prepare_fire_opal_ibm_smoke_manifest(
            batch,
            matched_classical_result=classical,
            local_quantum_result=local,
            policy=FireOpalIbmBudgetPolicy(maximum_circuit_depth=18),
            prepared_at=PREPARED_AT,
        )
    with pytest.raises(ValueError, match="total_shot_budget_exceeded"):
        prepare_fire_opal_ibm_smoke_manifest(
            batch,
            matched_classical_result=classical,
            local_quantum_result=local,
            policy=FireOpalIbmBudgetPolicy(maximum_total_shots=25_599),
            prepared_at=PREPARED_AT,
        )


def test_manifest_validator_rejects_rehashed_budget_tampering(tmp_path):
    _batch, _classical, _local, bundle, _store = _wave_d_fixture(tmp_path)
    payload = bundle.manifest.to_public_dict()
    payload["policy_contract"]["maximum_circuits"] = 99
    payload["policy_hash"] = stable_hash(payload["policy_contract"])
    payload["manifest_hash"] = stable_hash(
        fire_opal_discovery._manifest_material(payload)
    )
    payload["manifest_id"] = f"fire-opal-ibm-smoke:{payload['manifest_hash'][:24]}"

    errors = validate_prepared_manifest(payload)

    assert "manifest_circuit_budget_exceeded" in errors


def test_authorization_is_exact_expiring_budgeted_and_nonce_bound(tmp_path):
    _batch, _classical, _local, bundle, _store = _wave_d_fixture(tmp_path)
    with pytest.raises(PermissionError, match="explicit_operator_approval_required"):
        build_execution_authorization(
            bundle.manifest,
            backend_name=BACKEND_NAME,
            approval_nonce=APPROVAL_NONCE,
            estimated_provider_cost_usd=1.0,
            maximum_provider_cost_usd=2.0,
            issued_at=ISSUED_AT,
            expires_at=EXPIRES_AT,
            explicit_operator_approval=False,
        )
    authorization = _authorization(bundle)
    validate_execution_authorization(
        authorization,
        manifest=bundle.manifest,
        backend_name=BACKEND_NAME,
        approval_nonce=APPROVAL_NONCE,
        now=SUBMIT_NOW,
    )
    with pytest.raises(ValueError, match="authorization_id_mismatch"):
        validate_execution_authorization(
            replace(authorization, authorization_id="tampered-authorization"),
            manifest=bundle.manifest,
            backend_name=BACKEND_NAME,
            approval_nonce=APPROVAL_NONCE,
            now=SUBMIT_NOW,
        )
    with pytest.raises(PermissionError, match="nonce_mismatch"):
        validate_execution_authorization(
            authorization,
            manifest=bundle.manifest,
            backend_name=BACKEND_NAME,
            approval_nonce="wrong-approval-nonce-value",
            now=SUBMIT_NOW,
        )
    with pytest.raises(PermissionError, match="not_current"):
        validate_execution_authorization(
            authorization,
            manifest=bundle.manifest,
            backend_name=BACKEND_NAME,
            approval_nonce=APPROVAL_NONCE,
            now=datetime(2026, 7, 12, 4, 0, tzinfo=timezone.utc),
        )


def test_blocked_readiness_never_calls_provider(tmp_path):
    _batch, _classical, _local, bundle, store = _wave_d_fixture(tmp_path)
    gateway = FakeGateway()
    with pytest.raises(PermissionError, match="readiness_blocked:authenticated"):
        submit_authorized_fire_opal_ibm_smoke(
            bundle,
            backend_name=BACKEND_NAME,
            authorization=_authorization(bundle),
            approval_nonce=APPROVAL_NONCE,
            readiness=_readiness(ready=False),
            store=store,
            gateway=gateway,
            now=SUBMIT_NOW,
        )
    assert gateway.validate_calls == 0
    assert gateway.submit_calls == 0
    assert not store.public_path(bundle.manifest.manifest_hash).exists()


def test_provider_validation_rejection_stops_before_submission(tmp_path):
    _batch, _classical, _local, bundle, store = _wave_d_fixture(tmp_path)
    gateway = FakeGateway(validation={"results": ["unsupported gate"], "warnings": []})
    state = submit_authorized_fire_opal_ibm_smoke(
        bundle,
        backend_name=BACKEND_NAME,
        authorization=_authorization(bundle),
        approval_nonce=APPROVAL_NONCE,
        readiness=_readiness(),
        store=store,
        gateway=gateway,
        now=SUBMIT_NOW,
    )
    assert state["lifecycle_status"] == "provider_validation_rejected"
    assert state["provider_validation_error_count"] == 1
    assert state["hardware_job_submitted"] is False
    assert gateway.validate_calls == 1
    assert gateway.submit_calls == 0


def test_submit_is_idempotent_and_completed_receipt_is_sanitized(tmp_path):
    batch, classical, local, bundle, store = _wave_d_fixture(tmp_path)
    gateway = FakeGateway(
        statuses=["STARTED", "SUCCESS"],
        result=_ideal_provider_result(bundle),
    )
    authorization = _authorization(bundle)
    submitted = submit_authorized_fire_opal_ibm_smoke(
        bundle,
        backend_name=BACKEND_NAME,
        authorization=authorization,
        approval_nonce=APPROVAL_NONCE,
        readiness=_readiness(),
        store=store,
        gateway=gateway,
        now=SUBMIT_NOW,
    )
    assert submitted["lifecycle_status"] == "submitted"
    assert submitted["hardware_job_submitted"] is True
    assert gateway.validate_calls == 1
    assert gateway.submit_calls == 1

    duplicate = submit_authorized_fire_opal_ibm_smoke(
        bundle,
        backend_name=BACKEND_NAME,
        authorization=authorization,
        approval_nonce=APPROVAL_NONCE,
        readiness=_readiness(),
        store=store,
        gateway=gateway,
        now=SUBMIT_NOW,
    )
    assert duplicate["provider_action_id_hash"] == submitted["provider_action_id_hash"]
    assert gateway.validate_calls == 1
    assert gateway.submit_calls == 1

    pending = poll_fire_opal_ibm_smoke(
        bundle,
        batch=batch,
        matched_classical_result=classical,
        local_quantum_result=local,
        store=store,
        gateway=gateway,
        now=datetime(2026, 7, 12, 2, 1, tzinfo=timezone.utc),
    )
    assert pending["lifecycle_status"] == "provider_pending"
    completed = poll_fire_opal_ibm_smoke(
        bundle,
        batch=batch,
        matched_classical_result=classical,
        local_quantum_result=local,
        store=store,
        gateway=gateway,
        now=datetime(2026, 7, 12, 2, 2, tzinfo=timezone.utc),
    )
    receipt = completed["receipt"]
    validate_hardware_receipt(receipt)
    assert completed["lifecycle_status"] == "completed"
    assert completed["hardware_experiment_completed"] is True
    assert receipt["hardware_kernel_hash"]
    assert receipt["research_candidates"][0]["feature_pair"] == [
        "source_density",
        "source_agreement",
    ]
    assert receipt["validated_edge_created"] is False
    assert receipt["paper_order_created"] is False
    public_text = store.public_path(bundle.manifest.manifest_hash).read_text(
        encoding="utf-8"
    )
    assert "123456" not in public_text
    assert BACKEND_NAME not in public_text
    assert "raw-provider-job-id-must-not-persist" not in public_text
    assert "must-not-persist" not in public_text


def test_ambiguous_submission_fails_closed_and_never_retries(tmp_path):
    _batch, _classical, _local, bundle, store = _wave_d_fixture(tmp_path)
    gateway = FakeGateway(submit_error=TimeoutError("provider timeout with raw detail"))
    state = submit_authorized_fire_opal_ibm_smoke(
        bundle,
        backend_name=BACKEND_NAME,
        authorization=_authorization(bundle),
        approval_nonce=APPROVAL_NONCE,
        readiness=_readiness(),
        store=store,
        gateway=gateway,
        now=SUBMIT_NOW,
    )
    assert state["lifecycle_status"] == "submission_ambiguous_requires_reconciliation"
    assert state["failure_class"] == "TimeoutError"
    assert "raw detail" not in json.dumps(state)
    with pytest.raises(RuntimeError, match="attempt_budget_exhausted"):
        submit_authorized_fire_opal_ibm_smoke(
            bundle,
            backend_name=BACKEND_NAME,
            authorization=_authorization(bundle),
            approval_nonce=APPROVAL_NONCE,
            readiness=_readiness(),
            store=store,
            gateway=gateway,
            now=SUBMIT_NOW,
        )
    assert gateway.submit_calls == 1


def test_private_action_repairs_public_mirror_without_resubmission(tmp_path):
    _batch, _classical, _local, bundle, store = _wave_d_fixture(tmp_path)
    gateway = FakeGateway()
    authorization = _authorization(bundle)
    submit_authorized_fire_opal_ibm_smoke(
        bundle,
        backend_name=BACKEND_NAME,
        authorization=authorization,
        approval_nonce=APPROVAL_NONCE,
        readiness=_readiness(),
        store=store,
        gateway=gateway,
        now=SUBMIT_NOW,
    )
    public = store.read_public(bundle.manifest.manifest_hash)
    public.update(
        {
            "lifecycle_status": "submission_in_progress",
            "hardware_job_submitted": False,
            "provider_action_id_hash": None,
            "provider_status": None,
        }
    )
    store.write_public(bundle.manifest.manifest_hash, public)

    repaired = submit_authorized_fire_opal_ibm_smoke(
        bundle,
        backend_name=BACKEND_NAME,
        authorization=authorization,
        approval_nonce=APPROVAL_NONCE,
        readiness=_readiness(),
        store=store,
        gateway=gateway,
        now=datetime(2026, 7, 12, 2, 1, tzinfo=timezone.utc),
    )

    assert repaired["lifecycle_status"] == "submitted"
    assert repaired["hardware_job_submitted"] is True
    assert repaired["provider_action_id_hash"]
    assert gateway.submit_calls == 1


def test_poll_timeout_and_failure_budget_are_visible_and_recoverable(tmp_path):
    batch, classical, local, bundle, store = _wave_d_fixture(tmp_path)
    gateway = FakeGateway(
        statuses=[
            RuntimeError("poll secret one"),
            RuntimeError("poll secret two"),
            RuntimeError("poll secret three"),
            "SUCCESS",
        ],
        result=_ideal_provider_result(bundle),
    )
    submit_authorized_fire_opal_ibm_smoke(
        bundle,
        backend_name=BACKEND_NAME,
        authorization=_authorization(bundle),
        approval_nonce=APPROVAL_NONCE,
        readiness=_readiness(),
        store=store,
        gateway=gateway,
        now=SUBMIT_NOW,
    )
    for minute in (1, 2, 3):
        state = poll_fire_opal_ibm_smoke(
            bundle,
            batch=batch,
            matched_classical_result=classical,
            local_quantum_result=local,
            store=store,
            gateway=gateway,
            now=datetime(2026, 7, 12, 2, minute, tzinfo=timezone.utc),
        )
    assert state["lifecycle_status"] == "poll_failure_budget_exhausted"
    with pytest.raises(RuntimeError, match="poll_failure_budget_exhausted"):
        poll_fire_opal_ibm_smoke(
            bundle,
            batch=batch,
            matched_classical_result=classical,
            local_quantum_result=local,
            store=store,
            gateway=gateway,
            now=datetime(2026, 7, 12, 2, 4, tzinfo=timezone.utc),
        )
    recovered = poll_fire_opal_ibm_smoke(
        bundle,
        batch=batch,
        matched_classical_result=classical,
        local_quantum_result=local,
        store=store,
        gateway=gateway,
        now=datetime(2026, 7, 12, 4, 30, tzinfo=timezone.utc),
        explicit_recovery=True,
    )
    assert recovered["lifecycle_status"] == "completed"
    assert recovered["timed_out"] is True
    assert "poll secret" not in json.dumps(recovered)


def test_malformed_provider_result_cannot_claim_completion(tmp_path):
    batch, classical, local, bundle, store = _wave_d_fixture(tmp_path)
    gateway = FakeGateway(statuses=["SUCCESS"], result={"results": [{"0": 1}]})
    submit_authorized_fire_opal_ibm_smoke(
        bundle,
        backend_name=BACKEND_NAME,
        authorization=_authorization(bundle),
        approval_nonce=APPROVAL_NONCE,
        readiness=_readiness(),
        store=store,
        gateway=gateway,
        now=SUBMIT_NOW,
    )
    state = poll_fire_opal_ibm_smoke(
        bundle,
        batch=batch,
        matched_classical_result=classical,
        local_quantum_result=local,
        store=store,
        gateway=gateway,
        now=datetime(2026, 7, 12, 2, 1, tzinfo=timezone.utc),
    )
    assert state["lifecycle_status"] == "result_retrieval_failed"
    assert state["hardware_experiment_completed"] is False
    assert state["receipt"] is None
    assert state["paper_order_created"] is False


def test_production_gateway_construction_is_provider_silent(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        "orchestrator.quantum._import_fireopal_without_update_check",
        lambda: calls.append("imported"),
    )

    class MinimalSettings:
        runtime_dir = str(tmp_path)
        qctrl_organization_slug = "qadam"

    FireOpalSdkIbmGateway(MinimalSettings())
    assert calls == []
