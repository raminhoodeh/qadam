"""QEG-0 baseline, ownership and dashboard non-interference audit."""

from __future__ import annotations

import subprocess
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import ROOT, now_iso, read_json, runtime_dir, write_json_atomic
from orchestrator.qadam_qeg_common import (
    BASELINE_ARTIFACT,
    COMPATIBILITY_ARTIFACT,
    DASHBOARD_UX_BASELINE_ARTIFACT,
    OWNERSHIP_ARTIFACT,
    artifact_snapshot,
    qeg_authority,
    write_phase_status,
)

PROTECTED_DASHBOARD_FILES = (
    "landing-page-repo/dashboard/index.html",
    "landing-page-repo/dashboard.js",
    "landing-page-repo/auth.css",
)

PLAN_DEPENDENCIES = (
    "docs/qadam-operator-ready-edge-engine-implementation-plan.md",
    "docs/qadam-backtest-completion-implementation-plan.md",
    "docs/qadam-evidence-fit-active-paper-trading-overhaul-implementation-plan.md",
    "docs/qadam-permanent-operator-reliability-repair-implementation-plan.md",
)


def _git_dirty_paths() -> list[str]:
    completed = subprocess.run(
        ["git", "status", "--short"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    return sorted(line[3:] for line in completed.stdout.splitlines() if len(line) >= 4)


def _source_count(payload: dict[str, Any]) -> int:
    rows = payload.get("sources") if isinstance(payload.get("sources"), list) else []
    return int(payload.get("source_count") or len(rows))


def _instrument_count(payload: dict[str, Any]) -> int:
    rows = payload.get("instruments") if isinstance(payload.get("instruments"), list) else []
    return int(payload.get("watched_market_count") or payload.get("instrument_count") or len(rows))


def build_baseline(settings: Settings | None = None) -> tuple[dict[str, Any], ...]:
    runtime = runtime_dir(settings)
    sources = read_json(runtime / "qsase_source_universe.json")
    instruments = read_json(runtime / "qsase_trading_universe.json")
    scores = read_json(runtime / "qadam_pattern_score_v3.json")
    foundry = read_json(runtime / "qadam_strategy_foundry_v3.json")
    policy = read_json(runtime / "qadam_experimental_paper_policy.json")
    operator = read_json(runtime / "qadam_operator_service_status.json")
    baseline = {
        "schema_version": "qadam_qeg_baseline.v1",
        "artifact_type": "qadam_qeg_baseline",
        "generated_at": now_iso(),
        "status": "baseline_frozen",
        "source_count": _source_count(sources),
        "instrument_count": _instrument_count(instruments),
        "source_state": sources.get("status"),
        "instrument_state": instruments.get("status"),
        "pattern_score_record_count": scores.get("record_count", 0),
        "strategy_hypothesis_count": foundry.get("hypothesis_count", 0),
        "validated_edge_count": foundry.get("edge_count", 0),
        "policy_version": policy.get("policy_version"),
        "policy_status": policy.get("status"),
        "discovery_micro_notional": policy.get("risk", {}).get("discovery_target_notional_usd"),
        "absolute_paper_trade_ceiling_usd": policy.get("risk", {}).get("absolute_trade_ceiling_usd"),
        "operator_status": operator.get("status"),
        "observation_ready": operator.get("observation_ready"),
        "dirty_worktree_paths": _git_dirty_paths(),
        "dirty_paths_preserved": True,
        "implementation_status_separate_from_empirical_status": True,
        "authority": qeg_authority(),
    }
    ownership = {
        "schema_version": "qadam_qeg_artifact_ownership.v1",
        "artifact_type": "qadam_qeg_artifact_ownership",
        "generated_at": now_iso(),
        "status": "ownership_additive_no_collision",
        "new_logical_resource": "temporal_graph",
        "canonical_event_owner": "qeg_evidence_cycle",
        "derived_index_owner": "qeg_evidence_cycle",
        "existing_owners_retained": {
            "source_lake": "source_ingestion",
            "score_plane": "pattern_scoring",
            "edge_registry": "research_evidence_validation",
            "akber": "akber_review",
            "router": "portfolio_router_review",
            "paperops": "guarded_paperops",
            "paper_state": "paper_lifecycle_poll",
            "dashboard": "dashboard_refresh",
        },
        "legacy_phase6_graph": {
            "state": "legacy_reference_only",
            "may_override_current_graph": False,
            "learning_approval_state_preserved": True,
        },
        "authority": qeg_authority(),
    }
    compatibility = {
        "schema_version": "qadam_qeg_compatibility_matrix.v1",
        "artifact_type": "qadam_qeg_compatibility_matrix",
        "generated_at": now_iso(),
        "status": "compatible",
        "dependencies": [
            {"path": path, "exists": (ROOT / path).exists(), "mode": "consume_or_adapter"}
            for path in PLAN_DEPENDENCIES
        ],
        "canonical_paperops_wrapper": "scripts/run_paperops_autonomous_pass.py",
        "parallel_broker_route_allowed": False,
        "authority": qeg_authority(),
    }
    dashboard = {
        "schema_version": "qadam_qeg_dashboard_ux_baseline.v1",
        "artifact_type": "qadam_qeg_dashboard_ux_baseline",
        "generated_at": now_iso(),
        "status": "protected",
        "protected_route_structure": True,
        "files": [artifact_snapshot(ROOT / path) for path in PROTECTED_DASHBOARD_FILES],
        "route_change_allowed": False,
        "authority": qeg_authority(),
    }
    return baseline, ownership, compatibility, dashboard


def build_and_write_baseline(settings: Settings | None = None) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    baseline, ownership, compatibility, dashboard = build_baseline(settings)
    artifacts = (
        (BASELINE_ARTIFACT, baseline),
        (OWNERSHIP_ARTIFACT, ownership),
        (COMPATIBILITY_ARTIFACT, compatibility),
        (DASHBOARD_UX_BASELINE_ARTIFACT, dashboard),
    )
    for name, payload in artifacts:
        write_json_atomic(runtime / name, payload)
    errors: list[str] = []
    if baseline["source_count"] <= 0:
        errors.append("source_universe_missing")
    if baseline["instrument_count"] <= 0:
        errors.append("trading_universe_missing")
    if not all(row["exists"] for row in compatibility["dependencies"]):
        errors.append("plan_dependency_missing")
    if not (ROOT / compatibility["canonical_paperops_wrapper"]).exists():
        errors.append("canonical_paperops_wrapper_missing")
    if not any(row["exists"] for row in dashboard["files"]):
        errors.append("protected_dashboard_files_missing")
    write_phase_status(
        "QEG-0",
        status="passed" if not errors else "blocked",
        implementation_complete=not errors,
        empirical_state="baseline_frozen",
        artifacts=[name for name, _payload in artifacts],
        blockers=errors,
        settings=settings,
    )
    return baseline, errors
