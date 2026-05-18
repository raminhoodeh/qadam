#!/usr/bin/env python3
"""Check Phase 1 Trust Score seed readiness."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.trust_scores import build_trust_score_seed


def main() -> int:
    payload = build_trust_score_seed()
    print(f"trust_score_seed_status={payload['status']}")
    print(f"trust_score_seed_count={payload['seed_count']}")
    print(f"trust_score_above_half_count={payload['above_half_count']}")
    print(f"trust_score_above_half_threshold_met={payload['above_half_threshold_met']}")
    print(f"trust_score_physical_logistics_latency_pass_count={payload['physical_logistics_latency_pass_count']}")
    print(f"trust_score_physical_logistics_latency_threshold_met={payload['physical_logistics_latency_threshold_met']}")
    print(f"trust_score_real_data_seed_complete={payload['real_data_seed_complete']}")
    print(f"trust_score_boundary={payload['boundary']}")
    if payload["seed_count"] < 35:
        print("trust_score_seed_count_too_low=true")
        return 1
    if payload["above_half_count"] < 20:
        print("trust_score_above_half_count_too_low=true")
        return 1
    if payload["physical_logistics_latency_pass_count"] < 2:
        print("trust_score_physical_logistics_latency_count_too_low=true")
        return 1
    print("trust_score_seed_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
