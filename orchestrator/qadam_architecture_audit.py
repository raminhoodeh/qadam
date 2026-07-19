"""RF-1 no-change architecture and artifact ownership audit."""

from __future__ import annotations

import ast
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
import re
from typing import Any, Iterable

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    authority_flags,
    now_iso,
    runtime_dir,
    unique_errors,
    validate_authority,
    write_json_atomic,
)

SCHEMA_VERSION = "qadam_architecture_audit.v1"
PHASE_ID = "RF-1"

INVENTORY_ARTIFACT = "qadam_architecture_inventory.json"
EDGE_GRAPH_ARTIFACT = "qadam_edge_path_dependency_graph.json"
PRODUCER_CONSUMER_ARTIFACT = "qadam_artifact_producer_consumer_map.json"
DECISIONS_ARTIFACT = "qadam_architecture_refactor_decisions.jsonl"
CHECK_ARTIFACT = "qadam_architecture_audit_checks.json"

SCAN_ROOTS = ("orchestrator", "scripts")
ARTIFACT_PATTERN = re.compile(r"[A-Za-z0-9_.-]+\.jsonl?")
SCRIPT_PATTERN = re.compile(r"scripts/[A-Za-z0-9_.-]+\.(?:py|js|sh)")

WRITE_TOKENS = (
    "write_text(",
    "write_json",
    "_write_json",
    "append_jsonl",
    "_append_jsonl",
    "atomic_write",
    "os.replace(",
)
READ_TOKENS = (
    "read_text(",
    "read_json",
    "_read_json",
    "read_jsonl",
    "_read_jsonl",
    "json.load",
)

EDGE_STAGES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("source", ("adapter", "source", "acled", "gdelt", "reddit", "telegram_inbound")),
    ("storage", ("store", "storage", "postgres", "timescale", "artifact")),
    ("evidence", ("evidence", "source_price", "memory")),
    ("feature", ("feature", "market_context", "confirmation")),
    ("score", ("pattern", "score", "quantum")),
    ("label", ("label", "forward_window", "outcome")),
    ("backtest", ("backtest", "historical", "replay")),
    ("edge", ("edge", "validated_edge")),
    ("strategy", ("strategy", "hypothesis")),
    ("akber", ("akber", "signal_integrity")),
    ("risk", ("risk", "drawdown", "portfolio")),
    ("router", ("router", "handoff")),
    ("paperops", ("paperops", "alpaca_paper", "staged_order")),
    ("lifecycle", ("lifecycle", "position", "fill", "close_to_ledger")),
    ("learning", ("learning", "postmortem", "attribution")),
    ("dashboard", ("dashboard", "cockpit", "telegram")),
)

SAFETY_TERMS = (
    "paperops",
    "broker",
    "authority",
    "risk",
    "execution",
    "proof",
    "live_capital",
    "drawdown",
    "idempotency",
)


def _paths(settings: Settings | None = None) -> dict[str, Path]:
    runtime = runtime_dir(settings)
    return {
        "inventory": runtime / INVENTORY_ARTIFACT,
        "edge_graph": runtime / EDGE_GRAPH_ARTIFACT,
        "producer_consumer": runtime / PRODUCER_CONSUMER_ARTIFACT,
        "decisions": runtime / DECISIONS_ARTIFACT,
        "checks": runtime / CHECK_ARTIFACT,
    }


def _source_files() -> list[Path]:
    files: list[Path] = []
    for root_name in SCAN_ROOTS:
        root = ROOT / root_name
        if not root.exists():
            continue
        for suffix in ("*.py", "*.js", "*.sh"):
            files.extend(path for path in root.rglob(suffix) if path.is_file())
    return sorted(set(files))


def _module_name(path: Path) -> str:
    relative = path.relative_to(ROOT)
    if relative.suffix != ".py":
        return str(relative)
    return ".".join(relative.with_suffix("").parts)


