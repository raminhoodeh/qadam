#!/usr/bin/env python3
"""Validate and write Qadam's quantum-optimized pattern recognition engine."""

from __future__ import annotations

from copy import deepcopy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.cockpit_status import build_cockpit_status  # noqa: E402
from orchestrator.config import Settings  # noqa: E402
from orchestrator.daily_edge_findings import build_daily_edge_findings_brief  # noqa: E402
from orchestrator.pattern_recognition_engine import (  # noqa: E402
    PATTERN_RECOGNITION_ENGINE_AUTHORITY_FALSE_FIELDS,
    PATTERN_RECOGNITION_ENGINE_FEATURE_VECTOR_LENGTH,
    PATTERN_RECOGNITION_ENGINE_JOB_TYPES,
    build_pattern_recognition_engine,
    validate_pattern_recognition_engine,
    write_pattern_recognition_engine,
)
from orchestrator.quantum_mandatory_review_gate import (  # noqa: E402
    build_quantum_mandatory_review_gate,
)


REPORT_PATH = ROOT / "data/runtime/pattern_recognition_engine_check.json"


def _blocked_quantum_gate(gate: dict[str, object]) -> dict[str, object]:
    blocked = deepcopy(gate)
    blocked["status"] = "quantum_review_gate_blocked"
    blocked["quantum_review_status"] = "provider_error"
    blocked["quantum_review_complete"] = False
    blocked["quantum_core_gate"] = False
    blocked["pattern_review_dependency_satisfied_count"] = 0
    blocked["pattern_review_dependency_blocked_count"] = blocked.get("candidate_pattern_count", 5)
    blocked["edge_validation_dependency_satisfied"] = False
    blocked["candidate_ranking_dependency_satisfied"] = False
    blocked["strategy_update_dependency_satisfied"] = False
    blocked["telegram_findings_dependency_satisfied"] = False
    blocked["fail_closed_reasons"] = ["synthetic_quantum_gate_probe"]
    effects = dict(blocked.get("downstream_effects", {}))
    effects["validated_edge_quantum_dependency_satisfied"] = False
    effects["candidate_ranking_dependency_satisfied"] = False
    effects["strategy_update_proposal_dependency_satisfied"] = False
    effects["telegram_review_body_dependency_satisfied"] = False
    blocked["downstream_effects"] = effects
    decisions: list[dict[str, object]] = []
    for raw_decision in blocked.get("pattern_gate_decisions", []):
        if not isinstance(raw_decision, dict):
            continue
        decision = deepcopy(raw_decision)
        decision["status"] = "blocked_pending_quantum_review"
        decision["review_complete"] = False
        decision["core_gate"] = False
        decision["dependency_satisfied"] = False
        decision["edge_validation_dependency_satisfied"] = False
        decision["candidate_ranking_dependency_satisfied"] = False
        decision["strategy_update_dependency_satisfied"] = False
        decision["paper_trade_consideration_quantum_dependency_satisfied"] = False
        decision["missing_requirements"] = ["synthetic_quantum_gate_probe"]
        decisions.append(decision)
    blocked["pattern_gate_decisions"] = decisions
    return blocked


