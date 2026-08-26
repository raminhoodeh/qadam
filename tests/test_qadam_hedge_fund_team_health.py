from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.intelligence import (
    LocalResearchAssessmentStore,
    run_local_research_analyst_inference,
)
from orchestrator.qadam_hedge_fund_team_health import (
    FRONTIER_RESPONSE_SCHEMA,
    PIPELINE_STAGE_SERVICES,
    build_pipeline_health,
    ensure_local_research_analyst_ready,
    run_frontier_strategy_lead_assessment,
    run_hedge_fund_team_cycle,
    send_team_health_telegram_update,
    validate_hedge_fund_team_health,
)
from orchestrator.qadam_operator_ready_common import authority_flags, now_iso, write_json_atomic


def _settings(tmp_path: Path) -> Settings:
    return replace(
        Settings.from_env(),
        runtime_dir=str(tmp_path),
        data_root=str(tmp_path.parent),
    )


def _operator() -> dict:
    service_ids = {
        service_id
        for _number, _name, stage_services in PIPELINE_STAGE_SERVICES
        for service_id in stage_services
    }
    return {
        "generated_at": now_iso(),
        "status": "operator_service_running_guarded_paper",
        "service_running": True,
        "services": [
            {
                "service_id": service_id,
                "freshness": {"state": "fresh"},
            }
            for service_id in sorted(service_ids)
        ],
    }


def _team_authority() -> dict:
    return {
        **authority_flags(),
        "local_service_restart_allowed": True,
        "model_inference_allowed": True,
        "research_advisory_only": True,
        "strategy_admission_allowed": False,
        "risk_threshold_mutation_allowed": False,
        "paperops_invocation_allowed": False,
        "quantum_job_submission_allowed": False,
        "autonomous_code_edit_allowed": False,
    }


def test_pipeline_health_covers_all_ten_stages_and_detects_akber_failure() -> None:
    operator = _operator()
    circuits = {"services": {}}

    healthy = build_pipeline_health(operator, circuits)

    assert healthy["status"] == "healthy"
    assert healthy["healthy_stage_count"] == 10
    assert [row["stage"] for row in healthy["stages"]] == list(range(1, 11))

    akber = next(row for row in operator["services"] if row["service_id"] == "akber_review")
    akber["freshness"]["state"] = "stale"
    degraded = build_pipeline_health(operator, circuits)

    assert degraded["status"] == "degraded"
    stage_six = next(row for row in degraded["stages"] if row["stage"] == 6)
    assert stage_six["status"] == "degraded"
    assert stage_six["degraded_services"] == ["akber_review"]


def test_local_model_repair_starts_server_and_loads_model(monkeypatch) -> None:
    probes = iter(
        [
            {"probe_status": "connection_error", "model_available": False},
            {"probe_status": "ok", "model_available": False},
            {
                "probe_status": "ok",
                "model_available": True,
                "resolved_model": "gemma-4-e4b",
            },
        ]
    )
    commands: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        "orchestrator.qadam_hedge_fund_team_health.lm_studio_models_probe",
        lambda *_args, **_kwargs: next(probes),
    )
    monkeypatch.setattr(
        "orchestrator.qadam_hedge_fund_team_health._lms_executable",
        lambda: "/fake/lms",
    )
    monkeypatch.setattr(
        "orchestrator.qadam_hedge_fund_team_health.secret_value",
        lambda name, _settings: "google/gemma-4-e4b" if name == "LM_STUDIO_MODEL" else None,
    )

    def run(command: tuple[str, ...], _timeout: int) -> dict:
        commands.append(command)
        return {"returncode": 0, "status": "passed", "duration_seconds": 0.1}

    result = ensure_local_research_analyst_ready(
        Settings.from_env(),
        repair=True,
        command_runner=run,
        sleep_fn=lambda _seconds: None,
    )

    assert result["status"] == "ready"
    assert commands == [
        ("/fake/lms", "server", "start"),
        (
            "/fake/lms",
            "load",
            "google/gemma-4-e4b",
            "--identifier",
            "gemma-4-e4b",
            "-y",
        ),
    ]


