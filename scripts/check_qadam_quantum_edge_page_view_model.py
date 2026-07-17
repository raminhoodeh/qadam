#!/usr/bin/env python3
"""Build and verify the canonical three-layer Quantum Edge page projection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_quantum_edge_page_view_model import (  # noqa: E402
    build_quantum_edge_page_view_model,
    build_quantum_edge_page_view_model_from_sources,
    validate_quantum_edge_page_view_model,
    write_quantum_edge_page_view_model,
)


SITE_SOURCE_ARTIFACTS = {
    "wave_f": "quantum-edge-wave-f.json",
    "wave_g": "quantum-edge-wave-g.json",
    "wave_h": "quantum-edge-wave-h.json",
}


def _load_site_sources(site_root: Path) -> dict[str, dict[str, object]]:
    return {
        source_id: json.loads(
            (site_root / "status" / filename).read_text(encoding="utf-8")
        )
        for source_id, filename in SITE_SOURCE_ARTIFACTS.items()
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-dir", type=Path)
    parser.add_argument(
        "--site-root",
        type=Path,
        action="append",
        help="Static site root to update; repeat to write verified byte-identical mirrors.",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Validate existing site projections against current inputs without writing.",
    )
    arguments = parser.parse_args()

    settings = Settings.from_env()
    runtime_dir = arguments.runtime_dir or Path(settings.runtime_dir)
    if not runtime_dir.is_absolute():
        runtime_dir = ROOT / runtime_dir
    site_roots = []
    for site_root in arguments.site_root or []:
        site_roots.append(site_root if site_root.is_absolute() else ROOT / site_root)

    errors: list[str] = []
    if arguments.verify_only:
        if not site_roots:
            errors.append("quantum_edge_page_verify_only_requires_site_root")
            payload = build_quantum_edge_page_view_model(runtime_dir)
        else:
            try:
                first_payload = json.loads(
                    (site_roots[0] / "status" / "quantum-edge-page.json").read_text(
                        encoding="utf-8"
                    )
                )
                payload = build_quantum_edge_page_view_model_from_sources(
                    _load_site_sources(site_roots[0]),
                    generated_at=first_payload.get("generated_at"),
                )
            except (OSError, json.JSONDecodeError) as exc:
                print(f"quantum_edge_page_verify_site_error={exc}")
                return 1
            for site_root in site_roots:
                site_path = site_root / "status" / "quantum-edge-page.json"
                try:
                    site_payload = json.loads(site_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    errors.append(
                        f"quantum_edge_page_site_artifact_unreadable:{site_path}:{exc}"
                    )
                    continue
                if site_payload != payload:
                    errors.append(f"quantum_edge_page_site_artifact_mismatch:{site_path}")
        outputs = {"runtime": runtime_dir / "qadam_quantum_edge_page.json"}
    else:
        payload = build_quantum_edge_page_view_model(runtime_dir)
        outputs = write_quantum_edge_page_view_model(
            payload,
            runtime_dir=runtime_dir,
            site_root=site_roots[0] if site_roots else None,
        )
        for index, site_root in enumerate(site_roots[1:], start=2):
            mirror_outputs = write_quantum_edge_page_view_model(
                payload,
                runtime_dir=runtime_dir,
                site_root=site_root,
            )
            outputs[f"site_{index}"] = mirror_outputs["site"]
    errors.extend(validate_quantum_edge_page_view_model(payload))
    answer = payload["answer"]
    engineering = answer["engineering_checks"]
    market = answer["market_proof_prerequisites"]
    consequence = payload["consequence"]
    guarded = consequence["guarded_route"]

    print(f"quantum_edge_page_status={payload['projection_status']}")
    print(f"quantum_edge_page_generated_at={payload['generated_at']}")
    print(f"quantum_edge_page_content_hash={payload['content_hash']}")
    print(f"quantum_edge_page_source_count={len(payload['source_artifacts'])}")
    print(
        "quantum_edge_page_semantic_coherence_passed="
        f"{payload['source_lineage']['semantic_coherence_passed']}"
    )
    print(
        "quantum_edge_page_source_integrity_errors="
        f"{payload['source_lineage']['integrity_errors']}"
    )
    print(
        "quantum_edge_page_source_semantic_errors="
        f"{payload['source_lineage']['semantic_errors']}"
    )
    print(f"quantum_edge_page_proof_state={answer['proof_state']}")
    print(
        "quantum_edge_page_scientific_verdict="
        f"{answer['scientific_verdict']}"
    )
    print(
        "quantum_edge_page_engineering_checks="
        f"{engineering['score_label']}"
    )
    print(
        "quantum_edge_page_market_proof_prerequisites="
        f"{market['score_label']}"
    )
    print(
        "quantum_edge_page_paper_orders="
        f"{guarded['paper_order_count']}"
    )
    print(
        "quantum_edge_page_broker_writes="
        f"{guarded['broker_write_count']}"
    )
    print("quantum_edge_page_provider_calls_performed=0")
    print("quantum_edge_page_research_jobs_performed=0")
    print("quantum_edge_page_trading_mutations_performed=0")
    print(f"quantum_edge_page_runtime_artifact={outputs['runtime']}")
    print(
        "quantum_edge_page_site_artifacts="
        f"{[str(outputs[key]) for key in outputs if key.startswith('site')]}"
    )
    print(f"quantum_edge_page_validation_errors={errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
