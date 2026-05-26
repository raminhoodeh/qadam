"""Phase 4 certification gate.

Q4-12 aggregates the Phase 4 evidence package and decides whether Phase 4 may
exit into Phase 5. The gate is intentionally fail-closed: missing explicit Fund
Manager approval blocks certification, but the certification evaluation itself is
still replayable and public-safe.
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.phase4_approval_record import (
    build_fund_manager_approval_event,
    validate_fund_manager_approval_event,
)
from orchestrator.phase4_artifacts import (
    PHASE4_ARTIFACT_SCHEMA_VERSION,
    phase4_artifact_bundle_summary,
    phase4_authority_boundary,
)
from orchestrator.phase4_candidate_strategy_universe import (
    build_candidate_strategy_universe,
    validate_candidate_strategy_universe,
)
from orchestrator.phase4_data_veracity import (
    build_data_veracity_audit,
    validate_data_veracity_audit,
)
from orchestrator.phase4_manifested_strategy import (
    build_manifested_strategy_metadata,
    validate_manifested_strategy_metadata,
)
from orchestrator.phase4_resource_validation import (
    build_resource_validation,
    validate_resource_validation,
)
from orchestrator.phase4_strategy_toggles import (
    build_strategy_toggle_snapshot,
    validate_strategy_toggle_snapshot,
)
from orchestrator.phase4_triple_mirror import (
    build_triple_mirror_audit,
    validate_triple_mirror_audit,
)
from orchestrator.phase4_trust_scores import (
    build_trust_score_recalculation,
    validate_trust_score_recalculation,
)
from orchestrator.phase4_world_model_validation import (
    build_world_model_validation,
    validate_world_model_validation,
)
from orchestrator.preference_mcp_domain_packs import (
    build_preference_domain_pack_mapping,
    validate_preference_domain_pack_mapping,
)
from orchestrator.preference_mcp_identity import build_preference_mcp_identity_status
from orchestrator.preference_mcp_provenance import (
    validate_preference_source_quorum_report,
)
from orchestrator.preference_mcp_source_promotion import (
    UPSTREAM_REGISTRY_MAP,
    build_preference_source_promotion_decisions,
    preference_source_promotion_paths,
    validate_preference_source_promotion_decisions,
)
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT


PHASE4_CERTIFICATION_SCHEMA_VERSION = 1
CERTIFICATION_RUNTIME_ARTIFACT = "phase4_certification.json"
CERTIFICATION_EVENT_LOG = "phase4_certification_events.jsonl"
CERTIFICATION_EVENT_TYPE = "phase4_certification_evaluated"
CERTIFICATION_EVENT_COMPONENT = "phase4_certification"

NO_EXECUTION_BOUNDARY = (
    "Phase 4 certification is an exit gate only. It cannot create trade candidates, "
    "approve risk, stage or submit paper orders, write to brokers, call quantum "
    "providers, submit hardware jobs, enable schedulers, or enable live capital."
)

AUTHORITY_COUNT_FIELDS: tuple[str, ...] = (
    "trade_candidate_count",
    "trade_candidate_created_count",
    "risk_agent_handoff_allowed_count",
    "execution_policy_handoff_allowed_count",
    "execution_allowed_count",
    "paper_order_allowed_count",
    "staged_paper_order_allowed_count",
    "broker_write_allowed_count",
    "live_capital_enabled_count",
    "hardware_submission_allowed_count",
    "hardware_submitted_count",
    "hardware_scheduler_enabled_count",
    "provider_call_allowed_count",
    "scheduler_enabled_count",
    "authority_flag_violation_count",
)

AUTHORITY_FLAG_FIELDS: tuple[str, ...] = (
    "trade_candidate_creation_allowed",
    "trade_candidate_authority",
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
    "hardware_submission_allowed",
    "hardware_submitted",
    "hardware_scheduler_enabled",
    "provider_call_allowed",
    "scheduler_enabled",
)

ARTIFACT_FILES: dict[str, str] = {
    "triple_mirror_audit": "phase4_triple_mirror_audit.json",
    "data_veracity_audit": "phase4_data_veracity_audit.json",
    "trust_score_recalculation": "phase4_trust_score_recalculation.json",
    "resource_validation": "phase4_resource_validation.json",
    "world_model_validation": "phase4_world_model_validation.json",
    "candidate_strategy_universe": "phase4_candidate_strategy_universe.json",
    "manifested_strategy_metadata": "phase4_manifested_strategy_metadata.json",
    "strategy_toggle_snapshot": "phase4_strategy_toggle_snapshot.json",
    "fund_manager_approval_event": "phase4_fund_manager_approval_event.json",
}

PREFERENCE_CERTIFICATION_GATE_SCHEMA_VERSION = 1
PREFERENCE_CERTIFICATION_BOUNDARY = (
    "PREF-11 makes Preference/PREF MCP a certification input only. It verifies "
    "identity posture, provenance, domain-pack coverage, paid-tool policy, and "
    "source-quorum boundaries before Phase 5. It cannot call live MCP tools, "
    "consume paid tools, satisfy source quorum, create trade candidates, approve "
    "risk, stage or submit paper orders, write brokers, call quantum providers, "
    "enable schedulers, or enable live capital."
)
PREFERENCE_INVALID_IDENTITY_STATUSES: tuple[str, ...] = (
    "anonymous",
    "missing_identity",
    "not_verified",
    "",
)
PREFERENCE_CERTIFICATION_AUTHORITY_FIELDS: tuple[str, ...] = (
    "live_mcp_call_allowed",
    "search_tools_allowed",
    "domain_tool_calls_allowed",
    "paid_tool_calls_allowed",
    "paid_tools_allowed",
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


def _read_or_build(
    settings: Settings | None,
    filename: str,
    builder: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    path = _runtime_dir(settings) / filename
    return _read_json(path) or builder()


def _artifact_validations(artifacts: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    return {
        "triple_mirror_audit": validate_triple_mirror_audit(
            artifacts["triple_mirror_audit"]
        ),
        "data_veracity_audit": validate_data_veracity_audit(
            artifacts["data_veracity_audit"]
        ),
        "trust_score_recalculation": validate_trust_score_recalculation(
            artifacts["trust_score_recalculation"]
        ),
        "resource_validation": validate_resource_validation(
            artifacts["resource_validation"]
        ),
        "world_model_validation": validate_world_model_validation(
            artifacts["world_model_validation"]
        ),
        "candidate_strategy_universe": validate_candidate_strategy_universe(
            artifacts["candidate_strategy_universe"]
        ),
        "manifested_strategy_metadata": validate_manifested_strategy_metadata(
            artifacts["manifested_strategy_metadata"]
        ),
        "strategy_toggle_snapshot": validate_strategy_toggle_snapshot(
            artifacts["strategy_toggle_snapshot"]
        ),
        "fund_manager_approval_event": validate_fund_manager_approval_event(
            artifacts["fund_manager_approval_event"],
            manifested_strategy=artifacts["manifested_strategy_metadata"],
        ),
    }


def _load_phase4_artifacts(
    settings: Settings | None = None,
    *,
    approval_event: dict[str, Any] | None = None,
    strategy_toggle_snapshot: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    artifacts = {
        "triple_mirror_audit": _read_or_build(
            settings,
            ARTIFACT_FILES["triple_mirror_audit"],
            lambda: build_triple_mirror_audit(settings),
        ),
        "data_veracity_audit": _read_or_build(
            settings,
            ARTIFACT_FILES["data_veracity_audit"],
            lambda: build_data_veracity_audit(settings),
        ),
        "trust_score_recalculation": _read_or_build(
            settings,
            ARTIFACT_FILES["trust_score_recalculation"],
            lambda: build_trust_score_recalculation(settings),
        ),
        "resource_validation": _read_or_build(
            settings,
            ARTIFACT_FILES["resource_validation"],
            lambda: build_resource_validation(settings),
        ),
        "world_model_validation": _read_or_build(
            settings,
            ARTIFACT_FILES["world_model_validation"],
            lambda: build_world_model_validation(settings),
        ),
        "candidate_strategy_universe": _read_or_build(
            settings,
            ARTIFACT_FILES["candidate_strategy_universe"],
            lambda: build_candidate_strategy_universe(settings),
        ),
        "manifested_strategy_metadata": _read_or_build(
            settings,
            ARTIFACT_FILES["manifested_strategy_metadata"],
            lambda: build_manifested_strategy_metadata(settings=settings),
        ),
    }
    artifacts["fund_manager_approval_event"] = (
        approval_event
        or _read_or_build(
            settings,
            ARTIFACT_FILES["fund_manager_approval_event"],
            lambda: build_fund_manager_approval_event(settings=settings),
        )
    )
    artifacts["strategy_toggle_snapshot"] = (
        strategy_toggle_snapshot
        or _read_or_build(
            settings,
            ARTIFACT_FILES["strategy_toggle_snapshot"],
            lambda: build_strategy_toggle_snapshot(
                settings=settings,
                approval_event=artifacts["fund_manager_approval_event"],
            ),
        )
    )
    return artifacts


def _status_counts(validation_sets: dict[str, list[str]]) -> dict[str, Any]:
    counts = {key: len(errors) for key, errors in validation_sets.items()}
    return {
        "by_artifact": counts,
        "artifact_validation_error_count": sum(counts.values()),
        "validated_artifact_count": sum(1 for value in counts.values() if value == 0),
        "artifact_count": len(counts),
    }


def _strategy_explicitness(candidate_universe: dict[str, Any], manifested: dict[str, Any]) -> dict[str, Any]:
    candidates = [
        candidate
        for candidate in candidate_universe.get("candidates", [])
        if isinstance(candidate, dict)
    ]
    source_weight_count = sum(len(candidate.get("source_weights", {}) or {}) for candidate in candidates)
    model_weight_count = sum(len(candidate.get("model_weights", {}) or {}) for candidate in candidates)
    quantum_role_count = sum(1 for candidate in candidates if candidate.get("quantum_role"))
    risk_assumption_count = sum(len(candidate.get("risk_assumptions", []) or []) for candidate in candidates)
    market_confirmation_requirement_count = sum(
        len(candidate.get("market_confirmation_requirements", []) or [])
        for candidate in candidates
    )
    candidate_count = len(candidates)
    complete = bool(
        candidate_count
        and manifested.get("active_instrument_count", 0) > 0
        and manifested.get("catalyst_class_count", 0) > 0
        and source_weight_count >= candidate_count
        and model_weight_count >= candidate_count
        and quantum_role_count == candidate_count
        and risk_assumption_count >= candidate_count
        and market_confirmation_requirement_count >= candidate_count
    )
    return {
        "complete": complete,
        "strategy_family_candidate_count": candidate_count,
        "active_instrument_count": manifested.get("active_instrument_count", 0),
        "catalyst_class_count": manifested.get("catalyst_class_count", 0),
        "source_weight_count": source_weight_count,
        "model_weight_count": model_weight_count,
        "quantum_role_count": quantum_role_count,
        "risk_assumption_count": risk_assumption_count,
        "market_confirmation_requirement_count": market_confirmation_requirement_count,
    }


def _world_model_status(world_model: dict[str, Any]) -> dict[str, Any]:
    status_counts = world_model.get("status_counts", {})
    claim_count = int(world_model.get("claim_count") or 0)
    covered_count = sum(
        int(status_counts.get(status, 0) or world_model.get(f"{status}_claim_count", 0) or 0)
        for status in ("validated", "provisional", "rejected", "untestable")
    )
    complete = claim_count > 0 and covered_count == claim_count
    return {
        "complete": complete,
        "claim_count": claim_count,
        "covered_claim_count": covered_count,
        "validated_claim_count": world_model.get("validated_claim_count", 0),
        "provisional_claim_count": world_model.get("provisional_claim_count", 0),
        "rejected_claim_count": world_model.get("rejected_claim_count", 0),
        "untestable_claim_count": world_model.get("untestable_claim_count", 0),
        "world_model_frames_are_factual_evidence": world_model.get(
            "world_model_frames_are_factual_evidence"
        )
        is True,
        "world_model_frames_are_trade_triggers": world_model.get(
            "world_model_frames_are_trade_triggers"
        )
        is True,
        "world_model_frames_can_increase_signal_confidence": world_model.get(
            "world_model_frames_can_increase_signal_confidence"
        )
        is True,
    }


def _phase3_zero_authority(settings: Settings | None = None) -> dict[str, Any]:
    cockpit = _read_json(_runtime_dir(settings) / "cockpit-status.json") or {}
    quantum = cockpit.get("quantum_oracle", {})
    provider_readiness = quantum.get("provider_readiness", {})
    qctrl = provider_readiness.get("qctrl_readiness", {})
    hardware_stubs = provider_readiness.get("hardware_provider_stubs", {})
    scheduler = quantum.get("scheduler_dry_run", {})
    checks = {
        "quantum_execution_allowed_count": quantum.get("execution_allowed_count", 0),
        "quantum_paper_order_allowed_count": quantum.get("paper_order_allowed_count", 0),
        "quantum_trade_candidate_created_count": quantum.get("trade_candidate_created_count", 0),
        "provider_call_allowed_count": provider_readiness.get("provider_call_allowed_count", 0),
        "hardware_submission_allowed_count": hardware_stubs.get("hardware_submission_allowed_count", 0),
        "hardware_submitted_count": hardware_stubs.get("hardware_submitted_count", 0),
        "hardware_scheduler_enabled_count": hardware_stubs.get("hardware_scheduler_enabled_count", 0),
        "qctrl_provider_call_count": qctrl.get("provider_call_count", 0),
        "scheduler_jobs_queued_count": scheduler.get("jobs_queued_count", 0),
        "scheduler_jobs_submitted_count": scheduler.get("jobs_submitted_count", 0),
        "scheduler_hardware_jobs_submitted_count": scheduler.get("hardware_jobs_submitted_count", 0),
    }
    violations = {key: value for key, value in checks.items() if value not in (0, False, None)}
    return {
        "status": "ok" if not violations else "blocked",
        "checks": checks,
        "violation_count": len(violations),
        "violations": violations,
        "boundary": (
            "Phase 3 quantum/provider/scheduler posture remains readiness-only and "
            "non-executing."
        ),
    }


def _preference_runtime_artifacts(settings: Settings | None = None) -> dict[str, dict[str, Any]]:
    runtime = _runtime_dir(settings)
    source_promotion_path, _history_path = preference_source_promotion_paths(settings)
    return {
        "identity": (
            _read_json(runtime / "preference_mcp_identity_status.json")
            or build_preference_mcp_identity_status(
                settings=settings,
                live_status_check=False,
                record_event=False,
            )
        ),
        "domain_packs": (
            _read_json(runtime / "preference_domain_packs.json")
            or build_preference_domain_pack_mapping(settings=settings)
        ),
        "provenance": _read_json(runtime / "preference_provenance_source_quorum.json")
        or {},
        "source_promotion": (
            _read_json(source_promotion_path)
            or build_preference_source_promotion_decisions(
                settings=settings,
                cockpit={
                    "durable_ingestion": {
                        "replay_status": "not_run",
                        "missing_sources": [],
                    }
                },
            )
        ),
    }


def _preference_authority_flags() -> dict[str, bool]:
    return {field: False for field in PREFERENCE_CERTIFICATION_AUTHORITY_FIELDS}


def _preference_policy_violations(
    candidate_universe: dict[str, Any],
    manifested: dict[str, Any],
    preference_artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    candidates = [
        candidate
        for candidate in candidate_universe.get("candidates", [])
        if isinstance(candidate, dict)
    ]
    candidate_count = int(candidate_universe.get("strategy_family_candidate_count") or len(candidates))
    candidate_policy_count = 0
    candidate_family_with_domain_pack_count = 0
    candidate_source_quorum_violations: list[str] = []
    candidate_preference_only_violations: list[str] = []
    candidate_authority_violations: list[str] = []
    candidate_domain_pack_missing: list[str] = []

    for candidate in candidates:
        candidate_key = str(candidate.get("candidate_key") or "unknown_candidate")
        policy = candidate.get("preference_context_policy", {})
        if not isinstance(policy, dict) or policy.get("source_key") != "preference_mcp":
            candidate_domain_pack_missing.append(candidate_key)
            continue
        candidate_policy_count += 1
        if int(policy.get("approved_domain_pack_count", 0) or 0) > 0:
            candidate_family_with_domain_pack_count += 1
        else:
            candidate_domain_pack_missing.append(candidate_key)
        if policy.get("source_quorum_credit_allowed") is not False:
            candidate_source_quorum_violations.append(candidate_key)
        if policy.get("preference_only_confirmation_allowed") is not False:
            candidate_preference_only_violations.append(candidate_key)
        for key in (
            "trade_candidate_creation_allowed",
            "risk_handoff_allowed",
            "execution_allowed",
            "paper_order_allowed",
            "broker_write_allowed",
            "live_capital_enabled",
        ):
            if policy.get(key) is not False:
                candidate_authority_violations.append(f"{candidate_key}:{key}")

    preference_policy = candidate_universe.get("preference_mcp_policy", {})
    manifestation = manifested.get("preference_mcp_manifestation", {})
    provenance = preference_artifacts.get("provenance", {})
    domain_packs = preference_artifacts.get("domain_packs", {})
    source_promotion = preference_artifacts.get("source_promotion", {})
    source_quorum_violations: list[str] = []
    if candidate_source_quorum_violations:
        source_quorum_violations.extend(
            f"candidate:{key}" for key in candidate_source_quorum_violations
        )
    if candidate_preference_only_violations:
        source_quorum_violations.extend(
            f"candidate_preference_only:{key}"
            for key in candidate_preference_only_violations
        )
    for layer_name, layer in (
        ("candidate_artifact_policy", preference_policy),
        ("manifested_strategy", manifestation),
        ("domain_packs", domain_packs),
        ("provenance", provenance),
        ("source_promotion", source_promotion),
    ):
        if not isinstance(layer, dict):
            source_quorum_violations.append(f"{layer_name}:missing")
            continue
        for key in (
            "source_quorum_credit_allowed",
            "strategy_source_quorum_credit_allowed",
            "preference_counts_as_canonical_source",
            "preference_only_source_quorum_allowed",
            "preference_only_confirmation_allowed",
        ):
            if key in layer and layer.get(key) is not False:
                source_quorum_violations.append(f"{layer_name}:{key}")

    approved_domain_packs = sorted(
        {
            str(domain_pack)
            for source in (
                domain_packs.get("unique_domain_packs", []) or (),
                preference_policy.get("approved_domain_packs", []) or (),
                manifestation.get("approved_domain_packs", []) or (),
            )
            for domain_pack in source
            if str(domain_pack).strip()
        }
    )
    domain_validation_errors = validate_preference_domain_pack_mapping(domain_packs)
    provenance_validation_errors = (
        validate_preference_source_quorum_report(provenance) if provenance else ["preference_provenance_missing"]
    )
    source_promotion_validation_errors = (
        validate_preference_source_promotion_decisions(source_promotion)
        if source_promotion
        else ["preference_source_promotion_missing"]
    )
    manifestation_preference_aware = (
        isinstance(manifestation, dict)
        and manifestation.get("source_role") == "supplemental_multi_source_data_plane"
        and int(manifestation.get("approved_domain_pack_count", 0) or 0) > 0
        and manifestation.get("source_quorum_credit_allowed") is False
        and manifestation.get("preference_only_confirmation_allowed") is False
    )

    return {
        "strategy_family_candidate_count": candidate_count,
        "candidate_policy_count": candidate_policy_count,
        "candidate_family_with_domain_pack_count": candidate_family_with_domain_pack_count,
        "candidate_domain_pack_missing": candidate_domain_pack_missing,
        "candidate_authority_violations": candidate_authority_violations,
        "approved_domain_packs": approved_domain_packs,
        "approved_domain_pack_count": len(approved_domain_packs),
        "domain_pack_status": str(domain_packs.get("status") or "not_run"),
        "domain_pack_validation_error_count": len(domain_validation_errors),
        "domain_pack_validation_errors": domain_validation_errors,
        "provenance_status": str(provenance.get("status") or "not_run"),
        "provenance_context_status": str(
            provenance.get("preference_context_status") or "not_run"
        ),
        "preference_distinct_upstream_source_count": int(
            provenance.get("preference_distinct_upstream_source_count", 0) or 0
        ),
        "provenance_validation_error_count": len(provenance_validation_errors),
        "provenance_validation_errors": provenance_validation_errors,
        "source_promotion_status": str(source_promotion.get("status") or "not_run"),
        "source_promotion_validation_error_count": len(
            source_promotion_validation_errors
        ),
        "source_promotion_validation_errors": source_promotion_validation_errors,
        "source_promotion_decision_count": int(
            source_promotion.get("decision_count", 0) or 0
        ),
        "source_promotion_expected_decision_count": (
            EXPECTED_PREFERENCE_SOURCE_PROMOTION_DECISION_COUNT
        ),
        "source_promotion_promoted_decision_count": int(
            source_promotion.get("promoted_decision_count", 0) or 0
        ),
        "source_promotion_existing_registry_decision_count": int(
            source_promotion.get("existing_registry_decision_count", 0) or 0
        ),
        "source_promotion_new_source_deferred_count": int(
            source_promotion.get("new_source_deferred_count", 0) or 0
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
        "manifestation_preference_aware": manifestation_preference_aware,
        "manifestation_family_policy_count": int(
            manifestation.get("candidate_family_with_policy_count", 0) or 0
        )
        if isinstance(manifestation, dict)
        else 0,
        "source_quorum_policy_violations": sorted(set(source_quorum_violations)),
        "source_quorum_policy_violation_count": len(set(source_quorum_violations)),
    }


def _build_preference_certification_gate(
    *,
    settings: Settings | None,
    candidate_universe: dict[str, Any],
    manifested: dict[str, Any],
    approval_event: dict[str, Any],
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    preference_artifacts = _preference_runtime_artifacts(settings)
    identity = preference_artifacts["identity"]
    policy = _preference_policy_violations(candidate_universe, manifested, preference_artifacts)
    identity_status = str(identity.get("identity_status") or "not_verified")
    identity_gate_status = str(identity.get("status") or "blocked")
    preference_enabled = bool(settings.preference_mcp_enabled)
    identity_blocker_active = (
        preference_enabled
        and (
            identity_gate_status != "verified_non_anonymous"
            or identity_status in PREFERENCE_INVALID_IDENTITY_STATUSES
        )
    )
    paid_tools_allowed = any(
        bool(value)
        for value in (
            settings.preference_mcp_paid_tools_allowed,
            identity.get("paid_tools_allowed_by_config"),
            identity.get("paid_tool_calls_allowed"),
            policy.get("paid_tool_calls_allowed"),
        )
    )
    explicit_paid_tool_approval = (
        approval_event.get("preference_paid_tool_calls_approved") is True
        or approval_event.get("paid_tool_calls_approved") is True
    )
    authority_violations = list(policy["candidate_authority_violations"])
    authority_flags = _preference_authority_flags()
    blockers: list[str] = []
    if identity_blocker_active:
        blockers.append("preference_enabled_identity_not_verified")
    if (
        policy["provenance_status"] != "validated"
        or policy["provenance_validation_error_count"] != 0
    ):
        blockers.append("preference_provenance_validation_failed")
    if (
        policy["domain_pack_status"] != "validated"
        or policy["domain_pack_validation_error_count"] != 0
        or policy["approved_domain_pack_count"] < 1
        or policy["candidate_family_with_domain_pack_count"]
        != policy["strategy_family_candidate_count"]
    ):
        blockers.append("preference_domain_pack_coverage_incomplete")
    if (
        policy["source_promotion_status"] != "validated"
        or policy["source_promotion_validation_error_count"] != 0
        or policy["source_promotion_decision_count"]
        != EXPECTED_PREFERENCE_SOURCE_PROMOTION_DECISION_COUNT
        or policy["source_promotion_promoted_decision_count"] != 0
        or policy["source_promotion_canonical_source_count_after"] != EXPECTED_SOURCE_COUNT
        or policy["source_promotion_aggregator_promoted"] is not False
        or policy["preference_mcp_source_36"] is not False
    ):
        blockers.append("preference_source_promotion_policy_invalid")
    if policy["candidate_policy_count"] != policy["strategy_family_candidate_count"]:
        blockers.append("preference_candidate_policy_coverage_incomplete")
    if not policy["manifestation_preference_aware"]:
        blockers.append("preference_manifested_strategy_not_preference_aware")
    if paid_tools_allowed and not explicit_paid_tool_approval:
        blockers.append("preference_paid_tools_enabled_without_explicit_approval")
    if policy["source_quorum_policy_violation_count"] != 0:
        blockers.append("preference_source_quorum_policy_violation")
    if authority_violations:
        blockers.append("preference_authority_violation")

    return {
        "schema_version": PREFERENCE_CERTIFICATION_GATE_SCHEMA_VERSION,
        "source_key": "preference_mcp",
        "source_role": "supplemental_multi_source_data_plane",
        "status": "validated" if not blockers else "blocked",
        "public_safe": True,
        "preference_enabled": preference_enabled,
        "identity_status": identity_status,
        "identity_gate_status": identity_gate_status,
        "identity_blocker_active": identity_blocker_active,
        "quota_metadata_present": bool(identity.get("quota_metadata_present")),
        "quota_degraded": (
            identity_gate_status != "verified_non_anonymous"
            or identity.get("quota_metadata_present") is not True
        ),
        **policy,
        **authority_flags,
        "paid_tools_allowed": paid_tools_allowed,
        "paid_tool_calls_allowed": False,
        "paid_tool_explicit_approval_present": explicit_paid_tool_approval,
        "source_quorum_credit_allowed": False,
        "preference_only_confirmation_allowed": False,
        "authority_flags": authority_flags,
        "authority_violation_count": len(authority_violations),
        "authority_violations": authority_violations,
        "certification_blockers": sorted(set(blockers)),
        "certification_blocker_count": len(set(blockers)),
        "phase5_handoff_blocked_by_preference_policy": bool(blockers),
        "required_next_steps": (
            []
            if not blockers
            else [
                "Repair Preference identity, provenance, domain-pack, paid-tool, or source-quorum policy before Phase 5.",
                "Rerun PREF checks, Q4-10 approval, and Q4-12 certification.",
            ]
        ),
        "boundary": PREFERENCE_CERTIFICATION_BOUNDARY,
    }


def _validate_preference_certification_gate(gate: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "source_key",
        "source_role",
        "status",
        "public_safe",
        "preference_enabled",
        "identity_status",
        "identity_gate_status",
        "identity_blocker_active",
        "provenance_status",
        "provenance_validation_error_count",
        "domain_pack_status",
        "domain_pack_validation_error_count",
        "source_promotion_status",
        "source_promotion_validation_error_count",
        "source_promotion_decision_count",
        "source_promotion_expected_decision_count",
        "source_promotion_promoted_decision_count",
        "source_promotion_canonical_source_count_after",
        "source_promotion_expected_canonical_source_count",
        "source_promotion_aggregator_promoted",
        "preference_mcp_source_36",
        "approved_domain_pack_count",
        "strategy_family_candidate_count",
        "candidate_policy_count",
        "candidate_family_with_domain_pack_count",
        "manifestation_preference_aware",
        "paid_tools_allowed",
        "paid_tool_calls_allowed",
        "paid_tool_explicit_approval_present",
        "source_quorum_credit_allowed",
        "preference_only_confirmation_allowed",
        "source_quorum_policy_violation_count",
        "authority_flags",
        "authority_violation_count",
        "certification_blockers",
        "certification_blocker_count",
        "boundary",
    }
    missing = sorted(required_fields - set(gate))
    if missing:
        errors.append("preference_gate_missing_fields:" + ",".join(missing))
    if gate.get("schema_version") != PREFERENCE_CERTIFICATION_GATE_SCHEMA_VERSION:
        errors.append("preference_gate_schema_version_mismatch")
    if gate.get("source_key") != "preference_mcp":
        errors.append("preference_gate_source_key_mismatch")
    if gate.get("source_role") != "supplemental_multi_source_data_plane":
        errors.append("preference_gate_role_invalid")
    if gate.get("public_safe") is not True:
        errors.append("preference_gate_public_safe_not_true")

    blockers = gate.get("certification_blockers", [])
    if not isinstance(blockers, list):
        errors.append("preference_gate_blockers_not_list")
        blockers = []
    if gate.get("certification_blocker_count") != len(blockers):
        errors.append("preference_gate_blocker_count_mismatch")
    if blockers and gate.get("status") != "blocked":
        errors.append("preference_gate_status_mismatch")
    if not blockers and gate.get("status") != "validated":
        errors.append("preference_gate_status_mismatch")

    invalid_identity = str(gate.get("identity_status") or "") in PREFERENCE_INVALID_IDENTITY_STATUSES
    if gate.get("preference_enabled") is True and (
        gate.get("identity_gate_status") != "verified_non_anonymous" or invalid_identity
    ):
        errors.append("preference_enabled_identity_not_verified")
    if gate.get("identity_blocker_active") is True and (
        "preference_enabled_identity_not_verified" not in blockers
    ):
        errors.append("preference_identity_blocker_missing")
    if gate.get("provenance_status") != "validated" or gate.get(
        "provenance_validation_error_count"
    ) != 0:
        errors.append("preference_provenance_validation_failed")
    if (
        gate.get("domain_pack_status") != "validated"
        or gate.get("domain_pack_validation_error_count") != 0
        or int(gate.get("approved_domain_pack_count", 0) or 0) < 1
        or gate.get("candidate_family_with_domain_pack_count")
        != gate.get("strategy_family_candidate_count")
    ):
        errors.append("preference_domain_pack_coverage_incomplete")
    if (
        gate.get("source_promotion_status") != "validated"
        or gate.get("source_promotion_validation_error_count") != 0
        or int(gate.get("source_promotion_decision_count", 0) or 0)
        != EXPECTED_PREFERENCE_SOURCE_PROMOTION_DECISION_COUNT
        or int(gate.get("source_promotion_expected_decision_count", 0) or 0)
        != EXPECTED_PREFERENCE_SOURCE_PROMOTION_DECISION_COUNT
        or int(gate.get("source_promotion_promoted_decision_count", 0) or 0) != 0
        or int(gate.get("source_promotion_canonical_source_count_after", 0) or 0)
        != EXPECTED_SOURCE_COUNT
        or int(gate.get("source_promotion_expected_canonical_source_count", 0) or 0)
        != EXPECTED_SOURCE_COUNT
        or gate.get("source_promotion_aggregator_promoted") is not False
        or gate.get("preference_mcp_source_36") is not False
    ):
        errors.append("preference_source_promotion_policy_invalid")
    if gate.get("candidate_policy_count") != gate.get("strategy_family_candidate_count"):
        errors.append("preference_candidate_policy_coverage_incomplete")
    if gate.get("manifestation_preference_aware") is not True:
        errors.append("preference_manifested_strategy_not_preference_aware")
    if (
        gate.get("paid_tools_allowed") is True
        and gate.get("paid_tool_explicit_approval_present") is not True
    ):
        errors.append("preference_paid_tools_enabled_without_explicit_approval")
    if gate.get("paid_tool_calls_allowed") is not False:
        errors.append("preference_paid_tool_calls_allowed")
    if gate.get("source_quorum_credit_allowed") is not False:
        errors.append("preference_source_quorum_credit_allowed")
    if gate.get("preference_only_confirmation_allowed") is not False:
        errors.append("preference_only_confirmation_allowed")
    if gate.get("source_quorum_policy_violation_count", 0) != 0:
        errors.append("preference_source_quorum_policy_violation")
    if gate.get("authority_violation_count", 0) != 0:
        errors.append("preference_authority_violation")
    flags = gate.get("authority_flags", {})
    if not isinstance(flags, dict):
        errors.append("preference_gate_authority_flags_missing")
    else:
        for key in PREFERENCE_CERTIFICATION_AUTHORITY_FIELDS:
            if flags.get(key) is not False:
                errors.append(f"preference_gate_authority_flag_enabled:{key}")
    for key in PREFERENCE_CERTIFICATION_AUTHORITY_FIELDS:
        if key == "paid_tools_allowed" and gate.get(key) is True:
            continue
        if gate.get(key) is not False:
            errors.append(f"preference_gate_authority_enabled:{key}")
    if "cannot call live MCP tools" not in str(gate.get("boundary") or ""):
        errors.append("preference_gate_boundary_weak")
    return sorted(set(errors))


def _authority_violations(artifacts: dict[str, dict[str, Any]]) -> list[str]:
    violations: list[str] = []
    for name, artifact in artifacts.items():
        for key in AUTHORITY_COUNT_FIELDS:
            value = artifact.get(key)
            if value not in (None, 0, False):
                violations.append(f"{name}:{key}:{value}")
        for key in AUTHORITY_FLAG_FIELDS:
            if artifact.get(key) is True:
                violations.append(f"{name}:{key}:true")
        boundary = artifact.get("authority_boundary")
        if isinstance(boundary, dict):
            for key, value in boundary.items():
                if key.endswith("_allowed") or key.endswith("_enabled"):
                    if value is True:
                        violations.append(f"{name}:authority_boundary:{key}:true")
    return violations


def _build_blockers(
    *,
    approval_event: dict[str, Any],
    manifested: dict[str, Any],
    toggles: dict[str, Any],
    bundle_summary: dict[str, Any],
    validation_summary: dict[str, Any],
    strategy_explicitness: dict[str, Any],
    world_model_status: dict[str, Any],
    phase3_zero_authority: dict[str, Any],
    authority_violations: list[str],
    preference_gate: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    approval_state = str(approval_event.get("approval_state") or "missing")
    approval_logged = approval_event.get("approval_logged") is True
    if approval_state != "approved":
        blockers.append("explicit_fund_manager_approval_required")
    if approval_state == "approved" and not approval_logged:
        blockers.append("approved_fund_manager_event_not_logged")
    if not str(manifested.get("document_fingerprint") or "").strip():
        blockers.append("manifested_strategy_document_fingerprint_missing")
    if bundle_summary.get("error_count", 0) != 0:
        blockers.append("phase4_artifact_bundle_validation_errors")
    if validation_summary.get("artifact_validation_error_count", 0) != 0:
        blockers.append("phase4_specific_artifact_validation_errors")
    if not strategy_explicitness.get("complete"):
        blockers.append("strategy_explicitness_incomplete")
    if not world_model_status.get("complete"):
        blockers.append("world_model_validation_status_incomplete")
    if toggles.get("event_log_written") is not True:
        blockers.append("strategy_toggle_event_log_missing")
    if approval_state == "approved" and toggles.get("approved_shadow_toggle_count") != toggles.get("toggle_count"):
        blockers.append("approved_strategy_toggles_not_approved_shadow")
    if approval_state != "approved" and toggles.get("approved_shadow_toggle_count", 0) != 0:
        blockers.append("approved_shadow_toggles_without_approval")
    if phase3_zero_authority.get("violation_count", 0) != 0:
        blockers.append("phase3_zero_authority_violation")
    if authority_violations:
        blockers.append("phase4_authority_violation")
    blockers.extend(preference_gate.get("certification_blockers", []))
    return sorted(dict.fromkeys(blockers))


def _phase4_exit_gate(blockers: list[str], certified: bool) -> str:
    if certified:
        return "passed_to_phase5_guarded_orchestration_design"
    if any(str(blocker).startswith("preference_") for blocker in blockers):
        if "explicit_fund_manager_approval_required" in blockers:
            return "blocked_pending_explicit_approval_and_preference_policy"
        return "blocked_pending_preference_policy_repair"
    return "blocked_pending_explicit_fund_manager_approval"


def _stage_status(blockers: list[str], certified: bool) -> str:
    if certified:
        return "phase4_certified"
    if any(str(blocker).startswith("preference_") for blocker in blockers):
        if "explicit_fund_manager_approval_required" in blockers:
            return "blocked_pending_explicit_approval_and_preference_policy"
        return "blocked_pending_preference_policy"
    return "blocked_pending_explicit_approval"


def _required_next_steps(blockers: list[str]) -> list[str]:
    if not blockers:
        return []
    steps: list[str] = []
    if "explicit_fund_manager_approval_required" in blockers:
        steps.extend(
            [
                "Log explicit Fund Manager approval for the amended Preference-aware Manifested Strategy Document.",
                "Rerun Q4-10 approval record and Q4-12 certification checks.",
                "Keep strategy toggles draft until approval is logged.",
            ]
        )
    if any(str(blocker).startswith("preference_") for blocker in blockers):
        steps.extend(
            [
                "Repair Preference identity, provenance, domain-pack, paid-tool, or source-quorum policy before Phase 5.",
                "Rerun PREF checks before rerunning Q4-10 and Q4-12.",
            ]
        )
    return list(dict.fromkeys(steps))


def build_phase4_certification(
    *,
    settings: Settings | None = None,
    approval_event: dict[str, Any] | None = None,
    strategy_toggle_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    artifacts = _load_phase4_artifacts(
        settings,
        approval_event=approval_event,
        strategy_toggle_snapshot=strategy_toggle_snapshot,
    )
    validations = _artifact_validations(artifacts)
    validation_summary = _status_counts(validations)
    artifact_list = list(artifacts.values())
    bundle_summary = phase4_artifact_bundle_summary(artifact_list)
    strategy_explicitness = _strategy_explicitness(
        artifacts["candidate_strategy_universe"],
        artifacts["manifested_strategy_metadata"],
    )
    world_status = _world_model_status(artifacts["world_model_validation"])
    phase3_zero = _phase3_zero_authority(settings)
    authority_violations = _authority_violations(artifacts)
    approval = artifacts["fund_manager_approval_event"]
    toggles = artifacts["strategy_toggle_snapshot"]
    preference_gate = _build_preference_certification_gate(
        settings=settings,
        candidate_universe=artifacts["candidate_strategy_universe"],
        manifested=artifacts["manifested_strategy_metadata"],
        approval_event=approval,
    )
    blockers = _build_blockers(
        approval_event=approval,
        manifested=artifacts["manifested_strategy_metadata"],
        toggles=toggles,
        bundle_summary=bundle_summary,
        validation_summary=validation_summary,
        strategy_explicitness=strategy_explicitness,
        world_model_status=world_status,
        phase3_zero_authority=phase3_zero,
        authority_violations=authority_violations,
        preference_gate=preference_gate,
    )
    phase4_certified = not blockers
    phase5_handoff_allowed = phase4_certified
    phase4_exit_gate = _phase4_exit_gate(blockers, phase4_certified)
    artifact = {
        "schema_version": PHASE4_ARTIFACT_SCHEMA_VERSION,
        "phase4_certification_schema_version": PHASE4_CERTIFICATION_SCHEMA_VERSION,
        "artifact_type": "phase4_certification",
        "artifact_id": "phase4:q4-12:phase4-certification",
        "status": "certified" if phase4_certified else "blocked",
        "phase": "Q4",
        "stage": "Q4-12",
        "stage_status": _stage_status(blockers, phase4_certified),
        "generated_at": _now(),
        "public_safe": True,
        "authority_boundary": phase4_authority_boundary(),
        "boundary": NO_EXECUTION_BOUNDARY,
        "no_execution_boundary": NO_EXECUTION_BOUNDARY,
        "certification_logged": False,
        "event_log_required": True,
        "event_log_correlation_id": None,
        "event_log_path": None,
        "event_log_created_at": None,
        "phase4_certified": phase4_certified,
        "phase4_complete": phase4_certified,
        "phase4_exit_gate": phase4_exit_gate,
        "phase5_handoff_allowed": phase5_handoff_allowed,
        "phase5_handoff_scope": (
            "guarded_orchestration_design_only" if phase5_handoff_allowed else "blocked"
        ),
        "phase4_certification_allowed": phase4_certified,
        "certification_blockers": blockers,
        "certification_blocker_count": len(blockers),
        "required_next_steps": _required_next_steps(blockers),
        "artifact_bundle_summary": bundle_summary,
        "artifact_validation_summary": validation_summary,
        "artifact_validation_errors": validations,
        "strategy_explicitness": strategy_explicitness,
        "world_model_validation_status": world_status,
        "phase3_zero_authority": phase3_zero,
        "preference_mcp_certification_gate": preference_gate,
        "approval_state": approval.get("approval_state", "missing"),
        "approval_logged": approval.get("approval_logged") is True,
        "approval_event_id": approval.get("event_log_correlation_id"),
        "approval_required_amendment_count": len(approval.get("required_amendments", [])),
        "strategy_document_fingerprint": artifacts["manifested_strategy_metadata"].get(
            "document_fingerprint"
        ),
        "strategy_document_status": artifacts["manifested_strategy_metadata"].get("status"),
        "strategy_toggle_count": toggles.get("toggle_count", 0),
        "strategy_toggle_event_log_written": toggles.get("event_log_written") is True,
        "draft_strategy_toggle_count": toggles.get("draft_toggle_count", 0),
        "approved_shadow_strategy_toggle_count": toggles.get(
            "approved_shadow_toggle_count",
            0,
        ),
        "trade_candidate_count": 0,
        "risk_agent_handoff_allowed_count": 0,
        "execution_policy_handoff_allowed_count": 0,
        "execution_allowed_count": 0,
        "paper_order_allowed_count": 0,
        "staged_paper_order_allowed_count": 0,
        "broker_write_allowed_count": 0,
        "live_capital_enabled_count": 0,
        "provider_call_allowed_count": 0,
        "hardware_submission_allowed_count": 0,
        "hardware_submitted_count": 0,
        "hardware_scheduler_enabled_count": 0,
        "scheduler_enabled_count": 0,
        "authority_violation_count": len(authority_violations),
        "authority_violations": authority_violations,
        "trade_candidate_creation_allowed": False,
        "trade_candidate_authority": False,
        "risk_approval_allowed": False,
        "risk_agent_handoff_allowed": False,
        "execution_policy_handoff_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "staged_paper_order_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
        "quantum_provider_call_allowed": False,
        "provider_call_allowed": False,
        "quantum_hardware_submission_allowed": False,
        "hardware_submission_allowed": False,
        "hardware_submitted": False,
        "hardware_scheduler_enabled": False,
        "scheduler_enabled": False,
        "market_confirmation_policy": {
            "yahoo_finance_role": "supplemental_market_confirmation_only",
            "yahoo_only_confirmation_allowed": False,
            "canonical_source_promotion_allowed": False,
        },
    }
    artifact["validation_errors"] = validate_phase4_certification(artifact)
    return artifact


def validate_phase4_certification(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "phase4_certification_schema_version",
        "artifact_type",
        "artifact_id",
        "status",
        "phase",
        "stage",
        "stage_status",
        "generated_at",
        "public_safe",
        "authority_boundary",
        "boundary",
        "phase4_certified",
        "phase4_complete",
        "phase4_exit_gate",
        "phase5_handoff_allowed",
        "phase4_certification_allowed",
        "certification_blockers",
        "artifact_bundle_summary",
        "artifact_validation_summary",
        "strategy_explicitness",
        "world_model_validation_status",
        "phase3_zero_authority",
        "preference_mcp_certification_gate",
    }
    missing = sorted(required_fields - set(artifact))
    if missing:
        errors.append("missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PHASE4_ARTIFACT_SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if artifact.get("phase4_certification_schema_version") != PHASE4_CERTIFICATION_SCHEMA_VERSION:
        errors.append("phase4_certification_schema_version_mismatch")
    if artifact.get("artifact_type") != "phase4_certification":
        errors.append("artifact_type_not_phase4_certification")
    if artifact.get("phase") != "Q4" or artifact.get("stage") != "Q4-12":
        errors.append("phase_or_stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("public_safe_not_true")
    if artifact.get("event_log_required") is not True:
        errors.append("event_log_required_not_true")

    approval_state = artifact.get("approval_state")
    approval_logged = artifact.get("approval_logged") is True
    certified = artifact.get("phase4_certified") is True
    blockers = artifact.get("certification_blockers")
    if not isinstance(blockers, list):
        errors.append("certification_blockers_missing")
        blockers = []

    if certified:
        if artifact.get("status") != "certified":
            errors.append("certified_status_mismatch")
        if approval_state != "approved" or not approval_logged:
            errors.append("certified_without_approved_logged_approval")
        if artifact.get("phase5_handoff_allowed") is not True:
            errors.append("certified_without_phase5_handoff")
        if blockers:
            errors.append("certified_with_blockers")
    else:
        if artifact.get("status") != "blocked":
            errors.append("blocked_status_mismatch")
        if artifact.get("phase4_certification_allowed") is not False:
            errors.append("blocked_certification_allowed")
        if artifact.get("phase5_handoff_allowed") is not False:
            errors.append("blocked_phase5_handoff_allowed")
        if approval_state != "approved" and "explicit_fund_manager_approval_required" not in blockers:
            errors.append("missing_explicit_approval_blocker")

    if artifact.get("artifact_bundle_summary", {}).get("error_count", 0) != 0:
        errors.append("artifact_bundle_has_errors")
    if artifact.get("artifact_validation_summary", {}).get("artifact_validation_error_count", 0) != 0:
        errors.append("artifact_validations_have_errors")
    if artifact.get("strategy_explicitness", {}).get("complete") is not True:
        errors.append("strategy_explicitness_incomplete")
    if artifact.get("world_model_validation_status", {}).get("complete") is not True:
        errors.append("world_model_validation_incomplete")
    if artifact.get("phase3_zero_authority", {}).get("violation_count", 0) != 0:
        errors.append("phase3_zero_authority_violation")
    preference_gate = artifact.get("preference_mcp_certification_gate", {})
    if not isinstance(preference_gate, dict):
        errors.append("preference_gate_missing")
        preference_gate = {}
    preference_gate_errors = _validate_preference_certification_gate(preference_gate)
    errors.extend(preference_gate_errors)
    if preference_gate.get("certification_blocker_count", 0) != 0:
        for blocker in preference_gate.get("certification_blockers", []):
            if blocker not in blockers:
                errors.append(f"preference_blocker_missing_from_certification:{blocker}")
    if artifact.get("phase5_handoff_allowed") is True:
        if preference_gate.get("status") != "validated":
            errors.append("phase5_handoff_allowed_with_preference_gate_not_validated")
        if preference_gate.get("certification_blocker_count", 0) != 0:
            errors.append("phase5_handoff_allowed_with_preference_policy_blockers")
    if artifact.get("authority_violation_count") != 0:
        errors.append("authority_violation_count_not_zero")
    if artifact.get("strategy_toggle_event_log_written") is not True:
        errors.append("strategy_toggle_event_log_not_written")

    if approval_state != "approved" and artifact.get("approved_shadow_strategy_toggle_count", 0) != 0:
        errors.append("approved_shadow_toggles_without_approval")
    if approval_state == "approved" and artifact.get("approved_shadow_strategy_toggle_count") != artifact.get("strategy_toggle_count"):
        errors.append("approved_toggles_not_approved_shadow")

    for key in AUTHORITY_COUNT_FIELDS:
        if artifact.get(key, 0) != 0:
            errors.append(f"authority_count_not_zero:{key}")
    for key in AUTHORITY_FLAG_FIELDS:
        if artifact.get(key) is not False:
            errors.append(f"authority_flag_enabled:{key}")
    boundary = artifact.get("no_execution_boundary") or artifact.get("boundary") or ""
    if "cannot create trade candidates" not in boundary:
        errors.append("no_execution_boundary_weak")
    if artifact.get("market_confirmation_policy", {}).get("yahoo_finance_role") != (
        "supplemental_market_confirmation_only"
    ):
        errors.append("yahoo_finance_policy_not_supplemental")
    return errors


def attach_phase4_certification_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(event_log_path or (_runtime_dir(settings) / CERTIFICATION_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        CERTIFICATION_EVENT_TYPE,
        CERTIFICATION_EVENT_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "phase4_certified": output.get("phase4_certified"),
            "phase4_exit_gate": output.get("phase4_exit_gate"),
            "phase5_handoff_allowed": output.get("phase5_handoff_allowed"),
            "approval_state": output.get("approval_state"),
            "approval_logged": output.get("approval_logged"),
            "certification_blockers": output.get("certification_blockers", []),
            "preference_mcp_certification_gate": {
                "status": output.get("preference_mcp_certification_gate", {}).get(
                    "status"
                ),
                "identity_status": output.get(
                    "preference_mcp_certification_gate",
                    {},
                ).get("identity_status"),
                "provenance_status": output.get(
                    "preference_mcp_certification_gate",
                    {},
                ).get("provenance_status"),
                "approved_domain_pack_count": output.get(
                    "preference_mcp_certification_gate",
                    {},
                ).get("approved_domain_pack_count"),
                "source_promotion_status": output.get(
                    "preference_mcp_certification_gate",
                    {},
                ).get("source_promotion_status"),
                "source_promotion_decision_count": output.get(
                    "preference_mcp_certification_gate",
                    {},
                ).get("source_promotion_decision_count"),
                "source_promotion_promoted_decision_count": output.get(
                    "preference_mcp_certification_gate",
                    {},
                ).get("source_promotion_promoted_decision_count"),
                "source_promotion_canonical_source_count_after": output.get(
                    "preference_mcp_certification_gate",
                    {},
                ).get("source_promotion_canonical_source_count_after"),
                "certification_blocker_count": output.get(
                    "preference_mcp_certification_gate",
                    {},
                ).get("certification_blocker_count"),
            },
            "trade_candidate_count": output.get("trade_candidate_count"),
            "execution_allowed_count": output.get("execution_allowed_count"),
            "paper_order_allowed_count": output.get("paper_order_allowed_count"),
            "broker_write_allowed_count": output.get("broker_write_allowed_count"),
            "live_capital_enabled_count": output.get("live_capital_enabled_count"),
            "no_execution_boundary": output.get("no_execution_boundary"),
        },
    )
    output["certification_logged"] = True
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_path"] = str(log.path)
    output["event_log_created_at"] = entry.created_at
    output["validation_errors"] = validate_phase4_certification(output)
    return output, entry


def write_phase4_certification(
    artifact: dict[str, Any],
    path: str | Path | None = None,
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    output = deepcopy(artifact)
    if record_event:
        output, _ = attach_phase4_certification_event_log(
            output,
            event_log_path=event_log_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase4_certification(output)
    output_path = Path(path or (_runtime_dir(settings) / CERTIFICATION_RUNTIME_ARTIFACT))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path, output
