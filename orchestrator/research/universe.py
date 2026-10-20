"""Research recipes from frozen identities and code, never dashboard prose."""

from orchestrator.qadam_operator_ready_common import read_json
from orchestrator.qadam_wave_b_common import STRATEGY_HYPOTHESES
from orchestrator.qsase_strategy_foundry import KNOWN_STRATEGY_FAMILIES


def research_universe(runtime):
    frozen = read_json(runtime / "qsase_backtest_universe_freeze.json")
    current = read_json(runtime / "qsase_trading_universe.json")
    latest = {row.get("symbol"): row for row in current.get("instruments", []) if isinstance(row, dict)}
    rows = []
    for family, recipe in KNOWN_STRATEGY_FAMILIES.items():
        markets = []
        for row in frozen.get("instruments", []):
            if not isinstance(row, dict) or family not in (row.get("strategy_family_ids") or []):
                continue
            markets.append({**row, **latest.get(row.get("symbol"), {})})
        rows.append({**recipe, "strategy_family_id": family,
                     "direction_hypothesis": STRATEGY_HYPOTHESES[family]["direction"],
                     "horizon_hypothesis": STRATEGY_HYPOTHESES[family]["horizon"],
                     "watched_markets": markets,
                     "paper_route_available_count": sum(row.get("paper_route_available") is True for row in markets)})
    return {"schema_version": "qadam-research-universe.1", "all_strategy_rows": rows,
            "identity_source": "qsase_backtest_universe_freeze.json",
            "definition_source": "reviewed_KNOWN_STRATEGY_FAMILIES",
            "dashboard_presence_used_as_evidence": False,
            "paper_order_allowed": False}
