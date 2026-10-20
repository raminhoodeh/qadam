import json
import sqlite3

from orchestrator.learning.coverage import attribution_coverage


def test_legacy_gross_results_are_not_pretended_to_be_net_strategy_results(tmp_path):
    with sqlite3.connect(tmp_path / "qadam-control-plane.sqlite3") as conn:
        conn.execute("CREATE TABLE outcomes (state TEXT,payload_json TEXT)")
        for row in [
            {"paper_epoch_id": "current", "accounting_status": "gross_reconstructed",
             "realized_pnl": 12, "attribution_status": "exact_entry_decision",
             "strategy_version": "strategy-version-unclassified", "net_return": None},
            {"paper_epoch_id": "old", "realized_pnl": 999},
        ]:
            conn.execute("INSERT INTO outcomes VALUES ('closed',?)", (json.dumps(row),))
    report = attribution_coverage(tmp_path, epoch_id="current")
    assert report["closed_broker_outcomes"] == 1
    assert report["reconstructed_gross_pnl"] == 12
    assert report["counts"]["missing_registered_strategy_version"] == 1
    assert report["counts"]["costed_lots"] == 0
    assert report["historical_gaps_block_new_discovery"] is False
