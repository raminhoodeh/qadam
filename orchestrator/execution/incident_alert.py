"""Event-driven, read-only execution alerts independent of the three-hour brief."""

from datetime import datetime, timedelta, timezone

from orchestrator.qadam_operator_ready_common import read_json, runtime_dir, now_iso, sha256_json
from orchestrator.secrets import secret_value


def _parse(value):
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return stamp if stamp.tzinfo else None
    except (ValueError, TypeError):
        return None


def publish_execution_incident(snapshot, settings, *, sender=None):
    from orchestrator.qadam_operator_ready_common import write_json_atomic
    from orchestrator.qadam_telegram_readonly_interface import send_readonly_response

    path = runtime_dir(settings) / "qadam_execution_incident_delivery.json"
    previous = read_json(path)
    control = snapshot.get("control_plane") or {}
    state = control.get("execution_state") or {}
    if not control.get("present") or control.get("read_error"):
        return {"status": "control_unavailable"}
    frozen = bool(state.get("frozen"))
    now = datetime.now(timezone.utc)
    prior_incident = previous.get("incident_id")
    if not frozen and not prior_incident:
        return {"status": "no_incident"}
    if not frozen:
        check = control.get("latest_reconciliation") or {}
        observed = _parse(check.get("mirror_observed_at"))
        if (check.get("status") != "passed" or check.get("blockers") or not observed
                or not 0 <= (now - observed).total_seconds() <= 180):
            return {"status": "recovery_unverified"}
    reason = str(state.get("reason") or "unknown")
    incident_id = (state.get("incident_id") or sha256_json({
        "reason": reason, "started_at": state.get("updated_at"),
    })) if frozen else prior_incident
    key = f"{incident_id}:{'frozen' if frozen else 'recovered'}"
    if previous.get("delivery_key") == key and previous.get("delivered"):
        delivered_at = _parse(previous.get("generated_at"))
        if not frozen or not delivered_at or (now - delivered_at).total_seconds() < 10800:
            return {"status": "already_delivered"}
    next_attempt = _parse(previous.get("next_attempt_at"))
    if previous.get("delivery_key") == key and not previous.get("delivered") and next_attempt and now < next_attempt:
        return {"status": "retry_deferred", "next_attempt_at": previous["next_attempt_at"]}
    message = (
        "Qadam execution alert: paper trading is frozen. New entries and due exits are blocked.\n"
        f"Cause: {reason[:500]}.\n"
        "The self-healer will attempt only allowlisted recovery. Execution stays blocked until "
        "broker reconciliation passes; unresolved faults require review."
        if frozen else
        "Qadam execution recovery: broker reconciliation passed and the execution freeze cleared. "
        "Normal paper entry and exit checks can resume. This does not confirm a new order or fill."
    )
    token, target = secret_value("TELEGRAM_BOT_TOKEN", settings), secret_value("TELEGRAM_GROUP_CHAT_ID", settings)
    if not token or not target:
        return {"status": "missing_configuration"}
    attempts = int(previous.get("attempt_count") or 0) + 1 if previous.get("delivery_key") == key else 1
    # Persist intent before transport. A crash may leave delivery ambiguous, but
    # notification replay never repeats a broker action.
    pending = {"generated_at": now.isoformat(), "incident_id": incident_id, "delivery_key": key,
               "frozen": frozen, "delivered": False, "status": "sending_unconfirmed",
               "attempt_count": attempts, "broker_write_count": 0,
               "next_attempt_at": (now + timedelta(seconds=60)).isoformat()}
    write_json_atomic(path, pending)
    try:
        response = (sender or send_readonly_response)(str(token), str(target), message, None)
        delivered = response.get("ok") is True
        error = None if delivered else response.get("error_class", "provider_error")
    except Exception as exc:
        response, delivered, error = {}, False, type(exc).__name__
    result = {
        **pending,
        "generated_at": now_iso(), "incident_id": incident_id,
        "delivery_key": key, "delivered": delivered, "frozen": frozen,
        "status": "delivered" if delivered else "retry_pending",
        "error_class": error, "provider_message_id": response.get("message_id"),
        "broker_write_count": 0,
        "next_attempt_at": None if delivered else (
            now + timedelta(seconds=min(1800, 60 * 2 ** min(attempts - 1, 5)))
        ).isoformat(),
    }
    write_json_atomic(path, result)
    return result
