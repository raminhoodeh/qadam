"""Phase 6 Learning Loop artifact contracts.

Q6-1 defines the shared schema, authority ledger, event names, source posture,
and provenance rules for the Learning Loop. It is schema-only: it does not
create postmortems, approve learning, write a Knowledge Graph, update model
weights, mutate trust scores, run strategies, or enable live capital.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from world_monitor.source_registry import EXPECTED_SOURCE_COUNT


PHASE6_ARTIFACT_SCHEMA_VERSION = 1

PHASE6_STATUS_ENUMS: tuple[str, ...] = (
    "blocked",
    "schema_only",
    "read_only",
    "draft",
    "pending_review",
    "approved",
    "deferred",
    "rejected",
    "staged",
    "linked",
    "proposal",
    "replay",
    "visible",
    "certified",
)

PHASE6_ARTIFACT_TYPES: tuple[str, ...] = (
    "learning_authority_ledger",
    "learning_source_inventory",
    "closed_trade_outcome",
    "postmortem_packet",
    "postmortem_draft",
    "postmortem_analysis_packet",
    "postmortem_review",
    "outcome_link",
    "learning_approval_record",
    "knowledge_graph_staged_write",
    "knowledge_graph_read_view",
    "model_weight_update_proposal",
    "trust_score_update_proposal",
    "shadow_strategy_replay",
    "architect_learning_summary",
    "cockpit_learning_visibility",
    "phase6_certification",
)

PHASE6_AUTHORITY_FIELDS: tuple[str, ...] = (
    "phase6_learning_loop_implementation_allowed",
    "phase6_postmortem_ingestion_allowed",
    "phase6_postmortem_draft_allowed",
    "phase6_learning_review_approval_allowed",
    "phase6_learning_write_allowed",
    "phase6_knowledge_graph_write_allowed",
    "phase6_model_weight_update_allowed",
    "phase6_trust_score_update_allowed",
    "phase6_shadow_strategy_runner_allowed",
    "phase6_architect_policy_mutation_allowed",
    "phase6_policy_mutation_allowed",
    "phase7_demo_proof_planning_allowed",
    "phase7_proof_credit_allowed",
    "broker_post_allowed",
    "alpaca_post_allowed",
    "broker_write_allowed",
    "prediction_market_write_allowed",
    "crypto_perps_write_allowed",
    "live_endpoint_allowed",
    "live_capital_enabled",
)

PHASE6_UNSAFE_COUNT_FIELDS: tuple[str, ...] = (
    "broker_post_called_count",
    "alpaca_post_called_count",
    "broker_write_allowed_count",
    "prediction_market_write_allowed_count",
    "crypto_perps_write_allowed_count",
    "live_endpoint_allowed_count",
    "live_capital_enabled_count",
    "phase7_proof_credit_allowed_count",
    "phase6_postmortem_ingestion_allowed_count",
    "phase6_learning_write_allowed_count",
    "phase6_knowledge_graph_write_allowed_count",
    "phase6_model_weight_update_allowed_count",
    "phase6_trust_score_update_allowed_count",
    "phase6_shadow_strategy_runner_allowed_count",
    "phase6_policy_mutation_allowed_count",
)

PHASE6_COMMON_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "artifact_type",
    "artifact_id",
    "phase",
    "stage",
    "status",
    "generated_at",
    "public_safe",
    "event_log_required",
    "event_log_written",
    "event_log_correlation_id",
    "event_contract",
    "authority_ledger",
    "source_posture",
    "provenance",
    "boundary",
)

PHASE6_SOURCE_POSTURE_REQUIRED_FIELDS: tuple[str, ...] = (
    "canonical_source_required",
    "canonical_source_count",
    "supplemental_source_bypass_allowed",
    "yahoo_finance_role",
    "preference_mcp_role",
    "preference_mcp_source_36",
    "preference_paid_tools_allowed",
    "qctrl_role",
    "source_quorum_bypass_allowed",
)

PHASE6_PROVENANCE_REQUIRED_FIELDS: tuple[str, ...] = (
    "source_refs",
    "event_log_required",
    "raw_secret_exposed",
    "raw_payload_exposed",
    "local_path_exposed",
    "execution_evidence_refs",
    "market_context_refs",
    "model_interpretation_refs",
    "governance_refs",
)

PHASE6_EVENT_TYPES: dict[str, str] = {
    "artifact_schema": "phase6_artifact_schema_recorded",
    "postmortem_draft": "phase6_postmortem_draft_created",
    "postmortem_review": "phase6_postmortem_review_recorded",
    "staged_learning_write": "phase6_learning_write_staged",
    "model_update_proposal": "phase6_model_weight_update_proposed",
    "trust_update_proposal": "phase6_trust_score_update_proposed",
    "certification": "phase6_certification_recorded",
}

PHASE6_REQUIRED_EVENT_CATEGORIES: tuple[str, ...] = (
    "postmortem_draft",
    "postmortem_review",
    "staged_learning_write",
    "model_update_proposal",
    "trust_update_proposal",
    "certification",
)


@dataclass(frozen=True)
class Phase6ArtifactContract:
    artifact_type: str
    description: str
    required_fields: tuple[str, ...]
    allowed_statuses: tuple[str, ...]
    default_status: str
    event_category: str
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["required_fields"] = list(self.required_fields)
        payload["allowed_statuses"] = list(self.allowed_statuses)
        return payload


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def phase6_authority_defaults() -> dict[str, bool]:
    return {field: False for field in PHASE6_AUTHORITY_FIELDS}


def phase6_unsafe_counter_defaults() -> dict[str, int]:
    return {field: 0 for field in PHASE6_UNSAFE_COUNT_FIELDS}


def phase6_authority_ledger() -> dict[str, Any]:
    defaults = phase6_authority_defaults()
    return {
        "authority_schema_version": PHASE6_ARTIFACT_SCHEMA_VERSION,
        "stage": "Q6-1",
        "authority_field_count": len(PHASE6_AUTHORITY_FIELDS),
        "explicit_authority_grant_count": 0,
        **defaults,
        "boundary": (
            "Q6-1 defines Phase 6 artifact shapes only. Every authority flag "
            "defaults false until a later Q6 gate explicitly grants and "
            "validates a narrower permission."
        ),
    }


def phase6_source_posture() -> dict[str, Any]:
    return {
        "canonical_source_required": True,
        "canonical_source_count": EXPECTED_SOURCE_COUNT,
        "supplemental_source_bypass_allowed": False,
        "yahoo_finance_role": "supplemental_market_confirmation_only",
        "preference_mcp_role": "supplemental_multi_source_data_plane",
        "preference_mcp_source_36": False,
        "preference_paid_tools_allowed": False,
        "qctrl_role": "shadow_annotation_only",
        "source_quorum_bypass_allowed": False,
        "boundary": (
            "Phase 6 learning artifacts must keep execution evidence, market "
            "context, source provenance, model interpretation, and governance "
            "approval separate. Yahoo Finance, Preference/PREF MCP, and Q-CTRL "
            "remain supplemental context by default."
        ),
    }


def phase6_provenance(source_refs: tuple[str, ...] | None = None) -> dict[str, Any]:
    return {
        "source_refs": list(
            source_refs
            or (
                "data/runtime/phase6_readiness.json",
                "data/runtime/phase5_phase6_handoff.json",
                "data/runtime/phase5_position_monitor.json",
            )
        ),
        "event_log_required": True,
        "raw_secret_exposed": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "execution_evidence_refs": [],
        "market_context_refs": [],
        "model_interpretation_refs": [],
        "governance_refs": [],
        "boundary": (
            "Phase 6 artifacts must cite public-safe relative source refs and "
            "must not expose secrets, raw private payloads, or local-only "
            "absolute paths."
        ),
    }


def phase6_event_contract(event_category: str) -> dict[str, Any]:
    event_type = PHASE6_EVENT_TYPES[event_category]
    return {
        "event_schema_version": PHASE6_ARTIFACT_SCHEMA_VERSION,
        "event_category": event_category,
        "event_type": event_type,
        "event_log_required": True,
        "append_only": True,
        "supersession_required_for_change": True,
        "raw_secret_exposed": False,
        "raw_payload_exposed": False,
        "boundary": (
            "Phase 6 events are append-only audit records. They cannot be used "
            "to hide policy mutation, broker writes, live capital, or Phase 7 "
            "proof credit."
        ),
    }


def phase6_event_contracts() -> dict[str, dict[str, Any]]:
    return {
        category: phase6_event_contract(category)
        for category in PHASE6_REQUIRED_EVENT_CATEGORIES
    }


def phase6_artifact_contracts() -> tuple[Phase6ArtifactContract, ...]:
    common = PHASE6_COMMON_REQUIRED_FIELDS
    return (
        Phase6ArtifactContract(
            artifact_type="learning_authority_ledger",
            description="Shared authority ledger for every Phase 6 artifact.",
            required_fields=common
            + ("authority_field_count", "explicit_authority_grant_count"),
            allowed_statuses=("schema_only", "blocked"),
            default_status="schema_only",
            event_category="artifact_schema",
            boundary="The authority ledger can describe permissions but cannot grant them in Q6-1.",
        ),
        Phase6ArtifactContract(
            artifact_type="learning_source_inventory",
            description="Read-only inventory contract for postmortem-due source artifacts.",
            required_fields=common
            + ("postmortem_due_count", "source_inventory_write_allowed", "source_ref_count"),
            allowed_statuses=("schema_only", "blocked", "read_only"),
            default_status="schema_only",
            event_category="artifact_schema",
            boundary="Source inventory can list eligible inputs but cannot ingest or mutate them in Q6-1.",
        ),
        Phase6ArtifactContract(
            artifact_type="closed_trade_outcome",
            description="Normalized closed-trade outcome contract.",
            required_fields=common
            + ("closed_trade_ref", "outcome_status", "learning_write_allowed"),
            allowed_statuses=("schema_only", "blocked", "read_only"),
            default_status="schema_only",
            event_category="artifact_schema",
            boundary="Closed-trade outcomes cannot write learning state or rewrite Phase 5 lifecycle records.",
        ),
        Phase6ArtifactContract(
            artifact_type="postmortem_packet",
            description="Required packet shape for postmortem drafts.",
            required_fields=common
            + ("packet_sections", "assertion_source_refs_required", "uncited_conclusion_allowed"),
            allowed_statuses=("schema_only", "blocked", "draft"),
            default_status="schema_only",
            event_category="artifact_schema",
            boundary="Packet contracts can define shape only; they cannot create a postmortem draft.",
        ),
        Phase6ArtifactContract(
            artifact_type="postmortem_draft",
            description="Draft postmortem artifact contract.",
            required_fields=common
            + ("draft_state", "source_assertion_count", "approval_state", "learning_write_allowed"),
            allowed_statuses=("schema_only", "blocked", "draft", "pending_review"),
            default_status="schema_only",
            event_category="postmortem_draft",
            boundary="Postmortem drafts are review inputs only and cannot approve learning writes.",
        ),
        Phase6ArtifactContract(
            artifact_type="postmortem_analysis_packet",
            description="Specialized catalyst, pricing, regime, execution, or override analysis packet.",
            required_fields=common
            + ("analysis_packet_type", "claim_count", "all_claims_cited", "approval_state"),
            allowed_statuses=("schema_only", "blocked", "draft"),
            default_status="schema_only",
            event_category="postmortem_draft",
            boundary="Analysis packets can explain evidence but cannot approve updates or mutate scores.",
        ),
        Phase6ArtifactContract(
            artifact_type="postmortem_review",
            description="Human or governance review contract for a reduced postmortem.",
            required_fields=common
            + ("review_state", "reviewer_label", "learning_action_count", "write_allowed"),
            allowed_statuses=("schema_only", "blocked", "pending_review", "approved", "deferred", "rejected"),
            default_status="schema_only",
            event_category="postmortem_review",
            boundary="Reviews can record approval intent only after later gates; Q6-1 cannot approve writes.",
        ),
        Phase6ArtifactContract(
            artifact_type="outcome_link",
            description="Link-only contract connecting outcome, source, risk, execution, and quantum refs.",
            required_fields=common
            + ("source_trade_ref", "linked_ref_count", "link_write_allowed"),
            allowed_statuses=("schema_only", "blocked", "linked"),
            default_status="schema_only",
            event_category="postmortem_review",
            boundary="Outcome links can connect refs only and cannot update learning state in Q6-1.",
        ),
        Phase6ArtifactContract(
            artifact_type="learning_approval_record",
            description="Governance approval, deferral, or rejection record before learning writes.",
            required_fields=common
            + ("approval_state", "approval_logged", "learning_write_allowed"),
            allowed_statuses=("schema_only", "blocked", "pending_review", "approved", "deferred", "rejected"),
            default_status="schema_only",
            event_category="postmortem_review",
            boundary="Approval records cannot approve learning writes during Q6-1.",
        ),
        Phase6ArtifactContract(
            artifact_type="knowledge_graph_staged_write",
            description="Staged catalyst-memory write contract for later approved learning.",
            required_fields=common
            + ("kg_write_state", "staged_write_allowed", "supersedes_ref", "approval_ref"),
            allowed_statuses=("schema_only", "blocked", "staged"),
            default_status="schema_only",
            event_category="staged_learning_write",
            boundary="Knowledge Graph writes cannot be staged or committed before a later approval gate.",
        ),
        Phase6ArtifactContract(
            artifact_type="knowledge_graph_read_view",
            description="Read/search view contract for approved learning entries.",
            required_fields=common + ("read_view_state", "write_allowed", "result_count"),
            allowed_statuses=("schema_only", "blocked", "read_only"),
            default_status="schema_only",
            event_category="staged_learning_write",
            boundary="Read views can expose approved entries later but cannot create or alter graph records.",
        ),
        Phase6ArtifactContract(
            artifact_type="model_weight_update_proposal",
            description="Bayesian model-weight update proposal contract.",
            required_fields=common
            + ("proposal_state", "before_weight", "after_weight", "apply_allowed"),
            allowed_statuses=("schema_only", "blocked", "proposal"),
            default_status="schema_only",
            event_category="model_update_proposal",
            boundary="Model-weight proposals cannot apply updates in Q6-1.",
        ),
        Phase6ArtifactContract(
            artifact_type="trust_score_update_proposal",
            description="Source trust-score update proposal contract.",
            required_fields=common
            + ("proposal_state", "before_score", "after_score", "apply_allowed"),
            allowed_statuses=("schema_only", "blocked", "proposal"),
            default_status="schema_only",
            event_category="trust_update_proposal",
            boundary="Trust-score proposals cannot apply score changes in Q6-1.",
        ),
        Phase6ArtifactContract(
            artifact_type="shadow_strategy_replay",
            description="What-would-have-happened replay contract.",
            required_fields=common
            + ("replay_state", "trade_candidate_creation_allowed", "order_creation_allowed"),
            allowed_statuses=("schema_only", "blocked", "replay"),
            default_status="schema_only",
            event_category="model_update_proposal",
            boundary="Shadow strategy replay cannot create candidates, orders, or live actions.",
        ),
        Phase6ArtifactContract(
            artifact_type="architect_learning_summary",
            description="Architect recommendation contract.",
            required_fields=common
            + ("summary_state", "recommendation_count", "policy_mutation_allowed"),
            allowed_statuses=("schema_only", "blocked", "proposal"),
            default_status="schema_only",
            event_category="trust_update_proposal",
            boundary="Architect summaries can recommend only and cannot mutate policy.",
        ),
        Phase6ArtifactContract(
            artifact_type="cockpit_learning_visibility",
            description="Public-safe cockpit and dashboard visibility contract.",
            required_fields=common
            + ("visibility_state", "backend_derived", "ui_inferred_readiness_count"),
            allowed_statuses=("schema_only", "blocked", "visible"),
            default_status="schema_only",
            event_category="artifact_schema",
            boundary="Visibility records must be backend-derived and cannot infer readiness from the UI.",
        ),
        Phase6ArtifactContract(
            artifact_type="phase6_certification",
            description="Phase 6 certification contract.",
            required_fields=common
            + ("phase6_certified", "phase7_demo_proof_planning_allowed", "phase7_proof_credit_allowed"),
            allowed_statuses=("schema_only", "blocked", "certified"),
            default_status="schema_only",
            event_category="certification",
            boundary="Certification can summarize Phase 6 only and cannot enable live capital or proof credit.",
        ),
    )


def phase6_contract_by_type() -> dict[str, Phase6ArtifactContract]:
    return {contract.artifact_type: contract for contract in phase6_artifact_contracts()}


def _base_artifact(artifact_type: str, *, status: str | None = None) -> dict[str, Any]:
    contract = phase6_contract_by_type()[artifact_type]
    authority = phase6_authority_ledger()
    return {
        "schema_version": PHASE6_ARTIFACT_SCHEMA_VERSION,
        "artifact_type": artifact_type,
        "artifact_id": f"sample:q6-1:{artifact_type}",
        "phase": "Q6",
        "stage": "Q6-1",
        "status": status or contract.default_status,
        "generated_at": _now(),
        "public_safe": True,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_correlation_id": None,
        "event_contract": phase6_event_contract(contract.event_category),
        "authority_ledger": authority,
        "source_posture": phase6_source_posture(),
        "provenance": phase6_provenance(),
        "boundary": contract.boundary,
        **phase6_authority_defaults(),
        **phase6_unsafe_counter_defaults(),
    }


def build_phase6_sample_artifacts() -> list[dict[str, Any]]:
    return [
        {
            **_base_artifact("learning_authority_ledger"),
            "authority_field_count": len(PHASE6_AUTHORITY_FIELDS),
            "explicit_authority_grant_count": 0,
        },
        {
            **_base_artifact("learning_source_inventory"),
            "postmortem_due_count": 0,
            "source_inventory_write_allowed": False,
            "source_ref_count": 0,
        },
        {
            **_base_artifact("closed_trade_outcome"),
            "closed_trade_ref": None,
            "outcome_status": "schema_only_not_normalized",
            "learning_write_allowed": False,
        },
        {
            **_base_artifact("postmortem_packet"),
            "packet_sections": [
                "thesis",
                "timeline",
                "catalyst_read",
                "pricing_read",
                "regime_read",
                "execution_read",
                "source_quality",
                "uncertainty",
                "proposed_learning_actions",
            ],
            "assertion_source_refs_required": True,
            "uncited_conclusion_allowed": False,
        },
        {
            **_base_artifact("postmortem_draft"),
            "draft_state": "schema_only_not_created",
            "source_assertion_count": 0,
            "approval_state": "not_requested",
            "learning_write_allowed": False,
        },
        {
            **_base_artifact("postmortem_analysis_packet"),
            "analysis_packet_type": "schema_only",
            "claim_count": 0,
            "all_claims_cited": True,
            "approval_state": "not_requested",
        },
        {
            **_base_artifact("postmortem_review"),
            "review_state": "not_reviewed",
            "reviewer_label": None,
            "learning_action_count": 0,
            "write_allowed": False,
        },
        {
            **_base_artifact("outcome_link"),
            "source_trade_ref": None,
            "linked_ref_count": 0,
            "link_write_allowed": False,
        },
        {
            **_base_artifact("learning_approval_record"),
            "approval_state": "not_requested",
            "approval_logged": False,
            "learning_write_allowed": False,
        },
        {
            **_base_artifact("knowledge_graph_staged_write"),
            "kg_write_state": "schema_only_not_staged",
            "staged_write_allowed": False,
            "supersedes_ref": None,
            "approval_ref": None,
        },
        {
            **_base_artifact("knowledge_graph_read_view"),
            "read_view_state": "schema_only_not_available",
            "write_allowed": False,
            "result_count": 0,
        },
        {
            **_base_artifact("model_weight_update_proposal"),
            "proposal_state": "schema_only_not_proposed",
            "before_weight": None,
            "after_weight": None,
            "apply_allowed": False,
        },
        {
            **_base_artifact("trust_score_update_proposal"),
            "proposal_state": "schema_only_not_proposed",
            "before_score": None,
            "after_score": None,
            "apply_allowed": False,
        },
        {
            **_base_artifact("shadow_strategy_replay"),
            "replay_state": "schema_only_not_run",
            "trade_candidate_creation_allowed": False,
            "order_creation_allowed": False,
        },
        {
            **_base_artifact("architect_learning_summary"),
            "summary_state": "schema_only_not_created",
            "recommendation_count": 0,
            "policy_mutation_allowed": False,
        },
        {
            **_base_artifact("cockpit_learning_visibility"),
            "visibility_state": "schema_only_not_visible",
            "backend_derived": True,
            "ui_inferred_readiness_count": 0,
        },
        {
            **_base_artifact("phase6_certification"),
            "phase6_certified": False,
            "phase7_demo_proof_planning_allowed": False,
            "phase7_proof_credit_allowed": False,
        },
    ]


def _authority_errors(
    artifact: dict[str, Any],
    *,
    allowed_authority_fields: tuple[str, ...] = (),
) -> list[str]:
    errors: list[str] = []
    allowed = set(allowed_authority_fields)
    invalid_allowed = sorted(allowed - set(PHASE6_AUTHORITY_FIELDS))
    for field in invalid_allowed:
        errors.append(f"unknown_allowed_authority_field:{field}")
    ledger = artifact.get("authority_ledger")
    if not isinstance(ledger, dict):
        return ["authority_ledger_missing_or_invalid"]
    if ledger.get("authority_field_count") != len(PHASE6_AUTHORITY_FIELDS):
        errors.append("authority_field_count_mismatch")
    explicit_count = 0
    for field in PHASE6_AUTHORITY_FIELDS:
        field_allowed = field in allowed and artifact.get(field) is True
        if field_allowed:
            explicit_count += 1
        if field not in ledger:
            errors.append(f"authority_ledger_field_missing:{field}")
        if field_allowed:
            if ledger.get(field) is not True:
                errors.append(f"allowed_authority_ledger_not_enabled:{field}")
        elif ledger.get(field) is not False:
            errors.append(f"authority_ledger_enabled:{field}")
        if field not in artifact:
            errors.append(f"authority_field_missing:{field}")
        elif not field_allowed and artifact.get(field) is not False:
            errors.append(f"authority_enabled:{field}")
        if field in ledger and field in artifact and ledger.get(field) != artifact.get(field):
            errors.append(f"authority_field_mismatch:{field}")
    if ledger.get("explicit_authority_grant_count", 0) != explicit_count:
        errors.append("explicit_authority_grant_count_mismatch")
    return errors


def _unsafe_counter_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in PHASE6_UNSAFE_COUNT_FIELDS:
        if field not in artifact:
            errors.append(f"unsafe_counter_missing:{field}")
        elif int(artifact.get(field, 0) or 0) != 0:
            errors.append(f"unsafe_counter_nonzero:{field}")
    return errors


def _source_posture_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    posture = artifact.get("source_posture")
    if not isinstance(posture, dict):
        return ["source_posture_missing_or_invalid"]
    for field in PHASE6_SOURCE_POSTURE_REQUIRED_FIELDS:
        if field not in posture:
            errors.append(f"source_posture_field_missing:{field}")
    if posture.get("canonical_source_required") is not True:
        errors.append("canonical_source_not_required")
    if posture.get("canonical_source_count") != EXPECTED_SOURCE_COUNT:
        errors.append("canonical_source_count_mismatch")
    if posture.get("supplemental_source_bypass_allowed") is not False:
        errors.append("supplemental_source_bypass_allowed")
    if posture.get("yahoo_finance_role") != "supplemental_market_confirmation_only":
        errors.append("yahoo_finance_role_invalid")
    if posture.get("preference_mcp_role") != "supplemental_multi_source_data_plane":
        errors.append("preference_mcp_role_invalid")
    if posture.get("preference_mcp_source_36") is not False:
        errors.append("preference_mcp_source_36")
    if posture.get("preference_paid_tools_allowed") is not False:
        errors.append("preference_paid_tools_allowed")
    if posture.get("qctrl_role") != "shadow_annotation_only":
        errors.append("qctrl_role_invalid")
    if posture.get("source_quorum_bypass_allowed") is not False:
        errors.append("source_quorum_bypass_allowed")
    return errors


def _has_local_path(ref: str) -> bool:
    if ref.startswith("/"):
        return True
    if ref.startswith("~"):
        return True
    return len(ref) > 2 and ref[1:3] == ":\\"


def _provenance_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    provenance = artifact.get("provenance")
    if not isinstance(provenance, dict):
        return ["provenance_missing_or_invalid"]
    for field in PHASE6_PROVENANCE_REQUIRED_FIELDS:
        if field not in provenance:
            errors.append(f"provenance_field_missing:{field}")
    refs = provenance.get("source_refs")
    if not isinstance(refs, list) or not refs:
        errors.append("provenance_source_refs_missing")
        refs = []
    for ref in refs:
        if not isinstance(ref, str) or not ref.strip():
            errors.append("provenance_source_ref_invalid")
            continue
        if _has_local_path(ref):
            errors.append("provenance_local_path_leak")
        if "api_key" in ref.lower() or "secret" in ref.lower() or "token" in ref.lower():
            errors.append("provenance_secret_ref_leak")
    if provenance.get("event_log_required") is not True:
        errors.append("provenance_event_log_not_required")
    for field in ("raw_secret_exposed", "raw_payload_exposed", "local_path_exposed"):
        if provenance.get(field) is not False:
            errors.append(f"provenance_exposure_enabled:{field}")
    for field in (
        "execution_evidence_refs",
        "market_context_refs",
        "model_interpretation_refs",
        "governance_refs",
    ):
        if not isinstance(provenance.get(field), list):
            errors.append(f"provenance_ref_bucket_invalid:{field}")
    return errors


def _event_contract_errors(artifact: dict[str, Any], contract: Phase6ArtifactContract) -> list[str]:
    errors: list[str] = []
    event_contract = artifact.get("event_contract")
    if not isinstance(event_contract, dict):
        return ["event_contract_missing_or_invalid"]
    if event_contract.get("event_category") != contract.event_category:
        errors.append("event_contract_category_mismatch")
    expected_type = PHASE6_EVENT_TYPES.get(contract.event_category)
    if event_contract.get("event_type") != expected_type:
        errors.append("event_contract_type_mismatch")
    if event_contract.get("event_log_required") is not True:
        errors.append("event_contract_log_not_required")
    if event_contract.get("append_only") is not True:
        errors.append("event_contract_not_append_only")
    if event_contract.get("supersession_required_for_change") is not True:
        errors.append("event_contract_supersession_not_required")
    for field in ("raw_secret_exposed", "raw_payload_exposed"):
        if event_contract.get(field) is not False:
            errors.append(f"event_contract_exposure_enabled:{field}")
    return errors


def _boundary_errors(artifact: dict[str, Any]) -> list[str]:
    boundary = str(artifact.get("boundary") or "")
    lowered = boundary.lower()
    if len(boundary.strip()) < 40:
        return ["boundary_weak_or_missing"]
    if "cannot" not in lowered:
        return ["boundary_weak_or_missing"]
    if not any(
        term in lowered
        for term in ("write", "mutate", "enable", "approve", "create", "update", "grant", "apply", "infer")
    ):
        return ["boundary_weak_or_missing"]
    return []


def _specific_errors(artifact: dict[str, Any], *, expected_stage: str) -> list[str]:
    artifact_type = str(artifact.get("artifact_type") or "")
    errors: list[str] = []
    if expected_stage != "Q6-1":
        return errors
    if artifact_type == "learning_source_inventory":
        if artifact.get("source_inventory_write_allowed") is not False:
            errors.append("source_inventory_write_allowed_in_q6_1")
    if artifact_type in ("closed_trade_outcome", "postmortem_draft", "learning_approval_record"):
        if artifact.get("learning_write_allowed") is not False:
            errors.append(f"learning_write_allowed_in_q6_1:{artifact_type}")
    if artifact_type == "postmortem_packet":
        if artifact.get("assertion_source_refs_required") is not True:
            errors.append("postmortem_packet_assertion_refs_not_required")
        if artifact.get("uncited_conclusion_allowed") is not False:
            errors.append("uncited_conclusion_allowed")
    if artifact_type == "postmortem_analysis_packet":
        if artifact.get("all_claims_cited") is not True:
            errors.append("analysis_claims_uncited")
    if artifact_type == "postmortem_review":
        if artifact.get("write_allowed") is not False:
            errors.append("postmortem_review_write_allowed_in_q6_1")
    if artifact_type == "outcome_link":
        if artifact.get("link_write_allowed") is not False:
            errors.append("outcome_link_write_allowed_in_q6_1")
    if artifact_type == "knowledge_graph_staged_write":
        if artifact.get("staged_write_allowed") is not False:
            errors.append("kg_staged_write_allowed_in_q6_1")
    if artifact_type == "knowledge_graph_read_view":
        if artifact.get("write_allowed") is not False:
            errors.append("kg_read_view_write_allowed_in_q6_1")
    if artifact_type in ("model_weight_update_proposal", "trust_score_update_proposal"):
        if artifact.get("apply_allowed") is not False:
            errors.append(f"proposal_apply_allowed_in_q6_1:{artifact_type}")
    if artifact_type == "shadow_strategy_replay":
        if artifact.get("trade_candidate_creation_allowed") is not False:
            errors.append("shadow_replay_trade_candidate_creation_allowed")
        if artifact.get("order_creation_allowed") is not False:
            errors.append("shadow_replay_order_creation_allowed")
    if artifact_type == "architect_learning_summary":
        if artifact.get("policy_mutation_allowed") is not False:
            errors.append("architect_policy_mutation_allowed_in_q6_1")
    if artifact_type == "cockpit_learning_visibility":
        if artifact.get("backend_derived") is not True:
            errors.append("cockpit_visibility_not_backend_derived")
        if int(artifact.get("ui_inferred_readiness_count", 0) or 0) != 0:
            errors.append("cockpit_ui_inferred_readiness")
    if artifact_type == "phase6_certification":
        if artifact.get("phase6_certified") is not False:
            errors.append("phase6_certified_in_q6_1")
        if artifact.get("phase7_demo_proof_planning_allowed") is not False:
            errors.append("phase7_demo_proof_planning_allowed_in_q6_1")
        if artifact.get("phase7_proof_credit_allowed") is not False:
            errors.append("phase7_proof_credit_allowed_in_q6_1")
    return errors


def validate_phase6_event_contracts(contracts: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for category in PHASE6_REQUIRED_EVENT_CATEGORIES:
        contract = contracts.get(category)
        if not isinstance(contract, dict):
            errors.append(f"event_contract_missing:{category}")
            continue
        if contract.get("event_type") != PHASE6_EVENT_TYPES[category]:
            errors.append(f"event_contract_type_mismatch:{category}")
        if contract.get("event_log_required") is not True:
            errors.append(f"event_contract_log_not_required:{category}")
        if contract.get("append_only") is not True:
            errors.append(f"event_contract_not_append_only:{category}")
        if contract.get("supersession_required_for_change") is not True:
            errors.append(f"event_contract_supersession_not_required:{category}")
    return errors


def validate_phase6_artifact(
    artifact: dict[str, Any],
    *,
    expected_stage: str = "Q6-1",
    allowed_authority_fields: tuple[str, ...] = (),
) -> list[str]:
    errors: list[str] = []
    artifact_type = str(artifact.get("artifact_type"))
    contract = phase6_contract_by_type().get(artifact_type)
    if contract is None:
        return [f"unknown_artifact_type:{artifact.get('artifact_type')}"]

    for field in contract.required_fields:
        if field not in artifact:
            errors.append(f"missing_field:{artifact_type}:{field}")
    if artifact.get("schema_version") != PHASE6_ARTIFACT_SCHEMA_VERSION:
        errors.append(f"schema_version_mismatch:{artifact_type}")
    if artifact.get("phase") != "Q6":
        errors.append(f"phase_mismatch:{artifact_type}")
    if artifact.get("stage") != expected_stage:
        errors.append(f"stage_mismatch:{artifact_type}")
    if artifact.get("status") not in contract.allowed_statuses:
        errors.append(f"status_invalid:{artifact_type}:{artifact.get('status')}")
    if artifact.get("public_safe") is not True:
        errors.append(f"public_safe_not_true:{artifact_type}")
    if artifact.get("event_log_required") is not True:
        errors.append(f"event_log_required_not_true:{artifact_type}")
    if not isinstance(artifact.get("event_log_written"), bool):
        errors.append(f"event_log_written_not_bool:{artifact_type}")
    errors.extend(_boundary_errors(artifact))
    errors.extend(_authority_errors(artifact, allowed_authority_fields=allowed_authority_fields))
    errors.extend(_unsafe_counter_errors(artifact))
    errors.extend(_source_posture_errors(artifact))
    errors.extend(_provenance_errors(artifact))
    errors.extend(_event_contract_errors(artifact, contract))
    errors.extend(_specific_errors(artifact, expected_stage=expected_stage))
    return sorted(set(errors))


def phase6_artifact_bundle_summary(artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    seen = Counter(str(artifact.get("artifact_type")) for artifact in artifacts)
    missing_types = [
        artifact_type
        for artifact_type in PHASE6_ARTIFACT_TYPES
        if seen.get(artifact_type, 0) == 0
    ]
    duplicate_types = [
        artifact_type
        for artifact_type, count in seen.items()
        if artifact_type in PHASE6_ARTIFACT_TYPES and count > 1
    ]
    for artifact in artifacts:
        errors.extend(validate_phase6_artifact(artifact))
    for artifact_type in missing_types:
        errors.append(f"missing_artifact_type:{artifact_type}")
    for artifact_type in duplicate_types:
        errors.append(f"duplicate_artifact_type:{artifact_type}")
    event_contract_errors = validate_phase6_event_contracts(phase6_event_contracts())
    errors.extend(event_contract_errors)

    authority_enabled_count = sum(
        1
        for artifact in artifacts
        for field in PHASE6_AUTHORITY_FIELDS
        if artifact.get(field) is not False
    )
    unsafe_counter_total = sum(
        int(artifact.get(field, 0) or 0)
        for artifact in artifacts
        for field in PHASE6_UNSAFE_COUNT_FIELDS
    )

    return {
        "status": "ok" if not errors else "error",
        "schema_version": PHASE6_ARTIFACT_SCHEMA_VERSION,
        "artifact_count": len(artifacts),
        "artifact_type_count": len(PHASE6_ARTIFACT_TYPES),
        "status_enum_count": len(PHASE6_STATUS_ENUMS),
        "authority_field_count": len(PHASE6_AUTHORITY_FIELDS),
        "unsafe_counter_field_count": len(PHASE6_UNSAFE_COUNT_FIELDS),
        "event_contract_count": len(PHASE6_REQUIRED_EVENT_CATEGORIES),
        "missing_artifact_types": missing_types,
        "duplicate_artifact_types": duplicate_types,
        "error_count": len(errors),
        "errors": errors,
        "authority_enabled_count": authority_enabled_count,
        "unsafe_counter_total": unsafe_counter_total,
        "source_posture_status": "validated" if not errors else "error",
        "provenance_status": "validated" if not errors else "error",
        "event_contract_status": "validated" if not event_contract_errors else "error",
        "boundary": (
            "Q6-1 validates Learning Loop artifact shapes only. Later Q6 stages "
            "must explicitly grant and verify any non-default learning authority."
        ),
    }
