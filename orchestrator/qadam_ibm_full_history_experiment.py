"""Explicitly authorized IBM hardware discovery over Qadam's full history.

Quantum hardware cannot ingest the historical lake row-for-row. This module
uses every eligible score/label row to build deterministic chronological
prototypes from pre-outcome features, then executes the resulting fidelity
kernel through the existing guarded Q-CTRL Fire Opal/IBM route. Outcome labels
never enter the circuit and hardware results remain research-only.
"""

from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
import secrets
import time
from typing import Any

import numpy as np

from orchestrator.config import Settings
from orchestrator.qadam_classical_discovery import run_classical_discovery
from orchestrator.qadam_discovery_backend import (
    DiscoveryInputBatch,
    validate_discovery_input_batch,
)
from orchestrator.qadam_fire_opal_ibm_discovery import (
    FireOpalIbmBudgetPolicy,
    FireOpalIbmExperimentStore,
    FireOpalSdkIbmGateway,
    PreparedFireOpalIbmBundle,
    PreparedFireOpalIbmManifest,
    build_execution_authorization,
    build_sanitized_hardware_receipt,
    prepare_fire_opal_ibm_smoke_manifest,
    submit_authorized_fire_opal_ibm_smoke,
    validate_private_state,
    validate_public_state,
)
from orchestrator.qadam_local_quantum_discovery import (
    LocalQuantumDiscoveryPolicy,
    QiskitLocalQuantumDiscoveryBackend,
)
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    file_sha256,
    now_iso,
    read_json,
    runtime_dir,
    write_json_atomic,
)
from orchestrator.qadam_quantum_discovery_evidence import stable_hash
from orchestrator.qadam_statistical_backtest import load_empirical_backtest_dataset
from orchestrator.secrets import secret_value

SCHEMA_VERSION = "qadam.IbmFullHistoryExperiment.v1"
EXPERIMENT_ID = "ibm-full-history-surprise-discovery-v1"
STATUS_ARTIFACT = "qadam_ibm_full_history_experiment_status.json"
MANIFEST_ARTIFACT = "qadam_ibm_full_history_experiment_manifest.json"
AUTHORIZATION_ARTIFACT = "qadam_ibm_full_history_experiment_authorization.json"
RESULT_ARTIFACT = "qadam_ibm_full_history_experiment_result.json"
ANALYSIS_CACHE_ARTIFACT = ".qadam_ibm_full_history_analysis_cache.json"
QBC_COVERAGE_ARTIFACT = "qadam_backtest_completion_coverage.json"
QBC_RESULTS_ARTIFACT = "qadam_backtest_completion_results_summary.json"

