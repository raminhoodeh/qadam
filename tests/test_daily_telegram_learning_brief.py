import json
from dataclasses import replace
from pathlib import Path
from urllib.error import URLError

from orchestrator.config import Settings
import orchestrator.daily_telegram_learning_brief as learning_brief_module
from orchestrator.daily_telegram_learning_brief import (
    build_learning_research_snapshot,
    build_daily_telegram_learning_brief,
    validate_daily_telegram_learning_brief,
)


ROOT = Path(__file__).resolve().parents[1]


def _live_learning_settings(tmp_path: Path) -> Settings:
    secrets_path = tmp_path / "qadam-secrets.env"
    secrets_path.write_text(
        "TELEGRAM_BOT_TOKEN=123456:test-token\nTELEGRAM_GROUP_CHAT_ID=-1001234567890\n",
        encoding="utf-8",
    )
    secrets_path.chmod(0o600)
    return replace(
        Settings.from_env(),
        runtime_dir=str(tmp_path),
        secrets_file=str(secrets_path),
        mode="paper",
        live_capital_enabled=False,
        telegram_daily_learning_brief_enabled=True,
        telegram_daily_learning_brief_dry_run=False,
    )


def _fixed_ibm_hardware_research_snapshot() -> dict:
    return {
        "generated_at": "2026-07-21T12:00:00+00:00",
        "source_count": 41,
        "instrument_count": 19,
        "candidate_relationship_count": 5,
        "backtest": {
            "attempted_hypothesis_count": 360,
            "completed_method_count": 12,
            "eligible_group_count": 0,
            "raw_significant_result_count": 20,
            "adjusted_significant_result_count": 2,
            "validated_edge_count": 0,
            "rejected_result_count": 360,
            "status": "completed_no_validated_edge",
            "why_no_result": "No result survived holdout, costs and stability checks.",
        },
        "strongest_pattern": {
            "title": "physical-disruption signals versus CL=F, USO and XLE",
            "research_score": 0.525,
            "fresh_source_count": 1,
            "contributing_source_count": 5,
            "stage": "candidate_relationship",
        },
        "interesting_patterns": [
            {
                "title": "physical-disruption signals versus CL=F, USO and XLE",
                "research_score": 0.525,
                "fresh_source_count": 1,
                "contributing_source_count": 5,
                "stage": "candidate_relationship",
            },
            {
                "title": "policy and innovation signals versus SMH, SOXX and NVDA",
                "research_score": 0.2,
                "fresh_source_count": 4,
                "contributing_source_count": 5,
                "stage": "candidate_relationship",
            },
        ],
        "quantum": {
            "headline": "Matched quantum and classical review completed.",
            "classical_preferred_count": 1,
            "strengthened_count": 0,
            "quantum_usefulness_score": 0.0,
        },
        "quantum_hardware_learning": {
            "evidence_mode": "ibm_hardware_candidate_rejected",
            "hardware_run_completed": True,
            "hardware_provider": "IBM Quantum via Q-CTRL Fire Opal",
            "hardware_result_generated_at": "2026-07-21T10:00:00+00:00",
            "candidate_validation_generated_at": "2026-07-21T11:00:00+00:00",
            "represented_score_label_row_count": 746275,
            "backend_qubit_count": 127,
            "hardware_candidate_count": 1,
            "feature_pair": ["market_flow", "evidence_freshness"],
            "conditioning_feature": "market_regime",
            "opportunity_count": 2762,
            "interaction_beats_classical_baseline": False,
            "incremental_net_return_per_opportunity": -0.00066,
            "multiple_testing_adjusted_p_value": 1.0,
            "strategy_changed": False,
            "paper_order_created": False,
            "validated_edge_created": False,
            "learning_summary": "The hardware candidate did not beat its classical baseline.",
            "public_safe": True,
        },
        "strategy_hypothesis_count": 0,
        "paper_order_count": 0,
        "next_test": "Test official STOCK Act transaction details.",
        "public_safe": True,
    }


