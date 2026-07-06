#!/usr/bin/env python3
"""Validate Qadam operational soak run and final declaration artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qadam_operational_soak_run import (
    DAILY_SUMMARIES_ARTIFACT,
    FINAL_DECLARATION_ARTIFACT,
    INCIDENT_LOG_ARTIFACT,
    PRIMARY_ARTIFACT,
    _runtime_dir,
    build_and_write_operational_soak_run,
    validate_operational_soak,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    settings = Settings.from_env()
    payload, final_declaration, written, errors = build_and_write_operational_soak_run(settings, refresh_certification=True)
    runtime = _runtime_dir(settings)
    loaded = _load_json(runtime / PRIMARY_ARTIFACT)
    final = _load_json(runtime / FINAL_DECLARATION_ARTIFACT)
    daily = _read_jsonl(runtime / DAILY_SUMMARIES_ARTIFACT)
    incidents = _read_jsonl(runtime / INCIDENT_LOG_ARTIFACT)
    validation_errors = list(errors)

    for filename in (PRIMARY_ARTIFACT, DAILY_SUMMARIES_ARTIFACT, INCIDENT_LOG_ARTIFACT, FINAL_DECLARATION_ARTIFACT):
        if not (runtime / filename).exists():
            validation_errors.append(f"{filename}_missing")

    validation_errors.extend(validate_operational_soak(loaded, final))
    if loaded.get("observed_soak_day_count") != len({row.get("soak_date") for row in daily if row.get("soak_date")}):
        validation_errors.append("soak_day_count_mismatch")
    if loaded.get("unresolved_incident_count") != len(incidents):
        validation_errors.append("incident_count_mismatch")
    if final.get("generated_at") != final_declaration.get("generated_at"):
        validation_errors.append("final_declaration_generated_at_mismatch")

    print(f"artifact={written.get('primary')}")
    print(f"daily_summaries={written.get('daily_summaries')}")
    print(f"incident_log={written.get('incident_log')}")
    print(f"final_declaration={written.get('final_declaration')}")
    print(f"status={loaded.get('status')}")
    print(f"soak_complete={loaded.get('soak_complete')}")
    print(f"observed_soak_day_count={loaded.get('observed_soak_day_count')}")
    print(f"required_soak_days={loaded.get('required_soak_days')}")
    print(f"operationally_complete={loaded.get('operationally_complete')}")
    print(f"certification_status={loaded.get('certification_status')}")
    print(f"unresolved_incident_count={loaded.get('unresolved_incident_count')}")
    print(f"unresolved_critical_incident_count={loaded.get('unresolved_critical_incident_count')}")
    print(f"final_declaration_status={final.get('status')}")
    print(f"calendar_honest={loaded.get('calendar_honest')}")
    print(f"simulated_elapsed_time_allowed={loaded.get('simulated_elapsed_time_allowed')}")
    print(f"paper_order_created_count={loaded.get('paper_order_created_count')}")
    print(f"broker_write_count={loaded.get('broker_write_count')}")
    print(f"live_capital_enabled={loaded.get('live_capital_enabled')}")

    if validation_errors:
        for error in sorted(set(validation_errors)):
            print(f"error={error}")
        return 1
    if payload.get("generated_at") != loaded.get("generated_at"):
        print("error=written_generated_at_mismatch")
        return 1
    print("qadam_operational_soak_run_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
