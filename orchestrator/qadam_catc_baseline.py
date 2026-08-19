"""Read-only CATC baseline capture and implementation status management."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import plistlib
import subprocess
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import (
    now_iso,
    read_json,
    runtime_dir,
    write_json_atomic,
)

SCHEMA_VERSION = "qadam_catc_baseline.v1"
REPO_ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION_STATUS = "qadam_catc_implementation_status.json"
IMPLEMENTATION_LOG = REPO_ROOT / "docs" / "qadam-catc-implementation-log.md"

CONTROL_ARTIFACTS = (
    "qadam_tradeability_envelopes.jsonl",
    "qadam_akber_filter_v3_results.jsonl",
    "qadam_forward_shadow_records.jsonl",
    "qadam_portfolio_risk_proposals.jsonl",
    "qadam_router_v3_decisions.jsonl",
    "qadam_paperops_handoff_v3_records.jsonl",
    "qadam_paperops_handoff_v3_accepted.jsonl",
    "qadam_paperops_handoff_v3_receipts.jsonl",
    "paperops_paper_lifecycle_poller.json",
    "paperops_autonomous_pass_summary.json",
    "qadam_operator_service_status.json",
    "qadam_operator_service_receipts.jsonl",
    "qadam_operator_repair_requests.jsonl",
    "qadam_operator_dashboard_view_model.json",
    "cockpit-status.json",
)


def _run(*args: str) -> str:
    try:
        result = subprocess.run(
            args,
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip()


def _hash_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _classify(path: str) -> str:
    if path.startswith((".env", "data/runtime/qadam-secrets")):
        return "secret_excluded"
    if path.startswith("data/runtime/"):
        return "runtime_mutation"
    if path.startswith("tests/"):
        return "test_change"
    if path.startswith("docs/"):
        return "documentation_change"
    if path.startswith(("orchestrator/", "scripts/", "config/")):
        return "source_change"
    if path.startswith(("landing-page-repo/", "public/", "dashboard/")):
        return "public_snapshot_or_ui"
    return "unrelated_or_unclassified_user_work"


def worktree_inventory() -> dict[str, Any]:
    raw = _run("git", "status", "--porcelain=v1", "-z")
    rows: list[dict[str, Any]] = []
    for item in raw.split("\0"):
        if not item:
            continue
        status = item[:2]
        path = item[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        classification = _classify(path)
        absolute = REPO_ROOT / path
        rows.append(
            {
                "status": status,
                "path": path,
                "classification": classification,
                "exists": absolute.exists(),
                "size_bytes": absolute.stat().st_size if absolute.is_file() else None,
                "sha256": None if classification == "secret_excluded" else _hash_file(absolute),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_catc_worktree_inventory",
        "generated_at": now_iso(),
        "head_commit": _run("git", "rev-parse", "HEAD"),
        "branch": _run("git", "branch", "--show-current"),
        "dirty_entry_count": len(rows),
        "entries": rows,
        "secrets_excluded": True,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
    }


def artifact_inventory(runtime: Path) -> list[dict[str, Any]]:
    rows = []
    for name in CONTROL_ARTIFACTS:
        path = runtime / name
        rows.append(
            {
                "name": name,
                "exists": path.is_file(),
                "size_bytes": path.stat().st_size if path.is_file() else None,
                "modified_at": (
                    datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
                    if path.is_file()
                    else None
                ),
                "sha256": _hash_file(path),
            }
        )
    return rows


def service_inventory() -> dict[str, Any]:
    uid = str(Path.home().stat().st_uid)
    launch_output = _run("launchctl", "print", f"gui/{uid}/com.qadam.operator")
    plist_paths = (
        Path.home() / "Library" / "LaunchAgents" / "com.qadam.operator.plist",
        Path.home() / "Library" / "LaunchAgents" / "com.qadam.operator-exploratory-exit-manager.plist",
        Path.home() / "Library" / "LaunchAgents" / "com.qadam.daily-learning.plist",
    )
    services = []
    for path in plist_paths:
        record: dict[str, Any] = {
            "path": str(path),
            "exists": path.is_file(),
            "sha256": _hash_file(path),
        }
        if path.is_file():
            try:
                plist = plistlib.loads(path.read_bytes())
            except (OSError, plistlib.InvalidFileException):
                plist = {}
            record["label"] = plist.get("Label")
            record["program_arguments"] = plist.get("ProgramArguments", [])
            record["run_at_load"] = plist.get("RunAtLoad")
        services.append(record)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_catc_active_service_inventory",
        "generated_at": now_iso(),
        "operator_loaded": bool(launch_output),
        "operator_quiesced": not bool(launch_output),
        "launchctl_excerpt": launch_output[:2000],
        "services": services,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
    }


def broker_read_only_snapshot(runtime: Path) -> dict[str, Any]:
    lifecycle = read_json(runtime / "paperops_paper_lifecycle_poller.json")
    summary = read_json(runtime / "paperops_autonomous_pass_summary.json")
    account = read_json(runtime / "paper_account_status.json")
    if not account:
        account = read_json(runtime / "qadam_clean_broker_account_preflight.json")
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_catc_broker_read_only_snapshot",
        "generated_at": now_iso(),
        "source": "existing_local_read_only_broker_mirrors",
        "network_call_performed": False,
        "account": account,
        "lifecycle_summary": {
            key: lifecycle.get(key)
            for key in (
                "status",
                "order_count",
                "open_position_count",
                "closed_trade_count",
                "generated_at",
            )
        },
        "last_paperops_summary": {
            key: summary.get(key)
            for key in (
                "status",
                "paperops_cycle_state",
                "submitted_paper_order_count",
                "open_position_count",
                "closed_paper_trade_count",
                "generated_at",
            )
        },
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
    }


def capture_catc_baseline(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    runtime.mkdir(parents=True, exist_ok=True)
    worktree = worktree_inventory()
    service = service_inventory()
    broker = broker_read_only_snapshot(runtime)
    artifacts = artifact_inventory(runtime)
    baseline = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_catc_baseline",
        "generated_at": now_iso(),
        "status": "captured",
        "head_commit": worktree["head_commit"],
        "branch": worktree["branch"],
        "operator_quiesced": service["operator_quiesced"],
        "dirty_entry_count": worktree["dirty_entry_count"],
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "broker_snapshot_source": broker["source"],
        "dashboard_ux_preservation_required": True,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
    }
    write_json_atomic(runtime / "qadam_catc_worktree_inventory.json", worktree)
    write_json_atomic(runtime / "qadam_catc_active_service_inventory.json", service)
    write_json_atomic(runtime / "qadam_catc_broker_read_only_snapshot.json", broker)
    write_json_atomic(runtime / "qadam_catc_baseline.json", baseline)
    return baseline


def write_implementation_status(
    *,
    completed_phases: list[str],
    in_progress_phase: str | None,
    blockers: list[str] | None = None,
    runtime: Path | None = None,
) -> dict[str, Any]:
    target = runtime or runtime_dir()
    phases = [f"CATC-{index}" for index in range(18)]
    rows = []
    for phase in phases:
        if phase in completed_phases:
            state = "completed"
        elif phase == in_progress_phase:
            state = "in_progress"
        else:
            state = "pending"
        rows.append({"phase_id": phase, "state": state})
    payload = {
        "schema_version": "qadam_catc_implementation_status.v1",
        "artifact_type": "qadam_catc_implementation_status",
        "generated_at": now_iso(),
        "status": "blocked" if blockers else "in_progress" if in_progress_phase else "complete",
        "completed_phase_count": len(completed_phases),
        "phase_count": 18,
        "in_progress_phase": in_progress_phase,
        "phases": rows,
        "blockers": blockers or [],
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
    }
    write_json_atomic(target / IMPLEMENTATION_STATUS, payload)
    return payload


def append_implementation_log(note: str) -> None:
    if not IMPLEMENTATION_LOG.exists():
        IMPLEMENTATION_LOG.write_text(
            "# Qadam CATC Implementation Log\n\n",
            encoding="utf-8",
        )
    with IMPLEMENTATION_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"## {now_iso()}\n\n{note.strip()}\n\n")


__all__ = [
    "append_implementation_log",
    "capture_catc_baseline",
    "write_implementation_status",
]
