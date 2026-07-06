"""Qadam git and live-deploy readiness.

This module is read-only. It measures whether local commits, dashboard commits,
and deploy receipts are closed out cleanly. It never writes credentials, edits
remotes, pushes branches, or changes deployment state.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings

SCHEMA_VERSION = "qadam_git_deploy_readiness.v1"
PRIMARY_ARTIFACT = "qadam_git_deploy_readiness.json"
LIVE_DEPLOY_CLOSURE_ARTIFACT = "qadam_live_deploy_closure.json"
HISTORY_ARTIFACT = "qadam_git_deploy_readiness_history.jsonl"
EVENTS_ARTIFACT = "qadam_git_deploy_readiness_events.jsonl"

ROOT_BRANCH = "qadam-foundation"
DASHBOARD_BRANCH = "main"
DEPLOY_RECEIPT_ARTIFACT = "dashboard-deployment-receipt.json"
CODEBASE_NOTIFICATION_ARTIFACT = "telegram_codebase_upgrade_notification.json"

AUTHORITY_FLAGS = {
    "read_only": True,
    "credential_write_allowed": False,
    "remote_write_allowed": False,
    "git_push_attempted": False,
    "deploy_attempted": False,
    "broker_write_allowed": False,
    "paper_order_allowed": False,
    "live_capital_enabled": False,
    "telegram_command_path_enabled": False,
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _runtime_dir(settings: Settings | None = None) -> Path:
    active_settings = settings or Settings.from_env()
    path = Path(active_settings.runtime_dir)
    if not path.is_absolute():
        path = _repo_root() / path
    return path


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _json_dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _jsonl_line(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True) + "\n"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_dump(payload), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(_jsonl_line(payload))


def _run_git(repo: Path, args: list[str], timeout: int = 10) -> dict[str, Any]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo,
            env=env,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "ok": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(exc),
            "args": ["git", *args],
        }
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "args": ["git", *args],
    }


def _redact_remote(value: str) -> str:
    if "@" not in value or "://" not in value:
        return value
    scheme, rest = value.split("://", 1)
    return f"{scheme}://<redacted>@{rest.split('@', 1)[1]}"


def _int(value: Any) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def _repo_state(repo: Path, name: str, target_branch: str) -> dict[str, Any]:
    branch = _run_git(repo, ["branch", "--show-current"])
    head = _run_git(repo, ["rev-parse", "--short=12", "HEAD"])
    full_head = _run_git(repo, ["rev-parse", "HEAD"])
    upstream = _run_git(repo, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    status = _run_git(repo, ["status", "--porcelain"])
    remote_url = _run_git(repo, ["remote", "get-url", "origin"])
    credential_helper = _run_git(repo, ["config", "--get", "credential.helper"])
    tracked_runtime = _run_git(repo, ["ls-files", "data/runtime"])

    upstream_name = upstream["stdout"] if upstream["ok"] else f"origin/{target_branch}"
    ahead_behind = _run_git(repo, ["rev-list", "--left-right", "--count", f"{upstream_name}...HEAD"])
    behind_count = 0
    ahead_count = 0
    if ahead_behind["ok"]:
        parts = ahead_behind["stdout"].split()
        if len(parts) >= 2:
            behind_count = _int(parts[0])
            ahead_count = _int(parts[1])

    remote_probe = _run_git(repo, ["ls-remote", "--exit-code", "origin", f"refs/heads/{target_branch}"], timeout=12)
    dirty_lines = [line for line in status["stdout"].splitlines() if line.strip()] if status["ok"] else []
    protected_dirty = [
        line
        for line in dirty_lines
        if ".env" in line or "secret" in line.lower() or "credential" in line.lower()
    ]

    blockers: list[str] = []
    if ahead_count > 0:
        blockers.append("local_commits_not_pushed")
    if behind_count > 0:
        blockers.append("remote_commits_not_integrated")
    if protected_dirty:
        blockers.append("protected_or_secret_like_dirty_paths_present")
    if not remote_probe["ok"]:
        if "could not read Username" in remote_probe["stderr"]:
            blockers.append("git_https_credentials_missing")
        elif "Authentication failed" in remote_probe["stderr"]:
            blockers.append("git_authentication_failed")
        else:
            blockers.append("remote_read_probe_failed")

    return {
        "repo_name": name,
        "repo_path_label": "." if repo == _repo_root() else repo.name,
        "branch": branch["stdout"] if branch["ok"] else "unknown",
        "target_remote_branch": target_branch,
        "head_short": head["stdout"] if head["ok"] else "unknown",
        "head": full_head["stdout"] if full_head["ok"] else "unknown",
        "upstream": upstream_name,
        "ahead_count": ahead_count,
        "behind_count": behind_count,
        "dirty_path_count": len(dirty_lines),
        "dirty_paths_sample": dirty_lines[:25],
        "protected_dirty_path_count": len(protected_dirty),
        "protected_dirty_paths": protected_dirty,
        "remote_url": _redact_remote(remote_url["stdout"]) if remote_url["ok"] else "unknown",
        "credential_helper_configured": credential_helper["ok"] and bool(credential_helper["stdout"]),
        "credential_helper": credential_helper["stdout"] if credential_helper["ok"] else "",
        "remote_read_probe": {
            "ok": remote_probe["ok"],
            "returncode": remote_probe["returncode"],
            "stderr": remote_probe["stderr"][:300],
        },
        "tracked_runtime_artifact_count": len(tracked_runtime["stdout"].splitlines()) if tracked_runtime["ok"] else 0,
        "blockers": blockers,
        "ready_for_push": ahead_count == 0 and behind_count == 0 and not protected_dirty and remote_probe["ok"],
    }


def _deploy_receipt_state(runtime_dir: Path, root_state: dict[str, Any], dashboard_state: dict[str, Any]) -> dict[str, Any]:
    receipt = _read_json(runtime_dir / DEPLOY_RECEIPT_ARTIFACT)
    notification = _read_json(runtime_dir / CODEBASE_NOTIFICATION_ARTIFACT)
    receipt_root = str(receipt.get("core_commit") or receipt.get("root_commit") or "")
    receipt_dashboard = str(receipt.get("dashboard_commit") or "")
    aliases = receipt.get("aliases") if isinstance(receipt.get("aliases"), list) else []

    blockers: list[str] = []
    if not receipt:
        blockers.append("deploy_receipt_missing")
    if receipt_root and not root_state.get("head", "").startswith(receipt_root):
        blockers.append("deploy_receipt_root_commit_not_current_head")
    if receipt_dashboard and not dashboard_state.get("head", "").startswith(receipt_dashboard):
        blockers.append("deploy_receipt_dashboard_commit_not_current_head")
    if aliases and not {"qadam.trade", "www.qadam.trade"}.issubset(set(str(alias) for alias in aliases)):
        blockers.append("production_aliases_incomplete")

    return {
        "deploy_receipt_present": bool(receipt),
        "receipt_generated_at": receipt.get("generated_at"),
        "deploy_url": receipt.get("deployment_url") or receipt.get("deploy_url"),
        "aliases": aliases,
        "receipt_root_commit": receipt_root,
        "receipt_dashboard_commit": receipt_dashboard,
        "notification_status": notification.get("telegram_codebase_upgrade_status") or notification.get("status"),
        "notification_live_send_succeeded": bool(notification.get("live_send_succeeded")),
        "blockers": blockers,
        "deploy_receipt_matches_current_heads": not blockers,
    }


def build_git_deploy_readiness(settings: Settings | None = None) -> dict[str, Any]:
    runtime_dir = _runtime_dir(settings)
    root = _repo_root()
    dashboard = root / "landing-page-repo"
    now = _now()

    root_state = _repo_state(root, "qadam-core", ROOT_BRANCH)
    dashboard_state = _repo_state(dashboard, "qadam-dashboard", DASHBOARD_BRANCH)
    deploy_state = _deploy_receipt_state(runtime_dir, root_state, dashboard_state)

    blockers = []
    for state in (root_state, dashboard_state):
        blockers.extend(f"{state['repo_name']}:{blocker}" for blocker in state.get("blockers", []))
    blockers.extend(f"deploy:{blocker}" for blocker in deploy_state.get("blockers", []))

    status = "qadam_git_deploy_ready" if not blockers else "qadam_git_deploy_blocked"
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_git_deploy_readiness",
        "generated_at": _iso(now),
        "status": status,
        "read_only": True,
        "public_safe": True,
        "command_disabled": True,
        "authority_flags": AUTHORITY_FLAGS,
        "root_repo": root_state,
        "dashboard_repo": dashboard_state,
        "deploy_closure": deploy_state,
        "blocker_count": len(blockers),
        "blockers": sorted(set(blockers)),
        "deployment_closure_passed": not blockers,
        "next_action": "configure_secure_git_credentials_and_push" if blockers else "ready",
    }


def validate_git_deploy_readiness(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if payload.get("artifact_type") != "qadam_git_deploy_readiness":
        errors.append("artifact_type_mismatch")
    if payload.get("read_only") is not True:
        errors.append("read_only_must_be_true")
    authority = payload.get("authority_flags") if isinstance(payload.get("authority_flags"), dict) else {}
    for key in (
        "credential_write_allowed",
        "remote_write_allowed",
        "git_push_attempted",
        "deploy_attempted",
        "broker_write_allowed",
        "paper_order_allowed",
        "live_capital_enabled",
    ):
        if authority.get(key) is not False:
            errors.append(f"{key}_must_be_false")
    for key in ("root_repo", "dashboard_repo", "deploy_closure"):
        if not isinstance(payload.get(key), dict):
            errors.append(f"{key}_missing")
    return errors


def write_git_deploy_readiness(payload: dict[str, Any], settings: Settings | None = None) -> dict[str, str]:
    runtime_dir = _runtime_dir(settings)
    primary = runtime_dir / PRIMARY_ARTIFACT
    closure = runtime_dir / LIVE_DEPLOY_CLOSURE_ARTIFACT
    history = runtime_dir / HISTORY_ARTIFACT
    events = runtime_dir / EVENTS_ARTIFACT

    closure_payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_live_deploy_closure",
        "generated_at": payload.get("generated_at"),
        "status": "live_deploy_closure_passed" if payload.get("deployment_closure_passed") else "live_deploy_closure_blocked",
        "deployment_closure_passed": payload.get("deployment_closure_passed"),
        "root_head": payload.get("root_repo", {}).get("head"),
        "dashboard_head": payload.get("dashboard_repo", {}).get("head"),
        "deploy_url": payload.get("deploy_closure", {}).get("deploy_url"),
        "aliases": payload.get("deploy_closure", {}).get("aliases", []),
        "blockers": payload.get("blockers", []),
        "read_only": True,
        "public_safe": True,
        "command_disabled": True,
        "authority_flags": AUTHORITY_FLAGS,
    }

    _write_json(primary, payload)
    _write_json(closure, closure_payload)
    _append_jsonl(history, payload)
    _append_jsonl(events, {
        "schema_version": SCHEMA_VERSION,
        "generated_at": payload.get("generated_at"),
        "event": payload.get("status"),
        "blockers": payload.get("blockers", []),
    })
    return {
        "primary": str(primary),
        "closure": str(closure),
        "history": str(history),
        "events": str(events),
    }


def build_and_write_git_deploy_readiness(settings: Settings | None = None) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    payload = build_git_deploy_readiness(settings)
    errors = validate_git_deploy_readiness(payload)
    written = write_git_deploy_readiness(payload, settings)
    return payload, written, errors
