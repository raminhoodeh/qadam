"""Preference/PREF MCP upstream source-promotion decisions.

PREF-12 evaluates specific Preference-backed upstream feeds one at a time. It
does not promote the Preference aggregator as a canonical source, and it keeps
the 35-source registry unchanged unless a named upstream source passes every
promotion gate and receives explicit registry approval.
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.preference_mcp_adapter import fetch_preference_mcp_sample
from orchestrator.preference_mcp_identity import (
    PREFERENCE_PROVIDER_LABEL,
    PREFERENCE_SOURCE_KEY,
    SECRET_LIKE_PATTERNS,
)
from orchestrator.preference_mcp_provenance import (
    build_preference_source_quorum_report,
    preference_provenance_paths,
    validate_preference_source_quorum_report,
)
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT, SOURCE_SPECS


PREFERENCE_SOURCE_PROMOTION_SCHEMA_VERSION = 1
PREFERENCE_SOURCE_PROMOTION_STAGE = "PREF-12"
PREFERENCE_SOURCE_PROMOTION_ARTIFACT_TYPE = "preference_mcp_source_promotion_decisions"
PREFERENCE_SOURCE_PROMOTION_ARTIFACT_ID = "preference:pref-12:source-promotion-decisions"
PREFERENCE_SOURCE_PROMOTION_BOUNDARY = (
    "Preference/PREF MCP PREF-12 records registry decisions for individual "
    "upstream feeds only. It cannot promote the Preference aggregator as source "
    "36, cannot change source counts without a named upstream promotion, cannot "
    "satisfy source quorum, create trade candidates, approve risk, stage or "
    "submit paper orders, write to brokers, call quantum providers, submit "
    "hardware jobs, enable schedulers, or enable live capital."
)

PROMOTION_AUTHORITY_FLAGS: tuple[str, ...] = (
    "preference_aggregator_promoted",
    "source_quorum_credit_allowed",
    "canonical_rank_impact_allowed",
    "trade_candidate_creation_allowed",
    "risk_approval_authority",
    "execution_authority",
    "paper_order_authority",
    "broker_write_authority",
    "fill_confirmation_authority",
    "receipt_evidence_authority",
    "reconciliation_truth_authority",
    "quantum_provider_call_allowed",
    "hardware_submission_allowed",
    "scheduler_enabled",
    "live_capital_authority",
)

PROMOTION_REQUIRED_GATES: tuple[str, ...] = (
    "provenance_gate",
    "freshness_gate",
    "terms_usage_gate",
    "deterministic_test_gate",
    "durable_replay_gate",
    "independent_corroboration_gate",
    "explicit_registry_approval_gate",
)

UPSTREAM_REGISTRY_MAP: dict[str, dict[str, Any]] = {
    "polymarket": {
        "candidate_registry_source_key": "polymarket",
        "registry_decision": "use_existing_registry_source_no_new_count",
        "promotion_status": "not_promoted_existing_registry_source",
        "decision_reason": (
            "Polymarket already has a canonical Qadam registry entry. Preference "
            "may mirror or challenge context later, but it must not replace the "
            "direct CLOB/orderbook adapter or add a second canonical source."
        ),
    },
    "kalshi": {
        "candidate_registry_source_key": "kalshi",
        "registry_decision": "use_existing_registry_source_no_new_count",
        "promotion_status": "not_promoted_existing_registry_source",
        "decision_reason": (
            "Kalshi already has a canonical Qadam registry entry. Preference "
            "context remains supplemental until the direct Kalshi adapter and "
            "credentials are governed through the existing source key."
        ),
    },
    "vessel_tracking": {
        "candidate_registry_source_key": "ais_maritime",
        "registry_decision": "use_existing_combined_ais_registry_source_no_new_count",
        "promotion_status": "not_promoted_existing_registry_source",
        "decision_reason": (
            "Preference vessel context maps to the existing combined AIS Maritime "
            "source. Provider choice and direct adapter behavior remain unresolved, "
            "so no new vessel source is added."
        ),
    },
    "noaa": {
        "candidate_registry_source_key": None,
        "registry_decision": "defer_new_source_pending_direct_endpoint_terms_and_replay_review",
        "promotion_status": "not_promoted_new_source_deferred",
        "decision_reason": (
            "NOAA-style weather context is useful for commodities, but no direct "
            "Qadam registry source, terms review, durable replay contract, or "
            "independent corroboration path has been approved yet."
        ),
    },
    "sec_edgar": {
        "candidate_registry_source_key": "sec_edgar",
        "registry_decision": "use_existing_registry_source_no_new_count",
        "promotion_status": "not_promoted_existing_registry_source",
        "decision_reason": (
            "SEC EDGAR already has a canonical Qadam registry entry. Preference "
            "filing context may challenge observations but cannot count as a "
            "separate source or replace direct SEC provenance."
        ),
    },
    "kol_wallets": {
        "candidate_registry_source_key": None,
        "registry_decision": "defer_new_source_pending_wallet_identity_terms_and_replay_review",
        "promotion_status": "not_promoted_new_source_deferred",
        "decision_reason": (
            "KOL wallet context is risk sentiment only. It needs wallet identity "
            "policy, terms review, replay behavior, and company-truth boundaries "
            "before any canonical-source decision."
        ),
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _events(envelope: dict[str, Any]) -> list[dict[str, Any]]:
    events = envelope.get("events", [])
    return [event for event in events if isinstance(event, dict)] if isinstance(events, list) else []


def _authority_flags() -> dict[str, bool]:
    return {flag: False for flag in PROMOTION_AUTHORITY_FLAGS}


def _contains_secret_like_value(payload: Any) -> bool:
    encoded = json.dumps(payload, sort_keys=True, default=str)
    return any(pattern.search(encoded) for pattern in SECRET_LIKE_PATTERNS)


def _provenance_report(settings: Settings | None = None) -> dict[str, Any]:
    report_path, _history_path = preference_provenance_paths(settings)
    report = _read_json(report_path)
    if report:
        return report
    envelope = fetch_preference_mcp_sample()
    return build_preference_source_quorum_report(preference_events=_events(envelope))


def _sample_events_by_upstream(settings: Settings | None = None) -> dict[str, list[dict[str, Any]]]:
    _ = settings
    envelope = fetch_preference_mcp_sample()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for event in _events(envelope):
        raw_payload = event.get("raw_payload", {})
        if not isinstance(raw_payload, dict):
            continue
        upstream = str(raw_payload.get("upstream_source") or "").strip()
        if not upstream:
            provenance = raw_payload.get("preference_provenance", {})
            if isinstance(provenance, dict):
                upstream = str(provenance.get("upstream_source_name") or "").strip()
        if upstream:
            grouped.setdefault(upstream, []).append(event)
    return grouped


def _observed_provenance_identities(events: list[dict[str, Any]]) -> list[str]:
    identities: list[str] = []
    for event in events:
        raw_payload = event.get("raw_payload", {})
        provenance = raw_payload.get("preference_provenance") if isinstance(raw_payload, dict) else None
        if isinstance(provenance, dict) and provenance.get("upstream_source_identity"):
            identities.append(str(provenance["upstream_source_identity"]))
    return sorted(set(identities))


def _durable_replay_gate(candidate_source_key: str | None, durable: dict[str, Any]) -> str:
    if not candidate_source_key:
        return "blocked_no_canonical_registry_source"
    if durable.get("replay_status") == "ok":
        missing = set(str(item) for item in durable.get("missing_sources") or ())
        if candidate_source_key not in missing:
            return "covered_by_existing_registry_replay"
    return "blocked_pending_direct_adapter_durable_replay"


def _decision_from_upstream(
    upstream_source: str,
    events: list[dict[str, Any]],
    *,
    provenance: dict[str, Any],
    cockpit: dict[str, Any],
) -> dict[str, Any]:
    registry_lookup = {source.key: source for source in SOURCE_SPECS}
    blueprint = deepcopy(UPSTREAM_REGISTRY_MAP.get(upstream_source, {}))
    candidate_key = blueprint.get("candidate_registry_source_key")
    existing_source = registry_lookup.get(candidate_key) if candidate_key else None
    provenance_errors = validate_preference_source_quorum_report(provenance)
    provenance_gate = (
        "passed_sample_provenance"
        if provenance.get("status") == "validated" and not provenance_errors and events
        else "blocked_provenance_not_validated"
    )
    durable_gate = _durable_replay_gate(candidate_key, cockpit.get("durable_ingestion", {}))
    existing_registry_decision = existing_source is not None
    independent_gate = (
        "mapped_to_existing_registry_source"
        if existing_registry_decision
        else "blocked_pending_independent_corroboration_source"
    )
    freshness_gate = "blocked_deterministic_sample_only_no_live_freshness"
    terms_gate = "blocked_pending_direct_upstream_terms_review"
    deterministic_gate = "passed_deterministic_sample_fixture"
    approval_gate = "blocked_pending_explicit_registry_approval"
    gate_statuses = {
        "provenance_gate": provenance_gate,
        "freshness_gate": freshness_gate,
        "terms_usage_gate": terms_gate,
        "deterministic_test_gate": deterministic_gate,
        "durable_replay_gate": durable_gate,
        "independent_corroboration_gate": independent_gate,
        "explicit_registry_approval_gate": approval_gate,
    }
    promotion_ready = all(str(status).startswith("passed") for status in gate_statuses.values())
    promotion_status = str(blueprint.get("promotion_status") or "not_promoted_unmapped_upstream")
    registry_decision = str(
        blueprint.get("registry_decision")
        or "defer_unmapped_source_pending_direct_endpoint_terms_and_replay_review"
    )
    return {
        "upstream_source": upstream_source,
        "source_key": f"preference_upstream:{upstream_source}",
        "candidate_registry_source_key": candidate_key,
        "existing_registry_source": existing_registry_decision,
        "existing_registry_source_status": existing_source.status if existing_source else None,
        "sample_observation_count": len(events),
        "observed_upstream_identity_count": len(_observed_provenance_identities(events)),
        "observed_upstream_identities": _observed_provenance_identities(events),
        "registry_decision": registry_decision,
        "promotion_status": promotion_status,
        "promoted_to_canonical": False,
        "canonical_source_count_delta": 0,
        "source_count_after_decision": EXPECTED_SOURCE_COUNT,
        "preference_context_role_after_decision": "supplemental_challenge_context_only",
        "promotion_ready": promotion_ready,
        "promotion_blockers": [
            gate
            for gate, status in gate_statuses.items()
            if not str(status).startswith("passed")
            and status != "mapped_to_existing_registry_source"
        ],
        "gate_statuses": gate_statuses,
        "decision_reason": blueprint.get("decision_reason")
        or "No Preference-backed upstream source is promoted without a direct endpoint, terms review, replay contract, and explicit registry approval.",
        "source_quorum_credit_allowed": False,
        "canonical_rank_impact_allowed": False,
        "trade_candidate_creation_allowed": False,
        "authority_flags": _authority_flags(),
    }


def build_preference_source_promotion_decisions(
    settings: Settings | None = None,
    *,
    cockpit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    runtime = _runtime_dir(settings)
    cockpit = cockpit or _read_json(runtime / "cockpit-status.json") or {}
    if not cockpit:
        from orchestrator.cockpit_status import build_cockpit_status

        cockpit = build_cockpit_status(settings)
    provenance = _provenance_report(settings)
    events_by_upstream = _sample_events_by_upstream(settings)
    decisions = [
        _decision_from_upstream(
            upstream,
            events_by_upstream.get(upstream, []),
            provenance=provenance,
            cockpit=cockpit,
        )
        for upstream in sorted(UPSTREAM_REGISTRY_MAP)
    ]
    promoted = [decision for decision in decisions if decision.get("promoted_to_canonical") is True]
    existing_registry = [
        decision for decision in decisions if decision.get("existing_registry_source") is True
    ]
    new_source_deferred = [
        decision
        for decision in decisions
        if decision.get("existing_registry_source") is not True
    ]
    authority_flags = _authority_flags()
    artifact = {
        "schema_version": PREFERENCE_SOURCE_PROMOTION_SCHEMA_VERSION,
        "artifact_type": PREFERENCE_SOURCE_PROMOTION_ARTIFACT_TYPE,
        "artifact_id": PREFERENCE_SOURCE_PROMOTION_ARTIFACT_ID,
        "phase": "PREF",
        "stage": PREFERENCE_SOURCE_PROMOTION_STAGE,
        "status": "validated",
        "generated_at": _now(),
        "public_safe": True,
        "source_key": PREFERENCE_SOURCE_KEY,
        "provider_label": PREFERENCE_PROVIDER_LABEL,
        "expected_canonical_source_count": EXPECTED_SOURCE_COUNT,
        "canonical_source_count_before": EXPECTED_SOURCE_COUNT,
        "canonical_source_count_after": EXPECTED_SOURCE_COUNT,
        "canonical_source_count_delta": 0,
        "preference_aggregator_promoted": False,
        "preference_mcp_source_36": False,
        "decision_count": len(decisions),
        "promoted_decision_count": len(promoted),
        "existing_registry_decision_count": len(existing_registry),
        "new_source_deferred_count": len(new_source_deferred),
        "required_promotion_gates": list(PROMOTION_REQUIRED_GATES),
        "decisions": decisions,
        "first_concrete_registry_decision": decisions[0] if decisions else {},
        "source_quorum_credit_allowed": False,
        "canonical_rank_impact_allowed": False,
        "trade_candidate_creation_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
        "authority_flags": authority_flags,
        "boundary": PREFERENCE_SOURCE_PROMOTION_BOUNDARY,
    }
    artifact["validation_errors"] = validate_preference_source_promotion_decisions(artifact)
    artifact["status"] = "validated" if not artifact["validation_errors"] else "rejected"
    return artifact


def validate_preference_source_promotion_decisions(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version",
        "artifact_type",
        "stage",
        "public_safe",
        "source_key",
        "provider_label",
        "expected_canonical_source_count",
        "canonical_source_count_before",
        "canonical_source_count_after",
        "canonical_source_count_delta",
        "preference_aggregator_promoted",
        "preference_mcp_source_36",
        "decision_count",
        "promoted_decision_count",
        "existing_registry_decision_count",
        "new_source_deferred_count",
        "required_promotion_gates",
        "decisions",
        "authority_flags",
        "boundary",
    }
    for field in sorted(required - set(artifact)):
        errors.append(f"missing_field:{field}")
    if artifact.get("schema_version") != PREFERENCE_SOURCE_PROMOTION_SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if artifact.get("artifact_type") != PREFERENCE_SOURCE_PROMOTION_ARTIFACT_TYPE:
        errors.append("artifact_type_not_preference_source_promotion_decisions")
    if artifact.get("stage") != PREFERENCE_SOURCE_PROMOTION_STAGE:
        errors.append("stage_not_pref_12")
    if artifact.get("public_safe") is not True:
        errors.append("public_safe_not_true")
    if artifact.get("source_key") != PREFERENCE_SOURCE_KEY:
        errors.append("source_key_mismatch")
    if artifact.get("provider_label") != PREFERENCE_PROVIDER_LABEL:
        errors.append("provider_label_mismatch")
    if artifact.get("preference_aggregator_promoted") is not False:
        errors.append("preference_aggregator_promoted")
    if artifact.get("preference_mcp_source_36") is not False:
        errors.append("preference_mcp_source_36")
    if artifact.get("expected_canonical_source_count") != EXPECTED_SOURCE_COUNT:
        errors.append("expected_canonical_source_count_mismatch")
    if artifact.get("canonical_source_count_before") != EXPECTED_SOURCE_COUNT:
        errors.append("canonical_source_count_before_mismatch")
    if artifact.get("canonical_source_count_after") != EXPECTED_SOURCE_COUNT:
        errors.append("canonical_source_count_after_mismatch")
    if artifact.get("canonical_source_count_delta") != 0:
        errors.append("canonical_source_count_delta_nonzero")
    if artifact.get("source_quorum_credit_allowed") is not False:
        errors.append("source_quorum_credit_allowed")
    if artifact.get("canonical_rank_impact_allowed") is not False:
        errors.append("canonical_rank_impact_allowed")

    decisions = artifact.get("decisions", [])
    if not isinstance(decisions, list):
        errors.append("decisions_not_list")
        decisions = []
    if artifact.get("decision_count") != len(decisions):
        errors.append("decision_count_mismatch")
    if len(decisions) < 1:
        errors.append("no_upstream_registry_decisions")
    if sorted(artifact.get("required_promotion_gates", [])) != sorted(PROMOTION_REQUIRED_GATES):
        errors.append("required_promotion_gates_mismatch")

    promoted_count = 0
    existing_count = 0
    new_deferred_count = 0
    seen_upstreams: set[str] = set()
    registry_keys = {source.key for source in SOURCE_SPECS}
    for decision in decisions:
        if not isinstance(decision, dict):
            errors.append("decision_not_object")
            continue
        upstream = str(decision.get("upstream_source") or "")
        if not upstream:
            errors.append("decision_upstream_missing")
        if upstream in seen_upstreams:
            errors.append(f"duplicate_upstream_decision:{upstream}")
        seen_upstreams.add(upstream)
        candidate_key = decision.get("candidate_registry_source_key")
        existing_registry_source = decision.get("existing_registry_source") is True
        if existing_registry_source:
            existing_count += 1
            if candidate_key not in registry_keys:
                errors.append(f"existing_registry_source_key_unknown:{upstream}:{candidate_key}")
        else:
            new_deferred_count += 1
        if decision.get("promoted_to_canonical") is True:
            promoted_count += 1
            gate_statuses = decision.get("gate_statuses", {})
            for gate in PROMOTION_REQUIRED_GATES:
                if not str(gate_statuses.get(gate) or "").startswith("passed"):
                    errors.append(f"promoted_without_gate:{upstream}:{gate}")
        else:
            if int(decision.get("canonical_source_count_delta", 0) or 0) != 0:
                errors.append(f"non_promoted_decision_changes_source_count:{upstream}")
        if decision.get("source_count_after_decision") != EXPECTED_SOURCE_COUNT:
            errors.append(f"decision_source_count_after_mismatch:{upstream}")
        for key in (
            "source_quorum_credit_allowed",
            "canonical_rank_impact_allowed",
            "trade_candidate_creation_allowed",
        ):
            if decision.get(key) is not False:
                errors.append(f"decision_authority_enabled:{upstream}:{key}")
        flags = decision.get("authority_flags", {})
        if not isinstance(flags, dict):
            errors.append(f"decision_authority_flags_missing:{upstream}")
        else:
            for flag in PROMOTION_AUTHORITY_FLAGS:
                if flags.get(flag) is not False:
                    errors.append(f"decision_authority_flag_enabled:{upstream}:{flag}")

    if artifact.get("promoted_decision_count") != promoted_count:
        errors.append("promoted_decision_count_mismatch")
    if artifact.get("existing_registry_decision_count") != existing_count:
        errors.append("existing_registry_decision_count_mismatch")
    if artifact.get("new_source_deferred_count") != new_deferred_count:
        errors.append("new_source_deferred_count_mismatch")
    if promoted_count != 0:
        errors.append("unexpected_promoted_decision")

    flags = artifact.get("authority_flags", {})
    if not isinstance(flags, dict):
        errors.append("authority_flags_not_object")
    else:
        for flag in PROMOTION_AUTHORITY_FLAGS:
            if flags.get(flag) is not False:
                errors.append(f"authority_flag_enabled:{flag}")
    for key in (
        "trade_candidate_creation_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
    ):
        if artifact.get(key) is not False:
            errors.append(f"artifact_authority_enabled:{key}")
    if "cannot promote the Preference aggregator" not in str(artifact.get("boundary") or ""):
        errors.append("boundary_missing_aggregator_promotion_block")
    if _contains_secret_like_value(artifact):
        errors.append("secret_like_value_exposed")
    return errors


def preference_source_promotion_paths(settings: Settings | None = None) -> tuple[Path, Path]:
    settings = settings or Settings.from_env()
    runtime_dir = Path(settings.runtime_dir)
    return (
        runtime_dir / "preference_source_promotion_decisions.json",
        runtime_dir / "preference_source_promotion_decisions_history.jsonl",
    )


def write_preference_source_promotion_decisions(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
) -> tuple[Path, Path]:
    output_path, history_path = preference_source_promotion_paths(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    artifact["runtime_artifact_path"] = str(output_path)
    artifact["history_log_path"] = str(history_path)
    artifact["validation_errors"] = validate_preference_source_promotion_decisions(artifact)
    artifact["status"] = "validated" if not artifact["validation_errors"] else "rejected"
    output_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PREFERENCE_SOURCE_PROMOTION_SCHEMA_VERSION,
        "artifact_id": artifact.get("artifact_id"),
        "stage": artifact.get("stage"),
        "status": artifact.get("status"),
        "generated_at": artifact.get("generated_at"),
        "recorded_at": _now(),
        "decision_count": artifact.get("decision_count"),
        "promoted_decision_count": artifact.get("promoted_decision_count"),
        "canonical_source_count_after": artifact.get("canonical_source_count_after"),
        "validation_error_count": len(artifact.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path
