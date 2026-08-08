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
    sha256_json,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_portfolio_risk_engine import (
    POLICY_VERSION as PORTFOLIO_POLICY_VERSION,
)
from orchestrator.qadam_wave_b_common import (
    parse_timestamp,
    safe_float,
    stable_id,
)

SCHEMA_VERSION = "qadam_active_discovery_trial.v2"
TRIAL_VERSION = (
    "qadam-active-discovery-trial.2-evidence-adaptive-five-market-sessions"
)
EVIDENCE_FIT_CONTRACT_VERSION = "qadam-evidence-fit-active-discovery.1"
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
FUNNEL_ARTIFACT = "qadam_active_discovery_conversion_funnel.jsonl"
ELIGIBLE_DAYS_ARTIFACT = "qadam_active_discovery_eligible_days.jsonl"
ROOT_CAUSES_ARTIFACT = "qadam_active_discovery_root_causes.jsonl"
CERTIFICATION_ARTIFACT = "qadam_active_discovery_trial_certification.json"
POLICY_ARTIFACT = "qadam_experimental_paper_policy.json"
POLICY_AMENDMENT_ARTIFACT = "qadam_experimental_policy_amendment.json"

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
EVENT_TRIGGERS_ARTIFACT = "qadam_current_event_triggers.jsonl"
REGIME_TRIGGERS_ARTIFACT = "qadam_current_regime_observations.jsonl"
DISLOCATION_TRIGGERS_ARTIFACT = "qadam_current_market_dislocations.jsonl"

PRIMARY_ROOT_CAUSES = {
    "market_closed",
    "no_real_trigger",
    "source_outage",
    "mapping_defect",
    "evidence_conversion_defect",
    "akber_hold",
    "akber_veto",
    "risk_veto",
    "duplicate_exposure",
    "route_failure",
}

PIPELINE_SERVICES = (
    "pattern_scoring",
    "research_evidence_validation",
    "akber_review",
    "forward_shadow",
    "portfolio_router_review",
)


def _artifact_hash(path: Path) -> str | None:
    return file_sha256(path) if path.is_file() else None


def _policy_binding(runtime: Path) -> dict[str, Any]:
    policy = read_json(runtime / POLICY_ARTIFACT)
    amendment = read_json(runtime / POLICY_AMENDMENT_ARTIFACT)
    policy_contract = {
        "policy_version": policy.get("policy_version"),
        "discovery_micro_admission": policy.get("discovery_micro_admission"),
        "risk": policy.get("risk"),
        "live_capital_enabled": policy.get("live_capital_enabled"),
    }
    return {
        "policy_version": policy.get("policy_version"),
        "policy_contract_digest": sha256_json(policy_contract),
        "amendment_id": amendment.get("amendment_id"),
        "amendment_generated_at": amendment.get("generated_at"),
        "amendment_to_policy_version": amendment.get("to_policy_version"),
        "operator_approved": amendment.get("operator_approved") is True,
    }


