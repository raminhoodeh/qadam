"""Disk-backed tradeability journeys, reachability, and contract defect handling."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_akber_filter_v3 import build_akber_input, evaluate_akber_input
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_decision_evidence_packets import (
    build_decision_evidence_packets_from_inputs,
    validate_decision_evidence_packets,
)
from orchestrator.qadam_forward_shadow import freeze_shadow_decision
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    append_jsonl_durable,
    authority_flags,
    git_snapshot,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_json,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_portfolio_risk_engine import (
    _setup_from_lineage,
    default_portfolio_policy,
    evaluate_position_size,
)
from orchestrator.qadam_router_v3_paperops import (
    _assemble_setup,
    build_handoff,
    build_handoff_consumption_state,
    route_setup,
    validate_handoff_consumption_state,
)
from orchestrator.qadam_tradeability_envelope import (
    TradeabilityEnvelope,
    compile_tradeability_envelope,
    envelope_to_hypothesis_projection,
)

SCHEMA_VERSION = "qadam.tradeability-reliability.v1"
FIXTURE_PATH = (
    ROOT
    / "tests"
    / "fixtures"
    / "qadam_tradeability_journeys"
    / "provider_boundary.json"
)

GOLDEN_ARTIFACT = "qadam_tradeability_golden_journeys.json"
GOLDEN_CHECKS_ARTIFACT = "qadam_tradeability_golden_journey_checks.json"
REACHABILITY_ARTIFACT = "qadam_tradeability_reachability_canary.json"
REACHABILITY_HISTORY_ARTIFACT = "qadam_tradeability_reachability_history.jsonl"
REACHABILITY_CHECKS_ARTIFACT = "qadam_tradeability_reachability_checks.json"
SOURCE_DEFECTS_ARTIFACT = "qadam_tradeability_contract_defects.jsonl"
DEFECTS_ARTIFACT = "qadam_contract_defects.jsonl"
REPAIR_REQUESTS_ARTIFACT = "qadam_contract_repair_requests.jsonl"
DEFECT_SUMMARY_ARTIFACT = "qadam_contract_defect_summary.json"
SELF_HEALING_CHECKS_ARTIFACT = "qadam_contract_self_healing_checks.json"

STRUCTURAL_DEFECT_CLASSES = {
    "contract_schema_drift",
    "producer_field_omission",
    "consumer_undocumented_requirement",
    "mixed_generation",
    "prompt_compile_failure",
    "critic_contract_failure",
    "capability_matrix_mismatch",
}
SAFE_RETRY_CLASSES = {
    "transient_provider_read",
    "lock_contention",
    "deterministic_incomplete_write",
}
JOURNEY_EXPECTATIONS = {
    "valid_pass": "accepted_for_guarded_paperops_sequence",
    "missing_context": "hold_missing_context",
    "inactive_trigger": "watchlist_inactive_trigger",
    "adverse_evidence": "veto",
    "duplicate_exposure": "duplicate_rejected",
    "closed_market": "hold_missing_context",
    "stale_provider": "hold_missing_context",
    "direction_unresolved": "packet_rejected",
    "parse_failure": "packet_rejected",
    "mixed_generation": "envelope_rejected",
}


def _load_fixture(namespace: str = "golden-discovery") -> dict[str, Any]:
    fixture = read_json(FIXTURE_PATH)
    if not fixture:
        raise ValueError("tradeability_golden_fixture_missing")
    rendered = json.dumps(fixture).replace("golden-discovery", namespace)
    loaded = json.loads(rendered)
    if not isinstance(loaded, dict):
        raise ValueError("tradeability_golden_fixture_invalid")
    return loaded


def _mutate_fixture(fixture: dict[str, Any], variant: str) -> None:
    hypothesis = fixture["hypothesis"]
    artifacts = fixture["decision_artifacts"]
    packet = artifacts["market_context"]["recent_packets"][0]
    price = packet["price_volume_context"]["records"][0]
    if variant == "missing_context":
        price.pop("volume_ratio", None)
        packet["technical_context"] = {"status": "unavailable", "records": []}
        artifacts["signal_integrity_reviews"] = []
        artifacts["nonlinear_comparisons"] = []
    elif variant == "inactive_trigger":
        fixture["trigger"]["trigger_state"] = "inactive"
    elif variant == "adverse_evidence":
        hypothesis["expected_edge_range"]["net_expectancy"] = -0.001
        hypothesis["risk_concept"]["expected_reward_to_risk"] = 0.5
    elif variant == "closed_market":
        price["market_state"] = "closed"
        price["session_state"] = "closed"
    elif variant == "stale_provider":
        packet["generated_at"] = "2026-08-07T00:00:00+00:00"
        packet["price_volume_context"]["status"] = "stale"
        price["market_state"] = "stale"
        artifacts["tradingview_status"]["truthful_state"] = "stale"
        artifacts["tradingview_status"]["live_calls_enabled"] = False
        artifacts["tradingview_status"]["provider_backed_record_count"] = 0
        artifacts["alpaca_mirror"]["status"] = "stale"
        artifacts["alpaca_mirror"]["snapshot"]["observed_at"] = (
            "2026-08-07T00:00:00+00:00"
        )
    elif variant == "direction_unresolved":
        fixture["direction_resolution"] = None
    elif variant == "parse_failure":
        hypothesis["hypothesis_id"] = None


def _write_internal_artifacts(
    root: Path,
    *,
    packet_state: dict[str, Any],
    envelope: TradeabilityEnvelope | None = None,
    projection: dict[str, Any] | None = None,
    akber_input: dict[str, Any] | None = None,
    akber_result: dict[str, Any] | None = None,
    shadow: dict[str, Any] | None = None,
    risk_proposal: dict[str, Any] | None = None,
    router_decision: dict[str, Any] | None = None,
    handoff: dict[str, Any] | None = None,
    consumption: dict[str, Any] | None = None,
) -> dict[str, str]:
    store = AtomicArtifactStore(root)
    records: dict[str, Any] = {
        "qadam_decision_evidence_packets.jsonl": packet_state.get("packets", []),
        "qadam_decision_evidence_packet_rejections.jsonl": packet_state.get(
            "rejections", []
        ),
        "qadam_generation_integrity_checks.json": packet_state.get("integrity", {}),
    }
    if envelope is not None:
        records["qadam_tradeability_envelopes.jsonl"] = [
            envelope.model_dump(mode="json")
        ]
    if projection is not None:
        records["qadam_strategy_hypotheses_v3.jsonl"] = [projection]
    if akber_input is not None:
        records["qadam_akber_filter_v3_inputs.jsonl"] = [akber_input]
    if akber_result is not None:
        records["qadam_akber_filter_v3_results.jsonl"] = [akber_result]
    if shadow is not None:
        records["qadam_forward_shadow_decisions.jsonl"] = [shadow]
    if risk_proposal is not None:
        records["qadam_position_size_proposals.jsonl"] = [risk_proposal]
    if router_decision is not None:
        records["qadam_router_v3_decisions.jsonl"] = [router_decision]
    if handoff is not None:
        records["qadam_paperops_handoff_v3.jsonl"] = [handoff]
    if consumption is not None:
        records["qadam_paperops_handoff_v3_consumption.json"] = consumption
    hashes: dict[str, str] = {}
    for name, payload in records.items():
        if name.endswith(".jsonl"):
            store.write_jsonl(name, payload if isinstance(payload, list) else [payload])
        else:
            store.write_json(name, payload)
        hashes[name] = sha256_json(payload)
    return hashes


def _front_half(
    fixture: dict[str, Any],
    variant: str,
    root: Path,
) -> dict[str, Any]:
    generated_at = str(fixture["generated_at"])
    hypothesis = fixture["hypothesis"]
    resolution = fixture.get("direction_resolution")
    packet_state = build_decision_evidence_packets_from_inputs(
        [hypothesis],
        [resolution] if isinstance(resolution, dict) else [],
        [fixture["trigger"]],
        [],
        [],
        fixture["decision_artifacts"],
        generated_at=generated_at,
    )
    packet_errors = validate_decision_evidence_packets(packet_state)
    if packet_errors or not packet_state.get("packets"):
        _write_internal_artifacts(root, packet_state=packet_state)
        return {
            "stage": "decision_packet",
            "actual": "packet_rejected",
            "packet_errors": packet_errors,
            "rejections": packet_state.get("rejections", []),
        }
    packet = deepcopy(packet_state["packets"][0])
    if variant == "mixed_generation":
        packet["mixed_generation_join"] = True
    try:
        envelope = compile_tradeability_envelope(
            hypothesis,
            packet,
            source_draft_ref=f"fixture:{variant}",
        )
    except Exception as exc:
        _write_internal_artifacts(root, packet_state=packet_state)
        return {
            "stage": "tradeability_envelope",
            "actual": "envelope_rejected",
            "error_class": exc.__class__.__name__,
            "error": str(exc),
        }
    projection = envelope_to_hypothesis_projection(envelope, hypothesis)
    akber_input = build_akber_input(
        projection,
        packet["akber_context"],
        generated_at=generated_at,
        strict_provenance=True,
    )
    akber_result = evaluate_akber_input(akber_input)
    hashes = _write_internal_artifacts(
        root,
        packet_state=packet_state,
        envelope=envelope,
        projection=projection,
        akber_input=akber_input,
        akber_result=akber_result,
    )
    return {
        "stage": "akber",
        "actual": akber_result["decision"],
        "packet_state": packet_state,
        "envelope": envelope,
        "projection": projection,
        "akber_input": akber_input,
        "akber_result": akber_result,
        "artifact_hashes": hashes,
    }


def _valid_full_journey(fixture: dict[str, Any], root: Path) -> dict[str, Any]:
    front = _front_half(fixture, "valid_pass", root)
    if front.get("actual") != "pass":
        return front
    generated_at = str(fixture["generated_at"])
    hypothesis = front["projection"]
    akber_input = front["akber_input"]
    akber_result = front["akber_result"]
    shadow = freeze_shadow_decision(
        hypothesis,
        akber_result,
        decision_at=generated_at,
        entry_observation=fixture["entry_observation"],
        akber_input=akber_input,
        require_entry_observation=True,
    )
    policy = default_portfolio_policy(generated_at)
    risk_setup = _setup_from_lineage(
        hypothesis,
        {},
        akber_input,
        akber_result,
        [shadow],
        [],
        {},
        {"instruments": [{"symbol": "SMH", "market_family": "technology"}]},
        policy,
        generated_at=generated_at,
    )
    portfolio = {
        "equity": 100000.0,
        "positions": [],
        "daily_loss_pct": 0.0,
        "trailing_drawdown_pct": 0.0,
        "new_notional_today": 0.0,
        "daily_new_notional_basis": "complete",
        "open_order_count": 0,
        "open_discovery_micro_exposure_count": 0,
        "open_discovery_micro_symbols": [],
        "open_discovery_micro_clusters": [],
        "tail_loss_estimate": 0.0,
    }
    risk = evaluate_position_size(
        risk_setup, portfolio, policy, generated_at=generated_at
    )
    if risk.get("proposal") is None:
        return {
            "stage": "risk",
            "actual": "risk_rejected",
            "rejection": risk.get("rejection"),
        }
    proposal = risk["proposal"]
    release = {
        "experimental_paper_release_effective": True,
        "experimental_policy_operator_approved": True,
        "experimental_risk_policy_operator_approved": True,
        "risk_policy_version": proposal["policy_version"],
    }
    setup = _assemble_setup(
        hypothesis,
        edge={},
        score={},
        akber=akber_result,
        shadow_decision=shadow,
        shadow_outcome={},
        shadow_promotion={},
        risk_proposal=proposal,
        risk_state={
            "drawdown_context_complete": True,
            "daily_loss_pct": 0.0,
            "trailing_drawdown_pct": 0.0,
        },
        qctrl={
            "status": "consultation_recorded",
            "head_of_quant_note": {"latest_oracle_recommendation": "pass"},
        },
        approvals={},
        release=release,
        epoch={"paper_epoch_id": "canary-paper-epoch"},
        open_symbols=set(),
    )
    decision = route_setup(setup, release, generated_at=generated_at)
    if decision.get("paperops_handoff_allowed") is not True:
        return {"stage": "router", "actual": decision.get("final_state"), "decision": decision}
    handoff = build_handoff(decision, setup)
    consumption = build_handoff_consumption_state(
        [handoff],
        [decision],
        release,
        {"status": "released", "paperops_watch_only_mode": False},
        generated_at=generated_at,
        active_epoch_id="canary-paper-epoch",
    )
    consumption_errors = validate_handoff_consumption_state(consumption)
    hashes = _write_internal_artifacts(
        root,
        packet_state=front["packet_state"],
        envelope=front["envelope"],
        projection=hypothesis,
        akber_input=akber_input,
        akber_result=akber_result,
        shadow=shadow,
        risk_proposal=proposal,
        router_decision=decision,
        handoff=handoff,
        consumption=consumption,
    )
    actual = (
        "accepted_for_guarded_paperops_sequence"
        if consumption.get("accepted_handoff_count") == 1 and not consumption_errors
        else "handoff_rejected"
    )
    return {
        "stage": "broker_disabled_paperops_handoff",
        "actual": actual,
        "decision_state": decision.get("final_state"),
        "risk_proposed_notional_usd": proposal.get("proposed_notional"),
        "accepted_handoff_count": consumption.get("accepted_handoff_count"),
        "consumption_errors": consumption_errors,
        "artifact_hashes": hashes,
        "decision": decision,
        "handoff": handoff,
        "consumption": consumption,
    }


def _run_journey(name: str, namespace: str) -> dict[str, Any]:
    fixture = _load_fixture(namespace)
    if name not in {"valid_pass", "duplicate_exposure"}:
        _mutate_fixture(fixture, name)
    with TemporaryDirectory(prefix=f"qadam-{name}-") as temporary:
        root = Path(temporary)
        result = _valid_full_journey(fixture, root) if name in {
            "valid_pass",
            "duplicate_exposure",
        } else _front_half(fixture, name, root)
        if name == "duplicate_exposure" and result.get("actual") == (
            "accepted_for_guarded_paperops_sequence"
        ):
            handoff = result["handoff"]
            decision = result["decision"]
            duplicate = build_handoff_consumption_state(
                [handoff, handoff],
                [decision],
                {
                    "experimental_paper_release_effective": True,
                    "experimental_policy_operator_approved": True,
                    "experimental_risk_policy_operator_approved": True,
                },
                {"status": "released", "paperops_watch_only_mode": False},
                generated_at=str(fixture["generated_at"]),
                active_epoch_id="canary-paper-epoch",
            )
            reasons = {
                reason
                for rejection in duplicate.get("rejections", [])
                for reason in rejection.get("rejection_reasons", [])
            }
            result = {
                "stage": "paperops_handoff_deduplication",
                "actual": "duplicate_rejected"
                if {
                    "duplicate_handoff_id_in_batch",
                    "duplicate_idempotency_key_in_batch",
                }.issubset(reasons)
                else "duplicate_not_rejected",
                "rejection_reasons": sorted(reasons),
            }
    expected = JOURNEY_EXPECTATIONS[name]
    return {
        "journey_id": name,
        "expected": expected,
        "actual": result.get("actual"),
        "passed": result.get("actual") == expected,
        "terminal_stage": result.get("stage"),
        "first_blocker": (
            result.get("error")
            or result.get("rejection_reasons")
            or result.get("rejections")
            or result.get("consumption_errors")
            or []
        ),
        "decision_state": result.get("decision_state"),
        "risk_proposed_notional_usd": result.get("risk_proposed_notional_usd"),
        "accepted_handoff_count": result.get("accepted_handoff_count", 0),
        "artifact_hashes": result.get("artifact_hashes", {}),
        "test_namespace": True,
        "broker_disabled": True,
        "paper_order_created": False,
        "broker_write_count": 0,
        "proof_credit_created": False,
        "authority": authority_flags(),
    }


def build_golden_journey_state() -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    generated_at = now_iso()
    journeys = [
        _run_journey(name, f"golden-{name}") for name in JOURNEY_EXPECTATIONS
    ]
    errors: list[str] = []
    for journey in journeys:
        if journey.get("passed") is not True:
            errors.append(f"golden_journey_failed:{journey.get('journey_id')}")
        errors.extend(
            validate_authority(
                journey.get("authority", {}),
                prefix=f"journey:{journey.get('journey_id')}",
            )
        )
        if journey.get("paper_order_created") is not False:
            errors.append(f"golden_journey_created_order:{journey.get('journey_id')}")
        if int(journey.get("broker_write_count") or 0) != 0:
            errors.append(f"golden_journey_broker_write:{journey.get('journey_id')}")
    errors = unique_errors(errors)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_tradeability_golden_journeys",
        "generated_at": generated_at,
        "status": "passed" if not errors else "blocked",
        "fixture_boundary": "external_provider_boundary_only",
        "journey_count": len(journeys),
        "passed_count": sum(row.get("passed") is True for row in journeys),
        "valid_pass_reached_broker_disabled_handoff": next(
            row for row in journeys if row["journey_id"] == "valid_pass"
        )["passed"],
        "journeys": journeys,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "authority": authority_flags(),
    }
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_tradeability_golden_journey_checks",
        "generated_at": generated_at,
        "status": payload["status"],
        "implementation_complete": not errors,
        "journey_count": len(journeys),
        "passed_count": payload["passed_count"],
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    return payload, checks, errors


def build_and_write_golden_journeys(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    payload, checks, errors = build_golden_journey_state()
    store = AtomicArtifactStore(runtime_dir(settings))
    store.write_json(GOLDEN_ARTIFACT, payload)
    store.write_json(GOLDEN_CHECKS_ARTIFACT, checks)
    return payload, checks, errors


def build_and_write_reachability_canary(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    generated_at = now_iso()
    build = git_snapshot(ROOT)
    build_id = str(build.get("head") or "uncommitted")
    journey = _run_journey("valid_pass", f"canary-{build_id[:12]}")
    status = "reachable" if journey.get("passed") is True else "blocked_contract"
    current_envelopes = read_jsonl(runtime / "qadam_tradeability_envelopes.jsonl")
    market_clock = read_json(runtime / "qadam_market_clock_truth.json")
    market_session_date = (
        str(market_clock.get("session_date") or "")
        if market_clock.get("provider_backed") is True
        and market_clock.get("provider_fresh") is True
        and market_clock.get("actionable_for_conversion") is True
        and market_clock.get("session_phase") == "regular"
        else ""
    )
    real_market_session_observed = bool(market_session_date)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_tradeability_reachability_canary",
        "generated_at": generated_at,
        "canary_id": "tradeability-canary:" + sha256_json(
            {
                "build_id": build_id,
                "journey": journey.get("artifact_hashes"),
                "market_session_date": market_session_date or "build_only",
            }
        )[:24],
        "build_id": build_id,
        "status": status,
        "market_session_date": market_session_date or None,
        "real_market_session_observed": real_market_session_observed,
        "market_clock_truth_id": market_clock.get("truth_id"),
        "test_namespace": True,
        "broker_disabled": True,
        "fixture_boundary": "external_provider_boundary_only",
        "current_setup_state": (
            "current_setup_present" if current_envelopes else "no_current_setup"
        ),
        "operational_health_is_not_reachability": True,
        "ready_idle_is_not_reachability": True,
        "journey": journey,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "paper_calendar_advanced": False,
        "authority": authority_flags(),
    }
    payload["signature"] = sha256_json(payload)
    errors: list[str] = []
    if status != "reachable":
        errors.append("tradeability_canary_not_reachable")
    errors.extend(validate_authority(payload["authority"], prefix="reachability_canary"))
    errors = unique_errors(errors)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_tradeability_reachability_checks",
        "generated_at": generated_at,
        "status": "passed" if not errors else "blocked",
        "reachability_state": status,
        "current_setup_state": payload["current_setup_state"],
        "canary_exercised_count": 1,
        "accepted_broker_disabled_handoff_count": journey.get(
            "accepted_handoff_count", 0
        ),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store = AtomicArtifactStore(runtime)
    store.write_json(REACHABILITY_ARTIFACT, payload)
    history = read_jsonl(runtime / REACHABILITY_HISTORY_ARTIFACT)
    if payload["canary_id"] not in {row.get("canary_id") for row in history}:
        append_jsonl_durable(runtime / REACHABILITY_HISTORY_ARTIFACT, payload)
    store.write_json(REACHABILITY_CHECKS_ARTIFACT, checks)
    return payload, checks, errors


def classify_contract_defect(record: dict[str, Any]) -> str:
    text = " ".join(
        str(value)
        for value in (
            record.get("defect_class"),
            record.get("error"),
            record.get("reasons"),
        )
    ).lower()
    if "mixed_generation" in text:
        return "mixed_generation"
    if "capability" in text or "uncollectable" in text:
        return "capability_matrix_mismatch"
    if "prompt" in text:
        return "prompt_compile_failure"
    if "critic" in text:
        return "critic_contract_failure"
    if "consumer" in text or "undocumented" in text:
        return "consumer_undocumented_requirement"
    if "missing" in text or "omission" in text or "packet" in text:
        return "producer_field_omission"
    return "contract_schema_drift"


def build_and_write_contract_defect_state(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    generated_at = now_iso()
    source = read_jsonl(runtime / SOURCE_DEFECTS_ARTIFACT)
    defects: list[dict[str, Any]] = []
    for row in source:
        defect_class = classify_contract_defect(row)
        fingerprint = sha256_json(
            {
                "class": defect_class,
                "hypothesis_id": row.get("hypothesis_id"),
                "reasons": row.get("reasons"),
                "source": row.get("source_draft_ref"),
            }
        )
        defects.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_contract_defect",
                "generated_at": generated_at,
                "defect_id": "contract-defect:" + fingerprint[:24],
                "defect_fingerprint": fingerprint,
                "defect_class": defect_class,
                "producer": "canonical_tradeability",
                "consumer": "tradeability_envelope",
                "field_ids": row.get("reasons", []),
                "source_record": row,
                "ordinary_market_hold": False,
                "automatic_retry_allowed": defect_class in SAFE_RETRY_CLASSES,
                "automatic_code_or_policy_change_allowed": False,
                "authority": authority_flags(),
            }
        )
    existing_requests = read_jsonl(runtime / REPAIR_REQUESTS_ARTIFACT)
    existing_fingerprints = {
        str(row.get("defect_fingerprint")) for row in existing_requests
    }
    new_requests = []
    for defect in defects:
        if defect["defect_fingerprint"] in existing_fingerprints:
            continue
        new_requests.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_contract_repair_request",
                "generated_at": generated_at,
                "repair_request_id": "contract-repair:"
                + defect["defect_fingerprint"][:24],
                "defect_id": defect["defect_id"],
                "defect_fingerprint": defect["defect_fingerprint"],
                "defect_class": defect["defect_class"],
                "producer": defect["producer"],
                "consumer": defect["consumer"],
                "field_ids": defect["field_ids"],
                "status": "operator_or_engineering_review_required",
                "deduplicated": True,
                "automatic_retry_allowed": defect["automatic_retry_allowed"],
                "schema_change_allowed": False,
                "prompt_change_allowed": False,
                "code_change_allowed": False,
                "threshold_change_allowed": False,
                "authority_change_allowed": False,
                "authority": authority_flags(),
            }
        )
    requests = existing_requests + new_requests
    errors: list[str] = []
    if len({row.get("defect_fingerprint") for row in requests}) != len(requests):
        errors.append("contract_repair_request_not_deduplicated")
    if any(
        row.get("automatic_retry_allowed") is True
        and row.get("defect_class") in STRUCTURAL_DEFECT_CLASSES
        for row in requests
    ):
        errors.append("structural_contract_defect_auto_retry_enabled")
    for row in [*defects, *requests]:
        errors.extend(validate_authority(row.get("authority", {}), prefix="contract_defect"))
    errors = unique_errors(errors)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_contract_defect_summary",
        "generated_at": generated_at,
        "status": "contract_defect_active" if defects else "clear",
        "active_defect_count": len(defects),
        "open_repair_request_count": len(requests),
        "new_repair_request_count": len(new_requests),
        "structural_defect_count": sum(
            row["defect_class"] in STRUCTURAL_DEFECT_CLASSES for row in defects
        ),
        "ordinary_market_hold_count": 0,
        "service_circuit_required": bool(defects),
        "same_build_integration_probe_required_for_closure": True,
        "authority": authority_flags(),
    }
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_contract_self_healing_checks",
        "generated_at": generated_at,
        "status": "passed" if not errors else "blocked",
        "implementation_complete": not errors,
        "active_defect_count": len(defects),
        "deduplicated_repair_request_count": len(requests),
        "unsafe_mutation_allowed_count": 0,
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store = AtomicArtifactStore(runtime)
    store.write_jsonl(DEFECTS_ARTIFACT, defects)
    store.write_jsonl(REPAIR_REQUESTS_ARTIFACT, requests)
    store.write_json(DEFECT_SUMMARY_ARTIFACT, summary)
    store.write_json(SELF_HEALING_CHECKS_ARTIFACT, checks)
    return summary, checks, errors


__all__ = [
    "build_and_write_contract_defect_state",
    "build_and_write_golden_journeys",
    "build_and_write_reachability_canary",
    "build_golden_journey_state",
    "classify_contract_defect",
]
