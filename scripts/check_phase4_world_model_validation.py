#!/usr/bin/env python3
"""Run and validate the Phase 4 world-model lens validation report."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.phase4_world_model_validation import (  # noqa: E402
    build_world_model_validation,
    validate_world_model_validation,
    write_world_model_validation,
)


def main() -> int:
    errors: list[str] = []
    artifact = build_world_model_validation()
    output_path = write_world_model_validation(artifact)
    validation_errors = validate_world_model_validation(artifact)

    required_fields = {
        "validation_status",
        "observed_support",
        "observed_contradiction",
        "testability",
        "allowed_strategy_role",
        "evidence_boundary",
    }
    field_complete_count = sum(1 for row in artifact["claims"] if required_fields.issubset(set(row)))
    factual_evidence_count = sum(1 for row in artifact["claims"] if row["factual_evidence_allowed"])
    trade_trigger_count = sum(1 for row in artifact["claims"] if row["trade_trigger_allowed"])
    source_check_complete_count = sum(1 for row in artifact["claims"] if row["source_checks"])

    validated_probe = deepcopy(artifact)
    validated_probe["claims"][0]["validation_status"] = "validated"
    validated_probe["validated_claim_count"] = artifact["validated_claim_count"] + 1
    validated_probe["provisional_claim_count"] = artifact["provisional_claim_count"] - 1
    validated_probe_errors = validate_world_model_validation(validated_probe)

    untestable_probe = deepcopy(artifact)
    untestable_probe["claims"][0]["validation_status"] = "untestable"
    untestable_probe["claims"][0]["confidence_increase_allowed"] = True
    untestable_probe["untestable_claim_count"] = artifact["untestable_claim_count"] + 1
    untestable_probe["provisional_claim_count"] = artifact["provisional_claim_count"] - 1
    untestable_probe_errors = validate_world_model_validation(untestable_probe)

    authority_probe = deepcopy(artifact)
    authority_probe["claims"][0]["authority_flags"]["factual_evidence_authority"] = True
    authority_probe_errors = validate_world_model_validation(authority_probe)

    active_rejected_probe = deepcopy(artifact)
    active_rejected_probe["claims"][0]["validation_status"] = "rejected"
    active_rejected_probe["claims"][0]["active_strategy_frame"] = True
    active_rejected_probe["claims"][0]["observed_contradiction"] = ["probe_contradiction"]
    active_rejected_probe["active_strategy_frame_count"] = artifact["active_strategy_frame_count"] + 1
    active_rejected_probe["rejected_claim_count"] = artifact["rejected_claim_count"] + 1
    active_rejected_probe["provisional_claim_count"] = artifact["provisional_claim_count"] - 1
    active_rejected_probe_errors = validate_world_model_validation(active_rejected_probe)

    print("phase4_world_model_validation_status=" + ("ok" if not validation_errors else "error"))
    print(f"phase4_world_model_validation_schema_version={artifact['world_model_validation_schema_version']}")
    print(f"phase4_world_model_validation_artifact_path={output_path}")
    print(f"phase4_world_model_claim_count={artifact['claim_count']}")
    print(f"phase4_world_model_validated_claim_count={artifact['validated_claim_count']}")
    print(f"phase4_world_model_provisional_claim_count={artifact['provisional_claim_count']}")
    print(f"phase4_world_model_rejected_claim_count={artifact['rejected_claim_count']}")
    print(f"phase4_world_model_untestable_claim_count={artifact['untestable_claim_count']}")
    print(f"phase4_world_model_active_strategy_frame_count={artifact['active_strategy_frame_count']}")
    print(f"phase4_world_model_observed_support_count={artifact['observed_support_count']}")
    print(f"phase4_world_model_observed_contradiction_count={artifact['observed_contradiction_count']}")
    print(f"phase4_world_model_confidence_increase_allowed_count={artifact['confidence_increase_allowed_count']}")
    print(f"phase4_world_model_factual_evidence_allowed_count={artifact['factual_evidence_allowed_count']}")
    print(f"phase4_world_model_trade_trigger_allowed_count={artifact['trade_trigger_allowed_count']}")
    print(f"phase4_world_model_durable_replay_source_check_count={artifact['durable_replay_source_check_count']}")
    print(f"phase4_world_model_missing_source_check_count={artifact['missing_source_check_count']}")
    print(f"phase4_world_model_authority_flag_violation_count={artifact['authority_flag_violation_count']}")
    print(f"phase4_world_model_field_complete_count={field_complete_count}")
    print(f"phase4_world_model_source_check_complete_count={source_check_complete_count}")
    print(f"phase4_world_model_validation_error_count={len(validation_errors)}")
    print(f"phase4_world_model_validated_probe_error_count={len(validated_probe_errors)}")
    print(f"phase4_world_model_untestable_probe_error_count={len(untestable_probe_errors)}")
    print(f"phase4_world_model_authority_probe_error_count={len(authority_probe_errors)}")
    print(f"phase4_world_model_active_rejected_probe_error_count={len(active_rejected_probe_errors)}")
    print(f"phase4_world_model_trade_candidate_creation_allowed={artifact['trade_candidate_creation_allowed']}")
    print(f"phase4_world_model_execution_allowed={artifact['execution_allowed']}")
    print(f"phase4_world_model_paper_order_allowed={artifact['paper_order_allowed']}")
    print(f"phase4_world_model_broker_write_allowed={artifact['broker_write_allowed']}")
    print(f"phase4_world_model_boundary={artifact['boundary']}")

    if validation_errors:
        errors.extend(validation_errors)
    if artifact["claim_count"] != 5:
        errors.append("world_model_claim_count_mismatch")
    if artifact["validated_claim_count"] != 0:
        errors.append("unexpected_validated_world_model_claims")
    if artifact["provisional_claim_count"] != artifact["claim_count"]:
        errors.append("world_model_claims_not_all_provisional")
    if artifact["active_strategy_frame_count"] != 0:
        errors.append("unexpected_active_world_model_frames")
    if artifact["observed_support_count"] != 0:
        errors.append("unexpected_observed_support")
    if artifact["observed_contradiction_count"] != 0:
        errors.append("unexpected_observed_contradiction")
    if artifact["confidence_increase_allowed_count"] != 0:
        errors.append("world_model_confidence_increase_allowed")
    if factual_evidence_count != 0 or artifact["factual_evidence_allowed_count"] != 0:
        errors.append("world_model_factual_evidence_allowed")
    if trade_trigger_count != 0 or artifact["trade_trigger_allowed_count"] != 0:
        errors.append("world_model_trade_trigger_allowed")
    if artifact["missing_source_check_count"] != 0:
        errors.append("world_model_missing_source_checks")
    if field_complete_count != artifact["claim_count"]:
        errors.append("world_model_fields_incomplete")
    if source_check_complete_count != artifact["claim_count"]:
        errors.append("world_model_source_checks_incomplete")
    if artifact["authority_flag_violation_count"] != 0:
        errors.append("world_model_authority_flag_violation_count_not_zero")
    if not any(error.startswith("validated_claim_missing_observed_support:") for error in validated_probe_errors):
        errors.append("validated_probe_not_rejected")
    if not any(
        error.startswith("untestable_or_rejected_confidence_increase_allowed:")
        for error in untestable_probe_errors
    ):
        errors.append("untestable_probe_not_rejected")
    if not any(error.startswith("world_model_authority_enabled:") for error in authority_probe_errors):
        errors.append("authority_probe_not_rejected")
    if not any(error.startswith("active_world_model_frame_status_invalid:") for error in active_rejected_probe_errors):
        errors.append("active_rejected_probe_not_rejected")
    for key in (
        "trade_candidate_creation_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
    ):
        if artifact.get(key) is not False:
            errors.append(f"artifact_authority_enabled:{key}")

    if errors:
        for error in errors:
            print(f"phase4_world_model_validation_error={error}")
        print("phase4_world_model_validation_check=failed")
        return 1

    print("phase4_world_model_validation_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
