from dataclasses import replace

from orchestrator.config import Settings
from orchestrator.qadam_local_model_lock import local_model_lock
from orchestrator.qadam_hedge_fund_team_health import ensure_local_research_analyst_ready
from orchestrator.intelligence import run_local_research_analyst_inference


def setup(tmp_path, monkeypatch):
    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path), state_root=str(tmp_path))
    monkeypatch.setattr("orchestrator.qadam_hedge_fund_team_health.lm_studio_models_probe",
                        lambda *a, **k: {"probe_status": "ok", "model_available": True,
                                         "resolved_model": "gemma-test"})
    monkeypatch.setattr("orchestrator.qadam_hedge_fund_team_health._lms_executable", lambda: "/fake/lms")
    monkeypatch.setattr("orchestrator.qadam_hedge_fund_team_health.secret_value",
                        lambda key, _: "google/gemma-test" if key == "LM_STUDIO_MODEL" else None)
    return settings


def test_inference_timeout_reloads_only_configured_model_then_cools_down(tmp_path, monkeypatch):
    settings = setup(tmp_path, monkeypatch)
    commands = []
    def command_runner(command, timeout):
        commands.append(command)
        return {"returncode": 0, "status": "passed"}
    args = dict(repair=True, inference_failed=True, command_runner=command_runner, sleep_fn=lambda _: None)
    result = ensure_local_research_analyst_ready(settings, **args)
    assert result["status"] == "ready"
    assert commands == [("/fake/lms", "unload", "gemma-test"),
                        ("/fake/lms", "load", "google/gemma-test", "--identifier", "gemma-test", "-y")]
    assert ensure_local_research_analyst_ready(settings, **args)["reason"] == "local_model_reload_cooldown"
    assert len(commands) == 2


def test_reload_and_second_inference_do_not_interrupt_an_active_request(tmp_path, monkeypatch):
    settings = setup(tmp_path, monkeypatch)
    with local_model_lock(tmp_path) as acquired:
        assert acquired
        result = ensure_local_research_analyst_ready(settings, repair=True, inference_failed=True)
        assert result["reason"] == "local_inference_busy"
        assert ensure_local_research_analyst_ready(settings, repair=True)["reason"] == "local_inference_busy"
        assert run_local_research_analyst_inference(settings=settings, live=True)["reason"] == "local_inference_busy"
    with local_model_lock(tmp_path) as acquired:
        assert acquired


def test_remote_endpoint_cannot_trigger_local_reload(tmp_path, monkeypatch):
    settings = setup(tmp_path, monkeypatch)
    monkeypatch.setattr("orchestrator.qadam_hedge_fund_team_health.secret_value", lambda *a: "https://remote.example/v1")
    assert ensure_local_research_analyst_ready(settings, repair=True, inference_failed=True)["reason"] == "remote_model_reload_not_permitted"


def test_failed_unload_does_not_load_another_copy(tmp_path, monkeypatch):
    settings = setup(tmp_path, monkeypatch)
    commands = []
    def run(command, timeout):
        commands.append(command)
        return {"returncode": 1, "status": "failed"}
    result = ensure_local_research_analyst_ready(settings, repair=True, inference_failed=True,
                                               command_runner=run, sleep_fn=lambda _: None)
    assert result["reason"] == "local_model_unload_failed"
    assert len(commands) == 1