FEATURE_NAMES = (
    "pattern_strength",
    "source_trust",
    "source_freshness",
    "source_activity",
    "causal_mapping_strength",
    "strategy_fit",
    "market_volatility",
    "market_flow",
)
ROW_FIELDS = (
    "raw_pattern_score",
    "source_trust",
    "source_freshness",
    "source_event_count",
    "causal_mapping_strength",
    "strategy_fit",
    "rolling_volatility",
    "volume_relative",
)
PROTOTYPE_COUNT = 32
LANDMARK_COUNT = 4
PROVIDER_BUDGET_USD = 100.0
PENDING_PROVIDER_STATUSES = {"PENDING", "QUEUED", "RUNNING", "IN_PROGRESS"}
EXPERIMENT_RUNTIME_WARNINGS = (
    {
        "category": "elevated_measurement_error",
        "source": "qctrl_execute_warning",
        "summary": (
            "Q-CTRL warned that the selected IBM device had elevated measurement "
            "error that could reduce result quality."
        ),
        "opportunistic_rerun_used": False,
    },
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _analysis_cache_path(runtime: Path) -> Path:
    return runtime / "qadam_fire_opal_ibm_discovery" / ANALYSIS_CACHE_ARTIFACT


def _write_analysis_cache(
    runtime: Path,
    *,
    batch: DiscoveryInputBatch,
    classical: Any,
    local: Any,
    manifest_hash: str,
) -> None:
    path = _analysis_cache_path(runtime)
    write_json_atomic(
        path,
        {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_ibm_full_history_analysis_cache",
            "manifest_hash": manifest_hash,
            "batch": batch.to_dict(),
            "classical": classical.to_dict(),
            "local": local.to_dict(),
        },
    )
    path.chmod(0o600)


def _restore_batch(payload: dict[str, Any]) -> DiscoveryInputBatch:
    source = payload.get("batch")
    if not isinstance(source, dict):
        raise ValueError("ibm_full_history_analysis_batch_missing")
    values = {field.name: source.get(field.name) for field in fields(DiscoveryInputBatch)}
    for key in (
        "feature_names",
        "window_manifest_hashes",
        "window_ids",
    ):
        values[key] = tuple(values[key] or ())
    values["matrix"] = tuple(tuple(row) for row in values["matrix"] or ())
    values["missingness_masks"] = tuple(
        tuple(row) for row in values["missingness_masks"] or ()
    )
    batch = DiscoveryInputBatch(**values)
    errors = validate_discovery_input_batch(batch.to_dict())
    if errors:
        raise ValueError(f"ibm_full_history_cached_batch_invalid:{','.join(errors)}")
    return batch


def _restore_bundle(
    public: dict[str, Any],
    private: dict[str, Any],
) -> PreparedFireOpalIbmBundle:
    source = public.get("manifest")
    if not isinstance(source, dict):
        raise ValueError("ibm_full_history_provider_manifest_missing")
    values = {
        field.name: source.get(field.name)
        for field in fields(PreparedFireOpalIbmManifest)
    }
    for key in (
        "landmark_indices",
        "source_feature_circuit_hashes",
        "circuit_hashes",
        "circuit_depths",
    ):
        values[key] = tuple(values[key] or ())
    values["circuit_pairs"] = tuple(
        tuple(pair) for pair in values["circuit_pairs"] or ()
    )
    manifest = PreparedFireOpalIbmManifest(**values)
    return PreparedFireOpalIbmBundle(
        manifest=manifest,
        qasm_circuits=tuple(private.get("qasm_circuits") or ()),
    )


def _safe_number(value: Any) -> float:
    try:
        resolved = float(value)
    except (TypeError, ValueError):
        return 0.0
    return resolved if np.isfinite(resolved) else 0.0


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


def _chronological_prototypes(
    rows: list[dict[str, Any]],
    *,
    prototype_count: int = PROTOTYPE_COUNT,
) -> tuple[np.ndarray, list[dict[str, Any]], dict[str, Any]]:
    """Compress every row into chronological prototypes without using labels."""

    if len(rows) < prototype_count:
        raise ValueError("ibm_full_history_insufficient_rows")
    ordered = sorted(
        rows,
        key=lambda row: (
            str(row.get("decision_at") or ""),
            str(row.get("score_id") or ""),
        ),
    )
    raw = np.asarray(
        [[_safe_number(row.get(field)) for field in ROW_FIELDS] for row in ordered],
        dtype=float,
    )
    means = raw.mean(axis=0)
    scales = raw.std(axis=0)
    scales = np.where(scales <= 1e-12, 1.0, scales)
    standardized = np.clip((raw - means) / scales, -3.0, 3.0)
    buckets = np.array_split(np.arange(len(ordered)), prototype_count)
    matrix: list[list[float]] = []
    lineage: list[dict[str, Any]] = []
    represented = 0
    for index, bucket in enumerate(buckets):
        if bucket.size == 0:
            raise ValueError("ibm_full_history_empty_prototype")
        prototype = standardized[bucket].mean(axis=0)
        bucket_rows = [ordered[int(row_index)] for row_index in bucket]
        score_ids = [str(row.get("score_id") or "") for row in bucket_rows]
        row_hash = stable_hash(score_ids)
        matrix.append([round(float(value), 12) for value in prototype])
        represented += len(bucket_rows)
        lineage.append(
            {
                "prototype_index": index,
                "row_count": len(bucket_rows),
                "first_decision_at": str(bucket_rows[0].get("decision_at") or ""),
                "last_decision_at": str(bucket_rows[-1].get("decision_at") or ""),
                "score_id_set_hash": row_hash,
                "instrument_count": len(
                    {str(row.get("instrument") or "") for row in bucket_rows}
                ),
                "source_count": len(
                    {
                        str(source)
                        for row in bucket_rows
                        for source in row.get("source_keys", [])
                    }
                ),
            }
        )
    if represented != len(ordered):
        raise ValueError("ibm_full_history_row_accounting_mismatch")
    audit = {
        "input_row_count": len(ordered),
        "represented_row_count": represented,
        "prototype_count": prototype_count,
        "feature_count": len(FEATURE_NAMES),
        "feature_names": list(FEATURE_NAMES),
        "feature_means": {
            name: round(float(value), 12)
            for name, value in zip(FEATURE_NAMES, means, strict=True)
        },
        "feature_scales": {
            name: round(float(value), 12)
            for name, value in zip(FEATURE_NAMES, scales, strict=True)
        },
        "labels_sent_to_quantum_circuit": False,
        "all_rows_represented_once": represented == len(ordered),
    }
    return np.asarray(matrix, dtype=float), lineage, audit


def build_full_history_batch(
    settings: Settings | None = None,
) -> tuple[DiscoveryInputBatch, dict[str, Any], list[dict[str, Any]]]:
    resolved = settings or Settings.from_env()
    runtime = runtime_dir(resolved)
    rows, score_audit = load_empirical_backtest_dataset(runtime)
    if score_audit.get("status") != "empirical_score_label_pairs_loaded":
        raise RuntimeError("ibm_full_history_score_label_plane_unavailable")
    matrix, lineage, prototype_audit = _chronological_prototypes(rows)
    coverage = read_json(runtime / QBC_COVERAGE_ARTIFACT)
    qbc_results = read_json(runtime / QBC_RESULTS_ARTIFACT)
    window_ids = tuple(
        f"qbc-history-prototype:{row['prototype_index']:02d}:{row['score_id_set_hash'][:16]}"
        for row in lineage
    )
    window_hashes = tuple(
        stable_hash(
            {
                "window_id": window_id,
                "lineage": row,
                "features": matrix[index].tolist(),
            }
        )
        for index, (window_id, row) in enumerate(zip(window_ids, lineage, strict=True))
    )
    material: dict[str, Any] = {
        "market_sleeve": "qadam_whole_universe",
        "target_instrument": "QADAM_ALL_WATCHED_INSTRUMENTS",
        "feature_names": FEATURE_NAMES,
        "matrix": tuple(tuple(float(value) for value in row) for row in matrix),
        "missingness_masks": tuple(
            tuple(0 for _ in FEATURE_NAMES) for _ in range(len(matrix))
        ),
        "window_manifest_hashes": window_hashes,
        "window_ids": window_ids,
        "feature_schema_version": "qadam.full_history_quantum_features.v1",
        "chronological_split_identity": (
            "chronological-split:qbc-full-history-unsupervised-no-labels-v1"
        ),
        "encoding_version": "qadam.full_history_fire_opal_angle_encoding.v1",
        "random_seed": 1729,
        "contract_fixture_only": False,
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
        raise ValueError(f"ibm_full_history_batch_invalid:{','.join(errors)}")
    envelope = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_ibm_full_history_input_envelope",
        "experiment_id": EXPERIMENT_ID,
        "generated_at": now_iso(),
        "status": "full_history_represented_for_hardware_discovery",
        "shared_manifest_hash": shared_manifest_hash,
        "provider_backed_historical_row_lineage_count": int(
            coverage.get("provider_backed_historical_rows") or 0
        ),
        "paired_score_label_row_count": int(
            score_audit.get("paired_score_label_count") or 0
        ),
        "paired_rows_numerically_represented": prototype_audit[
            "represented_row_count"
        ],
        "qbc_terminal_result_lineage_count": int(
            qbc_results.get("current_registered_result_count") or 0
        ),
        "canonical_source_count": int(coverage.get("source_count") or 0),
        "canonical_instrument_count": int(coverage.get("instrument_count") or 0),
        "historically_scored_source_count": int(
            coverage.get("historically_scored_source_count") or 0
        ),
        "score_plane_source_count": int(score_audit.get("source_count") or 0),
        "score_plane_instrument_count": int(
            score_audit.get("instrument_count") or 0
        ),
        "score_dataset_hash": score_audit.get("score_dataset_hash"),
        "label_dataset_hash": score_audit.get("label_dataset_hash"),
        "coverage_artifact_sha256": file_sha256(runtime / QBC_COVERAGE_ARTIFACT),
        "results_artifact_sha256": file_sha256(runtime / QBC_RESULTS_ARTIFACT),
        "prototype_audit": prototype_audit,
        "prototype_lineage": lineage,
        "boundary": (
            "All scoreable historical records contribute to the circuit matrix. "
            "The wider provider-backed lake is bound by provenance and coverage; "
            "unpaired or context-only rows are not fabricated into predictive features."
        ),
        "authority": authority_flags(),
    }
    return batch, envelope, rows


def prepare_full_history_experiment(
    settings: Settings | None = None,
) -> dict[str, Any]:
    resolved = settings or Settings.from_env()
    runtime = runtime_dir(resolved)
    batch, envelope, _rows = build_full_history_batch(resolved)
    local_policy = LocalQuantumDiscoveryPolicy(
        maximum_landmarks=LANDMARK_COUNT,
        maximum_batch_rows=PROTOTYPE_COUNT,
        maximum_circuit_evaluations=128,
        finite_shot_count=1024,
    )
    classical = run_classical_discovery(batch)
    local = QiskitLocalQuantumDiscoveryBackend(local_policy).run(
        batch,
        mode="ideal",
        matched_classical_result=classical,
    )
    hardware_policy = FireOpalIbmBudgetPolicy(
        maximum_circuits=128,
        shots_per_circuit=256,
        maximum_total_shots=32_768,
        maximum_provider_budget_usd=PROVIDER_BUDGET_USD,
    )
    bundle = prepare_fire_opal_ibm_smoke_manifest(
        batch,
        matched_classical_result=classical,
        local_quantum_result=local,
        policy=hardware_policy,
    )
    _write_analysis_cache(
        runtime,
        batch=batch,
        classical=classical,
        local=local,
        manifest_hash=bundle.manifest.manifest_hash,
    )
    store = FireOpalIbmExperimentStore(runtime)
    store.write_prepared(bundle)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_ibm_full_history_experiment_manifest",
        "experiment_id": EXPERIMENT_ID,
        "generated_at": now_iso(),
        "status": "prepared_for_explicit_hardware_authorization",
        "input_envelope": envelope,
        "batch": {
            "batch_id": batch.batch_id,
            "shared_manifest_hash": batch.shared_manifest_hash,
            "prototype_count": len(batch.matrix),
            "feature_count": len(batch.feature_names),
            "feature_names": list(batch.feature_names),
            "labels_present": batch.labels_present,
            "contract_fixture_only": batch.contract_fixture_only,
        },
        "classical_result_id": classical.result_id,
        "local_quantum_result_id": local.result_id,
        "local_quantum_kernel_hash": local.kernel_hash,
        "hardware_manifest": bundle.manifest.to_public_dict(),
        "provider_budget_usd": PROVIDER_BUDGET_USD,
        "operator_authorization_required": True,
        "hardware_scheduler_enabled": False,
        "trade_or_execution_authority_created": False,
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / MANIFEST_ARTIFACT, payload)
    return {
        "batch": batch,
        "envelope": envelope,
        "classical": classical,
        "local": local,
        "bundle": bundle,
        "store": store,
        "manifest": payload,
    }


