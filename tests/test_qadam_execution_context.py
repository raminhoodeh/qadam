from datetime import datetime, timedelta, timezone
from pathlib import Path

from orchestrator.config import Settings
from orchestrator.qadam_execution_context import build_execution_contexts
from orchestrator.qadam_operator_ready_common import write_json_atomic


def _settings(tmp_path: Path) -> Settings:
    base = Settings.from_env()
    return Settings(**{**base.__dict__, "runtime_dir": str(tmp_path), "state_root": str(tmp_path)})


def test_provider_backed_current_quote_is_actionable(tmp_path: Path) -> None:
    now = datetime(2026, 8, 19, 14, 30, tzinfo=timezone.utc)
    write_json_atomic(
        tmp_path / "qadam_instrument_role_registry.json",
        {"instruments": [{"symbol": "SPY", "guarded_paper_route_confirmed": True}]},
    )
    write_json_atomic(
        tmp_path / "market_context_packet.json",
        {
            "generated_at": now.isoformat(),
            "recent_packets": [
                {
                    "price_volume_context": {
                        "records": [
                            {
                                "symbol": "SPY",
                                "provider": "alpaca_paper_market_data",
                                "provider_backed": True,
                                "quote_actionable": True,
                                "session_state": "regular_session",
                                "quote_observed_at": (now - timedelta(seconds=10)).isoformat(),
                                "bid": 500.0,
                                "ask": 500.1,
                                "midpoint": 500.05,
                            }
                        ]
                    }
                }
            ],
        },
    )

    contexts, summary, errors = build_execution_contexts(
        _settings(tmp_path), timestamp=now
    )

    assert errors == []
    assert contexts[0]["status"] == "quote_ready"
    assert summary["quote_ready_count"] == 1
