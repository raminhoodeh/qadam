"""Validate one-way public status bridge safety, delivery, and parity."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    runtime_dir,
    unique_errors,
    validate_authority,
)

SCHEMA_VERSION = "qadam_public_status_bridge_check.v1"
ARTIFACT = "qadam_public_status_bridge_checks.json"


def _parse(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def build_public_status_bridge_check(
    settings: Settings | None = None,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    security = read_json(runtime / "qadam_public_status_bridge_security.json")
    receipt = read_json(runtime / "qadam_public_status_publication_receipt.json")
    parity = read_json(runtime / "qadam_public_status_parity.json")
    security_errors: list[str] = []
    if security.get("browser_to_laptop_route") is not False:
        security_errors.append("public_bridge_browser_to_laptop_route_present")
    if security.get("command_route") is not False:
        security_errors.append("public_bridge_command_route_present")
    if security.get("broker_write_route") is not False:
        security_errors.append("public_bridge_broker_write_route_present")
    if security.get("paper_order_route") is not False:
        security_errors.append("public_bridge_paper_order_route_present")
    if security.get("secret_value_exposed") is not False:
        security_errors.append("public_bridge_secret_value_exposed")
    if receipt.get("secret_value_exposed") is not False:
        security_errors.append("public_bridge_receipt_exposed_secret")
    security_errors.extend(
        validate_authority(security.get("authority", {}), prefix="public_bridge_security")
    )
    security_errors.extend(
        validate_authority(receipt.get("authority", {}), prefix="public_bridge_receipt")
    )
    implementation_valid = not unique_errors(security_errors)
    configured = all(
        security.get(key) is True
        for key in (
            "endpoint_configured",
            "token_configured",
            "signing_key_configured",
        )
    )
    published = receipt.get("published") is True and receipt.get("status") == "published"
    parity_passed = parity.get("digest_match") is True and parity.get("status") == "passed"
    generated = _parse(receipt.get("generated_at"))
    age = (
        int((datetime.now(timezone.utc) - generated).total_seconds())
        if generated is not None
        else None
    )
    fresh = age is not None and age <= 900
    operating_ready = implementation_valid and configured and published and parity_passed and fresh
    blockers = []
    if not configured:
        blockers.append("public_status_endpoint_token_or_signing_key_not_configured")
    if not published:
        blockers.append("public_status_snapshot_not_published")
    if not parity_passed:
        blockers.append("public_status_receiver_digest_parity_not_passed")
    if not fresh:
        blockers.append("public_status_publication_receipt_not_fresh")
    blockers.extend(security_errors)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_public_status_bridge_checks",
        "generated_at": now_iso(),
        "status": "passed" if operating_ready else "blocked",
        "implementation_valid": implementation_valid,
        "operating_ready": operating_ready,
        "configured": configured,
        "published": published,
        "digest_parity_passed": parity_passed,
        "publication_age_seconds": age,
        "publication_fresh": fresh,
        "browser_to_laptop_route": False,
        "command_route": False,
        "broker_write_route": False,
        "secret_value_exposed": False,
        "blocker_count": len(unique_errors(blockers)),
        "blockers": unique_errors(blockers),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "authority": authority_flags(),
    }
    AtomicArtifactStore(runtime).write_json(ARTIFACT, payload)
    return payload


__all__ = ["ARTIFACT", "build_public_status_bridge_check"]
