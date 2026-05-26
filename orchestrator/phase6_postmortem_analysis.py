"""Q6-6 deterministic postmortem analysis packets.

This stage splits the Q6-5 postmortem draft into focused analysis packets for
catalyst, pricing, regime, execution, and override readiness. The packets are
draft-only evidence summaries: they cite source refs, expose uncertainty and
missing evidence, and cannot approve postmortems, write learning state, mutate
policy, or change strategies.
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.phase6_artifacts import (
    PHASE6_ARTIFACT_SCHEMA_VERSION,
    PHASE6_UNSAFE_COUNT_FIELDS,
    phase6_authority_defaults,
    phase6_authority_ledger,
    phase6_event_contract,
    phase6_provenance,
    phase6_source_posture,
    phase6_unsafe_counter_defaults,
    validate_phase6_artifact,
)
from orchestrator.phase6_postmortem_agent import (
    PHASE6_POSTMORTEM_DRAFT_RUNTIME_ARTIFACT,
    validate_phase6_postmortem_draft,
)


PHASE6_POSTMORTEM_ANALYSIS_SCHEMA_VERSION = 1
PHASE6_POSTMORTEM_ANALYSIS_RUNTIME_ARTIFACT = "phase6_postmortem_analysis_packets.json"
PHASE6_POSTMORTEM_ANALYSIS_HISTORY = "phase6_postmortem_analysis_packets_history.jsonl"
PHASE6_POSTMORTEM_ANALYSIS_EVENT_LOG = "phase6_postmortem_analysis_packets_events.jsonl"
PHASE6_POSTMORTEM_ANALYSIS_EVENT_TYPE = "phase6_postmortem_analysis_packets_created"
PHASE6_POSTMORTEM_ANALYSIS_COMPONENT = "phase6_postmortem_analysis"

SOURCE_POSTMORTEM_DRAFT_REF = f"data/runtime/{PHASE6_POSTMORTEM_DRAFT_RUNTIME_ARTIFACT}"

ANALYSIS_PACKET_TYPES: tuple[str, ...] = (
    "catalyst_analysis",
    "pricing_analysis",
    "regime_analysis",
    "execution_analysis",
    "override_analysis",
)

PHASE6_POSTMORTEM_ANALYSIS_BOUNDARY = (
    "Q6-6 creates deterministic local analysis packets only. It can split a "
    "Q6-5 postmortem draft into catalyst, pricing, regime, execution, and "
    "override-readiness packets with cited claims, confidence, uncertainty, "
    "and missing evidence, but it cannot approve a postmortem, cannot approve "
    "learning actions, cannot write learning data, cannot write a Knowledge "
    "Graph, cannot update model weights, cannot update trust scores, cannot "
    "mutate policy, cannot mutate strategies, cannot call broker POST routes, "
    "cannot call Alpaca POST routes, cannot call live endpoints, cannot enable "
    "live capital, and cannot count Phase 5 test trades toward Phase 7 proof."
)

WRITE_DISABLED_FIELDS: tuple[str, ...] = (
    "postmortem_approved",
    "learning_write_allowed",
    "learning_write_created",
    "knowledge_graph_write_created",
    "model_weight_update_created",
    "trust_score_update_created",
    "policy_mutation_created",
    "strategy_mutation_created",
    "phase5_source_artifacts_mutated",
    "phase7_proof_credit_allowed",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _repo_root(settings: Settings | None = None) -> Path:
    return _runtime_dir(settings).parent.parent


def _path(ref: str, settings: Settings | None = None) -> Path:
    return _repo_root(settings) / ref


def _read_json(ref: str, settings: Settings | None = None) -> dict[str, Any] | None:
    path = _path(ref, settings)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _disabled_write_fields() -> dict[str, bool]:
    return {field: False for field in WRITE_DISABLED_FIELDS}


def _has_local_path(ref: str) -> bool:
    if ref.startswith("/") or ref.startswith("~"):
        return True
    return len(ref) > 2 and ref[1:3] == ":\\"


def phase6_postmortem_analysis_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE6_POSTMORTEM_ANALYSIS_RUNTIME_ARTIFACT,
        runtime / PHASE6_POSTMORTEM_ANALYSIS_HISTORY,
        runtime / PHASE6_POSTMORTEM_ANALYSIS_EVENT_LOG,
    )


def _source_refs(draft: dict[str, Any]) -> list[str]:
    refs = [SOURCE_POSTMORTEM_DRAFT_REF]
    provenance = draft.get("provenance", {})
    if isinstance(provenance, dict):
        for ref in provenance.get("source_refs", []):
            if isinstance(ref, str) and ref not in refs:
                refs.append(ref)
    outcome_ref = draft.get("source_outcome_artifact_ref")
    if isinstance(outcome_ref, str) and outcome_ref not in refs:
        refs.append(outcome_ref)
    return refs


def _provenance(draft: dict[str, Any]) -> dict[str, Any]:
    provenance = phase6_provenance(tuple(_source_refs(draft)))
    draft_provenance = draft.get("provenance", {})
    if isinstance(draft_provenance, dict):
        for bucket in (
            "execution_evidence_refs",
            "market_context_refs",
            "model_interpretation_refs",
            "governance_refs",
        ):
            values = [
                ref for ref in draft_provenance.get(bucket, []) if isinstance(ref, str)
            ]
            provenance[bucket] = values
    return provenance


def _packet_sections(draft: dict[str, Any]) -> dict[str, dict[str, Any]]:
    packet = _dict(draft.get("packet"))
    sections = _list(packet.get("sections"))
    return {
        str(section.get("section_key")): section
        for section in sections
        if isinstance(section, dict) and section.get("section_key")
    }


def _section_source_refs(draft: dict[str, Any], section_key: str) -> list[str]:
    sections = _packet_sections(draft)
    section = sections.get(section_key, {})
    refs: list[str] = []
    for assertion in _list(section.get("assertions")):
        if not isinstance(assertion, dict):
            continue
        for ref in _list(assertion.get("source_refs")):
            if isinstance(ref, str) and ref and ref not in refs:
                refs.append(ref)
    if refs:
        return refs
    return [SOURCE_POSTMORTEM_DRAFT_REF]


def _outcome_record(draft: dict[str, Any]) -> dict[str, Any]:
    outcome_ref = draft.get("source_outcome_artifact_ref")
    outcome = _read_json(str(outcome_ref)) if isinstance(outcome_ref, str) else None
    records = outcome.get("outcome_records", []) if isinstance(outcome, dict) else []
    if isinstance(records, list) and records and isinstance(records[0], dict):
        return records[0]
    return {}


def _claim(
    packet_type: str,
    ordinal: int,
    claim_kind: str,
    statement: str,
    source_refs: list[str],
    confidence: float,
    *,
    conclusion: bool = False,
) -> dict[str, Any]:
    return {
        "claim_id": f"q6-6:{packet_type}:{ordinal}",
        "claim_kind": claim_kind,
        "statement": statement,
        "source_refs": source_refs,
        "confidence": confidence,
        "conclusion": conclusion,
        "review_required": True,
    }


def _uncertainty(field: str, reason: str, source_refs: list[str]) -> dict[str, Any]:
    return {
        "field": field,
        "reason": reason,
        "source_refs": source_refs,
        "review_required": True,
    }


def _missing_evidence(field: str, reason: str, source_refs: list[str]) -> dict[str, Any]:
    return {
        "field": field,
        "reason": reason,
        "source_refs": source_refs,
        "required_for_review": True,
    }


def _analysis_packet(
    packet_type: str,
    *,
    source_outcome_ref: str | None,
    source_closed_trade_ref: str | None,
    source_refs: list[str],
    claims: list[dict[str, Any]],
    confidence: float,
    confidence_label: str,
    uncertainty: list[dict[str, Any]],
    missing_evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "packet_id": f"phase6:q6-6:{packet_type}:crude_oil_energy_security_disruption",
        "analysis_packet_type": packet_type,
        "analysis_state": "deterministic_analysis_packet_created",
        "source_postmortem_draft_ref": SOURCE_POSTMORTEM_DRAFT_REF,
        "source_outcome_ref": source_outcome_ref,
        "source_closed_trade_ref": source_closed_trade_ref,
        "source_refs": source_refs,
        "claims": claims,
        "claim_count": len(claims),
        "all_claims_cited": all(bool(claim.get("source_refs")) for claim in claims),
        "confidence": confidence,
        "confidence_label": confidence_label,
        "uncertainty": uncertainty,
        "uncertainty_count": len(uncertainty),
        "missing_evidence": missing_evidence,
        "missing_evidence_count": len(missing_evidence),
        "approval_state": "not_requested",
        "review_required": True,
        "write_authority": False,
        **_disabled_write_fields(),
    }


def _build_packets(draft: dict[str, Any]) -> list[dict[str, Any]]:
    record = _outcome_record(draft)
    thesis = _dict(record.get("thesis"))
    market_context = _dict(record.get("market_context"))
    sizing = _dict(record.get("sizing"))
    execution_path = _dict(record.get("execution_path"))
    source_context = _dict(record.get("source_context"))
    truth_partition = _dict(record.get("truth_partition"))
    broker_truth = _dict(truth_partition.get("broker_truth"))
    risk_decision = _dict(record.get("risk_decision"))
    realized_outcome = _dict(record.get("realized_outcome"))
    source_outcome_ref = draft.get("source_outcome_ref")
    source_closed_trade_ref = draft.get("source_closed_trade_ref")
    catalyst_refs = _section_source_refs(draft, "catalyst_read")
    pricing_refs = _section_source_refs(draft, "pricing_read")
    regime_refs = _section_source_refs(draft, "regime_read")
    execution_refs = _section_source_refs(draft, "execution_read")
    override_refs = _section_source_refs(draft, "override_readiness_read")
    outcome_refs = [str(ref) for ref in (draft.get("source_outcome_artifact_ref"),) if ref]

    return [
        _analysis_packet(
            "catalyst_analysis",
            source_outcome_ref=source_outcome_ref,
            source_closed_trade_ref=source_closed_trade_ref,
            source_refs=list(dict.fromkeys(catalyst_refs + outcome_refs)),
            claims=[
                _claim(
                    "catalyst_analysis",
                    1,
                    "evidence",
                    (
                        "Expected catalyst classes are "
                        f"{','.join(map(str, _list(thesis.get('expected_catalyst_classes'))))}."
                    ),
                    catalyst_refs,
                    0.55,
                ),
                _claim(
                    "catalyst_analysis",
                    2,
                    "deferred",
                    "Actual catalyst remains unknown and must not be inferred in Q6-6.",
                    catalyst_refs,
                    0.2,
                ),
            ],
            confidence=0.42,
            confidence_label="low_until_specific_catalyst_review",
            uncertainty=[
                _uncertainty(
                    "actual_catalyst",
                    "Q6-3 and Q6-5 mark the actual catalyst as unknown/deferred.",
                    catalyst_refs,
                )
            ],
            missing_evidence=[
                _missing_evidence(
                    "specific_event_ref",
                    "No specific catalyst event ref is present in the seed draft.",
                    catalyst_refs,
                ),
                _missing_evidence(
                    "postmortem_root_cause",
                    "Root cause remains unknown pending later review.",
                    catalyst_refs,
                ),
            ],
        ),
        _analysis_packet(
            "pricing_analysis",
            source_outcome_ref=source_outcome_ref,
            source_closed_trade_ref=source_closed_trade_ref,
            source_refs=list(dict.fromkeys(pricing_refs + outcome_refs)),
            claims=[
                _claim(
                    "pricing_analysis",
                    1,
                    "evidence",
                    (
                        "Market confirmation was "
                        f"{market_context.get('market_confirmation_status')} with pricing gap "
                        f"{market_context.get('market_confirmation_pricing_gap')}."
                    ),
                    pricing_refs,
                    0.62,
                ),
                _claim(
                    "pricing_analysis",
                    2,
                    "evidence",
                    (
                        "Closed trade outcome was "
                        f"{realized_outcome.get('outcome_bucket')} with realized PnL "
                        f"{sizing.get('realized_pnl_gbp')} GBP."
                    ),
                    pricing_refs,
                    0.6,
                ),
            ],
            confidence=0.54,
            confidence_label="medium_for_local_price_context_low_for_fill_truth",
            uncertainty=[
                _uncertainty(
                    "pricing_read",
                    "Full pricing read remains deferred to analysis and review.",
                    pricing_refs,
                )
            ],
            missing_evidence=[
                _missing_evidence(
                    "broker_fill_price",
                    "Broker fill price is absent because broker truth is not available.",
                    pricing_refs,
                ),
                _missing_evidence(
                    "broker_fill_timestamp",
                    "Broker fill timestamp is absent because no broker POST occurred.",
                    pricing_refs,
                ),
            ],
        ),
        _analysis_packet(
            "regime_analysis",
            source_outcome_ref=source_outcome_ref,
            source_closed_trade_ref=source_closed_trade_ref,
            source_refs=list(dict.fromkeys(regime_refs + outcome_refs)),
            claims=[
                _claim(
                    "regime_analysis",
                    1,
                    "deferred",
                    "Q6-5 makes no macro regime conclusion for this seed.",
                    regime_refs,
                    0.25,
                ),
                _claim(
                    "regime_analysis",
                    2,
                    "evidence",
                    (
                        "Source intake had "
                        f"{source_context.get('required_source_present_count')}/"
                        f"{source_context.get('required_source_count')} required sources present."
                    ),
                    regime_refs,
                    0.5,
                ),
            ],
            confidence=0.3,
            confidence_label="low_regime_context_deferred",
            uncertainty=[
                _uncertainty(
                    "regime_read",
                    "The closed-trade outcome explicitly deferred regime interpretation.",
                    regime_refs,
                )
            ],
            missing_evidence=[
                _missing_evidence(
                    "macro_regime_classification",
                    "No reviewed macro regime classification is present.",
                    regime_refs,
                ),
                _missing_evidence(
                    "source_quality_assessment",
                    "Full source-quality assessment is deferred.",
                    regime_refs,
                ),
            ],
        ),
        _analysis_packet(
            "execution_analysis",
            source_outcome_ref=source_outcome_ref,
            source_closed_trade_ref=source_closed_trade_ref,
            source_refs=list(dict.fromkeys(execution_refs + outcome_refs)),
            claims=[
                _claim(
                    "execution_analysis",
                    1,
                    "evidence",
                    (
                        f"Execution path used {execution_path.get('selected_venue')} with "
                        f"receipt state {execution_path.get('receipt_state')}."
                    ),
                    execution_refs,
                    0.72,
                ),
                _claim(
                    "execution_analysis",
                    2,
                    "evidence",
                    str(truth_partition.get("distinction")),
                    execution_refs,
                    0.78,
                    conclusion=True,
                ),
            ],
            confidence=0.66,
            confidence_label="medium_high_for_local_lifecycle_low_for_broker_truth",
            uncertainty=[
                _uncertainty(
                    "execution_quality_assessment",
                    "Q6-3 deferred execution-quality assessment.",
                    execution_refs,
                )
            ],
            missing_evidence=[
                _missing_evidence(
                    "broker_fill_id",
                    "Broker fill id is missing; local lifecycle is not broker truth.",
                    execution_refs,
                ),
                _missing_evidence(
                    "broker_truth_receipt",
                    f"Broker truth source is {broker_truth.get('source')}.",
                    execution_refs,
                ),
            ],
        ),
        _analysis_packet(
            "override_analysis",
            source_outcome_ref=source_outcome_ref,
            source_closed_trade_ref=source_closed_trade_ref,
            source_refs=list(dict.fromkeys(override_refs + outcome_refs)),
            claims=[
                _claim(
                    "override_analysis",
                    1,
                    "evidence",
                    (
                        f"Risk decision was {risk_decision.get('risk_decision')} and "
                        "Phase 7 proof credit remains false."
                    ),
                    override_refs,
                    0.7,
                ),
                _claim(
                    "override_analysis",
                    2,
                    "evidence",
                    "Q6-6 has no authority to approve learning writes or policy changes.",
                    override_refs,
                    0.85,
                    conclusion=True,
                ),
            ],
            confidence=0.74,
            confidence_label="high_for_authority_boundary",
            uncertainty=[
                _uncertainty(
                    "learning_actions",
                    "Learning actions remain deferred until review and approval gates.",
                    override_refs,
                )
            ],
            missing_evidence=[
                _missing_evidence(
                    "human_review_ref",
                    "No Q6-7 reducer or review record exists yet.",
                    override_refs,
                )
            ],
        ),
    ]


def build_phase6_postmortem_analysis(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    draft = _read_json(SOURCE_POSTMORTEM_DRAFT_REF, settings) or {}
    draft_errors = validate_phase6_postmortem_draft(draft) if draft else []
    blockers: list[str] = []
    if not draft:
        blockers.append("postmortem_draft_missing")
    elif draft.get("status") != "draft":
        blockers.append("postmortem_draft_not_draft")
    if draft_errors:
        blockers.append("postmortem_draft_validation_errors")

    packets = _build_packets(draft) if not blockers else []
    claim_count = sum(int(packet.get("claim_count", 0) or 0) for packet in packets)
    uncertainty_count = sum(
        int(packet.get("uncertainty_count", 0) or 0) for packet in packets
    )
    missing_evidence_count = sum(
        int(packet.get("missing_evidence_count", 0) or 0) for packet in packets
    )
    all_claims_cited = bool(packets) and all(
        packet.get("all_claims_cited") is True for packet in packets
    )
    status = "draft" if not blockers else "blocked"
    authority = phase6_authority_ledger()
    authority["stage"] = "Q6-6"
    authority["boundary"] = PHASE6_POSTMORTEM_ANALYSIS_BOUNDARY
    artifact = {
        "schema_version": PHASE6_ARTIFACT_SCHEMA_VERSION,
        "phase6_postmortem_analysis_schema_version": (
            PHASE6_POSTMORTEM_ANALYSIS_SCHEMA_VERSION
        ),
        "artifact_type": "postmortem_analysis_packet",
        "artifact_id": "phase6:q6-6:postmortem-analysis:crude_oil_energy_security_disruption",
        "phase": "Q6",
        "stage": "Q6-6",
        "status": status,
        "generated_at": generated_at,
        "public_safe": True,
        "recorded": False,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_event_count": 0,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "runtime_artifact_path": None,
        "history_log_path": None,
        "event_contract": phase6_event_contract("postmortem_draft"),
        "authority_ledger": authority,
        "source_posture": phase6_source_posture(),
        "provenance": _provenance(draft),
        "boundary": PHASE6_POSTMORTEM_ANALYSIS_BOUNDARY,
        **phase6_authority_defaults(),
        **phase6_unsafe_counter_defaults(),
        **_disabled_write_fields(),
        "analysis_packet_type": "analysis_packet_bundle",
        "analysis_packet_types": list(ANALYSIS_PACKET_TYPES),
        "analysis_packet_count": len(packets),
        "analysis_state": "deterministic_analysis_packets_created" if packets else "blocked",
        "packets": packets,
        "claim_count": claim_count,
        "all_claims_cited": all_claims_cited,
        "confidence_packet_count": len(
            [packet for packet in packets if packet.get("confidence") is not None]
        ),
        "uncertainty_count": uncertainty_count,
        "missing_evidence_count": missing_evidence_count,
        "approval_state": "not_requested",
        "postmortem_approved": False,
        "postmortem_draft_ref": SOURCE_POSTMORTEM_DRAFT_REF,
        "source_postmortem_draft_ref": SOURCE_POSTMORTEM_DRAFT_REF,
        "source_draft_status": draft.get("status"),
        "source_outcome_ref": draft.get("source_outcome_ref"),
        "source_closed_trade_ref": draft.get("source_closed_trade_ref"),
        "llm_required": False,
        "llm_used": False,
        "deterministic_analysis": True,
        "learning_write_allowed": False,
        "phase5_test_trades_count_for_phase7": False,
        "phase7_proof_credit_allowed": False,
        "unsafe_write_counter_total": 0,
        "blockers": sorted(set(blockers)),
        "blocker_count": len(set(blockers)),
        "recommended_next_stage": "Q6-7 Reducer And Review Gate",
    }
    artifact["validation_errors"] = validate_phase6_postmortem_analysis(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "error"
    return artifact


def _write_disabled_errors(prefix: str, payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in WRITE_DISABLED_FIELDS:
        if payload.get(field) is not False:
            errors.append(f"{prefix}_write_enabled:{field}")
    return errors


def _source_ref_errors(prefix: str, refs: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(refs, list) or not refs:
        return [f"{prefix}_source_refs_missing"]
    for ref in refs:
        if not isinstance(ref, str) or not ref.strip():
            errors.append(f"{prefix}_source_ref_invalid")
            continue
        if _has_local_path(ref):
            errors.append(f"{prefix}_local_source_ref")
        if any(secret_word in ref.lower() for secret_word in ("api_key", "secret", "token")):
            errors.append(f"{prefix}_secret_source_ref")
    return errors


def validate_phase6_postmortem_analysis(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "phase6_postmortem_analysis_schema_version",
        "artifact_type",
        "artifact_id",
        "phase",
        "stage",
        "status",
        "generated_at",
        "public_safe",
        "event_log_required",
        "event_log_written",
        "event_contract",
        "authority_ledger",
        "source_posture",
        "provenance",
        "boundary",
        "analysis_packet_type",
        "analysis_packet_types",
        "analysis_packet_count",
        "analysis_state",
        "packets",
        "claim_count",
        "all_claims_cited",
        "confidence_packet_count",
        "uncertainty_count",
        "missing_evidence_count",
        "approval_state",
        "learning_write_allowed",
        "postmortem_approved",
        "source_postmortem_draft_ref",
        "source_outcome_ref",
        "source_closed_trade_ref",
        "llm_used",
        "deterministic_analysis",
        "phase5_test_trades_count_for_phase7",
        "phase7_proof_credit_allowed",
        "unsafe_write_counter_total",
        "blockers",
        "blocker_count",
    }
    missing = sorted(required_fields - set(artifact))
    if missing:
        errors.append("postmortem_analysis_missing_fields:" + ",".join(missing))
    if artifact.get("phase6_postmortem_analysis_schema_version") != (
        PHASE6_POSTMORTEM_ANALYSIS_SCHEMA_VERSION
    ):
        errors.append("postmortem_analysis_schema_version_mismatch")
    errors.extend(validate_phase6_artifact(artifact, expected_stage="Q6-6"))
    if artifact.get("artifact_type") != "postmortem_analysis_packet":
        errors.append("postmortem_analysis_artifact_type_mismatch")
    if artifact.get("status") not in {"draft", "blocked", "error"}:
        errors.append("postmortem_analysis_status_invalid")
    if artifact.get("analysis_packet_type") != "analysis_packet_bundle":
        errors.append("analysis_packet_type_invalid")
    if artifact.get("analysis_state") != "deterministic_analysis_packets_created":
        errors.append("analysis_state_invalid")
    if artifact.get("approval_state") != "not_requested":
        errors.append("approval_state_invalid")
    if artifact.get("postmortem_approved") is not False:
        errors.append("postmortem_approved")
    if artifact.get("learning_write_allowed") is not False:
        errors.append("learning_write_allowed")
    errors.extend(_write_disabled_errors("postmortem_analysis", artifact))
    for field in PHASE6_UNSAFE_COUNT_FIELDS:
        if int(artifact.get(field, 0) or 0) != 0:
            errors.append(f"postmortem_analysis_unsafe_count_nonzero:{field}")
    unsafe_total = sum(int(artifact.get(field, 0) or 0) for field in PHASE6_UNSAFE_COUNT_FIELDS)
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("postmortem_analysis_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("postmortem_analysis_unsafe_total_nonzero")
    if artifact.get("llm_used") is not False:
        errors.append("llm_used")
    if artifact.get("deterministic_analysis") is not True:
        errors.append("deterministic_analysis_not_true")
    if artifact.get("phase7_proof_credit_allowed") is not False:
        errors.append("phase7_proof_credit_allowed")
    if artifact.get("phase5_test_trades_count_for_phase7") is not False:
        errors.append("phase5_test_trades_count_for_phase7")
    if artifact.get("source_postmortem_draft_ref") != SOURCE_POSTMORTEM_DRAFT_REF:
        errors.append("source_postmortem_draft_ref_invalid")
    if not artifact.get("source_outcome_ref"):
        errors.append("source_outcome_ref_missing")
    if not artifact.get("source_closed_trade_ref"):
        errors.append("source_closed_trade_ref_missing")

    packet_types = artifact.get("analysis_packet_types", [])
    if not isinstance(packet_types, list) or set(packet_types) != set(ANALYSIS_PACKET_TYPES):
        errors.append("analysis_packet_types_invalid")
    packets = artifact.get("packets", [])
    if not isinstance(packets, list):
        errors.append("analysis_packets_invalid")
        packets = []
    if artifact.get("analysis_packet_count") != len(packets):
        errors.append("analysis_packet_count_mismatch")
    if artifact.get("analysis_packet_count") != len(ANALYSIS_PACKET_TYPES):
        errors.append("analysis_packet_count_invalid")
    seen_packet_types: set[str] = set()
    claim_count = 0
    confidence_packet_count = 0
    uncertainty_count = 0
    missing_evidence_count = 0
    all_claims_cited = True
    for packet in packets:
        if not isinstance(packet, dict):
            errors.append("analysis_packet_invalid")
            all_claims_cited = False
            continue
        packet_type = str(packet.get("analysis_packet_type") or "")
        seen_packet_types.add(packet_type)
        if packet_type not in ANALYSIS_PACKET_TYPES:
            errors.append(f"analysis_packet_type_unknown:{packet_type}")
        if packet.get("analysis_state") != "deterministic_analysis_packet_created":
            errors.append(f"analysis_packet_state_invalid:{packet_type}")
        if packet.get("approval_state") != "not_requested":
            errors.append(f"analysis_packet_approval_state_invalid:{packet_type}")
        if packet.get("write_authority") is not False:
            errors.append(f"analysis_packet_write_authority:{packet_type}")
        errors.extend(_write_disabled_errors(f"analysis_packet:{packet_type}", packet))
        errors.extend(_source_ref_errors(f"analysis_packet:{packet_type}", packet.get("source_refs")))
        confidence = packet.get("confidence")
        if not isinstance(confidence, int | float) or not 0 <= float(confidence) <= 1:
            errors.append(f"analysis_packet_confidence_invalid:{packet_type}")
        else:
            confidence_packet_count += 1
        claims = packet.get("claims", [])
        if not isinstance(claims, list) or not claims:
            errors.append(f"analysis_packet_claims_missing:{packet_type}")
            claims = []
            all_claims_cited = False
        if packet.get("claim_count") != len(claims):
            errors.append(f"analysis_packet_claim_count_mismatch:{packet_type}")
        if packet.get("all_claims_cited") is not True:
            errors.append(f"analysis_packet_claims_uncited:{packet_type}")
            all_claims_cited = False
        for claim in claims:
            if not isinstance(claim, dict):
                errors.append(f"analysis_claim_invalid:{packet_type}")
                all_claims_cited = False
                continue
            if not claim.get("claim_id") or not claim.get("statement"):
                errors.append(f"analysis_claim_required_field_missing:{packet_type}")
            claim_refs = claim.get("source_refs")
            ref_errors = _source_ref_errors(f"analysis_claim:{packet_type}", claim_refs)
            errors.extend(ref_errors)
            if ref_errors:
                all_claims_cited = False
            claim_confidence = claim.get("confidence")
            if (
                not isinstance(claim_confidence, int | float)
                or not 0 <= float(claim_confidence) <= 1
            ):
                errors.append(f"analysis_claim_confidence_invalid:{packet_type}")
        claim_count += len(claims)
        uncertainty = packet.get("uncertainty", [])
        if not isinstance(uncertainty, list) or not uncertainty:
            errors.append(f"analysis_packet_uncertainty_missing:{packet_type}")
            uncertainty = []
        if packet.get("uncertainty_count") != len(uncertainty):
            errors.append(f"analysis_packet_uncertainty_count_mismatch:{packet_type}")
        for marker in uncertainty:
            if not isinstance(marker, dict) or not marker.get("field") or not marker.get("reason"):
                errors.append(f"analysis_uncertainty_invalid:{packet_type}")
                continue
            errors.extend(
                _source_ref_errors(
                    f"analysis_uncertainty:{packet_type}",
                    marker.get("source_refs"),
                )
            )
        uncertainty_count += len(uncertainty)
        missing_evidence = packet.get("missing_evidence", [])
        if not isinstance(missing_evidence, list) or not missing_evidence:
            errors.append(f"analysis_packet_missing_evidence_missing:{packet_type}")
            missing_evidence = []
        if packet.get("missing_evidence_count") != len(missing_evidence):
            errors.append(f"analysis_packet_missing_evidence_count_mismatch:{packet_type}")
        for marker in missing_evidence:
            if not isinstance(marker, dict) or not marker.get("field") or not marker.get("reason"):
                errors.append(f"analysis_missing_evidence_invalid:{packet_type}")
                continue
            errors.extend(
                _source_ref_errors(
                    f"analysis_missing_evidence:{packet_type}",
                    marker.get("source_refs"),
                )
            )
        missing_evidence_count += len(missing_evidence)
    if seen_packet_types != set(ANALYSIS_PACKET_TYPES):
        errors.append("analysis_packet_type_set_mismatch")
    if artifact.get("claim_count") != claim_count:
        errors.append("claim_count_mismatch")
    if artifact.get("all_claims_cited") is not all_claims_cited:
        errors.append("all_claims_cited_mismatch")
    if artifact.get("all_claims_cited") is not True:
        errors.append("all_claims_cited_false")
    if artifact.get("confidence_packet_count") != confidence_packet_count:
        errors.append("confidence_packet_count_mismatch")
    if artifact.get("confidence_packet_count") != len(ANALYSIS_PACKET_TYPES):
        errors.append("confidence_packet_count_invalid")
    if artifact.get("uncertainty_count") != uncertainty_count:
        errors.append("uncertainty_count_mismatch")
    if artifact.get("missing_evidence_count") != missing_evidence_count:
        errors.append("missing_evidence_count_mismatch")
    if uncertainty_count < len(ANALYSIS_PACKET_TYPES):
        errors.append("uncertainty_count_too_low")
    if missing_evidence_count < len(ANALYSIS_PACKET_TYPES):
        errors.append("missing_evidence_count_too_low")
    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("blockers_invalid")
        blockers = []
    if artifact.get("blocker_count") != len(blockers):
        errors.append("blocker_count_mismatch")
    if artifact.get("status") == "draft" and blockers:
        errors.append("draft_with_blockers")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "deterministic local analysis packets only",
        "cannot approve a postmortem",
        "cannot approve learning actions",
        "cannot write learning data",
        "cannot write a Knowledge Graph",
        "cannot mutate policy",
        "cannot mutate strategies",
        "cannot count Phase 5 test trades toward Phase 7 proof",
    ):
        if phrase not in boundary:
            errors.append("postmortem_analysis_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("postmortem_analysis_event_log_path_missing")
        if not str(artifact.get("event_log_correlation_id") or "").strip():
            errors.append("postmortem_analysis_event_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("postmortem_analysis_event_log_count_mismatch")
    return sorted(set(errors))


def attach_phase6_postmortem_analysis_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(
        event_log_path or (_runtime_dir(settings) / PHASE6_POSTMORTEM_ANALYSIS_EVENT_LOG)
    )
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE6_POSTMORTEM_ANALYSIS_EVENT_TYPE,
        PHASE6_POSTMORTEM_ANALYSIS_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "analysis_state": output.get("analysis_state"),
            "analysis_packet_count": output.get("analysis_packet_count"),
            "analysis_packet_types": output.get("analysis_packet_types"),
            "claim_count": output.get("claim_count"),
            "all_claims_cited": output.get("all_claims_cited"),
            "confidence_packet_count": output.get("confidence_packet_count"),
            "uncertainty_count": output.get("uncertainty_count"),
            "missing_evidence_count": output.get("missing_evidence_count"),
            "approval_state": output.get("approval_state"),
            "postmortem_approved": output.get("postmortem_approved"),
            "learning_write_created": output.get("learning_write_created"),
            "knowledge_graph_write_created": output.get("knowledge_graph_write_created"),
            "policy_mutation_created": output.get("policy_mutation_created"),
            "strategy_mutation_created": output.get("strategy_mutation_created"),
            "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
            "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
            "boundary": output.get("boundary"),
        },
    )
    output["recorded"] = True
    output["event_log_written"] = True
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = 1
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_created_at"] = entry.created_at
    output["validation_errors"] = validate_phase6_postmortem_analysis(output)
    if output["validation_errors"]:
        output["status"] = "error"
    return output, entry


def write_phase6_postmortem_analysis(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase6_postmortem_analysis_paths(
        settings
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase6_postmortem_analysis_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase6_postmortem_analysis(output)
        if output["validation_errors"]:
            output["status"] = "error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase6_postmortem_analysis(output)
    if output["validation_errors"]:
        output["status"] = "error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE6_POSTMORTEM_ANALYSIS_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "analysis_state": output.get("analysis_state"),
        "analysis_packet_count": output.get("analysis_packet_count"),
        "claim_count": output.get("claim_count"),
        "all_claims_cited": output.get("all_claims_cited"),
        "confidence_packet_count": output.get("confidence_packet_count"),
        "uncertainty_count": output.get("uncertainty_count"),
        "missing_evidence_count": output.get("missing_evidence_count"),
        "postmortem_approved": output.get("postmortem_approved"),
        "learning_write_created": output.get("learning_write_created"),
        "knowledge_graph_write_created": output.get("knowledge_graph_write_created"),
        "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
        "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
        "blocker_count": output.get("blocker_count"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
