"""One-way publisher for Qadam's public-safe dashboard snapshot.

The publisher can send only an already validated cockpit snapshot to the
dedicated public status receiver. It exposes no browser-to-laptop route and has
no trading, broker, command, proof, or live-capital authority.
"""

from __future__ import annotations

import gzip
import hashlib
import hmac
import json
import os
from pathlib import Path
import urllib.error
import urllib.request
from typing import Any, Callable

from orchestrator.cockpit_status import validate_cockpit_status
from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    runtime_dir,
    write_json_atomic,
)
from orchestrator.secrets import secret_value

SCHEMA_VERSION = "qadam_public_status_publisher.v1"
RECEIPT_ARTIFACT = "qadam_public_status_publication_receipt.json"
SECURITY_ARTIFACT = "qadam_public_status_bridge_security.json"
PARITY_ARTIFACT = "qadam_public_status_parity.json"
SNAPSHOT_ARTIFACT = "cockpit-status.json"
MAX_UNCOMPRESSED_BYTES = 8 * 1024 * 1024
MAX_COMPRESSED_BYTES = 4 * 1024 * 1024

Transport = Callable[[str, bytes, dict[str, str], int], tuple[int, dict[str, Any]]]


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _default_transport(
    endpoint: str,
    body: bytes,
    headers: dict[str, str],
    timeout_seconds: int,
) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(
        endpoint,
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read()
            payload = json.loads(raw.decode("utf-8")) if raw else {}
            return int(response.status), payload
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        payload = json.loads(raw.decode("utf-8")) if raw else {}
        return int(exc.code), payload


def _configuration(settings: Settings) -> dict[str, Any]:
    endpoint = (
        secret_value("QADAM_STATUS_PUBLISH_ENDPOINT", settings)
        or os.getenv("QADAM_STATUS_PUBLISH_ENDPOINT", "")
        or "https://www.qadam.trade/api/cockpit-status-publish"
    ).strip()
    token = secret_value("QADAM_STATUS_PUBLISH_TOKEN", settings) or ""
    signing_key = secret_value("QADAM_STATUS_BRIDGE_SIGNING_KEY", settings) or ""
    return {
        "endpoint": endpoint,
        "token": token,
        "signing_key": signing_key,
        "endpoint_configured": endpoint.startswith("https://"),
        "token_configured": bool(token),
        "signing_key_configured": bool(signing_key),
    }


def _write_security_artifact(
    runtime: Path,
    config: dict[str, Any],
    *,
    status: str,
) -> dict[str, Any]:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_public_status_bridge_security",
        "generated_at": now_iso(),
        "status": status,
        "endpoint_configured": config["endpoint_configured"],
        "token_configured": config["token_configured"],
        "signing_key_configured": config["signing_key_configured"],
        "payload_source": f"data/runtime/{SNAPSHOT_ARTIFACT}",
        "transport": "outbound_https_post_gzip_hmac_sha256",
        "browser_to_laptop_route": False,
        "command_route": False,
        "broker_write_route": False,
        "paper_order_route": False,
        "live_capital_enabled": False,
        "secret_value_exposed": False,
        "authority": authority_flags(),
        "boundary": (
            "One-way publication of an already validated public-safe snapshot. "
            "The receiver cannot call the laptop, execute commands, approve "
            "research, create orders, write to brokers, or grant proof credit."
        ),
    }
    write_json_atomic(runtime / SECURITY_ARTIFACT, payload)
    write_json_atomic(runtime / "qadam_public_status_security_audit.json", payload)
    return payload


