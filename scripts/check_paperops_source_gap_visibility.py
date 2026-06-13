#!/usr/bin/env python3
"""Validate public-safe PaperOps source-gap visibility."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.paperops_source_gap_visibility import (  # noqa: E402
    PAPEROPS_SOURCE_GAP_VISIBILITY_SCHEMA_VERSION,
    build_paperops_source_gap_visibility,
    paperops_source_gap_visibility_paths,
    validate_paperops_source_gap_visibility,
    write_paperops_source_gap_visibility,
)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    _, _, event_log_path = paperops_source_gap_visibility_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    artifact = build_paperops_source_gap_visibility(settings=settings)
    output_path, history_path, event_path, written = write_paperops_source_gap_visibility(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_paperops_source_gap_visibility(written)
    replay = EventLog(event_path, echo=False).replay()

    promoted_optional_probe = deepcopy(written)
    optional_keys = promoted_optional_probe.get("optional_gap_keys") or []
    if optional_keys:
        promoted_optional_probe["blockers"] = [optional_keys[0]]
        promoted_optional_probe["blocker_count"] = 1
    promoted_optional_errors = validate_paperops_source_gap_visibility(
        promoted_optional_probe
    )

    record_blocking_probe = deepcopy(written)
    if record_blocking_probe.get("source_gap_records"):
        record_blocking_probe["source_gap_records"][0]["trade_blocking"] = True
    record_blocking_errors = validate_paperops_source_gap_visibility(
        record_blocking_probe
    )

    silent_blocker_probe = deepcopy(written)
    silent_blocker_probe["silent_blocker_count"] = 1
    silent_blocker_probe["silent_blocker_keys"] = ["hidden_optional_gap_blocker"]
    silent_blocker_errors = validate_paperops_source_gap_visibility(
        silent_blocker_probe
    )

    unsafe_probe = deepcopy(written)
    unsafe_probe["live_capital_enabled"] = True
    unsafe_probe["live_endpoint_called_count"] = 1
    unsafe_probe["broker_post_called_count"] = 1
    unsafe_probe["phase7_proof_credit_allowed"] = True
    unsafe_errors = validate_paperops_source_gap_visibility(unsafe_probe)

    print(f"paperops_source_gap_visibility_status={written['status']}")
    print(
        "paperops_source_gap_visibility_schema_version="
        f"{PAPEROPS_SOURCE_GAP_VISIBILITY_SCHEMA_VERSION}"
    )
    print(f"paperops_source_gap_visibility_artifact_path={output_path}")
    print(f"paperops_source_gap_visibility_history_path={history_path}")
    print(f"paperops_source_gap_visibility_event_log_path={event_path}")
    print(
        "paperops_source_gap_visibility_event_log_events="
        f"{replay['total_events']}"
    )
    print(
        "paperops_source_gap_visibility_policy_status="
        f"{written['source_gap_policy_status']}"
    )
    print(
        "paperops_source_gap_visibility_source_gap_count="
        f"{written['source_gap_count']}"
    )
    print(
        "paperops_source_gap_visibility_optional_gap_count="
        f"{written['optional_gap_count']}"
    )
    print(
        "paperops_source_gap_visibility_optional_gap_keys="
        f"{','.join(written['optional_gap_keys'])}"
    )
    print(
        "paperops_source_gap_visibility_non_blocking_gap_count="
        f"{written['non_blocking_gap_count']}"
    )
    print(
        "paperops_source_gap_visibility_required_gap_count="
        f"{written['required_gap_count']}"
    )
    print(
        "paperops_source_gap_visibility_trade_blocking_gap_count="
        f"{written['trade_blocking_source_gap_count']}"
    )
    print(
        "paperops_source_gap_visibility_source_quorum_blocking_gap_count="
        f"{written['source_quorum_blocking_gap_count']}"
    )
    print(
        "paperops_source_gap_visibility_silent_blocker_count="
        f"{written['silent_blocker_count']}"
    )
    print(
        "paperops_source_gap_visibility_blockers="
        f"{','.join(written['blockers'])}"
    )
    print(
        "paperops_source_gap_visibility_blocker_count="
        f"{written['blocker_count']}"
    )
    print(
        "paperops_source_gap_visibility_live_endpoint_called_count="
        f"{written['live_endpoint_called_count']}"
    )
    print(
        "paperops_source_gap_visibility_broker_post_called_count="
        f"{written['broker_post_called_count']}"
    )
    print(
        "paperops_source_gap_visibility_live_capital_enabled="
        f"{written['live_capital_enabled']}"
    )
    print(
        "paperops_source_gap_visibility_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(
        "paperops_source_gap_visibility_validation_errors="
        f"{validation_errors}"
    )

    if validation_errors:
        errors.append(f"source gap visibility validation failed: {validation_errors}")
    if replay["total_events"] != 1:
        errors.append("source gap visibility event log did not record exactly one event")
    if written["public_safe"] is not True:
        errors.append("source gap visibility is not public-safe")
    if written["required_gap_count"] != 0:
        errors.append("source gap visibility has required source gaps")
    if written["trade_blocking_source_gap_count"] != 0:
        errors.append("source gap visibility has trade-blocking source gaps")
    if written["silent_blocker_count"] != 0:
        errors.append("source gap visibility has silent blockers")
    if written["blocker_count"] != 0:
        errors.append("source gap visibility has blockers")
    if written["non_blocking_gap_count"] != written["optional_gap_count"]:
        errors.append("source gap non-blocking count does not match optional count")
    if optional_keys and (
        "paperops_source_gap_visibility_optional_promoted_to_blocker"
        not in promoted_optional_errors
    ):
        errors.append("optional-gap promoted-to-blocker probe was not rejected")
    if (
        "paperops_source_gap_visibility_record_blocks:trade_blocking"
        not in record_blocking_errors
    ):
        errors.append("source-gap record blocking probe was not rejected")
    if (
        "paperops_source_gap_visibility_counter_nonzero:silent_blocker_count"
        not in silent_blocker_errors
    ):
        errors.append("silent blocker probe was not rejected")
    if "paperops_source_gap_visibility_forbidden:live_capital_enabled" not in unsafe_errors:
        errors.append("live capital probe was not rejected")
    if (
        "paperops_source_gap_visibility_counter_nonzero:live_endpoint_called_count"
        not in unsafe_errors
    ):
        errors.append("live endpoint probe was not rejected")
    if "paperops_source_gap_visibility_forbidden:phase7_proof_credit_allowed" not in unsafe_errors:
        errors.append("proof credit probe was not rejected")

    if errors:
        print("paperops_source_gap_visibility_check=failed")
        for error in errors:
            print(f"error={error}")
        return 1
    print("paperops_source_gap_visibility_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
