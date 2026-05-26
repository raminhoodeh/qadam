"""Phase 4 Manifested Strategy Draft metadata and validation."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.phase4_artifacts import (
    PHASE4_ARTIFACT_SCHEMA_VERSION,
    phase4_authority_boundary,
    validate_phase4_artifact,
)
from orchestrator.phase4_candidate_strategy_universe import build_candidate_strategy_universe


MANIFESTED_STRATEGY_METADATA_SCHEMA_VERSION = 1
MANIFESTED_STRATEGY_PATH = Path("docs/qadam-manifested-strategy.md")

REQUIRED_DOCUMENT_TERMS: tuple[str, ...] = (
    "active instruments",
    "excluded instruments",
    "catalyst classes",
    "source weights",
    "model weights",
    "market-confirmation requirements",
    "Preference/PREF MCP",
    "domain packs",
    "source-quorum rule",
    "quota/freshness degradation rule",
    "Preference-only context",
    "quantum role",
    "risk assumptions",
    "invalidation conditions",
    "no-trade conditions",
    "No execution",
)

STRATEGY_DOCUMENT_AUTHORITY_FIELDS: tuple[str, ...] = (
    "trade_candidate_creation_allowed",
    "risk_approval_allowed",
    "risk_agent_handoff_allowed",
    "execution_policy_handoff_allowed",
    "execution_allowed",
    "paper_order_allowed",
    "staged_paper_order_allowed",
    "broker_write_allowed",
    "live_capital_enabled",
    "preference_live_mcp_call_allowed",
    "preference_paid_tool_calls_allowed",
    "preference_source_quorum_credit_allowed",
    "preference_only_confirmation_allowed",
    "preference_trade_candidate_creation_allowed",
    "quantum_provider_call_allowed",
    "quantum_hardware_submission_allowed",
    "scheduler_enabled",
)


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


def _document_text(path: str | Path = MANIFESTED_STRATEGY_PATH) -> str:
    document_path = Path(path)
    if not document_path.exists():
        return ""
    return document_path.read_text(encoding="utf-8")


def _fingerprint(text: str) -> str | None:
    if not text.strip():
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _slug_to_title(value: str) -> str:
    return value.replace("_", " ").title()


def _candidate_terms(candidate_universe: dict[str, Any]) -> dict[str, Any]:
    candidates = candidate_universe.get("candidates", [])
    active_instruments = sorted(
        {
            str(instrument)
            for candidate in candidates
            for instrument in candidate.get("instrument_universe", [])
            if str(instrument).strip()
        }
    )
    catalyst_classes = sorted(
        {
            str(catalyst)
            for candidate in candidates
            for catalyst in candidate.get("catalyst_classes", [])
            if str(catalyst).strip()
        }
    )
    candidate_keys = [str(candidate.get("candidate_key")) for candidate in candidates if candidate.get("candidate_key")]
    candidate_names = [str(candidate.get("name")) for candidate in candidates if candidate.get("name")]
    preference_policies = [
        candidate.get("preference_context_policy", {})
        for candidate in candidates
        if isinstance(candidate.get("preference_context_policy"), dict)
    ]
    preference_domain_packs = sorted(
        {
            str(pack.get("domain_pack"))
            for policy in preference_policies
            for pack in policy.get("mapped_domain_packs", [])
            if isinstance(pack, dict) and pack.get("domain_pack")
        }
    )
    return {
        "active_instruments": active_instruments,
        "catalyst_classes": catalyst_classes,
        "candidate_keys": candidate_keys,
        "candidate_names": candidate_names,
        "preference_domain_packs": preference_domain_packs,
        "preference_policy_candidate_count": len(preference_policies),
    }


def _authority_defaults() -> dict[str, bool]:
    return {field: False for field in STRATEGY_DOCUMENT_AUTHORITY_FIELDS}


def validate_manifested_strategy_metadata(artifact: dict[str, Any], *, document_text: str | None = None) -> list[str]:
    errors = list(validate_phase4_artifact(artifact))
    if artifact.get("artifact_type") != "manifested_strategy_metadata":
        errors.append("artifact_type_not_manifested_strategy_metadata")
    text = document_text if document_text is not None else _document_text(str(artifact.get("document_path") or ""))
    lowered = text.lower()
    for term in REQUIRED_DOCUMENT_TERMS:
        if term.lower() not in lowered:
            errors.append(f"manifested_strategy_missing_term:{term}")

    candidate_keys = artifact.get("strategy_family_candidate_keys")
    if not isinstance(candidate_keys, list) or not candidate_keys:
        errors.append("strategy_family_candidate_keys_missing")
        candidate_keys = []
    for candidate_key in candidate_keys:
        if str(candidate_key).lower() not in lowered:
            errors.append(f"manifested_strategy_missing_candidate:{candidate_key}")

    active_instruments = artifact.get("active_instruments")
    if not isinstance(active_instruments, list) or not active_instruments:
        errors.append("active_instruments_missing")
        active_instruments = []
    for instrument in active_instruments:
        if str(instrument).lower() not in lowered:
            errors.append(f"manifested_strategy_missing_instrument:{instrument}")

    if artifact.get("document_fingerprint") != _fingerprint(text):
        errors.append("document_fingerprint_mismatch")
    if artifact.get("document_fingerprint") is None:
        errors.append("document_fingerprint_missing")
    if artifact.get("approval_required") is not True:
        errors.append("approval_required_not_true")
    if artifact.get("approval_state") != "not_requested":
        errors.append("approval_state_not_not_requested")
    if artifact.get("approved_shadow_ready") is not False:
        errors.append("approved_shadow_ready_not_false")
    if artifact.get("trade_candidate_count") != 0:
        errors.append("trade_candidate_count_not_zero")
    if re.search(r"\btrade_candidate\b", text):
        errors.append("manifested_strategy_uses_trade_candidate_token")

    preference_manifestation = artifact.get("preference_mcp_manifestation", {})
    if not isinstance(preference_manifestation, dict):
        errors.append("preference_manifestation_missing")
    else:
        if preference_manifestation.get("source_role") != "supplemental_multi_source_data_plane":
            errors.append("preference_manifestation_role_invalid")
        if preference_manifestation.get("candidate_family_with_policy_count") != artifact.get(
            "strategy_family_candidate_count"
        ):
            errors.append("preference_manifestation_family_coverage_incomplete")
        if int(preference_manifestation.get("approved_domain_pack_count", 0) or 0) < 1:
            errors.append("preference_manifestation_domain_packs_missing")
        for domain_pack in preference_manifestation.get("approved_domain_packs", []):
            if str(domain_pack).lower() not in lowered:
                errors.append(f"manifested_strategy_missing_preference_domain_pack:{domain_pack}")
        for key in (
            "source_quorum_credit_allowed",
            "preference_only_confirmation_allowed",
            "trade_candidate_creation_allowed",
            "risk_handoff_allowed",
            "execution_allowed",
            "paper_order_allowed",
            "broker_write_allowed",
            "live_capital_enabled",
        ):
            if preference_manifestation.get(key) is not False:
                errors.append(f"preference_manifestation_authority_enabled:{key}")
        degradation_rule = str(preference_manifestation.get("quota_freshness_degradation_rule") or "")
        if "quota" not in degradation_rule.lower() or "freshness" not in degradation_rule.lower():
            errors.append("preference_manifestation_quota_freshness_rule_missing")

    for field in STRATEGY_DOCUMENT_AUTHORITY_FIELDS:
        if artifact.get(field) is not False:
            errors.append(f"manifested_strategy_authority_enabled:{field}")
    return errors


def build_manifested_strategy_metadata(
    path: str | Path = MANIFESTED_STRATEGY_PATH,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    candidate_universe = _candidate_universe(settings)
    text = _document_text(path)
    candidate_terms = _candidate_terms(candidate_universe)
    authority_fields = _authority_defaults()
    active_instruments = candidate_terms["active_instruments"]
    catalyst_classes = candidate_terms["catalyst_classes"]
    artifact = {
        "schema_version": PHASE4_ARTIFACT_SCHEMA_VERSION,
        "manifested_strategy_metadata_schema_version": MANIFESTED_STRATEGY_METADATA_SCHEMA_VERSION,
        "artifact_type": "manifested_strategy_metadata",
        "artifact_id": "phase4:q4-8:manifested-strategy-draft",
        "status": "validated",
        "generated_at": _now(),
        "public_safe": True,
        "authority_boundary": phase4_authority_boundary(),
        "boundary": "Manifested Strategy Draft is a strategy-governance document only and cannot enable execution.",
        "document_path": str(path),
        "document_fingerprint": _fingerprint(text),
        "active_instrument_count": len(active_instruments),
        "active_instruments": active_instruments,
        "excluded_instruments": [
            "single-name equities outside approved exposure maps",
            "crypto perpetuals",
            "leveraged ETFs",
            "private placements",
            "illiquid OTC products",
        ],
        "catalyst_class_count": len(catalyst_classes),
        "catalyst_classes": catalyst_classes,
        "strategy_family_candidate_count": int(candidate_universe.get("strategy_family_candidate_count") or 0),
        "strategy_family_candidate_keys": candidate_terms["candidate_keys"],
        "strategy_family_candidate_names": candidate_terms["candidate_names"],
        "candidate_strategy_universe_artifact_id": candidate_universe.get("artifact_id"),
        "candidate_strategy_universe_status": candidate_universe.get("status"),
        "preference_mcp_manifestation": {
            "source_key": "preference_mcp",
            "source_role": "supplemental_multi_source_data_plane",
            "candidate_family_with_policy_count": candidate_terms["preference_policy_candidate_count"],
            "approved_domain_packs": candidate_terms["preference_domain_packs"],
            "approved_domain_pack_count": len(candidate_terms["preference_domain_packs"]),
            "source_quorum_rule": (
                "Preference cannot satisfy source quorum. Only promoted upstream sources with explicit "
                "registry decisions can count toward canonical source quorum."
            ),
            "quota_freshness_degradation_rule": (
                "Preference quota or freshness degradation, unverified identity, stale context, or missing "
                "provenance keeps Preference hold-only and blocks any confidence upgrade."
            ),
            "source_quorum_credit_allowed": False,
            "preference_only_confirmation_allowed": False,
            "trade_candidate_creation_allowed": False,
            "risk_handoff_allowed": False,
            "execution_allowed": False,
            "paper_order_allowed": False,
            "broker_write_allowed": False,
            "live_capital_enabled": False,
            "boundary": (
                "Preference/PREF MCP is supplemental context only and cannot create or approve strategy, "
                "risk, execution, broker, quantum, scheduler, or live-capital actions."
            ),
        },
        "trade_candidate_count": 0,
        "approval_required": True,
        "approval_state": "not_requested",
        "approval_event_logged": False,
        "approved_shadow_ready": False,
        "event_log_correlation_id": None,
        **authority_fields,
    }
    validation_errors = validate_manifested_strategy_metadata(artifact, document_text=text)
    artifact["validation_errors"] = validation_errors
    artifact["status"] = "validated" if not validation_errors else "rejected"
    return artifact


def write_manifested_strategy_metadata(
    artifact: dict[str, Any],
    path: str | Path | None = None,
    *,
    settings: Settings | None = None,
) -> Path:
    output_path = Path(path or (_runtime_dir(settings) / "phase4_manifested_strategy_metadata.json"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def strategy_document_section_title(candidate_key: str) -> str:
    return _slug_to_title(candidate_key)