def publish_public_status(
    settings: Settings | None = None,
    *,
    transport: Transport | None = None,
    require_configured: bool = False,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    runtime = runtime_dir(settings)
    snapshot_path = runtime / SNAPSHOT_ARTIFACT
    config = _configuration(settings)
    configured = all(
        config[key]
        for key in (
            "endpoint_configured",
            "token_configured",
            "signing_key_configured",
        )
    )
    _write_security_artifact(
        runtime,
        config,
        status="passed" if configured else "configuration_incomplete",
    )

    base_receipt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_public_status_publication_receipt",
        "generated_at": now_iso(),
        "snapshot_path": f"data/runtime/{SNAPSHOT_ARTIFACT}",
        "endpoint_configured": config["endpoint_configured"],
        "token_configured": config["token_configured"],
        "signing_key_configured": config["signing_key_configured"],
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "secret_value_exposed": False,
        "authority": authority_flags(),
    }
    if not configured:
        receipt = {
            **base_receipt,
            "status": "blocked" if require_configured else "disabled_not_configured",
            "published": False,
            "reason": "publish_endpoint_token_or_signing_key_missing",
            "boundary": "Static deployed snapshot remains the explicit fallback.",
        }
        write_json_atomic(
            runtime / PARITY_ARTIFACT,
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_public_status_parity",
                "generated_at": now_iso(),
                "status": "not_evaluated",
                "local_payload_digest": None,
                "receiver_payload_digest": None,
                "digest_match": False,
                "reason": "publication_not_configured",
                "secret_value_exposed": False,
                "authority": authority_flags(),
            },
        )
        write_json_atomic(runtime / RECEIPT_ARTIFACT, receipt)
        write_json_atomic(runtime / "qadam_public_status_publish_receipt.json", receipt)
        return receipt
    if not snapshot_path.exists():
        receipt = {
            **base_receipt,
            "status": "blocked",
            "published": False,
            "reason": "public_safe_snapshot_missing",
        }
        write_json_atomic(runtime / RECEIPT_ARTIFACT, receipt)
        write_json_atomic(runtime / "qadam_public_status_publish_receipt.json", receipt)
        return receipt

    payload = read_json(snapshot_path)
    try:
        validate_cockpit_status(payload)
    except (TypeError, ValueError) as exc:
        receipt = {
            **base_receipt,
            "status": "blocked",
            "published": False,
            "reason": "public_safe_snapshot_validation_failed",
            "validation_error": str(exc)[:500],
        }
        write_json_atomic(runtime / RECEIPT_ARTIFACT, receipt)
        write_json_atomic(runtime / "qadam_public_status_publish_receipt.json", receipt)
        return receipt

    canonical = _canonical_bytes(payload)
    compressed = gzip.compress(canonical, compresslevel=6, mtime=0)
    digest = hashlib.sha256(canonical).hexdigest()
    signature = hmac.new(
        config["signing_key"].encode("utf-8"),
        canonical,
        hashlib.sha256,
    ).hexdigest()
    if len(canonical) > MAX_UNCOMPRESSED_BYTES or len(compressed) > MAX_COMPRESSED_BYTES:
        receipt = {
            **base_receipt,
            "status": "blocked",
            "published": False,
            "reason": "snapshot_exceeds_publication_budget",
            "payload_bytes": len(canonical),
            "compressed_bytes": len(compressed),
        }
        write_json_atomic(runtime / RECEIPT_ARTIFACT, receipt)
        write_json_atomic(runtime / "qadam_public_status_publish_receipt.json", receipt)
        return receipt

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {config['token']}",
        "Content-Encoding": "gzip",
        "Content-Type": "application/json",
        "User-Agent": "Qadam-Public-Status-Publisher/1",
        "X-Qadam-Payload-Digest": digest,
        "X-Qadam-Signature": signature,
    }
    sender = transport or _default_transport
    try:
        status_code, response = sender(
            config["endpoint"],
            compressed,
            headers,
            timeout_seconds,
        )
        response_digest = str(response.get("payload_digest") or "")
        accepted = 200 <= status_code < 300 and response_digest == digest
        reason = "receiver_confirmed_digest" if accepted else str(
            response.get("status") or "receiver_parity_failed"
        )
    except (OSError, TimeoutError, ValueError, urllib.error.URLError) as exc:
        status_code = (
            int(exc.code) if isinstance(exc, urllib.error.HTTPError) else None
        )
        response = {}
        response_digest = ""
        accepted = False
        reason = f"transport_error:{exc.__class__.__name__}"
        if status_code is not None:
            reason += f":http_status_{status_code}"

    receipt = {
        **base_receipt,
        "status": "published" if accepted else "degraded",
        "published": accepted,
        "reason": reason,
        "payload_generated_at": payload.get("generated_at"),
        "payload_digest": digest,
        "payload_bytes": len(canonical),
        "compressed_bytes": len(compressed),
        "http_status": status_code,
        "receiver_status": response.get("status"),
        "receiver_upstream_status": response.get("upstream_status"),
        "receiver_digest_matches": response_digest == digest,
        "receiver_stored_at": response.get("stored_at"),
        "boundary": "Status publication only; no execution authority was transferred.",
    }
    parity = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_public_status_parity",
        "generated_at": now_iso(),
        "status": "passed" if accepted else "degraded",
        "local_payload_digest": digest,
        "receiver_payload_digest": response_digest or None,
        "digest_match": response_digest == digest,
        "payload_generated_at": payload.get("generated_at"),
        "secret_value_exposed": False,
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / PARITY_ARTIFACT, parity)
    write_json_atomic(runtime / RECEIPT_ARTIFACT, receipt)
    write_json_atomic(runtime / "qadam_public_status_publish_receipt.json", receipt)
    return receipt
