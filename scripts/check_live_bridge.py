#!/usr/bin/env python3
# ruff: noqa: E402
"""Validate the D9 secure live bridge contract and static implementation hooks."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.cockpit_status import export_cockpit_status, validate_cockpit_status  # noqa: E402
from orchestrator.config import Settings  # noqa: E402
from orchestrator.telegram_comms import ensure_d8a_telegram_dry_run  # noqa: E402


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    settings = Settings.from_env()
    ensure_d8a_telegram_dry_run(settings)
    configured_site_root = os.getenv("QADAM_DASHBOARD_SITE_ROOT", "").strip()
    landing_repo_path = Path(configured_site_root) if configured_site_root else ROOT / "landing-page-repo"
    result = export_cockpit_status(settings=settings, landing_repo_path=landing_repo_path)

    runtime_path = Path(result["runtime_path"])
    signature_path = Path(result["runtime_signature_path"])
    payload = json.loads(runtime_path.read_text(encoding="utf-8"))
    signature = json.loads(signature_path.read_text(encoding="utf-8"))
    validate_cockpit_status(payload)

    bridge = payload["live_bridge"]
    require(bridge["phase"] == "D9", "live bridge phase mismatch")
    require(bridge["status"] == "read_only_ready", "live bridge is not ready")
    require(bridge["endpoint"] == "/api/cockpit-status", "live bridge endpoint mismatch")
    require(bridge["allowed_methods"] == ["GET", "HEAD"], "live bridge allowed methods mismatch")
    require(all(method in bridge["forbidden_methods"] for method in ("POST", "PUT", "PATCH", "DELETE")), "write methods not blocked")
    require(bridge["authentication"] == "supabase_founding_fund_manager_required", "live bridge auth mismatch")
    require(bridge["rate_limit_per_minute"] > 0, "live bridge rate limit missing")
    require(bridge["read_only"] is True, "live bridge must be read-only")
    require(bridge["write_authority"] is False, "live bridge write authority enabled")
    require(bridge["broker_write_route"] is False, "live bridge broker write route enabled")
    require(bridge["local_orchestrator_exposed"] is False, "live bridge exposes local orchestrator")
    require(bridge["static_fallback"] == "/status/cockpit-status.json", "static fallback mismatch")
    require("public-safe cockpit status snapshot only" in bridge["boundary"], "bridge boundary is weak")
    require(signature["payload_generated_at"] == payload["generated_at"], "signature generated_at mismatch")
    require(signature["payload_schema_version"] == payload["schema_version"], "signature schema mismatch")
    require(signature["read_only"] is True, "signature read-only flag missing")
    require(signature["broker_write_route"] is False, "signature broker route flag missing")
    require(len(signature["signature"]) == 64, "signature digest length mismatch")

    route_path = ROOT / "cockpit" / "app" / "api" / "cockpit-status" / "route.ts"
    route = route_path.read_text(encoding="utf-8")
    for marker in (
        "currentSupabaseUserFromRequest",
        "rateLimit",
        "export async function GET",
        "export async function HEAD",
        "export async function POST",
        "export async function PUT",
        "export async function PATCH",
        "export async function DELETE",
        "methodNotAllowed",
        "\"X-Qadam-Broker-Write-Route\": \"false\"",
        "validatePublicStatus",
    ):
        require(marker in route, f"route missing marker: {marker}")

    renderer = (landing_repo_path / "dashboard.js").read_text(encoding="utf-8")
    for marker in (
        "STATUS_SOURCES",
        "\"/api/cockpit-status\"",
        "\"/status/cockpit-status.json\"",
        "statusFetchHeaders",
        "dashboardStatusSource",
        "read-only status API",
        "static snapshot fallback",
    ):
        require(marker in renderer, f"dashboard renderer missing marker: {marker}")

    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    for marker in (
        "QADAM_LIVE_BRIDGE_ENABLED=true",
        "QADAM_STATUS_BRIDGE_ENDPOINT=/api/cockpit-status",
        "QADAM_STATUS_BRIDGE_RATE_LIMIT_PER_MINUTE=60",
        "QADAM_STATUS_BRIDGE_SIGNING_KEY=",
    ):
        require(marker in env_example, f"env example missing marker: {marker}")

    print("live_bridge_check=ok")
    print(f"live_bridge_status={bridge['status']}")
    print(f"live_bridge_endpoint={bridge['endpoint']}")
    print(f"live_bridge_signature_status={signature['status']}")
    print(f"live_bridge_rate_limit_per_minute={bridge['rate_limit_per_minute']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        print(f"live_bridge_check=failed:{error}")
        raise SystemExit(1)
