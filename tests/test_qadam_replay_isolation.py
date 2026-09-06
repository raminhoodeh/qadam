import os

import pytest

from scripts.profile_qadam_dashboard_replay import _deny_effects, _replay_environment


@pytest.mark.parametrize("event,args", [
    ("socket.getaddrinfo", ("example.com", 443)), ("socket.connect", (None, None)),
    ("subprocess.Popen", ("python",)), ("os.posix_spawn", ("python",)),
    ("open", ("data/runtime/qadam-secrets.env", "r", 0)),
    ("open", (".env.local", "r", 0)),
    ("open", ("output.json", "w", 0)),
    ("open", ("output.json", None, os.O_WRONLY | os.O_CREAT)),
    ("sqlite3.connect", ("file:/tmp/copy.sqlite3?mode=rw",)),
    ("sqlite3.connect", ("/tmp/copy.sqlite3",)),
    ("os.rename", ("a", "b")),
])
def test_replay_denies_credentials_external_effects_and_database_writes(event, args):
    with pytest.raises(RuntimeError, match="read_only_replay_"):
        _deny_effects(event, args)


def test_replay_can_read_captured_inputs_and_read_only_database():
    _deny_effects("open", ("captured.json", "r", 0))
    _deny_effects("open", ("/usr/lib/python3.12/secrets.py", "r", 0))
    _deny_effects("sqlite3.connect", ("file:/tmp/isolated-control-plane.sqlite3?mode=ro",))


def test_replay_does_not_inherit_tokens_or_authority_flags(tmp_path):
    result = _replay_environment({"PATH": "/usr/bin", "HOME": "/tmp",
        "ALPACA_API_KEY": "fixture", "QADAM_EXECUTION_OWNER_TOKEN": "fixture",
        "TELEGRAM_BOT_TOKEN": "fixture", "UNKNOWN_PROVIDER_API_KEY": "fixture",
        "QADAM_ALPACA_PAPER_SUBMIT_ENABLED": "true"}, tmp_path, tmp_path / "runtime")
    assert result["PATH"] == "/usr/bin"
    assert result["QADAM_ALPACA_PAPER_SUBMIT_ENABLED"] == "false"
    assert result["QADAM_ALPACA_PAPER_EXIT_ENABLED"] == "false"
    assert not any(key in result for key in ("ALPACA_API_KEY", "QADAM_EXECUTION_OWNER_TOKEN",
        "TELEGRAM_BOT_TOKEN", "UNKNOWN_PROVIDER_API_KEY"))
