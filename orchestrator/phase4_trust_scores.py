"""Phase 4 Trust Score recalculation.

This module preserves the Phase 1 seed score for every canonical source and
adds a Phase 4 provisional score derived from read-only data veracity evidence.
It cannot route execution, paper orders, broker writes, reconciliation, or live
capital.
"""

from __future__ import annotations

import json
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
from orchestrator.phase4_data_veracity import build_data_veracity_audit
from orchestrator.preference_mcp_identity import PREFERENCE_SOURCE_KEY
from orchestrator.preference_mcp_source_promotion import (
    build_preference_source_promotion_decisions,
    preference_source_promotion_paths,
)
from orchestrator.trust_scores import build_trust_score_seed
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT


TRUST_SCORE_RECALCULATION_SCHEMA_VERSION = 1
TRUST_SCORE_QUARANTINE_THRESHOLD = 0.3
QUARANTINE_SCORE_CAP = 0.29

TRUST_SCORE_AUTHORITY_FLAGS: tuple[str, ...] = (
    "signal_authority",
    "trade_candidate_creation_allowed",
    "risk_approval_authority",
    "execution_authority",
    "paper_order_authority",
    "broker_write_authority",
    "fill_confirmation_authority",
    "receipt_evidence_authority",
    "reconciliation_truth_authority",
    "live_capital_authority",
)


@dataclass(frozen=True)
class TrustScoreRecalculationRow:
    source_key: str
    source_name: str
    canonical_source: bool
    pipeline: str
    tier: int
    seed_score: float
    seed_basis: str
    seed_evidence_status: str
    observed_score: float
    final_provisional_score: float
    score_delta: float
    score_change_direction: str
    evidence_mode: str
    evidence_basis: str
    reason_codes: tuple[str, ...]
    quarantine: bool
    quarantine_reasons: tuple[str, ...]
    routing_boundary: str
    authority_flags: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["reason_codes"] = list(self.reason_codes)
        payload["quarantine_reasons"] = list(self.quarantine_reasons)
        return payload


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _authority_flags() -> dict[str, bool]:
    return {flag: False for flag in TRUST_SCORE_AUTHORITY_FLAGS}


def _data_veracity_artifact(settings: Settings | None = None) -> dict[str, Any]:
    runtime_path = _runtime_dir(settings) / "phase4_data_veracity_audit.json"
    return _read_json(runtime_path) or build_data_veracity_audit(settings)


def _preference_source_promotion(settings: Settings | None = None) -> dict[str, Any]:
    promotion_path, _history_path = preference_source_promotion_paths(settings)
    return _read_json(promotion_path) or build_preference_source_promotion_decisions(
        settings=settings,
    )


def _evidence_mode(veracity: dict[str, Any]) -> str:
    if veracity.get("coverage_status") == "durable_replay_observed":
        return "durable_replay"
    if veracity.get("source_role") == "supplemental_market_confirmation":
        return "supplemental_market_confirmation"
    if veracity.get("source_role") == "supplemental_multi_source_data_plane":
        return "supplemental_multi_source_data_plane"
    if "sample" in str(veracity.get("evidence_basis", "")):
        return "deterministic_sample"
    return "registered_prior"


def _score_adjustment(veracity: dict[str, Any]) -> tuple[float, list[str]]:
    adjustment = 0.0
    reasons: list[str] = []
    if veracity.get("coverage_status") == "durable_replay_observed":
        adjustment += 0.03
        reasons.append("durable_replay_observed")
    if veracity.get("freshness_status") == "fresh_replay_snapshot":
        adjustment += 0.02
        reasons.append("fresh_replay_snapshot")
    if veracity.get("corroboration_status") == "corroboration_ready_read_only":
        adjustment += 0.03
        reasons.append("corroboration_ready_read_only")
    if veracity.get("latency_status") == "latency_observed":
        adjustment += 0.01
        reasons.append("latency_observed")
    degradation = str(veracity.get("degradation_status") or "")
    if degradation.startswith("degraded:missing_credentials"):
        adjustment -= 0.22
        reasons.append("missing_credentials_penalty")
    elif degradation.startswith("degraded:needs_clarity"):
        adjustment -= 0.18
        reasons.append("needs_clarity_penalty")
    elif degradation.startswith("degraded"):
        adjustment -= 0.16
        reasons.append("degraded_evidence_penalty")
    if veracity.get("corroboration_status") == "registered_context_only":
        reasons.append("registered_context_only_no_corroboration_bonus")
    return adjustment, reasons


