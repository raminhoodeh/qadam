from __future__ import annotations

from types import SimpleNamespace

from orchestrator import secrets


def test_keychain_secret_value_reads_qadam_service(monkeypatch):
    secrets._keychain_secret_value.cache_clear()
    monkeypatch.setattr(secrets.sys, "platform", "darwin")
    observed = {}

    def fake_run(command, **kwargs):
        observed["command"] = command
        observed["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout="stored-value\n")

    monkeypatch.setattr(secrets.subprocess, "run", fake_run)
    assert secrets._keychain_secret_value("EXAMPLE_KEY") == "stored-value"
    assert observed["command"] == [
        "/usr/bin/security",
        "find-generic-password",
        "-a",
        "qadam",
        "-s",
        "qadam:EXAMPLE_KEY",
        "-w",
    ]
    assert observed["kwargs"]["capture_output"] is True


def test_keychain_secret_value_fails_closed(monkeypatch):
    secrets._keychain_secret_value.cache_clear()
    monkeypatch.setattr(secrets.sys, "platform", "darwin")
    monkeypatch.setattr(
        secrets.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=44, stdout=""),
    )
    assert secrets._keychain_secret_value("MISSING_KEY") is None