def _new_contract(
    runtime: Path,
    generated_at: str,
    previous_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    trial_id = stable_id("active-discovery-trial", generated_at, TRIAL_VERSION)
    previous_contract = previous_contract or {}
    policy_binding = _policy_binding(runtime)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_active_discovery_trial_contract",
        "trial_id": trial_id,
        "trial_version": TRIAL_VERSION,
        "evidence_fit_contract_version": EVIDENCE_FIT_CONTRACT_VERSION,
        "supersedes_trial_id": previous_contract.get("trial_id"),
        "supersedes_trial_version": previous_contract.get("trial_version"),
        "activated_at": generated_at,
        "policy_binding": policy_binding,
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
        "evidence_fit_bindings": {
            "akber_policy_version": "qadam-akber-evidence-fit.1",
            "risk_router_alignment_version": "qadam-risk-router-evidence-fit.1",
            "current_trigger_contract_required": True,
            "one_primary_root_cause_required": True,
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
    current_binding = _policy_binding(runtime)
    if (
        contract.get("trial_version") == TRIAL_VERSION
        and contract.get("policy_binding") == current_binding
        and current_binding.get("policy_version") == EXPERIMENTAL_POLICY_VERSION
        and current_binding.get("amendment_to_policy_version")
        == EXPERIMENTAL_POLICY_VERSION
        and current_binding.get("operator_approved") is True
    ):
        migrated = dict(contract)
        migrated["evidence_fit_contract_version"] = EVIDENCE_FIT_CONTRACT_VERSION
        migrated["evidence_fit_bindings"] = {
            "akber_policy_version": "qadam-akber-evidence-fit.1",
            "risk_router_alignment_version": "qadam-risk-router-evidence-fit.1",
            "current_trigger_contract_required": True,
            "one_primary_root_cause_required": True,
        }
        if migrated != contract:
            AtomicArtifactStore(runtime).write_json(CONTRACT_ARTIFACT, migrated)
        return migrated
    contract = _new_contract(runtime, generated_at, contract)
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


def _current_trigger_index(runtime: Path) -> dict[str, list[dict[str, Any]]]:
    """Index current real triggers by affected instrument without inventing history."""

    indexed: dict[str, list[dict[str, Any]]] = {}
    for artifact, state_field, active_values in (
        (EVENT_TRIGGERS_ARTIFACT, "trigger_state", {"active"}),
        (REGIME_TRIGGERS_ARTIFACT, "regime_state", {"active", "active_long", "active_short"}),
        (DISLOCATION_TRIGGERS_ARTIFACT, "dislocation_state", {"active"}),
    ):
        for trigger in read_jsonl(runtime / artifact):
            if trigger.get("sample_or_fixture") is True:
                continue
            state = str(trigger.get(state_field) or "unknown")
            instruments = trigger.get("affected_instruments")
            if not isinstance(instruments, list):
                instruments = []
                strategy = str(trigger.get("strategy_family_id") or "")
                if strategy == "silver_macro_liquidity_stress":
                    instruments = ["SIL", "SLV"]
                elif strategy == "power_scarcity_congestion":
                    instruments = ["CEG", "VST", "NRG", "TLN", "XLU", "GRID", "UNG"]
            normalized = {
                "trigger_id": trigger.get("trigger_id")
                or trigger.get("regime_id")
                or trigger.get("dislocation_id"),
                "strategy_family_id": trigger.get("strategy_family_id"),
                "state": "active" if state in active_values else "inactive",
                "raw_state": state,
                "available_at": trigger.get("available_at"),
            }
            for instrument in instruments:
                indexed.setdefault(str(instrument), []).append(normalized)
    return indexed


def _market_session_actionable(runtime: Path) -> bool:
    mirror = read_json(runtime / MIRROR_ARTIFACT)
    clock = mirror.get("market_clock") if isinstance(mirror.get("market_clock"), dict) else {}
    return clock.get("is_open") is True


def _primary_root_cause(row: dict[str, Any]) -> str:
    """Classify one upstream cause for a no-trade evaluation."""

    if row.get("market_session_actionable") is False:
        return "market_closed"
    router_state = str(row.get("router_state") or "")
    router_root = str(row.get("router_primary_root_cause") or "")
    if "duplicate" in router_root:
        return "duplicate_exposure"
    if router_state in {"blocked-safety-boundary"} or "route" in router_root:
        return "route_failure"
    akber = str(row.get("akber_decision") or "")
    if akber == "veto":
        return "akber_veto"
    if akber == "hold_missing_context":
        return "akber_hold"
    if akber == "watchlist_inactive_trigger":
        return "no_real_trigger"
    if row.get("risk_state") == "rejected":
        return "risk_veto"
    if row.get("current_trigger_state") != "active":
        return "no_real_trigger"
    blockers = [str(value) for value in row.get("blockers", [])]
    if any("source" in value and any(term in value for term in ("stale", "unavailable", "outage")) for value in blockers):
        return "source_outage"
    if any(
        term in value
        for value in blockers
        for term in ("unsupported_strategy_mapping", "redundant_instrument", "instrument_mapping")
    ):
        return "mapping_defect"
    if row.get("hypothesis_id") is None or blockers:
        return "evidence_conversion_defect"
    if router_state in {"reject", "repair-requested", "hold"}:
        return "route_failure" if router_state == "blocked-safety-boundary" else "evidence_conversion_defect"
    return "no_real_trigger"


def _evaluation_rows(
    runtime: Path,
    session_date: str,
    generated_at: str,
    *,
    trial_id: str,
) -> list[dict[str, Any]]:
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
    trigger_index = _current_trigger_index(runtime)
    session_actionable = _market_session_actionable(runtime)
    rows: list[dict[str, Any]] = []
    for instrument in sorted(best):
        score = best[instrument]
        score_id = str(score.get("score_id") or "")
        hypothesis = hypotheses.get(score_id, {})
        akber_result = akber.get(score_id, {})
        risk = risk_proposals.get(score_id) or risk_rejections.get(score_id) or {}
        router = routers.get(score_id, {})
        triggers = trigger_index.get(instrument, [])
        active_triggers = [row for row in triggers if row.get("state") == "active"]
        trigger_state = (
            "active" if active_triggers else "inactive" if triggers else "not_observed"
        )
        hypothesis_id = str(hypothesis.get("hypothesis_id") or "")
        shadow = shadows.get(hypothesis_id, {})
        akber_stage_states = {
            str(stage.get("stage") or ""): str(stage.get("state") or "")
            for stage in akber_result.get("stages", [])
            if isinstance(stage, dict)
        }
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
        row = {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_active_discovery_evaluation",
                "trial_id": trial_id,
                "trial_version": TRIAL_VERSION,
                "evaluation_id": stable_id(
                    "active-discovery-evaluation", trial_id, session_date, instrument
                ),
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
                "router_primary_root_cause": router.get("primary_root_cause"),
                "current_trigger_state": trigger_state,
                "current_trigger_ids": [
                    trigger.get("trigger_id") for trigger in active_triggers if trigger.get("trigger_id")
                ],
                "market_session_actionable": session_actionable,
                "execution_context_actionable": bool(
                    session_actionable
                    and akber_stage_states.get("execution") in {"passed", "pass"}
                ),
                "blockers": unique_errors(str(value) for value in blockers if value),
                "trigger_origin": "scheduled_autonomous_research",
                "candidate_created": False,
                "order_created": False,
                "broker_write_count": 0,
                "proof_credit_count": 0,
                "live_capital_enabled": False,
                "authority": authority_flags(),
            }
        if row["router_state"] in {
            "experimental_paper_review_candidate",
            "validated_paper_review_candidate",
        }:
            row["primary_root_cause"] = None
            row["no_trade_outcome_accounted_for"] = False
        else:
            row["primary_root_cause"] = _primary_root_cause(row)
            row["no_trade_outcome_accounted_for"] = True
        rows.append(row)
    return rows


def _decorate_legacy_evaluation(row: dict[str, Any]) -> dict[str, Any]:
    """Preserve older factual rows while marking unrecorded EF-7 context honestly."""

    decorated = dict(row)
    decorated.setdefault("current_trigger_state", "not_recorded_pre_ef7")
    decorated.setdefault("current_trigger_ids", [])
    decorated.setdefault("market_session_actionable", None)
    if decorated.get("router_state") in {
        "experimental_paper_review_candidate",
        "validated_paper_review_candidate",
    }:
        decorated.setdefault("primary_root_cause", None)
        decorated.setdefault("no_trade_outcome_accounted_for", False)
    else:
        decorated.setdefault("primary_root_cause", _primary_root_cause(decorated))
        decorated.setdefault("no_trade_outcome_accounted_for", True)
    return decorated


def _merge_evaluations(
    previous: list[dict[str, Any]], current: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    merged = {
        str(row.get("evaluation_id") or ""): _decorate_legacy_evaluation(row)
        for row in previous
        if row.get("evaluation_id")
    }
    for row in current:
        prior = merged.get(str(row["evaluation_id"]), {})
        if prior.get("first_evaluated_at"):
            row["first_evaluated_at"] = prior["first_evaluated_at"]
        merged[str(row["evaluation_id"])] = row
    return sorted(
        (_decorate_legacy_evaluation(row) for row in merged.values()),
        key=lambda row: (str(row.get("session_date")), str(row.get("instrument"))),
    )


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
    trial_id: str,
) -> dict[str, Any]:
    relevant = [
        row
        for row in rows
        if row.get("session_date") == session_date and row.get("trial_id") == trial_id
    ]
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
        "trial_id": trial_id,
        "trial_version": TRIAL_VERSION,
        "session_id": stable_id("active-discovery-session", trial_id, session_date),
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
        "active_current_trigger_count": sum(
            row.get("current_trigger_state") == "active" for row in relevant
        ),
        "actionable_execution_context_count": sum(
            row.get("execution_context_actionable") is True for row in relevant
        ),
        "account_level_stop_active": any(
            row.get("primary_root_cause") in {"risk_veto", "duplicate_exposure"}
            and any(
                term in str(blocker)
                for blocker in row.get("blockers", [])
                for term in ("daily_loss", "drawdown", "concurrent_position_limit")
            )
            for row in relevant
        ),
        "operator_service_healthy_at_observation": generation.get("consistent") is True,
        "generation_consistency": generation,
        "paper_order_origin_counts_since_trial_start": dict(sorted(origins.items())),
        "scheduled_autonomous_paper_order_count_since_trial_start": origins.get("scheduled_autonomous", 0),
        "trade_quota": None,
        "forced_trade_allowed": False,
        "live_capital_enabled": False,
        "proof_credit_count": 0,
        "authority": authority_flags(),
    }


def _conversion_funnel_rows(
    sessions: list[dict[str, Any]], evaluations: list[dict[str, Any]], *, trial_id: str
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for session in sessions:
        if session.get("trial_id") != trial_id:
            continue
        session_rows = [
            row
            for row in evaluations
            if row.get("trial_id") == trial_id
            and row.get("session_date") == session.get("session_date")
        ]
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_active_discovery_conversion_funnel",
                "trial_id": trial_id,
                "session_id": session.get("session_id"),
                "session_date": session.get("session_date"),
                "generated_at": session.get("generated_at"),
                "instrument_evaluations": len(session_rows),
                "shortlisted": sum(row.get("shortlisted") is True for row in session_rows),
                "hypotheses": sum(bool(row.get("hypothesis_id")) for row in session_rows),
                "active_triggers": sum(
                    row.get("current_trigger_state") == "active" for row in session_rows
                ),
                "akber_reviews": sum(
                    row.get("akber_decision") != "not_reached" for row in session_rows
                ),
                "akber_passes": sum(row.get("akber_decision") == "pass" for row in session_rows),
                "shadow_snapshots": sum(
                    row.get("shadow_state") != "not_reached" for row in session_rows
                ),
                "risk_proposals": sum(row.get("risk_state") == "proposal" for row in session_rows),
                "router_reviews": sum(
                    row.get("router_state") != "not_reached" for row in session_rows
                ),
                "paper_handoffs": sum(
                    row.get("router_state")
                    in {
                        "experimental_paper_review_candidate",
                        "validated_paper_review_candidate",
                    }
                    for row in session_rows
                ),
                "paper_order_created_by_trial_module": 0,
                "authority": authority_flags(),
            }
        )
    return rows