def _direction(delta: float) -> str:
    if delta > 0:
        return "up"
    if delta < 0:
        return "down"
    return "unchanged"


def _recalculate_row(seed: dict[str, Any], veracity: dict[str, Any]) -> TrustScoreRecalculationRow:
    seed_score = float(seed["score"])
    adjustment, adjustment_reasons = _score_adjustment(veracity)
    observed_score = max(0.0, min(0.95, seed_score + adjustment))
    quarantine_reasons: list[str] = []
    if veracity.get("quarantine") is True:
        quarantine_reasons.append("data_veracity_quarantine")
    if observed_score < TRUST_SCORE_QUARANTINE_THRESHOLD:
        quarantine_reasons.append("below_trust_threshold")
    final_score = observed_score
    if quarantine_reasons:
        final_score = min(observed_score, QUARANTINE_SCORE_CAP)
        adjustment_reasons.append("quarantine_cap_applied")
    final_score = round(final_score, 2)
    observed_score = round(observed_score, 2)
    delta = round(final_score - seed_score, 2)
    reasons = [
        f"seed_basis:{seed['basis']}",
        f"seed_evidence:{seed['evidence_status']}",
        f"evidence_mode:{_evidence_mode(veracity)}",
        *adjustment_reasons,
        *[f"veracity:{reason}" for reason in veracity.get("reason_codes", [])],
    ]
    return TrustScoreRecalculationRow(
        source_key=str(seed["source_key"]),
        source_name=str(veracity.get("source_name") or seed["source_key"]),
        canonical_source=True,
        pipeline=str(seed["pipeline"]),
        tier=int(seed["tier"]),
        seed_score=seed_score,
        seed_basis=str(seed["basis"]),
        seed_evidence_status=str(seed["evidence_status"]),
        observed_score=observed_score,
        final_provisional_score=final_score,
        score_delta=delta,
        score_change_direction=_direction(delta),
        evidence_mode=_evidence_mode(veracity),
        evidence_basis=str(veracity.get("evidence_basis") or "unknown"),
        reason_codes=tuple(dict.fromkeys(reasons)),
        quarantine=bool(quarantine_reasons),
        quarantine_reasons=tuple(dict.fromkeys(quarantine_reasons)),
        routing_boundary=(
            "Phase 4 Trust Scores can inform strategy review only. They cannot route signals, "
            "trade candidates, orders, broker writes, fills, receipts, reconciliation, or live capital."
        ),
        authority_flags=_authority_flags(),
    )


