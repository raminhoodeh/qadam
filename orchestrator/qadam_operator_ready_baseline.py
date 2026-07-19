"""OR-0 canonical runtime truth and safety baseline."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    unique_errors,
    validate_authority,
)

SCHEMA_VERSION = "qadam_operator_ready_baseline.v1"
PHASE_ID = "OR-0"

BASELINE_ARTIFACT = "qadam_operator_ready_baseline.json"
TRUTH_ARTIFACT = "qadam_canonical_truth_contract.json"
RECONCILIATION_ARTIFACT = "qadam_runtime_state_reconciliation.json"
PROGRAM_STATUS_ARTIFACT = "qadam_operator_ready_program_status.json"
CHECK_ARTIFACT = "qadam_operator_ready_baseline_checks.json"

SOURCE_UNIVERSE_ARTIFACT = "qsase_source_universe.json"
SOURCE_RELIABILITY_ARTIFACT = "qsase_source_reliability.json"
SOURCE_RELIABILITY_RECORDS_ARTIFACT = "qsase_source_reliability_records.jsonl"
PROVIDER_CAPABILITY_ARTIFACT = "qsase_backfill_provider_capability_audit.json"
OPERATOR_PROVIDER_CAPABILITY_ARTIFACT = "qadam_provider_capability_registry.jsonl"
LONG_LOCK_ARTIFACT = "qadam_long_backtest_lock.json"
BACKFILL_STATE_ARTIFACT = "qsase_whole_universe_backfill_backtest_state.json"
BACKFILL_MANIFEST_ARTIFACT = "qsase_whole_universe_backfill_backtest_manifest.json"

MASTER_PLAN = ROOT / "docs" / "qadam-master-implementation-plan.md"
CURRENT_PAPER_TRIAL = "30-day paper growth trial"

SOURCE_TAXONOMY = (
    {
        "key": "registered_source",
        "definition": "A distinct source record present in the canonical source universe.",
    },
    {
        "key": "configured_adapter",
        "definition": "An adapter configured or locally ready; this does not prove a fresh response.",
    },
    {
        "key": "responding_provider",
        "definition": "A provider with a successful observed response; this does not prove freshness.",
    },
    {
        "key": "fresh_observation",
        "definition": "A source observation inside its category-specific freshness budget.",
    },
    {
        "key": "historical_capable_provider",
        "definition": "A provider able to return historical data through a permitted interface.",
    },
    {
        "key": "quorum_eligible_evidence_source",
        "definition": "A fresh independent source currently allowed to contribute to evidence quorum.",
    },
    {
        "key": "supplemental_context_source",
        "definition": "A visible context source that cannot satisfy required source quorum alone.",
    },
)


def _source_counts(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    universe = read_json(runtime / SOURCE_UNIVERSE_ARTIFACT)
    reliability = read_json(runtime / SOURCE_RELIABILITY_ARTIFACT)
    reliability_records = read_jsonl(runtime / SOURCE_RELIABILITY_RECORDS_ARTIFACT)
    capability = read_json(runtime / PROVIDER_CAPABILITY_ARTIFACT)
    operator_capabilities = read_jsonl(runtime / OPERATOR_PROVIDER_CAPABILITY_ARTIFACT)
    sources = universe.get("sources") if isinstance(universe.get("sources"), list) else []

    def configured(source: dict[str, Any]) -> bool:
        state = str(source.get("adapter_status") or source.get("state") or "").lower()
        credential = str(source.get("credential_status") or "").lower()
        return state in {"online", "ready", "connected", "ok", "sample_ready"} or credential in {
            "configured",
            "not_required",
        }

    def responding(source: dict[str, Any]) -> bool:
        state = str(source.get("state") or source.get("adapter_status") or "").lower()
        return state in {"online", "connected", "ok"} and bool(source.get("observed_timestamp"))

    historical_records = operator_capabilities
    if not historical_records:
        historical_records = capability.get("providers")
        if not isinstance(historical_records, list):
            historical_records = capability.get("records")
        if not isinstance(historical_records, list):
            historical_records = []
    fresh_records = [record for record in reliability_records if record.get("freshness_state") == "fresh"]
    quorum_records = [
        record
        for record in reliability_records
        if record.get("source_quorum_contribution", {}).get("can_contribute") is True
    ]
    supplemental_records = [
        record for record in reliability_records if record.get("supplemental_context_only") is True
    ]
    historical_capable = [
        record
        for record in historical_records
        if record.get("historical_supported") is True
        or record.get("historical_api_supported") is True
        or record.get("history_state") in {"supported", "available"}
    ]
    return {
        "registered_source_count": len(sources),
        "configured_adapter_count": sum(configured(source) for source in sources),
        "responding_provider_count": sum(responding(source) for source in sources),
        "fresh_observation_count": len(fresh_records),
        "historical_capable_provider_count": len(historical_capable),
        "quorum_eligible_evidence_source_count": len(quorum_records),
        "supplemental_context_source_count": len(supplemental_records),
        "source_universe_generated_at": universe.get("generated_at"),
        "source_reliability_generated_at": reliability.get("generated_at"),
        "counts_are_distinct_taxonomies": True,
        "counts_may_not_be_compared_as_equivalent": True,
    }


def _control_document_audit() -> dict[str, Any]:
    try:
        text = MASTER_PLAN.read_text(encoding="utf-8")
    except OSError:
        text = ""
    start = text.find("## 2026-07-10 Paper Growth Operating Target")
    end = text.find("\n## ", start + 4) if start >= 0 else -1
    active_target = text[start:end] if start >= 0 else ""
    contradictions: list[str] = []
    if CURRENT_PAPER_TRIAL not in active_target:
        contradictions.append("active_master_paper_trial_missing")
    if "60-day paper growth trial" in active_target:
        contradictions.append("active_master_retains_60_day_trial")
    if "500+ live data feeds" in text:
        contradictions.append("master_retains_unqualified_500_plus_feed_claim")
    return {
        "master_plan": str(MASTER_PLAN.relative_to(ROOT)),
        "canonical_paper_trial_present": CURRENT_PAPER_TRIAL in active_target,
        "unqualified_feed_claim_present": "500+ live data feeds" in text,
        "control_document_contradiction_count": len(contradictions),
        "control_document_contradictions": contradictions,
    }


def build_runtime_state_reconciliation(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    lock = read_json(runtime / LONG_LOCK_ARTIFACT)
    state = read_json(runtime / BACKFILL_STATE_ARTIFACT)
    manifest = read_json(runtime / BACKFILL_MANIFEST_ARTIFACT)
    contradictions: list[dict[str, Any]] = []
    lock_started = lock.get("phase_1_backfill_started")
    state_started = state.get("phase_1_backfill_started")
    if lock_started != state_started:
        contradictions.append(
            {
                "contradiction_id": "backfill_started_lock_state_mismatch",
                "lock_value": lock_started,
                "state_value": state_started,
                "resolution_owner": "OR-1_atomic_research_supervisor",
                "automatic_resolution_allowed": False,
            }
        )
    manifest_jobs = manifest.get("jobs") if isinstance(manifest.get("jobs"), list) else []
    if state.get("completed_job_count") and len(manifest_jobs) != state.get("completed_job_count"):
        contradictions.append(
            {
                "contradiction_id": "manifest_state_completed_job_count_mismatch",
                "manifest_job_count": len(manifest_jobs),
                "state_completed_job_count": state.get("completed_job_count"),
                "resolution_owner": "OR-1_atomic_research_supervisor",
                "automatic_resolution_allowed": False,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_runtime_state_reconciliation",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "contradictions_visible" if contradictions else "state_consistent",
        "research_lock": {
            "status": lock.get("status"),
            "phase_1_backfill_started": lock_started,
            "paperops_watch_only_mode": lock.get("paperops_watch_only_mode"),
            "release_requires_explicit_operator_action": lock.get(
                "release_requires_explicit_operator_action"
            ),
        },
        "backfill_state": {
            "status": state.get("status"),
            "phase_1_backfill_started": state_started,
            "completed_job_count": state.get("completed_job_count"),
            "pending_job_count": state.get("pending_job_count"),
        },
        "backfill_manifest": {
            "status": manifest.get("status"),
            "job_count": len(manifest_jobs),
            "generated_at": manifest.get("generated_at"),
        },
        "contradiction_count": len(contradictions),
        "contradictions": contradictions,
        "lock_preserved": lock.get("status") == "active",
        "paperops_watch_only_preserved": lock.get("paperops_watch_only_mode") is True,
        "authority": authority_flags(),
    }


def build_canonical_truth_contract(settings: Settings | None = None) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_canonical_truth_contract",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "canonical_truth_ready",
        "current_paper_trial": {
            "user_facing_name": CURRENT_PAPER_TRIAL,
            "duration_calendar_days": 30,
            "calendar_is_real_elapsed_time": True,
            "backfill_allowed": False,
            "simulated_elapsed_time_allowed": False,
            "forced_trade_allowed": False,
            "live_capital_enabled": False,
        },
        "source_taxonomy": list(SOURCE_TAXONOMY),
        "source_counts": _source_counts(settings),
        "control_document_audit": _control_document_audit(),
        "runtime_truth_precedence": True,
        "authority": authority_flags(),
    }


def validate_operator_ready_baseline(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    truth = bundle.get("truth") if isinstance(bundle.get("truth"), dict) else {}
    reconciliation = bundle.get("reconciliation") if isinstance(bundle.get("reconciliation"), dict) else {}
    trial = truth.get("current_paper_trial") if isinstance(truth.get("current_paper_trial"), dict) else {}
    counts = truth.get("source_counts") if isinstance(truth.get("source_counts"), dict) else {}
    if trial.get("user_facing_name") != CURRENT_PAPER_TRIAL:
        errors.append("canonical_paper_trial_name_mismatch")
    if trial.get("duration_calendar_days") != 30:
        errors.append("canonical_paper_trial_duration_mismatch")
    for key in ("backfill_allowed", "simulated_elapsed_time_allowed", "forced_trade_allowed", "live_capital_enabled"):
        if trial.get(key) is not False:
            errors.append(f"canonical_trial_unsafe:{key}")
    if len(truth.get("source_taxonomy", [])) != len(SOURCE_TAXONOMY):
        errors.append("source_taxonomy_incomplete")
    if counts.get("registered_source_count", 0) < 1:
        errors.append("registered_source_count_missing")
    if counts.get("counts_are_distinct_taxonomies") is not True:
        errors.append("source_counts_not_taxonomy_labeled")
    if truth.get("control_document_audit", {}).get("control_document_contradiction_count") != 0:
        errors.append("control_document_contradiction_remaining")
    if reconciliation.get("lock_preserved") is not True:
        errors.append("research_lock_not_preserved")
    if reconciliation.get("paperops_watch_only_preserved") is not True:
        errors.append("paperops_watch_only_not_preserved")
    if reconciliation.get("contradiction_count", 0) and reconciliation.get("status") != "contradictions_visible":
        errors.append("runtime_contradiction_hidden")
    errors.extend(validate_authority(truth.get("authority", {}), prefix="truth"))
    errors.extend(validate_authority(reconciliation.get("authority", {}), prefix="reconciliation"))
    return unique_errors(errors)


def validate_negative_baseline_probes(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    unsafe = deepcopy(bundle)
    unsafe["truth"]["current_paper_trial"]["simulated_elapsed_time_allowed"] = True
    if "canonical_trial_unsafe:simulated_elapsed_time_allowed" not in validate_operator_ready_baseline(unsafe):
        errors.append("or0_simulated_time_probe_not_rejected")
    live = deepcopy(bundle)
    live["truth"]["authority"]["live_capital_enabled"] = True
    if "truth_forbidden_true:live_capital_enabled" not in validate_operator_ready_baseline(live):
        errors.append("or0_live_capital_probe_not_rejected")
    hidden = deepcopy(bundle)
    hidden["reconciliation"]["status"] = "state_consistent"
    if "runtime_contradiction_hidden" not in validate_operator_ready_baseline(hidden):
        errors.append("or0_hidden_contradiction_probe_not_rejected")
    return unique_errors(errors)


def build_and_write_operator_ready_baseline(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    truth = build_canonical_truth_contract(settings)
    reconciliation = build_runtime_state_reconciliation(settings)
    bundle = {"truth": truth, "reconciliation": reconciliation}
    errors = validate_operator_ready_baseline(bundle)
    errors.extend(validate_negative_baseline_probes(bundle))
    errors = unique_errors(errors)
    baseline = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_ready_baseline",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "ready_with_visible_state_contradictions" if reconciliation["contradiction_count"] else "ready",
        "source_counts": truth["source_counts"],
        "current_paper_trial": truth["current_paper_trial"],
        "runtime_contradiction_count": reconciliation["contradiction_count"],
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    program_status = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_ready_program_status",
        "generated_at": now_iso(),
        "status": "or0_ready_for_or1" if not errors else "or0_blocked",
        "current_phase": PHASE_ID,
        "next_phase": "OR-1",
        "paperops_state": "watch_only_research_lock_active",
        "why_not_trading_now": "Historical research lock remains active while evidence infrastructure is built.",
        "runtime_contradiction_count": reconciliation["contradiction_count"],
        "authority": authority_flags(),
    }
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_ready_baseline_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "validation_errors": errors,
        "negative_probe_count": 3,
        "runtime_contradiction_count": reconciliation["contradiction_count"],
        "state_contradictions_visible": True,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "paper_growth_trial_calendar_advanced": False,
        "simulated_elapsed_time_allowed": False,
        "authority": authority_flags(),
    }
    store: AtomicArtifactStore[dict[str, Any]] = AtomicArtifactStore(runtime_dir(settings))
    store.write_json(TRUTH_ARTIFACT, truth)
    store.write_json(RECONCILIATION_ARTIFACT, reconciliation)
    store.write_json(BASELINE_ARTIFACT, baseline)
    store.write_json(PROGRAM_STATUS_ARTIFACT, program_status)
    store.write_json(CHECK_ARTIFACT, checks)
    return {"truth": truth, "reconciliation": reconciliation, "baseline": baseline, "program_status": program_status}, checks, errors
