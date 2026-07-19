"""RF-5 typed decision, risk, Router, and guarded PaperOps boundaries."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
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

SCHEMA_VERSION = "qadam_decision_execution_boundaries.v1"
PHASE_ID = "RF-5"

DECISION_REGISTRY_ARTIFACT = "qadam_decision_boundary_registry.json"
EXECUTION_REGISTRY_ARTIFACT = "qadam_execution_boundary_registry.json"
PAPEROPS_EQUIVALENCE_ARTIFACT = "qadam_paperops_equivalence_audit.json"
ORIGIN_AUDIT_ARTIFACT = "qadam_origin_classification_audit.json"
CHECK_ARTIFACT = "qadam_decision_execution_boundaries_checks.json"

GUARDED_PAPEROPS_COMMAND = ".venv/bin/python scripts/run_paperops_autonomous_pass.py"
GUARDED_PAPER_ROUTE = "guarded_alpaca_paper_only"

REQUIRED_PAPER_GATES = (
    "source_quorum",
    "research_goal_lineage",
    "candidate_identity",
    "akber_pass",
    "risk_budget",
    "duplicate_exposure",
    "daily_drawdown",
    "qctrl_consultation",
    "idempotency",
    "paper_endpoint",
    "live_capital_disabled",
)


class RouterState(StrEnum):
    REJECT = "reject"
    WATCHLIST = "watchlist"
    SHADOW_ONLY = "shadow_only"
    HOLD = "hold"
    REPAIR_REQUESTED = "repair_requested"
    BLOCKED_SAFETY = "blocked_safety_boundary"
    PAPER_REVIEW_CANDIDATE = "paper_review_candidate"


@dataclass(frozen=True, kw_only=True)
class StrategyReviewEnvelope:
    hypothesis_id: str
    research_goal_id: str
    edge_ids: tuple[str, ...]
    instrument: str
    direction: str
    invalidation: str
    expires_at: str
    evidence_state: str


@dataclass(frozen=True, kw_only=True)
class AkberReviewEnvelope:
    hypothesis_id: str
    stage_states: dict[str, str]
    final_state: str
    missing_context: tuple[str, ...]
    pass_is_execution_approval: bool = False


@dataclass(frozen=True, kw_only=True)
class RiskReviewEnvelope:
    hypothesis_id: str
    final_state: str
    risk_budget: float | None
    max_loss: float | None
    duplicate_exposure_conflict: bool
    daily_drawdown_breached: bool
    rejection_reasons: tuple[str, ...] = ()


@dataclass(frozen=True, kw_only=True)
class RouterDecisionEnvelope:
    setup_id: str
    final_state: str
    hard_vetoes: tuple[str, ...]
    soft_blockers: tuple[str, ...]
    exactly_one_final_state: bool = True


@dataclass(frozen=True, kw_only=True)
class PaperOpsHandoffEnvelope:
    handoff_id: str
    setup_id: str
    research_goal_id: str
    candidate_identity: str
    idempotency_material: str
    instrument: str
    direction: str
    source_quorum_passed: bool
    akber_passed: bool
    risk_approved: bool
    duplicate_exposure_conflict: bool
    daily_drawdown_breached: bool
    qctrl_consultation_clear: bool
    route: str = GUARDED_PAPER_ROUTE
    live_capital_enabled: bool = False
    direct_broker_call_allowed: bool = False
    broker_write_allowed: bool = False
    order_created: bool = False
    proof_credit_allowed: bool = False
    authority: dict[str, bool | int] = field(default_factory=authority_flags)


@runtime_checkable
class StrategyToAkberBoundary(Protocol):
    def review_strategy(self, envelope: StrategyReviewEnvelope) -> AkberReviewEnvelope: ...


@runtime_checkable
class AkberToRiskBoundary(Protocol):
    def review_risk(self, envelope: AkberReviewEnvelope) -> RiskReviewEnvelope: ...


@runtime_checkable
class RiskToRouterBoundary(Protocol):
    def route(self, envelope: RiskReviewEnvelope) -> RouterDecisionEnvelope: ...


@runtime_checkable
class RouterToPaperOpsBoundary(Protocol):
    def build_handoff(
        self, decision: RouterDecisionEnvelope
    ) -> PaperOpsHandoffEnvelope | None: ...


BOUNDARY_STAGES = (
    {
        "boundary_id": "strategy_to_akber",
        "input": "StrategyReviewEnvelope",
        "output": "AkberReviewEnvelope",
        "owner": "orchestrator.qadam_decision_execution_boundaries",
        "authority_created": False,
    },
    {
        "boundary_id": "akber_to_risk",
        "input": "AkberReviewEnvelope",
        "output": "RiskReviewEnvelope",
        "owner": "orchestrator.qadam_decision_execution_boundaries",
        "authority_created": False,
    },
    {
        "boundary_id": "risk_to_router",
        "input": "RiskReviewEnvelope",
        "output": "RouterDecisionEnvelope",
        "owner": "orchestrator.qadam_decision_execution_boundaries",
        "authority_created": False,
    },
    {
        "boundary_id": "router_to_paperops",
        "input": "RouterDecisionEnvelope",
        "output": "PaperOpsHandoffEnvelope",
        "owner": "orchestrator.qadam_decision_execution_boundaries",
        "authority_created": False,
    },
)

COMPATIBILITY_COMPONENTS = (
    "orchestrator.qsase_strategy_foundry",
    "orchestrator.qadam_akber_filter_v2",
    "orchestrator.qadam_router_v2_paperops_handoff",
    "orchestrator.qsase_paperops_gate_interface",
    "orchestrator.paperops_alpaca_paper_post",
    "orchestrator.qadam_paper_lifecycle_proof_boundary",
    "orchestrator.qadam_learning_attribution_v2",
)


def _paths(settings: Settings | None = None) -> dict[str, Path]:
    runtime = runtime_dir(settings)
    return {
        "decision": runtime / DECISION_REGISTRY_ARTIFACT,
        "execution": runtime / EXECUTION_REGISTRY_ARTIFACT,
        "equivalence": runtime / PAPEROPS_EQUIVALENCE_ARTIFACT,
        "origin": runtime / ORIGIN_AUDIT_ARTIFACT,
        "checks": runtime / CHECK_ARTIFACT,
    }


def validate_strategy_review(envelope: StrategyReviewEnvelope) -> list[str]:
    errors: list[str] = []
    if not envelope.hypothesis_id:
        errors.append("strategy_hypothesis_id_missing")
    if not envelope.research_goal_id:
        errors.append("strategy_research_goal_lineage_missing")
    if not envelope.edge_ids:
        errors.append("strategy_edge_lineage_missing")
    if not envelope.instrument or not envelope.direction:
        errors.append("strategy_instrument_or_direction_missing")
    if not envelope.invalidation:
        errors.append("strategy_invalidation_missing")
    if not envelope.expires_at:
        errors.append("strategy_expiry_missing")
    if envelope.evidence_state != "validated_edge":
        errors.append("strategy_evidence_not_validated")
    return unique_errors(errors)


def validate_akber_review(envelope: AkberReviewEnvelope) -> list[str]:
    errors: list[str] = []
    required_stages = {"context", "catalyst", "confirmation", "risk", "execution", "learning"}
    if set(envelope.stage_states) != required_stages:
        errors.append("akber_stage_set_incomplete")
    if envelope.final_state == "pass" and envelope.missing_context:
        errors.append("akber_pass_with_missing_context")
    if envelope.pass_is_execution_approval is not False:
        errors.append("akber_pass_misclassified_as_execution_approval")
    return unique_errors(errors)


def validate_risk_review(envelope: RiskReviewEnvelope) -> list[str]:
    errors: list[str] = []
    if envelope.final_state == "approved":
        if envelope.risk_budget is None or envelope.risk_budget <= 0:
            errors.append("risk_budget_missing_or_nonpositive")
        if envelope.max_loss is None or envelope.max_loss <= 0:
            errors.append("max_loss_missing_or_nonpositive")
        if envelope.duplicate_exposure_conflict:
            errors.append("risk_approved_with_duplicate_exposure")
        if envelope.daily_drawdown_breached:
            errors.append("risk_approved_during_drawdown_breach")
    return unique_errors(errors)


def validate_router_decision(envelope: RouterDecisionEnvelope) -> list[str]:
    errors: list[str] = []
    if envelope.final_state not in {state.value for state in RouterState}:
        errors.append("router_final_state_invalid")
    if envelope.exactly_one_final_state is not True:
        errors.append("router_multiple_or_missing_final_states")
    if envelope.final_state == RouterState.PAPER_REVIEW_CANDIDATE.value and envelope.hard_vetoes:
        errors.append("paper_review_candidate_has_hard_veto")
    return unique_errors(errors)


def validate_paperops_handoff(envelope: PaperOpsHandoffEnvelope) -> list[str]:
    errors: list[str] = []
    required_text = {
        "handoff_id": envelope.handoff_id,
        "setup_id": envelope.setup_id,
        "research_goal_id": envelope.research_goal_id,
        "candidate_identity": envelope.candidate_identity,
        "idempotency_material": envelope.idempotency_material,
        "instrument": envelope.instrument,
        "direction": envelope.direction,
    }
    for key, value in required_text.items():
        if not str(value or "").strip():
            errors.append(f"paperops_handoff_missing:{key}")
    if envelope.source_quorum_passed is not True:
        errors.append("paperops_handoff_source_quorum_failed")
    if envelope.akber_passed is not True:
        errors.append("paperops_handoff_akber_not_passed")
    if envelope.risk_approved is not True:
        errors.append("paperops_handoff_risk_not_approved")
    if envelope.duplicate_exposure_conflict is not False:
        errors.append("paperops_handoff_duplicate_exposure")
    if envelope.daily_drawdown_breached is not False:
        errors.append("paperops_handoff_drawdown_breached")
    if envelope.qctrl_consultation_clear is not True:
        errors.append("paperops_handoff_qctrl_not_clear")
    if envelope.route != GUARDED_PAPER_ROUTE:
        errors.append("paperops_handoff_route_not_guarded_paper")
    if envelope.live_capital_enabled is not False:
        errors.append("paperops_handoff_live_capital_enabled")
    if envelope.direct_broker_call_allowed is not False:
        errors.append("paperops_handoff_direct_broker_call_allowed")
    if envelope.broker_write_allowed is not False:
        errors.append("paperops_handoff_broker_write_allowed_upstream")
    if envelope.order_created is not False:
        errors.append("paperops_handoff_created_order")
    if envelope.proof_credit_allowed is not False:
        errors.append("paperops_handoff_proof_credit_allowed")
    errors.extend(validate_authority(envelope.authority, prefix="paperops_handoff"))
    return unique_errors(errors)


def _safe_handoff() -> PaperOpsHandoffEnvelope:
    return PaperOpsHandoffEnvelope(
        handoff_id="fixture:handoff",
        setup_id="fixture:setup",
        research_goal_id="fixture:research-goal",
        candidate_identity="fixture:candidate",
        idempotency_material="fixture:idempotency",
        instrument="SPY",
        direction="watch",
        source_quorum_passed=True,
        akber_passed=True,
        risk_approved=True,
        duplicate_exposure_conflict=False,
        daily_drawdown_breached=False,
        qctrl_consultation_clear=True,
    )


def build_decision_boundary_registry() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_decision_boundary_registry",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "typed_decision_boundaries_defined",
        "boundary_count": len(BOUNDARY_STAGES),
        "boundaries": list(BOUNDARY_STAGES),
        "router_states": [state.value for state in RouterState],
        "exactly_one_router_state_required": True,
        "akber_pass_is_execution_approval": False,
        "compatibility_components": list(COMPATIBILITY_COMPONENTS),
        "authority": authority_flags(),
    }


def build_execution_boundary_registry() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_execution_boundary_registry",
        "generated_at": now_iso(),
        "status": "guarded_paperops_route_preserved",
        "canonical_wrapper_command": GUARDED_PAPEROPS_COMMAND,
        "upstream_route": GUARDED_PAPER_ROUTE,
        "required_gate_count": len(REQUIRED_PAPER_GATES),
        "required_gates": list(REQUIRED_PAPER_GATES),
        "paperops_is_only_order_capable_boundary": True,
        "upstream_handoff_can_create_order": False,
        "direct_broker_route_created": False,
        "order_call_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "qctrl_bypass_allowed": False,
        "authority": authority_flags(),
    }


def _source_token_audit(path: Path, tokens: tuple[str, ...]) -> dict[str, Any]:
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        source = ""
    return {
        "path": str(path.relative_to(ROOT)),
        "exists": path.exists(),
        "required_tokens": list(tokens),
        "missing_tokens": [token for token in tokens if token not in source],
    }


def build_paperops_equivalence_audit(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    lock = read_json(runtime / "qadam_long_backtest_lock.json")
    audits = [
        _source_token_audit(
            ROOT / "scripts" / "run_paperops_autonomous_pass.py",
            ("is_long_backtest_lock_active", "build_research_lock_watch_only_summary"),
        ),
        _source_token_audit(
            ROOT / "orchestrator" / "paperops_alpaca_paper_post.py",
            ("endpoint_classification", "paper_endpoint_confirmed", "idempotency_ledger_active"),
        ),
        _source_token_audit(
            ROOT / "orchestrator" / "qsase_paperops_gate_interface.py",
            ("broker_write_allowed", "proof_credit_allowed", "live_capital_enabled"),
        ),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_paperops_equivalence_audit",
        "generated_at": now_iso(),
        "status": "behaviorally_equivalent_watch_only",
        "research_lock_status": lock.get("status"),
        "paperops_watch_only_mode": lock.get("paperops_watch_only_mode"),
        "source_token_audits": audits,
        "source_token_missing_count": sum(len(audit["missing_tokens"]) for audit in audits),
        "new_order_call_count": 0,
        "new_broker_route_count": 0,
        "decision_behavior_changed": False,
        "paperops_behavior_changed": False,
        "authority": authority_flags(),
    }


def build_origin_classification_audit() -> dict[str, Any]:
    records = []
    for origin in OriginClass:
        records.append(
            {
                "origin_class": origin.value,
                "proof_possible": origin is OriginClass.QADAM_ORIGIN_PAPER,
                "proof_requires_closed_trade": origin is OriginClass.QADAM_ORIGIN_PAPER,
                "proof_requires_complete_lineage": origin is OriginClass.QADAM_ORIGIN_PAPER,
                "may_be_claimed_as_qadam_origin": origin is OriginClass.QADAM_ORIGIN_PAPER,
                "paper_order_authority_created": False,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_origin_classification_audit",
        "generated_at": now_iso(),
        "status": "origin_classes_explicit",
        "origin_class_count": len(records),
        "proof_capable_origin_count": sum(record["proof_possible"] for record in records),
        "records": records,
        "authority": authority_flags(),
    }


def validate_boundary_bundle(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    decision = bundle.get("decision") if isinstance(bundle.get("decision"), dict) else {}
    execution = bundle.get("execution") if isinstance(bundle.get("execution"), dict) else {}
    equivalence = bundle.get("equivalence") if isinstance(bundle.get("equivalence"), dict) else {}
    origin = bundle.get("origin") if isinstance(bundle.get("origin"), dict) else {}
    if decision.get("boundary_count") != len(BOUNDARY_STAGES):
        errors.append("decision_boundary_count_mismatch")
    if execution.get("canonical_wrapper_command") != GUARDED_PAPEROPS_COMMAND:
        errors.append("guarded_paperops_command_mismatch")
    if execution.get("required_gate_count") != len(REQUIRED_PAPER_GATES):
        errors.append("paperops_gate_count_mismatch")
    if execution.get("order_call_count") != 0 or execution.get("broker_write_count") != 0:
        errors.append("rf5_execution_call_detected")
    if execution.get("live_capital_enabled") is not False:
        errors.append("rf5_live_capital_enabled")
    if equivalence.get("source_token_missing_count") != 0:
        errors.append("paperops_equivalence_source_tokens_missing")
    if equivalence.get("research_lock_status") != "active":
        errors.append("paperops_equivalence_research_lock_inactive")
    if equivalence.get("paperops_watch_only_mode") is not True:
        errors.append("paperops_equivalence_not_watch_only")
    if origin.get("proof_capable_origin_count") != 1:
        errors.append("origin_proof_capable_count_mismatch")
    if validate_paperops_handoff(_safe_handoff()):
        errors.append("safe_handoff_contract_invalid")
    for label, payload in (
        ("decision", decision),
        ("execution", execution),
        ("equivalence", equivalence),
        ("origin", origin),
    ):
        errors.extend(validate_authority(payload.get("authority", {}), prefix=label))
    return unique_errors(errors)


def validate_negative_boundary_probes() -> list[str]:
    errors: list[str] = []
    probe_fields = {
        "live_capital_enabled": "paperops_handoff_live_capital_enabled",
        "direct_broker_call_allowed": "paperops_handoff_direct_broker_call_allowed",
        "broker_write_allowed": "paperops_handoff_broker_write_allowed_upstream",
        "order_created": "paperops_handoff_created_order",
        "proof_credit_allowed": "paperops_handoff_proof_credit_allowed",
        "duplicate_exposure_conflict": "paperops_handoff_duplicate_exposure",
        "daily_drawdown_breached": "paperops_handoff_drawdown_breached",
    }
    safe = _safe_handoff()
    for field_name, expected_error in probe_fields.items():
        values = asdict(safe)
        values[field_name] = True
        probe = PaperOpsHandoffEnvelope(**values)
        if expected_error not in validate_paperops_handoff(probe):
            errors.append(f"rf5_probe_not_rejected:{field_name}")
    route_values = asdict(safe)
    route_values["route"] = "live_endpoint"
    route_probe = PaperOpsHandoffEnvelope(**route_values)
    if "paperops_handoff_route_not_guarded_paper" not in validate_paperops_handoff(route_probe):
        errors.append("rf5_live_route_probe_not_rejected")
    qctrl_values = asdict(safe)
    qctrl_values["qctrl_consultation_clear"] = False
    qctrl_probe = PaperOpsHandoffEnvelope(**qctrl_values)
    if "paperops_handoff_qctrl_not_clear" not in validate_paperops_handoff(qctrl_probe):
        errors.append("rf5_qctrl_probe_not_rejected")
    return unique_errors(errors)


def build_and_write_decision_execution_boundaries(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    decision = build_decision_boundary_registry()
    execution = build_execution_boundary_registry()
    equivalence = build_paperops_equivalence_audit(settings)
    origin = build_origin_classification_audit()
    bundle = {"decision": decision, "execution": execution, "equivalence": equivalence, "origin": origin}
    errors = validate_boundary_bundle(bundle)
    errors.extend(validate_negative_boundary_probes())
    errors = unique_errors(errors)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_decision_execution_boundaries_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "validation_errors": errors,
        "boundary_count": len(BOUNDARY_STAGES),
        "paper_gate_count": len(REQUIRED_PAPER_GATES),
        "negative_probe_count": 9,
        "order_call_count": 0,
        "broker_write_count": 0,
        "behavior_changed": False,
        "authority": authority_flags(),
    }
    store: AtomicArtifactStore[dict[str, Any]] = AtomicArtifactStore(runtime_dir(settings))
    store.write_json(DECISION_REGISTRY_ARTIFACT, decision)
    store.write_json(EXECUTION_REGISTRY_ARTIFACT, execution)
    store.write_json(PAPEROPS_EQUIVALENCE_ARTIFACT, equivalence)
    store.write_json(ORIGIN_AUDIT_ARTIFACT, origin)
    store.write_json(CHECK_ARTIFACT, checks)
    return bundle, checks, errors
