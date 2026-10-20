"""Broker state must not replace the exact canonical prewrite contract."""

import json

CONTRACT_FIELDS = ("purpose", "candidate", "exit_plan", "paper_only", "live_capital_enabled")


def project_order(connection, order_key, broker_payload, previous):
    contract = {key: previous[key] for key in CONTRACT_FIELDS if key in previous}
    recovered_from = None
    if not contract.get("purpose"):
        row = connection.execute(
            "SELECT event_id,payload_json FROM operating_events WHERE aggregate_type='order' "
            "AND aggregate_id=? AND event_type IN ('order_prepared_with_exit_plan',"
            "'order_reprepared_after_pre_submit_defer','exit_order_prepared') "
            "ORDER BY created_at DESC,rowid DESC LIMIT 1", (order_key,)
        ).fetchone()
        if row:
            original = json.loads(row["payload_json"])
            contract = {key: original[key] for key in CONTRACT_FIELDS if key in original}
            recovered_from = row["event_id"]
    return {**broker_payload, **contract}, recovered_from
