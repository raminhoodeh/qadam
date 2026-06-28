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
import re
import subprocess
from typing import Any
import urllib.parse
import urllib.request

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.secrets import secret_status, secret_value
from orchestrator.telegram_comms import FORBIDDEN_TELEGRAM_TEXT
from orchestrator.telegram_message_quality import (
    telegram_human_message_style,
    telegram_message_specificity,
)


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


def _clean_list(values: Any, fallback: list[str], *, limit: int = 160, count: int = 4) -> list[str]:
    if not isinstance(values, list | tuple):
        values = []
    cleaned: list[str] = []
    for value in values:
        text = _clean_text(value, "", limit=limit)
        if text and text not in cleaned:
            cleaned.append(text)
        if len(cleaned) >= count:
            break
    return cleaned or fallback[:count]


def _sentence_fragment(value: Any, fallback: str = "", *, limit: int = 180) -> str:
    text = _clean_text(value, fallback, limit=limit).rstrip(".")
    if text.startswith("The "):
        text = "the " + text[4:]
    elif text.startswith("A "):
        text = "a " + text[2:]
    elif text.startswith("An "):
        text = "an " + text[3:]
    elif text:
        text = text[0].lower() + text[1:]
    return text


def _telegram_body_safe_fragment(value: Any) -> bool:
    text = str(value or "")
    return not re.search(
        r"\b(?:commit|branch|git|vercel|deployment|delivery key|fingerprint|schema|artifact|runtime|repo|repository|alias(?:es)?)\b|https?://|qadam\.trade/",
        text,
        re.IGNORECASE,
    )


def _status_paths(status_lines: list[str]) -> list[str]:
    paths: list[str] = []
    for line in status_lines:
        text = line[2:].strip() if len(line) > 2 else line.strip()
        if " -> " in text:
            text = text.rsplit(" -> ", 1)[-1].strip()
        if text:
            paths.append(text)
    return paths


def _git_file_list(repo: Path, *args: str) -> list[str]:
    return [
        line.strip()
        for line in _git_output(repo, *args).splitlines()
        if line.strip()
    ]


def _change_area_for_path(path: str) -> str:
    if path == "orchestrator/provider_decision_pass.py" or path == "orchestrator/source_health.py":
        return "source provider decisions"
    if path in {
        "scripts/check_provider_decision_pass.py",
        "scripts/check_source_registry_blockers.py",
    }:
        return "source provider regression checks"
    if path == "world_monitor/source_registry.py":
        return "source registry"
    if path.startswith("orchestrator/telegram") or path.startswith("scripts/send_telegram"):
        return "Telegram communication runtime"
    if path.startswith("scripts/check_telegram") or "telegram" in path and path.startswith("scripts/"):
        return "Telegram regression checks"
    if path.startswith("orchestrator/paperops") or path.startswith("orchestrator/paper_"):
        return "PaperOps trading control plane"
    if path.startswith("orchestrator/"):
        return "Python orchestration logic"
    if path in {"dashboard.js", "dashboard/index.html", "auth.css"} or path in {
        "landing-page-repo/dashboard.js",
        "landing-page-repo/dashboard/index.html",
        "landing-page-repo/auth.css",
    }:
        return "dashboard overview experience"
    if path.startswith("scripts/") and "deploy" in path:
        return "dashboard deployment automation"
    if path.startswith("landing-page-repo/scripts/"):
        return "dashboard deployment automation"
    if path.startswith("scripts/"):
        return "operator scripts and readiness checks"
    if path.startswith("status/") or path.startswith("landing-page-repo/status/"):
        return "public cockpit status snapshot"
    if path.startswith("landing-page-repo/"):
        return "dashboard web app"
    if path.startswith("docs/"):
        return "operator documentation"
    if path.startswith("data/runtime/"):
        return "runtime evidence artifact"
    if path.startswith(".") or "env" in path:
        return "configuration surface"
    return "project source"


