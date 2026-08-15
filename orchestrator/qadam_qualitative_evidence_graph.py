"""Map grounded qualitative claims into Qadam's canonical temporal graph."""

from __future__ import annotations

from collections import Counter
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_qualitative_common import (
    EXTERNAL_DOCUMENTS_ARTIFACT,
    QUALITATIVE_CLAIMS_ARTIFACT,
    QUALITATIVE_ENTITY_MAPPINGS_ARTIFACT,
    QUALITATIVE_GRAPH_SUMMARY_ARTIFACT,
    QUALITATIVE_INSTRUMENT_MAPPINGS_ARTIFACT,
    now_iso,
    public_authority,
    read_jsonl,
    runtime_dir,
    stable_id,
    unique,
)
from orchestrator.qadam_temporal_graph_contracts import build_edge, build_node
from orchestrator.qadam_temporal_graph_store import TemporalGraphStore, validate_store

ORIGIN_ENTITIES = {
    "sec_nvda_submissions": ("NVIDIA", "company"),
    "sec_lmt_submissions": ("Lockheed Martin", "company"),
    "federal_reserve_press": ("Federal Reserve", "institution"),
    "eia_today_in_energy": ("US Energy Information Administration", "institution"),
    "qiskit_releases": ("IBM Qiskit", "technology_project"),
}


