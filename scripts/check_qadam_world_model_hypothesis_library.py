#!/usr/bin/env python3
"""Build and certify Qadam Phase 3 world-model hypothesis library."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qadam_world_model_hypothesis_library import (
    DASHBOARD_SUMMARY_ARTIFACT,
    HYPOTHESES_ARTIFACT,
    MARKET_MAPPINGS_ARTIFACT,
    PRIMARY_ARTIFACT,
    RESEARCH_QUESTIONS_ARTIFACT,
    _paths,
    build_and_write_world_model_hypothesis_library,
    build_world_model_hypothesis_library,
    load_world_model_hypothesis_library,
    validate_negative_world_model_hypothesis_probes,
    validate_world_model_hypothesis_bundle,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    settings = Settings.from_env()
    if args.dry_run:
        bundle = build_world_model_hypothesis_library(settings)
        loaded = {
            "primary": bundle.primary,
            "hypotheses": bundle.hypotheses,
            "research_questions": bundle.research_questions,
            "market_mappings": bundle.market_mappings,
            "dashboard_summary": bundle.dashboard_summary,
        }
        written: dict[str, str] = {}
        validation_errors = validate_world_model_hypothesis_bundle(loaded)
    else:
        bundle, written, validation_errors = build_and_write_world_model_hypothesis_library(settings)
        loaded = load_world_model_hypothesis_library(settings)
        validation_errors.extend(validate_world_model_hypothesis_bundle(loaded))
        validation_errors.extend(validate_negative_world_model_hypothesis_probes(settings))
        paths = _paths(settings)
        for key in ("primary", "hypotheses", "research_questions", "market_mappings", "dashboard_summary"):
            if not paths[key].exists():
                validation_errors.append(f"{paths[key].name}_missing")

    primary = bundle.primary
    dashboard = bundle.dashboard_summary
    print(f"primary={written.get('primary', PRIMARY_ARTIFACT)}")
    print(f"hypotheses={written.get('hypotheses', HYPOTHESES_ARTIFACT)}")
    print(f"research_questions={written.get('research_questions', RESEARCH_QUESTIONS_ARTIFACT)}")
    print(f"market_mappings={written.get('market_mappings', MARKET_MAPPINGS_ARTIFACT)}")
    print(f"dashboard_summary={written.get('dashboard_summary', DASHBOARD_SUMMARY_ARTIFACT)}")
    print(f"status={primary.get('status')}")
    print(f"hypothesis_count={primary.get('hypothesis_count')}")
    print(f"falsifiable_hypothesis_count={primary.get('falsifiable_hypothesis_count')}")
    print(f"research_question_count={primary.get('research_question_count')}")
    print(f"market_mapping_count={primary.get('market_mapping_count')}")
    print(f"mapped_market_count={dashboard.get('mapped_market_count')}")
    print(f"source_quorum_credit_allowed={primary.get('source_quorum_credit_allowed')}")
    print(f"trade_candidate_creation_allowed={primary.get('trade_candidate_creation_allowed')}")
    print(f"trade_candidate_created_count={primary.get('trade_candidate_created_count')}")
    print(f"paper_order_created_count={primary.get('paper_order_created_count')}")
    print(f"broker_write_count={primary.get('broker_write_count')}")
    print(f"live_capital_enabled={primary.get('live_capital_enabled')}")
    print(f"proof_credit_allowed={primary.get('proof_credit_allowed')}")
    print(f"validation_error_count={len(set(validation_errors))}")
    if validation_errors:
        for error in sorted(set(validation_errors)):
            print(f"error={error}")
        return 1
    print("qadam_world_model_hypothesis_library_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
