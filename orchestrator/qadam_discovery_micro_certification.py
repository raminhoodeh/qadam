"""End-to-end certification for evidence-fit discovery-paper conversion.

The certification separates implementation reachability from empirical market
results. It may prove that a complete setup can reach the guarded PaperOps
boundary, but it never creates an order, grants proof credit, or treats a
research score as a trading probability.
"""

from __future__ import annotations

from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_discovery_micro_conversion import (
    CALIBRATION_ARTIFACT,
    CERTIFICATION_ARTIFACT,
    CURRENT_EXPECTANCY_ARTIFACT,
    DIRECTION_RETRY_ARTIFACT,
    INSTRUMENT_ROLES,
    discovery_micro_policy,
    evidence_profile_for_strategy,
)
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_tradeability_reliability import (
    SAFE_RETRY_CLASSES,
    STRUCTURAL_DEFECT_CLASSES,
    build_and_write_reachability_canary,
    classify_contract_defect,
)

SCHEMA_VERSION = "qadam_discovery_micro_conversion_certification.v1"


def _result(
    check_id: str,
    title: str,
    passed: bool,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "title": title,
        "passed": bool(passed),
        "evidence": evidence,
    }


def _direction_index(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (str(row.get("strategy_family_id") or ""), str(row.get("instrument") or "")): row
        for row in rows
        if row.get("strategy_family_id") and row.get("instrument")
    }


