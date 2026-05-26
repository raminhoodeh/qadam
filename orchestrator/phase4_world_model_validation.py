"""Phase 4 validation for private world-model lenses.

World-model claim cards can shape hypotheses and red-team prompts. They cannot
be factual evidence, signal confidence, trade triggers, approvals, orders,
broker truth, or live-capital authority.
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
from orchestrator.phase4_data_veracity import build_data_veracity_audit
from orchestrator.phase4_resource_validation import build_resource_validation
from orchestrator.world_model import world_model_claims, world_model_summary


WORLD_MODEL_VALIDATION_SCHEMA_VERSION = 1

WORLD_MODEL_VALIDATION_STATUSES: tuple[str, ...] = (
    "validated",
    "provisional",
    "rejected",
    "untestable",
)

WORLD_MODEL_AUTHORITY_FLAGS: tuple[str, ...] = (
    "factual_evidence_authority",
    "signal_confidence_authority",
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
    "quantum_provider_call_allowed",
    "quantum_hardware_submission_allowed",
    "scheduler_enabled",
)

SOURCE_ALIASES: dict[str, str] = {
    "x": "twitter_x",
}


@dataclass(frozen=True)
class WorldModelSourceCheck:
    requested_source: str
    source_key: str
    registered: bool
    durable_replay_observed: bool
    corroboration_status: str
    degraded_or_quarantined: bool
    evidence_basis: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WorldModelValidationRow:
    claim_key: str
    source_path: str
    claim_type: str
    validation_status: str
    observed_support: tuple[str, ...]
    observed_contradiction: tuple[str, ...]
    testability: str
    allowed_strategy_role: str
    evidence_boundary: str
    active_strategy_frame: bool
    confidence_increase_allowed: bool
    factual_evidence_allowed: bool
    trade_trigger_allowed: bool
    hypothesis_generation_allowed: bool
    red_team_prompt_allowed: bool
    private_prior_only: bool
    observable_signature_count: int
    market_channels: tuple[str, ...]
    source_checks: tuple[WorldModelSourceCheck, ...]
    durable_replay_source_count: int
    ready_source_count: int
    degraded_source_count: int
    missing_source_count: int
    authority_flags: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["observed_support"] = list(self.observed_support)
        payload["observed_contradiction"] = list(self.observed_contradiction)
        payload["market_channels"] = list(self.market_channels)
        payload["source_checks"] = [check.to_dict() for check in self.source_checks]
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
    return {flag: False for flag in WORLD_MODEL_AUTHORITY_FLAGS}


def _data_veracity_artifact(settings: Settings | None = None) -> dict[str, Any]:
    runtime_path = _runtime_dir(settings) / "phase4_data_veracity_audit.json"
    return _read_json(runtime_path) or build_data_veracity_audit(settings)


def _resource_validation_artifact(settings: Settings | None = None) -> dict[str, Any]:
    runtime_path = _runtime_dir(settings) / "phase4_resource_validation.json"
    return _read_json(runtime_path) or build_resource_validation(settings)


def _source_checks(claim: dict[str, Any], veracity: dict[str, Any]) -> tuple[WorldModelSourceCheck, ...]:
    rows = {
        str(row.get("source_key")): row
        for row in [
            *veracity.get("canonical_sources", []),
            *veracity.get("supplemental_sources", []),
        ]
        if row.get("source_key")
    }
    checks: list[WorldModelSourceCheck] = []
    for requested in claim.get("live_sources_to_check", ()):
        requested_source = str(requested)
        source_key = SOURCE_ALIASES.get(requested_source, requested_source)
        row = rows.get(source_key)
        checks.append(
            WorldModelSourceCheck(
                requested_source=requested_source,
                source_key=source_key,
                registered=row is not None,
                durable_replay_observed=row.get("coverage_status") == "durable_replay_observed" if row else False,
                corroboration_status=str(row.get("corroboration_status") or "not_registered") if row else "not_registered",
                degraded_or_quarantined=bool(row.get("quarantine")) if row else True,
                evidence_basis=str(row.get("evidence_basis") or "not_registered") if row else "not_registered",
            )
        )
    return tuple(checks)


def _validation_status(claim: dict[str, Any], checks: tuple[WorldModelSourceCheck, ...]) -> str:
    observable_signatures = claim.get("observable_signatures") or ()
    if not observable_signatures or not checks:
        return "untestable"
    observed_support: tuple[str, ...] = tuple(claim.get("observed_support") or ())
    observed_contradiction: tuple[str, ...] = tuple(claim.get("observed_contradiction") or ())
    if observed_contradiction:
        return "rejected"
    if observed_support and any(check.durable_replay_observed and not check.degraded_or_quarantined for check in checks):
        return "validated"
    if any(check.registered for check in checks):
        return "provisional"
    return "untestable"


def _testability(claim: dict[str, Any], checks: tuple[WorldModelSourceCheck, ...]) -> str:
    if not claim.get("observable_signatures"):
        return "untestable_no_observable_signatures"
    if not checks:
        return "untestable_no_source_checks"
    if any(check.durable_replay_observed for check in checks):
        return "testable_with_durable_replay_sources"
    if any(check.registered for check in checks):
        return "testable_with_registered_sources"
    return "untestable_sources_not_registered"


def _row_from_claim(claim: dict[str, Any], veracity: dict[str, Any]) -> WorldModelValidationRow:
    checks = _source_checks(claim, veracity)
    status = _validation_status(claim, checks)
    durable_count = sum(1 for check in checks if check.durable_replay_observed)
    ready_count = sum(1 for check in checks if check.durable_replay_observed and not check.degraded_or_quarantined)
    degraded_count = sum(1 for check in checks if check.degraded_or_quarantined)
    missing_count = sum(1 for check in checks if not check.registered)
    return WorldModelValidationRow(
        claim_key=str(claim["key"]),
        source_path=str(claim.get("source_path") or "unknown"),
        claim_type=str(claim.get("claim_type") or "unknown"),
        validation_status=status,
        observed_support=tuple(str(item) for item in claim.get("observed_support", ())),
        observed_contradiction=tuple(str(item) for item in claim.get("observed_contradiction", ())),
        testability=_testability(claim, checks),
        allowed_strategy_role="hypothesis_generation_and_red_team_prompt_only",
        evidence_boundary=(
            "World-model frames are private priors only. They can generate hypotheses and "
            "red-team prompts, but they are not factual evidence, signal confidence, trade "
            "triggers, approval authority, order authority, or live-capital authority."
        ),
        active_strategy_frame=False,
        confidence_increase_allowed=False,
        factual_evidence_allowed=False,
        trade_trigger_allowed=False,
        hypothesis_generation_allowed=True,
        red_team_prompt_allowed=True,
        private_prior_only=True,
        observable_signature_count=len(tuple(claim.get("observable_signatures") or ())),
        market_channels=tuple(str(channel) for channel in claim.get("market_channels", ())),
        source_checks=checks,
        durable_replay_source_count=durable_count,
        ready_source_count=ready_count,
        degraded_source_count=degraded_count,
        missing_source_count=missing_count,
        authority_flags=_authority_flags(),
    )


def build_world_model_validation(settings: Settings | None = None) -> dict[str, Any]:
    claims = world_model_claims()
    summary = world_model_summary()
    veracity = _data_veracity_artifact(settings)
    resource_validation = _resource_validation_artifact(settings)
    rows = [_row_from_claim(claim, veracity) for claim in claims]
    row_dicts = [row.to_dict() for row in rows]
    status_counts = Counter(row.validation_status for row in rows)
    authority_violations = [
        f"{row.claim_key}:{flag}"
        for row in rows
        for flag, enabled in row.authority_flags.items()
        if enabled is not False
    ]
    artifact = {
        "schema_version": PHASE4_ARTIFACT_SCHEMA_VERSION,
        "world_model_validation_schema_version": WORLD_MODEL_VALIDATION_SCHEMA_VERSION,
        "artifact_type": "world_model_validation",
        "artifact_id": "phase4:q4-6:world-model-lens-validation",
        "status": "validated" if not authority_violations else "rejected",
        "generated_at": _now(),
        "public_safe": True,
        "private_claim_text_redacted": True,
        "authority_boundary": phase4_authority_boundary(),
        "boundary": "World-model validation is a private hypothesis-lens report and cannot create execution authority.",
        "claim_count": len(rows),
        "validated_claim_count": status_counts["validated"],
        "provisional_claim_count": status_counts["provisional"],
        "rejected_claim_count": status_counts["rejected"],
        "untestable_claim_count": status_counts["untestable"],
        "active_strategy_frame_count": sum(1 for row in rows if row.active_strategy_frame),
        "observed_support_count": sum(len(row.observed_support) for row in rows),
        "observed_contradiction_count": sum(len(row.observed_contradiction) for row in rows),
        "confidence_increase_allowed_count": sum(1 for row in rows if row.confidence_increase_allowed),
        "factual_evidence_allowed_count": sum(1 for row in rows if row.factual_evidence_allowed),
        "trade_trigger_allowed_count": sum(1 for row in rows if row.trade_trigger_allowed),
        "durable_replay_source_check_count": sum(row.durable_replay_source_count for row in rows),
        "missing_source_check_count": sum(row.missing_source_count for row in rows),
        "authority_flag_violation_count": len(authority_violations),
        "authority_flag_violations": authority_violations,
        "evidence_boundary": "World-model frames are private priors, not factual evidence or trade triggers.",
        "allowed_strategy_role": "hypothesis_generation_and_red_team_prompt_only",
        "world_model_frames_are_factual_evidence": False,
        "world_model_frames_are_trade_triggers": False,
        "world_model_frames_can_increase_signal_confidence": False,
        "world_model_summary": {
            "corpus_dir": summary.get("corpus_dir"),
            "corpus_file_count": summary.get("corpus_file_count"),
            "claim_count": summary.get("claim_count"),
            "foundational_prior_count": summary.get("foundational_prior_count"),
        },
        "resource_validation_artifact_id": resource_validation.get("artifact_id"),
        "private_foundational_prior_count": resource_validation.get("private_foundational_prior_count"),
        "data_veracity_artifact_id": veracity.get("artifact_id"),
        "claims": row_dicts,
        "validation_statuses": list(WORLD_MODEL_VALIDATION_STATUSES),
        "status_counts": dict(sorted(status_counts.items())),
        "trade_candidate_creation_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
    }
    artifact["validation_errors"] = validate_world_model_validation(artifact)
    return artifact


def validate_world_model_validation(artifact: dict[str, Any]) -> list[str]:
    errors = list(validate_phase4_artifact(artifact))
    if artifact.get("artifact_type") != "world_model_validation":
        errors.append("artifact_type_not_world_model_validation")
    if artifact.get("world_model_frames_are_factual_evidence") is not False:
        errors.append("world_model_frames_marked_factual_evidence")
    if artifact.get("world_model_frames_are_trade_triggers") is not False:
        errors.append("world_model_frames_marked_trade_triggers")
    if artifact.get("world_model_frames_can_increase_signal_confidence") is not False:
        errors.append("world_model_frames_can_increase_signal_confidence")

    claims = artifact.get("claims")
    if not isinstance(claims, list):
        errors.append("world_model_claims_missing")
        claims = []
    if artifact.get("claim_count") != len(claims):
        errors.append("world_model_claim_count_mismatch")

    actual_counts = Counter(str(row.get("validation_status")) for row in claims)
    count_fields = {
        "validated": "validated_claim_count",
        "provisional": "provisional_claim_count",
        "rejected": "rejected_claim_count",
        "untestable": "untestable_claim_count",
    }
    for status, field in count_fields.items():
        if actual_counts.get(status, 0) != int(artifact.get(field, 0)):
            errors.append(f"world_model_status_count_mismatch:{status}")

    required_fields = {
        "validation_status",
        "observed_support",
        "observed_contradiction",
        "testability",
        "allowed_strategy_role",
        "evidence_boundary",
        "authority_flags",
    }
    active_count = 0
    for row in claims:
        claim_key = str(row.get("claim_key") or "unknown_claim")
        missing = sorted(required_fields - set(row))
        if missing:
            errors.append(f"world_model_fields_missing:{claim_key}:{','.join(missing)}")
        status = str(row.get("validation_status") or "")
        if status not in WORLD_MODEL_VALIDATION_STATUSES:
            errors.append(f"world_model_status_invalid:{claim_key}:{status}")
        observed_support = row.get("observed_support")
        observed_contradiction = row.get("observed_contradiction")
        if not isinstance(observed_support, list):
            errors.append(f"world_model_observed_support_invalid:{claim_key}")
            observed_support = []
        if not isinstance(observed_contradiction, list):
            errors.append(f"world_model_observed_contradiction_invalid:{claim_key}")
            observed_contradiction = []
        if not str(row.get("testability") or "").strip():
            errors.append(f"world_model_testability_missing:{claim_key}")
        if row.get("allowed_strategy_role") != "hypothesis_generation_and_red_team_prompt_only":
            errors.append(f"world_model_allowed_role_invalid:{claim_key}")
        if not str(row.get("evidence_boundary") or "").strip():
            errors.append(f"world_model_evidence_boundary_missing:{claim_key}")

        durable_ready = int(row.get("ready_source_count") or 0)
        if status == "validated" and not observed_support:
            errors.append(f"validated_claim_missing_observed_support:{claim_key}")
        if status == "validated" and durable_ready <= 0:
            errors.append(f"validated_claim_missing_durable_corroboration:{claim_key}")
        if observed_contradiction and status != "rejected":
            errors.append(f"contradicted_claim_not_rejected:{claim_key}")
        if status in {"rejected", "untestable"} and row.get("confidence_increase_allowed") is not False:
            errors.append(f"untestable_or_rejected_confidence_increase_allowed:{claim_key}")
        if row.get("factual_evidence_allowed") is not False:
            errors.append(f"world_model_factual_evidence_allowed:{claim_key}")
        if row.get("trade_trigger_allowed") is not False:
            errors.append(f"world_model_trade_trigger_allowed:{claim_key}")
        if row.get("private_prior_only") is not True:
            errors.append(f"world_model_private_prior_not_true:{claim_key}")
        if row.get("active_strategy_frame") is True:
            active_count += 1
            if status in {"rejected", "untestable"}:
                errors.append(f"active_world_model_frame_status_invalid:{claim_key}:{status}")
        source_checks = row.get("source_checks")
        if not isinstance(source_checks, list):
            errors.append(f"world_model_source_checks_missing:{claim_key}")
            source_checks = []
        if row.get("testability") == "testable_with_durable_replay_sources" and not any(
            check.get("durable_replay_observed") is True for check in source_checks
        ):
            errors.append(f"world_model_testability_without_durable_source:{claim_key}")

        flags = row.get("authority_flags")
        if not isinstance(flags, dict):
            errors.append(f"world_model_authority_flags_missing:{claim_key}")
            continue
        for flag in WORLD_MODEL_AUTHORITY_FLAGS:
            if flags.get(flag) is not False:
                errors.append(f"world_model_authority_enabled:{claim_key}:{flag}")

    if active_count != artifact.get("active_strategy_frame_count"):
        errors.append("active_strategy_frame_count_mismatch")
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


def write_world_model_validation(
    artifact: dict[str, Any],
    path: str | Path | None = None,
    *,
    settings: Settings | None = None,
) -> Path:
    output_path = Path(path or (_runtime_dir(settings) / "phase4_world_model_validation.json"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path
