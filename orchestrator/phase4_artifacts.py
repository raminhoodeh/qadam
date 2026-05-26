"""Phase 4 Strategy Manifestation artifact contracts.

Phase 4 can define, validate, and approve strategy posture. It cannot create
trade candidates, approve risk, submit orders, write to brokers, call quantum
providers, or enable live capital.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


PHASE4_ARTIFACT_SCHEMA_VERSION = 1

PHASE4_STATUS_ENUMS: tuple[str, ...] = (
    "draft",
    "provisional",
    "validated",
    "rejected",
    "untestable",
    "approved_shadow",
    "inactive",
)

PHASE4_APPROVAL_STATES: tuple[str, ...] = (
    "not_requested",
    "approved",
    "rejected",
    "amendments_required",
)

PHASE4_COMMON_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "artifact_type",
    "artifact_id",
    "status",
    "generated_at",
    "public_safe",
    "authority_boundary",
    "boundary",
)

PHASE4_AUTHORITY_BOUNDARY_FIELDS: tuple[str, ...] = (
    "trade_candidate_creation_allowed",
    "risk_approval_allowed",
    "execution_allowed",
    "paper_order_allowed",
    "staged_paper_order_allowed",
    "broker_write_allowed",
    "live_capital_enabled",
    "quantum_provider_call_allowed",
    "quantum_hardware_submission_allowed",
    "scheduler_enabled",
)

PHASE4_ARTIFACT_TYPES: tuple[str, ...] = (
    "triple_mirror_audit",
    "data_veracity_audit",
    "trust_score_recalculation",
    "resource_validation",
    "world_model_validation",
    "candidate_strategy_universe",
    "manifested_strategy_metadata",
    "strategy_toggle_snapshot",
    "fund_manager_approval_event",
)

PHASE4_STRATEGY_TOGGLE_STATES: tuple[str, ...] = (
    "inactive",
    "draft",
    "approved_shadow",
    "suspended",
    "retired",
)


@dataclass(frozen=True)
class Phase4ArtifactContract:
    artifact_type: str
    description: str
    required_fields: tuple[str, ...]
    allowed_statuses: tuple[str, ...]
    default_status: str
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["required_fields"] = list(self.required_fields)
        payload["allowed_statuses"] = list(self.allowed_statuses)
        return payload


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def phase4_authority_boundary() -> dict[str, Any]:
    boundary = {field: False for field in PHASE4_AUTHORITY_BOUNDARY_FIELDS}
    boundary["boundary"] = (
        "Phase 4 artifacts are strategy-governance records only. They cannot "
        "create trade candidates, approve risk, submit orders, write to "
        "brokers, call quantum providers, schedule hardware, or enable live capital."
    )
    return boundary


def phase4_artifact_contracts() -> tuple[Phase4ArtifactContract, ...]:
    return (
        Phase4ArtifactContract(
            artifact_type="triple_mirror_audit",
            description="Compare plan intent, Resource Registry mapping, and observed runtime behavior.",
            required_fields=PHASE4_COMMON_REQUIRED_FIELDS
            + ("drift_status", "mirror_count", "authority_mismatch_count"),
            allowed_statuses=("draft", "provisional", "validated", "rejected"),
            default_status="draft",
            boundary="Audit findings are advisory and cannot promote resources or strategies automatically.",
        ),
        Phase4ArtifactContract(
            artifact_type="data_veracity_audit",
            description="Score source coverage, freshness, latency, degradation, and corroboration posture.",
            required_fields=PHASE4_COMMON_REQUIRED_FIELDS
            + ("canonical_source_count", "supplemental_source_count", "quarantined_source_count"),
            allowed_statuses=("draft", "provisional", "validated", "rejected"),
            default_status="draft",
            boundary="Data veracity can lower confidence or quarantine sources but cannot create orders.",
        ),
        Phase4ArtifactContract(
            artifact_type="trust_score_recalculation",
            description="Record seed, observed, and final provisional Trust Scores with reason codes.",
            required_fields=PHASE4_COMMON_REQUIRED_FIELDS
            + ("score_count", "observation_backed_count", "quarantined_source_count"),
            allowed_statuses=("draft", "provisional", "validated", "rejected"),
            default_status="draft",
            boundary="Trust Scores are routing evidence for review only; they cannot approve execution.",
        ),
        Phase4ArtifactContract(
            artifact_type="resource_validation",
            description="Validate Resource Registry references for strategy use.",
            required_fields=PHASE4_COMMON_REQUIRED_FIELDS
            + ("resource_count", "validated_resource_count", "provisional_resource_count"),
            allowed_statuses=("draft", "provisional", "validated", "rejected"),
            default_status="draft",
            boundary="Resource Registry entries are non-live references, not observed market evidence.",
        ),
        Phase4ArtifactContract(
            artifact_type="world_model_validation",
            description="Classify private world-model frames against observed support and contradiction.",
            required_fields=PHASE4_COMMON_REQUIRED_FIELDS
            + ("claim_count", "validated_claim_count", "untestable_claim_count", "evidence_boundary"),
            allowed_statuses=("draft", "provisional", "validated", "rejected", "untestable"),
            default_status="draft",
            boundary="World-model claims remain private priors, not factual evidence or trade triggers.",
        ),
        Phase4ArtifactContract(
            artifact_type="candidate_strategy_universe",
            description="Define draft strategy-family candidates without creating trade candidates.",
            required_fields=PHASE4_COMMON_REQUIRED_FIELDS
            + ("strategy_family_candidate_count", "draft_hypothesis_count", "trade_candidate_count", "candidates"),
            allowed_statuses=("draft", "provisional", "validated", "rejected"),
            default_status="draft",
            boundary="Strategy-family candidates are draft hypotheses only and cannot route risk or execution.",
        ),
        Phase4ArtifactContract(
            artifact_type="manifested_strategy_metadata",
            description="Metadata for the Manifested Strategy Document.",
            required_fields=PHASE4_COMMON_REQUIRED_FIELDS
            + (
                "document_path",
                "document_fingerprint",
                "active_instrument_count",
                "catalyst_class_count",
                "approval_required",
            ),
            allowed_statuses=("draft", "provisional", "validated", "rejected", "approved_shadow"),
            default_status="draft",
            boundary="Strategy manifestation approval is not trade, risk, order, or broker approval.",
        ),
        Phase4ArtifactContract(
            artifact_type="strategy_toggle_snapshot",
            description="Visible strategy availability states for future guarded orchestration design.",
            required_fields=PHASE4_COMMON_REQUIRED_FIELDS
            + ("toggle_count", "toggles", "event_log_required"),
            allowed_statuses=("inactive", "draft", "approved_shadow", "rejected"),
            default_status="inactive",
            boundary="A strategy toggle can mark approved-shadow posture only; it cannot route execution.",
        ),
        Phase4ArtifactContract(
            artifact_type="fund_manager_approval_event",
            description="Replayable Event Log payload for approval, rejection, or amendment request.",
            required_fields=PHASE4_COMMON_REQUIRED_FIELDS
            + ("approval_state", "approval_logged", "approver_label", "event_log_correlation_id"),
            allowed_statuses=("draft", "approved_shadow", "rejected"),
            default_status="draft",
            boundary="Fund Manager strategy approval does not enable paper orders, broker writes, or live capital.",
        ),
    )


def phase4_contract_by_type() -> dict[str, Phase4ArtifactContract]:
    return {contract.artifact_type: contract for contract in phase4_artifact_contracts()}


def _base_artifact(artifact_type: str, *, status: str | None = None) -> dict[str, Any]:
    contracts = phase4_contract_by_type()
    contract = contracts[artifact_type]
    return {
        "schema_version": PHASE4_ARTIFACT_SCHEMA_VERSION,
        "artifact_type": artifact_type,
        "artifact_id": f"sample:{artifact_type}",
        "status": status or contract.default_status,
        "generated_at": _now(),
        "public_safe": True,
        "authority_boundary": phase4_authority_boundary(),
        "boundary": contract.boundary,
    }


def build_phase4_sample_artifacts(*, include_approval_event: bool = True) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []

    artifacts.append(
        {
            **_base_artifact("triple_mirror_audit"),
            "drift_status": "not_run",
            "mirror_count": 3,
            "authority_mismatch_count": 0,
        }
    )
    artifacts.append(
        {
            **_base_artifact("data_veracity_audit"),
            "canonical_source_count": 35,
            "supplemental_source_count": 1,
            "quarantined_source_count": 0,
        }
    )
    artifacts.append(
        {
            **_base_artifact("trust_score_recalculation"),
            "score_count": 35,
            "observation_backed_count": 0,
            "quarantined_source_count": 0,
        }
    )
    artifacts.append(
        {
            **_base_artifact("resource_validation"),
            "resource_count": 29,
            "validated_resource_count": 0,
            "provisional_resource_count": 29,
        }
    )
    artifacts.append(
        {
            **_base_artifact("world_model_validation", status="untestable"),
            "claim_count": 5,
            "validated_claim_count": 0,
            "untestable_claim_count": 5,
            "evidence_boundary": "World-model claims are private priors, not factual evidence or trade triggers.",
        }
    )
    artifacts.append(
        {
            **_base_artifact("candidate_strategy_universe"),
            "strategy_family_candidate_count": 1,
            "draft_hypothesis_count": 1,
            "trade_candidate_count": 0,
            "candidates": [
                {
                    "object_type": "strategy_family_candidate",
                    "candidate_key": "sample_strategy_family",
                    "risk_agent_handoff_allowed": False,
                    "execution_policy_handoff_allowed": False,
                    "trade_candidate_created": False,
                    "execution_allowed": False,
                    "paper_order_allowed": False,
                    "broker_write_allowed": False,
                    "live_capital_enabled": False,
                    "boundary": "Sample strategy-family candidate is a draft hypothesis only.",
                }
            ],
        }
    )
    artifacts.append(
        {
            **_base_artifact("manifested_strategy_metadata"),
            "document_path": "docs/qadam-manifested-strategy.md",
            "document_fingerprint": None,
            "active_instrument_count": 0,
            "catalyst_class_count": 0,
            "approval_required": True,
        }
    )
    artifacts.append(
        {
            **_base_artifact("strategy_toggle_snapshot", status="approved_shadow"),
            "toggle_count": 1,
            "toggles": [
                {
                    "strategy_key": "sample_strategy_family",
                    "toggle_state": "approved_shadow",
                    "execution_allowed": False,
                    "paper_order_allowed": False,
                    "broker_write_allowed": False,
                    "live_capital_enabled": False,
                    "boundary": "Approved-shadow means strategy review visibility only.",
                }
            ],
            "event_log_required": True,
        }
    )
    if include_approval_event:
        artifacts.append(
            {
                **_base_artifact("fund_manager_approval_event"),
                "approval_state": "not_requested",
                "approval_logged": False,
                "approver_label": None,
                "event_log_correlation_id": None,
            }
        )
    return artifacts


def _authority_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    boundary = artifact.get("authority_boundary")
    if not isinstance(boundary, dict):
        return ["authority_boundary_missing_or_invalid"]
    for field in PHASE4_AUTHORITY_BOUNDARY_FIELDS:
        if boundary.get(field) is not False:
            errors.append(f"authority_boundary_enabled:{field}")
    return errors


def _toggle_errors(artifact: dict[str, Any]) -> list[str]:
    if artifact.get("artifact_type") != "strategy_toggle_snapshot":
        return []
    errors: list[str] = []
    toggles = artifact.get("toggles")
    if not isinstance(toggles, list):
        return ["toggles_missing_or_invalid"]
    for index, toggle in enumerate(toggles):
        if not isinstance(toggle, dict):
            errors.append(f"toggle_invalid:{index}")
            continue
        state = toggle.get("toggle_state")
        if state not in PHASE4_STRATEGY_TOGGLE_STATES:
            errors.append(f"toggle_state_invalid:{index}")
        for field in ("execution_allowed", "paper_order_allowed", "broker_write_allowed", "live_capital_enabled"):
            if toggle.get(field) is not False:
                errors.append(f"toggle_authority_enabled:{index}:{field}")
    return errors


def validate_phase4_artifact(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    artifact_type = artifact.get("artifact_type")
    contracts = phase4_contract_by_type()
    contract = contracts.get(str(artifact_type))
    if contract is None:
        return [f"unknown_artifact_type:{artifact_type}"]

    for field in contract.required_fields:
        if field not in artifact:
            errors.append(f"missing_field:{artifact_type}:{field}")
    if artifact.get("schema_version") != PHASE4_ARTIFACT_SCHEMA_VERSION:
        errors.append(f"schema_version_mismatch:{artifact_type}")
    if artifact.get("status") not in contract.allowed_statuses:
        errors.append(f"status_invalid:{artifact_type}:{artifact.get('status')}")
    if artifact.get("public_safe") is not True:
        errors.append(f"public_safe_not_true:{artifact_type}")
    if not str(artifact.get("boundary", "")).strip():
        errors.append(f"boundary_missing:{artifact_type}")
    if artifact_type == "fund_manager_approval_event":
        approval_state = artifact.get("approval_state")
        if approval_state not in PHASE4_APPROVAL_STATES:
            errors.append(f"approval_state_invalid:{approval_state}")
        if approval_state == "approved" and artifact.get("approval_logged") is not True:
            errors.append("approval_not_logged")
    errors.extend(_authority_errors(artifact))
    errors.extend(_toggle_errors(artifact))
    return errors


def phase4_artifact_bundle_summary(artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    seen = Counter(str(artifact.get("artifact_type")) for artifact in artifacts)
    missing_types = [artifact_type for artifact_type in PHASE4_ARTIFACT_TYPES if seen.get(artifact_type, 0) == 0]
    duplicate_types = [artifact_type for artifact_type, count in seen.items() if count > 1]
    for artifact in artifacts:
        errors.extend(validate_phase4_artifact(artifact))
    for artifact_type in missing_types:
        errors.append(f"missing_artifact_type:{artifact_type}")
    for artifact_type in duplicate_types:
        errors.append(f"duplicate_artifact_type:{artifact_type}")

    approval_events = [artifact for artifact in artifacts if artifact.get("artifact_type") == "fund_manager_approval_event"]
    approval_event = approval_events[0] if approval_events else {}
    approval_state = approval_event.get("approval_state", "missing")
    approval_logged = approval_event.get("approval_logged") is True
    strategy_documents = [
        artifact for artifact in artifacts if artifact.get("artifact_type") == "manifested_strategy_metadata"
    ]
    strategy_document = strategy_documents[0] if strategy_documents else {}
    strategy_document_ready = bool(str(strategy_document.get("document_fingerprint") or "").strip())
    approval_complete = approval_state == "approved" and approval_logged
    phase4_certification_allowed = not errors and approval_complete and strategy_document_ready

    return {
        "status": "ok" if not errors else "error",
        "schema_version": PHASE4_ARTIFACT_SCHEMA_VERSION,
        "artifact_count": len(artifacts),
        "artifact_type_count": len(PHASE4_ARTIFACT_TYPES),
        "status_enum_count": len(PHASE4_STATUS_ENUMS),
        "authority_boundary_field_count": len(PHASE4_AUTHORITY_BOUNDARY_FIELDS),
        "missing_artifact_types": missing_types,
        "duplicate_artifact_types": duplicate_types,
        "error_count": len(errors),
        "errors": errors,
        "approval_state": approval_state,
        "approval_logged": approval_logged,
        "approval_complete": approval_complete,
        "strategy_document_ready": strategy_document_ready,
        "phase4_certification_allowed": phase4_certification_allowed,
        "boundary": (
            "Phase 4 certification remains blocked until all artifacts validate "
            "and an approved Fund Manager approval event is replayable."
        ),
    }
