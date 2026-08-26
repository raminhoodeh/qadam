from __future__ import annotations

from dataclasses import replace
import fcntl
import json
from pathlib import Path
import plistlib

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import ROOT, write_json_atomic
from orchestrator.qadam_telegram_readonly_interface import (
    QUERY_NAMES,
    RESPONSE_LEDGER_ARTIFACT,
    build_readonly_query_response,
    classify_readonly_query,
    handle_readonly_query_update,
    validate_interface_status,
    write_interface_status,
)
from orchestrator.telegram_inbound_intake import (
    TELEGRAM_INBOUND_POLL_LOCK,
    TelegramInboundIntakeStore,
    poll_telegram_inbound_updates,
)


def _settings(tmp_path: Path) -> Settings:
    return replace(
        Settings.from_env(),
        runtime_dir=str(tmp_path),
        data_root=str(tmp_path.parent),
    )


def _write_json(path: Path, payload: dict) -> None:
    write_json_atomic(path, payload)


def test_query_classifier_supports_group_commands_and_rejects_arbitrary_chat() -> None:
    assert classify_readonly_query("/status") == "status"
    assert classify_readonly_query("/portfolio@QadamTradeBot", "QadamTradeBot") == "portfolio"
    assert classify_readonly_query("Qadam patterns") == "patterns"
    assert classify_readonly_query("@QadamTradeBot repairs", "@QadamTradeBot") == "repairs"
    assert classify_readonly_query("/buy SMH") == "forbidden_control"
    assert classify_readonly_query("tell me a joke") is None