def test_frontier_assessment_requires_real_accepted_json(tmp_path: Path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    monkeypatch.setattr(
        "orchestrator.qadam_hedge_fund_team_health.gemini_credential_probe",
        lambda *_args, **_kwargs: {"probe_status": "ok"},
    )
    monkeypatch.setattr(
        "orchestrator.qadam_hedge_fund_team_health.secret_value",
        lambda name, _settings: "test-key" if name == "GEMINI_API_KEY" else None,
    )

    captured: dict = {}

    def requester(_url: str, payload: dict, _timeout: int) -> dict:
        captured.update(payload)
        content = {
            "summary": "Evidence is coherent but remains research-only.",
            "challenges": ["Test the alternative regime explanation."],
            "alternative_explanations": ["A broad market move may explain it."],
            "evidence_gaps": ["Forward outcomes are still sparse."],
            "next_research_questions": ["Does it persist out of sample?"],
            "recommendation": "continue_observation",
            "confidence": 0.61,
        }
        return {
            "status": "ok",
            "payload": {"candidates": [{"content": {"parts": [{"text": json.dumps(content)}]}}]},
        }

    result = run_frontier_strategy_lead_assessment(
        {"summary": "Local assessment"}, settings, requester=requester
    )

    assert result["status"] == "accepted"
    assert result["assessment"]["recommendation"] == "continue_observation"
    assert result["paper_order_allowed"] is False
    assert result["strategy_admission_allowed"] is False
    generation = captured["generationConfig"]
    assert generation["maxOutputTokens"] == 1600
    assert generation["thinkingConfig"] == {"thinkingLevel": "LOW"}
    assert generation["responseMimeType"] == "application/json"
    assert generation["responseJsonSchema"] == FRONTIER_RESPONSE_SCHEMA


def test_local_assessment_uses_bounded_structured_inference(tmp_path: Path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    captured: dict = {}
    monkeypatch.setattr(
        "orchestrator.intelligence.read_research_shadow_triage_queue",
        lambda _settings: (
            {
                "packet_id": "packet-1",
                "status": "queued",
                "summary": "A bounded source-price relationship needs review.",
                "uncertainty": "known",
                "source_event_refs": ["source-1"],
                "created_at": now_iso(),
            },
        ),
    )
    monkeypatch.setattr(
        "orchestrator.intelligence.lm_studio_models_probe",
        lambda *_args, **_kwargs: {
            "probe_status": "ok",
            "resolved_model": "gemma-test",
        },
    )
    monkeypatch.setattr(
        "orchestrator.intelligence.secret_value",
        lambda name, _settings: {
            "LOCAL_LLM_PROVIDER": "lm_studio",
            "LM_STUDIO_BASE_URL": "http://127.0.0.1:1234/v1",
            "LM_STUDIO_MODEL": "gemma-test",
            "LM_STUDIO_TIMEOUT_SECONDS": "90",
        }.get(name),
    )

    def model_request(_url: str, payload: dict, **_kwargs) -> dict:
        captured.update(payload)
        content = {
            "summary": "The relationship remains research-only.",
            "watch_focus": "Observe the next independent source update.",
            "anomalies": ["The sample remains small."],
            "missing_correlations": ["A second source is still needed."],
            "next_questions": ["Does the relationship persist out of sample?"],
            "escalation_recommendation": "hold_shadow",
            "confidence": 0.54,
        }
        return {
            "status": "ok",
            "payload": {"choices": [{"message": {"content": json.dumps(content)}}]},
        }

    monkeypatch.setattr("orchestrator.intelligence._http_json_post", model_request)
    result = run_local_research_analyst_inference(
        limit=1,
        live=True,
        settings=settings,
        store=LocalResearchAssessmentStore(path=tmp_path / "assessments.jsonl", settings=settings),
        event_log=EventLog(path=tmp_path / "events.jsonl", echo=False),
    )

    assert result["status"] == "ok"
    assert result["assessment"]["mode"] == "live_local_llm"
    assert result["assessment"]["raw_response_status"] == "ok"
    assert captured["max_tokens"] == 2200
    assert captured["reasoning_effort"] == "low"
    assert captured["response_format"]["type"] == "json_schema"
    assert captured["response_format"]["json_schema"]["strict"] is True


def test_complete_team_cycle_requires_real_model_receipts(tmp_path: Path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    write_json_atomic(tmp_path / "qadam_operator_service_status.json", _operator())
    write_json_atomic(tmp_path / "qadam_operator_circuit_breakers.json", {"services": {}})
    write_json_atomic(
        tmp_path / "qadam_quantum_usefulness_summary.json",
        {
            "generated_at": now_iso(),
            "status": "complete_no_incremental_quantum_value",
            "quantum_contribution_verdict": "not_useful_for_tested_edges",
        },
    )
    monkeypatch.setattr(
        "orchestrator.qadam_hedge_fund_team_health.ensure_local_research_analyst_ready",
        lambda *_args, **_kwargs: {
            "status": "ready",
            "probe": {
                "probe_status": "ok",
                "model_available": True,
                "resolved_model": "gemma-test",
            },
            "repair_attempted": False,
            "repair_actions": [],
        },
    )
    frontier_calls = 0

    def frontier_runner(*_args, **_kwargs) -> dict:
        nonlocal frontier_calls
        frontier_calls += 1
        if frontier_calls == 1:
            return {
                "status": "degraded",
                "probe_status": "ok",
                "model": "gemini-test",
                "generated_at": now_iso(),
                "reason": "output_contract_rejected",
            }
        return {
            "status": "accepted",
            "probe_status": "ok",
            "model": "gemini-test",
            "generated_at": now_iso(),
            "input_digest": "frontier-digest",
        }

    monkeypatch.setattr(
        "orchestrator.qadam_hedge_fund_team_health.run_frontier_strategy_lead_assessment",
        frontier_runner,
    )

    local_calls = 0

    def local_runner(**_kwargs) -> dict:
        nonlocal local_calls
        local_calls += 1
        if local_calls == 1:
            return {
                "status": "ok",
                "processed_packet_count": 1,
                "assessment": {
                    "mode": "live_local_llm_contract_fallback",
                    "raw_response_status": "critic_or_parse_fallback",
                },
            }
        return {
            "status": "ok",
            "processed_packet_count": 3,
            "assessment": {
                "mode": "live_local_llm",
                "raw_response_status": "ok",
                "model": "gemma-test",
                "assessment_id": "assessment-1",
                "created_at": now_iso(),
            },
        }

    payload, errors = run_hedge_fund_team_cycle(
        settings,
        force=True,
        local_inference_runner=local_runner,
    )

    assert errors == []
    assert payload["status"] == "passed"
    assert payload["healthy_required_role_count"] == 4
    assert payload["trading_pipeline"]["healthy_stage_count"] == 10
    assert payload["team"]["local_research_analyst"]["inference_attempt_count"] == 2
    assert payload["team"]["frontier_strategy_lead"]["inference_attempt_count"] == 2
    assert payload["paper_order_created_count"] == 0
    assert payload["broker_write_count"] == 0


def test_telegram_health_is_deduped_and_command_disabled(tmp_path: Path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    monkeypatch.setattr(
        "orchestrator.qadam_hedge_fund_team_health.secret_value",
        lambda name, _settings: {
            "TELEGRAM_BOT_TOKEN": "test-token",
            "TELEGRAM_GROUP_CHAT_ID": "-100999",
        }.get(name),
    )
    messages: list[str] = []

    def sender(_token: str, _target: str, text: str, _reply: int | None) -> dict:
        messages.append(text)
        return {"ok": True}

    team_health = {
        "status": "passed",
        "healthy_required_role_count": 4,
        "team": {
            "python_coo": {"status": "healthy_active"},
            "local_research_analyst": {
                "status": "healthy_active",
                "processed_packet_count": 5,
            },
            "frontier_strategy_lead": {"status": "healthy_active"},
            "head_of_quant": {"status": "healthy_idle"},
        },
        "trading_pipeline": {"healthy_stage_count": 10},
        "repair_summary": {"local_repair_attempted": False},
    }
    critic = {
        "status": "passed",
        "operating_state": "healthy_idle_explained",
        "primary_reason": "No current setup is ready for paper review.",
    }

    first = send_team_health_telegram_update(team_health, critic, settings, sender=sender)
    second = send_team_health_telegram_update(team_health, critic, settings, sender=sender)
    changed = send_team_health_telegram_update(
        {**team_health, "status": "degraded", "healthy_required_role_count": 3},
        {**critic, "status": "degraded", "operating_state": "team_attention_required"},
        settings,
        sender=sender,
    )

    assert first["status"] == "delivered"
    assert second["status"] == "already_sent"
    assert changed["status"] == "delivered"
    assert len(messages) == 2
    assert "10/10 stages healthy" in messages[0]
    assert "Gemma completed local analysis" in messages[0]


def test_validator_rejects_unsafe_authority() -> None:
    payload = {
        "schema_version": "qadam_hedge_fund_team_health.v1",
        "artifact_type": "qadam_hedge_fund_team_health",
        "team": {
            "python_coo": {},
            "local_research_analyst": {},
            "frontier_strategy_lead": {},
            "head_of_quant": {},
            "fund_manager": {},
        },
        "trading_pipeline": {"stages": [{"stage": number} for number in range(1, 11)]},
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "quantum_job_submitted_count": 0,
        "authority": {**_team_authority(), "paperops_invocation_allowed": True},
    }

    assert "team_health_unsafe_authority:paperops_invocation_allowed" in (
        validate_hedge_fund_team_health(payload)
    )
