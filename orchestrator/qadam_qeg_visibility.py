"""Public-safe QEG projections for the existing dashboard and Telegram boundary."""

from __future__ import annotations

from collections import Counter
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import (
    append_jsonl_durable,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_json,
    unique_errors,
    write_json_atomic,
)
from orchestrator.qadam_qeg_common import (
    ACTIONABILITY_QUEUE_ARTIFACT,
    ACTIVE_DISCOVERY_FUNNEL_ARTIFACT,
    CHALLENGER_TOURNAMENT_ARTIFACT,
    CLAIM_SUMMARY_ARTIFACT,
    EXPERIMENT_BRIDGE_ARTIFACT,
    EXPERIMENT_SUMMARY_ARTIFACT,
    GRAPH_HEALTH_ARTIFACT,
    GRAPH_MANIFEST_ARTIFACT,
    MULTI_SETUP_ARTIFACT,
    OUTCOME_LEARNING_ARTIFACT,
    PAPER_ADMISSION_ARTIFACT,
    PATTERN_CANDIDATES_ARTIFACT,
    QEG_DASHBOARD_ARTIFACT,
    QEG_RESOURCE_REGISTRY_ARTIFACT,
    QEG_TELEGRAM_ARTIFACT,
    QEG_TELEGRAM_DEDUPE_ARTIFACT,
    QUANTUM_CHALLENGER_ARTIFACT,
    REFERENCE_SUMMARY_ARTIFACT,
    STRATEGY_VERSIONS_ARTIFACT,
    freshness_label,
    qeg_authority,
    stable_id,
    write_phase_status,
)
from orchestrator.qadam_temporal_graph_store import TemporalGraphStore

SOURCE_UNIVERSE_ARTIFACT = "qsase_source_universe.json"
TRADING_UNIVERSE_ARTIFACT = "qsase_trading_universe.json"


def _rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    values = payload.get(key)
    return [row for row in values if isinstance(row, dict)] if isinstance(values, list) else []


