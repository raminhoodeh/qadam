from __future__ import annotations

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
