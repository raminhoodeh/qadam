from orchestrator.qadam_operator_service import SERVICE_DEFINITIONS
from orchestrator import qadam_runtime_domains as domains
from orchestrator.qadam_runtime_domains import (
    order_by_domain,
    order_by_domain_reservations,
    service_domain,
    validate_domain_coverage,
)


def test_every_active_service_has_exactly_one_domain() -> None:
    service_ids = [definition.service_id for definition in SERVICE_DEFINITIONS]
    assert validate_domain_coverage(service_ids) == []
    assert all(service_domain(service_id) in {"execution", "research", "projection"} for service_id in service_ids)


def test_one_policy_snapshot_per_dispatch_and_reload_next_call(monkeypatch):
    original = domains.load_domain_policy
    calls = []

    def load():
        calls.append(1)
        return original()

    monkeypatch.setattr(domains, "load_domain_policy", load)
    records = tuple(definition.service_id for definition in SERVICE_DEFINITIONS)
    for expected in (1, 2):
        domains.order_by_domain_reservations(
            records, service_id_getter=str, secondary_priority_getter=lambda _: 0, max_jobs=10)
        assert len(calls) == expected


def test_execution_domain_is_dispatched_before_research_and_projection() -> None:
    ordered = order_by_domain(
        ("dashboard_refresh", "source_ingestion", "execution_context"),
        service_id_getter=lambda value: value,
        secondary_priority_getter=lambda _value: 0,
    )
    assert ordered == ("execution_context", "source_ingestion", "dashboard_refresh")


def test_domain_reservations_prevent_projection_starvation() -> None:
    records = tuple(definition.service_id for definition in SERVICE_DEFINITIONS)

    ordered = order_by_domain_reservations(
        records,
        service_id_getter=lambda value: value,
        secondary_priority_getter=lambda _value: 0,
        max_jobs=10,
    )
    scheduled = ordered[:10]

    assert sum(service_domain(value) == "execution" for value in scheduled) == 8
    assert sum(service_domain(value) == "research" for value in scheduled) == 1
    assert sum(service_domain(value) == "projection" for value in scheduled) == 1


def test_domain_reservations_preserve_rotated_order_within_domain() -> None:
    records = (
        "dashboard_refresh",
        "public_status_publication",
        "active_discovery_trial",
        "source_ingestion",
        "execution_context",
    )

    ordered = order_by_domain_reservations(
        records,
        service_id_getter=lambda value: value,
        secondary_priority_getter=lambda _value: 0,
        max_jobs=3,
    )

    assert ordered[:3] == (
        "execution_context",
        "source_ingestion",
        "dashboard_refresh",
    )
