"""Version trading rules separately from changing observations and research scores."""

from hashlib import sha256
import json
from typing import Any


def version_hypothesis(hypothesis: dict[str, Any]) -> dict[str, Any]:
    direction = hypothesis.get("direction_horizon", {})
    mapping = hypothesis.get("instrument_proxy_mapping", {})
    definition = {
        "contract_version": "paper-strategy-definition.1",
        "strategy_family_id": hypothesis.get("strategy_mapping", {}).get("strategy_family_id")
        or hypothesis.get("strategy_family_id"),
        "evidence_class": hypothesis.get("evidence_class"),
        "experimental_tier": hypothesis.get("experimental_tier"),
        "direction": direction.get("direction"), "horizon": direction.get("horizon"),
        "execution_proxy": mapping.get("execution_proxy"),
        "evidence_profile": hypothesis.get("pattern_lineage", {}).get("evidence_profile"),
        "source_recipe": hypothesis.get("candidate_identity_material", {}).get("source_recipe_fingerprint"),
        "entry_rule": hypothesis.get("entry_concept"),
        "exit_rules": hypothesis.get("invalidation_exit"),
        "risk_concept": hypothesis.get("risk_concept"),
        "evaluation_contract": {
            "version": "matched-forward.1", "benchmark": "SPY", "cost_bps": 5.0,
            "review_schedule": "20_then_doubling_nonoverlapping_events",
            "familywise_sign_test_alpha": 0.05,
            "multiplicity": "summable_registered_version_and_review_index_budget_two_comparators",
            "units": "decimal_return_after_costs", "no_trade_return": 0,
            "matched_benchmark_required": True, "independent_events_required": True,
            "retrospective_preregistration_allowed": False,
            "paper_returns_are_not_live_returns": True,
        },
    }
    digest = sha256(json.dumps(definition, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {**hypothesis, "strategy_version_id": "paper-strategy-version:" + digest[:24],
            "strategy_definition": definition, "strategy_definition_sha256": digest}
