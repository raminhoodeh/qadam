#!/usr/bin/env python3
"""Build and verify Wave E merger and independent evaluation truth."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_classical_discovery import run_classical_discovery  # noqa: E402
from orchestrator.qadam_discovery_contract_fixture import (  # noqa: E402
    build_wave_c_contract_fixture_batch,
)
from orchestrator.qadam_hybrid_candidate_merger import (  # noqa: E402
    HybridMergeContext,
    discovery_evidence_records,
    merge_hybrid_candidates,
    write_hybrid_candidate_state,
)
from orchestrator.qadam_independent_quantum_value import (  # noqa: E402
    evaluate_independent_quantum_value,
    no_holdout_evaluation_input,
    write_independent_evaluation_state,
)
from orchestrator.qadam_local_quantum_discovery import (  # noqa: E402
    QiskitLocalQuantumDiscoveryBackend,
)
from orchestrator.qadam_quantum_discovery_evidence import _runtime_dir  # noqa: E402


def _merge_context() -> HybridMergeContext:
    return HybridMergeContext(
        source_transform_key="wave-c-nonlinear-contract-features.v1",
        feature_pair=("source_density", "source_agreement"),
        economic_target="crude oil repricing",
        outcome_definition="BNO one-day directional return",
        relationship_key="source density x source agreement",
        direction_or_question="nonlinear interaction",
        horizon="one_day",
        regime="all_regimes",
        accepted_instruments=("BNO", "USO"),
        relationship="Source density and source agreement move together nonlinearly.",
        interpretation=(
            "A broad and mutually confirming source regime may precede crude-oil repricing."
        ),
        confirmation="Repeat the relationship on untouched point-in-time evidence.",
        falsifier="No holdout improvement over the matched classical baseline.",
        blocker="No empirical chronological holdout exists yet.",
        next_action="Backfill provider evidence and run independent evaluation.",
    )


def main() -> int:
    generated_at = datetime.now(timezone.utc).isoformat()
    batch = build_wave_c_contract_fixture_batch()
    classical = run_classical_discovery(batch)
    quantum = QiskitLocalQuantumDiscoveryBackend().run(
        batch,
        mode="ideal",
        matched_classical_result=classical,
    )
    evidence = [
        *discovery_evidence_records(classical),
        *discovery_evidence_records(quantum),
    ]
    hybrid_state = merge_hybrid_candidates(
        [_merge_context()],
        evidence,
        generated_at=generated_at,
    )
    candidate = hybrid_state["candidates"][0]
    evaluation_state = evaluate_independent_quantum_value(
        hybrid_state,
        [
            no_holdout_evaluation_input(
                candidate,
                shared_manifest_hash=batch.shared_manifest_hash,
            )
        ],
        evaluated_at=generated_at,
    )
    runtime_dir = _runtime_dir()
    hybrid_paths = write_hybrid_candidate_state(runtime_dir, hybrid_state)
    evaluation_paths = write_independent_evaluation_state(
        runtime_dir,
        evaluation_state,
    )
    result = evaluation_state["evaluations"][0]
    summary = evaluation_state["summary"]
    errors: list[str] = []
    if hybrid_state["summary"]["candidate_count"] != 1:
        errors.append("hybrid_candidate_count_invalid")
    if hybrid_state["summary"]["joint_candidate_count"] != 1:
        errors.append("joint_candidate_count_invalid")
    if hybrid_state["summary"]["provenance_count"] != 2:
        errors.append("hybrid_provenance_count_invalid")
    if candidate["validation_contribution"] != "not_tested":
        errors.append("hybrid_candidate_self_validated")
    if result["validation_contribution"] != "not_measurable":
        errors.append("current_verdict_not_honest")
    if result["measurability_blockers"] != [
        "empirical_untouched_holdout_missing"
    ]:
        errors.append("current_holdout_blocker_invalid")
    if summary["quantum_edge_claimed"] is not False:
        errors.append("quantum_edge_claimed_without_holdout")
    if summary["provider_call_attempted"] is not False:
        errors.append("provider_call_attempted")
    if summary["hardware_submission_attempted"] is not False:
        errors.append("hardware_submission_attempted")
    if any(
        summary[key] != 0
        for key in (
            "candidate_promotion_count",
            "validated_edge_count",
            "strategy_hypothesis_count",
            "trade_candidate_count",
            "paper_order_count",
        )
    ):
        errors.append("downstream_state_created")

    print(f"wave_e_generated_at={generated_at}")
    print(f"wave_e_shared_manifest_hash={batch.shared_manifest_hash}")
    print(f"wave_e_hybrid_candidate_id={candidate['candidate_id']}")
    print(f"wave_e_discovery_origin={candidate['discovery_origin']}")
    print(f"wave_e_evidence_record_count={candidate['evidence_record_count']}")
    print(f"wave_e_provenance_count={hybrid_state['summary']['provenance_count']}")
    print(f"wave_e_contract_fixture_only={candidate['contract_fixture_only']}")
    print(f"wave_e_validation_contribution={result['validation_contribution']}")
    print(f"wave_e_measurability_blockers={result['measurability_blockers']}")
    print(f"wave_e_quantum_edge_claimed={summary['quantum_edge_claimed']}")
    print(f"wave_e_provider_call_attempted={summary['provider_call_attempted']}")
    print(
        "wave_e_hardware_submission_attempted="
        f"{summary['hardware_submission_attempted']}"
    )
    print(f"wave_e_candidate_promotion_count={summary['candidate_promotion_count']}")
    print(f"wave_e_paper_order_count={summary['paper_order_count']}")
    print(f"wave_e_hybrid_summary_artifact={hybrid_paths['summary']}")
    print(f"wave_e_evaluation_summary_artifact={evaluation_paths['summary']}")
    print(f"wave_e_errors={errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
