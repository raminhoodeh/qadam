"""D9 secure live bridge contract and signed snapshot publisher helpers."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings

LIVE_BRIDGE_SCHEMA_VERSION = 1
LIVE_BRIDGE_SIGNATURE_FILENAME = "cockpit-status.signature.json"
LIVE_BRIDGE_ALLOWED_METHODS = ("GET", "HEAD")
LIVE_BRIDGE_FORBIDDEN_METHODS = ("POST", "PUT", "PATCH", "DELETE")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _signing_secret_configured() -> bool:
    return bool(os.getenv("QADAM_STATUS_BRIDGE_SIGNING_KEY", "").strip())


def _snapshot_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _snapshot_signature(payload: dict[str, Any]) -> tuple[str, str, bool]:
    secret = os.getenv("QADAM_STATUS_BRIDGE_SIGNING_KEY", "").strip()
    if secret:
        signature = hmac.new(secret.encode("utf-8"), _canonical_bytes(payload), hashlib.sha256).hexdigest()
        return "hmac_sha256", signature, True
    return "sha256_digest", _snapshot_digest(payload), False


def live_bridge_contract(settings: Settings, generated_at: str | None = None) -> dict[str, Any]:
    """Return the public-safe D9 bridge contract for the cockpit status payload."""

    configured = _signing_secret_configured()
    return {
        "schema_version": LIVE_BRIDGE_SCHEMA_VERSION,
        "phase": "D9",
        "status": "read_only_ready" if settings.live_bridge_enabled else "disabled",
        "generated_at": generated_at or _now(),
        "endpoint": settings.live_bridge_endpoint,
        "static_fallback": "/status/cockpit-status.json",
        "allowed_methods": list(LIVE_BRIDGE_ALLOWED_METHODS),
        "forbidden_methods": list(LIVE_BRIDGE_FORBIDDEN_METHODS),
        "authentication": "supabase_founding_fund_manager_required",
        "rate_limit_per_minute": settings.live_bridge_rate_limit_per_minute,
        "cache_policy": {
            "mode": "no_store_live_with_static_fallback",
            "max_age_seconds": settings.live_bridge_max_age_seconds,
            "stale_after_seconds": settings.live_bridge_stale_after_seconds,
        },
        "publisher": {
            "status": "hmac_signed" if configured else "local_digest_until_signing_secret_configured",
            "signature_algorithm": "hmac_sha256" if configured else "sha256_digest",
            "signature_configured": configured,
            "signature_file": f"status/{LIVE_BRIDGE_SIGNATURE_FILENAME}",
            "payload_source": "public_safe_cockpit_status",
        },
        "health_checks": [
            "auth_required",
            "rate_limit_enforced",
            "method_block_enforced",
            "snapshot_fallback_available",
            "broker_write_route_absent",
        ],
        "read_only": True,
        "browser_authority": "read_only",
        "write_authority": False,
        "broker_write_route": False,
        "local_orchestrator_exposed": False,
        "boundary": (
            "D9 bridge serves the public-safe cockpit status snapshot only. It cannot run shell commands, "
            "read secrets, expose the local orchestrator, approve trades, or send broker orders."
        ),
    }


def build_status_signature(payload: dict[str, Any]) -> dict[str, Any]:
    """Build a detached signature manifest for a public-safe cockpit status payload."""

    algorithm, signature, configured = _snapshot_signature(payload)
    return {
        "schema_version": LIVE_BRIDGE_SCHEMA_VERSION,
        "status": "signed" if configured else "digest_only",
        "payload_file": "cockpit-status.json",
        "payload_schema_version": payload.get("schema_version"),
        "payload_generated_at": payload.get("generated_at"),
        "signed_at": payload.get("generated_at") or _now(),
        "algorithm": algorithm,
        "signature": signature,
        "signature_configured": configured,
        "read_only": True,
        "browser_authority": "read_only",
        "broker_write_route": False,
        "boundary": "Detached D9 status proof for the public-safe snapshot. It carries no secret material.",
    }


def write_status_signature(payload: dict[str, Any], status_path: str | Path) -> Path:
    """Write the detached signature manifest beside a status snapshot."""

    path = Path(status_path).with_name(LIVE_BRIDGE_SIGNATURE_FILENAME)
    path.write_text(json.dumps(build_status_signature(payload), indent=2, sort_keys=True), encoding="utf-8")
    return path
