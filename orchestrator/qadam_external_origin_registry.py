"""Approved qualitative origin, terms, trust and independence policy."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_qualitative_common import (
    EXTERNAL_PROMOTION_ARTIFACT,
    EXTERNAL_TERMS_ARTIFACT,
    ORIGIN_REGISTRY_PATH,
    TRUST_POLICY_PATH,
    now_iso,
    public_authority,
    read_json,
    repo_root,
    runtime_dir,
    stable_id,
)


ALLOWED_INITIAL_TRANSPORTS = {"official_web", "rss", "github_api"}


def validate_origin_registry(registry: dict[str, Any], trust: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    rows = registry.get("origins") if isinstance(registry.get("origins"), list) else []
    tiers = trust.get("trust_tiers") if isinstance(trust.get("trust_tiers"), dict) else {}
    ids = [str(row.get("origin_id") or "") for row in rows if isinstance(row, dict)]
    if not rows:
        errors.append("external_origin_registry_empty")
    if any(not value for value in ids) or len(ids) != len(set(ids)):
        errors.append("external_origin_identity_missing_or_duplicate")
    for row in rows:
        if not isinstance(row, dict):
            errors.append("external_origin_record_invalid")
            continue
        origin_id = str(row.get("origin_id") or "unknown")
        if row.get("trust_tier") not in tiers:
            errors.append(f"external_origin_trust_tier_invalid:{origin_id}")
        if not row.get("independence_cluster"):
            errors.append(f"external_origin_independence_cluster_missing:{origin_id}")
        if row.get("enabled") is True:
            url = str(row.get("url") or "")
            parsed = urlparse(url)
            allowed = {str(value).lower() for value in row.get("allowed_domains") or []}
            if row.get("transport") not in ALLOWED_INITIAL_TRANSPORTS:
                errors.append(f"external_origin_enabled_transport_not_allowed:{origin_id}")
            if parsed.scheme != "https" or not parsed.hostname:
                errors.append(f"external_origin_enabled_url_invalid:{origin_id}")
            elif parsed.hostname.lower() not in allowed:
                errors.append(f"external_origin_domain_not_allowlisted:{origin_id}")
            if row.get("terms_state") != "reviewed_internal_research":
                errors.append(f"external_origin_terms_not_reviewed:{origin_id}")
        if str(row.get("transport") or "") in {"search", "jina_reader"} and row.get("trust_tier") != "discovery_only":
            errors.append(f"transport_misclassified_as_origin:{origin_id}")
    if trust.get("transport_never_counts_as_origin") is not True:
        errors.append("transport_origin_separation_not_enforced")
    if trust.get("same_origin_repetition_never_inflates_quorum") is not True:
        errors.append("same_origin_independence_rule_missing")
    return sorted(set(errors))


def build_external_origin_state(settings: Settings | None = None) -> tuple[dict[str, Any], list[str]]:
    generated_at = now_iso()
    registry = read_json(repo_root() / ORIGIN_REGISTRY_PATH)
    trust = read_json(repo_root() / TRUST_POLICY_PATH)
    errors = validate_origin_registry(registry, trust)
    origins = registry.get("origins") if isinstance(registry.get("origins"), list) else []
    terms_rows = [
        {
            "origin_id": row.get("origin_id"),
            "origin_class": row.get("origin_class"),
            "transport": row.get("transport"),
            "terms_state": row.get("terms_state"),
            "historical_use": row.get("historical_use"),
            "retention_class": row.get("retention_class"),
            "redistribution": row.get("redistribution"),
            "enabled": row.get("enabled") is True,
        }
        for row in origins
        if isinstance(row, dict)
    ]
    promotions = [
        {
            "schema_version": "qadam_external_origin_promotion.v1",
            "promotion_id": stable_id("origin-promotion", row.get("origin_id"), row.get("enabled")),
            "generated_at": generated_at,
            "origin_id": row.get("origin_id"),
            "from_state": "registered",
            "to_state": "research_eligible" if row.get("enabled") else "operator_review_required",
            "reason": "reviewed zero-auth official origin" if row.get("enabled") else "not enabled in initial zero-auth lane",
            "human_review_required": row.get("enabled") is not True,
            "authority": public_authority(),
        }
        for row in origins
        if isinstance(row, dict)
    ]
    payload = {
        "schema_version": "qadam_external_origin_terms_matrix.v1",
        "artifact_type": "qadam_external_origin_terms_matrix",
        "generated_at": generated_at,
        "status": "passed" if not errors else "blocked",
        "origin_count": len(origins),
        "enabled_origin_count": sum(row.get("enabled") is True for row in origins),
        "transport_counts": dict(Counter(str(row.get("transport") or "unknown") for row in origins)),
        "trust_tier_counts": dict(Counter(str(row.get("trust_tier") or "unknown") for row in origins)),
        "origins": terms_rows,
        "validation_errors": errors,
        "authority": public_authority(),
    }
    store = AtomicArtifactStore(runtime_dir(settings))
    store.write_json(EXTERNAL_TERMS_ARTIFACT, payload)
    store.write_jsonl(EXTERNAL_PROMOTION_ARTIFACT, promotions)
    return payload, errors


__all__ = ["build_external_origin_state", "validate_origin_registry"]
