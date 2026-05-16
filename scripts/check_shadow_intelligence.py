#!/usr/bin/env python3
"""Check Phase 2 shadow intelligence contracts without model calls."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.intelligence import (
    provider_status,
    run_research_shadow_triage_queue,
    run_shadow_intelligence_sample,
    shadow_intelligence_summary,
)


def main() -> int:
    result = run_shadow_intelligence_sample()
    summary = shadow_intelligence_summary()
    providers = result["provider_status"]
    frontier = providers["frontier_llm"]
    local = providers["local_llm"]

    print("shadow_intelligence_status=" + result["status"])
    print(f"shadow_intelligence_schema_version={result['schema_version']}")
    print(f"shadow_intelligence_evidence_count={result['evidence_count']}")
    print(f"shadow_intelligence_signal_count={result['shadow_signal_count']}")
    print(f"shadow_intelligence_execution_allowed_count={result['execution_allowed_count']}")
    print(f"shadow_intelligence_store_status={result['store']['status']}")
    print(f"shadow_intelligence_total_store_signals={summary['store']['signal_count']}")
    print(f"shadow_intelligence_gemini_configured={frontier['credential_configured']}")
    print(f"shadow_intelligence_gemini_mode={frontier['mode']}")
    print(f"shadow_intelligence_local_provider={local['provider']}")
    print(f"shadow_intelligence_local_model={local['model']}")
    print(f"shadow_intelligence_local_mode={local['mode']}")
    print(f"shadow_intelligence_local_probe_status={local['probe_status']}")
    print(f"shadow_intelligence_gemini_probe_status={frontier['probe_status']}")
    print(f"shadow_intelligence_boundary={result['boundary']}")

    dry_providers = provider_status()
    triage_result = run_research_shadow_triage_queue(limit=5)
    print(f"shadow_intelligence_provider_probe_mode={dry_providers['status']}")
    print(f"shadow_intelligence_queue_packet_count={triage_result['packet_count']}")
    print(f"shadow_intelligence_queue_processed_count={triage_result['processed_packet_count']}")
    print(f"shadow_intelligence_queue_signal_count={triage_result['shadow_signal_count']}")

    if result["status"] != "ok":
        return 1
    if result["shadow_signal_count"] < 1:
        print("shadow_intelligence_no_shadow_signals=true")
        return 1
    if result["execution_allowed_count"] != 0:
        print("shadow_intelligence_execution_allowed_not_zero=true")
        return 1
    if result["store"]["status"] != "ok":
        print("shadow_intelligence_store_not_ok=true")
        return 1
    if triage_result["execution_allowed_count"] != 0:
        print("shadow_intelligence_queue_execution_allowed_not_zero=true")
        return 1

    print("shadow_intelligence_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
