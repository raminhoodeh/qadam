"""Phase 4 Resource Registry validation.

The Resource Registry is a non-live reference layer. Phase 4 may classify
resources for strategy drafting, but registry entries cannot become market
observations, trade candidates, approvals, orders, broker truth, or live capital
authority.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.phase4_artifacts import (
    PHASE4_ARTIFACT_SCHEMA_VERSION,
    phase4_authority_boundary,
    validate_phase4_artifact,
)
from orchestrator.resource_registry import resource_registry


RESOURCE_VALIDATION_SCHEMA_VERSION = 1

RESOURCE_VALIDATION_STATUSES: tuple[str, ...] = (
    "validated_strategy_reference",
    "architecture_reference",
    "provisional_reference",
    "rejected_reference",
    "private_foundational_prior",
)

ACTIVE_STRATEGY_REFERENCE_STATUSES: tuple[str, ...] = (
    "validated_strategy_reference",
    "provisional_reference",
)

RESOURCE_REFERENCE_AUTHORITY_FLAGS: tuple[str, ...] = (
    "live_observation_authority",
    "signal_authority",
    "trade_candidate_creation_allowed",
    "risk_approval_authority",
    "execution_authority",
    "paper_order_authority",
    "broker_write_authority",
    "fill_confirmation_authority",
    "receipt_evidence_authority",
    "reconciliation_truth_authority",
    "live_capital_authority",
    "quantum_provider_call_allowed",
    "quantum_hardware_submission_allowed",
    "scheduler_enabled",
)

CATEGORY_STATUS_POLICY: dict[str, str] = {
    "strategy_guardrail": "validated_strategy_reference",
    "analytical_framework": "validated_strategy_reference",
    "prediction_market_paper": "validated_strategy_reference",
    "ai_architecture": "architecture_reference",
    "technical_infrastructure": "architecture_reference",
    "supplemental_data_plane": "architecture_reference",
    "prediction_market_stack": "architecture_reference",
    "osint_reference": "architecture_reference",
    "signal_benchmark": "provisional_reference",
    "product_positioning": "provisional_reference",
    "private_world_model": "private_foundational_prior",
}


@dataclass(frozen=True)
class ResourceValidationRow:
    resource_key: str
    name: str
    category: str
    source: str
    role: str
    original_validation_status: str
    phase4_validation_status: str
    phase4_reference_role: str
    production_active: bool
    active_strategy_reference: bool
    strategy_provenance_allowed: bool
    public_strategy_document_allowed: bool
    private_world_model: bool
    non_live_reference: bool
    mapped_modules: tuple[str, ...]
    module_mapping_count: int
    decision_notes: str
    decision_note_present: bool
    risk_boundary: str
    rejection_reasons: tuple[str, ...]
    authority_flags: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["mapped_modules"] = list(self.mapped_modules)
        payload["rejection_reasons"] = list(self.rejection_reasons)
        return payload


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _authority_flags() -> dict[str, bool]:
    return {flag: False for flag in RESOURCE_REFERENCE_AUTHORITY_FLAGS}


def _classification_status(resource: dict[str, Any]) -> str:
    category = str(resource.get("category") or "")
    original_status = str(resource.get("validation_status") or "provisional_reference")
    if category == "private_world_model" or original_status == "foundational_prior":
        return "private_foundational_prior"
    if original_status in {"validated_strategy_reference", "architecture_reference", "rejected_reference"}:
        return original_status
    return CATEGORY_STATUS_POLICY.get(category, "provisional_reference")


def _reference_role(status: str) -> str:
    return {
        "validated_strategy_reference": "strategy_reference_candidate",
        "architecture_reference": "architecture_design_reference",
        "provisional_reference": "provisional_strategy_reference_candidate",
        "rejected_reference": "excluded_from_strategy_provenance",
        "private_foundational_prior": "private_world_model_prior",
    }[status]


def _risk_boundary(resource: dict[str, Any], status: str) -> str:
    category = str(resource.get("category") or "")
    if status == "rejected_reference":
        return "Rejected references cannot appear in active strategy provenance."
    if status == "private_foundational_prior" or category == "private_world_model":
        return (
            "Private world-model material can shape hypotheses only. It is not live evidence, "
            "cannot appear as factual public strategy provenance, and requires source corroboration."
        )
    if category == "strategy_guardrail":
        return (
            "Strategy guardrails can constrain draft strategy posture only. They cannot create "
            "signals, trade candidates, approvals, orders, or live-capital authority."
        )
    if category == "analytical_framework":
        return (
            "Analytical frameworks can structure review notes only. They require observed source "
            "evidence before influencing any approved-shadow strategy."
        )
    if category == "prediction_market_paper":
        return (
            "Prediction-market papers can inform modelling assumptions only. They cannot authorize "
            "market access, orders, broker writes, or execution."
        )
    if category in {"prediction_market_stack", "technical_infrastructure"}:
        return (
            "Tool and infrastructure references are architecture inputs only. They grant no "
            "credentials, broker writes, order routing, retries, scheduler authority, or live capital."
        )
    if category == "supplemental_data_plane":
        return (
            "Supplemental data-plane references can structure discovery, provenance, and context checks only. "
            "They are not canonical sources, cannot source-wash upstream feeds, and cannot change canonical "
            "source rank without a separate upstream-source registry decision."
        )
    if category == "ai_architecture":
        return (
            "AI architecture references can inform experiment design only. They must be tested "
            "against read-only evidence before any strategy document relies on their outputs."
        )
    if category == "osint_reference":
        return (
            "OSINT references can inform monitoring design only. They are not live observations "
            "unless represented through the Source Registry and durable replay."
        )
    if category == "signal_benchmark":
        return (
            "Signal benchmarks can inform UX and comparison notes only. They are not evidence of "
            "market truth and cannot rank or promote active strategies."
        )
    if category == "product_positioning":
        return (
            "Product-positioning references can inform presentation only. They cannot influence "
            "source confidence, strategy approval, or execution readiness."
        )
    return "Resource Registry references are non-live context only and require corroboration before strategy use."


def _row_from_resource(resource: dict[str, Any]) -> ResourceValidationRow:
    status = _classification_status(resource)
    mapped_modules = tuple(str(module) for module in resource.get("mapped_modules", ()))
    decision_notes = str(resource.get("decision_notes") or "").strip()
    private_world_model = status == "private_foundational_prior" or resource.get("category") == "private_world_model"
    production_active = bool(resource.get("production_active"))
    active_strategy_reference = production_active
    strategy_provenance_allowed = status in ACTIVE_STRATEGY_REFERENCE_STATUSES
    public_strategy_document_allowed = not private_world_model and status != "rejected_reference"
    rejection_reasons: tuple[str, ...] = ()
    if status == "rejected_reference":
        rejection_reasons = ("phase4_rejected_reference",)
    return ResourceValidationRow(
        resource_key=str(resource["key"]),
        name=str(resource.get("name") or resource["key"]),
        category=str(resource.get("category") or "uncategorized"),
        source=str(resource.get("source") or "unknown"),
        role=str(resource.get("role") or ""),
        original_validation_status=str(resource.get("validation_status") or "provisional_reference"),
        phase4_validation_status=status,
        phase4_reference_role=_reference_role(status),
        production_active=production_active,
        active_strategy_reference=active_strategy_reference,
        strategy_provenance_allowed=strategy_provenance_allowed,
        public_strategy_document_allowed=public_strategy_document_allowed,
        private_world_model=private_world_model,
        non_live_reference=True,
        mapped_modules=mapped_modules,
        module_mapping_count=len(mapped_modules),
        decision_notes=decision_notes,
        decision_note_present=bool(decision_notes),
        risk_boundary=_risk_boundary(resource, status),
        rejection_reasons=rejection_reasons,
        authority_flags=_authority_flags(),
    )


def build_resource_validation(settings: Settings | None = None) -> dict[str, Any]:
    rows = [_row_from_resource(resource) for resource in resource_registry()]
    row_dicts = [row.to_dict() for row in rows]
    status_counts = Counter(row.phase4_validation_status for row in rows)
    active_rows = [row for row in rows if row.active_strategy_reference]
    authority_violations = [
        f"{row.resource_key}:{flag}"
        for row in rows
        for flag, enabled in row.authority_flags.items()
        if enabled is not False
    ]
    artifact = {
        "schema_version": PHASE4_ARTIFACT_SCHEMA_VERSION,
        "resource_validation_schema_version": RESOURCE_VALIDATION_SCHEMA_VERSION,
        "artifact_type": "resource_validation",
        "artifact_id": "phase4:q4-5:resource-registry-validation",
        "status": "validated" if not authority_violations else "rejected",
        "generated_at": _now(),
        "public_safe": True,
        "authority_boundary": phase4_authority_boundary(),
        "boundary": "Resource Registry entries are non-live references, not live observations or execution authority.",
        "resource_count": len(rows),
        "validated_resource_count": status_counts["validated_strategy_reference"],
        "architecture_reference_count": status_counts["architecture_reference"],
        "provisional_resource_count": status_counts["provisional_reference"],
        "rejected_reference_count": status_counts["rejected_reference"],
        "private_foundational_prior_count": status_counts["private_foundational_prior"],
        "active_strategy_reference_count": len(active_rows),
        "manifested_strategy_document_present": False,
        "resource_entries_are_live_observations": False,
        "authority_flag_violation_count": len(authority_violations),
        "authority_flag_violations": authority_violations,
        "validation_statuses": list(RESOURCE_VALIDATION_STATUSES),
        "resource_rows": row_dicts,
        "status_counts": dict(sorted(status_counts.items())),
        "capability_considerations": [
            {
                "key": "yahoo_finance_api",
                "name": "Yahoo Finance API",
                "resource_registry_entry": False,
                "classification": "supplemental_market_confirmation_capability",
                "canonical_rank_impact_allowed": False,
                "live_observation_authority": False,
                "strategy_provenance_allowed": False,
                "boundary": (
                    "Yahoo Finance remains a supplemental market-confirmation capability. It is not "
                    "a Resource Registry entry, does not validate registry references, and cannot "
                    "provide broker, order, receipt, reconciliation, or live-capital truth."
                ),
            },
            {
                "key": "preference_mcp",
                "name": "Preference / PREF MCP",
                "resource_registry_entry": True,
                "classification": "supplemental_multi_source_data_plane_reference",
                "canonical_rank_impact_allowed": False,
                "live_observation_authority": False,
                "strategy_provenance_allowed": False,
                "source_quorum_credit_allowed": False,
                "boundary": (
                    "Preference is registered as a supplemental data-plane reference, not as source 36. "
                    "It can inform status, catalog, and provenance checks, but cannot validate active "
                    "strategy provenance, satisfy source quorum, or affect canonical trust rank unless a "
                    "specific upstream source is separately promoted."
                ),
            },
        ],
        "trade_candidate_creation_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
    }
    artifact["validation_errors"] = validate_resource_validation(artifact)
    return artifact


def validate_resource_validation(artifact: dict[str, Any]) -> list[str]:
    errors = list(validate_phase4_artifact(artifact))
    if artifact.get("artifact_type") != "resource_validation":
        errors.append("artifact_type_not_resource_validation")
    if artifact.get("resource_entries_are_live_observations") is not False:
        errors.append("resource_entries_marked_live_observations")

    rows = artifact.get("resource_rows")
    if not isinstance(rows, list):
        errors.append("resource_rows_missing")
        rows = []
    if artifact.get("resource_count") != len(rows):
        errors.append("resource_count_mismatch")

    actual_counts = Counter(str(row.get("phase4_validation_status")) for row in rows)
    for status in RESOURCE_VALIDATION_STATUSES:
        if actual_counts.get(status, 0) != int(artifact.get(_count_field(status), 0)):
            errors.append(f"status_count_mismatch:{status}")

    active_count = sum(1 for row in rows if row.get("active_strategy_reference") is True)
    if active_count != artifact.get("active_strategy_reference_count"):
        errors.append("active_strategy_reference_count_mismatch")

    for row in rows:
        resource_key = str(row.get("resource_key") or "unknown_resource")
        status = str(row.get("phase4_validation_status") or "")
        if status not in RESOURCE_VALIDATION_STATUSES:
            errors.append(f"resource_status_invalid:{resource_key}:{status}")
        if row.get("non_live_reference") is not True:
            errors.append(f"resource_not_non_live_reference:{resource_key}")
        if not row.get("mapped_modules"):
            errors.append(f"resource_missing_module_mapping:{resource_key}")
        if row.get("decision_note_present") is not True:
            errors.append(f"resource_missing_decision_note:{resource_key}")
        if not str(row.get("risk_boundary") or "").strip():
            errors.append(f"resource_missing_risk_boundary:{resource_key}")

        active = row.get("active_strategy_reference") is True
        if active and status not in ACTIVE_STRATEGY_REFERENCE_STATUSES:
            errors.append(f"active_strategy_reference_status_invalid:{resource_key}:{status}")
        if active and not row.get("mapped_modules"):
            errors.append(f"active_reference_missing_module_mapping:{resource_key}")
        if active and row.get("decision_note_present") is not True:
            errors.append(f"active_reference_missing_decision_note:{resource_key}")
        if active and not str(row.get("risk_boundary") or "").strip():
            errors.append(f"active_reference_missing_risk_boundary:{resource_key}")
        if status == "rejected_reference" and active:
            errors.append(f"rejected_resource_active_strategy_provenance:{resource_key}")
        if status == "rejected_reference" and row.get("strategy_provenance_allowed") is not False:
            errors.append(f"rejected_resource_strategy_provenance_allowed:{resource_key}")

        private_world_model = row.get("private_world_model") is True
        if private_world_model and status != "private_foundational_prior":
            errors.append(f"private_world_model_status_invalid:{resource_key}:{status}")
        if private_world_model and row.get("strategy_provenance_allowed") is not False:
            errors.append(f"private_world_model_strategy_provenance_allowed:{resource_key}")
        if private_world_model and row.get("public_strategy_document_allowed") is not False:
            errors.append(f"private_world_model_public_strategy_allowed:{resource_key}")

        flags = row.get("authority_flags")
        if not isinstance(flags, dict):
            errors.append(f"resource_authority_flags_missing:{resource_key}")
            continue
        for flag in RESOURCE_REFERENCE_AUTHORITY_FLAGS:
            if flags.get(flag) is not False:
                errors.append(f"resource_authority_enabled:{resource_key}:{flag}")
        if private_world_model and flags.get("live_observation_authority") is not False:
            errors.append(f"private_world_model_live_authority:{resource_key}")

    for consideration in artifact.get("capability_considerations", []):
        key = consideration.get("key", "unknown_capability")
        if key == "yahoo_finance_api":
            if consideration.get("resource_registry_entry") is not False:
                errors.append("yahoo_finance_marked_resource_registry_entry")
            if consideration.get("canonical_rank_impact_allowed") is not False:
                errors.append("yahoo_finance_canonical_rank_impact_allowed")
            if consideration.get("live_observation_authority") is not False:
                errors.append("yahoo_finance_live_observation_authority")
        if key == "preference_mcp":
            if consideration.get("resource_registry_entry") is not True:
                errors.append("preference_mcp_resource_registry_entry_missing")
            if consideration.get("canonical_rank_impact_allowed") is not False:
                errors.append("preference_mcp_canonical_rank_impact_allowed")
            if consideration.get("live_observation_authority") is not False:
                errors.append("preference_mcp_live_observation_authority")
            if consideration.get("strategy_provenance_allowed") is not False:
                errors.append("preference_mcp_strategy_provenance_allowed")
            if consideration.get("source_quorum_credit_allowed") is not False:
                errors.append("preference_mcp_source_quorum_credit_allowed")

    for key in (
        "trade_candidate_creation_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
    ):
        if artifact.get(key) is not False:
            errors.append(f"artifact_authority_enabled:{key}")
    if artifact.get("authority_flag_violation_count") != 0:
        errors.append("authority_flag_violations_present")
    return errors


def _count_field(status: str) -> str:
    return {
        "validated_strategy_reference": "validated_resource_count",
        "architecture_reference": "architecture_reference_count",
        "provisional_reference": "provisional_resource_count",
        "rejected_reference": "rejected_reference_count",
        "private_foundational_prior": "private_foundational_prior_count",
    }[status]


def write_resource_validation(
    artifact: dict[str, Any],
    path: str | Path | None = None,
    *,
    settings: Settings | None = None,
) -> Path:
    output_path = Path(path or (_runtime_dir(settings) / "phase4_resource_validation.json"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path
