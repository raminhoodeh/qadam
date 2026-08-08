"""EF-9 public-safe evidence-fit dashboard and notification projection.

The projection explains how current evidence moves through Qadam. It is a
read-only mirror: it cannot create research hypotheses, trading candidates,
approvals, handoffs, orders, broker writes, proof credit, or live authority.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_json,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_wave_b_common import stable_id

SCHEMA_VERSION = "qadam_evidence_fit_visibility.v1"
PHASE_ID = "EF-9"

DASHBOARD_ARTIFACT = "qadam_evidence_fit_dashboard_summary.json"
FUNNEL_ARTIFACT = "qadam_strategy_conversion_funnel.json"
MATERIAL_CHANGES_ARTIFACT = "qadam_material_research_changes.jsonl"
NOTIFICATION_CANDIDATES_ARTIFACT = (
    "qadam_evidence_fit_notification_candidates.jsonl"
)
CHECK_ARTIFACT = "qadam_evidence_fit_visibility_checks.json"

SOURCE_CONTRACT_ARTIFACT = "qadam_strategy_source_contract.json"
INSTRUMENT_REGISTRY_ARTIFACT = "qadam_instrument_role_registry.json"
TRIGGER_SUMMARY_ARTIFACT = "qadam_trigger_factory_summary.json"
EVENT_TRIGGERS_ARTIFACT = "qadam_current_event_triggers.jsonl"
REGIME_ARTIFACT = "qadam_current_regime_observations.jsonl"
DISLOCATIONS_ARTIFACT = "qadam_current_market_dislocations.jsonl"
DIRECTIONS_ARTIFACT = "qadam_direction_resolutions.jsonl"
HYPOTHESES_ARTIFACT = "qadam_strategy_hypotheses_v3.jsonl"
AKBER_RESULTS_ARTIFACT = "qadam_akber_filter_v3_results.jsonl"
ROUTER_DECISIONS_ARTIFACT = "qadam_router_v3_decisions.jsonl"
ROUTER_ROOT_ARTIFACT = "qadam_router_root_cause_summary.json"
TRIAL_FUNNEL_ARTIFACT = "qadam_active_discovery_conversion_funnel.jsonl"
TRIAL_CERTIFICATION_ARTIFACT = "qadam_active_discovery_trial_certification.json"
OUTCOMES_ARTIFACT = "qadam_active_discovery_outcomes.jsonl"
PROMOTIONS_ARTIFACT = "qadam_strategy_promotion_proposals.jsonl"
ADMISSIONS_ARTIFACT = "qadam_strategy_admission_decisions.jsonl"
PAPER_LINEAGE_ARTIFACT = "qadam_paper_trade_lineage.jsonl"
QUANTUM_SUMMARY_ARTIFACT = "qadam_quantum_usefulness_summary.json"

MATERIAL_HISTORY_LIMIT = 100
NOTIFICATION_HISTORY_LIMIT = 100


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _latest(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return rows[-1] if rows else {}


def _strategy_id(record: dict[str, Any]) -> str:
    mapping = record.get("strategy_mapping")
    mapping = mapping if isinstance(mapping, dict) else {}
    return str(
        record.get("strategy_family_id")
        or record.get("strategy_family")
        or mapping.get("strategy_family_id")
        or "unclassified"
    )


def _instrument(record: dict[str, Any]) -> str | None:
    mapping = record.get("instrument_proxy_mapping")
    mapping = mapping if isinstance(mapping, dict) else {}
    return (
        record.get("instrument")
        or record.get("observed_instrument")
        or mapping.get("execution_proxy")
    )


def _direction(record: dict[str, Any]) -> str:
    horizon = record.get("direction_horizon")
    horizon = horizon if isinstance(horizon, dict) else {}
    return str(record.get("actionable_direction") or horizon.get("direction") or "abstain")


def _evidence_profile(record: dict[str, Any]) -> str:
    confirmation = record.get("catalyst_confirmation")
    confirmation = confirmation if isinstance(confirmation, dict) else {}
    return str(record.get("evidence_profile") or confirmation.get("evidence_profile") or "unclassified")


def _plain_root_cause(value: str) -> str:
    labels = {
        "market_closed": "The market session is closed.",
        "no_real_trigger": "No strategy-specific trigger is active.",
        "source_outage": "A required provider is unavailable.",
        "mapping_defect": "A source or instrument mapping needs repair.",
        "evidence_conversion_defect": "Observed evidence did not reach the next schema correctly.",
        "akber_hold": "Akber is waiting for required current context.",
        "akber_veto": "Akber found measured adverse evidence.",
        "risk_veto": "Portfolio risk rejected the setup.",
        "duplicate_exposure": "The portfolio already has conflicting exposure.",
        "route_failure": "The guarded paper route is unavailable.",
    }
    return labels.get(value, value.replace("_", " ").strip().capitalize() or "No current blocker")


def _source_area(source_contract: dict[str, Any]) -> dict[str, Any]:
    availability = source_contract.get("availability_counts") or {}
    roles = source_contract.get("role_counts") or {}
    profile_freshness: dict[str, Counter[str]] = defaultdict(Counter)
    trigger_sources: dict[str, list[str]] = defaultdict(list)
    for source in source_contract.get("sources") or []:
        if not isinstance(source, dict):
            continue
        freshness = str(source.get("freshness_status") or "not_reported")
        for strategy_id in source.get("strategy_family_ids") or []:
            profile_freshness[str(strategy_id)][freshness] += 1
            if source.get("current_trigger_active") is True:
                trigger_sources[str(strategy_id)].append(
                    str(source.get("source_name") or source.get("source_key"))
                )
    usable = _int(availability.get("live_fresh")) + _int(
        availability.get("supplemental_current")
    )
    return {
        "headline": f"{usable} of {_int(source_contract.get('source_count'))} registered sources are usable now",
        "summary": (
            "Registered sources are not treated as equally tradeable evidence. "
            "Qadam separates current triggers, historical support, market confirmation, "
            "supplemental context, negative controls, and unavailable providers."
        ),
        "metrics": [
            {"label": "Registered", "value": _int(source_contract.get("source_count"))},
            {"label": "Live and fresh", "value": _int(availability.get("live_fresh"))},
            {"label": "Current triggers", "value": _int(roles.get("current_trigger"))},
            {"label": "Historical support", "value": _int(roles.get("historical_causal_support"))},
            {"label": "Temporarily degraded", "value": _int(availability.get("temporarily_degraded"))},
        ],
        "profile_freshness": [
            {
                "strategy_family_id": strategy_id,
                "freshness_counts": dict(sorted(counts.items())),
                "active_trigger_sources": sorted(set(trigger_sources[strategy_id])),
            }
            for strategy_id, counts in sorted(profile_freshness.items())
        ],
        "next_action": "Refresh profile-specific sources and use only evidence whose current role and freshness permit it.",
    }


def _universe_area(registry: dict[str, Any]) -> dict[str, Any]:
    roles = registry.get("role_counts") or {}
    return {
        "headline": f"{_int(registry.get('instrument_count'))} watched instruments, {_int(registry.get('guarded_route_count'))} guarded paper expressions",
        "summary": (
            "Qadam distinguishes instruments it can observe from instruments it may express "
            "through Alpaca Paper. Futures and prediction contracts may remain research context "
            "while a listed ETF or equity acts as the approved paper proxy."
        ),
        "metrics": [
            {"label": "Watched", "value": _int(registry.get("instrument_count"))},
            {"label": "Direct paper instruments", "value": _int(roles.get("direct_paper_instrument"))},
            {"label": "Research price context", "value": _int(roles.get("research_price_context"))},
            {"label": "Prediction contracts", "value": _int(roles.get("prediction_contract_context"))},
        ],
        "next_action": "Use only a recorded direct instrument or approved proxy when a setup reaches PaperOps.",
    }


def _pattern_rows(
    directions: list[dict[str, Any]],
    hypotheses: list[dict[str, Any]],
    event_triggers: list[dict[str, Any]],
    regimes: list[dict[str, Any]],
    dislocations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    trigger_by_strategy: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in [*event_triggers, *regimes, *dislocations]:
        trigger_by_strategy[_strategy_id(row)].append(row)
    hypothesis_by_score = {
        str(row.get("score_id") or row.get("pattern_lineage", {}).get("score_id") or ""): row
        for row in hypotheses
    }
    records = []
    for row in directions:
        strategy = _strategy_id(row)
        triggers = trigger_by_strategy.get(strategy, [])
        hypothesis = hypothesis_by_score.get(str(row.get("score_id") or ""), {})
        records.append(
            {
                "score_id": row.get("score_id"),
                "strategy_family_id": strategy,
                "instrument": row.get("instrument"),
                "direction": row.get("actionable_direction"),
                "direction_state": row.get("resolution_state"),
                "evidence_profile": _evidence_profile(hypothesis),
                "current_trigger_state": "active" if triggers else "inactive",
                "current_trigger_count": len(triggers),
                "next_handoff": (
                    "Akber evidence packet"
                    if row.get("actionable_direction") in {"long", "short"} and triggers
                    else "Wait for a directionally useful current trigger"
                ),
                "explanation": row.get("explanation"),
            }
        )
    return records


def _strategy_rows(
    hypotheses: list[dict[str, Any]],
    promotions: list[dict[str, Any]],
    event_triggers: list[dict[str, Any]],
    regimes: list[dict[str, Any]],
    dislocations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    hypothesis_counts = Counter(_strategy_id(row) for row in hypotheses)
    trigger_counts = Counter(
        _strategy_id(row) for row in [*event_triggers, *regimes, *dislocations]
    )
    promotion_by_strategy = {
        _strategy_id(row): row for row in promotions
    }
    strategy_ids = sorted(set(hypothesis_counts) | set(trigger_counts) | set(promotion_by_strategy))
    return [
        {
            "strategy_family_id": strategy_id,
            "current_hypothesis_count": hypothesis_counts[strategy_id],
            "active_trigger_count": trigger_counts[strategy_id],
            "promotion_state": promotion_by_strategy.get(strategy_id, {}).get(
                "current_promotion_state", "research_observation"
            ),
            "validated_edge_present": promotion_by_strategy.get(strategy_id, {}).get(
                "validated_edge_present", False
            ),
            "real_forward_outcome_count": _int(
                promotion_by_strategy.get(strategy_id, {}).get("real_forward_outcome_count")
            ),
            "next_action": (
                "Collect unchanged forward outcomes"
                if promotion_by_strategy.get(strategy_id)
                else "Wait for a qualified directional hypothesis"
            ),
        }
        for strategy_id in strategy_ids
    ]


def build_conversion_funnel(
    *,
    source_contract: dict[str, Any],
    instrument_registry: dict[str, Any],
    trigger_summary: dict[str, Any],
    directions: list[dict[str, Any]],
    hypotheses: list[dict[str, Any]],
    akber_results: list[dict[str, Any]],
    router_decisions: list[dict[str, Any]],
    router_root: dict[str, Any],
    trial_funnel: list[dict[str, Any]],
    paper_lineage: list[dict[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    latest_trial = _latest(trial_funnel)
    latest_router = _latest(router_decisions)
    latest_akber = _latest(akber_results)
    current_root = str(
        latest_router.get("primary_root_cause")
        or router_root.get("primary_root_cause")
        or "no_real_trigger"
    )
    guarded_lineage = [
        row
        for row in paper_lineage
        if row.get("accepted_v3_handoff_verified") is True
        and row.get("proof_checks", {}).get("guarded_alpaca_paper_route") is True
    ]
    direction_counts = Counter(
        "actionable"
        if row.get("actionable_direction") in {"long", "short"}
        else "abstain"
        for row in directions
    )
    akber_counts = Counter(str(row.get("decision") or "not_reviewed") for row in akber_results)
    router_counts = Counter(str(row.get("final_state") or "not_reviewed") for row in router_decisions)
    stages = [
        {"stage": "sources", "label": "Usable sources", "count": _int((source_contract.get("availability_counts") or {}).get("live_fresh"))},
        {"stage": "instruments", "label": "Watched instruments", "count": _int(instrument_registry.get("instrument_count"))},
        {"stage": "triggers", "label": "Active triggers", "count": _int(trigger_summary.get("active_event_trigger_count")) + _int(trigger_summary.get("active_regime_count")) + _int(trigger_summary.get("active_market_dislocation_count"))},
        {"stage": "directions", "label": "Actionable directions", "count": direction_counts["actionable"]},
        {"stage": "hypotheses", "label": "Current hypotheses", "count": len(hypotheses)},
        {"stage": "akber", "label": "Akber passes", "count": akber_counts["pass"]},
        {"stage": "risk", "label": "Risk proposals", "count": _int(latest_trial.get("risk_proposals"))},
        {"stage": "router", "label": "Paper-review candidates", "count": router_counts["paper_review_candidate"] + router_counts["experimental_paper_review_candidate"]},
        {"stage": "paperops", "label": "Paper handoffs", "count": _int(latest_trial.get("paper_handoffs"))},
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_strategy_conversion_funnel",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "ready",
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "stages": stages,
        "current_setup": {
            "instrument": _instrument(latest_router) or _instrument(_latest(hypotheses)),
            "direction": latest_router.get("direction") or _direction(_latest(hypotheses)),
            "akber_state": latest_akber.get("decision") or "not_reviewed",
            "router_state": latest_router.get("final_state") or "not_reviewed",
            "primary_root_cause": current_root,
            "plain_english_root_cause": _plain_root_cause(current_root),
        },
        "historical_guarded_handoff_proof_count": len(guarded_lineage),
        "current_handoff_count": _int(latest_trial.get("paper_handoffs")),
        "paper_order_created": False,
        "broker_write_count": 0,
        "authority": authority_flags(),
    }


def _learning_area(
    outcomes: list[dict[str, Any]],
    promotions: list[dict[str, Any]],
    admissions: list[dict[str, Any]],
    quantum: dict[str, Any],
) -> dict[str, Any]:
    mature = [row for row in outcomes if row.get("matured") is True]
    positive = [
        row
        for row in mature
        if (row.get("net_return_after_costs") or row.get("realized_net_pnl") or 0) > 0
    ]
    weakened = [
        row
        for row in mature
        if (row.get("net_return_after_costs") or row.get("realized_net_pnl") or 0) <= 0
    ]
    admission_count = sum(row.get("paper_strategy_admitted") is True for row in admissions)
    return {
        "headline": f"{len(mature)} mature real outcomes; {admission_count} strategy admissions",
        "summary": (
            "Qadam keeps positive, negative, held, vetoed, and missed outcomes distinct. "
            "A proposed strategy remains unchanged until its versioned evidence and frozen-risk admission checks pass."
        ),
        "metrics": [
            {"label": "Mature outcomes", "value": len(mature)},
            {"label": "Strengthened", "value": len(positive)},
            {"label": "Weakened or inconclusive", "value": len(weakened)},
            {"label": "Promotion proposals", "value": len(promotions)},
            {"label": "Automatic admissions", "value": admission_count},
        ],
        "quantum_usefulness": {
            "state": quantum.get("status") or quantum.get("state") or "not_positive",
            "positive_attribution_allowed": quantum.get(
                "quantum_advantage_claim_allowed", False
            ) is True,
        },
        "next_action": "Let real horizons mature, then retest unchanged strategy versions before any promotion.",
    }


def _material_fingerprint(payload: dict[str, Any]) -> str:
    return sha256_json(
        {
            "funnel": payload.get("funnel", {}).get("stages"),
            "current_setup": payload.get("funnel", {}).get("current_setup"),
            "promotion_states": [
                (row.get("strategy_family_id"), row.get("promotion_state"), row.get("real_forward_outcome_count"))
                for row in payload.get("strategy_rows", [])
            ],
            "mature_outcomes": payload.get("areas", {}).get("learning", {}).get("metrics", [])[0:1],
        }
    )


def _notification_body(funnel: dict[str, Any], trigger_count: int) -> str:
    setup = funnel.get("current_setup") or {}
    instrument = setup.get("instrument") or "No instrument"
    direction = str(setup.get("direction") or "abstain").lower()
    root = setup.get("plain_english_root_cause") or "No current setup is ready."
    handoffs = _int(funnel.get("current_handoff_count"))
    return (
        f"Evidence update: the {instrument} setup points {direction}. {root} "
        f"{trigger_count} current triggers; {handoffs} PaperOps handoffs."
    )


def build_evidence_fit_visibility_state(
    settings: Settings | None = None,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    generated = generated_at or now_iso()
    source_contract = read_json(runtime / SOURCE_CONTRACT_ARTIFACT)
    instrument_registry = read_json(runtime / INSTRUMENT_REGISTRY_ARTIFACT)
    trigger_summary = read_json(runtime / TRIGGER_SUMMARY_ARTIFACT)
    event_triggers = read_jsonl(runtime / EVENT_TRIGGERS_ARTIFACT)
    regimes = read_jsonl(runtime / REGIME_ARTIFACT)
    dislocations = read_jsonl(runtime / DISLOCATIONS_ARTIFACT)
    directions = read_jsonl(runtime / DIRECTIONS_ARTIFACT)
    hypotheses = read_jsonl(runtime / HYPOTHESES_ARTIFACT)
    akber_results = read_jsonl(runtime / AKBER_RESULTS_ARTIFACT)
    router_decisions = read_jsonl(runtime / ROUTER_DECISIONS_ARTIFACT)
    router_root = read_json(runtime / ROUTER_ROOT_ARTIFACT)
    trial_funnel = read_jsonl(runtime / TRIAL_FUNNEL_ARTIFACT)
    trial_certification = read_json(runtime / TRIAL_CERTIFICATION_ARTIFACT)
    outcomes = read_jsonl(runtime / OUTCOMES_ARTIFACT)
    promotions = read_jsonl(runtime / PROMOTIONS_ARTIFACT)
    admissions = read_jsonl(runtime / ADMISSIONS_ARTIFACT)
    paper_lineage = read_jsonl(runtime / PAPER_LINEAGE_ARTIFACT)
    quantum = read_json(runtime / QUANTUM_SUMMARY_ARTIFACT)

    funnel = build_conversion_funnel(
        source_contract=source_contract,
        instrument_registry=instrument_registry,
        trigger_summary=trigger_summary,
        directions=directions,
        hypotheses=hypotheses,
        akber_results=akber_results,
        router_decisions=router_decisions,
        router_root=router_root,
        trial_funnel=trial_funnel,
        paper_lineage=paper_lineage,
        generated_at=generated,
    )
    pattern_rows = _pattern_rows(
        directions, hypotheses, event_triggers, regimes, dislocations
    )
    strategy_rows = _strategy_rows(
        hypotheses, promotions, event_triggers, regimes, dislocations
    )
    current_setup = funnel["current_setup"]
    areas = {
        "sources": _source_area(source_contract),
        "universe": _universe_area(instrument_registry),
        "patterns": {
            "headline": f"{len(pattern_rows)} directional research records; {sum(row['current_trigger_state'] == 'active' for row in pattern_rows)} currently triggered",
            "summary": "Each row now shows its direction, evidence profile, current trigger state, and next handoff. Research scores still rank investigations; they do not claim a probability of profit.",
            "metrics": [
                {"label": "Direction records", "value": len(pattern_rows)},
                {"label": "Actionable directions", "value": sum(row["direction"] in {"long", "short"} for row in pattern_rows)},
                {"label": "Active trigger links", "value": sum(row["current_trigger_count"] for row in pattern_rows)},
            ],
            "next_action": "Advance only records with a current profile-specific trigger into one same-generation Akber packet.",
        },
        "strategies": {
            "headline": f"{len(strategy_rows)} strategy families have current conversion evidence",
            "summary": "Configured strategies and emerging formations share the same evidence path. A strategy changes only through a versioned promotion record; pattern activity alone cannot rewrite it.",
            "metrics": [
                {"label": "Current families", "value": len(strategy_rows)},
                {"label": "Current hypotheses", "value": len(hypotheses)},
                {"label": "Promotion proposals", "value": len(promotions)},
                {"label": "Admitted", "value": sum(row.get("paper_strategy_admitted") is True for row in admissions)},
            ],
            "next_action": "Collect unchanged forward outcomes and promote only evidence that survives the frozen policy.",
        },
        "decision": {
            "headline": f"Current decision: {current_setup.get('router_state', 'not reviewed')}",
            "summary": current_setup.get("plain_english_root_cause"),
            "metrics": funnel["stages"][2:],
            "first_blocker": current_setup.get("primary_root_cause"),
            "next_action": "Resolve the first blocker, then rebuild the same-generation packet; downstream consequences are not separate market reasons.",
        },
        "orders": {
            "headline": f"{funnel['current_handoff_count']} current guarded handoffs",
            "summary": "Only real canonical PaperOps handoffs and Alpaca Paper lifecycle records appear here. Backtests, shadow outcomes, and dashboard projections never become orders.",
            "metrics": [
                {"label": "Current handoffs", "value": funnel["current_handoff_count"]},
                {"label": "Historical guarded route proofs", "value": funnel["historical_guarded_handoff_proof_count"]},
                {"label": "Orders created by this projection", "value": 0},
            ],
            "next_action": "Wait for one clean Router state and let canonical PaperOps own the order lifecycle.",
        },
        "learning": _learning_area(outcomes, promotions, admissions, quantum),
    }
    dashboard = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_evidence_fit_dashboard_summary",
        "phase_id": PHASE_ID,
        "generated_at": generated,
        "status": "ready",
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "command_disabled": True,
        "registered_source_count": _int(source_contract.get("source_count")),
        "watched_instrument_count": _int(instrument_registry.get("instrument_count")),
        "pattern_rows": pattern_rows,
        "strategy_rows": strategy_rows,
        "funnel": funnel,
        "areas": areas,
        "trial": {
            "implementation_ready": trial_certification.get("implementation_ready") is True,
            "empirical_status": trial_certification.get("empirical_trial_status"),
            "eligible_days_observed": _int(trial_certification.get("eligible_market_days_observed")),
            "eligible_day_target": _int(trial_certification.get("eligible_market_day_target")),
            "simulated_time_used": False,
        },
        "authority": authority_flags(),
        "boundary": "Read-only evidence projection. It cannot create or approve a trade.",
    }
    fingerprint = _material_fingerprint(
        {"funnel": funnel, "strategy_rows": strategy_rows, "areas": areas}
    )
    previous_changes = read_jsonl(runtime / MATERIAL_CHANGES_ARTIFACT)
    previous_notifications = read_jsonl(runtime / NOTIFICATION_CANDIDATES_ARTIFACT)
    duplicate = any(row.get("material_fingerprint") == fingerprint for row in previous_changes)
    material_change = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_material_research_change",
        "phase_id": PHASE_ID,
        "generated_at": generated,
        "material_change_id": stable_id("ef9-material-change", fingerprint),
        "material_fingerprint": fingerprint,
        "status": "unchanged_duplicate" if duplicate else "material_change",
        "current_setup": current_setup,
        "funnel_stage_counts": funnel["stages"],
        "notification_candidate_created": not duplicate,
        "paper_order_created": False,
        "broker_write_count": 0,
        "authority": authority_flags(),
    }
    changes = [*previous_changes, material_change][-MATERIAL_HISTORY_LIMIT:]
    trigger_count = _int(trigger_summary.get("active_event_trigger_count")) + _int(
        trigger_summary.get("active_regime_count")
    ) + _int(trigger_summary.get("active_market_dislocation_count"))
    notification = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_evidence_fit_notification_candidate",
        "phase_id": PHASE_ID,
        "generated_at": generated,
        "notification_candidate_id": stable_id("ef9-notification", fingerprint),
        "material_fingerprint": fingerprint,
        "status": "duplicate_suppressed" if duplicate else "ready_for_review",
        "body": None if duplicate else _notification_body(funnel, trigger_count),
        "public_safe": True,
        "review_only": True,
        "live_send_attempted": False,
        "live_send_allowed": False,
        "command_disabled": True,
        "paper_order_created": False,
        "broker_write_count": 0,
        "proof_credit_granted": False,
        "authority": authority_flags(),
    }
    notifications = [*previous_notifications, notification][
        -NOTIFICATION_HISTORY_LIMIT:
    ]
    dashboard["notification"] = {
        "status": notification["status"],
        "body": notification["body"],
        "duplicate_suppressed": duplicate,
        "live_send_attempted": False,
    }
    return {
        "dashboard": dashboard,
        "funnel": funnel,
        "material_changes": changes,
        "notifications": notifications,
        "latest_material_change": material_change,
        "latest_notification": notification,
    }


def validate_evidence_fit_visibility(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    dashboard = state.get("dashboard") or {}
    funnel = state.get("funnel") or {}
    notification = state.get("latest_notification") or {}
    if dashboard.get("registered_source_count") != 41:
        errors.append("evidence_fit_dashboard_source_count_mismatch")
    if dashboard.get("watched_instrument_count") != 19:
        errors.append("evidence_fit_dashboard_instrument_count_mismatch")
    if set((dashboard.get("areas") or {})) != {
        "sources", "universe", "patterns", "strategies", "decision", "orders", "learning"
    }:
        errors.append("evidence_fit_dashboard_area_contract_mismatch")
    if not funnel.get("stages") or len(funnel.get("stages") or []) != 9:
        errors.append("evidence_fit_conversion_funnel_incomplete")
    if not funnel.get("current_setup", {}).get("primary_root_cause"):
        errors.append("evidence_fit_first_root_cause_missing")
    if notification.get("status") == "duplicate_suppressed" and notification.get("body"):
        errors.append("evidence_fit_duplicate_notification_has_body")
    if notification.get("status") == "ready_for_review" and not notification.get("body"):
        errors.append("evidence_fit_material_notification_body_missing")
    if notification.get("live_send_attempted") is not False:
        errors.append("evidence_fit_notification_live_send_attempted")
    for payload in [dashboard, funnel, notification, *state.get("material_changes", [])]:
        errors.extend(validate_authority(payload.get("authority") or {}))
        if payload.get("paper_order_created") is True:
            errors.append("evidence_fit_projection_created_order")
        if _int(payload.get("broker_write_count")):
            errors.append("evidence_fit_projection_created_broker_write")
    return unique_errors(errors)


def build_and_write_evidence_fit_visibility(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    state = build_evidence_fit_visibility_state(settings)
    errors = validate_evidence_fit_visibility(state)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_evidence_fit_visibility_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "implementation_complete": not errors,
        "dashboard_area_count": len(state["dashboard"]["areas"]),
        "conversion_stage_count": len(state["funnel"]["stages"]),
        "pattern_row_count": len(state["dashboard"]["pattern_rows"]),
        "strategy_row_count": len(state["dashboard"]["strategy_rows"]),
        "notification_status": state["latest_notification"]["status"],
        "notification_live_send_attempted": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_granted_count": 0,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store = AtomicArtifactStore(runtime)
    store.write_json(DASHBOARD_ARTIFACT, state["dashboard"])
    store.write_json(FUNNEL_ARTIFACT, state["funnel"])
    store.write_jsonl(MATERIAL_CHANGES_ARTIFACT, state["material_changes"])
    store.write_jsonl(NOTIFICATION_CANDIDATES_ARTIFACT, state["notifications"])
    store.write_json(CHECK_ARTIFACT, checks)
    return state, checks, errors


__all__ = [
    "CHECK_ARTIFACT",
    "DASHBOARD_ARTIFACT",
    "FUNNEL_ARTIFACT",
    "MATERIAL_CHANGES_ARTIFACT",
    "NOTIFICATION_CANDIDATES_ARTIFACT",
    "build_and_write_evidence_fit_visibility",
    "build_conversion_funnel",
    "build_evidence_fit_visibility_state",
    "validate_evidence_fit_visibility",
]
