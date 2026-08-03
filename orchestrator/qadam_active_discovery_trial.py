"""Five-market-session active discovery trial and public-safe progress view.

The trial observes Qadam's existing guarded pipeline. It does not create a
candidate, approve risk, submit an order, advance the 30-day paper growth
trial, or grant proof credit.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_experimental_paper_policy import (
    POLICY_VERSION as EXPERIMENTAL_POLICY_VERSION,
)
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    file_sha256,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_portfolio_risk_engine import (
    POLICY_VERSION as PORTFOLIO_POLICY_VERSION,
)
from orchestrator.qadam_wave_b_common import (
    parse_timestamp,
    record_set_hash,
    safe_float,
    stable_id,
)

SCHEMA_VERSION = "qadam_active_discovery_trial.v1"
TRIAL_VERSION = "qadam-active-discovery-trial.1-five-market-sessions"
MARKET_SESSION_TARGET = 5
EXPECTED_INSTRUMENT_COUNT = 19
SHORTLIST_TARGET = 5
NEW_YORK = ZoneInfo("America/New_York")

CONTRACT_ARTIFACT = "qadam_active_discovery_trial_contract.json"
STATUS_ARTIFACT = "qadam_active_discovery_trial_status.json"
EVALUATIONS_ARTIFACT = "qadam_active_discovery_trial_evaluations.jsonl"
SESSIONS_ARTIFACT = "qadam_active_discovery_trial_sessions.jsonl"
DASHBOARD_ARTIFACT = "qadam_active_discovery_trial_dashboard_summary.json"
CHECK_ARTIFACT = "qadam_active_discovery_trial_checks.json"

PATTERN_ARTIFACT = "qadam_pattern_score_v3_records.jsonl"
PATTERN_CHECK_ARTIFACT = "qadam_pattern_score_v3_checks.json"
HYPOTHESES_ARTIFACT = "qadam_strategy_hypotheses_v3.jsonl"
FOUNDRY_REJECTIONS_ARTIFACT = "qadam_strategy_hypothesis_rejections_v3.jsonl"
AKBER_RESULTS_ARTIFACT = "qadam_akber_filter_v3_results.jsonl"
SHADOW_DECISIONS_ARTIFACT = "qadam_forward_shadow_decisions.jsonl"
RISK_PROPOSALS_ARTIFACT = "qadam_position_size_proposals.jsonl"
RISK_REJECTIONS_ARTIFACT = "qadam_risk_rejections.jsonl"
ROUTER_DECISIONS_ARTIFACT = "qadam_router_v3_decisions.jsonl"
HANDOFFS_ARTIFACT = "qadam_paperops_handoff_v3_accepted.jsonl"
PAPER_ORDERS_ARTIFACT = "paper_orders.jsonl"
MIRROR_ARTIFACT = "alpaca_paper_mirror.json"
RECEIPT_INDEX_ARTIFACT = "qadam_operator_service_receipt_index.json"

PIPELINE_SERVICES = (
    "pattern_scoring",
    "research_evidence_validation",
    "akber_review",
    "forward_shadow",
    "portfolio_router_review",
)


def _artifact_hash(path: Path) -> str | None:
    return file_sha256(path) if path.is_file() else None


def _new_contract(runtime: Path, generated_at: str) -> dict[str, Any]:
    trial_id = stable_id("active-discovery-trial", generated_at, TRIAL_VERSION)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_active_discovery_trial_contract",
        "trial_id": trial_id,
        "trial_version": TRIAL_VERSION,
        "activated_at": generated_at,
        "status": "frozen_active",
        "market_session_target": MARKET_SESSION_TARGET,
        "expected_instrument_count": EXPECTED_INSTRUMENT_COUNT,
        "shortlist_target_per_session": SHORTLIST_TARGET,
        "purpose": (
            "Measure whether the full watched universe can repeatedly progress through "
            "Qadam's guarded discovery pipeline during five real US market sessions."
        ),
        "seven_stages": [
            {"stage": 1, "name": "Unattended reliability", "output": "fresh healthy cycle"},
            {"stage": 2, "name": "Whole-universe evaluation", "output": "19 ranked instrument reviews"},
            {"stage": 3, "name": "Setup formation", "output": "bounded directional hypotheses or explicit rejections"},
            {"stage": 4, "name": "Akber review", "output": "pass, hold, or veto with typed reasons"},
            {"stage": 5, "name": "Shadow and portfolio risk", "output": "decision-time shadow and bounded size proposal or rejection"},
            {"stage": 6, "name": "Router and guarded PaperOps", "output": "one final state and guarded paper handoff when eligible"},
            {"stage": 7, "name": "Outcome and learning", "output": "session record, lifecycle outcome, and proposal-only learning"},
        ],
        "frozen_policy": {
            "experimental_policy_version": EXPERIMENTAL_POLICY_VERSION,
            "portfolio_policy_version": PORTFOLIO_POLICY_VERSION,
            "discovery_target_notional_usd": {"minimum": 500.0, "maximum": 1000.0},
            "absolute_trade_ceiling_usd": 5000.0,
            "maximum_concurrent_discovery_positions": 3,
            "maximum_discovery_positions_per_correlated_cluster": 1,
            "guarded_route": "guarded_alpaca_paper_via_paperops",
        },
        "calibration_snapshot": {
            "backtest_manifest_sha256": _artifact_hash(runtime / "qadam_backtest_run_manifest.json"),
            "akber_replay_sha256": _artifact_hash(runtime / "qadam_akber_filter_v3_replay.jsonl"),
            "akber_ablation_sha256": _artifact_hash(runtime / "qadam_akber_filter_v3_ablation.jsonl"),
            "thresholds_frozen_during_trial": True,
            "automatic_recalibration_allowed": False,
        },
        "acceptance_contract": {
            "minimum_distinct_instrument_evaluations": 15,
            "minimum_akber_reviews": 5,
            "minimum_paper_orders": None,
            "trade_quota": None,
            "zero_handoffs_is_reported_as_no_tradeable_setup_observed": True,
            "a_trade_is_never_forced_to_pass_the_trial": True,
        },
        "calendar": {
            "real_us_market_sessions_only": True,
            "backfill_allowed": False,
            "simulated_elapsed_time_allowed": False,
            "weekends_count": False,
        },
        "boundaries": {
            "paper_only": True,
            "live_capital_enabled": False,
            "direct_broker_write_allowed": False,
            "automatic_ambiguous_write_retry_allowed": False,
            "validated_edge_credit_allowed": False,
            "paper_proof_ledger_credit_allowed": False,
            "thirty_day_trial_calendar_advance_allowed": False,
        },
        "authority": authority_flags(),
    }


def _load_or_create_contract(runtime: Path, generated_at: str) -> dict[str, Any]:
    contract = read_json(runtime / CONTRACT_ARTIFACT)
    if contract.get("trial_version") == TRIAL_VERSION:
        return contract
    contract = _new_contract(runtime, generated_at)
    AtomicArtifactStore(runtime).write_json(CONTRACT_ARTIFACT, contract)
    return contract


def _market_session_date(runtime: Path, activated_at: str) -> str | None:
    mirror = read_json(runtime / MIRROR_ARTIFACT)
    clock = mirror.get("market_clock") if isinstance(mirror.get("market_clock"), dict) else {}
    observed = parse_timestamp(clock.get("timestamp"))
    activated = parse_timestamp(activated_at)
    if observed is None or activated is None or observed < activated:
        return None
    local = observed.astimezone(NEW_YORK)
    if local.weekday() >= 5 or clock.get("is_open") is not True:
        return None
    return local.date().isoformat()


def _best_scores_by_instrument(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for row in rows:
        instrument = str(row.get("instrument") or "")
        if not instrument or row.get("negative_control") is True:
            continue
        current = best.get(instrument)
        if current is None or safe_float(row.get("raw_pattern_score")) > safe_float(
            current.get("raw_pattern_score")
        ):
            best[instrument] = row
    return best


def _shortlisted_score_ids(best: dict[str, dict[str, Any]]) -> set[str]:
    ranked = sorted(
        best.values(),
        key=lambda row: (-safe_float(row.get("raw_pattern_score")), str(row.get("instrument") or "")),
    )
    selected: list[dict[str, Any]] = []
    seen_families: set[str] = set()
    for row in ranked:
        family = str(row.get("strategy_family_id") or row.get("market_family") or "")
        if family and family not in seen_families:
            selected.append(row)
            seen_families.add(family)
        if len(selected) == SHORTLIST_TARGET:
            break
    for row in ranked:
        if len(selected) == SHORTLIST_TARGET:
            break
        if row not in selected:
            selected.append(row)
    return {str(row.get("score_id")) for row in selected if row.get("score_id")}


def _score_id(record: dict[str, Any]) -> str:
    return str(
        record.get("score_id")
        or record.get("pattern_lineage", {}).get("score_id")
        or record.get("lineage", {}).get("score_id")
        or ""
    )


def _generation_consistency(runtime: Path) -> dict[str, Any]:
    index = read_json(runtime / RECEIPT_INDEX_ARTIFACT)
    receipts = index.get("latest_successful_receipts")
    receipts = receipts if isinstance(receipts, dict) else {}
    selected = {service: receipts.get(service, {}) for service in PIPELINE_SERVICES}
    missing = [service for service, receipt in selected.items() if not receipt]
    mixed = sum(int(receipt.get("mixed_generation_join_count") or 0) for receipt in selected.values())
    unbound = [
        service
        for service, receipt in selected.items()
        if receipt and receipt.get("input_generation_binding_complete") is not True
    ]
    pattern = selected["pattern_scoring"]
    validation = selected["research_evidence_validation"]
    akber = selected["akber_review"]
    shadow = selected["forward_shadow"]
    router = selected["portfolio_router_review"]
    comparisons = {
        "pattern_to_validation": pattern.get("generation_ids", {}).get("score_plane")
        == validation.get("input_generation_ids", {}).get("score_plane"),
        "validation_to_akber": validation.get("generation_ids", {}).get("edge_registry")
        == akber.get("input_generation_ids", {}).get("edge_registry"),
        "validation_to_shadow": validation.get("generation_ids", {}).get("edge_registry")
        == shadow.get("input_generation_ids", {}).get("edge_registry"),
        "validation_to_router": validation.get("generation_ids", {}).get("edge_registry")
        == router.get("input_generation_ids", {}).get("edge_registry"),
        "akber_price_to_shadow": akber.get("generation_ids", {}).get("price_lake")
        == shadow.get("input_generation_ids", {}).get("price_lake"),
        "akber_price_to_router": akber.get("generation_ids", {}).get("price_lake")
        == router.get("input_generation_ids", {}).get("price_lake"),
    }
    consistent = not missing and not unbound and mixed == 0 and all(comparisons.values())
    return {
        "consistent": consistent,
        "missing_successful_receipts": missing,
        "unbound_input_services": unbound,
        "mixed_generation_join_count": mixed,
        "comparisons": comparisons,
    }


def _evaluation_rows(runtime: Path, session_date: str, generated_at: str) -> list[dict[str, Any]]:
    scores = read_jsonl(runtime / PATTERN_ARTIFACT)
    best = _best_scores_by_instrument(scores)
    shortlist = _shortlisted_score_ids(best)
    hypotheses = {_score_id(row): row for row in read_jsonl(runtime / HYPOTHESES_ARTIFACT) if _score_id(row)}
    foundry_rejections = {
        _score_id(row): row for row in read_jsonl(runtime / FOUNDRY_REJECTIONS_ARTIFACT) if _score_id(row)
    }
    akber = {_score_id(row): row for row in read_jsonl(runtime / AKBER_RESULTS_ARTIFACT) if _score_id(row)}
    shadows = {str(row.get("hypothesis_id") or ""): row for row in read_jsonl(runtime / SHADOW_DECISIONS_ARTIFACT)}
    risk_proposals = {_score_id(row): row for row in read_jsonl(runtime / RISK_PROPOSALS_ARTIFACT) if _score_id(row)}
    risk_rejections = {_score_id(row): row for row in read_jsonl(runtime / RISK_REJECTIONS_ARTIFACT) if _score_id(row)}
    routers = {_score_id(row): row for row in read_jsonl(runtime / ROUTER_DECISIONS_ARTIFACT) if _score_id(row)}
    rows: list[dict[str, Any]] = []
    for instrument in sorted(best):
        score = best[instrument]
        score_id = str(score.get("score_id") or "")
        hypothesis = hypotheses.get(score_id, {})
        akber_result = akber.get(score_id, {})
        risk = risk_proposals.get(score_id) or risk_rejections.get(score_id) or {}
        router = routers.get(score_id, {})
        hypothesis_id = str(hypothesis.get("hypothesis_id") or "")
        shadow = shadows.get(hypothesis_id, {})
        blockers = []
        if not hypothesis:
            blockers.extend(foundry_rejections.get(score_id, {}).get("rejection_reasons", []))
        blockers.extend(akber_result.get("missing_critical_context", []))
        blockers.extend(risk.get("rejection_reasons", []))
        blockers.extend(router.get("hard_vetoes", []))
        blockers.extend(router.get("hold_reasons", []))
        stage_reached = 2
        if hypothesis:
            stage_reached = 3
        if akber_result:
            stage_reached = 4
        if shadow or risk:
            stage_reached = 5
        if router:
            stage_reached = 6
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_active_discovery_evaluation",
                "evaluation_id": stable_id("active-discovery-evaluation", session_date, instrument),
                "session_date": session_date,
                "first_evaluated_at": generated_at,
                "latest_evaluated_at": generated_at,
                "instrument": instrument,
                "market_family": score.get("market_family"),
                "strategy_family_id": score.get("strategy_family_id"),
                "score_id": score_id,
                "research_score": score.get("raw_pattern_score"),
                "direction_hypothesis": score.get("direction_hypothesis"),
                "horizon_hypothesis": score.get("horizon_hypothesis"),
                "shortlisted": score_id in shortlist,
                "stage_reached": stage_reached,
                "hypothesis_id": hypothesis_id or None,
                "akber_decision": akber_result.get("decision") or "not_reached",
                "shadow_state": shadow.get("decision") or shadow.get("state") or "not_reached",
                "risk_state": "proposal" if score_id in risk_proposals else "rejected" if risk else "not_reached",
                "router_state": router.get("final_state") or "not_reached",
                "blockers": unique_errors(str(value) for value in blockers if value),
                "trigger_origin": "scheduled_autonomous_research",
                "candidate_created": False,
                "order_created": False,
                "broker_write_count": 0,
                "proof_credit_count": 0,
                "live_capital_enabled": False,
                "authority": authority_flags(),
            }
        )
    return rows


def _merge_evaluations(
    previous: list[dict[str, Any]], current: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    merged = {str(row.get("evaluation_id") or ""): row for row in previous if row.get("evaluation_id")}
    for row in current:
        prior = merged.get(str(row["evaluation_id"]), {})
        if prior.get("first_evaluated_at"):
            row["first_evaluated_at"] = prior["first_evaluated_at"]
        merged[str(row["evaluation_id"])] = row
    return sorted(merged.values(), key=lambda row: (str(row.get("session_date")), str(row.get("instrument"))))


def _trigger_origin(order: dict[str, Any], guarded_receipts: list[dict[str, Any]]) -> str:
    identifiers = " ".join(
        str(order.get(field) or "")
        for field in ("client_order_id", "idempotency_key", "source_idempotency_key")
    )
    if "q7-operator-sleeve-" in identifiers:
        return "operator_exploratory"
    submitted = parse_timestamp(order.get("submitted_at") or order.get("created_at"))
    if submitted is not None and any(
        (completed := parse_timestamp(receipt.get("completed_at") or receipt.get("generated_at")))
        is not None
        and abs((submitted - completed).total_seconds()) <= 1800
        for receipt in guarded_receipts
    ):
        return "scheduled_autonomous"
    return "manual_or_unattributed"


def _session_record(
    session_date: str,
    rows: list[dict[str, Any]],
    generation: dict[str, Any],
    runtime: Path,
    generated_at: str,
    activated_at: str,
) -> dict[str, Any]:
    relevant = [row for row in rows if row.get("session_date") == session_date]
    started = parse_timestamp(activated_at) or datetime.min.replace(tzinfo=timezone.utc)
    receipt_index = read_json(runtime / RECEIPT_INDEX_ARTIFACT)
    latest = receipt_index.get("latest_successful_receipts") or {}
    guarded_receipts = [
        receipt
        for service, receipt in latest.items()
        if service == "guarded_paperops"
        and (parse_timestamp(receipt.get("completed_at") or receipt.get("generated_at")) or started) >= started
    ]
    orders = [
        order
        for order in read_jsonl(runtime / PAPER_ORDERS_ARTIFACT)
        if (parse_timestamp(order.get("submitted_at") or order.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc)) >= started
    ]
    origins = Counter(_trigger_origin(order, guarded_receipts) for order in orders)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_active_discovery_trial_session",
        "session_id": stable_id("active-discovery-session", session_date),
        "session_date": session_date,
        "generated_at": generated_at,
        "real_market_session_observed": True,
        "backfilled": False,
        "simulated_elapsed_time": False,
        "instrument_evaluation_count": len({row.get("instrument") for row in relevant}),
        "shortlisted_setup_count": sum(row.get("shortlisted") is True for row in relevant),
        "hypothesis_count": sum(bool(row.get("hypothesis_id")) for row in relevant),
        "akber_review_count": sum(row.get("akber_decision") != "not_reached" for row in relevant),
        "akber_decision_counts": dict(Counter(row.get("akber_decision") for row in relevant)),
        "risk_review_count": sum(row.get("risk_state") != "not_reached" for row in relevant),
        "router_review_count": sum(row.get("router_state") != "not_reached" for row in relevant),
        "generation_consistency": generation,
        "paper_order_origin_counts_since_trial_start": dict(sorted(origins.items())),
        "scheduled_autonomous_paper_order_count_since_trial_start": origins.get("scheduled_autonomous", 0),
        "trade_quota": None,
        "forced_trade_allowed": False,
        "live_capital_enabled": False,
        "proof_credit_count": 0,
        "authority": authority_flags(),
    }


def build_active_discovery_trial(
    settings: Settings | None = None,
    *,
    generated_at: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    runtime = runtime_dir(settings)
    generated = generated_at or now_iso()
    contract = _load_or_create_contract(runtime, generated)
    session_date = _market_session_date(runtime, str(contract.get("activated_at") or generated))
    evaluations = read_jsonl(runtime / EVALUATIONS_ARTIFACT)
    generation = _generation_consistency(runtime)
    if session_date:
        evaluations = _merge_evaluations(
            evaluations, _evaluation_rows(runtime, session_date, generated)
        )
    sessions_by_date = {
        str(row.get("session_date") or ""): row
        for row in read_jsonl(runtime / SESSIONS_ARTIFACT)
        if row.get("session_date")
    }
    if session_date:
        sessions_by_date[session_date] = _session_record(
            session_date,
            evaluations,
            generation,
            runtime,
            generated,
            str(contract.get("activated_at") or generated),
        )
    sessions = sorted(sessions_by_date.values(), key=lambda row: str(row.get("session_date")))
    counted_sessions = sessions[:MARKET_SESSION_TARGET]
    total_evaluations = sum(int(row.get("instrument_evaluation_count") or 0) for row in counted_sessions)
    total_akber = sum(int(row.get("akber_review_count") or 0) for row in counted_sessions)
    total_autonomous_orders = max(
        [int(row.get("scheduled_autonomous_paper_order_count_since_trial_start") or 0) for row in counted_sessions]
        + [0]
    )
    reliability = read_json(runtime / "qadam_operator_service_status.json")
    circuits = read_json(runtime / "qadam_operator_circuit_breakers.json")
    repair = read_json(runtime / "qadam_operator_repair_queue.json")
    open_circuits = int(reliability.get("open_circuit_count") or 0)
    if isinstance(circuits.get("circuits"), dict):
        open_circuits = sum(
            row.get("state") in {"open", "half_open"}
            for row in circuits["circuits"].values()
            if isinstance(row, dict)
        )
    repair_count = int(repair.get("repair_request_count") or len(repair.get("requests") or []))
    session_target_reached = len(counted_sessions) >= MARKET_SESSION_TARGET
    operational_integrity = bool(
        session_target_reached
        and all(row.get("instrument_evaluation_count") == EXPECTED_INSTRUMENT_COUNT for row in counted_sessions)
        and all(row.get("generation_consistency", {}).get("consistent") is True for row in counted_sessions)
        and open_circuits == 0
        and repair_count == 0
    )
    throughput_observed = total_evaluations >= 15 and total_akber >= 5
    if not session_target_reached:
        state = "active_collecting_real_market_sessions"
    elif not operational_integrity:
        state = "complete_with_operational_reliability_gaps"
    elif total_autonomous_orders:
        state = "complete_autonomous_paper_conversion_observed"
    else:
        state = "complete_no_tradeable_setup_observed"

    current_preview = _evaluation_rows(runtime, session_date or "preview", generated)
    stages = [
        {"stage": 1, "name": "Unattended reliability", "state": "ready" if open_circuits == 0 and repair_count == 0 else "needs_attention", "evidence": {"open_circuits": open_circuits, "repair_requests": repair_count}},
        {"stage": 2, "name": "Whole-universe evaluation", "state": "ready" if len(current_preview) == EXPECTED_INSTRUMENT_COUNT else "needs_attention", "evidence": {"evaluated_instruments": len(current_preview), "expected_instruments": EXPECTED_INSTRUMENT_COUNT}},
        {"stage": 3, "name": "Setup formation", "state": "active", "evidence": {"shortlisted": sum(row.get("shortlisted") is True for row in current_preview), "hypotheses": sum(bool(row.get("hypothesis_id")) for row in current_preview)}},
        {"stage": 4, "name": "Akber review", "state": "active", "evidence": dict(Counter(row.get("akber_decision") for row in current_preview))},
        {"stage": 5, "name": "Shadow and portfolio risk", "state": "active", "evidence": {"shadow_reviews": sum(row.get("shadow_state") != "not_reached" for row in current_preview), "risk_reviews": sum(row.get("risk_state") != "not_reached" for row in current_preview)}},
        {"stage": 6, "name": "Router and guarded PaperOps", "state": "active", "evidence": {"router_reviews": sum(row.get("router_state") != "not_reached" for row in current_preview), "autonomous_paper_orders": total_autonomous_orders}},
        {"stage": 7, "name": "Outcome and learning", "state": "collecting" if not session_target_reached else "review_ready", "evidence": {"market_sessions": len(counted_sessions), "target": MARKET_SESSION_TARGET}},
    ]
    status = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_active_discovery_trial_status",
        "trial_id": contract.get("trial_id"),
        "trial_version": TRIAL_VERSION,
        "generated_at": generated,
        "status": state,
        "activated_at": contract.get("activated_at"),
        "market_session_target": MARKET_SESSION_TARGET,
        "market_sessions_observed": len(counted_sessions),
        "market_sessions_remaining": max(MARKET_SESSION_TARGET - len(counted_sessions), 0),
        "current_market_session_date": session_date,
        "seven_stage_state": stages,
        "metrics": {
            "current_instrument_evaluation_count": len(current_preview),
            "current_shortlist_count": sum(row.get("shortlisted") is True for row in current_preview),
            "current_hypothesis_count": sum(bool(row.get("hypothesis_id")) for row in current_preview),
            "current_akber_decision_counts": dict(Counter(row.get("akber_decision") for row in current_preview)),
            "total_session_instrument_evaluations": total_evaluations,
            "total_session_akber_reviews": total_akber,
            "scheduled_autonomous_paper_order_count": total_autonomous_orders,
        },
        "generation_consistency": generation,
        "operational_integrity_passed": operational_integrity,
        "research_throughput_observed": throughput_observed,
        "tradeable_setup_observed": total_autonomous_orders > 0,
        "zero_trade_interpretation": (
            "No setup completed every evidence, Akber, risk and Router gate during the observed sessions."
            if session_target_reached and not total_autonomous_orders
            else None
        ),
        "no_forced_trades": True,
        "trade_quota": None,
        "paper_order_created_by_trial_module": 0,
        "broker_write_count": 0,
        "proof_credit_count": 0,
        "thirty_day_trial_calendar_advanced": False,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    dashboard = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_active_discovery_trial_dashboard_summary",
        "generated_at": generated,
        "status": state,
        "eyebrow": "Five-market-day active discovery trial",
        "headline": f"Session {len(counted_sessions)} of {MARKET_SESSION_TARGET}",
        "summary": (
            f"Qadam is evaluating all {len(current_preview)} watched instruments, shortlisting "
            f"{status['metrics']['current_shortlist_count']} for deeper review, and allowing only "
            "fully evidenced setups to continue through Akber, portfolio risk and guarded Alpaca Paper."
        ),
        "metrics": status["metrics"],
        "seven_stage_state": stages,
        "current_top_setups": [
            {
                key: row.get(key)
                for key in (
                    "instrument",
                    "strategy_family_id",
                    "research_score",
                    "direction_hypothesis",
                    "stage_reached",
                    "akber_decision",
                    "risk_state",
                    "router_state",
                    "blockers",
                )
            }
            for row in sorted(current_preview, key=lambda row: -safe_float(row.get("research_score")))
            if row.get("shortlisted") is True
        ],
        "why_not_trading_now": read_json(runtime / "qadam_router_v3_why_not_trading_now.json").get("primary_reason"),
        "boundary": "Read-only trial visibility. No trade quota, authority, broker write, live capital, or proof credit.",
        "public_safe": True,
        "read_only": True,
    }
    return status, evaluations, sessions, dashboard


def validate_active_discovery_trial(
    contract: dict[str, Any],
    status: dict[str, Any],
    evaluations: list[dict[str, Any]],
    sessions: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    if contract.get("trial_version") != TRIAL_VERSION:
        errors.append("active_discovery_trial_contract_version_invalid")
    if contract.get("market_session_target") != MARKET_SESSION_TARGET:
        errors.append("active_discovery_trial_session_target_changed")
    if contract.get("expected_instrument_count") != EXPECTED_INSTRUMENT_COUNT:
        errors.append("active_discovery_trial_instrument_count_changed")
    if contract.get("shortlist_target_per_session") != SHORTLIST_TARGET:
        errors.append("active_discovery_trial_shortlist_target_changed")
    if len(contract.get("seven_stages") or []) != 7:
        errors.append("active_discovery_trial_stage_count_invalid")
    if contract.get("acceptance_contract", {}).get("trade_quota") is not None:
        errors.append("active_discovery_trial_trade_quota_present")
    calendar = contract.get("calendar", {})
    if calendar.get("backfill_allowed") is not False or calendar.get("simulated_elapsed_time_allowed") is not False:
        errors.append("active_discovery_trial_calendar_fabrication_allowed")
    boundaries = contract.get("boundaries", {})
    for field in (
        "live_capital_enabled",
        "direct_broker_write_allowed",
        "automatic_ambiguous_write_retry_allowed",
        "validated_edge_credit_allowed",
        "paper_proof_ledger_credit_allowed",
        "thirty_day_trial_calendar_advance_allowed",
    ):
        if boundaries.get(field) is not False:
            errors.append(f"active_discovery_trial_unsafe_boundary:{field}")
    frozen = contract.get("frozen_policy", {})
    if frozen.get("experimental_policy_version") != EXPERIMENTAL_POLICY_VERSION:
        errors.append("active_discovery_trial_experimental_policy_changed")
    if frozen.get("portfolio_policy_version") != PORTFOLIO_POLICY_VERSION:
        errors.append("active_discovery_trial_portfolio_policy_changed")
    if frozen.get("discovery_target_notional_usd") != {
        "minimum": 500.0,
        "maximum": 1000.0,
    }:
        errors.append("active_discovery_trial_target_notional_changed")
    if frozen.get("absolute_trade_ceiling_usd") != 5000.0:
        errors.append("active_discovery_trial_absolute_ceiling_changed")
    if frozen.get("maximum_concurrent_discovery_positions") != 3:
        errors.append("active_discovery_trial_concurrency_changed")
    if frozen.get("maximum_discovery_positions_per_correlated_cluster") != 1:
        errors.append("active_discovery_trial_cluster_limit_changed")
    if frozen.get("guarded_route") != "guarded_alpaca_paper_via_paperops":
        errors.append("active_discovery_trial_guarded_route_changed")
    calibration = contract.get("calibration_snapshot", {})
    for field in (
        "backtest_manifest_sha256",
        "akber_replay_sha256",
        "akber_ablation_sha256",
    ):
        if not calibration.get(field):
            errors.append(f"active_discovery_trial_calibration_missing:{field}")
    if (
        calibration.get("thresholds_frozen_during_trial") is not True
        or calibration.get("automatic_recalibration_allowed") is not False
    ):
        errors.append("active_discovery_trial_calibration_not_frozen")
    if status.get("paper_order_created_by_trial_module") != 0:
        errors.append("active_discovery_trial_module_created_order")
    for row in evaluations:
        if row.get("candidate_created") is not False or row.get("order_created") is not False:
            errors.append(f"active_discovery_evaluation_created_trade_object:{row.get('evaluation_id')}")
        if row.get("live_capital_enabled") is not False or row.get("proof_credit_count") != 0:
            errors.append(f"active_discovery_evaluation_unsafe:{row.get('evaluation_id')}")
        errors.extend(validate_authority(row.get("authority", {}), prefix="active_discovery_evaluation"))
    for row in sessions:
        if row.get("backfilled") is not False or row.get("simulated_elapsed_time") is not False:
            errors.append(f"active_discovery_session_not_real:{row.get('session_id')}")
        if row.get("forced_trade_allowed") is not False or row.get("trade_quota") is not None:
            errors.append(f"active_discovery_session_trade_pressure:{row.get('session_id')}")
    errors.extend(validate_authority(contract.get("authority", {}), prefix="active_discovery_contract"))
    errors.extend(validate_authority(status.get("authority", {}), prefix="active_discovery_status"))
    return unique_errors(errors)


def build_and_write_active_discovery_trial(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    status, evaluations, sessions, dashboard = build_active_discovery_trial(settings)
    contract = read_json(runtime / CONTRACT_ARTIFACT)
    errors = validate_active_discovery_trial(contract, status, evaluations, sessions)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_active_discovery_trial_checks",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "implementation_ready": not errors,
        "trial_state": status.get("status"),
        "market_sessions_observed": status.get("market_sessions_observed"),
        "instrument_evaluation_count": status.get("metrics", {}).get("current_instrument_evaluation_count"),
        "generation_consistent": status.get("generation_consistency", {}).get("consistent"),
        "no_forced_trades": status.get("no_forced_trades") is True,
        "paper_order_created_by_trial_module": 0,
        "broker_write_count": 0,
        "proof_credit_count": 0,
        "live_capital_enabled": False,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store = AtomicArtifactStore(runtime)
    store.write_json(STATUS_ARTIFACT, status)
    store.write_jsonl(EVALUATIONS_ARTIFACT, evaluations)
    store.write_jsonl(SESSIONS_ARTIFACT, sessions)
    store.write_json(DASHBOARD_ARTIFACT, dashboard)
    store.write_json(CHECK_ARTIFACT, checks)
    return status, checks, errors


__all__ = [
    "CHECK_ARTIFACT",
    "CONTRACT_ARTIFACT",
    "DASHBOARD_ARTIFACT",
    "EVALUATIONS_ARTIFACT",
    "MARKET_SESSION_TARGET",
    "SESSIONS_ARTIFACT",
    "STATUS_ARTIFACT",
    "TRIAL_VERSION",
    "build_active_discovery_trial",
    "build_and_write_active_discovery_trial",
    "validate_active_discovery_trial",
]