def _classification(path: Path, source: str) -> list[str]:
    relative = str(path.relative_to(ROOT)).lower()
    labels: set[str] = set()
    if relative.startswith("scripts/check_"):
        labels.add("validation")
    if any(term in relative for term in SAFETY_TERMS) or any(
        term in source.lower() for term in ("broker_write_allowed", "live_capital_enabled")
    ):
        labels.add("safety_critical")
    if "fixture" in relative or "synthetic" in relative:
        labels.add("fixture_or_synthetic")
    if "qsase" in relative or re.search(r"phase[0-9]", relative):
        labels.add("compatibility_generation")
    if any(
        token in relative
        for token in (
            "qadam_operator_ready",
            "qadam_refactor_baseline",
            "qadam_dynamic_plan",
            "qadam_architecture_audit",
        )
    ):
        labels.add("wave0_canonical")
    if not labels:
        labels.add("supporting_or_unclassified")
    return sorted(labels)


def _python_imports(path: Path, source: str) -> list[str]:
    if path.suffix != ".py":
        return []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return sorted(imports)


def _file_record(path: Path) -> dict[str, Any]:
    relative = str(path.relative_to(ROOT))
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        source = ""
    artifact_names = sorted(set(ARTIFACT_PATTERN.findall(source)))
    command_targets = sorted(set(SCRIPT_PATTERN.findall(source)))
    imports = _python_imports(path, source)
    write_capable = any(token in source for token in WRITE_TOKENS)
    read_capable = any(token in source for token in READ_TOKENS)
    return {
        "path": relative,
        "module": _module_name(path),
        "suffix": path.suffix,
        "size_bytes": path.stat().st_size,
        "classifications": _classification(path, source),
        "imports": imports,
        "artifact_names": artifact_names,
        "command_targets": command_targets,
        "artifact_write_capable": write_capable,
        "artifact_read_capable": read_capable,
        "direct_json_coupling": bool(artifact_names and (write_capable or read_capable)),
    }


def _local_import_edges(records: list[dict[str, Any]]) -> list[dict[str, str]]:
    local_modules = {record["module"] for record in records if record["suffix"] == ".py"}
    edges: set[tuple[str, str]] = set()
    for record in records:
        if record["suffix"] != ".py":
            continue
        for imported in record["imports"]:
            candidates = [module for module in local_modules if imported == module or imported.startswith(module + ".")]
            if candidates:
                target = max(candidates, key=len)
                if target != record["module"]:
                    edges.add((record["module"], target))
    return [{"source": source, "target": target} for source, target in sorted(edges)]


def _strongly_connected_components(
    nodes: Iterable[str], edges: list[dict[str, str]]
) -> list[list[str]]:
    graph: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        graph[edge["source"]].append(edge["target"])
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    components: list[list[str]] = []

    def visit(node: str) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for target in graph.get(node, []):
            if target not in indices:
                visit(target)
                lowlinks[node] = min(lowlinks[node], lowlinks[target])
            elif target in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[target])
        if lowlinks[node] == indices[node]:
            component: list[str] = []
            while stack:
                member = stack.pop()
                on_stack.remove(member)
                component.append(member)
                if member == node:
                    break
            if len(component) > 1:
                components.append(sorted(component))

    for node in sorted(set(nodes)):
        if node not in indices:
            visit(node)
    return sorted(components)


def _artifact_map(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    artifact_records: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {"producers": set(), "consumers": set(), "references": set()}
    )
    for record in records:
        for artifact in record["artifact_names"]:
            artifact_records[artifact]["references"].add(record["path"])
            if record["artifact_write_capable"]:
                artifact_records[artifact]["producers"].add(record["path"])
            if record["artifact_read_capable"]:
                artifact_records[artifact]["consumers"].add(record["path"])
    output: list[dict[str, Any]] = []
    for artifact, mapping in sorted(artifact_records.items()):
        output.append(
            {
                "artifact": artifact,
                "producers": sorted(mapping["producers"]),
                "consumers": sorted(mapping["consumers"]),
                "references": sorted(mapping["references"]),
                "producer_count": len(mapping["producers"]),
                "consumer_count": len(mapping["consumers"]),
                "ownership_state": (
                    "unresolved_multiple_producer_candidates"
                    if len(mapping["producers"]) > 1
                    else "single_producer_candidate"
                    if len(mapping["producers"]) == 1
                    else "no_static_producer_detected"
                ),
                "analysis_method": "static_string_and_write_token_heuristic",
            }
        )
    return output


