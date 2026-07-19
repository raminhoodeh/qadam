"""RF-4 provider, storage, job, and pure research boundaries.

This module defines interfaces only. It performs no network acquisition and
does not promote the existing local/sample baseline into historical evidence.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import StrEnum
import inspect
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore, OriginClass
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    authority_flags,
    now_iso,
    read_json,
    runtime_dir,
    unique_errors,
    validate_authority,
)

SCHEMA_VERSION = "qadam_research_boundaries.v1"
PHASE_ID = "RF-4"

PROVIDER_REGISTRY_ARTIFACT = "qadam_provider_protocol_registry.json"
STORAGE_REGISTRY_ARTIFACT = "qadam_storage_boundary_registry.json"
RESEARCH_AUDIT_ARTIFACT = "qadam_research_service_boundary_audit.json"
BASELINE_ORIGIN_ARTIFACT = "qadam_local_baseline_origin_audit.json"
CHECK_ARTIFACT = "qadam_research_boundaries_checks.json"


class StoragePlane(StrEnum):
    RAW = "raw"
    NORMALIZED = "normalized"
    POINT_IN_TIME = "point_in_time"
    RESEARCH = "research"
    GENERATED_VIEW = "generated_view"
    PROOF_ELIGIBLE = "proof_eligible"


@dataclass(frozen=True, kw_only=True)
class ProviderCapability:
    provider_id: str
    data_kind: str
    current_supported: bool
    historical_supported: bool
    credential_required: bool
    rate_limit_class: str
    outage_state: str = "unknown"
    earliest_available_at: str | None = None
    latest_available_at: str | None = None


@dataclass(frozen=True, kw_only=True)
class ObservationRequest:
    source_key: str
    start_at: str | None = None
    end_at: str | None = None
    cursor: str | None = None
    limit: int = 1000


@dataclass(frozen=True, kw_only=True)
class PriceRequest:
    instrument: str
    interval: str
    start_at: str | None = None
    end_at: str | None = None
    cursor: str | None = None
    limit: int = 1000


@dataclass(frozen=True, kw_only=True)
class ProviderBatch:
    provider_id: str
    origin_class: str
    records: tuple[dict[str, Any], ...]
    next_cursor: str | None
    request_started_at: str
    response_received_at: str
    checksum: str
    network_call_count: int


@runtime_checkable
class CurrentObservationProvider(Protocol):
    def fetch_current_observations(self, request: ObservationRequest) -> ProviderBatch: ...


@runtime_checkable
class HistoricalObservationProvider(Protocol):
    def fetch_historical_observations(self, request: ObservationRequest) -> ProviderBatch: ...


@runtime_checkable
class CurrentPriceProvider(Protocol):
    def fetch_current_prices(self, request: PriceRequest) -> ProviderBatch: ...


@runtime_checkable
class HistoricalPriceProvider(Protocol):
    def fetch_historical_prices(self, request: PriceRequest) -> ProviderBatch: ...


@runtime_checkable
class ProviderCapabilityReader(Protocol):
    def capabilities(self) -> tuple[ProviderCapability, ...]: ...


@dataclass(frozen=True, kw_only=True)
class ResumableJobSpec:
    job_id: str
    job_type: str
    provider_id: str
    partition_key: str
    start_at: str | None
    end_at: str | None
    max_attempts: int
    rate_limit_class: str
    origin_class: str
    checksum_policy: str = "sha256_canonical_payload"
    idempotency_key: str = ""


@dataclass(frozen=True, kw_only=True)
class ResumableJobCheckpoint:
    job_id: str
    state: str
    attempt: int
    cursor: str | None
    completed_partition_count: int
    record_count: int
    last_checksum: str | None
    updated_at: str
    retry_class: str | None = None
    terminal_reason: str | None = None


@dataclass(frozen=True, kw_only=True)
class StorageEnvelope:
    record_id: str
    plane: str
    record_type: str
    origin_class: str
    schema_version: str
    generated_at: str
    payload: dict[str, Any]
    checksum: str
    evidence_eligible: bool
    proof_eligible: bool


@runtime_checkable
class FeatureBuilder(Protocol):
    def build_features(self, records: tuple[dict[str, Any], ...]) -> dict[str, Any]: ...


@runtime_checkable
class PatternScorer(Protocol):
    def score(self, feature_vector: dict[str, Any]) -> dict[str, Any]: ...


@runtime_checkable
class ForwardLabeler(Protocol):
    def label(self, score_record: dict[str, Any], prices: tuple[dict[str, Any], ...]) -> dict[str, Any]: ...


@runtime_checkable
class BacktestEngine(Protocol):
    def run(self, scores: tuple[dict[str, Any], ...], labels: tuple[dict[str, Any], ...]) -> dict[str, Any]: ...


class LocalResearchStore:
    """Plane-separated local store used by research implementations and tests."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir.resolve()
        self.stores = {
            plane: AtomicArtifactStore[dict[str, Any]](self.base_dir / plane.value)
            for plane in StoragePlane
        }

    def write_json(self, plane: StoragePlane, name: str, payload: dict[str, Any]) -> Path:
        if plane is StoragePlane.PROOF_ELIGIBLE and payload.get("proof_eligible") is not True:
            raise ValueError("proof_plane_requires_explicit_eligibility")
        return self.stores[plane].write_json(name, payload)

    def read_json(self, plane: StoragePlane, name: str) -> dict[str, Any]:
        return self.stores[plane].read_json(name)


