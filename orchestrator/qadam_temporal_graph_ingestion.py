"""QEG-4 adapters from Qadam's canonical source and instrument universes."""

from __future__ import annotations

from collections import Counter
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import now_iso, read_json, runtime_dir, write_json_atomic
from orchestrator.qadam_qeg_common import qeg_authority, stable_id, write_phase_status
from orchestrator.qadam_temporal_graph_contracts import build_edge, build_node
from orchestrator.qadam_temporal_graph_store import TemporalGraphStore

INGESTION_SUMMARY_ARTIFACT = "qadam_temporal_graph_ingestion_summary.json"


def _source_identity(row: dict[str, Any], index: int) -> str:
    return str(row.get("source_key") or row.get("key") or row.get("source_id") or row.get("name") or f"source-{index}")


def _instrument_identity(row: dict[str, Any], index: int) -> str:
    return str(row.get("symbol") or row.get("instrument") or row.get("market_id") or f"instrument-{index}")


def ingest_canonical_universes(settings: Settings | None = None) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    source_payload = read_json(runtime / "qsase_source_universe.json")
    trading_payload = read_json(runtime / "qsase_trading_universe.json")
    sources = source_payload.get("sources") if isinstance(source_payload.get("sources"), list) else []
    instruments = trading_payload.get("instruments") if isinstance(trading_payload.get("instruments"), list) else []
    errors: list[str] = []
    if not sources:
        errors.append("canonical_source_universe_empty")
    if not instruments:
        errors.append("canonical_trading_universe_empty")
    records: list[dict[str, Any]] = []
    source_nodes: dict[str, dict[str, Any]] = {}
    instrument_nodes: dict[str, dict[str, Any]] = {}
    for index, source in enumerate(sources):
        identity = _source_identity(source, index)
        state = str(source.get("state") or source.get("adapter_status") or "unknown")
        provider_backed = state.lower() in {"online", "connected", "ok", "fresh"} and bool(
            source.get("observed_timestamp") or source.get("available_at")
        )
        node = build_node(
            "source_feed", identity, layer="observed", evidence_state="metadata_only",
            payload={
                "source_key": identity,
                "label": source.get("label") or source.get("name") or identity,
                "source_family": source.get("source_family") or source.get("category"),
                "state": state,
                "freshness_state": source.get("freshness_state"),
                "source_quorum_contribution": source.get("source_quorum_contribution"),
                "independence_cluster_id": source.get("independence_cluster_id"),
                "historical_state": source.get("historical_state") or source.get("historical_coverage_state"),
                "metadata_only": True,
                "provider_backed_observation_present": provider_backed,
            },
            available_at=source.get("available_at") or source.get("observed_timestamp") or source_payload.get("generated_at"),
            source_artifact="data/runtime/qsase_source_universe.json",
        )
        source_nodes[identity] = node
        records.append(node)
        if provider_backed:
            observation = build_node(
                "source_observation", f"{identity}:{source.get('observed_timestamp') or source.get('available_at')}",
                layer="observed", evidence_state="provider_backed",
                payload={
                    "source_key": identity,
                    "observation_state": state,
                    "provider_backed": True,
                    "sample_or_fixture": False,
                },
                available_at=source.get("available_at") or source.get("observed_timestamp"),
                source_artifact="data/runtime/qsase_source_universe.json",
            )
            records.extend(
                [
                    observation,
                    build_edge(
                        "reported_by", observation["node_id"], node["node_id"], layer="observed",
                        evidence_state="provider_backed", payload={},
                        available_at=observation["available_at"],
                        source_artifact="data/runtime/qsase_source_universe.json",
                    ),
                ]
            )
    for index, instrument in enumerate(instruments):
        identity = _instrument_identity(instrument, index)
        node_type = "prediction_contract" if ":" in identity else "instrument"
        node = build_node(
            node_type, identity, layer="observed", evidence_state="metadata_only",
            payload={
                "symbol": identity,
                "label": instrument.get("label") or instrument.get("name") or identity,
                "market_family": instrument.get("market_family") or instrument.get("category"),
                "paper_route_available": instrument.get("paper_route_available") or instrument.get("paperability"),
                "price_history_state": instrument.get("price_history_state") or instrument.get("history_state"),
                "proxy_for": instrument.get("proxy_for"),
                "core_universe": True,
            },
            available_at=trading_payload.get("generated_at"),
            source_artifact="data/runtime/qsase_trading_universe.json",
        )
        instrument_nodes[identity] = node
        records.append(node)
    store = TemporalGraphStore(settings)
    append = store.append(records) if records else {"written": 0, "duplicates": 0}
    manifest = store.rebuild()
    family_counts = Counter(
        str(source.get("source_family") or source.get("category") or "unknown") for source in sources
    )
    summary = {
        "schema_version": "qadam_temporal_graph_ingestion.v1",
        "artifact_type": "qadam_temporal_graph_ingestion_summary",
        "generated_at": now_iso(),
        "status": "complete" if not errors else "blocked",
        "source_identity_count": len(source_nodes),
        "instrument_identity_count": len(instrument_nodes),
        "source_family_counts": dict(sorted(family_counts.items())),
        "provider_backed_observation_count": sum(
            1 for row in records if row.get("node_type") == "source_observation"
        ),
        "graph_records_written": append["written"],
        "graph_duplicate_records": append["duplicates"],
        "graph_generation_id": manifest.get("generation_id"),
        "unavailable_sources_fabricated_as_history": 0,
        "core_universe_modified": False,
        "power_sleeve_state": "separate_additive_sleeve",
        "authority": qeg_authority(),
        "blockers": errors,
    }
    write_json_atomic(runtime / INGESTION_SUMMARY_ARTIFACT, summary)
    write_phase_status(
        "QEG-4", status="passed" if not errors else "blocked",
        implementation_complete=not errors, empirical_state="canonical_universe_graph_materialized",
        artifacts=[INGESTION_SUMMARY_ARTIFACT, "qadam_temporal_graph_manifest.json"], blockers=errors,
        settings=settings,
    )
    return summary, errors
