from dataclasses import replace

from orchestrator.config import Settings
from orchestrator.daily_learning_automation import daily_learning_local_context
from orchestrator.daily_learning_scheduler import (
    build_daily_learning_scheduler_decision,
)
from orchestrator.daily_telegram_learning_brief import (
    daily_telegram_learning_delivery_key,
)


def _settings():
    return replace(
        Settings.from_env(),
        daily_learning_automation_timezone="Asia/Dubai",
        daily_learning_automation_local_times=("08:00", "20:00"),
    )


def test_twice_daily_schedule_selects_morning_and_evening_slots():
    before_morning = daily_learning_local_context(
        settings=_settings(),
        generated_at="2026-07-22T03:59:00+00:00",
    )
    morning = daily_learning_local_context(
        settings=_settings(),
        generated_at="2026-07-22T04:00:00+00:00",
    )
    evening = daily_learning_local_context(
        settings=_settings(),
        generated_at="2026-07-22T16:00:00+00:00",
    )

    assert before_morning["due_for_delivery"] is False
    assert before_morning["brief_slot"] == "morning"
    assert morning["due_for_delivery"] is True
    assert morning["brief_slot"] == "morning"
    assert morning["delivery_after_local_time"] == "08:00"
    assert evening["due_for_delivery"] is True
    assert evening["brief_slot"] == "evening"
    assert evening["delivery_after_local_time"] == "20:00"
    assert evening["delivery_local_times"] == ["08:00", "20:00"]


def test_scheduler_runs_only_for_a_due_unsent_slot():
    before = build_daily_learning_scheduler_decision(
        settings=_settings(),
        generated_at="2026-07-23T03:59:00+00:00",
        sent_delivery_keys=set(),
        scheduler_state={},
    )
    due = build_daily_learning_scheduler_decision(
        settings=_settings(),
        generated_at="2026-07-23T04:02:00+00:00",
        sent_delivery_keys=set(),
        scheduler_state={},
    )
    sent_key = daily_telegram_learning_delivery_key("2026-07-23", "morning")
    sent = build_daily_learning_scheduler_decision(
        settings=_settings(),
        generated_at="2026-07-23T04:07:00+00:00",
        sent_delivery_keys={sent_key},
        scheduler_state={},
    )

    assert before["should_run"] is False
    assert before["reason"] == "slot_not_due"
    assert due["should_run"] is True
    assert due["reason"] == "due_unsent_slot"
    assert sent["should_run"] is False
    assert sent["reason"] == "slot_already_sent"
    assert sent["telegram_command_path_enabled"] is False
    assert sent["broker_write_allowed"] is False
    assert sent["live_capital_enabled"] is False


def test_scheduler_throttles_failed_slot_retries():
    delivery_key = daily_telegram_learning_delivery_key("2026-07-23", "morning")
    state = {
        "delivery_key": delivery_key,
        "last_attempt_at": "2026-07-23T04:02:00+00:00",
    }
    cooling_down = build_daily_learning_scheduler_decision(
        settings=_settings(),
        generated_at="2026-07-23T04:07:00+00:00",
        sent_delivery_keys=set(),
        scheduler_state=state,
    )
    retry_due = build_daily_learning_scheduler_decision(
        settings=_settings(),
        generated_at="2026-07-23T04:17:00+00:00",
        sent_delivery_keys=set(),
        scheduler_state=state,
    )

    assert cooling_down["should_run"] is False
    assert cooling_down["reason"] == "retry_cooldown_active"
    assert retry_due["should_run"] is True
    assert retry_due["reason"] == "due_unsent_slot"
