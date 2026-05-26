"""Q6-4 postmortem packet contract.

This stage defines the packet shape that Q6-5 must fill. It records required
sections and assertion rules, and exposes validators that reject narrative-only
postmortems, missing outcome refs, uncited conclusions, and hidden write
authority. It does not create a postmortem draft.
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


PHASE6_POSTMORTEM_PACKET_CONTRACT_SCHEMA_VERSION = 1
PHASE6_POSTMORTEM_PACKET_CONTRACT_RUNTIME_ARTIFACT = (
    "phase6_postmortem_packet_contract.json"
)
PHASE6_POSTMORTEM_PACKET_CONTRACT_HISTORY = "phase6_postmortem_packet_contract_history.jsonl"
PHASE6_POSTMORTEM_PACKET_CONTRACT_EVENT_LOG = (
    "phase6_postmortem_packet_contract_events.jsonl"
)
PHASE6_POSTMORTEM_PACKET_CONTRACT_EVENT_TYPE = (
    "phase6_postmortem_packet_contract_recorded"
)
PHASE6_POSTMORTEM_PACKET_CONTRACT_COMPONENT = "phase6_postmortem_packet_contract"

SOURCE_OUTCOME_ARTIFACT_REF = f"data/runtime/{PHASE6_CLOSED_TRADE_OUTCOME_RUNTIME_ARTIFACT}"

POSTMORTEM_PACKET_SECTIONS: tuple[str, ...] = (
    "thesis",
    "timeline",
    "catalyst_read",
    "pricing_read",
    "regime_read",
    "execution_read",
    "override_readiness_read",
    "source_quality",
    "mistakes",
    "useful_signals",
    "harmful_signals",
    "uncertainty",
    "proposed_learning_actions",
)

ASSERTION_REQUIRED_FIELDS: tuple[str, ...] = (
    "assertion_id",
    "assertion_kind",
    "statement",
    "source_refs",
    "is_hypothesis",
    "conclusion",
    "review_required",
)

ALLOWED_ASSERTION_KINDS: tuple[str, ...] = (
    "evidence",
    "unknown",
    "deferred",
    "hypothesis",
    "proposed_learning_action",
)

PACKET_WRITE_DISABLED_FIELDS: tuple[str, ...] = (
    "postmortem_draft_created",
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

PHASE6_POSTMORTEM_PACKET_CONTRACT_BOUNDARY = (
    "Q6-4 defines the postmortem packet contract only. It can require source "
    "refs, required sections, hypothesis markers, and validation rules for a "
    "future Q6-5 draft, but it cannot create a postmortem draft, cannot approve "
    "a postmortem, cannot write learning data, cannot write a Knowledge Graph, "
    "cannot update model weights, cannot update trust scores, cannot mutate "
    "policy, cannot mutate strategies, cannot call broker POST routes, cannot "
    "call Alpaca POST routes, cannot call live endpoints, cannot enable live "
    "capital, and cannot count Phase 5 test trades toward Phase 7 proof."
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


def _has_local_path(ref: str) -> bool:
    if ref.startswith("/") or ref.startswith("~"):
        return True
    return len(ref) > 2 and ref[1:3] == ":\\"


def phase6_postmortem_packet_contract_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE6_POSTMORTEM_PACKET_CONTRACT_RUNTIME_ARTIFACT,
        runtime / PHASE6_POSTMORTEM_PACKET_CONTRACT_HISTORY,
        runtime / PHASE6_POSTMORTEM_PACKET_CONTRACT_EVENT_LOG,
    )


def _disabled_write_fields() -> dict[str, bool]:
    return {field: False for field in PACKET_WRITE_DISABLED_FIELDS}


def _section_contracts() -> list[dict[str, Any]]:
    contracts: list[dict[str, Any]] = []
    for section_key in POSTMORTEM_PACKET_SECTIONS:
        contracts.append(
            {
                "section_key": section_key,
                "required": True,
                "source_refs_or_hypothesis_required": True,
                "uncited_conclusion_allowed": False,
                "minimum_assertion_count_for_draft": 1,
                "allowed_assertion_kinds": list(ALLOWED_ASSERTION_KINDS),
                "allowed_empty_in_contract_template": True,
                "write_authority": False,
            }
        )
    return contracts


def _packet_template(
    *,
    source_outcome_ref: str | None,
    source_closed_trade_ref: str | None,
) -> dict[str, Any]:
    return {
        "template_only": True,
        "packet_state": "contract_template_not_draft",
        "postmortem_draft": False,
        "source_outcome_ref": source_outcome_ref,
        "source_closed_trade_ref": source_closed_trade_ref,
        "narrative_only": False,
        "narrative_body": None,
        "sections": [
            {
                "section_key": section_key,
                "required": True,
                "assertions": [],
                "assertion_count": 0,
                "source_refs_or_hypothesis_required": True,
                "uncited_conclusion_allowed": False,
                "minimum_assertion_count_for_draft": 1,
            }
            for section_key in POSTMORTEM_PACKET_SECTIONS
        ],
        "write_authority": False,
        **_disabled_write_fields(),
    }


def _provenance(outcome_artifact: dict[str, Any]) -> dict[str, Any]:
    outcome_provenance = outcome_artifact.get("provenance", {})
    source_refs = [SOURCE_OUTCOME_ARTIFACT_REF]
    if isinstance(outcome_provenance, dict):
        source_refs.extend(
            [
                ref
                for ref in outcome_provenance.get("source_refs", [])
                if isinstance(ref, str) and ref not in source_refs
            ]
        )
    provenance = phase6_provenance(tuple(source_refs))
    provenance["execution_evidence_refs"] = (
        outcome_provenance.get("execution_evidence_refs", [])
        if isinstance(outcome_provenance, dict)
        else []
    )
    provenance["market_context_refs"] = (
        outcome_provenance.get("market_context_refs", [])
        if isinstance(outcome_provenance, dict)
        else []
    )
    provenance["model_interpretation_refs"] = (
        outcome_provenance.get("model_interpretation_refs", [])
        if isinstance(outcome_provenance, dict)
        else []
    )
    provenance["governance_refs"] = (
        outcome_provenance.get("governance_refs", [])
        if isinstance(outcome_provenance, dict)
        else []
    )
    return provenance


def build_phase6_postmortem_packet_contract(
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    outcome_artifact = _read_json(SOURCE_OUTCOME_ARTIFACT_REF, settings) or {}
    outcome_errors = (
        validate_phase6_closed_trade_outcome(outcome_artifact) if outcome_artifact else []
    )
    outcome_record = (
        outcome_artifact.get("outcome_records", [{}])[0]
        if isinstance(outcome_artifact.get("outcome_records"), list)
        and outcome_artifact.get("outcome_records")
        else {}
    )
    blockers: list[str] = []
    if not outcome_artifact:
        blockers.append("closed_trade_outcome_artifact_missing")
    elif outcome_artifact.get("status") != "read_only":
        blockers.append("closed_trade_outcome_not_read_only")
    if outcome_artifact.get("outcome_record_count") != 1:
        blockers.append("closed_trade_outcome_record_missing")
    if outcome_errors:
        blockers.append("closed_trade_outcome_validation_errors")

    source_outcome_ref = outcome_record.get("outcome_ref")
    source_closed_trade_ref = outcome_record.get("source_closed_trade_ref")
    if not source_outcome_ref:
        blockers.append("source_outcome_ref_missing")
    if not source_closed_trade_ref:
        blockers.append("source_closed_trade_ref_missing")

    status = "schema_only" if not blockers else "blocked"
    authority = phase6_authority_ledger()
    authority["stage"] = "Q6-4"
    authority["boundary"] = PHASE6_POSTMORTEM_PACKET_CONTRACT_BOUNDARY
    artifact = {
        "schema_version": PHASE6_ARTIFACT_SCHEMA_VERSION,
        "phase6_postmortem_packet_contract_schema_version": (
            PHASE6_POSTMORTEM_PACKET_CONTRACT_SCHEMA_VERSION
        ),
        "artifact_type": "postmortem_packet",
        "artifact_id": "phase6:q6-4:postmortem-packet-contract",
        "phase": "Q6",
        "stage": "Q6-4",
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
        "event_contract": phase6_event_contract("artifact_schema"),
        "authority_ledger": authority,
        "source_posture": phase6_source_posture(),
        "provenance": _provenance(outcome_artifact),
        "boundary": PHASE6_POSTMORTEM_PACKET_CONTRACT_BOUNDARY,
        **phase6_authority_defaults(),
        **phase6_unsafe_counter_defaults(),
        **_disabled_write_fields(),
        "packet_contract_state": "postmortem_packet_contract_defined",
        "packet_sections": list(POSTMORTEM_PACKET_SECTIONS),
        "packet_section_count": len(POSTMORTEM_PACKET_SECTIONS),
        "section_contracts": _section_contracts(),
        "required_section_count": len(POSTMORTEM_PACKET_SECTIONS),
        "assertion_source_refs_required": True,
        "assertion_required_fields": list(ASSERTION_REQUIRED_FIELDS),
        "allowed_assertion_kinds": list(ALLOWED_ASSERTION_KINDS),
        "uncited_conclusion_allowed": False,
        "narrative_only_allowed": False,
        "missing_outcome_ref_allowed": False,
        "hypothesis_marker_required_when_uncited": True,
        "packet_validator_available": True,
        "source_outcome_artifact_ref": SOURCE_OUTCOME_ARTIFACT_REF,
        "source_outcome_ref": source_outcome_ref,
        "source_closed_trade_ref": source_closed_trade_ref,
        "source_outcome_status": outcome_artifact.get("status"),
        "source_outcome_record_count": outcome_artifact.get("outcome_record_count", 0),
        "source_outcome_validation_error_count": len(outcome_errors),
        "packet_template": _packet_template(
            source_outcome_ref=source_outcome_ref,
            source_closed_trade_ref=source_closed_trade_ref,
        ),
        "packet_template_section_count": len(POSTMORTEM_PACKET_SECTIONS),
        "packet_template_assertion_count": 0,
        "phase5_test_trades_count_for_phase7": False,
        "phase7_proof_credit_allowed": False,
        "unsafe_write_counter_total": 0,
        "blockers": sorted(set(blockers)),
        "blocker_count": len(set(blockers)),
        "recommended_next_stage": "Q6-5 Postmortem Agent Drafting",
    }
    artifact["validation_errors"] = validate_phase6_postmortem_packet_contract(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "error"
    return artifact


def _section_keys(sections: Any) -> set[str]:
    if not isinstance(sections, list):
        return set()
    return {
        str(section.get("section_key"))
        for section in sections
        if isinstance(section, dict) and section.get("section_key")
    }


def _write_disabled_errors(prefix: str, payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in PACKET_WRITE_DISABLED_FIELDS:
        if payload.get(field) is not False:
            errors.append(f"{prefix}_write_enabled:{field}")
    return errors


def validate_postmortem_packet_payload(
    packet: dict[str, Any],
    contract: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if not isinstance(packet, dict):
        return ["packet_invalid"]
    if not packet.get("source_outcome_ref"):
        errors.append("packet_missing_outcome_ref")
    elif packet.get("source_outcome_ref") != contract.get("source_outcome_ref"):
        errors.append("packet_outcome_ref_mismatch")
    if not packet.get("source_closed_trade_ref"):
        errors.append("packet_missing_closed_trade_ref")
    if packet.get("narrative_only") is True:
        errors.append("narrative_only_packet")
    if packet.get("narrative_body") and not packet.get("sections"):
        errors.append("narrative_only_packet")
    if packet.get("write_authority") is not False:
        errors.append("packet_write_authority")
    errors.extend(_write_disabled_errors("packet", packet))

    sections = packet.get("sections")
    if not isinstance(sections, list):
        errors.append("packet_sections_invalid")
        sections = []
    required_sections = set(POSTMORTEM_PACKET_SECTIONS)
    present_sections = _section_keys(sections)
    for section_key in sorted(required_sections - present_sections):
        errors.append(f"packet_required_section_missing:{section_key}")
    template_only = packet.get("template_only") is True
    for section in sections:
        if not isinstance(section, dict):
            errors.append("packet_section_invalid")
            continue
        section_key = str(section.get("section_key") or "")
        if section_key not in required_sections:
            errors.append(f"packet_unknown_section:{section_key}")
        if section.get("uncited_conclusion_allowed") is not False:
            errors.append(f"section_uncited_conclusion_allowed:{section_key}")
        assertions = section.get("assertions")
        if not isinstance(assertions, list):
            errors.append(f"section_assertions_invalid:{section_key}")
            assertions = []
        if not template_only and not assertions:
            errors.append(f"section_assertions_missing:{section_key}")
        if section.get("assertion_count") is not None and section.get("assertion_count") != len(
            assertions
        ):
            errors.append(f"section_assertion_count_mismatch:{section_key}")
        for assertion in assertions:
            if not isinstance(assertion, dict):
                errors.append(f"packet_assertion_invalid:{section_key}")
                continue
            for field in ASSERTION_REQUIRED_FIELDS:
                if field not in assertion:
                    errors.append(f"packet_assertion_missing_field:{section_key}:{field}")
            assertion_kind = str(assertion.get("assertion_kind") or "")
            if assertion_kind not in ALLOWED_ASSERTION_KINDS:
                errors.append(f"packet_assertion_kind_invalid:{section_key}:{assertion_kind}")
            source_refs = assertion.get("source_refs", [])
            if not isinstance(source_refs, list):
                errors.append(f"packet_assertion_source_refs_invalid:{section_key}")
                source_refs = []
            is_hypothesis = assertion.get("is_hypothesis") is True
            if is_hypothesis:
                if not assertion.get("hypothesis_reason"):
                    errors.append(f"packet_hypothesis_reason_missing:{section_key}")
                if assertion.get("review_required") is not True:
                    errors.append(f"packet_hypothesis_review_not_required:{section_key}")
            else:
                if not source_refs:
                    errors.append(f"packet_assertion_source_refs_missing:{section_key}")
                if assertion.get("conclusion") is True and not source_refs:
                    errors.append("uncited_conclusion")
            for ref in source_refs:
                if not isinstance(ref, str) or not ref.strip():
                    errors.append(f"packet_assertion_source_ref_invalid:{section_key}")
                    continue
                if _has_local_path(ref):
                    errors.append("packet_assertion_local_source_ref")
                if any(secret_word in ref.lower() for secret_word in ("api_key", "secret", "token")):
                    errors.append("packet_assertion_secret_ref")
    return sorted(set(errors))


def build_postmortem_packet_validation_fixture(contract: dict[str, Any]) -> dict[str, Any]:
    source_outcome_ref = str(contract.get("source_outcome_ref") or "")
    source_closed_trade_ref = str(contract.get("source_closed_trade_ref") or "")
    outcome_artifact_ref = str(contract.get("source_outcome_artifact_ref") or "")
    sections: list[dict[str, Any]] = []
    for section_key in POSTMORTEM_PACKET_SECTIONS:
        assertion = {
            "assertion_id": f"fixture:{section_key}:1",
            "assertion_kind": (
                "proposed_learning_action"
                if section_key == "proposed_learning_actions"
                else "deferred"
                if section_key
                in {"catalyst_read", "pricing_read", "regime_read", "source_quality"}
                else "evidence"
            ),
            "statement": (
                f"{section_key} must be filled from cited Q6-3 outcome evidence or "
                "explicitly marked as hypothesis in Q6-5."
            ),
            "source_refs": [outcome_artifact_ref],
            "is_hypothesis": False,
            "hypothesis_reason": None,
            "conclusion": section_key in {"realized_outcome", "execution_read"},
            "review_required": True,
        }
        sections.append(
            {
                "section_key": section_key,
                "required": True,
                "assertions": [assertion],
                "assertion_count": 1,
                "source_refs_or_hypothesis_required": True,
                "uncited_conclusion_allowed": False,
            }
        )
    return {
        "template_only": False,
        "packet_state": "validation_fixture_not_recorded",
        "source_outcome_ref": source_outcome_ref,
        "source_closed_trade_ref": source_closed_trade_ref,
        "narrative_only": False,
        "narrative_body": None,
        "sections": sections,
        "write_authority": False,
        **_disabled_write_fields(),
    }


def validate_phase6_postmortem_packet_contract(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "phase6_postmortem_packet_contract_schema_version",
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
        "packet_sections",
        "assertion_source_refs_required",
        "uncited_conclusion_allowed",
        "packet_contract_state",
        "section_contracts",
        "required_section_count",
        "narrative_only_allowed",
        "missing_outcome_ref_allowed",
        "packet_validator_available",
        "source_outcome_artifact_ref",
        "source_outcome_ref",
        "source_closed_trade_ref",
        "packet_template",
        "phase5_test_trades_count_for_phase7",
        "phase7_proof_credit_allowed",
        "unsafe_write_counter_total",
        "blockers",
        "blocker_count",
    }
    missing = sorted(required_fields - set(artifact))
    if missing:
        errors.append("postmortem_packet_contract_missing_fields:" + ",".join(missing))
    if artifact.get("phase6_postmortem_packet_contract_schema_version") != (
        PHASE6_POSTMORTEM_PACKET_CONTRACT_SCHEMA_VERSION
    ):
        errors.append("postmortem_packet_contract_schema_version_mismatch")
    errors.extend(validate_phase6_artifact(artifact, expected_stage="Q6-4"))
    if artifact.get("artifact_type") != "postmortem_packet":
        errors.append("postmortem_packet_contract_artifact_type_mismatch")
    if artifact.get("status") not in {"schema_only", "blocked", "error"}:
        errors.append("postmortem_packet_contract_status_invalid")
    if artifact.get("packet_contract_state") != "postmortem_packet_contract_defined":
        errors.append("postmortem_packet_contract_state_invalid")
    if artifact.get("assertion_source_refs_required") is not True:
        errors.append("assertion_source_refs_not_required")
    if artifact.get("uncited_conclusion_allowed") is not False:
        errors.append("uncited_conclusion_allowed")
    if artifact.get("narrative_only_allowed") is not False:
        errors.append("narrative_only_allowed")
    if artifact.get("missing_outcome_ref_allowed") is not False:
        errors.append("missing_outcome_ref_allowed")
    if artifact.get("packet_validator_available") is not True:
        errors.append("packet_validator_not_available")
    if artifact.get("source_outcome_artifact_ref") != SOURCE_OUTCOME_ARTIFACT_REF:
        errors.append("source_outcome_artifact_ref_invalid")
    if not artifact.get("source_outcome_ref"):
        errors.append("source_outcome_ref_missing")
    if not artifact.get("source_closed_trade_ref"):
        errors.append("source_closed_trade_ref_missing")
    errors.extend(_write_disabled_errors("postmortem_packet_contract", artifact))
    for field in PHASE6_UNSAFE_COUNT_FIELDS:
        if int(artifact.get(field, 0) or 0) != 0:
            errors.append(f"postmortem_packet_contract_unsafe_count_nonzero:{field}")
    unsafe_total = sum(int(artifact.get(field, 0) or 0) for field in PHASE6_UNSAFE_COUNT_FIELDS)
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("postmortem_packet_contract_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("postmortem_packet_contract_unsafe_total_nonzero")
    if artifact.get("phase7_proof_credit_allowed") is not False:
        errors.append("phase7_proof_credit_allowed")
    if artifact.get("phase5_test_trades_count_for_phase7") is not False:
        errors.append("phase5_test_trades_count_for_phase7")

    packet_sections = artifact.get("packet_sections", [])
    if not isinstance(packet_sections, list):
        errors.append("packet_sections_invalid")
        packet_sections = []
    if set(packet_sections) != set(POSTMORTEM_PACKET_SECTIONS):
        errors.append("packet_sections_mismatch")
    if artifact.get("packet_section_count") != len(POSTMORTEM_PACKET_SECTIONS):
        errors.append("packet_section_count_mismatch")
    if artifact.get("required_section_count") != len(POSTMORTEM_PACKET_SECTIONS):
        errors.append("required_section_count_mismatch")
    section_contracts = artifact.get("section_contracts", [])
    if not isinstance(section_contracts, list):
        errors.append("section_contracts_invalid")
        section_contracts = []
    if _section_keys(section_contracts) != set(POSTMORTEM_PACKET_SECTIONS):
        errors.append("section_contracts_mismatch")
    for section in section_contracts:
        if not isinstance(section, dict):
            errors.append("section_contract_invalid")
            continue
        section_key = section.get("section_key")
        if section.get("required") is not True:
            errors.append(f"section_contract_not_required:{section_key}")
        if section.get("source_refs_or_hypothesis_required") is not True:
            errors.append(f"section_contract_refs_not_required:{section_key}")
        if section.get("uncited_conclusion_allowed") is not False:
            errors.append(f"section_contract_uncited_conclusion_allowed:{section_key}")
        if section.get("write_authority") is not False:
            errors.append(f"section_contract_write_authority:{section_key}")
    template = artifact.get("packet_template")
    if not isinstance(template, dict):
        errors.append("packet_template_invalid")
    else:
        template_errors = validate_postmortem_packet_payload(template, artifact)
        errors.extend(f"packet_template:{error}" for error in template_errors)
        if template.get("template_only") is not True:
            errors.append("packet_template_not_template_only")
        if template.get("postmortem_draft") is not False:
            errors.append("packet_template_postmortem_draft")
        if int(artifact.get("packet_template_assertion_count", 0) or 0) != 0:
            errors.append("packet_template_assertion_count_nonzero")
    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("blockers_invalid")
        blockers = []
    if artifact.get("blocker_count") != len(blockers):
        errors.append("blocker_count_mismatch")
    if artifact.get("status") == "schema_only" and blockers:
        errors.append("schema_only_with_blockers")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "defines the postmortem packet contract only",
        "cannot create a postmortem draft",
        "cannot approve a postmortem",
        "cannot write learning data",
        "cannot write a Knowledge Graph",
        "cannot mutate policy",
        "cannot mutate strategies",
        "cannot count Phase 5 test trades toward Phase 7 proof",
    ):
        if phrase not in boundary:
            errors.append("postmortem_packet_contract_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("postmortem_packet_contract_event_log_path_missing")
        if not str(artifact.get("event_log_correlation_id") or "").strip():
            errors.append("postmortem_packet_contract_event_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("postmortem_packet_contract_event_log_count_mismatch")
    return sorted(set(errors))


def attach_phase6_postmortem_packet_contract_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(
        event_log_path or (_runtime_dir(settings) / PHASE6_POSTMORTEM_PACKET_CONTRACT_EVENT_LOG)
    )
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE6_POSTMORTEM_PACKET_CONTRACT_EVENT_TYPE,
        PHASE6_POSTMORTEM_PACKET_CONTRACT_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "source_outcome_ref": output.get("source_outcome_ref"),
            "packet_section_count": output.get("packet_section_count"),
            "assertion_source_refs_required": output.get("assertion_source_refs_required"),
            "uncited_conclusion_allowed": output.get("uncited_conclusion_allowed"),
            "narrative_only_allowed": output.get("narrative_only_allowed"),
            "postmortem_draft_created": output.get("postmortem_draft_created"),
            "learning_write_created": output.get("learning_write_created"),
            "knowledge_graph_write_created": output.get("knowledge_graph_write_created"),
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
    output["validation_errors"] = validate_phase6_postmortem_packet_contract(output)
    if output["validation_errors"]:
        output["status"] = "error"
    return output, entry


def write_phase6_postmortem_packet_contract(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase6_postmortem_packet_contract_paths(
        settings
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase6_postmortem_packet_contract_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase6_postmortem_packet_contract(output)
        if output["validation_errors"]:
            output["status"] = "error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase6_postmortem_packet_contract(output)
    if output["validation_errors"]:
        output["status"] = "error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE6_POSTMORTEM_PACKET_CONTRACT_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "source_outcome_ref": output.get("source_outcome_ref"),
        "packet_section_count": output.get("packet_section_count"),
        "assertion_source_refs_required": output.get("assertion_source_refs_required"),
        "uncited_conclusion_allowed": output.get("uncited_conclusion_allowed"),
        "narrative_only_allowed": output.get("narrative_only_allowed"),
        "postmortem_draft_created": output.get("postmortem_draft_created"),
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
