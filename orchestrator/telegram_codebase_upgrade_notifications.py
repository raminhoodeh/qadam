"""Telegram group notifications for Qadam codebase upgrades.

This module sends outbound-only Telegram group alerts after a codebase or
dashboard deployment upgrade has been recorded. It does not create commits,
push branches, deploy assets, approve trades, submit broker orders, or expose
secrets.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from typing import Any
import urllib.parse
import urllib.request

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.secrets import secret_status, secret_value
from orchestrator.telegram_comms import FORBIDDEN_TELEGRAM_TEXT


TELEGRAM_CODEBASE_UPGRADE_SCHEMA_VERSION = 1
TELEGRAM_CODEBASE_UPGRADE_RUNTIME_ARTIFACT = "telegram_codebase_upgrade_notification.json"
TELEGRAM_CODEBASE_UPGRADE_HISTORY = "telegram_codebase_upgrade_notifications_history.jsonl"
TELEGRAM_CODEBASE_UPGRADE_EVENT_LOG = "telegram_codebase_upgrade_notifications_events.jsonl"
TELEGRAM_CODEBASE_UPGRADE_EVENT_TYPE = "telegram_codebase_upgrade_notification_recorded"
TELEGRAM_CODEBASE_UPGRADE_COMPONENT = "telegram_codebase_upgrade_notifications"

TELEGRAM_CODEBASE_UPGRADE_BOUNDARY = (
    "Telegram codebase upgrade notifications are outbound group alerts for "
    "already-recorded Qadam codebase or dashboard upgrades only. They cannot "
    "create trade candidates, approve risk, approve execution, submit or close "
    "broker orders, handle Telegram commands, create commits, push code, deploy "
    "assets, expose secrets or chat ids, grant Phase 7 proof credit, or enable "
    "live capital."
)

TELEGRAM_CODEBASE_UPGRADE_FALSE_FIELDS = (
    "telegram_command_path_enabled",
    "telegram_trade_command_enabled",
    "trade_candidate_created",
    "risk_approval_allowed",
    "execution_allowed",
    "paper_execution_allowed",
    "paper_order_allowed",
    "paper_order_staging_allowed",
    "paper_order_submission_allowed",
    "broker_write_allowed",
    "broker_post_allowed",
    "alpaca_post_allowed",
    "order_cancel_allowed",
    "position_close_allowed",
    "position_resize_allowed",
    "repository_write_allowed",
    "git_commit_allowed",
    "git_push_allowed",
    "deploy_allowed",
    "deployment_mutation_allowed",
    "live_endpoint_allowed",
    "live_capital_enabled",
    "phase7_proof_credit_allowed",
    "secret_value_exposed",
    "raw_payload_exposed",
    "raw_provider_response_persisted",
    "authorization_header_exposed",
    "chat_id_exposed",
    "bot_token_exposed",
    "telegram_handle_exposed",
    "broker_order_identifier_exposed",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _short(value: Any, fallback: str = "unknown") -> str:
    text = str(value or "").strip()
    return text[:12] if text else fallback


def _clean_text(value: Any, fallback: str = "not provided", limit: int = 220) -> str:
    text = " ".join(str(value or "").replace("\n", " ").split())
    return (text[:limit] or fallback).strip()


def telegram_codebase_upgrade_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / TELEGRAM_CODEBASE_UPGRADE_RUNTIME_ARTIFACT,
        runtime / TELEGRAM_CODEBASE_UPGRADE_HISTORY,
        runtime / TELEGRAM_CODEBASE_UPGRADE_EVENT_LOG,
    )


def _delivery_path(settings: Settings) -> Path:
    path = _runtime_dir(settings) / "telegram-deliveries.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _sent_delivery_keys(settings: Settings) -> set[str]:
    path = _delivery_path(settings)
    if not path.exists():
        return set()
    keys: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if (
                isinstance(payload, dict)
                and payload.get("message_class") == "codebase_upgrade"
                and payload.get("target") == "group"
                and payload.get("status") == "sent"
            ):
                key = str(payload.get("delivery_key") or "")
                if key:
                    keys.add(key)
    return keys


def _archive_delivery(settings: Settings, payload: dict[str, Any]) -> None:
    safe_payload = {
        "schema_version": TELEGRAM_CODEBASE_UPGRADE_SCHEMA_VERSION,
        "created_at": payload.get("created_at") or _now(),
        "target": "group",
        "status": payload.get("status", "unknown"),
        "message_class": "codebase_upgrade",
        "delivery_key": payload.get("delivery_key"),
        "telegram_message_id": payload.get("telegram_message_id"),
        "failure_category": payload.get("failure_category"),
        "send_requested": payload.get("send_requested") is True,
        "live_send_attempted": payload.get("live_send_attempted") is True,
        "bot_token_exposed": False,
        "chat_id_exposed": False,
        "raw_provider_response_persisted": False,
        "boundary": TELEGRAM_CODEBASE_UPGRADE_BOUNDARY,
    }
    with _delivery_path(settings).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(safe_payload, sort_keys=True) + "\n")


def _telegram_send(token: str, chat_id: str, text: str) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload if isinstance(payload, dict) else {}


def _git_output(repo: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:  # noqa: BLE001 - degrade public status safely.
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _git_repo_state(repo: Path, label: str) -> dict[str, Any]:
    head = _git_output(repo, "rev-parse", "HEAD") or "unknown"
    short_head = _git_output(repo, "rev-parse", "--short=12", "HEAD") or _short(head)
    branch = _git_output(repo, "rev-parse", "--abbrev-ref", "HEAD") or "unknown"
    status_lines = [
        line
        for line in _git_output(repo, "status", "--porcelain=v1").splitlines()
        if line.strip()
    ]
    staged = 0
    unstaged = 0
    untracked = 0
    for line in status_lines:
        marker = line[:2]
        if marker == "??":
            untracked += 1
            continue
        if marker[:1].strip():
            staged += 1
        if marker[1:2].strip():
            unstaged += 1
    status_digest = sha256("\n".join(sorted(status_lines)).encode("utf-8")).hexdigest()
    fingerprint = sha256(f"{head}:{status_digest}".encode("utf-8")).hexdigest()
    return {
        "repo": label,
        "head": head,
        "head_short": short_head,
        "branch": branch,
        "dirty": bool(status_lines),
        "status_digest": status_digest,
        "fingerprint": fingerprint,
        "changed_file_count": len(status_lines),
        "staged_file_count": staged,
        "unstaged_file_count": unstaged,
        "untracked_file_count": untracked,
    }


def _safe_url(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    parsed = urllib.parse.urlparse(text)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        return None
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path[:120], "", "", ""))


def _safe_aliases(values: Any) -> list[str]:
    if not isinstance(values, list | tuple):
        return []
    aliases: list[str] = []
    for value in values:
        text = str(value or "").strip().lower()
        if text in {"qadam.trade", "www.qadam.trade"} and text not in aliases:
            aliases.append(text)
    return aliases


def _deployment_context(
    settings: Settings,
    *,
    deployment_url: str | None = None,
    aliases: list[str] | None = None,
) -> dict[str, Any]:
    receipt = _read_json(_runtime_dir(settings) / "dashboard-deployment-receipt.json")
    safe_url = _safe_url(deployment_url) or _safe_url(receipt.get("deployment_url"))
    safe_aliases = _safe_aliases(aliases) or _safe_aliases(receipt.get("aliases"))
    if not safe_aliases:
        safe_aliases = ["qadam.trade", "www.qadam.trade"]
    return {
        "deployment_url": safe_url,
        "aliases": safe_aliases,
        "receipt_present": bool(receipt),
        "receipt_deployed_at": receipt.get("deployed_at") if isinstance(receipt, dict) else None,
    }


def _render_upgrade_message(source: dict[str, Any]) -> tuple[str, str]:
    root = source.get("root_repo", {})
    dashboard = source.get("dashboard_repo", {})
    deployment = source.get("deployment", {})
    aliases = ", ".join(deployment.get("aliases", []) or ["qadam.trade", "www.qadam.trade"])
    deployment_text = deployment.get("deployment_url") or aliases
    action = "deployed" if source.get("source") == "production_deploy" else "recorded"
    title = "Qadam Codebase Upgrade"
    body = "\n".join(
        [
            f"Qadam: codebase upgrade {action}",
            f"Upgrade: core {_short(root.get('head_short'))} / dashboard {_short(dashboard.get('head_short'))}",
            f"What changed: {_clean_text(source.get('summary'), 'Qadam codebase and dashboard were upgraded.')}",
            f"Deployment: {deployment_text}",
            f"Aliases: {aliases}",
            "Status: notification only. Trading logic, broker writes, paper orders, and live capital are unchanged by Telegram.",
            "Dashboard: qadam.trade/dashboard/",
        ]
    )
    return title, body


def _safe_text(title: str, body: str) -> bool:
    text = f"{title}\n{body}"
    return all(not pattern.search(text) for pattern in FORBIDDEN_TELEGRAM_TEXT)


def _delivery_key(source: dict[str, Any], *, force_send: bool, generated_at: str) -> str:
    deployment = source.get("deployment", {})
    raw = {
        "dashboard": source.get("dashboard_repo", {}).get("fingerprint"),
        "deployment_url": deployment.get("deployment_url"),
        "root": source.get("root_repo", {}).get("fingerprint"),
        "source": source.get("source"),
        "summary": source.get("summary"),
    }
    if force_send:
        raw["force_generated_at"] = generated_at
    return sha256(
        ("qadam:telegram_codebase_upgrade:" + json.dumps(raw, sort_keys=True)).encode("utf-8")
    ).hexdigest()


def build_telegram_codebase_upgrade_notification(
    settings: Settings | None = None,
    *,
    send_requested: bool = False,
    force_send: bool = False,
    summary: str | None = None,
    source: str = "manual",
    deployment_url: str | None = None,
    aliases: list[str] | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    root = _repo_root()
    source_context = {
        "source": _clean_text(source, "manual", limit=80),
        "summary": _clean_text(summary, "Qadam codebase and dashboard were upgraded."),
        "root_repo": _git_repo_state(root, "qadam-core"),
        "dashboard_repo": _git_repo_state(root / "landing-page-repo", "qadam-dashboard"),
        "deployment": _deployment_context(settings, deployment_url=deployment_url, aliases=aliases),
    }
    title, body = _render_upgrade_message(source_context)
    text = f"{title}\n\n{body}"
    message_safe = _safe_text(title, body)
    token = secret_value("TELEGRAM_BOT_TOKEN", settings)
    chat_id = secret_value("TELEGRAM_GROUP_CHAT_ID", settings)
    bot_configured = secret_status("TELEGRAM_BOT_TOKEN", settings).configured
    group_chat_configured = secret_status("TELEGRAM_GROUP_CHAT_ID", settings).configured
    enabled = settings.telegram_codebase_upgrade_notifications_enabled
    dry_run = settings.telegram_codebase_upgrade_notifications_dry_run
    delivery_key = _delivery_key(source_context, force_send=force_send, generated_at=generated_at)
    already_sent = delivery_key in _sent_delivery_keys(settings)

    blockers: list[str] = []
    if not message_safe:
        blockers.append("unsafe_message_text")
    if not enabled:
        blockers.append("codebase_upgrade_notifications_disabled")
    if dry_run:
        blockers.append("codebase_upgrade_notifications_dry_run")
    if not bot_configured:
        blockers.append("telegram_bot_token_missing")
    if not group_chat_configured:
        blockers.append("telegram_group_chat_missing")
    if already_sent and not force_send:
        blockers.append("telegram_codebase_upgrade_already_sent")

    status = "dry_run_ready" if message_safe else "suppressed_not_safe"
    if message_safe and not enabled:
        status = "blocked_pending_enablement"
    elif message_safe and enabled and not dry_run:
        status = "ready_to_send"
    if already_sent and not force_send:
        status = "already_sent"

    live_send_attempted = False
    live_send_succeeded = False
    telegram_message_id: int | None = None
    failure_category: str | None = None
    if (
        send_requested
        and message_safe
        and enabled
        and not dry_run
        and bot_configured
        and group_chat_configured
        and (not already_sent or force_send)
    ):
        live_send_attempted = True
        try:
            assert token is not None
            assert chat_id is not None
            response = _telegram_send(token, chat_id, text)
            if response.get("ok") is True:
                live_send_succeeded = True
                result = response.get("result", {})
                if isinstance(result, dict) and result.get("message_id") is not None:
                    telegram_message_id = int(result["message_id"])
                status = "sent"
            else:
                status = "failed"
                failure_category = "telegram_api_rejected"
        except Exception as exc:  # noqa: BLE001 - keep persisted failure sanitized.
            status = "failed"
            failure_category = type(exc).__name__

        _archive_delivery(
            settings,
            {
                "created_at": _now(),
                "status": status,
                "delivery_key": delivery_key,
                "telegram_message_id": telegram_message_id,
                "failure_category": failure_category,
                "send_requested": send_requested,
                "live_send_attempted": live_send_attempted,
            },
        )

    artifact = {
        "schema_version": TELEGRAM_CODEBASE_UPGRADE_SCHEMA_VERSION,
        "artifact_type": "telegram_codebase_upgrade_notification",
        "artifact_id": f"telegram:codebase-upgrade:{delivery_key[:16]}",
        "phase": "PaperOps",
        "stage": "Codebase-Upgrade-Notify",
        "status": status,
        "generated_at": generated_at,
        "public_safe": True,
        "recorded": False,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_event_count": 0,
        "runtime_artifact_path": None,
        "history_log_path": None,
        "mode": settings.mode,
        "target": "group",
        "recipient_scope": "fund_manager_group",
        "message_class": "codebase_upgrade",
        "delivery_key": delivery_key,
        "source": source_context["source"],
        "summary": source_context["summary"],
        "root_commit": source_context["root_repo"]["head"],
        "root_commit_short": source_context["root_repo"]["head_short"],
        "root_branch": source_context["root_repo"]["branch"],
        "root_dirty": source_context["root_repo"]["dirty"],
        "root_changed_file_count": source_context["root_repo"]["changed_file_count"],
        "root_staged_file_count": source_context["root_repo"]["staged_file_count"],
        "root_unstaged_file_count": source_context["root_repo"]["unstaged_file_count"],
        "root_untracked_file_count": source_context["root_repo"]["untracked_file_count"],
        "dashboard_commit": source_context["dashboard_repo"]["head"],
        "dashboard_commit_short": source_context["dashboard_repo"]["head_short"],
        "dashboard_branch": source_context["dashboard_repo"]["branch"],
        "dashboard_dirty": source_context["dashboard_repo"]["dirty"],
        "dashboard_changed_file_count": source_context["dashboard_repo"]["changed_file_count"],
        "dashboard_staged_file_count": source_context["dashboard_repo"]["staged_file_count"],
        "dashboard_unstaged_file_count": source_context["dashboard_repo"]["unstaged_file_count"],
        "dashboard_untracked_file_count": source_context["dashboard_repo"]["untracked_file_count"],
        "deployment_url": source_context["deployment"]["deployment_url"],
        "aliases": source_context["deployment"]["aliases"],
        "deployment_receipt_present": source_context["deployment"]["receipt_present"],
        "deployment_receipt_deployed_at": source_context["deployment"]["receipt_deployed_at"],
        "codebase_upgrade_notifications_enabled": enabled,
        "codebase_upgrade_notifications_dry_run": dry_run,
        "send_requested": send_requested,
        "force_send": force_send,
        "already_sent": already_sent,
        "bot_configured": bot_configured,
        "group_chat_configured": group_chat_configured,
        "message_preview": {"title": title, "body": body, "dashboard_link": "qadam.trade/dashboard/"},
        "message_preview_redacted": message_safe,
        "live_send_attempted": live_send_attempted,
        "live_send_succeeded": live_send_succeeded,
        "telegram_message_id_present": telegram_message_id is not None,
        "delivery_failure_category": failure_category,
        "blockers": blockers,
        "blocker_count": len(blockers),
        **{field: False for field in TELEGRAM_CODEBASE_UPGRADE_FALSE_FIELDS},
        "boundary": TELEGRAM_CODEBASE_UPGRADE_BOUNDARY,
    }
    artifact["validation_errors"] = validate_telegram_codebase_upgrade_notification(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "invalid"
    return artifact


def validate_telegram_codebase_upgrade_notification(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "aliases",
        "artifact_id",
        "artifact_type",
        "boundary",
        "bot_configured",
        "codebase_upgrade_notifications_dry_run",
        "codebase_upgrade_notifications_enabled",
        "dashboard_changed_file_count",
        "dashboard_commit_short",
        "delivery_key",
        "deployment_url",
        "group_chat_configured",
        "live_send_attempted",
        "live_send_succeeded",
        "message_class",
        "message_preview",
        "message_preview_redacted",
        "public_safe",
        "root_changed_file_count",
        "root_commit_short",
        "send_requested",
        "status",
        "summary",
        "target",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("telegram_codebase_upgrade_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != TELEGRAM_CODEBASE_UPGRADE_SCHEMA_VERSION:
        errors.append("telegram_codebase_upgrade_schema_version_mismatch")
    if artifact.get("artifact_type") != "telegram_codebase_upgrade_notification":
        errors.append("telegram_codebase_upgrade_type_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("telegram_codebase_upgrade_not_public_safe")
    if artifact.get("mode") != "paper":
        errors.append("telegram_codebase_upgrade_mode_not_paper")
    if artifact.get("target") != "group":
        errors.append("telegram_codebase_upgrade_target_not_group")
    if artifact.get("message_class") != "codebase_upgrade":
        errors.append("telegram_codebase_upgrade_message_class_invalid")
    if artifact.get("status") not in {
        "already_sent",
        "blocked_pending_enablement",
        "dry_run_ready",
        "failed",
        "invalid",
        "ready_to_send",
        "sent",
        "suppressed_not_safe",
    }:
        errors.append("telegram_codebase_upgrade_status_invalid")
    preview = artifact.get("message_preview", {})
    if not isinstance(preview, dict):
        errors.append("telegram_codebase_upgrade_preview_missing")
    else:
        title = str(preview.get("title") or "")
        body = str(preview.get("body") or "")
        if not title.strip() or not body.strip():
            errors.append("telegram_codebase_upgrade_preview_empty")
        for phrase in (
            "Qadam: codebase upgrade",
            "Upgrade:",
            "What changed:",
            "Deployment:",
            "Status: notification only.",
            "Dashboard: qadam.trade/dashboard/",
        ):
            if phrase not in body:
                errors.append("telegram_codebase_upgrade_message_missing:" + phrase)
        if not _safe_text(title, body):
            errors.append("telegram_codebase_upgrade_forbidden_text")
    if artifact.get("message_preview_redacted") is not True:
        errors.append("telegram_codebase_upgrade_preview_not_redacted")
    if artifact.get("live_send_attempted") is True:
        if artifact.get("send_requested") is not True:
            errors.append("telegram_codebase_upgrade_live_attempt_without_request")
        if artifact.get("codebase_upgrade_notifications_enabled") is not True:
            errors.append("telegram_codebase_upgrade_live_attempt_without_gate")
        if artifact.get("codebase_upgrade_notifications_dry_run") is not False:
            errors.append("telegram_codebase_upgrade_live_attempt_in_dry_run")
        if artifact.get("bot_configured") is not True:
            errors.append("telegram_codebase_upgrade_live_attempt_without_bot")
        if artifact.get("group_chat_configured") is not True:
            errors.append("telegram_codebase_upgrade_live_attempt_without_group")
    if artifact.get("live_send_succeeded") is True and artifact.get("status") != "sent":
        errors.append("telegram_codebase_upgrade_succeeded_status_mismatch")
    for field in TELEGRAM_CODEBASE_UPGRADE_FALSE_FIELDS:
        if artifact.get(field) is not False:
            errors.append(f"telegram_codebase_upgrade_authority_enabled:{field}")
    if "cannot create trade candidates" not in str(artifact.get("boundary") or ""):
        errors.append("telegram_codebase_upgrade_boundary_weak")
    encoded = json.dumps(
        {
            "aliases": artifact.get("aliases"),
            "deployment_url": artifact.get("deployment_url"),
            "message_preview": artifact.get("message_preview"),
            "summary": artifact.get("summary"),
        },
        sort_keys=True,
    )
    if (
        "/Users/" in encoded
        or "/private/" in encoded
        or "@" in encoded
        or "chat_id" in encoded
        or "bot_token" in encoded
    ):
        errors.append("telegram_codebase_upgrade_public_text_leak")
    return sorted(set(errors))


def write_telegram_codebase_upgrade_notification(
    artifact: dict[str, Any],
    settings: Settings | None = None,
    *,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    settings = settings or Settings.from_env()
    output_path, history_path, default_event_path = telegram_codebase_upgrade_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = deepcopy(artifact)
    written["recorded"] = True
    written["runtime_artifact_path"] = str(output_path)
    written["history_log_path"] = str(history_path)
    if record_event:
        event = EventLog(event_path, echo=False).write(
            TELEGRAM_CODEBASE_UPGRADE_EVENT_TYPE,
            TELEGRAM_CODEBASE_UPGRADE_COMPONENT,
            {
                "status": written.get("status"),
                "delivery_key": written.get("delivery_key"),
                "source": written.get("source"),
                "root_commit_short": written.get("root_commit_short"),
                "dashboard_commit_short": written.get("dashboard_commit_short"),
                "deployment_url_present": bool(written.get("deployment_url")),
                "codebase_upgrade_notifications_enabled": written.get(
                    "codebase_upgrade_notifications_enabled"
                ),
                "codebase_upgrade_notifications_dry_run": written.get(
                    "codebase_upgrade_notifications_dry_run"
                ),
                "live_send_attempted": written.get("live_send_attempted"),
                "live_send_succeeded": written.get("live_send_succeeded"),
                "telegram_command_path_enabled": written.get("telegram_command_path_enabled"),
                "broker_write_allowed": written.get("broker_write_allowed"),
                "paper_order_allowed": written.get("paper_order_allowed"),
                "repository_write_allowed": written.get("repository_write_allowed"),
                "deploy_allowed": written.get("deploy_allowed"),
                "live_capital_enabled": written.get("live_capital_enabled"),
                "secret_value_exposed": written.get("secret_value_exposed"),
                "chat_id_exposed": written.get("chat_id_exposed"),
                "bot_token_exposed": written.get("bot_token_exposed"),
                "boundary": written.get("boundary"),
            },
        )
        written["event_log_written"] = True
        written["event_log_path"] = str(event_path)
        written["event_log_event_count"] = 1
        written["event_log_correlation_id"] = event.correlation_id
        written["event_log_created_at"] = event.created_at
    written["validation_errors"] = validate_telegram_codebase_upgrade_notification(written)
    if written["validation_errors"]:
        written["status"] = "invalid"
    output_path.write_text(json.dumps(written, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": TELEGRAM_CODEBASE_UPGRADE_SCHEMA_VERSION,
        "artifact_id": written.get("artifact_id"),
        "status": written.get("status"),
        "recorded_at": _now(),
        "delivery_key": written.get("delivery_key"),
        "root_commit_short": written.get("root_commit_short"),
        "dashboard_commit_short": written.get("dashboard_commit_short"),
        "deployment_url_present": bool(written.get("deployment_url")),
        "live_send_attempted": written.get("live_send_attempted"),
        "live_send_succeeded": written.get("live_send_succeeded"),
        "validation_error_count": len(written.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, written


def telegram_codebase_upgrade_public_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    output_path, _, _ = telegram_codebase_upgrade_paths(settings)
    artifact = _read_json(output_path)
    if not artifact:
        return {
            "schema_version": TELEGRAM_CODEBASE_UPGRADE_SCHEMA_VERSION,
            "status": "not_run",
            "enabled": settings.telegram_codebase_upgrade_notifications_enabled,
            "dry_run": settings.telegram_codebase_upgrade_notifications_dry_run,
            "target": "group",
            "source": None,
            "summary": None,
            "root_commit_short": None,
            "root_dirty": False,
            "root_changed_file_count": 0,
            "dashboard_commit_short": None,
            "dashboard_dirty": False,
            "dashboard_changed_file_count": 0,
            "deployment_url": None,
            "aliases": ["qadam.trade", "www.qadam.trade"],
            "already_sent": False,
            "live_send_attempted": False,
            "live_send_succeeded": False,
            "telegram_message_id_present": False,
            "last_delivery_failure_category": None,
            "blocker_count": 0,
            "blockers": [],
            "telegram_command_path_enabled": False,
            "broker_write_allowed": False,
            "paper_order_allowed": False,
            "repository_write_allowed": False,
            "deploy_allowed": False,
            "live_capital_enabled": False,
            "boundary": TELEGRAM_CODEBASE_UPGRADE_BOUNDARY,
        }
    return {
        "schema_version": TELEGRAM_CODEBASE_UPGRADE_SCHEMA_VERSION,
        "status": artifact.get("status", "unknown"),
        "enabled": artifact.get("codebase_upgrade_notifications_enabled") is True,
        "dry_run": artifact.get("codebase_upgrade_notifications_dry_run") is True,
        "target": "group",
        "source": artifact.get("source"),
        "summary": artifact.get("summary"),
        "root_commit_short": artifact.get("root_commit_short"),
        "root_dirty": artifact.get("root_dirty") is True,
        "root_changed_file_count": _int(artifact.get("root_changed_file_count")),
        "dashboard_commit_short": artifact.get("dashboard_commit_short"),
        "dashboard_dirty": artifact.get("dashboard_dirty") is True,
        "dashboard_changed_file_count": _int(artifact.get("dashboard_changed_file_count")),
        "deployment_url": artifact.get("deployment_url"),
        "aliases": [str(item) for item in artifact.get("aliases", [])],
        "already_sent": artifact.get("already_sent") is True,
        "live_send_attempted": artifact.get("live_send_attempted") is True,
        "live_send_succeeded": artifact.get("live_send_succeeded") is True,
        "telegram_message_id_present": artifact.get("telegram_message_id_present") is True,
        "last_delivery_failure_category": artifact.get("delivery_failure_category"),
        "blocker_count": _int(artifact.get("blocker_count")),
        "blockers": [str(item) for item in artifact.get("blockers", [])],
        "telegram_command_path_enabled": False,
        "broker_write_allowed": False,
        "paper_order_allowed": False,
        "repository_write_allowed": False,
        "deploy_allowed": False,
        "live_capital_enabled": False,
        "boundary": TELEGRAM_CODEBASE_UPGRADE_BOUNDARY,
    }
