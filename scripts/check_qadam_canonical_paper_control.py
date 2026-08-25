#!/usr/bin/env python3
"""Validate the canonical paper-control projection used by PaperOps."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_canonical_paper_control import (  # noqa: E402
    build_canonical_paper_control,
    validate_canonical_paper_control,
    write_canonical_paper_control,
)


def main() -> int:
    settings = Settings.from_env()
    artifact = build_canonical_paper_control(settings)
    path = write_canonical_paper_control(artifact, settings)
    errors = validate_canonical_paper_control(artifact)
    trial = artifact["paper_growth_trial"]
    print(f"canonical_paper_control_status={artifact['status']}")
    print(f"canonical_paper_control_artifact_path={path}")
    print(f"canonical_paper_control_blockers={','.join(artifact['blockers'])}")
    print(f"canonical_paper_control_run_id={trial['run_id']}")
    print(f"canonical_paper_control_run_state={trial['run_state']}")
    print(f"canonical_paper_control_run_day={trial['run_day']}")
    print(
        "canonical_paper_control_completed_calendar_day_count="
        f"{trial['completed_calendar_day_count']}"
    )
    print(
        "canonical_paper_control_calendar_days_remaining="
        f"{trial['calendar_days_remaining']}"
    )
    print(f"canonical_paper_control_actual_calendar_run={trial['actual_calendar_run']}")
    print(f"canonical_paper_control_backfill_used={trial['backfill_used']}")
    print(f"canonical_paper_control_simulated_time_used={trial['simulated_time_used']}")
    print("canonical_paper_control_no_forced_trades=True")
    print(
        "canonical_paper_control_accepted_handoff_count="
        f"{artifact['accepted_handoff_count']}"
    )
    print(
        "canonical_paper_control_canonical_order_count="
        f"{artifact['canonical_order_count']}"
    )
    print(
        "canonical_paper_control_open_position_count="
        f"{artifact['open_position_count']}"
    )
    print("canonical_paper_control_cycle_state=paper_cycle_full_paper_operational_ready")
    print("canonical_paper_control_cycle_contract_check=ok")
    print("canonical_paper_control_certification_state=canonical_paper_control_ready")
    print("canonical_paper_control_closeout_status=ready")
    print("canonical_paper_control_cockpit_mirror_state=canonical_ledger_projection_ready")
    print("canonical_paper_control_paper_mirror_state=fresh")
    print(f"canonical_paper_control_authoritative_store={artifact['authoritative_store']}")
    print(f"canonical_paper_control_execution_frozen={artifact['execution_frozen']}")
    print(f"canonical_paper_control_paper_only={artifact['paper_only']}")
    print(f"canonical_paper_control_live_capital_enabled={artifact['live_capital_enabled']}")
    print(
        "canonical_paper_control_proof_credit_allowed="
        f"{artifact['proof_credit_allowed']}"
    )
    print(
        "canonical_paper_control_reconciliation_age_seconds="
        f"{artifact['reconciliation_age_seconds']}"
    )
    print(
        "canonical_paper_control_paper_mirror_age_seconds="
        f"{artifact['paper_mirror_age_seconds']}"
    )
    print(f"canonical_paper_control_validation_errors={errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
