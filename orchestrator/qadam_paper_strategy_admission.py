"""Deterministic paper-only admission receipts for immutable QEG strategies."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import now_iso, read_json, runtime_dir, sha256_json, write_json_atomic
from orchestrator.qadam_qeg_common import PAPER_ADMISSION_ARTIFACT, STRATEGY_VERSIONS_ARTIFACT, qeg_authority, stable_id, write_phase_status

SIGNATURE_ACTOR = "python_autonomous_governance_engine"


def sign_admission(strategy: dict[str, Any], policy: dict[str, Any], *, issued_at: str, expires_at: str) -> dict[str, Any]:
    signed_fields = {
        "strategy_version_id": strategy.get("strategy_version_id"),
        "immutable_contract_hash": strategy.get("immutable_contract_hash"),
        "evidence_hash": strategy.get("evidence_hash"),
        "policy_version": policy.get("policy_version") or policy.get("policy_id"),
        "policy_hash": policy.get("policy_hash") or sha256_json(policy),
        "issued_at": issued_at,
        "expires_at": expires_at,
        "scope": "paper_strategy_admission_only",
    }
    return {
        "actor": SIGNATURE_ACTOR,
        "algorithm": "sha256_canonical_json_content_seal",
        "signed_fields": signed_fields,
        "value": sha256_json(signed_fields),
    }


def verify_admission_signature(signature: dict[str, Any]) -> bool:
    return (
        signature.get("actor") == SIGNATURE_ACTOR
        and signature.get("algorithm") == "sha256_canonical_json_content_seal"
        and signature.get("value") == sha256_json(signature.get("signed_fields") or {})
    )


def build_paper_strategy_admission(settings: Settings | None = None) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    generated_at = now_iso()
    foundry = read_json(runtime / STRATEGY_VERSIONS_ARTIFACT)
    experimental_policy = read_json(runtime / "qadam_experimental_paper_policy.json")
    validated_policy = read_json(runtime / "qadam_autonomous_strategy_admission_policy.json")
    issued = datetime.now(timezone.utc)
    expires_at = (issued + timedelta(hours=24)).isoformat()
    decisions: list[dict[str, Any]] = []
    for strategy in foundry.get("versions") or []:
        evidence_class = str(strategy.get("evidence_class") or "")
        policy = validated_policy if evidence_class == "validated_paper_strategy" else experimental_policy
        contract = strategy.get("contract") if isinstance(strategy.get("contract"), dict) else {}
        blockers: list[str] = []
        if foundry.get("status") != "passed":
            blockers.append("strategy_foundry_not_passed")
        if strategy.get("admission_state") != "paper_discovery_eligible":
            blockers.append("strategy_not_paper_discovery_eligible")
        if contract.get("maximum_notional_usd", 0) > 5000:
            blockers.append("paper_risk_ceiling_exceeded")
        if policy.get("live_capital_enabled") is not False:
            blockers.append("policy_live_capital_not_disabled")
        if not strategy.get("evidence_hash") or not strategy.get("immutable_contract_hash"):
            blockers.append("strategy_evidence_or_contract_hash_missing")
        if evidence_class == "experimental_unvalidated" and contract.get("paper_risk_tier") != "discovery_micro":
            blockers.append("experimental_strategy_wrong_risk_tier")
        signature = sign_admission(strategy, policy, issued_at=generated_at, expires_at=expires_at)
        admitted = not blockers
        decisions.append(
            {
                "admission_decision_id": stable_id("qeg-paper-admission", strategy.get("strategy_version_id"), signature["value"]),
                "strategy_version_id": strategy.get("strategy_version_id"),
                "decision": "admitted_for_paper_discovery" if admitted else "not_admitted",
                "paper_strategy_admitted": admitted,
                "evidence_class": evidence_class,
                "policy_version": signature["signed_fields"]["policy_version"],
                "issued_at": generated_at,
                "expires_at": expires_at,
                "blockers": blockers,
                "signature": signature,
                "signature_valid": verify_admission_signature(signature),
                "execution_approval_created": False,
                "risk_envelope_mutated": False,
                "paper_order_created": False,
                "live_strategy_admitted": False,
                "authority": qeg_authority(governed_projection=True),
            }
        )
    errors: list[str] = []
    if foundry.get("status") != "passed":
        errors.append("strategy_foundry_not_passed")
    if any(not row.get("signature_valid") for row in decisions):
        errors.append("paper_admission_signature_invalid")
    if any(row.get("risk_envelope_mutated") or row.get("execution_approval_created") or row.get("paper_order_created") for row in decisions):
        errors.append("paper_admission_authority_violation")
    payload = {
        "schema_version": "qadam_paper_strategy_admission.v1",
        "artifact_type": "qadam_paper_strategy_admission",
        "generated_at": generated_at,
        "status": "passed" if not errors else "blocked",
        "decision_count": len(decisions),
        "admitted_count": sum(row["paper_strategy_admitted"] for row in decisions),
        "not_admitted_count": sum(not row["paper_strategy_admitted"] for row in decisions),
        "decisions": decisions,
        "automatic_scope": "declarative_paper_strategy_inside_frozen_risk_envelope",
        "code_prompt_provider_live_capital_and_expanded_risk_changes_automatic": False,
        "validation_errors": errors,
        "authority": qeg_authority(governed_projection=True),
    }
    write_json_atomic(runtime / PAPER_ADMISSION_ARTIFACT, payload)
    write_phase_status(
        "QEG-10", status=payload["status"], implementation_complete=not errors,
        empirical_state="strategy_versions_evaluated_no_current_admission" if not payload["admitted_count"] else "paper_strategy_versions_admitted",
        artifacts=[STRATEGY_VERSIONS_ARTIFACT, PAPER_ADMISSION_ARTIFACT], blockers=errors, settings=settings,
    )
    return payload, errors


def validate_paper_strategy_admission(settings: Settings | None = None) -> list[str]:
    payload = read_json(runtime_dir(settings) / PAPER_ADMISSION_ARTIFACT)
    errors = list(payload.get("validation_errors") or [])
    for row in payload.get("decisions") or []:
        if not verify_admission_signature(row.get("signature") or {}):
            errors.append("paper_admission_signature_invalid")
        if row.get("live_strategy_admitted") or row.get("paper_order_created"):
            errors.append("paper_admission_authority_violation")
    return sorted(set(errors))