def _eligible_day_rows(
    sessions: list[dict[str, Any]], evaluations: list[dict[str, Any]], *, trial_id: str
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for session in sessions:
        if session.get("trial_id") != trial_id:
            continue
        session_rows = [
            row
            for row in evaluations
            if row.get("trial_id") == trial_id
            and row.get("session_date") == session.get("session_date")
        ]
        active_trigger = any(
            row.get("current_trigger_state") == "active" for row in session_rows
        )
        actionable_execution = any(
            row.get("execution_context_actionable") is True for row in session_rows
        )
        healthy = bool(
            session.get("operator_service_healthy_at_observation") is True
            or session.get("generation_consistency", {}).get("consistent") is True
        )
        account_stop = session.get("account_level_stop_active") is True
        reasons: list[str] = []
        if not healthy:
            reasons.append("operator_or_generation_health_not_clean")
        if not active_trigger:
            reasons.append("no_real_current_trigger_recorded")
        if not actionable_execution:
            reasons.append("no_actionable_execution_context_recorded")
        if account_stop:
            reasons.append("account_level_stop_active")
        eligible = bool(healthy and active_trigger and actionable_execution and not account_stop)
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_active_discovery_eligible_day",
                "trial_id": trial_id,
                "session_id": session.get("session_id"),
                "session_date": session.get("session_date"),
                "generated_at": session.get("generated_at"),
                "real_market_session_observed": session.get("real_market_session_observed") is True,
                "operator_and_pipeline_healthy": healthy,
                "real_current_trigger_observed": active_trigger,
                "actionable_execution_context_observed": actionable_execution,
                "account_level_stop_active": account_stop,
                "eligible_for_conversion_measurement": eligible,
                "ineligible_reasons": reasons,
                "backfilled": False,
                "simulated_elapsed_time": False,
                "paper_order_created": False,
                "authority": authority_flags(),
            }
        )
    return rows


