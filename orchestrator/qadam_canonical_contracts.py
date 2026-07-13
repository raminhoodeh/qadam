"""RF-3 canonical edge-path contracts and artifact ownership registry."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
import json
from pathlib import Path
from typing import Any, ClassVar, Generic, Iterable, TypeVar

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import (
    atomic_write_text,
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    unique_errors,
    validate_authority,
    write_json_atomic,
)

SCHEMA_VERSION = "qadam_canonical_contracts.v1"
PHASE_ID = "RF-3"

CONTRACT_REGISTRY_ARTIFACT = "qadam_contract_registry.json"
OWNERSHIP_REGISTRY_ARTIFACT = "qadam_artifact_ownership_registry.json"
MIGRATION_STATUS_ARTIFACT = "qadam_contract_migration_status.json"
COMPATIBILITY_AUDIT_ARTIFACT = "qadam_compatibility_reader_audit.json"
CHECK_ARTIFACT = "qadam_canonical_contracts_checks.json"


class OriginClass(StrEnum):
    QADAM_RUNTIME = "qadam_runtime"
    QADAM_ORIGIN_PAPER = "qadam_origin_paper"
    PROVIDER_CURRENT = "provider_current"
    PROVIDER_HISTORICAL = "provider_historical"
    BROKER_MIRROR = "broker_mirror"
    BACKTEST = "backtest"
    SHADOW = "shadow"
    FIXTURE = "fixture"
    SYNTHETIC = "synthetic"
    IMPORTED = "imported"
    OPERATOR = "operator"


NON_PROOF_ORIGINS = {
    OriginClass.QADAM_RUNTIME,
    OriginClass.PROVIDER_CURRENT,
    OriginClass.PROVIDER_HISTORICAL,
    OriginClass.BROKER_MIRROR,
    OriginClass.BACKTEST,
    OriginClass.SHADOW,
    OriginClass.FIXTURE,
    OriginClass.SYNTHETIC,
    OriginClass.IMPORTED,
    OriginClass.OPERATOR,
}


@dataclass(frozen=True, kw_only=True)
class CanonicalRecord:
    """Common immutable envelope for every canonical edge-path record."""

    record_type: ClassVar[str] = "CanonicalRecord"
    schema_version: ClassVar[str] = "qadam.CanonicalRecord.v1"

    record_id: str
    generated_at: str
    origin_class: str
    observed_at: str | None = None
    available_at: str | None = None
    decision_at: str | None = None
    public_safe: bool = True
    evidence_eligible: bool = False
    proof_eligible: bool = False
    authority: dict[str, bool | int] = field(default_factory=authority_flags)
    lineage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": self.record_type,
            "schema_version": self.schema_version,
            **asdict(self),
        }


@dataclass(frozen=True, kw_only=True)
class SourceEvent(CanonicalRecord):
    record_type: ClassVar[str] = "SourceEvent"
    schema_version: ClassVar[str] = "qadam.SourceEvent.v1"
    source_key: str = ""
    event_type: str = "observation"
    payload_hash: str = ""
    trust_state: str = "unscored"


@dataclass(frozen=True, kw_only=True)
class PriceEvidence(CanonicalRecord):
    record_type: ClassVar[str] = "PriceEvidence"
    schema_version: ClassVar[str] = "qadam.PriceEvidence.v1"
    instrument: str = ""
    provider: str = ""
    price: float | None = None
    currency: str = "USD"
    interval: str = "unknown"


@dataclass(frozen=True, kw_only=True)
class FeatureVector(CanonicalRecord):
    record_type: ClassVar[str] = "FeatureVector"
    schema_version: ClassVar[str] = "qadam.FeatureVector.v1"
    feature_set_version: str = ""
    instrument: str = ""
    features: dict[str, float | int | str | bool | None] = field(default_factory=dict)
    source_event_ids: tuple[str, ...] = ()


@dataclass(frozen=True, kw_only=True)
class PatternScore(CanonicalRecord):
    record_type: ClassVar[str] = "PatternScore"
    schema_version: ClassVar[str] = "qadam.PatternScore.v1"
    feature_vector_id: str = ""
    score_version: str = ""
    raw_score: float | None = None
    direction: str = "undetermined"
    strategy_fit: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class ForwardLabel(CanonicalRecord):
    record_type: ClassVar[str] = "ForwardLabel"
    schema_version: ClassVar[str] = "qadam.ForwardLabel.v1"
    pattern_score_id: str = ""
    horizon: str = ""
    gross_return: float | None = None
    net_return: float | None = None
    max_adverse_excursion: float | None = None
    label_available_at: str | None = None


@dataclass(frozen=True, kw_only=True)
class BacktestRun(CanonicalRecord):
    record_type: ClassVar[str] = "BacktestRun"
    schema_version: ClassVar[str] = "qadam.BacktestRun.v1"
    run_id: str = ""
    score_version: str = ""
    label_version: str = ""
    split_policy: str = "walk_forward"
    result_state: str = "research_only"


@dataclass(frozen=True, kw_only=True)
class EdgeRecord(CanonicalRecord):
    record_type: ClassVar[str] = "EdgeRecord"
    schema_version: ClassVar[str] = "qadam.EdgeRecord.v1"
    edge_id: str = ""
    edge_state: str = "candidate"
    backtest_run_ids: tuple[str, ...] = ()
    net_expectancy: float | None = None
    confidence_class: str = "unvalidated"


@dataclass(frozen=True, kw_only=True)
class StrategyHypothesis(CanonicalRecord):
    record_type: ClassVar[str] = "StrategyHypothesis"
    schema_version: ClassVar[str] = "qadam.StrategyHypothesis.v1"
    hypothesis_id: str = ""
    research_goal_id: str = ""
    edge_ids: tuple[str, ...] = ()
    instrument: str = ""
    direction: str = "undetermined"
    invalidation: str = ""
    expires_at: str | None = None


@dataclass(frozen=True, kw_only=True)
class AkberDecision(CanonicalRecord):
    record_type: ClassVar[str] = "AkberDecision"
    schema_version: ClassVar[str] = "qadam.AkberDecision.v1"
    setup_id: str = ""
    stage_states: dict[str, str] = field(default_factory=dict)
    final_state: str = "hold"
    missing_context: tuple[str, ...] = ()


@dataclass(frozen=True, kw_only=True)
class RiskDecision(CanonicalRecord):
    record_type: ClassVar[str] = "RiskDecision"
    schema_version: ClassVar[str] = "qadam.RiskDecision.v1"
    setup_id: str = ""
    final_state: str = "not_reviewed"
    max_loss: float | None = None
    risk_budget: float | None = None
    rejection_reasons: tuple[str, ...] = ()


@dataclass(frozen=True, kw_only=True)
class RouterDecision(CanonicalRecord):
    record_type: ClassVar[str] = "RouterDecision"
    schema_version: ClassVar[str] = "qadam.RouterDecision.v1"
    setup_id: str = ""
    final_state: str = "hold"
    hard_vetoes: tuple[str, ...] = ()
    soft_blockers: tuple[str, ...] = ()


@dataclass(frozen=True, kw_only=True)
class PaperOpsHandoff(CanonicalRecord):
    record_type: ClassVar[str] = "PaperOpsHandoff"
    schema_version: ClassVar[str] = "qadam.PaperOpsHandoff.v1"
    setup_id: str = ""
    research_goal_id: str = ""
    candidate_identity: str = ""
    idempotency_material: str = ""
    route: str = "guarded_alpaca_paper_only"
    handoff_state: str = "upstream_review_only"
    order_created: bool = False


@dataclass(frozen=True, kw_only=True)
class TradeLifecycle(CanonicalRecord):
    record_type: ClassVar[str] = "TradeLifecycle"
    schema_version: ClassVar[str] = "qadam.TradeLifecycle.v1"
    trade_id: str = ""
    lifecycle_state: str = "unknown"
    broker_order_id_hash: str | None = None
    complete_lineage: bool = False


@dataclass(frozen=True, kw_only=True)
class LearningAttribution(CanonicalRecord):
    record_type: ClassVar[str] = "LearningAttribution"
    schema_version: ClassVar[str] = "qadam.LearningAttribution.v1"
    subject_id: str = ""
    outcome_class: str = "unknown"
    component_attribution: dict[str, float | str] = field(default_factory=dict)
    proposal_only: bool = True


@dataclass(frozen=True, kw_only=True)
class RuntimeHealth(CanonicalRecord):
    record_type: ClassVar[str] = "RuntimeHealth"
    schema_version: ClassVar[str] = "qadam.RuntimeHealth.v1"
    component: str = ""
    health_state: str = "unknown"
    freshness_state: str = "unknown"
    blockers: tuple[str, ...] = ()


CONTRACT_CLASSES = (
    SourceEvent,
    PriceEvidence,
    FeatureVector,
    PatternScore,
    ForwardLabel,
    BacktestRun,
    EdgeRecord,
    StrategyHypothesis,
    AkberDecision,
    RiskDecision,
    RouterDecision,
    PaperOpsHandoff,
    TradeLifecycle,
    LearningAttribution,
    RuntimeHealth,
)

CANONICAL_OWNERS = {
    "SourceEvent": "orchestrator.qadam_research_boundaries",
    "PriceEvidence": "orchestrator.qadam_research_boundaries",
    "FeatureVector": "orchestrator.qadam_research_boundaries",
    "PatternScore": "orchestrator.qadam_research_boundaries",
    "ForwardLabel": "orchestrator.qadam_research_boundaries",
    "BacktestRun": "orchestrator.qadam_research_boundaries",
    "EdgeRecord": "orchestrator.qadam_research_boundaries",
    "StrategyHypothesis": "orchestrator.qadam_decision_execution_boundaries",
    "AkberDecision": "orchestrator.qadam_decision_execution_boundaries",
    "RiskDecision": "orchestrator.qadam_decision_execution_boundaries",
    "RouterDecision": "orchestrator.qadam_decision_execution_boundaries",
    "PaperOpsHandoff": "orchestrator.qadam_decision_execution_boundaries",
    "TradeLifecycle": "orchestrator.qadam_decision_execution_boundaries",
    "LearningAttribution": "orchestrator.qadam_decision_execution_boundaries",
    "RuntimeHealth": "orchestrator.qadam_refactor_baseline",
}

CANONICAL_ARTIFACTS = {
    contract.record_type: f"qadam_canonical_{contract.record_type.lower()}s.jsonl"
    for contract in CONTRACT_CLASSES
}

COMPATIBILITY_ARTIFACTS = {
    "SourceEvent": ["qadam_source_evidence_contracts.jsonl", "qsase_source_universe.json"],
    "PriceEvidence": ["qadam_price_evidence_contracts.jsonl", "qsase_trading_universe.json"],
    "FeatureVector": ["qsase_source_price_edges.jsonl"],
    "PatternScore": ["qadam_pattern_engine_v2_records.jsonl", "qsase_candidate_patterns.jsonl"],
    "ForwardLabel": ["qsase_historical_source_price_memory.jsonl"],
    "BacktestRun": ["qsase_baseline_backtest_results.jsonl"],
    "EdgeRecord": ["qsase_validated_edges.jsonl", "qsase_pattern_intelligence.json"],
    "StrategyHypothesis": ["qsase_strategy_hypotheses.jsonl"],
    "AkberDecision": ["qadam_akber_filter_v2_results.jsonl"],
    "RiskDecision": ["qsase_market_confirmation.json"],
    "RouterDecision": ["qadam_router_v2_decisions.jsonl"],
    "PaperOpsHandoff": ["qadam_paperops_handoff_v2_records.jsonl"],
    "TradeLifecycle": ["qadam_paper_lifecycle_v2_records.jsonl"],
    "LearningAttribution": ["qadam_learning_attribution_v2_records.jsonl"],
    "RuntimeHealth": ["qsase_dashboard_status.json", "qadam_self_healing_status.json"],
}

DEFENSE_IN_DEPTH_BOUNDARIES = (
    "source",
    "research",
    "strategy",
    "akber",
    "risk",
    "router",
    "paperops",
    "broker",
    "dashboard",
    "telegram",
    "proof",
    "dynamic_plan",
)


T = TypeVar("T", bound=dict[str, Any])


class AtomicArtifactStore(Generic[T]):
    """Atomic local artifact store with explicit runtime root confinement."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir.resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def path(self, name: str) -> Path:
        if Path(name).name != name:
            raise ValueError("artifact_name_must_be_basename")
        target = (self.base_dir / name).resolve()
        if target.parent != self.base_dir:
            raise ValueError("artifact_path_outside_store")
        return target

    def write_json(self, name: str, payload: T) -> Path:
        path = self.path(name)
        write_json_atomic(path, payload)
        return path

    def read_json(self, name: str) -> dict[str, Any]:
        return read_json(self.path(name))

    def write_jsonl(self, name: str, records: Iterable[dict[str, Any]]) -> Path:
        path = self.path(name)
        text = "".join(json.dumps(record, sort_keys=True, default=str) + "\n" for record in records)
        atomic_write_text(path, text)
        return path

    def read_jsonl(self, name: str) -> list[dict[str, Any]]:
        return read_jsonl(self.path(name))


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def validate_canonical_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    record_type = record.get("record_type")
    contract_class = next(
        (contract for contract in CONTRACT_CLASSES if contract.record_type == record_type),
        None,
    )
    if contract_class is None:
        errors.append("canonical_record_type_unknown")
        return errors
    if record.get("schema_version") != contract_class.schema_version:
        errors.append("canonical_record_schema_mismatch")
    if not str(record.get("record_id") or "").strip():
        errors.append("canonical_record_id_missing")
    if _parse_timestamp(record.get("generated_at")) is None:
        errors.append("canonical_generated_at_invalid")
    try:
        origin = OriginClass(str(record.get("origin_class")))
    except ValueError:
        errors.append("canonical_origin_class_invalid")
        origin = None
    available_at = _parse_timestamp(record.get("available_at"))
    decision_at = _parse_timestamp(record.get("decision_at"))
    if available_at and decision_at and available_at > decision_at:
        errors.append("canonical_future_information_leakage")
    if origin in NON_PROOF_ORIGINS and record.get("proof_eligible") is not False:
        errors.append(f"canonical_nonproof_origin_proof_eligible:{origin.value}")
    if record.get("proof_eligible") is True:
        if origin != OriginClass.QADAM_ORIGIN_PAPER:
            errors.append("canonical_proof_origin_invalid")
        if record_type != "TradeLifecycle":
            errors.append("canonical_proof_record_type_invalid")
        if record.get("lifecycle_state") != "closed":
            errors.append("canonical_proof_trade_not_closed")
        if record.get("complete_lineage") is not True:
            errors.append("canonical_proof_lineage_incomplete")
    if record_type == "PaperOpsHandoff" and record.get("order_created") is not False:
        errors.append("canonical_handoff_created_order")
    if record_type == "LearningAttribution" and record.get("proposal_only") is not True:
        errors.append("canonical_learning_not_proposal_only")
    errors.extend(validate_authority(record.get("authority", {}), prefix="canonical_record"))
    return unique_errors(errors)