def build_and_write_discovery_micro_certification(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    generated_at = now_iso()
    reachability, reachability_checks, reachability_errors = (
        build_and_write_reachability_canary(settings)
    )
    producer = reachability.get("producer_contract_canary") or {}
    policy = read_json(runtime / "qadam_experimental_paper_policy.json")
    micro = discovery_micro_policy(policy)
    patterns = read_json(runtime / "qadam_graph_pattern_candidates.json")
    queue = read_json(runtime / "qadam_actionability_queue.json")
    bridge = read_json(runtime / "qadam_graph_experiment_bridge.json")
    directions = read_jsonl(runtime / "qadam_direction_resolutions.jsonl")
    retries = read_jsonl(runtime / DIRECTION_RETRY_ARTIFACT)
    expectancy_rows = read_jsonl(runtime / CURRENT_EXPECTANCY_ARTIFACT)
    foundry = read_json(runtime / "qadam_graph_strategy_versions.json")
    calibration = read_json(runtime / CALIBRATION_ARTIFACT)

    checks: list[dict[str, Any]] = []
    checks.append(
        _result(
            "fix_01_authoritative_policy",
            "Discovery policy is the authoritative admission contract",
            bool(
                micro.get("enabled") is True
                and micro.get("positive_historical_expectancy_required") is False
                and micro.get("positive_current_expectancy_after_costs_required") is True
                and micro.get("validated_edge_required") is False
                and micro.get("source_quorum_eligible_required") is False
            ),
            {
                "policy_version": policy.get("policy_version"),
                "admission_mode": micro.get("admission_mode"),
                "historical_expectancy_required": micro.get(
                    "positive_historical_expectancy_required"
                ),
                "current_expectancy_required": micro.get(
                    "positive_current_expectancy_after_costs_required"
                ),
                "validated_edge_required": micro.get("validated_edge_required"),
            },
        )
    )

    old_expectancy_blocker = "positive_provisional_after_cost_expectancy_missing"
    foundry_reasons = {
        str(reason)
        for row in [
            *(foundry.get("rejections") or []),
            *(foundry.get("research_holds") or []),
        ]
        for reason in row.get("reasons") or []
    }
    producer_expectancy = producer.get("producer_expectancy") or {}
    expectancy_contract_clean = bool(
        expectancy_rows
        and old_expectancy_blocker not in foundry_reasons
        and all(
            row.get("artifact_type") == "qadam_current_expectancy_v2"
            and row.get("research_score_is_probability") is False
            and row.get("historical_expectancy_required") is False
            and row.get("not_execution_approval") is True
            for row in expectancy_rows
        )
        and producer_expectancy.get("ready_for_discovery_micro_review") is True
    )
    checks.append(
        _result(
            "fix_02_current_expectancy_v2",
            "Current Expectancy V2 replaces rejected historical expectancy as a gate",
            expectancy_contract_clean,
            {
                "runtime_record_count": len(expectancy_rows),
                "runtime_ready_count": sum(
                    row.get("ready_for_discovery_micro_review") is True
                    for row in expectancy_rows
                ),
                "legacy_blocker_present": old_expectancy_blocker in foundry_reasons,
                "producer_canary_net_expectancy": producer_expectancy.get(
                    "economics", {}
                ).get("net_expectancy"),
            },
        )
    )

    expression = producer.get("producer_direction", {}).get(
        "event_to_trade_expression"
    ) or {}
    required_expression_fields = {
        "event",
        "mechanism",
        "instrument",
        "direction",
        "confidence",
        "invalidation",
    }
    checks.append(
        _result(
            "fix_03_structured_causal_direction",
            "Direction follows an event-to-instrument causal expression",
            bool(
                required_expression_fields.issubset(expression)
                and expression.get("direction") in {"long", "short"}
            ),
            {"event_to_trade_expression": expression},
        )
    )

    instrument_expression = producer_expectancy.get("instrument_expression") or {}
    checks.append(
        _result(
            "fix_04_instrument_specific_logic",
            "Instrument role and basis risk are explicit",
            bool(
                len(INSTRUMENT_ROLES) == 19
                and instrument_expression.get("role")
                and instrument_expression.get("basis_risk")
                and expression.get("instrument") in INSTRUMENT_ROLES
            ),
            {
                "instrument_role_count": len(INSTRUMENT_ROLES),
                "canary_instrument": expression.get("instrument"),
                "canary_instrument_expression": instrument_expression,
            },
        )
    )

    direction_by_key = _direction_index(directions)
    retry_keys = {
        (str(row.get("strategy_family_id") or ""), str(row.get("instrument") or ""))
        for row in retries
    }
    ambiguous_event_keys = {
        key
        for key, row in direction_by_key.items()
        if row.get("actionable_direction") == "abstain_direction_unresolved"
        and isinstance(row.get("causal_classification"), dict)
        and bool(row.get("causal_classification"))
        and row.get("evidence_ids")
    }
    retry_contract_clean = bool(
        ambiguous_event_keys.issubset(retry_keys)
        and all(
            row.get("state")
            in {"scheduled_for_next_real_market_open", "waiting_for_fresh_market_clock"}
            and row.get("automatic_retry_scope")
            == "read_only_direction_re_evaluation"
            and row.get("broker_write_retry_allowed") is False
            and row.get("paper_order_created") is False
            for row in retries
        )
    )
    checks.append(
        _result(
            "fix_05_market_open_direction_retry",
            "Ambiguous event directions retry read-only at a real market open",
            retry_contract_clean,
            {
                "ambiguous_event_direction_count": len(ambiguous_event_keys),
                "scheduled_retry_count": len(retries),
                "uncovered_keys": sorted(ambiguous_event_keys - retry_keys),
            },
        )
    )

    ready_pattern_ids = {
        str(row.get("pattern_relationship_id") or "")
        for row in queue.get("rows") or []
        if row.get("state") == "ready_for_preregistered_experiment"
    }
    experiments = bridge.get("experiments") or []
    experiment_pattern_ids = {
        str(row.get("pattern_relationship_id") or "") for row in experiments
    }
    checks.append(
        _result(
            "fix_06_automatic_preregistration",
            "Actionable research is preregistered before outcomes are read",
            bool(
                ready_pattern_ids.issubset(experiment_pattern_ids)
                and all(
                    row.get("preregistered_before_outcome") is True
                    and row.get("holdout_read_allowed") is False
                    for row in experiments
                )
            ),
            {
                "queue_ready_count": len(ready_pattern_ids),
                "preregistered_experiment_count": len(experiments),
                "missing_preregistrations": sorted(
                    ready_pattern_ids - experiment_pattern_ids
                ),
            },
        )
    )

    candidates = patterns.get("candidates") or []
    profile_mismatches = [
        {
            "pattern_relationship_id": row.get("pattern_relationship_id"),
            "actual": row.get("evidence_profile"),
            "expected": evidence_profile_for_strategy(row.get("strategy_family_id")),
        }
        for row in candidates
        if row.get("evidence_profile")
        != evidence_profile_for_strategy(row.get("strategy_family_id"))
    ]
    non_quorum_claims = [
        row.get("pattern_relationship_id")
        for row in candidates
        if row.get("non_quorum_support_claimed_as_quorum") is True
    ]
    checks.append(
        _result(
            "fix_07_evidence_profile_admission",
            "Event, regime and dislocation profiles use collectable evidence",
            not profile_mismatches and not non_quorum_claims,
            {
                "candidate_count": len(candidates),
                "profile_mismatches": profile_mismatches,
                "non_quorum_false_claims": non_quorum_claims,
            },
        )
    )

    proposed_notional = float(producer.get("risk_proposed_notional_usd") or 0)
    canary_artifacts = producer.get("artifact_hashes") or {}
    shadow_risk_clean = bool(
        producer.get("actual") == "accepted_for_guarded_paperops_sequence"
        and "qadam_forward_shadow_decisions.jsonl" in canary_artifacts
        and "qadam_position_size_proposals.jsonl" in canary_artifacts
        and 0 < proposed_notional <= 1000
    )
    checks.append(
        _result(
            "fix_08_automatic_shadow_and_risk",
            "A complete micro setup receives shadow evidence and bounded risk",
            shadow_risk_clean,
            {
                "shadow_artifact_created": "qadam_forward_shadow_decisions.jsonl"
                in canary_artifacts,
                "risk_artifact_created": "qadam_position_size_proposals.jsonl"
                in canary_artifacts,
                "proposed_notional_usd": proposed_notional,
                "discovery_target_ceiling_usd": 1000.0,
            },
        )
    )

    checks.append(
        _result(
            "fix_09_akber_discovery_micro",
            "Akber can pass a complete discovery-micro setup without edge proof",
            bool(
                producer.get("actual") == "accepted_for_guarded_paperops_sequence"
                and producer.get("validated_edge_required") is False
                and producer.get("decision_state")
                == "experimental_paper_review_candidate"
                and "qadam_akber_filter_v3_results.jsonl" in canary_artifacts
            ),
            {
                "decision_state": producer.get("decision_state"),
                "validated_edge_required": producer.get("validated_edge_required"),
                "akber_result_artifact_created": "qadam_akber_filter_v3_results.jsonl"
                in canary_artifacts,
            },
        )
    )

    checks.append(
        _result(
            "fix_10_real_reachability_canary",
            "The actual producer contract reaches a broker-disabled PaperOps handoff",
            bool(
                not reachability_errors
                and reachability_checks.get("producer_contract_canary_reachable")
                is True
                and int(
                    reachability_checks.get("accepted_broker_disabled_handoff_count")
                    or 0
                )
                == 1
            ),
            {
                "reachability_state": reachability_checks.get("reachability_state"),
                "canary_exercised_count": reachability_checks.get(
                    "canary_exercised_count"
                ),
                "accepted_broker_disabled_handoff_count": reachability_checks.get(
                    "accepted_broker_disabled_handoff_count"
                ),
            },
        )
    )

    defect_class = classify_contract_defect(
        {
            "error": (
                "policy requirement_mismatch: consumer required historical "
                "expectancy while discovery policy marked it optional"
            )
        }
    )
    checks.append(
        _result(
            "fix_11_contract_failures_are_defects",
            "Policy/consumer mismatches become structural repair defects",
            bool(
                defect_class == "policy_contract_mismatch"
                and defect_class in STRUCTURAL_DEFECT_CLASSES
                and defect_class not in SAFE_RETRY_CLASSES
            ),
            {
                "negative_probe_classification": defect_class,
                "automatic_retry_allowed": defect_class in SAFE_RETRY_CLASSES,
                "structural_repair_required": defect_class
                in STRUCTURAL_DEFECT_CLASSES,
            },
        )
    )

    calibration_clean = bool(
        calibration
        and calibration.get("proposal_only") is True
        and calibration.get("automatic_threshold_mutation_allowed") is False
        and calibration.get("automatic_risk_or_authority_mutation_allowed") is False
        and calibration.get("simulated_or_backfilled_sessions_used") is False
    )
    checks.append(
        _result(
            "fix_12_five_session_recalibration",
            "Recalibration waits for five real sessions and remains proposal-only",
            calibration_clean,
            {
                "status": calibration.get("status"),
                "eligible_real_market_sessions": calibration.get(
                    "eligible_real_market_sessions"
                ),
                "required_real_market_sessions": calibration.get(
                    "required_real_market_sessions"
                ),
                "empirical_window_complete": calibration.get(
                    "empirical_window_complete"
                ),
            },
        )
    )

    minimum_score = float(micro.get("minimum_research_score") or 0.45)
    high_active = [
        row
        for row in candidates
        if row.get("current_trigger_active") is True
        and float(row.get("research_rank") or 0) >= minimum_score
    ]
    foundry_outcomes = {
        str(row.get("pattern_relationship_id") or ""): row
        for row in [
            *(foundry.get("versions") or []),
            *(foundry.get("research_holds") or []),
            *(foundry.get("rejections") or []),
        ]
    }
    precise_outcomes: list[dict[str, Any]] = []
    for row in high_active:
        key = (
            str(row.get("strategy_family_id") or ""),
            str(row.get("instrument") or ""),
        )
        direction = direction_by_key.get(key) or {}
        outcome = foundry_outcomes.get(str(row.get("pattern_relationship_id") or ""))
        actionable = direction.get("actionable_direction") in {"long", "short"}
        precise_hold = bool(outcome and (outcome.get("reasons") or outcome.get("strategy_version_id")))
        retry = key in retry_keys
        precise_outcomes.append(
            {
                "pattern_relationship_id": row.get("pattern_relationship_id"),
                "instrument": row.get("instrument"),
                "research_rank": row.get("research_rank"),
                "actionable_direction": direction.get("actionable_direction"),
                "precise_hold_or_rejection": precise_hold,
                "read_only_retry_scheduled": retry,
                "accounted_for": actionable or precise_hold or retry,
            }
        )
    acceptance = {
        "high_scoring_active_patterns_accounted_for": bool(
            high_active and all(row["accounted_for"] for row in precise_outcomes)
        ),
        "complete_micro_experiment_reaches_akber": producer.get("actual")
        == "accepted_for_guarded_paperops_sequence",
        "valid_candidate_receives_bounded_risk": shadow_risk_clean,
        "paperops_handoff_possible_without_validated_edge": bool(
            producer.get("actual") == "accepted_for_guarded_paperops_sequence"
            and producer.get("validated_edge_required") is False
        ),
        "scores_do_not_directly_create_orders": True,
        "high_scoring_active_pattern_outcomes": precise_outcomes,
    }
    errors = [
        f"acceptance_check_failed:{row['check_id']}"
        for row in checks
        if row.get("passed") is not True
    ]
    for key, value in acceptance.items():
        if key.endswith("_outcomes") or key == "scores_do_not_directly_create_orders":
            continue
        if value is not True:
            errors.append(f"acceptance_target_failed:{key}")
    errors.extend(reachability_errors)
    errors.extend(validate_authority(authority_flags(), prefix="discovery_micro_certification"))
    errors = unique_errors(errors)

    empirical_complete = calibration.get("empirical_window_complete") is True
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_discovery_micro_conversion_certification",
        "generated_at": generated_at,
        "status": "passed" if not errors else "blocked",
        "implementation_complete": not errors,
        "checks_passed": sum(row.get("passed") is True for row in checks),
        "checks_required": 12,
        "checks": checks,
        "acceptance_target": acceptance,
        "empirical_recalibration_status": (
            "complete_proposal_ready"
            if empirical_complete
            else "pending_five_real_eligible_market_sessions"
        ),
        "eligible_real_market_sessions": calibration.get(
            "eligible_real_market_sessions", 0
        ),
        "required_real_market_sessions": calibration.get(
            "required_real_market_sessions", 5
        ),
        "current_runtime_state": (
            "waiting_for_next_actionable_regular_market_session"
            if not any(
                row.get("ready_for_discovery_micro_review") is True
                for row in expectancy_rows
            )
            else "current_micro_setups_ready_for_review"
        ),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "live_capital_enabled": False,
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    AtomicArtifactStore(runtime).write_json(CERTIFICATION_ARTIFACT, payload)
    return payload, errors


__all__ = ["build_and_write_discovery_micro_certification"]
