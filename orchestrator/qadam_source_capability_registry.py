"""Canonical 41-source capability and decision-usability registry."""

from __future__ import annotations

from collections import Counter
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    canonical_json,
    now_iso,
    read_json,
    runtime_dir,
    sha256_text,
)

SCHEMA_VERSION = "qadam_source_capability_registry.v1"
REGISTRY_ARTIFACT = "qadam_source_capability_registry.json"
CHECK_ARTIFACT = "qadam_source_capability_registry_checks.json"


def _strategy_source_requirements(runtime: Any) -> dict[str, list[str]]:
    strategy_universe = read_json(runtime / "qsase_dashboard_strategy_universe.json")
    required_by_source: dict[str, list[str]] = {}
    for strategy in strategy_universe.get("all_strategy_rows", []):
        if not isinstance(strategy, dict):
            continue
        strategy_id = str(strategy.get("strategy_family_id") or "").strip()
        if not strategy_id:
            continue
        for source_key in strategy.get("source_keywords", []):
            key = str(source_key or "").strip()
            if key:
                required_by_source.setdefault(key, []).append(strategy_id)
    return {
        key: sorted(set(strategy_ids))
        for key, strategy_ids in required_by_source.items()
    }


def _capability_class(
    *,
    provider_backed: bool,
    fresh: bool,
    sample: bool,
    supplemental: bool,
    forward_only: bool,
    historical_alpha_usable: bool,
    history_state: str,
    required_by_strategy_ids: list[str],
) -> tuple[str, bool]:
    if provider_backed and fresh and not sample:
        return "fresh_provider_backed", False
    if supplemental:
        return "supplemental_context", False
    if forward_only and not required_by_strategy_ids:
        return "forward_only_registered", False
    if historical_alpha_usable and not required_by_strategy_ids:
        return "historical_research_only", False
    if history_state == "excluded" and not required_by_strategy_ids:
        return "reviewed_unavailable_or_excluded", False
    if required_by_strategy_ids:
        return "required_source_unavailable_now", True
    return "registered_not_currently_usable", False


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
    required_by_source = _strategy_source_requirements(runtime)
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
        required_by_strategy_ids = required_by_source.get(source_key, [])
        capability_class, active_failure = _capability_class(
            provider_backed=provider_backed,
            fresh=fresh,
            sample=sample,
            supplemental=source.get("supplemental_context_only") is True,
            forward_only=history.get("forward_only") is True,
            historical_alpha_usable=historical_alpha_usable,
            history_state=history_state,
            required_by_strategy_ids=required_by_strategy_ids,
        )
        rows.append(
            {
                "source_key": source_key,
                "source_name": source.get("source_name"),
                "source_family": source.get("source_family"),
                "operating_state": source.get("state") or source.get("adapter_status"),
                "live_freshness": source.get("freshness_status"),
                "latest_observation_at": source.get("observed_timestamp"),
                "provider_event_latest_at": source.get("provider_event_latest_at"),
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
                "capability_class": capability_class,
                "required_by_strategy_ids": required_by_strategy_ids,
                "active_strategy_source_failure": active_failure,
                "absence_is_classified": capability_class
                in {
                    "supplemental_context",
                    "forward_only_registered",
                    "historical_research_only",
                    "reviewed_unavailable_or_excluded",
                },
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
        "classified_limit": sum(row["absence_is_classified"] for row in rows),
        "active_strategy_source_failure": sum(
            row["active_strategy_source_failure"] for row in rows
        ),
    }
    counts["strategy_scoped_source_gap"] = counts[
        "active_strategy_source_failure"
    ]
    rows_by_key = {str(row["source_key"]): row for row in rows}
    strategy_coverage: list[dict[str, Any]] = []
    strategy_universe = read_json(runtime / "qsase_dashboard_strategy_universe.json")
    for strategy in strategy_universe.get("all_strategy_rows", []):
        if not isinstance(strategy, dict):
            continue
        strategy_id = str(strategy.get("strategy_family_id") or "").strip()
        source_keys = [
            str(value)
            for value in strategy.get("source_keywords", [])
            if str(value or "").strip()
        ]
        fresh_keys = [
            key
            for key in source_keys
            if rows_by_key.get(key, {}).get("confirmation_eligible_now") is True
        ]
        missing_keys = [key for key in source_keys if key not in fresh_keys]
        readiness = (
            "ready_for_multi_source_research"
            if len(fresh_keys) >= 2
            else "limited_single_fresh_source"
            if len(fresh_keys) == 1
            else "blocked_no_fresh_provider_backed_source"
        )
        strategy_coverage.append(
            {
                "strategy_family_id": strategy_id,
                "strategy_label": strategy.get("label") or strategy_id,
                "required_source_count": len(source_keys),
                "fresh_provider_backed_source_count": len(fresh_keys),
                "fresh_provider_backed_source_keys": fresh_keys,
                "unavailable_source_keys": missing_keys,
                "research_readiness": readiness,
                "candidate_or_order_authority": False,
            }
        )
    material_rows = [
        {
            "source_key": row["source_key"],
            "capability_class": row["capability_class"],
            "live_freshness": row["live_freshness"],
            # Retrieval clocks change on every healthy poll. Provider event time
            # changes only when the source contributes genuinely new evidence.
            "provider_event_latest_at": row["provider_event_latest_at"],
            "provider_backed_current": row["provider_backed_current"],
            "sample_or_fixture": row["sample_or_fixture"],
            "historical_state": row["historical_state"],
            "historical_alpha_usable": row["historical_alpha_usable"],
            "required_by_strategy_ids": row["required_by_strategy_ids"],
        }
        for row in rows
    ]
    material_fingerprint = sha256_text(
        canonical_json(
            {
                "sources": material_rows,
                "strategy_coverage": strategy_coverage,
            }
        )
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_source_capability_registry",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "counts": counts,
        "operating_status": (
            "operational_with_strategy_scoped_source_gaps"
            if counts["active_strategy_source_failure"]
            else "operational_with_classified_limits"
        ),
        "material_fingerprint": material_fingerprint,
        "operating_state_counts": dict(Counter(str(row["operating_state"]) for row in rows)),
        "capability_class_counts": dict(
            Counter(str(row["capability_class"]) for row in rows)
        ),
        "strategy_source_coverage": strategy_coverage,
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
