"""Operator account holds stop requests; recovery cannot clear a suspension."""

import json
import re
from pathlib import Path

from orchestrator.qadam_operator_ready_common import read_json, write_json_atomic, now_iso

ARTIFACT = "qadam_gemini_account_hold.json"


def provider_failure_details(error):
    """Retain bounded error categories, never response text, URLs or secrets."""
    try:
        payload = json.loads(error.read(8192).decode("utf-8"))
        details = payload.get("error", {})
        details = details if isinstance(details, dict) else {}
    except (OSError, ValueError, AttributeError, UnicodeError):
        details = {}
    message = str(details.get("message") or "").lower()
    reason = "provider_account_or_request_error"
    for fragments, category in (
        (("prepayment credits are depleted", "insufficient credits"), "prepayment_credits_depleted"),
        (("suspended", "hijacked resources"), "provider_suspension_reported"),
        (("reported as leaked", "api key was leaked"), "provider_credential_exposure_reported"),
        (("api key not valid", "api_key_invalid"), "provider_credential_invalid"),
    ):
        if any(fragment in message for fragment in fragments):
            reason = category
            break
    code = str(details.get("status") or "")
    return {"provider_error_reason": reason,
            "provider_error_code": code if re.fullmatch(r"[A-Z_]{1,64}", code) else None}


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
