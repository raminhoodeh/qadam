#!/usr/bin/env python3
"""Build and validate Qadam Phase 12 Dashboard VNext artifacts."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qadam_dashboard_vnext import (
    DASHBOARD_SUMMARY_ARTIFACT,
    DOWNSTREAM_SECTIONS_ARTIFACT,
    EVENTS_ARTIFACT,
    PRIMARY_ARTIFACT,
    PROTECTED_SECTIONS_ARTIFACT,
    _runtime_dir,
    build_and_write_dashboard_vnext,
    load_dashboard_vnext,
    validate_dashboard_vnext_bundle,
    validate_negative_dashboard_vnext_probes,
)


def main() -> int:
    settings = Settings.from_env()
    bundle, written = build_and_write_dashboard_vnext(settings)
    runtime_dir = _runtime_dir(settings)

    validation_errors: list[str] = []
    for filename in (
        PRIMARY_ARTIFACT,
        PROTECTED_SECTIONS_ARTIFACT,
        DOWNSTREAM_SECTIONS_ARTIFACT,
        DASHBOARD_SUMMARY_ARTIFACT,
        EVENTS_ARTIFACT,
    ):
        if not (runtime_dir / filename).exists():
            validation_errors.append(f"{filename}_missing")

    validation_errors.extend(validate_dashboard_vnext_bundle(bundle))
    validation_errors.extend(validate_dashboard_vnext_bundle(load_dashboard_vnext(settings)))
    validation_errors.extend(validate_negative_dashboard_vnext_probes())

    primary = bundle.primary
    protected = bundle.protected_sections
    downstream = bundle.downstream_sections
    summary = bundle.dashboard_summary
    print(f"primary={written.get('primary')}")
    print(f"protected_sections={written.get('protected_sections')}")
    print(f"downstream_sections={written.get('downstream_sections')}")
    print(f"dashboard_summary={written.get('dashboard_summary')}")
    print(f"events={written.get('events')}")
    print(f"status={primary.get('status')}")
    print(f"protected_section_order={protected.get('protected_section_order')}")
    print(f"protected_section_count={protected.get('protected_section_count')}")
    print(f"protected_sections_not_reordered={protected.get('protected_sections_not_reordered')}")
    print(f"protected_sections_not_renamed={protected.get('protected_sections_not_renamed')}")
    print(f"protected_sections_not_removed={protected.get('protected_sections_not_removed')}")
    print(f"protected_sections_not_structurally_overhauled={protected.get('protected_sections_not_structurally_overhauled')}")
    print(f"enrichment_only_inside_protected_sections={protected.get('enrichment_only_inside_protected_sections')}")
    print(f"all_portfolio_values_agree={protected.get('all_portfolio_values_agree')}")
    print(f"downstream_section_order={downstream.get('downstream_section_order')}")
    print(f"downstream_section_count={downstream.get('downstream_section_count')}")
    print(f"strategy_card_count={downstream.get('strategy_card_count')}")
    print(f"pattern_card_count={downstream.get('pattern_card_count')}")
    print(f"akber_plain_english_state={downstream.get('akber_plain_english_state')}")
    print(f"router_paperops_single_answer={downstream.get('router_paperops_single_answer')}")
    print(f"learning_summary={downstream.get('learning_summary')}")
    print(f"paper_order_created_count={summary.get('paper_order_created_count')}")
    print(f"broker_write_count={summary.get('broker_write_count')}")
    print(f"proof_credit_allowed={summary.get('proof_credit_allowed')}")
    print(f"live_capital_enabled={summary.get('live_capital_enabled')}")
    if validation_errors:
        for error in validation_errors:
            print(f"error={error}")
        return 1
    print("qadam_dashboard_vnext_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
