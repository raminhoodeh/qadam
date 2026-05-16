"""Qadam orchestrator entry point."""

from __future__ import annotations

import asyncio

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.health_server import serve_health
from orchestrator.system_state import build_system_health
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT, SOURCE_SPECS


def _install_uvloop_if_available() -> None:
    try:
        import uvloop
    except Exception:
        return
    uvloop.install()


async def run() -> None:
    settings = Settings.from_env()
    event_log = EventLog()
    event_log.write(
        "orchestrator_started",
        "orchestrator",
        {
            "env": settings.env,
            "mode": settings.mode,
            "trial_balance_gbp": settings.trial_balance_gbp,
            "source_count": len(SOURCE_SPECS),
            "expected_source_count": EXPECTED_SOURCE_COUNT,
            "fund_manager_allowlist_count": len(settings.fund_manager_allowlist),
        },
    )

    def health() -> dict[str, object]:
        return build_system_health(settings, event_log_health=event_log.health())

    server = await serve_health(settings.health_host, settings.health_port, health)
    event_log.write(
        "health_endpoint_started",
        "orchestrator",
        {"host": settings.health_host, "port": settings.health_port},
    )

    async with server:
        await server.serve_forever()


def main() -> None:
    _install_uvloop_if_available()
    asyncio.run(run())


if __name__ == "__main__":
    main()