def select_supported_ibm_backend(
    readiness: dict[str, Any],
    settings: Settings | None = None,
) -> tuple[str, dict[str, Any]]:
    """Select the least-busy operational backend without persisting its name."""

    resolved = settings or Settings.from_env()
    supported_hashes = set(readiness.get("supported_device_name_hashes") or [])
    if not supported_hashes:
        raise RuntimeError("ibm_full_history_no_supported_device_hashes")
    from qiskit_ibm_runtime import QiskitRuntimeService

    service = QiskitRuntimeService(
        channel="ibm_quantum_platform",
        token=secret_value("IBM_QUANTUM_TOKEN", resolved),
        instance=secret_value("IBM_QUANTUM_INSTANCE", resolved),
    )
    candidates: list[tuple[int, str, int]] = []
    for backend in service.backends():
        name = getattr(backend, "name", None)
        if callable(name):
            name = name()
        name = str(name or "")
        if not name or sha256(name.encode("utf-8")).hexdigest() not in supported_hashes:
            continue
        try:
            status = backend.status()
            operational = bool(getattr(status, "operational", True))
            pending_jobs = int(getattr(status, "pending_jobs", 0) or 0)
        except Exception:  # noqa: BLE001 - backend remains eligible with unknown queue.
            operational = True
            pending_jobs = 1_000_000
        if not operational:
            continue
        qubits = int(getattr(backend, "num_qubits", 0) or 0)
        candidates.append((pending_jobs, name, qubits))
    if not candidates:
        raise RuntimeError("ibm_full_history_no_operational_supported_backend")
    pending_jobs, backend_name, qubits = sorted(candidates)[0]
    return backend_name, {
        "backend_name_hash": sha256(backend_name.encode("utf-8")).hexdigest(),
        "pending_jobs_at_selection": pending_jobs,
        "backend_qubit_count": qubits,
        "candidate_backend_count": len(candidates),
    }


