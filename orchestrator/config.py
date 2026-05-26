"""Runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

from orchestrator.release_contract import (
    LIVE_CAPITAL_ENABLED,
    PAPER_ACCOUNT_BALANCE_GBP,
    PAPER_OPERATIONAL_MAX_NOTIONAL_GBP,
)

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
    yfinance_enabled: bool
    yfinance_cache_dir: str
    yfinance_request_budget_per_run: int
    yfinance_symbol_allowlist: tuple[str, ...]
    preference_mcp_enabled: bool
    preference_mcp_endpoint: str
    preference_mcp_transport: str
    preference_mcp_daily_call_budget: int
    preference_mcp_run_call_budget: int
    preference_mcp_paid_tools_allowed: bool
    preference_mcp_tool_allowlist: tuple[str, ...]
    preference_mcp_domain_allowlist: tuple[str, ...]
    preference_mcp_timeout_seconds: int
    paper_operational_enabled: bool
    alpaca_paper_submit_enabled: bool
    alpaca_paper_exit_enabled: bool
    live_capital_enabled: bool
    paper_operational_max_notional_gbp: int
    quantum_paper_parity_required: bool
    qctrl_paper_consultation_enabled: bool

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
            trial_balance_gbp=int(
                os.getenv("QADAM_TRIAL_BALANCE_GBP", str(PAPER_ACCOUNT_BALANCE_GBP))
            ),
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
            yfinance_enabled=_bool_env("YFINANCE_ENABLED", False),
            yfinance_cache_dir=os.getenv("YFINANCE_CACHE_DIR", "./data/runtime/yfinance-cache"),
            yfinance_request_budget_per_run=int(os.getenv("YFINANCE_REQUEST_BUDGET_PER_RUN", "25")),
            yfinance_symbol_allowlist=_csv_tuple(
                os.getenv(
                    "YFINANCE_SYMBOL_ALLOWLIST",
                    "CL=F,BZ=F,USO,XLE,SI=F,SLV,SIL,PAAS,ITA,XAR,LMT,RTX,NOC,"
                    "SMH,SOXX,NVDA,TSM,ASML,AMD,SPY,QQQ,TLT,HYG,^VIX,DX-Y.NYB",
                )
            ),
            preference_mcp_enabled=_bool_env("PREFERENCE_MCP_ENABLED", False),
            preference_mcp_endpoint=os.getenv("PREFERENCE_MCP_ENDPOINT", "https://pref.trade/mcp"),
            preference_mcp_transport=os.getenv("PREFERENCE_MCP_TRANSPORT", "streamable-http"),
            preference_mcp_daily_call_budget=int(os.getenv("PREFERENCE_DAILY_CALL_BUDGET", "250")),
            preference_mcp_run_call_budget=int(os.getenv("PREFERENCE_RUN_CALL_BUDGET", "10")),
            preference_mcp_paid_tools_allowed=_bool_env("PREFERENCE_PAID_TOOLS_ALLOWED", False),
            preference_mcp_tool_allowlist=_csv_tuple(os.getenv("PREFERENCE_TOOL_ALLOWLIST", "")),
            preference_mcp_domain_allowlist=_csv_tuple(
                os.getenv(
                    "PREFERENCE_DOMAIN_ALLOWLIST",
                    "prediction_markets,physical_movement,filings_corporate,"
                    "macro_commodities,crypto_wallets,news_narrative",
                )
            ),
            preference_mcp_timeout_seconds=int(os.getenv("PREFERENCE_MCP_TIMEOUT_SECONDS", "15")),
            paper_operational_enabled=_bool_env("QADAM_PAPER_OPERATIONAL_ENABLED", False),
            alpaca_paper_submit_enabled=_bool_env("QADAM_ALPACA_PAPER_SUBMIT_ENABLED", False),
            alpaca_paper_exit_enabled=_bool_env("QADAM_ALPACA_PAPER_EXIT_ENABLED", False),
            live_capital_enabled=_bool_env("QADAM_LIVE_CAPITAL_ENABLED", LIVE_CAPITAL_ENABLED),
            paper_operational_max_notional_gbp=int(
                os.getenv(
                    "QADAM_PAPER_OPERATIONAL_MAX_NOTIONAL_GBP",
                    str(PAPER_OPERATIONAL_MAX_NOTIONAL_GBP),
                )
            ),
            quantum_paper_parity_required=_bool_env("QADAM_QUANTUM_PAPER_PARITY_REQUIRED", True),
            qctrl_paper_consultation_enabled=_bool_env(
                "QADAM_QCTRL_PAPER_CONSULTATION_ENABLED", False
            ),
        )
