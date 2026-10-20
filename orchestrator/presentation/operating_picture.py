"""Public read model separating operational, evidence, decision and economic states."""

from datetime import datetime


def read_shared_brief(runtime, now: str) -> dict:
    from orchestrator.presentation.generations import read_projection
    from orchestrator.qadam_artifact_generations import GenerationError

    try:
        snapshot = read_projection(runtime)
    except (OSError, ValueError, GenerationError):
        return {"generation_id": None, "text": "Dashboard snapshot unavailable; shared figures could not be verified."}
    if snapshot is None:
        return {"generation_id": None, "text": ""}
    primary = snapshot[0].get("qsase_dashboard_status.json", {})
    picture = primary.get("operating_picture") or {}
    if not picture:
        return {"generation_id": snapshot[1], "text": "Shared operating figures are not yet available."}
    rows = {row["key"]: row for row in picture.get("dimensions", [])}

    def value(key, maximum_age):
        row = rows.get(key, {})
        if not _current({"generated_at": row.get("observed_at")}, now, maximum_age):
            return None
        return row.get("value")

    sources = value("evidence", 1800)
    reviews = value("economics", 21600)
    text = (f"Evidence: {sources} provider-backed sources current." if sources is not None
            else "Evidence coverage is stale or unavailable.")
    text += (f" Learning: {reviews} strategy versions eligible for review."
             if reviews is not None else " Learning review is stale or unavailable.")
    text += " Review eligibility is not a validated edge."
    execution = picture.get("execution_health") or {}
    if picture.get("critical_execution_failure") is True:
        text += " Execution needs attention: " + ", ".join(execution.get("blockers") or ["not verified"]) + "."
    activity = picture.get("trading_activity") or {}
    if activity.get("available") and _current({"generated_at": activity.get("as_of")}, now, 1800):
        counts = activity.get("counts") or {}
        text += (f" Last seven calendar days: {counts.get('broker_acknowledged_entries', 0)} acknowledged entries, "
                 f"{counts.get('filled_exit_orders', 0)} filled exit orders; "
                 f"{activity.get('independent_acknowledged_entry_events', 0)} identified entry events.")
    return {"generation_id": snapshot[1], "text": text}


def _current(document: dict, now: str, max_age: int) -> bool:
    try:
        age = (datetime.fromisoformat(now.replace("Z", "+00:00")) -
               datetime.fromisoformat(document["generated_at"].replace("Z", "+00:00"))).total_seconds()
        return 0 <= age <= max_age
    except (KeyError, ValueError, TypeError, AttributeError):
        return False


def build_picture(*, operator: dict, capability: dict, router: dict, tournament: dict,
                  ledger: dict, generated_at: str, research_economics: dict | None = None,
                  execution_health: dict | None = None, publication: dict | None = None) -> dict:
    system_current = _current(operator, generated_at, 1800)
    evidence_current = _current(capability, generated_at, 1800)
    decision_current = _current(router, generated_at, 1800)
    economics_current = _current(tournament, generated_at, 21600)
    coverage = capability.get("counts") or {}
    candidates = tournament.get("candidates") or []
    health = execution_health or ledger.get("health_dimensions") or {}
    execution_degraded = health.get("status") != "healthy"
    publication = publication or {}
    publication_current = publication.get("published") is True and _current(publication, generated_at, 600)
    return {
        "schema_version": "qadam-operating-picture.1", "generated_at": generated_at,
        "public_safe": True, "read_only": True, "paper_only": True,
        "execution_health": health,
        "critical_execution_failure": execution_degraded,
        "operationally_ready": bool(system_current and operator.get("operational_ready") is True
                                   and not execution_degraded and publication_current),
        "publication_health": {"current": publication_current, "state": publication.get("status", "unverified"),
                               "reason": publication.get("reason"), "observed_at": publication.get("generated_at")},
        "dimensions": [
            {"key": "operations", "label": "System operation",
             "state": "current" if system_current else "stale_or_unavailable",
             "observed_at": operator.get("generated_at"),
             "value": operator.get("status") if system_current else None,
             "open_circuits": operator.get("open_circuit_count") if system_current else None},
            {"key": "evidence", "label": "Evidence supply",
             "state": "current" if evidence_current else "stale_or_unavailable",
             "observed_at": capability.get("generated_at"),
             "value": coverage.get("provider_backed_current") if evidence_current else None,
             "catalogue_count": coverage.get("catalogue"), "catalogue_is_live_coverage": False},
            {"key": "decisions", "label": "Experiment progression",
             "state": "current" if decision_current else "stale_or_unavailable",
             "observed_at": router.get("generated_at"),
             "value": router.get("current_router_state") if decision_current else None,
             "handoff_count": router.get("handoff_count") if decision_current else None,
             "handoff_is_fill": False},
            {"key": "economics", "label": "Economic evidence",
             "state": "current" if economics_current else "stale_or_unavailable",
             "observed_at": tournament.get("generated_at"),
             "value": tournament.get("emerging_review_eligible_count") if economics_current else None,
             "review_is_validated_edge": False},
        ],
        "strategy_reviews": [{key: row.get(key) for key in (
            "strategy_version_id", "strategy_family_id", "state", "registered_at",
            "independent_outcome_count", "next_checkpoint", "observation_timetable",
            "next_review_checkpoint", "mean_net_return", "mean_benchmark_delta",
            "return_dispersion_stdev", "worst_event_net_return", "largest_positive_event_share",
            "equal_notional_event_curve_max_drawdown", "event_curve_is_actual_portfolio_drawdown",
            "regime_observation_counts", "exclusion_counts", "eligible_for_emerging_review")}
            for row in candidates[-100:] if isinstance(row, dict)],
        "active_version_coverage": tournament.get("active_version_coverage"),
        "outcome_accounting": {key: (ledger.get("outcome_accounting") or {}).get(key) for key in (
            "closed_record_count", "exact_entry_attribution_count", "exact_multi_entry_allocation_count",
            "unresolved_attribution_count", "modelled_cost_lot_count", "cost_measured_count")},
        "research_economics": research_economics or {
            "subscription_expense_usd": None, "model_expense_usd": None,
            "cost_state": "not_reconciled_to_provider_bills",
            "source_marginal_value": "requires_preregistered_source_ablation",
            "paper_pnl_is_cash_income": False, "automatic_budget_expansion": False},
        "health_implies_profitability": False, "paper_order_allowed": False,
        "broker_write_count": 0, "live_capital_enabled": False,
    }
