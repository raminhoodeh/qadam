from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

import pytest

from orchestrator.qadam_operator_ready_common import authority_flags
from orchestrator.qadam_public_status_bridge_check import build_public_status_bridge_check


class _Settings:
    runtime_dir: str

    def __init__(self, runtime_dir: str) -> None:
        self.runtime_dir = runtime_dir


def test_unconfigured_bridge_is_safe_but_not_operating_ready(tmp_path) -> None:
    import json

    (tmp_path / "qadam_public_status_bridge_security.json").write_text(
        json.dumps(
            {
                "endpoint_configured": False,
                "token_configured": False,
                "signing_key_configured": False,
                "browser_to_laptop_route": False,
                "command_route": False,
                "broker_write_route": False,
                "paper_order_route": False,
                "secret_value_exposed": False,
                "authority": authority_flags(),
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "qadam_public_status_publication_receipt.json").write_text(
        json.dumps(
            {
                "status": "disabled_not_configured",
                "published": False,
                "secret_value_exposed": False,
                "authority": authority_flags(),
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "qadam_public_status_parity.json").write_text(
        '{"status":"not_evaluated","digest_match":false}', encoding="utf-8"
    )
    result = build_public_status_bridge_check(_Settings(str(tmp_path)))
    assert result["implementation_valid"] is True
    assert result["operating_ready"] is False
    assert result["broker_write_count"] == 0


@pytest.mark.parametrize("payload_age,receipt_age,ready", [
    (60, 0, True), (601, 0, False), (None, 0, False), (-30, 0, False),
    (60, -30, False), (60, 901, False),
])
def test_resending_an_old_payload_cannot_make_the_bridge_fresh(tmp_path, payload_age, receipt_age, ready):
    now = datetime.now(timezone.utc)
    security = {key: True for key in ("endpoint_configured", "token_configured", "signing_key_configured")}
    security.update({key: False for key in ("browser_to_laptop_route", "command_route",
                                          "broker_write_route", "paper_order_route", "secret_value_exposed")})
    security["authority"] = authority_flags()
    receipt = {"generated_at": (now - timedelta(seconds=receipt_age)).isoformat(),
               "payload_generated_at": (now - timedelta(seconds=payload_age)).isoformat() if payload_age is not None else None,
               "status": "published", "published": True, "secret_value_exposed": False,
               "authority": authority_flags()}
    for filename, value in (
        ("qadam_public_status_bridge_security.json", security),
        ("qadam_public_status_publication_receipt.json", receipt),
        ("qadam_public_status_parity.json", {"status": "passed", "digest_match": True}),
    ):
        (tmp_path / filename).write_text(json.dumps(value), encoding="utf-8")
    result = build_public_status_bridge_check(_Settings(str(tmp_path)))
    assert result["operating_ready"] is ready
    assert result["publication_fresh"] is ready
    if payload_age is None or payload_age > 600 or payload_age < 0:
        assert "public_status_payload_not_fresh" in result["blockers"]
