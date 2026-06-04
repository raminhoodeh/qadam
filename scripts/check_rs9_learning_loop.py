#!/usr/bin/env python3
"""Validate RS-9 Learning Loop and full-potential review."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.rs9_learning_loop import (  # noqa: E402
    MUTATION_AUTHORITY_FIELDS,
    PUBLIC_STATUS_FIELDS,
    SOURCE_REFS,
    UNSAFE_COUNT_FIELDS,
    build_rs9_learning_loop,
    rs9_learning_loop_paths,
    rs9_learning_loop_public_status,
    validate_rs9_learning_loop,
    write_rs9_learning_loop,
)


def _has_error(errors: list[str], prefix_or_exact: str) -> bool:
    return any(error == prefix_or_exact or error.startswith(prefix_or_exact) for error in errors)


def main() -> int:
    settings = Settings.from_env()
    errors: list[str] = []
    output_path, history_path, event_log_path = rs9_learning_loop_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    artifact = build_rs9_learning_loop(settings=settings)
    output_path, history_path, event_log_path, written = write_rs9_learning_loop(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_rs9_learning_loop(written)
    public_status = rs9_learning_loop_public_status(settings=settings)
    replay = EventLog(event_log_path, echo=False).replay()

    if validation_errors:
        errors.append("rs9 validation errors: " + "; ".join(validation_errors))
    if not output_path.exists():
        errors.append("RS-9 runtime artifact was not written")
    if not history_path.exists():
        errors.append("RS-9 history log was not written")
    if not event_log_path.exists():
        errors.append("RS-9 Event Log was not written")
    if replay.get("total_events") != 1:
        errors.append("RS-9 Event Log must contain exactly one event for this check")
    if written.get("phase") != "RS" or written.get("stage") != "RS-9":
        errors.append("RS-9 phase/stage mismatch")
    if written.get("status") != "review_ready":
        errors.append("RS-9 should be review_ready when source artifacts are present")
    if written.get("learning_direction") not in {"improving", "degrading", "uncertain"}:
        errors.append("RS-9 learning direction is missing")
    if written.get("full_potential_state") != "learning_visible_but_mutation_locked":
        errors.append("RS-9 full-potential state mismatch")
    if written.get("paperops_guarded_paper_trading_not_blocked") is not True:
        errors.append("RS-9 must not block guarded PaperOps paper trading")
    if written.get("source_artifact_count") != len(SOURCE_REFS):
        errors.append("RS-9 source artifact count mismatch")
    if written.get("source_missing_count") != 0:
        errors.append("RS-9 source artifacts missing")
    if written.get("source_validation_error_count") != 0:
        errors.append("RS-9 source validation errors present")
    if written.get("proposal_count") != 5:
        errors.append("RS-9 must expose five learning proposal surfaces")
    if written.get("blocked_proposal_count") != 5:
        errors.append("RS-9 proposals should all be blocked pending review")
    if written.get("active_proposal_count") != 0:
        errors.append("RS-9 must not expose active/applicable proposals yet")
    for key in (
        "strategy_weight_proposal_count",
        "source_trust_proposal_count",
        "risk_sizing_proposal_count",
        "market_context_proposal_count",
        "worldview_lens_proposal_count",
    ):
        if written.get(key) != 1:
            errors.append(f"RS-9 proposal surface count mismatch: {key}")
    for proposal in written.get("learning_proposals", []):
        if proposal.get("approval_required") is not True:
            errors.append("RS-9 proposal missing approval requirement")
        if proposal.get("apply_allowed") is not False:
            errors.append("RS-9 proposal apply route is enabled")
        if proposal.get("mutation_allowed") is not False:
            errors.append("RS-9 proposal mutation route is enabled")
        for ref in proposal.get("source_refs", []):
            if not isinstance(ref, str) or not ref.startswith("data/runtime/"):
                errors.append("RS-9 proposal source ref is not public-safe")
    for field in MUTATION_AUTHORITY_FIELDS:
        if written.get(field) is not False:
            errors.append(f"RS-9 authority field enabled: {field}")
    for field in UNSAFE_COUNT_FIELDS:
        if written.get(field) != 0:
            errors.append(f"RS-9 unsafe count nonzero: {field}")
    if set(public_status) - set(PUBLIC_STATUS_FIELDS):
        errors.append("RS-9 public status exposes non-public fields")
    if public_status.get("proposal_count") != written.get("proposal_count"):
        errors.append("RS-9 public status proposal count mismatch")
    public_dump = json.dumps(public_status, sort_keys=True)
    for forbidden in (
        "/Users/",
        "/private/",
        "api_key",
        "access_token",
        "refresh_token",
        "broker_order_id",
        "external_order_id",
    ):
        if forbidden in public_dump:
            errors.append(f"RS-9 public status leaked forbidden marker: {forbidden}")

    mutation_probe = deepcopy(written)
    mutation_probe["strategy_weight_mutation_allowed"] = True
    mutation_probe["learning_proposals"][0]["mutation_allowed"] = True
    mutation_errors = validate_rs9_learning_loop(mutation_probe)
    if not _has_error(mutation_errors, "rs9_authority_enabled:strategy_weight_mutation_allowed"):
        errors.append("RS-9 failed to reject strategy-weight mutation authority")
    if not _has_error(mutation_errors, "rs9_learning_proposal_mutation_allowed"):
        errors.append("RS-9 failed to reject proposal mutation")

    trust_probe = deepcopy(written)
    trust_probe["source_trust_mutation_allowed"] = True
    trust_probe["trust_score_update_allowed"] = True
    trust_errors = validate_rs9_learning_loop(trust_probe)
    if not _has_error(trust_errors, "rs9_authority_enabled:source_trust_mutation_allowed"):
        errors.append("RS-9 failed to reject source-trust mutation")
    if not _has_error(trust_errors, "rs9_authority_enabled:trust_score_update_allowed"):
        errors.append("RS-9 failed to reject trust-score update authority")

    risk_probe = deepcopy(written)
    risk_probe["risk_sizing_mutation_allowed"] = True
    risk_probe["policy_mutation_allowed"] = True
    risk_errors = validate_rs9_learning_loop(risk_probe)
    if not _has_error(risk_errors, "rs9_authority_enabled:risk_sizing_mutation_allowed"):
        errors.append("RS-9 failed to reject risk-sizing mutation")
    if not _has_error(risk_errors, "rs9_authority_enabled:policy_mutation_allowed"):
        errors.append("RS-9 failed to reject policy mutation")

    worldview_probe = deepcopy(written)
    worldview_probe["worldview_lens_strength_mutation_allowed"] = True
    worldview_errors = validate_rs9_learning_loop(worldview_probe)
    if not _has_error(worldview_errors, "rs9_authority_enabled:worldview_lens_strength_mutation_allowed"):
        errors.append("RS-9 failed to reject worldview-lens mutation")

    command_probe = deepcopy(written)
    command_probe["dashboard_command_authority"] = True
    command_probe["telegram_command_authority"] = True
    command_errors = validate_rs9_learning_loop(command_probe)
    if not _has_error(command_errors, "rs9_authority_enabled:dashboard_command_authority"):
        errors.append("RS-9 failed to reject dashboard command authority")
    if not _has_error(command_errors, "rs9_authority_enabled:telegram_command_authority"):
        errors.append("RS-9 failed to reject Telegram command authority")

    broker_probe = deepcopy(written)
    broker_probe["broker_post_called_count"] = 1
    broker_probe["unsafe_write_counter_total"] = 1
    broker_errors = validate_rs9_learning_loop(broker_probe)
    if not _has_error(broker_errors, "rs9_unsafe_count_nonzero:broker_post_called_count"):
        errors.append("RS-9 failed to reject broker POST count")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print("rs9_learning_loop_check=failed")
        return 1
    print("rs9_learning_loop_check=ok")
    print(f"rs9_learning_direction={written['learning_direction']}")
    print(f"rs9_proposal_count={written['proposal_count']}")
    print(f"rs9_blocked_authority_count={written['blocked_authority_count']}")
    print("rs9_paperops_guarded_paper_trading_not_blocked=True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