def build_qualitative_evidence_graph(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    documents = {str(row.get("document_id")): row for row in read_jsonl(runtime / EXTERNAL_DOCUMENTS_ARTIFACT)}
    claims = read_jsonl(runtime / QUALITATIVE_CLAIMS_ARTIFACT)
    records: list[dict[str, Any]] = []
    entity_mappings: list[dict[str, Any]] = []
    instrument_mappings: list[dict[str, Any]] = []
    errors: list[str] = []

    provider_nodes: dict[str, dict[str, Any]] = {}
    document_nodes: dict[str, dict[str, Any]] = {}
    entity_nodes: dict[str, dict[str, Any]] = {}
    instrument_nodes: dict[str, dict[str, Any]] = {}
    strategy_nodes: dict[str, dict[str, Any]] = {}

    for document in documents.values():
        origin_id = str(document.get("origin_id") or "unknown")
        provider_nodes.setdefault(
            origin_id,
            build_node(
                "source_provider",
                origin_id,
                layer="observed",
                evidence_state="provider_backed",
                available_at=document.get("availability_time"),
                source_artifact=EXTERNAL_DOCUMENTS_ARTIFACT,
                payload={
                    "origin_id": origin_id,
                    "trust_tier": document.get("trust_tier"),
                    "independence_cluster": document.get("independence_cluster"),
                    "source_quorum_credit_allowed": False,
                },
            ),
        )
        document_id = str(document.get("document_id"))
        document_nodes[document_id] = build_node(
            "reference_document",
            document_id,
            layer="observed",
            evidence_state="provider_backed" if document.get("research_eligible") else "metadata_only",
            available_at=document.get("availability_time"),
            source_artifact=EXTERNAL_DOCUMENTS_ARTIFACT,
            payload={
                "document_id": document_id,
                "origin_id": origin_id,
                "title": document.get("title"),
                "canonical_url": document.get("canonical_url"),
                "normalized_text_hash": document.get("normalized_text_hash"),
                "independence_cluster": document.get("independence_cluster"),
                "research_eligible": document.get("research_eligible"),
            },
        )
        records.append(
            build_edge(
                "published_by",
                document_nodes[document_id]["node_id"],
                provider_nodes[origin_id]["node_id"],
                layer="observed",
                evidence_state="provider_backed",
                available_at=document.get("availability_time"),
                source_artifact=EXTERNAL_DOCUMENTS_ARTIFACT,
                payload={"independence_cluster": document.get("independence_cluster")},
            )
        )

    for claim in claims:
        claim_id = str(claim.get("claim_id") or "")
        document_id = str(claim.get("document_id") or "")
        document = documents.get(document_id, {})
        if not claim_id or document_id not in document_nodes:
            errors.append(f"claim_document_lineage_missing:{claim_id or 'unknown'}")
            continue
        claim_node = build_node(
            "external_claim",
            claim_id,
            layer="observed",
            evidence_state="provider_backed",
            available_at=claim.get("availability_time"),
            source_artifact=QUALITATIVE_CLAIMS_ARTIFACT,
            payload={
                "claim_id": claim_id,
                "claim_type": claim.get("claim_type"),
                "direction": claim.get("direction"),
                "document_id": document_id,
                "supporting_span": claim.get("supporting_span"),
                "independence_cluster": claim.get("independence_cluster"),
            },
        )
        records.append(claim_node)
        records.append(
            build_edge(
                "derived_from",
                claim_node["node_id"],
                document_nodes[document_id]["node_id"],
                layer="observed",
                evidence_state="provider_backed",
                available_at=claim.get("availability_time"),
                source_artifact=QUALITATIVE_CLAIMS_ARTIFACT,
                payload={"span_grounded": True},
            )
        )
        origin_id = str(document.get("origin_id") or "")
        entity_name, entity_kind = ORIGIN_ENTITIES.get(origin_id, (origin_id or "Unknown origin", "origin"))
        entity_nodes.setdefault(
            entity_name,
            build_node(
                "entity",
                entity_name,
                layer="observed",
                evidence_state="provider_backed",
                available_at=claim.get("availability_time"),
                source_artifact=QUALITATIVE_CLAIMS_ARTIFACT,
                payload={"name": entity_name, "entity_kind": entity_kind},
            ),
        )
        records.append(
            build_edge(
                "mentions",
                claim_node["node_id"],
                entity_nodes[entity_name]["node_id"],
                layer="observed",
                evidence_state="provider_backed",
                available_at=claim.get("availability_time"),
                source_artifact=QUALITATIVE_CLAIMS_ARTIFACT,
            )
        )
        entity_mappings.append({
            "mapping_id": stable_id("entity-mapping", claim_id, entity_name),
            "claim_id": claim_id,
            "entity": entity_name,
            "entity_kind": entity_kind,
            "mapping_state": "observed_origin_identity",
            "authority": public_authority(),
        })
        for symbol in unique(claim.get("instrument_hypotheses") or []):
            instrument_nodes.setdefault(
                symbol,
                build_node(
                    "instrument",
                    symbol,
                    layer="inferred",
                    evidence_state="research_only",
                    available_at=claim.get("availability_time"),
                    source_artifact=QUALITATIVE_CLAIMS_ARTIFACT,
                    payload={"symbol": symbol, "mapping_role": "research_hypothesis"},
                ),
            )
            records.append(
                build_edge(
                    "affects",
                    claim_node["node_id"],
                    instrument_nodes[symbol]["node_id"],
                    layer="inferred",
                    evidence_state="research_only",
                    available_at=claim.get("availability_time"),
                    source_artifact=QUALITATIVE_CLAIMS_ARTIFACT,
                    payload={"mapping_state": "hypothesized_not_validated"},
                )
            )
            instrument_mappings.append({
                "mapping_id": stable_id("instrument-mapping", claim_id, symbol),
                "claim_id": claim_id,
                "instrument_symbol": symbol,
                "mapping_state": "hypothesized_not_validated",
                "point_in_time_constituent_required": symbol in {"SMH", "SOXX", "ITA", "XAR", "PPA"},
                "paper_candidate_allowed": False,
                "authority": public_authority(),
            })
        for strategy_id in unique(claim.get("strategy_family_hypotheses") or []):
            strategy_nodes.setdefault(
                strategy_id,
                build_node(
                    "strategy_family",
                    strategy_id,
                    layer="governed",
                    evidence_state="governed_projection",
                    available_at=claim.get("availability_time"),
                    source_artifact=QUALITATIVE_CLAIMS_ARTIFACT,
                    payload={"strategy_family_id": strategy_id, "existing_family": True},
                ),
            )
            records.append(
                build_edge(
                    "maps_to_strategy",
                    claim_node["node_id"],
                    strategy_nodes[strategy_id]["node_id"],
                    layer="inferred",
                    evidence_state="research_only",
                    available_at=claim.get("availability_time"),
                    source_artifact=QUALITATIVE_CLAIMS_ARTIFACT,
                    payload={"mapping_state": "research_hypothesis"},
                )
            )

    nodes = [*provider_nodes.values(), *document_nodes.values(), *entity_nodes.values(), *instrument_nodes.values(), *strategy_nodes.values()]
    all_records = [*nodes, *records]
    store = TemporalGraphStore(settings)
    append_result = store.append(all_records) if all_records else {"written": 0, "duplicates": 0}
    try:
        graph_manifest = store.rebuild()
        errors.extend(validate_store(settings))
    except (RuntimeError, ValueError) as exc:
        graph_manifest = {}
        errors.append(f"temporal_graph_rebuild_failed:{type(exc).__name__}:{exc}")
    artifact_store = AtomicArtifactStore(runtime)
    artifact_store.write_jsonl(QUALITATIVE_ENTITY_MAPPINGS_ARTIFACT, entity_mappings)
    artifact_store.write_jsonl(QUALITATIVE_INSTRUMENT_MAPPINGS_ARTIFACT, instrument_mappings)
    summary = {
        "schema_version": "qadam_qualitative_graph_summary.v1",
        "artifact_type": "qadam_qualitative_graph_summary",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "claim_count": len(claims),
        "mapped_claim_count": len({str(row.get('claim_id')) for row in instrument_mappings}),
        "entity_mapping_count": len(entity_mappings),
        "instrument_mapping_count": len(instrument_mappings),
        "independence_cluster_count": len({str(row.get('independence_cluster')) for row in claims}),
        "append_result": append_result,
        "canonical_graph_generation_id": graph_manifest.get("generation_id"),
        "record_type_counts": dict(sorted(Counter(str(row.get("node_type") or row.get("edge_type")) for row in all_records).items())),
        "inferred_edges_receive_observed_authority": False,
        "unmapped_claim_count": max(0, len(claims) - len({str(row.get('claim_id')) for row in instrument_mappings})),
        "validation_errors": unique(errors),
        "authority": public_authority(),
    }
    artifact_store.write_json(QUALITATIVE_GRAPH_SUMMARY_ARTIFACT, summary)
    return summary, unique(errors)


__all__ = ["build_qualitative_evidence_graph"]