def _write_status(
    runtime: Path,
    *,
    state: dict[str, Any],
    manifest: dict[str, Any],
    backend_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = state.get("receipt") if isinstance(state.get("receipt"), dict) else {}
    result = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_ibm_full_history_experiment_result",
        "experiment_id": EXPERIMENT_ID,
        "generated_at": now_iso(),
        "status": state.get("lifecycle_status") or "prepared",
        "hardware_execution_authorized": state.get("hardware_execution_authorized")
        is True,
        "hardware_job_submitted": state.get("hardware_job_submitted") is True,
        "hardware_experiment_completed": state.get("hardware_experiment_completed")
        is True,
        "provider_status": state.get("provider_status"),
        "provider_action_id_hash": state.get("provider_action_id_hash"),
        "backend_name_hash": state.get("backend_name_hash"),
        "provider_call_count": int(state.get("provider_call_count") or 0),
        "poll_count": int(state.get("poll_count") or 0),
        "provider_runtime_warnings": (
            [dict(row) for row in EXPERIMENT_RUNTIME_WARNINGS]
            if state.get("hardware_job_submitted") is True
            else []
        ),
        "failure_category": state.get("failure_category"),
        "receipt_hash": state.get("receipt_hash"),
        "hardware_research_candidate_count": len(
            receipt.get("research_candidates") or []
        ),
        "hardware_method_results": receipt.get("method_results") or [],
        "research_candidates": receipt.get("research_candidates") or [],
        "input_envelope": manifest.get("input_envelope"),
        "hardware_manifest_hash": (
            manifest.get("hardware_manifest") or {}
        ).get("manifest_hash"),
        "backend_selection": backend_summary,
        "validated_edge_created": False,
        "strategy_hypothesis_created": False,
        "trade_candidate_created": False,
        "risk_approval_created": False,
        "execution_approval_created": False,
        "paper_order_created": False,
        "broker_write_count": 0,
        "proof_credit_created": False,
        "profitability_certified": False,
        "interpretation": (
            "A completed hardware run may identify structural relationships. It does "
            "not prove that those relationships predict returns until separate, "
            "frozen out-of-sample validation succeeds."
        ),
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / RESULT_ARTIFACT, result)
    status = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_ibm_full_history_experiment_status",
        "experiment_id": EXPERIMENT_ID,
        "generated_at": result["generated_at"],
        "status": result["status"],
        "hardware_job_submitted": result["hardware_job_submitted"],
        "hardware_experiment_completed": result["hardware_experiment_completed"],
        "hardware_research_candidate_count": result[
            "hardware_research_candidate_count"
        ],
        "provider_status": result["provider_status"],
        "failure_category": result["failure_category"],
        "public_safe": True,
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / STATUS_ARTIFACT, status)
    return result


