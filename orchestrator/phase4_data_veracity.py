"""Phase 4 Data Veracity Audit.

The audit scores source coverage, freshness, latency, degradation, and
corroboration posture from existing read-only runtime evidence. It never
creates signals, trade candidates, broker truth, fill truth, receipt evidence,
reconciliation truth, orders, or live-capital authority.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.phase4_artifacts import (
    PHASE4_ARTIFACT_SCHEMA_VERSION,
    phase4_authority_boundary,
    validate_phase4_artifact,
)
from orchestrator.preference_mcp_identity import (
    PREFERENCE_SOURCE_KEY,
    build_preference_mcp_identity_status,
)
from orchestrator.preference_mcp_provenance import preference_provenance_paths
from orchestrator.preference_mcp_source_promotion import (
    build_preference_source_promotion_decisions,
    preference_source_promotion_paths,
)
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT, SOURCE_SPECS


DATA_VERACITY_AUDIT_SCHEMA_VERSION = 1

VERACITY_AUTHORITY_FLAGS: tuple[str, ...] = (
    "signal_authority",
    "trade_candidate_creation_allowed",
    "risk_approval_authority",
    "execution_authority",
    "paper_order_authority",
    "broker_write_authority",
    "broker_echo_authority",
    "fill_confirmation_authority",
    "receipt_evidence_authority",
    "reconciliation_truth_authority",
    "live_capital_authority",
)


@dataclass(frozen=True)
class SourceVeracity:
    source_key: str
    source_name: str
    source_role: str
    canonical_source: bool
    pipeline: str
    tier: int | None
    coverage_status: str
    freshness_status: str
    latency_status: str
    degradation_status: str
    corroboration_status: str
    evidence_basis: str
    routing_boundary: str
    quarantine: bool
    reason_codes: tuple[str, ...]
    authority_flags: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["reason_codes"] = list(self.reason_codes)
        return payload


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return fallback or {}
    return json.loads(path.read_text(encoding="utf-8"))


def _latest_runtime_evidence(settings: Settings | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    runtime = _runtime_dir(settings)
    data_map = _read_json(runtime / "data_environment_map.json", {"sources": [], "summary": {}})
    cockpit = _read_json(runtime / "cockpit-status.json", {})
    if not cockpit:
        from orchestrator.cockpit_status import build_cockpit_status

        cockpit = build_cockpit_status(settings)
    return data_map, cockpit


def _authority_flags() -> dict[str, bool]:
    return {field: False for field in VERACITY_AUTHORITY_FLAGS}


def _coverage_status(source_key: str, durable: dict[str, Any]) -> str:
    replay_ready = durable.get("status") == "ok" and durable.get("replay_status") == "ok"
    missing_sources = set(durable.get("missing_sources") or ())
    if replay_ready and source_key not in missing_sources:
        return "durable_replay_observed"
    if source_key in missing_sources:
        return "missing_durable_replay"
    return "registered_not_replayed"


def _freshness_status(source: dict[str, Any], durable: dict[str, Any], coverage_status: str) -> str:
    if coverage_status == "missing_durable_replay":
        return "freshness_missing"
    if durable.get("latest_observed_at") and coverage_status == "durable_replay_observed":
        return "fresh_replay_snapshot"
    if source.get("last_heartbeat") or source.get("checked_at"):
        return "heartbeat_observed"
    return "freshness_unavailable"


def _latency_status(source: dict[str, Any]) -> str:
    latency_ms = source.get("latency_ms")
    if isinstance(latency_ms, int | float):
        return "latency_observed"
    if source.get("promoted_adapter"):
        return "latency_not_reported_adapter_ready"
    cadence = str(source.get("cadence") or "")
    if cadence:
        return "cadence_registered_latency_not_measured"
    return "latency_unavailable"


def _degradation_status(source: dict[str, Any], coverage_status: str) -> str:
    if coverage_status == "missing_durable_replay":
        return "degraded_missing_replay"
    degraded_reason = source.get("degraded_reason")
    runtime_status = str(source.get("runtime_status") or source.get("raw_status") or "")
    status = str(source.get("status") or "")
    if degraded_reason:
        return f"degraded:{degraded_reason}"
    if runtime_status in {"unavailable_missing_credentials", "deferred"}:
        return f"degraded:{runtime_status}"
    if status in {"degraded", "offline"}:
        return f"degraded:{status}"
    return "not_degraded"


def _corroboration_status(source: dict[str, Any], coverage_status: str, degradation_status: str) -> str:
    if coverage_status == "missing_durable_replay":
        return "cannot_corroborate_missing_replay"
    if degradation_status.startswith("degraded"):
        return "corroboration_limited_by_degradation"
    if source.get("promoted_adapter") and coverage_status == "durable_replay_observed":
        return "corroboration_ready_read_only"
    return "registered_context_only"


def _score_source(
    spec_by_key: dict[str, Any],
    data_source: dict[str, Any],
    watching_source: dict[str, Any],
    durable: dict[str, Any],
) -> SourceVeracity:
    source_key = str(data_source.get("source_key") or watching_source.get("source_key"))
    spec = spec_by_key[source_key]
    merged = {**data_source, **watching_source}
    coverage = _coverage_status(source_key, durable)
    freshness = _freshness_status(merged, durable, coverage)
    latency = _latency_status(merged)
    degradation = _degradation_status(merged, coverage)
    corroboration = _corroboration_status(merged, coverage, degradation)
    reason_codes: list[str] = [coverage, freshness, latency, degradation, corroboration]
    quarantine = coverage == "missing_durable_replay" or degradation.startswith("degraded")
    evidence_basis = "durable_replay_and_source_heartbeat"
    if merged.get("promoted_adapter"):
        evidence_basis += "_with_adapter_status"
    return SourceVeracity(
        source_key=source_key,
        source_name=str(merged.get("source_name") or spec.name),
        source_role="canonical_source",
        canonical_source=True,
        pipeline=str(merged.get("pipeline") or spec.pipeline),
        tier=int(merged.get("tier") or spec.tier),
        coverage_status=coverage,
        freshness_status=freshness,
        latency_status=latency,
        degradation_status=degradation,
        corroboration_status=corroboration,
        evidence_basis=evidence_basis,
        routing_boundary=(
            "Canonical source veracity can inform later strategy review, but cannot create "
            "signals, trade candidates, orders, broker truth, receipts, reconciliation truth, or live capital."
        ),
        quarantine=quarantine,
        reason_codes=tuple(reason_codes),
        authority_flags=_authority_flags(),
    )


def _score_yahoo(cockpit: dict[str, Any]) -> SourceVeracity:
    yahoo = cockpit.get("yahoo_finance", {})
    degraded = bool(yahoo.get("degraded")) or yahoo.get("enabled") is not True
    coverage = "supplemental_deferred" if yahoo.get("enabled") is not True else "supplemental_observed"
    freshness = "freshness_deferred" if yahoo.get("enabled") is not True else "supplemental_last_check_observed"
    latency = "latency_not_measured_supplemental"
    degradation = f"degraded:{yahoo.get('degraded_reason')}" if degraded else "not_degraded"
    corroboration = "supplemental_hold_single_source_not_allowed"
    return SourceVeracity(
        source_key="yahoo_finance",
        source_name="Yahoo Finance / yfinance",
        source_role="supplemental_market_confirmation",
        canonical_source=False,
        pipeline="market",
        tier=None,
        coverage_status=coverage,
        freshness_status=freshness,
        latency_status=latency,
        degradation_status=degradation,
        corroboration_status=corroboration,
        evidence_basis="public_safe_cockpit_yahoo_finance_status",
        routing_boundary=(
            "Yahoo Finance is supplemental market confirmation only. Yahoo-only market confirmation "
            "is a hold condition and cannot create signal, order, broker, fill, receipt, reconciliation, "
            "or live-capital authority."
        ),
        quarantine=True,
        reason_codes=(coverage, freshness, latency, degradation, corroboration),
        authority_flags=_authority_flags(),
    )


def _score_preference(settings: Settings | None = None) -> SourceVeracity:
    settings = settings or Settings.from_env()
    identity = build_preference_mcp_identity_status(
        settings=settings,
        live_status_check=False,
        record_event=False,
    )
    provenance_path, _history_path = preference_provenance_paths(settings)
    provenance = _read_json(provenance_path, {})

    identity_status = str(identity.get("status") or "unknown")
    identity_detail = str(identity.get("identity_status") or "unknown")
    provenance_status = str(provenance.get("status") or "not_observed")
    distinct_upstream_count = int(provenance.get("preference_distinct_upstream_source_count") or 0)
    provenance_validated = provenance_status == "validated" and distinct_upstream_count > 0

    if provenance_validated:
        coverage = "supplemental_sample_provenance_validated"
    elif identity_status == "verified_non_anonymous":
        coverage = "supplemental_identity_verified_provenance_pending"
    else:
        coverage = "supplemental_identity_blocked"

    if provenance.get("generated_at"):
        freshness = "supplemental_provenance_report_observed"
    elif identity.get("generated_at"):
        freshness = "supplemental_identity_status_observed"
    else:
        freshness = "freshness_unavailable"

    latency = "latency_not_measured_supplemental"
    if identity_status != "verified_non_anonymous":
        degradation = f"degraded:identity_{identity_status}"
    elif not provenance_validated:
        degradation = "degraded:preference_provenance_not_validated"
    else:
        degradation = "not_degraded"

    if provenance_validated:
        corroboration = "supplemental_explicit_upstream_context_not_canonical"
    elif identity_status == "verified_non_anonymous":
        corroboration = "supplemental_hold_provenance_required"
    else:
        corroboration = "supplemental_hold_identity_blocked_not_canonical"

    reason_codes = [
        coverage,
        freshness,
        latency,
        degradation,
        corroboration,
        f"identity_status:{identity_status}",
        f"identity_detail:{identity_detail}",
        f"provenance_status:{provenance_status}",
        f"distinct_upstream_count:{distinct_upstream_count}",
        "preference_not_source_36",
        "canonical_rank_impact_disallowed",
    ]
    return SourceVeracity(
        source_key=PREFERENCE_SOURCE_KEY,
        source_name="Preference / PREF MCP",
        source_role="supplemental_multi_source_data_plane",
        canonical_source=False,
        pipeline="multi_source",
        tier=None,
        coverage_status=coverage,
        freshness_status=freshness,
        latency_status=latency,
        degradation_status=degradation,
        corroboration_status=corroboration,
        evidence_basis="preference_identity_status_and_source_quorum_report",
        routing_boundary=(
            "Preference/PREF MCP is a supplemental multi-source data plane, not source 36. "
            "It can enrich context only after identity, catalog, provenance, source-quorum, and "
            "domain-allowlist gates pass; it cannot increase canonical source rank, create signals, "
            "orders, broker truth, receipts, reconciliation truth, or live-capital authority."
        ),
        quarantine=True,
        reason_codes=tuple(reason_codes),
        authority_flags=_authority_flags(),
    )


def _preference_source_promotion(
    settings: Settings | None = None,
    *,
    cockpit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    promotion_path, _history_path = preference_source_promotion_paths(settings)
    return _read_json(promotion_path, {}) or build_preference_source_promotion_decisions(
        settings=settings,
        cockpit=cockpit,
    )


def _source_lookup(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("source_key")): row for row in rows if row.get("source_key")}


def build_data_veracity_audit(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    data_map, cockpit = _latest_runtime_evidence(settings)
    preference_source_promotion = _preference_source_promotion(settings, cockpit=cockpit)
    durable = cockpit.get("durable_ingestion", {})
    spec_by_key = {source.key: source for source in SOURCE_SPECS}
    data_sources = _source_lookup(data_map.get("sources", []))
    watching_sources = _source_lookup(cockpit.get("watching", []))
    canonical_rows: list[SourceVeracity] = []
    for spec in SOURCE_SPECS:
        canonical_rows.append(
            _score_source(
                spec_by_key,
                data_sources.get(spec.key, {"source_key": spec.key}),
                watching_sources.get(spec.key, {"source_key": spec.key}),
                durable,
            )
        )
    supplemental_rows = [_score_yahoo(cockpit), _score_preference(settings)]
    source_rows = [row.to_dict() for row in canonical_rows]
    supplemental_source_rows = [row.to_dict() for row in supplemental_rows]
    quarantined = [row for row in canonical_rows if row.quarantine]
    by_coverage = Counter(row.coverage_status for row in canonical_rows)
    by_degradation = Counter(row.degradation_status for row in canonical_rows)
    by_corroboration = Counter(row.corroboration_status for row in canonical_rows)
    authority_flag_violations = [
        f"{row.source_key}:{field}"
        for row in (*canonical_rows, *supplemental_rows)
        for field, enabled in row.authority_flags.items()
        if enabled is not False
    ]
    artifact = {
        "schema_version": PHASE4_ARTIFACT_SCHEMA_VERSION,
        "audit_schema_version": DATA_VERACITY_AUDIT_SCHEMA_VERSION,
        "artifact_type": "data_veracity_audit",
        "artifact_id": "phase4:q4-3:data-veracity-audit",
        "status": "validated" if not authority_flag_violations else "rejected",
        "generated_at": _now(),
        "public_safe": True,
        "authority_boundary": phase4_authority_boundary(),
        "boundary": "Data Veracity Audit is read-only evidence scoring and cannot create execution authority.",
        "canonical_source_count": len(canonical_rows),
        "expected_canonical_source_count": EXPECTED_SOURCE_COUNT,
        "supplemental_source_count": len(supplemental_rows),
        "quarantined_source_count": len(quarantined),
        "authority_flag_violation_count": len(authority_flag_violations),
        "authority_flag_violations": authority_flag_violations,
        "durable_replay": {
            "status": durable.get("status"),
            "contract_status": durable.get("contract_status"),
            "replay_status": durable.get("replay_status"),
            "observation_count": durable.get("observation_count"),
            "replayed_source_count": durable.get("replayed_source_count"),
            "missing_source_count": durable.get("missing_source_count"),
            "latest_observed_at": durable.get("latest_observed_at"),
            "write_authority": durable.get("write_authority"),
            "signal_authority": durable.get("signal_authority"),
            "order_authority": durable.get("order_authority"),
        },
        "coverage_summary": dict(sorted(by_coverage.items())),
        "degradation_summary": dict(sorted(by_degradation.items())),
        "corroboration_summary": dict(sorted(by_corroboration.items())),
        "canonical_sources": source_rows,
        "supplemental_sources": supplemental_source_rows,
        "yahoo_finance_policy": {
            "role": supplemental_rows[0].source_role,
            "canonical_source": False,
            "single_source_market_confirmation_status": "hold",
            "corroboration_only": True,
            "routing_boundary": supplemental_rows[0].routing_boundary,
        },
        "preference_mcp_policy": {
            "role": "supplemental_multi_source_data_plane",
            "canonical_source": False,
            "source_36": False,
            "corroboration_only": True,
            "canonical_rank_impact_allowed": False,
            "source_quorum_credit_allowed": False,
            "source_promotion_status": preference_source_promotion.get("status", "not_run"),
            "source_promotion_decision_count": int(
                preference_source_promotion.get("decision_count", 0) or 0
            ),
            "source_promotion_promoted_decision_count": int(
                preference_source_promotion.get("promoted_decision_count", 0) or 0
            ),
            "source_promotion_canonical_source_count_after": int(
                preference_source_promotion.get(
                    "canonical_source_count_after",
                    EXPECTED_SOURCE_COUNT,
                )
                or EXPECTED_SOURCE_COUNT
            ),
            "routing_boundary": next(
                row.routing_boundary for row in supplemental_rows if row.source_key == PREFERENCE_SOURCE_KEY
            ),
        },
        "trade_candidate_creation_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "fill_confirmation_authority": False,
        "receipt_evidence_authority": False,
        "reconciliation_truth_authority": False,
        "live_capital_enabled": False,
    }
    artifact["validation_errors"] = validate_phase4_artifact(artifact)
    return artifact


def validate_data_veracity_audit(artifact: dict[str, Any]) -> list[str]:
    errors = list(validate_phase4_artifact(artifact))
    if artifact.get("artifact_type") != "data_veracity_audit":
        errors.append("artifact_type_not_data_veracity_audit")
    if artifact.get("canonical_source_count") != EXPECTED_SOURCE_COUNT:
        errors.append("canonical_source_count_mismatch")
    if artifact.get("supplemental_source_count", 0) < 1:
        errors.append("supplemental_source_missing")
    canonical_sources = artifact.get("canonical_sources")
    supplemental_sources = artifact.get("supplemental_sources")
    if not isinstance(canonical_sources, list):
        errors.append("canonical_sources_missing")
        canonical_sources = []
    if not isinstance(supplemental_sources, list):
        errors.append("supplemental_sources_missing")
        supplemental_sources = []
    required_fields = {
        "coverage_status",
        "freshness_status",
        "latency_status",
        "degradation_status",
        "corroboration_status",
        "evidence_basis",
        "routing_boundary",
    }
    for row in [*canonical_sources, *supplemental_sources]:
        source_key = row.get("source_key", "unknown_source")
        missing = sorted(required_fields - set(row))
        if missing:
            errors.append(f"source_veracity_fields_missing:{source_key}:{','.join(missing)}")
        if not str(row.get("evidence_basis", "")).strip():
            errors.append(f"source_evidence_basis_missing:{source_key}")
        if not str(row.get("routing_boundary", "")).strip():
            errors.append(f"source_routing_boundary_missing:{source_key}")
        flags = row.get("authority_flags", {})
        if not isinstance(flags, dict):
            errors.append(f"authority_flags_missing:{source_key}")
            continue
        for field in VERACITY_AUTHORITY_FLAGS:
            if flags.get(field) is not False:
                errors.append(f"source_authority_enabled:{source_key}:{field}")
    for row in supplemental_sources:
        if row.get("source_key") == "yahoo_finance":
            if row.get("canonical_source") is not False:
                errors.append("yahoo_marked_canonical")
            if row.get("corroboration_status") != "supplemental_hold_single_source_not_allowed":
                errors.append("yahoo_single_source_hold_missing")
        if row.get("source_key") == PREFERENCE_SOURCE_KEY:
            if row.get("canonical_source") is not False:
                errors.append("preference_mcp_marked_canonical")
            if row.get("source_role") != "supplemental_multi_source_data_plane":
                errors.append("preference_mcp_role_invalid")
            if "canonical_rank_impact_disallowed" not in row.get("reason_codes", []):
                errors.append("preference_mcp_rank_boundary_missing")
            if "preference_not_source_36" not in row.get("reason_codes", []):
                errors.append("preference_mcp_source_36_boundary_missing")
            if row.get("corroboration_status") not in {
                "supplemental_explicit_upstream_context_not_canonical",
                "supplemental_hold_provenance_required",
                "supplemental_hold_identity_blocked_not_canonical",
            }:
                errors.append("preference_mcp_corroboration_boundary_invalid")
    preference_policy = artifact.get("preference_mcp_policy", {})
    if isinstance(preference_policy, dict):
        if preference_policy.get("canonical_source") is not False:
            errors.append("preference_policy_marked_canonical")
        if preference_policy.get("source_36") is not False:
            errors.append("preference_policy_source_36")
        if preference_policy.get("canonical_rank_impact_allowed") is not False:
            errors.append("preference_policy_rank_impact_allowed")
        if preference_policy.get("source_quorum_credit_allowed") is not False:
            errors.append("preference_policy_source_quorum_credit_allowed")
        if int(preference_policy.get("source_promotion_promoted_decision_count", 0) or 0) != 0:
            errors.append("preference_policy_promoted_source_decision_present")
        if int(preference_policy.get("source_promotion_canonical_source_count_after", 0) or 0) != EXPECTED_SOURCE_COUNT:
            errors.append("preference_policy_source_count_after_mismatch")
    else:
        errors.append("preference_mcp_policy_missing")
    for key in (
        "trade_candidate_creation_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "fill_confirmation_authority",
        "receipt_evidence_authority",
        "reconciliation_truth_authority",
        "live_capital_enabled",
    ):
        if artifact.get(key) is not False:
            errors.append(f"artifact_authority_enabled:{key}")
    if artifact.get("authority_flag_violation_count") != 0:
        errors.append("authority_flag_violations_present")
    return errors


def write_data_veracity_audit(
    artifact: dict[str, Any],
    path: str | Path | None = None,
    *,
    settings: Settings | None = None,
) -> Path:
    output_path = Path(path or (_runtime_dir(settings) / "phase4_data_veracity_audit.json"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path
