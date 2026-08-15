"""AR-0/AR-1 baseline, supply-chain and sandbox policy checks."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

from orchestrator.agent_reach_bridge import build_agent_reach_bridge_status
from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_qualitative_common import (
    AGENT_REACH_BASELINE_ARTIFACT,
    AGENT_REACH_LOCK_PATH,
    AGENT_REACH_SANDBOX_ARTIFACT,
    AGENT_REACH_SUPPLY_CHAIN_ARTIFACT,
    COMMAND_POLICY_PATH,
    ORIGIN_REGISTRY_PATH,
    QUALITATIVE_GAP_MAP_ARTIFACT,
    SOURCE_COUNT_CONTRACT_ARTIFACT,
    now_iso,
    public_authority,
    read_json,
    read_jsonl,
    repo_root,
    runtime_dir,
    sha256_json,
)


def _tree_hash(path: Path) -> str:
    digest = hashlib.sha256()
    if not path.is_dir():
        return ""
    for item in sorted(value for value in path.rglob("*") if value.is_file() and value.name != ".DS_Store"):
        digest.update(str(item.relative_to(path)).encode("utf-8"))
        digest.update(hashlib.sha256(item.read_bytes()).digest())
    return digest.hexdigest()


def _akber_gap_map(runtime: Path) -> dict[str, Any]:
    rows = read_jsonl(runtime / "qadam_akber_filter_v3_inputs.jsonl")
    missing = Counter()
    adverse = Counter()
    for row in rows:
        context = row.get("context") if isinstance(row.get("context"), dict) else {}
        for field, value in context.items():
            if not isinstance(value, dict):
                continue
            state = str(value.get("state") or "")
            if state in {"missing", "stale", "unavailable", "not_available"} or value.get("available") is False:
                missing[str(field)] += 1
            if state in {"adverse", "veto", "unsafe", "failed"}:
                adverse[str(field)] += 1
    return {
        "akber_input_count": len(rows),
        "missing_field_counts": dict(sorted(missing.items())),
        "adverse_field_counts": dict(sorted(adverse.items())),
        "context_or_catalyst_missing_count": sum(
            count for field, count in missing.items() if field in {"source_price_context", "fresh_catalyst"}
        ),
    }


def build_agent_reach_baseline(settings: Settings | None = None) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    generated_at = now_iso()
    bridge = build_agent_reach_bridge_status(settings=settings)
    origin_registry = read_json(repo_root() / ORIGIN_REGISTRY_PATH)
    enabled_origins = [
        row
        for row in origin_registry.get("origins") or []
        if isinstance(row, dict) and row.get("enabled") is True
    ]
    sources = read_json(runtime / "qsase_source_universe.json")
    instruments = read_json(runtime / "qsase_trading_universe.json")
    patterns = read_jsonl(runtime / "qadam_pattern_score_v3_records.jsonl")
    hypotheses = read_jsonl(runtime / "qadam_strategy_hypotheses_v3.jsonl")
    shadows = read_jsonl(runtime / "qadam_forward_shadow_decisions.jsonl")
    router = read_jsonl(runtime / "qadam_router_v3_decisions.jsonl")
    errors: list[str] = []
    if sources.get("source_count") != 41:
        errors.append("canonical_source_count_not_41")
    if instruments.get("watched_market_count") != 19:
        errors.append("canonical_instrument_count_not_19")
    if bridge.get("counts_as_canonical_source") is not False:
        errors.append("agent_reach_changed_canonical_source_count")
    source_contract = {
        "schema_version": "qadam_source_count_contract.v1",
        "artifact_type": "qadam_source_count_contract",
        "generated_at": generated_at,
        "status": "passed" if not errors else "blocked",
        "canonical_source_count": sources.get("source_count"),
        "legacy_bridge_registry_count": bridge.get("canonical_source_count"),
        "legacy_bridge_registry_count_is_not_canonical": True,
        "canonical_instrument_count": instruments.get("watched_market_count"),
        "qualitative_transport_count": bridge.get("mapped_channel_count"),
        "qualitative_origin_count": len(enabled_origins),
        "transport_included_in_canonical_source_count": False,
        "source_count_owner": "qsase_source_universe",
        "authority": public_authority(),
    }
    gap_map = {
        "schema_version": "qadam_qualitative_evidence_gap_map.v1",
        "artifact_type": "qadam_qualitative_evidence_gap_map",
        "generated_at": generated_at,
        **_akber_gap_map(runtime),
        "pattern_count": len(patterns),
        "strategy_hypothesis_count": len(hypotheses),
        "shadow_decision_count": len(shadows),
        "router_decision_count": len(router),
        "authority": public_authority(),
    }
    baseline = {
        "schema_version": "qadam_agent_reach_baseline.v1",
        "artifact_type": "qadam_agent_reach_baseline",
        "generated_at": generated_at,
        "status": "passed" if not errors else "blocked",
        "source_contract": source_contract,
        "gap_map": gap_map,
        "agent_reach_bridge_status": bridge.get("status"),
        "active_specification": "docs/qadam-agent-reach-qualitative-evidence-enrichment-implementation-plan.md",
        "historical_note_is_not_active_specification": True,
        "validation_errors": errors,
        "authority": public_authority(),
    }
    store = AtomicArtifactStore(runtime)
    store.write_json(AGENT_REACH_BASELINE_ARTIFACT, baseline)
    store.write_json(SOURCE_COUNT_CONTRACT_ARTIFACT, source_contract)
    store.write_json(QUALITATIVE_GAP_MAP_ARTIFACT, gap_map)
    return baseline, errors


def build_agent_reach_sandbox(settings: Settings | None = None) -> tuple[dict[str, Any], list[str]]:
    generated_at = now_iso()
    root = repo_root()
    runtime = runtime_dir(settings)
    lock = read_json(root / AGENT_REACH_LOCK_PATH)
    policy = read_json(root / COMMAND_POLICY_PATH)
    reference = root / str(lock.get("reference_path") or "Agent-Reach-main")
    observed_tree_hash = _tree_hash(reference)
    worker = root / str(policy.get("allowed_worker") or "")
    errors: list[str] = []
    if not reference.is_dir():
        errors.append("agent_reach_reference_missing")
    if observed_tree_hash != lock.get("reference_tree_sha256"):
        errors.append("agent_reach_reference_hash_drift")
    if lock.get("runtime_import_allowed") is not False:
        errors.append("agent_reach_runtime_import_not_disabled")
    if lock.get("auto_update_allowed") is not False or lock.get("system_install_allowed") is not False:
        errors.append("agent_reach_mutating_install_path_enabled")
    if not worker.is_file():
        errors.append("sandbox_worker_missing")
    for field in (
        "authenticated_transports_enabled",
        "browser_session_access_allowed",
        "cookie_access_allowed",
        "home_directory_read_allowed",
        "arbitrary_command_allowed",
    ):
        if policy.get(field) is not False:
            errors.append(f"sandbox_policy_forbidden_true:{field}")
    allowed_transports = set(policy.get("allowed_transports") or [])
    if not allowed_transports or allowed_transports - {"official_web", "rss", "github_api"}:
        errors.append("sandbox_transport_allowlist_invalid")
    source_text = worker.read_text(encoding="utf-8") if worker.is_file() else ""
    for forbidden in ("subprocess", "os.system", "eval(", "exec(", "pickle", "browser_cookie"):
        if forbidden in source_text:
            errors.append(f"sandbox_worker_forbidden_primitive:{forbidden}")
    supply_chain = {
        "schema_version": "qadam_agent_reach_supply_chain_audit.v1",
        "artifact_type": "qadam_agent_reach_supply_chain_audit",
        "generated_at": generated_at,
        "status": "passed" if not errors else "blocked",
        "pinned_reference": lock,
        "observed_reference_tree_sha256": observed_tree_hash,
        "runtime_import_allowed": False,
        "license_manifest": [
            {"component": "Agent Reach reference", "license": "MIT", "runtime_imported": False},
            {"component": "Python standard library worker", "license": "PSF", "runtime_imported": True},
        ],
        "validation_errors": errors,
        "authority": public_authority(),
    }
    sandbox = {
        "schema_version": "qadam_agent_reach_sandbox_status.v1",
        "artifact_type": "qadam_agent_reach_sandbox_status",
        "generated_at": generated_at,
        "status": "passed" if not errors else "blocked",
        "worker": str(worker.relative_to(root)) if worker.is_file() else None,
        "sandbox_exec_available": shutil.which("sandbox-exec") is not None,
        "filtered_environment_required": True,
        "write_only_spool_required": True,
        "network_domain_allowlist_required": True,
        "secret_access_allowed": False,
        "browser_session_access_allowed": False,
        "cookie_access_allowed": False,
        "arbitrary_command_allowed": False,
        "policy_hash": sha256_json(policy),
        "validation_errors": errors,
        "authority": public_authority(),
    }
    store = AtomicArtifactStore(runtime)
    store.write_json(AGENT_REACH_SUPPLY_CHAIN_ARTIFACT, supply_chain)
    store.write_json(AGENT_REACH_SANDBOX_ARTIFACT, sandbox)
    return sandbox, errors


def run_baseline_and_sandbox(settings: Settings | None = None) -> dict[str, Any]:
    baseline, baseline_errors = build_agent_reach_baseline(settings)
    sandbox, sandbox_errors = build_agent_reach_sandbox(settings)
    errors = sorted(set([*baseline_errors, *sandbox_errors]))
    return {
        "status": "passed" if not errors else "blocked",
        "baseline": baseline,
        "sandbox": sandbox,
        "validation_errors": errors,
    }


__all__ = ["build_agent_reach_baseline", "build_agent_reach_sandbox", "run_baseline_and_sandbox"]
