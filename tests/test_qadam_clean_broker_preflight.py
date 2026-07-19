from __future__ import annotations

from orchestrator.qadam_clean_broker_preflight import (
    build_clean_broker_preflight,
    validate_clean_broker_preflight,
)


class _Settings:
    runtime_dir: str

    def __init__(self, runtime_dir: str) -> None:
        self.runtime_dir = runtime_dir


def test_clean_broker_preflight_fails_existing_account(tmp_path, monkeypatch) -> None:
    fingerprint = "sha256:existing"
    (tmp_path / "qadam_testing_epoch_inventory.json").write_text(
        '{"broker_account_fingerprint":"sha256:existing"}', encoding="utf-8"
    )
    monkeypatch.setattr(
        "orchestrator.qadam_clean_broker_preflight.alpaca_paper_mirror_status",
        lambda _settings: {
            "paper_mode": True,
            "base_url": "https://paper-api.alpaca.markets",
            "readonly_paths": ["/account"],
        },
    )
    monkeypatch.setattr(
        "orchestrator.qadam_clean_broker_preflight.broker_account_fingerprint",
        lambda _account: fingerprint,
    )
    payload = build_clean_broker_preflight(
        settings=_Settings(str(tmp_path)),
        fetcher=lambda: {
            "account": {"currency": "USD", "equity": "100000", "cash": "100000", "status": "ACTIVE"},
            "positions": [],
            "orders": [],
        },
    )
    assert payload["preflight_passed"] is False
    assert "clean_broker_account_is_not_new" in payload["blockers"]
    assert validate_clean_broker_preflight(payload) == []


def test_clean_broker_preflight_passes_new_empty_account(tmp_path, monkeypatch) -> None:
    (tmp_path / "qadam_testing_epoch_inventory.json").write_text(
        '{"broker_account_fingerprint":"sha256:old"}', encoding="utf-8"
    )
    monkeypatch.setattr(
        "orchestrator.qadam_clean_broker_preflight.alpaca_paper_mirror_status",
        lambda _settings: {
            "paper_mode": True,
            "base_url": "https://paper-api.alpaca.markets",
            "readonly_paths": ["/account"],
        },
    )
    monkeypatch.setattr(
        "orchestrator.qadam_clean_broker_preflight.broker_account_fingerprint",
        lambda _account: "sha256:new",
    )
    payload = build_clean_broker_preflight(
        settings=_Settings(str(tmp_path)),
        fetcher=lambda: {
            "account": {"currency": "USD", "equity": "100000", "cash": "100000", "status": "ACTIVE"},
            "positions": [],
            "orders": [],
        },
    )
    assert payload["preflight_passed"] is True
    assert validate_clean_broker_preflight(payload) == []


def test_clean_broker_preflight_rejects_any_order_history(tmp_path, monkeypatch) -> None:
    (tmp_path / "qadam_testing_epoch_inventory.json").write_text(
        '{"broker_account_fingerprint":"sha256:old"}', encoding="utf-8"
    )
    monkeypatch.setattr(
        "orchestrator.qadam_clean_broker_preflight.alpaca_paper_mirror_status",
        lambda _settings: {
            "paper_mode": True,
            "base_url": "https://paper-api.alpaca.markets",
            "readonly_paths": ["/account", "/orders"],
        },
    )
    monkeypatch.setattr(
        "orchestrator.qadam_clean_broker_preflight.broker_account_fingerprint",
        lambda _account: "sha256:new",
    )
    payload = build_clean_broker_preflight(
        settings=_Settings(str(tmp_path)),
        fetcher=lambda: {
            "account": {"currency": "USD", "equity": "100000", "cash": "100000", "status": "ACTIVE"},
            "positions": [],
            "orders": [{"id": "closed-test-order"}],
        },
    )
    assert payload["preflight_passed"] is False
    assert "clean_broker_has_order_history" in payload["blockers"]
