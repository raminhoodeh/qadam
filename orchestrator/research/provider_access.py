"""Operator account holds stop requests; recovery cannot clear a suspension."""

from pathlib import Path

from orchestrator.qadam_operator_ready_common import read_json, write_json_atomic, now_iso

ARTIFACT = "qadam_gemini_account_hold.json"


def gemini_account_hold(settings):
    path = Path(settings.runtime_dir) / ARTIFACT
    if not path.exists():
        return None
    record = read_json(path)
    if record.get("status") == "released_after_operator_review":
        return None
    return {"provider": "gemini", "status": "held", "operator_action_required": True,
            "automatic_retry_allowed": False, "reason": record.get("reason") or "account_hold_unreadable"}


def record_gemini_account_hold(settings, *, reason, release_reviewed=False):
    if not reason or len(reason) > 300:
        raise ValueError("bounded_operator_reason_required")
    record = {"provider": "gemini", "generated_at": now_iso(), "reason": reason,
              "status": "released_after_operator_review" if release_reviewed else "held",
              "operator_action_required": not release_reviewed,
              "broker_calls": 0, "credential_changes": 0}
    write_json_atomic(Path(settings.runtime_dir) / ARTIFACT, record)
    return record
