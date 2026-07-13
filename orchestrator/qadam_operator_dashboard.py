"""OR-17 public-safe operator dashboard and communications projection.

The projection enriches the existing protected route matrix with V3 evidence.
It is read-only and cannot create commands, approvals, orders, broker writes,
Telegram sends, policy mutations, or proof credit.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import os
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
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    authority_flags,
    file_sha256,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_json,
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
OPERATOR_CERTIFICATION_ARTIFACT = "qadam_operator_ready_edge_engine_certification.json"
LOCK_ARTIFACT = "qadam_long_backtest_lock.json"
ANTI_SLOP_ARTIFACT = "qsase_dashboard_anti_slop_audit.json"
TELEGRAM_DEDUPE_ARTIFACT = "qadam_telegram_next_generation_dedupe_ledger.jsonl"

PINNED_CONTEXT_ROUTES = (
    ("system", "team", "Qadam Team"),
)

STANDALONE_CROSS_CUTTING_ROUTES = (
    ("system", "overview", "System", "Full operating picture"),
)

PROTECTED_NAVIGATION = (
    (
        "fund",
        "Fund",
        (("portfolio", "Portfolio"), ("timeline", "Timeline")),
    ),
    ("observe", "Observe", (("sources", "Data Sources"), ("universe", "Trading Universe"))),
    (
        "patterns",
        "Find Patterns",
        (("findings", "Pattern Discovery"), ("nonlinear", "Quantum Review")),
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
    f"{module_id}/{view_id}"
    for module_id, view_id, _view_label in PINNED_CONTEXT_ROUTES
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
    SHADOW_STATE_ARTIFACT: 5 * 60,
    ROUTER_SCOREBOARD_ARTIFACT: 5 * 60,
    LIFECYCLE_ARTIFACT: 15 * 60,
    SUPERVISOR_HEARTBEAT_ARTIFACT: 5 * 60,
    OPERATOR_SERVICE_ARTIFACT: 5 * 60,
    OPERATOR_CERTIFICATION_ARTIFACT: 5 * 60,
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


def build_freshness_audit(
    settings: Settings | None = None, *, generated_at: str
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    reference = parse_timestamp(generated_at) or datetime.now(timezone.utc)
    records = [
        _freshness_record(runtime, filename, threshold, reference)
        for filename, threshold in FRESHNESS_SPECS.items()
    ]
    counts = Counter(record["freshness_state"] for record in records)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_dashboard_freshness",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "fresh" if not counts.get("stale") and not counts.get("missing") else "stale_labels_required",
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
        str(record.get("source_key")): record
        for record in reliability
        if record.get("source_key")
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
        str(record.get("instrument")): record
        for record in edges
        if record.get("instrument")
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
        key=lambda record: (-safe_float(record.get("raw_pattern_score")), str(record.get("instrument"))),
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
        fresh_count = sum(record.get("fresh") is True for record in inputs if isinstance(record, dict))
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
        stage_key = "validated" if validated else (
            "documented" if score.get("confidence_state") == "score_ready_for_tape" else "found"
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
        findings.append(
            {
                "pattern_id": score.get("score_id"),
                "rank": rank,
                "rank_badges": [f"priority {rank}", stage_key],
                "title": f"{instrument} evidence pattern",
                "stage_key": stage_key,
                "stage_label": stage_key.replace("_", " "),
                "confidence_label": f"raw pattern score {score_value:.3f}; not a probability",
                "tradeability_state": "research_only" if not validated else "validated_edge_research_only",
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
                    "contribution": "not_useful_yet"
                    if quantum.get("quantum_usefulness_score") is None
                    else "incremental",
                    "plain_english_result": (
                        "Nonlinear and quantum incremental value is not measurable without holdout outcomes."
                        if quantum.get("quantum_usefulness_score") is None
                        else "Nonlinear review added measured holdout value; it remains non-authoritative."
                    ),
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
        "status": "research_only_no_validated_edge" if edge_count == 0 else "validated_edges_visible",
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
    return {
        "status": lifecycle.get("status") or "not_recorded",
        "paper_order_mirror_count": lifecycle.get("order_record_count", 0),
        "open_position_mirror_count": lifecycle.get("position_record_count", 0),
        "closed_paper_trade_count": lifecycle.get("closed_trade_record_count", 0),
        "state_counts": {
            **states,
            "closed_postmortem_due": max(
                0,
                int(states.get("closed", 0) or 0)
                - int(states.get("postmortem_complete", 0) or 0),
            ),
        },
        "origin_counts": lifecycle.get("origin_counts", {}),
        "proof_eligible_count": proof.get("proof_eligible_count", 0),
        "mirror_only_historical_record_count": proof.get(
            "mirror_only_historical_record_count", 0
        ),
    }


def _learning_compatibility(
    records: list[dict[str, Any]], proof: dict[str, Any]
) -> dict[str, Any]:
    outcome_counts = Counter(str(record.get("outcome_type") or "unknown") for record in records)
    champion_counts = Counter(
        str(record.get("champion_challenger", {}).get("state") or "unknown")
        for record in records
    )
    proposal_count = sum(
        record.get("champion_challenger", {}).get("proposal_only") is True
        for record in records
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
                "tone": "degraded" if group in {"canonical_truth", "operator_experience"} else "pending",
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
    operator_certification: dict[str, Any],
    freshness: dict[str, Any],
) -> dict[str, Any]:
    source_count = int(source_summary.get("source_count", 0) or 0)
    fresh_source_count = int(source_summary.get("fresh_count", 0) or 0)
    completed_jobs = int(backfill_progress.get("completed_jobs", 0) or 0)
    total_jobs = int(backfill_progress.get("total_jobs", 0) or 0)
    validated_edges = int(edge_summary.get("validated_edge_count", 0) or 0)
    decision_count = int(router_scoreboard.get("decision_count", 0) or 0)
    paper_review_count = int(
        router_scoreboard.get("paper_review_candidate_count", 0) or 0
    )
    empirical_quantum_count = int(
        quantum_review.get("empirical_comparison_count", 0) or 0
    )
    quantum_review_count = len(quantum_review.get("reviews") or [])
    position_count = int(current_portfolio.get("position_count", 0) or 0)
    attribution_count = int(learning.get("attribution_record_count", 0) or 0)
    proof_count = int(proof.get("proof_eligible_count", 0) or 0)
    services = operator_service.get("services")
    services = services if isinstance(services, list) else []
    running_services = [row for row in services if row.get("service_process_running") is True]
    service_labels = {
        "source_ingestion": "Source ingestion",
        "market_price_refresh": "Market price refresh",
        "pattern_scoring": "Pattern scoring",
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
            "tone": "online" if row.get("service_process_running") is True else (
                "pending" if row.get("paperops_watch_only") is True else "degraded"
            ),
            "process_running": row.get("service_process_running") is True,
            "paperops_watch_only": row.get("paperops_watch_only") is True,
            "purpose": row.get("purpose"),
            "trigger": row.get("trigger"),
            "cadence_seconds": int(row.get("cadence_seconds", 0) or 0),
            "generated_at": row.get("generated_at"),
        }
        for row in services
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

    freshness_records = freshness.get("records")
    freshness_records = freshness_records if isinstance(freshness_records, list) else []
    freshness_by_name = {
        Path(str(record.get("artifact") or "")).name: record
        for record in freshness_records
    }

    def updated_at(filename: str, fallback: Any = None) -> Any:
        return freshness_by_name.get(filename, {}).get("generated_at") or fallback

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
            "tone": "online" if operator_service.get("service_running") is True else "degraded",
            "status": "Running" if operator_service.get("service_running") is True else "Not running",
            "metric": f"{len(running_services)}/{len(services)} services running",
            "issue": operator_why_not.get("headline") or "No runtime issue was exported.",
            "next_action": "Install, start, and observe the operator service across real sessions." if not running_services else "Continue monitoring liveness and repair state.",
            "route": _system_route("system", "overview"),
        },
        {
            "domain_id": "data",
            "label": "Data & freshness",
            "tone": "online" if not stale_count and not missing_count else "degraded",
            "status": "Current" if not stale_count and not missing_count else "Needs refresh",
            "metric": f"{fresh_artifact_count}/{artifact_count} artifacts current",
            "issue": f"{stale_count} stale and {missing_count} missing monitored artifacts." if stale_count or missing_count else "All monitored artifacts are current.",
            "next_action": "Refresh stale projections and resolve source acquisition gaps." if stale_count or missing_count else "Maintain the current refresh cadence.",
            "route": _system_route("observe", "sources"),
        },
        {
            "domain_id": "research",
            "label": "Research & edge",
            "tone": "online" if validated_edges else "pending",
            "status": "Validated" if validated_edges else "Evidence maturing",
            "metric": f"{len(findings)} relationships · {validated_edges} validated edges",
            "issue": certification_reason("evidence_and_edge", "No validated out-of-sample edge exists yet."),
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
            "next_action": "Keep the guarded route watch-only until every release condition passes." if release.get("release_effective") is not True else "Monitor clean handoffs through the guarded paper route.",
            "route": _system_route("decide", "decision"),
        },
        {
            "domain_id": "learning",
            "label": "Learning & persistence",
            "tone": "online" if attribution_count else "pending",
            "status": "Recording outcomes" if attribution_count else "Waiting for outcomes",
            "metric": f"{attribution_count} attributed · {proof_count} proof eligible",
            "issue": "No Qadam-origin paper outcome is proof eligible yet." if not proof_count else "Proof-eligible outcomes are available for review.",
            "next_action": "Continue real paper outcomes and postmortems without backfilling elapsed time." if not proof_count else "Review attribution before proposing any change.",
            "route": _system_route("learn", "outcomes"),
        },
    ]
    certification_groups = operator_certification.get("groups")
    certification_groups = (
        certification_groups if isinstance(certification_groups, dict) else {}
    )
    return {
        "artifact_type": "qadam_system_overview",
        "generated_at": generated_at,
        "status": "needs_attention" if stale_count or not running_services else "operational",
        "current_state": {
            "state": runtime_state,
            "tone": "pending" if runtime_state == "research-only" else (
                "online" if runtime_state == "paper-operational" else "degraded"
            ),
            "headline": system_headline,
            "why_not_trading_now": why_not_trading,
            "metrics": [
                {"label": "System mode", "value": runtime_state.replace("-", " ")},
                {"label": "Operator", "value": "running" if running_services else "not running"},
                {"label": "Sources", "value": f"{fresh_source_count}/{source_count} fresh"},
                {"label": "Historical evidence", "value": f"{completed_jobs}/{total_jobs} jobs"},
                {"label": "Validated edges", "value": validated_edges},
                {"label": "Paper operations", "value": paperops_state},
            ],
        },
        "flow": flow,
        "running_now": {
            "status": "running" if running_services else "not_running",
            "headline": f"{len(running_services)} of {len(services)} services are currently running." if services else "No service inventory was exported.",
            "running_count": len(running_services),
            "service_count": len(services),
            "updated_at": operator_service.get("generated_at"),
            "services": service_rows,
        },
        "health_domains": health_domains,
        "needs_attention": _system_needs_attention(
            operator_why_not, operator_certification
        ),
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
                        "generated_at": record.get("generated_at"),
                        "age_seconds": record.get("age_seconds"),
                        "freshness_state": record.get("freshness_state"),
                    }
                    for record in freshness_records
                ],
            },
            "operator_service": {
                "status": operator_service.get("status"),
                "installed": operator_service.get("service_installed") is True,
                "running": operator_service.get("service_running") is True,
                "operational_ready": operator_service.get("operational_ready") is True,
                "repair_queue": operator_service.get("repair_queue") or {},
            },
            "supervisor": {
                "status": heartbeat.get("status"),
                "generated_at": heartbeat.get("generated_at"),
                "progress": backfill_progress,
            },
            "certification": {
                "status": operator_certification.get("status"),
                "state": operator_certification.get("certification_state"),
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
            "release": {
                "status": release.get("status"),
                "release_recommended": release.get("release_recommended") is True,
                "release_effective": release.get("release_effective") is True,
                "blocker_count": len(release.get("blockers") or []),
            },
        },
        "boundary": "System Overview is public-safe and read-only. It cannot create commands, approve trades, submit orders, write to brokers, grant proof credit, or enable live capital.",
    }


def _communication_mirror(
    why_not: dict[str, Any], dedupe: list[dict[str, Any]], generated_at: str
) -> dict[str, Any]:
    body = (
        "Qadam is research-only. No validated edge exists yet, so PaperOps remains watch-only."
        if why_not.get("status") != "paper_review_candidate_available"
        else "Qadam has a paper-review candidate. It still enters only through guarded PaperOps checks."
    )
    digest = sha256_json({"message_class": "operator_status", "body": body})
    prior_hashes = {
        str(record.get("message_hash") or record.get("dedupe_hash") or "")
        for record in dedupe
    }
    duplicate = digest in prior_hashes
    message = {
        "message_id": stable_id("operator-telegram-note", digest),
        "message_class": "operator_status",
        "status": "message_rejected_duplicate" if duplicate else "message_ready_for_review",
        "body": body,
        "character_count": len(body),
        "message_hash": digest,
        "deduplicated": duplicate,
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
        "message_ready_count": 0 if duplicate else 1,
        "message_rejected_duplicate_count": 1 if duplicate else 0,
        "message_rejected_quality_count": 0,
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
    configured_site_root = os.getenv("QADAM_DASHBOARD_SITE_ROOT", "").strip()
    site_root = Path(configured_site_root) if configured_site_root else ROOT / "landing-page-repo"
    path = site_root / "dashboard.js"
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
            and "QSASE_DASHBOARD_NAVIGATION.filter((module) => !module.crossCutting)"
            in text
        ),
        "legacy_system_aliases_present": (
            'candidate === "system/activity"' in text
            and 'candidate === "system/health"' in text
        ),
        "legacy_learning_aliases_present": (
            'candidate === "learn/replay"' in text
            and 'candidate === "learn/briefs"' in text
        ),
        "cross_cutting_routes_use_lifecycle_context": (
            "data-lifecycle-relationship" in text
            and "is-cross-cutting" in text
        ),
        "default_route_preserved": (
            'const QSASE_DEFAULT_ROUTE = { moduleId: "fund", viewId: "portfolio" };'
            in text
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
        "portfolio_series_summary": series.get("current_value_gbp")
        or series.get("latest_value"),
        "portfolio_chart_latest": latest.get("portfolio_value")
        or latest.get("equity_gbp"),
        "current_portfolio_contract": current.get("portfolio_consistency", {}).get(
            "current_value"
        ),
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
    edges = read_jsonl(runtime / EDGE_REGISTRY_ARTIFACT)
    edge_summary = read_json(runtime / EDGE_SUMMARY_ARTIFACT)
    quantum = read_json(runtime / QUANTUM_SUMMARY_ARTIFACT)
    hypotheses = read_jsonl(runtime / HYPOTHESES_ARTIFACT)
    foundry = read_json(runtime / FOUNDRY_ARTIFACT)
    akber_results = read_jsonl(runtime / AKBER_RESULTS_ARTIFACT)
    akber_dashboard = read_json(runtime / AKBER_DASHBOARD_ARTIFACT)
    shadow_state = read_json(runtime / SHADOW_STATE_ARTIFACT)
    shadow_promotion = read_json(runtime / SHADOW_PROMOTION_ARTIFACT)
    router_scoreboard = read_json(runtime / ROUTER_SCOREBOARD_ARTIFACT)
    router_why_not = read_json(runtime / ROUTER_WHY_NOT_ARTIFACT)
    handoffs = read_jsonl(runtime / HANDOFF_ARTIFACT)
    release = read_json(runtime / RELEASE_ARTIFACT)
    lifecycle = read_json(runtime / LIFECYCLE_ARTIFACT)
    lineage = read_jsonl(runtime / LINEAGE_ARTIFACT)
    postmortems = read_jsonl(runtime / POSTMORTEMS_ARTIFACT)
    proof = read_json(runtime / PROOF_ARTIFACT)
    learning = read_jsonl(runtime / ATTRIBUTION_ARTIFACT)
    performance = read_json(runtime / PERFORMANCE_ARTIFACT)
    backfill = read_json(runtime / BACKFILL_ARTIFACT)
    supervisor = read_json(runtime / SUPERVISOR_STATUS_ARTIFACT)
    heartbeat = read_json(runtime / SUPERVISOR_HEARTBEAT_ARTIFACT)
    operator_service = read_json(runtime / OPERATOR_SERVICE_ARTIFACT)
    operator_why_not = read_json(runtime / OPERATOR_WHY_NOT_RUNNING_ARTIFACT)
    operator_certification = read_json(runtime / OPERATOR_CERTIFICATION_ARTIFACT)
    lock = read_json(runtime / LOCK_ARTIFACT)
    anti_slop = read_json(runtime / ANTI_SLOP_ARTIFACT)
    dedupe = read_jsonl(runtime / TELEGRAM_DEDUPE_ARTIFACT, limit=500)
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
                heartbeat.get("progress")
                if isinstance(heartbeat.get("progress"), dict)
                else {}
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
    gate_compat = _paperops_gate_compatibility(
        router_scoreboard, release, len(handoffs)
    )
    lifecycle_compat = _lifecycle_compatibility(lifecycle, proof)
    learning_compat = _learning_compatibility(learning, proof)
    communications = _communication_mirror(router_why_not, dedupe, generated)
    runtime_state = "research-only" if lock.get("status") == "active" else (
        "paper-operational" if release.get("release_effective") is True else "blocked"
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
        operator_certification=operator_certification,
        freshness=freshness,
    )
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
        },
        "fund/timeline": {
            "trading_history": trading_history,
            "origin_counts": lifecycle.get("origin_counts", {}),
        },
        "observe/sources": {"source_network": source_network, "source_state": source_summary},
        "observe/universe": trading_universe,
        "patterns/findings": pattern_discovery,
        "patterns/nonlinear": quantum_review,
        "decide/strategies": {
            "strategy_universe": strategy_universe,
            "strategy_evidence": strategy_evidence,
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
        },
        "trade/orders": {
            "handoff_count": len(handoffs),
            "paper_order_created_count": 0,
            "trading_history": trading_history,
        },
        "learn/outcomes": learning_cycle,
        "learn/improvements": {
            **improvement_pipeline,
            "stage1_learning_input": stage1_learning_input,
        },
        "system/overview": system_overview,
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
                    "instrument": record.get("instrument_proxy_mapping", {}).get(
                        "execution_proxy"
                    ),
                    "strategy_family": record.get("strategy_mapping", {}).get(
                        "strategy_label"
                    ),
                    "thesis": record.get("entry_concept", {}).get("summary"),
                    "state": record.get("hypothesis_state"),
                    "reason": record.get("blocker_state", {}).get("state"),
                    "source_quorum": "required later",
                    "akber_filter": "not run" if not akber_results else akber_results[0].get("decision"),
                    "quantum_review": "research annotation only",
                    "next_allowed_action": "Akber review" if record.get("akber_review_allowed") else "shadow only",
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
                "throughput_units_per_second": heartbeat.get(
                    "throughput_units_per_second", 0.0
                ),
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
    portfolio_audit = _portfolio_truth_audit(
        dashboard_status, portfolio_series, current_portfolio
    )
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
                record.get("raw_pattern_score_is_probability") is not False
                for record in findings
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
        state["freshness"].get("stale_count", 0)
        + state["freshness"].get("missing_count", 0)
    ):
        errors.append("operator_dashboard_stale_label_count_mismatch")
    for message in communications.get("latest_messages", []):
        if len(str(message.get("body") or "")) > 220:
            errors.append("operator_telegram_message_too_long")
        if message.get("notify_only") is not True:
            errors.append("operator_telegram_message_not_notify_only")
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
        "status": "passed" if not [
            *validate_lifecycle_contract(state["lifecycle_contract"]),
            *validate_lifecycle_summary(state["lifecycle_dashboard"]),
        ] else "blocked",
        "stage_count": state["lifecycle_contract"]["stage_count"],
        "route_count": state["lifecycle_contract"]["route_count"],
        "single_global_current_stage": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "validation_errors": unique_errors([
            *validate_lifecycle_contract(state["lifecycle_contract"]),
            *validate_lifecycle_summary(state["lifecycle_dashboard"]),
        ]),
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
        "portfolio_values_agree": state["truth"]["portfolio_truth"][
            "all_portfolio_values_agree"
        ],
        "stale_count": state["freshness"]["stale_count"],
        "missing_count": state["freshness"]["missing_count"],
        "displayed_pattern_count": state["truth"]["pattern_truth"][
            "displayed_finding_count"
        ],
        "duplicate_pattern_count": state["truth"]["pattern_truth"][
            "duplicate_finding_count"
        ],
        "raw_score_probability_violation_count": state["truth"]["pattern_truth"][
            "raw_pattern_score_displayed_as_probability_count"
        ],
        "telegram_message_ready_count": state["communications"][
            "message_ready_count"
        ],
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