def build_trust_score_recalculation(settings: Settings | None = None) -> dict[str, Any]:
    seed_payload = build_trust_score_seed(settings)
    veracity = _data_veracity_artifact(settings)
    preference_source_promotion = _preference_source_promotion(settings)
    veracity_by_key = {row["source_key"]: row for row in veracity.get("canonical_sources", [])}
    rows: list[TrustScoreRecalculationRow] = []
    for seed in seed_payload["seeds"]:
        source_key = seed["source_key"]
        veracity_row = veracity_by_key.get(source_key)
        if veracity_row is None:
            veracity_row = {
                "source_key": source_key,
                "source_name": source_key,
                "coverage_status": "missing_veracity_row",
                "freshness_status": "freshness_unavailable",
                "latency_status": "latency_unavailable",
                "degradation_status": "degraded:missing_veracity_row",
                "corroboration_status": "cannot_corroborate_missing_veracity",
                "evidence_basis": "missing_data_veracity_audit_row",
                "reason_codes": ["missing_veracity_row"],
                "quarantine": True,
            }
        rows.append(_recalculate_row(seed, veracity_row))

    supplemental_market_confirmation = []
    for supplemental in veracity.get("supplemental_sources", []):
        supplemental_market_confirmation.append(
            {
                "source_key": supplemental.get("source_key"),
                "source_role": supplemental.get("source_role"),
                "canonical_source": False,
                "score_included": False,
                "canonical_rank_impact_allowed": False,
                "source_quorum_credit_allowed": False,
                "evidence_basis": supplemental.get("evidence_basis"),
                "evidence_mode": _evidence_mode(supplemental),
                "corroboration_status": supplemental.get("corroboration_status"),
                "reason_codes": supplemental.get("reason_codes", []),
                "routing_boundary": supplemental.get("routing_boundary"),
                "authority_flags": _authority_flags(),
            }
        )

    row_dicts = [row.to_dict() for row in rows]
    changed_rows = [row for row in rows if row.score_delta != 0]
    upgraded_rows = [row for row in rows if row.score_delta > 0]
    downgraded_rows = [row for row in rows if row.score_delta < 0]
    quarantined_rows = [row for row in rows if row.quarantine]
    observation_backed_rows = [row for row in rows if row.evidence_mode in {"durable_replay", "deterministic_sample"}]
    authority_violations = [
        f"{row.source_key}:{flag}"
        for row in rows
        for flag, enabled in row.authority_flags.items()
        if enabled is not False
    ]
    artifact = {
        "schema_version": PHASE4_ARTIFACT_SCHEMA_VERSION,
        "recalculation_schema_version": TRUST_SCORE_RECALCULATION_SCHEMA_VERSION,
        "artifact_type": "trust_score_recalculation",
        "artifact_id": "phase4:q4-4:trust-score-recalculation",
        "status": "validated" if not authority_violations else "rejected",
        "generated_at": _now(),
        "public_safe": True,
        "authority_boundary": phase4_authority_boundary(),
        "boundary": "Trust Score recalculation is read-only strategy evidence and cannot create execution authority.",
        "score_count": len(rows),
        "expected_score_count": EXPECTED_SOURCE_COUNT,
        "observation_backed_count": len(observation_backed_rows),
        "changed_score_count": len(changed_rows),
        "upgraded_score_count": len(upgraded_rows),
        "downgraded_score_count": len(downgraded_rows),
        "quarantined_source_count": len(quarantined_rows),
        "trust_score_quarantine_threshold": TRUST_SCORE_QUARANTINE_THRESHOLD,
        "quarantine_score_cap": QUARANTINE_SCORE_CAP,
        "authority_flag_violation_count": len(authority_violations),
        "authority_flag_violations": authority_violations,
        "seed_boundary": seed_payload["boundary"],
        "data_veracity_artifact_id": veracity.get("artifact_id"),
        "data_veracity_generated_at": veracity.get("generated_at"),
        "scores": row_dicts,
        "supplemental_market_confirmation": supplemental_market_confirmation,
        "yahoo_finance_policy": {
            "score_included": False,
            "canonical_rank_impact_allowed": False,
            "market_confirmation_only": True,
            "single_source_market_confirmation_status": "hold",
            "boundary": (
                "Yahoo Finance can add supplemental market-confirmation notes only; it cannot change "
                "canonical source rank or provide broker, fill, receipt, reconciliation, order, or live-capital truth."
            ),
        },
        "preference_mcp_policy": {
            "score_included": False,
            "canonical_rank_impact_allowed": False,
            "source_quorum_credit_allowed": False,
            "market_confirmation_only": False,
            "supplemental_data_plane_only": True,
            "source_36": False,
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
            "boundary": (
                "Preference/PREF MCP can add supplemental upstream-context notes only; it cannot change "
                "canonical source rank, satisfy strategy source quorum by itself, provide broker, fill, "
                "receipt, reconciliation, order, or live-capital truth, or become source 36 without an "
                "explicit source-registry promotion decision for a specific upstream source."
            ),
        },
        "trade_candidate_creation_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
    }
    artifact["validation_errors"] = validate_phase4_artifact(artifact)
    return artifact


