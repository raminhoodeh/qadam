#!/usr/bin/env python3
"""Run and validate the Phase 4 candidate strategy universe."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.phase4_candidate_strategy_universe import (  # noqa: E402
    FIRST_TRADING_UNIVERSE,
    build_candidate_strategy_universe,
    validate_candidate_strategy_universe,
    write_candidate_strategy_universe,
)


def main() -> int:
    errors: list[str] = []
    artifact = build_candidate_strategy_universe()
    output_path = write_candidate_strategy_universe(artifact)
    validation_errors = validate_candidate_strategy_universe(artifact)

    candidates = artifact["candidates"]
    no_trade_complete_count = sum(1 for candidate in candidates if candidate.get("no_trade_conditions"))
    invalidation_complete_count = sum(1 for candidate in candidates if candidate.get("invalidation_conditions"))
    preference_policy_complete_count = sum(
        1
        for candidate in candidates
        if candidate.get("preference_context_policy", {}).get("source_key") == "preference_mcp"
        and candidate.get("preference_context_policy", {}).get("approved_domain_pack_count", 0) > 0
        and candidate.get("preference_context_policy", {}).get("source_quorum_credit_allowed") is False
        and candidate.get("preference_context_policy", {}).get("preference_only_confirmation_allowed") is False
    )
    source_weight_complete_count = sum(
        1
        for candidate in candidates
        if set(candidate.get("source_weights", {})) == set(candidate.get("required_source_groups", []))
        and 0.995 <= sum(float(value) for value in candidate.get("source_weights", {}).values()) <= 1.005
    )
    decision_source_coverage_complete_count = sum(
        1
        for candidate in candidates
        if candidate.get("decision_source_coverage", {}).get("all_canonical_sources_considered") is True
        and candidate.get("decision_source_coverage", {}).get("decision_source_usage_complete") is True
        and candidate.get("decision_source_coverage", {}).get("source_quorum_bypass_allowed") is False
    )
    model_weight_complete_count = sum(
        1
        for candidate in candidates
        if 0.995 <= sum(float(value) for value in candidate.get("model_weights", {}).values()) <= 1.005
    )
    research_context_complete_count = sum(
        1 for candidate in candidates if isinstance(candidate.get("strategy_research_context"), dict)
    )
    research_context_with_matches_count = sum(
        1
        for candidate in candidates
        if candidate.get("strategy_research_context", {}).get("matched_research_candidate_count", 0) > 0
    )
    research_context_challenge_count = sum(
        int(candidate.get("strategy_research_context", {}).get("strategy_lead_challenge_count", 0) or 0)
        for candidate in candidates
    )

    object_type_probe = deepcopy(artifact)
    object_type_probe["candidates"][0]["object_type"] = "trade_candidate"
    object_type_probe_errors = validate_candidate_strategy_universe(object_type_probe)

    no_trade_probe = deepcopy(artifact)
    no_trade_probe["candidates"][0]["no_trade_conditions"] = []
    no_trade_probe_errors = validate_candidate_strategy_universe(no_trade_probe)

    risk_handoff_probe = deepcopy(artifact)
    risk_handoff_probe["candidates"][0]["risk_agent_handoff_allowed"] = True
    risk_handoff_probe["risk_agent_handoff_allowed_count"] = 1
    risk_handoff_probe_errors = validate_candidate_strategy_universe(risk_handoff_probe)

    authority_probe = deepcopy(artifact)
    authority_probe["candidates"][0]["authority_flags"]["execution_authority"] = True
    authority_probe_errors = validate_candidate_strategy_universe(authority_probe)

    yahoo_only_probe = deepcopy(artifact)
    yahoo_only_probe["candidates"][0]["market_confirmation_requirements"]["yahoo_only_confirmation_allowed"] = True
    yahoo_only_probe_errors = validate_candidate_strategy_universe(yahoo_only_probe)

    preference_source_quorum_probe = deepcopy(artifact)
    preference_source_quorum_probe["candidates"][0]["preference_context_policy"]["source_quorum_credit_allowed"] = True
    preference_source_quorum_probe_errors = validate_candidate_strategy_universe(preference_source_quorum_probe)

    preference_only_probe = deepcopy(artifact)
    preference_only_probe["candidates"][0]["preference_context_policy"]["preference_only_confirmation_allowed"] = True
    preference_only_probe_errors = validate_candidate_strategy_universe(preference_only_probe)

    preference_domain_probe = deepcopy(artifact)
    preference_domain_probe["candidates"][0]["preference_context_policy"]["approved_domain_pack_count"] = 0
    preference_domain_probe["preference_mcp_policy"]["candidate_family_with_domain_pack_count"] = (
        artifact["strategy_family_candidate_count"] - 1
    )
    preference_domain_probe_errors = validate_candidate_strategy_universe(preference_domain_probe)

    decision_source_coverage_probe = deepcopy(artifact)
    decision_source_coverage_probe["candidates"][0]["decision_source_coverage"][
        "decision_source_usage_complete"
    ] = False
    decision_source_coverage_errors = validate_candidate_strategy_universe(
        decision_source_coverage_probe
    )

    source_quorum_bypass_probe = deepcopy(artifact)
    source_quorum_bypass_probe["candidates"][0]["decision_source_coverage"][
        "source_quorum_bypass_allowed"
    ] = True
    source_quorum_bypass_errors = validate_candidate_strategy_universe(
        source_quorum_bypass_probe
    )

    research_authority_probe = deepcopy(artifact)
    research_authority_probe["candidates"][0]["strategy_research_context"]["trade_candidate_creation_allowed"] = True
    research_authority_errors = validate_candidate_strategy_universe(research_authority_probe)

    research_policy_probe = deepcopy(artifact)
    research_policy_probe["strategy_research_intake_policy"]["execution_allowed"] = True
    research_policy_errors = validate_candidate_strategy_universe(research_policy_probe)

    print("phase4_candidate_strategy_status=" + ("ok" if not validation_errors else "error"))
    print(f"phase4_candidate_strategy_schema_version={artifact['candidate_strategy_universe_schema_version']}")
    print(f"phase4_candidate_strategy_artifact_path={output_path}")
    print(f"phase4_candidate_strategy_first_universe_count={len(FIRST_TRADING_UNIVERSE)}")
    print(f"phase4_candidate_strategy_family_count={artifact['strategy_family_candidate_count']}")
    print(f"phase4_candidate_strategy_draft_hypothesis_count={artifact['draft_hypothesis_count']}")
    print(f"phase4_candidate_strategy_trade_candidate_count={artifact['trade_candidate_count']}")
    print(f"phase4_candidate_strategy_no_trade_complete_count={no_trade_complete_count}")
    print(f"phase4_candidate_strategy_invalidation_complete_count={invalidation_complete_count}")
    print(f"phase4_candidate_strategy_preference_policy_complete_count={preference_policy_complete_count}")
    print(f"phase4_candidate_strategy_source_weight_complete_count={source_weight_complete_count}")
    print(
        "phase4_candidate_strategy_decision_source_coverage_complete_count="
        f"{decision_source_coverage_complete_count}"
    )
    print(f"phase4_candidate_strategy_model_weight_complete_count={model_weight_complete_count}")
    print(f"phase4_candidate_strategy_research_context_complete_count={research_context_complete_count}")
    print(f"phase4_candidate_strategy_research_family_coverage={research_context_with_matches_count}")
    print(f"phase4_candidate_strategy_research_challenge_count={research_context_challenge_count}")
    print(f"phase4_candidate_strategy_risk_handoff_allowed_count={artifact['risk_agent_handoff_allowed_count']}")
    print(
        "phase4_candidate_strategy_execution_policy_handoff_allowed_count="
        f"{artifact['execution_policy_handoff_allowed_count']}"
    )
    print(f"phase4_candidate_strategy_execution_allowed_count={artifact['execution_allowed_count']}")
    print(f"phase4_candidate_strategy_paper_order_allowed_count={artifact['paper_order_allowed_count']}")
    print(f"phase4_candidate_strategy_broker_write_allowed_count={artifact['broker_write_allowed_count']}")
    print(f"phase4_candidate_strategy_live_capital_enabled_count={artifact['live_capital_enabled_count']}")
    print(f"phase4_candidate_strategy_authority_flag_violation_count={artifact['authority_flag_violation_count']}")
    print(f"phase4_candidate_strategy_validation_error_count={len(validation_errors)}")
    print(f"phase4_candidate_strategy_object_type_probe_error_count={len(object_type_probe_errors)}")
    print(f"phase4_candidate_strategy_no_trade_probe_error_count={len(no_trade_probe_errors)}")
    print(f"phase4_candidate_strategy_risk_handoff_probe_error_count={len(risk_handoff_probe_errors)}")
    print(f"phase4_candidate_strategy_authority_probe_error_count={len(authority_probe_errors)}")
    print(f"phase4_candidate_strategy_yahoo_only_probe_error_count={len(yahoo_only_probe_errors)}")
    print(
        "phase4_candidate_strategy_preference_source_quorum_probe_error_count="
        f"{len(preference_source_quorum_probe_errors)}"
    )
    print(
        "phase4_candidate_strategy_preference_only_probe_error_count="
        f"{len(preference_only_probe_errors)}"
    )
    print(
        "phase4_candidate_strategy_preference_domain_probe_error_count="
        f"{len(preference_domain_probe_errors)}"
    )
    print(
        "phase4_candidate_strategy_decision_source_coverage_probe_error_count="
        f"{len(decision_source_coverage_errors)}"
    )
    print(
        "phase4_candidate_strategy_source_quorum_bypass_probe_error_count="
        f"{len(source_quorum_bypass_errors)}"
    )
    print(
        "phase4_candidate_strategy_research_authority_probe_error_count="
        f"{len(research_authority_errors)}"
    )
    print(
        "phase4_candidate_strategy_research_policy_probe_error_count="
        f"{len(research_policy_errors)}"
    )
    print(
        "phase4_candidate_strategy_preference_domain_pack_count="
        f"{artifact['preference_mcp_policy']['approved_domain_pack_count']}"
    )
    print(
        "phase4_candidate_strategy_preference_family_coverage="
        f"{artifact['preference_mcp_policy']['candidate_family_with_domain_pack_count']}"
    )
    print(
        "phase4_candidate_strategy_research_candidate_count="
        f"{artifact['strategy_research_intake_policy']['research_candidate_count']}"
    )
    print(
        "phase4_candidate_strategy_research_policy_family_coverage="
        f"{artifact['strategy_research_intake_policy']['strategy_family_with_research_context_count']}"
    )
    print(f"phase4_candidate_strategy_trade_candidate_creation_allowed={artifact['trade_candidate_creation_allowed']}")
    print(f"phase4_candidate_strategy_execution_allowed={artifact['execution_allowed']}")
    print(f"phase4_candidate_strategy_paper_order_allowed={artifact['paper_order_allowed']}")
    print(f"phase4_candidate_strategy_broker_write_allowed={artifact['broker_write_allowed']}")
    print(f"phase4_candidate_strategy_boundary={artifact['boundary']}")

    if validation_errors:
        errors.extend(validation_errors)
    if artifact["strategy_family_candidate_count"] != len(FIRST_TRADING_UNIVERSE):
        errors.append("strategy_family_candidate_count_mismatch")
    if artifact["draft_hypothesis_count"] != artifact["strategy_family_candidate_count"]:
        errors.append("draft_hypothesis_count_mismatch")
    if artifact["trade_candidate_count"] != 0:
        errors.append("trade_candidate_count_not_zero")
    if no_trade_complete_count != artifact["strategy_family_candidate_count"]:
        errors.append("no_trade_conditions_incomplete")
    if invalidation_complete_count != artifact["strategy_family_candidate_count"]:
        errors.append("invalidation_conditions_incomplete")
    if preference_policy_complete_count != artifact["strategy_family_candidate_count"]:
        errors.append("preference_policy_incomplete")
    if source_weight_complete_count != artifact["strategy_family_candidate_count"]:
        errors.append("source_weights_incomplete")
    if decision_source_coverage_complete_count != artifact["strategy_family_candidate_count"]:
        errors.append("decision_source_coverage_incomplete")
    if model_weight_complete_count != artifact["strategy_family_candidate_count"]:
        errors.append("model_weights_incomplete")
    if research_context_complete_count != artifact["strategy_family_candidate_count"]:
        errors.append("research_context_incomplete")
    if research_context_with_matches_count < 4:
        errors.append("research_context_family_coverage_low")
    if research_context_challenge_count < 4:
        errors.append("research_context_challenges_missing")
    for key in (
        "risk_agent_handoff_allowed_count",
        "execution_policy_handoff_allowed_count",
        "execution_allowed_count",
        "paper_order_allowed_count",
        "broker_write_allowed_count",
        "live_capital_enabled_count",
        "authority_flag_violation_count",
    ):
        if artifact.get(key) != 0:
            errors.append(f"authority_count_not_zero:{key}")
    if not any(error.startswith("candidate_object_type_invalid:") for error in object_type_probe_errors):
        errors.append("object_type_probe_not_rejected")
    if not any(error.startswith("strategy_candidate_required_list_empty:") for error in no_trade_probe_errors):
        errors.append("no_trade_probe_not_rejected")
    if not any(error.startswith("strategy_candidate_risk_handoff_allowed:") for error in risk_handoff_probe_errors):
        errors.append("risk_handoff_probe_not_rejected")
    if not any(error.startswith("strategy_candidate_authority_flag_enabled:") for error in authority_probe_errors):
        errors.append("authority_probe_not_rejected")
    if not any(
        error.startswith("strategy_candidate_yahoo_only_confirmation_allowed:")
        for error in yahoo_only_probe_errors
    ):
        errors.append("yahoo_only_probe_not_rejected")
    if not any(
        error.startswith("strategy_candidate_preference_source_quorum_allowed:")
        for error in preference_source_quorum_probe_errors
    ):
        errors.append("preference_source_quorum_probe_not_rejected")
    if not any(
        error.startswith("strategy_candidate_preference_only_confirmation_allowed:")
        for error in preference_only_probe_errors
    ):
        errors.append("preference_only_probe_not_rejected")
    if not any(
        error.startswith("strategy_candidate_preference_domain_packs_missing:")
        for error in preference_domain_probe_errors
    ):
        errors.append("preference_domain_probe_not_rejected")
    if not any(
        error.startswith("strategy_candidate_decision_source_usage_incomplete:")
        for error in decision_source_coverage_errors
    ):
        errors.append("decision_source_coverage_probe_not_rejected")
    if not any(
        error.startswith("strategy_candidate_source_quorum_bypass_allowed:")
        for error in source_quorum_bypass_errors
    ):
        errors.append("source_quorum_bypass_probe_not_rejected")
    if not any(
        error.startswith("strategy_candidate_research_authority_enabled:")
        for error in research_authority_errors
    ):
        errors.append("research_authority_probe_not_rejected")
    if "strategy_research_intake_policy_authority_enabled:execution_allowed" not in research_policy_errors:
        errors.append("research_policy_probe_not_rejected")
    if artifact.get("preference_mcp_policy", {}).get("source_quorum_credit_allowed") is not False:
        errors.append("preference_policy_source_quorum_enabled")
    if artifact.get("preference_mcp_policy", {}).get("candidate_family_with_domain_pack_count") != artifact[
        "strategy_family_candidate_count"
    ]:
        errors.append("preference_policy_family_coverage_incomplete")
    research_policy = artifact.get("strategy_research_intake_policy", {})
    if research_policy.get("research_candidate_count") != 4:
        errors.append("research_policy_candidate_count_invalid")
    if research_policy.get("strategy_family_with_research_context_count", 0) < 4:
        errors.append("research_policy_family_coverage_low")
    if research_policy.get("strategy_lead_challenge_count", 0) < 4:
        errors.append("research_policy_challenges_missing")
    for key in (
        "trade_candidate_creation_allowed",
        "risk_handoff_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
    ):
        if research_policy.get(key) is not False:
            errors.append(f"research_policy_authority_enabled:{key}")
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
            print(f"phase4_candidate_strategy_error={error}")
        print("phase4_candidate_strategy_check=failed")
        return 1

    print("phase4_candidate_strategy_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
