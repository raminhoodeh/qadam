#!/usr/bin/env python3
"""Acceptance check for Phase 1 data spine readiness.

This is intentionally stricter than the individual adapter checks. It verifies
that the source registry, heartbeat map, promoted adapter set, and deterministic
test-ingestion spine agree on the same public-safe source contract.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.ingestion import TestIngestionStore, run_test_ingestion
from orchestrator.source_health import PROMOTED_ADAPTER_STATUS, run_source_heartbeat
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT, SOURCE_SPECS

EXPECTED_PIPELINES = {"conflict", "physical", "macro", "market", "social"}
REQUIRED_PROMOTED_ADAPTERS = set(PROMOTED_ADAPTER_STATUS)
ALLOWED_RUNTIME_STATUSES = {
    "deferred",
    "derived",
    "fallback_only",
    "live_optional",
    "local_bridge_required",
    "ready_to_build",
    "ready_to_port",
    "registered",
    "unavailable_missing_credentials",
}
SECRET_VALUE_PREFIXES = ("ghp_", "vcp_", "sk-", "AIza", "sb_secret_", "PVZ")


def _secret_name_is_safe(name: str) -> bool:
    return "=" not in name and not name.startswith(SECRET_VALUE_PREFIXES)


def _load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def main() -> int:
    settings = Settings.from_env()
    errors: list[str] = []

    heartbeat = run_source_heartbeat(settings=settings)
    data_map = _load_json(heartbeat["data_environment_map_path"])
    sources = data_map.get("sources", [])
    summary = data_map.get("summary", {})
    registry_by_key = {source.key: source for source in SOURCE_SPECS}
    source_keys = [source.get("source_key") for source in sources]
    duplicate_keys = sorted(key for key, count in Counter(source_keys).items() if count > 1)
    pipeline_counts = Counter(source.get("pipeline") for source in sources)
    promoted_keys = {source.get("source_key") for source in sources if source.get("promoted_adapter")}

    if summary.get("source_count") != EXPECTED_SOURCE_COUNT or len(sources) != EXPECTED_SOURCE_COUNT:
        errors.append("source_count_mismatch")
    if set(source_keys) != set(registry_by_key):
        errors.append("source_key_set_mismatch")
    if duplicate_keys:
        errors.append(f"duplicate_source_keys:{','.join(str(key) for key in duplicate_keys)}")
    if set(pipeline_counts) != EXPECTED_PIPELINES:
        errors.append("pipeline_set_mismatch")
    if dict(sorted(pipeline_counts.items())) != summary.get("by_pipeline"):
        errors.append("pipeline_summary_mismatch")
    if set(PROMOTED_ADAPTER_STATUS) != REQUIRED_PROMOTED_ADAPTERS:
        errors.append("promoted_adapter_registry_mismatch")
    if not REQUIRED_PROMOTED_ADAPTERS.issubset(promoted_keys):
        errors.append("required_promoted_adapter_missing")

    for source in sources:
        key = source.get("source_key")
        spec = registry_by_key.get(str(key))
        if spec is None:
            continue
        runtime_status = str(source.get("runtime_status"))
        if runtime_status not in ALLOWED_RUNTIME_STATUSES:
            errors.append(f"invalid_runtime_status:{key}:{runtime_status}")
        if source.get("registry_status") != spec.status:
            errors.append(f"registry_status_mismatch:{key}")
        if source.get("endpoint_count") != len(spec.endpoints):
            errors.append(f"endpoint_count_mismatch:{key}")
        if source.get("tier") not in {1, 2, 3, 4}:
            errors.append(f"invalid_tier:{key}")
        if source.get("promoted_adapter"):
            trust_score = source.get("trust_score")
            if not isinstance(trust_score, (int, float)) or not 0 <= float(trust_score) <= 1:
                errors.append(f"promoted_adapter_trust_score_missing:{key}")
            if runtime_status not in {"live_optional", "unavailable_missing_credentials", "local_bridge_required"}:
                errors.append(f"promoted_adapter_bad_runtime:{key}:{runtime_status}")
        if (
            spec.status in {"needs_clarity", "needs_choice", "needs_new_adapter"}
            and not source.get("promoted_adapter")
            and runtime_status != "deferred"
        ):
            errors.append(f"unresolved_source_not_deferred:{key}")
        if spec.status == "derived" and runtime_status != "derived":
            errors.append(f"derived_source_bad_runtime:{key}")
        if spec.status == "local_bridge" and runtime_status != "local_bridge_required":
            errors.append(f"local_bridge_source_bad_runtime:{key}")
        if runtime_status == "unavailable_missing_credentials" and not source.get("missing_secrets"):
            errors.append(f"credential_block_without_missing_names:{key}")
        secret_names = list(source.get("configured_secrets") or []) + list(source.get("missing_secrets") or [])
        if any(not isinstance(name, str) or not _secret_name_is_safe(name) for name in secret_names):
            errors.append(f"unsafe_secret_name_shape:{key}")

    ingestion_store = TestIngestionStore(ROOT / settings.runtime_dir / "phase1_data_spine_observations.jsonl", settings)
    ingestion_log = EventLog(ROOT / settings.runtime_dir / "phase1_data_spine_event_log.jsonl", echo=False)
    ingestion = run_test_ingestion(limit=None, store=ingestion_store, event_log=ingestion_log)
    if ingestion["selected_count"] != EXPECTED_SOURCE_COUNT:
        errors.append("test_ingestion_not_full_registry")
    if ingestion["store"]["status"] != "ok":
        errors.append("test_ingestion_store_not_ok")
    if ingestion["event_log"]["status"] != "ok":
        errors.append("test_ingestion_event_log_not_ok")

    print("phase1_data_spine_status=" + ("ok" if not errors else "error"))
    print(f"phase1_data_spine_source_count={len(sources)}")
    print(f"phase1_data_spine_expected_source_count={EXPECTED_SOURCE_COUNT}")
    print(f"phase1_data_spine_pipeline_count={len(pipeline_counts)}")
    print(f"phase1_data_spine_promoted_adapter_count={len(promoted_keys)}")
    print(f"phase1_data_spine_missing_credential_source_count={summary.get('missing_credential_source_count', 0)}")
    print(f"phase1_data_spine_deferred_count={summary.get('deferred_count', 0)}")
    print(f"phase1_data_spine_test_observation_count={ingestion['selected_count']}")
    print("phase1_data_spine_boundary=Read-only source readiness and deterministic observations only. No signal confidence or execution authority.")
    for error in errors:
        print(f"phase1_data_spine_error={error}")

    if errors:
        return 1
    print("phase1_data_spine_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
