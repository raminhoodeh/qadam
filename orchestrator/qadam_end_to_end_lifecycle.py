"""Canonical public-safe 10-stage Qadam operating lifecycle.

The lifecycle explains architecture and aggregates existing runtime evidence. It
does not create research records, approvals, orders, broker writes, policy
changes, live-capital authority, or proof credit.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    runtime_dir,
    unique_errors,
    validate_authority,
)

SCHEMA_VERSION = "qadam_end_to_end_lifecycle.v1"
CONTRACT_ARTIFACT = "qadam_end_to_end_lifecycle.json"
ROUTE_MAP_ARTIFACT = "qadam_dashboard_route_stage_map.json"
SUMMARY_ARTIFACT = "qadam_lifecycle_dashboard_summary.json"
CHECK_ARTIFACT = "qadam_end_to_end_lifecycle_checks.json"

STAGE_IDS = (
    "observe_world",
    "qualify_evidence",
    "discover_patterns",
    "form_strategy_hypotheses",
    "validate_edge",
    "filter_tradeability",
    "govern_decision",
    "execute_monitor",
    "learn_outcome",
    "improve_reenter",
)

ROUTE_ORDER = (
    "system/team",
    "fund/portfolio",
    "fund/timeline",
    "observe/sources",
    "observe/universe",
    "patterns/findings",
    "patterns/nonlinear",
    "decide/strategies",
    "decide/decision",
    "trade/orders",
    "learn/outcomes",
    "learn/improvements",
    "system/overview",
)

ALLOWED_RELATIONSHIPS = {
    "primary",
    "supporting",
    "outcome_mirror",
    "cross_cutting",
    "unrelated",
}

ALLOWED_RUNTIME_STATES = {
    "active",
    "waiting_for_evidence",
    "blocked",
    "idle",
    "degraded",
    "unavailable",
}

STAGES: tuple[dict[str, Any], ...] = (
    {
        "stage_id": "observe_world",
        "number": 1,
        "label": "Observe the World",
        "short_label": "Observe",
        "plain_english": "Qadam watches independent world and market sources for changes worth recording.",
        "key_question": "What changed in the world or the markets?",
        "sub_stages": [
            "Ingest read-only sources",
            "Check freshness and outages",
            "Classify source trust",
            "Record provenance-linked observations",
        ],
        "inputs": ["Configured public and private read-only data providers"],
        "outputs": ["Fresh provenance-linked observations"],
        "actors": ["Python COO", "Local LLM Research Analyst"],
        "primary_routes": ["observe/sources"],
        "supporting_routes": ["observe/universe"],
        "safety_boundary": "Sources can inform research but cannot create trades or satisfy authority alone.",
    },
    {
        "stage_id": "qualify_evidence",
        "number": 2,
        "label": "Qualify the Evidence",
        "short_label": "Evidence",
        "plain_english": "Qadam checks whether an observation is timely, trustworthy, point-in-time safe, and relevant to a watched market.",
        "key_question": "Is the information reliable, timely, and relevant to a watched market?",
        "sub_stages": [
            "Normalize evidence",
            "Align source and price timestamps",
            "Map evidence to watched instruments",
            "Check quorum and paperability",
        ],
        "inputs": ["Fresh source observations", "Watched-market definitions"],
        "outputs": ["Qualified source-price evidence packet"],
        "actors": ["Python COO", "Local LLM Research Analyst"],
        "primary_routes": ["observe/universe"],
        "supporting_routes": ["observe/sources"],
        "safety_boundary": "Qualified evidence remains research input and is not a trade candidate.",
    },
    {
        "stage_id": "discover_patterns",
        "number": 3,
        "label": "Discover Patterns",
        "short_label": "Patterns",
        "plain_english": "Qadam searches for distinct relationships that repeat across sources, prices, assets, and market regimes.",
        "key_question": "Is there a repeatable relationship worth investigating?",
        "sub_stages": [
            "Engineer point-in-time features",
            "Scan transparent linear relationships",
            "Retrieve historical analogs",
            "Review nonlinear and quantum-assisted relationships",
            "Rank or reject findings",
        ],
        "inputs": ["Qualified source-price evidence"],
        "outputs": ["Ranked research pattern"],
        "actors": ["Python COO", "Local LLM Research Analyst", "Head of Quant"],
        "primary_routes": ["patterns/findings", "patterns/nonlinear"],
        "supporting_routes": ["decide/strategies"],
        "safety_boundary": "A pattern is research evidence, not a probability, strategy approval, or order.",
    },
    {
        "stage_id": "form_strategy_hypotheses",
        "number": 4,
        "label": "Form Strategy Hypotheses",
        "short_label": "Strategies",
        "plain_english": "Qadam turns a supported pattern into a testable trading idea with instruments, invalidation, lineage, and risk logic.",
        "key_question": "How could this pattern become a disciplined trading approach?",
        "sub_stages": [
            "Map to a defined strategy",
            "Propose an emerging strategy when needed",
            "Assign Research Goal lineage",
            "Define instruments, invalidation, and risk concept",
            "Reject weak hypotheses",
        ],
        "inputs": ["Ranked pattern evidence"],
        "outputs": ["Research-backed strategy hypothesis"],
        "actors": ["Local LLM Research Analyst", "Frontier LLM Strategy Lead"],
        "primary_routes": ["decide/strategies"],
        "supporting_routes": ["patterns/findings"],
        "safety_boundary": "A strategy hypothesis is not a qualified setup or execution approval.",
    },
    {
        "stage_id": "validate_edge",
        "number": 5,
        "label": "Validate the Edge",
        "short_label": "Validate",
        "plain_english": "Qadam tests whether a strategy worked repeatedly after costs, risk, holdout checks, and forward observation.",
        "key_question": "Does this strategy have a repeatable, tradeable edge?",
        "sub_stages": [
            "Run point-in-time historical backtests",
            "Use walk-forward and out-of-sample checks",
            "Observe forward shadow outcomes",
            "Measure expectancy and drawdown",
            "Graduate, hold, or reject the edge",
        ],
        "inputs": ["Strategy hypothesis", "Historical evidence", "Forward shadow evidence"],
        "outputs": ["Validated, rejected, or still-observing edge record"],
        "actors": ["Python COO", "Frontier LLM Strategy Lead", "Head of Quant"],
        "primary_routes": ["decide/strategies"],
        "supporting_routes": ["patterns/findings", "patterns/nonlinear"],
        "safety_boundary": "Backtests and shadow results cannot create orders or paper proof ledger credit.",
    },
    {
        "stage_id": "filter_tradeability",
        "number": 6,
        "label": "Filter Tradeability",
        "short_label": "Akber",
        "plain_english": "Akber checks whether an evidence-backed idea is practical to trade now, rather than merely interesting.",
        "key_question": "Is this idea practical to trade now?",
        "sub_stages": [
            "Build complete practical context",
            "Check catalyst and confirmation",
            "Check volatility, liquidity, and timing",
            "Check risk-reward and invalidation",
            "Return pass, hold, or veto",
        ],
        "inputs": ["Validated edge evidence", "Current market confirmation"],
        "outputs": ["Akber pass, hold, or veto with explanation"],
        "actors": ["Frontier LLM Strategy Lead", "Python COO"],
        "primary_routes": ["decide/decision"],
        "supporting_routes": ["decide/strategies"],
        "safety_boundary": "Akber pass is not risk approval, execution approval, or an order.",
    },
    {
        "stage_id": "govern_decision",
        "number": 7,
        "label": "Govern the Decision",
        "short_label": "Govern",
        "plain_english": "Qadam combines portfolio risk and safety gates into exactly one final Router state for each setup.",
        "key_question": "Is this setup allowed into the guarded paper route?",
        "sub_stages": [
            "Apply portfolio risk budget",
            "Check drawdown and duplicate exposure",
            "Build idempotency material",
            "Respect Q-CTRL consultation state",
            "Route to reject, hold, shadow, repair, or paper review",
        ],
        "inputs": ["Akber verdict", "Risk state", "PaperOps safety state"],
        "outputs": ["One Router state and, only when clean, a PaperOps handoff"],
        "actors": ["Python COO", "Frontier LLM Strategy Lead"],
        "primary_routes": ["decide/decision"],
        "supporting_routes": ["trade/orders"],
        "safety_boundary": "Only a clean paper-review candidate can reach PaperOps; no dashboard authority is created.",
    },
    {
        "stage_id": "execute_monitor",
        "number": 8,
        "label": "Execute and Monitor",
        "short_label": "Paper Trade",
        "plain_english": "The Python executor submits only through guarded Alpaca Paper and keeps every paper order and position in an unambiguous lifecycle state.",
        "key_question": "What happened to the paper order and position?",
        "sub_stages": [
            "Submit through guarded Alpaca Paper",
            "Reconcile broker acceptance",
            "Track fills and open positions",
            "Apply stale-order policy",
            "Record close or cancellation",
        ],
        "inputs": ["Clean PaperOps handoff"],
        "outputs": ["Unambiguous paper-order and position state"],
        "actors": ["Python COO", "Paper execution desk"],
        "primary_routes": ["trade/orders"],
        "supporting_routes": ["fund/portfolio", "fund/timeline"],
        "safety_boundary": "Paper execution only; no live-capital route or unmanaged broker write exists.",
    },
    {
        "stage_id": "learn_outcome",
        "number": 9,
        "label": "Learn From the Outcome",
        "short_label": "Learn",
        "plain_english": "Qadam compares what it expected with what happened and records only lessons supported by attributable evidence.",
        "key_question": "What did the trade, hold, veto, or research event teach Qadam?",
        "sub_stages": [
            "Record outcome or research event",
            "Attribute source, model, filter, and route effects",
            "Write a postmortem",
            "Separate market outcome from system defect",
            "Record a supported lesson",
        ],
        "inputs": ["Paper outcome", "Hold or veto", "Shadow outcome", "System event"],
        "outputs": ["Supported lesson with complete lineage"],
        "actors": ["Local LLM Research Analyst", "Frontier LLM Strategy Lead", "Python COO"],
        "primary_routes": ["learn/outcomes"],
        "supporting_routes": ["fund/timeline", "fund/portfolio"],
        "safety_boundary": "Only a real closed Qadam paper trade with complete lineage may be considered for the paper proof ledger.",
    },
    {
        "stage_id": "improve_reenter",
        "number": 10,
        "label": "Improve and Re-enter",
        "short_label": "Improve",
        "plain_english": "Qadam tests a specific proposed change before an approved, versioned improvement can affect the next observation cycle.",
        "key_question": "Should Qadam change future behavior because of what it learned?",
        "sub_stages": [
            "Propose a measurable change",
            "Test it historically",
            "Observe it forward without orders",
            "Review evidence and failure conditions",
            "Apply or reject a versioned change",
            "Return an approved version to Observe",
        ],
        "inputs": ["Supported lesson", "Historical and forward test evidence"],
        "outputs": ["Approved versioned improvement or rejected proposal"],
        "actors": ["Frontier LLM Strategy Lead", "Python COO", "Human operator"],
        "primary_routes": ["learn/improvements"],
        "supporting_routes": ["learn/outcomes", "observe/sources"],
        "safety_boundary": "Learning remains proposal-first and cannot silently change code, policy, secrets, or authority.",
    },
)

ROUTE_CONTEXTS: dict[str, dict[str, Any]] = {
    "system/team": {
        "relationship": "cross_cutting",
        "primary_stage_ids": [],
        "supporting_stage_ids": list(STAGE_IDS),
        "outcome_stage_ids": [],
        "cross_cutting": True,
        "relationship_label": "Cross-cutting across all 10 stages",
        "module_relationship": "The hybrid Qadam team contributes different responsibilities throughout the lifecycle.",
        "entry_from": [],
        "hands_off_to": [],
    },
    "fund/portfolio": {
        "relationship": "outcome_mirror",
        "primary_stage_ids": [],
        "supporting_stage_ids": ["learn_outcome"],
        "outcome_stage_ids": ["execute_monitor"],
        "cross_cutting": False,
        "relationship_label": "Stage 8 outcome mirror; supports stage 9",
        "module_relationship": "Portfolio values show the financial consequences of guarded paper execution and provide evidence for later learning.",
        "entry_from": ["execute_monitor"],
        "hands_off_to": ["learn_outcome"],
    },
    "fund/timeline": {
        "relationship": "outcome_mirror",
        "primary_stage_ids": [],
        "supporting_stage_ids": ["learn_outcome"],
        "outcome_stage_ids": ["execute_monitor"],
        "cross_cutting": False,
        "relationship_label": "Stage 8 chronology; supports stage 9",
        "module_relationship": "The timeline records paper-order and position events in the order they happened and links them to learning.",
        "entry_from": ["execute_monitor"],
        "hands_off_to": ["learn_outcome"],
    },
    "observe/sources": {
        "relationship": "primary",
        "primary_stage_ids": ["observe_world"],
        "supporting_stage_ids": ["qualify_evidence"],
        "outcome_stage_ids": [],
        "cross_cutting": False,
        "relationship_label": "Primary stage 1 of 10; supports stage 2",
        "module_relationship": "This page owns source observation, freshness, trust, and outage visibility.",
        "entry_from": ["improve_reenter"],
        "hands_off_to": ["qualify_evidence"],
    },
    "observe/universe": {
        "relationship": "primary",
        "primary_stage_ids": ["qualify_evidence"],
        "supporting_stage_ids": ["observe_world"],
        "outcome_stage_ids": [],
        "cross_cutting": False,
        "relationship_label": "Primary stage 2 of 10; supports stage 1",
        "module_relationship": "This page shows where qualified evidence may map across Qadam's watched markets and instruments.",
        "entry_from": ["observe_world"],
        "hands_off_to": ["discover_patterns"],
    },
    "patterns/findings": {
        "relationship": "primary",
        "primary_stage_ids": ["discover_patterns"],
        "supporting_stage_ids": ["validate_edge"],
        "outcome_stage_ids": [],
        "cross_cutting": False,
        "relationship_label": "Primary stage 3 of 10; supports stage 5",
        "module_relationship": "This page owns ranked pattern findings and shows what each relationship still needs before edge validation.",
        "entry_from": ["qualify_evidence"],
        "hands_off_to": ["form_strategy_hypotheses", "validate_edge"],
    },
    "patterns/nonlinear": {
        "relationship": "primary",
        "primary_stage_ids": ["discover_patterns"],
        "supporting_stage_ids": ["validate_edge"],
        "outcome_stage_ids": [],
        "cross_cutting": False,
        "relationship_label": "Stage 3 specialist review; supports stage 5",
        "module_relationship": "This page tests whether nonlinear or quantum-assisted analysis adds evidence beyond a matched classical baseline.",
        "entry_from": ["discover_patterns"],
        "hands_off_to": ["validate_edge"],
    },
    "decide/strategies": {
        "relationship": "primary",
        "primary_stage_ids": ["form_strategy_hypotheses", "validate_edge"],
        "supporting_stage_ids": ["filter_tradeability"],
        "outcome_stage_ids": [],
        "cross_cutting": False,
        "relationship_label": "Primary stages 4 and 5; supports stage 6",
        "module_relationship": "This page shows how patterns become strategy hypotheses and how those ideas earn, fail, or await edge evidence.",
        "entry_from": ["discover_patterns"],
        "hands_off_to": ["filter_tradeability"],
    },
    "decide/decision": {
        "relationship": "primary",
        "primary_stage_ids": ["filter_tradeability", "govern_decision"],
        "supporting_stage_ids": ["execute_monitor"],
        "outcome_stage_ids": [],
        "cross_cutting": False,
        "relationship_label": "Primary stages 6 and 7; supports stage 8",
        "module_relationship": "This page owns Akber's practical verdict, portfolio governance, the Router state, and the guarded PaperOps boundary.",
        "entry_from": ["validate_edge"],
        "hands_off_to": ["execute_monitor"],
    },
    "trade/orders": {
        "relationship": "primary",
        "primary_stage_ids": ["execute_monitor"],
        "supporting_stage_ids": ["learn_outcome"],
        "outcome_stage_ids": [],
        "cross_cutting": False,
        "relationship_label": "Primary stage 8 of 10; supports stage 9",
        "module_relationship": "This page owns the guarded paper-order and position lifecycle after a clean PaperOps handoff.",
        "entry_from": ["govern_decision"],
        "hands_off_to": ["learn_outcome"],
    },
    "learn/outcomes": {
        "relationship": "primary",
        "primary_stage_ids": ["learn_outcome"],
        "supporting_stage_ids": ["improve_reenter"],
        "outcome_stage_ids": [],
        "cross_cutting": False,
        "relationship_label": "Primary stage 9 of 10; supports stage 10",
        "module_relationship": "This page owns attributable outcomes, postmortems, and supported lessons.",
        "entry_from": ["execute_monitor"],
        "hands_off_to": ["improve_reenter"],
    },
    "learn/improvements": {
        "relationship": "primary",
        "primary_stage_ids": ["improve_reenter"],
        "supporting_stage_ids": ["observe_world"],
        "outcome_stage_ids": [],
        "cross_cutting": False,
        "relationship_label": "Primary stage 10 of 10; returns to stage 1",
        "module_relationship": "This page owns proposed, tested, reviewed, applied, and rejected improvements before the next observation cycle.",
        "entry_from": ["learn_outcome"],
        "hands_off_to": ["observe_world"],
    },
    "system/overview": {
        "relationship": "cross_cutting",
        "primary_stage_ids": [],
        "supporting_stage_ids": list(STAGE_IDS),
        "outcome_stage_ids": [],
        "cross_cutting": True,
        "relationship_label": "Monitors all 10 stages",
        "module_relationship": "This page reports freshness, activity, blockers, and defects across the complete lifecycle.",
        "entry_from": [],
        "hands_off_to": [],
    },
}

STAGE_ARTIFACT_REFS: dict[str, list[str]] = {
    "observe_world": ["data/runtime/qadam_source_operational_state.jsonl"],
    "qualify_evidence": ["data/runtime/qadam_backfill_coverage.json", "data/runtime/qsase_trading_universe.json"],
    "discover_patterns": ["data/runtime/qadam_pattern_score_v3_records.jsonl", "data/runtime/qadam_quantum_usefulness_summary.json"],
    "form_strategy_hypotheses": ["data/runtime/qadam_strategy_hypotheses_v3.jsonl", "data/runtime/qadam_strategy_foundry_v3.json"],
    "validate_edge": ["data/runtime/qadam_edge_registry_summary.json", "data/runtime/qadam_forward_shadow_state.json"],
    "filter_tradeability": ["data/runtime/qadam_akber_filter_v3_results.jsonl", "data/runtime/qadam_akber_filter_v3_dashboard_summary.json"],
    "govern_decision": ["data/runtime/qadam_router_v3_scoreboard.json", "data/runtime/qadam_research_lock_release_readiness.json"],
    "execute_monitor": ["data/runtime/qadam_paper_lifecycle_v3.json", "data/runtime/qsase_dashboard_current_portfolio.json"],
    "learn_outcome": ["data/runtime/qadam_learning_cycle_dashboard.json", "data/runtime/qadam_paper_proof_eligibility.json"],
    "improve_reenter": ["data/runtime/qadam_improvement_pipeline_dashboard.json", "data/runtime/qadam_stage1_learning_input.json"],
}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return default


def _rows(value: Any) -> list[dict[str, Any]]:
    return value if isinstance(value, list) else []


def _field_count(payload: Any, *fields: str) -> int:
    if isinstance(payload, list):
        return len(payload)
    if not isinstance(payload, dict):
        return 0
    for field in fields:
        value = payload.get(field)
        if isinstance(value, list):
            return len(value)
        if value is not None:
            return _safe_int(value)
    return 0


def build_lifecycle_contract(*, generated_at: str | None = None) -> dict[str, Any]:
    generated = generated_at or now_iso()
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_end_to_end_lifecycle_contract",
        "generated_at": generated,
        "status": "canonical_lifecycle_defined",
        "stage_count": len(STAGES),
        "route_count": len(ROUTE_CONTEXTS),
        "stages": [dict(stage) for stage in STAGES],
        "route_contexts": {route: dict(context) for route, context in ROUTE_CONTEXTS.items()},
        "cycle": [*STAGE_IDS, STAGE_IDS[0]],
        "single_global_current_stage": False,
        "concurrent_item_lifecycles_supported": True,
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "paper_only": True,
        "authority": authority_flags(),
    }


def build_route_stage_map(*, generated_at: str | None = None) -> dict[str, Any]:
    generated = generated_at or now_iso()
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_dashboard_route_stage_map",
        "generated_at": generated,
        "status": "route_stage_map_ready",
        "route_count": len(ROUTE_CONTEXTS),
        "route_order": list(ROUTE_ORDER),
        "route_contexts": {route: dict(context) for route, context in ROUTE_CONTEXTS.items()},
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "paper_only": True,
        "authority": authority_flags(),
    }


def _freshness_index(freshness: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = freshness.get("records") if isinstance(freshness, dict) else []
    return {
        str(record.get("artifact") or ""): record
        for record in _rows(records)
        if record.get("artifact")
    }


def _stage_freshness(stage_id: str, freshness: dict[str, Any]) -> tuple[str, str | None]:
    index = _freshness_index(freshness)
    matched = [index[ref] for ref in STAGE_ARTIFACT_REFS[stage_id] if ref in index]
    if not matched:
        return "not_monitored", None
    states = {str(record.get("freshness_state") or "unknown") for record in matched}
    timestamps = [str(record.get("generated_at")) for record in matched if record.get("generated_at")]
    if "missing" in states:
        state = "missing"
    elif "stale" in states:
        state = "stale"
    elif states == {"fresh"}:
        state = "fresh"
    else:
        state = "unknown"
    return state, max(timestamps) if timestamps else None


def _runtime_record(
    *,
    stage_id: str,
    state: str,
    summary: str,
    item_count: int,
    blockers: list[str] | None,
    freshness: dict[str, Any],
    metrics: list[dict[str, Any]],
) -> dict[str, Any]:
    freshness_state, source_generated_at = _stage_freshness(stage_id, freshness)
    effective_state = state
    effective_blockers = [str(item) for item in (blockers or []) if str(item)]
    if freshness_state in {"missing", "stale"} and state not in {"blocked", "unavailable"}:
        effective_state = "degraded"
        effective_blockers.append(
            "Required lifecycle evidence is stale."
            if freshness_state == "stale"
            else "Required lifecycle evidence is missing."
        )
    return {
        "stage_id": stage_id,
        "state": effective_state,
        "summary": summary,
        "item_count": max(0, _safe_int(item_count)),
        "blockers": list(dict.fromkeys(effective_blockers)),
        "freshness": freshness_state,
        "source_generated_at": source_generated_at,
        "artifact_refs": STAGE_ARTIFACT_REFS[stage_id],
        "metrics": metrics,
    }


def build_lifecycle_dashboard_summary(
    context: dict[str, Any],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated = generated_at or now_iso()
    source = context.get("source_summary") if isinstance(context.get("source_summary"), dict) else {}
    source_count = _safe_int(source.get("source_count"))
    fresh_source_count = _safe_int(source.get("fresh_count"))
    universe = context.get("trading_universe") if isinstance(context.get("trading_universe"), dict) else {}
    instrument_count = _field_count(
        universe,
        "instrument_count",
        "watched_instrument_count",
        "market_count",
        "rows",
        "instruments",
        "markets",
    )
    backfill = context.get("backfill_progress") if isinstance(context.get("backfill_progress"), dict) else {}
    completed_jobs = _safe_int(backfill.get("completed_jobs"))
    total_jobs = _safe_int(backfill.get("total_jobs"))
    findings = _rows(context.get("findings"))
    quantum = context.get("quantum_review") if isinstance(context.get("quantum_review"), dict) else {}
    quantum_comparisons = _field_count(quantum, "empirical_comparison_count", "reviews")
    hypotheses = _rows(context.get("hypotheses"))
    foundry = context.get("foundry") if isinstance(context.get("foundry"), dict) else {}
    edge = context.get("edge_summary") if isinstance(context.get("edge_summary"), dict) else {}
    validated_edges = _safe_int(edge.get("validated_edge_count"))
    shadow = context.get("shadow_state") if isinstance(context.get("shadow_state"), dict) else {}
    shadow_count = _field_count(shadow, "decision_count", "record_count", "rows", "decisions")
    akber_results = _rows(context.get("akber_results"))
    akber_counts = Counter(
        str(record.get("decision") or record.get("state") or "unknown").lower()
        for record in akber_results
    )
    akber_pass = sum(count for key, count in akber_counts.items() if "pass" in key)
    akber_hold = sum(count for key, count in akber_counts.items() if "hold" in key or "wait" in key)
    akber_veto = sum(count for key, count in akber_counts.items() if "veto" in key or "reject" in key)
    router = context.get("router_scoreboard") if isinstance(context.get("router_scoreboard"), dict) else {}
    router_decisions = _safe_int(router.get("decision_count"))
    paper_review_count = _safe_int(router.get("paper_review_candidate_count"))
    handoff_count = _safe_int(context.get("handoff_count"))
    release = context.get("release") if isinstance(context.get("release"), dict) else {}
    router_why_not = context.get("router_why_not") if isinstance(context.get("router_why_not"), dict) else {}
    lifecycle = context.get("lifecycle") if isinstance(context.get("lifecycle"), dict) else {}
    order_count = _field_count(lifecycle, "order_count", "paper_order_count", "orders", "records")
    ambiguous_count = _safe_int(lifecycle.get("ambiguous_lifecycle_count"))
    portfolio = context.get("current_portfolio") if isinstance(context.get("current_portfolio"), dict) else {}
    open_positions = _field_count(portfolio, "position_count", "open_position_count", "rows", "positions")
    learning = context.get("learning_cycle") if isinstance(context.get("learning_cycle"), dict) else {}
    learning_counts = learning.get("counts") if isinstance(learning.get("counts"), dict) else {}
    learning_event_count = _safe_int(learning_counts.get("learnable_event_count"))
    outcome_count = _safe_int(learning_counts.get("qadam_origin_outcome_count"))
    proof_count = _safe_int(learning_counts.get("proof_eligible_count"))
    improvement = context.get("improvement_pipeline") if isinstance(context.get("improvement_pipeline"), dict) else {}
    improvement_counts = improvement.get("counts") if isinstance(improvement.get("counts"), dict) else {}
    active_improvements = _safe_int(improvement_counts.get("active_candidate_count"))
    applied_improvements = _safe_int(improvement_counts.get("applied_version_count"))
    freshness = context.get("freshness") if isinstance(context.get("freshness"), dict) else {}

    source_state = "unavailable" if not source_count else (
        "degraded" if fresh_source_count < source_count else "active"
    )
    source_blockers = [] if source_count and fresh_source_count == source_count else [
        "No source state is available."
        if not source_count
        else f"{source_count - fresh_source_count} sources are not currently fresh."
    ]
    evidence_state = "active" if instrument_count and fresh_source_count else (
        "waiting_for_evidence" if instrument_count or source_count else "unavailable"
    )
    evidence_blockers = [] if instrument_count and fresh_source_count else [
        "Qualified source and market evidence is incomplete."
    ]
    pattern_state = "active" if findings else (
        "waiting_for_evidence" if instrument_count else "unavailable"
    )
    strategy_state = "active" if hypotheses else (
        "waiting_for_evidence" if findings else "idle"
    )
    edge_state = "active" if validated_edges else (
        "waiting_for_evidence" if hypotheses or findings else "idle"
    )
    if akber_results:
        akber_state = "active" if akber_pass else ("blocked" if akber_veto and not akber_hold else "waiting_for_evidence")
    else:
        akber_state = "waiting_for_evidence" if hypotheses else "idle"
    governance_state = "active" if paper_review_count or handoff_count else (
        "waiting_for_evidence" if router_decisions else "idle"
    )
    if release.get("release_effective") is False and (paper_review_count or handoff_count):
        governance_state = "blocked"
    execution_state = "degraded" if ambiguous_count else (
        "active" if order_count or open_positions else "idle"
    )
    learning_state = "active" if learning_event_count or outcome_count else (
        "waiting_for_evidence" if order_count else "idle"
    )
    improvement_state = "active" if active_improvements or applied_improvements else (
        "waiting_for_evidence" if learning_event_count else "idle"
    )

    stage_states = {
        "observe_world": _runtime_record(
            stage_id="observe_world",
            state=source_state,
            summary=f"{fresh_source_count} of {source_count} connected sources are currently fresh." if source_count else "Current source state is unavailable.",
            item_count=source_count,
            blockers=source_blockers,
            freshness=freshness,
            metrics=[
                {"label": "Connected sources", "value": source_count},
                {"label": "Fresh sources", "value": fresh_source_count},
            ],
        ),
        "qualify_evidence": _runtime_record(
            stage_id="qualify_evidence",
            state=evidence_state,
            summary=(
                f"{instrument_count} watched instruments are available for source-price qualification; {completed_jobs} of {total_jobs} historical jobs are complete."
                if instrument_count
                else "No qualified trading-universe projection is available."
            ),
            item_count=instrument_count,
            blockers=evidence_blockers,
            freshness=freshness,
            metrics=[
                {"label": "Watched instruments", "value": instrument_count},
                {"label": "Historical jobs", "value": f"{completed_jobs}/{total_jobs}"},
            ],
        ),
        "discover_patterns": _runtime_record(
            stage_id="discover_patterns",
            state=pattern_state,
            summary=f"{len(findings)} distinct relationships are documented; {quantum_comparisons} empirical nonlinear comparisons are available.",
            item_count=len(findings),
            blockers=[] if findings else ["No ranked pattern finding is currently available."],
            freshness=freshness,
            metrics=[
                {"label": "Documented relationships", "value": len(findings)},
                {"label": "Nonlinear comparisons", "value": quantum_comparisons},
            ],
        ),
        "form_strategy_hypotheses": _runtime_record(
            stage_id="form_strategy_hypotheses",
            state=strategy_state,
            summary=f"{len(hypotheses)} strategy hypotheses are recorded; foundry state is {foundry.get('status') or 'not reported'}.",
            item_count=len(hypotheses),
            blockers=[] if hypotheses else ["No pattern has produced an eligible strategy hypothesis yet."],
            freshness=freshness,
            metrics=[{"label": "Strategy hypotheses", "value": len(hypotheses)}],
        ),
        "validate_edge": _runtime_record(
            stage_id="validate_edge",
            state=edge_state,
            summary=f"{validated_edges} validated edges and {shadow_count} forward shadow decisions are recorded.",
            item_count=validated_edges,
            blockers=[] if validated_edges else ["No out-of-sample edge has graduated yet."],
            freshness=freshness,
            metrics=[
                {"label": "Validated edges", "value": validated_edges},
                {"label": "Shadow decisions", "value": shadow_count},
            ],
        ),
        "filter_tradeability": _runtime_record(
            stage_id="filter_tradeability",
            state=akber_state,
            summary=f"Akber has {akber_pass} passes, {akber_hold} holds, and {akber_veto} vetoes in the current evidence set.",
            item_count=len(akber_results),
            blockers=[] if akber_pass else ["No idea currently has a complete practical tradeability pass."],
            freshness=freshness,
            metrics=[
                {"label": "Pass", "value": akber_pass},
                {"label": "Hold", "value": akber_hold},
                {"label": "Veto", "value": akber_veto},
            ],
        ),
        "govern_decision": _runtime_record(
            stage_id="govern_decision",
            state=governance_state,
            summary=f"{router_decisions} Router decisions include {paper_review_count} paper-review candidates and {handoff_count} guarded handoffs.",
            item_count=router_decisions,
            blockers=[] if paper_review_count or handoff_count else [
                str(router_why_not.get("primary_reason") or "No setup is currently eligible for guarded paper review.")
            ],
            freshness=freshness,
            metrics=[
                {"label": "Router decisions", "value": router_decisions},
                {"label": "Paper-review candidates", "value": paper_review_count},
                {"label": "Guarded handoffs", "value": handoff_count},
            ],
        ),
        "execute_monitor": _runtime_record(
            stage_id="execute_monitor",
            state=execution_state,
            summary=f"{order_count} paper-order lifecycle records and {open_positions} open positions are visible; {ambiguous_count} lifecycle states are ambiguous.",
            item_count=order_count + open_positions,
            blockers=[] if not ambiguous_count else [f"{ambiguous_count} paper-order lifecycle states need reconciliation."],
            freshness=freshness,
            metrics=[
                {"label": "Order lifecycle records", "value": order_count},
                {"label": "Open positions", "value": open_positions},
                {"label": "Ambiguous states", "value": ambiguous_count},
            ],
        ),
        "learn_outcome": _runtime_record(
            stage_id="learn_outcome",
            state=learning_state,
            summary=f"{learning_event_count} learnable events include {outcome_count} Qadam-origin outcomes and {proof_count} records eligible for the paper proof ledger.",
            item_count=learning_event_count,
            blockers=[] if learning_event_count else ["No attributable Qadam outcome is ready for a supported lesson yet."],
            freshness=freshness,
            metrics=[
                {"label": "Learnable events", "value": learning_event_count},
                {"label": "Qadam outcomes", "value": outcome_count},
                {"label": "Paper proof ledger", "value": proof_count},
            ],
        ),
        "improve_reenter": _runtime_record(
            stage_id="improve_reenter",
            state=improvement_state,
            summary=f"{active_improvements} improvements are being tested and {applied_improvements} approved versions are active.",
            item_count=active_improvements + applied_improvements,
            blockers=[] if active_improvements or applied_improvements else ["No supported lesson has opened a measurable improvement test."],
            freshness=freshness,
            metrics=[
                {"label": "Being tested", "value": active_improvements},
                {"label": "Applied versions", "value": applied_improvements},
            ],
        ),
    }
    state_counts = Counter(record["state"] for record in stage_states.values())
    contract = build_lifecycle_contract(generated_at=generated)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_lifecycle_dashboard_summary",
        "generated_at": generated,
        "status": "lifecycle_ready_with_degraded_stages"
        if state_counts.get("degraded") or state_counts.get("unavailable")
        else "lifecycle_ready",
        "stage_count": len(STAGES),
        "route_count": len(ROUTE_CONTEXTS),
        "single_global_current_stage": False,
        "concurrent_item_lifecycles_supported": True,
        "stages": contract["stages"],
        "route_contexts": contract["route_contexts"],
        "stage_states": stage_states,
        "state_counts": dict(sorted(state_counts.items())),
        "freshness": freshness.get("status") or "not_reported",
        "contract_ref": f"data/runtime/{CONTRACT_ARTIFACT}",
        "route_map_ref": f"data/runtime/{ROUTE_MAP_ARTIFACT}",
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "paper_only": True,
        "authority": authority_flags(),
    }


def validate_lifecycle_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if contract.get("artifact_type") != "qadam_end_to_end_lifecycle_contract":
        errors.append("lifecycle_contract_type_invalid")
    stages = _rows(contract.get("stages"))
    if len(stages) != 10:
        errors.append("lifecycle_stage_count_not_ten")
    if [stage.get("number") for stage in stages] != list(range(1, 11)):
        errors.append("lifecycle_stage_numbers_invalid")
    if [stage.get("stage_id") for stage in stages] != list(STAGE_IDS):
        errors.append("lifecycle_stage_ids_invalid")
    if len({stage.get("stage_id") for stage in stages}) != len(stages):
        errors.append("lifecycle_stage_ids_duplicated")
    route_contexts = contract.get("route_contexts") if isinstance(contract.get("route_contexts"), dict) else {}
    if set(route_contexts) != set(ROUTE_ORDER):
        errors.append("lifecycle_route_map_incomplete")
    for route, context in route_contexts.items():
        if context.get("relationship") not in ALLOWED_RELATIONSHIPS:
            errors.append(f"lifecycle_route_relationship_invalid:{route}")
        referenced = [
            *context.get("primary_stage_ids", []),
            *context.get("supporting_stage_ids", []),
            *context.get("outcome_stage_ids", []),
        ]
        if any(stage_id not in STAGE_IDS for stage_id in referenced):
            errors.append(f"lifecycle_route_stage_unknown:{route}")
        if not context.get("relationship_label") or not context.get("module_relationship"):
            errors.append(f"lifecycle_route_explanation_missing:{route}")
    for stage in stages:
        for field in (
            "label",
            "short_label",
            "plain_english",
            "key_question",
            "sub_stages",
            "inputs",
            "outputs",
            "actors",
            "primary_routes",
            "safety_boundary",
        ):
            if not stage.get(field):
                errors.append(f"lifecycle_stage_field_missing:{stage.get('stage_id')}:{field}")
        if any(route not in ROUTE_ORDER for route in stage.get("primary_routes", [])):
            errors.append(f"lifecycle_stage_primary_route_invalid:{stage.get('stage_id')}")
    if contract.get("single_global_current_stage") is not False:
        errors.append("lifecycle_false_global_stage_claim")
    if contract.get("concurrent_item_lifecycles_supported") is not True:
        errors.append("lifecycle_concurrent_items_not_supported")
    if contract.get("public_safe") is not True or contract.get("read_only") is not True:
        errors.append("lifecycle_contract_not_public_read_only")
    errors.extend(validate_authority(contract.get("authority", {}), prefix="lifecycle_contract"))
    return unique_errors(errors)


def validate_lifecycle_summary(summary: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if summary.get("artifact_type") != "qadam_lifecycle_dashboard_summary":
        errors.append("lifecycle_summary_type_invalid")
    if summary.get("stage_count") != 10:
        errors.append("lifecycle_summary_stage_count_invalid")
    states = summary.get("stage_states") if isinstance(summary.get("stage_states"), dict) else {}
    if set(states) != set(STAGE_IDS):
        errors.append("lifecycle_summary_states_incomplete")
    for stage_id, record in states.items():
        if record.get("state") not in ALLOWED_RUNTIME_STATES:
            errors.append(f"lifecycle_runtime_state_invalid:{stage_id}")
        if not record.get("summary"):
            errors.append(f"lifecycle_runtime_summary_missing:{stage_id}")
        if not record.get("freshness"):
            errors.append(f"lifecycle_runtime_freshness_missing:{stage_id}")
        if not isinstance(record.get("artifact_refs"), list) or not record.get("artifact_refs"):
            errors.append(f"lifecycle_runtime_provenance_missing:{stage_id}")
        if not isinstance(record.get("blockers"), list):
            errors.append(f"lifecycle_runtime_blockers_invalid:{stage_id}")
    if summary.get("single_global_current_stage") is not False:
        errors.append("lifecycle_summary_false_global_stage_claim")
    for field in ("paper_order_created_count", "broker_write_count"):
        if summary.get(field) != 0:
            errors.append(f"lifecycle_summary_{field}_nonzero")
    for field in ("proof_credit_allowed", "live_capital_enabled"):
        if summary.get(field) is not False:
            errors.append(f"lifecycle_summary_{field}_unsafe")
    for field in ("public_safe", "read_only", "command_disabled", "paper_only"):
        if summary.get(field) is not True:
            errors.append(f"lifecycle_summary_{field}_must_be_true")
    errors.extend(validate_authority(summary.get("authority", {}), prefix="lifecycle_summary"))
    return unique_errors(errors)


def write_lifecycle_artifacts(
    contract: dict[str, Any],
    route_map: dict[str, Any],
    summary: dict[str, Any],
    settings: Settings | None = None,
) -> dict[str, str]:
    store = AtomicArtifactStore(runtime_dir(settings))
    store.write_json(CONTRACT_ARTIFACT, contract)
    store.write_json(ROUTE_MAP_ARTIFACT, route_map)
    store.write_json(SUMMARY_ARTIFACT, summary)
    return {
        "contract": str(store.path(CONTRACT_ARTIFACT)),
        "route_map": str(store.path(ROUTE_MAP_ARTIFACT)),
        "summary": str(store.path(SUMMARY_ARTIFACT)),
    }


def build_and_write_end_to_end_lifecycle(
    context: dict[str, Any],
    settings: Settings | None = None,
    *,
    generated_at: str | None = None,
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    generated = generated_at or now_iso()
    contract = build_lifecycle_contract(generated_at=generated)
    route_map = build_route_stage_map(generated_at=generated)
    summary = build_lifecycle_dashboard_summary(context, generated_at=generated)
    errors = [
        *validate_lifecycle_contract(contract),
        *validate_lifecycle_summary(summary),
    ]
    written = write_lifecycle_artifacts(contract, route_map, summary, settings)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_end_to_end_lifecycle_checks",
        "generated_at": generated,
        "status": "passed" if not errors else "blocked",
        "stage_count": contract["stage_count"],
        "route_count": contract["route_count"],
        "single_global_current_stage": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "validation_error_count": len(unique_errors(errors)),
        "validation_errors": unique_errors(errors),
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "paper_only": True,
        "authority": authority_flags(),
    }
    store = AtomicArtifactStore(runtime_dir(settings))
    store.write_json(CHECK_ARTIFACT, checks)
    written["checks"] = str(store.path(CHECK_ARTIFACT))
    return summary, written, unique_errors(errors)
