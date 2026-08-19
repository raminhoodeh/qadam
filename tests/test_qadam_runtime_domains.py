from orchestrator.qadam_operator_service import SERVICE_DEFINITIONS
from orchestrator.qadam_runtime_domains import (
    order_by_domain,
    service_domain,
    validate_domain_coverage,
)


def test_every_active_service_has_exactly_one_domain() -> None:
    service_ids = [definition.service_id for definition in SERVICE_DEFINITIONS]
    assert validate_domain_coverage(service_ids) == []
    assert all(service_domain(service_id) in {"execution", "research", "projection"} for service_id in service_ids)


def test_execution_domain_is_dispatched_before_research_and_projection() -> None:
    ordered = order_by_domain(
        ("dashboard_refresh", "source_ingestion", "execution_context"),
        service_id_getter=lambda value: value,
        secondary_priority_getter=lambda _value: 0,
    )
    assert ordered == ("execution_context", "source_ingestion", "dashboard_refresh")
