"""Final three-state certification for autonomous experimental paper operation.

Implementation readiness, current broker operation, and unattended reliability
are deliberately independent. A missing clean broker account cannot invalidate
completed software, and completed software cannot impersonate a running fund.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_experimental_paper_policy import POLICY_VERSION
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    authority_flags,
    file_sha256,
    now_iso,
    read_json,
    runtime_dir,
    unique_errors,
    validate_authority,
)

SCHEMA_VERSION = "qadam_autonomous_experimental_paper_epoch_certification.v1"
CERTIFICATION_ARTIFACT = (
    "qadam_autonomous_experimental_paper_epoch_certification.json"
)
CHECK_ARTIFACT = "qadam_autonomous_experimental_paper_epoch_checks.json"

PAPER_ENDPOINT = "https://paper-api.alpaca.markets"
CANONICAL_WRAPPER = "scripts/run_paperops_autonomous_pass.py"
RISK_POLICY_VERSION = "qadam-paper-portfolio-risk.2-frozen"
STARTING_BALANCE_USD = 100000.0
ABSOLUTE_TRADE_CEILING_USD = 5000.0

PROTECTED_DASHBOARD_HASHES = {
    "dashboard.js": "51b32983e8e04466da0c9ae6fb874248e3eadbda8ad7fc4ffffd0112288574da",
    "auth.css": "8d44502dcfaec16ad570482630b73de84ef91377634579cbb4fb8f5968fe83c0",
    "auth.js": "c5af5d4c864e5aed34bfdd27ab9086b1fe34f0c302424300140fc51877de6c0a",
    "dashboard/index.html": "ad22544cc8ee83ce5ee6b103b5c954599d7d809043ee4f6052a33d5d1891aaa9",
}
PROTECTED_DASHBOARD_APPROVED_COMMIT = (
    "049ff897941eba15c78267a69743aa4a19fa08a0"
)


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _fresh(payload: dict[str, Any], *, seconds: int = 600) -> bool:
    generated = _parse_timestamp(payload.get("generated_at"))
    if generated is None:
        return False
    age = (datetime.now(timezone.utc) - generated).total_seconds()
    return 0 <= age <= seconds


def _status_passed(payload: dict[str, Any], *, allow_maturing: bool = False) -> bool:
    allowed = {"passed"}
    if allow_maturing:
        allowed.add("evidence_maturing")
    return str(payload.get("status") or "") in allowed and int(
        payload.get("validation_error_count") or 0
    ) == 0


def _dashboard_hash_audit() -> dict[str, Any]:
    root = ROOT / "landing-page-repo"
    rows = []
    for relative, expected in PROTECTED_DASHBOARD_HASHES.items():
        actual = file_sha256(root / relative)
        rows.append(
            {
                "path": f"landing-page-repo/{relative}",
                "expected_sha256": expected,
                "actual_sha256": actual,
                "matches_approved_ux": actual == expected,
            }
        )
    return {
        "approved_commit": PROTECTED_DASHBOARD_APPROVED_COMMIT,
        "asset_count": len(rows),
        "matching_asset_count": sum(row["matches_approved_ux"] for row in rows),
        "protected_ux_preserved": all(row["matches_approved_ux"] for row in rows),
        "assets": rows,
    }


def _gate(gate_id: str, passed: bool, observed: Any, expected: str) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
        "blocker": None if passed else gate_id,
    }


def _implementation_gates(runtime: Path, dashboard: dict[str, Any]) -> list[dict[str, Any]]:
    foundation = read_json(runtime / "qadam_autonomous_experimental_epoch_status.json")
    migration = read_json(runtime / "qadam_experimental_contract_migration.json")
    source = read_json(runtime / "qadam_source_provider_capabilities_checks.json")
    backfill = read_json(runtime / "qadam_provider_backfill_checks.json")
    point_in_time = read_json(runtime / "qadam_point_in_time_evidence_checks.json")
    backtest = read_json(runtime / "qadam_statistical_backtest_checks.json")
    foundry = read_json(runtime / "qadam_strategy_foundry_v3_checks.json")
    akber = read_json(runtime / "qadam_akber_filter_v3_checks.json")
    risk = read_json(runtime / "qadam_portfolio_risk_engine_checks.json")
    router = read_json(runtime / "qadam_router_v3_paperops_checks.json")
    eligibility = read_json(runtime / "qadam_experimental_paper_eligibility_checks.json")
    lifecycle = read_json(runtime / "qadam_paper_lineage_and_proof_checks.json")
    release = read_json(runtime / "qadam_experimental_paper_release_checks.json")
    trial = read_json(runtime / "qadam_experimental_paper_trial_checks.json")
    soak = read_json(runtime / "qadam_operator_soak_v3_checks.json")
    service = read_json(runtime / "qadam_operator_service_checks.json")
    active_edge_research = read_json(
        runtime / "qadam_active_edge_research_certification.json"
    )
    return [
        _gate(
            "experimental_policy_and_mode_implemented",
            foundation.get("implementation_foundation_ready") is True,
            foundation.get("status"),
            "implementation_foundation_ready",
        ),
        _gate(
            "legacy_contract_migration_fails_closed",
            migration.get("status") == "passed_legacy_defaults_fail_closed"
            and int(migration.get("legacy_rows_upgraded_to_experimental") or 0) == 0
            and int(migration.get("legacy_rows_upgraded_to_validated") or 0) == 0,
            migration.get("status"),
            "legacy records remain legacy_test with zero upgrades",
        ),
        _gate(
            "source_capability_contract_passed",
            _status_passed(source)
            and int(source.get("blocking_repair_request_count") or 0) == 0,
            source.get("status"),
            "passed with zero blocking source repairs",
        ),
        _gate(
            "provider_history_terminal",
            _status_passed(backfill)
            and backfill.get("or3_acceptance_passed") is True
            and int(backfill.get("remaining_partition_count") or 0) == 0,
            {
                "status": backfill.get("status"),
                "remaining_partitions": backfill.get("remaining_partition_count"),
            },
            "all provider partitions acquired or honestly classified",
        ),
        _gate(
            "point_in_time_and_backtest_passed",
            _status_passed(point_in_time) and _status_passed(backtest),
            {
                "point_in_time": point_in_time.get("status"),
                "backtest": backtest.get("status"),
                "validated_edges": backtest.get("validated_edge_count", 0),
            },
            "both checks pass; zero validated edges is allowed",
        ),
        _gate(
            "foundry_akber_risk_router_implemented",
            all(
                _status_passed(payload, allow_maturing=True)
                for payload in (foundry, akber, risk, router)
            ),
            {
                "foundry": foundry.get("status"),
                "akber": akber.get("status"),
                "risk": risk.get("status"),
                "router": router.get("status"),
            },
            "all class-aware research and routing validators pass",
        ),
        _gate(
            "experimental_eligibility_implemented",
            eligibility.get("status") == "passed"
            and eligibility.get("zero_candidate_ready_idle_allowed") is True,
            {
                "status": eligibility.get("status"),
                "operating_state": eligibility.get("operating_state"),
            },
            "passed and zero-candidate ready_idle is healthy",
        ),
        _gate(
            "lifecycle_and_proof_tiers_implemented",
            _status_passed(lifecycle, allow_maturing=True)
            and int(lifecycle.get("mirror_record_backfill_proof_credit_count") or 0) == 0,
            lifecycle.get("status"),
            "implementation ready with no historical proof credit",
        ),
        _gate(
            "release_trial_and_soak_contracts_implemented",
            all(
                payload.get("implementation_ready") is True
                and int(payload.get("validation_error_count") or 0) == 0
                for payload in (release, trial, soak)
            ),
            {
                "release": release.get("status"),
                "trial": trial.get("status"),
                "soak": soak.get("status"),
            },
            "all three implementation validators pass independently of operation",
        ),
        _gate(
            "operator_service_contract_implemented",
            service.get("implementation_ready") is True
            and int(service.get("validation_error_count") or 0) == 0,
            service.get("status"),
            "service definition and safety checks pass",
        ),
        _gate(
            "active_edge_research_operational",
            active_edge_research.get("status") == "operational"
            and active_edge_research.get("operational") is True
            and active_edge_research.get(
                "automatic_strategy_progression_operational"
            )
            is True
            and not active_edge_research.get("blockers")
            and int(active_edge_research.get("paper_order_created_count") or 0) == 0
            and int(active_edge_research.get("broker_write_count") or 0) == 0
            and int(active_edge_research.get("proof_credit_count") or 0) == 0,
            {
                "status": active_edge_research.get("status"),
                "empirical_state": active_edge_research.get("empirical_state"),
                "edge_proven": active_edge_research.get("edge_proven"),
                "automatic_strategy_progression_operational": (
                    active_edge_research.get(
                        "automatic_strategy_progression_operational"
                    )
                ),
            },
            (
                "real provider research is operational and can progress a bounded "
                "strategy automatically; a currently proven edge is not required"
            ),
        ),
        _gate(
            "protected_dashboard_ux_preserved",
            dashboard["protected_ux_preserved"] is True,
            dashboard["matching_asset_count"],
            f"{dashboard['asset_count']} approved assets match exactly",
        ),
    ]


def _negative_safety_probes(runtime: Path, dashboard: dict[str, Any]) -> list[dict[str, Any]]:
    policy = read_json(runtime / "qadam_experimental_paper_policy.json")
    mode = read_json(runtime / "qadam_execution_mode.json")
    migration = read_json(runtime / "qadam_experimental_contract_migration.json")
    release = read_json(runtime / "qadam_experimental_paper_release_checks.json")
    trial = read_json(runtime / "qadam_30_day_paper_growth_trial_summary.json")
    proof = read_json(runtime / "qadam_paper_proof_eligibility.json")
    eligibility = read_json(runtime / "qadam_experimental_paper_eligibility.json")
    router = read_json(runtime / "qadam_router_v3_paperops_checks.json")
    route = policy.get("route") if isinstance(policy.get("route"), dict) else {}
    risk = policy.get("risk") if isinstance(policy.get("risk"), dict) else {}
    calendar = policy.get("calendar") if isinstance(policy.get("calendar"), dict) else {}
    return [
        _gate(
            "live_capital_and_live_route_denied",
            policy.get("live_capital_enabled") is False
            and mode.get("live_capital_enabled") is False
            and route.get("alpaca_paper_endpoint") == PAPER_ENDPOINT
            and route.get("direct_broker_call_allowed") is False,
            {
                "policy_live_capital": policy.get("live_capital_enabled"),
                "mode_live_capital": mode.get("live_capital_enabled"),
                "endpoint": route.get("alpaca_paper_endpoint"),
            },
            "paper endpoint only, direct broker calls false, live capital false",
        ),
        _gate(
            "canonical_wrapper_only",
            route.get("canonical_wrapper")
            == f".venv/bin/python {CANONICAL_WRAPPER}"
            and release.get("canonical_wrapper_only") is True
            and int(release.get("direct_broker_call_count") or 0) == 0,
            route.get("canonical_wrapper"),
            f".venv/bin/python {CANONICAL_WRAPPER}",
        ),
        _gate(
            "risk_ceiling_frozen",
            float(risk.get("absolute_trade_ceiling_usd") or 0)
            == ABSOLUTE_TRADE_CEILING_USD
            and risk.get("risk_or_authority_mutation_allowed") is False,
            risk,
            "US$5,000 ceiling and no autonomous risk mutation",
        ),
        _gate(
            "legacy_rows_never_upgraded",
            int(migration.get("legacy_rows_upgraded_to_experimental") or 0) == 0
            and int(migration.get("legacy_rows_upgraded_to_validated") or 0) == 0,
            {
                "experimental": migration.get("legacy_rows_upgraded_to_experimental"),
                "validated": migration.get("legacy_rows_upgraded_to_validated"),
            },
            "both counts zero",
        ),
        _gate(
            "experimental_candidate_is_not_order_or_edge",
            eligibility.get("candidate_is_not_order") is True
            and eligibility.get("proof_credit_allowed") is False
            and eligibility.get("live_capital_enabled") is False,
            eligibility.get("status"),
            "candidate is review input only with no edge, order, proof, or live authority",
        ),
        _gate(
            "router_and_handoff_negative_probes_passed",
            router.get("status") == "passed"
            and int(router.get("validation_error_count") or 0) == 0
            and int(router.get("paper_order_created_count") or 0) == 0
            and int(router.get("broker_write_count") or 0) == 0,
            router.get("status"),
            "passed with zero orders and broker writes",
        ),
        _gate(
            "calendar_cannot_be_fabricated",
            calendar.get("backfill_allowed") is False
            and calendar.get("simulated_elapsed_time_allowed") is False
            and trial.get("backfill_used") is False
            and trial.get("simulated_elapsed_time_used") is False,
            {
                "backfill": trial.get("backfill_used"),
                "simulated": trial.get("simulated_elapsed_time_used"),
            },
            "all false",
        ),
        _gate(
            "experimental_outcome_cannot_grant_edge_credit",
            int(trial.get("validated_edge_evidence_count") or 0) == 0
            and int(trial.get("validated_edge_credit_count") or 0) == 0
            and int(proof.get("mirror_record_backfill_proof_credit_count") or 0) == 0,
            {
                "trial_edge_evidence": trial.get("validated_edge_evidence_count"),
                "trial_edge_credit": trial.get("validated_edge_credit_count"),
                "historical_backfill_credit": proof.get(
                    "mirror_record_backfill_proof_credit_count"
                ),
            },
            "all counts zero",
        ),
        _gate(
            "no_forced_trades_or_silent_promotion",
            trial.get("no_forced_trades") is True
            and trial.get("automatic_strategy_promotion_allowed") is False,
            {
                "no_forced_trades": trial.get("no_forced_trades"),
                "automatic_promotion": trial.get(
                    "automatic_strategy_promotion_allowed"
                ),
            },
            "no forced trades and no automatic promotion",
        ),
        _gate(
            "dashboard_ux_and_authority_boundary_preserved",
            dashboard["protected_ux_preserved"] is True,
            dashboard["matching_asset_count"],
            f"{dashboard['asset_count']} approved dashboard assets unchanged",
        ),
    ]


def _operation_gates(runtime: Path) -> list[dict[str, Any]]:
    broker = read_json(runtime / "qadam_clean_broker_account_preflight.json")
    mirror = read_json(runtime / "alpaca_paper_mirror.json")
    epoch = read_json(runtime / "current_paper_epoch.json")
    cutover = read_json(runtime / "qadam_clean_epoch_cutover_receipt.json")
    dashboard = read_json(runtime / "qadam_dashboard_epoch_isolation.json")
    service = read_json(runtime / "qadam_operator_service_checks.json")
    release = read_json(runtime / "qadam_experimental_paper_release_readiness.json")
    release_checks = read_json(runtime / "qadam_experimental_paper_release_checks.json")
    lock = read_json(runtime / "qadam_long_backtest_lock.json")
    mode = read_json(runtime / "qadam_execution_mode.json")
    eligibility = read_json(runtime / "qadam_experimental_paper_eligibility.json")
    router = read_json(runtime / "qadam_router_v3_paperops_checks.json")
    trial = read_json(runtime / "qadam_30_day_paper_growth_trial_summary.json")
    snapshot = mirror.get("snapshot") if isinstance(mirror.get("snapshot"), dict) else {}
    epoch_fingerprint = str(epoch.get("broker_account_fingerprint") or "")
    cutover_fingerprint = str(cutover.get("broker_account_fingerprint") or "")
    mirror_fingerprint = str(
        mirror.get("broker_account_fingerprint")
        or snapshot.get("broker_account_fingerprint")
        or ""
    )
    return [
        _gate(
            "active_bound_100000_usd_alpaca_paper_epoch",
            cutover.get("provider_backed_initial_mirror") is True
            and abs(float(cutover.get("starting_balance") or 0) - STARTING_BALANCE_USD)
            <= 0.01
            and broker.get("paper_endpoint_verified") is True
            and mirror.get("status") == "ok"
            and _fresh({"generated_at": snapshot.get("observed_at")}, seconds=600)
            and mirror.get("paper_epoch_id") == epoch.get("paper_epoch_id")
            and mirror.get("paper_epoch_kind")
            == "clean_experimental_operator_epoch"
            and snapshot.get("account_currency") == "USD"
            and mirror.get("broker_reconciliation_status") in {
                "ok",
                "history_unavailable",
            }
            and bool(epoch_fingerprint)
            and epoch_fingerprint == cutover_fingerprint == mirror_fingerprint,
            {
                "mirror_status": mirror.get("status"),
                "mirror_observed_at": snapshot.get("observed_at"),
                "paper_epoch_id": mirror.get("paper_epoch_id"),
                "starting_balance": cutover.get("starting_balance"),
                "current_equity": snapshot.get("equity"),
                "positions": mirror.get("position_count"),
                "orders": mirror.get("order_count"),
                "account_binding_matches": bool(epoch_fingerprint)
                and epoch_fingerprint == cutover_fingerprint == mirror_fingerprint,
            },
            (
                "fresh read-only Alpaca Paper mirror bound to the immutable clean "
                "US$100,000 epoch; positions and orders may change after launch"
            ),
        ),
        _gate(
            "clean_experimental_epoch_active",
            epoch.get("paper_epoch_kind") == "clean_experimental_operator_epoch"
            and abs(float(epoch.get("starting_balance") or 0) - STARTING_BALANCE_USD)
            <= 0.01
            and epoch.get("account_currency") == "USD",
            {
                "kind": epoch.get("paper_epoch_kind"),
                "balance": epoch.get("starting_balance"),
                "currency": epoch.get("account_currency"),
            },
            "clean_experimental_operator_epoch at US$100,000 USD",
        ),
        _gate(
            "testing_epoch_archived_and_cutover_complete",
            cutover.get("cutover_executed") is True
            and cutover.get("cutover_mode") == "experimental_unvalidated"
            and cutover.get("testing_epoch_archived") is True
            and cutover.get("paper_epoch_id") == epoch.get("paper_epoch_id"),
            cutover.get("status"),
            "experimental cutover completed with archived legacy epoch",
        ),
        _gate(
            "dashboard_current_epoch_isolated",
            dashboard.get("status") == "passed"
            and int(dashboard.get("archived_identifier_leak_count") or 0) == 0
            and int(dashboard.get("legacy_epoch_marker_count") or 0) == 0,
            dashboard.get("status"),
            "passed with zero legacy leaks",
        ),
        _gate(
            "experimental_release_effective",
            release.get("experimental_paper_release_effective") is True
            and release_checks.get("experimental_paper_launch_complete") is True
            and release.get("policy_version") == POLICY_VERSION
            and release.get("risk_policy_version") == RISK_POLICY_VERSION,
            release.get("status"),
            "effective, approved, version-bound experimental paper release",
        ),
        _gate(
            "operator_service_running",
            service.get("service_running") is True and _fresh(service, seconds=600),
            {
                "status": service.get("status"),
                "running": service.get("service_running"),
            },
            "fresh running supervised service",
        ),
        _gate(
            "paperops_lock_narrowly_released",
            lock.get("status") == "released"
            and lock.get("paperops_watch_only_mode") is False
            and mode.get("experimental_paper_enabled") is True
            and mode.get("validated_paper_enabled") is False
            and mode.get("live_capital_enabled") is False,
            {
                "lock": lock.get("status"),
                "watch_only": lock.get("paperops_watch_only_mode"),
                "experimental": mode.get("experimental_paper_enabled"),
                "live": mode.get("live_capital_enabled"),
            },
            "experimental paper enabled only; validated/live authority false",
        ),
        _gate(
            "eligibility_and_router_healthy",
            eligibility.get("status") in {"ready_idle", "candidate_available"}
            and router.get("status") == "passed",
            {
                "eligibility": eligibility.get("status"),
                "router": router.get("status"),
            },
            "healthy ready_idle or candidate_available through passing Router",
        ),
        _gate(
            "real_trial_calendar_running",
            trial.get("status") in {"active", "complete_pending_operator_review"}
            and trial.get("paper_epoch_id") == epoch.get("paper_epoch_id")
            and trial.get("backfill_used") is False
            and trial.get("simulated_elapsed_time_used") is False,
            {
                "status": trial.get("status"),
                "trial_day": trial.get("trial_day"),
            },
            "real current-epoch 30-day paper growth trial active",
        ),
    ]


def build_autonomous_experimental_paper_epoch_certification(
    settings: Settings | None = None,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    dashboard = _dashboard_hash_audit()
    implementation_gates = _implementation_gates(runtime, dashboard)
    negative_probes = _negative_safety_probes(runtime, dashboard)
    operation_gates = _operation_gates(runtime)
    soak = read_json(runtime / "qadam_operator_soak_v3.json")
    trial = read_json(runtime / "qadam_30_day_paper_growth_trial_summary.json")
    edge = read_json(runtime / "qadam_edge_registry_summary.json")
    quantum = read_json(runtime / "qadam_nonlinear_quantum_value_checks.json")
    why_not = read_json(runtime / "qadam_router_v3_why_not_trading_now.json")
    repairs = read_json(runtime / "qadam_operator_repair_queue.json")
    lifecycle = read_json(runtime / "qadam_paper_lifecycle_v3.json")
    proof = read_json(runtime / "qadam_paper_proof_eligibility.json")
    portfolio = read_json(runtime / "qsase_dashboard_status.json").get(
        "dashboard_portfolio", {}
    )

    implementation_complete = all(row["passed"] for row in implementation_gates) and all(
        row["passed"] for row in negative_probes
    )
    operation_running = implementation_complete and all(
        row["passed"] for row in operation_gates
    )
    unattended = bool(
        operation_running
        and soak.get("unattended_reliability_certified") is True
        and int(soak.get("completed_real_session_count") or 0) >= 7
    )
    implementation_blockers = [
        row["gate_id"] for row in implementation_gates + negative_probes if not row["passed"]
    ]
    operation_blockers = [row["gate_id"] for row in operation_gates if not row["passed"]]
    reliability_blockers = [] if unattended else list(soak.get("blockers") or [])
    if operation_running is False and "operation_not_running" not in reliability_blockers:
        reliability_blockers.insert(0, "operation_not_running")

    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_autonomous_experimental_paper_epoch_certification",
        "generated_at": now_iso(),
        "status": (
            "fully_operational_and_unattended_reliability_certified"
            if unattended
            else "autonomous_experimental_paper_operation_running_soak_in_progress"
            if operation_running
            else "implementation_complete_waiting_for_operational_cutover"
            if implementation_complete
            else "implementation_blocked"
        ),
        "implementation_complete": implementation_complete,
        "autonomous_experimental_paper_operation_running": operation_running,
        "unattended_reliability_certified": unattended,
        "implementation_gates": implementation_gates,
        "negative_safety_probes": negative_probes,
        "operation_gates": operation_gates,
        "implementation_blocker_count": len(implementation_blockers),
        "implementation_blockers": implementation_blockers,
        "operation_blocker_count": len(operation_blockers),
        "operation_blockers": operation_blockers,
        "unattended_reliability_blockers": unique_errors(reliability_blockers),
        "dashboard_ux_protection": dashboard,
        "trial": {
            "state": trial.get("status"),
            "day": int(trial.get("trial_day") or 0),
            "calendar_days_remaining": int(trial.get("calendar_days_remaining") or 30),
            "submitted_paper_order_count": int(
                trial.get("submitted_paper_order_count") or 0
            ),
            "open_position_count": int(trial.get("open_position_count") or 0),
            "closed_paper_trade_count": int(
                trial.get("closed_paper_trade_count") or 0
            ),
            "experimental_forward_outcome_count": int(
                trial.get("experimental_forward_outcome_count") or 0
            ),
            "net_paper_pnl_usd": trial.get("net_paper_pnl_usd"),
            "net_paper_return_pct": trial.get("net_paper_return_pct"),
            "drawdown_pct": trial.get("drawdown_pct"),
        },
        "validated_edge_count": int(edge.get("validated_edge_count") or 0),
        "broker_execution_fact_count": int(proof.get("broker_execution_fact_count") or 0),
        "lifecycle": {
            "order_record_count": int(lifecycle.get("order_record_count") or 0),
            "open_position_count": int(lifecycle.get("position_record_count") or 0),
            "closed_trade_count": int(lifecycle.get("closed_trade_record_count") or 0),
            "ambiguous_order_count": int(lifecycle.get("ambiguous_order_count") or 0),
        },
        "portfolio": {
            "current_value_usd": portfolio.get("current_value")
            or portfolio.get("current_value_usd"),
            "drawdown_pct": portfolio.get("drawdown_pct"),
        },
        "quantum": {
            "status": quantum.get("status"),
            "review_mode": quantum.get("quantum_review_mode")
            or quantum.get("execution_mode")
            or "not_reported",
            "advantage_state": quantum.get("quantum_advantage_state")
            or quantum.get("quantum_usefulness_state")
            or "unproven",
        },
        "why_not_trading_now": why_not.get("primary_reason")
        or why_not.get("plain_english_reason")
        or "No current Router explanation was recorded.",
        "active_repair_request_count": int(repairs.get("open_request_count") or 0),
        "critical_repair_request_count": int(repairs.get("critical_request_count") or 0),
        "paper_only": True,
        "live_capital_enabled": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "paper_calendar_advanced_by_certifier": False,
        "authority": authority_flags(),
    }


def validate_autonomous_experimental_paper_epoch_certification(
    certification: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if certification.get("implementation_complete") is True:
        if certification.get("implementation_blockers"):
            errors.append("implementation_complete_with_blockers")
        if not all(
            row.get("passed") is True
            for row in certification.get("implementation_gates", [])
            + certification.get("negative_safety_probes", [])
        ):
            errors.append("implementation_complete_with_failed_gate")
    if certification.get("autonomous_experimental_paper_operation_running") is True:
        if certification.get("implementation_complete") is not True:
            errors.append("operation_running_without_complete_implementation")
        if certification.get("operation_blockers"):
            errors.append("operation_running_with_blockers")
        if not all(
            row.get("passed") is True
            for row in certification.get("operation_gates", [])
        ):
            errors.append("operation_running_with_failed_gate")
    if certification.get("unattended_reliability_certified") is True:
        if certification.get("autonomous_experimental_paper_operation_running") is not True:
            errors.append("unattended_reliability_without_running_operation")
    if certification.get("dashboard_ux_protection", {}).get(
        "protected_ux_preserved"
    ) is not True:
        errors.append("protected_dashboard_ux_changed")
    if certification.get("paper_only") is not True:
        errors.append("certification_not_paper_only")
    if certification.get("live_capital_enabled") is not False:
        errors.append("certification_live_capital_enabled")
    for field in (
        "paper_order_created_count",
        "broker_write_count",
        "proof_credit_created_count",
    ):
        if int(certification.get(field) or 0) != 0:
            errors.append(f"certifier_forbidden_count:{field}")
    if certification.get("paper_calendar_advanced_by_certifier") is not False:
        errors.append("certifier_advanced_paper_calendar")
    errors.extend(
        validate_authority(certification.get("authority", {}), prefix="experimental_cert")
    )
    return unique_errors(errors)


def build_and_write_autonomous_experimental_paper_epoch_certification(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    certification = build_autonomous_experimental_paper_epoch_certification(settings)
    errors = validate_autonomous_experimental_paper_epoch_certification(certification)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_autonomous_experimental_paper_epoch_checks",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "implementation_complete": certification["implementation_complete"],
        "autonomous_experimental_paper_operation_running": certification[
            "autonomous_experimental_paper_operation_running"
        ],
        "unattended_reliability_certified": certification[
            "unattended_reliability_certified"
        ],
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store = AtomicArtifactStore(runtime_dir(settings))
    store.write_json(CERTIFICATION_ARTIFACT, certification)
    store.write_json(CHECK_ARTIFACT, checks)
    return certification, checks, errors


__all__ = [
    "CERTIFICATION_ARTIFACT",
    "CHECK_ARTIFACT",
    "PROTECTED_DASHBOARD_HASHES",
    "build_and_write_autonomous_experimental_paper_epoch_certification",
    "build_autonomous_experimental_paper_epoch_certification",
    "validate_autonomous_experimental_paper_epoch_certification",
]
