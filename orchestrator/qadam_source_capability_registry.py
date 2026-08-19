"""Canonical 41-source capability and decision-usability registry."""

from __future__ import annotations

from collections import Counter
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import now_iso, read_json, runtime_dir

SCHEMA_VERSION = "qadam_source_capability_registry.v1"
REGISTRY_ARTIFACT = "qadam_source_capability_registry.json"
CHECK_ARTIFACT = "qadam_source_capability_registry_checks.json"


def build_source_capability_registry(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    universe = read_json(runtime / "qsase_source_universe.json")
    historical = read_json(runtime / "qadam_historical_source_coverage_matrix.json")
    empirical = read_json(runtime / "qadam_source_empirical_role_registry.json")
    historical_by_key = {
        str(row.get("source_key") or ""): row
        for row in historical.get("rows", [])
        if isinstance(row, dict)
    }
    empirical_by_key = {
        str(row.get("source_key") or ""): row
        for row in empirical.get("sources", [])
        if isinstance(row, dict)
    }
    rows: list[dict[str, Any]] = []
    for source in universe.get("sources", []):
        if not isinstance(source, dict):
            continue
        source_key = str(source.get("source_key") or "")
        history = historical_by_key.get(source_key, {})
        empirical_role = empirical_by_key.get(source_key, {})
        provider_backed = source.get("provider_backed_observation") is True
        fresh = source.get("freshness_status") == "fresh"
        sample = source.get("sample_fixture") is True
        live_role = (
            "usable_current_confirmation"
            if provider_backed and fresh and not sample
            else "supplemental_context"
            if source.get("supplemental_context_only") is True
            else "registered_unavailable_currently"
        )
        history_state = str(history.get("status") or "unclassified")
        # The acquisition matrix describes what the OR-3 pilot was allowed to
        # ingest. The later empirical role registry is authoritative for what
        # was actually scored after point-in-time and label checks completed.
        historical_alpha_usable = (
            empirical_role.get("historically_scored") is True
            and empirical_role.get("empirical_role") == "scored_signal"
            and empirical_role.get("closure_state") == "provider_backed_acquired"
        )
        rows.append(
            {
                "source_key": source_key,
                "source_name": source.get("source_name"),
                "source_family": source.get("source_family"),
                "operating_state": source.get("state") or source.get("adapter_status"),
                "live_freshness": source.get("freshness_status"),
                "latest_observation_at": source.get("observed_timestamp"),
                "provider_backed_current": provider_backed,
                "sample_or_fixture": sample,
                "trust_posture": source.get("trust_posture"),
                "trust_score": source.get("trust_score"),
                "live_decision_role": live_role,
                "quorum_eligible_now": (
                    source.get("source_quorum_contribution", {}).get("can_contribute") is True
                    and provider_backed
                    and fresh
                    and not sample
                ),
                "confirmation_eligible_now": live_role == "usable_current_confirmation",
                "historical_state": history_state,
                "historical_coverage": history.get("historical_coverage"),
                "forward_only": history.get("forward_only") is True,
                "historical_alpha_usable": historical_alpha_usable,
                "historical_empirical_role": empirical_role.get("empirical_role"),
                "historically_scored": empirical_role.get("historically_scored") is True,
                "provider_backed_historical_row_count": int(
                    empirical_role.get("provider_backed_row_count") or 0
                ),
                "scoreability_disposition": empirical_role.get(
                    "scoreability_disposition"
                ),
                "availability_time_preserved": bool(history.get("timezone_semantics")),
                "feature_producer": source.get("source_pipeline"),
                "label_maturity": "matures_by_declared_forward_horizon",
                "strategy_relevance": history.get("strategy_and_discovery_roles", []),
                "subscription_or_cost": history.get("expected_cost"),
                "status_reason": history.get("classification_reason"),
                "direct_trade_authority": False,
            }
        )
    errors: list[str] = []
    if len(rows) != 41:
        errors.append(f"source_count_mismatch:{len(rows)}")
    keys = [row["source_key"] for row in rows]
    if any(not key for key in keys) or len(keys) != len(set(keys)):
        errors.append("source_identity_missing_or_duplicate")
    if any(row["sample_or_fixture"] and row["quorum_eligible_now"] for row in rows):
        errors.append("fixture_counted_as_quorum")
    counts = {
        "catalogue": len(rows),
        "provider_backed_current": sum(row["provider_backed_current"] for row in rows),
        "fresh_current_confirmation": sum(row["confirmation_eligible_now"] for row in rows),
        "quorum_eligible_now": sum(row["quorum_eligible_now"] for row in rows),
        "historical_alpha_usable": sum(row["historical_alpha_usable"] for row in rows),
        "forward_only": sum(row["forward_only"] for row in rows),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_source_capability_registry",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "counts": counts,
        "operating_state_counts": dict(Counter(str(row["operating_state"]) for row in rows)),
        "sources": rows,
        "validation_errors": errors,
        "catalogue_count_is_not_independent_signal_count": True,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
    }


def build_and_write_source_capability_registry(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    payload = build_source_capability_registry(settings)
    errors = list(payload["validation_errors"])
    store = AtomicArtifactStore(runtime)
    store.write_json(REGISTRY_ARTIFACT, payload)
    store.write_json(
        CHECK_ARTIFACT,
        {
            **payload,
            "artifact_type": "qadam_source_capability_registry_checks",
            "validation_error_count": len(errors),
        },
    )
    return payload, errors


__all__ = ["build_and_write_source_capability_registry"]
