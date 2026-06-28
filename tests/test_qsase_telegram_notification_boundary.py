import copy

from orchestrator.qsase_telegram_notification_boundary import (
    TELEGRAM_AUTHORITY_FLAGS,
    build_qsase_inbound_readonly_record,
    build_qsase_telegram_notification_boundary,
    dedupe_qsase_telegram_message,
    score_qsase_telegram_message,
    validate_negative_qsase_telegram_notification_boundary_probes,
    validate_qsase_telegram_message_candidate,
    validate_qsase_telegram_notification_boundary,
)


def test_qsase_telegram_candidates_are_short_specific_and_dashboard_only():
    payload = build_qsase_telegram_notification_boundary()

    assert payload["message_candidate_count"] == 5
    assert payload["message_sent_count"] == 0
    assert payload["message_rejected_generic_count"] == 0
    assert payload["message_rejected_unsafe_count"] == 0
    assert validate_qsase_telegram_notification_boundary(payload) == []

    for candidate in payload["message_candidates"]:
        assert candidate["status"] in {"message_ready_for_dashboard_only", "message_rejected_duplicate"}
        assert len(candidate["body"]) <= 360
        assert candidate["quality"]["specificity_status"] == "specific"
        assert candidate["quality"]["human_style_status"] == "human"
        assert candidate["source_artifact_refs"]
        assert "State:" in candidate["body"]
        assert "Reason:" in candidate["body"]
        assert "Next:" in candidate["body"]
        assert "Order:" in candidate["body"]
        assert validate_qsase_telegram_message_candidate(candidate) == []


def test_qsase_telegram_dedupe_fingerprint_blocks_repeats():
    payload = build_qsase_telegram_notification_boundary()
    candidate = payload["message_candidates"][0]
    duplicate = dedupe_qsase_telegram_message(
        candidate,
        [{"fingerprint": candidate["fingerprint"], "message_status": "message_ready_for_dashboard_only"}],
    )

    assert duplicate["duplicate"] is True
    assert duplicate["status"] == "duplicate_suppressed"
    assert duplicate["material_change_required_for_repeat"] is True


def test_qsase_telegram_inbound_is_read_only_and_commands_are_ignored():
    command_record = build_qsase_inbound_readonly_record(
        {"text_excerpt": "/buy SMH", "received_at": "2026-06-28T00:00:00+00:00"}
    )

    assert command_record["command_detected"] is True
    assert command_record["command_ignored"] is True
    assert command_record["trade_authority_created"] is False
    assert command_record["trade_candidate_created"] is False
    assert command_record["risk_approval_created"] is False
    assert command_record["execution_approval_created"] is False
    assert command_record["paper_order_created"] is False
    assert command_record["broker_write_created"] is False
    assert command_record["proof_credit_allowed"] is False
    assert command_record["live_capital_enabled"] is False


def test_qsase_telegram_authority_and_dashboard_mirror_are_safe():
    payload = build_qsase_telegram_notification_boundary()

    assert payload["authority_flags"] == TELEGRAM_AUTHORITY_FLAGS
    assert all(value is False for value in payload["authority"].values())
    assert payload["telegram_live_send_allowed"] is False
    assert payload["telegram_command_path_enabled"] is False
    assert payload["telegram_trade_command_enabled"] is False
    assert payload["paper_order_created_count"] == 0
    assert payload["broker_write_count"] == 0
    assert payload["proof_credit_allowed"] is False
    assert payload["live_capital_enabled"] is False

    mirror = payload["dashboard_communications_mirror"]
    assert mirror["status"] == "dashboard_communications_mirror_ready"
    assert mirror["command_disabled"] is True
    assert mirror["telegram_live_send_allowed"] is False
    assert mirror["paper_order_created_count"] == 0
    assert mirror["broker_write_count"] == 0
    assert mirror["proof_credit_allowed"] is False
    assert mirror["live_capital_enabled"] is False


def test_qsase_telegram_negative_quality_and_authority_probes():
    payload = build_qsase_telegram_notification_boundary()
    generic_probe = copy.deepcopy(payload["message_candidates"][0])
    generic_probe["body"] = "Qadam Codebase Upgrade\nWhat changed:\nWhy it matters:\nWhat to check:"
    generic_quality = score_qsase_telegram_message(generic_probe)
    assert generic_quality["generic_rejected"] is True

    command_probe = copy.deepcopy(payload["message_candidates"][0])
    command_probe["body"] = "/buy SMH\nState: command\nReason: operator asked\nNext: submit\nOrder: buy SMH"
    command_quality = score_qsase_telegram_message(command_probe)
    assert command_quality["unsafe_rejected"] is True

    proof_probe = copy.deepcopy(payload)
    proof_probe["proof_credit_allowed"] = True
    assert any("proof_credit_allowed" in error for error in validate_qsase_telegram_notification_boundary(proof_probe))

    assert validate_negative_qsase_telegram_notification_boundary_probes() == []
