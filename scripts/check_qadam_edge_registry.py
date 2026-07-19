#!/usr/bin/env python3
"""Build and validate OR-10 edge registry and Strategy Evidence Map V3."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_edge_registry import (  # noqa: E402
    CHECK_ARTIFACT,
    EDGE_REGISTRY_ARTIFACT,
    NEW_FAMILY_ARTIFACT,
    RETIREMENT_ARTIFACT,
    STRATEGY_MAP_ARTIFACT,
    SUMMARY_ARTIFACT,
    build_and_write_edge_registry,
)
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    _state, checks, errors = build_and_write_edge_registry(settings)
    for name in (
        EDGE_REGISTRY_ARTIFACT,
        SUMMARY_ARTIFACT,
        STRATEGY_MAP_ARTIFACT,
        RETIREMENT_ARTIFACT,
        NEW_FAMILY_ARTIFACT,
        CHECK_ARTIFACT,
    ):
        print(f"artifact={runtime / name}")
    for key in (
        "status",
        "implementation_ready",
        "acceptance_passed",
        "edge_count",
        "edge_validated_certification_passed",
        "paper_operator_ready_certification_passed",
        "valid_no_edge_outcome",
        "backtest_result_count",
        "backtest_rejected_result_count",
        "or9_input_matches_or8",
        "strategy_count",
        "strategy_class_counts",
        "paper_attention_strategy_count",
        "evidence_backed_strategy_count",
        "exploratory_strategy_count",
        "under_evidenced_strategy_count",
        "retirement_proposal_count",
        "new_family_proposal_count",
        "candidate_created_count",
        "qualified_setup_created_count",
        "order_created_count",
        "broker_write_count",
        "proof_credit_created_count",
    ):
        print(f"{key}={checks[key]}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 0 if checks.get("acceptance_passed") is True and not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
