import json
from dataclasses import replace
from pathlib import Path
from urllib.error import URLError

from orchestrator.config import Settings
import orchestrator.daily_telegram_learning_brief as learning_brief_module
from orchestrator.daily_telegram_learning_brief import (
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
    )

    validate_daily_telegram_learning_brief(payload)
    body = payload["body"]

    assert payload["status"] == "daily_telegram_learning_brief_ready_to_send"
    assert payload["live_send_attempted"] is True
    assert payload["live_send_succeeded"] is False
    assert payload["last_delivery_failure_category"] == "URLError"
    assert payload["delivery_retry_status"] == "queued_after_transport_failure"
    assert "The reads:" in body
    assert "oil shipping/GPS/fire/flight vs CL=F, BZ=F, USO and XLE" in body
    assert "silver rates, trade and mining flow vs SI=F, SLV, SIL and PAAS" in body
    assert "semiconductors export/news, filings, patents, GitHub" in body
    assert "prediction markets Polymarket/Kalshi odds vs news/social/conflict" in body
    assert "defence stocks conflict, maritime/flight, GPS and filings vs ITA" in body
    assert "whether inputs arrive before price or odds move" in body
    assert "source and conflict pressure" not in body
    assert "not create a paper order" in body


def test_daily_learning_brief_stays_quiet_without_material_change(tmp_path):
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
        send_requested=True,
        generated_at=daily_findings["generated_at"],
    )

    validate_daily_telegram_learning_brief(payload)
    assert payload["status"] == "daily_telegram_learning_brief_quiet_no_material_change"
    assert payload["notification_candidate_created"] is False
    assert payload["telegram_live_send_allowed"] is False
    assert payload["live_send_attempted"] is False
    assert "No material learning change" in payload["body"]


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
    )

    validate_daily_telegram_learning_brief(payload)
    assert payload["status"] == "daily_telegram_learning_brief_dry_run_ready"
    assert payload["notification_candidate_created"] is True
    assert "A new STOCK Act disclosure matured" in payload["body"]
    assert "The defence hypothesis weakened" in payload["body"]
    assert "Test whether sector concentration improves timing" in payload["body"]
