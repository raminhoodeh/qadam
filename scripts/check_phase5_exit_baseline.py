#!/usr/bin/env python3
"""Validate the Q5E-0 Phase 5 exit-unblock baseline."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.phase5_alpaca_paper_dry_run import (  # noqa: E402
    ALPACA_PAPER_DRY_RUN_RUNTIME_ARTIFACT,
    validate_phase5_alpaca_paper_dry_run_bundle,
)
from orchestrator.phase5_certification import (  # noqa: E402
    PHASE5_CERTIFICATION_RUNTIME_ARTIFACT,
    validate_phase5_certification,
)
from orchestrator.phase5_execution_adapter_status import (  # noqa: E402
    EXECUTION_ADAPTER_RUNTIME_ARTIFACT,
    validate_phase5_execution_adapter_status_bundle,
)
from orchestrator.phase5_kill_switch import (  # noqa: E402
    KILL_SWITCH_RUNTIME_ARTIFACT,
    validate_phase5_kill_switch_ledger,
)
from orchestrator.phase5_paper_order_staging import (  # noqa: E402
    PAPER_ORDER_STAGING_RUNTIME_ARTIFACT,
    validate_phase5_paper_order_staging_bundle,
)
from orchestrator.phase5_paper_submit_enablement import (  # noqa: E402
    PAPER_SUBMIT_ENABLEMENT_RUNTIME_ARTIFACT,
    paper_submit_approval_path,
    validate_phase5_paper_submit_approval,
    validate_phase5_paper_submit_enablement_bundle,
)
from orchestrator.phase5_paper_trade_drill import (  # noqa: E402
    PAPER_TRADE_DRILL_RUNTIME_ARTIFACT,
    validate_phase5_paper_trade_drill_bundle,
)
from orchestrator.phase5_position_monitor import (  # noqa: E402
    POSITION_MONITOR_RUNTIME_ARTIFACT,
    validate_phase5_position_monitor_bundle,
)
from orchestrator.phase5_prediction_market_adapter import (  # noqa: E402
    PREDICTION_MARKET_ADAPTER_RUNTIME_ARTIFACT,
    validate_phase5_prediction_market_adapter_bundle,
)
from orchestrator.phase5_risk_sizing import (  # noqa: E402
    RISK_SIZING_RUNTIME_ARTIFACT,
    validate_phase5_risk_sizing_bundle,
)
from orchestrator.phase5_signal_review import (  # noqa: E402
    SIGNAL_REVIEW_RUNTIME_ARTIFACT,
    validate_phase5_signal_review_bundle,
)
from orchestrator.phase5_system_map import (  # noqa: E402
    SYSTEM_MAP_RUNTIME_ARTIFACT,
    validate_phase5_system_map_bundle,
)
from orchestrator.phase5_telegram_notifier import (  # noqa: E402
    TELEGRAM_NOTIFIER_RUNTIME_ARTIFACT,
    validate_phase5_telegram_notifier_bundle,
)


EXPECTED_DRILL_BLOCKERS = {
    "alpaca_dry_run_receipt_missing",
    "closed_trade_missing",
    "execution_adapter_not_staging_ready",
    "open_position_missing",
    "paper_order_submission_missing",
    "paper_submit_path_unavailable",
    "postmortem_due_missing",
    "risk_size_eligible_trade_missing",
    "staged_paper_order_missing",
    "submitted_order_not_mirrored",
}


def _runtime_dir(settings: Settings) -> Path:
    return Path(settings.runtime_dir)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _nonzero_errors(bundle: dict[str, Any], *, keys: tuple[str, ...], prefix: str) -> list[str]:
    errors: list[str] = []
    for key in keys:
        if int(bundle.get(key, 0) or 0) != 0:
            errors.append(f"{prefix}_{key}_nonzero")
    return errors


def main() -> int:
    settings = Settings.from_env()
    runtime_dir = _runtime_dir(settings)
    artifacts = {
        "risk": _read_json(runtime_dir / RISK_SIZING_RUNTIME_ARTIFACT),
        "kill_switch": _read_json(runtime_dir / KILL_SWITCH_RUNTIME_ARTIFACT),
        "execution_adapter": _read_json(runtime_dir / EXECUTION_ADAPTER_RUNTIME_ARTIFACT),
        "staging": _read_json(runtime_dir / PAPER_ORDER_STAGING_RUNTIME_ARTIFACT),
        "dry_run": _read_json(runtime_dir / ALPACA_PAPER_DRY_RUN_RUNTIME_ARTIFACT),
        "approval": _read_json(paper_submit_approval_path(settings)),
        "submit": _read_json(runtime_dir / PAPER_SUBMIT_ENABLEMENT_RUNTIME_ARTIFACT),
        "prediction": _read_json(runtime_dir / PREDICTION_MARKET_ADAPTER_RUNTIME_ARTIFACT),
        "telegram": _read_json(runtime_dir / TELEGRAM_NOTIFIER_RUNTIME_ARTIFACT),
        "position": _read_json(runtime_dir / POSITION_MONITOR_RUNTIME_ARTIFACT),
        "signal_review": _read_json(runtime_dir / SIGNAL_REVIEW_RUNTIME_ARTIFACT),
        "system_map": _read_json(runtime_dir / SYSTEM_MAP_RUNTIME_ARTIFACT),
        "drill": _read_json(runtime_dir / PAPER_TRADE_DRILL_RUNTIME_ARTIFACT),
        "certification": _read_json(runtime_dir / PHASE5_CERTIFICATION_RUNTIME_ARTIFACT),
    }

    validation_errors = {
        "risk": validate_phase5_risk_sizing_bundle(artifacts["risk"]),
        "kill_switch": validate_phase5_kill_switch_ledger(artifacts["kill_switch"]),
        "execution_adapter": validate_phase5_execution_adapter_status_bundle(
            artifacts["execution_adapter"]
        ),
        "staging": validate_phase5_paper_order_staging_bundle(artifacts["staging"]),
        "dry_run": validate_phase5_alpaca_paper_dry_run_bundle(artifacts["dry_run"]),
        "approval": validate_phase5_paper_submit_approval(artifacts["approval"]),
        "submit": validate_phase5_paper_submit_enablement_bundle(artifacts["submit"]),
        "prediction": validate_phase5_prediction_market_adapter_bundle(artifacts["prediction"]),
        "telegram": validate_phase5_telegram_notifier_bundle(artifacts["telegram"]),
        "position": validate_phase5_position_monitor_bundle(artifacts["position"]),
        "signal_review": validate_phase5_signal_review_bundle(artifacts["signal_review"]),
        "system_map": validate_phase5_system_map_bundle(artifacts["system_map"]),
        "drill": validate_phase5_paper_trade_drill_bundle(artifacts["drill"]),
        "certification": validate_phase5_certification(artifacts["certification"]),
    }
    errors = [
        f"{key}_validation_errors:{','.join(value)}"
        for key, value in validation_errors.items()
        if value
    ]

    risk = artifacts["risk"]
    staging = artifacts["staging"]
    dry_run = artifacts["dry_run"]
    approval = artifacts["approval"]
    submit = artifacts["submit"]
    prediction = artifacts["prediction"]
    telegram = artifacts["telegram"]
    position = artifacts["position"]
    signal_review = artifacts["signal_review"]
    system_map = artifacts["system_map"]
    drill = artifacts["drill"]
    certification = artifacts["certification"]

    if risk.get("paper_size_eligible_count") != 0:
        errors.append("risk_paper_size_eligible_count_not_zero")
    if staging.get("staged_order_count") != 0:
        errors.append("staging_staged_order_count_not_zero")
    if dry_run.get("request_preview_count") != 0:
        errors.append("dry_run_request_preview_count_not_zero")
    if dry_run.get("dry_run_receipt_count") != 0:
        errors.append("dry_run_receipt_count_not_zero")
    if approval.get("approval_state") != "approved" or approval.get("approval_logged") is not True:
        errors.append("paper_submit_approval_not_logged")
    if submit.get("paper_submit_approval_present") is not True:
        errors.append("submit_approval_not_present")
    if submit.get("submit_path_available_count") != 0:
        errors.append("submit_path_available_before_q5e_1")
    if drill.get("paper_submit_approval_present") is not True:
        errors.append("drill_approval_not_present")
    if set(drill.get("blockers", [])) != EXPECTED_DRILL_BLOCKERS:
        errors.append("drill_blocker_set_mismatch")
    if drill.get("phase5_paper_trade_drill_exit_gate_passed") is not False:
        errors.append("drill_exit_gate_not_blocked")
    if drill.get("paper_trade_drill_complete") is not False:
        errors.append("drill_unexpectedly_complete")
    if certification.get("phase5_certified") is not False:
        errors.append("certification_unexpectedly_certified")
    if certification.get("phase6_handoff_allowed") is not False:
        errors.append("phase6_handoff_unexpectedly_allowed")
    if certification.get("phase7_proof_credit_allowed") is not False:
        errors.append("phase7_proof_credit_unexpectedly_allowed")
    if system_map.get("unsafe_control_count") != 0:
        errors.append("system_map_unsafe_control_count_not_zero")
    if system_map.get("guardrails", {}).get("dashboard_claims_trading_now") is not False:
        errors.append("system_map_claims_trading_now")

    for key, bundle in (
        ("risk", risk),
        ("staging", staging),
        ("dry_run", dry_run),
        ("submit", submit),
        ("prediction", prediction),
        ("telegram", telegram),
        ("position", position),
        ("signal_review", signal_review),
        ("certification", certification),
    ):
        errors.extend(
            _nonzero_errors(
                bundle,
                keys=(
                    "broker_write_allowed_count",
                    "broker_post_called_count",
                    "alpaca_post_called_count",
                    "paper_order_submitted_count",
                    "prediction_market_write_allowed_count",
                    "live_endpoint_allowed_count",
                    "live_capital_enabled_count",
                ),
                prefix=key,
            )
        )

    print(f"phase5_exit_baseline_risk_paper_size_eligible_count={risk['paper_size_eligible_count']}")
    print(f"phase5_exit_baseline_staged_order_count={staging['staged_order_count']}")
    print(f"phase5_exit_baseline_request_preview_count={dry_run['request_preview_count']}")
    print(f"phase5_exit_baseline_dry_run_receipt_count={dry_run['dry_run_receipt_count']}")
    print(f"phase5_exit_baseline_paper_submit_approval_state={approval['approval_state']}")
    print(f"phase5_exit_baseline_paper_submit_approval_logged={approval['approval_logged']}")
    print(f"phase5_exit_baseline_submit_path_available_count={submit['submit_path_available_count']}")
    print(f"phase5_exit_baseline_submitted_order_count={position['submitted_order_count']}")
    print(f"phase5_exit_baseline_open_position_count={position['open_position_count']}")
    print(f"phase5_exit_baseline_closed_trade_count={position['closed_trade_count']}")
    print(f"phase5_exit_baseline_postmortem_due_count={position['postmortem_due_count']}")
    print(f"phase5_exit_baseline_drill_state={drill['paper_trade_drill_state']}")
    print(f"phase5_exit_baseline_drill_blocker_count={drill['blocker_count']}")
    print(
        "phase5_exit_baseline_drill_exit_gate_passed="
        f"{drill['phase5_paper_trade_drill_exit_gate_passed']}"
    )
    print(f"phase5_exit_baseline_phase5_certified={certification['phase5_certified']}")
    print(f"phase5_exit_baseline_phase6_handoff_allowed={certification['phase6_handoff_allowed']}")
    print(f"phase5_exit_baseline_phase7_proof_credit_allowed={certification['phase7_proof_credit_allowed']}")
    print(f"phase5_exit_baseline_validation_error_group_count={len([v for v in validation_errors.values() if v])}")
    print("phase5_exit_baseline_remaining_blockers=" + ",".join(drill["blockers"]))

    if errors:
        for error in sorted(set(errors)):
            print(f"phase5_exit_baseline_error={error}")
        print("phase5_exit_baseline_check=failed")
        return 1

    print("phase5_exit_baseline_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