def test_daily_learning_brief_explains_recognised_patterns_and_stays_retryable(
    monkeypatch,
    tmp_path,
):
    daily_findings = json.loads((ROOT / "data/runtime/daily_edge_findings_brief.json").read_text())
    promotion_gates = json.loads((ROOT / "data/runtime/promotion_gates.json").read_text())
    settings = _live_learning_settings(tmp_path)

    def fail_transport(*_args, **_kwargs):
        raise URLError("offline")

    monkeypatch.setattr(learning_brief_module, "_telegram_send", fail_transport)

    payload = build_daily_telegram_learning_brief(
        daily_edge_findings=daily_findings,
        promotion_gates=promotion_gates,
        settings=settings,
        send_requested=True,
        generated_at=daily_findings["generated_at"],
        brief_slot="evening",
        brief_slot_label="Evening",
    )

    validate_daily_telegram_learning_brief(payload)
    body = payload["body"]

    assert payload["status"] == "daily_telegram_learning_brief_ready_to_send"
    assert payload["live_send_attempted"] is True
    assert payload["live_send_succeeded"] is False
    assert payload["last_delivery_failure_category"] == "URLError"
    assert payload["delivery_retry_status"] == "queued_after_transport_failure"
    assert "Evening research brief" in body
    assert "No new provider-backed evidence matured today" in body
    assert "candidate" in body
    assert "paper order" in body
    assert "force a trade" not in body
    assert "honest research cycle" not in body


def test_daily_learning_brief_explains_real_ibm_hardware_learning(tmp_path):
    daily_findings = json.loads((ROOT / "data/runtime/daily_edge_findings_brief.json").read_text())
    promotion_gates = json.loads((ROOT / "data/runtime/promotion_gates.json").read_text())
    settings = _live_learning_settings(tmp_path)
    research_snapshot = _fixed_ibm_hardware_research_snapshot()

    payload = build_daily_telegram_learning_brief(
        daily_edge_findings=daily_findings,
        promotion_gates=promotion_gates,
        settings=settings,
        send_requested=False,
        generated_at=daily_findings["generated_at"],
        brief_slot="morning",
        brief_slot_label="Morning",
        research_snapshot=research_snapshot,
    )

    validate_daily_telegram_learning_brief(payload)
    quantum_learning = payload["research_snapshot"]["quantum_hardware_learning"]
    assert quantum_learning["evidence_mode"] == "ibm_hardware_candidate_rejected"
    assert quantum_learning["hardware_run_completed"] is True
    assert quantum_learning["opportunity_count"] == 2762
    assert quantum_learning["strategy_changed"] is False
    assert quantum_learning["paper_order_created"] is False
    assert "IBM Quantum testing found" in payload["body"]
    assert "physical-disruption signals versus CL=F, USO and XLE" in payload["body"]
    assert "policy and innovation signals versus SMH, SOXX and NVDA" in payload["body"]
    assert "2,762 cost-adjusted opportunities" in payload["body"]
    assert "matched classical benchmark by 0.066%" in payload["body"]
    assert "excluded from strategy decisions" in payload["body"]
    assert "not a simulator" not in payload["body"]
    assert "Qadam rejected it" not in payload["body"]


def test_daily_learning_brief_rejects_unverified_hardware_claim(tmp_path):
    daily_findings = json.loads((ROOT / "data/runtime/daily_edge_findings_brief.json").read_text())
    promotion_gates = json.loads((ROOT / "data/runtime/promotion_gates.json").read_text())
    settings = _live_learning_settings(tmp_path)
    research_snapshot = _fixed_ibm_hardware_research_snapshot()
    research_snapshot["quantum_hardware_learning"]["hardware_run_completed"] = False

    payload = build_daily_telegram_learning_brief(
        daily_edge_findings=daily_findings,
        promotion_gates=promotion_gates,
        settings=settings,
        send_requested=False,
        generated_at=daily_findings["generated_at"],
        brief_slot="evening",
        brief_slot_label="Evening",
        research_snapshot=research_snapshot,
    )

    try:
        validate_daily_telegram_learning_brief(payload)
    except ValueError as exc:
        assert "hardware claim is unverified" in str(exc)
    else:
        raise AssertionError("Unverified IBM hardware claim passed validation")


def test_daily_learning_brief_sends_scheduled_insight_without_material_change(tmp_path):
    daily_findings = json.loads((ROOT / "data/runtime/daily_edge_findings_brief.json").read_text())
    promotion_gates = json.loads((ROOT / "data/runtime/promotion_gates.json").read_text())
    settings = _live_learning_settings(tmp_path)
    material_delta = {
        "artifact_type": "qadam_material_learning_delta",
        "status": "quiet_no_material_change",
        "material_change": False,
        "current_semantic_hash": "unchanged-evidence",
        "five_part_answer": {},
    }

    payload = build_daily_telegram_learning_brief(
        daily_edge_findings=daily_findings,
        promotion_gates=promotion_gates,
        material_learning_delta=material_delta,
        settings=settings,
        send_requested=False,
        generated_at=daily_findings["generated_at"],
        brief_slot="morning",
        brief_slot_label="Morning",
    )

    validate_daily_telegram_learning_brief(payload)
    assert payload["status"] == "daily_telegram_learning_brief_ready_to_send"
    assert payload["notification_candidate_created"] is True
    assert payload["telegram_live_send_allowed"] is True
    assert payload["live_send_attempted"] is False
    assert "Morning research brief" in payload["body"]
    assert "No material research result changed overnight" in payload["body"]
    assert "Current quantum evidence" in payload["body"]
    assert payload["material_change"] is False