def main() -> None:
    settings = Settings.from_env()
    cockpit_status = build_cockpit_status(settings)
    edge_tracker = cockpit_status["edge_tracker"]
    edge_ledger = cockpit_status["edge_pattern_ledger"]
    quantum_gate = build_quantum_mandatory_review_gate(edge_ledger=edge_ledger)
    daily_brief = build_daily_edge_findings_brief(cockpit_status=cockpit_status)
    engine = build_pattern_recognition_engine(
        edge_tracker=edge_tracker,
        edge_pattern_ledger=edge_ledger,
        quantum_gate=quantum_gate,
        daily_edge_findings=daily_brief,
    )
    validate_pattern_recognition_engine(engine)
    paths = write_pattern_recognition_engine(engine, settings=settings)

    errors: list[str] = []
    authority_leaks = [
        field
        for field in PATTERN_RECOGNITION_ENGINE_AUTHORITY_FALSE_FIELDS
        if engine.get(field) is not False
    ]
    if authority_leaks:
        errors.append("authority_leaks=" + ",".join(authority_leaks))
    pattern_authority_leaks = [
        pattern.get("pattern_id", pattern.get("sleeve_key", "unknown"))
        for pattern in engine["candidate_patterns"]
        if any(
            pattern.get(field) is not False
            for field in PATTERN_RECOGNITION_ENGINE_AUTHORITY_FALSE_FIELDS
        )
    ]
    if pattern_authority_leaks:
        errors.append("pattern_authority_leaks=" + ",".join(map(str, pattern_authority_leaks)))
    if engine["status"] != "pattern_engine_ready_for_quantum_oracle":
        errors.append(f"engine_not_ready={engine['status']}")
    if engine["source_scan"].get("mode") != "all_sources_every_sleeve":
        errors.append("source_scan_not_all_sources_every_sleeve")
    if engine["source_scan"].get("source_count", 0) < 30:
        errors.append("source_count_below_30")
    if engine["source_scan"].get("watched_instrument_count", 0) < 20:
        errors.append("watched_instrument_count_below_20")
    if engine["candidate_pattern_count"] != 5:
        errors.append("candidate_pattern_count_not_5")
    if engine["quantum_oracle_contract_accepted_count"] != 5:
        errors.append("oracle_contract_accepted_count_not_5")
    if engine["quantum_oracle_job_preview_count"] != 5 * len(PATTERN_RECOGNITION_ENGINE_JOB_TYPES):
        errors.append("oracle_job_preview_count_mismatch")
    if engine["quantum_optimization"].get("optimized_for_quantum_oracle") is not True:
        errors.append("not_optimized_for_quantum_oracle")
    if engine["quantum_optimization"].get("provider_call_allowed") is not False:
        errors.append("quantum_provider_call_allowed")
    if engine["quantum_optimization"].get("hardware_submission_allowed") is not False:
        errors.append("quantum_hardware_submission_allowed")
    if engine["quantum_optimization"].get("oracle_run_allowed") is not False:
        errors.append("quantum_oracle_run_allowed")
    if any(
        pattern.get("quantum_feature_vector_length")
        != PATTERN_RECOGNITION_ENGINE_FEATURE_VECTOR_LENGTH
        for pattern in engine["candidate_patterns"]
    ):
        errors.append("feature_vector_length_mismatch")

    blocked_probe = build_pattern_recognition_engine(
        edge_tracker=edge_tracker,
        edge_pattern_ledger=edge_ledger,
        quantum_gate=_blocked_quantum_gate(quantum_gate),
        daily_edge_findings=daily_brief,
    )
    validate_pattern_recognition_engine(blocked_probe)
    fail_closed_probe_rejected = (
        blocked_probe["status"] == "pattern_engine_blocked_pending_quantum_gate"
        and blocked_probe["candidate_pattern_count"] == 0
        and blocked_probe["quantum_oracle_contract_accepted_count"] == 0
        and blocked_probe["quantum_oracle_job_preview_count"] == 0
    )
    if not fail_closed_probe_rejected:
        errors.append("fail_closed_probe_not_rejected")

    feature_probe_rejected = False
    feature_probe = deepcopy(engine)
    feature_probe["candidate_patterns"][0]["quantum_feature_vector"] = [0.1, 0.2]
    try:
        validate_pattern_recognition_engine(feature_probe)
    except ValueError:
        feature_probe_rejected = True
    if not feature_probe_rejected:
        errors.append("feature_probe_not_rejected")

    authority_probe_rejected = False
    authority_probe = deepcopy(engine)
    authority_probe["candidate_patterns"][0]["paper_order_allowed"] = True
    try:
        validate_pattern_recognition_engine(authority_probe)
    except ValueError:
        authority_probe_rejected = True
    if not authority_probe_rejected:
        errors.append("authority_probe_not_rejected")

    report = {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "engine_status": engine["status"],
        "source_count": engine["source_scan"]["source_count"],
        "watched_instrument_count": engine["source_scan"]["watched_instrument_count"],
        "candidate_pattern_count": engine["candidate_pattern_count"],
        "feature_vector_length": PATTERN_RECOGNITION_ENGINE_FEATURE_VECTOR_LENGTH,
        "oracle_job_type_count": len(PATTERN_RECOGNITION_ENGINE_JOB_TYPES),
        "quantum_oracle_contract_accepted_count": engine[
            "quantum_oracle_contract_accepted_count"
        ],
        "quantum_oracle_job_preview_count": engine["quantum_oracle_job_preview_count"],
        "quantum_optimized": engine["quantum_optimization"]["optimized_for_quantum_oracle"],
        "quantum_gate_status": engine["quantum_gate"]["status"],
        "fail_closed_probe_rejected": fail_closed_probe_rejected,
        "feature_probe_rejected": feature_probe_rejected,
        "authority_probe_rejected": authority_probe_rejected,
        "paths": paths,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if errors:
        raise SystemExit("; ".join(errors))

    print("pattern_recognition_engine_check=ok")
    print(f"pattern_recognition_engine_status={engine['status']}")
    print(f"pattern_recognition_engine_source_count={engine['source_scan']['source_count']}")
    print(
        "pattern_recognition_engine_watched_instrument_count="
        f"{engine['source_scan']['watched_instrument_count']}"
    )
    print(f"pattern_recognition_engine_candidate_pattern_count={engine['candidate_pattern_count']}")
    print(f"pattern_recognition_engine_feature_vector_length={PATTERN_RECOGNITION_ENGINE_FEATURE_VECTOR_LENGTH}")
    print(f"pattern_recognition_engine_oracle_job_type_count={len(PATTERN_RECOGNITION_ENGINE_JOB_TYPES)}")
    print(
        "pattern_recognition_engine_oracle_contract_accepted_count="
        f"{engine['quantum_oracle_contract_accepted_count']}"
    )
    print(
        "pattern_recognition_engine_oracle_job_preview_count="
        f"{engine['quantum_oracle_job_preview_count']}"
    )
    print(
        "pattern_recognition_engine_quantum_optimized="
        f"{engine['quantum_optimization']['optimized_for_quantum_oracle']}"
    )
    print(f"pattern_recognition_engine_quantum_gate_status={engine['quantum_gate']['status']}")
    print(f"pattern_recognition_engine_fail_closed_probe_rejected={fail_closed_probe_rejected}")
    print(f"pattern_recognition_engine_feature_probe_rejected={feature_probe_rejected}")
    print(f"pattern_recognition_engine_authority_probe_rejected={authority_probe_rejected}")
    print(f"pattern_recognition_engine_artifact_path={paths['output_path']}")


if __name__ == "__main__":
    main()
