from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_paper_epoch import (
    CLEAN_STARTING_EQUITY,
    archive_testing_epoch,
    broker_account_fingerprint,
    build_epoch_record,
    clear_archived_execution_artifacts,
    filter_current_epoch_records,
    record_matches_epoch,
    research_artifact_was_archived,
)
from orchestrator.paper_account import PaperAccountSnapshot


class _Settings:
    def __init__(self, runtime_dir: Path) -> None:
        self.runtime_dir = str(runtime_dir)


def _clean_epoch() -> dict:
    return build_epoch_record(
        epoch_kind="clean_operator_epoch",
        started_at="2026-07-18T12:00:00+00:00",
        broker_account_fingerprint_value="sha256:new",
        starting_equity=CLEAN_STARTING_EQUITY,
        currency="USD",
        label="clean operator epoch",
        previous_epoch_id="legacy-testing-epoch",
        paper_epoch_id="paper-epoch-clean",
    )


def test_clean_epoch_requires_usd_and_exact_starting_equity() -> None:
    with pytest.raises(ValueError, match="USD"):
        build_epoch_record(
            epoch_kind="clean_operator_epoch",
            started_at="2026-07-18T12:00:00+00:00",
            broker_account_fingerprint_value="sha256:new",
            starting_equity=100_000,
            currency="GBP",
            label="invalid",
        )
    with pytest.raises(ValueError, match="100,000"):
        build_epoch_record(
            epoch_kind="clean_operator_epoch",
            started_at="2026-07-18T12:00:00+00:00",
            broker_account_fingerprint_value="sha256:new",
            starting_equity=99_999,
            currency="USD",
            label="invalid",
        )


def test_broker_fingerprint_is_stable_and_hides_identity() -> None:
    account = {"id": "secret-account-id", "currency": "USD", "status": "ACTIVE", "paper": True}
    first = broker_account_fingerprint(account)
    second = broker_account_fingerprint(account)
    assert first == second
    assert first is not None and first.startswith("sha256:")
    assert "secret-account-id" not in first


def test_clean_epoch_filters_legacy_and_wrong_epoch_records() -> None:
    epoch = _clean_epoch()
    records = [
        {"order_id": "old", "submitted_at": "2026-07-17T12:00:00+00:00"},
        {"order_id": "wrong", "paper_epoch_id": "paper-epoch-other"},
        {"order_id": "new", "paper_epoch_id": "paper-epoch-clean"},
        {
            "order_id": "timestamp-fallback",
            "submitted_at": "2026-07-18T12:01:00+00:00",
            "broker_account_fingerprint": "sha256:new",
        },
    ]
    assert record_matches_epoch(records[0], epoch) is False
    assert record_matches_epoch(records[1], epoch) is False
    assert record_matches_epoch(records[2], epoch) is True
    assert record_matches_epoch(records[3], epoch) is True
    assert [row["order_id"] for row in filter_current_epoch_records(records, epoch=epoch)] == [
        "new",
        "timestamp-fallback",
    ]


def test_archive_is_verified_before_active_files_are_cleared(tmp_path: Path) -> None:
    settings = _Settings(tmp_path)
    (tmp_path / "paper_orders.jsonl").write_text('{"order_id":"test"}\n', encoding="utf-8")
    (tmp_path / "paper_closed_trades.jsonl").write_text('{"trade_id":"test"}\n', encoding="utf-8")
    (tmp_path / "qadam_learning_cycle_dashboard.json").write_text(
        '{"trade_id":"test","headline":"legacy lesson"}\n', encoding="utf-8"
    )
    (tmp_path / "qadam_paper_trade_lineage.jsonl").write_text(
        '{"trade_id":"test","paper_epoch_id":"legacy"}\n', encoding="utf-8"
    )
    result = archive_testing_epoch(testing_epoch_id="legacy-testing-epoch", settings=settings)
    assert (result.archive_dir / "manifest.json").is_file()
    assert (result.archive_dir / "checksums.json").is_file()
    assert research_artifact_was_archived(result) is False
    cleared = clear_archived_execution_artifacts(result, settings=settings)
    assert set(cleared) == {
        "paper_orders.jsonl",
        "paper_closed_trades.jsonl",
        "qadam_learning_cycle_dashboard.json",
        "qadam_paper_trade_lineage.jsonl",
    }
    assert not (tmp_path / "paper_orders.jsonl").exists()
    assert (result.archive_dir / "paper_orders.jsonl").is_file()


def test_paper_snapshot_emits_currency_native_fields_with_legacy_aliases() -> None:
    snapshot = PaperAccountSnapshot(
        schema_version=1,
        snapshot_id="snapshot",
        account_scope="paper",
        mode="paper",
        broker="alpaca_paper_readonly",
        connection_status="connected",
        starting_balance_gbp=100_000,
        current_balance_gbp=100_050,
        cash_gbp=95_000,
        equity_gbp=100_050,
        peak_equity_gbp=100_100,
        realized_pnl_gbp=50,
        unrealized_pnl_gbp=0,
        drawdown_pct=0.05,
        max_drawdown_pct=0.05,
        live_capital_enabled=False,
        write_authority=False,
        open_position_count=0,
        closed_trade_count=1,
        postmortem_due_count=1,
        postmortem_complete_count=0,
        maturity_closed_trade_target=100,
        maturity_closed_trade_count=1,
        timeline_status="current",
        observed_at="2026-07-18T12:00:00+00:00",
        boundary="read only",
        account_currency="USD",
        display_currency="USD",
        paper_epoch_id="paper-epoch-clean",
        paper_epoch_kind="clean_operator_epoch",
    )
    payload = snapshot.to_dict()
    assert payload["starting_balance"] == 100_000
    assert payload["current_balance"] == 100_050
    assert payload["account_currency"] == "USD"
    assert payload["paper_epoch_id"] == "paper-epoch-clean"
    assert payload["current_balance_gbp"] == 100_050