def _change_areas(paths: list[str]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for path in paths:
        area = _change_area_for_path(path)
        counts[area] = counts.get(area, 0) + 1
    return [
        {"area": area, "file_count": counts[area]}
        for area in sorted(counts)
    ]


def _area_lines(repo_state: dict[str, Any]) -> list[str]:
    repo = _clean_text(repo_state.get("repo"), "repo", limit=40)
    lines = []
    for item in repo_state.get("change_areas", []):
        if not isinstance(item, dict):
            continue
        area = _clean_text(item.get("area"), "source", limit=80)
        count = _int(item.get("file_count"))
        unit = "file" if count == 1 else "files"
        lines.append(f"{repo}: {area} ({count} {unit})")
    return lines


def _compact_area_parts(repo_state: dict[str, Any], label: str, *, count: int = 2) -> list[str]:
    parts: list[str] = []
    for item in repo_state.get("change_areas", []):
        if not isinstance(item, dict):
            continue
        area = _clean_text(item.get("area"), "source", limit=64)
        file_count = _int(item.get("file_count"))
        if not area or not file_count:
            continue
        unit = "file" if file_count == 1 else "files"
        parts.append(f"{label}: {area} ({file_count} {unit})")
        if len(parts) >= count:
            break
    return parts


def _derived_details(root_repo: dict[str, Any], dashboard_repo: dict[str, Any]) -> list[str]:
    details = _area_lines(root_repo) + _area_lines(dashboard_repo)
    if root_repo.get("last_commit_subject"):
        details.append(f"Core latest commit: {_clean_text(root_repo.get('last_commit_subject'), limit=120)}")
    if dashboard_repo.get("last_commit_subject"):
        details.append(
            f"Dashboard latest commit: {_clean_text(dashboard_repo.get('last_commit_subject'), limit=120)}"
        )
    return details[:5]


def _derived_benefits(root_repo: dict[str, Any], dashboard_repo: dict[str, Any]) -> list[str]:
    areas = {
        str(item.get("area") or "")
        for repo_state in (root_repo, dashboard_repo)
        for item in repo_state.get("change_areas", [])
        if isinstance(item, dict)
    }
    benefits: list[str] = []
    if "Telegram communication runtime" in areas:
        benefits.append("Telegram updates now carry event-specific context instead of repeating a fixed template.")
    if "Telegram regression checks" in areas:
        benefits.append("Low-information Telegram notices are caught by checks before they reach the team.")
    if "dashboard overview experience" in areas:
        benefits.append("The dashboard can show the communication state and why the latest update matters.")
    if "dashboard deployment automation" in areas:
        benefits.append("Production deploys can carry richer context automatically after aliases are updated.")
    if "PaperOps trading control plane" in areas:
        benefits.append("Paper-trading status messages can explain the actual lifecycle event and portfolio impact.")
    if "source provider decisions" in areas or "source registry" in areas:
        benefits.append("Optional source providers are now described without turning them into missing credentials.")
    if "source provider regression checks" in areas:
        benefits.append("Provider decisions are checked for read-only boundaries before dashboard deployment.")
    if "operator documentation" in areas:
        benefits.append("Operator docs now separate current key setup from optional provider work.")
    if not benefits:
        benefits.append("Fund Managers get a human-readable explanation of the update without checking local logs.")
    if len(benefits) < 2:
        benefits.append("The update keeps deployment notes specific enough for review without exposing secrets.")
    return benefits[:5]


def _plain_update_explanation(source: dict[str, Any]) -> tuple[str, str]:
    summary = _clean_text(source.get("summary"), "", limit=180)
    details = _clean_list(source.get("details"), [], limit=160, count=3)
    benefits = _clean_list(source.get("benefits"), [], limit=180, count=3)
    safe_details = [detail for detail in details if _telegram_body_safe_fragment(detail)]
    safe_benefits = [benefit for benefit in benefits if _telegram_body_safe_fragment(benefit)]
    areas = {
        str(item.get("area") or "")
        for repo_state in (source.get("root_repo", {}), source.get("dashboard_repo", {}))
        for item in repo_state.get("change_areas", [])
        if isinstance(item, dict)
    }

    if summary and summary not in {"Qadam codebase and dashboard were upgraded.", "Qadam has been updated."}:
        change = summary.rstrip(".") + "."
        if safe_details:
            detail = _sentence_fragment(safe_details[0], limit=160)
            change = f"{change} In plain terms, {detail}."
    elif "Telegram communication runtime" in areas or "Telegram regression checks" in areas:
        change = (
            "Qadam now rewrites its Telegram updates into plain language before they go out, "
            "so the group gets a short explanation instead of an engineering-style status note."
        )
    elif "dashboard overview experience" in areas or "public cockpit status snapshot" in areas:
        change = (
            "Qadam's live dashboard has been refreshed so the operating picture is easier to read "
            "and the latest system state is reflected in public-safe form."
        )
    elif "source provider decisions" in areas or "source registry" in areas:
        change = (
            "Qadam's data-source layer has been cleaned up, which makes it clearer which inputs are "
            "connected now and which ones still need credentials or provider approval."
        )
    elif "PaperOps trading control plane" in areas:
        change = (
            "Qadam's paper-trading control plane has been updated, so the system can explain its "
            "paper portfolio state and trading decisions more clearly."
        )
    else:
        change = _clean_text(
            source.get("summary"),
            "Qadam has been updated and the live operating dashboard has been refreshed.",
            limit=180,
        )
        change = change.replace("committed ", "").replace("runtime ", "operating ")

    benefit_reason = _sentence_fragment(safe_benefits[0], limit=180) if safe_benefits else (
        "the group can understand why the update matters without checking local logs"
    )
    benefit = (
        f"This helps because {benefit_reason}. Telegram still has no trading power and it does not "
        "switch on live capital; it is just the place where Qadam explains what changed in plain English."
    )
    return change, benefit


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


def _sent_commit_pairs(settings: Settings) -> set[tuple[str, str]]:
    _, history_path, _ = telegram_codebase_upgrade_paths(settings)
    if not history_path.exists():
        return set()
    pairs: set[tuple[str, str]] = set()
    with history_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            if payload.get("status") != "sent" and payload.get("live_send_succeeded") is not True:
                continue
            root = str(payload.get("root_commit_short") or "").strip()
            dashboard = str(payload.get("dashboard_commit_short") or "").strip()
            if root and dashboard:
                pairs.add((root, dashboard))
    return pairs


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
        "root_commit_short": payload.get("root_commit_short"),
        "dashboard_commit_short": payload.get("dashboard_commit_short"),
        "send_requested": payload.get("send_requested") is True,
        "live_send_attempted": payload.get("live_send_attempted") is True,
        "message_preview": payload.get("message_preview"),
        "message_fingerprint": payload.get("message_fingerprint"),
        "message_preview_redacted": payload.get("message_preview_redacted") is True,
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
    last_commit_subject = _clean_text(
        _git_output(repo, "log", "-1", "--pretty=%s"),
        "latest commit unavailable",
        limit=140,
    )
    status_lines = [
        line
        for line in _git_output(repo, "status", "--porcelain=v1").splitlines()
        if line.strip()
    ]
    status_paths = _status_paths(status_lines)
    last_commit_paths = _git_file_list(repo, "show", "--name-only", "--pretty=format:", "--no-renames", "HEAD")
    change_paths = list(dict.fromkeys([*last_commit_paths, *status_paths]))
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
        "last_commit_subject": last_commit_subject,
        "dirty": bool(status_lines),
        "status_digest": status_digest,
        "fingerprint": fingerprint,
        "changed_file_count": len(status_lines),
        "change_areas": _change_areas(change_paths),
        "change_area_count": len(_change_areas(change_paths)),
        "last_commit_file_count": len(last_commit_paths),
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
    change, benefit = _plain_update_explanation(source)
    action = "has just gone live" if source.get("source") == "production_deploy" else "has a new update"
    title = "Qadam"
    if change.startswith("Qadam's "):
        change = "Its " + change[8:]
    elif change.startswith("Qadam "):
        change = "It " + change[6:]
    body = f"Qadam {action}. {change}\n\n{benefit}"
    return title, body


def _safe_text(title: str, body: str) -> bool:
    text = f"{title}\n{body}"
    return all(not pattern.search(text) for pattern in FORBIDDEN_TELEGRAM_TEXT)


def _delivery_key(source: dict[str, Any], *, force_send: bool, generated_at: str) -> str:
    deployment = source.get("deployment", {})
    raw = {
        "aliases": sorted(deployment.get("aliases", []) or []),
        "dashboard": source.get("dashboard_repo", {}).get("head"),
        "root": source.get("root_repo", {}).get("head"),
        "source": source.get("source"),
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
    details: list[str] | None = None,
    benefits: list[str] | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    root = _repo_root()
    root_repo = _git_repo_state(root, "qadam-core")
    dashboard_repo = _git_repo_state(root / "landing-page-repo", "qadam-dashboard")
    derived_details = _derived_details(root_repo, dashboard_repo)
    derived_benefits = _derived_benefits(root_repo, dashboard_repo)
    change_area_lines = _area_lines(root_repo) + _area_lines(dashboard_repo)
    if not change_area_lines:
        change_area_lines = [
            "qadam-core: latest commit fingerprint recorded (1 commit)",
            "qadam-dashboard: latest dashboard fingerprint recorded (1 commit)",
        ]
    source_context = {
        "source": _clean_text(source, "manual", limit=80),
        "summary": _clean_text(summary, "Qadam codebase and dashboard were upgraded."),
        "details": _clean_list(
            details,
            derived_details
            or [
                "Qadam records the core and dashboard fingerprints behind each upgrade.",
                "The deployment hook posts to the Fund Manager group after production aliases update.",
                "The dashboard Communications panel mirrors whether the upgrade update was sent.",
            ],
        ),
        "benefits": _clean_list(
            benefits,
            derived_benefits
            or [
                "The group can understand the point of the update without checking Git, Vercel, or logs.",
                "Missed Telegram sends become visible in runtime status instead of disappearing silently.",
                "Each message says whether trading authority changed; for this rail it remains notification-only.",
            ],
        ),
        "change_area_lines": _clean_list(change_area_lines, change_area_lines, limit=140, count=6),
        "root_repo": root_repo,
        "dashboard_repo": dashboard_repo,
        "deployment": _deployment_context(settings, deployment_url=deployment_url, aliases=aliases),
    }
    title, body = _render_upgrade_message(source_context)
    text = body
    message_safe = _safe_text(title, body)
    message_specificity = telegram_message_specificity(title, body)
    message_style = telegram_human_message_style(title, body)
    token = secret_value("TELEGRAM_BOT_TOKEN", settings)
    chat_id = secret_value("TELEGRAM_GROUP_CHAT_ID", settings)
    bot_configured = secret_status("TELEGRAM_BOT_TOKEN", settings).configured
    group_chat_configured = secret_status("TELEGRAM_GROUP_CHAT_ID", settings).configured
    enabled = settings.telegram_codebase_upgrade_notifications_enabled
    dry_run = settings.telegram_codebase_upgrade_notifications_dry_run
    delivery_key = _delivery_key(source_context, force_send=force_send, generated_at=generated_at)
    commit_pair = (
        str(source_context["root_repo"].get("head_short") or "").strip(),
        str(source_context["dashboard_repo"].get("head_short") or "").strip(),
    )
    already_sent = delivery_key in _sent_delivery_keys(settings) or commit_pair in _sent_commit_pairs(settings)

    blockers: list[str] = []
    if not message_safe:
        blockers.append("unsafe_message_text")
    if message_specificity["status"] != "specific":
        blockers.append("telegram_message_not_specific")
    if message_style["status"] != "human":
        blockers.append("telegram_message_not_human")
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

    message_sendable = (
        message_safe
        and message_specificity["status"] == "specific"
        and message_style["status"] == "human"
    )
    status = "dry_run_ready" if message_sendable else "suppressed_not_safe"
    if message_sendable and not enabled:
        status = "blocked_pending_enablement"
    elif message_sendable and enabled and not dry_run:
        status = "ready_to_send"
    if already_sent and not force_send:
        status = "already_sent"

    live_send_attempted = False
    live_send_succeeded = False
    telegram_message_id: int | None = None
    failure_category: str | None = None
    if (
        send_requested
        and message_sendable
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
                "root_commit_short": source_context["root_repo"]["head_short"],
                "dashboard_commit_short": source_context["dashboard_repo"]["head_short"],
                "send_requested": send_requested,
                "live_send_attempted": live_send_attempted,
                "message_preview": {"title": title, "body": body, "dashboard_link": "qadam.trade/dashboard/"},
                "message_preview_redacted": message_safe,
                "message_fingerprint": message_specificity["fingerprint"],
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
        "delivery_identity": {
            "root_commit": source_context["root_repo"]["head"],
            "dashboard_commit": source_context["dashboard_repo"]["head"],
            "source": source_context["source"],
            "aliases": source_context["deployment"]["aliases"],
        },
        "source": source_context["source"],
        "summary": source_context["summary"],
        "details": source_context["details"],
        "benefits": source_context["benefits"],
        "change_area_lines": source_context["change_area_lines"],
        "root_commit": source_context["root_repo"]["head"],
        "root_commit_short": source_context["root_repo"]["head_short"],
        "root_branch": source_context["root_repo"]["branch"],
        "root_last_commit_subject": source_context["root_repo"]["last_commit_subject"],
        "root_change_areas": source_context["root_repo"]["change_areas"],
        "root_change_area_count": source_context["root_repo"]["change_area_count"],
        "root_last_commit_file_count": source_context["root_repo"]["last_commit_file_count"],
        "root_dirty": source_context["root_repo"]["dirty"],
        "root_changed_file_count": source_context["root_repo"]["changed_file_count"],
        "root_staged_file_count": source_context["root_repo"]["staged_file_count"],
        "root_unstaged_file_count": source_context["root_repo"]["unstaged_file_count"],
        "root_untracked_file_count": source_context["root_repo"]["untracked_file_count"],
        "dashboard_commit": source_context["dashboard_repo"]["head"],
        "dashboard_commit_short": source_context["dashboard_repo"]["head_short"],
        "dashboard_branch": source_context["dashboard_repo"]["branch"],
        "dashboard_last_commit_subject": source_context["dashboard_repo"]["last_commit_subject"],
        "dashboard_change_areas": source_context["dashboard_repo"]["change_areas"],
        "dashboard_change_area_count": source_context["dashboard_repo"]["change_area_count"],
        "dashboard_last_commit_file_count": source_context["dashboard_repo"]["last_commit_file_count"],
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
        "message_specificity": message_specificity,
        "message_specificity_status": message_specificity["status"],
        "message_specificity_score": message_specificity["score"],
        "message_fingerprint": message_specificity["fingerprint"],
        "message_human_style": message_style,
        "message_human_style_status": message_style["status"],
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
        "delivery_identity",
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
        "details",
        "benefits",
        "change_area_lines",
        "target",
        "message_specificity",
        "message_specificity_score",
        "message_specificity_status",
        "message_fingerprint",
        "message_human_style",
        "message_human_style_status",
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
        style = telegram_human_message_style(title, body)
        if style["status"] != "human":
            errors.append("telegram_codebase_upgrade_message_not_human:" + ",".join(style["errors"]))
        for phrase in (
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
        ):
            if phrase in body:
                errors.append("telegram_codebase_upgrade_message_too_verbose:" + phrase)
        if len([line for line in body.splitlines() if line.strip()]) > 3:
            errors.append("telegram_codebase_upgrade_message_too_long")
        if not _safe_text(title, body):
            errors.append("telegram_codebase_upgrade_forbidden_text")
    if artifact.get("message_human_style_status") != "human":
        errors.append("telegram_codebase_upgrade_human_style_status_not_human")
    specificity = artifact.get("message_specificity", {})
    if not isinstance(specificity, dict):
        errors.append("telegram_codebase_upgrade_specificity_missing")
    else:
        if specificity.get("status") != "specific":
            errors.append("telegram_codebase_upgrade_message_not_specific")
        if _int(specificity.get("score")) < _int(specificity.get("minimum_score", 70)):
            errors.append("telegram_codebase_upgrade_specificity_score_low")
    if artifact.get("message_specificity_status") != "specific":
        errors.append("telegram_codebase_upgrade_specificity_status_not_specific")
    if _int(artifact.get("message_specificity_score")) < 70:
        errors.append("telegram_codebase_upgrade_specificity_score_low")
    if not str(artifact.get("message_fingerprint") or "").strip():
        errors.append("telegram_codebase_upgrade_message_fingerprint_missing")
    if not isinstance(artifact.get("change_area_lines"), list) or not artifact.get("change_area_lines"):
        errors.append("telegram_codebase_upgrade_change_areas_missing")
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
            "details": artifact.get("details"),
            "benefits": artifact.get("benefits"),
            "change_area_lines": artifact.get("change_area_lines"),
            "root_change_areas": artifact.get("root_change_areas"),
            "dashboard_change_areas": artifact.get("dashboard_change_areas"),
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
            "details": [],
            "benefits": [],
            "change_area_lines": [],
            "root_commit_short": None,
            "root_last_commit_subject": None,
            "root_change_areas": [],
            "root_dirty": False,
            "root_changed_file_count": 0,
            "dashboard_commit_short": None,
            "dashboard_last_commit_subject": None,
            "dashboard_change_areas": [],
            "dashboard_dirty": False,
            "dashboard_changed_file_count": 0,
            "message_specificity_status": "not_run",
            "message_specificity_score": 0,
            "message_fingerprint": None,
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
    preview = artifact.get("message_preview", {}) if isinstance(artifact.get("message_preview"), dict) else {}
    specificity = artifact.get("message_specificity", {})
    if not isinstance(specificity, dict) or not specificity:
        specificity = telegram_message_specificity(
            str(preview.get("title") or ""),
            str(preview.get("body") or ""),
        )
    root_change_areas = artifact.get("root_change_areas", [])
    dashboard_change_areas = artifact.get("dashboard_change_areas", [])
    change_area_lines = [str(item) for item in artifact.get("change_area_lines", []) if str(item).strip()]
    if not change_area_lines:
        root = _repo_root()
        root_repo = _git_repo_state(root, "qadam-core")
        dashboard_repo = _git_repo_state(root / "landing-page-repo", "qadam-dashboard")
        root_change_areas = root_change_areas or root_repo.get("change_areas", [])
        dashboard_change_areas = dashboard_change_areas or dashboard_repo.get("change_areas", [])
        change_area_lines = _area_lines(root_repo) + _area_lines(dashboard_repo)
    benefits = [str(item) for item in artifact.get("benefits", []) if str(item).strip()]
    if len(benefits) < 2:
        fallback_benefits = _derived_benefits(
            {"change_areas": root_change_areas},
            {"change_areas": dashboard_change_areas},
        )
        for benefit in fallback_benefits:
            if benefit not in benefits:
                benefits.append(benefit)
            if len(benefits) >= 2:
                break
    return {
        "schema_version": TELEGRAM_CODEBASE_UPGRADE_SCHEMA_VERSION,
        "status": artifact.get("status", "unknown"),
        "enabled": artifact.get("codebase_upgrade_notifications_enabled") is True,
        "dry_run": artifact.get("codebase_upgrade_notifications_dry_run") is True,
        "target": "group",
        "source": artifact.get("source"),
        "summary": artifact.get("summary"),
        "details": [str(item) for item in artifact.get("details", [])],
        "benefits": benefits,
        "change_area_lines": change_area_lines,
        "root_commit_short": artifact.get("root_commit_short"),
        "root_last_commit_subject": artifact.get("root_last_commit_subject"),
        "root_change_areas": root_change_areas,
        "root_dirty": artifact.get("root_dirty") is True,
        "root_changed_file_count": _int(artifact.get("root_changed_file_count")),
        "dashboard_commit_short": artifact.get("dashboard_commit_short"),
        "dashboard_last_commit_subject": artifact.get("dashboard_last_commit_subject"),
        "dashboard_change_areas": dashboard_change_areas,
        "dashboard_dirty": artifact.get("dashboard_dirty") is True,
        "dashboard_changed_file_count": _int(artifact.get("dashboard_changed_file_count")),
        "message_specificity_status": artifact.get("message_specificity_status") or specificity.get("status"),
        "message_specificity_score": _int(artifact.get("message_specificity_score") or specificity.get("score")),
        "message_fingerprint": artifact.get("message_fingerprint") or specificity.get("fingerprint"),
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
