#!/usr/bin/env python3
"""Validate PaperOps guarded close-to-ledger verifier."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.paperops_close_to_ledger import (  # noqa: E402
    build_paperops_close_to_ledger,
    validate_paperops_close_to_ledger,
    write_paperops_close_to_ledger,
)


def _expect(errors: list[str], expected: str) -> str | None:
    if expected not in errors:
        return f"expected_probe_error_missing:{expected}"
    return None


def _run_negative_probes(artifact: dict) -> list[str]:
    probe_errors: list[str] = []

    live_probe = deepcopy(artifact)
    live_probe["live_capital_enabled"] = True
    if error := _expect(
        validate_paperops_close_to_ledger(live_probe),
        "paperops_close_to_ledger_live_capital_enabled",
    ):
        probe_errors.append(error)

    broker_probe = deepcopy(artifact)
    broker_probe["broker_post_called_count"] = 1
    if error := _expect(
        validate_paperops_close_to_ledger(broker_probe),
        "paperops_close_to_ledger_broker_post_called",
    ):
        probe_errors.append(error)

    proof_probe = deepcopy(artifact)
    proof_probe["phase7_proof_credit_allowed"] = True
    proof_probe["phase7_proof_credit_allowed_count"] = 1
    if error := _expect(
        validate_paperops_close_to_ledger(proof_probe),
        "paperops_close_to_ledger_phase7_proof_credit_allowed",
    ):
        probe_errors.append(error)

    mirror_probe = deepcopy(artifact)
    mirror_probe["mirror_trade_counted_for_proof_count"] = 1
    if error := _expect(
        validate_paperops_close_to_ledger(mirror_probe),
        "paperops_close_to_ledger_mirror_trade_counted_for_proof",
    ):
        probe_errors.append(error)

    return probe_errors


def main() -> int:
    settings = Settings.from_env()
    written = write_paperops_close_to_ledger(settings=settings)
    validation_errors = validate_paperops_close_to_ledger(written)
    probe_errors = _run_negative_probes(build_paperops_close_to_ledger(settings=settings))

    print(f"paperops_close_to_ledger_status={written['status']}")
    print(f"paperops_close_to_ledger_latest_close_at={written['latest_successful_close_requested_at']}")
    print(f"paperops_close_to_ledger_latest_close_symbol={written['latest_successful_close_symbol']}")
    print(f"paperops_close_to_ledger_close_receipt_present={written['guarded_close_receipt_present']}")
    print(f"paperops_close_to_ledger_close_receipt_verified={written['guarded_close_receipt_verified']}")
    print(
        "paperops_close_to_ledger_lifecycle_mirror_fresh_after_latest_close="
        f"{written['lifecycle_mirror_fresh_after_latest_close']}"
    )
    print(
        "paperops_close_to_ledger_lifecycle_mirror_freshness_status="
        f"{written['lifecycle_mirror_freshness_status']}"
    )
    print(
        "paperops_close_to_ledger_research_goal_lineage_present="
        f"{written['research_goal_lineage_present']}"
    )
    print(
        "paperops_close_to_ledger_postmortem_due_marker_created_count="
        f"{written['postmortem_due_marker_created_count']}"
    )
    print(
        "paperops_close_to_ledger_paper_proof_ledger_verified_record_count="
        f"{written['paper_proof_ledger_verified_record_count']}"
    )
    print(
        "paperops_close_to_ledger_closed_proof_trade_count="
        f"{written['closed_proof_trade_count']}"
    )
    print(
        "paperops_close_to_ledger_mirror_trade_counted_for_proof_count="
        f"{written['mirror_trade_counted_for_proof_count']}"
    )
    print(f"paperops_close_to_ledger_blockers={','.join(written['blockers'])}")
    print(f"paperops_close_to_ledger_live_endpoint_called_count={written['live_endpoint_called_count']}")
    print(f"paperops_close_to_ledger_broker_post_called_count={written['broker_post_called_count']}")
    print(f"paperops_close_to_ledger_phase7_proof_credit_allowed={written['phase7_proof_credit_allowed']}")
    print(f"paperops_close_to_ledger_validation_errors={','.join(validation_errors)}")
    print(f"paperops_close_to_ledger_probe_error_count={len(probe_errors)}")

    if validation_errors:
        return 1
    if probe_errors:
        print("paperops_close_to_ledger_probe_errors=" + ",".join(probe_errors))
        return 1
    print("paperops_close_to_ledger_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
