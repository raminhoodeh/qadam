from __future__ import annotations

from dataclasses import replace
import gzip
import hashlib
import hmac
import json

from orchestrator.config import Settings
from orchestrator.qadam_public_status_publisher import publish_public_status


def _settings(tmp_path):
    return replace(Settings.from_env(), runtime_dir=str(tmp_path), data_root=str(tmp_path.parent))


def test_publisher_fails_safe_when_configuration_is_missing(tmp_path, monkeypatch):
    monkeypatch.delenv("QADAM_STATUS_PUBLISH_ENDPOINT", raising=False)
    monkeypatch.delenv("QADAM_STATUS_PUBLISH_TOKEN", raising=False)
    monkeypatch.delenv("QADAM_STATUS_BRIDGE_SIGNING_KEY", raising=False)
    monkeypatch.setattr(
        "orchestrator.qadam_public_status_publisher.secret_value",
        lambda *_args, **_kwargs: None,
    )
    receipt = publish_public_status(_settings(tmp_path))
    assert receipt["status"] == "disabled_not_configured"
    assert receipt["published"] is False
    assert receipt["broker_write_count"] == 0


def test_publisher_sends_validated_gzip_hmac_payload(tmp_path, monkeypatch):
    payload = {"generated_at": "2026-07-18T00:00:00+00:00", "mode": "paper"}
    (tmp_path / "cockpit-status.json").write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(
        "orchestrator.qadam_public_status_publisher.validate_cockpit_status",
        lambda value: None if value == payload else (_ for _ in ()).throw(ValueError()),
    )
    values = {
        "QADAM_STATUS_PUBLISH_ENDPOINT": "https://example.test/api/status",
        "QADAM_STATUS_PUBLISH_TOKEN": "publish-token",
        "QADAM_STATUS_BRIDGE_SIGNING_KEY": "signing-key",
    }
    monkeypatch.setattr(
        "orchestrator.qadam_public_status_publisher.secret_value",
        lambda key, _settings: values.get(key),
    )
    observed = {}

    def transport(endpoint, body, headers, timeout):
        canonical = gzip.decompress(body)
        observed.update(endpoint=endpoint, canonical=canonical, headers=headers, timeout=timeout)
        digest = hashlib.sha256(canonical).hexdigest()
        return 201, {"payload_digest": digest, "stored_at": "2026-07-18T00:00:01+00:00"}

    receipt = publish_public_status(_settings(tmp_path), transport=transport)
    expected_signature = hmac.new(b"signing-key", observed["canonical"], hashlib.sha256).hexdigest()
    assert receipt["status"] == "published"
    assert receipt["receiver_digest_matches"] is True
    assert observed["endpoint"].startswith("https://")
    assert observed["headers"]["X-Qadam-Signature"] == expected_signature
    assert observed["headers"]["Authorization"] == "Bearer publish-token"
