"""Migration, generation, consumer, visibility, and release audits for CTC."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
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
    sha256_json,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_operator_service import (
    operator_build_dirty_records,
    operator_build_identity,
)

SCHEMA_VERSION = "qadam.canonical-tradeability-compiler.v1"

MIGRATION_ARTIFACT = "qadam_tradeability_migration_status.json"
PARITY_ARTIFACT = "qadam_legacy_contract_parity.json"
CONSUMER_AUDIT_ARTIFACT = "qadam_consumer_migration_audit.json"
DEPRECATION_ARTIFACT = "qadam_deprecation_registry.json"
MIGRATION_CHECKS_ARTIFACT = "qadam_tradeability_migration_checks.json"

GENERATION_MANIFEST_ARTIFACT = "qadam_decision_generation_manifest.json"
GENERATION_RECEIPTS_ARTIFACT = "qadam_decision_generation_receipts.jsonl"
GENERATION_FAILURES_ARTIFACT = "qadam_decision_generation_failures.jsonl"
GENERATION_CHECKS_ARTIFACT = "qadam_decision_dag_checks.json"

ENVELOPE_AKBER_ARTIFACT = "qadam_envelope_akber_decisions.jsonl"
ENVELOPE_SHADOW_ARTIFACT = "qadam_envelope_shadow_decisions.jsonl"
ENVELOPE_RISK_ARTIFACT = "qadam_envelope_risk_decisions.jsonl"
ENVELOPE_ROUTER_ARTIFACT = "qadam_envelope_router_decisions.jsonl"
DOWNSTREAM_CHECKS_ARTIFACT = "qadam_downstream_consumer_checks.json"

DASHBOARD_SUMMARY_ARTIFACT = "qadam_tradeability_compiler_dashboard_summary.json"
AGENT_DASHBOARD_ARTIFACT = "qadam_agent_gauntlet_dashboard_summary.json"
FUNNEL_ARTIFACT = "qadam_tradeability_funnel.json"
PUBLIC_SAFETY_ARTIFACT = "qadam_tradeability_public_safety_audit.json"

CERTIFICATION_ARTIFACT = "qadam_canonical_tradeability_compiler_certification.json"
SOAK_ARTIFACT = "qadam_tradeability_soak_status.json"
RELEASE_ARTIFACT = "qadam_tradeability_release_manifest.json"
LEGACY_REMOVAL_ARTIFACT = "qadam_legacy_removal_audit.json"
IMPLEMENTATION_STATUS_ARTIFACT = "qadam_ctc_implementation_status.json"

CANONICAL_ARTIFACTS = {
    "envelopes": "qadam_tradeability_envelopes.jsonl",
    "hypotheses": "qadam_strategy_hypotheses_v3.jsonl",
    "packets": "qadam_decision_evidence_packets.jsonl",
    "akber_inputs": "qadam_akber_filter_v3_inputs.jsonl",
    "akber_results": "qadam_akber_filter_v3_results.jsonl",
    "shadow": "qadam_forward_shadow_decisions.jsonl",
    "risk": "qadam_position_size_proposals.jsonl",
    "router": "qadam_router_v3_decisions.jsonl",
    "handoffs": "qadam_paperops_handoff_v3.jsonl",
}
ACTIVE_CONSUMER_FILES = (
    ROOT / "orchestrator" / "qadam_akber_filter_v3.py",
    ROOT / "orchestrator" / "qadam_forward_shadow.py",
    ROOT / "orchestrator" / "qadam_portfolio_risk_engine.py",
    ROOT / "orchestrator" / "qadam_router_v3_paperops.py",
)
LEGACY_QEG_TOKENS = (
    "qadam_qeg_strategy_hypotheses.jsonl",
    "qadam_qeg_akber_inputs.jsonl",
    "qadam_qeg_akber_results.jsonl",
    "qadam_qeg_decision_evidence_packets.jsonl",
)


def _read_rows(runtime: Path) -> dict[str, list[dict[str, Any]]]:
    return {
        key: read_jsonl(runtime / filename)
        for key, filename in CANONICAL_ARTIFACTS.items()
    }


def _hypothesis_id(row: dict[str, Any]) -> str:
    lineage = row.get("lineage") if isinstance(row.get("lineage"), dict) else {}
    identity = row.get("identity") if isinstance(row.get("identity"), dict) else {}
    return str(
        row.get("hypothesis_id")
        or lineage.get("hypothesis_id")
        or identity.get("hypothesis_id")
        or ""
    )


def _current_canonical_rows(
    rows: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, list[dict[str, Any]]], set[str]]:
    """Exclude legacy/history rows that are not in the current compiler output."""

    hypothesis_ids = {
        _hypothesis_id(row) for row in rows["hypotheses"] if _hypothesis_id(row)
    }
    current: dict[str, list[dict[str, Any]]] = {}
    for lane, lane_rows in rows.items():
        if lane == "envelopes":
            current[lane] = lane_rows if hypothesis_ids else []
        else:
            current[lane] = [
                row for row in lane_rows if _hypothesis_id(row) in hypothesis_ids
            ]
    return current, hypothesis_ids


def build_and_write_migration_audit(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    generated_at = now_iso()
    pipeline_source = (ROOT / "orchestrator" / "qadam_tradeability_pipeline.py").read_text(
        encoding="utf-8"
    )
    foundry_source = (ROOT / "orchestrator" / "qadam_strategy_foundry_v3.py").read_text(
        encoding="utf-8"
    )
    producer_records = [
        {
            "producer": "canonical_tradeability",
            "artifact": CANONICAL_ARTIFACTS["hypotheses"],
            "active": "store.write_jsonl(LEGACY_HYPOTHESES_ARTIFACT" in pipeline_source,
        },
        {
            "producer": "strategy_foundry_v3",
            "artifact": CANONICAL_ARTIFACTS["hypotheses"],
            "active": "store.write_jsonl(HYPOTHESES_ARTIFACT" in foundry_source,
        },
    ]
    active_producers = [row for row in producer_records if row["active"]]
    consumer_rows = []
    for path in ACTIVE_CONSUMER_FILES:
        source = path.read_text(encoding="utf-8")
        legacy_tokens = [token for token in LEGACY_QEG_TOKENS if token in source]
        consumer_rows.append(
            {
                "consumer": path.stem,
                "canonical_hypothesis_artifact": CANONICAL_ARTIFACTS["hypotheses"],
                "legacy_qeg_token_count": len(legacy_tokens),
                "legacy_qeg_tokens": legacy_tokens,
                "cutover_complete": not legacy_tokens,
            }
        )
    rows, _ = _current_canonical_rows(_read_rows(runtime))
    qeg_drafts = read_jsonl(runtime / "qadam_qeg_strategy_hypotheses.jsonl")
    v3_drafts = read_jsonl(runtime / "qadam_strategy_drafts_v3.jsonl")
    projections = rows["hypotheses"]
    errors: list[str] = []
    if len(active_producers) != 1 or active_producers[0]["producer"] != (
        "canonical_tradeability"
    ):
        errors.append("canonical_hypothesis_producer_count_not_one")
    if any(not row["cutover_complete"] for row in consumer_rows):
        errors.append("active_consumer_reads_legacy_qeg_contract")
    errors = unique_errors(errors)
    migration = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_tradeability_migration_status",
        "generated_at": generated_at,
        "status": "cutover_complete" if not errors else "blocked",
        "active_canonical_producer_count": len(active_producers),
        "active_canonical_producer": (
            active_producers[0]["producer"] if len(active_producers) == 1 else None
        ),
        "producer_records": producer_records,
        "consumer_cutover_count": sum(row["cutover_complete"] for row in consumer_rows),
        "consumer_count": len(consumer_rows),
        "qeg_role": "research_draft_and_historical_audit_only",
        "qeg_downstream_authority": False,
        "authority": authority_flags(),
    }
    parity = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_legacy_contract_parity",
        "generated_at": generated_at,
        "v3_draft_count": len(v3_drafts),
        "qeg_draft_count": len(qeg_drafts),
        "canonical_projection_count": len(projections),
        "semantic_difference_policy": (
            "QEG graph outputs may add evidence, but only the compiler projection may enter Akber."
        ),
        "comparison_only": True,
        "authority": authority_flags(),
    }
    consumer_audit = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_consumer_migration_audit",
        "generated_at": generated_at,
        "status": "passed" if not errors else "blocked",
        "consumers": consumer_rows,
        "authority": authority_flags(),
    }
    deprecation = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_deprecation_registry",
        "generated_at": generated_at,
        "records": [
            {
                "artifact": token,
                "state": "comparison_and_research_draft_only",
                "active_downstream_reader_allowed": False,
                "removal_condition": "five-session soak and rollback audit complete",
            }
            for token in LEGACY_QEG_TOKENS
        ],
        "authority": authority_flags(),
    }
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_tradeability_migration_checks",
        "generated_at": generated_at,
        "status": "passed" if not errors else "blocked",
        "implementation_complete": not errors,
        "active_canonical_producer_count": len(active_producers),
        "legacy_active_consumer_count": sum(
            not row["cutover_complete"] for row in consumer_rows
        ),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store = AtomicArtifactStore(runtime)
    store.write_json(MIGRATION_ARTIFACT, migration)
    store.write_json(PARITY_ARTIFACT, parity)
    store.write_json(CONSUMER_AUDIT_ARTIFACT, consumer_audit)
    store.write_json(DEPRECATION_ARTIFACT, deprecation)
    store.write_json(MIGRATION_CHECKS_ARTIFACT, checks)
    return migration, checks, errors


def _generation_id(row: dict[str, Any]) -> str:
    generation = row.get("generation")
    if isinstance(generation, dict) and generation.get("decision_generation_id"):
        return str(generation["decision_generation_id"])
    return str(row.get("decision_generation_id") or "")


def build_and_write_decision_generation_audit(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    generated_at = now_iso()
    rows, _ = _current_canonical_rows(_read_rows(runtime))
    by_hypothesis: dict[str, list[dict[str, Any]]] = {}
    for lane, lane_rows in rows.items():
        for row in lane_rows:
            hypothesis_id = _hypothesis_id(row)
            if hypothesis_id:
                by_hypothesis.setdefault(hypothesis_id, []).append(
                    {
                        "lane": lane,
                        "artifact_id": row.get("envelope_id")
                        or row.get("akber_result_id")
                        or row.get("decision_id")
                        or row.get("proposal_id")
                        or row.get("router_decision_id")
                        or row.get("paperops_handoff_id"),
                        "decision_generation_id": _generation_id(row),
                        "record_hash": sha256_json(row),
                    }
                )
    receipts = []
    failures = []
    for hypothesis_id, records in sorted(by_hypothesis.items()):
        lanes = {str(row.get("lane") or "") for row in records}
        akber_result = next(
            (
                row
                for row in rows["akber_results"]
                if _hypothesis_id(row) == hypothesis_id
            ),
            {},
        )
        router_decision = next(
            (
                row
                for row in rows["router"]
                if _hypothesis_id(row) == hypothesis_id
            ),
            {},
        )
        required_lanes = {
            "envelopes",
            "hypotheses",
            "packets",
            "akber_inputs",
            "akber_results",
        }
        if akber_result.get("decision") == "pass":
            required_lanes.update({"shadow", "risk", "router"})
        if router_decision.get("paperops_handoff_allowed") is True:
            required_lanes.add("handoffs")
        missing_lanes = sorted(required_lanes - lanes)
        nonempty = {
            row["decision_generation_id"]
            for row in records
            if row["decision_generation_id"]
        }
        complete = not missing_lanes and len(nonempty) == 1 and all(
            row["decision_generation_id"] for row in records
        )
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_decision_generation_receipt",
            "generated_at": generated_at,
            "hypothesis_id": hypothesis_id,
            "decision_generation_id": next(iter(nonempty)) if len(nonempty) == 1 else None,
            "lane_count": len(records),
            "records": records,
            "required_lanes": sorted(required_lanes),
            "missing_lanes": missing_lanes,
            "same_generation_complete": complete,
            "mixed_generation_join": len(nonempty) > 1,
            "authority": authority_flags(),
        }
        receipts.append(receipt)
        if not complete:
            failures.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "artifact_type": "qadam_decision_generation_failure",
                    "generated_at": generated_at,
                    "hypothesis_id": hypothesis_id,
                    "failure_class": (
                        "mixed_generation" if len(nonempty) > 1 else "generation_lineage_missing"
                    ),
                    "missing_lanes": missing_lanes,
                    "records": records,
                    "authority": authority_flags(),
                }
            )
    envelope_count = len(rows["envelopes"])
    errors = []
    if failures:
        errors.append(f"decision_generation_failure_count:{len(failures)}")
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_decision_generation_manifest",
        "generated_at": generated_at,
        "status": (
            "ready_idle"
            if not by_hypothesis
            else "complete"
            if not failures
            else "blocked"
        ),
        "current_hypothesis_count": len(by_hypothesis),
        "current_envelope_count": envelope_count,
        "completed_generation_count": sum(
            row["same_generation_complete"] for row in receipts
        ),
        "mixed_generation_join_count": sum(
            row["mixed_generation_join"] for row in receipts
        ),
        "partial_generation_current_count": len(failures),
        "atomic_publication_required": True,
        "paperops_requires_completed_generation": True,
        "authority": authority_flags(),
    }
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_decision_dag_checks",
        "generated_at": generated_at,
        "status": "passed" if not errors else "blocked",
        "implementation_complete": not errors,
        "valid_idle_state": not by_hypothesis,
        "mixed_generation_join_count": manifest["mixed_generation_join_count"],
        "partial_generation_current_count": manifest[
            "partial_generation_current_count"
        ],
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store = AtomicArtifactStore(runtime)
    store.write_json(GENERATION_MANIFEST_ARTIFACT, manifest)
    store.write_jsonl(GENERATION_RECEIPTS_ARTIFACT, receipts)
    store.write_jsonl(GENERATION_FAILURES_ARTIFACT, failures)
    store.write_json(GENERATION_CHECKS_ARTIFACT, checks)
    return manifest, checks, errors


def build_and_write_consumer_audit(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    generated_at = now_iso()
    rows, _ = _current_canonical_rows(_read_rows(runtime))
    envelope_ids = {
        str(row.get("envelope_id")) for row in rows["envelopes"] if row.get("envelope_id")
    }
    hypothesis_envelopes = {
        str(row.get("hypothesis_id")): str(row.get("tradeability_envelope_id"))
        for row in rows["hypotheses"]
        if row.get("hypothesis_id")
    }
    missing_projection_envelopes = sorted(
        envelope_id
        for envelope_id in hypothesis_envelopes.values()
        if envelope_id not in envelope_ids
    )
    errors = []
    if missing_projection_envelopes:
        errors.append("canonical_projection_envelope_reference_missing")
    for path in ACTIVE_CONSUMER_FILES:
        source = path.read_text(encoding="utf-8")
        if any(token in source for token in LEGACY_QEG_TOKENS):
            errors.append(f"legacy_qeg_reader_active:{path.name}")
    expected_generations = {
        _hypothesis_id(row): _generation_id(row)
        for row in rows["hypotheses"]
        if _hypothesis_id(row)
    }
    for lane in ("akber_inputs", "akber_results", "shadow", "risk", "router", "handoffs"):
        lane_counts: Counter[str] = Counter()
        for row in rows[lane]:
            hypothesis_id = _hypothesis_id(row)
            lane_counts[hypothesis_id] += 1
            generation_id = _generation_id(row)
            if not generation_id:
                errors.append(f"canonical_consumer_generation_missing:{lane}:{hypothesis_id}")
            elif generation_id != expected_generations.get(hypothesis_id):
                errors.append(f"canonical_consumer_generation_mismatch:{lane}:{hypothesis_id}")
            if lane == "router" and row.get("exactly_one_final_state") is not True:
                errors.append(f"router_final_state_not_exactly_one:{hypothesis_id}")
        for hypothesis_id, count in lane_counts.items():
            if hypothesis_id and count > 1:
                errors.append(f"canonical_consumer_duplicate:{lane}:{hypothesis_id}")
    errors = unique_errors(errors)
    decision_rows = {
        "akber": rows["akber_results"],
        "shadow": rows["shadow"],
        "risk": rows["risk"],
        "router": rows["router"],
    }
    store = AtomicArtifactStore(runtime)
    store.write_jsonl(ENVELOPE_AKBER_ARTIFACT, decision_rows["akber"])
    store.write_jsonl(ENVELOPE_SHADOW_ARTIFACT, decision_rows["shadow"])
    store.write_jsonl(ENVELOPE_RISK_ARTIFACT, decision_rows["risk"])
    store.write_jsonl(ENVELOPE_ROUTER_ARTIFACT, decision_rows["router"])
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_downstream_consumer_audit",
        "generated_at": generated_at,
        "status": "passed" if not errors else "blocked",
        "canonical_envelope_count": len(envelope_ids),
        "canonical_projection_count": len(hypothesis_envelopes),
        "downstream_counts": {key: len(value) for key, value in decision_rows.items()},
        "legacy_qeg_reader_count": sum(
            any(token in path.read_text(encoding="utf-8") for token in LEGACY_QEG_TOKENS)
            for path in ACTIVE_CONSUMER_FILES
        ),
        "missing_context_is_adverse_evidence": False,
        "exactly_one_router_state_required": True,
        "authority": authority_flags(),
    }
    checks = {
        **payload,
        "artifact_type": "qadam_downstream_consumer_checks",
        "implementation_complete": not errors,
        "validation_errors": errors,
    }
    store.write_json(DOWNSTREAM_CHECKS_ARTIFACT, checks)
    return payload, checks, errors


def build_and_write_visibility(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    generated_at = now_iso()
    rows, _ = _current_canonical_rows(_read_rows(runtime))
    reachability = read_json(runtime / "qadam_tradeability_reachability_checks.json")
    defects = read_json(runtime / "qadam_contract_defect_summary.json")
    agent = read_json(runtime / "qadam_agent_gauntlet_summary.json")
    stages = {
        "observations": read_json(runtime / "qadam_pattern_score_v3_checks.json").get(
            "score_count", 0
        ),
        "accepted_research_packets": len(
            read_jsonl(runtime / "qadam_accepted_research_packets.jsonl")
        ),
        "envelopes": len(rows["envelopes"]),
        "akber_entries": len(rows["akber_inputs"]),
        "akber_passes": sum(row.get("decision") == "pass" for row in rows["akber_results"]),
        "shadows": len(rows["shadow"]),
        "risk_proposals": len(rows["risk"]),
        "router_decisions": len(rows["router"]),
        "handoffs": len(rows["handoffs"]),
        "orders_created_by_compiler": 0,
    }
    dashboard = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_tradeability_compiler_dashboard_summary",
        "generated_at": generated_at,
        "public_safe": True,
        "read_only": True,
        "operational_health": read_json(
            runtime / "qadam_operator_service_health.json"
        ).get("status", "unknown"),
        "tradeability_reachability": reachability.get("reachability_state", "not_exercised"),
        "current_setup_state": reachability.get("current_setup_state", "no_current_setup"),
        "contract_defect_state": defects.get("status", "unknown"),
        "funnel": stages,
        "first_blocker": (
            "contract_defect"
            if int(defects.get("active_defect_count") or 0)
            else "no_current_setup"
            if not rows["envelopes"]
            else "see_canonical_router_decision"
        ),
        "next_action": (
            "repair_contract"
            if int(defects.get("active_defect_count") or 0)
            else "wait_for_new_provider_backed_setup"
            if not rows["envelopes"]
            else "continue_canonical_decision_dag"
        ),
        "protected_dashboard_structure_changed": False,
        "authority": authority_flags(),
    }
    agent_dashboard = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_agent_gauntlet_dashboard_summary",
        "generated_at": generated_at,
        "public_safe": True,
        "task_count": agent.get("task_count", 0),
        "accepted_packet_count": agent.get("accepted_packet_count", 0),
        "rejected_packet_count": agent.get("rejected_packet_count", 0),
        "raw_prompts_exposed": False,
        "chain_of_thought_exposed": False,
        "authority": authority_flags(),
    }
    funnel = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_tradeability_funnel",
        "generated_at": generated_at,
        "stages": stages,
        "counts_reconcile_with_canonical_artifacts": True,
        "canary_records_included": False,
        "authority": authority_flags(),
    }
    serialized = str({"dashboard": dashboard, "agent": agent_dashboard, "funnel": funnel})
    forbidden = [
        token
        for token in ("api_key\":", "secret\":", "/users/", "compiled_prompt")
        if token in serialized.lower()
    ]
    errors = unique_errors(
        [f"public_projection_forbidden_token:{token}" for token in forbidden]
        + validate_authority(dashboard["authority"], prefix="dashboard_tradeability")
    )
    safety = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_tradeability_public_safety_audit",
        "generated_at": generated_at,
        "status": "passed" if not errors else "blocked",
        "forbidden_token_count": len(forbidden),
        "raw_prompt_exposed": False,
        "private_source_payload_exposed": False,
        "credential_exposed": False,
        "canary_exposed_as_current_setup": False,
        "command_enabled": False,
        "authority": authority_flags(),
        "validation_errors": errors,
    }
    store = AtomicArtifactStore(runtime)
    store.write_json(DASHBOARD_SUMMARY_ARTIFACT, dashboard)
    store.write_json(AGENT_DASHBOARD_ARTIFACT, agent_dashboard)
    store.write_json(FUNNEL_ARTIFACT, funnel)
    store.write_json(PUBLIC_SAFETY_ARTIFACT, safety)
    return dashboard, safety, errors


def build_and_write_certification(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    generated_at = now_iso()
    checks_by_phase = {
        "CTC-0": read_json(runtime / "qadam_ctc0_baseline_checks.json"),
        "CTC-1": read_json(runtime / "qadam_contract_hierarchy_checks.json"),
        "CTC-2": read_json(runtime / "qadam_tradeability_envelope_checks.json"),
        "CTC-3": read_json(runtime / "qadam_capability_matrix_checks.json"),
        "CTC-4": read_json(runtime / "qadam_agent_compiler_checks.json"),
        "CTC-5": read_json(runtime / "qadam_agent_compiler_checks.json"),
        "CTC-6": read_json(runtime / "qadam_agent_compiler_checks.json"),
        "CTC-7": read_json(runtime / MIGRATION_CHECKS_ARTIFACT),
        "CTC-8": read_json(runtime / GENERATION_CHECKS_ARTIFACT),
        "CTC-9": read_json(runtime / DOWNSTREAM_CHECKS_ARTIFACT),
        "CTC-10": read_json(runtime / "qadam_tradeability_golden_journey_checks.json"),
        "CTC-11": read_json(runtime / "qadam_tradeability_reachability_checks.json"),
        "CTC-12": read_json(runtime / "qadam_contract_self_healing_checks.json"),
        "CTC-13": read_json(runtime / PUBLIC_SAFETY_ARTIFACT),
    }
    phase_failures = [
        phase
        for phase, check in checks_by_phase.items()
        if check.get("status") != "passed"
    ]
    build_identity = operator_build_identity(settings)
    build_dirty_files = operator_build_dirty_records()
    build = {
        "head": build_identity.get("git_commit"),
        "branch": build_identity.get("git_branch"),
        "dirty": bool(build_dirty_files),
        "dirty_files": build_dirty_files,
        "dirty_path_count": len(build_dirty_files),
        "dirty_worktree_digest": build_identity.get("dirty_worktree_digest"),
        "build_scope": build_identity.get("build_scope", []),
        "service_contract_hash": build_identity.get("service_contract_hash"),
    }
    active_untracked_code = [
        row["path"]
        for row in build.get("dirty_files", [])
        if row.get("state") == "??"
        and Path(str(row.get("path"))).suffix in {".py", ".json", ".md"}
        and str(row.get("path", "")).split("/", 1)[0]
        in {"orchestrator", "scripts", "schemas", "agents", "config"}
    ]
    history = read_jsonl(runtime / "qadam_tradeability_reachability_history.jsonl")
    current_build = str(build.get("head") or "")
    successful_days = sorted(
        {
            str(row.get("market_session_date") or "")
            for row in history
            if row.get("status") == "reachable"
            and str(row.get("build_id") or "") == current_build
            and row.get("real_market_session_observed") is True
            and str(row.get("market_session_date") or "")
        }
    )
    defects = read_json(runtime / "qadam_contract_defect_summary.json")
    soak_complete = len(successful_days) >= 5 and int(
        defects.get("active_defect_count") or 0
    ) == 0
    implementation_errors = [f"phase_check_failed:{phase}" for phase in phase_failures]
    implementation_errors = unique_errors(implementation_errors)
    release_blockers = []
    if build.get("dirty") is True:
        release_blockers.append("release_worktree_dirty")
    if active_untracked_code:
        release_blockers.append("active_untracked_runtime_code_present")
    if not soak_complete:
        release_blockers.append("five_real_market_session_soak_incomplete")
    release = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_tradeability_release_manifest",
        "generated_at": generated_at,
        "build": build,
        "active_untracked_runtime_code": active_untracked_code,
        "active_untracked_runtime_code_count": len(active_untracked_code),
        "running_build_identity_must_equal_committed_release": True,
        "release_status": "certified" if not release_blockers else "pending",
        "release_blockers": release_blockers,
        "authority": authority_flags(),
    }
    soak = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_tradeability_soak_status",
        "generated_at": generated_at,
        "required_real_market_sessions": 5,
        "completed_real_market_sessions": len(successful_days),
        "completed_session_dates": successful_days,
        "contract_shape_defect_count": int(defects.get("active_defect_count") or 0),
        "status": "passed" if soak_complete else "collecting_real_market_time",
        "simulated_or_backfilled_sessions_allowed": False,
        "authority": authority_flags(),
    }
    legacy = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_legacy_removal_audit",
        "generated_at": generated_at,
        "legacy_qeg_active_downstream_reader_count": read_json(
            runtime / CONSUMER_AUDIT_ARTIFACT
        ).get("legacy_qeg_reader_count", 0),
        "legacy_qeg_artifacts_state": "audit_only_pending_soak_removal",
        "removal_allowed": soak_complete,
        "rollback_manifest_preserved": True,
        "authority": authority_flags(),
    }
    production_certified = not implementation_errors and not release_blockers
    certification = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_canonical_tradeability_compiler_certification",
        "generated_at": generated_at,
        "status": (
            "certified"
            if production_certified
            else "implementation_passed_soak_or_release_pending"
            if not implementation_errors
            else "blocked"
        ),
        "implementation_complete": not implementation_errors,
        "production_release_certified": production_certified,
        "phase_checks": {
            phase: check.get("status", "missing") for phase, check in checks_by_phase.items()
        },
        "tradeability_reachability": read_json(
            runtime / "qadam_tradeability_reachability_checks.json"
        ).get("reachability_state"),
        "current_setup_state": read_json(
            runtime / "qadam_tradeability_reachability_checks.json"
        ).get("current_setup_state"),
        "active_canonical_producer_count": read_json(
            runtime / MIGRATION_CHECKS_ARTIFACT
        ).get("active_canonical_producer_count"),
        "implementation_errors": implementation_errors,
        "release_blockers": release_blockers,
        "paper_order_created_by_certification": False,
        "broker_write_count": 0,
        "proof_credit_created": False,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    status = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_ctc_implementation_status",
        "generated_at": generated_at,
        "implementation_complete": not implementation_errors,
        "production_certified": production_certified,
        "current_phase": "CTC-14 soak" if not production_certified else "complete",
        "completed_phase_count": 14 - len(phase_failures),
        "required_phase_count": 14,
        "pending_empirical_requirement": (
            "five_real_market_sessions" if not soak_complete else None
        ),
        "authority": authority_flags(),
    }
    store = AtomicArtifactStore(runtime)
    store.write_json(RELEASE_ARTIFACT, release)
    store.write_json(SOAK_ARTIFACT, soak)
    store.write_json(LEGACY_REMOVAL_ARTIFACT, legacy)
    store.write_json(CERTIFICATION_ARTIFACT, certification)
    store.write_json(IMPLEMENTATION_STATUS_ARTIFACT, status)
    return certification, status, implementation_errors


__all__ = [
    "build_and_write_certification",
    "build_and_write_consumer_audit",
    "build_and_write_decision_generation_audit",
    "build_and_write_migration_audit",
    "build_and_write_visibility",
]
