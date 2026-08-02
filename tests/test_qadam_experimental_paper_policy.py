from __future__ import annotations

from orchestrator.qadam_experimental_paper_policy import (
    DISCOVERY_MICRO_TIER,
    EXPERIMENTAL_UNVALIDATED,
    LEGACY_TEST,
    VALIDATED_PAPER_STRATEGY,
    default_policy,
    evidence_class,
    experimental_tier,
    validate_class_lineage,
    validate_policy,
)


def _common_lineage() -> dict:
    return {
        "research_goal_id": "goal:test",
        "score_id": "score:test",
        "hypothesis_id": "hypothesis:test",
        "akber_result_id": "akber:test",
        "shadow_evidence_id": "shadow:test",
        "risk_proposal_id": "risk:test",
    }


def test_missing_evidence_class_defaults_to_legacy_without_upgrade() -> None:
    assert evidence_class({}) == LEGACY_TEST
    assert evidence_class({"evidence_class": "unknown"}) == LEGACY_TEST


def test_experimental_lineage_requires_pattern_and_forbids_edge_claim() -> None:
    lineage = {**_common_lineage(), "pattern_relationship_id": "pattern:test"}
    assert validate_class_lineage(EXPERIMENTAL_UNVALIDATED, lineage) == []
    lineage["edge_id"] = "edge:test"
    assert "experimental_lineage_must_not_claim_edge_id" in validate_class_lineage(
        EXPERIMENTAL_UNVALIDATED, lineage
    )


def test_validated_lineage_still_requires_edge() -> None:
    lineage = _common_lineage()
    assert "missing_lineage:edge_id" in validate_class_lineage(
        VALIDATED_PAPER_STRATEGY, lineage
    )
    lineage["edge_id"] = "edge:test"
    assert validate_class_lineage(VALIDATED_PAPER_STRATEGY, lineage) == []


def test_policy_is_paper_only_and_frozen() -> None:
    policy = default_policy("2026-07-19T00:00:00+00:00")
    assert validate_policy(policy) == []
    assert policy["live_capital_enabled"] is False
    assert policy["risk"]["absolute_trade_ceiling_usd"] == 5000.0
    assert policy["risk"]["discovery_micro_trade_ceiling_usd"] == 500.0
    assert policy["risk"]["maximum_concurrent_discovery_micro_positions"] == 1
    assert policy["proof"]["validated_edge_credit_allowed"] is False


def test_discovery_micro_tier_is_explicit_and_cannot_expand_its_risk() -> None:
    record = {
        "evidence_class": EXPERIMENTAL_UNVALIDATED,
        "experimental_tier": DISCOVERY_MICRO_TIER,
    }
    assert experimental_tier(record) == DISCOVERY_MICRO_TIER

    policy = default_policy("2026-07-19T00:00:00+00:00")
    policy["risk"]["discovery_micro_trade_ceiling_usd"] = 5_000.0
    assert "experimental_policy_discovery_micro_ceiling_changed" in validate_policy(
        policy
    )
