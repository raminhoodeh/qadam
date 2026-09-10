from __future__ import annotations

from dataclasses import replace
import gzip
import hashlib
import hmac
import json
import pytest

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


@pytest.mark.parametrize("receiver_error,retryable", [
    ("status_object_store_400", False),
    ("status_bucket_check_544", True),
    ("status_bucket_create_503", True),
    ("status_object_store_502", True),
    ("status_bucket_check_401", False),
    ("status_bucket_check_403", False),
    ("invalid_json_544", False),
])
def test_publisher_preserves_safe_receiver_diagnostic(tmp_path, monkeypatch, receiver_error, retryable):
    payload = {"generated_at": "2026-07-18T00:00:00+00:00", "mode": "paper"}
    (tmp_path / "cockpit-status.json").write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(
        "orchestrator.qadam_public_status_publisher.validate_cockpit_status",
        lambda _value: None,
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

    receipt = publish_public_status(
        _settings(tmp_path),
        transport=lambda *_args: (
            400,
            {
                "status": "invalid_public_status_payload",
                "error": receiver_error,
            },
        ),
    )

    assert receipt["status"] == "degraded"
    assert receipt["receiver_error"] == receiver_error
    assert receipt["secret_value_exposed"] is False
    from orchestrator.runtime.operator import _result_is_optional_publication_transport_hold

    assert _result_is_optional_publication_transport_hold(
        ("scripts/publish_qadam_public_status.py",),
        {"returncode": 1, "work_result": receipt},
    ) is retryable
    assert receipt["published"] is False
