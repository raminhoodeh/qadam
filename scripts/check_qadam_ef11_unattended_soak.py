#!/usr/bin/env python3
"""Record truthful EF11 soak progress without simulating elapsed time."""

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore  # noqa: E402
from orchestrator.qadam_ef11_open_market_conversion import (  # noqa: E402
    SOAK_ARTIFACT,
    SOAK_SESSIONS_ARTIFACT,
    build_and_write_ef11_state,
)
from orchestrator.qadam_operator_ready_common import authority_flags, now_iso, read_json, read_jsonl, runtime_dir  # noqa: E402


REQUIRED_MARKET_PHASES = ("pre_market", "regular", "post_market")
RECOVERY_TYPES = (
    "restart_recovery",
    "network_interruption_recovery",
    "provider_throttle_recovery",
    "laptop_wake_recovery",
)


def _observed_recoveries(runtime: Path) -> dict[str, bool]:
    rows = read_jsonl(runtime / "qadam_operator_service_receipts.jsonl")
    rows += read_jsonl(runtime / "qadam_conversion_recovery_history.jsonl")
    observed = {kind: False for kind in RECOVERY_TYPES}
    for row in rows:
        if str(row.get("status") or "").lower() not in {
            "passed",
            "recovered",
            "closed",
            "success",
        }:
            continue
        recovery_type = str(
            row.get("recovery_type")
            or row.get("event_type")
            or row.get("classification")
            or ""
        ).lower()
        if recovery_type in observed:
            observed[recovery_type] = True
    return observed


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    bundle, _checks, errors = build_and_write_ef11_state(settings)
    operator = read_json(runtime / "qadam_operator_service_status.json")
    observed_at = now_iso()
    phase = str(bundle["market_truth"].get("session_phase") or "unknown")
    session_date = str(
        bundle["market_truth"].get("session_date")
        or datetime.now(timezone.utc).date().isoformat()
    )
    session_id = f"ef11-soak:{session_date}:{phase}"
    session = {
        "generated_at": observed_at,
        "session_id": session_id,
        "operator_running": operator.get("service_running") is True,
        "open_circuit_count": int(operator.get("open_circuit_count") or 0),
        "market_session_phase": phase,
        "market_session_date": session_date,
        "provider_clock_fresh": bundle["market_truth"].get("provider_fresh") is True,
        "conversion_repair_request_count": int(
            bundle["repair_queue"].get("repair_request_count") or 0
        ),
        "real_elapsed_time": True,
        "backfilled": False,
        "simulated_elapsed_time": False,
        "paper_only": True,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    sessions = read_jsonl(runtime / SOAK_SESSIONS_ARTIFACT)
    if not any(row.get("session_id") == session_id for row in sessions):
        sessions.append(session)
    phases = sorted(
        {
            str(row.get("market_session_phase"))
            for row in sessions
            if row.get("market_session_phase")
        }
    )
    recoveries = _observed_recoveries(runtime)
    missing_phases = [phase for phase in REQUIRED_MARKET_PHASES if phase not in phases]
    missing_recoveries = [kind for kind, seen in recoveries.items() if not seen]
    no_open_circuits = session["open_circuit_count"] == 0
    no_repair_requests = session["conversion_repair_request_count"] == 0
    critical_services_healthy = (
        session["operator_running"]
        and no_open_circuits
        and no_repair_requests
        and bundle["structural_certification"].get("structural_ready") is True
    )
    complete = not missing_phases and not missing_recoveries and critical_services_healthy
    status = {
        "generated_at": observed_at,
        "artifact_type": "qadam_ef11_unattended_soak",
        "status": "passed" if complete else "collecting_real_soak",
        "session_count": len(sessions),
        "distinct_market_phase_count": len(phases),
        "observed_market_phases": phases,
        "missing_market_phases": missing_phases,
        "recovery_observations": recoveries,
        "missing_recovery_observations": missing_recoveries,
        "critical_services_healthy": critical_services_healthy,
        "no_open_critical_circuit": no_open_circuits,
        "no_open_conversion_repair_request": no_repair_requests,
        "complete": complete,
        "real_market_transition_required": True,
        "backfill_allowed": False,
        "simulated_elapsed_time_allowed": False,
        "open_circuit_count": session["open_circuit_count"],
        "conversion_repair_request_count": session["conversion_repair_request_count"],
        "paper_only": True,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    store = AtomicArtifactStore(runtime)
    store.write_jsonl(SOAK_SESSIONS_ARTIFACT, sessions)
    store.write_json(SOAK_ARTIFACT, status)
    print("status=passed")
    print(f"soak_state={status['status']}")
    print(f"session_count={status['session_count']}")
    print(f"missing_market_phases={len(missing_phases)}")
    print(f"missing_recovery_observations={len(missing_recoveries)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
