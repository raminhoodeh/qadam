#!/usr/bin/env python3
"""Build and optionally submit one bounded operator exploratory paper basket."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.paperops_alpaca_paper_post import (  # noqa: E402
    submit_operator_exploratory_sleeve,
)
from orchestrator.qadam_operator_exploratory_sleeve import (  # noqa: E402
    build_operator_exploratory_sleeve,
)


REQUESTED_LEGS = (
    {
        "exposure": "silver_macro_liquidity",
        "requested_symbol": "SLV",
        "approved_execution_proxies": ["SIL"],
        "side": "buy",
        "allocation_usd": 1_500.0,
        "thesis": "Collect a forward paper outcome for Qadam's strongest current silver relationship.",
        "source_context": ["fred", "ecb", "usgs"],
    },
    {
        "exposure": "defence_geopolitical_repricing",
        "requested_symbol": "XAR",
        "approved_execution_proxies": ["ITA", "PPA"],
        "side": "buy",
        "allocation_usd": 1_250.0,
        "thesis": "Collect a forward paper outcome for the current defence repricing relationship.",
        "source_context": ["sec_edgar", "gdelt", "acled"],
    },
    {
        "exposure": "energy_security",
        "requested_symbol": "USO",
        "approved_execution_proxies": ["XLE", "BNO"],
        "side": "buy",
        "allocation_usd": 1_000.0,
        "thesis": "Observe whether the current energy sell-off mean-reverts under the energy-security research sleeve.",
        "source_context": ["acled", "ais_maritime", "eia"],
    },
    {
        "exposure": "semiconductor_policy",
        "requested_symbol": "SMH",
        "approved_execution_proxies": ["SOXX", "QQQ"],
        "side": "buy",
        "allocation_usd": 750.0,
        "thesis": "Collect a bounded forward outcome for semiconductor policy and innovation repricing.",
        "source_context": ["sec_edgar", "patents", "gdelt"],
    },
    {
        "exposure": "broad_equity_hedge",
        "requested_symbol": "SPY",
        "approved_execution_proxies": [],
        "side": "sell",
        "allocation_usd": 500.0,
        "thesis": "Partially offset broad equity beta while the exploratory long basket is open.",
        "source_context": ["alpaca_market_data", "fred"],
    },
)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--operator-approved", action="store_true")
    parser.add_argument("--execute-paper-orders", action="store_true")
    parser.add_argument(
        "--request-id",
        default="operator-request-2026-08-03-five-leg-exploratory-basket",
    )
    args = parser.parse_args()

    settings = Settings.from_env()
    runtime = Path(settings.runtime_dir)
    market_context = json.loads(
        (runtime / "market_context_packet.json").read_text(encoding="utf-8")
    )
    sleeve = build_operator_exploratory_sleeve(
        request_id=args.request_id,
        requested_legs=REQUESTED_LEGS,
        market_context_packet=market_context,
        explicit_operator_approval=args.operator_approved,
    )
    _write_json(runtime / "qadam_operator_exploratory_sleeve.json", sleeve)
    print(f"operator_exploratory_sleeve_status={sleeve.get('status')}")
    print(f"operator_exploratory_sleeve_leg_count={sleeve.get('leg_count')}")
    print(
        "operator_exploratory_sleeve_gross_notional_usd="
        f"{sleeve.get('gross_notional_usd')}"
    )
    print(
        "operator_exploratory_sleeve_validation_error_count="
        f"{len(sleeve.get('validation_errors', []))}"
    )
    for leg in sleeve.get("legs", []):
        print(
            "operator_exploratory_leg="
            f"{leg.get('sequence')}:{leg.get('execution_symbol')}:{leg.get('side')}:"
            f"{leg.get('quantity')}:{leg.get('estimated_notional_usd')}"
        )
    if sleeve.get("status") != "ready_for_guarded_paper_submission":
        return 1

    submission = submit_operator_exploratory_sleeve(
        settings=settings,
        sleeve=sleeve,
        execute_post=args.execute_paper_orders,
    )
    print(f"operator_exploratory_submission_status={submission.get('status')}")
    print(
        "operator_exploratory_submission_attempted_count="
        f"{submission.get('post_attempted_count')}"
    )
    print(
        "operator_exploratory_submission_succeeded_count="
        f"{submission.get('post_succeeded_count')}"
    )
    print(
        "operator_exploratory_submission_blockers="
        + ",".join(submission.get("blockers", []))
    )
    return 0 if submission.get("status") == "submitted_to_alpaca_paper" else 2


if __name__ == "__main__":
    raise SystemExit(main())
