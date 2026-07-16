#!/usr/bin/env python3
"""Export and verify the public Wave F dashboard projection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_wave_f_public_view import (  # noqa: E402
    build_wave_f_public_view,
    write_wave_f_public_view,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-root", type=Path, action="append")
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Validate existing site projections against current inputs without writing.",
    )
    arguments = parser.parse_args()
    settings = Settings.from_env()
    runtime_dir = Path(settings.runtime_dir)
    if not runtime_dir.is_absolute():
        runtime_dir = ROOT / runtime_dir
    site_roots = [
        site_root if site_root.is_absolute() else ROOT / site_root
        for site_root in arguments.site_root or []
    ]
    errors: list[str] = []
    if arguments.verify_only:
        if not site_roots:
            errors.append("wave_f_verify_only_requires_site_root")
            payload = build_wave_f_public_view(runtime_dir)
        else:
            try:
                first_payload = json.loads(
                    (site_roots[0] / "status" / "quantum-edge-wave-f.json").read_text(
                        encoding="utf-8"
                    )
                )
                payload = build_wave_f_public_view(
                    runtime_dir,
                    generated_at=first_payload.get("generated_at"),
                )
            except (OSError, json.JSONDecodeError) as exc:
                print(f"wave_f_verify_site_error={exc}")
                return 1
            for site_root in site_roots:
                site_path = site_root / "status" / "quantum-edge-wave-f.json"
                try:
                    site_payload = json.loads(site_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    errors.append(f"wave_f_site_artifact_unreadable:{site_path}:{exc}")
                    continue
                if site_payload != payload:
                    errors.append(f"wave_f_site_artifact_mismatch:{site_path}")
        outputs = {"runtime": runtime_dir / "qadam_quantum_edge_wave_f_public_view.json"}
    else:
        payload = build_wave_f_public_view(runtime_dir)
        outputs = write_wave_f_public_view(
            payload,
            runtime_dir=runtime_dir,
            site_root=site_roots[0] if site_roots else None,
        )
        for index, site_root in enumerate(site_roots[1:], start=2):
            mirror_outputs = write_wave_f_public_view(
                payload,
                runtime_dir=runtime_dir,
                site_root=site_root,
            )
            outputs[f"site_{index}"] = mirror_outputs["site"]
    patterns = payload["pattern_recognition"]
    quantum = payload["quantum_edge"]
    strategies = payload["trading_strategies"]
    authenticity = quantum["hardware_authenticity"]
    if patterns["candidate_count"] != 6:
        errors.append("wave_f_candidate_count_unexpected")
    if not any(row["discovery_origin"] == "joint_discovery" for row in patterns["candidates"]):
        errors.append("wave_f_joint_candidate_missing")
    if patterns.get("comparison_scope", {}).get("source_count") != 41:
        errors.append("wave_f_source_scope_unexpected")
    if patterns.get("comparison_scope", {}).get("instrument_count") != 19:
        errors.append("wave_f_instrument_scope_unexpected")
    if patterns.get("eyebrow") != "Predictive Architecture":
        errors.append("wave_f_predictive_architecture_eyebrow_missing")
    if len(patterns.get("status_lifecycle", [])) != 9:
        errors.append("wave_f_pattern_status_lifecycle_incomplete")
    if not patterns.get("strategy_path_explainer", {}).get("paragraph"):
        errors.append("wave_f_pattern_strategy_path_missing")
    for candidate in patterns["candidates"]:
        score = candidate.get("research_score", {})
        if score.get("value") is None or score.get("is_probability") is not False:
            errors.append(f"wave_f_score_contract_invalid:{candidate.get('candidate_id')}")
        if not candidate.get("potential_pattern_summary"):
            errors.append(f"wave_f_potential_pattern_missing:{candidate.get('candidate_id')}")
        if not candidate.get("strategy_lenses"):
            errors.append(f"wave_f_strategy_fit_missing:{candidate.get('candidate_id')}")
        if not str(candidate.get("relationship") or "").endswith("?"):
            errors.append(f"wave_f_pattern_question_missing:{candidate.get('candidate_id')}")
        if candidate.get("observed_at") != candidate.get("last_observed_at"):
            errors.append(
                f"wave_f_pattern_observation_range_invalid:{candidate.get('candidate_id')}"
            )
        if {"GLD", "SPY"} & set(candidate.get("instruments") or []) and candidate.get(
            "pattern_category"
        ) != "Macro Watchlist":
            errors.append(f"wave_f_macro_watchlist_missing:{candidate.get('candidate_id')}")
    fixture_rows = [
        row for row in patterns["candidates"] if row.get("contract_fixture_only") is True
    ]
    if not fixture_rows or any(
        row.get("evidence_label") != "System test only" for row in fixture_rows
    ):
        errors.append("wave_f_fixture_plain_language_missing")
    if quantum["proof_state"] != "quantum_edge_not_yet_proven":
        errors.append("wave_f_current_proof_state_invalid")
    if authenticity["hardware_experiment_completed"] is not False:
        errors.append("wave_f_unearned_hardware_completion")
    if authenticity["provider_call_count"] != 0:
        errors.append("wave_f_provider_call_count_invalid")
    if strategies["validated_strategy_count"] != 0:
        errors.append("wave_f_unearned_validated_strategy")
    if strategies.get("validated_core_strategy_count") != 0:
        errors.append("wave_f_unearned_validated_core_strategy")
    if strategies.get("validated_pattern_sourced_strategy_count") != 0:
        errors.append("wave_f_unearned_validated_pattern_sourced_strategy")
    if strategies.get("eyebrow") != "Dynamic Strategy Rotation":
        errors.append("wave_f_dynamic_strategy_rotation_eyebrow_missing")
    if strategies["research_playbook_count"] != 5:
        errors.append("wave_f_research_playbook_count_unexpected")
    if strategies.get("core_strategy_count") != 5:
        errors.append("wave_f_core_strategy_count_unexpected")
    if strategies.get("emerging_strategy_count") != 0:
        errors.append("wave_f_emerging_strategy_count_unexpected")
    if len(strategies.get("strategy_progression", [])) != 5:
        errors.append("wave_f_strategy_progression_incomplete")
    for strategy in strategies.get("core_playbooks", []):
        if not strategy.get("pattern_lineage"):
            errors.append(
                f"wave_f_strategy_pattern_lineage_missing:{strategy.get('strategy_family_id')}"
            )
        if not strategy.get("core_instruments"):
            errors.append(
                f"wave_f_strategy_core_instruments_missing:{strategy.get('strategy_family_id')}"
            )
        if not strategy.get("thesis") or not strategy.get("confirmation"):
            errors.append(
                f"wave_f_strategy_plain_language_missing:{strategy.get('strategy_family_id')}"
            )
    if any(payload["authority"].values()):
        errors.append("wave_f_authority_escalated")

    print(f"wave_f_generated_at={payload['generated_at']}")
    print(f"wave_f_content_hash={payload['content_hash']}")
    print(f"wave_f_pattern_candidate_count={patterns['candidate_count']}")
    print(f"wave_f_comparison_scope={patterns.get('comparison_scope', {})}")
    print(
        "wave_f_pattern_scores="
        f"{[(row['candidate_id'], row['research_score']['display']) for row in patterns['candidates']]}"
    )
    print(
        "wave_f_pattern_origin_counts="
        f"{[(row['key'], row['count']) for row in patterns['filters']]}"
    )
    print(f"wave_f_quantum_proof_state={quantum['proof_state']}")
    print(f"wave_f_completed_proof_step_count={quantum['completed_proof_step_count']}")
    print(f"wave_f_hardware_experiment_completed={authenticity['hardware_experiment_completed']}")
    print(f"wave_f_provider_call_count={authenticity['provider_call_count']}")
    print(f"wave_f_validated_strategy_count={strategies['validated_strategy_count']}")
    print(
        "wave_f_validated_strategy_split="
        f"core:{strategies['validated_core_strategy_count']},"
        f"pattern_sourced:{strategies['validated_pattern_sourced_strategy_count']}"
    )
    print(f"wave_f_research_playbook_count={strategies['research_playbook_count']}")
    print(f"wave_f_core_strategy_count={strategies['core_strategy_count']}")
    print(f"wave_f_emerging_strategy_count={strategies['emerging_strategy_count']}")
    print(f"wave_f_runtime_artifact={outputs['runtime']}")
    print(
        f"wave_f_site_artifacts={[str(outputs[key]) for key in outputs if key.startswith('site')]}"
    )
    print(f"wave_f_errors={errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
