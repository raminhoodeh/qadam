#!/usr/bin/env python3
"""Validate the local Qadam foundation scaffold."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.agent_registry import agent_registry_summary
from orchestrator.agent_runtime import agent_runtime_summary
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT, SOURCE_SPECS, unresolved_sources
from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.execution import execution_registry
from orchestrator.local_store import local_store_health
from orchestrator.quantum import quantum_providers
from orchestrator.release_contract import PAPER_ACCOUNT_BALANCE_GBP
from orchestrator.secrets import validate_secret_file


def ensure_local_storage(settings: Settings) -> list[Path]:
    paths = [
        Path(settings.data_root),
        Path(settings.raw_payload_dir),
        Path(settings.runtime_dir),
        Path(settings.postgres_data_dir),
        Path(settings.chroma_persist_dir),
        Path(settings.local_backup_dir),
    ]
    for path in paths:
        resolved = path if path.is_absolute() else ROOT / path
        resolved.mkdir(parents=True, exist_ok=True)
        if not resolved.is_dir():
            raise RuntimeError(f"storage path is not a directory: {resolved}")
    return paths


def main() -> int:
    settings = Settings.from_env()
    storage_paths = ensure_local_storage(settings)
    print(f"qadam_env={settings.env}")
    print(f"qadam_mode={settings.mode}")
    print(f"trial_balance_gbp={settings.trial_balance_gbp}")
    print(f"fund_manager_allowlist={list(settings.fund_manager_allowlist)}")
    print(f"pending_fund_managers={list(settings.pending_fund_managers)}")
    print(f"local_storage_paths={[str(path) for path in storage_paths]}")
    secret_file_status = validate_secret_file(settings.secrets_file)
    print(f"secret_file_exists={secret_file_status['exists']}")
    print(f"secret_file_strict_permissions={secret_file_status['strict_permissions']}")
    if secret_file_status["exists"] and not secret_file_status["strict_permissions"]:
        print("secret_file_permissions_too_broad=true")
        return 1

    if settings.mode != "paper":
        print("qadam_mode_must_be_paper=true")
        return 1
    if settings.trial_balance_gbp != PAPER_ACCOUNT_BALANCE_GBP:
        print("trial_balance_mismatch=true")
        return 1

    count = len(SOURCE_SPECS)
    print(f"source_count={count}")
    print(f"expected_source_count={EXPECTED_SOURCE_COUNT}")
    if count != EXPECTED_SOURCE_COUNT:
        print("registry_count_mismatch=true")
        return 1

    by_pipeline = Counter(source.pipeline for source in SOURCE_SPECS)
    by_tier = Counter(source.tier for source in SOURCE_SPECS)
    print(f"pipelines={dict(sorted(by_pipeline.items()))}")
    print(f"tiers={dict(sorted(by_tier.items()))}")
    print(f"unresolved={[source.key for source in unresolved_sources()]}")

    venues = execution_registry()
    write_enabled = [
        venue["key"]
        for venue in venues
        if venue["mode"] == "live" or venue["write_health"] not in {"blocked_foundation_phase", "blocked_first_release"}
    ]
    print(f"execution_venues={[venue['key'] for venue in venues]}")
    print(f"execution_write_enabled={write_enabled}")
    if write_enabled:
        print("execution_must_be_disabled_in_foundation=true")
        return 1

    providers = quantum_providers(settings)
    print(f"quantum_providers={[provider['key'] + ':' + provider['status'] for provider in providers]}")
    qctrl = next(provider for provider in providers if provider["key"] == "qctrl")
    print(f"qctrl_configured={qctrl['credential_configured']}")

    agent_os = agent_registry_summary()
    print(f"agent_os_status={agent_os['status']}")
    print(f"agent_os_agent_count={agent_os['agent_count']}")
    print(f"agent_os_skill_count={agent_os['skill_count']}")
    if agent_os["status"] != "ok":
        print("agent_os_not_ok=true")
        return 1

    agent_runtime = agent_runtime_summary(settings)
    print(f"agent_runtime_status={agent_runtime['status']}")
    print(f"agent_runtime_authorization_check_count={agent_runtime['authorization_check_count']}")
    print(f"agent_runtime_expected_block_count={agent_runtime['expected_block_count']}")
    if agent_runtime["status"] != "ok":
        print("agent_runtime_not_ok=true")
        return 1

    event_log_path = (ROOT / settings.runtime_dir / "foundation_check_event_log.jsonl").resolve()
    event_log = EventLog(event_log_path, echo=False)
    event_log.write(
        "foundation_check_event",
        "foundation_check",
        {"source_count": count, "execution_write_enabled": len(write_enabled)},
    )
    replay = event_log.replay()
    event_log_health = event_log.health()
    print(f"event_log_backend={event_log_health['backend']}")
    print(f"event_log_status={event_log_health['status']}")
    print(f"event_log_total_events={replay['total_events']}")
    if event_log_health["status"] != "ok":
        print("event_log_health_not_ok=true")
        return 1
    if replay["total_events"] < 1:
        print("event_log_replay_empty=true")
        return 1

    storage_health = local_store_health(settings)
    print(f"local_store_status={storage_health['status']}")
    print(f"local_store_reachable_services={storage_health['summary']['reachable_services']}")
    print(f"local_store_offline_services={storage_health['summary']['offline_services']}")
    if storage_health["status"] == "error":
        print("local_store_directory_error=true")
        return 1

    print("foundation_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