def submit_full_history_experiment(
    *,
    explicit_operator_approval: bool,
    settings: Settings | None = None,
) -> dict[str, Any]:
    if explicit_operator_approval is not True:
        raise PermissionError("ibm_full_history_explicit_operator_approval_required")
    resolved = settings or Settings.from_env()
    runtime = runtime_dir(resolved)
    prepared = prepare_full_history_experiment(resolved)
    readiness = read_json(runtime / "qctrl_fire_opal_ibm_readiness.json")
    backend_name, backend_summary = select_supported_ibm_backend(readiness, resolved)
    current = _utc_now()
    nonce = secrets.token_urlsafe(32)
    authorization = build_execution_authorization(
        prepared["bundle"].manifest,
        backend_name=backend_name,
        approval_nonce=nonce,
        estimated_provider_cost_usd=PROVIDER_BUDGET_USD,
        maximum_provider_cost_usd=PROVIDER_BUDGET_USD,
        issued_at=current.isoformat(),
        expires_at=(current + timedelta(hours=1)).isoformat(),
        explicit_operator_approval=True,
    )
    authorization_payload = authorization.to_public_dict()
    authorization_payload.update(
        {
            "experiment_id": EXPERIMENT_ID,
            "operator_approval_basis": "explicit_current_task_single_run",
            "backend_selection": backend_summary,
            "approval_nonce_persisted": False,
            "recurring_hardware_authority_created": False,
        }
    )
    write_json_atomic(runtime / AUTHORIZATION_ARTIFACT, authorization_payload)
    state = submit_authorized_fire_opal_ibm_smoke(
        prepared["bundle"],
        backend_name=backend_name,
        authorization=authorization,
        approval_nonce=nonce,
        readiness=readiness,
        store=prepared["store"],
        gateway=FireOpalSdkIbmGateway(resolved),
        now=current,
    )
    return _write_status(
        runtime,
        state=state,
        manifest=prepared["manifest"],
        backend_summary=backend_summary,
    )


