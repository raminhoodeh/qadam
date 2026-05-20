"""Runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_FUND_MANAGER_EMAILS = (
    "raminhoodeh@gmail.com",
    "troycookecareer@gmail.com",
    "akber.ali@hotmail.co.uk",
    "isioras@yahoo.co.uk",
)
DEFAULT_PENDING_FUND_MANAGERS = ("Anas",)


def _csv_tuple(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    env: str
    mode: str
    trial_balance_gbp: int
    health_host: str
    health_port: int
    database_url: str
    chroma_host: str
    chroma_port: int
    data_root: str
    raw_payload_dir: str
    runtime_dir: str
    postgres_data_dir: str
    chroma_persist_dir: str
    local_backup_dir: str
    secrets_file: str
    fund_manager_allowlist: tuple[str, ...]
    pending_fund_managers: tuple[str, ...]
    telegram_enabled: bool
    telegram_dry_run: bool
    telegram_bot_configured: bool
    telegram_bot_username_configured: bool
    telegram_default_chat_configured: bool
    live_bridge_enabled: bool
    live_bridge_endpoint: str
    live_bridge_max_age_seconds: int
    live_bridge_stale_after_seconds: int
    live_bridge_rate_limit_per_minute: int

    @classmethod
    def from_env(cls) -> "Settings":
        allowlist = _csv_tuple(
            os.getenv("QADAM_FOUNDING_MANAGER_ALLOWLIST", ",".join(DEFAULT_FUND_MANAGER_EMAILS))
        )
        pending = _csv_tuple(
            os.getenv("QADAM_PENDING_FOUNDING_MANAGERS", ",".join(DEFAULT_PENDING_FUND_MANAGERS))
        )
        return cls(
            env=os.getenv("QADAM_ENV", "local"),
            mode=os.getenv("QADAM_MODE", "paper"),
            trial_balance_gbp=int(os.getenv("QADAM_TRIAL_BALANCE_GBP", "1000")),
            health_host=os.getenv("QADAM_HEALTH_HOST", "127.0.0.1"),
            health_port=int(os.getenv("QADAM_HEALTH_PORT", "8717")),
            database_url=os.getenv("DATABASE_URL", "postgresql://qadam:qadam@localhost:5432/qadam"),
            chroma_host=os.getenv("CHROMA_HOST", "127.0.0.1"),
            chroma_port=int(os.getenv("CHROMA_PORT", "8000")),
            data_root=os.getenv("QADAM_DATA_ROOT", "./data"),
            raw_payload_dir=os.getenv("QADAM_RAW_PAYLOAD_DIR", "./data/raw_payloads"),
            runtime_dir=os.getenv("QADAM_RUNTIME_DIR", "./data/runtime"),
            postgres_data_dir=os.getenv("QADAM_POSTGRES_DATA_DIR", "./data/postgres"),
            chroma_persist_dir=os.getenv("QADAM_CHROMA_PERSIST_DIR", "./data/chroma"),
            local_backup_dir=os.getenv("QADAM_LOCAL_BACKUP_DIR", "./data/backups"),
            secrets_file=os.getenv("QADAM_SECRETS_FILE", "./data/runtime/qadam-secrets.env"),
            fund_manager_allowlist=allowlist,
            pending_fund_managers=pending,
            telegram_enabled=_bool_env("QADAM_TELEGRAM_ENABLED", False),
            telegram_dry_run=_bool_env("QADAM_TELEGRAM_DRY_RUN", True),
            telegram_bot_configured=bool(os.getenv("TELEGRAM_BOT_TOKEN", "").strip()),
            telegram_bot_username_configured=bool(os.getenv("TELEGRAM_BOT_USERNAME", "").strip()),
            telegram_default_chat_configured=bool(os.getenv("TELEGRAM_DEFAULT_CHAT_ID", "").strip()),
            live_bridge_enabled=_bool_env("QADAM_LIVE_BRIDGE_ENABLED", True),
            live_bridge_endpoint=os.getenv("QADAM_STATUS_BRIDGE_ENDPOINT", "/api/cockpit-status"),
            live_bridge_max_age_seconds=int(os.getenv("QADAM_STATUS_BRIDGE_MAX_AGE_SECONDS", "15")),
            live_bridge_stale_after_seconds=int(os.getenv("QADAM_STATUS_BRIDGE_STALE_AFTER_SECONDS", "60")),
            live_bridge_rate_limit_per_minute=int(os.getenv("QADAM_STATUS_BRIDGE_RATE_LIMIT_PER_MINUTE", "60")),
        )