def validate_trust_score_recalculation(artifact: dict[str, Any]) -> list[str]:
    errors = list(validate_phase4_artifact(artifact))
    if artifact.get("artifact_type") != "trust_score_recalculation":
        errors.append("artifact_type_not_trust_score_recalculation")
    if artifact.get("score_count") != EXPECTED_SOURCE_COUNT:
        errors.append("score_count_mismatch")
    scores = artifact.get("scores")
    if not isinstance(scores, list):
        errors.append("scores_missing")
        scores = []
    required_fields = {
        "seed_score",
        "observed_score",
        "final_provisional_score",
        "score_delta",
        "evidence_basis",
        "evidence_mode",
        "reason_codes",
        "quarantine",
        "authority_flags",
    }
    for row in scores:
        source_key = row.get("source_key", "unknown_source")
        missing = sorted(required_fields - set(row))
        if missing:
            errors.append(f"trust_score_fields_missing:{source_key}:{','.join(missing)}")
        if row.get("canonical_source") is not True:
            errors.append(f"canonical_score_not_canonical:{source_key}")
        if row.get("score_delta") != 0 and not row.get("reason_codes"):
            errors.append(f"changed_score_missing_reason:{source_key}")
        if row.get("score_delta", 0) > 0 and row.get("evidence_mode") not in {"durable_replay", "deterministic_sample"}:
            errors.append(f"upgrade_without_observation_evidence:{source_key}")
        if row.get("final_provisional_score", 1.0) < TRUST_SCORE_QUARANTINE_THRESHOLD and row.get("quarantine") is not True:
            errors.append(f"below_threshold_not_quarantined:{source_key}")
        flags = row.get("authority_flags", {})
        if not isinstance(flags, dict):
            errors.append(f"authority_flags_missing:{source_key}")
            continue
        for flag in TRUST_SCORE_AUTHORITY_FLAGS:
            if flags.get(flag) is not False:
                errors.append(f"trust_score_authority_enabled:{source_key}:{flag}")
    supplemental = artifact.get("supplemental_market_confirmation")
    if not isinstance(supplemental, list):
        errors.append("supplemental_market_confirmation_missing")
        supplemental = []
    for row in supplemental:
        if row.get("source_key") == "yahoo_finance":
            if row.get("score_included") is not False:
                errors.append("yahoo_score_included")
            if row.get("canonical_rank_impact_allowed") is not False:
                errors.append("yahoo_canonical_rank_impact_allowed")
            if row.get("canonical_source") is not False:
                errors.append("yahoo_marked_canonical")
        if row.get("source_key") == PREFERENCE_SOURCE_KEY:
            if row.get("score_included") is not False:
                errors.append("preference_mcp_score_included")
            if row.get("canonical_rank_impact_allowed") is not False:
                errors.append("preference_mcp_canonical_rank_impact_allowed")
            if row.get("source_quorum_credit_allowed") is not False:
                errors.append("preference_mcp_source_quorum_credit_allowed")
            if row.get("canonical_source") is not False:
                errors.append("preference_mcp_marked_canonical")
            if row.get("evidence_mode") != "supplemental_multi_source_data_plane":
                errors.append("preference_mcp_evidence_mode_invalid")
    preference_policy = artifact.get("preference_mcp_policy", {})
    if not isinstance(preference_policy, dict):
        errors.append("preference_mcp_policy_missing")
    else:
        if preference_policy.get("score_included") is not False:
            errors.append("preference_policy_score_included")
        if preference_policy.get("canonical_rank_impact_allowed") is not False:
            errors.append("preference_policy_rank_impact_allowed")
        if preference_policy.get("source_quorum_credit_allowed") is not False:
            errors.append("preference_policy_source_quorum_credit_allowed")
        if preference_policy.get("source_36") is not False:
            errors.append("preference_policy_source_36")
        if int(preference_policy.get("source_promotion_promoted_decision_count", 0) or 0) != 0:
            errors.append("preference_policy_promoted_source_decision_present")
        if int(preference_policy.get("source_promotion_canonical_source_count_after", 0) or 0) != EXPECTED_SOURCE_COUNT:
            errors.append("preference_policy_source_count_after_mismatch")
    for key in (
        "trade_candidate_creation_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
    ):
        if artifact.get(key) is not False:
            errors.append(f"artifact_authority_enabled:{key}")
    if artifact.get("authority_flag_violation_count") != 0:
        errors.append("authority_flag_violations_present")
    return errors


def write_trust_score_recalculation(
    artifact: dict[str, Any],
    path: str | Path | None = None,
    *,
    settings: Settings | None = None,
) -> Path:
    output_path = Path(path or (_runtime_dir(settings) / "phase4_trust_score_recalculation.json"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path
