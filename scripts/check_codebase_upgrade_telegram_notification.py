#!/usr/bin/env python3
"""Validate Telegram codebase-upgrade notification behavior."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.telegram_codebase_upgrade_notifications import (  # noqa: E402
    TELEGRAM_CODEBASE_UPGRADE_SCHEMA_VERSION,
    build_telegram_codebase_upgrade_notification,
    telegram_codebase_upgrade_paths,
    telegram_codebase_upgrade_public_status,
    validate_telegram_codebase_upgrade_notification,
    write_telegram_codebase_upgrade_notification,
)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_path = telegram_codebase_upgrade_paths(settings)
    previous_output = output_path.read_text(encoding="utf-8") if output_path.exists() else None
    if event_path.exists():
        event_path.unlink()

    artifact = build_telegram_codebase_upgrade_notification(
        settings=settings,
        send_requested=False,
        summary="Qadam now sends Telegram group updates when the codebase is upgraded.",
        source="contract_check",
        deployment_url="https://qadam-contract-check.vercel.app",
        aliases=["qadam.trade", "www.qadam.trade"],
        details=[
            "The notifier records upgrade fingerprints without exposing local paths.",
            "The dashboard Communications panel can show the latest send state.",
        ],
        benefits=[
            "Fund Managers get the context and benefit of an update in the chat.",
            "The message separates communication changes from trading authority.",
        ],
    )
    output_path, history_path, event_path, written = write_telegram_codebase_upgrade_notification(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_path,
    )
    validation_errors = validate_telegram_codebase_upgrade_notification(written)
    replay = EventLog(event_path, echo=False).replay()
    public_status = telegram_codebase_upgrade_public_status(settings)

    forced_preview = build_telegram_codebase_upgrade_notification(
        settings=settings,
        send_requested=False,
        force_send=True,
        summary="Qadam now sends Telegram group updates when the codebase is upgraded.",
        source="contract_check",
        deployment_url="https://qadam-contract-check.vercel.app",
        aliases=["qadam.trade", "www.qadam.trade"],
        details=[
            "The notifier records upgrade fingerprints without exposing local paths.",
            "The dashboard Communications panel can show the latest send state.",
        ],
        benefits=[
            "Fund Managers get the context and benefit of an update in the chat.",
            "The message separates communication changes from trading authority.",
        ],
    )
    forced_validation_errors = validate_telegram_codebase_upgrade_notification(forced_preview)

    same_commit_first = build_telegram_codebase_upgrade_notification(
        settings=settings,
        send_requested=False,
        summary="Same commit notification idempotency check.",
        source="contract_check",
        deployment_url="https://qadam-contract-check-a.vercel.app",
        aliases=["qadam.trade", "www.qadam.trade"],
    )
    same_commit_second = build_telegram_codebase_upgrade_notification(
        settings=settings,
        send_requested=False,
        summary="Same commit notification idempotency check.",
        source="contract_check",
        deployment_url="https://qadam-contract-check-b.vercel.app",
        aliases=["qadam.trade", "www.qadam.trade"],
    )

    command_probe = deepcopy(forced_preview)
    command_probe["telegram_command_path_enabled"] = True
    command_errors = validate_telegram_codebase_upgrade_notification(command_probe)

    broker_probe = deepcopy(forced_preview)
    broker_probe["broker_write_allowed"] = True
    broker_errors = validate_telegram_codebase_upgrade_notification(broker_probe)

    repo_probe = deepcopy(forced_preview)
    repo_probe["repository_write_allowed"] = True
    repo_errors = validate_telegram_codebase_upgrade_notification(repo_probe)

    deploy_probe = deepcopy(forced_preview)
    deploy_probe["deploy_allowed"] = True
    deploy_errors = validate_telegram_codebase_upgrade_notification(deploy_probe)

    live_capital_probe = deepcopy(forced_preview)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_errors = validate_telegram_codebase_upgrade_notification(live_capital_probe)

    secret_probe = deepcopy(forced_preview)
    secret_probe["bot_token_exposed"] = True
    secret_errors = validate_telegram_codebase_upgrade_notification(secret_probe)

    print(f"telegram_codebase_upgrade_status={written['status']}")
    print(
        "telegram_codebase_upgrade_schema_version="
        f"{TELEGRAM_CODEBASE_UPGRADE_SCHEMA_VERSION}"
    )
    print(f"telegram_codebase_upgrade_artifact_path={output_path}")
    print(f"telegram_codebase_upgrade_history_path={history_path}")
    print(f"telegram_codebase_upgrade_event_log_path={event_path}")
    print(f"telegram_codebase_upgrade_source={written['source']}")
    print(f"telegram_codebase_upgrade_root_commit_short={written['root_commit_short']}")
    print(
        "telegram_codebase_upgrade_dashboard_commit_short="
        f"{written['dashboard_commit_short']}"
    )
    print(f"telegram_codebase_upgrade_deployment_url={written['deployment_url']}")
    print(
        "telegram_codebase_upgrade_enabled="
        f"{written['codebase_upgrade_notifications_enabled']}"
    )
    print(
        "telegram_codebase_upgrade_dry_run="
        f"{written['codebase_upgrade_notifications_dry_run']}"
    )
    print(f"telegram_codebase_upgrade_bot_configured={written['bot_configured']}")
    print(
        "telegram_codebase_upgrade_group_chat_configured="
        f"{written['group_chat_configured']}"
    )
    print(f"telegram_codebase_upgrade_send_requested={written['send_requested']}")
    print(f"telegram_codebase_upgrade_already_sent={written['already_sent']}")
    print(f"telegram_codebase_upgrade_live_send_attempted={written['live_send_attempted']}")
    print(f"telegram_codebase_upgrade_live_send_succeeded={written['live_send_succeeded']}")
    print(f"telegram_codebase_upgrade_detail_count={len(written['details'])}")
    print(f"telegram_codebase_upgrade_benefit_count={len(written['benefits'])}")
    print(f"telegram_codebase_upgrade_change_area_count={len(written['change_area_lines'])}")
    print(
        "telegram_codebase_upgrade_specificity_status="
        f"{written['message_specificity_status']}"
    )
    print(
        "telegram_codebase_upgrade_specificity_score="
        f"{written['message_specificity_score']}"
    )
    print(f"telegram_codebase_upgrade_event_log_events={replay['total_events']}")
    print(f"telegram_codebase_upgrade_public_status={public_status['status']}")
    print(f"telegram_codebase_upgrade_public_enabled={public_status['enabled']}")
    print(f"telegram_codebase_upgrade_validation_errors={validation_errors}")
    print(
        "telegram_codebase_upgrade_forced_validation_errors="
        f"{forced_validation_errors}"
    )
    print(f"telegram_codebase_upgrade_command_probe_error_count={len(command_errors)}")
    print(f"telegram_codebase_upgrade_broker_probe_error_count={len(broker_errors)}")
    print(f"telegram_codebase_upgrade_repo_probe_error_count={len(repo_errors)}")
    print(f"telegram_codebase_upgrade_deploy_probe_error_count={len(deploy_errors)}")
    print(
        "telegram_codebase_upgrade_live_capital_probe_error_count="
        f"{len(live_capital_errors)}"
    )
    print(f"telegram_codebase_upgrade_secret_probe_error_count={len(secret_errors)}")

    if validation_errors:
        errors.extend(validation_errors)
    if forced_validation_errors:
        errors.extend(forced_validation_errors)
    if replay["total_events"] != 1:
        errors.append("telegram_codebase_upgrade_event_log_count_mismatch")
    if written["message_class"] != "codebase_upgrade":
        errors.append("telegram_codebase_upgrade_message_class_mismatch")
    if not written["delivery_key"]:
        errors.append("telegram_codebase_upgrade_delivery_key_missing")
    if same_commit_first["delivery_key"] != same_commit_second["delivery_key"]:
        errors.append("telegram_codebase_upgrade_delivery_key_deployment_url_sensitive")
    if len(written.get("details", [])) < 2:
        errors.append("telegram_codebase_upgrade_details_missing")
    if len(written.get("benefits", [])) < 2:
        errors.append("telegram_codebase_upgrade_benefits_missing")
    if len(written.get("change_area_lines", [])) < 1:
        errors.append("telegram_codebase_upgrade_change_areas_missing")
    if written.get("message_specificity_status") != "specific":
        errors.append("telegram_codebase_upgrade_not_specific")
    if int(written.get("message_specificity_score", 0) or 0) < 70:
        errors.append("telegram_codebase_upgrade_specificity_score_low")
    if not written["root_commit_short"] or not written["dashboard_commit_short"]:
        errors.append("telegram_codebase_upgrade_git_fingerprint_missing")
    if written["deployment_url"] != "https://qadam-contract-check.vercel.app":
        errors.append("telegram_codebase_upgrade_deployment_url_sanitized_wrong")
    if public_status["target"] != "group":
        errors.append("telegram_codebase_upgrade_public_target_not_group")
    for field in (
        "telegram_command_path_enabled",
        "broker_write_allowed",
        "paper_order_allowed",
        "repository_write_allowed",
        "deploy_allowed",
        "live_capital_enabled",
    ):
        if public_status[field] is not False:
            errors.append(f"telegram_codebase_upgrade_public_authority_enabled:{field}")
    expected = (
        (
            "telegram_codebase_upgrade_authority_enabled:telegram_command_path_enabled",
            command_errors,
        ),
        ("telegram_codebase_upgrade_authority_enabled:broker_write_allowed", broker_errors),
        ("telegram_codebase_upgrade_authority_enabled:repository_write_allowed", repo_errors),
        ("telegram_codebase_upgrade_authority_enabled:deploy_allowed", deploy_errors),
        ("telegram_codebase_upgrade_authority_enabled:live_capital_enabled", live_capital_errors),
        ("telegram_codebase_upgrade_authority_enabled:bot_token_exposed", secret_errors),
    )
    for marker, probe_errors in expected:
        if marker not in probe_errors:
            errors.append(f"telegram_codebase_upgrade_probe_not_rejected:{marker}")
    preview_body = forced_preview.get("message_preview", {}).get("body", "")
    if not preview_body.startswith("Qadam update."):
        errors.append("telegram_codebase_upgrade_preview_missing:qadam_update_intro")
    if "This helps because" not in preview_body:
        errors.append("telegram_codebase_upgrade_preview_missing:plain_explanation")
    for marker in (
        "Qadam has just gone live",
        "Qadam has gone live",
        "Telegram still has no trading power",
        "live capital",
    ):
        if marker in preview_body:
            errors.append(f"telegram_codebase_upgrade_preview_repetitive_disclaimer:{marker}")
    for marker in (
        "Upgrade:",
        "What changed:",
        "Detected update areas:",
        "Why it matters:",
        "Evidence:",
        "Status:",
        "Dashboard:",
        "What to check:",
        "Deployment:",
        "Aliases:",
        "commit",
        "version control",
        "Vercel",
    ):
        if marker in preview_body:
            errors.append(f"telegram_codebase_upgrade_preview_too_verbose:{marker}")
    if len([line for line in preview_body.splitlines() if line.strip()]) > 3:
        errors.append("telegram_codebase_upgrade_preview_too_many_lines")
    public_encoded = str(public_status)
    if "/Users/" in public_encoded or "chat_id" in public_encoded or "bot_token" in public_encoded:
        errors.append("telegram_codebase_upgrade_public_leak")

    if previous_output is None:
        output_path.unlink(missing_ok=True)
    else:
        output_path.write_text(previous_output, encoding="utf-8")

    if errors:
        for error in errors:
            print(f"telegram_codebase_upgrade_error={error}")
        print("telegram_codebase_upgrade_check=failed")
        return 1
    print("telegram_codebase_upgrade_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
