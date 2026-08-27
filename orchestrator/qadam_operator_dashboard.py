"""OR-17 public-safe operator dashboard and communications projection.

The projection enriches the existing protected route matrix with V3 evidence.
It is read-only and cannot create commands, approvals, orders, broker writes,
Telegram sends, policy mutations, or proof credit.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_pattern_dashboard_views import (
    PATTERN_DISCOVERY_ARTIFACT,
    QUANTUM_REVIEW_ARTIFACT,
    build_pattern_dashboard_views,
    validate_pattern_dashboard_views,
)
from orchestrator.qadam_improvement_pipeline_view_model import (
    APPLIED_VERSIONS_ARTIFACT,
    IMPROVEMENT_PIPELINE_ARTIFACT,
    IMPROVEMENT_PROPOSALS_ARTIFACT,
    build_improvement_pipeline_view_model,
    validate_improvement_pipeline_view_model,
)
from orchestrator.qadam_end_to_end_lifecycle import (
    CHECK_ARTIFACT as LIFECYCLE_CHECK_ARTIFACT,
    ROUTE_CONTEXTS as LIFECYCLE_ROUTE_CONTEXTS,
    build_lifecycle_contract,
    build_lifecycle_dashboard_summary,
    build_route_stage_map,
    validate_lifecycle_contract,
    validate_lifecycle_summary,
    write_lifecycle_artifacts,
)
from orchestrator.qadam_learning_cycle_view_model import (
    LEARNING_CYCLE_ARTIFACT,
    LEARNING_CYCLE_EVENTS_ARTIFACT,
    build_learning_cycle_view_model,
    validate_learning_cycle_view_model,
)
from orchestrator.qadam_market_session_truth import expected_market_session_phase
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    authority_flags,
    file_sha256,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_wave_b_common import parse_timestamp, safe_float, stable_id
from orchestrator.qadam_stage1_learning_input import (
    STAGE1_HANDOFFS_ARTIFACT,
    STAGE1_INPUT_ARTIFACT,
    build_stage1_learning_input,
    validate_stage1_learning_input,
)
from orchestrator.telegram_message_quality import (
    telegram_human_message_style,
    telegram_message_fingerprint,
)

SCHEMA_VERSION = "qadam_operator_dashboard.v1"
PHASE_ID = "OR-17"

VIEW_MODEL_ARTIFACT = "qadam_operator_dashboard_view_model.json"
FRESHNESS_ARTIFACT = "qadam_operator_dashboard_freshness.json"
TRUTH_AUDIT_ARTIFACT = "qadam_operator_dashboard_truth_audit.json"
COMMUNICATIONS_ARTIFACT = "qadam_operator_communications_mirror.json"
CHECK_ARTIFACT = "qadam_operator_dashboard_checks.json"

DASHBOARD_STATUS_ARTIFACT = "qsase_dashboard_status.json"
PORTFOLIO_SERIES_ARTIFACT = "qsase_dashboard_portfolio_value_series.json"
CURRENT_PORTFOLIO_ARTIFACT = "qsase_dashboard_current_portfolio.json"
TRADING_HISTORY_ARTIFACT = "qsase_dashboard_trading_history.json"
SOURCE_NETWORK_ARTIFACT = "qsase_dashboard_source_network.json"
SOURCE_OPERATIONAL_ARTIFACT = "qadam_source_operational_state.jsonl"
SOURCE_RELIABILITY_RECORDS_ARTIFACT = "qsase_source_reliability_records.jsonl"
TRADING_UNIVERSE_ARTIFACT = "qsase_trading_universe.json"
STRATEGY_UNIVERSE_ARTIFACT = "qsase_dashboard_strategy_universe.json"
STRATEGY_EVIDENCE_ARTIFACT = "qadam_strategy_evidence_map_v3.json"
PATTERN_SCORE_ARTIFACT = "qadam_pattern_score_v3_records.jsonl"
EDGE_REGISTRY_ARTIFACT = "qadam_edge_registry.jsonl"
EDGE_SUMMARY_ARTIFACT = "qadam_edge_registry_summary.json"
QUANTUM_SUMMARY_ARTIFACT = "qadam_quantum_usefulness_summary.json"
HYPOTHESES_ARTIFACT = "qadam_strategy_hypotheses_v3.jsonl"
FOUNDRY_ARTIFACT = "qadam_strategy_foundry_v3.json"
AKBER_RESULTS_ARTIFACT = "qadam_akber_filter_v3_results.jsonl"
AKBER_DASHBOARD_ARTIFACT = "qadam_akber_filter_v3_dashboard_summary.json"
SHADOW_STATE_ARTIFACT = "qadam_forward_shadow_state.json"
SHADOW_PROMOTION_ARTIFACT = "qadam_shadow_promotion_readiness.json"
ROUTER_SCOREBOARD_ARTIFACT = "qadam_router_v3_scoreboard.json"
ROUTER_WHY_NOT_ARTIFACT = "qadam_router_v3_why_not_trading_now.json"
HANDOFF_ARTIFACT = "qadam_paperops_handoff_v3.jsonl"
RELEASE_ARTIFACT = "qadam_research_lock_release_readiness.json"
EXPERIMENTAL_RELEASE_ARTIFACT = "qadam_experimental_paper_release_readiness.json"
EXPERIMENTAL_TRIAL_ARTIFACT = "qadam_30_day_paper_growth_trial_summary.json"
EXPERIMENTAL_SOAK_ARTIFACT = "qadam_operator_soak_v3.json"
EXPERIMENTAL_CERTIFICATION_ARTIFACT = "qadam_autonomous_experimental_paper_epoch_certification.json"
LIFECYCLE_ARTIFACT = "qadam_paper_lifecycle_v3.json"
LINEAGE_ARTIFACT = "qadam_paper_trade_lineage.jsonl"
POSTMORTEMS_ARTIFACT = "qadam_paper_postmortems_v3.jsonl"
PROOF_ARTIFACT = "qadam_paper_proof_eligibility.json"
ATTRIBUTION_ARTIFACT = "qadam_learning_attribution_v3.jsonl"
PERFORMANCE_ARTIFACT = "qadam_paper_performance_summary.json"
BACKFILL_ARTIFACT = "qadam_backfill_coverage.json"
SUPERVISOR_STATUS_ARTIFACT = "qadam_research_supervisor_status.json"
SUPERVISOR_HEARTBEAT_ARTIFACT = "qadam_research_supervisor_heartbeat.json"
OPERATOR_SERVICE_ARTIFACT = "qadam_operator_service_status.json"
OPERATOR_WHY_NOT_RUNNING_ARTIFACT = "qadam_operator_why_not_running.json"
OPERATOR_REPAIR_QUEUE_ARTIFACT = "qadam_operator_repair_queue.json"
OPERATOR_CERTIFICATION_ARTIFACT = "qadam_operator_ready_edge_engine_certification.json"
PERMANENT_RELIABILITY_ARTIFACT = "qadam_permanent_operator_reliability_status.json"
TRADEABILITY_COMPILER_ARTIFACT = "qadam_tradeability_compiler_dashboard_summary.json"
LOCK_ARTIFACT = "qadam_long_backtest_lock.json"
ANTI_SLOP_ARTIFACT = "qsase_dashboard_anti_slop_audit.json"
TELEGRAM_DEDUPE_ARTIFACT = "qadam_telegram_next_generation_dedupe_ledger.jsonl"
LEARNING_BACKTEST_GAP_ARTIFACT = "qadam_learning_backtest_dashboard_summary.json"
BACKTEST_COMPLETION_ARTIFACT = "qadam_backtest_completion_dashboard_summary.json"
MATERIAL_LEARNING_DELTA_ARTIFACT = "qadam_material_learning_delta.json"
EF11_DASHBOARD_ARTIFACT = "qadam_ef11_dashboard_summary.json"
EF11_CERTIFICATION_ARTIFACT = "qadam_ef11_open_market_conversion_certification.json"
EF11_TELEGRAM_CANDIDATE_ARTIFACT = "qadam_ef11_telegram_notification_candidate.json"
QUALITATIVE_DASHBOARD_ARTIFACT = "qadam_qualitative_dashboard_summary.json"
QUALITATIVE_COMMUNICATIONS_ARTIFACT = "qadam_qualitative_communications_summary.json"
RESEARCH_PROGRESSION_ARTIFACT = "qadam_research_progression_health.json"
EF11_CLOSED_MARKET_FRESHNESS_SECONDS = 72 * 60 * 60

PINNED_CONTEXT_ROUTES = (("system", "team", "Qadam Team"),)

STANDALONE_CROSS_CUTTING_ROUTES = (("system", "overview", "System", "Full operating picture"),)

PROTECTED_NAVIGATION = (
    (
        "fund",
        "Fund",
        (("portfolio", "Portfolio"), ("timeline", "Trading History")),
    ),
    ("observe", "Observe", (("sources", "Data Sources"), ("universe", "Trading Universe"))),
    (
        "patterns",
        "Find Patterns",
        (("findings", "Pattern Recognition"), ("nonlinear", "Quantum Edge")),
    ),
    (
        "decide",
        "Test & Decide",
        (
            ("strategies", "Trading Strategies"),
            ("decision", "Decision Room"),
        ),
    ),
    ("trade", "Trade", (("orders", "Order Monitor"),)),
    (
        "learn",
        "Learn & Improve",
        (
            ("outcomes", "Results & Lessons"),
            ("improvements", "Tests & Improvements"),
        ),
    ),
    (
        "system",
        "System",
        (("overview", "System Overview"),),
    ),
)

GROUPED_ROUTE_ORDER = tuple(
    f"{module_id}/{view_id}"
    for module_id, _module_label, views in PROTECTED_NAVIGATION
    for view_id, _view_label in views
)
PINNED_ROUTE_ORDER = tuple(
    f"{module_id}/{view_id}" for module_id, view_id, _view_label in PINNED_CONTEXT_ROUTES
)
ROUTE_ORDER = PINNED_ROUTE_ORDER + GROUPED_ROUTE_ORDER
JOURNEY_ROUTE_ORDER = tuple(
    f"{module_id}/{view_id}"
    for module_id, _module_label, views in PROTECTED_NAVIGATION
    if module_id != "system"
    for view_id, _view_label in views
)
DEFAULT_ROUTE = "fund/portfolio"
STATUS_REFRESH_MS = 15_000

FRESHNESS_SPECS = {
    DASHBOARD_STATUS_ARTIFACT: 30 * 60,
    PORTFOLIO_SERIES_ARTIFACT: 30 * 60,
    CURRENT_PORTFOLIO_ARTIFACT: 30 * 60,
    SOURCE_OPERATIONAL_ARTIFACT: 30 * 60,
    PATTERN_SCORE_ARTIFACT: 30 * 60,
    EDGE_SUMMARY_ARTIFACT: 30 * 60,
    AKBER_DASHBOARD_ARTIFACT: 30 * 60,
    # Shadow and Router refreshes can legitimately wait behind the bounded
    # challenger worker's research-plane lock. Three cadences distinguish that
    # expected serialization from a genuinely missed producer.
    SHADOW_STATE_ARTIFACT: 15 * 60,
    ROUTER_SCOREBOARD_ARTIFACT: 15 * 60,
    LIFECYCLE_ARTIFACT: 15 * 60,
    OPERATOR_SERVICE_ARTIFACT: 5 * 60,
    # The consolidated operator service owns research scheduling. The legacy
    # supervisor heartbeat remains only as a compatibility record and must not
    # be presented as an active liveness signal.
    # Manual certification snapshots are intentionally not freshness-monitored
    # here. Rebuilding them from the dashboard refresh creates a recursive
    # health dependency; live status, build identity, circuits, repair requests,
    # and soak evidence are monitored directly instead.
    # A valid guarded PaperOps pass can occupy the synchronous operator for
    # longer than ten minutes. These are health projections, not trade-time
    # quotes; EF11 continues to enforce its own stricter market clocks.
    EF11_DASHBOARD_ARTIFACT: 30 * 60,
    EF11_CERTIFICATION_ARTIFACT: 30 * 60,
}

FORBIDDEN_PUBLIC_KEYS = {
    "access_token",
    "api_key",
    "authorization",
    "bot_token",
    "chat_id",
    "cookie",
    "credential",
    "password",
    "secret",
}


def _artifact_generated_at(path: Path) -> str | None:
    if path.suffix == ".jsonl":
        rows = read_jsonl(path, limit=1)
        return str(rows[-1].get("generated_at")) if rows and rows[-1].get("generated_at") else None
    payload = read_json(path)
    return str(payload.get("generated_at")) if payload.get("generated_at") else None


def _freshness_record(
    runtime: Path, filename: str, threshold: int, reference: datetime
) -> dict[str, Any]:
    path = runtime / filename
    generated_at = _artifact_generated_at(path) if path.exists() else None
    observed = parse_timestamp(generated_at)
    if observed is None and path.exists():
        observed = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    age = max(0, int((reference - observed).total_seconds())) if observed else None
    if not path.exists():
        state = "missing"
    elif age is None or age > threshold:
        state = "stale"
    else:
        state = "fresh"
    return {
        "artifact": f"data/runtime/{filename}",
        "exists": path.exists(),
        "generated_at": generated_at,
        "age_seconds": age,
        "stale_after_seconds": threshold,
        "freshness_state": state,
        "display_label_required": state != "fresh",
        "sha256": file_sha256(path),
    }


def build_freshness_audit(settings: Settings | None = None, *, generated_at: str) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    reference = parse_timestamp(generated_at) or datetime.now(timezone.utc)
    thresholds = dict(FRESHNESS_SPECS)
    if expected_market_session_phase(reference) != "regular":
        thresholds[EF11_DASHBOARD_ARTIFACT] = EF11_CLOSED_MARKET_FRESHNESS_SECONDS
        thresholds[EF11_CERTIFICATION_ARTIFACT] = EF11_CLOSED_MARKET_FRESHNESS_SECONDS
    records = [
        _freshness_record(runtime, filename, threshold, reference)
        for filename, threshold in thresholds.items()
    ]
    counts = Counter(record["freshness_state"] for record in records)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_dashboard_freshness",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "fresh"
        if not counts.get("stale") and not counts.get("missing")
        else "stale_labels_required",
        "artifact_count": len(records),
        "fresh_count": counts.get("fresh", 0),
        "stale_count": counts.get("stale", 0),
        "missing_count": counts.get("missing", 0),
        "stale_or_missing_labeled_count": sum(
            record["display_label_required"] for record in records
        ),
        "records": records,
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "authority": authority_flags(),
    }


def _source_summary(
    operational: list[dict[str, Any]], reliability: list[dict[str, Any]]
) -> dict[str, Any]:
    reliability_by_key = {
        str(record.get("source_key")): record for record in reliability if record.get("source_key")
    }
    rows: list[dict[str, Any]] = []
    for record in operational:
        key = str(record.get("source_key") or "")
        reliable = reliability_by_key.get(key, {})
        adapter_status = str(reliable.get("adapter_status") or "not_verified")
        historical_class = str(record.get("historical_capability_class") or "unknown")
        rows.append(
            {
                "source_key": key,
                "configured": record.get("context_visible") is True,
                "responding": adapter_status == "online",
                "fresh": record.get("freshness_state") == "fresh",
                "quorum_eligible": record.get("source_quorum_eligible") is True,
                "historical_capable": "supported" in historical_class,
                "freshness_state": record.get("freshness_state"),
                "failure_class": record.get("failure_class"),
                "observed_at": record.get("observed_at"),
            }
        )
    return {
        "configured_count": sum(row["configured"] for row in rows),
        "responding_count": sum(row["responding"] for row in rows),
        "fresh_count": sum(row["fresh"] for row in rows),
        "quorum_eligible_count": sum(row["quorum_eligible"] for row in rows),
        "historical_capable_count": sum(row["historical_capable"] for row in rows),
        "source_count": len(rows),
        "rows": rows,
    }


def _distinct_pattern_findings(
    scores: list[dict[str, Any]], edges: list[dict[str, Any]], quantum: dict[str, Any]
) -> list[dict[str, Any]]:
    edge_by_instrument = {
        str(record.get("instrument")): record for record in edges if record.get("instrument")
    }
    best: dict[tuple[str, str], dict[str, Any]] = {}
    for score in scores:
        key = (
            str(score.get("instrument") or "unknown"),
            str(score.get("strategy_family_id") or "strategy_agnostic"),
        )
        if key not in best or safe_float(score.get("raw_pattern_score")) > safe_float(
            best[key].get("raw_pattern_score")
        ):
            best[key] = score
    ranked = sorted(
        best.values(),
        key=lambda record: (
            -safe_float(record.get("raw_pattern_score")),
            str(record.get("instrument")),
        ),
    )[:12]
    findings: list[dict[str, Any]] = []
    for rank, score in enumerate(ranked, start=1):
        instrument = str(score.get("instrument") or "unknown")
        edge = edge_by_instrument.get(instrument, {})
        inputs = score.get("feature_inputs")
        inputs = inputs if isinstance(inputs, list) else []
        source_chain = [
            str(record.get("source_key"))
            for record in inputs
            if isinstance(record, dict) and record.get("source_key")
        ]
        fresh_count = sum(
            record.get("fresh") is True for record in inputs if isinstance(record, dict)
        )
        independent_count = len(
            {
                str(record.get("independence_cluster_id"))
                for record in inputs
                if isinstance(record, dict) and record.get("independence_cluster_id")
            }
        )
        score_value = safe_float(score.get("raw_pattern_score"))
        missing = list(score.get("missing_critical_features") or [])
        validated = bool(edge)
        stage_key = (
            "validated"
            if validated
            else (
                "documented" if score.get("confidence_state") == "score_ready_for_tape" else "found"
            )
        )
        blocker = (
            ", ".join(str(value).replace("_", " ") for value in missing)
            if missing
            else (
                "historical forward labels and a validated edge are still missing"
                if not validated
                else "Akber and forward-shadow confirmation are still required"
            )
        )
        strategy = str(score.get("strategy_label") or "Strategy-agnostic discovery")
        quantum_verdict = str(quantum.get("quantum_contribution_verdict") or "")
        quantum_score = quantum.get("quantum_usefulness_score")
        if (
            quantum_verdict == "incremental_value_observed_research_only"
            and quantum_score is not None
            and safe_float(quantum_score) > 0
        ):
            quantum_contribution = "incremental"
            quantum_plain_english = "Controlled quantum review added incremental research value; it remains non-authoritative."
        elif quantum_verdict == "not_useful_for_tested_edges":
            quantum_contribution = "not_useful"
            quantum_plain_english = "The tested quantum method did not add reliable value beyond the matched classical baseline."
        elif int(quantum.get("fallback_comparison_count", 0) or 0) > 0:
            quantum_contribution = "fallback"
            quantum_plain_english = "The review used a labelled classical fallback, so no quantum edge credit was granted."
        else:
            quantum_contribution = "neutral"
            quantum_plain_english = (
                "Quantum usefulness is not yet established by controlled holdout evidence."
            )
        findings.append(
            {
                "pattern_id": score.get("score_id"),
                "rank": rank,
                "rank_badges": [f"priority {rank}", stage_key],
                "title": f"{instrument} evidence pattern",
                "stage_key": stage_key,
                "stage_label": stage_key.replace("_", " "),
                "confidence_label": f"raw pattern score {score_value:.3f}; not a probability",
                "tradeability_state": "research_only"
                if not validated
                else "validated_edge_research_only",
                "evidence_quality_score": round(score_value, 6),
                "detected_signal": (
                    f"{fresh_count} fresh source inputs across {independent_count} independent source clusters"
                ),
                "market_affected": instrument,
                "instrument_symbols": [instrument],
                "strategy_fit": strategy,
                "raw_pattern_score": score_value,
                "raw_pattern_score_is_probability": False,
                "historical_edge_state": edge.get("promotion_class") or "not_validated",
                "source_signal_summary": (
                    f"Qadam scored {len(inputs)} source features available before the outcome window."
                ),
                "price_relationship": (
                    "A cost-adjusted historical edge is registered."
                    if validated
                    else "No cost-adjusted historical source-price edge is registered yet."
                ),
                "evidence_summary": (
                    f"{len(inputs)} inputs; {fresh_count} fresh; {independent_count} independent clusters."
                ),
                "what_qadam_thinks": (
                    f"The current evidence is most compatible with {strategy}, but the score alone does not prove a tradeable edge."
                ),
                "what_would_confirm": (
                    "Provider-backed forward labels, walk-forward holdout support, positive return after costs, and current Akber confirmation."
                ),
                "what_blocks_trade": blocker,
                "next_action": (
                    "Collect provider-backed labels and rerun the frozen backtest protocol."
                    if not validated
                    else "Complete Akber context and real-time forward shadowing."
                ),
                "source_chain": source_chain[:10],
                "quantum_review": {
                    "state": quantum.get("status") or "not_measurable",
                    "contribution": quantum_contribution,
                    "plain_english_result": quantum_plain_english,
                },
            }
        )
    return findings


def _pattern_compatibility(
    findings: list[dict[str, Any]], scores: list[dict[str, Any]], edge_count: int
) -> dict[str, Any]:
    documented = sum(row["stage_key"] == "documented" for row in findings)
    validated = sum(row["stage_key"] == "validated" for row in findings)
    return {
        "status": "research_only_no_validated_edge"
        if edge_count == 0
        else "validated_edges_visible",
        "summary": (
            f"{len(findings)} distinct findings shown from {len(scores)} score records; raw scores are not probabilities."
        ),
        "finding_count": len(findings),
        "paper_ready_count": 0,
        "findings": findings,
        "stage_counts": {
            "found": len(findings),
            "documented": documented,
            "validated": validated,
            "trade_candidate": 0,
            "paper_ready": 0,
        },
        "human_brief": {
            "body": (
                "Qadam can describe current source-side patterns, but it has not yet measured a repeatable cost-adjusted edge. "
                "The strongest current record is research evidence, not a trading probability."
            )
        },
        "technical_diagnostics": {
            "linear_pattern_count": len(scores),
            "nonlinear_pattern_count": 0,
            "quantum_review_count": 0,
            "linear_rows": [
                {
                    "pattern_type": "pattern_score_v3",
                    "instrument": score.get("instrument"),
                    "state": score.get("confidence_state"),
                    "score": score.get("raw_pattern_score"),
                    "score_is_probability": False,
                }
                for score in scores[:24]
            ],
            "nonlinear_rows": [],
            "quantum_rows": [],
        },
    }


def _akber_stages(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if results:
        return list(results[0].get("stages") or [])
    return [
        {
            "stage": stage,
            "state": "waiting_for_edge_backed_hypothesis",
            "plain_english": explanation,
        }
        for stage, explanation in (
            ("context", "Does the historical relationship fit the current market setting?"),
            ("catalyst", "Is the event fresh and strong enough to matter now?"),
            ("confirmation", "Do price, volume, volatility, and nonlinear review agree?"),
            ("risk", "Is the invalidation clear and the expected reward worth the risk?"),
            ("execution", "Is the paper proxy liquid, paperable, and affordable after costs?"),
            ("postmortem_learning", "What will Qadam measure after the decision?"),
        )
    ]


def _router_compatibility(
    scoreboard: dict[str, Any], why_not: dict[str, Any], akber_results: list[dict[str, Any]]
) -> dict[str, Any]:
    counts = scoreboard.get("state_counts")
    counts = counts if isinstance(counts, dict) else {}
    return {
        "status": scoreboard.get("status") or "not_recorded",
        "decision_count": scoreboard.get("decision_count", 0),
        "hold_count": counts.get("hold", 0),
        "blocked_safety_boundary_count": counts.get("blocked-safety-boundary", 0),
        "paper_review_candidate_count": scoreboard.get("paper_review_candidate_count", 0),
        "why_not_trading_now": {
            "reason": why_not.get("primary_reason") or "No current Router V3 answer is available."
        },
        "scoreboard": {
            "top_reason": why_not.get("primary_reason"),
            "ranked_count": scoreboard.get("decision_count", 0),
            "ranked_decisions": [],
        },
        "akber_stages": _akber_stages(akber_results),
        "akber_plain_english_decision": (
            akber_results[0].get("plain_english_explanation")
            if akber_results
            else "Akber has no edge-backed hypothesis to review yet."
        ),
    }


def _paperops_gate_compatibility(
    scoreboard: dict[str, Any], release: dict[str, Any], handoff_count: int
) -> dict[str, Any]:
    return {
        "status": release.get("status") or "hold",
        "handoff_record_count": handoff_count,
        "top_blocking_gate": (release.get("blockers") or ["none"])[0],
        "guarded_alpaca_paper_route_state": (
            "available_after_explicit_release"
            if release.get("release_effective") is True
            else "watch_only_research_lock_active"
        ),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "boundary": (
            "Router V3 handoffs are review context, not orders. The guarded Alpaca Paper PaperOps wrapper is the only possible submit route."
        ),
        "paper_review_candidate_count": scoreboard.get("paper_review_candidate_count", 0),
    }


def _lifecycle_compatibility(lifecycle: dict[str, Any], proof: dict[str, Any]) -> dict[str, Any]:
    states = lifecycle.get("state_counts")
    states = states if isinstance(states, dict) else {}
    origin_counts = lifecycle.get("origin_counts")
    origin_counts = origin_counts if isinstance(origin_counts, dict) else {}
    mirror_only_count = int(
        proof.get("mirror_only_historical_record_count")
        or origin_counts.get("mirror_only_historical_record")
        or 0
    )
    qadam_origin_count = sum(
        int(value or 0)
        for key, value in origin_counts.items()
        if key != "mirror_only_historical_record"
    )
    return {
        "status": lifecycle.get("status") or "not_recorded",
        "paper_order_mirror_count": lifecycle.get(
            "broker_record_count", lifecycle.get("order_record_count", 0)
        ),
        "open_position_mirror_count": lifecycle.get("position_record_count", 0),
        "closed_paper_trade_count": lifecycle.get("closed_trade_record_count", 0),
        "state_counts": {
            **states,
            "closed_postmortem_due": max(
                0,
                int(states.get("closed", 0) or 0) - int(states.get("postmortem_complete", 0) or 0),
            ),
        },
        "origin_counts": origin_counts,
        "qadam_origin_lifecycle_count": qadam_origin_count,
        "proof_eligible_count": proof.get("proof_eligible_count", 0),
        "mirror_only_historical_record_count": mirror_only_count,
        "origin_truth_summary": (
            f"{mirror_only_count} broker-mirror records are historical reference only; "
            f"{qadam_origin_count} records have complete Qadam-origin lineage."
        ),
    }


def _learning_compatibility(records: list[dict[str, Any]], proof: dict[str, Any]) -> dict[str, Any]:
    outcome_counts = Counter(str(record.get("outcome_type") or "unknown") for record in records)
    champion_counts = Counter(
        str(record.get("champion_challenger", {}).get("state") or "unknown") for record in records
    )
    proposal_count = sum(
        record.get("champion_challenger", {}).get("proposal_only") is True for record in records
    )
    return {
        "status": "proposal_only",
        "attribution_record_count": len(records),
        "policy_proposal_count": proposal_count,
        "proof_eligible_count": proof.get("proof_eligible_count", 0),
        "policy_mutation_created": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "outcome_class_counts": dict(sorted(outcome_counts.items())),
        "causal_label_counts": dict(sorted(champion_counts.items())),
        "boundary": (
            "Learning attribution is proposal-only. It cannot mutate sources, strategies, thresholds, risk, authority, or proof."
        ),
    }


def _system_route(module_id: str, view_id: str) -> dict[str, str]:
    return {"module_id": module_id, "view_id": view_id}


def _optional_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _system_blocker_context(code: str, group: str) -> tuple[str, dict[str, str], str]:
    if code.startswith("operator_service") or group == "operator_experience":
        return (
            "Runtime & services",
            _system_route("system", "overview"),
            "Review the unattended service state and its real-session soak evidence.",
        )
    if code == "research_lock_active" or group == "router_and_paperops":
        return (
            "Paper operations",
            _system_route("decide", "decision"),
            "Keep PaperOps watch-only until the evidence and release gates pass.",
        )
    if group == "canonical_truth":
        return (
            "Data & freshness",
            _system_route("observe", "sources"),
            "Refresh the monitored artifacts and resolve any missing source inputs.",
        )
    if group == "research_operations":
        return (
            "Research operations",
            _system_route("learn", "replay"),
            "Complete provider-backed historical acquisition and source repairs.",
        )
    if group == "evidence_and_edge":
        return (
            "Research & edge",
            _system_route("patterns", "findings"),
            "Accumulate eligible score inputs, forward labels, and untouched holdout evidence.",
        )
    if group == "akber_shadow_and_portfolio":
        return (
            "Shadow & portfolio",
            _system_route("learn", "replay"),
            "Run real-time shadow observation and measure the filter against replay evidence.",
        )
    return (
        "System",
        _system_route("system", "overview"),
        "Inspect the supporting diagnostics before changing any operating state.",
    )


def _system_needs_attention(
    operator_why_not: dict[str, Any], certification: dict[str, Any]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    operator_blockers = operator_why_not.get("blockers")
    operator_blockers = operator_blockers if isinstance(operator_blockers, list) else []
    service_blockers = [
        row
        for row in operator_blockers
        if str(row.get("code") or "").startswith("operator_service")
    ]
    if service_blockers:
        first = service_blockers[0]
        rows.append(
            {
                "blocker_id": "operator_service_unavailable",
                "domain": "Runtime & services",
                "reason": operator_why_not.get("headline")
                or first.get("plain_english")
                or "The unattended operator service is not available.",
                "next_action": first.get("next_action")
                or "Review installation and liveness before relying on unattended operation.",
                "route": _system_route("system", "overview"),
                "tone": "degraded",
            }
        )
        seen.add("operator_service_unavailable")
    for blocker in operator_blockers:
        code = str(blocker.get("code") or "operator_blocker")
        if code.startswith("operator_service"):
            continue
        reason = str(blocker.get("plain_english") or "").strip()
        dedupe_key = reason.lower()
        if not reason or dedupe_key in seen:
            continue
        domain, route, fallback_action = _system_blocker_context(code, "")
        rows.append(
            {
                "blocker_id": code,
                "domain": domain,
                "reason": reason,
                "next_action": blocker.get("next_action") or fallback_action,
                "route": route,
                "tone": "pending",
            }
        )
        seen.add(dedupe_key)
    certification_blockers = certification.get("top_blockers")
    certification_blockers = (
        certification_blockers if isinstance(certification_blockers, list) else []
    )
    for blocker in certification_blockers:
        reason = str(blocker.get("reason") or "").strip()
        dedupe_key = reason.lower()
        if not reason or dedupe_key in seen:
            continue
        code = str(blocker.get("check_id") or "certification_blocker")
        group = str(blocker.get("group") or "")
        domain, route, next_action = _system_blocker_context(code, group)
        rows.append(
            {
                "blocker_id": code,
                "domain": domain,
                "reason": reason,
                "next_action": next_action,
                "route": route,
                "tone": "degraded"
                if group in {"canonical_truth", "operator_experience"}
                else "pending",
            }
        )
        seen.add(dedupe_key)
        if len(rows) >= 8:
            break
    return rows


def _system_recent_activity(freshness: dict[str, Any]) -> list[dict[str, Any]]:
    activity_contract = {
        DASHBOARD_STATUS_ARTIFACT: (
            "Portfolio snapshot",
            "Fund",
            _system_route("fund", "portfolio"),
            "Portfolio and paper-account state were exported.",
        ),
        PORTFOLIO_SERIES_ARTIFACT: (
            "Performance timeline",
            "Fund",
            _system_route("fund", "timeline"),
            "The portfolio value series was refreshed.",
        ),
        CURRENT_PORTFOLIO_ARTIFACT: (
            "Portfolio composition",
            "Fund",
            _system_route("fund", "portfolio"),
            "Current positions, cash, and exposure were reconciled.",
        ),
        SOURCE_OPERATIONAL_ARTIFACT: (
            "Source operations",
            "Observe",
            _system_route("observe", "sources"),
            "Source availability and freshness were re-evaluated.",
        ),
        PATTERN_SCORE_ARTIFACT: (
            "Pattern scoring",
            "Find Patterns",
            _system_route("patterns", "findings"),
            "Point-in-time pattern scores were refreshed.",
        ),
        EDGE_SUMMARY_ARTIFACT: (
            "Edge registry",
            "Find Patterns",
            _system_route("patterns", "findings"),
            "Candidate and validated edge status was rechecked.",
        ),
        AKBER_DASHBOARD_ARTIFACT: (
            "Six-stage review",
            "Test & Decide",
            _system_route("decide", "decision"),
            "Tradeability context was reviewed against the current evidence.",
        ),
        SHADOW_STATE_ARTIFACT: (
            "Forward shadow",
            "Learn & Improve",
            _system_route("learn", "replay"),
            "Real-time shadow observation state was refreshed.",
        ),
        ROUTER_SCOREBOARD_ARTIFACT: (
            "Decision router",
            "Test & Decide",
            _system_route("decide", "decision"),
            "The current paper-trade decision state was recomputed.",
        ),
        LIFECYCLE_ARTIFACT: (
            "Paper lifecycle",
            "Trade",
            _system_route("trade", "orders"),
            "Mirrored paper orders and positions were reconciled.",
        ),
        SUPERVISOR_HEARTBEAT_ARTIFACT: (
            "Research supervisor",
            "System",
            _system_route("system", "overview"),
            "The latest research heartbeat and backfill progress were exported.",
        ),
        OPERATOR_SERVICE_ARTIFACT: (
            "Operator service",
            "System",
            _system_route("system", "overview"),
            "Service installation, liveness, and watch-only state were checked.",
        ),
        OPERATOR_CERTIFICATION_ARTIFACT: (
            "Operator certification",
            "System",
            _system_route("system", "overview"),
            "Evidence, safety, and paper-readiness checks were re-evaluated.",
        ),
    }
    rows: list[dict[str, Any]] = []
    records = freshness.get("records")
    records = records if isinstance(records, list) else []
    for record in records:
        filename = Path(str(record.get("artifact") or "")).name
        contract = activity_contract.get(filename)
        if not contract:
            continue
        label, stage, route, summary = contract
        freshness_state = str(record.get("freshness_state") or "unknown")
        rows.append(
            {
                "activity_id": f"artifact:{filename}",
                "label": label,
                "stage": stage,
                "summary": summary,
                "generated_at": record.get("generated_at"),
                "freshness_state": freshness_state,
                "tone": "online" if freshness_state == "fresh" else "degraded",
                "route": route,
            }
        )
    rows.sort(key=lambda row: str(row.get("generated_at") or ""), reverse=True)
    return rows[:10]


def _system_overview_projection(
    *,
    generated_at: str,
    runtime_state: str,
    source_summary: dict[str, Any],
    backfill_progress: dict[str, Any],
    heartbeat: dict[str, Any],
    findings: list[dict[str, Any]],
    edge_summary: dict[str, Any],
    quantum_review: dict[str, Any],
    router_scoreboard: dict[str, Any],
    router_why_not: dict[str, Any],
    release: dict[str, Any],
    lifecycle: dict[str, Any],
    learning: dict[str, Any],
    proof: dict[str, Any],
    current_portfolio: dict[str, Any],
    handoff_count: int,
    operator_service: dict[str, Any],
    operator_why_not: dict[str, Any],
    operator_repair_queue: dict[str, Any],
    operator_certification: dict[str, Any],
    permanent_reliability: dict[str, Any],
    freshness: dict[str, Any],
) -> dict[str, Any]:
    source_count = int(source_summary.get("source_count", 0) or 0)
    fresh_source_count = int(source_summary.get("fresh_count", 0) or 0)
    completed_jobs = int(backfill_progress.get("completed_jobs", 0) or 0)
    total_jobs = int(backfill_progress.get("total_jobs", 0) or 0)
    validated_edges = int(edge_summary.get("validated_edge_count", 0) or 0)
    decision_count = int(router_scoreboard.get("decision_count", 0) or 0)
    paper_review_count = int(router_scoreboard.get("paper_review_candidate_count", 0) or 0)
    empirical_quantum_count = int(quantum_review.get("empirical_comparison_count", 0) or 0)
    quantum_review_count = len(quantum_review.get("reviews") or [])
    position_count = int(current_portfolio.get("position_count", 0) or 0)
    attribution_count = int(learning.get("attribution_record_count", 0) or 0)
    proof_count = int(proof.get("proof_eligible_count", 0) or 0)
    freshness_records = freshness.get("records")
    freshness_records = freshness_records if isinstance(freshness_records, list) else []
    freshness_by_name = {
        Path(str(record.get("artifact") or "")).name: record for record in freshness_records
    }

    def updated_at(filename: str, fallback: Any = None) -> Any:
        return freshness_by_name.get(filename, {}).get("generated_at") or fallback

    operator_freshness = freshness_by_name.get(OPERATOR_SERVICE_ARTIFACT, {})
    operator_check_state = str(operator_freshness.get("freshness_state") or "not_reported")
    operator_check_current = operator_check_state == "fresh"
    operator_running_reported = operator_service.get("service_running") is True
    operator_installed_reported = operator_service.get("service_installed") is True
    operator_running = operator_running_reported if operator_check_current else None
    services = operator_service.get("services")
    services = services if isinstance(services, list) else []
    service_labels = {
        "source_ingestion": "Source ingestion",
        "market_price_refresh": "Market price refresh",
        "pattern_scoring": "Pattern scoring",
        "research_evidence_validation": "Research evidence validation",
        "akber_router_review": "Six-stage and Router review",
        "guarded_paperops": "Guarded PaperOps",
        "paper_lifecycle_poll": "Paper lifecycle poll",
        "attribution_and_dashboard": "Attribution and dashboard",
        "challenger_research": "Challenger research",
    }
    service_rows = [
        {
            "service_id": row.get("service_id"),
            "label": service_labels.get(
                str(row.get("service_id") or ""),
                str(row.get("service_id") or "Service").replace("_", " ").title(),
            ),
            "state": row.get("current_state") or "not_reported",
            "diagnostic_state": (
                "paused_by_policy"
                if row.get("paperops_watch_only") is True
                else "state_unverified"
                if not operator_check_current
                else "running"
                if row.get("service_process_running") is True
                else "stopped"
            ),
            "tone": (
                "policy"
                if row.get("paperops_watch_only") is True
                else "unmonitored"
                if not operator_check_current
                else "online"
                if row.get("service_process_running") is True
                else "degraded"
            ),
            "process_running": (
                row.get("service_process_running") is True if operator_check_current else None
            ),
            "last_reported_process_running": (row.get("service_process_running") is True),
            "paperops_watch_only": row.get("paperops_watch_only") is True,
            "purpose": row.get("purpose"),
            "trigger": row.get("trigger"),
            "owner": row.get("ownership"),
            "safe_retry_class": row.get("safe_retry_class"),
            "latency_sensitive": row.get("latency_sensitive") is True,
            "cadence_seconds": int(row.get("cadence_seconds", 0) or 0),
            "generated_at": row.get("generated_at"),
            "last_success_at": row.get("last_success_at"),
            "last_failure_at": row.get("last_failure_at"),
            "next_expected_at": row.get("next_expected_at"),
            "missed_run_count": int(row.get("missed_run_count", 0) or 0),
        }
        for row in services
    ]
    scheduled_services = [row for row in service_rows if row.get("paperops_watch_only") is not True]
    policy_paused_services = [row for row in service_rows if row.get("paperops_watch_only") is True]
    running_scheduled_services = [
        row for row in scheduled_services if row.get("process_running") is True
    ]
    reported_running_scheduled_services = [
        row for row in scheduled_services if row.get("last_reported_process_running") is True
    ]
    stopped_scheduled_services = [
        row for row in scheduled_services if row.get("process_running") is False
    ]
    certification_blockers = operator_certification.get("blockers")
    certification_blockers = (
        certification_blockers if isinstance(certification_blockers, list) else []
    )

    def certification_reason(group: str, fallback: str) -> str:
        return next(
            (
                str(row.get("reason"))
                for row in certification_blockers
                if row.get("group") == group and row.get("reason")
            ),
            fallback,
        )

    paperops_state = (
        "Paper review available"
        if release.get("release_effective") is True and paper_review_count
        else "Watch only"
    )
    system_headline = (
        "Qadam is in research-only mode; paper trading remains on hold."
        if runtime_state == "research-only"
        else "Qadam's guarded paper route is operational."
        if runtime_state == "paper-operational"
        else "Qadam is held pending operating checks."
    )
    why_not_trading = (
        router_why_not.get("primary_reason")
        or operator_why_not.get("headline")
        or "No current trading explanation was exported."
    )
    flow = [
        {
            "flow_id": "observe",
            "label": "Observe",
            "state": "Fresh inputs available" if fresh_source_count else "Waiting for fresh inputs",
            "tone": "online" if fresh_source_count else "degraded",
            "metric": f"{fresh_source_count}/{source_count} sources fresh",
            "summary": "Read-only source evidence is collected, classified, and checked for quorum use.",
            "updated_at": updated_at(SOURCE_OPERATIONAL_ARTIFACT),
            "route": _system_route("observe", "sources"),
        },
        {
            "flow_id": "evidence",
            "label": "Historical Evidence",
            "state": "Complete" if total_jobs and completed_jobs == total_jobs else "Building",
            "tone": "online" if total_jobs and completed_jobs == total_jobs else "pending",
            "metric": f"{completed_jobs}/{total_jobs} jobs complete",
            "summary": "Provider-backed history is assembled before scoring or backtesting receives credit.",
            "updated_at": heartbeat.get("generated_at"),
            "route": _system_route("learn", "replay"),
        },
        {
            "flow_id": "patterns",
            "label": "Pattern Discovery",
            "state": "Validated edge present" if validated_edges else "Evidence maturing",
            "tone": "online" if validated_edges else "pending",
            "metric": f"{len(findings)} relationships · {validated_edges} validated",
            "summary": "Distinct source-to-market relationships are ranked without treating raw scores as probabilities.",
            "updated_at": updated_at(PATTERN_SCORE_ARTIFACT),
            "route": _system_route("patterns", "findings"),
        },
        {
            "flow_id": "quantum",
            "label": "Quantum Review",
            "state": "Measured" if empirical_quantum_count else "Waiting for holdout",
            "tone": "online" if empirical_quantum_count else "pending",
            "metric": f"{empirical_quantum_count}/{quantum_review_count} empirical comparisons",
            "summary": "Nonlinear and quantum methods must beat a matched classical baseline before adding edge credit.",
            "updated_at": quantum_review.get("generated_at"),
            "route": _system_route("patterns", "nonlinear"),
        },
        {
            "flow_id": "decision",
            "label": "Decision Room",
            "state": "Paper review candidate" if paper_review_count else "No eligible setup",
            "tone": "online" if paper_review_count else "pending",
            "metric": f"{decision_count} decisions · {paper_review_count} paper review",
            "summary": "The Router combines evidence, the six-stage filter, and safety state into one current answer.",
            "updated_at": updated_at(ROUTER_SCOREBOARD_ARTIFACT),
            "route": _system_route("decide", "decision"),
        },
        {
            "flow_id": "paperops",
            "label": "Paper Operations",
            "state": paperops_state,
            "tone": "online" if release.get("release_effective") is True else "pending",
            "metric": f"{handoff_count} guarded handoffs",
            "summary": "Only a clean handoff may enter the existing guarded Alpaca Paper route.",
            "updated_at": updated_at(LIFECYCLE_ARTIFACT),
            "route": _system_route("trade", "orders"),
        },
        {
            "flow_id": "portfolio",
            "label": "Portfolio",
            "state": "Positions open" if position_count else "Holding cash",
            "tone": "online",
            "metric": f"{position_count} open positions",
            "summary": "Paper-account performance, composition, positions, and lineage are reconciled here.",
            "updated_at": updated_at(CURRENT_PORTFOLIO_ARTIFACT),
            "route": _system_route("fund", "portfolio"),
        },
        {
            "flow_id": "learning",
            "label": "Learning",
            "state": "Attribution available" if attribution_count else "Waiting for outcomes",
            "tone": "online" if attribution_count else "pending",
            "metric": f"{attribution_count} records · {proof_count} proof eligible",
            "summary": "Outcomes become attributed evidence and reviewable proposals; policy never changes automatically.",
            "updated_at": lifecycle.get("generated_at"),
            "route": _system_route("learn", "outcomes"),
        },
    ]
    stale_count = int(freshness.get("stale_count", 0) or 0)
    missing_count = int(freshness.get("missing_count", 0) or 0)
    artifact_count = int(freshness.get("artifact_count", 0) or 0)
    fresh_artifact_count = int(freshness.get("fresh_count", 0) or 0)
    health_domains = [
        {
            "domain_id": "runtime",
            "label": "Runtime & services",
            "tone": "online" if operator_running is True else "degraded",
            "status": (
                "Running"
                if operator_running is True
                else "Not running"
                if operator_running is False
                else "State unverified"
            ),
            "metric": (
                f"{len(running_scheduled_services)}/{len(scheduled_services)} "
                "required workflows running"
                if operator_check_current and scheduled_services
                else "Required workflow inventory not reported"
                if operator_check_current
                else "Current workflow state not verified"
            ),
            "issue": operator_why_not.get("headline") or "No runtime issue was exported.",
            "next_action": (
                "Continue monitoring liveness and repair state."
                if operator_running is True
                else "Install, start, and observe the operator service across real sessions."
                if operator_running is False
                else "Refresh the operator-service check before diagnosing process state."
            ),
            "route": _system_route("system", "overview"),
        },
        {
            "domain_id": "data",
            "label": "Data & freshness",
            "tone": "online" if not stale_count and not missing_count else "degraded",
            "status": "Current" if not stale_count and not missing_count else "Needs refresh",
            "metric": f"{fresh_artifact_count}/{artifact_count} artifacts current",
            "issue": f"{stale_count} stale and {missing_count} missing monitored artifacts."
            if stale_count or missing_count
            else "All monitored artifacts are current.",
            "next_action": "Refresh stale projections and resolve source acquisition gaps."
            if stale_count or missing_count
            else "Maintain the current refresh cadence.",
            "route": _system_route("observe", "sources"),
        },
        {
            "domain_id": "research",
            "label": "Research & edge",
            "tone": "online" if validated_edges else "pending",
            "status": "Validated" if validated_edges else "Evidence maturing",
            "metric": f"{len(findings)} relationships · {validated_edges} validated edges",
            "issue": certification_reason(
                "evidence_and_edge", "No validated out-of-sample edge exists yet."
            ),
            "next_action": "Complete point-in-time scoring, forward labels, holdout backtests, and nonlinear comparison.",
            "route": _system_route("patterns", "findings"),
        },
        {
            "domain_id": "paperops",
            "label": "Paper operations",
            "tone": "online" if release.get("release_effective") is True else "pending",
            "status": paperops_state,
            "metric": f"{paper_review_count} eligible setups · {handoff_count} handoffs",
            "issue": why_not_trading,
            "next_action": "Keep the guarded route watch-only until every release condition passes."
            if release.get("release_effective") is not True
            else "Monitor clean handoffs through the guarded paper route.",
            "route": _system_route("decide", "decision"),
        },
        {
            "domain_id": "learning",
            "label": "Learning & persistence",
            "tone": "online" if attribution_count else "pending",
            "status": "Recording outcomes" if attribution_count else "Waiting for outcomes",
            "metric": f"{attribution_count} attributed · {proof_count} proof eligible",
            "issue": "No Qadam-origin paper outcome is proof eligible yet."
            if not proof_count
            else "Proof-eligible outcomes are available for review.",
            "next_action": "Continue real paper outcomes and postmortems without backfilling elapsed time."
            if not proof_count
            else "Review attribution before proposing any change.",
            "route": _system_route("learn", "outcomes"),
        },
    ]
    resource_state = heartbeat.get("resource_state")
    resource_state = resource_state if isinstance(resource_state, dict) else {}
    source_rows = source_summary.get("rows")
    source_rows = source_rows if isinstance(source_rows, list) else []
    alpaca_source = next(
        (row for row in source_rows if str(row.get("source_key") or "") == "alpaca"),
        {},
    )
    affected_service_labels = [
        str(row.get("label") or "Scheduled process")
        for row in (stopped_scheduled_services if operator_check_current else scheduled_services)
    ]
    repair_requests = operator_repair_queue.get("requests")
    repair_requests = repair_requests if isinstance(repair_requests, list) else []
    active_incidents: list[dict[str, Any]] = []
    if not operator_check_current:
        active_incidents.append(
            {
                "incident_id": "operating_evidence_overdue",
                "severity": "critical",
                "tone": "degraded",
                "state": "open",
                "title": "Automation state is unverified",
                "summary": (
                    "The operator-service health check is overdue, so Qadam cannot verify "
                    "whether scheduled research, refresh, scoring, and monitoring are "
                    f"running now. {stale_count} monitored artifacts are overdue and "
                    f"{missing_count} are missing."
                ),
                "root_cause": (
                    "The operator-service health check missed its freshness threshold; "
                    "the last report cannot be treated as current state."
                ),
                "affected_capabilities": affected_service_labels,
                "affected_count": len(affected_service_labels),
                "first_seen_at": None,
                "last_confirmed_at": freshness.get("generated_at"),
                "evidence_state": operator_check_state,
                "evidence": [
                    {
                        "label": "Operator health check",
                        "value": operator_check_state.replace("_", " ").title(),
                    },
                    {
                        "label": "Last reported installation",
                        "value": ("Installed" if operator_installed_reported else "Not installed"),
                    },
                    {
                        "label": "Last reported process",
                        "value": ("Running" if operator_running_reported else "Stopped"),
                    },
                    {"label": "Overdue artifacts", "value": stale_count},
                    {"label": "Missing artifacts", "value": missing_count},
                ],
                "owner": "Python COO / system operator",
                "next_action": (
                    "Refresh the operator-service health check first. If a fresh report "
                    "still shows stopped, review the generated launch configuration, "
                    "start the service explicitly, and verify a new heartbeat."
                ),
                "route": _system_route("system", "overview"),
            }
        )
    elif operator_running is False:
        active_incidents.append(
            {
                "incident_id": "operator_service_stopped",
                "severity": "critical",
                "tone": "degraded",
                "state": "open",
                "title": "Automation service is stopped",
                "summary": (
                    "A current operator check confirms that Qadam's scheduled research, "
                    "refresh, scoring, and monitoring processes are stopped. "
                    f"{stale_count} monitored artifacts are overdue and "
                    f"{missing_count} are missing."
                ),
                "root_cause": (
                    "The operator service is not installed."
                    if not operator_installed_reported
                    else "The installed operator service is not currently running."
                ),
                "affected_capabilities": affected_service_labels,
                "affected_count": len(affected_service_labels),
                "first_seen_at": None,
                "last_confirmed_at": operator_service.get("generated_at"),
                "evidence_state": operator_check_state,
                "evidence": [
                    {
                        "label": "Installation",
                        "value": ("Installed" if operator_installed_reported else "Not installed"),
                    },
                    {"label": "Process", "value": "Stopped"},
                    {"label": "Current artifacts", "value": fresh_artifact_count},
                    {"label": "Overdue artifacts", "value": stale_count},
                    {"label": "Missing artifacts", "value": missing_count},
                ],
                "owner": "Python COO / system operator",
                "next_action": (
                    "Review the generated launch configuration, install or start the "
                    "operator service explicitly, and verify a fresh heartbeat."
                ),
                "route": _system_route("system", "overview"),
            }
        )
    elif stale_count or missing_count:
        active_incidents.append(
            {
                "incident_id": "operating_evidence_overdue",
                "severity": "warning",
                "tone": "degraded",
                "state": "open",
                "title": "Operating evidence is overdue",
                "summary": (
                    f"{stale_count} monitored artifacts are overdue and "
                    f"{missing_count} are missing. Decisions that depend on them remain "
                    "fail-closed until refreshed."
                ),
                "root_cause": (
                    "One or more monitored producers missed their freshness threshold "
                    "while the operator service remained current."
                ),
                "affected_capabilities": [
                    "Source qualification",
                    "Pattern scoring",
                    "Decision review",
                    "Paper lifecycle monitoring",
                ],
                "affected_count": 4,
                "first_seen_at": None,
                "last_confirmed_at": freshness.get("generated_at"),
                "evidence_state": freshness.get("status") or "not_reported",
                "evidence": [
                    {"label": "Current artifacts", "value": fresh_artifact_count},
                    {"label": "Overdue artifacts", "value": stale_count},
                    {"label": "Missing artifacts", "value": missing_count},
                ],
                "owner": "Python COO / data operations",
                "next_action": (
                    "Inspect the overdue producers, retry only known-safe refreshes, and "
                    "confirm new timestamps before relying on downstream decisions."
                ),
                "route": _system_route("observe", "sources"),
            }
        )

    disk_free_gb = _optional_float(resource_state.get("disk_free_gb"))
    disk_pause_required = resource_state.get("disk_pause_required") is True
    if disk_pause_required:
        active_incidents.append(
            {
                "incident_id": "host_disk_capacity_critical",
                "severity": "critical",
                "tone": "degraded",
                "state": "open",
                "title": "Host disk capacity requires attention",
                "summary": (
                    "The exported host guard requires disk-sensitive unattended work "
                    "to pause until capacity is restored."
                ),
                "root_cause": "Available disk capacity crossed the configured pause threshold.",
                "affected_capabilities": [
                    "Historical evidence preparation",
                    "Artifact persistence",
                    "Unattended research",
                ],
                "affected_count": 3,
                "first_seen_at": None,
                "last_confirmed_at": heartbeat.get("generated_at"),
                "evidence_state": "current" if heartbeat.get("generated_at") else "not_reported",
                "evidence": [
                    {
                        "label": "Disk free",
                        "value": (
                            f"{disk_free_gb:.1f} GB" if disk_free_gb is not None else "Not reported"
                        ),
                    },
                    {"label": "Disk pause required", "value": "Yes"},
                ],
                "owner": "Python COO / host runtime",
                "next_action": (
                    "Restore safe disk capacity, confirm the pause guard clears, and "
                    "only then resume disk-sensitive unattended work."
                ),
                "route": _system_route("system", "overview"),
            }
        )
    infrastructure_domains = [
        {
            "domain_id": "host",
            "label": "Host & laptop resources",
            "status": "Needs attention" if disk_pause_required else "Partially monitored",
            "tone": "degraded" if disk_pause_required else "unmonitored",
            "metric": (
                f"{disk_free_gb:.1f} GB disk free"
                if disk_free_gb is not None
                else "Disk, CPU, and memory coverage incomplete"
            ),
            "summary": (
                "Disk capacity crossed the configured pause threshold; CPU and RAM "
                "also lack a current public-safe health check."
                if disk_pause_required
                else "Disk capacity is checked, but CPU and RAM do not yet have a "
                "current public-safe health check."
            ),
            "impact": "Resource pressure could interrupt unattended research before Qadam reports it.",
            "last_checked_at": heartbeat.get("generated_at"),
            "owner": "Python COO / host runtime",
            "next_action": (
                "Restore safe disk capacity, then add CPU and memory telemetry."
                if disk_pause_required
                else "Add current CPU and memory telemetry to complete host coverage."
            ),
            "route": _system_route("system", "overview"),
            "components": [
                {
                    "label": "Disk capacity",
                    "status": "Needs attention" if disk_pause_required else "Within threshold",
                    "tone": "degraded" if disk_pause_required else "online",
                    "detail": (
                        f"{disk_free_gb:.1f} GB free"
                        if disk_free_gb is not None
                        else "No current disk measurement"
                    ),
                },
                {
                    "label": "CPU pressure",
                    "status": "No current health check",
                    "tone": "unmonitored",
                    "detail": "CPU load is not exported to this public-safe projection.",
                },
                {
                    "label": "Memory pressure",
                    "status": "No current health check",
                    "tone": "unmonitored",
                    "detail": "RAM pressure is not exported to this public-safe projection.",
                },
            ],
        },
        {
            "domain_id": "runtime",
            "label": "Runtime & automation",
            "status": (
                "Running"
                if operator_running is True
                else "Stopped"
                if operator_running is False
                else "State unverified"
            ),
            "tone": "online" if operator_running is True else "degraded",
            "metric": (
                f"{len(running_scheduled_services)}/{len(scheduled_services)} "
                f"required workflows running · {len(policy_paused_services)} policy-paused"
                if operator_check_current and scheduled_services
                else "Required workflow inventory not reported"
                if operator_check_current
                else "Required workflow state is not currently verified"
            ),
            "summary": (
                "The automation service is running."
                if operator_running is True
                else "A current check confirms that the operator service is stopped."
                if operator_running is False
                else (
                    "The operator-service check is overdue. The last report said "
                    f"{'running' if operator_running_reported else 'stopped'}, but that "
                    "cannot be treated as current state."
                )
            ),
            "impact": (
                "Scheduled ingestion, scoring, review, monitoring, and dashboard refresh are affected."
                if operator_running is False
                else "The current availability of scheduled work cannot be established."
                if operator_running is None
                else "Scheduled operating processes are available."
            ),
            "last_checked_at": operator_service.get("generated_at"),
            "owner": "Python COO / operator service",
            "next_action": (
                "Continue monitoring the current heartbeat."
                if operator_running is True
                else "Install or start the operator service, then verify a fresh heartbeat."
                if operator_running is False
                else "Refresh the operator-service check before diagnosing its process state."
            ),
            "route": _system_route("system", "overview"),
            "components": [
                {
                    "label": "Operator service",
                    "status": (
                        "Running"
                        if operator_running is True
                        else "Stopped"
                        if operator_running is False
                        else "Current state unverified"
                    ),
                    "tone": "online" if operator_running is True else "degraded",
                    "detail": (
                        operator_service.get("status") or "No runtime state exported."
                        if operator_check_current
                        else (
                            "Last reported "
                            f"{'running' if operator_running_reported else 'stopped'}; "
                            f"check state is {operator_check_state.replace('_', ' ')}."
                        )
                    ),
                },
                {
                    "label": "Research supervisor",
                    "status": (
                        heartbeat.get("status") or "Not reported"
                        if operator_check_current
                        else "Current state unverified"
                    ),
                    "tone": (
                        "online"
                        if operator_check_current
                        and str(heartbeat.get("status") or "") == "running"
                        else "degraded"
                        if operator_check_current
                        else "unmonitored"
                    ),
                    "detail": (
                        f"{completed_jobs}/{total_jobs} historical jobs complete"
                        if operator_check_current
                        else (
                            f"Last reported {heartbeat.get('status') or 'not reported'}; "
                            "the current operator check is overdue."
                        )
                    ),
                },
            ],
        },
        {
            "domain_id": "data",
            "label": "Data providers & freshness",
            "status": (
                "Current"
                if source_count and fresh_source_count == source_count
                else "Needs attention"
            ),
            "tone": (
                "online" if source_count and fresh_source_count == source_count else "degraded"
            ),
            "metric": f"{fresh_source_count}/{source_count} sources current",
            "summary": (
                f"{int(source_summary.get('responding_count', 0) or 0)} configured "
                f"sources are responding; {fresh_source_count} are current enough for use."
            ),
            "impact": "Overdue or unavailable source evidence reduces qualification and scoring coverage.",
            "last_checked_at": updated_at(SOURCE_OPERATIONAL_ARTIFACT),
            "owner": "Research Analyst / source adapters",
            "next_action": "Inspect unavailable providers and refresh overdue source observations.",
            "route": _system_route("observe", "sources"),
            "components": [
                {
                    "label": "Configured sources",
                    "status": f"{int(source_summary.get('configured_count', 0) or 0)} configured",
                    "tone": "online",
                    "detail": f"{source_count} source records are represented.",
                },
                {
                    "label": "Responding providers",
                    "status": f"{int(source_summary.get('responding_count', 0) or 0)} responding",
                    "tone": "online"
                    if int(source_summary.get("responding_count", 0) or 0) == source_count
                    else "degraded",
                    "detail": "Provider or adapter availability from the latest source check.",
                },
                {
                    "label": "Quorum-eligible evidence",
                    "status": f"{int(source_summary.get('quorum_eligible_count', 0) or 0)} eligible",
                    "tone": "online" if fresh_source_count else "degraded",
                    "detail": "Only current, qualified sources may contribute to decisions.",
                },
            ],
        },
        {
            "domain_id": "storage",
            "label": "Storage & persistence",
            "status": "Partially monitored",
            "tone": "unmonitored",
            "metric": f"{artifact_count - missing_count}/{artifact_count} monitored artifacts present",
            "summary": (
                "Monitored runtime artifacts are present, but database connectivity, "
                "integrity, and growth do not yet have a complete public-safe check."
            ),
            "impact": "A persistence failure could prevent reliable recovery or historical audit.",
            "last_checked_at": freshness.get("generated_at"),
            "owner": "Python COO / persistence layer",
            "next_action": "Add database connectivity and integrity checks to the System projection.",
            "route": _system_route("system", "overview"),
            "components": [
                {
                    "label": "Runtime artifacts",
                    "status": f"{artifact_count - missing_count}/{artifact_count} present",
                    "tone": "online" if not missing_count else "degraded",
                    "detail": f"{stale_count} present artifacts are overdue.",
                },
                {
                    "label": "Database connectivity",
                    "status": "No current health check",
                    "tone": "unmonitored",
                    "detail": "Database connectivity is not represented in this projection.",
                },
                {
                    "label": "Integrity & growth",
                    "status": "No current health check",
                    "tone": "unmonitored",
                    "detail": "Integrity and storage-growth checks are not currently exported.",
                },
            ],
        },
        {
            "domain_id": "research",
            "label": "Research processing",
            "status": (
                "Evidence building"
                if operator_running is True
                else "Not advancing"
                if operator_running is False
                else "Progress unverified"
            ),
            "tone": (
                "pending"
                if operator_running is True
                else "degraded"
                if operator_running is False
                else "unmonitored"
            ),
            "metric": f"{completed_jobs}/{total_jobs} historical jobs complete",
            "summary": (
                "Historical evidence is still being assembled and tested."
                if operator_running is True
                else "Historical evidence processing is not advancing while automation is stopped."
                if operator_running is False
                else "The latest research-progress evidence is not current enough to establish whether work is advancing."
            ),
            "impact": "Pattern validation and untouched holdout testing cannot complete without prepared evidence.",
            "last_checked_at": heartbeat.get("generated_at"),
            "owner": "Research Analyst / research supervisor",
            "next_action": (
                "Monitor backlog progress and provider throughput."
                if operator_running is True
                else "Restore automation, then monitor backlog progress and provider throughput."
                if operator_running is False
                else "Refresh the operator and research heartbeats before diagnosing progress."
            ),
            "route": _system_route("patterns", "findings"),
            "components": [
                {
                    "label": "Historical preparation",
                    "status": f"{completed_jobs}/{total_jobs} complete",
                    "tone": (
                        "online"
                        if total_jobs and completed_jobs == total_jobs
                        else "pending"
                        if operator_running is True and total_jobs
                        else "degraded"
                        if operator_running is False and total_jobs
                        else "unmonitored"
                    ),
                    "detail": f"{int(backfill_progress.get('remaining_jobs', 0) or 0)} jobs remain.",
                },
                {
                    "label": "Validated edge registry",
                    "status": f"{validated_edges} validated",
                    "tone": "online" if validated_edges else "pending",
                    "detail": "A zero count is a research result, not itself an infrastructure failure.",
                },
            ],
        },
        {
            "domain_id": "paper_broker",
            "label": "Paper broker & order monitoring",
            "status": (
                "Connection evidence current"
                if alpaca_source.get("fresh") is True
                else "Connection evidence overdue"
            ),
            "tone": "online" if alpaca_source.get("fresh") is True else "degraded",
            "metric": "Monitoring only · no new paper orders",
            "summary": (
                "Alpaca paper connectivity is represented by source evidence; the order "
                "route remains intentionally locked by policy."
            ),
            "impact": "Order and position monitoring may be outdated when broker evidence is overdue.",
            "last_checked_at": alpaca_source.get("observed_at"),
            "owner": "PaperOps / broker mirror",
            "next_action": "Refresh the Alpaca paper probe; keep order submission policy-locked.",
            "route": _system_route("trade", "orders"),
            "components": [
                {
                    "label": "Alpaca paper evidence",
                    "status": ("Current" if alpaca_source.get("fresh") is True else "Overdue"),
                    "tone": "online" if alpaca_source.get("fresh") is True else "degraded",
                    "detail": (
                        "Provider responding"
                        if alpaca_source.get("responding") is True
                        else "Provider response not current"
                    ),
                },
                {
                    "label": "New paper-order permission",
                    "status": "Paused by policy",
                    "tone": "policy",
                    "detail": why_not_trading,
                },
            ],
        },
        {
            "domain_id": "communications",
            "label": "Communications & notifications",
            "status": "No current health check",
            "tone": "unmonitored",
            "metric": "Delivery state not represented",
            "summary": (
                "Telegram and other outbound notification delivery are not diagnosed "
                "inside the current System projection."
            ),
            "impact": "A delivery failure could go unnoticed even when Qadam produced a valid brief.",
            "last_checked_at": None,
            "owner": "Python COO / communications",
            "next_action": "Add sanitized delivery probes and last-success evidence.",
            "route": _system_route("system", "overview"),
            "components": [
                {
                    "label": "Telegram delivery",
                    "status": "No current health check",
                    "tone": "unmonitored",
                    "detail": "No delivery receipt or current probe is exposed here.",
                },
            ],
        },
        {
            "domain_id": "deployment",
            "label": "Deployment & configuration",
            "status": "Partially monitored",
            "tone": "unmonitored",
            "metric": "Release policy recorded · deployment drift unchecked",
            "summary": (
                "Governed paper-release state is recorded, but the currently deployed "
                "build, configuration integrity, and repository drift do not yet have a "
                "complete public-safe health check."
            ),
            "impact": (
                "Deployment drift could affect the live dashboard or operating services "
                "without being diagnosed here."
            ),
            "last_checked_at": operator_certification.get("generated_at"),
            "owner": "Python COO / deployment operations",
            "next_action": (
                "Add release-receipt, configuration-integrity, and repository-drift "
                "checks; keep paper-release policy in the separate governance component."
            ),
            "route": _system_route("system", "overview"),
            "components": [
                {
                    "label": "Operator certification",
                    "status": operator_certification.get("certification_state")
                    or operator_certification.get("status")
                    or "Not reported",
                    "tone": "online"
                    if operator_certification.get("status") == "passed"
                    else "pending",
                    "detail": (
                        "A governance and readiness assessment, not a deployment-health probe."
                    ),
                },
                {
                    "label": "Paper release",
                    "status": "Effective" if release.get("release_effective") is True else "Held",
                    "tone": "online" if release.get("release_effective") is True else "policy",
                    "detail": why_not_trading,
                },
                {
                    "label": "Deployed build & configuration",
                    "status": "No current health check",
                    "tone": "unmonitored",
                    "detail": (
                        "Current release integrity and repository-to-deployment drift "
                        "are not represented in this projection."
                    ),
                },
            ],
        },
    ]
    unmonitored_domain_count = sum(
        domain.get("tone") == "unmonitored" for domain in infrastructure_domains
    )
    monitoring_gaps = [
        "host_cpu_utilization",
        "host_memory_utilization",
        "database_connectivity_and_integrity",
        "per_workflow_success_and_failure_history",
        "communications_delivery_health",
        "current_deployment_and_repository_drift",
    ]
    affected_domain_count = sum(
        domain.get("tone") in {"degraded", "unmonitored"} for domain in infrastructure_domains
    )
    overall_state = "degraded" if active_incidents or affected_domain_count else "healthy"
    overall_health = {
        "state": overall_state,
        "label": (
            "Needs attention"
            if active_incidents
            else "Partially monitored"
            if unmonitored_domain_count
            else "Healthy"
        ),
        "headline": (
            "Qadam's operating infrastructure needs attention."
            if active_incidents
            else "Qadam's monitored infrastructure is healthy, but coverage is incomplete."
            if unmonitored_domain_count
            else "Qadam's monitored operating infrastructure is healthy."
        ),
        "summary": (
            (
                "The operator-service check is overdue, so automation state is "
                f"unverified. {stale_count} monitored artifacts are overdue and "
                f"{missing_count} are missing."
            )
            if not operator_check_current
            else (
                "A current check confirms automation is stopped. "
                f"{stale_count} monitored artifacts are overdue and "
                f"{missing_count} are missing."
            )
            if operator_running is False
            else (f"{stale_count} monitored artifacts are overdue and {missing_count} are missing.")
            if stale_count or missing_count
            else (
                "All current checks are healthy, but "
                f"{unmonitored_domain_count} infrastructure domains still have "
                "incomplete monitoring."
            )
            if unmonitored_domain_count
            else "All currently monitored operating checks are healthy."
        ),
        "primary_cause": (
            active_incidents[0]["root_cause"]
            if active_incidents
            else (
                f"{unmonitored_domain_count} infrastructure domains do not yet "
                "have complete health coverage."
                if unmonitored_domain_count
                else "No active operating incident is currently exported."
            )
        ),
        "operational_effect": (
            f"{affected_domain_count} infrastructure areas need attention."
            if affected_domain_count
            else "No monitored infrastructure area is currently affected."
        ),
        "page_updated_at": generated_at,
        "last_operator_service_check_at": operator_service.get("generated_at"),
        "operator_service_check_state": operator_check_state,
        "last_known_healthy_at": None,
        "open_incident_count": len(active_incidents),
        "affected_domain_count": affected_domain_count,
        "monitoring_gap_count": unmonitored_domain_count,
        "explicit_monitoring_gap_count": len(monitoring_gaps),
        "metrics": [
            {
                "label": "Automation",
                "value": (
                    "Running"
                    if operator_running is True
                    else "Stopped"
                    if operator_running is False
                    else "State unverified"
                ),
                "tone": "online" if operator_running is True else "degraded",
            },
            {
                "label": "Active incidents",
                "value": len(active_incidents),
                "tone": "online" if not active_incidents else "degraded",
            },
            {
                "label": "Fresh evidence",
                "value": (
                    f"{fresh_artifact_count} of {artifact_count}"
                    if artifact_count
                    else "Not reported"
                ),
                "tone": (
                    "online"
                    if artifact_count and fresh_artifact_count == artifact_count
                    else "degraded"
                    if artifact_count
                    else "unmonitored"
                ),
            },
            {
                "label": "Unmonitored domains",
                "value": unmonitored_domain_count,
                "tone": "online" if not unmonitored_domain_count else "unmonitored",
            },
            {
                "label": "Required workflows running",
                "value": (
                    f"{len(running_scheduled_services)} of {len(scheduled_services)}"
                    if operator_check_current and scheduled_services
                    else "Not reported"
                    if operator_check_current
                    else "Not verified"
                ),
                "tone": (
                    "online"
                    if operator_check_current
                    and scheduled_services
                    and len(running_scheduled_services) == len(scheduled_services)
                    else "degraded"
                    if scheduled_services or not operator_check_current
                    else "unmonitored"
                ),
            },
        ],
    }
    operating_mode = {
        "state": runtime_state,
        "label": runtime_state.replace("-", " ").title(),
        "tone": "policy"
        if runtime_state == "research-only"
        else ("online" if runtime_state == "paper-operational" else "degraded"),
        "headline": (
            "Paper trading is intentionally monitoring-only."
            if runtime_state == "research-only"
            else system_headline
        ),
        "explanation": why_not_trading,
        "is_infrastructure_failure": False,
    }
    historical_workload_complete = bool(total_jobs and completed_jobs == total_jobs)
    historical_workload_status = (
        "Complete"
        if historical_workload_complete
        else "In progress"
        if operator_running is True and total_jobs
        else "Not advancing"
        if operator_running is False and total_jobs
        else "Progress unverified"
        if total_jobs
        else "Not reported"
    )
    historical_workload_tone = (
        "online"
        if historical_workload_complete
        else "pending"
        if operator_running is True and total_jobs
        else "degraded"
        if operator_running is False and total_jobs
        else "unmonitored"
    )
    running_count_known = bool(operator_check_current and scheduled_services)
    services_and_jobs = {
        "status": (
            "running"
            if operator_running is True
            else "stopped"
            if operator_running is False
            else "state_unverified"
        ),
        "headline": (
            (
                f"{len(running_scheduled_services)} of {len(scheduled_services)} "
                "required workflows are running."
            )
            if running_count_known
            else "No required workflow inventory was exported."
            if operator_check_current
            else (
                "Required workflow state is unverified because the operator-service "
                f"check is {operator_check_state.replace('_', ' ')}. The last report "
                f"showed {len(reported_running_scheduled_services)} of "
                f"{len(scheduled_services)} "
                "required workflows running."
            )
        ),
        "running_count": (len(running_scheduled_services) if running_count_known else None),
        "running_count_known": running_count_known,
        "scheduled_count": len(scheduled_services),
        "service_count": len(service_rows),
        "stopped_count": (len(stopped_scheduled_services) if operator_check_current else None),
        "policy_paused_count": len(policy_paused_services),
        "last_checked_at": operator_service.get("generated_at"),
        "check_freshness_state": operator_check_state,
        "services": service_rows,
        "workloads": [
            {
                "workload_id": "historical_evidence_backfill",
                "label": "Historical evidence preparation",
                "status": historical_workload_status,
                "tone": historical_workload_tone,
                "completed": completed_jobs,
                "total": total_jobs,
                "remaining": int(backfill_progress.get("remaining_jobs", 0) or 0),
                "progress_fraction": safe_float(backfill_progress.get("progress_fraction")),
                "throughput_units_per_second": safe_float(
                    heartbeat.get("throughput_units_per_second")
                ),
                "last_progress_at": heartbeat.get("generated_at"),
                "stuck": bool(
                    total_jobs and completed_jobs < total_jobs and operator_running is False
                ),
            }
        ],
    }
    data_dependencies = {
        "sources": {
            "configured_count": int(source_summary.get("configured_count", 0) or 0),
            "responding_count": int(source_summary.get("responding_count", 0) or 0),
            "fresh_count": fresh_source_count,
            "quorum_eligible_count": int(source_summary.get("quorum_eligible_count", 0) or 0),
            "source_count": source_count,
            "last_checked_at": updated_at(SOURCE_OPERATIONAL_ARTIFACT),
        },
        "artifacts": {
            "artifact_count": artifact_count,
            "fresh_count": fresh_artifact_count,
            "stale_count": stale_count,
            "missing_count": missing_count,
            "last_checked_at": freshness.get("generated_at"),
        },
        "historical_jobs": {
            "completed_jobs": completed_jobs,
            "total_jobs": total_jobs,
            "remaining_jobs": int(backfill_progress.get("remaining_jobs", 0) or 0),
            "last_checked_at": heartbeat.get("generated_at"),
            "status": historical_workload_status,
            "tone": historical_workload_tone,
        },
        "key_dependencies": [
            {
                "dependency_id": "alpaca_paper",
                "label": "Alpaca Paper",
                "status": ("Current" if alpaca_source.get("fresh") is True else "Evidence overdue"),
                "tone": "online" if alpaca_source.get("fresh") is True else "degraded",
                "last_checked_at": alpaca_source.get("observed_at"),
                "impact": "Provides paper broker and market context.",
            },
            {
                "dependency_id": "database_storage",
                "label": "Database & persistent storage",
                "status": "No current health check",
                "tone": "unmonitored",
                "last_checked_at": None,
                "impact": "Stores durable operating and research evidence.",
            },
            {
                "dependency_id": "telegram_delivery",
                "label": "Telegram delivery",
                "status": "No current health check",
                "tone": "unmonitored",
                "last_checked_at": None,
                "impact": "Delivers outbound learning and operating briefs.",
            },
            {
                "dependency_id": "quantum_provider_path",
                "label": "Quantum provider path",
                "status": "Experimental pathway",
                "tone": "pending",
                "last_checked_at": quantum_review.get("generated_at"),
                "impact": "Supports bounded nonlinear and quantum research comparisons.",
            },
        ],
    }
    dependency_edges = [
        {
            "from": "operator_service",
            "to": "scheduled_processes",
            "state": (
                "healthy"
                if operator_running is True
                else "affected"
                if operator_running is False
                else "unverified"
            ),
            "impact": (
                "The current operator check is overdue, so scheduled-process "
                "availability cannot be established."
                if operator_running is None
                else "Stopping the operator pauses scheduled ingestion, scoring, review, and monitoring."
            ),
        },
        {
            "from": "source_evidence",
            "to": "pattern_scoring",
            "state": "affected" if fresh_source_count < source_count else "healthy",
            "impact": "Only current qualified source evidence may enter pattern scoring.",
        },
        {
            "from": "pattern_validation",
            "to": "decision_review",
            "state": "healthy",
            "impact": (
                "A complete current setup may enter experimental Akber and Router review "
                "without being called a validated edge. Validated strategy promotion still "
                "requires the stricter edge evidence standard."
            ),
        },
        {
            "from": "decision_review",
            "to": "paper_order_route",
            "state": "paused_by_policy" if runtime_state == "research-only" else "healthy",
            "impact": "Paper orders remain policy-locked until every governed release condition passes.",
        },
    ]
    system_events = [
        {
            "event_id": f"incident:{incident['incident_id']}",
            "event_type": "incident",
            "tone": incident["tone"],
            "generated_at": incident.get("last_confirmed_at"),
            "title": incident["title"],
            "summary": incident["summary"],
            "state_change": "Active incident confirmed",
            "route": incident.get("route"),
        }
        for incident in active_incidents
    ]
    system_events.extend(
        {
            "event_id": item.get("activity_id"),
            "event_type": "evidence",
            "tone": item.get("tone"),
            "generated_at": item.get("generated_at"),
            "title": item.get("label"),
            "summary": item.get("summary"),
            "state_change": (
                "Evidence refreshed"
                if item.get("freshness_state") == "fresh"
                else "Evidence remains overdue"
            ),
            "route": item.get("route"),
        }
        for item in _system_recent_activity(freshness)
    )
    system_events.sort(
        key=lambda row: str(row.get("generated_at") or ""),
        reverse=True,
    )
    certification_groups = operator_certification.get("groups")
    certification_groups = certification_groups if isinstance(certification_groups, dict) else {}
    return {
        "artifact_type": "qadam_system_overview",
        "diagnostic_contract_version": "qadam_system_diagnostics.v2",
        "generated_at": generated_at,
        "status": "needs_attention" if overall_state == "degraded" else "operational",
        "overall_health": overall_health,
        "operating_mode": operating_mode,
        "root_cause_incidents": {
            "total_count": len(active_incidents),
            "critical_count": sum(
                incident.get("severity") == "critical" for incident in active_incidents
            ),
            "warning_count": sum(
                incident.get("severity") == "warning" for incident in active_incidents
            ),
            "rows": active_incidents,
        },
        "infrastructure_domains": infrastructure_domains,
        "services_schedules_jobs": services_and_jobs,
        "data_dependencies": data_dependencies,
        "dependency_edges": dependency_edges,
        "system_events": {
            "total_count": len(system_events),
            "rows": system_events[:12],
        },
        "current_state": {
            "state": runtime_state,
            "tone": "pending"
            if runtime_state == "research-only"
            else ("online" if runtime_state == "paper-operational" else "degraded"),
            "headline": system_headline,
            "why_not_trading_now": why_not_trading,
            "metrics": [
                {"label": "System mode", "value": runtime_state.replace("-", " ")},
                {
                    "label": "Operator",
                    "value": (
                        "running"
                        if operator_running is True
                        else "not running"
                        if operator_running is False
                        else "state unverified"
                    ),
                },
                {"label": "Sources", "value": f"{fresh_source_count}/{source_count} fresh"},
                {"label": "Historical evidence", "value": f"{completed_jobs}/{total_jobs} jobs"},
                {"label": "Validated edges", "value": validated_edges},
                {"label": "Paper operations", "value": paperops_state},
            ],
        },
        "flow": flow,
        "running_now": {
            "status": (
                "running"
                if operator_running is True
                else "not_running"
                if operator_running is False
                else "state_unverified"
            ),
            "headline": (
                (
                    f"{len(running_scheduled_services)} of {len(scheduled_services)} "
                    "required workflows are currently running."
                )
                if operator_check_current and services
                else "Current workflow state is not verified."
                if services
                else "No service inventory was exported."
            ),
            "running_count": (len(running_scheduled_services) if operator_check_current else None),
            "service_count": len(services),
            "updated_at": operator_service.get("generated_at"),
            "services": service_rows,
        },
        "health_domains": health_domains,
        "needs_attention": _system_needs_attention(operator_why_not, operator_certification),
        "recent_activity": _system_recent_activity(freshness),
        "technical_diagnostics": {
            "freshness": {
                "status": freshness.get("status"),
                "artifact_count": artifact_count,
                "fresh_count": fresh_artifact_count,
                "stale_count": stale_count,
                "missing_count": missing_count,
                "records": [
                    {
                        "artifact": record.get("artifact"),
                        "exists": record.get("exists") is True,
                        "generated_at": record.get("generated_at"),
                        "age_seconds": record.get("age_seconds"),
                        "stale_after_seconds": record.get("stale_after_seconds"),
                        "overdue_seconds": max(
                            0,
                            int(record.get("age_seconds", 0) or 0)
                            - int(record.get("stale_after_seconds", 0) or 0),
                        ),
                        "freshness_state": record.get("freshness_state"),
                    }
                    for record in freshness_records
                ],
            },
            "operator_service": {
                "status": operator_service.get("status"),
                "installed": (operator_installed_reported if operator_check_current else None),
                "running": operator_running,
                "last_reported_installed": operator_installed_reported,
                "last_reported_running": operator_running_reported,
                "check_freshness_state": operator_check_state,
                "operational_ready": (
                    operator_service.get("operational_ready") is True
                    if operator_check_current
                    else None
                ),
                "last_reported_operational_ready": (
                    operator_service.get("operational_ready") is True
                ),
                "generated_at": operator_service.get("generated_at"),
                "repair_queue": {
                    "status": operator_repair_queue.get("status"),
                    "generated_at": operator_repair_queue.get("generated_at"),
                    "open_request_count": int(
                        operator_repair_queue.get("open_request_count", 0) or 0
                    ),
                    "critical_request_count": int(
                        operator_repair_queue.get("critical_request_count", 0) or 0
                    ),
                    "requests": [
                        {
                            "repair_request_id": request.get("repair_request_id"),
                            "severity": request.get("severity"),
                            "state": request.get("state"),
                            "category": request.get("category"),
                            "summary": request.get("summary"),
                            "required_action": request.get("required_action"),
                        }
                        for request in repair_requests
                    ],
                },
            },
            "supervisor": {
                "status": heartbeat.get("status"),
                "generated_at": heartbeat.get("generated_at"),
                "current_job_id": heartbeat.get("current_job_id"),
                "current_phase": heartbeat.get("current_phase"),
                "estimated_remaining_seconds": heartbeat.get("estimated_remaining_seconds"),
                "last_successful_provider_call_at": heartbeat.get(
                    "last_successful_provider_call_at"
                ),
                "throughput_units_per_second": safe_float(
                    heartbeat.get("throughput_units_per_second")
                ),
                "resource_state": resource_state,
                "progress": backfill_progress,
            },
            "certification": {
                "status": operator_certification.get("status"),
                "state": permanent_reliability.get("status")
                or operator_certification.get("certification_state"),
                "operator_ready_state": operator_certification.get(
                    "certification_state"
                ),
                "levels": operator_certification.get("certification_levels") or {},
                "groups": [
                    {
                        "group_id": group_id,
                        "status": group.get("status"),
                        "check_count": group.get("check_count", 0),
                        "passed_check_count": group.get("passed_check_count", 0),
                        "failed_check_count": group.get("failed_check_count", 0),
                    }
                    for group_id, group in certification_groups.items()
                    if isinstance(group, dict)
                ],
            },
            "permanent_reliability": {
                "status": permanent_reliability.get("status") or "not_reported",
                "implementation_complete": permanent_reliability.get("implementation_complete")
                is True,
                "permanent_reliability_certified": permanent_reliability.get(
                    "permanent_reliability_certified"
                )
                is True,
                "real_soak_elapsed_seconds": safe_float(
                    permanent_reliability.get("real_soak_elapsed_seconds")
                ),
                "real_soak_required_seconds": safe_float(
                    permanent_reliability.get("real_soak_required_seconds")
                ),
                "open_circuit_count": int(permanent_reliability.get("open_circuit_count") or 0),
                "repair_request_count": int(permanent_reliability.get("repair_request_count") or 0),
                "blockers": list(permanent_reliability.get("blockers") or []),
                "generated_at": permanent_reliability.get("generated_at"),
            },
            "release": {
                "status": release.get("status"),
                "release_recommended": release.get("release_recommended") is True,
                "release_effective": release.get("release_effective") is True,
                "blocker_count": len(release.get("blockers") or []),
            },
            "monitoring_coverage": {
                "monitored_artifact_count": artifact_count,
                "infrastructure_domain_count": len(infrastructure_domains),
                "unmonitored_domain_count": unmonitored_domain_count,
                "monitoring_gap_count": len(monitoring_gaps),
                "gaps": monitoring_gaps,
            },
        },
        "boundary": "System Overview is public-safe and read-only. It cannot create commands, approve trades, submit orders, write to brokers, grant proof credit, or enable live capital.",
    }


def _communication_mirror(
    why_not: dict[str, Any],
    dedupe: list[dict[str, Any]],
    previous: dict[str, Any],
    generated_at: str,
    *,
    validated_edge_count: int,
    paper_review_candidate_count: int,
) -> dict[str, Any]:
    body = (
        f"Qadam has {paper_review_candidate_count} paper-review candidates and "
        f"{validated_edge_count} validated edges. Research remains active while "
        "evidence matures."
        if why_not.get("status") != "paper_review_candidate_available"
        else f"Qadam has {paper_review_candidate_count} paper-review candidates and "
        f"{validated_edge_count} validated edges. Any candidate can proceed only "
        "through guarded paper-only checks."
    )
    digest = telegram_message_fingerprint("", body)
    prior_hashes = {
        str(
            record.get("message_hash")
            or record.get("dedupe_hash")
            or record.get("event_fingerprint")
            or ""
        )
        for record in dedupe
    }
    prior_hashes.update(
        str(record.get("message_hash") or "")
        for record in previous.get("latest_messages", [])
        if isinstance(record, dict)
    )
    duplicate = digest in prior_hashes
    style = telegram_human_message_style("", body)
    quality_errors: list[str] = []
    if style.get("status") != "human":
        quality_errors.extend(str(error) for error in style.get("errors") or [])
    if len(body) > 220:
        quality_errors.append("body_exceeds_220_characters")
    if style.get("sentence_count") != 2:
        quality_errors.append("operator_note_must_have_two_sentences")
    if str(validated_edge_count) not in body or str(paper_review_candidate_count) not in body:
        quality_errors.append("specific_runtime_counts_missing")
    quality_errors = unique_errors(quality_errors)
    quality_passed = not quality_errors
    status = (
        "message_rejected_duplicate"
        if duplicate
        else "message_rejected_quality"
        if not quality_passed
        else "message_ready_for_review"
    )
    message = {
        "message_id": stable_id("operator-telegram-note", digest),
        "message_class": "operator_status",
        "status": status,
        "body": body,
        "character_count": len(body),
        "message_hash": digest,
        "deduplicated": duplicate,
        "quality_passed": quality_passed,
        "quality_errors": quality_errors,
        "human_style": style,
        "public_safe": True,
        "notify_only": True,
        "live_send_allowed": False,
        "command_path_enabled": False,
        "trade_candidate_created": False,
        "paper_order_created": False,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_communications_mirror",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "review_only",
        "message_candidate_count": 1,
        "message_ready_count": 1 if status == "message_ready_for_review" else 0,
        "message_rejected_duplicate_count": 1 if duplicate else 0,
        "message_rejected_quality_count": 1 if status == "message_rejected_quality" else 0,
        "deduplication": {
            "material_change_required_for_repeat": True,
            "prior_hash_count": len(prior_hashes),
            "duplicate_suppressed": duplicate,
        },
        "latest_messages": [message],
        "telegram_live_send_allowed": False,
        "telegram_command_path_enabled": False,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "authority": authority_flags(),
    }


def _route_contract_audit() -> dict[str, Any]:
    path = ROOT / "landing-page-repo" / "dashboard.js"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    pinned_position = text.find(
        'const QSASE_TEAM_ROUTE = { moduleId: "system", viewId: "team", label: "Qadam Team" };'
    )
    navigation_position = text.find("const QSASE_DASHBOARD_NAVIGATION")
    grouped_positions = [
        text.find(f'{{ id: "{view_id}", label:', navigation_position)
        for _module, _label, views in PROTECTED_NAVIGATION
        for view_id, _label in views
    ]
    positions = [pinned_position, *grouped_positions]
    route_order_preserved = (
        bool(positions)
        and all(value >= 0 for value in positions)
        and positions == sorted(positions)
    )
    return {
        "dashboard_js_exists": path.exists(),
        "protected_route_count": len(ROUTE_ORDER),
        "protected_route_order_preserved": route_order_preserved,
        "team_pinned_before_fund": pinned_position >= 0
        and pinned_position < text.find('{ id: "portfolio", label: "Portfolio" }'),
        "system_standalone_sidebar_link": (
            'class="qsase-standalone-nav qsase-system-nav' in text
            and "QSASE_DASHBOARD_NAVIGATION.filter((module) => !module.crossCutting)" in text
        ),
        "legacy_system_aliases_present": (
            'candidate === "system/activity"' in text and 'candidate === "system/health"' in text
        ),
        "legacy_learning_aliases_present": (
            'candidate === "learn/replay"' in text and 'candidate === "learn/briefs"' in text
        ),
        "cross_cutting_routes_use_lifecycle_context": (
            "data-lifecycle-relationship" in text and "is-cross-cutting" in text
        ),
        "default_route_preserved": (
            'const QSASE_DEFAULT_ROUTE = { moduleId: "fund", viewId: "portfolio" };' in text
        ),
        "query_deep_link_contract_present": "params.module" in text
        and "params.view" in text
        and "qsaseDashboardRouteHref" in text,
        "desktop_sidebar_present": "data-qsase-sidebar" in text,
        "mobile_section_control_present": "qsase-mobile-navigation" in text
        and "data-qsase-sidebar-toggle" in text,
        "refresh_interval_preserved": "DASHBOARD_STATUS_REFRESH_MS = 15000" in text,
        "refresh_navigation_state_preserved": "captureQsaseNavigationState" in text
        and "restoreQsaseNavigationState" in text,
        "lifecycle_component_present": "data-qadam-lifecycle" in text
        and "renderQadamLifecycleTimeline" in text,
        "legacy_journey_navigation_removed": "data-qsase-journey" not in text
        and "renderQsaseJourneyNavigation" not in text,
    }


def _portfolio_truth_audit(
    status: dict[str, Any], series: dict[str, Any], current: dict[str, Any]
) -> dict[str, Any]:
    portfolio = status.get("dashboard_portfolio")
    portfolio = portfolio if isinstance(portfolio, dict) else {}
    latest_rows = series.get("series")
    latest_rows = latest_rows if isinstance(latest_rows, list) else []
    latest = latest_rows[-1] if latest_rows else {}
    values = {
        "portfolio_card": portfolio.get("current_value_gbp"),
        "portfolio_series_summary": series.get("current_value_gbp") or series.get("latest_value"),
        "portfolio_chart_latest": latest.get("portfolio_value") or latest.get("equity_gbp"),
        "current_portfolio_contract": current.get("portfolio_consistency", {}).get("current_value"),
    }
    numeric = [safe_float(value) for value in values.values() if value is not None]
    delta = max(numeric) - min(numeric) if numeric else None
    return {
        "values": values,
        "available_value_count": len(numeric),
        "maximum_value_delta": round(delta, 8) if delta is not None else None,
        "all_portfolio_values_agree": len(numeric) >= 3 and delta is not None and delta <= 0.01,
        "position_count_agrees": int(portfolio.get("open_position_count", 0) or 0)
        == int(current.get("position_count", 0) or 0),
        "display_currency": portfolio.get("display_currency"),
    }


def build_operator_dashboard_state(
    settings: Settings | None = None,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    generated = generated_at or now_iso()
    dashboard_status = read_json(runtime / DASHBOARD_STATUS_ARTIFACT)
    portfolio_series = read_json(runtime / PORTFOLIO_SERIES_ARTIFACT)
    current_portfolio = read_json(runtime / CURRENT_PORTFOLIO_ARTIFACT)
    trading_history = read_json(runtime / TRADING_HISTORY_ARTIFACT)
    source_network = read_json(runtime / SOURCE_NETWORK_ARTIFACT)
    operational_sources = read_jsonl(runtime / SOURCE_OPERATIONAL_ARTIFACT)
    reliability_sources = read_jsonl(runtime / SOURCE_RELIABILITY_RECORDS_ARTIFACT)
    trading_universe = read_json(runtime / TRADING_UNIVERSE_ARTIFACT)
    strategy_universe = read_json(runtime / STRATEGY_UNIVERSE_ARTIFACT)
    strategy_evidence = read_json(runtime / STRATEGY_EVIDENCE_ARTIFACT)
    scores = read_jsonl(runtime / PATTERN_SCORE_ARTIFACT)
    edge_summary = read_json(runtime / EDGE_SUMMARY_ARTIFACT)
    hypotheses = read_jsonl(runtime / HYPOTHESES_ARTIFACT)
    foundry = read_json(runtime / FOUNDRY_ARTIFACT)
    akber_results = read_jsonl(runtime / AKBER_RESULTS_ARTIFACT)
    akber_dashboard = read_json(runtime / AKBER_DASHBOARD_ARTIFACT)
    shadow_state = read_json(runtime / SHADOW_STATE_ARTIFACT)
    router_scoreboard = read_json(runtime / ROUTER_SCOREBOARD_ARTIFACT)
    router_why_not = read_json(runtime / ROUTER_WHY_NOT_ARTIFACT)
    handoffs = read_jsonl(runtime / HANDOFF_ARTIFACT)
    validated_release = read_json(runtime / RELEASE_ARTIFACT)
    experimental_release = read_json(runtime / EXPERIMENTAL_RELEASE_ARTIFACT)
    release = (
        {
            **experimental_release,
            "release_effective": experimental_release.get("experimental_paper_release_effective")
            is True,
            "release_recommended": experimental_release.get("experimental_paper_release_ready")
            is True,
            "release_mode": "experimental_unvalidated",
        }
        if experimental_release
        else validated_release
    )
    lifecycle = read_json(runtime / LIFECYCLE_ARTIFACT)
    proof = read_json(runtime / PROOF_ARTIFACT)
    learning = read_jsonl(runtime / ATTRIBUTION_ARTIFACT)
    backfill = read_json(runtime / BACKFILL_ARTIFACT)
    heartbeat = read_json(runtime / SUPERVISOR_HEARTBEAT_ARTIFACT)
    operator_service = read_json(runtime / OPERATOR_SERVICE_ARTIFACT)
    operator_why_not = read_json(runtime / OPERATOR_WHY_NOT_RUNNING_ARTIFACT)
    operator_repair_queue = read_json(runtime / OPERATOR_REPAIR_QUEUE_ARTIFACT)
    operator_certification = read_json(runtime / OPERATOR_CERTIFICATION_ARTIFACT)
    permanent_reliability = read_json(runtime / PERMANENT_RELIABILITY_ARTIFACT)
    tradeability_compiler = read_json(runtime / TRADEABILITY_COMPILER_ARTIFACT)
    experimental_trial = read_json(runtime / EXPERIMENTAL_TRIAL_ARTIFACT)
    experimental_soak = read_json(runtime / EXPERIMENTAL_SOAK_ARTIFACT)
    experimental_certification = read_json(runtime / EXPERIMENTAL_CERTIFICATION_ARTIFACT)
    lock = read_json(runtime / LOCK_ARTIFACT)
    anti_slop = read_json(runtime / ANTI_SLOP_ARTIFACT)
    learning_backtest_gap = read_json(runtime / LEARNING_BACKTEST_GAP_ARTIFACT)
    backtest_completion = read_json(runtime / BACKTEST_COMPLETION_ARTIFACT)
    material_learning_delta = read_json(runtime / MATERIAL_LEARNING_DELTA_ARTIFACT)
    ef11_dashboard = read_json(runtime / EF11_DASHBOARD_ARTIFACT)
    ef11_certification = read_json(runtime / EF11_CERTIFICATION_ARTIFACT)
    ef11_telegram_candidate = read_json(runtime / EF11_TELEGRAM_CANDIDATE_ARTIFACT)
    qualitative_dashboard = read_json(runtime / QUALITATIVE_DASHBOARD_ARTIFACT)
    qualitative_communications = read_json(runtime / QUALITATIVE_COMMUNICATIONS_ARTIFACT)
    research_progression = read_json(runtime / RESEARCH_PROGRESSION_ARTIFACT)
    dedupe = read_jsonl(runtime / TELEGRAM_DEDUPE_ARTIFACT, limit=500)
    previous_communications = read_json(runtime / COMMUNICATIONS_ARTIFACT)
    learning_cycle = build_learning_cycle_view_model(settings, generated_at=generated)
    improvement_pipeline = build_improvement_pipeline_view_model(
        settings,
        generated_at=generated,
    )
    stage1_learning_input = build_stage1_learning_input(
        settings,
        generated_at=generated,
        pipeline_override=improvement_pipeline,
    )
    freshness = build_freshness_audit(settings, generated_at=generated)
    source_summary = _source_summary(operational_sources, reliability_sources)
    pattern_views = build_pattern_dashboard_views(settings, generated_at=generated)
    pattern_discovery = pattern_views["pattern_discovery"]
    quantum_review = pattern_views["quantum_review"]
    findings = pattern_discovery["relationships"]
    lifecycle_contract = build_lifecycle_contract(generated_at=generated)
    route_stage_map = build_route_stage_map(generated_at=generated)
    lifecycle_dashboard = build_lifecycle_dashboard_summary(
        {
            "source_summary": source_summary,
            "trading_universe": trading_universe,
            "backfill_progress": (
                heartbeat.get("progress") if isinstance(heartbeat.get("progress"), dict) else {}
            ),
            "findings": findings,
            "quantum_review": quantum_review,
            "hypotheses": hypotheses,
            "foundry": foundry,
            "edge_summary": edge_summary,
            "shadow_state": shadow_state,
            "akber_results": akber_results,
            "router_scoreboard": router_scoreboard,
            "router_why_not": router_why_not,
            "handoff_count": len(handoffs),
            "release": release,
            "lifecycle": lifecycle,
            "current_portfolio": current_portfolio,
            "learning_cycle": learning_cycle,
            "improvement_pipeline": improvement_pipeline,
            "freshness": freshness,
        },
        generated_at=generated,
    )
    stage_counts = Counter(str(record.get("stage") or "unknown") for record in findings)
    pattern_compat = {
        "status": pattern_discovery["status"],
        "summary": pattern_discovery["headline"],
        "finding_count": len(findings),
        "paper_ready_count": 0,
        "findings": findings,
        "stage_counts": {
            "found": 0,
            "documented": len(findings),
            "validated": stage_counts.get("validated_edge", 0),
            "trade_candidate": 0,
            "paper_ready": 0,
        },
        "human_brief": {
            "body": pattern_discovery["qualitative_analysis"]["summary"],
        },
        "qualitative_analysis": pattern_discovery["qualitative_analysis"],
        "technical_diagnostics": {
            "linear_pattern_count": len(scores),
            "nonlinear_pattern_count": 0,
            "quantum_review_count": quantum_review["empirical_comparison_count"],
            "linear_rows": [],
            "nonlinear_rows": [],
            "quantum_rows": [],
        },
    }
    router_compat = _router_compatibility(router_scoreboard, router_why_not, akber_results)
    gate_compat = _paperops_gate_compatibility(router_scoreboard, release, len(handoffs))
    lifecycle_compat = _lifecycle_compatibility(lifecycle, proof)
    learning_compat = _learning_compatibility(learning, proof)
    communications = _communication_mirror(
        router_why_not,
        dedupe,
        previous_communications,
        generated,
        validated_edge_count=int(edge_summary.get("validated_edge_count", 0) or 0),
        paper_review_candidate_count=int(
            router_scoreboard.get("paper_review_candidate_count", 0) or 0
        ),
    )
    learning_backtest_projection = {
        "status": learning_backtest_gap.get("status") or "not_exported",
        "plain_english_answer": learning_backtest_gap.get("plain_english_answer"),
        "provider_rows_acquired": int(learning_backtest_gap.get("provider_rows_acquired") or 0),
        "sources_with_provider_history": int(
            learning_backtest_gap.get("sources_with_provider_history") or 0
        ),
        "sources_empirically_scored": int(
            learning_backtest_gap.get("sources_empirically_scored") or 0
        ),
        "sources_forward_only": int(learning_backtest_gap.get("sources_forward_only") or 0),
        "sources_terminally_unavailable": int(
            learning_backtest_gap.get("sources_terminally_unavailable") or 0
        ),
        "past_observations_re_evaluated": int(
            learning_backtest_gap.get("past_observations_re_evaluated") or 0
        ),
        "lessons_applied": int(learning_backtest_gap.get("lessons_applied") or 0),
        "validated_edges": int(learning_backtest_gap.get("validated_edges") or 0),
        "focus_providers": {
            provider: {
                "status": record.get("status"),
                "record_count": int(record.get("record_count") or 0),
            }
            for provider, record in (learning_backtest_gap.get("focus_providers") or {}).items()
            if isinstance(record, dict)
        },
        "historical_acquisition_complete_is_not_empirical_complete": (
            learning_backtest_gap.get("historical_acquisition_complete_is_not_empirical_complete")
            is True
        ),
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
    }
    communications["research_learning_update"] = learning_backtest_projection
    backtest_completion_projection = {
        "status": backtest_completion.get("status") or "not_exported",
        "completion_state": backtest_completion.get("completion_state") or "not_exported",
        "headline": backtest_completion.get("headline"),
        "plain_english_answer": backtest_completion.get("plain_english_answer"),
        "coverage": backtest_completion.get("coverage") or {},
        "research": backtest_completion.get("research") or {},
        "strategies": backtest_completion.get("strategies") or {},
        "next_actions": backtest_completion.get("next_actions") or [],
        "page_enrichment": backtest_completion.get("page_enrichment") or {},
        "material_learning_delta": {
            "status": material_learning_delta.get("status") or "not_exported",
            "material_change": material_learning_delta.get("material_change") is True,
            "five_part_answer": material_learning_delta.get("five_part_answer") or {},
            "notification_candidate_created": (
                material_learning_delta.get("notification_candidate_created") is True
            ),
        },
        "historical_tests_are_not_trades": True,
        "profitability_certified": False,
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "command_disabled": True,
        "live_capital_enabled": False,
    }
    communications["backtest_completion_update"] = backtest_completion_projection
    open_market_conversion_projection = {
        "schema_version": ef11_dashboard.get("schema_version"),
        "artifact_type": ef11_dashboard.get("artifact_type"),
        "generated_at": ef11_dashboard.get("generated_at"),
        "certification_state": ef11_dashboard.get("certification_state"),
        "structural_ready": ef11_dashboard.get("structural_ready") is True,
        "provider_conversion_ready": ef11_dashboard.get("provider_conversion_ready") is True,
        "empirically_conversion_proven": ef11_dashboard.get(
            "empirically_conversion_proven"
        )
        is True,
        "eligible_market_days_completed": int(
            ef11_dashboard.get("eligible_market_days_completed") or 0
        ),
        "eligible_market_day_target": int(
            ef11_dashboard.get("eligible_market_day_target") or 5
        ),
        "pre_staged_setup_count": int(ef11_dashboard.get("pre_staged_setup_count") or 0),
        "ready_setup_count": int(ef11_dashboard.get("ready_setup_count") or 0),
        "current_risk_tier": ef11_dashboard.get("current_risk_tier"),
        "maximum_current_paper_notional_usd": float(
            ef11_dashboard.get("maximum_current_paper_notional_usd") or 0
        ),
        "absolute_paper_notional_ceiling_usd": float(
            ef11_dashboard.get("absolute_paper_notional_ceiling_usd") or 5000
        ),
        "primary_blocker": ef11_dashboard.get("primary_blocker"),
        "blocker_owner": ef11_dashboard.get("blocker_owner"),
        "next_recheck_at": ef11_dashboard.get("next_recheck_at"),
        "market_clock_fresh": ef11_dashboard.get("market_clock_fresh") is True,
        "market_session_phase": ef11_dashboard.get("market_session_phase"),
        "latest_conversion_generation_id": ef11_dashboard.get(
            "latest_conversion_generation_id"
        ),
        "latest_handoff_count": int(ef11_dashboard.get("latest_handoff_count") or 0),
        "latest_paper_order_count": int(
            ef11_dashboard.get("latest_paper_order_count") or 0
        ),
        "summary": ef11_dashboard.get("summary"),
        "telegram_material_event": {
            "send_candidate": ef11_telegram_candidate.get("send_candidate") is True,
            "event_type": ef11_telegram_candidate.get("material_event_type"),
            "message": ef11_telegram_candidate.get("message"),
        },
        "certification_complete": ef11_certification.get("complete") is True,
        "collecting_real_market_time": ef11_certification.get("complete") is not True,
        "paper_only": True,
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    communications["open_market_conversion_update"] = {
        "send_candidate": ef11_telegram_candidate.get("send_candidate") is True,
        "material_event_type": ef11_telegram_candidate.get("material_event_type"),
        "message": ef11_telegram_candidate.get("message"),
        "dedupe_key": ef11_telegram_candidate.get("dedupe_key"),
        "review_only": True,
        "command_disabled": True,
        "live_capital_enabled": False,
    }
    qualitative_research_projection = {
        "status": qualitative_dashboard.get("status") or "not_exported",
        "generated_at": qualitative_dashboard.get("generated_at"),
        "headline": qualitative_dashboard.get("headline"),
        "official_document_count": int(
            qualitative_dashboard.get("official_document_count") or 0
        ),
        "research_eligible_document_count": int(
            qualitative_dashboard.get("research_eligible_document_count") or 0
        ),
        "grounded_claim_count": int(
            qualitative_dashboard.get("grounded_claim_count") or 0
        ),
        "pending_forward_window_count": int(
            qualitative_dashboard.get("pending_forward_window_count") or 0
        ),
        "mature_forward_label_count": int(
            qualitative_dashboard.get("mature_forward_label_count") or 0
        ),
        "qualified_pattern_count": int(
            qualitative_dashboard.get("qualified_pattern_count") or 0
        ),
        "prediction_contract_count": int(
            qualitative_dashboard.get("prediction_contract_count") or 0
        ),
        "prediction_disagreement_count": int(
            qualitative_dashboard.get("prediction_disagreement_count") or 0
        ),
        "liquidity_qualified_prediction_disagreement_count": int(
            qualitative_dashboard.get(
                "liquidity_qualified_prediction_disagreement_count"
            )
            or 0
        ),
        "lane_contribution_count": int(
            qualitative_dashboard.get("lane_contribution_count") or 0
        ),
        "a4_paper_review_nomination_count": int(
            qualitative_dashboard.get("a4_paper_review_nomination_count") or 0
        ),
        "current_router_disposition": qualitative_dashboard.get(
            "current_router_disposition"
        ),
        "what_changed": qualitative_dashboard.get("what_changed"),
        "why_not_tradeable_yet": qualitative_dashboard.get(
            "why_not_tradeable_yet"
        ),
        "next_action": qualitative_dashboard.get("next_action"),
        "state_legend": {
            "discovered": "A grounded relationship is worth investigating.",
            "verified": "The source, claim and availability time have been checked.",
            "tested": "Forward outcomes and declared controls have been evaluated.",
            "strategy_relevant": "The relationship can refine or form a strategy hypothesis.",
            "tradeable": "A separate current Akber, risk, Router and PaperOps review passed.",
        },
        "existing_dashboard_structure_preserved": True,
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "paper_only": True,
        "live_send_allowed": False,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    communications["qualitative_research_update"] = {
        "status": qualitative_communications.get("status") or "not_exported",
        "generated_at": qualitative_communications.get("generated_at"),
        "material_change": qualitative_communications.get("material_change") is True,
        "message_candidate": qualitative_communications.get("message_candidate"),
        "fingerprint": qualitative_communications.get("fingerprint"),
        "candidate_only": True,
        "review_only": True,
        "command_disabled": True,
        "live_send_allowed": False,
        "live_send_attempted": False,
        "live_capital_enabled": False,
    }
    runtime_state = (
        "research-only"
        if lock.get("status") == "active"
        else ("paper-operational" if release.get("release_effective") is True else "blocked")
    )
    backfill_progress = heartbeat.get("progress")
    backfill_progress = backfill_progress if isinstance(backfill_progress, dict) else {}
    system_overview = _system_overview_projection(
        generated_at=generated,
        runtime_state=runtime_state,
        source_summary=source_summary,
        backfill_progress=backfill_progress,
        heartbeat=heartbeat,
        findings=findings,
        edge_summary=edge_summary,
        quantum_review=quantum_review,
        router_scoreboard=router_scoreboard,
        router_why_not=router_why_not,
        release=release,
        lifecycle=lifecycle,
        learning=learning_compat,
        proof=proof,
        current_portfolio=current_portfolio,
        handoff_count=len(handoffs),
        operator_service=operator_service,
        operator_why_not=operator_why_not,
        operator_repair_queue=operator_repair_queue,
        operator_certification=operator_certification,
        permanent_reliability=permanent_reliability,
        freshness=freshness,
    )
    system_overview["experimental_paper_epoch"] = {
        "certification_status": experimental_certification.get("status"),
        "implementation_complete": experimental_certification.get("implementation_complete")
        is True,
        "operation_running": experimental_certification.get(
            "autonomous_experimental_paper_operation_running"
        )
        is True,
        "release_state": release.get("status"),
        "trial_state": experimental_trial.get("status"),
        "trial_day": int(experimental_trial.get("trial_day") or 0),
        "trial_days_remaining": int(experimental_trial.get("calendar_days_remaining") or 30),
        "soak_completed_real_sessions": int(
            experimental_soak.get("completed_real_session_count") or 0
        ),
        "soak_required_real_sessions": int(
            experimental_soak.get("required_real_session_count") or 7
        ),
        "unattended_reliability_certified": experimental_soak.get(
            "unattended_reliability_certified"
        )
        is True,
        "validated_edge_count": int(edge_summary.get("validated_edge_count") or 0),
        "live_capital_enabled": False,
    }
    views = {
        "system/team": {
            "operating_model": "Python COO, local LLM Research Analyst, frontier LLM Strategy Lead, and nonlinear/quantum Head of Quant",
            "self_model_basis": "cognition, latency, source freshness, evidence quality, and paper-only authority",
            "navigation_role": "pinned_orientation_context",
            "journey_stage": False,
        },
        "fund/portfolio": {
            "portfolio": dashboard_status.get("dashboard_portfolio", {}),
            "current_portfolio": current_portfolio,
            "freshness": freshness["status"],
            "backtest_context": backtest_completion_projection,
        },
        "fund/timeline": {
            "trading_history": trading_history,
            "origin_counts": lifecycle.get("origin_counts", {}),
            "backtest_context": backtest_completion_projection,
        },
        "observe/sources": {
            "source_network": source_network,
            "source_state": source_summary,
            "backtest_completion": backtest_completion_projection,
            "qualitative_research": qualitative_research_projection,
        },
        "observe/universe": {
            **trading_universe,
            "backtest_completion": backtest_completion_projection,
            "qualitative_research": qualitative_research_projection,
        },
        "patterns/findings": {
            **pattern_discovery,
            "historical_research_program": learning_backtest_projection,
            "backtest_completion": backtest_completion_projection,
            "qualitative_research": qualitative_research_projection,
        },
        "patterns/nonlinear": {
            **quantum_review,
            "backtest_completion": backtest_completion_projection,
            "qualitative_research": qualitative_research_projection,
        },
        "decide/strategies": {
            "strategy_universe": strategy_universe,
            "strategy_evidence": strategy_evidence,
            "historical_research_program": learning_backtest_projection,
            "backtest_completion": backtest_completion_projection,
            "qualitative_research": qualitative_research_projection,
        },
        "decide/decision": {
            "trade_intents": {
                "hypothesis_count": len(hypotheses),
                "foundry_state": foundry.get("status"),
                "hypotheses": hypotheses,
            },
            "router": router_compat,
            "paperops_gate": gate_compat,
            "akber_status": akber_dashboard.get("status"),
            "akber_stages": _akber_stages(akber_results),
            "historical_research_program": learning_backtest_projection,
            "backtest_completion": backtest_completion_projection,
            "open_market_conversion": open_market_conversion_projection,
            "qualitative_research": qualitative_research_projection,
        },
        "trade/orders": {
            "handoff_count": len(handoffs),
            "paper_order_created_count": 0,
            "trading_history": trading_history,
            "open_market_conversion": open_market_conversion_projection,
            "qualitative_research_lineage": {
                "a4_paper_review_nomination_count": qualitative_research_projection[
                    "a4_paper_review_nomination_count"
                ],
                "current_router_disposition": qualitative_research_projection[
                    "current_router_disposition"
                ],
                "read_only": True,
                "command_disabled": True,
            },
        },
        "learn/outcomes": {
            **learning_cycle,
            "historical_research_program": learning_backtest_projection,
            "backtest_completion": backtest_completion_projection,
            "qualitative_research": qualitative_research_projection,
        },
        "learn/improvements": {
            **improvement_pipeline,
            "stage1_learning_input": stage1_learning_input,
            "historical_research_program": learning_backtest_projection,
            "backtest_completion": backtest_completion_projection,
            "qualitative_research": qualitative_research_projection,
        },
        "system/overview": {
            **system_overview,
            "historical_research_program": learning_backtest_projection,
            "backtest_completion": backtest_completion_projection,
            "qualitative_research": qualitative_research_projection,
        },
    }
    for route, view in views.items():
        view["lifecycle_context"] = LIFECYCLE_ROUTE_CONTEXTS[route]
    compatibility = {
        "pattern_intelligence": pattern_compat,
        "trade_intents": {
            "status": foundry.get("status"),
            "intent_count": len(hypotheses),
            "rows": [
                {
                    "instrument": record.get("instrument_proxy_mapping", {}).get("execution_proxy"),
                    "strategy_family": record.get("strategy_mapping", {}).get("strategy_label"),
                    "thesis": record.get("entry_concept", {}).get("summary"),
                    "state": record.get("hypothesis_state"),
                    "reason": record.get("blocker_state", {}).get("state"),
                    "source_quorum": "required later",
                    "akber_filter": "not run"
                    if not akber_results
                    else akber_results[0].get("decision"),
                    "quantum_review": "research annotation only",
                    "next_allowed_action": "Akber review"
                    if record.get("akber_review_allowed")
                    else "shadow only",
                    "is_order": False,
                }
                for record in hypotheses
            ],
        },
        "router": router_compat,
        "paperops_gate": gate_compat,
        "paper_lifecycle_v2": lifecycle_compat,
        "learning_attribution_v2": learning_compat,
        "telegram_summary_v2": communications,
        "telegram_communications_mirror_v2": communications,
        "operator_service": operator_service,
        "operator_why_not_running": operator_why_not,
        "operator_ready_certification": operator_certification,
        "permanent_operator_reliability": permanent_reliability,
        "tradeability_compiler": tradeability_compiler,
        "autonomous_experimental_paper_epoch": {
            "status": experimental_certification.get("status"),
            "implementation_complete": experimental_certification.get("implementation_complete")
            is True,
            "autonomous_experimental_paper_operation_running": (
                experimental_certification.get("autonomous_experimental_paper_operation_running")
                is True
            ),
            "unattended_reliability_certified": experimental_certification.get(
                "unattended_reliability_certified"
            )
            is True,
            "operation_blocker_count": int(
                experimental_certification.get("operation_blocker_count") or 0
            ),
            "validated_edge_count": int(
                experimental_certification.get("validated_edge_count") or 0
            ),
            "protected_dashboard_ux_preserved": experimental_certification.get(
                "dashboard_ux_protection", {}
            ).get("protected_ux_preserved")
            is True,
            "paper_only": True,
            "live_capital_enabled": False,
        },
        "experimental_paper_trial": experimental_trial,
        "operator_soak_v3": experimental_soak,
        "learning_backtest_gap_closure": learning_backtest_projection,
        "backtest_completion": backtest_completion_projection,
        "open_market_conversion": open_market_conversion_projection,
        "qualitative_research": qualitative_research_projection,
    }
    view_model = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_dashboard_view_model",
        "phase_id": PHASE_ID,
        "generated_at": generated,
        "status": "operator_dashboard_ready_with_stale_labels"
        if freshness["status"] != "fresh"
        else "operator_dashboard_ready",
        "runtime_state": {
            "state": runtime_state,
            "plain_english": (
                "Qadam is gathering and testing evidence while PaperOps remains watch-only."
                if runtime_state == "research-only"
                else router_why_not.get("primary_reason")
            ),
            "source_state": source_summary,
            "backfill": {
                "status": backfill.get("status"),
                "completed_jobs": backfill_progress.get("completed_jobs", 0),
                "total_jobs": backfill_progress.get("total_jobs", 0),
                "remaining_jobs": backfill_progress.get("remaining_jobs", 0),
                "progress_fraction": backfill_progress.get("progress_fraction", 0.0),
                "throughput_units_per_second": heartbeat.get("throughput_units_per_second", 0.0),
                "last_heartbeat": heartbeat.get("generated_at"),
            },
            "why_not_trading_now": router_why_not.get("primary_reason"),
            "operator_service": {
                "status": operator_service.get("status") or "not_exported",
                "installed": operator_service.get("service_installed") is True,
                "running": operator_service.get("service_running") is True,
                "operational_ready": operator_service.get("operational_ready") is True,
                "why_not_running": operator_why_not.get("headline"),
            },
            "tradeability_compiler": {
                "operational_health": tradeability_compiler.get("operational_health")
                or "not_exported",
                "reachability": tradeability_compiler.get("tradeability_reachability")
                or "not_exercised",
                "current_setup_state": tradeability_compiler.get("current_setup_state")
                or "no_current_setup",
                "contract_defect_state": tradeability_compiler.get("contract_defect_state")
                or "unknown",
                "first_blocker": tradeability_compiler.get("first_blocker"),
                "next_action": tradeability_compiler.get("next_action"),
                "read_only": True,
            },
            "research_progression": {
                "status": research_progression.get("status") or "not_exported",
                "material_progress_detected": research_progression.get(
                    "material_progress_detected"
                ),
                "last_material_progress_at": research_progression.get(
                    "last_material_progress_at"
                ),
                "fresh_provider_backed_source_count": research_progression.get(
                    "source_truth", {}
                ).get("fresh_provider_backed_count", 0),
                "active_strategy_source_failure_count": research_progression.get(
                    "source_truth", {}
                ).get("active_strategy_source_failure_count", 0),
                "validated_edge_count": research_progression.get(
                    "validation_truth", {}
                ).get("validated_edge_count", 0),
                "exact_stop_reasons": research_progression.get(
                    "exact_stop_reasons", []
                ),
                "read_only": True,
            },
        },
        "navigation_contract": {
            "contract_version": "qadam_protected_decision_flow.v5",
            "default_route": DEFAULT_ROUTE,
            "refresh_interval_ms": STATUS_REFRESH_MS,
            "module_count": len(PROTECTED_NAVIGATION),
            "route_count": len(ROUTE_ORDER),
            "route_order": list(ROUTE_ORDER),
            "journey_route_order": list(JOURNEY_ROUTE_ORDER),
            "pinned_context": [
                {
                    "module_id": module_id,
                    "view_id": view_id,
                    "label": view_label,
                    "journey_stage": False,
                }
                for module_id, view_id, view_label in PINNED_CONTEXT_ROUTES
            ],
            "standalone_cross_cutting": [
                {
                    "module_id": module_id,
                    "view_id": view_id,
                    "label": label,
                    "description": description,
                    "journey_stage": False,
                }
                for module_id, view_id, label, description in STANDALONE_CROSS_CUTTING_ROUTES
            ],
            "modules": [
                {
                    "module_id": module_id,
                    "label": module_label,
                    "views": [
                        {"view_id": view_id, "label": view_label}
                        for view_id, view_label in module_views
                    ],
                }
                for module_id, module_label, module_views in PROTECTED_NAVIGATION
            ],
            "legacy_route_aliases": {
                "fund/holdings": "fund/portfolio",
                "decide/intents": "decide/decision",
                "trade/lifecycle": "trade/orders",
                "learn/replay": "learn/improvements",
                "learn/briefs": "learn/outcomes",
                "system/activity": "system/overview",
                "system/health": "system/overview",
            },
            "query_deep_link_contract": "/dashboard/?module=<module>&view=<view>",
            "desktop_sidebar_required": True,
            "mobile_section_control_required": True,
            "refresh_state_persistence_required": True,
            "previous_next_journey_required": False,
            "lifecycle_timeline_required": True,
            "lifecycle_stage_count": 10,
            "cross_cutting_routes_in_journey": False,
        },
        "views": views,
        "end_to_end_lifecycle": lifecycle_dashboard,
        "end_to_end_lifecycle_contract_ref": "data/runtime/qadam_end_to_end_lifecycle.json",
        "dashboard_route_stage_map_ref": "data/runtime/qadam_dashboard_route_stage_map.json",
        "compatibility_sections": compatibility,
        "freshness_ref": f"data/runtime/{FRESHNESS_ARTIFACT}",
        "truth_audit_ref": f"data/runtime/{TRUTH_AUDIT_ARTIFACT}",
        "communications_ref": f"data/runtime/{COMMUNICATIONS_ARTIFACT}",
        "learning_backtest_gap_closure": learning_backtest_projection,
        "backtest_completion": backtest_completion_projection,
        "open_market_conversion": open_market_conversion_projection,
        "qualitative_research": qualitative_research_projection,
        "research_progression": research_progression,
        "research_progression_ref": f"data/runtime/{RESEARCH_PROGRESSION_ARTIFACT}",
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "paper_only": True,
        "telegram_live_send_allowed": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    route_audit = _route_contract_audit()
    portfolio_audit = _portfolio_truth_audit(dashboard_status, portfolio_series, current_portfolio)
    pattern_keys = [record.get("pattern_id") for record in findings]
    truth = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_dashboard_truth_audit",
        "phase_id": PHASE_ID,
        "generated_at": generated,
        "status": "passed",
        "route_contract": route_audit,
        "portfolio_truth": portfolio_audit,
        "pattern_truth": {
            "displayed_finding_count": len(findings),
            "distinct_finding_count": len(set(pattern_keys)),
            "duplicate_finding_count": len(pattern_keys) - len(set(pattern_keys)),
            "raw_pattern_score_displayed_as_probability_count": sum(
                record.get("raw_pattern_score_is_probability") is not False for record in findings
            ),
            "validated_edge_count": edge_summary.get("validated_edge_count", 0),
        },
        "trade_origin_truth": lifecycle.get("origin_counts", {}),
        "authority_truth": {
            "dashboard_command_path_enabled": False,
            "telegram_command_path_enabled": False,
            "telegram_live_send_allowed": False,
            "paper_order_created_count": 0,
            "broker_write_count": 0,
            "proof_credit_allowed": False,
            "live_capital_enabled": False,
        },
        "anti_slop": {
            "upstream_status": anti_slop.get("status"),
            "duplicate_pattern_cards_rejected": True,
            "generic_placeholder_copy_rejected": True,
            "harsh_internal_language_translated": True,
            "stale_state_labeled": True,
        },
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "authority": authority_flags(),
    }
    return {
        "view_model": view_model,
        "freshness": freshness,
        "truth": truth,
        "communications": communications,
        "pattern_discovery": pattern_discovery,
        "quantum_review": quantum_review,
        "learning_cycle": learning_cycle,
        "improvement_pipeline": improvement_pipeline,
        "stage1_learning_input": stage1_learning_input,
        "lifecycle_contract": lifecycle_contract,
        "route_stage_map": route_stage_map,
        "lifecycle_dashboard": lifecycle_dashboard,
    }


def _forbidden_public_key(payload: Any) -> str | None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            normalized = str(key).lower()
            if normalized in FORBIDDEN_PUBLIC_KEYS or normalized.endswith("_secret"):
                return normalized
            found = _forbidden_public_key(value)
            if found:
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = _forbidden_public_key(value)
            if found:
                return found
    return None


def validate_operator_dashboard_state(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    view_model = state["view_model"]
    truth = state["truth"]
    communications = state["communications"]
    navigation = view_model.get("navigation_contract", {})
    if navigation.get("route_order") != list(ROUTE_ORDER):
        errors.append("operator_dashboard_route_order_changed")
    if navigation.get("journey_route_order") != list(JOURNEY_ROUTE_ORDER):
        errors.append("operator_dashboard_journey_route_order_changed")
    if navigation.get("default_route") != DEFAULT_ROUTE:
        errors.append("operator_dashboard_default_route_changed")
    module_labels = {
        module.get("module_id"): {
            view.get("view_id"): view.get("label")
            for view in module.get("views", [])
            if isinstance(view, dict)
        }
        for module in navigation.get("modules", [])
        if isinstance(module, dict)
    }
    expected_visible_labels = {
        "fund": {"portfolio": "Portfolio", "timeline": "Trading History"},
        "patterns": {
            "findings": "Pattern Recognition",
            "nonlinear": "Quantum Edge",
        },
    }
    for module_id, labels in expected_visible_labels.items():
        for view_id, expected_label in labels.items():
            if module_labels.get(module_id, {}).get(view_id) != expected_label:
                errors.append(f"operator_dashboard_visible_label_mismatch:{module_id}/{view_id}")
    if set(view_model.get("views", {})) != set(ROUTE_ORDER):
        errors.append("operator_dashboard_route_matrix_incomplete")
    if navigation.get("legacy_route_aliases", {}).get("system/activity") != "system/overview":
        errors.append("operator_dashboard_activity_alias_missing")
    if navigation.get("legacy_route_aliases", {}).get("system/health") != "system/overview":
        errors.append("operator_dashboard_health_alias_missing")
    if navigation.get("legacy_route_aliases", {}).get("learn/replay") != "learn/improvements":
        errors.append("operator_dashboard_replay_alias_missing")
    if navigation.get("legacy_route_aliases", {}).get("learn/briefs") != "learn/outcomes":
        errors.append("operator_dashboard_briefs_alias_missing")
    system_overview = view_model.get("views", {}).get("system/overview", {})
    if system_overview.get("diagnostic_contract_version") != "qadam_system_diagnostics.v2":
        errors.append("operator_dashboard_system_diagnostic_contract_missing")
    overall_health = system_overview.get("overall_health", {})
    if overall_health.get("state") not in {"healthy", "degraded"}:
        errors.append("operator_dashboard_system_health_state_invalid")
    if system_overview.get("operating_mode", {}).get("is_infrastructure_failure") is not False:
        errors.append("operator_dashboard_operating_mode_misclassified")
    infrastructure_domains = system_overview.get("infrastructure_domains")
    infrastructure_domains = (
        infrastructure_domains if isinstance(infrastructure_domains, list) else []
    )
    expected_domain_ids = {
        "host",
        "runtime",
        "data",
        "storage",
        "research",
        "paper_broker",
        "communications",
        "deployment",
    }
    if {
        str(domain.get("domain_id") or "") for domain in infrastructure_domains
    } != expected_domain_ids:
        errors.append("operator_dashboard_infrastructure_inventory_incomplete")
    monitoring_gap_count = sum(
        domain.get("tone") == "unmonitored" for domain in infrastructure_domains
    )
    if monitoring_gap_count != int(overall_health.get("monitoring_gap_count", 0) or 0):
        errors.append("operator_dashboard_monitoring_gap_count_mismatch")
    incidents = system_overview.get("root_cause_incidents", {})
    incident_rows = incidents.get("rows")
    incident_rows = incident_rows if isinstance(incident_rows, list) else []
    if int(incidents.get("total_count", 0) or 0) != len(incident_rows):
        errors.append("operator_dashboard_incident_count_mismatch")
    incident_ids = [str(row.get("incident_id") or "") for row in incident_rows]
    if len(incident_ids) != len(set(incident_ids)):
        errors.append("operator_dashboard_duplicate_root_incident")
    if any(
        "research lock" in f"{row.get('title', '')} {row.get('summary', '')}".lower()
        or "validated edge" in f"{row.get('title', '')} {row.get('summary', '')}".lower()
        for row in incident_rows
    ):
        errors.append("operator_dashboard_policy_state_reported_as_incident")
    services_and_jobs = system_overview.get("services_schedules_jobs", {})
    service_rows = services_and_jobs.get("services")
    service_rows = service_rows if isinstance(service_rows, list) else []
    if int(services_and_jobs.get("service_count", 0) or 0) != len(service_rows):
        errors.append("operator_dashboard_service_count_mismatch")
    if int(services_and_jobs.get("scheduled_count", 0) or 0) + int(
        services_and_jobs.get("policy_paused_count", 0) or 0
    ) != len(service_rows):
        errors.append("operator_dashboard_service_denominator_mismatch")
    if services_and_jobs.get("running_count_known") is False:
        if services_and_jobs.get("running_count") is not None:
            errors.append("operator_dashboard_unverified_running_count_exported")
    elif not int(services_and_jobs.get("scheduled_count", 0) or 0):
        errors.append("operator_dashboard_empty_schedule_reported_as_verified")
    elif int(services_and_jobs.get("running_count", 0) or 0) > int(
        services_and_jobs.get("scheduled_count", 0) or 0
    ):
        errors.append("operator_dashboard_running_count_exceeds_schedule")
    if any(
        service.get("diagnostic_state")
        not in {"running", "stopped", "paused_by_policy", "state_unverified"}
        for service in service_rows
    ):
        errors.append("operator_dashboard_service_diagnostic_state_invalid")
    if any(
        service.get("diagnostic_state") == "paused_by_policy" and service.get("tone") != "policy"
        for service in service_rows
    ):
        errors.append("operator_dashboard_policy_paused_service_tone_invalid")
    if {
        "operator_service_stopped",
        "operating_evidence_overdue",
    }.issubset(set(incident_ids)):
        errors.append("operator_dashboard_downstream_incident_not_deduplicated")
    deployment_domain = next(
        (domain for domain in infrastructure_domains if domain.get("domain_id") == "deployment"),
        {},
    )
    if (
        system_overview.get("operating_mode", {}).get("state") == "research-only"
        and deployment_domain.get("tone") == "degraded"
    ):
        errors.append("operator_dashboard_policy_hold_degraded_deployment")
    monitoring_coverage = system_overview.get("technical_diagnostics", {}).get(
        "monitoring_coverage", {}
    )
    if int(monitoring_coverage.get("unmonitored_domain_count", 0) or 0) != monitoring_gap_count:
        errors.append("operator_dashboard_technical_domain_gap_mismatch")
    monitoring_gaps = monitoring_coverage.get("gaps")
    monitoring_gaps = monitoring_gaps if isinstance(monitoring_gaps, list) else []
    if int(monitoring_coverage.get("monitoring_gap_count", 0) or 0) != len(monitoring_gaps):
        errors.append("operator_dashboard_technical_monitoring_gap_mismatch")
    operator_check_state = str(overall_health.get("operator_service_check_state") or "")
    if operator_check_state and operator_check_state != "fresh":
        if "operator_service_stopped" in incident_ids:
            errors.append("operator_dashboard_stale_operator_reported_as_current")
        if any(
            service.get("paperops_watch_only") is not True
            and service.get("diagnostic_state") != "state_unverified"
            for service in service_rows
        ):
            errors.append("operator_dashboard_stale_workflow_state_reported_as_current")
    route_audit = truth.get("route_contract", {})
    for field in (
        "protected_route_order_preserved",
        "team_pinned_before_fund",
        "system_standalone_sidebar_link",
        "legacy_system_aliases_present",
        "legacy_learning_aliases_present",
        "cross_cutting_routes_use_lifecycle_context",
        "default_route_preserved",
        "query_deep_link_contract_present",
        "desktop_sidebar_present",
        "mobile_section_control_present",
        "refresh_interval_preserved",
        "refresh_navigation_state_preserved",
        "lifecycle_component_present",
        "legacy_journey_navigation_removed",
    ):
        if route_audit.get(field) is not True:
            errors.append(f"operator_dashboard_navigation_check_failed:{field}")
    portfolio = truth.get("portfolio_truth", {})
    if portfolio.get("all_portfolio_values_agree") is not True:
        errors.append("operator_dashboard_portfolio_value_mismatch")
    if portfolio.get("position_count_agrees") is not True:
        errors.append("operator_dashboard_position_count_mismatch")
    pattern_truth = truth.get("pattern_truth", {})
    if pattern_truth.get("duplicate_finding_count") != 0:
        errors.append("operator_dashboard_duplicate_pattern_findings")
    if pattern_truth.get("raw_pattern_score_displayed_as_probability_count") != 0:
        errors.append("operator_dashboard_raw_score_shown_as_probability")
    research_program = view_model.get("learning_backtest_gap_closure", {})
    if research_program.get("status") != "research_gap_closure_visible":
        errors.append("operator_dashboard_learning_backtest_visibility_missing")
    if (
        research_program.get("historical_acquisition_complete_is_not_empirical_complete")
        is not True
    ):
        errors.append("operator_dashboard_acquisition_empirical_boundary_missing")
    if int(research_program.get("sources_with_provider_history") or 0) < int(
        research_program.get("sources_empirically_scored") or 0
    ):
        errors.append("operator_dashboard_empirical_coverage_exceeds_provider_history")
    if int(research_program.get("lessons_applied") or 0) != 0:
        errors.append("operator_dashboard_unreviewed_learning_reported_applied")
    if communications.get("research_learning_update") != research_program:
        errors.append("operator_dashboard_communications_learning_mirror_mismatch")
    completion = view_model.get("backtest_completion", {})
    if completion.get("status") != "public_safe_current":
        errors.append("operator_dashboard_backtest_completion_visibility_missing")
    if int(completion.get("coverage", {}).get("source_count") or 0) != 41:
        errors.append("operator_dashboard_backtest_source_denominator_mismatch")
    if int(completion.get("coverage", {}).get("instrument_count") or 0) != 19:
        errors.append("operator_dashboard_backtest_instrument_denominator_mismatch")
    if completion.get("historical_tests_are_not_trades") is not True:
        errors.append("operator_dashboard_backtest_trade_boundary_missing")
    if completion.get("profitability_certified") is not False:
        errors.append("operator_dashboard_backtest_profitability_overclaim")
    if communications.get("backtest_completion_update") != completion:
        errors.append("operator_dashboard_communications_backtest_mirror_mismatch")
    qualitative = view_model.get("qualitative_research", {})
    if qualitative.get("status") != "research_operational":
        errors.append("operator_dashboard_qualitative_research_visibility_missing")
    for field in (
        "existing_dashboard_structure_preserved",
        "public_safe",
        "read_only",
        "command_disabled",
        "paper_only",
    ):
        if qualitative.get(field) is not True:
            errors.append(f"operator_dashboard_qualitative_boundary_missing:{field}")
    if qualitative.get("live_send_allowed") is not False:
        errors.append("operator_dashboard_qualitative_live_send_enabled")
    if qualitative.get("live_capital_enabled") is not False:
        errors.append("operator_dashboard_qualitative_live_capital_enabled")
    if set(qualitative.get("state_legend") or {}) != {
        "discovered",
        "verified",
        "tested",
        "strategy_relevant",
        "tradeable",
    }:
        errors.append("operator_dashboard_qualitative_state_legend_incomplete")
    qualitative_message = communications.get("qualitative_research_update", {})
    if qualitative_message.get("candidate_only") is not True:
        errors.append("operator_dashboard_qualitative_message_not_candidate_only")
    if qualitative_message.get("command_disabled") is not True:
        errors.append("operator_dashboard_qualitative_message_command_enabled")
    if qualitative_message.get("live_send_allowed") is not False:
        errors.append("operator_dashboard_qualitative_message_live_send_enabled")
    if qualitative_message.get("live_send_attempted") is not False:
        errors.append("operator_dashboard_qualitative_message_send_attempted")
    errors.extend(
        validate_pattern_dashboard_views(
            {
                "pattern_discovery": state.get("pattern_discovery", {}),
                "quantum_review": state.get("quantum_review", {}),
            }
        )
    )
    errors.extend(validate_learning_cycle_view_model(state.get("learning_cycle", {})))
    errors.extend(validate_improvement_pipeline_view_model(state.get("improvement_pipeline", {})))
    errors.extend(validate_stage1_learning_input(state.get("stage1_learning_input", {})))
    errors.extend(validate_lifecycle_contract(state.get("lifecycle_contract", {})))
    errors.extend(validate_lifecycle_summary(state.get("lifecycle_dashboard", {})))
    for route, view in view_model.get("views", {}).items():
        if view.get("lifecycle_context") != LIFECYCLE_ROUTE_CONTEXTS.get(route):
            errors.append(f"operator_dashboard_lifecycle_context_mismatch:{route}")
    if state["freshness"].get("stale_or_missing_labeled_count") != (
        state["freshness"].get("stale_count", 0) + state["freshness"].get("missing_count", 0)
    ):
        errors.append("operator_dashboard_stale_label_count_mismatch")
    for message in communications.get("latest_messages", []):
        if len(str(message.get("body") or "")) > 220:
            errors.append("operator_telegram_message_too_long")
        if message.get("notify_only") is not True:
            errors.append("operator_telegram_message_not_notify_only")
        if message.get("quality_passed") is not True:
            errors.append("operator_telegram_message_quality_failed")
        if message.get("human_style", {}).get("status") != "human":
            errors.append("operator_telegram_message_not_human_readable")
    duplicate_count = int(communications.get("message_rejected_duplicate_count", 0) or 0)
    ready_count = int(communications.get("message_ready_count", 0) or 0)
    if duplicate_count and ready_count:
        errors.append("operator_telegram_duplicate_marked_ready")
    for field in (
        "telegram_live_send_allowed",
        "telegram_command_path_enabled",
        "proof_credit_allowed",
    ):
        if communications.get(field) is not False:
            errors.append(f"operator_communications_unsafe:{field}")
    if communications.get("broker_write_count") != 0:
        errors.append("operator_communications_broker_write_nonzero")
    forbidden = _forbidden_public_key(state)
    if forbidden:
        errors.append(f"operator_dashboard_forbidden_public_key:{forbidden}")
    for payload, prefix in (
        (view_model, "operator_dashboard"),
        (state["freshness"], "operator_dashboard_freshness"),
        (truth, "operator_dashboard_truth"),
        (communications, "operator_communications"),
    ):
        if payload.get("public_safe") is not True:
            errors.append(f"{prefix}_not_public_safe")
        if payload.get("read_only") is not True:
            errors.append(f"{prefix}_not_read_only")
        if payload.get("command_disabled") is not True:
            errors.append(f"{prefix}_command_not_disabled")
        errors.extend(validate_authority(payload.get("authority", {}), prefix=prefix))
    return unique_errors(errors)


def build_and_write_operator_dashboard(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    state = build_operator_dashboard_state(settings)
    store.write_json(VIEW_MODEL_ARTIFACT, state["view_model"])
    store.write_json(FRESHNESS_ARTIFACT, state["freshness"])
    store.write_json(TRUTH_AUDIT_ARTIFACT, state["truth"])
    store.write_json(COMMUNICATIONS_ARTIFACT, state["communications"])
    store.write_json(PATTERN_DISCOVERY_ARTIFACT, state["pattern_discovery"])
    store.write_json(QUANTUM_REVIEW_ARTIFACT, state["quantum_review"])
    store.write_json(LEARNING_CYCLE_ARTIFACT, state["learning_cycle"])
    store.write_jsonl(LEARNING_CYCLE_EVENTS_ARTIFACT, state["learning_cycle"]["events"])
    store.write_json(IMPROVEMENT_PIPELINE_ARTIFACT, state["improvement_pipeline"])
    store.write_jsonl(IMPROVEMENT_PROPOSALS_ARTIFACT, state["improvement_pipeline"]["proposals"])
    if not store.path(APPLIED_VERSIONS_ARTIFACT).exists():
        store.write_jsonl(APPLIED_VERSIONS_ARTIFACT, [])
    store.write_json(STAGE1_INPUT_ARTIFACT, state["stage1_learning_input"])
    store.write_jsonl(STAGE1_HANDOFFS_ARTIFACT, state["stage1_learning_input"]["handoffs"])
    write_lifecycle_artifacts(
        state["lifecycle_contract"],
        state["route_stage_map"],
        state["lifecycle_dashboard"],
        settings,
    )
    errors = validate_operator_dashboard_state(state)
    lifecycle_checks = {
        "schema_version": state["lifecycle_contract"]["schema_version"],
        "artifact_type": "qadam_end_to_end_lifecycle_checks",
        "generated_at": state["view_model"]["generated_at"],
        "status": "passed"
        if not [
            *validate_lifecycle_contract(state["lifecycle_contract"]),
            *validate_lifecycle_summary(state["lifecycle_dashboard"]),
        ]
        else "blocked",
        "stage_count": state["lifecycle_contract"]["stage_count"],
        "route_count": state["lifecycle_contract"]["route_count"],
        "single_global_current_stage": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "validation_errors": unique_errors(
            [
                *validate_lifecycle_contract(state["lifecycle_contract"]),
                *validate_lifecycle_summary(state["lifecycle_dashboard"]),
            ]
        ),
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "paper_only": True,
        "authority": authority_flags(),
    }
    lifecycle_checks["validation_error_count"] = len(lifecycle_checks["validation_errors"])
    store.write_json(LIFECYCLE_CHECK_ARTIFACT, lifecycle_checks)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_dashboard_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "implementation_ready": not errors,
        "runtime_state": state["view_model"]["runtime_state"]["state"],
        "protected_route_count": len(ROUTE_ORDER),
        "portfolio_values_agree": state["truth"]["portfolio_truth"]["all_portfolio_values_agree"],
        "stale_count": state["freshness"]["stale_count"],
        "missing_count": state["freshness"]["missing_count"],
        "displayed_pattern_count": state["truth"]["pattern_truth"]["displayed_finding_count"],
        "duplicate_pattern_count": state["truth"]["pattern_truth"]["duplicate_finding_count"],
        "raw_score_probability_violation_count": state["truth"]["pattern_truth"][
            "raw_pattern_score_displayed_as_probability_count"
        ],
        "telegram_message_ready_count": state["communications"]["message_ready_count"],
        "learning_attribution_record_count": state["learning_cycle"]["counts"][
            "attribution_record_count"
        ],
        "learning_reference_record_count": state["learning_cycle"]["counts"][
            "mirror_reference_count"
        ],
        "improvement_candidate_count": state["improvement_pipeline"]["counts"][
            "active_candidate_count"
        ],
        "improvement_ready_count": state["improvement_pipeline"]["counts"][
            "ready_for_review_count"
        ],
        "stage1_applied_learning_version_count": state["stage1_learning_input"][
            "applied_handoff_count"
        ],
        "telegram_live_send_allowed": False,
        "command_path_enabled": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store.write_json(CHECK_ARTIFACT, checks)
    return state, checks, errors
