#!/usr/bin/env python3
"""Run and verify the Wave G guarded hybrid loop."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_wave_g_hybrid_loop import (  # noqa: E402
    ARTIFACT_NAME,
    AUTOMATION_STAGES,
    PUBLIC_LIFECYCLE_STATES,
    SITE_ARTIFACT_NAME,
    WaveGInterrupted,
    run_wave_g_cycle,
    validate_wave_g_broker_boundary,
    validate_wave_g_payload,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-dir", type=Path)
    parser.add_argument("--site-root", type=Path, action="append")
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Validate existing runtime and site mirrors without writing artifacts.",
    )
    parser.add_argument("--evidence-date")
    parser.add_argument("--interrupt-after-stage", choices=AUTOMATION_STAGES)
    arguments = parser.parse_args()

    settings = Settings.from_env()
    runtime_dir = arguments.runtime_dir or Path(settings.runtime_dir)
    if not runtime_dir.is_absolute():
        runtime_dir = ROOT / runtime_dir
    site_roots = [
        site_root if site_root.is_absolute() else ROOT / site_root
        for site_root in arguments.site_root or []
    ]
    errors = validate_wave_g_broker_boundary(ROOT)
    if arguments.verify_only:
        runtime_path = runtime_dir / ARTIFACT_NAME
        try:
            payload = json.loads(runtime_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"wave_g_verify_runtime_error={exc}")
            return 1
        for site_root in site_roots:
            site_path = site_root / "status" / SITE_ARTIFACT_NAME
            try:
                site_payload = json.loads(site_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"wave_g_site_artifact_unreadable:{site_path}:{exc}")
                continue
            if site_payload != payload:
                errors.append(f"wave_g_site_artifact_mismatch:{site_path}")
    else:
        try:
            payload = run_wave_g_cycle(
                runtime_dir,
                site_root=site_roots[0] if site_roots else None,
                evidence_date=arguments.evidence_date,
                interrupt_after_stage=arguments.interrupt_after_stage,
            )
            for site_root in site_roots[1:]:
                mirror_payload = run_wave_g_cycle(
                    runtime_dir,
                    site_root=site_root,
                    evidence_date=arguments.evidence_date,
                )
                if mirror_payload != payload:
                    errors.append(f"wave_g_site_artifact_mismatch:{site_root}")
        except WaveGInterrupted as exc:
            print(f"wave_g_interrupted={exc}")
            return 2

    try:
        validate_wave_g_payload(payload)
    except ValueError as exc:
        errors.append(str(exc))
    integration = payload["paper_integration"]
    automation = payload["automation"]
    lifecycle = payload["public_lifecycle"]
    if [row["state"] for row in lifecycle] != list(PUBLIC_LIFECYCLE_STATES):
        errors.append("wave_g_public_lifecycle_changed")
    if integration.get("paper_order_created_count") != 0:
        errors.append("wave_g_paper_order_created")
    if integration.get("broker_write_count") != 0:
        errors.append("wave_g_broker_write_detected")
    if automation.get("provider_calls_this_cycle") != 0:
        errors.append("wave_g_provider_call_detected")

    print(f"wave_g_cycle_id={payload['cycle_id']}")
    print(f"wave_g_generated_at={payload['generated_at']}")
    print(f"wave_g_status={payload['status']}")
    print(
        "wave_g_validated_edge_count="
        f"{len(payload['validated_edge_admissions'])}"
    )
    print(f"wave_g_strategy_count={integration.get('strategy_count')}")
    print(f"wave_g_risk_review_count={integration.get('risk_review_count')}")
    print(
        "wave_g_paperops_review_handoff_count="
        f"{integration.get('paperops_review_handoff_count')}"
    )
    print(
        "wave_g_provider_calls_this_cycle="
        f"{automation.get('provider_calls_this_cycle')}"
    )
    print(
        "wave_g_public_states="
        f"{[(row['state'], row['status']) for row in lifecycle]}"
    )
    print(f"wave_g_content_hash={payload['content_hash']}")
    print(f"wave_g_errors={errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
