#!/usr/bin/env python3
"""Validate the public-safe completion-gap contract."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.paperops_completion_gaps import (  # noqa: E402
    PAPEROPS_COMPLETION_GAPS_SCHEMA_VERSION,
    build_paperops_completion_gaps,
    validate_paperops_completion_gaps,
    write_paperops_completion_gaps,
)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    artifact = build_paperops_completion_gaps(settings=settings)
    output_path, history_path, written = write_paperops_completion_gaps(
        artifact,
        settings=settings,
    )
    validation_errors = validate_paperops_completion_gaps(written)

    authority_probe = deepcopy(written)
    authority_probe["broker_write_allowed"] = True
    authority_probe["live_capital_enabled"] = True
    authority_errors = validate_paperops_completion_gaps(authority_probe)

    optional_source_probe = deepcopy(written)
    for item in optional_source_probe.get("items", []):
        if isinstance(item, dict) and item.get("category") == "optional_source_credential":
            item["paper_operation_blocking"] = True
            break
    optional_source_errors = validate_paperops_completion_gaps(optional_source_probe)

    quantum_items = [
        item
        for item in written.get("items", [])
        if isinstance(item, dict) and item.get("category") == "quantum"
    ]
    bookmap_items = [
        item
        for item in written.get("items", [])
        if isinstance(item, dict) and item.get("gap_key") == "bookmap_local_bridge_not_connected"
    ]
    paperops_items = [
        item
        for item in written.get("items", [])
        if isinstance(item, dict) and item.get("category") == "paperops"
    ]
    optional_source_items = [
        item
        for item in written.get("items", [])
        if isinstance(item, dict) and item.get("category") == "optional_source_credential"
    ]

    print(f"paperops_completion_gaps_status={written['status']}")
    print(f"paperops_completion_gaps_schema_version={PAPEROPS_COMPLETION_GAPS_SCHEMA_VERSION}")
    print(f"paperops_completion_gaps_artifact_path={output_path}")
    print(f"paperops_completion_gaps_history_path={history_path}")
    print(
        "paperops_completion_gaps_operator_required_item_count="
        f"{written['operator_required_item_count']}"
    )
    print(
        "paperops_completion_gaps_paper_operation_blocking_gap_count="
        f"{written['paper_operation_blocking_gap_count']}"
    )
    print(
        "paperops_completion_gaps_optional_source_gap_count="
        f"{written['optional_source_gap_count']}"
    )
    print(f"paperops_completion_gaps_bookmap_connected={written['bookmap_connected']}")
    print(
        "paperops_completion_gaps_quantum_hardware_execution_confirmed="
        f"{written['quantum_hardware_execution_confirmed']}"
    )
    print(
        "paperops_completion_gaps_paperops_monitoring_ready="
        f"{written['paperops_monitoring_ready']}"
    )
    print(
        "paperops_completion_gaps_operator_required_keys="
        + ",".join(
            str(item.get("gap_key"))
            for item in written.get("operator_required_items", [])
            if isinstance(item, dict)
        )
    )
    print(f"paperops_completion_gaps_validation_errors={validation_errors}")

    if validation_errors:
        errors.append(f"completion gaps validation failed: {validation_errors}")
    if written["public_safe"] is not True:
        errors.append("completion gaps artifact is not public-safe")
    if quantum_items != quantum_items[:1] or not quantum_items:
        errors.append("completion gaps quantum item missing or duplicated")
    if not bookmap_items:
        errors.append("completion gaps Bookmap item missing")
    if not paperops_items:
        errors.append("completion gaps PaperOps monitoring item missing")
    if written["optional_source_gap_count"] != len(optional_source_items):
        errors.append("completion gaps optional source count mismatch")
    if written["paper_operation_blocking_gap_count"] != len(written.get("paper_blocking_items", [])):
        errors.append("completion gaps paper-blocking item count mismatch")
    if (
        "paperops_completion_gaps_forbidden:broker_write_allowed"
        not in authority_errors
    ):
        errors.append("broker-write authority probe was not rejected")
    if (
        "paperops_completion_gaps_forbidden:live_capital_enabled"
        not in authority_errors
    ):
        errors.append("live-capital authority probe was not rejected")
    if optional_source_items and (
        "paperops_completion_gaps_optional_source_blocks_paper"
        not in optional_source_errors
    ):
        errors.append("optional source blocking probe was not rejected")
    if written["quantum_hardware_execution_confirmed"]:
        quantum_item = quantum_items[0] if quantum_items else {}
        if quantum_item.get("current_state") != "IBM / Q-CTRL Hardware":
            errors.append("quantum hardware confirmation label is inconsistent")
    if not written["quantum_hardware_execution_confirmed"]:
        quantum_item = quantum_items[0] if quantum_items else {}
        if quantum_item.get("current_state") == "IBM / Q-CTRL Hardware":
            errors.append("quantum item overclaims hardware execution")

    if errors:
        print("paperops_completion_gaps_check=failed")
        for error in errors:
            print(f"error={error}")
        return 1
    print("paperops_completion_gaps_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
