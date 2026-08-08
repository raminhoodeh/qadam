#!/usr/bin/env python3
"""Rebuild and certify the read-only EF-0 through EF-4 implementation."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_akber_filter_v3 import build_and_write_akber_filter_v3  # noqa: E402
from orchestrator.qadam_decision_evidence_packets import (  # noqa: E402
    INTEGRITY_ARTIFACT,
    PACKETS_ARTIFACT,
    REJECTIONS_ARTIFACT as PACKET_REJECTIONS_ARTIFACT,
    SUMMARY_ARTIFACT as PACKET_SUMMARY_ARTIFACT,
    build_and_write_decision_evidence_packets,
)
from orchestrator.qadam_evidence_fit_baseline import (  # noqa: E402
    BASELINE_ARTIFACT,
    DRIFT_ARTIFACT,
    OWNERSHIP_ARTIFACT,
    PHASE_STATUS_ARTIFACT,
    build_and_write_evidence_fit_baseline,
    write_evidence_fit_phase_status,
)
from orchestrator.qadam_strategy_foundry_v3 import build_and_write_strategy_foundry_v3  # noqa: E402
from orchestrator.qadam_strategy_translation import (  # noqa: E402
    DIRECTIONS_ARTIFACT,
    FORMATIONS_ARTIFACT,
    REJECTIONS_ARTIFACT as TRANSLATION_REJECTIONS_ARTIFACT,
    SUMMARY_ARTIFACT as TRANSLATION_SUMMARY_ARTIFACT,
    build_and_write_strategy_translation,
)
from orchestrator.qadam_trigger_factory import (  # noqa: E402
    DISLOCATION_ARTIFACT,
    EVENT_ARTIFACT,
    REGIME_ARTIFACT,
    REJECTIONS_ARTIFACT as TRIGGER_REJECTIONS_ARTIFACT,
    SUMMARY_ARTIFACT as TRIGGER_SUMMARY_ARTIFACT,
    build_and_write_trigger_factory,
)
from orchestrator.qadam_universe_contract import (  # noqa: E402
    CHECK_ARTIFACT as UNIVERSE_CHECK_ARTIFACT,
    FRESHNESS_SLA_ARTIFACT,
    INSTRUMENT_REGISTRY_ARTIFACT,
    PROXY_REGISTRY_ARTIFACT,
    SOURCE_CONTRACT_ARTIFACT,
    build_and_write_universe_contract,
)


def main() -> int:
    _baseline, baseline_status, ef0_errors = build_and_write_evidence_fit_baseline()
    _universe, universe_checks, ef1_errors = build_and_write_universe_contract()
    _triggers, trigger_checks, ef2_errors = build_and_write_trigger_factory()
    _translation, translation_checks, ef3_errors = build_and_write_strategy_translation()
    _foundry, foundry_checks, foundry_errors = build_and_write_strategy_foundry_v3()
    _packets, packet_checks, ef4_errors = build_and_write_decision_evidence_packets()
    _akber, akber_checks, akber_errors = build_and_write_akber_filter_v3()

    status = write_evidence_fit_phase_status(
        {
            "EF-0": {
                "errors": ef0_errors,
                "checks": {"baseline_id": baseline_status.get("baseline_id")},
                "output_artifacts": [BASELINE_ARTIFACT, OWNERSHIP_ARTIFACT, DRIFT_ARTIFACT],
            },
            "EF-1": {
                "errors": ef1_errors,
                "checks": {
                    "source_count": universe_checks.get("source_count"),
                    "instrument_count": universe_checks.get("instrument_count"),
                },
                "output_artifacts": [
                    SOURCE_CONTRACT_ARTIFACT,
                    INSTRUMENT_REGISTRY_ARTIFACT,
                    PROXY_REGISTRY_ARTIFACT,
                    FRESHNESS_SLA_ARTIFACT,
                    UNIVERSE_CHECK_ARTIFACT,
                ],
            },
            "EF-2": {
                "errors": ef2_errors,
                "checks": {
                    "event_trigger_count": trigger_checks.get("event_trigger_count"),
                    "regime_observation_count": trigger_checks.get("regime_observation_count"),
                    "market_dislocation_count": trigger_checks.get("market_dislocation_count"),
                },
                "output_artifacts": [
                    EVENT_ARTIFACT,
                    REGIME_ARTIFACT,
                    DISLOCATION_ARTIFACT,
                    TRIGGER_SUMMARY_ARTIFACT,
                    TRIGGER_REJECTIONS_ARTIFACT,
                ],
            },
            "EF-3": {
                "errors": [*ef3_errors, *foundry_errors],
                "checks": {
                    "direction_resolution_count": translation_checks.get(
                        "direction_resolution_count"
                    ),
                    "emerging_strategy_formation_count": translation_checks.get(
                        "emerging_strategy_formation_count"
                    ),
                    "foundry_hypothesis_count": foundry_checks.get("hypothesis_count"),
                },
                "output_artifacts": [
                    DIRECTIONS_ARTIFACT,
                    TRANSLATION_REJECTIONS_ARTIFACT,
                    FORMATIONS_ARTIFACT,
                    TRANSLATION_SUMMARY_ARTIFACT,
                ],
            },
            "EF-4": {
                "errors": [*ef4_errors, *akber_errors],
                "checks": {
                    "decision_packet_count": packet_checks.get("packet_count"),
                    "mixed_generation_join_count": packet_checks.get("mixed_generation_join_count"),
                    "akber_input_count": akber_checks.get("input_count"),
                },
                "output_artifacts": [
                    PACKETS_ARTIFACT,
                    PACKET_SUMMARY_ARTIFACT,
                    PACKET_REJECTIONS_ARTIFACT,
                    INTEGRITY_ARTIFACT,
                ],
            },
        }
    )
    print(f"artifact={ROOT / 'data' / 'runtime' / PHASE_STATUS_ARTIFACT}")
    print(f"status={status['status']}")
    print(f"implemented_through_phase={status['implemented_through_phase']}")
    print(f"validation_error_count={status['validation_error_count']}")
    for error in status["validation_errors"]:
        print(f"error={error}")
    return 0 if status["implemented_through_phase"] == "EF-4" else 1


if __name__ == "__main__":
    raise SystemExit(main())
