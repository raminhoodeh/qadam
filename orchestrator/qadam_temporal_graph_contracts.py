"""Typed temporal and authority contracts for Qadam's evidence graph."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from orchestrator.qadam_qeg_common import (
    SCHEMA_VERSION,
    parse_time,
    qeg_authority,
    record_hash,
    stable_id,
)

TRUST_LAYERS = {"observed", "inferred", "tested", "governed"}
NODE_TYPES = {
    "source_provider", "source_feed", "source_observation", "reference_document",
    "external_claim", "world_event", "entity", "country", "sector", "instrument",
    "execution_proxy", "prediction_contract", "market_regime", "feature",
    "pattern_relationship", "research_goal", "hypothesis", "experiment_definition",
    "experiment_result", "validated_edge", "strategy_family", "strategy_version",
    "shadow_decision", "akber_decision", "portfolio_risk_decision", "router_decision",
    "paperops_handoff", "paper_order", "paper_position", "paper_outcome", "postmortem",
    "improvement_proposal", "repair_request",
}
EDGE_TYPES = {
    "reported_by", "published_by", "mentions", "located_in", "affects", "exposed_to",
    "proxy_for", "corroborates", "contradicts", "precedes", "co_occurs_with",
    "derived_from", "supports", "weakens", "duplicates", "supersedes", "tested_by",
    "failed_in_regime", "succeeded_in_regime", "maps_to_strategy", "generated_strategy",
    "filtered_by", "held_by", "vetoed_by", "passed_by", "routed_to", "executed_as",
    "resulted_in", "attributed_to", "proposed_change_to", "informs_research_question",
}
CLAIM_STATES = {
    "unreviewed", "verified_current", "verified_historical", "partially_verified",
    "unverified", "contradicted", "superseded", "rejected", "out_of_scope",
}
EVIDENCE_STATES = {
    "metadata_only", "provider_backed", "provisional_inference", "research_only",
    "interesting_unvalidated", "historical_candidate", "historically_rejected",
    "holdout_failed", "cost_failed", "unstable", "forward_shadow_required",
    "forward_candidate", "validated_edge", "governed_projection",
}


def build_node(
    node_type: str,
    identity: str,
    *,
    layer: str,
    evidence_state: str,
    payload: dict[str, Any],
    available_at: str | None = None,
    source_artifact: str | None = None,
    generated_at: str | None = None,
    node_id: str | None = None,
) -> dict[str, Any]:
    if node_type not in NODE_TYPES:
        raise ValueError(f"unsupported_node_type:{node_type}")
    now = generated_at or datetime.now(timezone.utc).isoformat()
    node = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": "node",
        "node_id": node_id or stable_id(node_type, identity),
        "node_type": node_type,
        "identity": identity,
        "trust_layer": layer,
        "evidence_state": evidence_state,
        "generated_at": now,
        "available_at": available_at or now,
        "source_artifact": source_artifact,
        "payload": deepcopy(payload),
        "authority": qeg_authority(governed_projection=layer == "governed"),
    }
    node["record_hash"] = record_hash(node, omit=("record_hash",))
    return node


def build_edge(
    edge_type: str,
    from_node_id: str,
    to_node_id: str,
    *,
    layer: str,
    evidence_state: str,
    payload: dict[str, Any] | None = None,
    available_at: str | None = None,
    source_artifact: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    if edge_type not in EDGE_TYPES:
        raise ValueError(f"unsupported_edge_type:{edge_type}")
    now = generated_at or datetime.now(timezone.utc).isoformat()
    identity = f"{edge_type}|{from_node_id}|{to_node_id}|{record_hash(payload or {})}"
    edge = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": "edge",
        "edge_id": stable_id("edge", identity),
        "edge_type": edge_type,
        "from_node_id": from_node_id,
        "to_node_id": to_node_id,
        "trust_layer": layer,
        "evidence_state": evidence_state,
        "generated_at": now,
        "available_at": available_at or now,
        "source_artifact": source_artifact,
        "payload": deepcopy(payload or {}),
        "authority": qeg_authority(governed_projection=layer == "governed"),
    }
    edge["record_hash"] = record_hash(edge, omit=("record_hash",))
    return edge


def validate_record(record: dict[str, Any], *, query_cutoff: str | None = None) -> list[str]:
    errors: list[str] = []
    kind = record.get("record_kind")
    if kind not in {"node", "edge"}:
        errors.append("record_kind_invalid")
    if kind == "node" and record.get("node_type") not in NODE_TYPES:
        errors.append("node_type_invalid")
    if kind == "node" and not isinstance(record.get("node_id"), str):
        errors.append("node_id_missing_or_invalid")
    if kind == "edge" and record.get("edge_type") not in EDGE_TYPES:
        errors.append("edge_type_invalid")
    if kind == "edge" and (
        not isinstance(record.get("from_node_id"), str)
        or not isinstance(record.get("to_node_id"), str)
    ):
        errors.append("edge_endpoint_missing_or_invalid")
    if record.get("trust_layer") not in TRUST_LAYERS:
        errors.append("trust_layer_invalid")
    if record.get("evidence_state") not in EVIDENCE_STATES:
        errors.append("evidence_state_invalid")
    available = parse_time(record.get("available_at"))
    generated = parse_time(record.get("generated_at"))
    if available is None:
        errors.append("available_at_missing_or_invalid")
    if generated is None:
        errors.append("generated_at_missing_or_invalid")
    if query_cutoff:
        cutoff = parse_time(query_cutoff)
        if cutoff is None:
            errors.append("query_cutoff_invalid")
        elif available and available > cutoff:
            errors.append("future_information_visible_at_query_cutoff")
    authority = record.get("authority") if isinstance(record.get("authority"), dict) else {}
    for key in (
        "broker_write_allowed", "live_broker_endpoint_allowed", "live_capital_enabled",
        "proof_credit_allowed", "paper_order_allowed", "risk_approval_allowed",
        "execution_approval_allowed", "graph_can_create_trade_authority",
        "graph_can_create_strategy_authority", "automatic_code_mutation_allowed",
        "automatic_risk_envelope_expansion_allowed",
    ):
        if authority.get(key) is not False:
            errors.append(f"unsafe_authority:{key}")
    expected = record_hash(record, omit=("record_hash",))
    if record.get("record_hash") != expected:
        errors.append("record_hash_mismatch")
    return sorted(set(errors))


def validate_negative_probes() -> list[str]:
    base = build_node(
        "source_observation", "negative-probe", layer="observed",
        evidence_state="provider_backed", payload={"provider": "probe"},
    )
    failures: list[str] = []
    unsafe = deepcopy(base)
    unsafe["authority"]["broker_write_allowed"] = True
    unsafe["record_hash"] = record_hash(unsafe, omit=("record_hash",))
    if "unsafe_authority:broker_write_allowed" not in validate_record(unsafe):
        failures.append("unsafe_broker_authority_probe_not_rejected")
    future = deepcopy(base)
    future["available_at"] = "2099-01-01T00:00:00+00:00"
    future["record_hash"] = record_hash(future, omit=("record_hash",))
    if "future_information_visible_at_query_cutoff" not in validate_record(
        future, query_cutoff="2026-01-01T00:00:00+00:00"
    ):
        failures.append("future_information_probe_not_rejected")
    return failures