def _edge_path(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stages: list[dict[str, Any]] = []
    for stage, tokens in EDGE_STAGES:
        components = [
            record["path"]
            for record in records
            if any(token in record["path"].lower() for token in tokens)
        ]
        artifacts = sorted(
            {
                artifact
                for record in records
                if record["path"] in components
                for artifact in record["artifact_names"]
            }
        )
        stages.append(
            {
                "stage": stage,
                "position": len(stages) + 1,
                "component_count": len(components),
                "components": components,
                "artifact_count": len(artifacts),
                "artifacts": artifacts,
            }
        )
    return stages


def build_architecture_audit(settings: Settings | None = None) -> dict[str, Any]:
    files = _source_files()
    records = [_file_record(path) for path in files]
    import_edges = _local_import_edges(records)
    cycles = _strongly_connected_components(
        (record["module"] for record in records if record["suffix"] == ".py"),
        import_edges,
    )
    artifacts = _artifact_map(records)
    edge_path = _edge_path(records)
    command_edges = [
        {"source": record["path"], "target": target}
        for record in records
        for target in record["command_targets"]
    ]
    inventory = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_architecture_inventory",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "inventory_complete",
        "analysis_mode": "read_only_static_analysis",
        "source_file_count": len(records),
        "python_file_count": sum(record["suffix"] == ".py" for record in records),
        "javascript_file_count": sum(record["suffix"] == ".js" for record in records),
        "shell_file_count": sum(record["suffix"] == ".sh" for record in records),
        "direct_json_coupling_file_count": sum(record["direct_json_coupling"] for record in records),
        "safety_critical_file_count": sum(
            "safety_critical" in record["classifications"] for record in records
        ),
        "compatibility_generation_file_count": sum(
            "compatibility_generation" in record["classifications"] for record in records
        ),
        "records": records,
        "authority": authority_flags(),
    }
    edge_graph = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_edge_path_dependency_graph",
        "generated_at": now_iso(),
        "status": "edge_path_mapped",
        "stage_count": len(edge_path),
        "stages": edge_path,
        "local_import_edge_count": len(import_edges),
        "local_import_edges": import_edges,
        "import_cycle_count": len(cycles),
        "import_cycles": cycles,
        "command_edge_count": len(command_edges),
        "command_edges": command_edges,
        "execution_boundary_terms": list(SAFETY_TERMS),
        "authority": authority_flags(),
    }
    producer_consumer = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_artifact_producer_consumer_map",
        "generated_at": now_iso(),
        "status": "artifact_references_mapped",
        "analysis_method": "static_string_and_write_token_heuristic",
        "artifact_count": len(artifacts),
        "multiple_producer_candidate_count": sum(
            record["producer_count"] > 1 for record in artifacts
        ),
        "no_static_producer_count": sum(record["producer_count"] == 0 for record in artifacts),
        "artifacts": artifacts,
        "authority": authority_flags(),
    }
    decisions = build_refactor_decisions(inventory, edge_graph, producer_consumer)
    return {
        "inventory": inventory,
        "edge_graph": edge_graph,
        "producer_consumer": producer_consumer,
        "decisions": decisions,
    }


def build_refactor_decisions(
    inventory: dict[str, Any],
    edge_graph: dict[str, Any],
    producer_consumer: dict[str, Any],
) -> list[dict[str, Any]]:
    generated_at = now_iso()
    return [
        {
            "decision_id": "rf1:canonical-artifact-ownership",
            "generated_at": generated_at,
            "state": "accepted_for_rf3",
            "decision": "Introduce one canonical owner per Wave 0 domain artifact.",
            "reason": (
                f"Static analysis found {producer_consumer['multiple_producer_candidate_count']} "
                "artifact names with multiple producer candidates."
            ),
            "behavior_change_allowed": False,
        },
        {
            "decision_id": "rf1:compatibility-readers",
            "generated_at": generated_at,
            "state": "accepted_for_rf3",
            "decision": "Retain existing artifacts behind declared compatibility readers.",
            "reason": (
                f"{inventory['compatibility_generation_file_count']} files belong to earlier "
                "QSASE or numbered-phase generations."
            ),
            "behavior_change_allowed": False,
        },
        {
            "decision_id": "rf1:boundary-separation",
            "generated_at": generated_at,
            "state": "accepted_for_rf4_rf5",
            "decision": "Separate provider/research and decision/execution interfaces.",
            "reason": (
                f"The edge graph contains {edge_graph['local_import_edge_count']} local import "
                "edges and direct artifact coupling across the decision path."
            ),
            "behavior_change_allowed": False,
        },
        {
            "decision_id": "rf1:no-mass-deletion",
            "generated_at": generated_at,
            "state": "accepted_for_rf6",
            "decision": "Quarantine legacy paths through metadata before any deletion review.",
            "reason": "Static ownership heuristics cannot prove dead code safely.",
            "behavior_change_allowed": False,
        },
    ]


