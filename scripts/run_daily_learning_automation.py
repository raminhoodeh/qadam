#!/usr/bin/env python3
"""Run one due slot of Qadam's twice-daily learning automation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.cockpit_status import (  # noqa: E402
    build_cockpit_status,
    export_cockpit_status,
)
from orchestrator.config import Settings  # noqa: E402
from orchestrator.daily_edge_findings import (  # noqa: E402
    build_daily_edge_findings_brief,
    validate_daily_edge_findings_brief,
    write_daily_edge_findings_brief,
)
from orchestrator.daily_learning_automation import (  # noqa: E402
    build_daily_learning_automation,
    daily_learning_local_context,
    validate_daily_learning_automation,
    write_daily_learning_automation,
)
from orchestrator.daily_telegram_learning_brief import (  # noqa: E402
    build_daily_telegram_learning_brief,
    validate_daily_telegram_learning_brief,
    write_daily_telegram_learning_brief,
)
from orchestrator.qadam_research_programme_state import (  # noqa: E402
    refresh_research_programme_state,
)
from orchestrator.telegram_human_brief import (  # noqa: E402
    build_telegram_human_brief,
    validate_telegram_human_brief,
    write_telegram_human_brief,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Attempt Telegram delivery only if the Stage 6 gates and a scheduled slot pass.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass the local delivery window. Slot idempotency still prevents duplicate sends.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    settings = Settings.from_env()
    cockpit_status = build_cockpit_status(settings)
    generated_at = cockpit_status["generated_at"]
    runtime_path = Path(settings.runtime_dir)
    if not runtime_path.is_absolute():
        runtime_path = ROOT / runtime_path
    refresh_research_programme_state(
        runtime_path,
        generated_at=generated_at,
    )
    local_context = daily_learning_local_context(settings=settings, generated_at=generated_at)
    due_or_forced = local_context["due_for_delivery"] or args.force
    effective_send_requested = (
        args.live
        and due_or_forced
        and settings.daily_learning_automation_enabled
        and not settings.daily_learning_automation_dry_run
    )
    material_delta_path = Path(settings.runtime_dir) / "qadam_material_learning_delta.json"
    material_learning_delta = None
    if material_delta_path.is_file():
        try:
            candidate = json.loads(material_delta_path.read_text(encoding="utf-8"))
            if isinstance(candidate, dict):
                material_learning_delta = candidate
        except (OSError, json.JSONDecodeError):
            material_learning_delta = None

    daily_findings = build_daily_edge_findings_brief(
        cockpit_status=cockpit_status,
        generated_at=generated_at,
    )
    validate_daily_edge_findings_brief(daily_findings)
    daily_paths = write_daily_edge_findings_brief(daily_findings, settings=settings)

    human_brief = build_telegram_human_brief(
        daily_edge_findings=daily_findings,
        promotion_gates=cockpit_status["promotion_gates"],
        settings=settings,
        send_requested=False,
        generated_at=generated_at,
    )
    validate_telegram_human_brief(human_brief)
    human_paths = write_telegram_human_brief(human_brief, settings=settings)

    learning_brief = build_daily_telegram_learning_brief(
        daily_edge_findings=daily_findings,
        promotion_gates=cockpit_status["promotion_gates"],
        material_learning_delta=material_learning_delta,
        settings=settings,
        send_requested=effective_send_requested,
        force_delivery_window=args.force,
        generated_at=generated_at,
        brief_slot=local_context["brief_slot"],
        brief_slot_label=local_context["brief_slot_label"],
    )
    validate_daily_telegram_learning_brief(learning_brief)
    learning_paths = write_daily_telegram_learning_brief(learning_brief, settings=settings)

    automation = build_daily_learning_automation(
        daily_edge_findings=daily_findings,
        daily_telegram_learning_brief=learning_brief,
        settings=settings,
        send_requested=args.live,
        force_delivery_window=args.force,
        generated_at=generated_at,
    )
    validate_daily_learning_automation(automation)
    automation_paths = write_daily_learning_automation(automation, settings=settings)
    cockpit_export = export_cockpit_status(settings=settings)

    print("daily_learning_automation_runner=ok")
    print(f"daily_learning_automation_status={automation['status']}")
    print(f"daily_learning_automation_local_date={automation['local_date']}")
    print(f"daily_learning_automation_timezone={automation['timezone']}")
    print(
        "daily_learning_automation_delivery_after_local_time="
        f"{automation['delivery_after_local_time']}"
    )
    print(
        "daily_learning_automation_delivery_local_times="
        f"{','.join(automation['delivery_local_times'])}"
    )
    print(f"daily_learning_automation_brief_slot={automation['brief_slot']}")
    print(f"daily_learning_automation_due_for_delivery={automation['due_for_delivery']}")
    print(f"daily_learning_automation_force_delivery_window={automation['force_delivery_window']}")
    print(f"daily_learning_automation_send_requested={automation['send_requested']}")
    print(
        "daily_learning_automation_effective_send_requested="
        f"{automation['effective_send_requested']}"
    )
    print(f"daily_learning_automation_enabled={automation['enabled']}")
    print(f"daily_learning_automation_dry_run={automation['dry_run']}")
    print(
        "daily_learning_automation_learning_brief_status="
        f"{automation['daily_telegram_learning_brief_status']}"
    )
    print(
        "daily_learning_automation_learning_brief_specificity="
        f"{automation['daily_telegram_learning_brief_specificity_status']}:"
        f"{automation['daily_telegram_learning_brief_specificity_score']}"
    )
    print(
        "daily_learning_automation_learning_brief_human_style="
        f"{automation['daily_telegram_learning_brief_human_style_status']}"
    )
    print(f"daily_learning_automation_source_count={automation['source_count']}")
    print(
        "daily_learning_automation_watched_instrument_count="
        f"{automation['watched_instrument_count']}"
    )
    print(
        f"daily_learning_automation_candidate_pattern_count={automation['candidate_pattern_count']}"
    )
    print(f"daily_learning_automation_validated_edge_count={automation['validated_edge_count']}")
    print(f"daily_learning_automation_quantum_gate_status={automation['quantum_gate_status']}")
    print(f"daily_learning_automation_live_send_attempted={automation['live_send_attempted']}")
    print(f"daily_learning_automation_live_send_succeeded={automation['live_send_succeeded']}")
    print(f"daily_learning_automation_material_delta_status={automation['material_delta_status']}")
    print(
        "daily_learning_automation_last_delivery_failure_category="
        f"{automation['last_delivery_failure_category']}"
    )
    print(f"daily_learning_automation_blockers={','.join(automation['blockers'])}")
    print(f"daily_learning_automation_artifact_path={automation_paths['output_path']}")
    print(f"daily_telegram_learning_brief_artifact_path={learning_paths['output_path']}")
    print(f"daily_edge_findings_artifact_path={daily_paths['output_path']}")
    print(f"telegram_human_brief_artifact_path={human_paths['output_path']}")
    print(f"daily_learning_cockpit_runtime_path={cockpit_export['runtime_path']}")
    print(f"daily_learning_cockpit_landing_path={cockpit_export['landing_path']}")

    if automation["status"] in {
        "daily_learning_automation_failed",
        "daily_learning_automation_blocked",
    }:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