def _source_projection(
    sources: list[dict[str, Any]], candidates: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    contributions: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        for source in candidate.get("source_path") or []:
            if isinstance(source, dict) and source.get("source_key"):
                contributions.setdefault(str(source["source_key"]), []).append(candidate)
    rows: list[dict[str, Any]] = []
    for source in sources:
        source_key = str(source.get("source_key") or "")
        linked = contributions.get(source_key, [])
        clusters = {
            str(item.get("independence_cluster_id") or "unknown")
            for candidate in linked
            for item in candidate.get("source_path") or []
            if isinstance(item, dict) and item.get("source_key") == source_key
        }
        rows.append(
            {
                "source_key": source_key,
                "source_name": source.get("source_name") or source_key,
                "source_family": source.get("source_family"),
                "provider_state": source.get("state") or source.get("adapter_status"),
                "freshness_state": source.get("freshness_status") or "unknown",
                "latest_observation_at": source.get("observed_timestamp") or source.get("provider_event_latest_at"),
                "provider_backed_observation": source.get("provider_backed_observation") is True,
                "verification_class": source.get("evidence_origin") or source.get("trust_posture") or "unverified",
                "trust_posture": source.get("trust_posture"),
                "quorum_contribution": (source.get("source_quorum_contribution") or {}).get("can_contribute") is True,
                "independence_clusters": sorted(clusters),
                "pattern_relationship_count": len(linked),
                "active_pattern_relationship_count": sum(row.get("current_trigger_active") is True for row in linked),
                "graph_contribution_state": "linked_to_current_research" if linked else "indexed_no_current_pattern_link",
                "trading_authority": False,
            }
        )
    return rows


def _instrument_projection(
    instruments: list[dict[str, Any]], candidates: list[dict[str, Any]], versions: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_symbol: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        by_symbol.setdefault(str(candidate.get("instrument") or ""), []).append(candidate)
    versions_by_symbol = Counter(str(row.get("instrument") or "") for row in versions)
    rows: list[dict[str, Any]] = []
    for instrument in instruments:
        symbol = str(instrument.get("symbol") or "")
        linked = by_symbol.get(symbol, [])
        rows.append(
            {
                "symbol": symbol,
                "display_name": instrument.get("display_name") or symbol,
                "market_family": instrument.get("market_family"),
                "entity_relationships": sorted(
                    {str(row.get("strategy_family_id")) for row in linked if row.get("strategy_family_id")}
                ),
                "pattern_relationship_count": len(linked),
                "active_pattern_relationship_count": sum(row.get("current_trigger_active") is True for row in linked),
                "strategy_version_count": versions_by_symbol[symbol],
                "price_data_state": instrument.get("price_data_state"),
                "market_observation_timestamp": instrument.get("market_observation_timestamp"),
                "paperability_state": instrument.get("paperability_state"),
                "paper_route_available": instrument.get("paper_route_available") is True,
                "route_fit": instrument.get("route_fit"),
                "proxy_relationship": {
                    "mapping_state": instrument.get("mapping_state"),
                    "basis_risk_explicit": instrument.get("route_fit") == "conditional_paper_proxy_fit",
                },
                "paper_order_allowed": False,
            }
        )
    return rows


def _pattern_projection(
    candidates: list[dict[str, Any]],
    queue_rows: list[dict[str, Any]],
    strategy_state: dict[str, Any],
    funnel: dict[str, Any],
) -> list[dict[str, Any]]:
    queue = {str(row.get("pattern_relationship_id")): row for row in queue_rows}
    versions = {
        str(row.get("pattern_relationship_id")): row
        for row in strategy_state.get("versions") or []
        if row.get("pattern_relationship_id")
    }
    rejections = {
        str(row.get("pattern_relationship_id")): row
        for row in strategy_state.get("rejections") or []
        if row.get("pattern_relationship_id")
    }
    evaluations = {
        str(row.get("pattern_relationship_id")): row
        for row in funnel.get("evaluations") or []
        if row.get("pattern_relationship_id")
    }
    projected: list[dict[str, Any]] = []
    for candidate in candidates:
        pattern_id = str(candidate.get("pattern_relationship_id") or "")
        queue_row = queue.get(pattern_id, {})
        rejection = rejections.get(pattern_id, {})
        version = versions.get(pattern_id, {})
        evaluation = evaluations.get(pattern_id, {})
        source_path = [
            {
                "source_key": row.get("source_key"),
                "fresh": row.get("fresh") is True,
                "quorum_eligible": row.get("quorum_eligible") is True,
                "independence_cluster_id": row.get("independence_cluster_id"),
                "available_at": row.get("available_at"),
            }
            for row in candidate.get("source_path") or []
            if isinstance(row, dict)
        ]
        status = "strategy_version_admitted" if version else "research_relationship"
        if rejection:
            status = "rejected_before_akber"
        if evaluation.get("final_state"):
            status = str(evaluation["final_state"])
        projected.append(
            {
                "pattern_relationship_id": pattern_id,
                "research_question": candidate.get("research_question"),
                "economic_mechanism": candidate.get("economic_mechanism"),
                "falsifier": candidate.get("falsifier"),
                "instrument": candidate.get("instrument"),
                "market_family": candidate.get("market_family"),
                "strategy_family_id": candidate.get("strategy_family_id"),
                "research_rank": candidate.get("research_rank"),
                "research_rank_type": "research_rank_not_profit_probability",
                "actionability_rank": queue_row.get("actionability_rank") or candidate.get("actionability_rank"),
                "queue_rank": queue_row.get("queue_rank"),
                "status": status,
                "status_lifecycle": [
                    "research_relationship",
                    "preregistered_experiment",
                    "validated_edge",
                    "strategy_version",
                    "akber_review",
                    "paper_review_candidate",
                ],
                "first_observation_at": candidate.get("first_observation_at"),
                "latest_observation_at": candidate.get("latest_observation_at"),
                "current_trigger_active": candidate.get("current_trigger_active") is True,
                "evidence_path": source_path,
                "support_count": sum(row["fresh"] and row["quorum_eligible"] for row in source_path),
                "contradiction_count": 0,
                "blockers": evaluation.get("reasons") or rejection.get("reasons") or queue_row.get("blockers") or [],
                "next_destination": evaluation.get("next_action") or candidate.get("next_action"),
                "is_strategy": bool(version),
                "is_trade_candidate": False,
                "paper_order_created": False,
            }
        )
    return projected


def _resource_registry(settings: Settings | None = None) -> dict[str, Any]:
    references = TemporalGraphStore(settings).query_nodes(node_type="reference_document")
    rows: list[dict[str, Any]] = []
    for node in references:
        payload = node.get("payload") if isinstance(node.get("payload"), dict) else {}
        url = payload.get("url")
        if not url:
            continue
        verification_state = payload.get("verification_state") or "unreviewed"
        source_class = payload.get("source_class") or "unclassified"
        if verification_state in {"superseded", "rejected", "out_of_scope"}:
            registry_group = "archived_superseded"
        elif source_class == "primary":
            registry_group = "primary_references"
        elif source_class == "technical_secondary":
            registry_group = "implementation_references"
        else:
            registry_group = "research_leads"
        rows.append(
            {
                "reference_id": payload.get("reference_id") or node.get("node_id"),
                "url": url,
                "host": payload.get("host"),
                "source_class": source_class,
                "registry_group": registry_group,
                "verification_state": verification_state,
                "collection_state": payload.get("collection_state") or "metadata_only",
                "market_evidence_eligible": False,
                "source_quorum_eligible": False,
            }
        )
    groups: dict[str, list[dict[str, Any]]] = {}
    for group in (
        "primary_references",
        "implementation_references",
        "research_leads",
        "archived_superseded",
    ):
        groups[group] = []
    for row in sorted(rows, key=lambda item: (str(item["registry_group"]), str(item["host"]), str(item["url"]))):
        groups[str(row["registry_group"])].append(row)
    return {
        "schema_version": "qadam_qeg_curated_resource_registry.v1",
        "artifact_type": "qadam_qeg_curated_resource_registry",
        "generated_at": now_iso(),
        "status": "complete",
        "reference_count": len(rows),
        "groups": groups,
        "curation_rule": "Metadata only. References remain classified leads until independently verified.",
        "full_text_fetch_attempted": False,
        "source_quorum_credit_count": 0,
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "authority": qeg_authority(governed_projection=True),
    }


def build_qeg_dashboard_projection(settings: Settings | None = None) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    generated_at = now_iso()
    manifest = read_json(runtime / GRAPH_MANIFEST_ARTIFACT)
    health = read_json(runtime / GRAPH_HEALTH_ARTIFACT)
    claims = read_json(runtime / CLAIM_SUMMARY_ARTIFACT)
    references = read_json(runtime / REFERENCE_SUMMARY_ARTIFACT)
    memory = read_json(runtime / EXPERIMENT_SUMMARY_ARTIFACT)
    pattern_state = read_json(runtime / PATTERN_CANDIDATES_ARTIFACT)
    queue_state = read_json(runtime / ACTIONABILITY_QUEUE_ARTIFACT)
    bridge = read_json(runtime / EXPERIMENT_BRIDGE_ARTIFACT)
    quantum = read_json(runtime / QUANTUM_CHALLENGER_ARTIFACT)
    strategies = read_json(runtime / STRATEGY_VERSIONS_ARTIFACT)
    admission = read_json(runtime / PAPER_ADMISSION_ARTIFACT)
    funnel = read_json(runtime / ACTIVE_DISCOVERY_FUNNEL_ARTIFACT)
    multi_setup = read_json(runtime / MULTI_SETUP_ARTIFACT)
    learning = read_json(runtime / OUTCOME_LEARNING_ARTIFACT)
    tournaments = read_json(runtime / CHALLENGER_TOURNAMENT_ARTIFACT)
    source_universe = read_json(runtime / SOURCE_UNIVERSE_ARTIFACT)
    trading_universe = read_json(runtime / TRADING_UNIVERSE_ARTIFACT)
    candidates = _rows(pattern_state, "candidates")
    versions = _rows(strategies, "versions")
    source_rows = _source_projection(_rows(source_universe, "sources"), candidates)
    instrument_rows = _instrument_projection(_rows(trading_universe, "instruments"), candidates, versions)
    pattern_rows = _pattern_projection(candidates, _rows(queue_state, "rows"), strategies, funnel)
    resource_registry = _resource_registry(settings)
    write_json_atomic(runtime / QEG_RESOURCE_REGISTRY_ARTIFACT, resource_registry)

    validated_edge_count = int(read_json(runtime / "qadam_edge_registry.json").get("validated_edge_count") or 0)
    current_state = (
        "paper_review_candidate_available"
        if int(funnel.get("paper_review_candidate_count") or 0) > 0
        else "evidence_maturing_no_validated_edge"
        if validated_edge_count == 0
        else "validated_edge_waiting_for_complete_trade_context"
    )
    blockers = unique_errors(
        [
            str(reason)
            for row in strategies.get("rejections") or []
            for reason in row.get("reasons") or []
        ]
    )
    payload = {
        "schema_version": "qadam_qeg_dashboard_projection.v1",
        "artifact_type": "qadam_qeg_dashboard_projection",
        "generated_at": generated_at,
        "status": "current" if manifest.get("status") == "complete" and health.get("status") == "healthy" else "degraded",
        "freshness": freshness_label(manifest.get("generated_at"), max_age_seconds=1800),
        "current_empirical_state": current_state,
        "implementation_state": "qeg_0_to_14_implemented",
        "headline": "Evidence compounds across research cycles; no validated graph-derived edge exists yet.",
        "sections": {
            "overview": {
                "graph_generation_id": manifest.get("generation_id"),
                "node_count": manifest.get("node_count", 0),
                "edge_count": manifest.get("edge_count", 0),
                "source_count": len(source_rows),
                "instrument_count": len(instrument_rows),
                "experiment_memory_count": memory.get("memory_record_count", 0),
                "negative_result_count": memory.get("negative_result_count", 0),
                "validated_edge_count": validated_edge_count,
                "strategy_version_count": strategies.get("strategy_version_count", 0),
                "paper_review_candidate_count": funnel.get("paper_review_candidate_count", 0),
            },
            "data_sources": {
                "headline": "How each source contributes to Qadam's connected evidence memory",
                "rows": source_rows,
            },
            "trading_universe": {
                "headline": "How watched instruments connect to entities, patterns, proxies and strategies",
                "rows": instrument_rows,
            },
            "patterns": {
                "headline": "Ranked research relationships, their evidence paths and their next destination",
                "rows": pattern_rows,
                "candidate_count": len(pattern_rows),
                "actionable_research_count": queue_state.get("ready_for_preregistered_experiment_count", 0),
            },
            "quantum": {
                "headline": "Quantum is compared with the same evidence, labels, folds and costs as classical methods.",
                "comparison_count": quantum.get("comparison_count", 0),
                "ibm_hardware_used": quantum.get("existing_hardware_used") is True,
                "matched_classical_baseline": "same evidence, labels, folds and costs",
                "incremental_mean_net_return": quantum.get("existing_hardware_incremental_mean_net_return"),
                "predictive_conclusion": quantum.get("existing_hardware_predictive_conclusion"),
                "quantum_value_state": quantum.get("quantum_value_state"),
                "strategy_evidence_changed": any(row.get("affects_strategy_evidence") is True for row in quantum.get("comparisons") or []),
            },
            "strategies": {
                "headline": "Patterns become strategy versions only after frozen evidence criteria pass.",
                "version_count": strategies.get("strategy_version_count", 0),
                "core_refinement_count": strategies.get("core_refinement_count", 0),
                "emerging_strategy_count": strategies.get("emerging_strategy_count", 0),
                "rejection_count": strategies.get("rejection_count", 0),
                "versions": versions,
                "rejections": (strategies.get("rejections") or [])[:20],
                "admitted_count": admission.get("admitted_count", 0),
            },
            "decision": {
                "headline": "Every complete setup enters the same Akber, shadow, risk and Router path.",
                "queue_count": queue_state.get("queue_count", 0),
                "evaluated_count": funnel.get("evaluated_count", 0),
                "akber_entered_count": funnel.get("akber_entered_count", 0),
                "akber_pass_count": funnel.get("akber_pass_count", 0),
                "paper_review_candidate_count": funnel.get("paper_review_candidate_count", 0),
                "final_state_counts": funnel.get("final_state_counts") or {},
                "evaluations": funnel.get("evaluations") or [],
            },
            "orders": {
                "headline": "Only canonical Router and PaperOps records appear here.",
                "decision_count": multi_setup.get("decision_count", 0),
                "handoff_count": multi_setup.get("handoff_count", 0),
                "paper_review_decision_count": multi_setup.get("paper_review_decision_count", 0),
                "canonical_wrapper_only": multi_setup.get("canonical_wrapper_only") is True,
                "broker_write_count": multi_setup.get("broker_write_count", 0),
            },
            "learning": {
                "headline": "Outcomes, holds and rejections become attributable memory before any change is proposed.",
                "learning_record_count": learning.get("learning_record_count", 0),
                "matured_record_count": learning.get("matured_record_count", 0),
                "negative_record_count": learning.get("negative_record_count", 0),
                "proposal_count": learning.get("proposal_count", 0),
                "challenger_tournament_count": tournaments.get("tournament_count", 0),
                "completed_challenger_count": tournaments.get("completed_tournament_count", 0),
            },
            "system": {
                "headline": "The append-only evidence record is canonical; the local index can be rebuilt.",
                "graph_generation_id": manifest.get("generation_id"),
                "graph_status": health.get("status"),
                "graph_root_bytes": (health.get("disk") or {}).get("graph_root_bytes", 0),
                "filesystem_free_bytes": (health.get("disk") or {}).get("filesystem_free_bytes", 0),
                "canonical_events_rebuildable": health.get("canonical_events_rebuildable") is True,
                "sqlite_index_disposable": health.get("sqlite_index_disposable") is True,
                "reference_count": references.get("reference_count", 0),
                "claim_count": claims.get("claim_count", 0),
                "preregistered_experiment_count": bridge.get("preregistered_experiment_count", 0),
                "blockers": blockers,
            },
        },
        "resource_registry_ref": QEG_RESOURCE_REGISTRY_ARTIFACT,
        "source_artifacts": [
            GRAPH_MANIFEST_ARTIFACT,
            GRAPH_HEALTH_ARTIFACT,
            PATTERN_CANDIDATES_ARTIFACT,
            ACTIONABILITY_QUEUE_ARTIFACT,
            EXPERIMENT_BRIDGE_ARTIFACT,
            QUANTUM_CHALLENGER_ARTIFACT,
            STRATEGY_VERSIONS_ARTIFACT,
            ACTIVE_DISCOVERY_FUNNEL_ARTIFACT,
            MULTI_SETUP_ARTIFACT,
            OUTCOME_LEARNING_ARTIFACT,
        ],
        "blockers": blockers,
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "paper_only": True,
        "live_capital_enabled": False,
        "paper_order_created": False,
        "proof_credit_granted": False,
        "authority": qeg_authority(governed_projection=True),
    }
    errors = validate_qeg_dashboard_payload(payload)
    write_json_atomic(runtime / QEG_DASHBOARD_ARTIFACT, payload)
    return payload, errors


def validate_qeg_dashboard_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    sections = payload.get("sections") if isinstance(payload.get("sections"), dict) else {}
    required = {"overview", "data_sources", "trading_universe", "patterns", "quantum", "strategies", "decision", "orders", "learning", "system"}
    if not required.issubset(sections):
        errors.append("qeg_dashboard_sections_missing")
    if payload.get("public_safe") is not True or payload.get("read_only") is not True or payload.get("command_disabled") is not True:
        errors.append("qeg_dashboard_public_boundary_invalid")
    if payload.get("live_capital_enabled") is not False or payload.get("paper_order_created") is not False:
        errors.append("qeg_dashboard_authority_violation")
    if (sections.get("overview") or {}).get("source_count") != 41:
        errors.append("qeg_dashboard_source_count_not_41")
    if (sections.get("overview") or {}).get("instrument_count") != 19:
        errors.append("qeg_dashboard_instrument_count_not_19")
    if any(row.get("research_rank_type") != "research_rank_not_profit_probability" for row in (sections.get("patterns") or {}).get("rows") or []):
        errors.append("qeg_dashboard_research_rank_misrepresented")
    if (sections.get("orders") or {}).get("canonical_wrapper_only") is not True:
        errors.append("qeg_dashboard_parallel_order_route_implied")
    return sorted(set(errors))


def build_qeg_telegram_projection(settings: Settings | None = None) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    dashboard = read_json(runtime / QEG_DASHBOARD_ARTIFACT)
    if not dashboard:
        dashboard, _errors = build_qeg_dashboard_projection(settings)
    patterns = (dashboard.get("sections") or {}).get("patterns") or {}
    quantum = (dashboard.get("sections") or {}).get("quantum") or {}
    overview = (dashboard.get("sections") or {}).get("overview") or {}
    decision = (dashboard.get("sections") or {}).get("decision") or {}
    rows = sorted(
        patterns.get("rows") or [],
        key=lambda row: (float(row.get("actionability_rank") or 0), float(row.get("research_rank") or 0)),
        reverse=True,
    )
    strongest = rows[0] if rows else {}
    material = {
        "pattern_relationship_id": strongest.get("pattern_relationship_id"),
        "research_rank": strongest.get("research_rank"),
        "actionability_rank": strongest.get("actionability_rank"),
        "current_trigger_active": strongest.get("current_trigger_active"),
        "status": strongest.get("status"),
        "validated_edge_count": overview.get("validated_edge_count"),
        "strategy_version_count": overview.get("strategy_version_count"),
        "paper_review_candidate_count": decision.get("paper_review_candidate_count"),
        "final_state_counts": decision.get("final_state_counts"),
        "matured_record_count": ((dashboard.get("sections") or {}).get("learning") or {}).get("matured_record_count"),
    }
    quantum_material = {
        "comparison_count": quantum.get("comparison_count"),
        "predictive_conclusion": quantum.get("predictive_conclusion"),
        "incremental_mean_net_return": quantum.get("incremental_mean_net_return"),
        "strategy_evidence_changed": quantum.get("strategy_evidence_changed"),
    }
    material_fingerprint = sha256_json(material)
    quantum_fingerprint = sha256_json(quantum_material)
    ledger = read_jsonl(runtime / QEG_TELEGRAM_DEDUPE_ARTIFACT)
    previous = ledger[-1] if ledger else {}
    material_changed = previous.get("material_fingerprint") != material_fingerprint
    quantum_changed = previous.get("quantum_fingerprint") != quantum_fingerprint
    message: str | None = None
    if material_changed:
        if strongest:
            message = (
                f"Qadam research update. Most actionable relationship: {strongest.get('research_question')} "
                f"Research rank {float(strongest.get('research_rank') or 0):.3f}; "
                f"{strongest.get('support_count', 0)}/{len(strongest.get('evidence_path') or [])} supporting sources are fresh and independent enough to count. "
                f"Current state: {strongest.get('status')}. "
                f"Validated edges: {overview.get('validated_edge_count', 0)}; paper-review candidates: {decision.get('paper_review_candidate_count', 0)}."
            )
        else:
            message = "Qadam research update. No graph relationship is currently ready for investigation or paper review."
        if quantum_changed:
            increment = quantum.get("incremental_mean_net_return")
            increment_text = f"{float(increment) * 100:.3f}%" if isinstance(increment, (int, float)) else "not measurable"
            message += (
                f" Quantum comparison: {quantum.get('predictive_conclusion') or 'not measured'}; "
                f"incremental mean net result versus the matched classical method: {increment_text}."
            )
        message += " Next: " + str(strongest.get("next_destination") or "wait for new independent evidence") + "."

    payload = {
        "schema_version": "qadam_qeg_telegram_projection.v1",
        "artifact_type": "qadam_qeg_telegram_projection",
        "generated_at": now_iso(),
        "status": "candidate_ready" if message else "suppressed_no_material_change",
        "material_changed": material_changed,
        "quantum_changed": quantum_changed,
        "material_fingerprint": material_fingerprint,
        "quantum_fingerprint": quantum_fingerprint,
        "message": message,
        "message_character_count": len(message or ""),
        "delivery_attempted": False,
        "delivery_succeeded": False,
        "dedupe_reason": None if message else "same material research state as the previous projection",
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "telegram_live_send_allowed": False,
        "telegram_command_path_enabled": False,
        "paper_order_created": False,
        "proof_credit_granted": False,
        "authority": qeg_authority(governed_projection=True),
    }
    errors = validate_qeg_telegram_payload(payload)
    write_json_atomic(runtime / QEG_TELEGRAM_ARTIFACT, payload)
    if message and not errors:
        append_jsonl_durable(
            runtime / QEG_TELEGRAM_DEDUPE_ARTIFACT,
            {
                "event_id": stable_id("qeg-telegram-candidate", material_fingerprint),
                "generated_at": payload["generated_at"],
                "material_fingerprint": material_fingerprint,
                "quantum_fingerprint": quantum_fingerprint,
                "delivery_attempted": False,
                "delivery_succeeded": False,
                "authority": qeg_authority(governed_projection=True),
            },
        )
    return payload, errors


def validate_qeg_telegram_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    message = str(payload.get("message") or "")
    if payload.get("public_safe") is not True or payload.get("command_disabled") is not True:
        errors.append("qeg_telegram_public_boundary_invalid")
    if payload.get("telegram_live_send_allowed") is not False or payload.get("telegram_command_path_enabled") is not False:
        errors.append("qeg_telegram_authority_violation")
    if payload.get("delivery_attempted") is not False or payload.get("paper_order_created") is not False:
        errors.append("qeg_telegram_side_effect_detected")
    if message and len(message) > 900:
        errors.append("qeg_telegram_message_too_long")
    if any(phrase in message.lower() for phrase in ("rather than forcing a trade", "real hardware, not a simulator", "supremacy", "guaranteed")):
        errors.append("qeg_telegram_promotional_or_repetitive_language")
    if payload.get("status") == "suppressed_no_material_change" and message:
        errors.append("qeg_telegram_dedupe_failed")
    return sorted(set(errors))


def build_qeg_visibility(settings: Settings | None = None) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    dashboard, dashboard_errors = build_qeg_dashboard_projection(settings)
    telegram, telegram_errors = build_qeg_telegram_projection(settings)
    errors = unique_errors([*dashboard_errors, *telegram_errors])
    write_phase_status(
        "QEG-14",
        status="passed" if not errors else "blocked",
        implementation_complete=not errors,
        empirical_state="public_visibility_current_evidence_maturing",
        artifacts=[QEG_DASHBOARD_ARTIFACT, QEG_TELEGRAM_ARTIFACT, QEG_RESOURCE_REGISTRY_ARTIFACT],
        blockers=errors,
        settings=settings,
    )
    return dashboard, telegram, errors


def validate_qeg_visibility(settings: Settings | None = None) -> list[str]:
    runtime = runtime_dir(settings)
    dashboard = read_json(runtime / QEG_DASHBOARD_ARTIFACT)
    telegram = read_json(runtime / QEG_TELEGRAM_ARTIFACT)
    return unique_errors([*validate_qeg_dashboard_payload(dashboard), *validate_qeg_telegram_payload(telegram)])
