"""Paper-only operational readiness gate.

This gate defines the target the user asked for: Qadam should behave like the
full autonomous system while remaining restricted to paper trading. It does not
place orders. It records whether the runtime is ready to advance toward a
paper-only operational loop and highlights the remaining blockers.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog


PAPER_OPS_SCHEMA_VERSION = 1
PAPER_OPS_RUNTIME_ARTIFACT = "paper_operational_readiness.json"
PAPER_OPS_HISTORY = "paper_operational_readiness_history.jsonl"
PAPER_OPS_EVENT_LOG = "paper_operational_readiness_events.jsonl"
PAPER_OPS_EVENT_TYPE = "paper_operational_readiness_recorded"
PAPER_OPS_COMPONENT = "paper_operational_readiness"

PAPER_OPS_BOUNDARY = (
    "PaperOps is the paper-only operating target. It may run the full Qadam "
    "decision, Head-of-Quant/Q-CTRL consultation, staging, Alpaca paper-submit, "
    "lifecycle, notification, and postmortem loop only in paper mode. It cannot "
    "load live credentials, cannot call live endpoints, cannot write "
    "prediction-market or crypto-perps orders, cannot enable live capital, "
    "cannot let Telegram approve trades, and cannot promote the system to live "
    "money."
)

TARGET_CAPABILITIES: tuple[tuple[str, str], ...] = (
    ("paper_mode_enforced", "QADAM_MODE must be paper and live capital must stay false."),
    (
        "paper_live_activation_approved",
        "Fund Manager approval must explicitly authorize system-level paper-live operation.",
    ),
    ("strategy_research_intake_connected", "External strategy notes must be structured as decision context."),
    ("phase7_run_active", "The 30-day demo-proof run ledger must be active."),
    ("source_spine_available", "Durable replay and current source status must be readable."),
    ("head_of_quant_oracle_connected", "The Head of Quant oracle must produce paper-run evidence."),
    (
        "qctrl_paper_consultation_connected",
        "Q-CTRL consultation must be implemented for full paper-reality parity.",
    ),
    ("qualified_setup_gate_connected", "Qualified setups must flow into Q7, even when count is zero."),
    ("auto_approval_connected", "Qualified setups must pass auto-approval without manual trade-level approval."),
    ("paper_order_staging_connected", "Auto-approved setups must become staged proof paper orders."),
    ("alpaca_paper_submit_connected", "Eligible staged proof orders must be able to submit to Alpaca paper only."),
    (
        "paper_lifecycle_poller_connected",
        "PaperOps-2 submitted paper orders must have read-only broker lifecycle readback.",
    ),
    (
        "paper_exit_path_connected",
        "Open paper positions must have a guarded paper-only exit path.",
    ),
    ("paper_lifecycle_connected", "Submitted paper orders must mirror into lifecycle, exits, and closed proof trades."),
    (
        "paperops_notification_review_connected",
        "Paper lifecycle notifications must be review-only and command-disabled.",
    ),
    (
        "paperops_30_day_operations_active",
        "The hourly PaperOps runner must be bound to the active 30-day paper window.",
    ),
    ("telegram_notify_only_connected", "Telegram may notify members but cannot approve or place trades."),
    ("learning_loop_review_only", "Learning/postmortems may review outcomes without mutating policy silently."),
    ("live_promotion_blocked", "Live promotion must remain blocked until post-proof review."),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _bool(value: Any) -> bool:
    return value is True or str(value).strip().lower() in {"1", "true", "yes", "on"}


def paper_operational_readiness_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PAPER_OPS_RUNTIME_ARTIFACT,
        runtime / PAPER_OPS_HISTORY,
        runtime / PAPER_OPS_EVENT_LOG,
    )


def _runtime_snapshot(settings: Settings) -> dict[str, dict[str, Any]]:
    runtime = _runtime_dir(settings)
    try:
        from orchestrator.quantum import qctrl_readiness, quantum_oracle_summary
        from orchestrator.paperops_qctrl_consultation import (
            read_latest_paperops_qctrl_consultation,
        )

        qctrl = qctrl_readiness(settings)
        quantum_summary = quantum_oracle_summary(settings)
        qctrl_consultation = read_latest_paperops_qctrl_consultation(settings)
    except Exception as exc:  # noqa: BLE001 - readiness should report the failure.
        qctrl = {"status": "error", "error": str(exc)}
        quantum_summary = {"status": "error", "error": str(exc)}
        qctrl_consultation = {"status": "error", "error": str(exc)}
    try:
        from orchestrator.strategy_research_intake import build_strategy_research_intake

        strategy_research = build_strategy_research_intake(settings)
    except Exception as exc:  # noqa: BLE001 - readiness should report the failure.
        strategy_research = {"status": "error", "error": str(exc)}
    return {
        "cockpit": _read_json(runtime / "cockpit-status.json"),
        "paper_live_activation": _read_json(runtime / "paper_live_activation.json"),
        "strategy_research": strategy_research,
        "demo_run": _read_json(runtime / "phase7_demo_proof_run.json"),
        "qualified_setup": _read_json(runtime / "phase7_qualified_setup_ledger.json"),
        "auto_approval": _read_json(runtime / "phase7_test_mode_auto_approval_router.json"),
        "staging": _read_json(runtime / "phase7_proof_order_staging.json"),
        "submit": _read_json(runtime / "phase7_guarded_alpaca_paper_submit_path.json"),
        "alpaca_paper_post": _read_json(runtime / "paperops_alpaca_paper_post.json"),
        "paper_lifecycle_poller": _read_json(
            runtime / "paperops_paper_lifecycle_poller.json"
        ),
        "paper_exit_path": _read_json(runtime / "paperops_paper_exit_path.json"),
        "notification_review": _read_json(runtime / "paperops_notification_review.json"),
        "paperops_30_day_operations": _read_json(runtime / "paperops_30_day_operations.json"),
        "lifecycle": _read_json(runtime / "phase7_proof_lifecycle_monitor.json"),
        "telegram": _read_json(runtime / "phase5_telegram_notifier.json"),
        "learning": _read_json(runtime / "phase6_certification.json"),
        "certification": _read_json(runtime / "phase7_certification.json"),
        "live_promotion": _read_json(runtime / "phase7_live_promotion_review.json"),
        "qctrl": qctrl,
        "qctrl_consultation": qctrl_consultation,
        "quantum_summary": quantum_summary,
    }


def _capability_records(settings: Settings, snapshot: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    cockpit = snapshot["cockpit"]
    mission = cockpit.get("mission_control", {}) if isinstance(cockpit, dict) else {}
    durable = mission.get("durable_spine", {}) if isinstance(mission, dict) else {}
    portfolio = mission.get("portfolio", {}) if isinstance(mission, dict) else {}
    paper_live_activation = snapshot["paper_live_activation"]
    demo_run = snapshot["demo_run"]
    setup = snapshot["qualified_setup"]
    auto = snapshot["auto_approval"]
    staging = snapshot["staging"]
    submit = snapshot["submit"]
    alpaca_paper_post = snapshot["alpaca_paper_post"]
    paper_lifecycle_poller = snapshot["paper_lifecycle_poller"]
    paper_exit_path = snapshot["paper_exit_path"]
    notification_review = snapshot["notification_review"]
    paperops_30_day_operations = snapshot["paperops_30_day_operations"]
    lifecycle = snapshot["lifecycle"]
    telegram = snapshot["telegram"]
    learning = snapshot["learning"]
    live_promotion = snapshot["live_promotion"]
    qctrl = snapshot["qctrl"]
    qctrl_consultation = snapshot["qctrl_consultation"]
    quantum_summary = snapshot["quantum_summary"]
    strategy_research = snapshot["strategy_research"]
    paper_live_activation_ready = (
        paper_live_activation.get("status") == "approved_pending_later_enablement"
        and paper_live_activation.get("approval_state") == "approved"
        and paper_live_activation.get("approval_logged") is True
        and paper_live_activation.get("paper_live_activation_approved") is True
        and paper_live_activation.get("paper_trading_system_approval_logged") is True
        and paper_live_activation.get("paper_live_mode") == "alpaca_paper_only"
        and paper_live_activation.get("live_capital_enabled") is False
        and paper_live_activation.get("live_endpoint_allowed") is False
        and paper_live_activation.get("paper_order_submission_allowed") is False
        and paper_live_activation.get("phase7_proof_credit_allowed") is False
        and paper_live_activation.get("forced_trades_allowed") is False
        and paper_live_activation.get("qctrl_consultation_required") is True
        and _int(paper_live_activation.get("broker_post_called_count")) == 0
        and _int(paper_live_activation.get("alpaca_post_called_count")) == 0
        and _int(paper_live_activation.get("live_endpoint_called_count")) == 0
    )
    qctrl_consultation_ready = (
        settings.qctrl_paper_consultation_enabled
        and qctrl_consultation.get("status") == "consultation_recorded"
        and qctrl_consultation.get("provider_call_recorded") is True
        and _int(qctrl_consultation.get("provider_call_count")) > 0
        and qctrl_consultation.get("paper_order_allowed") is False
        and qctrl_consultation.get("execution_allowed") is False
        and qctrl_consultation.get("broker_post_allowed") is False
    )
    alpaca_paper_post_ready = (
        settings.alpaca_paper_submit_enabled
        and alpaca_paper_post.get("paper_post_path_available") is True
        and alpaca_paper_post.get("endpoint_classification") == "alpaca_paper_endpoint"
        and alpaca_paper_post.get("paper_endpoint_confirmed") is True
        and alpaca_paper_post.get("live_endpoint_allowed") is False
        and alpaca_paper_post.get("live_capital_enabled") is False
        and _int(alpaca_paper_post.get("live_endpoint_called_count")) == 0
        and _int(alpaca_paper_post.get("unsafe_live_endpoint_called_count")) == 0
        and alpaca_paper_post.get("status")
        in {
            "ready_no_eligible_order",
            "ready_pending_explicit_execute",
            "submitted_to_alpaca_paper",
        }
    )
    paper_lifecycle_poller_ready = (
        paper_lifecycle_poller.get("status")
        in {
            "ready_no_submitted_paper_orders",
            "ready_pending_explicit_poll",
            "paper_lifecycle_poll_recorded",
        }
        and paper_lifecycle_poller.get("live_capital_enabled") is False
        and _int(paper_lifecycle_poller.get("live_endpoint_called_count")) == 0
        and _int(paper_lifecycle_poller.get("broker_post_called_count")) == 0
        and _int(paper_lifecycle_poller.get("alpaca_post_called_count")) == 0
        and paper_lifecycle_poller.get("phase7_proof_credit_allowed") is False
        and paper_lifecycle_poller.get("q7_lifecycle_mutation_performed") is False
    )
    paper_exit_path_ready = (
        settings.alpaca_paper_exit_enabled
        and paper_exit_path.get("status")
        in {
            "ready_no_exit_candidate",
            "ready_pending_explicit_execute",
            "paper_exit_close_recorded",
        }
        and paper_exit_path.get("live_capital_enabled") is False
        and _int(paper_exit_path.get("live_endpoint_called_count")) == 0
        and _int(paper_exit_path.get("broker_post_called_count")) == 0
        and _int(paper_exit_path.get("alpaca_post_called_count")) == 0
        and _int(paper_exit_path.get("order_cancel_called_count")) == 0
        and _int(paper_exit_path.get("position_resize_called_count")) == 0
        and paper_exit_path.get("phase7_proof_credit_allowed") is False
        and paper_exit_path.get("q7_lifecycle_mutation_performed") is False
    )
    notification_review_ready = (
        notification_review.get("status") == "review_ready"
        and notification_review.get("event_log_written") is True
        and len(notification_review.get("validation_errors", []) or []) == 0
        and _int(notification_review.get("notification_record_count")) >= 7
        and _int(notification_review.get("live_send_allowed_count")) == 0
        and _int(notification_review.get("telegram_command_path_enabled_count")) == 0
        and _int(notification_review.get("broker_write_allowed_count")) == 0
        and _int(notification_review.get("paper_order_allowed_count")) == 0
        and _int(notification_review.get("position_close_allowed_count")) == 0
        and _int(notification_review.get("position_resize_allowed_count")) == 0
        and _int(notification_review.get("live_endpoint_allowed_count")) == 0
        and notification_review.get("normal_live_notification_allowed") is False
        and notification_review.get("live_capital_enabled") is False
        and notification_review.get("phase7_proof_credit_allowed") is False
    )
    paperops_30_day_operations_ready = (
        paperops_30_day_operations.get("status")
        in {"operations_active", "operations_complete_pending_certification"}
        and paperops_30_day_operations.get("event_log_written") is True
        and len(paperops_30_day_operations.get("validation_errors", []) or []) == 0
        and paperops_30_day_operations.get("automation_active") is True
        and paperops_30_day_operations.get("automation_hourly") is True
        and paperops_30_day_operations.get("automation_prompt_paperops_bound") is True
        and paperops_30_day_operations.get("actual_calendar_run") is True
        and paperops_30_day_operations.get("backfill_used") is False
        and paperops_30_day_operations.get("simulated_time_used") is False
        and paperops_30_day_operations.get("no_forced_trades") is True
        and paperops_30_day_operations.get("dashboard_mirror_public_safe") is True
        and _int(paperops_30_day_operations.get("unsafe_write_counter_total")) == 0
        and paperops_30_day_operations.get("live_capital_enabled") is False
        and paperops_30_day_operations.get("phase7_proof_credit_allowed") is False
    )

    return [
        {
            "key": "paper_mode_enforced",
            "ready": settings.mode == "paper" and not settings.live_capital_enabled,
            "status": "ready" if settings.mode == "paper" and not settings.live_capital_enabled else "blocked",
            "detail": f"mode={settings.mode}; live_capital_enabled={settings.live_capital_enabled}",
            "required_for_full_paper_ops": True,
        },
        {
            "key": "paper_live_activation_approved",
            "ready": paper_live_activation_ready,
            "status": str(paper_live_activation.get("status") or "missing"),
            "detail": (
                f"approval={paper_live_activation.get('approval_state')}; "
                f"logged={paper_live_activation.get('paper_trading_system_approval_logged')}; "
                f"submit_allowed={paper_live_activation.get('paper_order_submission_allowed')}; "
                f"qctrl_required={paper_live_activation.get('qctrl_consultation_required')}"
            ),
            "required_for_full_paper_ops": True,
        },
        {
            "key": "strategy_research_intake_connected",
            "ready": strategy_research.get("status") == "ready_for_strategy_review"
            and _int(strategy_research.get("candidate_count")) == 4
            and strategy_research.get("trade_candidate_creation_allowed") is False
            and strategy_research.get("execution_allowed") is False,
            "status": str(strategy_research.get("status") or "missing"),
            "detail": (
                f"candidates={_int(strategy_research.get('candidate_count'))}; "
                f"source_note={strategy_research.get('source_note_exists')}; "
                f"trade_authority={strategy_research.get('trade_candidate_creation_allowed')}"
            ),
            "required_for_full_paper_ops": True,
        },
        {
            "key": "phase7_run_active",
            "ready": demo_run.get("run_state") == "active",
            "status": str(demo_run.get("run_state") or "missing"),
            "detail": f"run_id={demo_run.get('run_id')}; active_day={demo_run.get('active_day_number')}",
            "required_for_full_paper_ops": True,
        },
        {
            "key": "source_spine_available",
            "ready": durable.get("status") == "ok" or durable.get("replay_status") == "ok",
            "status": str(durable.get("status") or durable.get("replay_status") or "missing"),
            "detail": (
                f"replayed={durable.get('replayed_source_count')}/"
                f"{durable.get('expected_source_count')}"
            ),
            "required_for_full_paper_ops": True,
        },
        {
            "key": "head_of_quant_oracle_connected",
            "ready": quantum_summary.get("status") in {"ok", "ready_classical_fallback"}
            and _int(quantum_summary.get("result_count")) > 0
            and quantum_summary.get("latest_output_route_type") == "shadow_annotation",
            "status": str(quantum_summary.get("status") or "missing"),
            "detail": (
                f"backend={quantum_summary.get('latest_backend')}; "
                f"results={_int(quantum_summary.get('result_count'))}; "
                f"route={quantum_summary.get('latest_output_route_type')}"
            ),
            "required_for_full_paper_ops": True,
        },
        {
            "key": "qctrl_paper_consultation_connected",
            "ready": (not settings.quantum_paper_parity_required) or qctrl_consultation_ready,
            "status": (
                "ready"
                if qctrl_consultation_ready
                else str(qctrl.get("status") or "missing")
            ),
            "detail": (
                f"required={settings.quantum_paper_parity_required}; "
                f"enabled={settings.qctrl_paper_consultation_enabled}; "
                f"credential={qctrl.get('credential_configured')}; "
                f"sdk={qctrl.get('sdk_package_importable')}; "
                f"consultation_status={qctrl_consultation.get('status', 'missing')}; "
                f"provider_calls={_int(qctrl_consultation.get('provider_call_count'))}"
            ),
            "required_for_full_paper_ops": settings.quantum_paper_parity_required,
        },
        {
            "key": "paper_broker_read_connected",
            "ready": str(portfolio.get("connection_status") or "").startswith("alpaca_paper"),
            "status": str(portfolio.get("connection_status") or "missing"),
            "detail": "Alpaca paper mirror must stay read/paper scoped.",
            "required_for_full_paper_ops": True,
        },
        {
            "key": "qualified_setup_gate_connected",
            "ready": setup.get("recorded") is True and _int(setup.get("validation_error_count")) == 0,
            "status": str(setup.get("status") or "missing"),
            "detail": f"qualified_setup_count={_int(setup.get('qualified_setup_count'))}",
            "required_for_full_paper_ops": True,
        },
        {
            "key": "auto_approval_connected",
            "ready": auto.get("recorded") is True and auto.get("phase7_test_mode_auto_approval_allowed") is True,
            "status": str(auto.get("status") or "missing"),
            "detail": f"auto_approved_setup_count={_int(auto.get('auto_approved_setup_count'))}",
            "required_for_full_paper_ops": True,
        },
        {
            "key": "paper_order_staging_connected",
            "ready": staging.get("phase7_proof_order_staging_allowed") is True,
            "status": str(staging.get("status") or "missing"),
            "detail": f"staged_order_count={_int(staging.get('staged_order_count'))}",
            "required_for_full_paper_ops": True,
        },
        {
            "key": "alpaca_paper_submit_contract_connected",
            "ready": submit.get("phase7_proof_trade_submission_allowed") is True,
            "status": str(submit.get("status") or "missing"),
            "detail": (
                f"path_available={submit.get('submit_path_available', submit.get('path_available'))}; "
                f"submitted={_int(submit.get('submitted_paper_order_count'))}"
            ),
            "required_for_full_paper_ops": True,
        },
        {
            "key": "external_alpaca_paper_post_enabled",
            "ready": alpaca_paper_post_ready,
            "status": str(alpaca_paper_post.get("status") or "missing"),
            "detail": (
                f"enabled={settings.alpaca_paper_submit_enabled}; "
                f"path_available={alpaca_paper_post.get('paper_post_path_available')}; "
                f"eligible={_int(alpaca_paper_post.get('eligible_submit_record_count'))}; "
                f"paper_posts={_int(alpaca_paper_post.get('alpaca_paper_post_called_count'))}"
            ),
            "required_for_full_paper_ops": True,
        },
        {
            "key": "paper_lifecycle_poller_connected",
            "ready": paper_lifecycle_poller_ready,
            "status": str(paper_lifecycle_poller.get("status") or "missing"),
            "detail": (
                f"submitted_sources="
                f"{_int(paper_lifecycle_poller.get('source_submitted_paper_order_count'))}; "
                f"order_gets={_int(paper_lifecycle_poller.get('paper_order_poll_called_count'))}; "
                f"live_gets={_int(paper_lifecycle_poller.get('live_endpoint_called_count'))}"
            ),
            "required_for_full_paper_ops": True,
        },
        {
            "key": "paper_exit_path_connected",
            "ready": paper_exit_path_ready,
            "status": str(paper_exit_path.get("status") or "missing"),
            "detail": (
                f"enabled={settings.alpaca_paper_exit_enabled}; "
                f"open_readbacks={_int(paper_exit_path.get('open_position_readback_count'))}; "
                f"close_calls={_int(paper_exit_path.get('paper_position_close_called_count'))}"
            ),
            "required_for_full_paper_ops": True,
        },
        {
            "key": "paper_lifecycle_connected",
            "ready": lifecycle.get("phase7_proof_lifecycle_write_allowed") is True
            or lifecycle.get("proof_lifecycle_write_allowed") is True,
            "status": str(lifecycle.get("status") or "missing"),
            "detail": f"closed_proof_trade_count={_int(lifecycle.get('closed_proof_trade_count'))}",
            "required_for_full_paper_ops": True,
        },
        {
            "key": "paperops_notification_review_connected",
            "ready": notification_review_ready,
            "status": str(notification_review.get("status") or "missing"),
            "detail": (
                f"records={_int(notification_review.get('notification_record_count'))}; "
                f"live_sends={_int(notification_review.get('live_send_allowed_count'))}; "
                f"commands={_int(notification_review.get('telegram_command_path_enabled_count'))}"
            ),
            "required_for_full_paper_ops": True,
        },
        {
            "key": "paperops_30_day_operations_active",
            "ready": paperops_30_day_operations_ready,
            "status": str(paperops_30_day_operations.get("status") or "missing"),
            "detail": (
                f"scheduler={paperops_30_day_operations.get('scheduler_status')}; "
                f"day={paperops_30_day_operations.get('active_day_number')}; "
                f"cycle={paperops_30_day_operations.get('paper_operational_cycle_status')}"
            ),
            "required_for_full_paper_ops": True,
        },
        {
            "key": "telegram_notify_only_connected",
            "ready": telegram.get("command_path_enabled_count", 0) == 0,
            "status": str(telegram.get("mode") or telegram.get("status") or "missing"),
            "detail": (
                f"live_send_allowed_count={_int(telegram.get('live_send_allowed_count'))}; "
                f"send_gate={telegram.get('send_gate')}"
            ),
            "required_for_full_paper_ops": False,
        },
        {
            "key": "learning_loop_review_only",
            "ready": learning.get("phase6_certified") is True
            and learning.get("phase6_learning_write_allowed") is False,
            "status": str(learning.get("status") or "missing"),
            "detail": "Phase 6 can review/defer learning; silent mutation remains blocked.",
            "required_for_full_paper_ops": True,
        },
        {
            "key": "live_promotion_blocked",
            "ready": live_promotion.get("live_capital_enabled") is False
            or live_promotion.get("live_promotion_live_capital_enabled") is False,
            "status": str(live_promotion.get("status") or "missing"),
            "detail": "Live promotion must not be active during PaperOps.",
            "required_for_full_paper_ops": True,
        },
    ]


def _blockers(settings: Settings, capabilities: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    if not settings.paper_operational_enabled:
        blockers.append("paper_operational_flag_disabled")
    for capability in capabilities:
        if capability["required_for_full_paper_ops"] and not capability["ready"]:
            blockers.append(f"{capability['key']}_not_ready")
    return blockers


def _recommended_next_stage(safe_to_continue: bool, blockers: list[str]) -> str:
    if not safe_to_continue:
        return "Restore paper-only safety before continuing"
    if "paper_live_activation_approved_not_ready" in blockers:
        return "Run PT-0 paper-live activation charter"
    if "paperops_30_day_operations_active_not_ready" in blockers:
        return "Run PaperOps-6 30-day paper operations scheduler binding"
    if "qctrl_paper_consultation_connected_not_ready" in blockers:
        return "Resolve PaperOps-Q Q-CTRL product access for successful paper consultation"
    if "external_alpaca_paper_post_enabled_not_ready" in blockers:
        return "Enable PaperOps-2 after eligible Q7 staged proof order and explicit paper-submit review"
    if "paper_lifecycle_poller_connected_not_ready" in blockers:
        return "Run PaperOps-3 paper lifecycle poller after PaperOps-2 has a submitted paper order"
    if "paper_exit_path_connected_not_ready" in blockers:
        return "Enable PaperOps-4 guarded paper exit path after open-position readback exists"
    if "paper_operational_flag_disabled" in blockers:
        return "PaperOps full-mode enablement review"
    return "Run PaperOps-1 operational cycle"


def build_paper_operational_readiness(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    snapshot = _runtime_snapshot(settings)
    capabilities = _capability_records(settings, snapshot)
    blockers = _blockers(settings, capabilities)
    hard_safety_failures = [
        blocker
        for blocker in blockers
        if blocker
        in {
            "paper_mode_enforced_not_ready",
            "live_promotion_blocked_not_ready",
        }
    ]
    ready = not blockers
    safe_to_continue = not hard_safety_failures
    target_count = len(TARGET_CAPABILITIES)
    ready_count = sum(1 for capability in capabilities if capability["ready"])
    demo_run = snapshot["demo_run"]
    submit = snapshot["submit"]
    alpaca_paper_post = snapshot["alpaca_paper_post"]
    paper_lifecycle_poller = snapshot["paper_lifecycle_poller"]
    paper_exit_path = snapshot["paper_exit_path"]
    notification_review = snapshot["notification_review"]
    paperops_30_day_operations = snapshot["paperops_30_day_operations"]
    strategy_research = snapshot["strategy_research"]
    paper_live_activation = snapshot["paper_live_activation"]

    artifact = {
        "schema_version": PAPER_OPS_SCHEMA_VERSION,
        "artifact_type": "paper_operational_readiness",
        "artifact_id": "paperops:readiness:paper-only",
        "phase": "PaperOps",
        "stage": "PaperOps-0",
        "status": "ready_for_full_paper_ops" if ready else "blocked_pending_paper_ops",
        "generated_at": _now(),
        "public_safe": True,
        "recorded": False,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_event_count": 0,
        "runtime_artifact_path": None,
        "history_log_path": None,
        "mode": settings.mode,
        "paper_operational_enabled": settings.paper_operational_enabled,
        "alpaca_paper_submit_enabled": settings.alpaca_paper_submit_enabled,
        "alpaca_paper_exit_enabled": settings.alpaca_paper_exit_enabled,
        "paper_operational_max_notional_gbp": settings.paper_operational_max_notional_gbp,
        "live_capital_enabled": settings.live_capital_enabled,
        "paper_live_activation_status": paper_live_activation.get("status", "missing"),
        "paper_live_activation_approval_state": paper_live_activation.get(
            "approval_state",
            "missing",
        ),
        "paper_live_activation_approval_logged": (
            paper_live_activation.get("approval_logged") is True
        ),
        "paper_live_activation_approved": (
            paper_live_activation.get("paper_live_activation_approved") is True
        ),
        "paper_trading_system_approval_logged": (
            paper_live_activation.get("paper_trading_system_approval_logged") is True
        ),
        "paper_live_activation_mode": paper_live_activation.get("paper_live_mode", "missing"),
        "paper_live_activation_per_trade_manual_approval_required": (
            paper_live_activation.get("per_trade_manual_approval_required") is True
        ),
        "paper_live_activation_paper_order_submission_allowed": (
            paper_live_activation.get("paper_order_submission_allowed") is True
        ),
        "paper_live_activation_forced_trades_allowed": (
            paper_live_activation.get("forced_trades_allowed") is True
        ),
        "paper_live_activation_qctrl_consultation_required": (
            paper_live_activation.get("qctrl_consultation_required") is True
        ),
        "paper_live_activation_qctrl_execution_allowed": (
            paper_live_activation.get("qctrl_direct_execution_allowed") is True
        ),
        "paper_live_activation_qctrl_broker_post_allowed": (
            paper_live_activation.get("qctrl_broker_post_allowed") is True
        ),
        "paper_live_activation_phase7_proof_credit_allowed": (
            paper_live_activation.get("phase7_proof_credit_allowed") is True
        ),
        "paper_live_activation_max_order_notional_gbp": _int(
            paper_live_activation.get("max_order_notional_gbp")
        ),
        "paper_live_activation_daily_trade_cap": _int(
            paper_live_activation.get("daily_trade_cap")
        ),
        "paper_live_activation_broker_post_called_count": _int(
            paper_live_activation.get("broker_post_called_count")
        ),
        "paper_live_activation_alpaca_post_called_count": _int(
            paper_live_activation.get("alpaca_post_called_count")
        ),
        "paper_live_activation_live_endpoint_called_count": _int(
            paper_live_activation.get("live_endpoint_called_count")
        ),
        "quantum_paper_parity_required": settings.quantum_paper_parity_required,
        "qctrl_paper_consultation_enabled": settings.qctrl_paper_consultation_enabled,
        "qctrl_paper_consultation_required_for_full_parity": settings.quantum_paper_parity_required,
        "safe_to_continue_paper_only": safe_to_continue,
        "full_paper_operational_ready": ready,
        "target_capability_count": target_count,
        "ready_capability_count": ready_count,
        "required_capability_count": sum(
            1 for capability in capabilities if capability["required_for_full_paper_ops"]
        ),
        "required_capability_ready_count": sum(
            1
            for capability in capabilities
            if capability["required_for_full_paper_ops"] and capability["ready"]
        ),
        "target_capabilities": [
            {"key": key, "meaning": meaning} for key, meaning in TARGET_CAPABILITIES
        ],
        "capability_records": capabilities,
        "strategy_research_intake_status": strategy_research.get("status"),
        "strategy_research_candidate_count": _int(strategy_research.get("candidate_count")),
        "strategy_research_trade_candidate_creation_allowed": strategy_research.get(
            "trade_candidate_creation_allowed"
        ) is True,
        "strategy_research_execution_allowed": strategy_research.get("execution_allowed") is True,
        "phase7_run_state": demo_run.get("run_state", "missing"),
        "phase7_run_id": demo_run.get("run_id"),
        "phase7_active_day_number": demo_run.get("active_day_number"),
        "qualified_setup_count": _int(demo_run.get("qualified_setup_count")),
        "submitted_paper_order_count": _int(demo_run.get("submitted_paper_order_count")),
        "closed_proof_trade_count": _int(demo_run.get("closed_proof_trade_count")),
        "external_broker_post_performed_count": _int(
            submit.get("external_broker_post_performed_count")
        ),
        "broker_post_called_count": _int(submit.get("broker_post_called_count")),
        "alpaca_post_called_count": _int(submit.get("alpaca_post_called_count")),
        "alpaca_paper_post_gate_status": alpaca_paper_post.get("status", "missing"),
        "alpaca_paper_post_path_available": (
            alpaca_paper_post.get("paper_post_path_available") is True
        ),
        "alpaca_paper_post_eligible_submit_record_count": _int(
            alpaca_paper_post.get("eligible_submit_record_count")
        ),
        "alpaca_paper_post_called_count": _int(
            alpaca_paper_post.get("alpaca_paper_post_called_count")
        ),
        "alpaca_paper_post_succeeded_count": _int(
            alpaca_paper_post.get("alpaca_paper_post_succeeded_count")
        ),
        "alpaca_paper_post_live_endpoint_called_count": _int(
            alpaca_paper_post.get("live_endpoint_called_count")
        ),
        "paper_lifecycle_poller_status": paper_lifecycle_poller.get("status", "missing"),
        "paper_lifecycle_poller_source_submitted_paper_order_count": _int(
            paper_lifecycle_poller.get("source_submitted_paper_order_count")
        ),
        "paper_lifecycle_poller_poll_candidate_count": _int(
            paper_lifecycle_poller.get("poll_candidate_count")
        ),
        "paper_lifecycle_poller_order_poll_called_count": _int(
            paper_lifecycle_poller.get("paper_order_poll_called_count")
        ),
        "paper_lifecycle_poller_position_poll_called_count": _int(
            paper_lifecycle_poller.get("paper_position_poll_called_count")
        ),
        "paper_lifecycle_poller_broker_get_called_count": _int(
            paper_lifecycle_poller.get("broker_get_called_count")
        ),
        "paper_lifecycle_poller_broker_post_called_count": _int(
            paper_lifecycle_poller.get("broker_post_called_count")
        ),
        "paper_lifecycle_poller_live_endpoint_called_count": _int(
            paper_lifecycle_poller.get("live_endpoint_called_count")
        ),
        "paper_lifecycle_poller_open_position_count": _int(
            paper_lifecycle_poller.get("open_position_count")
        ),
        "paper_lifecycle_poller_closed_trade_count": _int(
            paper_lifecycle_poller.get("closed_trade_count")
        ),
        "paper_lifecycle_poller_phase7_proof_credit_allowed": (
            paper_lifecycle_poller.get("phase7_proof_credit_allowed") is True
        ),
        "paper_lifecycle_poller_q7_lifecycle_mutation_performed": (
            paper_lifecycle_poller.get("q7_lifecycle_mutation_performed") is True
        ),
        "paper_exit_path_status": paper_exit_path.get("status", "missing"),
        "paper_exit_path_enabled": settings.alpaca_paper_exit_enabled,
        "paper_exit_path_available": paper_exit_path.get("paper_exit_path_available") is True,
        "paper_exit_path_open_position_readback_count": _int(
            paper_exit_path.get("open_position_readback_count")
        ),
        "paper_exit_path_eligible_exit_record_count": _int(
            paper_exit_path.get("eligible_exit_record_count")
        ),
        "paper_exit_path_close_called_count": _int(
            paper_exit_path.get("paper_position_close_called_count")
        ),
        "paper_exit_path_close_succeeded_count": _int(
            paper_exit_path.get("paper_position_close_succeeded_count")
        ),
        "paper_exit_path_broker_write_called_count": _int(
            paper_exit_path.get("broker_write_called_count")
        ),
        "paper_exit_path_broker_post_called_count": _int(
            paper_exit_path.get("broker_post_called_count")
        ),
        "paper_exit_path_order_cancel_called_count": _int(
            paper_exit_path.get("order_cancel_called_count")
        ),
        "paper_exit_path_position_resize_called_count": _int(
            paper_exit_path.get("position_resize_called_count")
        ),
        "paper_exit_path_live_endpoint_called_count": _int(
            paper_exit_path.get("live_endpoint_called_count")
        ),
        "paper_exit_path_phase7_proof_credit_allowed": (
            paper_exit_path.get("phase7_proof_credit_allowed") is True
        ),
        "paper_exit_path_q7_lifecycle_mutation_performed": (
            paper_exit_path.get("q7_lifecycle_mutation_performed") is True
        ),
        "notification_review_status": notification_review.get("status", "missing"),
        "notification_review_event_log_written": (
            notification_review.get("event_log_written") is True
        ),
        "notification_review_record_count": _int(
            notification_review.get("notification_record_count")
        ),
        "notification_review_lifecycle_type_count": _int(
            notification_review.get("lifecycle_notification_type_count")
        ),
        "notification_review_eligible_review_count": _int(
            notification_review.get("eligible_review_count")
        ),
        "notification_review_suppressed_count": _int(
            notification_review.get("suppressed_notification_count")
        ),
        "notification_review_blocker_count": _int(
            notification_review.get("paperops_blocker_count")
        ),
        "notification_review_telegram_mode": notification_review.get(
            "telegram_mode",
            "missing",
        ),
        "notification_review_send_gate": notification_review.get(
            "telegram_send_gate",
            "missing",
        ),
        "notification_review_send_test_gate_state": notification_review.get(
            "send_test_gate_state",
            "missing",
        ),
        "notification_review_live_send_allowed_count": _int(
            notification_review.get("live_send_allowed_count")
        ),
        "notification_review_command_path_enabled_count": _int(
            notification_review.get("telegram_command_path_enabled_count")
        ),
        "notification_review_broker_write_allowed_count": _int(
            notification_review.get("broker_write_allowed_count")
        ),
        "notification_review_paper_order_allowed_count": _int(
            notification_review.get("paper_order_allowed_count")
        ),
        "notification_review_position_close_allowed_count": _int(
            notification_review.get("position_close_allowed_count")
        ),
        "notification_review_position_resize_allowed_count": _int(
            notification_review.get("position_resize_allowed_count")
        ),
        "notification_review_live_endpoint_allowed_count": _int(
            notification_review.get("live_endpoint_allowed_count")
        ),
        "notification_review_phase7_proof_credit_allowed": (
            notification_review.get("phase7_proof_credit_allowed") is True
        ),
        "notification_review_normal_live_notification_allowed": (
            notification_review.get("normal_live_notification_allowed") is True
        ),
        "paperops_30_day_operations_status": paperops_30_day_operations.get(
            "status",
            "missing",
        ),
        "paperops_30_day_operations_scheduler_status": paperops_30_day_operations.get(
            "scheduler_status",
            "missing",
        ),
        "paperops_30_day_operations_run_id": paperops_30_day_operations.get("run_id"),
        "paperops_30_day_operations_active_day_number": paperops_30_day_operations.get(
            "active_day_number"
        ),
        "paperops_30_day_operations_completed_calendar_day_count": _int(
            paperops_30_day_operations.get("completed_calendar_day_count")
        ),
        "paperops_30_day_operations_calendar_days_remaining": _int(
            paperops_30_day_operations.get("calendar_days_remaining")
        ),
        "paperops_30_day_operations_automation_active": (
            paperops_30_day_operations.get("automation_active") is True
        ),
        "paperops_30_day_operations_automation_prompt_paperops_bound": (
            paperops_30_day_operations.get("automation_prompt_paperops_bound") is True
        ),
        "paperops_30_day_operations_cycle_status": paperops_30_day_operations.get(
            "paper_operational_cycle_status",
            "missing",
        ),
        "paperops_30_day_operations_cycle_command_count": _int(
            paperops_30_day_operations.get("paper_operational_cycle_command_count")
        ),
        "paperops_30_day_operations_dashboard_mirror_status": (
            paperops_30_day_operations.get("dashboard_mirror_status", "missing")
        ),
        "paperops_30_day_operations_dashboard_mirror_public_safe": (
            paperops_30_day_operations.get("dashboard_mirror_public_safe") is True
        ),
        "paperops_30_day_operations_unsafe_write_counter_total": _int(
            paperops_30_day_operations.get("unsafe_write_counter_total")
        ),
        "paperops_30_day_operations_live_capital_enabled": (
            paperops_30_day_operations.get("live_capital_enabled") is True
        ),
        "paperops_30_day_operations_phase7_proof_credit_allowed": (
            paperops_30_day_operations.get("phase7_proof_credit_allowed") is True
        ),
        "prediction_market_write_allowed_count": _int(
            submit.get("prediction_market_write_allowed_count")
        ),
        "crypto_perps_write_allowed_count": _int(submit.get("crypto_perps_write_allowed_count")),
        "live_endpoint_allowed_count": _int(submit.get("live_endpoint_allowed_count")),
        "live_capital_enabled_count": 1 if settings.live_capital_enabled else 0,
        "phase7_proof_credit_allowed": False,
        "live_money_blocked": not settings.live_capital_enabled,
        "quantum_provider_required_for_paper_ops": settings.quantum_paper_parity_required,
        "quantum_provider_required_as_execution_prerequisite": False,
        "head_of_quant_oracle_result_count": _int(snapshot["quantum_summary"].get("result_count")),
        "head_of_quant_latest_backend": snapshot["quantum_summary"].get("latest_backend"),
        "head_of_quant_latest_route_type": snapshot["quantum_summary"].get("latest_output_route_type"),
        "qctrl_readiness_status": snapshot["qctrl"].get("status"),
        "qctrl_credential_configured": snapshot["qctrl"].get("credential_configured") is True,
        "qctrl_sdk_package_importable": snapshot["qctrl"].get("sdk_package_importable") is True,
        "qctrl_paper_consultation_status": snapshot["qctrl_consultation"].get("status", "missing"),
        "qctrl_paper_consultation_provider_call_recorded": (
            snapshot["qctrl_consultation"].get("provider_call_recorded") is True
        ),
        "qctrl_paper_consultation_head_note_status": (
            snapshot["qctrl_consultation"].get("head_of_quant_note", {}) or {}
        ).get("status"),
        "qctrl_provider_call_allowed": (
            snapshot["qctrl_consultation"].get("provider_call_allowed") is True
        ),
        "qctrl_provider_call_count": _int(snapshot["qctrl_consultation"].get("provider_call_count")),
        "qctrl_optimization_job_submitted": snapshot["qctrl"].get("optimization_job_submitted") is True,
        "qctrl_paper_order_allowed": snapshot["qctrl_consultation"].get("paper_order_allowed") is True,
        "qctrl_execution_allowed": snapshot["qctrl_consultation"].get("execution_allowed") is True,
        "telegram_required_for_trade_execution": False,
        "blockers": blockers,
        "blocker_count": len(blockers),
        "hard_safety_failures": hard_safety_failures,
        "hard_safety_failure_count": len(hard_safety_failures),
        "recommended_next_stage": _recommended_next_stage(safe_to_continue, blockers),
        "boundary": PAPER_OPS_BOUNDARY,
    }
    artifact["validation_errors"] = validate_paper_operational_readiness(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "invalid"
    return artifact


def validate_paper_operational_readiness(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if artifact.get("mode") != "paper":
        errors.append("paper_ops_mode_not_paper")
    if artifact.get("live_capital_enabled") is not False:
        errors.append("paper_ops_live_capital_enabled")
    if artifact.get("live_capital_enabled_count", 0) != 0:
        errors.append("paper_ops_live_capital_count_nonzero")
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "prediction_market_write_allowed_count",
        "crypto_perps_write_allowed_count",
        "live_endpoint_allowed_count",
        "alpaca_paper_post_live_endpoint_called_count",
        "paper_lifecycle_poller_broker_post_called_count",
        "paper_lifecycle_poller_live_endpoint_called_count",
        "paper_exit_path_broker_post_called_count",
        "paper_exit_path_order_cancel_called_count",
        "paper_exit_path_position_resize_called_count",
        "paper_exit_path_live_endpoint_called_count",
        "paperops_30_day_operations_unsafe_write_counter_total",
        "paper_live_activation_broker_post_called_count",
        "paper_live_activation_alpaca_post_called_count",
        "paper_live_activation_live_endpoint_called_count",
    ):
        if _int(artifact.get(key)) != 0:
            errors.append(f"paper_ops_unsafe_counter_nonzero:{key}")
    if artifact.get("paper_live_activation_status") != "approved_pending_later_enablement":
        errors.append("paper_ops_paper_live_activation_not_approved")
    if artifact.get("paper_live_activation_approval_state") != "approved":
        errors.append("paper_ops_paper_live_activation_approval_state_invalid")
    if artifact.get("paper_live_activation_approval_logged") is not True:
        errors.append("paper_ops_paper_live_activation_approval_not_logged")
    if artifact.get("paper_live_activation_approved") is not True:
        errors.append("paper_ops_paper_live_activation_approved_false")
    if artifact.get("paper_trading_system_approval_logged") is not True:
        errors.append("paper_ops_paper_trading_system_approval_not_logged")
    if artifact.get("paper_live_activation_mode") != "alpaca_paper_only":
        errors.append("paper_ops_paper_live_activation_mode_invalid")
    if artifact.get("paper_live_activation_per_trade_manual_approval_required") is not False:
        errors.append("paper_ops_paper_live_activation_manual_approval_required")
    if artifact.get("paper_live_activation_paper_order_submission_allowed") is not False:
        errors.append("paper_ops_paper_live_activation_submit_authority")
    if artifact.get("paper_live_activation_forced_trades_allowed") is not False:
        errors.append("paper_ops_paper_live_activation_forced_trades_allowed")
    if artifact.get("paper_live_activation_qctrl_consultation_required") is not True:
        errors.append("paper_ops_paper_live_activation_qctrl_not_required")
    if artifact.get("paper_live_activation_qctrl_execution_allowed") is not False:
        errors.append("paper_ops_paper_live_activation_qctrl_execution_authority")
    if artifact.get("paper_live_activation_qctrl_broker_post_allowed") is not False:
        errors.append("paper_ops_paper_live_activation_qctrl_broker_authority")
    if artifact.get("paper_live_activation_phase7_proof_credit_allowed") is not False:
        errors.append("paper_ops_paper_live_activation_proof_credit_allowed")
    if artifact.get("phase7_proof_credit_allowed") is not False:
        errors.append("paper_ops_phase7_proof_credit_allowed")
    if artifact.get("paper_lifecycle_poller_phase7_proof_credit_allowed") is not False:
        errors.append("paper_ops_lifecycle_poller_proof_credit_allowed")
    if artifact.get("paper_lifecycle_poller_q7_lifecycle_mutation_performed") is not False:
        errors.append("paper_ops_lifecycle_poller_q7_mutation_performed")
    if artifact.get("paper_exit_path_phase7_proof_credit_allowed") is not False:
        errors.append("paper_ops_exit_path_proof_credit_allowed")
    if artifact.get("paper_exit_path_q7_lifecycle_mutation_performed") is not False:
        errors.append("paper_ops_exit_path_q7_mutation_performed")
    for key in (
        "notification_review_live_send_allowed_count",
        "notification_review_command_path_enabled_count",
        "notification_review_broker_write_allowed_count",
        "notification_review_paper_order_allowed_count",
        "notification_review_position_close_allowed_count",
        "notification_review_position_resize_allowed_count",
        "notification_review_live_endpoint_allowed_count",
    ):
        if _int(artifact.get(key)) != 0:
            errors.append(f"paper_ops_notification_unsafe_counter_nonzero:{key}")
    if artifact.get("notification_review_phase7_proof_credit_allowed") is not False:
        errors.append("paper_ops_notification_phase7_proof_credit_allowed")
    if artifact.get("notification_review_normal_live_notification_allowed") is not False:
        errors.append("paper_ops_notification_normal_live_allowed")
    if artifact.get("paperops_30_day_operations_status") not in {
        "operations_active",
        "operations_complete_pending_certification",
    }:
        errors.append("paper_ops_30_day_operations_not_active")
    if artifact.get("paperops_30_day_operations_automation_active") is not True:
        errors.append("paper_ops_30_day_operations_scheduler_inactive")
    if artifact.get("paperops_30_day_operations_automation_prompt_paperops_bound") is not True:
        errors.append("paper_ops_30_day_operations_prompt_not_bound")
    if artifact.get("paperops_30_day_operations_dashboard_mirror_public_safe") is not True:
        errors.append("paper_ops_30_day_operations_dashboard_not_public_safe")
    if artifact.get("paperops_30_day_operations_live_capital_enabled") is not False:
        errors.append("paper_ops_30_day_operations_live_capital_enabled")
    if artifact.get("paperops_30_day_operations_phase7_proof_credit_allowed") is not False:
        errors.append("paper_ops_30_day_operations_proof_credit_allowed")
    if artifact.get("quantum_provider_required_as_execution_prerequisite") is not False:
        errors.append("paper_ops_quantum_provider_execution_prerequisite")
    if artifact.get("qctrl_execution_allowed") is not False:
        errors.append("paper_ops_qctrl_execution_authority")
    if artifact.get("qctrl_paper_order_allowed") is not False:
        errors.append("paper_ops_qctrl_paper_order_authority")
    if artifact.get("telegram_required_for_trade_execution") is not False:
        errors.append("paper_ops_telegram_trade_execution_required")
    if artifact.get("strategy_research_intake_status") != "ready_for_strategy_review":
        errors.append("paper_ops_strategy_research_intake_not_ready")
    if _int(artifact.get("strategy_research_candidate_count")) != 4:
        errors.append("paper_ops_strategy_research_candidate_count_invalid")
    if artifact.get("strategy_research_trade_candidate_creation_allowed") is not False:
        errors.append("paper_ops_strategy_research_trade_authority")
    if artifact.get("strategy_research_execution_allowed") is not False:
        errors.append("paper_ops_strategy_research_execution_authority")
    if artifact.get("safe_to_continue_paper_only") is True and artifact.get(
        "hard_safety_failure_count"
    ):
        errors.append("paper_ops_safe_with_hard_safety_failures")
    if artifact.get("full_paper_operational_ready") is True and artifact.get("blocker_count"):
        errors.append("paper_ops_ready_with_blockers")
    return errors


def write_paper_operational_readiness(
    artifact: dict[str, Any],
    settings: Settings | None = None,
    *,
    record_event: bool = True,
    event_log_path: Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    settings = settings or Settings.from_env()
    output_path, history_path, default_event_log_path = paper_operational_readiness_paths(
        settings
    )
    event_path = event_log_path or default_event_log_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = dict(artifact)
    written["recorded"] = True
    written["runtime_artifact_path"] = str(output_path)
    written["history_log_path"] = str(history_path)
    if record_event:
        event = EventLog(event_path, echo=False).write(
            PAPER_OPS_EVENT_TYPE,
            PAPER_OPS_COMPONENT,
            payload={
                "status": written["status"],
                "full_paper_operational_ready": written["full_paper_operational_ready"],
                "safe_to_continue_paper_only": written["safe_to_continue_paper_only"],
                "blocker_count": written["blocker_count"],
                "hard_safety_failure_count": written["hard_safety_failure_count"],
            },
        )
        written["event_log_written"] = True
        written["event_log_path"] = str(event_path)
        written["event_log_event_count"] = 1
        written["event_log_correlation_id"] = event.correlation_id
        written["event_log_created_at"] = event.created_at
    output_path.write_text(json.dumps(written, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(written, sort_keys=True) + "\n")
    return output_path, history_path, event_path, written
