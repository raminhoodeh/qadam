from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import time

import orchestrator.paperops_qctrl_consultation as consultation
import scripts.check_paperops_qctrl_consultation as checker


def _verified_artifact(verified_at: datetime) -> dict[str, object]:
    return {
        "status": "consultation_recorded",
        "generated_at": verified_at.isoformat(),
        "provider_verified_at": verified_at.isoformat(),
        "provider_call_succeeded": True,
        "provider_call_attempted": True,
        "provider_call_count": 1,
        "qctrl_paper_consultation_enabled": True,
    }


def test_recent_verified_consultation_is_reused_without_provider_call(monkeypatch) -> None:
    verified_at = datetime.now(timezone.utc) - timedelta(hours=1)
    artifact = _verified_artifact(verified_at)
    settings = SimpleNamespace(qctrl_paper_consultation_enabled=True)
    calls: list[bool | None] = []

    monkeypatch.setattr(
        checker,
        "read_latest_paperops_qctrl_consultation",
        lambda _settings: artifact,
    )

    def _build(_settings, *, allow_provider_call=None):
        calls.append(allow_provider_call)
        if allow_provider_call is not False:
            raise AssertionError("recent verification must not call Q-CTRL")
        return {"provider_call_allowed": True}

    monkeypatch.setattr(checker, "build_paperops_qctrl_consultation", _build)

    selected, preserved, reason = checker._select_consultation_artifact(settings)

    assert calls == [False]
    assert preserved is True
    assert reason == "recent_verified_consultation_reused_without_provider_call"
    assert selected["provider_call_reused"] is True
    assert selected["provider_verified_at"] == verified_at.isoformat()
    assert selected["generated_at"] != artifact["generated_at"]


def test_stale_verification_requires_bounded_provider_probe(monkeypatch) -> None:
    verified_at = datetime.now(timezone.utc) - timedelta(days=8)
    artifact = _verified_artifact(verified_at)
    settings = SimpleNamespace(qctrl_paper_consultation_enabled=True)
    calls: list[bool | None] = []
    candidate = {
        "status": "consultation_recorded",
        "provider_call_succeeded": True,
        "provider_call_attempted": True,
        "provider_call_count": 1,
        "qctrl_paper_consultation_enabled": True,
    }

    monkeypatch.setattr(
        checker,
        "read_latest_paperops_qctrl_consultation",
        lambda _settings: artifact,
    )

    def _build(_settings, *, allow_provider_call=None):
        calls.append(allow_provider_call)
        if allow_provider_call is False:
            return {"provider_call_allowed": True}
        return candidate

    monkeypatch.setattr(checker, "build_paperops_qctrl_consultation", _build)

    selected, preserved, reason = checker._select_consultation_artifact(settings)

    assert calls == [False, None]
    assert selected is candidate
    assert preserved is False
    assert reason == "none"


def test_provider_auth_probe_times_out_and_is_classified_as_network_error(
    monkeypatch,
) -> None:
    settings = SimpleNamespace(qctrl_organization_slug=None)

    def _import_module(name: str):
        if name == "qctrlworkflowclient.utils":
            return SimpleNamespace(
                get_installed_version=lambda _package: "1",
                get_latest_pypi_version=lambda _package: "1",
            )
        return SimpleNamespace(authenticate_qctrl_account=lambda **_kwargs: time.sleep(0.25))

    monkeypatch.setattr(consultation, "secret_value", lambda *_args: "configured")
    monkeypatch.setattr(consultation.importlib, "import_module", _import_module)
    monkeypatch.setattr(consultation, "PAPEROPS_QCTRL_AUTH_TIMEOUT_SECONDS", 0.01)

    started = time.monotonic()
    result = consultation._provider_auth_probe(
        module_name="fake_qctrl",
        settings=settings,
    )

    assert time.monotonic() - started < 0.2
    assert result["provider_call_attempted"] is True
    assert result["provider_call_succeeded"] is False
    assert result["provider_failure_class"] == "TimeoutError"
    assert result["provider_failure_category"] == "provider_network_error"
