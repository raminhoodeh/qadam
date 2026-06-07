#!/usr/bin/env python3
"""Inspect the live Signal Integrity funnel and pin missing pricing-gap producers."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.signal_integrity import (  # noqa: E402
    signal_integrity_funnel_diagnostics_path,
    write_signal_integrity_funnel_diagnostics,
)


def main() -> int:
    settings = Settings.from_env()
    artifact = write_signal_integrity_funnel_diagnostics(settings=settings)
    print(f"signal_integrity_funnel_diagnostics_artifact_path={signal_integrity_funnel_diagnostics_path(settings)}")
    print(f"signal_integrity_funnel_pricing_gap_rollout_stage={artifact['pricing_gap_rollout_stage']}")
    print(f"signal_integrity_funnel_shadow_signal_count={artifact['shadow_signal_count']}")
    print(f"signal_integrity_funnel_review_count={artifact['review_count']}")
    print(
        "signal_integrity_funnel_signals_with_market_confirmation_count="
        f"{artifact['signals_with_market_confirmation_count']}"
    )
    print(
        "signal_integrity_funnel_signals_with_pricing_gap_evidence_count="
        f"{artifact['signals_with_pricing_gap_evidence_count']}"
    )
    print(
        "signal_integrity_funnel_signals_blocked_only_by_missing_pricing_gap_count="
        f"{artifact['signals_blocked_only_by_missing_pricing_gap_count']}"
    )
    print(
        "signal_integrity_funnel_signals_passed_to_risk_count="
        f"{artifact['signals_passed_to_risk_count']}"
    )
    print(
        "signal_integrity_funnel_risk_review_count="
        f"{artifact['risk_review_count']}"
    )
    print(
        "signal_integrity_funnel_risk_reviews_blocked_only_by_pricing_gap_policy_count="
        f"{artifact['risk_reviews_blocked_only_by_pricing_gap_policy_count']}"
    )
    print(
        "signal_integrity_funnel_stage_b_candidate_signal_count="
        f"{artifact['stage_b_candidate_signal_count']}"
    )
    print(
        "signal_integrity_funnel_flagged_missing_pricing_gap_producer_count="
        f"{artifact['flagged_missing_pricing_gap_producer_count']}"
    )
    print(
        "signal_integrity_funnel_flagged_missing_pricing_gap_producers="
        f"{','.join(artifact['flagged_missing_pricing_gap_producers'])}"
    )
    for summary in artifact.get("producer_summaries", []):
        generated_by = summary.get("generated_by", "unknown_generator")
        print(
            "producer_summary="
            f"{generated_by}"
            f"|signals={summary.get('signal_count', 0)}"
            f"|market_confirmation={summary.get('market_confirmation_signal_count', 0)}"
            f"|pricing_gap_confirmed={summary.get('pricing_gap_confirmed_signal_count', 0)}"
            f"|hold_missing_pricing_gap={summary.get('hold_missing_pricing_gap_count', 0)}"
            f"|likely_missing_producer={summary.get('likely_missing_pricing_gap_producer', False)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
