#!/usr/bin/env python3
"""Rebuild and certify EF-5 through EF-8 without granting trade authority."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_active_discovery_trial import (  # noqa: E402
    CERTIFICATION_ARTIFACT as TRIAL_CERTIFICATION_ARTIFACT,
    CHECK_ARTIFACT as TRIAL_CHECK_ARTIFACT,
    DASHBOARD_ARTIFACT as TRIAL_DASHBOARD_ARTIFACT,
    ELIGIBLE_DAYS_ARTIFACT,
    FUNNEL_ARTIFACT,
    ROOT_CAUSES_ARTIFACT,
    build_and_write_active_discovery_trial,
)
from orchestrator.qadam_akber_filter_v3 import (  # noqa: E402
    build_and_write_akber_filter_v3,
)
from orchestrator.qadam_akber_evidence_fit import (  # noqa: E402
    ABLATION_ARTIFACT,
    CHECK_ARTIFACT as AKBER_FIT_CHECK_ARTIFACT,
    POLICY_ARTIFACT as AKBER_FIT_POLICY_ARTIFACT,
    PROPOSALS_ARTIFACT as AKBER_FIT_PROPOSALS_ARTIFACT,
    REPLAY_ARTIFACT as AKBER_FIT_REPLAY_ARTIFACT,
    build_and_write_akber_evidence_fit,
)
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore  # noqa: E402
from orchestrator.qadam_decision_evidence_packets import (  # noqa: E402
    build_and_write_decision_evidence_packets,
)
from orchestrator.qadam_evidence_fit_baseline import (  # noqa: E402
    PHASE_STATUS_ARTIFACT,
    write_evidence_fit_phase_status,
)
from orchestrator.qadam_operator_ready_common import (  # noqa: E402
    authority_flags,
    now_iso,
    runtime_dir,
)
from orchestrator.qadam_outcome_learning_promotion import (  # noqa: E402
    ADMISSIONS_ARTIFACT,
    ATTRIBUTION_ARTIFACT,
    CHECK_ARTIFACT as LEARNING_CHECK_ARTIFACT,
    OUTCOMES_ARTIFACT,
    PROPOSALS_ARTIFACT as PROMOTION_PROPOSALS_ARTIFACT,
    VERSION_REGISTRY_ARTIFACT,
    build_and_write_outcome_learning_promotion,
)
from orchestrator.qadam_risk_router_alignment import (  # noqa: E402
    CHECK_ARTIFACT as RISK_ROUTER_CHECK_ARTIFACT,
    CONCENTRATION_ARTIFACT,
    ROOT_CAUSE_ARTIFACT as ROUTER_ROOT_CAUSE_ARTIFACT,
    SIZE_PROPOSALS_ARTIFACT,
    build_and_write_risk_router_alignment,
)
from orchestrator.qadam_strategy_foundry_v3 import (  # noqa: E402
    build_and_write_strategy_foundry_v3,
)
from orchestrator.qadam_strategy_translation import (  # noqa: E402
    build_and_write_strategy_translation,
)
from orchestrator.qadam_trigger_factory import (  # noqa: E402
    build_and_write_trigger_factory,
)

CHECK_ARTIFACT = "qadam_evidence_fit_phases_5_8_checks.json"


def main() -> int:
    _trigger_state, _trigger_checks, trigger_errors = build_and_write_trigger_factory()
    _translation_state, _translation_checks, translation_errors = (
        build_and_write_strategy_translation()
    )
    _foundry_state, _foundry_checks, foundry_errors = (
        build_and_write_strategy_foundry_v3()
    )
    _packet_state, _packet_checks, packet_errors = (
        build_and_write_decision_evidence_packets()
    )
    _akber_core_state, akber_core_checks, akber_core_errors = (
        build_and_write_akber_filter_v3()
    )
    _akber_state, akber_checks, ef5_errors = build_and_write_akber_evidence_fit()
    _risk_state, risk_checks, ef6_errors = build_and_write_risk_router_alignment()
    _trial_status, trial_checks, ef7_errors = build_and_write_active_discovery_trial()
    _learning_state, learning_checks, ef8_errors = (
        build_and_write_outcome_learning_promotion()
    )

    phase_status = write_evidence_fit_phase_status(
        {
            "EF-5": {
                "errors": [
                    *trigger_errors,
                    *translation_errors,
                    *foundry_errors,
                    *packet_errors,
                    *akber_core_errors,
                    *ef5_errors,
                ],
                "checks": {
                    "current_akber_status": akber_core_checks.get("status"),
                    "current_akber_input_count": akber_core_checks.get(
                        "input_count"
                    ),
                    "profile_count": akber_checks.get("profile_count"),
                    "profile_replay_count": akber_checks.get("profile_replay_count"),
                    "profile_ablation_count": akber_checks.get(
                        "profile_ablation_count"
                    ),
                    "threshold_change_applied_count": akber_checks.get(
                        "threshold_change_applied_count"
                    ),
                },
                "output_artifacts": [
                    AKBER_FIT_POLICY_ARTIFACT,
                    AKBER_FIT_REPLAY_ARTIFACT,
                    ABLATION_ARTIFACT,
                    AKBER_FIT_PROPOSALS_ARTIFACT,
                    AKBER_FIT_CHECK_ARTIFACT,
                ],
            },
            "EF-6": {
                "errors": ef6_errors,
                "checks": {
                    "channel_concentration_record_count": risk_checks.get(
                        "channel_concentration_record_count"
                    ),
                    "router_decision_count": risk_checks.get(
                        "router_decision_count"
                    ),
                    "risk_envelope_unchanged": risk_checks.get(
                        "risk_envelope_unchanged"
                    ),
                },
                "output_artifacts": [
                    CONCENTRATION_ARTIFACT,
                    SIZE_PROPOSALS_ARTIFACT,
                    ROUTER_ROOT_CAUSE_ARTIFACT,
                    RISK_ROUTER_CHECK_ARTIFACT,
                ],
            },
            "EF-7": {
                "errors": ef7_errors,
                "checks": {
                    "implementation_ready": trial_checks.get(
                        "implementation_ready"
                    ),
                    "empirical_trial_complete": trial_checks.get(
                        "empirical_trial_complete"
                    ),
                    "market_sessions_observed": trial_checks.get(
                        "market_sessions_observed"
                    ),
                    "eligible_market_days_observed": trial_checks.get(
                        "eligible_market_days_observed"
                    ),
                },
                "output_artifacts": [
                    FUNNEL_ARTIFACT,
                    ELIGIBLE_DAYS_ARTIFACT,
                    ROOT_CAUSES_ARTIFACT,
                    TRIAL_DASHBOARD_ARTIFACT,
                    TRIAL_CERTIFICATION_ARTIFACT,
                    TRIAL_CHECK_ARTIFACT,
                ],
            },
            "EF-8": {
                "errors": ef8_errors,
                "checks": {
                    "outcome_record_count": learning_checks.get(
                        "outcome_record_count"
                    ),
                    "mature_real_outcome_count": learning_checks.get(
                        "mature_real_outcome_count"
                    ),
                    "automatic_emerging_paper_admission_count": learning_checks.get(
                        "automatic_emerging_paper_admission_count"
                    ),
                    "risk_envelope_mutation_count": learning_checks.get(
                        "risk_envelope_mutation_count"
                    ),
                },
                "output_artifacts": [
                    OUTCOMES_ARTIFACT,
                    ATTRIBUTION_ARTIFACT,
                    PROMOTION_PROPOSALS_ARTIFACT,
                    ADMISSIONS_ARTIFACT,
                    VERSION_REGISTRY_ARTIFACT,
                    LEARNING_CHECK_ARTIFACT,
                ],
            },
        }
    )
    errors = [
        *trigger_errors,
        *translation_errors,
        *foundry_errors,
        *packet_errors,
        *akber_core_errors,
        *ef5_errors,
        *ef6_errors,
        *ef7_errors,
        *ef8_errors,
    ]
    aggregate = {
        "schema_version": "qadam_evidence_fit_phases_5_8_checks.v1",
        "artifact_type": "qadam_evidence_fit_phases_5_8_checks",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "implemented_through_phase": phase_status.get(
            "implemented_through_phase"
        ),
        "ef7_empirical_trial_complete": trial_checks.get(
            "empirical_trial_complete"
        ),
        "ef7_empirical_state": trial_checks.get("trial_state"),
        "automatic_emerging_paper_admission_count": learning_checks.get(
            "automatic_emerging_paper_admission_count"
        ),
        "paper_order_created_by_implementation_count": 0,
        "risk_envelope_mutation_count": learning_checks.get(
            "risk_envelope_mutation_count"
        ),
        "live_capital_enabled": False,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    AtomicArtifactStore(runtime_dir()).write_json(CHECK_ARTIFACT, aggregate)

    print(f"artifact={ROOT / 'data' / 'runtime' / CHECK_ARTIFACT}")
    print(f"phase_status_artifact={ROOT / 'data' / 'runtime' / PHASE_STATUS_ARTIFACT}")
    print(f"status={aggregate['status']}")
    print(f"implemented_through_phase={aggregate['implemented_through_phase']}")
    print(f"ef7_empirical_trial_complete={aggregate['ef7_empirical_trial_complete']}")
    print(f"validation_error_count={aggregate['validation_error_count']}")
    for error in errors:
        print(f"error={error}")
    return 0 if not errors and aggregate["implemented_through_phase"] == "EF-8" else 1


if __name__ == "__main__":
    raise SystemExit(main())
