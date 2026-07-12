"""Stable hybrid candidate identity and provenance for Quantum Edge Wave E."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Iterable

from orchestrator.qadam_discovery_backend import (
    ClassicalDiscoveryResult,
    QuantumDiscoveryBackendResult,
    validate_discovery_result,
    validate_research_candidate,
)
from orchestrator.qadam_fire_opal_ibm_discovery import validate_hardware_receipt
from orchestrator.qadam_quantum_discovery_evidence import stable_hash
from orchestrator.qadam_quantum_edge_governance import ZERO_AUTHORITY_FIELDS

IDENTITY_SCHEMA_VERSION = "qadam.HybridCandidateIdentity.v1"
EVIDENCE_SCHEMA_VERSION = "qadam.HybridCandidateEvidence.v1"
CANDIDATE_SCHEMA_VERSION = "qadam.HybridResearchCandidate.v1"
MERGE_SCHEMA_VERSION = "qadam.HybridCandidateMerge.v1"
REJECTION_SCHEMA_VERSION = "qadam.HybridCandidateRejection.v1"
PROVENANCE_SCHEMA_VERSION = "qadam.HybridCandidateProvenance.v1"
STATE_SCHEMA_VERSION = "qadam.HybridCandidateState.v1"

CANDIDATE_ARTIFACT = "qadam_hybrid_candidates.jsonl"
MERGE_ARTIFACT = "qadam_hybrid_candidate_merges.jsonl"
REJECTION_ARTIFACT = "qadam_hybrid_candidate_rejections.jsonl"
PROVENANCE_ARTIFACT = "qadam_hybrid_candidate_provenance.jsonl"
SUMMARY_ARTIFACT = "qadam_hybrid_candidate_summary.json"

WAVE_E_ZERO_AUTHORITY_FIELDS = (
    *ZERO_AUTHORITY_FIELDS,
    "candidate_promotion_allowed",
    "evaluation_verdict_authority",
    "hardware_submission_allowed",
    "hardware_scheduler_enabled",
)

FORBIDDEN_PUBLIC_KEYS = {
    "action_id",
    "api_key",
    "backend_name",
    "credentials",
    "password",
    "provider_job_ids",
    "qasm_circuits",
    "raw_provider_response",
    "secret",
    "token",
}


def _authority() -> dict[str, bool]:
    return {
        "research_candidate_creation_allowed": False,
        "quantum_research_candidate_allowed": False,
        **{field_name: False for field_name in WAVE_E_ZERO_AUTHORITY_FIELDS},
    }


def _contains_forbidden_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in FORBIDDEN_PUBLIC_KEYS:
                return True
            if _contains_forbidden_key(child):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_forbidden_key(child) for child in value)
    return False


def _validate_timestamp(value: str, *, field_name: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ValueError(f"{field_name}_invalid") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field_name}_timezone_missing")


def _normalized_text(value: str) -> str:
    normalized = "_".join(value.strip().lower().replace("/", " ").split())
    if not normalized:
        raise ValueError("hybrid_candidate_identity_text_missing")
    return normalized


@dataclass(frozen=True, kw_only=True)
class HybridMergeContext:
    source_transform_key: str
    feature_pair: tuple[str, str]
    economic_target: str
    outcome_definition: str
    relationship_key: str
    direction_or_question: str
    horizon: str
    regime: str
    accepted_instruments: tuple[str, ...]
    relationship: str
    interpretation: str
    confirmation: str
    falsifier: str
    blocker: str
    next_action: str

    def identity_material(self) -> dict[str, Any]:
        if len(self.feature_pair) != 2 or self.feature_pair[0] == self.feature_pair[1]:
            raise ValueError("hybrid_candidate_context_feature_pair_invalid")
        if not self.accepted_instruments:
            raise ValueError("hybrid_candidate_context_instruments_missing")
        for field_name in (
            "relationship",
            "interpretation",
            "confirmation",
            "falsifier",
            "blocker",
            "next_action",
        ):
            if not str(getattr(self, field_name) or "").strip():
                raise ValueError(f"hybrid_candidate_context_missing:{field_name}")
        return {
            "schema_version": IDENTITY_SCHEMA_VERSION,
            "source_transform_key": _normalized_text(self.source_transform_key),
            "feature_pair": sorted(_normalized_text(value) for value in self.feature_pair),
            "economic_target": _normalized_text(self.economic_target),
            "outcome_definition": _normalized_text(self.outcome_definition),
            "relationship_key": _normalized_text(self.relationship_key),
            "direction_or_question": _normalized_text(self.direction_or_question),
            "horizon": _normalized_text(self.horizon),
            "regime": _normalized_text(self.regime),
        }

    @property
    def candidate_id(self) -> str:
        return f"hybrid-candidate:{stable_hash(self.identity_material())[:24]}"


def _result_payload(
    result: ClassicalDiscoveryResult | QuantumDiscoveryBackendResult | dict[str, Any],
) -> dict[str, Any]:
    payload = result.to_dict() if hasattr(result, "to_dict") else result
    if not isinstance(payload, dict):
        raise ValueError("hybrid_discovery_result_not_object")
    errors = validate_discovery_result(payload)
    if errors:
        raise ValueError(f"hybrid_discovery_result_invalid:{','.join(errors)}")
    return payload


def discovery_evidence_records(
    result: ClassicalDiscoveryResult | QuantumDiscoveryBackendResult | dict[str, Any],
) -> list[dict[str, Any]]:
    payload = _result_payload(result)
    origin = str(payload.get("discovery_origin") or "")
    if origin not in {"classical_discovery", "quantum_assisted_discovery"}:
        raise ValueError("hybrid_discovery_origin_invalid")
    records: list[dict[str, Any]] = []
    for candidate in payload.get("research_candidates", ()):
        errors = validate_research_candidate(candidate)
        if errors:
            raise ValueError(f"hybrid_candidate_invalid:{','.join(errors)}")
        material = {
            "source_result_id": payload["result_id"],
            "source_candidate_id": candidate["candidate_id"],
            "shared_manifest_hash": payload["shared_manifest_hash"],
            "discovery_origin": origin,
            "validation_contribution": "not_tested",
            "method": candidate["method"],
            "feature_pair": sorted(candidate["feature_pair"]),
            "structural_score": candidate["structural_score"],
            "market_sleeve": candidate["market_sleeve"],
            "observed_instrument": candidate["target_instrument"],
            "research_question": candidate["research_question"],
            "policy_hash": payload["policy_hash"],
            "execution_mode": payload["execution_mode"],
            "quantum_simulation_completed": payload.get("quantum_simulation_completed")
            is True,
            "hardware_experiment_completed": False,
            "hardware_receipt_hash": None,
            "provider": None,
            "contract_fixture_only": payload.get("contract_fixture_only") is True,
        }
        evidence_hash = stable_hash(material)
        records.append(
            {
                "schema_version": EVIDENCE_SCHEMA_VERSION,
                "evidence_id": f"hybrid-evidence:{evidence_hash[:24]}",
                "evidence_hash": evidence_hash,
                **material,
                "validated_edge_created": False,
                "strategy_hypothesis_created": False,
                "trade_candidate_created": False,
                "paper_order_created": False,
                "proof_eligible": False,
                "authority": _authority(),
            }
        )
    return records


def hardware_evidence_records(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    validate_hardware_receipt(receipt)
    records: list[dict[str, Any]] = []
    for candidate in receipt.get("research_candidates", ()):
        errors = validate_research_candidate(candidate)
        if errors:
            raise ValueError(f"hybrid_hardware_candidate_invalid:{','.join(errors)}")
        material = {
            "source_result_id": receipt["receipt_id"],
            "source_candidate_id": candidate["candidate_id"],
            "shared_manifest_hash": receipt["shared_manifest_hash"],
            "discovery_origin": "quantum_assisted_discovery",
            "validation_contribution": "not_tested",
            "method": candidate["method"],
            "feature_pair": sorted(candidate["feature_pair"]),
            "structural_score": candidate["structural_score"],
            "market_sleeve": candidate["market_sleeve"],
            "observed_instrument": candidate["target_instrument"],
            "research_question": candidate["research_question"],
            "policy_hash": receipt["local_quantum_policy_hash"],
            "execution_mode": receipt["execution_mode"],
            "quantum_simulation_completed": False,
            "hardware_experiment_completed": True,
            "hardware_receipt_hash": receipt["receipt_hash"],
            "provider": receipt["provider"],
            "contract_fixture_only": receipt.get("contract_fixture_only") is True,
        }
        evidence_hash = stable_hash(material)
        records.append(
            {
                "schema_version": EVIDENCE_SCHEMA_VERSION,
                "evidence_id": f"hybrid-evidence:{evidence_hash[:24]}",
                "evidence_hash": evidence_hash,
                **material,
                "validated_edge_created": False,
                "strategy_hypothesis_created": False,
                "trade_candidate_created": False,
                "paper_order_created": False,
                "proof_eligible": False,
                "authority": _authority(),
            }
        )
    return records


def validate_hybrid_evidence(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
        errors.append("evidence_schema_invalid")
    material = {
        key: record.get(key)
        for key in (
            "source_result_id",
            "source_candidate_id",
            "shared_manifest_hash",
            "discovery_origin",
            "validation_contribution",
            "method",
            "feature_pair",
            "structural_score",
            "market_sleeve",
            "observed_instrument",
            "research_question",
            "policy_hash",
            "execution_mode",
            "quantum_simulation_completed",
            "hardware_experiment_completed",
            "hardware_receipt_hash",
            "provider",
            "contract_fixture_only",
        )
    }
    expected_hash = stable_hash(material)
    if record.get("evidence_hash") != expected_hash:
        errors.append("evidence_hash_mismatch")
    if record.get("evidence_id") != f"hybrid-evidence:{expected_hash[:24]}":
        errors.append("evidence_id_mismatch")
    if record.get("validation_contribution") != "not_tested":
        errors.append("evidence_self_validation_attempted")
    if record.get("hardware_experiment_completed") is True and not record.get(
        "hardware_receipt_hash"
    ):
        errors.append("evidence_hardware_receipt_missing")
    for key in (
        "validated_edge_created",
        "strategy_hypothesis_created",
        "trade_candidate_created",
        "paper_order_created",
        "proof_eligible",
    ):
        if record.get(key) is not False:
            errors.append(f"evidence_downstream_state:{key}")
    for key in WAVE_E_ZERO_AUTHORITY_FIELDS:
        if record.get("authority", {}).get(key) is not False:
            errors.append(f"evidence_authority_escalated:{key}")
    if _contains_forbidden_key(record):
        errors.append("evidence_forbidden_public_key")
    return sorted(set(errors))


def _context_match(context: HybridMergeContext, evidence: dict[str, Any]) -> bool:
    expected_pair = sorted(_normalized_text(value) for value in context.feature_pair)
    actual_pair = sorted(
        _normalized_text(str(value)) for value in evidence.get("feature_pair", ())
    )
    accepted_instruments = {
        _normalized_text(instrument) for instrument in context.accepted_instruments
    }
    observed_instrument = _normalized_text(str(evidence.get("observed_instrument")))
    return actual_pair == expected_pair and observed_instrument in accepted_instruments


def merge_hybrid_candidates(
    contexts: Iterable[HybridMergeContext],
    evidence_records: Iterable[dict[str, Any]],
    *,
    generated_at: str,
) -> dict[str, Any]:
    _validate_timestamp(generated_at, field_name="hybrid_merge_generated_at")
    context_rows = list(contexts)
    supplied_evidence_rows = list(evidence_records)
    if len({context.candidate_id for context in context_rows}) != len(context_rows):
        raise ValueError("hybrid_merge_context_identity_collision")
    for evidence in supplied_evidence_rows:
        errors = validate_hybrid_evidence(evidence)
        if errors:
            raise ValueError(f"hybrid_evidence_invalid:{','.join(errors)}")
    evidence_rows = list(
        {row["evidence_id"]: row for row in supplied_evidence_rows}.values()
    )

    grouped: dict[str, list[dict[str, Any]]] = {
        context.candidate_id: [] for context in context_rows
    }
    rejections: list[dict[str, Any]] = []
    for evidence in evidence_rows:
        matches = [context for context in context_rows if _context_match(context, evidence)]
        if len(matches) == 1:
            grouped[matches[0].candidate_id].append(evidence)
            continue
        reason = "no_identity_context_match" if not matches else "ambiguous_identity_context_match"
        rejection_material = {
            "evidence_id": evidence["evidence_id"],
            "reason": reason,
            "matched_context_count": len(matches),
        }
        rejection_hash = stable_hash(rejection_material)
        rejections.append(
            {
                "schema_version": REJECTION_SCHEMA_VERSION,
                "rejection_id": f"hybrid-rejection:{rejection_hash[:24]}",
                **rejection_material,
                "generated_at": generated_at,
                "authority": _authority(),
            }
        )

    candidates: list[dict[str, Any]] = []
    merges: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    for context in context_rows:
        rows = sorted(
            {row["evidence_id"]: row for row in grouped[context.candidate_id]}.values(),
            key=lambda row: row["evidence_id"],
        )
        if not rows:
            continue
        origins = sorted({str(row["discovery_origin"]) for row in rows})
        discovery_origin = "joint_discovery" if len(origins) > 1 else origins[0]
        empirical_count = sum(not row["contract_fixture_only"] for row in rows)
        hardware_count = sum(row["hardware_experiment_completed"] for row in rows)
        simulation_count = sum(row["quantum_simulation_completed"] for row in rows)
        manifests = sorted({str(row["shared_manifest_hash"]) for row in rows})
        observed_instruments = sorted({str(row["observed_instrument"]) for row in rows})
        candidate = {
            "schema_version": CANDIDATE_SCHEMA_VERSION,
            "candidate_id": context.candidate_id,
            "identity": context.identity_material(),
            "identity_hash": stable_hash(context.identity_material()),
            "discovery_origin": discovery_origin,
            "discovery_origins": origins,
            "validation_contribution": "not_tested",
            "lifecycle_state": "candidate_relationship",
            "market": context.economic_target,
            "economic_target": context.economic_target,
            "outcome_definition": context.outcome_definition,
            "observed_instruments": observed_instruments,
            "source_chain": {
                "source_transform_key": context.source_transform_key,
                "feature_pair": sorted(context.feature_pair),
                "shared_manifest_hashes": manifests,
                "evidence_ids": [row["evidence_id"] for row in rows],
            },
            "relationship": context.relationship,
            "interpretation": context.interpretation,
            "confirmation": context.confirmation,
            "falsifier": context.falsifier,
            "blocker": context.blocker,
            "next_action": context.next_action,
            "evidence_state": "fixture_only" if empirical_count == 0 else "empirical_unvalidated",
            "evidence_record_count": len(rows),
            "empirical_evidence_count": empirical_count,
            "quantum_simulation_evidence_count": simulation_count,
            "hardware_evidence_count": hardware_count,
            "evidence_records": rows,
            "contract_fixture_only": empirical_count == 0,
            "candidate_persistence_allowed": empirical_count > 0,
            "validated_edge_created": False,
            "strategy_hypothesis_created": False,
            "trade_candidate_created": False,
            "risk_approval_created": False,
            "execution_approval_created": False,
            "paper_order_created": False,
            "proof_eligible": False,
            "generated_at": generated_at,
            "authority": _authority(),
        }
        candidate_hash = stable_hash(
            {
                key: value
                for key, value in candidate.items()
                if key not in {"generated_at", "candidate_hash"}
            }
        )
        candidate["candidate_hash"] = candidate_hash
        candidates.append(candidate)

        merge_material = {
            "candidate_id": context.candidate_id,
            "evidence_ids": [row["evidence_id"] for row in rows],
            "discovery_origins": origins,
            "merge_action": "joint_candidate_created" if len(origins) > 1 else "single_lane_candidate_created",
        }
        merge_hash = stable_hash(merge_material)
        merges.append(
            {
                "schema_version": MERGE_SCHEMA_VERSION,
                "merge_id": f"hybrid-merge:{merge_hash[:24]}",
                **merge_material,
                "automatic_promotion_created": False,
                "generated_at": generated_at,
                "authority": _authority(),
            }
        )
        for row in rows:
            provenance_material = {
                "candidate_id": context.candidate_id,
                "evidence_id": row["evidence_id"],
                "source_result_id": row["source_result_id"],
                "source_candidate_id": row["source_candidate_id"],
                "discovery_origin": row["discovery_origin"],
                "validation_contribution": "not_tested",
            }
            provenance_hash = stable_hash(provenance_material)
            provenance.append(
                {
                    "schema_version": PROVENANCE_SCHEMA_VERSION,
                    "provenance_id": f"hybrid-provenance:{provenance_hash[:24]}",
                    **provenance_material,
                    "generated_at": generated_at,
                    "authority": _authority(),
                }
            )

    summary = {
        "schema_version": STATE_SCHEMA_VERSION,
        "status": "hybrid_candidates_ready" if candidates else "no_hybrid_candidates",
        "generated_at": generated_at,
        "candidate_count": len(candidates),
        "joint_candidate_count": sum(
            candidate["discovery_origin"] == "joint_discovery" for candidate in candidates
        ),
        "classical_candidate_count": sum(
            candidate["discovery_origin"] == "classical_discovery" for candidate in candidates
        ),
        "quantum_candidate_count": sum(
            candidate["discovery_origin"] == "quantum_assisted_discovery"
            for candidate in candidates
        ),
        "empirical_candidate_count": sum(
            candidate["empirical_evidence_count"] > 0 for candidate in candidates
        ),
        "hardware_evidence_count": sum(
            candidate["hardware_evidence_count"] for candidate in candidates
        ),
        "merge_count": len(merges),
        "rejection_count": len(rejections),
        "provenance_count": len(provenance),
        "validated_edge_count": 0,
        "strategy_hypothesis_count": 0,
        "trade_candidate_count": 0,
        "paper_order_count": 0,
        "authority": _authority(),
    }
    state = {
        "schema_version": STATE_SCHEMA_VERSION,
        "candidates": candidates,
        "merges": merges,
        "rejections": rejections,
        "provenance": provenance,
        "summary": summary,
    }
    validate_hybrid_candidate_state(state)
    return state


def validate_hybrid_candidate_state(state: dict[str, Any]) -> None:
    if state.get("schema_version") != STATE_SCHEMA_VERSION:
        raise ValueError("hybrid_candidate_state_schema_invalid")
    candidates = state.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("hybrid_candidates_invalid")
    candidate_ids: set[str] = set()
    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_id") or "")
        if not candidate_id or candidate_id in candidate_ids:
            raise ValueError("hybrid_candidate_identity_duplicate")
        candidate_ids.add(candidate_id)
        identity = candidate.get("identity")
        if not isinstance(identity, dict):
            raise ValueError("hybrid_candidate_identity_invalid")
        identity_hash = stable_hash(identity)
        if candidate.get("identity_hash") != identity_hash:
            raise ValueError("hybrid_candidate_identity_hash_mismatch")
        if candidate_id != f"hybrid-candidate:{identity_hash[:24]}":
            raise ValueError("hybrid_candidate_id_mismatch")
        if candidate.get("validation_contribution") != "not_tested":
            raise ValueError("hybrid_candidate_self_validation_attempted")
        if candidate.get("lifecycle_state") != "candidate_relationship":
            raise ValueError("hybrid_candidate_lifecycle_invalid")
        if candidate.get("contract_fixture_only") is True and candidate.get(
            "candidate_persistence_allowed"
        ) is not False:
            raise ValueError("hybrid_fixture_candidate_persistence_allowed")
        expected_hash = stable_hash(
            {
                key: value
                for key, value in candidate.items()
                if key not in {"generated_at", "candidate_hash"}
            }
        )
        if candidate.get("candidate_hash") != expected_hash:
            raise ValueError("hybrid_candidate_hash_mismatch")
        for evidence in candidate.get("evidence_records", ()):
            errors = validate_hybrid_evidence(evidence)
            if errors:
                raise ValueError(f"hybrid_candidate_evidence_invalid:{','.join(errors)}")
        evidence_records = candidate.get("evidence_records", [])
        if candidate.get("evidence_record_count") != len(evidence_records):
            raise ValueError("hybrid_candidate_evidence_count_mismatch")
        evidence_ids = [record.get("evidence_id") for record in evidence_records]
        if candidate.get("source_chain", {}).get("evidence_ids") != evidence_ids:
            raise ValueError("hybrid_candidate_source_chain_mismatch")
        discovery_origins = sorted(
            {str(record.get("discovery_origin")) for record in evidence_records}
        )
        if candidate.get("discovery_origins") != discovery_origins:
            raise ValueError("hybrid_candidate_origins_mismatch")
        expected_origin = (
            "joint_discovery" if len(discovery_origins) > 1 else discovery_origins[0]
        )
        if candidate.get("discovery_origin") != expected_origin:
            raise ValueError("hybrid_candidate_origin_mismatch")
        for key in (
            "validated_edge_created",
            "strategy_hypothesis_created",
            "trade_candidate_created",
            "risk_approval_created",
            "execution_approval_created",
            "paper_order_created",
            "proof_eligible",
        ):
            if candidate.get(key) is not False:
                raise ValueError(f"hybrid_candidate_downstream_state:{key}")
        for key in WAVE_E_ZERO_AUTHORITY_FIELDS:
            if candidate.get("authority", {}).get(key) is not False:
                raise ValueError(f"hybrid_candidate_authority_escalated:{key}")
        if any(value is not False for value in candidate.get("authority", {}).values()):
            raise ValueError("hybrid_candidate_unrecognized_authority")

    merges = state.get("merges")
    rejections = state.get("rejections")
    provenance = state.get("provenance")
    if not all(isinstance(rows, list) for rows in (merges, rejections, provenance)):
        raise ValueError("hybrid_candidate_ledgers_invalid")
    merge_ids: set[str] = set()
    for record in merges:
        material = {
            key: record.get(key)
            for key in (
                "candidate_id",
                "evidence_ids",
                "discovery_origins",
                "merge_action",
            )
        }
        expected_id = f"hybrid-merge:{stable_hash(material)[:24]}"
        if record.get("merge_id") != expected_id or expected_id in merge_ids:
            raise ValueError("hybrid_merge_identity_invalid")
        merge_ids.add(expected_id)
        if record.get("candidate_id") not in candidate_ids:
            raise ValueError("hybrid_merge_candidate_missing")
        if record.get("automatic_promotion_created") is not False:
            raise ValueError("hybrid_merge_automatic_promotion")
        if any(value is not False for value in record.get("authority", {}).values()):
            raise ValueError("hybrid_merge_authority_escalated")
    rejection_ids: set[str] = set()
    for record in rejections:
        material = {
            key: record.get(key)
            for key in ("evidence_id", "reason", "matched_context_count")
        }
        expected_id = f"hybrid-rejection:{stable_hash(material)[:24]}"
        if record.get("rejection_id") != expected_id or expected_id in rejection_ids:
            raise ValueError("hybrid_rejection_identity_invalid")
        rejection_ids.add(expected_id)
        if any(value is not False for value in record.get("authority", {}).values()):
            raise ValueError("hybrid_rejection_authority_escalated")
    provenance_ids: set[str] = set()
    for record in provenance:
        material = {
            key: record.get(key)
            for key in (
                "candidate_id",
                "evidence_id",
                "source_result_id",
                "source_candidate_id",
                "discovery_origin",
                "validation_contribution",
            )
        }
        expected_id = f"hybrid-provenance:{stable_hash(material)[:24]}"
        if record.get("provenance_id") != expected_id or expected_id in provenance_ids:
            raise ValueError("hybrid_provenance_identity_invalid")
        provenance_ids.add(expected_id)
        if record.get("candidate_id") not in candidate_ids:
            raise ValueError("hybrid_provenance_candidate_missing")
        if record.get("validation_contribution") != "not_tested":
            raise ValueError("hybrid_provenance_self_validation_attempted")
        if any(value is not False for value in record.get("authority", {}).values()):
            raise ValueError("hybrid_provenance_authority_escalated")
    summary = state.get("summary")
    if not isinstance(summary, dict) or summary.get("candidate_count") != len(candidates):
        raise ValueError("hybrid_candidate_summary_mismatch")
    expected_summary_counts = {
        "joint_candidate_count": sum(
            candidate["discovery_origin"] == "joint_discovery"
            for candidate in candidates
        ),
        "classical_candidate_count": sum(
            candidate["discovery_origin"] == "classical_discovery"
            for candidate in candidates
        ),
        "quantum_candidate_count": sum(
            candidate["discovery_origin"] == "quantum_assisted_discovery"
            for candidate in candidates
        ),
        "empirical_candidate_count": sum(
            candidate["empirical_evidence_count"] > 0 for candidate in candidates
        ),
        "hardware_evidence_count": sum(
            candidate["hardware_evidence_count"] for candidate in candidates
        ),
        "merge_count": len(merges),
        "rejection_count": len(rejections),
        "provenance_count": len(provenance),
    }
    if any(summary.get(key) != value for key, value in expected_summary_counts.items()):
        raise ValueError("hybrid_candidate_summary_ledger_mismatch")
    if any(
        summary.get(key) != 0
        for key in (
            "validated_edge_count",
            "strategy_hypothesis_count",
            "trade_candidate_count",
            "paper_order_count",
        )
    ):
        raise ValueError("hybrid_candidate_summary_promoted_state")
    if any(value is not False for value in summary.get("authority", {}).values()):
        raise ValueError("hybrid_candidate_summary_authority_escalated")
    if _contains_forbidden_key(state):
        raise ValueError("hybrid_candidate_state_forbidden_public_key")


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def write_hybrid_candidate_state(
    runtime_dir: str | Path,
    state: dict[str, Any],
) -> dict[str, Path]:
    validate_hybrid_candidate_state(state)
    root = Path(runtime_dir)
    outputs: dict[str, Path] = {}
    for key, filename in (
        ("candidates", CANDIDATE_ARTIFACT),
        ("merges", MERGE_ARTIFACT),
        ("rejections", REJECTION_ARTIFACT),
        ("provenance", PROVENANCE_ARTIFACT),
    ):
        path = root / filename
        rows = state[key]
        text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
        _atomic_write(path, text)
        outputs[key] = path
    summary_path = root / SUMMARY_ARTIFACT
    _atomic_write(
        summary_path,
        json.dumps(state["summary"], indent=2, sort_keys=True) + "\n",
    )
    outputs["summary"] = summary_path
    return outputs