def sample_records() -> list[dict[str, Any]]:
    generated_at = now_iso()
    records: list[dict[str, Any]] = []
    for contract in CONTRACT_CLASSES:
        kwargs: dict[str, Any] = {
            "record_id": f"sample:{contract.record_type}",
            "generated_at": generated_at,
            "origin_class": OriginClass.FIXTURE.value,
            "observed_at": generated_at,
            "available_at": generated_at,
            "decision_at": generated_at,
            "evidence_eligible": False,
            "proof_eligible": False,
        }
        records.append(contract(**kwargs).to_dict())
    return records


def build_contract_registry() -> dict[str, Any]:
    contracts = []
    for contract in CONTRACT_CLASSES:
        contracts.append(
            {
                "record_type": contract.record_type,
                "schema_version": contract.schema_version,
                "canonical_owner": CANONICAL_OWNERS[contract.record_type],
                "canonical_artifact": CANONICAL_ARTIFACTS[contract.record_type],
                "compatibility_artifacts": COMPATIBILITY_ARTIFACTS[contract.record_type],
                "immutable": True,
                "origin_class_required": True,
                "authority_validation_required": True,
                "validator": "orchestrator.qadam_canonical_contracts.validate_canonical_record",
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_contract_registry",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "canonical_contracts_registered",
        "contract_count": len(contracts),
        "contracts": contracts,
        "origin_classes": [origin.value for origin in OriginClass],
        "defense_in_depth_boundaries": list(DEFENSE_IN_DEPTH_BOUNDARIES),
        "authority": authority_flags(),
    }


def build_ownership_registry() -> dict[str, Any]:
    records = [
        {
            "record_type": record_type,
            "canonical_owner": CANONICAL_OWNERS[record_type],
            "canonical_artifact": CANONICAL_ARTIFACTS[record_type],
            "owner_count": 1,
            "compatibility_reader_required": True,
            "compatibility_artifacts": COMPATIBILITY_ARTIFACTS[record_type],
            "legacy_producer_may_write_canonical_artifact": False,
        }
        for record_type in sorted(CANONICAL_OWNERS)
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_artifact_ownership_registry",
        "generated_at": now_iso(),
        "status": "single_canonical_owner_declared",
        "record_type_count": len(records),
        "ownership_conflict_count": sum(record["owner_count"] != 1 for record in records),
        "records": records,
        "authority": authority_flags(),
    }


def build_compatibility_audit(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    records: list[dict[str, Any]] = []
    for record_type, artifacts in COMPATIBILITY_ARTIFACTS.items():
        for artifact in artifacts:
            records.append(
                {
                    "record_type": record_type,
                    "artifact": f"data/runtime/{artifact}",
                    "exists": (runtime / artifact).exists(),
                    "reader_state": "declared_compatibility_reader",
                    "canonical_write_allowed": False,
                    "proof_inference_allowed": False,
                    "removal_allowed": False,
                }
            )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_compatibility_reader_audit",
        "generated_at": now_iso(),
        "status": "compatibility_readers_declared",
        "record_count": len(records),
        "present_artifact_count": sum(record["exists"] for record in records),
        "missing_artifact_count": sum(not record["exists"] for record in records),
        "records": records,
        "authority": authority_flags(),
    }


def build_migration_status(compatibility: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_contract_migration_status",
        "generated_at": now_iso(),
        "status": "compatibility_layer_active_no_behavior_change",
        "canonical_contract_count": len(CONTRACT_CLASSES),
        "canonical_producer_activation_count": 0,
        "compatibility_reader_count": compatibility["record_count"],
        "legacy_artifact_deletion_count": 0,
        "existing_behavior_changed": False,
        "next_phase": "RF-4_provider_storage_and_research_boundaries",
        "authority": authority_flags(),
    }


def validate_contract_bundle(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    registry = bundle.get("registry") if isinstance(bundle.get("registry"), dict) else {}
    ownership = bundle.get("ownership") if isinstance(bundle.get("ownership"), dict) else {}
    compatibility = (
        bundle.get("compatibility") if isinstance(bundle.get("compatibility"), dict) else {}
    )
    migration = bundle.get("migration") if isinstance(bundle.get("migration"), dict) else {}
    if registry.get("contract_count") != len(CONTRACT_CLASSES):
        errors.append("canonical_contract_count_mismatch")
    if ownership.get("record_type_count") != len(CONTRACT_CLASSES):
        errors.append("ownership_record_count_mismatch")
    if ownership.get("ownership_conflict_count") != 0:
        errors.append("canonical_ownership_conflict")
    owner_records = ownership.get("records") if isinstance(ownership.get("records"), list) else []
    canonical_artifacts = [record.get("canonical_artifact") for record in owner_records]
    if len(canonical_artifacts) != len(set(canonical_artifacts)):
        errors.append("canonical_artifact_name_collision")
    if migration.get("canonical_producer_activation_count") != 0:
        errors.append("rf3_canonical_producer_activated_early")
    if migration.get("legacy_artifact_deletion_count") != 0:
        errors.append("rf3_legacy_artifact_deleted")
    for record in sample_records():
        errors.extend(validate_canonical_record(record))
    for label, payload in (
        ("registry", registry),
        ("ownership", ownership),
        ("compatibility", compatibility),
        ("migration", migration),
    ):
        errors.extend(validate_authority(payload.get("authority", {}), prefix=label))
    return unique_errors(errors)


def validate_negative_contract_probes() -> list[str]:
    errors: list[str] = []
    base = sample_records()[0]

    unsafe = dict(base)
    unsafe["authority"] = dict(unsafe["authority"])
    unsafe["authority"]["live_capital_enabled"] = True
    if "canonical_record_forbidden_true:live_capital_enabled" not in validate_canonical_record(
        unsafe
    ):
        errors.append("rf3_live_capital_probe_not_rejected")

    leakage = dict(base)
    leakage["available_at"] = "2026-01-02T00:00:00+00:00"
    leakage["decision_at"] = "2026-01-01T00:00:00+00:00"
    if "canonical_future_information_leakage" not in validate_canonical_record(leakage):
        errors.append("rf3_leakage_probe_not_rejected")

    proof = dict(base)
    proof["proof_eligible"] = True
    if not any(
        error.startswith("canonical_nonproof_origin_proof_eligible")
        for error in validate_canonical_record(proof)
    ):
        errors.append("rf3_fixture_proof_probe_not_rejected")

    handoff = PaperOpsHandoff(
        record_id="probe:handoff",
        generated_at=now_iso(),
        origin_class=OriginClass.FIXTURE.value,
        order_created=True,
    ).to_dict()
    if "canonical_handoff_created_order" not in validate_canonical_record(handoff):
        errors.append("rf3_handoff_order_probe_not_rejected")
    return unique_errors(errors)


def build_and_write_canonical_contracts(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store: AtomicArtifactStore[dict[str, Any]] = AtomicArtifactStore(runtime)
    registry = build_contract_registry()
    ownership = build_ownership_registry()
    compatibility = build_compatibility_audit(settings)
    migration = build_migration_status(compatibility)
    bundle = {
        "registry": registry,
        "ownership": ownership,
        "compatibility": compatibility,
        "migration": migration,
    }
    errors = validate_contract_bundle(bundle)
    errors.extend(validate_negative_contract_probes())
    errors = unique_errors(errors)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_canonical_contracts_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "validation_errors": errors,
        "canonical_contract_count": len(CONTRACT_CLASSES),
        "ownership_conflict_count": ownership["ownership_conflict_count"],
        "negative_probe_count": 4,
        "compatibility_layer_active": True,
        "behavior_changed": False,
        "authority": authority_flags(),
    }
    store.write_json(CONTRACT_REGISTRY_ARTIFACT, registry)
    store.write_json(OWNERSHIP_REGISTRY_ARTIFACT, ownership)
    store.write_json(MIGRATION_STATUS_ARTIFACT, migration)
    store.write_json(COMPATIBILITY_AUDIT_ARTIFACT, compatibility)
    store.write_json(CHECK_ARTIFACT, checks)
    return bundle, checks, errors