def validate_architecture_audit(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    inventory = bundle.get("inventory") if isinstance(bundle.get("inventory"), dict) else {}
    edge_graph = bundle.get("edge_graph") if isinstance(bundle.get("edge_graph"), dict) else {}
    producer = (
        bundle.get("producer_consumer")
        if isinstance(bundle.get("producer_consumer"), dict)
        else {}
    )
    if inventory.get("source_file_count", 0) < 100:
        errors.append("architecture_inventory_implausibly_small")
    if edge_graph.get("stage_count") != len(EDGE_STAGES):
        errors.append("edge_path_stage_count_mismatch")
    stages = edge_graph.get("stages") if isinstance(edge_graph.get("stages"), list) else []
    if [stage.get("stage") for stage in stages] != [stage for stage, _ in EDGE_STAGES]:
        errors.append("edge_path_stage_order_mismatch")
    for stage in stages:
        if stage.get("component_count", 0) < 1:
            errors.append(f"edge_path_stage_unmapped:{stage.get('stage')}")
    if producer.get("artifact_count", 0) < 1:
        errors.append("artifact_map_empty")
    if len(bundle.get("decisions", [])) < 4:
        errors.append("refactor_decisions_incomplete")
    for section_name, section in (
        ("inventory", inventory),
        ("edge_graph", edge_graph),
        ("producer_consumer", producer),
    ):
        errors.extend(validate_authority(section.get("authority", {}), prefix=section_name))
    return unique_errors(errors)


def validate_negative_architecture_probes(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing_stage = deepcopy(bundle)
    missing_stage["edge_graph"]["stages"] = missing_stage["edge_graph"]["stages"][:-1]
    missing_stage["edge_graph"]["stage_count"] -= 1
    if "edge_path_stage_count_mismatch" not in validate_architecture_audit(missing_stage):
        errors.append("rf1_missing_stage_probe_not_rejected")
    unsafe = deepcopy(bundle)
    unsafe["inventory"]["authority"]["broker_write_allowed"] = True
    if "inventory_forbidden_true:broker_write_allowed" not in validate_architecture_audit(unsafe):
        errors.append("rf1_authority_probe_not_rejected")
    empty_artifacts = deepcopy(bundle)
    empty_artifacts["producer_consumer"]["artifact_count"] = 0
    empty_artifacts["producer_consumer"]["artifacts"] = []
    if "artifact_map_empty" not in validate_architecture_audit(empty_artifacts):
        errors.append("rf1_empty_artifact_probe_not_rejected")
    return unique_errors(errors)


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    text = "".join(
        __import__("json").dumps(record, sort_keys=True, default=str) + "\n"
        for record in records
    )
    from orchestrator.qadam_operator_ready_common import atomic_write_text

    atomic_write_text(path, text)


def build_and_write_architecture_audit(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    paths = _paths(settings)
    bundle = build_architecture_audit(settings)
    errors = validate_architecture_audit(bundle)
    errors.extend(validate_negative_architecture_probes(bundle))
    errors = unique_errors(errors)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_architecture_audit_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "validation_errors": errors,
        "negative_probe_count": 3,
        "behavior_changed": False,
        "authority": authority_flags(),
    }
    write_json_atomic(paths["inventory"], bundle["inventory"])
    write_json_atomic(paths["edge_graph"], bundle["edge_graph"])
    write_json_atomic(paths["producer_consumer"], bundle["producer_consumer"])
    _write_jsonl(paths["decisions"], bundle["decisions"])
    write_json_atomic(paths["checks"], checks)
    return bundle, checks, errors
