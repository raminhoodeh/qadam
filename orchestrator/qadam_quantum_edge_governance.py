"""Wave A governance contract for Qadam's hybrid quantum discovery loop."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings

SCHEMA_VERSION = "qadam_quantum_edge_governance.v1"
CANDIDATE_SCHEMA_VERSION = "qadam.QuantumResearchCandidate.v1"
ARTIFACT_NAME = "qadam_quantum_edge_governance.json"
WAVE_ID = "quantum_edge_wave_a"

DISCOVERY_ORIGINS = (
    "classical_discovery",
    "quantum_assisted_discovery",
    "joint_discovery",
)

VALIDATION_CONTRIBUTIONS = (
    "not_tested",
    "quantum_strengthened",
    "joint_corroboration",
    "classical_preferred",
    "weakened",
    "inconclusive",
    "not_measurable",
    "failed_safely",
)

CURRENT_PUBLIC_LABELS = {
    "findings": "Pattern Discovery",
    "nonlinear": "Quantum Review",
    "strategies": "Trading Strategies",
}

TARGET_PUBLIC_LABELS = {
    "findings": "Pattern Recognition",
    "nonlinear": "Quantum Edge",
    "strategies": "Trading Strategies",
}

ROUTE_CONTRACT = {
    "findings": "patterns/findings",
    "nonlinear": "patterns/nonlinear",
    "strategies": "decide/strategies",
}

RESEARCH_CAPABILITY_FIELD = "quantum_research_candidate_allowed"
ZERO_AUTHORITY_FIELDS = (
    "quantum_self_validation_allowed",
    "validated_edge_creation_allowed",
    "strategy_hypothesis_creation_allowed",
    "trade_candidate_creation_allowed",
    "risk_approval_allowed",
    "position_sizing_allowed",
    "execution_approval_allowed",
    "execution_allowed",
    "paper_order_allowed",
    "direct_broker_call_allowed",
    "broker_write_allowed",
    "proof_credit_allowed",
    "paper_proof_ledger_credit_allowed",
    "live_capital_enabled",
    "dashboard_command_authority",
    "telegram_command_authority",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def quantum_research_authority() -> dict[str, bool]:
    """Return the only Wave A authority shape allowed for quantum discovery."""

    return {
        RESEARCH_CAPABILITY_FIELD: True,
        **{field_name: False for field_name in ZERO_AUTHORITY_FIELDS},
    }


@dataclass(frozen=True, kw_only=True)
class QuantumResearchCandidate:
    """Research-only envelope emitted by a future quantum discovery backend."""

    candidate_id: str
    source_manifest_id: str
    target_market: str
    research_question: str
    generated_at: str
    discovery_origin: str = "quantum_assisted_discovery"
    validation_contribution: str = "not_tested"
    lifecycle_state: str = "candidate_relationship"
    public_safe: bool = True
    evidence_eligible: bool = False
    proof_eligible: bool = False
    strategy_hypothesis_created: bool = False
    trade_candidate_created: bool = False
    paper_order_created: bool = False
    authority: dict[str, bool] = field(default_factory=quantum_research_authority)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CANDIDATE_SCHEMA_VERSION,
            **asdict(self),
        }


def validate_quantum_research_candidate(
    candidate: QuantumResearchCandidate | dict[str, Any],
) -> list[str]:
    payload = candidate.to_dict() if isinstance(candidate, QuantumResearchCandidate) else candidate
    errors: list[str] = []

    for field_name in (
        "candidate_id",
        "source_manifest_id",
        "target_market",
        "research_question",
        "generated_at",
    ):
        if not str(payload.get(field_name) or "").strip():
            errors.append(f"quantum_candidate_missing:{field_name}")

    if payload.get("schema_version") != CANDIDATE_SCHEMA_VERSION:
        errors.append("quantum_candidate_schema_invalid")
    if payload.get("discovery_origin") != "quantum_assisted_discovery":
        errors.append("quantum_candidate_origin_invalid")
    if payload.get("validation_contribution") != "not_tested":
        errors.append("quantum_candidate_cannot_self_validate")
    if payload.get("lifecycle_state") != "candidate_relationship":
        errors.append("quantum_candidate_lifecycle_invalid")
    if payload.get("public_safe") is not True:
        errors.append("quantum_candidate_not_public_safe")
    if payload.get("evidence_eligible") is not False:
        errors.append("quantum_candidate_evidence_eligibility_escalated")
    if payload.get("proof_eligible") is not False:
        errors.append("quantum_candidate_proof_eligibility_escalated")
    for field_name in (
        "strategy_hypothesis_created",
        "trade_candidate_created",
        "paper_order_created",
    ):
        if payload.get(field_name) is not False:
            errors.append(f"quantum_candidate_created_downstream_state:{field_name}")

    authority = payload.get("authority")
    if not isinstance(authority, dict):
        errors.append("quantum_candidate_authority_missing")
        return sorted(set(errors))

    if authority.get(RESEARCH_CAPABILITY_FIELD) is not True:
        errors.append("quantum_candidate_research_capability_missing")
    for field_name in ZERO_AUTHORITY_FIELDS:
        if authority.get(field_name) is not False:
            errors.append(f"quantum_candidate_authority_escalated:{field_name}")
    unexpected_true = sorted(
        key
        for key, value in authority.items()
        if value is True and key != RESEARCH_CAPABILITY_FIELD
    )
    if unexpected_true:
        errors.append(
            "quantum_candidate_unrecognized_true_authority:"
            + ",".join(unexpected_true)
        )
    return sorted(set(errors))


def sample_quantum_research_candidate() -> QuantumResearchCandidate:
    return QuantumResearchCandidate(
        candidate_id="quantum-research-candidate:contract-sample",
        source_manifest_id="quantum-discovery-manifest:contract-sample",
        target_market="contract-only",
        research_question="Can a bounded quantum representation originate a research relationship?",
        generated_at=now_iso(),
    )


def build_quantum_edge_governance() -> dict[str, Any]:
    sample = sample_quantum_research_candidate()
    sample_errors = validate_quantum_research_candidate(sample)
    return {
        "schema_version": SCHEMA_VERSION,
        "wave_id": WAVE_ID,
        "status": "quantum_research_governance_ready"
        if not sample_errors
        else "blocked_invalid_quantum_research_governance",
        "generated_at": now_iso(),
        "public_safe": True,
        "current_public_labels": dict(CURRENT_PUBLIC_LABELS),
        "target_public_labels": dict(TARGET_PUBLIC_LABELS),
        "label_migration_wave": "wave_f",
        "route_contract": dict(ROUTE_CONTRACT),
        "discovery_origins": list(DISCOVERY_ORIGINS),
        "validation_contributions": list(VALIDATION_CONTRIBUTIONS),
        "authority": quantum_research_authority(),
        "sample_candidate": sample.to_dict(),
        "sample_candidate_validation_errors": sample_errors,
        "research_candidate_is_trade_signal": False,
        "hardware_activity_is_quantum_edge_proof": False,
        "quantum_result_is_strategy_approval": False,
        "provider_readiness_is_execution_authority": False,
        "boundary": (
            "Quantum may originate a public-safe research candidate relationship. "
            "It cannot validate itself, create a validated edge or strategy, approve "
            "risk or position size, approve execution, create an order, call a broker, "
            "grant proof credit, enable dashboard or Telegram commands, or enable live capital."
        ),
    }


def validate_quantum_edge_governance(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("quantum_governance_schema_invalid")
    if payload.get("wave_id") != WAVE_ID:
        errors.append("quantum_governance_wave_invalid")
    if payload.get("status") != "quantum_research_governance_ready":
        errors.append("quantum_governance_not_ready")
    if payload.get("public_safe") is not True:
        errors.append("quantum_governance_not_public_safe")
    if payload.get("target_public_labels") != TARGET_PUBLIC_LABELS:
        errors.append("quantum_governance_target_labels_invalid")
    if payload.get("route_contract") != ROUTE_CONTRACT:
        errors.append("quantum_governance_route_contract_changed")
    if payload.get("label_migration_wave") != "wave_f":
        errors.append("quantum_governance_label_migration_wave_invalid")
    if payload.get("discovery_origins") != list(DISCOVERY_ORIGINS):
        errors.append("quantum_governance_discovery_origins_invalid")
    if payload.get("validation_contributions") != list(VALIDATION_CONTRIBUTIONS):
        errors.append("quantum_governance_validation_contributions_invalid")

    authority = payload.get("authority")
    if not isinstance(authority, dict):
        errors.append("quantum_governance_authority_missing")
    else:
        if authority.get(RESEARCH_CAPABILITY_FIELD) is not True:
            errors.append("quantum_governance_research_capability_missing")
        for field_name in ZERO_AUTHORITY_FIELDS:
            if authority.get(field_name) is not False:
                errors.append(f"quantum_governance_authority_escalated:{field_name}")

    for field_name in (
        "research_candidate_is_trade_signal",
        "hardware_activity_is_quantum_edge_proof",
        "quantum_result_is_strategy_approval",
        "provider_readiness_is_execution_authority",
    ):
        if payload.get(field_name) is not False:
            errors.append(f"quantum_governance_boundary_escalated:{field_name}")

    sample = payload.get("sample_candidate")
    if not isinstance(sample, dict):
        errors.append("quantum_governance_sample_candidate_missing")
    else:
        errors.extend(validate_quantum_research_candidate(sample))
    if payload.get("sample_candidate_validation_errors") != []:
        errors.append("quantum_governance_sample_candidate_invalid")
    if "cannot validate itself" not in str(payload.get("boundary") or ""):
        errors.append("quantum_governance_boundary_weak")
    return sorted(set(errors))


def negative_governance_probe_errors() -> dict[str, list[str]]:
    safe = sample_quantum_research_candidate()

    self_validated = replace(safe, validation_contribution="quantum_strengthened")
    self_validation_errors = validate_quantum_research_candidate(self_validated)

    authority = quantum_research_authority()
    authority["strategy_hypothesis_creation_allowed"] = True
    strategy_escalated = replace(safe, authority=authority)
    strategy_errors = validate_quantum_research_candidate(strategy_escalated)

    order_authority = quantum_research_authority()
    order_authority["paper_order_allowed"] = True
    order_escalated = replace(safe, authority=order_authority)
    order_errors = validate_quantum_research_candidate(order_escalated)

    return {
        "self_validation": self_validation_errors,
        "strategy_authority": strategy_errors,
        "order_authority": order_errors,
    }


def write_quantum_edge_governance(
    payload: dict[str, Any],
    settings: Settings | None = None,
) -> Path:
    errors = validate_quantum_edge_governance(payload)
    if errors:
        raise ValueError(f"Quantum Edge governance invalid: {errors}")
    active_settings = settings or Settings.from_env()
    path = Path(active_settings.runtime_dir) / ARTIFACT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(path)
    return path
