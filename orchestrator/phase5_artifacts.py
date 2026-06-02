"""Phase 5 Layer B artifact contracts.

Q5-1 defines the shapes Layer B will use before any router, risk, staging,
submit, notification, or position-monitor behavior is promoted. These contracts
are schema records only; they do not start orchestration or grant execution
authority.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from world_monitor.source_registry import (
    EXPECTED_SOURCE_COUNT,
    canonical_decision_source_coverage,
)


PHASE5_ARTIFACT_SCHEMA_VERSION = 1

PHASE5_STATUS_ENUMS: tuple[str, ...] = (
    "blocked",
    "hold",
    "eligible",
    "staged",
    "submitted_paper_order",
    "open_position",
    "closed_trade",
    "cancelled",
    "failed_reconciliation",
    "live_blocked",
)

PHASE5_ARTIFACT_TYPES: tuple[str, ...] = (
    "layer_b_authority_ledger",
    "approval_policy_decision",
    "risk_sizing_review",
    "kill_switch_event",
    "execution_intent",
    "execution_adapter_status",
    "staged_paper_order",
    "broker_submit_receipt",
    "telegram_notification",
    "position_state",
    "closed_trade_summary",
    "phase5_certification",
)

PHASE5_AUTHORITY_FIELDS: tuple[str, ...] = (
    "phase5_orchestration_start_allowed",
    "trade_candidate_creation_allowed",
    "approval_policy_router_enabled",
    "risk_agent_approval_authority",
    "kill_switch_mutation_authority",
    "execution_adapter_write_authority",
    "paper_execution_allowed",
    "paper_order_staging_allowed",
    "paper_order_submission_allowed",
    "paper_order_allowed",
    "broker_write_allowed",
    "prediction_market_write_allowed",
    "telegram_live_notifications_allowed",
    "position_monitor_write_authority",
    "live_capital_enabled",
    "live_endpoint_allowed",
    "crypto_perps_write_allowed",
    "paid_preference_tools_allowed",
    "source_quorum_bypass_allowed",
)

PHASE5_COMMON_REQUIRED_FIELDS: tuple[str, ...] = (
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
    "authority_ledger",
    "source_posture",
    "provenance",
    "boundary",
)

PHASE5_SOURCE_POSTURE_REQUIRED_FIELDS: tuple[str, ...] = (
    "canonical_source_required",
    "canonical_source_count",
    "expected_canonical_source_count",
    "canonical_source_keys",
    "canonical_source_coverage_complete",
    "decision_source_coverage",
    "supplemental_source_bypass_allowed",
    "yahoo_finance_role",
    "preference_mcp_role",
    "preference_mcp_source_36",
    "preference_paid_tools_allowed",
    "source_quorum_bypass_allowed",
)

PHASE5_PROVENANCE_REQUIRED_FIELDS: tuple[str, ...] = (
    "source_refs",
    "event_log_required",
    "raw_secret_exposed",
    "raw_payload_exposed",
    "local_path_exposed",
)


@dataclass(frozen=True)
class Phase5ArtifactContract:
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


def phase5_authority_defaults() -> dict[str, bool]:
    return {field: False for field in PHASE5_AUTHORITY_FIELDS}


def phase5_authority_ledger() -> dict[str, Any]:
    defaults = phase5_authority_defaults()
    return {
        "authority_schema_version": PHASE5_ARTIFACT_SCHEMA_VERSION,
        "stage": "Q5-1",
        "authority_field_count": len(PHASE5_AUTHORITY_FIELDS),
        "explicit_authority_grant_count": 0,
        **defaults,
        "boundary": (
            "Q5-1 defines Layer B artifact shapes only. Every authority flag "
            "defaults false until a later Q5 gate explicitly grants and verifies it."
        ),
    }


def phase5_source_posture() -> dict[str, Any]:
    coverage = canonical_decision_source_coverage(coverage_scope="phase5_source_posture")
    return {
        "canonical_source_required": True,
        "canonical_source_count": EXPECTED_SOURCE_COUNT,
        "expected_canonical_source_count": EXPECTED_SOURCE_COUNT,
        "canonical_source_keys": coverage["canonical_source_keys"],
        "canonical_source_coverage_complete": coverage["all_canonical_sources_considered"],
        "decision_source_coverage": coverage,
        "supplemental_source_bypass_allowed": False,
        "yahoo_finance_role": "supplemental_market_confirmation_only",
        "preference_mcp_role": "supplemental_multi_source_data_plane",
        "preference_mcp_source_36": False,
        "preference_paid_tools_allowed": False,
        "source_quorum_bypass_allowed": False,
        "boundary": (
            "Canonical replayable evidence remains required. Yahoo Finance and "
            "Preference/PREF MCP can add context only; neither can bypass source "
            "quorum, create orders, or become canonical by default."
        ),
    }


def phase5_provenance(source_refs: tuple[str, ...] | None = None) -> dict[str, Any]:
    return {
        "source_refs": list(
            source_refs
            or (
                "data/runtime/phase4_certification.json",
                "data/runtime/phase5_layer_b_readiness.json",
            )
        ),
        "event_log_required": True,
        "raw_secret_exposed": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "boundary": (
            "Layer B artifacts must be replayable from explicit source refs and "
            "must not expose secrets, raw private payloads, or local-only paths."
        ),
    }


def phase5_artifact_contracts() -> tuple[Phase5ArtifactContract, ...]:
    common = PHASE5_COMMON_REQUIRED_FIELDS
    return (
        Phase5ArtifactContract(
            artifact_type="layer_b_authority_ledger",
            description="Shared authority ledger for every Layer B artifact.",
            required_fields=common
            + ("authority_field_count", "explicit_authority_grant_count"),
            allowed_statuses=("hold", "blocked"),
            default_status="hold",
            boundary="The authority ledger can describe permissions but cannot grant them in Q5-1.",
        ),
        Phase5ArtifactContract(
            artifact_type="approval_policy_decision",
            description="Deterministic policy decision from approved strategy posture.",
            required_fields=common
            + ("strategy_family_key", "policy_decision", "approved_strategy_toggle_state"),
            allowed_statuses=("blocked", "hold", "eligible"),
            default_status="blocked",
            boundary="Policy decisions cannot create orders, staged orders, receipts, or positions.",
        ),
        Phase5ArtifactContract(
            artifact_type="risk_sizing_review",
            description="Risk Agent paper-sizing review contract.",
            required_fields=common
            + ("risk_decision", "proposed_risk_gbp", "max_risk_gbp", "risk_blockers"),
            allowed_statuses=("blocked", "hold", "eligible"),
            default_status="blocked",
            boundary="Risk sizing can mark paper eligibility only after later gates; it cannot submit orders.",
        ),
        Phase5ArtifactContract(
            artifact_type="kill_switch_event",
            description="Global, strategy, venue, model, or data-source kill-switch event.",
            required_fields=common + ("switch_scope", "switch_state", "actor_label", "reason"),
            allowed_statuses=("blocked", "hold", "cancelled"),
            default_status="hold",
            boundary="Kill switches can block future actions; they cannot enable execution or live capital.",
        ),
        Phase5ArtifactContract(
            artifact_type="execution_intent",
            description="Paper-only execution intent before staging.",
            required_fields=common
            + ("instrument", "side", "quantity", "order_type", "intent_state"),
            allowed_statuses=("blocked", "hold", "eligible", "cancelled"),
            default_status="blocked",
            boundary="Execution intent is not an order and cannot write to a broker.",
        ),
        Phase5ArtifactContract(
            artifact_type="execution_adapter_status",
            description="Read-only venue status, permission, balance, and health contract.",
            required_fields=common + ("venue_key", "venue_mode", "read_health", "write_health"),
            allowed_statuses=("hold", "live_blocked", "blocked", "eligible"),
            default_status="hold",
            boundary="Adapter status is read-only until a later paper-submit gate verifies writes.",
        ),
        Phase5ArtifactContract(
            artifact_type="staged_paper_order",
            description="Staged paper order contract before submit.",
            required_fields=common
            + ("order_state", "idempotency_key", "staging_allowed", "submission_allowed"),
            allowed_statuses=("blocked", "staged", "cancelled", "failed_reconciliation"),
            default_status="blocked",
            boundary="Staging is separate from broker submit and remains disabled in Q5-1.",
        ),
        Phase5ArtifactContract(
            artifact_type="broker_submit_receipt",
            description="Broker submit receipt and idempotency contract.",
            required_fields=common
            + ("receipt_state", "broker_post_called", "paper_order_submitted", "idempotency_key"),
            allowed_statuses=("blocked", "submitted_paper_order", "failed_reconciliation"),
            default_status="blocked",
            boundary="Broker receipts cannot exist before the later paper-submit gate.",
        ),
        Phase5ArtifactContract(
            artifact_type="telegram_notification",
            description="Outbound notification contract with no command path.",
            required_fields=common
            + ("notification_state", "telegram_command_path_enabled", "live_send_allowed"),
            allowed_statuses=("blocked", "hold", "eligible"),
            default_status="blocked",
            boundary="Telegram can notify only after later gates; it cannot place or modify trades.",
        ),
        Phase5ArtifactContract(
            artifact_type="position_state",
            description="Read-only position and reconciliation state.",
            required_fields=common
            + ("position_state", "open_position_count", "closed_trade_count", "write_authority"),
            allowed_statuses=("blocked", "open_position", "closed_trade", "failed_reconciliation"),
            default_status="blocked",
            boundary="Position state is a mirror and cannot close, resize, or submit orders.",
        ),
        Phase5ArtifactContract(
            artifact_type="closed_trade_summary",
            description="Closed-trade summary and postmortem handoff contract.",
            required_fields=common
            + ("closed_trade_state", "postmortem_due", "phase5_test_trade"),
            allowed_statuses=("blocked", "closed_trade", "failed_reconciliation"),
            default_status="blocked",
            boundary="Closed trade summaries are records only and do not count toward Phase 7 proof.",
        ),
        Phase5ArtifactContract(
            artifact_type="phase5_certification",
            description="Phase 5 certification summary contract.",
            required_fields=common
            + ("phase5_certified", "q5_stage_count", "phase7_proof_credit_allowed"),
            allowed_statuses=("blocked", "hold", "eligible"),
            default_status="blocked",
            boundary="Certification can summarize Q5 state only; it cannot enable live capital.",
        ),
    )


def phase5_contract_by_type() -> dict[str, Phase5ArtifactContract]:
    return {contract.artifact_type: contract for contract in phase5_artifact_contracts()}


def _base_artifact(artifact_type: str, *, status: str | None = None) -> dict[str, Any]:
    contract = phase5_contract_by_type()[artifact_type]
    authority = phase5_authority_ledger()
    return {
        "schema_version": PHASE5_ARTIFACT_SCHEMA_VERSION,
        "artifact_type": artifact_type,
        "artifact_id": f"sample:q5-1:{artifact_type}",
        "phase": "Q5",
        "stage": "Q5-1",
        "status": status or contract.default_status,
        "generated_at": _now(),
        "public_safe": True,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_correlation_id": None,
        "authority_ledger": authority,
        "source_posture": phase5_source_posture(),
        "provenance": phase5_provenance(),
        "boundary": contract.boundary,
        **phase5_authority_defaults(),
    }


def build_phase5_sample_artifacts() -> list[dict[str, Any]]:
    return [
        {
            **_base_artifact("layer_b_authority_ledger"),
            "authority_field_count": len(PHASE5_AUTHORITY_FIELDS),
            "explicit_authority_grant_count": 0,
        },
        {
            **_base_artifact("approval_policy_decision"),
            "strategy_family_key": "sample_strategy_family",
            "policy_decision": "blocked_missing_q5_2_router",
            "approved_strategy_toggle_state": "approved_shadow",
        },
        {
            **_base_artifact("risk_sizing_review"),
            "risk_decision": "blocked_missing_q5_3_contract",
            "proposed_risk_gbp": 0.0,
            "max_risk_gbp": 0.0,
            "risk_blockers": ["risk_contract_not_implemented"],
        },
        {
            **_base_artifact("kill_switch_event"),
            "switch_scope": "global",
            "switch_state": "fail_closed",
            "actor_label": "system_schema_default",
            "reason": "Q5-4 kill-switch ledger not implemented.",
        },
        {
            **_base_artifact("execution_intent"),
            "instrument": "sample_instrument",
            "side": "buy",
            "quantity": 0,
            "order_type": "not_applicable",
            "intent_state": "blocked_missing_q5_5_and_q5_6",
        },
        {
            **_base_artifact("execution_adapter_status"),
            "venue_key": "alpaca_paper",
            "venue_mode": "read_only",
            "read_health": "not_checked_by_q5_1",
            "write_health": "blocked_missing_q5_5",
        },
        {
            **_base_artifact("staged_paper_order"),
            "order_state": "not_staged",
            "idempotency_key": None,
            "staging_allowed": False,
            "submission_allowed": False,
        },
        {
            **_base_artifact("broker_submit_receipt"),
            "receipt_state": "not_submitted",
            "broker_post_called": False,
            "paper_order_submitted": False,
            "idempotency_key": None,
        },
        {
            **_base_artifact("telegram_notification"),
            "notification_state": "dry_contract_only",
            "telegram_command_path_enabled": False,
            "live_send_allowed": False,
        },
        {
            **_base_artifact("position_state"),
            "position_state": "not_open",
            "open_position_count": 0,
            "closed_trade_count": 0,
            "write_authority": False,
        },
        {
            **_base_artifact("closed_trade_summary"),
            "closed_trade_state": "not_closed",
            "postmortem_due": False,
            "phase5_test_trade": True,
        },
        {
            **_base_artifact("phase5_certification"),
            "phase5_certified": False,
            "q5_stage_count": 16,
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
    invalid_allowed = sorted(allowed - set(PHASE5_AUTHORITY_FIELDS))
    for field in invalid_allowed:
        errors.append(f"unknown_allowed_authority_field:{field}")
    ledger = artifact.get("authority_ledger")
    if not isinstance(ledger, dict):
        return ["authority_ledger_missing_or_invalid"]
    if ledger.get("authority_field_count") != len(PHASE5_AUTHORITY_FIELDS):
        errors.append("authority_field_count_mismatch")
    explicit_count = 0
    for field in PHASE5_AUTHORITY_FIELDS:
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
        if field_allowed:
            pass
        elif artifact.get(field) is not False:
            errors.append(f"authority_enabled:{field}")
        if field in ledger and field in artifact and ledger.get(field) != artifact.get(field):
            errors.append(f"authority_field_mismatch:{field}")
    if ledger.get("explicit_authority_grant_count", 0) != explicit_count:
        errors.append("explicit_authority_grant_count_mismatch")
    return errors


def _source_posture_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    posture = artifact.get("source_posture")
    if not isinstance(posture, dict):
        return ["source_posture_missing_or_invalid"]
    for field in PHASE5_SOURCE_POSTURE_REQUIRED_FIELDS:
        if field not in posture:
            errors.append(f"source_posture_field_missing:{field}")
    if posture.get("canonical_source_required") is not True:
        errors.append("canonical_source_not_required")
    if posture.get("canonical_source_count") != EXPECTED_SOURCE_COUNT:
        errors.append("canonical_source_count_mismatch")
    if posture.get("expected_canonical_source_count") != EXPECTED_SOURCE_COUNT:
        errors.append("expected_canonical_source_count_mismatch")
    if posture.get("canonical_source_coverage_complete") is not True:
        errors.append("canonical_source_coverage_incomplete")
    if len(posture.get("canonical_source_keys", []) or []) != EXPECTED_SOURCE_COUNT:
        errors.append("canonical_source_keys_count_mismatch")
    coverage = posture.get("decision_source_coverage")
    if not isinstance(coverage, dict):
        errors.append("decision_source_coverage_missing_or_invalid")
    else:
        if coverage.get("canonical_source_count") != EXPECTED_SOURCE_COUNT:
            errors.append("decision_source_coverage_count_mismatch")
        if coverage.get("all_canonical_sources_considered") is not True:
            errors.append("decision_source_coverage_incomplete")
        if coverage.get("source_quorum_bypass_allowed") is not False:
            errors.append("decision_source_coverage_quorum_bypass_allowed")
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
    if posture.get("source_quorum_bypass_allowed") is not False:
        errors.append("source_quorum_bypass_allowed")
    return errors


def _provenance_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    provenance = artifact.get("provenance")
    if not isinstance(provenance, dict):
        return ["provenance_missing_or_invalid"]
    for field in PHASE5_PROVENANCE_REQUIRED_FIELDS:
        if field not in provenance:
            errors.append(f"provenance_field_missing:{field}")
    if not isinstance(provenance.get("source_refs"), list) or not provenance.get("source_refs"):
        errors.append("provenance_source_refs_missing")
    if provenance.get("event_log_required") is not True:
        errors.append("provenance_event_log_not_required")
    for field in ("raw_secret_exposed", "raw_payload_exposed", "local_path_exposed"):
        if provenance.get(field) is not False:
            errors.append(f"provenance_exposure_enabled:{field}")
    return errors


def _specific_errors(artifact: dict[str, Any], *, expected_stage: str) -> list[str]:
    artifact_type = str(artifact.get("artifact_type") or "")
    errors: list[str] = []
    if artifact_type == "staged_paper_order" and expected_stage == "Q5-1":
        if artifact.get("staging_allowed") is not False:
            errors.append("staging_allowed_in_q5_1")
        if artifact.get("submission_allowed") is not False:
            errors.append("submission_allowed_in_q5_1")
    if artifact_type == "broker_submit_receipt" and expected_stage == "Q5-1":
        if artifact.get("broker_post_called") is not False:
            errors.append("broker_post_called_in_q5_1")
        if artifact.get("paper_order_submitted") is not False:
            errors.append("paper_order_submitted_in_q5_1")
    if artifact_type == "telegram_notification" and expected_stage == "Q5-1":
        if artifact.get("telegram_command_path_enabled") is not False:
            errors.append("telegram_command_path_enabled")
        if artifact.get("live_send_allowed") is not False:
            errors.append("telegram_live_send_allowed_in_q5_1")
    if (
        artifact_type == "position_state"
        and expected_stage == "Q5-1"
        and artifact.get("write_authority") is not False
    ):
        errors.append("position_write_authority_enabled")
    if artifact_type == "phase5_certification" and expected_stage == "Q5-1":
        if artifact.get("phase5_certified") is not False:
            errors.append("phase5_certified_in_q5_1")
        if artifact.get("phase7_proof_credit_allowed") is not False:
            errors.append("phase7_proof_credit_allowed_in_q5_1")
    return errors


def validate_phase5_artifact(
    artifact: dict[str, Any],
    *,
    expected_stage: str = "Q5-1",
    allowed_authority_fields: tuple[str, ...] = (),
) -> list[str]:
    errors: list[str] = []
    artifact_type = str(artifact.get("artifact_type"))
    contract = phase5_contract_by_type().get(artifact_type)
    if contract is None:
        return [f"unknown_artifact_type:{artifact.get('artifact_type')}"]

    for field in contract.required_fields:
        if field not in artifact:
            errors.append(f"missing_field:{artifact_type}:{field}")
    if artifact.get("schema_version") != PHASE5_ARTIFACT_SCHEMA_VERSION:
        errors.append(f"schema_version_mismatch:{artifact_type}")
    if artifact.get("phase") != "Q5":
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
    if not str(artifact.get("boundary") or "").strip():
        errors.append(f"boundary_missing:{artifact_type}")
    errors.extend(_authority_errors(artifact, allowed_authority_fields=allowed_authority_fields))
    errors.extend(_source_posture_errors(artifact))
    errors.extend(_provenance_errors(artifact))
    errors.extend(_specific_errors(artifact, expected_stage=expected_stage))
    return errors


def phase5_artifact_bundle_summary(artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    seen = Counter(str(artifact.get("artifact_type")) for artifact in artifacts)
    missing_types = [
        artifact_type
        for artifact_type in PHASE5_ARTIFACT_TYPES
        if seen.get(artifact_type, 0) == 0
    ]
    duplicate_types = [
        artifact_type
        for artifact_type, count in seen.items()
        if artifact_type in PHASE5_ARTIFACT_TYPES and count > 1
    ]
    for artifact in artifacts:
        errors.extend(validate_phase5_artifact(artifact))
    for artifact_type in missing_types:
        errors.append(f"missing_artifact_type:{artifact_type}")
    for artifact_type in duplicate_types:
        errors.append(f"duplicate_artifact_type:{artifact_type}")

    authority_enabled_count = sum(
        1
        for artifact in artifacts
        for field in PHASE5_AUTHORITY_FIELDS
        if artifact.get(field) is not False
    )

    return {
        "status": "ok" if not errors else "error",
        "schema_version": PHASE5_ARTIFACT_SCHEMA_VERSION,
        "artifact_count": len(artifacts),
        "artifact_type_count": len(PHASE5_ARTIFACT_TYPES),
        "status_enum_count": len(PHASE5_STATUS_ENUMS),
        "authority_field_count": len(PHASE5_AUTHORITY_FIELDS),
        "missing_artifact_types": missing_types,
        "duplicate_artifact_types": duplicate_types,
        "error_count": len(errors),
        "errors": errors,
        "authority_enabled_count": authority_enabled_count,
        "source_posture_status": "validated" if not errors else "error",
        "provenance_status": "validated" if not errors else "error",
        "boundary": (
            "Q5-1 validates Layer B artifact shapes only. Later Q5 stages must "
            "explicitly grant and verify any non-default paper authority."
        ),
    }
