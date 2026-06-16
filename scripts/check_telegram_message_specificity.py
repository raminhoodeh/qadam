#!/usr/bin/env python3
"""Validate that Qadam Telegram messages are specific, not repeated boilerplate."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.telegram_codebase_upgrade_notifications import (  # noqa: E402
    build_telegram_codebase_upgrade_notification,
    validate_telegram_codebase_upgrade_notification,
)
from orchestrator.telegram_comms import render_telegram_message  # noqa: E402
from orchestrator.telegram_daily_portfolio_digest import (  # noqa: E402
    build_daily_portfolio_digest,
    validate_daily_portfolio_digest,
)
from orchestrator.telegram_human_brief import (  # noqa: E402
    build_telegram_human_brief,
    validate_telegram_human_brief,
)
from orchestrator.telegram_message_quality import (  # noqa: E402
    telegram_message_specificity,
)
from orchestrator.telegram_trade_notifications import (  # noqa: E402
    build_telegram_trade_notifications,
    validate_telegram_trade_notifications,
)
from orchestrator.cockpit_status import build_cockpit_status  # noqa: E402


def _score(title: str, body: str) -> int:
    return int(telegram_message_specificity(title, body).get("score", 0))


def main() -> int:
    settings = Settings.from_env()
    errors: list[str] = []

    bad = telegram_message_specificity(
        "Qadam Codebase Upgrade",
        "\n".join(
            [
                "Qadam: codebase upgrade deployed",
                "What changed: Qadam was upgraded.",
                "Why it matters: backend state changed.",
                "Evidence: structured runtime state.",
                "Status: notification only.",
                "Dashboard: qadam.trade/dashboard/",
            ]
        ),
    )
    print(f"telegram_specificity_bad_status={bad['status']}")
    print(f"telegram_specificity_bad_score={bad['score']}")
    if bad["status"] == "specific":
        errors.append("generic_message_scored_specific")

    renderer_samples = {
        "trade_candidate": {
            "instrument": "AAPL paper watch",
            "catalyst": "Yahoo Finance momentum and Preference market context moved together",
            "evidence_summary": "3 corroborating source packets; confidence=0.62; risk_gate=pending",
            "current_impact": "candidate is reviewable, but no paper order exists",
        },
        "blocked_trade": {
            "instrument": "TSLA paper watch",
            "catalyst": "headline volatility detected without sufficient confirmation",
            "evidence_summary": "2 sources, 1 conflict, no Q-CTRL consultation clearance",
            "blocked_reason": "failed signal integrity and sizing gates",
            "current_impact": "the idea stays in the research ledger only",
        },
        "insight_digest": {
            "title": "Insight digest: source divergence",
            "theme": "macro and equity evidence divergence",
            "why_it_matters": "Research Analyst found conflict between market data and narrative sources",
            "evidence": "5 packets reviewed; 2 conflicts; 0 orders authorized",
            "current_impact": "Strategy Lead keeps this as research context",
            "block": "not executable until signal integrity improves",
        },
        "source_degraded": {
            "title": "System warning: data source degraded",
            "subject": "Preference source health",
            "why_it_matters": "fewer live intelligence feeds can lower setup confidence",
            "evidence": "online_sources=27; degraded_sources=2; affected_pipeline=world_monitor",
            "current_impact": "affected sources are excluded from order authority",
            "block": "fail closed until the source recovers",
        },
        "open_position": {
            "title": "PaperOps: open paper position",
            "subject": "paper position lifecycle",
            "why_it_matters": "paper account mirror recorded an open position",
            "evidence": "open_positions=1; orders=1; lifecycle_ref=paper-account-mirror",
            "current_impact": "members can review exposure from the dashboard",
            "block": "Telegram cannot close, resize, or cancel the position",
        },
    }
    for message_class, context in renderer_samples.items():
        title, body = render_telegram_message(message_class, context)
        quality = telegram_message_specificity(title, body)
        print(f"telegram_specificity_renderer_{message_class}_status={quality['status']}")
        print(f"telegram_specificity_renderer_{message_class}_score={quality['score']}")
        if quality["status"] != "specific":
            errors.append(f"renderer_message_not_specific:{message_class}:{quality['reasons']}")

    codebase = build_telegram_codebase_upgrade_notification(
        settings=settings,
        send_requested=False,
        force_send=True,
        summary="Telegram messages now include event-specific context and a specificity score.",
        source="specificity_check",
        deployment_url="https://qadam-specificity-check.vercel.app",
        aliases=["qadam.trade", "www.qadam.trade"],
    )
    codebase_errors = validate_telegram_codebase_upgrade_notification(codebase)
    print(f"telegram_specificity_codebase_status={codebase['message_specificity_status']}")
    print(f"telegram_specificity_codebase_score={codebase['message_specificity_score']}")
    if codebase_errors:
        errors.extend(codebase_errors)
    if not codebase.get("change_area_lines"):
        errors.append("codebase_specificity_change_areas_missing")

    daily = build_daily_portfolio_digest(settings=settings, send_requested=False, force=True)
    daily_errors = validate_daily_portfolio_digest(daily)
    print(f"telegram_specificity_daily_status={daily['message_specificity_status']}")
    print(f"telegram_specificity_daily_score={daily['message_specificity_score']}")
    if daily_errors:
        errors.extend(daily_errors)
    if not str(daily.get("paperops_idle_reason") or "").strip():
        errors.append("daily_specificity_idle_reason_missing")

    cockpit_status = build_cockpit_status(settings)
    human_brief = build_telegram_human_brief(
        daily_edge_findings=cockpit_status["daily_edge_findings_brief"],
        promotion_gates=cockpit_status["promotion_gates"],
        settings=settings,
        send_requested=False,
        generated_at=cockpit_status["generated_at"],
    )
    validate_telegram_human_brief(human_brief)
    print(f"telegram_specificity_human_brief_status={human_brief['message_specificity_status']}")
    print(f"telegram_specificity_human_brief_score={human_brief['message_specificity_score']}")
    print(f"telegram_specificity_human_brief_style={human_brief['message_human_style_status']}")
    if human_brief["message_specificity_status"] != "specific":
        errors.append("human_brief_message_not_specific")
    if human_brief["message_human_style_status"] != "human":
        errors.append("human_brief_message_not_human")
    if human_brief["paragraph_count"] not in {1, 2}:
        errors.append("human_brief_paragraph_count_invalid")

    trade_notifications = build_telegram_trade_notifications(settings=settings, send_requested=False)
    trade_errors = validate_telegram_trade_notifications(trade_notifications)
    print(f"telegram_specificity_trade_bundle_status={trade_notifications['status']}")
    print(
        "telegram_specificity_trade_record_count="
        f"{len(trade_notifications.get('records', []))}"
    )
    if trade_errors:
        errors.extend(trade_errors)
    for record in trade_notifications.get("records", []):
        if not isinstance(record, dict):
            continue
        if record.get("message_specificity_status") != "specific":
            errors.append(f"trade_specificity_record_not_specific:{record.get('artifact_id')}")

    if errors:
        for error in sorted(set(errors)):
            print(f"telegram_specificity_error={error}")
        print("telegram_message_specificity_check=failed")
        return 1

    print("telegram_message_specificity_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
