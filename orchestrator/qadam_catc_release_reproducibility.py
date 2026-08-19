"""Verify that CATC source, dashboard, and installed runtime are one release."""

from __future__ import annotations

from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_autonomous_experimental_paper_epoch import _dashboard_hash_audit
from orchestrator.qadam_operator_ready_common import (
    now_iso,
    runtime_dir,
    write_json_atomic,
)
from orchestrator.qadam_operator_service import (
    _installed_launchd_matches_template,
    operator_build_identity,
)
from orchestrator.qadam_paperops_runtime_owner import paperops_runtime_owner_status

SCHEMA_VERSION = "qadam_catc_release_reproducibility.v1"
ARTIFACT = "qadam_catc_release_reproducibility.json"


def validate_release_reproducibility(
    *,
    build_identity: dict[str, Any],
    dashboard_audit: dict[str, Any],
    runtime_owner: dict[str, Any],
    launchd_template_matches: bool,
) -> list[str]:
    errors: list[str] = []
    if build_identity.get("git_commit") in {None, ""}:
        errors.append("release_git_commit_missing")
    if build_identity.get("dirty_worktree") is not False:
        errors.append("operator_build_scope_dirty")
    if dashboard_audit.get("protected_ux_preserved") is not True:
        errors.append("protected_dashboard_ux_changed")
    if not launchd_template_matches:
        errors.append("installed_launchd_template_mismatch")
    if runtime_owner.get("active") is not True:
        errors.append("guarded_paperops_runtime_owner_inactive")
    return errors


def build_and_write_release_reproducibility(
    settings: Settings | None = None,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    build_identity = operator_build_identity(settings)
    dashboard_audit = _dashboard_hash_audit()
    runtime_owner = paperops_runtime_owner_status(settings)
    launchd_template_matches = _installed_launchd_matches_template()
    errors = validate_release_reproducibility(
        build_identity=build_identity,
        dashboard_audit=dashboard_audit,
        runtime_owner=runtime_owner,
        launchd_template_matches=launchd_template_matches,
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_catc_release_reproducibility",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "installed_commit": build_identity.get("git_commit"),
        "operator_build_scope_clean": build_identity.get("dirty_worktree") is False,
        "operator_build_dirty_path_count": int(
            build_identity.get("dirty_path_count") or 0
        ),
        "protected_dashboard_approved_commit": dashboard_audit.get("approved_commit"),
        "protected_dashboard_ux_preserved": dashboard_audit.get(
            "protected_ux_preserved"
        )
        is True,
        "installed_launchd_template_matches": launchd_template_matches,
        "guarded_paperops_runtime_owner_active": runtime_owner.get("active") is True,
        "guarded_paperops_runtime_owner_blockers": runtime_owner.get("blockers") or [],
        "validation_errors": errors,
        "paper_only": True,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "live_capital_enabled": False,
    }
    write_json_atomic(runtime / ARTIFACT, payload)
    return payload


__all__ = [
    "build_and_write_release_reproducibility",
    "validate_release_reproducibility",
]
