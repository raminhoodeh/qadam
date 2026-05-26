"""Q6-5 deterministic Postmortem Agent draft.

This stage creates the first backend-derived postmortem draft from the Q5E
closed-trade seed. It uses the Q6-4 packet contract and Q6-3 closed-trade
outcome, does not call an LLM, and keeps approval, learning writes, Knowledge
Graph writes, score updates, policy mutation, and strategy mutation disabled.
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
from orchestrator.phase6_closed_trade_outcome import (
    PHASE6_CLOSED_TRADE_OUTCOME_RUNTIME_ARTIFACT,
    validate_phase6_closed_trade_outcome,
)
from orchestrator.phase6_postmortem_packets import (
    PHASE6_POSTMORTEM_PACKET_CONTRACT_RUNTIME_ARTIFACT,
    POSTMORTEM_PACKET_SECTIONS,
    validate_phase6_postmortem_packet_contract,
    validate_postmortem_packet_payload,
)


PHASE6_POSTMORTEM_DRAFT_SCHEMA_VERSION = 1
PHASE6_POSTMORTEM_DRAFT_RUNTIME_ARTIFACT = "phase6_postmortem_draft.json"
PHASE6_POSTMORTEM_DRAFT_HISTORY = "phase6_postmortem_draft_history.jsonl"
PHASE6_POSTMORTEM_DRAFT_EVENT_LOG = "phase6_postmortem_draft_events.jsonl"
PHASE6_POSTMORTEM_DRAFT_EVENT_TYPE = "phase6_postmortem_draft_created"
PHASE6_POSTMORTEM_DRAFT_COMPONENT = "phase6_postmortem_agent"

SOURCE_PACKET_CONTRACT_REF = f"data/runtime/{PHASE6_POSTMORTEM_PACKET_CONTRACT_RUNTIME_ARTIFACT}"
SOURCE_OUTCOME_REF = f"data/runtime/{PHASE6_CLOSED_TRADE_OUTCOME_RUNTIME_ARTIFACT}"

PHASE6_POSTMORTEM_DRAFT_BOUNDARY = (
    "Q6-5 creates a deterministic source-cited postmortem draft only. It can "
    "fill the Q6-4 packet sections from Q6-3 outcome evidence, mark unknowns "
    "and deferred reads, and emit an Event Log draft record, but it cannot "
    "approve a postmortem, cannot write learning data, cannot write a "
    "Knowledge Graph, cannot update model weights, cannot update trust scores, "
    "cannot mutate policy, cannot mutate strategies, cannot call broker POST "
    "routes, cannot call Alpaca POST routes, cannot call live endpoints, "
    "cannot enable live capital, and cannot count Phase 5 test trades toward "
    "Phase 7 proof."
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


def phase6_postmortem_draft_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE6_POSTMORTEM_DRAFT_RUNTIME_ARTIFACT,
        runtime / PHASE6_POSTMORTEM_DRAFT_HISTORY,
        runtime / PHASE6_POSTMORTEM_DRAFT_EVENT_LOG,
    )


def _disabled_write_fields() -> dict[str, bool]:
    return {field: False for field in WRITE_DISABLED_FIELDS}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _source_refs(contract: dict[str, Any], outcome: dict[str, Any]) -> list[str]:
    refs = [SOURCE_PACKET_CONTRACT_REF, SOURCE_OUTCOME_REF]
    for payload in (contract.get("provenance", {}), outcome.get("provenance", {})):
        if not isinstance(payload, dict):
            continue
        for ref in payload.get("source_refs", []):
            if isinstance(ref, str) and ref not in refs:
                refs.append(ref)
    return refs


def _provenance(contract: dict[str, Any], outcome: dict[str, Any]) -> dict[str, Any]:
    provenance = phase6_provenance(tuple(_source_refs(contract, outcome)))
    for bucket in (
        "execution_evidence_refs",
        "market_context_refs",
        "model_interpretation_refs",
        "governance_refs",
    ):
        values: list[str] = []
        for payload in (contract.get("provenance", {}), outcome.get("provenance", {})):
            if not isinstance(payload, dict):
                continue
            for ref in payload.get(bucket, []):
                if isinstance(ref, str) and ref not in values:
                    values.append(ref)
        provenance[bucket] = values
    return provenance


def _assertion(
    section_key: str,
    ordinal: int,
    assertion_kind: str,
    statement: str,
    source_refs: list[str],
    *,
    conclusion: bool = False,
    is_hypothesis: bool = False,
    hypothesis_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "assertion_id": f"q6-5:{section_key}:{ordinal}",
        "assertion_kind": assertion_kind,
        "statement": statement,
        "source_refs": source_refs,
        "is_hypothesis": is_hypothesis,
        "hypothesis_reason": hypothesis_reason,
        "conclusion": conclusion,
        "review_required": True,
    }


def _section(section_key: str, assertions: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "section_key": section_key,
        "required": True,
        "assertions": assertions,
        "assertion_count": len(assertions),
        "source_refs_or_hypothesis_required": True,
        "uncited_conclusion_allowed": False,
    }


def _outcome_record(outcome: dict[str, Any]) -> dict[str, Any]:
    records = outcome.get("outcome_records", [])
    if isinstance(records, list) and records and isinstance(records[0], dict):
        return records[0]
    return {}


def _marker(
    marker_type: str,
    field: Any,
    reason: str,
    source_refs: list[str],
) -> dict[str, Any]:
    return {
        "marker_type": marker_type,
        "field": str(field),
        "reason": reason,
        "source_refs": source_refs,
        "review_required": True,
    }


def _marker_fields(markers: Any) -> set[str]:
    if not isinstance(markers, list):
        return set()
    return {
        str(marker.get("field"))
        for marker in markers
        if isinstance(marker, dict) and marker.get("field")
    }


def _build_packet(contract: dict[str, Any], outcome: dict[str, Any]) -> dict[str, Any]:
    record = _outcome_record(outcome)
    outcome_ref = str(contract.get("source_outcome_ref") or record.get("outcome_ref") or "")
    closed_trade_ref = str(
        contract.get("source_closed_trade_ref") or record.get("source_closed_trade_ref") or ""
    )
    outcome_artifact_ref = str(contract.get("source_outcome_artifact_ref") or SOURCE_OUTCOME_REF)
    source_refs = [outcome_artifact_ref]
    provenance_refs = _source_refs(contract, outcome)
    thesis = _dict(record.get("thesis"))
    entry_state = _dict(record.get("entry_state"))
    exit_state = _dict(record.get("exit_state"))
    sizing = _dict(record.get("sizing"))
    risk_decision = _dict(record.get("risk_decision"))
    execution_path = _dict(record.get("execution_path"))
    receipt_refs = _dict(record.get("receipt_and_prewrite_refs"))
    market_context = _dict(record.get("market_context"))
    source_context = _dict(record.get("source_context"))
    invalidation = _dict(record.get("invalidation"))
    realized_outcome = _dict(record.get("realized_outcome"))
    truth_partition = _dict(record.get("truth_partition"))
    unknown_fields = _list(record.get("unknown_fields"))
    deferred_fields = _list(record.get("deferred_fields"))
    missing_ref_fields = [
        field for field in unknown_fields if str(field).startswith("broker_fill")
    ]
    unknown_markers = [
        _marker(
            "unknown_field",
            field,
            "Q6-3 marked this field unknown; Q6-5 does not infer missing evidence.",
            source_refs,
        )
        for field in unknown_fields
    ]
    deferred_markers = [
        _marker(
            "deferred_field",
            field,
            "Q6-3 deferred this read to a later postmortem analysis packet.",
            source_refs,
        )
        for field in deferred_fields
    ]
    missing_ref_markers = [
        _marker(
            "missing_reference",
            field,
            "No broker-fill reference is available because Q6-3 keeps local lifecycle state separate from broker truth.",
            source_refs,
        )
        for field in missing_ref_fields
    ]

    sections = [
        _section(
            "thesis",
            [
                _assertion(
                    "thesis",
                    1,
                    "evidence",
                    (
                        "Strategy family "
                        f"{record.get('strategy_family_key')} targeted "
                        f"{thesis.get('primary_instrument')} with catalyst classes "
                        f"{','.join(map(str, _list(thesis.get('expected_catalyst_classes'))))}."
                    ),
                    source_refs,
                ),
                _assertion(
                    "thesis",
                    2,
                    "unknown",
                    "Specific expected and actual catalysts remain unknown for Q6-5.",
                    source_refs,
                ),
            ],
        ),
        _section(
            "timeline",
            [
                _assertion(
                    "timeline",
                    1,
                    "evidence",
                    (
                        f"Submitted at {entry_state.get('submitted_at')}, opened at "
                        f"{entry_state.get('opened_at')}, and closed at "
                        f"{exit_state.get('closed_at')}."
                    ),
                    source_refs,
                )
            ],
        ),
        _section(
            "catalyst_read",
            [
                _assertion(
                    "catalyst_read",
                    1,
                    "deferred",
                    (
                        "Q6-3 marks actual catalyst analysis as deferred; Q6-5 "
                        "does not infer it."
                    ),
                    source_refs,
                )
            ],
        ),
        _section(
            "pricing_read",
            [
                _assertion(
                    "pricing_read",
                    1,
                    "evidence",
                    (
                        "Market confirmation status was "
                        f"{market_context.get('market_confirmation_status')} with pricing gap "
                        f"{market_context.get('market_confirmation_pricing_gap')}."
                    ),
                    source_refs,
                ),
                _assertion(
                    "pricing_read",
                    2,
                    "evidence",
                    (
                        "Closed trade recorded realized PnL "
                        f"{sizing.get('realized_pnl_gbp')} GBP, R multiple "
                        f"{realized_outcome.get('r_multiple')}, and outcome bucket "
                        f"{realized_outcome.get('outcome_bucket')}."
                    ),
                    source_refs,
                ),
                _assertion(
                    "pricing_read",
                    3,
                    "deferred",
                    "Full pricing read remains deferred for Q6-6 analysis packets.",
                    source_refs,
                ),
            ],
        ),
        _section(
            "regime_read",
            [
                _assertion(
                    "regime_read",
                    1,
                    "deferred",
                    "Regime interpretation is deferred; no macro regime conclusion is made in Q6-5.",
                    source_refs,
                )
            ],
        ),
        _section(
            "execution_read",
            [
                _assertion(
                    "execution_read",
                    1,
                    "evidence",
                    (
                        f"Execution path used venue {execution_path.get('selected_venue')} "
                        f"with receipt state {execution_path.get('receipt_state')} and "
                        f"permission scope {execution_path.get('permission_scope')}."
                    ),
                    source_refs,
                    conclusion=True,
                ),
                _assertion(
                    "execution_read",
                    2,
                    "evidence",
                    str(truth_partition.get("distinction")),
                    source_refs,
                ),
                _assertion(
                    "execution_read",
                    3,
                    "evidence",
                    (
                        "Prewrite and lifecycle evidence is backed by paper-order, "
                        "submit-receipt, closed-trade, and postmortem-due Event Logs."
                    ),
                    source_refs
                    + [
                        str(ref)
                        for ref in (
                            receipt_refs.get("paper_order_event_log_ref"),
                            receipt_refs.get("paper_submit_receipt_event_log_ref"),
                            receipt_refs.get("closed_trade_event_log_ref"),
                            receipt_refs.get("postmortem_due_event_log_ref"),
                        )
                        if ref
                    ],
                ),
            ],
        ),
        _section(
            "override_readiness_read",
            [
                _assertion(
                    "override_readiness_read",
                    1,
                    "evidence",
                    (
                        "Broker truth was not accepted as fill truth, write "
                        "authority remained disabled, and the risk decision was "
                        f"{risk_decision.get('risk_decision')}."
                    ),
                    source_refs,
                )
            ],
        ),
        _section(
            "source_quality",
            [
                _assertion(
                    "source_quality",
                    1,
                    "evidence",
                    (
                        "Q6-2 source intake reports "
                        f"{source_context.get('required_source_present_count')}/"
                        f"{source_context.get('required_source_count')} required sources present."
                    ),
                    source_refs,
                ),
                _assertion(
                    "source_quality",
                    2,
                    "deferred",
                    "Full source quality assessment remains deferred for Q6-6.",
                    source_refs,
                ),
            ],
        ),
        _section(
            "mistakes",
            [
                _assertion(
                    "mistakes",
                    1,
                    "unknown",
                    "No mistake is asserted in Q6-5; root cause remains unknown pending review.",
                    source_refs,
                )
            ],
        ),
        _section(
            "useful_signals",
            [
                _assertion(
                    "useful_signals",
                    1,
                    "evidence",
                    (
                        "Signal Integrity passed to risk shadow with integrity score "
                        f"{market_context.get('integrity_score')} and "
                        f"{market_context.get('source_count')} sources."
                    ),
                    source_refs,
                )
            ],
        ),
        _section(
            "harmful_signals",
            [
                _assertion(
                    "harmful_signals",
                    1,
                    "unknown",
                    "No harmful signal is asserted in Q6-5; this remains review-required.",
                    source_refs,
                )
            ],
        ),
        _section(
            "uncertainty",
            [
                _assertion(
                    "uncertainty",
                    1,
                    "unknown",
                    (
                        "Unknown fields: "
                        f"{','.join(map(str, unknown_fields))}; deferred fields: "
                        f"{','.join(map(str, deferred_fields))}."
                    ),
                    source_refs,
                ),
                _assertion(
                    "uncertainty",
                    2,
                    "hypothesis",
                    (
                        "The flat outcome may reflect the guarded lifecycle marker rather "
                        "than a market-driven result."
                    ),
                    [],
                    is_hypothesis=True,
                    hypothesis_reason=(
                        "Q6-3 explicitly separates local lifecycle state from broker fill truth."
                    ),
                ),
            ],
        ),
        _section(
            "proposed_learning_actions",
            [
                _assertion(
                    "proposed_learning_actions",
                    1,
                    "proposed_learning_action",
                    (
                        "Prepare Q6-6 catalyst, pricing, regime, execution, and source-quality "
                        "analysis packets before any learning action is approved. "
                        "The deferred invalidation read must include staged and risk "
                        f"invalidation evidence: {invalidation.get('deferred_postmortem_invalidation_read')}."
                    ),
                    source_refs,
                )
            ],
        ),
    ]
    assertion_count = sum(len(section["assertions"]) for section in sections)
    return {
        "template_only": False,
        "packet_state": "draft_from_q6_4_contract",
        "postmortem_draft": True,
        "source_outcome_ref": outcome_ref,
        "source_closed_trade_ref": closed_trade_ref,
        "narrative_only": False,
        "narrative_body": None,
        "sections": sections,
        "section_count": len(sections),
        "source_assertion_count": assertion_count,
        "unknown_fields_marked": unknown_fields,
        "unknown_field_count": len(unknown_fields),
        "unknown_markers": unknown_markers,
        "unknown_marker_count": len(unknown_markers),
        "deferred_fields_marked": deferred_fields,
        "deferred_field_count": len(deferred_fields),
        "deferred_markers": deferred_markers,
        "deferred_marker_count": len(deferred_markers),
        "missing_ref_markers": missing_ref_markers,
        "missing_ref_count": len(missing_ref_markers),
        "source_refs": provenance_refs,
        "write_authority": False,
        "postmortem_draft_created": False,
        **_disabled_write_fields(),
    }


def build_phase6_postmortem_draft(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    contract = _read_json(SOURCE_PACKET_CONTRACT_REF, settings) or {}
    outcome = _read_json(SOURCE_OUTCOME_REF, settings) or {}
    contract_errors = (
        validate_phase6_postmortem_packet_contract(contract) if contract else []
    )
    outcome_errors = validate_phase6_closed_trade_outcome(outcome) if outcome else []
    blockers: list[str] = []
    if not contract:
        blockers.append("postmortem_packet_contract_missing")
    elif contract.get("status") != "schema_only":
        blockers.append("postmortem_packet_contract_not_schema_only")
    if not outcome:
        blockers.append("closed_trade_outcome_missing")
    elif outcome.get("status") != "read_only":
        blockers.append("closed_trade_outcome_not_read_only")
    if contract_errors:
        blockers.append("postmortem_packet_contract_validation_errors")
    if outcome_errors:
        blockers.append("closed_trade_outcome_validation_errors")

    packet = _build_packet(contract, outcome) if not blockers else {}
    packet_errors = validate_postmortem_packet_payload(packet, contract) if packet else []
    if packet_errors:
        blockers.append("postmortem_packet_payload_validation_errors")

    status = "draft" if not blockers else "blocked"
    authority = phase6_authority_ledger()
    authority["stage"] = "Q6-5"
    authority["boundary"] = PHASE6_POSTMORTEM_DRAFT_BOUNDARY
    source_assertion_count = int(packet.get("source_assertion_count", 0) or 0)
    unknown_markers = _list(packet.get("unknown_markers"))
    deferred_markers = _list(packet.get("deferred_markers"))
    missing_ref_markers = _list(packet.get("missing_ref_markers"))
    artifact = {
        "schema_version": PHASE6_ARTIFACT_SCHEMA_VERSION,
        "phase6_postmortem_draft_schema_version": PHASE6_POSTMORTEM_DRAFT_SCHEMA_VERSION,
        "artifact_type": "postmortem_draft",
        "artifact_id": "phase6:q6-5:postmortem-draft:crude_oil_energy_security_disruption",
        "phase": "Q6",
        "stage": "Q6-5",
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
        "provenance": _provenance(contract, outcome),
        "boundary": PHASE6_POSTMORTEM_DRAFT_BOUNDARY,
        **phase6_authority_defaults(),
        **phase6_unsafe_counter_defaults(),
        **_disabled_write_fields(),
        "draft_state": "deterministic_postmortem_draft_created" if packet else "blocked",
        "approval_state": "not_requested",
        "postmortem_approved": False,
        "postmortem_draft_created": bool(packet),
        "postmortem_draft_count": 1 if packet else 0,
        "llm_required": False,
        "llm_used": False,
        "deterministic_draft": True,
        "source_packet_contract_ref": SOURCE_PACKET_CONTRACT_REF,
        "source_packet_contract_status": contract.get("status"),
        "source_outcome_artifact_ref": SOURCE_OUTCOME_REF,
        "source_outcome_ref": packet.get("source_outcome_ref") if packet else None,
        "source_closed_trade_ref": packet.get("source_closed_trade_ref") if packet else None,
        "packet": packet,
        "packet_validation_errors": packet_errors,
        "packet_validation_error_count": len(packet_errors),
        "packet_section_count": int(packet.get("section_count", 0) or 0),
        "source_assertion_count": source_assertion_count,
        "unknown_field_count": int(packet.get("unknown_field_count", 0) or 0),
        "unknown_markers": unknown_markers,
        "unknown_marker_count": len(unknown_markers),
        "deferred_field_count": int(packet.get("deferred_field_count", 0) or 0),
        "deferred_markers": deferred_markers,
        "deferred_marker_count": len(deferred_markers),
        "missing_ref_markers": missing_ref_markers,
        "missing_ref_count": len(missing_ref_markers),
        "missing_refs_marked": True,
        "unknowns_marked": True,
        "learning_write_allowed": False,
        "phase5_test_trades_count_for_phase7": False,
        "phase7_proof_credit_allowed": False,
        "unsafe_write_counter_total": 0,
        "blockers": sorted(set(blockers)),
        "blocker_count": len(set(blockers)),
        "recommended_next_stage": "Q6-6 Analysis Sub-Agent Packets",
    }
    artifact["validation_errors"] = validate_phase6_postmortem_draft(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "error"
    return artifact


def _write_disabled_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in WRITE_DISABLED_FIELDS:
        if artifact.get(field) is not False:
            errors.append(f"postmortem_draft_write_enabled:{field}")
    return errors


def validate_phase6_postmortem_draft(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "phase6_postmortem_draft_schema_version",
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
        "draft_state",
        "source_assertion_count",
        "approval_state",
        "learning_write_allowed",
        "postmortem_approved",
        "postmortem_draft_created",
        "postmortem_draft_count",
        "llm_required",
        "llm_used",
        "deterministic_draft",
        "source_packet_contract_ref",
        "source_outcome_artifact_ref",
        "source_outcome_ref",
        "source_closed_trade_ref",
        "packet",
        "packet_validation_error_count",
        "packet_section_count",
        "unknown_field_count",
        "unknown_markers",
        "unknown_marker_count",
        "deferred_field_count",
        "deferred_markers",
        "deferred_marker_count",
        "missing_ref_markers",
        "missing_ref_count",
        "missing_refs_marked",
        "unknowns_marked",
        "phase5_test_trades_count_for_phase7",
        "phase7_proof_credit_allowed",
        "unsafe_write_counter_total",
        "blockers",
        "blocker_count",
    }
    missing = sorted(required_fields - set(artifact))
    if missing:
        errors.append("postmortem_draft_missing_fields:" + ",".join(missing))
    if artifact.get("phase6_postmortem_draft_schema_version") != (
        PHASE6_POSTMORTEM_DRAFT_SCHEMA_VERSION
    ):
        errors.append("postmortem_draft_schema_version_mismatch")
    errors.extend(validate_phase6_artifact(artifact, expected_stage="Q6-5"))
    if artifact.get("artifact_type") != "postmortem_draft":
        errors.append("postmortem_draft_artifact_type_mismatch")
    if artifact.get("status") not in {"draft", "blocked", "error"}:
        errors.append("postmortem_draft_status_invalid")
    if artifact.get("draft_state") != "deterministic_postmortem_draft_created":
        errors.append("postmortem_draft_state_invalid")
    if artifact.get("approval_state") != "not_requested":
        errors.append("postmortem_draft_approval_state_invalid")
    if artifact.get("postmortem_approved") is not False:
        errors.append("postmortem_approved")
    if artifact.get("learning_write_allowed") is not False:
        errors.append("learning_write_allowed")
    errors.extend(_write_disabled_errors(artifact))
    for field in PHASE6_UNSAFE_COUNT_FIELDS:
        if int(artifact.get(field, 0) or 0) != 0:
            errors.append(f"postmortem_draft_unsafe_count_nonzero:{field}")
    unsafe_total = sum(int(artifact.get(field, 0) or 0) for field in PHASE6_UNSAFE_COUNT_FIELDS)
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("postmortem_draft_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("postmortem_draft_unsafe_total_nonzero")
    if artifact.get("postmortem_draft_created") is not True:
        errors.append("postmortem_draft_not_created")
    if artifact.get("postmortem_draft_count") != 1:
        errors.append("postmortem_draft_count_invalid")
    if artifact.get("llm_required") is not False:
        errors.append("llm_required")
    if artifact.get("llm_used") is not False:
        errors.append("llm_used")
    if artifact.get("deterministic_draft") is not True:
        errors.append("deterministic_draft_not_true")
    if artifact.get("source_packet_contract_ref") != SOURCE_PACKET_CONTRACT_REF:
        errors.append("source_packet_contract_ref_invalid")
    if artifact.get("source_outcome_artifact_ref") != SOURCE_OUTCOME_REF:
        errors.append("source_outcome_artifact_ref_invalid")
    if not artifact.get("source_outcome_ref"):
        errors.append("source_outcome_ref_missing")
    if not artifact.get("source_closed_trade_ref"):
        errors.append("source_closed_trade_ref_missing")
    if artifact.get("missing_refs_marked") is not True:
        errors.append("missing_refs_not_marked")
    if artifact.get("unknowns_marked") is not True:
        errors.append("unknowns_not_marked")
    if int(artifact.get("unknown_field_count", 0) or 0) < 1:
        errors.append("unknown_field_count_missing")
    if int(artifact.get("deferred_field_count", 0) or 0) < 1:
        errors.append("deferred_field_count_missing")
    unknown_markers = artifact.get("unknown_markers", [])
    deferred_markers = artifact.get("deferred_markers", [])
    missing_ref_markers = artifact.get("missing_ref_markers", [])
    if not isinstance(unknown_markers, list) or not unknown_markers:
        errors.append("unknown_markers_missing")
        unknown_markers = []
    if not isinstance(deferred_markers, list) or not deferred_markers:
        errors.append("deferred_markers_missing")
        deferred_markers = []
    if not isinstance(missing_ref_markers, list) or not missing_ref_markers:
        errors.append("missing_ref_markers_missing")
        missing_ref_markers = []
    if artifact.get("unknown_marker_count") != len(unknown_markers):
        errors.append("unknown_marker_count_mismatch")
    if artifact.get("deferred_marker_count") != len(deferred_markers):
        errors.append("deferred_marker_count_mismatch")
    if artifact.get("missing_ref_count") != len(missing_ref_markers):
        errors.append("missing_ref_count_mismatch")
    outcome = _read_json(SOURCE_OUTCOME_REF) or {}
    expected_record = _outcome_record(outcome)
    expected_unknown_fields = {str(field) for field in _list(expected_record.get("unknown_fields"))}
    expected_deferred_fields = {
        str(field) for field in _list(expected_record.get("deferred_fields"))
    }
    expected_missing_ref_fields = {
        field for field in expected_unknown_fields if field.startswith("broker_fill")
    }
    missing_unknown_markers = sorted(expected_unknown_fields - _marker_fields(unknown_markers))
    missing_deferred_markers = sorted(
        expected_deferred_fields - _marker_fields(deferred_markers)
    )
    missing_ref_marker_fields = sorted(
        expected_missing_ref_fields - _marker_fields(missing_ref_markers)
    )
    if missing_unknown_markers:
        errors.append("unknown_marker_missing:" + ",".join(missing_unknown_markers))
    if missing_deferred_markers:
        errors.append("deferred_marker_missing:" + ",".join(missing_deferred_markers))
    if missing_ref_marker_fields:
        errors.append("missing_ref_marker_missing:" + ",".join(missing_ref_marker_fields))
    if artifact.get("phase7_proof_credit_allowed") is not False:
        errors.append("phase7_proof_credit_allowed")
    if artifact.get("phase5_test_trades_count_for_phase7") is not False:
        errors.append("phase5_test_trades_count_for_phase7")
    packet = artifact.get("packet")
    if not isinstance(packet, dict):
        errors.append("postmortem_packet_missing")
        packet = {}
    contract = _read_json(SOURCE_PACKET_CONTRACT_REF) or {}
    if contract:
        packet_errors = validate_postmortem_packet_payload(packet, contract)
        errors.extend(f"postmortem_packet:{error}" for error in packet_errors)
        if artifact.get("packet_validation_error_count") != len(packet_errors):
            errors.append("packet_validation_error_count_mismatch")
    if packet.get("template_only") is not False:
        errors.append("postmortem_packet_template_only")
    if packet.get("postmortem_draft") is not True:
        errors.append("postmortem_packet_not_draft")
    if packet.get("postmortem_draft_created") is not False:
        errors.append("postmortem_packet_draft_created_write_flag")
    sections = packet.get("sections", [])
    if not isinstance(sections, list):
        errors.append("postmortem_packet_sections_invalid")
        sections = []
    if artifact.get("packet_section_count") != len(POSTMORTEM_PACKET_SECTIONS):
        errors.append("packet_section_count_invalid")
    if artifact.get("packet_section_count") != len(sections):
        errors.append("packet_section_count_mismatch")
    if int(artifact.get("source_assertion_count", 0) or 0) < len(POSTMORTEM_PACKET_SECTIONS):
        errors.append("source_assertion_count_too_low")
    if packet.get("source_assertion_count") != artifact.get("source_assertion_count"):
        errors.append("packet_source_assertion_count_mismatch")
    if packet.get("unknown_marker_count") != artifact.get("unknown_marker_count"):
        errors.append("packet_unknown_marker_count_mismatch")
    if packet.get("deferred_marker_count") != artifact.get("deferred_marker_count"):
        errors.append("packet_deferred_marker_count_mismatch")
    if packet.get("missing_ref_count") != artifact.get("missing_ref_count"):
        errors.append("packet_missing_ref_count_mismatch")
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
        "deterministic source-cited postmortem draft only",
        "cannot approve a postmortem",
        "cannot write learning data",
        "cannot write a Knowledge Graph",
        "cannot update model weights",
        "cannot update trust scores",
        "cannot mutate policy",
        "cannot mutate strategies",
        "cannot count Phase 5 test trades toward Phase 7 proof",
    ):
        if phrase not in boundary:
            errors.append("postmortem_draft_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("postmortem_draft_event_log_path_missing")
        if not str(artifact.get("event_log_correlation_id") or "").strip():
            errors.append("postmortem_draft_event_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("postmortem_draft_event_log_count_mismatch")
    return sorted(set(errors))


def attach_phase6_postmortem_draft_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(event_log_path or (_runtime_dir(settings) / PHASE6_POSTMORTEM_DRAFT_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE6_POSTMORTEM_DRAFT_EVENT_TYPE,
        PHASE6_POSTMORTEM_DRAFT_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "draft_state": output.get("draft_state"),
            "source_outcome_ref": output.get("source_outcome_ref"),
            "source_assertion_count": output.get("source_assertion_count"),
            "packet_section_count": output.get("packet_section_count"),
            "unknown_marker_count": output.get("unknown_marker_count"),
            "deferred_marker_count": output.get("deferred_marker_count"),
            "missing_ref_count": output.get("missing_ref_count"),
            "postmortem_approved": output.get("postmortem_approved"),
            "learning_write_allowed": output.get("learning_write_allowed"),
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
    output["validation_errors"] = validate_phase6_postmortem_draft(output)
    if output["validation_errors"]:
        output["status"] = "error"
    return output, entry


def write_phase6_postmortem_draft(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase6_postmortem_draft_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase6_postmortem_draft_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase6_postmortem_draft(output)
        if output["validation_errors"]:
            output["status"] = "error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase6_postmortem_draft(output)
    if output["validation_errors"]:
        output["status"] = "error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE6_POSTMORTEM_DRAFT_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "draft_state": output.get("draft_state"),
        "source_outcome_ref": output.get("source_outcome_ref"),
        "packet_section_count": output.get("packet_section_count"),
        "source_assertion_count": output.get("source_assertion_count"),
        "unknown_marker_count": output.get("unknown_marker_count"),
        "deferred_marker_count": output.get("deferred_marker_count"),
        "missing_ref_count": output.get("missing_ref_count"),
        "postmortem_approved": output.get("postmortem_approved"),
        "learning_write_allowed": output.get("learning_write_allowed"),
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