PROTOCOLS = {
    "current_observation_provider": "CurrentObservationProvider",
    "historical_observation_provider": "HistoricalObservationProvider",
    "current_price_provider": "CurrentPriceProvider",
    "historical_price_provider": "HistoricalPriceProvider",
    "provider_capability_reader": "ProviderCapabilityReader",
}

RESEARCH_SERVICES = {
    "feature_builder": "FeatureBuilder",
    "pattern_scorer": "PatternScorer",
    "forward_labeler": "ForwardLabeler",
    "backtest_engine": "BacktestEngine",
}

CURRENT_ADAPTER_COMPATIBILITY = (
    {
        "module": "orchestrator.adapters",
        "adapters": ["GDELTAdapter", "OrefAdapter", "NASAFIRMSAdapter", "FREDAdapter", "RSSAdapter"],
        "boundary_state": "compatibility_adapter_requires_protocol_wrapper",
    },
    {
        "module": "orchestrator.phase1_live_adapters",
        "adapters": ["PHASE1_LIVE_ADAPTERS"],
        "boundary_state": "compatibility_adapter_requires_protocol_wrapper",
    },
    {
        "module": "orchestrator.historical_backfill",
        "adapters": ["HistoricalBackfillPlan", "HistoricalBackfillStore"],
        "boundary_state": "sample_contract_not_provider_history",
    },
)


def _paths(settings: Settings | None = None) -> dict[str, Path]:
    runtime = runtime_dir(settings)
    return {
        "provider_registry": runtime / PROVIDER_REGISTRY_ARTIFACT,
        "storage_registry": runtime / STORAGE_REGISTRY_ARTIFACT,
        "research_audit": runtime / RESEARCH_AUDIT_ARTIFACT,
        "baseline_origin": runtime / BASELINE_ORIGIN_ARTIFACT,
        "checks": runtime / CHECK_ARTIFACT,
    }


def build_provider_protocol_registry() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_provider_protocol_registry",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "provider_protocols_defined_no_acquisition",
        "protocol_count": len(PROTOCOLS),
        "protocols": [
            {
                "protocol_id": protocol_id,
                "interface": interface,
                "network_access_location": "provider_implementation_only",
                "pure_research_access_allowed": False,
                "returns_typed_provider_batch": True,
            }
            for protocol_id, interface in PROTOCOLS.items()
        ],
        "compatibility_adapters": list(CURRENT_ADAPTER_COMPATIBILITY),
        "provider_call_count": 0,
        "provider_acquisition_started": False,
        "authority": authority_flags(),
    }


