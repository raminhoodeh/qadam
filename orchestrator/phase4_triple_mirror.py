"""Phase 4 Triple-Mirror Audit.

The audit compares plan intent, Resource Registry mapping, and observed
runtime posture. It is advisory except for authority mismatches, which fail
closed because Phase 4 cannot create trade, order, broker, quantum-provider,
hardware, scheduler, or live-capital authority.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.phase4_artifacts import (
    PHASE4_ARTIFACT_SCHEMA_VERSION,
    phase4_authority_boundary,
    validate_phase4_artifact,
)
from orchestrator.resource_registry import resource_registry


TRIPLE_MIRROR_AUDIT_SCHEMA_VERSION = 1

DRIFT_STATUSES: tuple[str, ...] = (
    "aligned",
    "missing_runtime",
    "implemented_not_documented",
    "resource_unmapped",
    "authority_mismatch",
)

PLAN_EXPECTATIONS: tuple[dict[str, Any], ...] = (
    {
        "key": "triple_mirror_audit",
        "docs_terms": ("Triple-Mirror Audit", "Q4-2"),
        "resource_modules": ("strategy_manifestation", "resource_registry"),
        "runtime_sections": ("mission_control",),
    },
    {
        "key": "data_veracity_audit",
        "docs_terms": ("Data Veracity Audit", "Trust Score recalculation"),
        "resource_modules": ("event_log", "market_pipeline"),
        "runtime_sections": ("durable_ingestion", "watching", "source_pipeline_summary"),
    },
    {
        "key": "strategy_manifestation",
        "docs_terms": ("Manifested Strategy Document", "Strategy toggles"),
        "resource_modules": ("strategy_manifestation", "strategy_lead", "signal_review"),
        "runtime_sections": ("cognition", "trade_layer"),
    },
    {
        "key": "runtime_safety_chain",
        "docs_terms": ("Risk Agent", "Execution Policy", "No execution"),
        "resource_modules": ("risk_agent", "execution_registry"),
        "runtime_sections": (
            "risk_agent",
            "execution_policy",
            "staged_paper_order",
            "broker_reconciliation",
            "paper_submit_receipt",
            "capital",
        ),
    },
    {
        "key": "head_of_quant_role",
        "docs_terms": ("quantum role", "Head of Quant"),
        "resource_modules": ("quant_plane",),
        "runtime_sections": ("quantum_oracle",),
    },
    {
        "key": "supplemental_market_confirmation",
        "docs_terms": ("Yahoo Finance", "supplemental market confirmation"),
        "resource_modules": ("market_pipeline",),
        "runtime_sections": ("yahoo_finance",),
    },
    {
        "key": "world_model_boundary",
        "docs_terms": ("World-model lens validation", "private priors"),
        "resource_modules": ("world_model",),
        "runtime_sections": ("decision_philosophy",),
    },
)

AUTHORITY_PROBES: tuple[dict[str, Any], ...] = (
    {
        "name": "durable_replay_write_authority",
        "path": ("durable_ingestion", "write_authority"),
        "allowed": False,
    },
    {
        "name": "durable_replay_signal_authority",
        "path": ("durable_ingestion", "signal_authority"),
        "allowed": False,
    },
    {
        "name": "durable_replay_order_authority",
        "path": ("durable_ingestion", "order_authority"),
        "allowed": False,
    },
    {
        "name": "risk_agent_execution_allowed_count",
        "path": ("risk_agent", "execution_allowed_count"),
        "allowed": 0,
    },
    {
        "name": "risk_agent_paper_order_allowed_count",
        "path": ("risk_agent", "paper_order_allowed_count"),
        "allowed": 0,
    },
    {
        "name": "risk_agent_broker_write_allowed_count",
        "path": ("risk_agent", "broker_write_allowed_count"),
        "allowed": 0,
    },
    {
        "name": "execution_policy_execution_allowed_count",
        "path": ("execution_policy", "execution_allowed_count"),
        "allowed": 0,
    },
    {
        "name": "execution_policy_staged_paper_order_allowed_count",
        "path": ("execution_policy", "staged_paper_order_allowed_count"),
        "allowed": 0,
    },
    {
        "name": "execution_policy_broker_write_allowed_count",
        "path": ("execution_policy", "broker_write_allowed_count"),
        "allowed": 0,
    },
    {
        "name": "staged_paper_order_execution_allowed_count",
        "path": ("staged_paper_order", "execution_allowed_count"),
        "allowed": 0,
    },
    {
        "name": "staged_paper_order_broker_write_allowed_count",
        "path": ("staged_paper_order", "broker_write_allowed_count"),
        "allowed": 0,
    },
    {
        "name": "broker_reconciliation_broker_write_allowed_count",
        "path": ("broker_reconciliation", "broker_write_allowed_count"),
        "allowed": 0,
    },
    {
        "name": "paper_submit_receipt_broker_write_allowed_count",
        "path": ("paper_submit_receipt", "broker_write_allowed_count"),
        "allowed": 0,
    },
    {
        "name": "paper_submit_receipt_broker_post_called_count",
        "path": ("paper_submit_receipt", "broker_post_called_count"),
        "allowed": 0,
    },
    {
        "name": "paper_account_write_authority",
        "path": ("capital", "write_authority"),
        "allowed": False,
    },
    {
        "name": "paper_account_live_capital_enabled",
        "path": ("capital", "live_capital_enabled"),
        "allowed": False,
    },
    {
        "name": "quantum_oracle_hardware_submitted_count",
        "path": ("quantum_oracle", "hardware_submitted_count"),
        "allowed": 0,
    },
    {
        "name": "quantum_oracle_execution_allowed_count",
        "path": ("quantum_oracle", "execution_allowed_count"),
        "allowed": 0,
    },
    {
        "name": "quantum_oracle_paper_order_allowed_count",
        "path": ("quantum_oracle", "paper_order_allowed_count"),
        "allowed": 0,
    },
    {
        "name": "quantum_oracle_trade_candidate_created_count",
        "path": ("quantum_oracle", "trade_candidate_created_count"),
        "allowed": 0,
    },
    {
        "name": "quantum_scheduler_enabled",
        "path": ("quantum_oracle", "scheduler_dry_run", "scheduler_enabled"),
        "allowed": False,
    },
    {
        "name": "yahoo_finance_signal_authority",
        "path": ("yahoo_finance", "signal_authority"),
        "allowed": False,
    },
    {
        "name": "yahoo_finance_broker_write_authority",
        "path": ("yahoo_finance", "broker_write_authority"),
        "allowed": False,
    },
    {
        "name": "yahoo_finance_live_capital_authority",
        "path": ("yahoo_finance", "live_capital_authority"),
        "allowed": False,
    },
    {
        "name": "trade_layer_execution_allowed_count",
        "path": ("trade_layer", "summary", "execution_allowed_count"),
        "allowed": 0,
    },
    {
        "name": "trade_layer_paper_order_allowed_count",
        "path": ("trade_layer", "summary", "paper_order_allowed_count"),
        "allowed": 0,
    },
)


@dataclass(frozen=True)
class MirrorFinding:
    key: str
    drift_status: str
    summary: str
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _latest_cockpit_status(settings: Settings | None = None) -> tuple[dict[str, Any], str]:
    runtime_path = _runtime_dir(settings) / "cockpit-status.json"
    if runtime_path.exists():
        return json.loads(runtime_path.read_text(encoding="utf-8")), str(runtime_path)
    from orchestrator.cockpit_status import build_cockpit_status

    return build_cockpit_status(settings), "generated_in_process"


def _path_get(payload: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _docs_mirror(root: Path) -> dict[str, Any]:
    files = {
        "master": root / "docs/qadam-master-implementation-plan.md",
        "phase4": root / "docs/qadam-phase-4-implementation-plan.md",
        "modular": root / "docs/qadam-modular-implementation-plan.md",
    }
    text_by_name = {name: _read_text(path) for name, path in files.items()}
    combined = "\n".join(text_by_name.values())
    expectation_rows: list[dict[str, Any]] = []
    missing_terms: list[str] = []
    for expectation in PLAN_EXPECTATIONS:
        terms = tuple(str(term) for term in expectation["docs_terms"])
        present_terms = [term for term in terms if term.lower() in combined.lower()]
        absent_terms = [term for term in terms if term not in present_terms]
        missing_terms.extend(f"{expectation['key']}:{term}" for term in absent_terms)
        expectation_rows.append(
            {
                "key": expectation["key"],
                "present_terms": present_terms,
                "missing_terms": absent_terms,
            }
        )
    return {
        "status": "aligned" if not missing_terms else "implemented_not_documented",
        "file_count": len(files),
        "expectation_count": len(PLAN_EXPECTATIONS),
        "missing_term_count": len(missing_terms),
        "missing_terms": missing_terms,
        "expectations": expectation_rows,
        "files": {name: str(path) for name, path in files.items()},
        "boundary": "Plan mirror is documentation evidence only; it cannot promote strategy or execution state.",
    }


def _resource_mirror() -> dict[str, Any]:
    resources = resource_registry()
    module_to_resources: dict[str, list[str]] = {}
    unmapped_resources: list[str] = []
    for resource in resources:
        mapped = tuple(resource.get("mapped_modules") or ())
        if not mapped:
            unmapped_resources.append(str(resource.get("key")))
        for module in mapped:
            module_to_resources.setdefault(str(module), []).append(str(resource.get("key")))
    expectation_rows: list[dict[str, Any]] = []
    missing_mappings: list[str] = []
    for expectation in PLAN_EXPECTATIONS:
        modules = tuple(str(module) for module in expectation["resource_modules"])
        mapped_modules = [module for module in modules if module in module_to_resources]
        absent_modules = [module for module in modules if module not in module_to_resources]
        missing_mappings.extend(f"{expectation['key']}:{module}" for module in absent_modules)
        expectation_rows.append(
            {
                "key": expectation["key"],
                "mapped_modules": mapped_modules,
                "missing_modules": absent_modules,
            }
        )
    production_active = [resource.get("key") for resource in resources if resource.get("production_active")]
    status = "aligned"
    if unmapped_resources or missing_mappings:
        status = "resource_unmapped"
    return {
        "status": status,
        "resource_count": len(resources),
        "module_count": len(module_to_resources),
        "unmapped_resource_count": len(unmapped_resources),
        "unmapped_resources": unmapped_resources,
        "missing_mapping_count": len(missing_mappings),
        "missing_mappings": missing_mappings,
        "production_active_count": len(production_active),
        "production_active": production_active,
        "expectations": expectation_rows,
        "boundary": "Resource mirror uses non-live references only; it cannot create live evidence or strategy approval.",
    }


def _runtime_mirror(cockpit_status: dict[str, Any], source: str) -> dict[str, Any]:
    missing_sections: list[str] = []
    expectation_rows: list[dict[str, Any]] = []
    for expectation in PLAN_EXPECTATIONS:
        sections = tuple(str(section) for section in expectation["runtime_sections"])
        present_sections = [section for section in sections if section in cockpit_status]
        absent_sections = [section for section in sections if section not in cockpit_status]
        missing_sections.extend(f"{expectation['key']}:{section}" for section in absent_sections)
        expectation_rows.append(
            {
                "key": expectation["key"],
                "present_sections": present_sections,
                "missing_sections": absent_sections,
            }
        )

    authority_mismatches: list[dict[str, Any]] = []
    authority_probe_rows: list[dict[str, Any]] = []
    for probe in AUTHORITY_PROBES:
        observed = _path_get(cockpit_status, tuple(probe["path"]))
        allowed = probe["allowed"]
        missing = observed is None
        mismatch = missing or observed != allowed
        row = {
            "name": probe["name"],
            "path": list(probe["path"]),
            "observed": observed,
            "allowed": allowed,
            "missing": missing,
            "mismatch": mismatch,
        }
        authority_probe_rows.append(row)
        if mismatch:
            authority_mismatches.append(row)

    durable = cockpit_status.get("durable_ingestion", {})
    yahoo = cockpit_status.get("yahoo_finance", {})
    quantum = cockpit_status.get("quantum_oracle", {})
    mission = cockpit_status.get("mission_control", {})
    status = "aligned"
    if missing_sections:
        status = "missing_runtime"
    if authority_mismatches:
        status = "authority_mismatch"
    return {
        "status": status,
        "source": source,
        "generated_at": cockpit_status.get("generated_at"),
        "schema_version": cockpit_status.get("schema_version"),
        "missing_section_count": len(missing_sections),
        "missing_sections": missing_sections,
        "authority_mismatch_count": len(authority_mismatches),
        "authority_mismatches": authority_mismatches,
        "authority_probes": authority_probe_rows,
        "expectations": expectation_rows,
        "headline": mission.get("headline"),
        "durable_replay": {
            "status": durable.get("status"),
            "contract_status": durable.get("contract_status"),
            "replay_status": durable.get("replay_status"),
            "replayed_source_count": durable.get("replayed_source_count"),
            "missing_source_count": durable.get("missing_source_count"),
        },
        "yahoo_finance": {
            "status": yahoo.get("status"),
            "enabled": yahoo.get("enabled"),
            "market_confirmation_role": yahoo.get("market_confirmation_role"),
            "canonical_source": yahoo.get("canonical_source"),
        },
        "quantum_oracle": {
            "status": quantum.get("status"),
            "backend": quantum.get("latest_backend"),
            "result_count": quantum.get("result_count"),
            "hardware_submitted_count": quantum.get("hardware_submitted_count"),
            "execution_allowed_count": quantum.get("execution_allowed_count"),
            "paper_order_allowed_count": quantum.get("paper_order_allowed_count"),
            "trade_candidate_created_count": quantum.get("trade_candidate_created_count"),
        },
        "boundary": "Runtime mirror is observed from public-safe cockpit status and remains read-only.",
    }


def _finding_status(*statuses: str) -> str:
    priority = ("authority_mismatch", "missing_runtime", "resource_unmapped", "implemented_not_documented", "aligned")
    for status in priority:
        if status in statuses:
            return status
    return "aligned"


def build_triple_mirror_audit(settings: Settings | None = None) -> dict[str, Any]:
    root = _repo_root()
    cockpit_status, cockpit_source = _latest_cockpit_status(settings)
    docs = _docs_mirror(root)
    resources = _resource_mirror()
    runtime = _runtime_mirror(cockpit_status, cockpit_source)
    drift_status = _finding_status(docs["status"], resources["status"], runtime["status"])
    findings = [
        MirrorFinding(
            key="plan_mirror",
            drift_status=docs["status"],
            summary="Phase 4 plan terms are present." if docs["status"] == "aligned" else "Plan terms need documentation follow-up.",
            evidence={
                "missing_term_count": docs["missing_term_count"],
                "missing_terms": docs["missing_terms"],
            },
        ),
        MirrorFinding(
            key="resource_mirror",
            drift_status=resources["status"],
            summary=(
                "Resource Registry mappings cover Phase 4 expectations."
                if resources["status"] == "aligned"
                else "Resource Registry mapping gaps were found."
            ),
            evidence={
                "resource_count": resources["resource_count"],
                "unmapped_resource_count": resources["unmapped_resource_count"],
                "missing_mapping_count": resources["missing_mapping_count"],
                "production_active_count": resources["production_active_count"],
                "missing_mappings": resources["missing_mappings"],
            },
        ),
        MirrorFinding(
            key="runtime_mirror",
            drift_status=runtime["status"],
            summary=(
                "Runtime status is observable and authority boundaries remain blocked."
                if runtime["status"] == "aligned"
                else "Runtime gaps or authority mismatches were found."
            ),
            evidence={
                "source": runtime["source"],
                "generated_at": runtime["generated_at"],
                "missing_section_count": runtime["missing_section_count"],
                "authority_mismatch_count": runtime["authority_mismatch_count"],
                "durable_replay": runtime["durable_replay"],
                "quantum_oracle": runtime["quantum_oracle"],
                "yahoo_finance": runtime["yahoo_finance"],
            },
        ),
    ]

    artifact = {
        "schema_version": PHASE4_ARTIFACT_SCHEMA_VERSION,
        "audit_schema_version": TRIPLE_MIRROR_AUDIT_SCHEMA_VERSION,
        "artifact_type": "triple_mirror_audit",
        "artifact_id": "phase4:q4-2:triple-mirror-audit",
        "status": "validated" if drift_status == "aligned" else "provisional",
        "generated_at": _now(),
        "public_safe": True,
        "authority_boundary": phase4_authority_boundary(),
        "boundary": "Triple-Mirror Audit is advisory and cannot promote strategy or execution authority.",
        "drift_status": drift_status,
        "mirror_count": 3,
        "authority_mismatch_count": runtime["authority_mismatch_count"],
        "docs_mirror": docs,
        "resource_mirror": resources,
        "runtime_mirror": runtime,
        "findings": [finding.to_dict() for finding in findings],
        "advisory_only": True,
        "resource_promotion_allowed": False,
        "strategy_promotion_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
    }
    artifact["validation_errors"] = validate_phase4_artifact(artifact)
    return artifact


def validate_triple_mirror_audit(artifact: dict[str, Any]) -> list[str]:
    errors = list(validate_phase4_artifact(artifact))
    if artifact.get("artifact_type") != "triple_mirror_audit":
        errors.append("artifact_type_not_triple_mirror_audit")
    if artifact.get("mirror_count") != 3:
        errors.append("mirror_count_mismatch")
    if artifact.get("advisory_only") is not True:
        errors.append("advisory_only_not_true")
    for key in ("resource_promotion_allowed", "strategy_promotion_allowed", "execution_allowed", "paper_order_allowed", "broker_write_allowed", "live_capital_enabled"):
        if artifact.get(key) is not False:
            errors.append(f"authority_enabled:{key}")
    runtime = artifact.get("runtime_mirror", {})
    if not isinstance(runtime, dict):
        errors.append("runtime_mirror_missing")
    else:
        if runtime.get("missing_section_count", 0) != 0:
            errors.append("runtime_sections_missing")
        if runtime.get("authority_mismatch_count", 0) != 0:
            errors.append("runtime_authority_mismatch")
    if artifact.get("drift_status") not in DRIFT_STATUSES:
        errors.append("drift_status_invalid")
    return errors


def write_triple_mirror_audit(
    artifact: dict[str, Any],
    path: str | Path | None = None,
    *,
    settings: Settings | None = None,
) -> Path:
    output_path = Path(path or (_runtime_dir(settings) / "phase4_triple_mirror_audit.json"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path
