#!/usr/bin/env python3
"""Validate RS-7 operator inbox, Telegram, and human oversight."""

from __future__ import annotations

from copy import deepcopy
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.cockpit_status import build_cockpit_status  # noqa: E402
from orchestrator.operator_inbox import (  # noqa: E402
    OPERATOR_INBOX_BOUNDARY,
    PUBLIC_STATUS_FIELDS,
    READ_ONLY_COMMANDS,
    build_operator_inbox,
    public_operator_inbox_status,
    validate_operator_inbox,
    write_operator_inbox,
)
from orchestrator.telegram_comms import ensure_d8a_telegram_dry_run  # noqa: E402
from orchestrator.telegram_inbound_intake import ensure_sample_telegram_inbound_intake  # noqa: E402


FORBIDDEN_PUBLIC_PATTERNS = (
    re.compile(r"\d{6,}:[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bvcp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"\bsb_secret_[0-9A-Za-z_-]{12,}\b"),
    re.compile(r"/Users/|/private/|/var/folders/|\\Users\\"),
    re.compile(r"chat_id|username|first_name|last_name|bot_token", re.IGNORECASE),
)


def _expect_rejected(payload: dict, expected_error: str) -> str | None:
    errors = validate_operator_inbox(payload)
    if expected_error not in errors:
        return f"expected_probe_error_missing:{expected_error}"
    return None


def _run_negative_probes(artifact: dict) -> list[str]:
    probe_errors: list[str] = []

    telegram_command = deepcopy(artifact)
    telegram_command["telegram_command_authority"] = True
    if error := _expect_rejected(
        telegram_command,
        "authority_enabled:telegram_command_authority",
    ):
        probe_errors.append(error)

    comment_approval = deepcopy(artifact)
    comment_approval["comment_can_approve_trades"] = True
    if error := _expect_rejected(comment_approval, "comment_can_approve_trades"):
        probe_errors.append(error)

    ack_approval = deepcopy(artifact)
    ack_approval["ack_can_approve_trades"] = True
    if error := _expect_rejected(ack_approval, "ack_can_approve_trades"):
        probe_errors.append(error)

    unsafe_command = deepcopy(artifact)
    unsafe_command["allowed_read_commands"] = list(READ_ONLY_COMMANDS) + ["/buy"]
    if error := _expect_rejected(unsafe_command, "allowed_read_commands_mismatch"):
        probe_errors.append(error)

    item_authority = deepcopy(artifact)
    if item_authority.get("items"):
        item_authority["items"][0]["paper_order_allowed"] = True
        item_authority["recent_items"][0]["paper_order_allowed"] = True
        if error := _expect_rejected(
            item_authority,
            f"item_authority_enabled:{item_authority['items'][0]['item_id']}:paper_order_allowed",
        ):
            probe_errors.append(error)

    return probe_errors


def main() -> int:
    settings = Settings.from_env()
    ensure_sample_telegram_inbound_intake(settings=settings)
    ensure_d8a_telegram_dry_run(settings=settings)

    base_payload = build_cockpit_status(settings=settings)
    artifact = write_operator_inbox(base_payload, settings=settings)
    validation_errors = validate_operator_inbox(artifact)
    probe_errors = _run_negative_probes(build_operator_inbox(base_payload, settings=settings))
    public_status = public_operator_inbox_status(artifact)
    public_encoded = json.dumps(public_status, sort_keys=True)

    public_missing = sorted(PUBLIC_STATUS_FIELDS - set(public_status))
    public_leak = any(pattern.search(public_encoded) for pattern in FORBIDDEN_PUBLIC_PATTERNS)

    print(f"operator_inbox_status={artifact['status']}")
    print(f"operator_inbox_item_count={artifact['item_count']}")
    print(f"operator_inbox_open_item_count={artifact['open_item_count']}")
    print(f"operator_inbox_high_or_critical_item_count={artifact['high_or_critical_item_count']}")
    print(f"operator_inbox_postmortem_due_item_count={artifact['postmortem_due_item_count']}")
    print(f"operator_inbox_paper_trade_related_item_count={artifact['paper_trade_related_item_count']}")
    print(f"operator_inbox_telegram_related_item_count={artifact['telegram_related_item_count']}")
    print(f"operator_inbox_allowed_read_command_count={artifact['read_command_count']}")
    print(f"operator_inbox_comment_count={artifact['comment_count']}")
    print(f"operator_inbox_acknowledgement_count={artifact['acknowledgement_count']}")
    print(f"operator_inbox_validation_error_count={len(validation_errors)}")
    print(f"operator_inbox_probe_error_count={len(probe_errors)}")
    print(f"operator_inbox_public_missing_field_count={len(public_missing)}")
    print(f"operator_inbox_public_leak={public_leak}")
    print("operator_inbox_report=data/runtime/operator_inbox.json")
    print(f"operator_inbox_boundary={artifact['boundary']}")

    errors: list[str] = []
    if artifact["status"] != "ok":
        errors.append("operator_inbox_status_not_ok")
    # An idle or clean paper epoch may legitimately have no review items. The
    # artifact validator already checks count parity, schema, and authority.
    if set(artifact["allowed_read_commands"]) != set(READ_ONLY_COMMANDS):
        errors.append("operator_inbox_read_commands_mismatch")
    if artifact["telegram_command_authority"] is not False:
        errors.append("operator_inbox_telegram_command_authority_enabled")
    if artifact["comment_can_approve_trades"] is not False:
        errors.append("operator_inbox_comment_approval_enabled")
    if artifact["ack_can_approve_trades"] is not False:
        errors.append("operator_inbox_ack_approval_enabled")
    for field in (
        "signal_authority",
        "trade_candidate_creation_allowed",
        "risk_handoff_allowed",
        "risk_approval_allowed",
        "execution_allowed",
        "execution_approval_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "qctrl_provider_call_allowed",
        "live_capital_enabled",
    ):
        if artifact.get(field) is not False:
            errors.append(f"operator_inbox_authority_enabled:{field}")
    if validation_errors:
        errors.extend(validation_errors)
    if probe_errors:
        errors.extend(probe_errors)
    if public_missing:
        errors.append("operator_inbox_public_fields_missing:" + ",".join(public_missing))
    if public_leak:
        errors.append("operator_inbox_public_secret_or_identifier_leak")
    if OPERATOR_INBOX_BOUNDARY not in artifact.get("boundary", ""):
        errors.append("operator_inbox_boundary_mismatch")

    if errors:
        for error in errors:
            print(f"operator_inbox_error={error}")
        print("operator_inbox_check=failed")
        return 1

    print("operator_inbox_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
