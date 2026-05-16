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


def secret_value(key: str, settings: Settings | None = None) -> str | None:
    settings = settings or Settings.from_env()
    env_value = os.getenv(key)
    if env_value:
        return env_value
    return load_secret_file(settings.secrets_file).get(key)


def secret_status(key: str, settings: Settings | None = None) -> SecretStatus:
    settings = settings or Settings.from_env()
    if os.getenv(key):
        return SecretStatus(key=key, configured=True, source="environment")

    values = load_secret_file(settings.secrets_file)
    return SecretStatus(
        key=key,
        configured=bool(values.get(key)),
        source="local_secret_file" if values.get(key) else "missing",
    )


def secret_statuses(keys: tuple[str, ...], settings: Settings | None = None) -> list[dict[str, object]]:
    settings = settings or Settings.from_env()
    return [secret_status(key, settings).to_dict() for key in keys]
