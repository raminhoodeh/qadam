"""Strict local secret loading.

Secrets are reported as configured/missing only. Values must never appear in
health output, docs, Event Log payloads, or cockpit responses.
"""

from __future__ import annotations

import os
import stat
from dataclasses import asdict, dataclass
from pathlib import Path

from orchestrator.config import Settings


@dataclass(frozen=True)
class SecretStatus:
    key: str
    configured: bool
    source: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _is_strict_mode(path: Path) -> bool:
    mode = stat.S_IMODE(path.stat().st_mode)
    return mode & (stat.S_IRWXG | stat.S_IRWXO) == 0


def validate_secret_file(path: str | Path) -> dict[str, object]:
    secret_path = Path(path)
    if not secret_path.exists():
        return {"path": str(secret_path), "exists": False, "strict_permissions": False}
    return {
        "path": str(secret_path),
        "exists": True,
        "strict_permissions": _is_strict_mode(secret_path),
    }


def load_secret_file(path: str | Path) -> dict[str, str]:
    secret_path = Path(path)
    if not secret_path.exists():
        return {}
    if not _is_strict_mode(secret_path):
        raise PermissionError(f"secret file permissions are too broad: {secret_path}")

    values: dict[str, str] = {}
    with secret_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, _, value = stripped.partition("=")
            values[key.strip()] = value.strip()
    return values


def _repo_root_from_settings(settings: Settings) -> Path:
    secret_path = Path(settings.secrets_file)
    if not secret_path.is_absolute():
        secret_path = Path.cwd() / secret_path
    try:
        return secret_path.resolve().parents[2]
    except IndexError:
        return Path.cwd()


def _load_local_env_file(settings: Settings) -> dict[str, str]:
    local_env_path = _repo_root_from_settings(settings) / ".env.local"
    if not local_env_path.exists():
        return {}
    if not _is_strict_mode(local_env_path):
        return {}
    return load_secret_file(local_env_path)


def secret_value(key: str, settings: Settings | None = None) -> str | None:
    settings = settings or Settings.from_env()
    env_value = os.getenv(key)
    if env_value:
        return env_value
    secret_file_value = load_secret_file(settings.secrets_file).get(key)
    if secret_file_value:
        return secret_file_value
    return _load_local_env_file(settings).get(key)


def secret_status(key: str, settings: Settings | None = None) -> SecretStatus:
    settings = settings or Settings.from_env()
    if os.getenv(key):
        return SecretStatus(key=key, configured=True, source="environment")

    values = load_secret_file(settings.secrets_file)
    if values.get(key):
        return SecretStatus(key=key, configured=True, source="local_secret_file")

    local_env_values = _load_local_env_file(settings)
    return SecretStatus(
        key=key,
        configured=bool(local_env_values.get(key)),
        source="local_env_file" if local_env_values.get(key) else "missing",
    )


def secret_statuses(keys: tuple[str, ...], settings: Settings | None = None) -> list[dict[str, object]]:
    settings = settings or Settings.from_env()
    return [secret_status(key, settings).to_dict() for key in keys]