def test_daily_learning_brief_uses_five_part_material_answer(tmp_path):
    daily_findings = json.loads((ROOT / "data/runtime/daily_edge_findings_brief.json").read_text())
    promotion_gates = json.loads((ROOT / "data/runtime/promotion_gates.json").read_text())
    settings = replace(_live_learning_settings(tmp_path), telegram_daily_learning_brief_dry_run=True)
    material_delta = {
        "artifact_type": "qadam_material_learning_delta",
        "status": "material_change",
        "material_change": True,
        "current_semantic_hash": "new-evidence",
        "five_part_answer": {
            "new_evidence_arrived": "A new STOCK Act disclosure matured.",
            "hypothesis_strengthened_or_weakened": "The defence hypothesis weakened.",
            "outcome_matured": "One forward outcome matured.",
            "what_was_rejected": "One timing rule was rejected.",
            "what_qadam_tests_next": "Test whether sector concentration improves timing.",
        },
    }

    payload = build_daily_telegram_learning_brief(
        daily_edge_findings=daily_findings,
        promotion_gates=promotion_gates,
        material_learning_delta=material_delta,
        settings=settings,
        generated_at=daily_findings["generated_at"],
        brief_slot="evening",
        brief_slot_label="Evening",
    )

    validate_daily_telegram_learning_brief(payload)
    assert payload["status"] == "daily_telegram_learning_brief_dry_run_ready"
    assert payload["notification_candidate_created"] is True
    assert "A new STOCK Act disclosure matured" in payload["body"]
    assert "The defence hypothesis weakened" in payload["body"]
    assert "One forward outcome matured" in payload["body"]
    assert "One timing rule was rejected" in payload["body"]
    assert "Test whether sector concentration improves timing" in payload["body"]


def test_twice_daily_slots_send_once_each(monkeypatch, tmp_path):
    daily_findings = json.loads((ROOT / "data/runtime/daily_edge_findings_brief.json").read_text())
    promotion_gates = json.loads((ROOT / "data/runtime/promotion_gates.json").read_text())
    settings = _live_learning_settings(tmp_path)
    source_settings = replace(settings, runtime_dir=str(ROOT / "data/runtime"))
    research_snapshot = build_learning_research_snapshot(source_settings)
    sent_bodies = []

    def send_ok(_token, _chat_id, body):
        sent_bodies.append(body)
        return {"ok": True, "result": {"message_id": len(sent_bodies)}}

    monkeypatch.setattr(learning_brief_module, "_telegram_send", send_ok)

    morning = build_daily_telegram_learning_brief(
        daily_edge_findings=daily_findings,
        promotion_gates=promotion_gates,
        settings=settings,
        send_requested=True,
        generated_at=daily_findings["generated_at"],
        brief_slot="morning",
        brief_slot_label="Morning",
        research_snapshot=research_snapshot,
    )
    evening = build_daily_telegram_learning_brief(
        daily_edge_findings=daily_findings,
        promotion_gates=promotion_gates,
        settings=settings,
        send_requested=True,
        generated_at=daily_findings["generated_at"],
        brief_slot="evening",
        brief_slot_label="Evening",
        research_snapshot=research_snapshot,
    )
    duplicate = build_daily_telegram_learning_brief(
        daily_edge_findings=daily_findings,
        promotion_gates=promotion_gates,
        settings=settings,
        send_requested=True,
        generated_at=daily_findings["generated_at"],
        brief_slot="morning",
        brief_slot_label="Morning",
        research_snapshot=research_snapshot,
    )

    assert morning["status"] == "daily_telegram_learning_brief_sent"
    assert evening["status"] == "daily_telegram_learning_brief_sent"
    assert duplicate["status"] == "daily_telegram_learning_brief_already_sent"
    assert duplicate["blockers"] == []
    assert duplicate["live_send_attempted"] is False
    assert len(sent_bodies) == 2
    assert morning["delivery_key"] != evening["delivery_key"]
    assert morning["body"] != evening["body"]
    assert "IBM Quantum" in morning["body"]
    assert "IBM Quantum" in evening["body"]
    for body in sent_bodies:
        assert "force a trade" not in body
        assert "not a simulator" not in body
        assert "honest research cycle" not in body
