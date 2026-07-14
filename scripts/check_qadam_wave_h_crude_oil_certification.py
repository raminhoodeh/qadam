#!/usr/bin/env python3
"""Build and verify the Wave H crude-oil certification artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_wave_h_crude_oil_certification import (  # noqa: E402
    build_current_wave_h_certification,
    validate_wave_h_payload,
    write_wave_h_certification,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-root", type=Path, action="append")
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Validate existing site certifications against current inputs without writing.",
    )
    args = parser.parse_args()

    settings = Settings.from_env()
    site_roots = [
        site_root if site_root.is_absolute() else ROOT / site_root
        for site_root in args.site_root or []
    ]
    errors: list[str] = []
    if args.verify_only:
        if not site_roots:
            errors.append("wave_h_verify_only_requires_site_root")
            payload = build_current_wave_h_certification(settings=settings)
        else:
            try:
                first_payload = json.loads(
                    (site_roots[0] / "status" / "quantum-edge-wave-h.json").read_text(
                        encoding="utf-8"
                    )
                )
                payload = build_current_wave_h_certification(
                    settings=settings,
                    generated_at=first_payload.get("generated_at"),
                )
            except (OSError, json.JSONDecodeError) as exc:
                print(f"wave_h_verify_site_error={exc}")
                return 1
            for site_root in site_roots:
                site_path = site_root / "status" / "quantum-edge-wave-h.json"
                try:
                    site_payload = json.loads(site_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    errors.append(f"wave_h_site_artifact_unreadable:{site_path}:{exc}")
                    continue
                if site_payload != payload:
                    errors.append(f"wave_h_site_artifact_mismatch:{site_path}")
        paths = {
            "runtime": Path(settings.runtime_dir)
            / "qadam_quantum_edge_wave_h_crude_oil_certification.json"
        }
    else:
        payload = build_current_wave_h_certification(settings=settings)
        paths = write_wave_h_certification(
            payload,
            runtime_dir=settings.runtime_dir,
            site_root=site_roots[0] if site_roots else None,
        )
        for index, site_root in enumerate(site_roots[1:], start=2):
            mirror_paths = write_wave_h_certification(
                payload,
                runtime_dir=settings.runtime_dir,
                site_root=site_root,
            )
            paths[f"site_{index}"] = mirror_paths["site"]
    errors.extend(validate_wave_h_payload(payload))
    certification = payload["certification"]
    evidence = payload["evidence_truth"]
    hardware = payload["hardware_authorization_checkpoint"]
    downstream = payload["downstream_truth"]

    print(f"wave_h_status={payload['status']}")
    print(f"wave_h_generated_at={payload['generated_at']}")
    print(f"wave_h_content_hash={payload['content_hash']}")
    print(f"wave_h_public_proof_state={payload['public_proof_state']}")
    print(f"wave_h_scientific_verdict={payload['scientific_verdict']}")
    print(f"wave_h_mechanism_certified={payload['mechanism_certified']}")
    print(
        "wave_h_engineering_checks="
        f"{certification['engineering_pass_count']}/{certification['engineering_check_count']}"
    )
    print(
        "wave_h_scientific_checks="
        f"{certification['scientific_pass_count']}/{certification['scientific_check_count']}"
    )
    print(f"wave_h_classified_windows={evidence['classified_window_count']}")
    print(f"wave_h_eligible_windows={evidence['eligible_window_count']}")
    print(f"wave_h_provider_rows={evidence['provider_row_count']}")
    print(f"wave_h_leakage_violations={evidence['leakage_violation_count']}")
    print(f"wave_h_hardware_manifest_hash={hardware['engineering_manifest_hash']}")
    print(f"wave_h_hardware_authorized={hardware['authorized']}")
    print(f"wave_h_provider_blocker={hardware['provider_blocker']}")
    print(f"wave_h_validated_edges={downstream['validated_edge_count']}")
    print(f"wave_h_strategies={downstream['strategy_count']}")
    print(f"wave_h_paperops_handoffs={downstream['paperops_review_handoff_count']}")
    print(f"wave_h_paper_orders={downstream['paper_order_count']}")
    print(f"wave_h_runtime_artifact={paths['runtime']}")
    print(
        "wave_h_site_artifacts="
        f"{[str(paths[key]) for key in paths if key.startswith('site')]}"
    )
    print(f"wave_h_errors={errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
