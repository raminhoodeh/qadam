#!/usr/bin/env python3
"""Validate credential-bound read-only source adapter contracts.

This check is intentionally isolated from the operator's real secret file. It
creates temporary strict-permission secret files and proves that credential-bound
sources activate only when their own credential contract is satisfied.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import stat
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings, _file_env_values  # noqa: E402
from orchestrator.credential_bound_adapters import (  # noqa: E402
    credential_bound_adapter_keys,
    credential_bound_adapter_registry,
    credential_bound_adapter_state,
)
from orchestrator.phase1_live_adapters import (  # noqa: E402
    Phase1ReadOnlyAdapter,
    phase1_live_adapter_status,
)


CHECKED_KEYS = ("reddit", "kalshi", "stock_act")
SECRET_ENV_KEYS = (
    "REDDIT_CLIENT_ID",
    "REDDIT_CLIENT_SECRET",
    "REDDIT_USER_AGENT",
    "KALSHI_API_KEY",
    "KALSHI_API_SECRET",
    "KALSHI_API_BASE_URL",
    "CAPITOL_TRADES_API_KEY",
    "CAPITOL_TRADES_API_URL",
    "CAPITOL_TRADES_APIFY_ACTOR_ID",
)
SECRET_LIKE_PATTERNS = (
    re.compile(r"\d{6,}:[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bvcp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bPVZ[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
)


@contextmanager
def _isolated_settings(secret_lines: tuple[str, ...]) -> Iterator[Settings]:
    previous_env = {key: os.environ.get(key) for key in SECRET_ENV_KEYS}
    previous_qadam_env = {
        key: os.environ.get(key)
        for key in (
            "QADAM_SECRETS_FILE",
            "QADAM_RUNTIME_DIR",
            "QADAM_RAW_PAYLOAD_DIR",
        )
    }
    with tempfile.TemporaryDirectory(prefix="qadam-credential-bound-") as tmp:
        tmp_path = Path(tmp)
        secret_path = tmp_path / "qadam-secrets.env"
        secret_path.write_text("\n".join(secret_lines) + ("\n" if secret_lines else ""), encoding="utf-8")
        secret_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        os.environ["QADAM_SECRETS_FILE"] = str(secret_path)
        os.environ["QADAM_RUNTIME_DIR"] = str(tmp_path / "runtime")
        os.environ["QADAM_RAW_PAYLOAD_DIR"] = str(tmp_path / "raw_payloads")
        for key in SECRET_ENV_KEYS:
            os.environ.pop(key, None)
        _file_env_values.cache_clear()
        try:
            yield Settings.from_env()
        finally:
            for key, value in previous_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            for key, value in previous_qadam_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            _file_env_values.cache_clear()


def _contains_secret_like_value(payload: Any) -> bool:
    encoded = json.dumps(payload, sort_keys=True, default=str)
    return any(pattern.search(encoded) for pattern in SECRET_LIKE_PATTERNS)


def _assert_authority_boundary(state: dict[str, Any], errors: list[str]) -> None:
    if state.get("order_authority") != "none":
        errors.append(f"order_authority_leaked:{state.get('source_key')}")
    if state.get("paper_trading_blocking") is not False:
        errors.append(f"paper_trading_blocking_changed:{state.get('source_key')}")
    if state.get("live_capital_authority") is not False:
        errors.append(f"live_capital_authority_leaked:{state.get('source_key')}")
    if state.get("evidence_authority") != "supplemental_readonly_context":
        errors.append(f"evidence_authority_unexpected:{state.get('source_key')}")


async def _fetch_live_state(source_key: str, settings: Settings) -> dict[str, Any]:
    return (await Phase1ReadOnlyAdapter(source_key, settings=settings).fetch_live()).to_dict()


def main() -> int:
    errors: list[str] = []
    observed: dict[str, Any] = {}

    if credential_bound_adapter_keys() != CHECKED_KEYS:
        errors.append("credential_bound_key_set_mismatch")

    with _isolated_settings(()) as settings:
        registry = credential_bound_adapter_registry(settings)
        observed["missing_registry"] = registry
        if registry.get("adapter_count") != 3:
            errors.append("credential_bound_adapter_count_mismatch")
        if registry.get("missing_credentials_count") != 3:
            errors.append("missing_credentials_count_mismatch")
        for key in CHECKED_KEYS:
            state = credential_bound_adapter_state(key, settings)
            observed[f"{key}_missing"] = state
            if state.get("activation_state") != "missing_credentials":
                errors.append(f"missing_state_not_missing:{key}")
            _assert_authority_boundary(state, errors)
            status = phase1_live_adapter_status(key, settings)
            if status.get("credential_bound") is not True:
                errors.append(f"phase1_status_not_credential_bound:{key}")
            live_result = asyncio.run(_fetch_live_state(key, settings))
            if not live_result.get("degraded"):
                errors.append(f"missing_credential_live_fetch_not_degraded:{key}")
            if live_result.get("degraded_reason") != "missing_credentials":
                errors.append(f"missing_credential_live_fetch_reason_mismatch:{key}")
            events = live_result.get("events", [])
            if isinstance(events, list) and events:
                errors.append(f"missing_credential_live_fetch_created_events:{key}")

    scenarios: tuple[tuple[str, tuple[str, ...], str], ...] = (
        (
            "reddit",
            (
                "REDDIT_CLIENT_ID=dummy_client_id",
                "REDDIT_CLIENT_SECRET=dummy_client_secret",
                "REDDIT_USER_AGENT=Qadam/0.1 test",
            ),
            "ready_for_live_readonly",
        ),
        (
            "kalshi",
            (
                "KALSHI_API_KEY=dummy_key_id",
                "KALSHI_API_SECRET=dummy_private_key_reference",
                "KALSHI_API_BASE_URL=https://trading-api.kalshi.com",
            ),
            "ready_for_live_readonly",
        ),
        (
            "stock_act",
            (
                "CAPITOL_TRADES_API_KEY=dummy_capitol_key",
            ),
            "ready_for_live_readonly",
        ),
        (
            "stock_act",
            (
                "CAPITOL_TRADES_API_KEY=dummy_capitol_key",
                "CAPITOL_TRADES_API_URL=https://api.apify.com/v2/actors/saswave~capitol-trades-scraper/run-sync-get-dataset-items",
            ),
            "ready_for_live_readonly",
        ),
    )
    for source_key, secret_lines, expected_state in scenarios:
        with _isolated_settings(secret_lines) as settings:
            state = credential_bound_adapter_state(source_key, settings)
            observed[f"{source_key}_{expected_state}"] = state
            if state.get("activation_state") != expected_state:
                errors.append(f"activation_state_mismatch:{source_key}:{expected_state}")
            if state.get("activation_ready") is not (expected_state == "ready_for_live_readonly"):
                errors.append(f"activation_ready_mismatch:{source_key}:{expected_state}")
            _assert_authority_boundary(state, errors)
            status = phase1_live_adapter_status(source_key, settings)
            if status.get("activation_ready") is not (expected_state == "ready_for_live_readonly"):
                errors.append(f"phase1_activation_ready_mismatch:{source_key}:{expected_state}")

    if _contains_secret_like_value(observed):
        errors.append("secret_like_value_detected")

    print("credential_bound_adapter_status=" + ("ok" if not errors else "error"))
    print(f"credential_bound_adapter_count={len(CHECKED_KEYS)}")
    print("credential_bound_adapter_keys=" + ",".join(CHECKED_KEYS))
    print("credential_bound_missing_state_passed=" + str(not any(error.startswith("missing_state_") for error in errors)))
    print("credential_bound_activation_state_passed=" + str(not any("activation_state" in error for error in errors)))
    print("credential_bound_authority_unchanged=" + str(not any("authority" in error or "blocking_changed" in error for error in errors)))
    print("credential_bound_secret_values_public_safe=" + str("secret_like_value_detected" not in errors))
    print("credential_bound_boundary=Read-only source adapters only. No source can approve signals, submit orders, call brokers, or enable live capital.")
    for error in errors:
        print(f"credential_bound_adapter_error={error}")
    if errors:
        return 1
    print("credential_bound_adapter_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
