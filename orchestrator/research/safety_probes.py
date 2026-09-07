"""Executable, isolated boundary probes; no fabricated historical certification."""

from datetime import datetime, timedelta, timezone


def run_probes():
    from scripts.run_qadam_live_source_refresh import _new_research_goal_events
    from orchestrator.storage.benchmarks import record_observations, matched_fill_benchmark
    from orchestrator.learning.forward_evaluation import evaluate_forward_version
    from orchestrator.qadam_operator_ready_common import validate_authority

    now = datetime.now(timezone.utc)
    base = {"normalised_summary": "Fixture boundary probe", "event_timestamp": now.isoformat(),
            "raw_payload": {"record_id": "boundary-probe"}}

    def rejected(event, reason):
        rows, counts = _new_research_goal_events("boundary_probe", {"events": [event]}, seen_event_refs=set(), now=now)
        return not rows and counts.get(reason) == 1

    probes = {
        "sample_source_not_ingested": lambda: rejected({**base, "raw_payload": {"sample": True}}, "sample"),
        "future_source_not_ingested": lambda: rejected({**base, "event_timestamp": (now + timedelta(days=1)).isoformat()}, "future"),
        "secret_source_not_ingested": lambda: rejected({**base, "normalised_summary": "ghp_" + "x" * 30}, "secret_like_content"),
        "benchmark_sample_cannot_write": lambda: record_observations(None, [{"instrument": "SPY", "sample": True}]) == 0,
        "invalid_fill_window_has_no_benchmark": lambda: matched_fill_benchmark(None, "invalid", "invalid", cost_bps=1)["benchmark_comparison_available"] is False,
        "unregistered_forward_sample_cannot_promote": lambda: evaluate_forward_version(None, [], as_of=now.isoformat())["eligible_for_emerging_review"] is False,
        "broker_authority_flag_rejected": lambda: bool(validate_authority({"broker_write_allowed": True})),
    }
    results = []
    for name, probe in probes.items():
        try:
            passed = probe() is True
            failure = None
        except Exception as exc:
            passed, failure = False, type(exc).__name__
        results.append({"probe": name, "status": "passed" if passed else "failed",
            "executed_at": now.isoformat(), "evidence_kind": "executed_production_boundary",
            "fixture_only": True, "failure_class": failure, "unsafe_side_effect_count": 0,
            "scope": "contract_boundary_not_full_broker_or_historical_certification"})
    return results
