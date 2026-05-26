#!/usr/bin/env python3
"""Run and validate the Phase 4 Trust Score recalculation."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.phase4_trust_scores import (  # noqa: E402
    build_trust_score_recalculation,
    validate_trust_score_recalculation,
    write_trust_score_recalculation,
)
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT  # noqa: E402


def main() -> int:
    errors: list[str] = []
    artifact = build_trust_score_recalculation()
    output_path = write_trust_score_recalculation(artifact)
    validation_errors = validate_trust_score_recalculation(artifact)

    changed_with_reasons = sum(1 for row in artifact["scores"] if row["score_delta"] != 0 and row["reason_codes"])
    below_threshold_quarantined = sum(
        1
        for row in artifact["scores"]
        if row["final_provisional_score"] < artifact["trust_score_quarantine_threshold"] and row["quarantine"]
    )
    upgraded_with_observation_evidence = sum(
        1
        for row in artifact["scores"]
        if row["score_delta"] > 0 and row["evidence_mode"] in {"durable_replay", "deterministic_sample"}
    )
    yahoo_rows = [row for row in artifact["supplemental_market_confirmation"] if row.get("source_key") == "yahoo_finance"]
    yahoo = yahoo_rows[0] if yahoo_rows else {}
    preference_rows = [
        row
        for row in artifact["supplemental_market_confirmation"]
        if row.get("source_key") == "preference_mcp"
    ]
    preference = preference_rows[0] if preference_rows else {}
    preference_policy = artifact.get("preference_mcp_policy", {})

    authority_probe = deepcopy(artifact)
    authority_probe["scores"][0]["authority_flags"]["paper_order_authority"] = True
    authority_probe_errors = validate_trust_score_recalculation(authority_probe)

    reason_probe = deepcopy(artifact)
    for row in reason_probe["scores"]:
        if row["score_delta"] != 0:
            row["reason_codes"] = []
            break
    reason_probe_errors = validate_trust_score_recalculation(reason_probe)

    yahoo_probe = deepcopy(artifact)
    yahoo_probe["supplemental_market_confirmation"][0]["score_included"] = True
    yahoo_probe_errors = validate_trust_score_recalculation(yahoo_probe)

    preference_probe = deepcopy(artifact)
    for row in preference_probe["supplemental_market_confirmation"]:
        if row.get("source_key") == "preference_mcp":
            row["score_included"] = True
            row["canonical_rank_impact_allowed"] = True
            row["source_quorum_credit_allowed"] = True
            break
    preference_probe_errors = validate_trust_score_recalculation(preference_probe)

    print("phase4_trust_score_status=" + ("ok" if not validation_errors else "error"))
    print(f"phase4_trust_score_schema_version={artifact['recalculation_schema_version']}")
    print(f"phase4_trust_score_artifact_path={output_path}")
    print(f"phase4_trust_score_count={artifact['score_count']}")
    print(f"phase4_trust_score_expected_count={artifact['expected_score_count']}")
    print(f"phase4_trust_score_observation_backed_count={artifact['observation_backed_count']}")
    print(f"phase4_trust_score_changed_count={artifact['changed_score_count']}")
    print(f"phase4_trust_score_changed_with_reasons={changed_with_reasons}")
    print(f"phase4_trust_score_upgraded_count={artifact['upgraded_score_count']}")
    print(f"phase4_trust_score_upgraded_with_observation_evidence={upgraded_with_observation_evidence}")
    print(f"phase4_trust_score_downgraded_count={artifact['downgraded_score_count']}")
    print(f"phase4_trust_score_quarantined_count={artifact['quarantined_source_count']}")
    print(f"phase4_trust_score_below_threshold_quarantined={below_threshold_quarantined}")
    print(f"phase4_trust_score_authority_flag_violation_count={artifact['authority_flag_violation_count']}")
    print(
        "phase4_trust_score_yahoo="
        f"score_included={yahoo.get('score_included')},"
        f"canonical_rank_impact_allowed={yahoo.get('canonical_rank_impact_allowed')},"
        f"role={yahoo.get('source_role')}"
    )
    print(
        "phase4_trust_score_preference="
        f"score_included={preference.get('score_included')},"
        f"canonical_rank_impact_allowed={preference.get('canonical_rank_impact_allowed')},"
        f"source_quorum_credit_allowed={preference.get('source_quorum_credit_allowed')},"
        f"role={preference.get('source_role')}"
    )
    print(
        "phase4_trust_score_preference_source_promotion="
        f"status={preference_policy.get('source_promotion_status')},"
        f"decisions={preference_policy.get('source_promotion_decision_count')},"
        f"promoted={preference_policy.get('source_promotion_promoted_decision_count')},"
        f"source_count_after={preference_policy.get('source_promotion_canonical_source_count_after')}"
    )
    print(f"phase4_trust_score_validation_error_count={len(validation_errors)}")
    print(f"phase4_trust_score_authority_probe_error_count={len(authority_probe_errors)}")
    print(f"phase4_trust_score_reason_probe_error_count={len(reason_probe_errors)}")
    print(f"phase4_trust_score_yahoo_probe_error_count={len(yahoo_probe_errors)}")
    print(f"phase4_trust_score_preference_probe_error_count={len(preference_probe_errors)}")
    print(f"phase4_trust_score_trade_candidate_creation_allowed={artifact['trade_candidate_creation_allowed']}")
    print(f"phase4_trust_score_execution_allowed={artifact['execution_allowed']}")
    print(f"phase4_trust_score_paper_order_allowed={artifact['paper_order_allowed']}")
    print(f"phase4_trust_score_broker_write_allowed={artifact['broker_write_allowed']}")
    print(f"phase4_trust_score_boundary={artifact['boundary']}")

    if validation_errors:
        errors.extend(validation_errors)
    if artifact["score_count"] != EXPECTED_SOURCE_COUNT:
        errors.append("score_count_mismatch")
    if changed_with_reasons != artifact["changed_score_count"]:
        errors.append("changed_scores_missing_reasons")
    if upgraded_with_observation_evidence != artifact["upgraded_score_count"]:
        errors.append("upgrades_without_observation_evidence")
    if artifact["authority_flag_violation_count"] != 0:
        errors.append("authority_flag_violation_count_not_zero")
    if not any(error.startswith("trust_score_authority_enabled:") for error in authority_probe_errors):
        errors.append("authority_probe_not_rejected")
    if not any(error.startswith("changed_score_missing_reason:") for error in reason_probe_errors):
        errors.append("reason_probe_not_rejected")
    if "yahoo_score_included" not in yahoo_probe_errors:
        errors.append("yahoo_score_probe_not_rejected")
    if yahoo.get("score_included") is not False or yahoo.get("canonical_rank_impact_allowed") is not False:
        errors.append("yahoo_affects_canonical_rank")
    if not preference:
        errors.append("preference_supplemental_rank_row_missing")
    elif (
        preference.get("score_included") is not False
        or preference.get("canonical_rank_impact_allowed") is not False
        or preference.get("source_quorum_credit_allowed") is not False
    ):
        errors.append("preference_affects_canonical_rank")
    if "preference_mcp_score_included" not in preference_probe_errors:
        errors.append("preference_score_probe_not_rejected")
    if "preference_mcp_canonical_rank_impact_allowed" not in preference_probe_errors:
        errors.append("preference_rank_probe_not_rejected")
    if "preference_mcp_source_quorum_credit_allowed" not in preference_probe_errors:
        errors.append("preference_source_quorum_probe_not_rejected")
    if preference_policy.get("source_promotion_status") != "validated":
        errors.append("preference_source_promotion_status_not_validated")
    if preference_policy.get("source_promotion_decision_count") != 6:
        errors.append("preference_source_promotion_decision_count_mismatch")
    if preference_policy.get("source_promotion_promoted_decision_count") != 0:
        errors.append("preference_source_promotion_promoted")
    if preference_policy.get("source_promotion_canonical_source_count_after") != EXPECTED_SOURCE_COUNT:
        errors.append("preference_source_promotion_source_count_mismatch")
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
            print(f"phase4_trust_score_error={error}")
        print("phase4_trust_score_recalculation_check=failed")
        return 1

    print("phase4_trust_score_recalculation_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
