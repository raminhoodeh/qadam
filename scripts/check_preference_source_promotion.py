#!/usr/bin/env python3
"""Validate PREF-12 Preference/PREF MCP upstream source-promotion decisions."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.preference_mcp_source_promotion import (  # noqa: E402
    PREFERENCE_SOURCE_PROMOTION_SCHEMA_VERSION,
    build_preference_source_promotion_decisions,
    validate_preference_source_promotion_decisions,
    write_preference_source_promotion_decisions,
)
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT  # noqa: E402


def main() -> int:
    errors: list[str] = []
    artifact = build_preference_source_promotion_decisions()
    output_path, history_path = write_preference_source_promotion_decisions(artifact)
    validation_errors = validate_preference_source_promotion_decisions(artifact)

    aggregator_probe = deepcopy(artifact)
    aggregator_probe["preference_aggregator_promoted"] = True
    aggregator_probe["preference_mcp_source_36"] = True
    aggregator_errors = validate_preference_source_promotion_decisions(aggregator_probe)

    source_count_probe = deepcopy(artifact)
    source_count_probe["canonical_source_count_after"] = EXPECTED_SOURCE_COUNT + 1
    source_count_probe["canonical_source_count_delta"] = 1
    source_count_errors = validate_preference_source_promotion_decisions(source_count_probe)

    promoted_without_gates_probe = deepcopy(artifact)
    promoted_without_gates_probe["decisions"][0]["promoted_to_canonical"] = True
    promoted_without_gates_probe["promoted_decision_count"] = 1
    promoted_without_gates_errors = validate_preference_source_promotion_decisions(
        promoted_without_gates_probe
    )

    authority_probe = deepcopy(artifact)
    authority_probe["broker_write_allowed"] = True
    authority_probe["authority_flags"]["broker_write_authority"] = True
    authority_errors = validate_preference_source_promotion_decisions(authority_probe)

    first_decision = artifact.get("first_concrete_registry_decision", {})
    existing_decisions = [
        decision for decision in artifact["decisions"] if decision.get("existing_registry_source") is True
    ]
    new_deferred = [
        decision for decision in artifact["decisions"] if decision.get("existing_registry_source") is not True
    ]
    source_count_stable = (
        artifact["canonical_source_count_before"]
        == artifact["canonical_source_count_after"]
        == EXPECTED_SOURCE_COUNT
    )

    print("preference_source_promotion_status=" + ("ok" if not validation_errors else "error"))
    print(f"preference_source_promotion_schema_version={PREFERENCE_SOURCE_PROMOTION_SCHEMA_VERSION}")
    print(f"preference_source_promotion_artifact_path={output_path}")
    print(f"preference_source_promotion_history_path={history_path}")
    print(f"preference_source_promotion_decision_count={artifact['decision_count']}")
    print(f"preference_source_promotion_promoted_decision_count={artifact['promoted_decision_count']}")
    print(
        "preference_source_promotion_existing_registry_decision_count="
        f"{artifact['existing_registry_decision_count']}"
    )
    print(
        "preference_source_promotion_new_source_deferred_count="
        f"{artifact['new_source_deferred_count']}"
    )
    print(
        "preference_source_promotion_source_count_before="
        f"{artifact['canonical_source_count_before']}"
    )
    print(
        "preference_source_promotion_source_count_after="
        f"{artifact['canonical_source_count_after']}"
    )
    print(f"preference_source_promotion_source_count_stable={source_count_stable}")
    print(
        "preference_source_promotion_aggregator_promoted="
        f"{artifact['preference_aggregator_promoted']}"
    )
    print(
        "preference_source_promotion_first_decision="
        f"{first_decision.get('upstream_source')}:"
        f"{first_decision.get('registry_decision')}:"
        f"{first_decision.get('promotion_status')}"
    )
    print(
        "preference_source_promotion_existing_sources="
        + ",".join(str(decision.get("candidate_registry_source_key")) for decision in existing_decisions)
    )
    print(
        "preference_source_promotion_deferred_sources="
        + ",".join(str(decision.get("upstream_source")) for decision in new_deferred)
    )
    print(f"preference_source_promotion_validation_error_count={len(validation_errors)}")
    print(f"preference_source_promotion_aggregator_probe_error_count={len(aggregator_errors)}")
    print(f"preference_source_promotion_source_count_probe_error_count={len(source_count_errors)}")
    print(
        "preference_source_promotion_promoted_without_gates_probe_error_count="
        f"{len(promoted_without_gates_errors)}"
    )
    print(f"preference_source_promotion_authority_probe_error_count={len(authority_errors)}")
    print(
        "preference_source_promotion_source_quorum_credit_allowed="
        f"{artifact['source_quorum_credit_allowed']}"
    )
    print(
        "preference_source_promotion_canonical_rank_impact_allowed="
        f"{artifact['canonical_rank_impact_allowed']}"
    )
    print(
        "preference_source_promotion_trade_candidate_creation_allowed="
        f"{artifact['trade_candidate_creation_allowed']}"
    )
    print(f"preference_source_promotion_broker_write_allowed={artifact['broker_write_allowed']}")
    print(f"preference_source_promotion_live_capital_enabled={artifact['live_capital_enabled']}")
    print(f"preference_source_promotion_boundary={artifact['boundary']}")

    if validation_errors:
        errors.extend(validation_errors)
    if artifact["status"] != "validated":
        errors.append("promotion_status_not_validated")
    if artifact["decision_count"] != 6:
        errors.append("promotion_decision_count_mismatch")
    if artifact["promoted_decision_count"] != 0:
        errors.append("unexpected_promoted_decision")
    if artifact["existing_registry_decision_count"] != 4:
        errors.append("existing_registry_decision_count_mismatch")
    if artifact["new_source_deferred_count"] != 2:
        errors.append("new_source_deferred_count_mismatch")
    if source_count_stable is not True:
        errors.append("source_count_not_stable")
    if first_decision.get("upstream_source") != "kalshi":
        errors.append("first_registry_decision_not_stable")
    if artifact["preference_aggregator_promoted"] is not False:
        errors.append("aggregator_promoted")
    if artifact["preference_mcp_source_36"] is not False:
        errors.append("preference_mcp_source_36")
    if "preference_aggregator_promoted" not in aggregator_errors:
        errors.append("aggregator_probe_not_rejected")
    if "canonical_source_count_after_mismatch" not in source_count_errors:
        errors.append("source_count_probe_not_rejected")
    if not any(error.startswith("promoted_without_gate:") for error in promoted_without_gates_errors):
        errors.append("promoted_without_gates_probe_not_rejected")
    if "authority_flag_enabled:broker_write_authority" not in authority_errors:
        errors.append("authority_probe_not_rejected")
    for key in (
        "source_quorum_credit_allowed",
        "canonical_rank_impact_allowed",
        "trade_candidate_creation_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
    ):
        if artifact.get(key) is not False:
            errors.append(f"promotion_authority_enabled:{key}")

    if errors:
        for error in errors:
            print(f"preference_source_promotion_error={error}")
        print("preference_source_promotion_check=failed")
        return 1

    print("preference_source_promotion_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
