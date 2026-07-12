#!/usr/bin/env python3
"""Export and verify the public Wave F dashboard projection."""

from __future__ import annotations

import argparse
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
    parser.add_argument("--site-root", type=Path)
    arguments = parser.parse_args()
    settings = Settings.from_env()
    runtime_dir = Path(settings.runtime_dir)
    if not runtime_dir.is_absolute():
        runtime_dir = ROOT / runtime_dir
    payload = build_wave_f_public_view(runtime_dir)
    outputs = write_wave_f_public_view(
        payload,
        runtime_dir=runtime_dir,
        site_root=arguments.site_root,
    )
    patterns = payload["pattern_recognition"]
    quantum = payload["quantum_edge"]
    strategies = payload["trading_strategies"]
    authenticity = quantum["hardware_authenticity"]
    errors: list[str] = []
    if patterns["candidate_count"] != 6:
        errors.append("wave_f_candidate_count_unexpected")
    if not any(
        row["discovery_origin"] == "joint_discovery"
        for row in patterns["candidates"]
    ):
        errors.append("wave_f_joint_candidate_missing")
    if quantum["proof_state"] != "quantum_edge_not_yet_proven":
        errors.append("wave_f_current_proof_state_invalid")
    if authenticity["hardware_experiment_completed"] is not False:
        errors.append("wave_f_unearned_hardware_completion")
    if authenticity["provider_call_count"] != 0:
        errors.append("wave_f_provider_call_count_invalid")
    if strategies["validated_strategy_count"] != 0:
        errors.append("wave_f_unearned_validated_strategy")
    if strategies["research_playbook_count"] != 5:
        errors.append("wave_f_research_playbook_count_unexpected")
    if any(payload["authority"].values()):
        errors.append("wave_f_authority_escalated")

    print(f"wave_f_generated_at={payload['generated_at']}")
    print(f"wave_f_content_hash={payload['content_hash']}")
    print(f"wave_f_pattern_candidate_count={patterns['candidate_count']}")
    print(
        "wave_f_pattern_origin_counts="
        f"{[(row['key'], row['count']) for row in patterns['filters']]}"
    )
    print(f"wave_f_quantum_proof_state={quantum['proof_state']}")
    print(
        "wave_f_completed_proof_step_count="
        f"{quantum['completed_proof_step_count']}"
    )
    print(
        "wave_f_hardware_experiment_completed="
        f"{authenticity['hardware_experiment_completed']}"
    )
    print(f"wave_f_provider_call_count={authenticity['provider_call_count']}")
    print(
        "wave_f_validated_strategy_count="
        f"{strategies['validated_strategy_count']}"
    )
    print(f"wave_f_research_playbook_count={strategies['research_playbook_count']}")
    print(f"wave_f_runtime_artifact={outputs['runtime']}")
    print(f"wave_f_site_artifact={outputs.get('site')}")
    print(f"wave_f_errors={errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