def poll_full_history_experiment(
    settings: Settings | None = None,
    *,
    explicit_recovery: bool = False,
) -> dict[str, Any]:
    """Poll provider status cheaply, then finalize a successful result once."""

    resolved = settings or Settings.from_env()
    runtime = runtime_dir(resolved)
    manifest = read_json(runtime / MANIFEST_ARTIFACT)
    hardware_manifest = manifest.get("hardware_manifest") or {}
    manifest_hash = str(hardware_manifest.get("manifest_hash") or "")
    if len(manifest_hash) != 64:
        raise RuntimeError("ibm_full_history_manifest_hash_missing")
    store = FireOpalIbmExperimentStore(runtime)
    current = _utc_now()
    should_finalize = False
    with store.claim(manifest_hash):
        private = store.read_private(manifest_hash)
        public = store.read_public(manifest_hash)
        validate_private_state(private, manifest_hash=manifest_hash)
        validate_public_state(public)
        if public.get("receipt"):
            state = public
        else:
            action_id = private.get("action_id")
            backend_name = private.get("backend_name")
            if not isinstance(action_id, str) or not isinstance(backend_name, str):
                raise RuntimeError("ibm_full_history_poll_requires_submitted_action")
            if public.get("provider_action_id_hash") != sha256(
                action_id.encode("utf-8")
            ).hexdigest():
                raise ValueError("ibm_full_history_poll_action_hash_mismatch")
            if public.get("backend_name_hash") != sha256(
                backend_name.encode("utf-8")
            ).hexdigest():
                raise ValueError("ibm_full_history_poll_backend_hash_mismatch")
            poll_count = int(private.get("poll_count") or 0)
            maximum_polls = int(
                (public.get("manifest") or {}).get("policy_contract", {}).get(
                    "maximum_poll_count"
                )
                or 0
            )
            if poll_count >= maximum_polls and explicit_recovery is not True:
                raise RuntimeError("ibm_full_history_poll_budget_exhausted")
            private["poll_count"] = poll_count + 1
            private["updated_at"] = current.isoformat()
            public["poll_count"] = poll_count + 1
            public["provider_call_count"] = int(
                public.get("provider_call_count") or 0
            ) + 1
            public["updated_at"] = current.isoformat()
            try:
                provider_status = FireOpalSdkIbmGateway(resolved).job_status(
                    action_id=action_id
                ).upper()
            except Exception as exc:  # noqa: BLE001 - persist only sanitized failure.
                failure_count = int(private.get("poll_failure_count") or 0) + 1
                private["poll_failure_count"] = failure_count
                private["lifecycle_status"] = "poll_failed_retryable"
                public.update(
                    {
                        "poll_failure_count": failure_count,
                        "lifecycle_status": "poll_failed_retryable",
                        "failure_category": "provider_status_poll_failed",
                        "failure_class": exc.__class__.__name__,
                        "failure_message_hash": sha256(
                            str(exc).encode("utf-8")
                        ).hexdigest(),
                    }
                )
                store.write_private(manifest_hash, private)
                store.write_public(manifest_hash, public)
                state = public
            else:
                public["provider_status"] = provider_status
                if provider_status in PENDING_PROVIDER_STATUSES:
                    lifecycle = "provider_pending"
                elif provider_status in {"FAILURE", "REVOKED"}:
                    lifecycle = "provider_terminal_failure"
                    public["failure_category"] = (
                        f"provider_status_{provider_status.lower()}"
                    )
                elif provider_status == "SUCCESS":
                    lifecycle = "provider_success_result_pending"
                    should_finalize = True
                else:
                    lifecycle = "provider_status_unknown"
                    public["failure_category"] = "provider_status_unknown"
                private["lifecycle_status"] = lifecycle
                public["lifecycle_status"] = lifecycle
                store.write_private(manifest_hash, private)
                store.write_public(manifest_hash, public)
                state = public
    if should_finalize:
        state = finalize_full_history_experiment(resolved)
    prior = read_json(runtime / RESULT_ARTIFACT)
    return _write_status(
        runtime,
        state=state,
        manifest=manifest,
        backend_summary=prior.get("backend_selection"),
    )