def test_portfolio_response_reads_canonical_projection(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _write_json(
        tmp_path / "cockpit-status.json",
        {
            "dashboard_portfolio": {
                "generated_at": "2026-08-26T10:00:00+00:00",
                "current_balance_gbp": 100_123.45,
                "starting_balance_gbp": 100_000.0,
                "cash_gbp": 99_500.0,
                "realized_pnl_gbp": 120.0,
                "unrealized_pnl_gbp": 3.45,
                "open_position_count": 1,
                "closed_trade_count": 4,
                "positions": [
                    {
                        "instrument": "SMH",
                        "quantity": 2,
                        "unrealized_pnl_gbp": 3.45,
                    }
                ],
            }
        },
    )
    _write_json(tmp_path / "alpaca_paper_mirror.json", {"status": "ok", "snapshot": {}})

    response, provenance = build_readonly_query_response("portfolio", settings=settings)

    assert "Equity: US$100,123.45" in response
    assert "- SMH: 2 shares, +US$3.45 open P&L" in response
    assert "cockpit-status.json" in provenance["source_artifacts"]
    assert len(response) < 1_800


def test_patterns_response_ranks_distinct_latest_generation(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    rows = [
        {
            "generated_at": "2026-08-26T10:00:00+00:00",
            "instrument": "SMH",
            "market_family": "semiconductors",
            "strategy_label": "Semiconductor Policy Options Asymmetry",
            "raw_pattern_score": 0.64,
            "confidence_state": "score_ready_for_tape",
        },
        {
            "generated_at": "2026-08-26T10:00:00+00:00",
            "instrument": "QQQ",
            "market_family": "semiconductors",
            "strategy_label": "Semiconductor Policy Options Asymmetry",
            "raw_pattern_score": 0.64,
            "confidence_state": "score_ready_for_tape",
        },
        {
            "generated_at": "2026-08-26T10:00:00+00:00",
            "instrument": "BNO",
            "market_family": "oil",
            "strategy_label": "Energy Security Disruption",
            "raw_pattern_score": 0.55,
            "confidence_state": "score_ready_for_tape",
        },
        {
            "generated_at": "2026-08-25T10:00:00+00:00",
            "instrument": "SPY",
            "market_family": "macro",
            "strategy_label": "Stale Pattern",
            "raw_pattern_score": 0.99,
            "confidence_state": "score_ready_for_tape",
        },
    ]
    (tmp_path / "qadam_pattern_score_v3_records.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )
    _write_json(tmp_path / "qadam_pattern_score_v3.json", {"generated_at": rows[0]["generated_at"]})

    response, _provenance = build_readonly_query_response("patterns", settings=settings)

    assert response.count("Semiconductor Policy Options Asymmetry") == 1
    assert "Energy Security Disruption: research score 0.550 on BNO" in response
    assert "Stale Pattern" not in response
    assert "not return probabilities or trade approval" in response


def test_money_and_position_wording_are_human_readable(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _write_json(
        tmp_path / "cockpit-status.json",
        {
            "dashboard_portfolio": {
                "current_balance_gbp": 99_990.0,
                "starting_balance_gbp": 100_000.0,
                "cash_gbp": 99_500.0,
                "realized_pnl_gbp": -8.0,
                "unrealized_pnl_gbp": -2.0,
                "open_position_count": 1,
                "positions": [
                    {
                        "instrument": "ITA",
                        "quantity": 1,
                        "unrealized_pnl_gbp": -2.0,
                    }
                ],
            }
        },
    )
    _write_json(tmp_path / "alpaca_paper_mirror.json", {"status": "ok", "snapshot": {}})

    response, _provenance = build_readonly_query_response("portfolio", settings=settings)

    assert "Total P&L: -US$10.00" in response
    assert "- ITA: 1 share, -US$2.00 open P&L" in response


def test_authorized_query_is_delivered_once_without_persisting_raw_ids(
    tmp_path: Path,
    monkeypatch,
) -> None:
    settings = _settings(tmp_path)
    monkeypatch.setattr(
        "orchestrator.qadam_telegram_readonly_interface.secret_value",
        lambda name, _settings: {
            "TELEGRAM_BOT_USERNAME": "QadamTradeBot",
            "TELEGRAM_GROUP_CHAT_ID": "-100999",
            "TELEGRAM_BOT_TOKEN": "test-token",
        }.get(name),
    )
    sent: list[str] = []

    def sender(_token: str, _target: str, text: str, _reply: int | None) -> dict:
        sent.append(text)
        return {"ok": True}

    update = {"update_id": 123}
    message = {
        "message_id": 456,
        "chat": {"id": -100999},
        "from": {"id": 789},
    }
    first = handle_readonly_query_update(
        update,
        message,
        "/help",
        settings=settings,
        sender=sender,
    )
    second = handle_readonly_query_update(
        update,
        message,
        "/help",
        settings=settings,
        sender=sender,
    )

    assert first["delivery_status"] == "delivered"
    assert second["delivery_status"] == "duplicate_suppressed"
    assert len(sent) == 1
    persisted = (tmp_path / RESPONSE_LEDGER_ARTIFACT).read_text(encoding="utf-8")
    assert "-100999" not in persisted
    assert '"message_id"' not in persisted
    assert '"chat_id"' not in persisted
    assert '"paper_order_created":false' in persisted


def test_failed_delivery_is_retryable_and_not_marked_delivered(tmp_path: Path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    monkeypatch.setattr(
        "orchestrator.qadam_telegram_readonly_interface.secret_value",
        lambda name, _settings: {
            "TELEGRAM_BOT_USERNAME": "QadamTradeBot",
            "TELEGRAM_GROUP_CHAT_ID": "-100999",
            "TELEGRAM_BOT_TOKEN": "test-token",
        }.get(name),
    )

    def failing_sender(_token: str, _target: str, _text: str, _reply: int | None) -> dict:
        return {"ok": False, "error_class": "URLError"}

    result = handle_readonly_query_update(
        {"update_id": 1},
        {"message_id": 2, "chat": {"id": -100999}, "from": {"id": 3}},
        "/status",
        settings=settings,
        sender=failing_sender,
    )

    assert result["delivery_status"] == "delivery_retry_pending"
    assert result["retry_required"] is True


def test_unauthorized_group_is_silently_ignored(tmp_path: Path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    monkeypatch.setattr(
        "orchestrator.qadam_telegram_readonly_interface.secret_value",
        lambda name, _settings: {
            "TELEGRAM_BOT_USERNAME": "QadamTradeBot",
            "TELEGRAM_GROUP_CHAT_ID": "-100999",
            "TELEGRAM_BOT_TOKEN": "test-token",
        }.get(name),
    )
    result = handle_readonly_query_update(
        {"update_id": 1},
        {"message_id": 2, "chat": {"id": -100111}, "from": {"id": 3}},
        "/health",
        settings=settings,
        sender=lambda *_args: {"ok": True},
    )

    assert result["delivery_status"] == "unauthorized_group_ignored"
    assert result["retry_required"] is False


def test_status_contract_preserves_query_and_execution_boundary(tmp_path: Path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    monkeypatch.setattr(
        "orchestrator.qadam_telegram_readonly_interface.secret_status",
        lambda _name, _settings: type("Status", (), {"configured": True})(),
    )
    status = write_interface_status(
        {"status": "ok", "query_count": 0},
        settings=settings,
        registration_result={"registered": True},
    )

    assert status["status"] == "ready"
    assert status["available_queries"] == list(QUERY_NAMES)
    assert status["authority"]["query_response_send_allowed"] is True
    assert status["authority"]["telegram_command_authority"] is False
    assert status["authority"]["paper_order_allowed"] is False
    assert status["paper_order_created_count"] == 0
    assert validate_interface_status(status) == []


def test_launchd_schedule_uses_readonly_runner_only() -> None:
    template = (
        ROOT / "ops" / "launchd" / "com.qadam.telegram-readonly-interface.plist.template"
    ).read_text(encoding="utf-8")
    payload = plistlib.loads(template.replace("__QADAM_ROOT__", str(ROOT)).encode())
    arguments = [str(item) for item in payload["ProgramArguments"]]

    assert payload["Label"] == "com.qadam.telegram-readonly-interface"
    assert payload["StartInterval"] == 30
    assert payload["RunAtLoad"] is True
    assert arguments[3].endswith("scripts/run_qadam_telegram_readonly_interface.py")
    assert all("paperops" not in argument.lower() for argument in arguments)
    assert payload["EnvironmentVariables"]["QADAM_LIVE_CAPITAL_ENABLED"] == "false"


def test_shared_poller_routes_query_without_adding_research_intake(tmp_path: Path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    monkeypatch.setattr(
        "orchestrator.telegram_inbound_intake.secret_value",
        lambda _name, _settings: "test-token",
    )
    monkeypatch.setattr(
        "orchestrator.telegram_inbound_intake._telegram_request",
        lambda _token, _payload: {
            "ok": True,
            "result": [
                {
                    "update_id": 77,
                    "message": {
                        "message_id": 88,
                        "chat": {"id": -100999},
                        "from": {"id": 99},
                        "text": "/status",
                    },
                }
            ],
        },
    )
    monkeypatch.setattr(
        "orchestrator.telegram_inbound_intake.handle_readonly_query_update",
        lambda *_args, **_kwargs: {
            "handled": True,
            "delivery_status": "delivered",
            "retry_required": False,
        },
    )
    monkeypatch.setattr(
        "orchestrator.telegram_inbound_intake.write_interface_status",
        lambda *_args, **_kwargs: {},
    )

    result = poll_telegram_inbound_updates(settings=settings)

    assert result["status"] == "ok"
    assert result["query_count"] == 1
    assert result["query_delivery_count"] == 1
    assert result["created_count"] == 0
    assert TelegramInboundIntakeStore(settings).read_records() == ()
    assert TelegramInboundIntakeStore(settings).latest_offset() == 78


def test_failed_query_delivery_does_not_advance_shared_offset(tmp_path: Path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    TelegramInboundIntakeStore(settings).write_offset(50)
    monkeypatch.setattr(
        "orchestrator.telegram_inbound_intake.secret_value",
        lambda _name, _settings: "test-token",
    )
    monkeypatch.setattr(
        "orchestrator.telegram_inbound_intake._telegram_request",
        lambda _token, _payload: {
            "ok": True,
            "result": [
                {
                    "update_id": 50,
                    "message": {
                        "message_id": 88,
                        "chat": {"id": -100999},
                        "from": {"id": 99},
                        "text": "/status",
                    },
                }
            ],
        },
    )
    monkeypatch.setattr(
        "orchestrator.telegram_inbound_intake.handle_readonly_query_update",
        lambda *_args, **_kwargs: {
            "handled": True,
            "delivery_status": "delivery_retry_pending",
            "retry_required": True,
        },
    )
    monkeypatch.setattr(
        "orchestrator.telegram_inbound_intake.write_interface_status",
        lambda *_args, **_kwargs: {},
    )

    result = poll_telegram_inbound_updates(settings=settings)

    assert result["status"] == "ok_with_query_delivery_retry"
    assert result["processed_update_count"] == 0
    assert TelegramInboundIntakeStore(settings).latest_offset() == 50


def test_shared_poll_lock_prevents_competing_consumers(tmp_path: Path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    monkeypatch.setattr(
        "orchestrator.telegram_inbound_intake.write_interface_status",
        lambda *_args, **_kwargs: {},
    )
    lock_path = tmp_path / TELEGRAM_INBOUND_POLL_LOCK
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = poll_telegram_inbound_updates(settings=settings)
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    assert result["status"] == "concurrent_poll_skipped"
    assert result["fetched_update_count"] == 0