def build_storage_boundary_registry() -> dict[str, Any]:
    records = []
    for plane in StoragePlane:
        records.append(
            {
                "plane": plane.value,
                "atomic_write_required": True,
                "origin_class_required": True,
                "schema_version_required": True,
                "checksum_required": True,
                "proof_eligibility_required": plane is StoragePlane.PROOF_ELIGIBLE,
                "network_access_allowed": False,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_storage_boundary_registry",
        "generated_at": now_iso(),
        "status": "plane_separated_storage_defined",
        "plane_count": len(records),
        "planes": records,
        "job_contract": {
            "spec": "ResumableJobSpec",
            "checkpoint": "ResumableJobCheckpoint",
            "required_fields": [
                "partition_key",
                "idempotency_key",
                "checksum_policy",
                "attempt",
                "cursor",
                "retry_class",
                "terminal_reason",
            ],
            "interruption_safe_resume_required": True,
        },
        "authority": authority_flags(),
    }


def build_research_boundary_audit() -> dict[str, Any]:
    source = inspect.getsource(__import__(__name__, fromlist=["*"]))
    tree = ast.parse(source)
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", 1)[0])
    forbidden_network_imports = sorted(
        imported_roots.intersection({"requests", "httpx", "urllib", "aiohttp"})
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_research_service_boundary_audit",
        "generated_at": now_iso(),
        "status": "pure_research_boundaries_defined",
        "service_count": len(RESEARCH_SERVICES),
        "services": [
            {
                "service_id": service_id,
                "interface": interface,
                "typed_input_required": True,
                "typed_output_required": True,
                "network_access_allowed": False,
                "broker_access_allowed": False,
                "authority_creation_allowed": False,
            }
            for service_id, interface in RESEARCH_SERVICES.items()
        ],
        "forbidden_network_imports": forbidden_network_imports,
        "score_label_separation_required": True,
        "feature_provider_separation_required": True,
        "backtest_execution_separation_required": True,
        "authority": authority_flags(),
    }


def build_local_baseline_origin_audit(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    state = read_json(runtime / "qsase_whole_universe_backfill_backtest_state.json")
    dashboard = read_json(runtime / "qsase_whole_universe_backfill_backtest_dashboard_summary.json")
    historical_source = (ROOT / "orchestrator" / "historical_backfill.py").read_text(encoding="utf-8")
    sample_contract_explicit = all(
        token in historical_source
        for token in (
            'mode="sample_contract"',
            '"historical_backfill_live_pull": False',
            "True historical pulls require live credentials",
        )
    )
    complete_windows = int(dashboard.get("complete_forward_window_count") or 0)
    missing_windows = int(dashboard.get("missing_forward_window_count") or 0)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_local_baseline_origin_audit",
        "generated_at": now_iso(),
        "status": "local_sample_baseline_explicitly_non_promotable",
        "state_artifact_status": state.get("status"),
        "dashboard_artifact_status": dashboard.get("status"),
        "origin_class": OriginClass.QADAM_RUNTIME.value,
        "provider_backed_historical_acquisition": False,
        "sample_contract_explicit": sample_contract_explicit,
        "provider_call_count_proven": False,
        "complete_forward_window_count": complete_windows,
        "missing_forward_window_count": missing_windows,
        "edge_promotion_allowed": False,
        "strategy_promotion_allowed": False,
        "paper_trade_eligibility_created": False,
        "proof_eligible": False,
        "next_provider_acquisition_phase": "OR-3",
        "authority": authority_flags(),
    }


def _sample_job() -> tuple[ResumableJobSpec, ResumableJobCheckpoint]:
    spec = ResumableJobSpec(
        job_id="fixture:job",
        job_type="historical_observation_partition",
        provider_id="fixture",
        partition_key="fixture/2026-01",
        start_at="2026-01-01T00:00:00+00:00",
        end_at="2026-01-31T23:59:59+00:00",
        max_attempts=3,
        rate_limit_class="fixture",
        origin_class=OriginClass.FIXTURE.value,
        idempotency_key="fixture:job:2026-01",
    )
    checkpoint = ResumableJobCheckpoint(
        job_id=spec.job_id,
        state="pending",
        attempt=0,
        cursor=None,
        completed_partition_count=0,
        record_count=0,
        last_checksum=None,
        updated_at=now_iso(),
    )
    return spec, checkpoint


def validate_research_boundary_bundle(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    provider = bundle.get("provider") if isinstance(bundle.get("provider"), dict) else {}
    storage = bundle.get("storage") if isinstance(bundle.get("storage"), dict) else {}
    research = bundle.get("research") if isinstance(bundle.get("research"), dict) else {}
    baseline = bundle.get("baseline") if isinstance(bundle.get("baseline"), dict) else {}
    if provider.get("protocol_count") != len(PROTOCOLS):
        errors.append("provider_protocol_count_mismatch")
    if provider.get("provider_call_count") != 0 or provider.get("provider_acquisition_started") is not False:
        errors.append("rf4_provider_acquisition_started")
    if storage.get("plane_count") != len(StoragePlane):
        errors.append("storage_plane_count_mismatch")
    if research.get("service_count") != len(RESEARCH_SERVICES):
        errors.append("research_service_count_mismatch")
    if research.get("forbidden_network_imports"):
        errors.append("pure_research_network_import_detected")
    if baseline.get("sample_contract_explicit") is not True:
        errors.append("local_sample_contract_not_explicit")
    if baseline.get("provider_backed_historical_acquisition") is not False:
        errors.append("local_baseline_mislabeled_provider_backed")
    if baseline.get("edge_promotion_allowed") is not False:
        errors.append("local_baseline_edge_promotion_allowed")
    if baseline.get("proof_eligible") is not False:
        errors.append("local_baseline_proof_eligible")
    spec, checkpoint = _sample_job()
    if not spec.idempotency_key or checkpoint.job_id != spec.job_id:
        errors.append("resumable_job_contract_invalid")
    for label, payload in (
        ("provider", provider),
        ("storage", storage),
        ("research", research),
        ("baseline", baseline),
    ):
        errors.extend(validate_authority(payload.get("authority", {}), prefix=label))
    return unique_errors(errors)


def validate_negative_research_boundary_probes(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    unsafe = {key: dict(value) if isinstance(value, dict) else value for key, value in bundle.items()}
    unsafe["provider"]["provider_call_count"] = 1
    unsafe["provider"]["provider_acquisition_started"] = True
    if "rf4_provider_acquisition_started" not in validate_research_boundary_bundle(unsafe):
        errors.append("rf4_provider_call_probe_not_rejected")

    promoted = {key: dict(value) if isinstance(value, dict) else value for key, value in bundle.items()}
    promoted["baseline"]["edge_promotion_allowed"] = True
    if "local_baseline_edge_promotion_allowed" not in validate_research_boundary_bundle(promoted):
        errors.append("rf4_local_promotion_probe_not_rejected")

    live = {key: dict(value) if isinstance(value, dict) else value for key, value in bundle.items()}
    live["research"]["authority"] = dict(live["research"]["authority"])
    live["research"]["authority"]["live_capital_enabled"] = True
    if "research_forbidden_true:live_capital_enabled" not in validate_research_boundary_bundle(live):
        errors.append("rf4_live_capital_probe_not_rejected")
    return unique_errors(errors)


def build_and_write_research_boundaries(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    provider = build_provider_protocol_registry()
    storage = build_storage_boundary_registry()
    research = build_research_boundary_audit()
    baseline = build_local_baseline_origin_audit(settings)
    bundle = {"provider": provider, "storage": storage, "research": research, "baseline": baseline}
    errors = validate_research_boundary_bundle(bundle)
    errors.extend(validate_negative_research_boundary_probes(bundle))
    errors = unique_errors(errors)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_research_boundaries_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "validation_errors": errors,
        "provider_protocol_count": len(PROTOCOLS),
        "storage_plane_count": len(StoragePlane),
        "research_service_count": len(RESEARCH_SERVICES),
        "provider_call_count": 0,
        "behavior_changed": False,
        "negative_probe_count": 3,
        "authority": authority_flags(),
    }
    store: AtomicArtifactStore[dict[str, Any]] = AtomicArtifactStore(runtime_dir(settings))
    store.write_json(PROVIDER_REGISTRY_ARTIFACT, provider)
    store.write_json(STORAGE_REGISTRY_ARTIFACT, storage)
    store.write_json(RESEARCH_AUDIT_ARTIFACT, research)
    store.write_json(BASELINE_ORIGIN_ARTIFACT, baseline)
    store.write_json(CHECK_ARTIFACT, checks)
    return bundle, checks, errors
