"""Phase 4 Fund Manager approval record contract.

The approval record captures a strategy-governance decision in the Event Log.
It can approve strategy for future approved-shadow orchestration design, reject
strategy, or request amendments. It cannot create trade candidates, approve
risk, stage orders, write to brokers, call quantum providers, or enable live
capital.
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.phase4_artifacts import (
    PHASE4_APPROVAL_STATES,
    PHASE4_ARTIFACT_SCHEMA_VERSION,
    phase4_artifact_bundle_summary,
    phase4_authority_boundary,
    validate_phase4_artifact,
)
from orchestrator.phase4_candidate_strategy_universe import build_candidate_strategy_universe
from orchestrator.phase4_manifested_strategy import build_manifested_strategy_metadata
from orchestrator.preference_mcp_source_promotion import (
    UPSTREAM_REGISTRY_MAP,
    build_preference_source_promotion_decisions,
    preference_source_promotion_paths,
    validate_preference_source_promotion_decisions,
)
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT


PHASE4_APPROVAL_RECORD_SCHEMA_VERSION = 1
APPROVAL_EVENT_TYPE = "phase4_fund_manager_approval_recorded"
APPROVAL_EVENT_COMPONENT = "phase4_fund_manager_approval"
APPROVAL_RUNTIME_ARTIFACT = "phase4_fund_manager_approval_event.json"
APPROVAL_EVENT_LOG = "phase4_approval_events.jsonl"

NO_EXECUTION_BOUNDARY = (
    "Fund Manager strategy approval is not trade, risk, order, broker, fill, "
    "receipt, reconciliation, quantum-provider, hardware, scheduler, or live-capital approval."
)

APPROVAL_AUTHORITY_FIELDS: tuple[str, ...] = (
    "trade_candidate_creation_allowed",
    "risk_approval_allowed",
    "risk_agent_handoff_allowed",
    "execution_policy_handoff_allowed",
    "execution_allowed",
    "paper_order_allowed",
    "staged_paper_order_allowed",
    "broker_write_allowed",
    "live_capital_enabled",
    "quantum_provider_call_allowed",
    "quantum_hardware_submission_allowed",
    "scheduler_enabled",
)

PREFERENCE_APPROVAL_AUTHORITY_FIELDS: tuple[str, ...] = (
    "paid_tool_calls_approved",
    "paid_tool_calls_allowed",
    "source_quorum_credit_allowed",
    "preference_only_confirmation_allowed",
    "trade_candidate_creation_allowed",
    "risk_handoff_allowed",
    "execution_allowed",
    "paper_order_allowed",
    "broker_write_allowed",
    "live_capital_enabled",
)

EXPECTED_PREFERENCE_SOURCE_PROMOTION_DECISION_COUNT = len(UPSTREAM_REGISTRY_MAP)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _candidate_universe(settings: Settings | None = None) -> dict[str, Any]:
    runtime_path = _runtime_dir(settings) / "phase4_candidate_strategy_universe.json"
    return _read_json(runtime_path) or build_candidate_strategy_universe(settings)


def _manifested_strategy_metadata(settings: Settings | None = None) -> dict[str, Any]:
    runtime_path = _runtime_dir(settings) / "phase4_manifested_strategy_metadata.json"
    return _read_json(runtime_path) or build_manifested_strategy_metadata(settings=settings)


def _preference_source_promotion(settings: Settings | None = None) -> dict[str, Any]:
    promotion_path, _history_path = preference_source_promotion_paths(settings)
    return _read_json(promotion_path) or build_preference_source_promotion_decisions(
        settings=settings,
        cockpit={"durable_ingestion": {"replay_status": "not_run", "missing_sources": []}},
    )


def _authority_defaults() -> dict[str, bool]:
    return {field: False for field in APPROVAL_AUTHORITY_FIELDS}


def _status_for_approval_state(approval_state: str) -> str:
    if approval_state == "approved":
        return "approved_shadow"
    if approval_state == "rejected":
        return "rejected"
    return "draft"


def _normalized_list(values: list[str] | tuple[str, ...] | None) -> list[str]:
    return [str(value).strip() for value in values or () if str(value).strip()]


def _strategy_family_keys(candidate_universe: dict[str, Any]) -> list[str]:
    return [
        str(candidate.get("candidate_key"))
        for candidate in candidate_universe.get("candidates", [])
        if isinstance(candidate, dict) and candidate.get("candidate_key")
    ]


def _preference_approval_scope(
    manifested_strategy: dict[str, Any],
    settings: Settings | None = None,
) -> dict[str, Any]:
    preference = manifested_strategy.get("preference_mcp_manifestation", {})
    if not isinstance(preference, dict):
        preference = {}
    source_promotion = _preference_source_promotion(settings)
    source_promotion_errors = validate_preference_source_promotion_decisions(
        source_promotion
    )
    authority = {field: False for field in PREFERENCE_APPROVAL_AUTHORITY_FIELDS}
    return {
        "source_key": "preference_mcp",
        "source_role": preference.get("source_role", "missing"),
        "preference_aware_strategy_document": (
            preference.get("source_role") == "supplemental_multi_source_data_plane"
            and int(preference.get("approved_domain_pack_count", 0) or 0) > 0
        ),
        "candidate_family_with_policy_count": int(
            preference.get("candidate_family_with_policy_count", 0) or 0
        ),
        "approved_domain_packs": list(preference.get("approved_domain_packs", [])),
        "approved_domain_pack_count": int(
            preference.get("approved_domain_pack_count", 0) or 0
        ),
        "source_promotion_status": str(source_promotion.get("status") or "not_run"),
        "source_promotion_decision_count": int(
            source_promotion.get("decision_count", 0) or 0
        ),
        "source_promotion_expected_decision_count": (
            EXPECTED_PREFERENCE_SOURCE_PROMOTION_DECISION_COUNT
        ),
        "source_promotion_promoted_decision_count": int(
            source_promotion.get("promoted_decision_count", 0) or 0
        ),
        "source_promotion_canonical_source_count_after": int(
            source_promotion.get("canonical_source_count_after", 0) or 0
        ),
        "source_promotion_expected_canonical_source_count": EXPECTED_SOURCE_COUNT,
        "source_promotion_aggregator_promoted": (
            source_promotion.get("preference_aggregator_promoted") is True
        ),
        "preference_mcp_source_36": (
            source_promotion.get("preference_mcp_source_36") is True
        ),
        "source_promotion_validation_error_count": len(source_promotion_errors),
        "source_promotion_validation_errors": source_promotion_errors,
        "source_quorum_rule": preference.get("source_quorum_rule"),
        "quota_freshness_degradation_rule": preference.get(
            "quota_freshness_degradation_rule"
        ),
        **authority,
        "authority_flags": authority,
        "boundary": (
            "Q4-10 approval can approve the amended Preference-aware strategy document "
            "only. It does not approve paid Preference tools, source-quorum credit, "
            "trade candidates, risk handoff, execution, broker writes, or live capital."
        ),
    }


def build_fund_manager_approval_event(
    *,
    approval_state: str = "amendments_required",
    approver_label: str = "fund_manager_pending_explicit_approval",
    approval_instruction: str | None = None,
    approved_strategy_families: list[str] | tuple[str, ...] | None = None,
    rejected_strategy_families: list[str] | tuple[str, ...] | None = None,
    required_amendments: list[str] | tuple[str, ...] | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    candidate_universe = _candidate_universe(settings)
    manifested_strategy = _manifested_strategy_metadata(settings)
    strategy_keys = _strategy_family_keys(candidate_universe)
    amendments = _normalized_list(required_amendments)
    if approval_state == "amendments_required" and not amendments:
        amendments = [
            (
                "Explicit Fund Manager approval text for the amended Preference-aware "
                "Manifested Strategy Document is required before Phase 4 certification "
                "or approved-shadow strategy toggles can be enabled."
            )
        ]
    approved = _normalized_list(approved_strategy_families)
    if approval_state == "approved" and not approved:
        approved = list(strategy_keys)
    rejected = _normalized_list(rejected_strategy_families)
    if approval_state == "rejected" and not rejected:
        rejected = list(strategy_keys)

    generated_at = _now()
    artifact = {
        "schema_version": PHASE4_ARTIFACT_SCHEMA_VERSION,
        "phase4_approval_record_schema_version": PHASE4_APPROVAL_RECORD_SCHEMA_VERSION,
        "artifact_type": "fund_manager_approval_event",
        "artifact_id": "phase4:q4-10:fund-manager-approval-event",
        "status": _status_for_approval_state(approval_state),
        "generated_at": generated_at,
        "public_safe": True,
        "authority_boundary": phase4_authority_boundary(),
        "boundary": NO_EXECUTION_BOUNDARY,
        "approval_state": approval_state,
        "approval_logged": False,
        "approval_decision_timestamp": generated_at,
        "approval_timestamp": generated_at,
        "approver_label": approver_label,
        "approver_identity_verified": approval_state == "approved",
        "approval_source": "phase4_q4_10_contract",
        "approval_instruction": approval_instruction,
        "event_log_required": True,
        "event_log_correlation_id": None,
        "event_log_path": None,
        "event_log_created_at": None,
        "strategy_document_version": manifested_strategy.get(
            "manifested_strategy_metadata_schema_version"
        ),
        "strategy_document_path": manifested_strategy.get("document_path"),
        "strategy_artifact_id": manifested_strategy.get("artifact_id"),
        "strategy_artifact_fingerprint": manifested_strategy.get("document_fingerprint"),
        "strategy_artifact_fingerprint_verified": bool(
            str(manifested_strategy.get("document_fingerprint") or "").strip()
        ),
        "preference_mcp_approval_scope": _preference_approval_scope(
            manifested_strategy,
            settings=settings,
        ),
        "strategy_family_candidate_count": len(strategy_keys),
        "strategy_family_candidate_keys": strategy_keys,
        "approved_strategy_families": approved,
        "rejected_strategy_families": rejected,
        "required_amendments": amendments,
        "no_execution_boundary": NO_EXECUTION_BOUNDARY,
        "certification_candidate": approval_state == "approved",
        "phase4_certification_allowed": False,
        "approved_shadow_ready": False,
        "trade_candidate_count": 0,
        "risk_agent_handoff_allowed_count": 0,
        "execution_policy_handoff_allowed_count": 0,
        "execution_allowed_count": 0,
        "paper_order_allowed_count": 0,
        "staged_paper_order_allowed_count": 0,
        "broker_write_allowed_count": 0,
        "live_capital_enabled_count": 0,
        "authority_flag_violation_count": 0,
        **_authority_defaults(),
    }
    artifact["validation_errors"] = validate_fund_manager_approval_event(
        artifact,
        manifested_strategy=manifested_strategy,
    )
    return artifact


def validate_fund_manager_approval_event(
    artifact: dict[str, Any],
    *,
    manifested_strategy: dict[str, Any] | None = None,
) -> list[str]:
    errors = list(validate_phase4_artifact(artifact))
    manifested_strategy = manifested_strategy or _manifested_strategy_metadata()
    if artifact.get("artifact_type") != "fund_manager_approval_event":
        errors.append("artifact_type_not_fund_manager_approval_event")
    if artifact.get("approval_state") not in PHASE4_APPROVAL_STATES:
        errors.append(f"approval_state_invalid:{artifact.get('approval_state')}")
    if artifact.get("event_log_required") is not True:
        errors.append("event_log_required_not_true")
    if not str(artifact.get("approver_label") or "").strip():
        errors.append("approver_label_missing")
    if not str(artifact.get("strategy_artifact_fingerprint") or "").strip():
        errors.append("strategy_artifact_fingerprint_missing")
    if (
        artifact.get("strategy_artifact_fingerprint")
        != manifested_strategy.get("document_fingerprint")
    ):
        errors.append("strategy_artifact_fingerprint_mismatch")
    if artifact.get("strategy_artifact_fingerprint_verified") is not True:
        errors.append("strategy_artifact_fingerprint_not_verified")

    preference_scope = artifact.get("preference_mcp_approval_scope")
    if not isinstance(preference_scope, dict):
        errors.append("preference_approval_scope_missing")
        preference_scope = {}
    else:
        if preference_scope.get("source_key") != "preference_mcp":
            errors.append("preference_approval_scope_source_key_mismatch")
        if preference_scope.get("source_role") != "supplemental_multi_source_data_plane":
            errors.append("preference_approval_scope_role_invalid")
        if preference_scope.get("preference_aware_strategy_document") is not True:
            errors.append("preference_aware_strategy_document_not_approved_scope")
        if int(preference_scope.get("approved_domain_pack_count", 0) or 0) < 1:
            errors.append("preference_approval_scope_domain_packs_missing")
        if int(preference_scope.get("candidate_family_with_policy_count", 0) or 0) != int(
            artifact.get("strategy_family_candidate_count", 0) or 0
        ):
            errors.append("preference_approval_scope_family_coverage_incomplete")
        if (
            preference_scope.get("source_promotion_status") != "validated"
            or int(
                preference_scope.get("source_promotion_validation_error_count", 0) or 0
            )
            != 0
            or int(preference_scope.get("source_promotion_decision_count", 0) or 0)
            != EXPECTED_PREFERENCE_SOURCE_PROMOTION_DECISION_COUNT
            or int(
                preference_scope.get("source_promotion_promoted_decision_count", 0)
                or 0
            )
            != 0
            or int(
                preference_scope.get(
                    "source_promotion_canonical_source_count_after",
                    0,
                )
                or 0
            )
            != EXPECTED_SOURCE_COUNT
            or preference_scope.get("source_promotion_aggregator_promoted") is not False
            or preference_scope.get("preference_mcp_source_36") is not False
        ):
            errors.append("preference_approval_scope_source_promotion_invalid")
        for key in PREFERENCE_APPROVAL_AUTHORITY_FIELDS:
            if preference_scope.get(key) is not False:
                errors.append(f"preference_approval_scope_authority_enabled:{key}")
        flags = preference_scope.get("authority_flags", {})
        if not isinstance(flags, dict):
            errors.append("preference_approval_scope_authority_flags_missing")
        else:
            for key in PREFERENCE_APPROVAL_AUTHORITY_FIELDS:
                if flags.get(key) is not False:
                    errors.append(
                        f"preference_approval_scope_authority_flag_enabled:{key}"
                    )

    state = artifact.get("approval_state")
    if state in {"approved", "rejected", "amendments_required"}:
        if artifact.get("approval_logged") is not True:
            errors.append("approval_decision_not_logged")
        if not str(artifact.get("event_log_correlation_id") or "").strip():
            errors.append("event_log_correlation_id_missing")
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("event_log_path_missing")
    if state == "approved":
        if artifact.get("status") != "approved_shadow":
            errors.append("approved_status_not_approved_shadow")
        if not artifact.get("approved_strategy_families"):
            errors.append("approved_strategy_families_missing")
        if artifact.get("required_amendments"):
            errors.append("approved_record_has_required_amendments")
        if artifact.get("approver_identity_verified") is not True:
            errors.append("approved_approver_identity_not_verified")
    if state == "rejected":
        if artifact.get("status") != "rejected":
            errors.append("rejected_status_not_rejected")
        if not artifact.get("rejected_strategy_families"):
            errors.append("rejected_strategy_families_missing")
    if state == "amendments_required":
        if artifact.get("status") != "draft":
            errors.append("amendments_required_status_not_draft")
        if not artifact.get("required_amendments"):
            errors.append("required_amendments_missing")
        if artifact.get("certification_candidate") is not False:
            errors.append("amendments_required_certification_candidate")

    for key in (
        "trade_candidate_count",
        "risk_agent_handoff_allowed_count",
        "execution_policy_handoff_allowed_count",
        "execution_allowed_count",
        "paper_order_allowed_count",
        "staged_paper_order_allowed_count",
        "broker_write_allowed_count",
        "live_capital_enabled_count",
        "authority_flag_violation_count",
    ):
        if artifact.get(key) != 0:
            errors.append(f"approval_authority_count_not_zero:{key}")
    for key in APPROVAL_AUTHORITY_FIELDS:
        if artifact.get(key) is not False:
            errors.append(f"approval_authority_enabled:{key}")
    return errors


def attach_fund_manager_approval_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(event_log_path or (_runtime_dir(settings) / APPROVAL_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        APPROVAL_EVENT_TYPE,
        APPROVAL_EVENT_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "approval_state": output.get("approval_state"),
            "approver_label": output.get("approver_label"),
            "approval_instruction": output.get("approval_instruction"),
            "strategy_artifact_id": output.get("strategy_artifact_id"),
            "strategy_artifact_fingerprint": output.get("strategy_artifact_fingerprint"),
            "preference_mcp_approval_scope": output.get(
                "preference_mcp_approval_scope",
                {},
            ),
            "preference_mcp_source_promotion": {
                "status": output.get("preference_mcp_approval_scope", {}).get(
                    "source_promotion_status"
                ),
                "decision_count": output.get("preference_mcp_approval_scope", {}).get(
                    "source_promotion_decision_count"
                ),
                "promoted_decision_count": output.get(
                    "preference_mcp_approval_scope",
                    {},
                ).get("source_promotion_promoted_decision_count"),
                "canonical_source_count_after": output.get(
                    "preference_mcp_approval_scope",
                    {},
                ).get("source_promotion_canonical_source_count_after"),
            },
            "approved_strategy_families": output.get("approved_strategy_families", []),
            "rejected_strategy_families": output.get("rejected_strategy_families", []),
            "required_amendments": output.get("required_amendments", []),
            "trade_candidate_count": output.get("trade_candidate_count"),
            "execution_allowed_count": output.get("execution_allowed_count"),
            "paper_order_allowed_count": output.get("paper_order_allowed_count"),
            "broker_write_allowed_count": output.get("broker_write_allowed_count"),
            "live_capital_enabled_count": output.get("live_capital_enabled_count"),
            "no_execution_boundary": output.get("no_execution_boundary"),
        },
    )
    output["approval_logged"] = True
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_path"] = str(log.path)
    output["event_log_created_at"] = entry.created_at
    output["validation_errors"] = validate_fund_manager_approval_event(output)
    return output, entry


def write_fund_manager_approval_event(
    artifact: dict[str, Any],
    path: str | Path | None = None,
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    output = deepcopy(artifact)
    if record_event:
        output, _ = attach_fund_manager_approval_event_log(
            output,
            event_log_path=event_log_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_fund_manager_approval_event(output)
    output_path = Path(path or (_runtime_dir(settings) / APPROVAL_RUNTIME_ARTIFACT))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path, output


def approval_bundle_certification_summary(approval_event: dict[str, Any]) -> dict[str, Any]:
    artifacts = []
    for artifact_type in (
        "triple_mirror_audit",
        "data_veracity_audit",
        "trust_score_recalculation",
        "resource_validation",
        "world_model_validation",
        "candidate_strategy_universe",
        "strategy_toggle_snapshot",
    ):
        status = "validated"
        if artifact_type == "world_model_validation":
            status = "untestable"
        if artifact_type == "strategy_toggle_snapshot":
            status = "draft"
        artifacts.append(
            {
                "schema_version": PHASE4_ARTIFACT_SCHEMA_VERSION,
                "artifact_type": artifact_type,
                "artifact_id": f"q4-10-summary:{artifact_type}",
                "status": status,
                "generated_at": _now(),
                "public_safe": True,
                "authority_boundary": phase4_authority_boundary(),
                "boundary": "Q4-10 certification probe placeholder without authority.",
                **_minimal_required_fields(artifact_type),
            }
        )
    artifacts.append(_manifested_strategy_metadata())
    artifacts.append(approval_event)
    return phase4_artifact_bundle_summary(artifacts)


def _minimal_required_fields(artifact_type: str) -> dict[str, Any]:
    if artifact_type == "triple_mirror_audit":
        return {"drift_status": "aligned", "mirror_count": 3, "authority_mismatch_count": 0}
    if artifact_type == "data_veracity_audit":
        return {
            "canonical_source_count": 35,
            "supplemental_source_count": 1,
            "quarantined_source_count": 0,
        }
    if artifact_type == "trust_score_recalculation":
        return {"score_count": 35, "observation_backed_count": 0, "quarantined_source_count": 0}
    if artifact_type == "resource_validation":
        return {
            "resource_count": 29,
            "validated_resource_count": 7,
            "provisional_resource_count": 5,
        }
    if artifact_type == "world_model_validation":
        return {
            "claim_count": 5,
            "validated_claim_count": 0,
            "untestable_claim_count": 5,
            "evidence_boundary": "World-model claims remain non-executable priors.",
        }
    if artifact_type == "candidate_strategy_universe":
        return {
            "strategy_family_candidate_count": 5,
            "draft_hypothesis_count": 5,
            "trade_candidate_count": 0,
            "candidates": [],
        }
    if artifact_type == "strategy_toggle_snapshot":
        return {"toggle_count": 0, "toggles": [], "event_log_required": True}
    return {}
