"""ACLED OAuth token refresh support.

This module is local-only credential infrastructure. It refreshes ACLED OAuth
tokens and updates the ignored runtime secret file, but it never returns token
values in reports, Event Log entries, or stdout.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.secrets import load_secret_file, secret_status

ACLED_TOKEN_URL = "https://acleddata.com/oauth/token"
ACLED_READ_URL = "https://acleddata.com/api/acled/read"
ACLED_CLIENT_ID = "acled"

SECRET_LIKE_PATTERNS = (
    re.compile(r"\d{6,}:[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bvcp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"\bsb_secret_[0-9A-Za-z_-]{12,}\b"),
    re.compile(r"\b[A-Za-z0-9_-]{40,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b"),
)


@dataclass(frozen=True)
class AcledRefreshAttempt:
    grant_type: str
    attempted: bool
    ok: bool
    status_code: int | None
    error_type: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AcledRefreshReport:
    schema_version: int
    checked_at: str
    token_endpoint: str
    read_endpoint: str
    credential_state: str
    refresh_status: str
    grant_type_used: str | None
    access_token_received: bool
    refresh_token_received: bool
    expires_in_seconds: int | None
    expires_at: str | None
    secret_file_updated: bool
    secret_file_path: str
    read_validation_status: str
    read_validation_status_code: int | None
    read_validation_error_type: str | None
    attempts: tuple[AcledRefreshAttempt, ...]
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["attempts"] = [attempt.to_dict() for attempt in self.attempts]
        return payload


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat()


def _contains_secret_like_value(payload: Any) -> bool:
    encoded = json.dumps(payload, sort_keys=True, default=str)
    return any(pattern.search(encoded) for pattern in SECRET_LIKE_PATTERNS)


def acled_token_input_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    refresh_configured = secret_status("ACLED_REFRESH_TOKEN", settings).configured
    email_configured = secret_status("ACLED_EMAIL", settings).configured
    password_configured = secret_status("ACLED_PASSWORD", settings).configured
    access_configured = secret_status("ACLED_ACCESS_TOKEN", settings).configured
    return {
        "access_token_configured": access_configured,
        "refresh_token_configured": refresh_configured,
        "password_grant_configured": email_configured and password_configured,
        "credential_state": (
            "refresh_ready"
            if refresh_configured
            else "password_grant_ready"
            if email_configured and password_configured
            else "missing"
        ),
        "secret_file_path": settings.secrets_file,
        "boundary": "Credential status only. Token values are never exposed.",
    }


def _token_from_payload(payload: dict[str, Any], key: str) -> str | None:
    variants = (key, f"ACLED_{key}")
    for variant in variants:
        value = payload.get(variant)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _expires_in(payload: dict[str, Any]) -> int | None:
    value = payload.get("expires_in")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _post_token_request(
    *,
    form_data: dict[str, str],
    timeout_seconds: float,
) -> tuple[AcledRefreshAttempt, dict[str, Any]]:
    try:
        import httpx
    except ImportError:
        return (
            AcledRefreshAttempt(
                grant_type=form_data["grant_type"],
                attempted=True,
                ok=False,
                status_code=None,
                error_type="missing_dependency:httpx",
            ),
            {},
        )

    try:
        with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
            response = client.post(
                ACLED_TOKEN_URL,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "Qadam/0.1 acled-token-refresh",
                },
                data=form_data,
            )
            status_code = response.status_code
            if status_code >= 400:
                return (
                    AcledRefreshAttempt(
                        grant_type=form_data["grant_type"],
                        attempted=True,
                        ok=False,
                        status_code=status_code,
                        error_type="http_status",
                    ),
                    {},
                )
            payload = response.json()
            if not isinstance(payload, dict):
                return (
                    AcledRefreshAttempt(
                        grant_type=form_data["grant_type"],
                        attempted=True,
                        ok=False,
                        status_code=status_code,
                        error_type="invalid_json_shape",
                    ),
                    {},
                )
            return (
                AcledRefreshAttempt(
                    grant_type=form_data["grant_type"],
                    attempted=True,
                    ok=True,
                    status_code=status_code,
                    error_type=None,
                ),
                payload,
            )
    except (httpx.HTTPError, ValueError) as exc:
        return (
            AcledRefreshAttempt(
                grant_type=form_data["grant_type"],
                attempted=True,
                ok=False,
                status_code=None,
                error_type=exc.__class__.__name__,
            ),
            {},
        )


def _validate_acled_read(access_token: str, *, timeout_seconds: float) -> tuple[str, int | None, str | None]:
    try:
        import httpx
    except ImportError:
        return "skipped_missing_dependency", None, "missing_dependency:httpx"

    try:
        with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
            response = client.get(
                ACLED_READ_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "User-Agent": "Qadam/0.1 acled-token-refresh",
                },
                params={"limit": 1, "_format": "json"},
            )
            if response.status_code >= 400:
                return "degraded", response.status_code, "http_status"
            return "live", response.status_code, None
    except httpx.HTTPError as exc:
        return "degraded", None, exc.__class__.__name__


def _updated_env_text(existing_text: str, updates: dict[str, str]) -> str:
    assignment = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
    seen: set[str] = set()
    output_lines: list[str] = []
    for line in existing_text.splitlines():
        match = assignment.match(line)
        if match and match.group(1) in updates:
            key = match.group(1)
            output_lines.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            output_lines.append(line)
    missing = [key for key in updates if key not in seen]
    if missing:
        if output_lines and output_lines[-1].strip():
            output_lines.append("")
        output_lines.append("# ACLED OAuth refresh state")
        for key in missing:
            output_lines.append(f"{key}={updates[key]}")
    return "\n".join(output_lines).rstrip() + "\n"


def _write_secret_updates(path: Path, updates: dict[str, str]) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    updated = _updated_env_text(existing, updates)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(updated, encoding="utf-8")
    os.chmod(tmp_path, 0o600)
    os.replace(tmp_path, path)


def refresh_acled_token(
    *,
    settings: Settings | None = None,
    write_secret_file: bool,
    allow_password_fallback: bool = True,
    validate_read: bool = False,
    timeout_seconds: float = 12.0,
) -> AcledRefreshReport:
    settings = settings or Settings.from_env()
    checked_at = _now()
    secret_path = Path(settings.secrets_file)
    values = load_secret_file(secret_path)
    input_status = acled_token_input_status(settings)
    attempts: list[AcledRefreshAttempt] = []
    payload: dict[str, Any] = {}
    grant_type_used: str | None = None

    if not write_secret_file:
        return AcledRefreshReport(
            schema_version=1,
            checked_at=_iso(checked_at),
            token_endpoint=ACLED_TOKEN_URL,
            read_endpoint=ACLED_READ_URL,
            credential_state=str(input_status["credential_state"]),
            refresh_status="check_only",
            grant_type_used=None,
            access_token_received=False,
            refresh_token_received=False,
            expires_in_seconds=None,
            expires_at=None,
            secret_file_updated=False,
            secret_file_path=str(secret_path),
            read_validation_status="not_requested",
            read_validation_status_code=None,
            read_validation_error_type=None,
            attempts=tuple(attempts),
            boundary="Check-only mode performs no provider call and cannot rotate tokens.",
        )

    if not secret_path.exists():
        return AcledRefreshReport(
            schema_version=1,
            checked_at=_iso(checked_at),
            token_endpoint=ACLED_TOKEN_URL,
            read_endpoint=ACLED_READ_URL,
            credential_state="missing",
            refresh_status="missing_secret_file",
            grant_type_used=None,
            access_token_received=False,
            refresh_token_received=False,
            expires_in_seconds=None,
            expires_at=None,
            secret_file_updated=False,
            secret_file_path=str(secret_path),
            read_validation_status="not_requested",
            read_validation_status_code=None,
            read_validation_error_type=None,
            attempts=tuple(attempts),
            boundary="ACLED refresh could not run because the local secret file is missing.",
        )

    if not os.access(secret_path, os.W_OK):
        return AcledRefreshReport(
            schema_version=1,
            checked_at=_iso(checked_at),
            token_endpoint=ACLED_TOKEN_URL,
            read_endpoint=ACLED_READ_URL,
            credential_state=str(input_status["credential_state"]),
            refresh_status="secret_file_not_writable",
            grant_type_used=None,
            access_token_received=False,
            refresh_token_received=False,
            expires_in_seconds=None,
            expires_at=None,
            secret_file_updated=False,
            secret_file_path=str(secret_path),
            read_validation_status="not_requested",
            read_validation_status_code=None,
            read_validation_error_type=None,
            attempts=tuple(attempts),
            boundary="ACLED refresh did not call the provider because the local secret file is not writable.",
        )

    refresh_token = values.get("ACLED_REFRESH_TOKEN", "").strip()
    if refresh_token:
        attempt, payload = _post_token_request(
            form_data={
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
                "client_id": ACLED_CLIENT_ID,
            },
            timeout_seconds=timeout_seconds,
        )
        attempts.append(attempt)
        if attempt.ok:
            grant_type_used = "refresh_token"

    if not grant_type_used and allow_password_fallback:
        email = values.get("ACLED_EMAIL", "").strip()
        password = values.get("ACLED_PASSWORD", "").strip()
        if email and password:
            attempt, payload = _post_token_request(
                form_data={
                    "username": email,
                    "password": password,
                    "grant_type": "password",
                    "client_id": ACLED_CLIENT_ID,
                },
                timeout_seconds=timeout_seconds,
            )
            attempts.append(attempt)
            if attempt.ok:
                grant_type_used = "password"

    access_token = _token_from_payload(payload, "access_token") if payload else None
    new_refresh_token = _token_from_payload(payload, "refresh_token") if payload else None
    expires_in = _expires_in(payload) if payload else None
    expires_at = _iso(checked_at + timedelta(seconds=expires_in)) if expires_in else None

    if not access_token or not new_refresh_token:
        refresh_status = "failed"
        if not attempts:
            refresh_status = "missing_refresh_and_password_credentials"
        report = AcledRefreshReport(
            schema_version=1,
            checked_at=_iso(checked_at),
            token_endpoint=ACLED_TOKEN_URL,
            read_endpoint=ACLED_READ_URL,
            credential_state=str(input_status["credential_state"]),
            refresh_status=refresh_status,
            grant_type_used=grant_type_used,
            access_token_received=bool(access_token),
            refresh_token_received=bool(new_refresh_token),
            expires_in_seconds=expires_in,
            expires_at=expires_at,
            secret_file_updated=False,
            secret_file_path=str(secret_path),
            read_validation_status="not_requested",
            read_validation_status_code=None,
            read_validation_error_type=None,
            attempts=tuple(attempts),
            boundary="ACLED refresh failed closed. Existing local credentials were not changed.",
        )
        _log_report(report)
        return report

    token_type = str(payload.get("token_type") or "Bearer")
    updates = {
        "ACLED_ACCESS_TOKEN": access_token,
        "ACLED_REFRESH_TOKEN": new_refresh_token,
        "ACLED_TOKEN_TYPE": token_type,
        "ACLED_TOKEN_EXPIRES_IN": str(expires_in or ""),
        "ACLED_TOKEN_EXPIRES_AT": expires_at or "",
        "ACLED_TOKEN_REFRESHED_AT": _iso(checked_at),
    }
    _write_secret_updates(secret_path, updates)

    read_status = "not_requested"
    read_status_code: int | None = None
    read_error: str | None = None
    if validate_read:
        read_status, read_status_code, read_error = _validate_acled_read(access_token, timeout_seconds=timeout_seconds)

    report = AcledRefreshReport(
        schema_version=1,
        checked_at=_iso(checked_at),
        token_endpoint=ACLED_TOKEN_URL,
        read_endpoint=ACLED_READ_URL,
        credential_state=str(input_status["credential_state"]),
        refresh_status="refreshed",
        grant_type_used=grant_type_used,
        access_token_received=True,
        refresh_token_received=True,
        expires_in_seconds=expires_in,
        expires_at=expires_at,
        secret_file_updated=True,
        secret_file_path=str(secret_path),
        read_validation_status=read_status,
        read_validation_status_code=read_status_code,
        read_validation_error_type=read_error,
        attempts=tuple(attempts),
        boundary="ACLED token refresh updates local ignored credentials only. It cannot create signals, risk approvals, messages, or orders.",
    )
    _log_report(report)
    return report


def _log_report(report: AcledRefreshReport) -> None:
    payload = report.to_dict()
    if _contains_secret_like_value(payload):
        raise ValueError("ACLED refresh report contains a secret-like value")
    EventLog(echo=False).write(
        "acled_token_refresh_completed",
        "acled_auth",
        {
            "refresh_status": report.refresh_status,
            "grant_type_used": report.grant_type_used,
            "secret_file_updated": report.secret_file_updated,
            "read_validation_status": report.read_validation_status,
            "read_validation_status_code": report.read_validation_status_code,
            "execution_allowed": False,
        },
        severity="info" if report.refresh_status == "refreshed" else "warning",
    )


def write_acled_refresh_report(settings: Settings, report: AcledRefreshReport) -> Path:
    payload = report.to_dict()
    if _contains_secret_like_value(payload):
        raise ValueError("ACLED refresh report contains a secret-like value")
    output_path = Path(settings.runtime_dir) / "acled_token_refresh.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    history_path = Path(settings.runtime_dir) / "acled_token_refresh.jsonl"
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    return output_path