def finalize_full_history_experiment(
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Retrieve one successful job and persist only its sanitized receipt."""

    resolved = settings or Settings.from_env()
    runtime = runtime_dir(resolved)
    manifest = read_json(runtime / MANIFEST_ARTIFACT)
    hardware_manifest = manifest.get("hardware_manifest") or {}
    manifest_hash = str(hardware_manifest.get("manifest_hash") or "")
    cache = read_json(_analysis_cache_path(runtime))
    if cache.get("manifest_hash") != manifest_hash:
        raise RuntimeError("ibm_full_history_analysis_cache_mismatch")
    batch = _restore_batch(cache)
    store = FireOpalIbmExperimentStore(runtime)
    current = _utc_now()
    with store.claim(manifest_hash):
        private = store.read_private(manifest_hash)
        public = store.read_public(manifest_hash)
        validate_private_state(private, manifest_hash=manifest_hash)
        validate_public_state(public)
        if public.get("receipt"):
            return public
        if public.get("provider_status") != "SUCCESS":
            raise RuntimeError("ibm_full_history_result_not_ready")
        action_id = private.get("action_id")
        backend_name = private.get("backend_name")
        if not isinstance(action_id, str) or not isinstance(backend_name, str):
            raise RuntimeError("ibm_full_history_result_identity_missing")
        bundle = _restore_bundle(public, private)
        public["provider_call_count"] = int(public.get("provider_call_count") or 0) + 1
        try:
            raw_result = FireOpalSdkIbmGateway(resolved).job_result(
                action_id=action_id
            )
            receipt = build_sanitized_hardware_receipt(
                bundle=bundle,
                batch=batch,
                matched_classical_result=cache.get("classical") or {},
                local_quantum_result=cache.get("local") or {},
                action_id=action_id,
                backend_name=backend_name,
                raw_provider_result=raw_result,
                completed_at=current.isoformat(),
            )
        except Exception as exc:  # noqa: BLE001 - persist only sanitized failure.
            failure_count = int(private.get("poll_failure_count") or 0) + 1
            private["poll_failure_count"] = failure_count
            private["lifecycle_status"] = "result_retrieval_failed"
            public.update(
                {
                    "poll_failure_count": failure_count,
                    "lifecycle_status": "result_retrieval_failed",
                    "failure_category": "provider_result_retrieval_failed",
                    "failure_class": exc.__class__.__name__,
                    "failure_message_hash": sha256(
                        str(exc).encode("utf-8")
                    ).hexdigest(),
                }
            )
            store.write_private(manifest_hash, private)
            store.write_public(manifest_hash, public)
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
        store.write_private(manifest_hash, private)
        store.write_public(manifest_hash, public)
        return public


def wait_for_full_history_experiment(
    settings: Settings | None = None,
    *,
    poll_interval_seconds: int = 20,
    maximum_wait_seconds: int = 7_200,
) -> dict[str, Any]:
    started = time.monotonic()
    terminal = {
        "completed",
        "provider_terminal_failure",
        "provider_validation_failed",
        "provider_validation_rejected",
        "submission_ambiguous_requires_reconciliation",
        "poll_failure_budget_exhausted",
        "provider_status_unknown",
        "result_retrieval_failed",
    }
    while True:
        result = poll_full_history_experiment(settings)
        if result.get("status") in terminal:
            return result
        if time.monotonic() - started >= maximum_wait_seconds:
            return result
        time.sleep(max(1, poll_interval_seconds))


def validate_full_history_result(
    result: dict[str, Any],
    *,
    require_completed: bool,
) -> list[str]:
    errors: list[str] = []
    envelope = result.get("input_envelope") or {}
    prototype = envelope.get("prototype_audit") or {}
    if result.get("schema_version") != SCHEMA_VERSION:
        errors.append("ibm_full_history_schema_invalid")
    if int(envelope.get("provider_backed_historical_row_lineage_count") or 0) <= 0:
        errors.append("ibm_full_history_provider_lineage_missing")
    if int(envelope.get("paired_score_label_row_count") or 0) <= 0:
        errors.append("ibm_full_history_score_rows_missing")
    if envelope.get("paired_rows_numerically_represented") != envelope.get(
        "paired_score_label_row_count"
    ):
        errors.append("ibm_full_history_not_all_score_rows_represented")
    if prototype.get("all_rows_represented_once") is not True:
        errors.append("ibm_full_history_row_accounting_failed")
    if prototype.get("labels_sent_to_quantum_circuit") is not False:
        errors.append("ibm_full_history_label_leakage")
    if require_completed and result.get("hardware_experiment_completed") is not True:
        errors.append("ibm_full_history_hardware_not_completed")
    for key in (
        "validated_edge_created",
        "strategy_hypothesis_created",
        "trade_candidate_created",
        "risk_approval_created",
        "execution_approval_created",
        "paper_order_created",
        "proof_credit_created",
        "profitability_certified",
    ):
        if result.get(key) is not False:
            errors.append(f"ibm_full_history_forbidden_state:{key}")
    if int(result.get("broker_write_count") or 0) != 0:
        errors.append("ibm_full_history_broker_write_created")
    return sorted(set(errors))
