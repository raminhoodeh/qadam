"""Runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_FUND_MANAGER_EMAILS = (
    "raminhoodeh@gmail.com",
    "troycookecareer@gmail.com",
    "isioras@yahoo.co.uk",
)
DEFAULT_PENDING_FUND_MANAGERS = ("Akber", "Anas")


def _csv_tuple(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


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
        )
