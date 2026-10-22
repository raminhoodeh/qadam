"""Current collection health, separate from evidence quality and retired reports.

This module observes existing owners. It cannot poll providers, grant quorum,
change credentials, or create execution authority.
"""

from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from orchestrator.qadam_operator_ready_common import read_json


COVERAGE_ARTIFACT = "qadam_source_collection_coverage.json"
CURRENT_MONITORS = (
    (COVERAGE_ARTIFACT, "source_collection", 7200),
    ("qadam_operator_service_status.json", "operator", 300),
    ("qadam_position_care_status.json", "position_care", 1200),
    ("qadam_strategy_decision_summary.json", "strategy_decision", 7200),
    ("qadam_paper_lifecycle_v3.json", "paper_lifecycle", 1800),
    ("qsase_dashboard_status.json", "public_dashboard_status", 7200),
)
RETIRED_MONITORS = (
    "qsase_historical_memory_completion.json",
    "qsase_akber_input_completeness.json",
    "qsase_dashboard_completion_v2.json",
    "qsase_paper_lifecycle_v2.json",
    "qadam_git_deploy_readiness.json",
    "qadam_telegram_vnext_dashboard_summary.json",
    "qsase_whole_universe_backfill_backtest_state.json",
    "qsase_whole_universe_backfill_backtest_summary.json",
    "qadam_next_generation_phase0_safety_lock.json",
)


def canonical_supervision_active(runtime: Path) -> bool:
    path = runtime / "qadam-control-plane.sqlite3"
    if not path.exists():
        return False
    try:
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=5)) as db:
            return db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='execution_runtime_policy'"
            ).fetchone() is not None
    except sqlite3.Error:
        # An unreadable existing control plane must produce a current fault,
        # not silently fall back to a seemingly healthy legacy report.
        return True


def _parse(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo is not None else None


def collection_diagnostics(runtime: Path, reference: datetime) -> dict:
    coverage = read_json(runtime / COVERAGE_ARTIFACT)
    sources = coverage.get("sources")
    sources = sources if isinstance(sources, list) else []
    issues, limitations, excluded = [], [], []
    for source in sources:
        if not isinstance(source, dict):
            continue
        key = str(source.get("source_key") or "unknown")
        state = source.get("collection_status")
        if state in {"derived_alias", "intentionally_disabled", "not_selected"}:
            excluded.append({"source_key": key, "collection_status": state,
                             "reason": "not_an_independent_active_collector"})
            continue
        if state == "collected":
            evidence = source.get("collection_evidence_state")
            if evidence != "provider_observations" or source.get("evidence_freshness") not in {"fresh", "recent"}:
                limitations.append({
                    "source_key": key, "collection_status": state,
                    "collection_evidence_state": evidence,
                    "evidence_freshness": source.get("evidence_freshness"),
                    "reason": "collection_success_does_not_prove_fresh_timestamped_trade_evidence",
                    "fresh_catalyst_credit_allowed": False,
                })
            continue
        next_attempt = _parse(source.get("next_attempt_at"))
        external = state == "needs_configuration"
        retry = state == "retry_scheduled"
        overdue = bool(next_attempt and (reference - next_attempt).total_seconds() > 1800)
        actionable = not external and (not retry or next_attempt is None or overdue)
        recovery = ("operator_or_provider_action_required" if external else
                    "retry_deadline_missed" if overdue else
                    "bounded_retry_scheduled" if retry and next_attempt else "collector_repair_required")
        issues.append({
            "source_key": key, "source_name": key,
            "classification": source.get("failure_class") or "collection_state_unverified",
            "collection_status": state, "recovery_state": recovery,
            "operator_action_required": external, "actionable_repair": actionable,
            "next_attempt_at": source.get("next_attempt_at"),
            "required_action": source.get("access_repair_action") or source.get("next_action"),
            "source_quorum_contribution_allowed": False,
            "paper_order_allowed": False, "broker_write_allowed": False,
            "live_capital_enabled": False,
        })
    generated = _parse(coverage.get("generated_at"))
    age = (reference - generated).total_seconds() if generated else None
    keys = [row.get("source_key") for row in sources if isinstance(row, dict)]
    valid_catalogue = (bool(keys) and len(keys) == len(sources)
                       and all(isinstance(key, str) and key for key in keys)
                       and len(set(keys)) == len(keys))
    coverage_current = age is not None and 0 <= age <= 7200 and valid_catalogue
    return {
        "generated_at": reference.isoformat(), "coverage_generated_at": coverage.get("generated_at"),
        "coverage_current": coverage_current,
        "catalogue_count": len(sources),
        "collection_state_counts": dict(Counter(row.get("collection_status") for row in sources if isinstance(row, dict))),
        "provider_outage_count": len(issues), "records": issues,
        "external_action_count": sum(row["operator_action_required"] for row in issues),
        "scheduled_retry_count": sum(row["recovery_state"] == "bounded_retry_scheduled" for row in issues),
        "actionable_repair_count": sum(row["actionable_repair"] for row in issues),
        "classification_counts": dict(Counter(row["classification"] for row in issues)),
        "evidence_limitations": limitations, "evidence_limitation_count": len(limitations),
        "excluded_collectors": excluded, "excluded_collector_count": len(excluded),
        "retired_diagnostic_artifacts": list(RETIRED_MONITORS),
        "boundary": "Collection, evidence quality, external access, and runtime faults are distinct. No evidence or trade authority is created.",
    }
