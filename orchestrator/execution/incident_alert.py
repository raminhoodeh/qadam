"""Event-driven, read-only execution alerts independent of the three-hour brief."""

from orchestrator.qadam_operator_ready_common import read_json, runtime_dir, now_iso, sha256_json
from orchestrator.secrets import secret_value


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
    prior_incident = previous.get("incident_id")
    if not frozen and not prior_incident:
        return {"status": "no_incident"}
    if not frozen and (control.get("latest_reconciliation") or {}).get("status") != "passed":
        return {"status": "recovery_unverified"}
    reason = str(state.get("reason") or "unknown")
    # Reconciliation retries update timestamps; the incident remains the same
    # until a verified recovery, so they must not generate repeated alerts.
    incident_id = sha256_json({"reason": reason}) if frozen else prior_incident
    key = f"{incident_id}:{'frozen' if frozen else 'recovered'}"
    if previous.get("delivery_key") == key and previous.get("delivered"):
        return {"status": "already_delivered"}
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
    try:
        response = (sender or send_readonly_response)(str(token), str(target), message, None)
        delivered = response.get("ok") is True
        error = None if delivered else response.get("error_class", "provider_error")
    except Exception as exc:
        response, delivered, error = {}, False, type(exc).__name__
    result = {
        "generated_at": now_iso(), "incident_id": incident_id,
        "delivery_key": key, "delivered": delivered, "frozen": frozen,
        "status": "delivered" if delivered else "retry_pending",
        "error_class": error, "provider_message_id": response.get("message_id"),
        "broker_write_count": 0,
    }
    write_json_atomic(path, result)
    return result