def _root_cause_rows(
    evaluations: list[dict[str, Any]], *, trial_id: str
) -> list[dict[str, Any]]:
    return [
        {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_active_discovery_root_cause",
            "trial_id": trial_id,
            "evaluation_id": row.get("evaluation_id"),
            "session_date": row.get("session_date"),
            "instrument": row.get("instrument"),
            "primary_root_cause": row.get("primary_root_cause"),
            "propagated_blockers": row.get("blockers", []),
            "exactly_one_primary_root_cause": row.get("primary_root_cause")
            in PRIMARY_ROOT_CAUSES,
            "paper_order_created": False,
            "authority": authority_flags(),
        }
        for row in evaluations
        if row.get("trial_id") == trial_id
        and row.get("no_trade_outcome_accounted_for") is True
    ]


def _trial_certification(
    status: dict[str, Any], eligible_days: list[dict[str, Any]], *, errors: list[str]
) -> dict[str, Any]:
    eligible_count = sum(
        row.get("eligible_for_conversion_measurement") is True for row in eligible_days
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_active_discovery_trial_certification",
        "phase_id": "EF-7",
        "generated_at": status.get("generated_at"),
        "implementation_status": "passed" if not errors else "blocked",
        "implementation_ready": not errors,
        "empirical_trial_status": (
            "complete" if eligible_count >= MARKET_SESSION_TARGET else "collecting_real_eligible_days"
        ),
        "real_market_sessions_observed": status.get("market_sessions_observed"),
        "eligible_market_days_observed": eligible_count,
        "eligible_market_day_target": MARKET_SESSION_TARGET,
        "trial_complete": eligible_count >= MARKET_SESSION_TARGET,
        "no_simulated_time": True,
        "no_trade_quota": True,
        "paper_order_created_by_trial_module": 0,
        "broker_write_count": 0,
        "proof_credit_count": 0,
        "live_capital_enabled": False,
        "validation_errors": errors,
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
    trial_id = str(contract.get("trial_id") or "")
    session_date = _market_session_date(runtime, str(contract.get("activated_at") or generated))
    evaluations = read_jsonl(runtime / EVALUATIONS_ARTIFACT)
    generation = _generation_consistency(runtime)
    if session_date:
        evaluations = _merge_evaluations(
            evaluations,
            _evaluation_rows(
                runtime, session_date, generated, trial_id=trial_id
            ),
        )
    sessions_by_id = {
        str(row.get("session_id") or ""): row
        for row in read_jsonl(runtime / SESSIONS_ARTIFACT)
        if row.get("session_id")
    }
    if session_date:
        session = _session_record(
            session_date,
            evaluations,
            generation,
            runtime,
            generated,
            str(contract.get("activated_at") or generated),
            trial_id,
        )
        sessions_by_id[str(session["session_id"])] = session
    sessions = sorted(
        sessions_by_id.values(),
        key=lambda row: (str(row.get("trial_id")), str(row.get("session_date"))),
    )
    current_sessions = [row for row in sessions if row.get("trial_id") == trial_id]
    counted_sessions = current_sessions
    eligible_days = _eligible_day_rows(
        current_sessions, evaluations, trial_id=trial_id
    )
    eligible_session_count = sum(
        row.get("eligible_for_conversion_measurement") is True
        for row in eligible_days
    )
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
    session_target_reached = eligible_session_count >= MARKET_SESSION_TARGET
    eligible_session_ids = {
        str(row.get("session_id") or "")
        for row in eligible_days
        if row.get("eligible_for_conversion_measurement") is True
    }
    eligible_sessions = [
        row
        for row in counted_sessions
        if str(row.get("session_id") or "") in eligible_session_ids
    ]
    operational_integrity = bool(
        session_target_reached
        and all(
            row.get("instrument_evaluation_count") == EXPECTED_INSTRUMENT_COUNT
            for row in eligible_sessions[:MARKET_SESSION_TARGET]
        )
        and all(
            row.get("generation_consistency", {}).get("consistent") is True
            for row in eligible_sessions[:MARKET_SESSION_TARGET]
        )
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

    current_preview = _evaluation_rows(
        runtime, session_date or "preview", generated, trial_id=trial_id
    )
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
        "eligible_market_days_observed": eligible_session_count,
        "eligible_market_days_remaining": max(
            MARKET_SESSION_TARGET - eligible_session_count, 0
        ),
        "market_sessions_remaining": max(
            MARKET_SESSION_TARGET - eligible_session_count, 0
        ),
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
            "eligible_market_day_count": eligible_session_count,
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
        "headline": (
            f"{eligible_session_count} of {MARKET_SESSION_TARGET} eligible market days; "
            f"{len(counted_sessions)} real sessions observed"
        ),
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
    if contract.get("evidence_fit_contract_version") != EVIDENCE_FIT_CONTRACT_VERSION:
        errors.append("active_discovery_trial_evidence_fit_contract_missing")
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
    binding = contract.get("policy_binding")
    binding = binding if isinstance(binding, dict) else {}
    if binding.get("policy_version") != EXPERIMENTAL_POLICY_VERSION:
        errors.append("active_discovery_trial_policy_binding_version_invalid")
    if binding.get("amendment_to_policy_version") != EXPERIMENTAL_POLICY_VERSION:
        errors.append("active_discovery_trial_amendment_binding_version_invalid")
    if binding.get("operator_approved") is not True:
        errors.append("active_discovery_trial_amendment_not_operator_approved")
    if not binding.get("policy_contract_digest") or not binding.get("amendment_id"):
        errors.append("active_discovery_trial_policy_binding_incomplete")
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
        if row.get("no_trade_outcome_accounted_for") is True and row.get(
            "primary_root_cause"
        ) not in PRIMARY_ROOT_CAUSES:
            errors.append(
                f"active_discovery_primary_root_cause_invalid:{row.get('evaluation_id')}"
            )
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
    trial_id = str(status.get("trial_id") or "")
    funnel = _conversion_funnel_rows(sessions, evaluations, trial_id=trial_id)
    eligible_days = _eligible_day_rows(sessions, evaluations, trial_id=trial_id)
    root_causes = _root_cause_rows(evaluations, trial_id=trial_id)
    if any(row.get("exactly_one_primary_root_cause") is not True for row in root_causes):
        errors.append("active_discovery_root_cause_cardinality_invalid")
    if any(row.get("simulated_elapsed_time") is not False for row in eligible_days):
        errors.append("active_discovery_eligible_day_simulated")
    if any(row.get("paper_order_created") is not False for row in eligible_days):
        errors.append("active_discovery_eligible_day_created_order")
    errors = unique_errors(errors)
    certification = _trial_certification(status, eligible_days, errors=errors)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_active_discovery_trial_checks",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "implementation_ready": not errors,
        "trial_state": status.get("status"),
        "market_sessions_observed": status.get("market_sessions_observed"),
        "eligible_market_days_observed": status.get("eligible_market_days_observed"),
        "empirical_trial_complete": certification.get("trial_complete"),
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
    store.write_jsonl(FUNNEL_ARTIFACT, funnel)
    store.write_jsonl(ELIGIBLE_DAYS_ARTIFACT, eligible_days)
    store.write_jsonl(ROOT_CAUSES_ARTIFACT, root_causes)
    store.write_json(CERTIFICATION_ARTIFACT, certification)
    store.write_json(CHECK_ARTIFACT, checks)
    return status, checks, errors


__all__ = [
    "CHECK_ARTIFACT",
    "CERTIFICATION_ARTIFACT",
    "CONTRACT_ARTIFACT",
    "DASHBOARD_ARTIFACT",
    "EVALUATIONS_ARTIFACT",
    "ELIGIBLE_DAYS_ARTIFACT",
    "FUNNEL_ARTIFACT",
    "MARKET_SESSION_TARGET",
    "PRIMARY_ROOT_CAUSES",
    "ROOT_CAUSES_ARTIFACT",
    "SESSIONS_ARTIFACT",
    "STATUS_ARTIFACT",
    "TRIAL_VERSION",
    "build_active_discovery_trial",
    "build_and_write_active_discovery_trial",
    "validate_active_discovery_trial",
]
