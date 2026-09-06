"""Authoritative scheduler domains for Qadam's unattended operator."""

from __future__ import annotations

import json
from typing import Any, Iterable, TypeVar

from orchestrator.paths import project_root

REPO_ROOT = project_root()
POLICY_PATH = REPO_ROOT / "config" / "qadam_scheduler_domains.json"

T = TypeVar("T")


def load_domain_policy() -> dict[str, Any]:
    payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    domains = payload.get("domains")
    if not isinstance(domains, dict) or set(domains) != {
        "execution",
        "research",
        "projection",
    }:
        raise ValueError("scheduler_domain_policy_invalid")
    seen: set[str] = set()
    duplicates: set[str] = set()
    for record in domains.values():
        service_ids = record.get("service_ids") if isinstance(record, dict) else None
        if not isinstance(service_ids, list):
            raise ValueError("scheduler_domain_services_invalid")
        for service_id in service_ids:
            normalized = str(service_id)
            if normalized in seen:
                duplicates.add(normalized)
            seen.add(normalized)
    if duplicates:
        raise ValueError("scheduler_service_in_multiple_domains:" + ",".join(sorted(duplicates)))
    return payload


def service_domain(service_id: str) -> str:
    return _service_domain(service_id, load_domain_policy())


def _service_domain(service_id: str, policy: dict[str, Any]) -> str:
    for domain, record in policy["domains"].items():
        if service_id in record["service_ids"]:
            return str(domain)
    raise ValueError(f"scheduler_service_domain_missing:{service_id}")


def validate_domain_coverage(service_ids: Iterable[str]) -> list[str]:
    policy = load_domain_policy()
    configured = {
        str(service_id)
        for record in policy["domains"].values()
        for service_id in record["service_ids"]
    }
    active = {str(service_id) for service_id in service_ids}
    errors = [f"scheduler_domain_missing:{value}" for value in sorted(active - configured)]
    errors.extend(f"scheduler_unknown_service:{value}" for value in sorted(configured - active))
    if int(policy.get("max_jobs_per_cycle") or 0) < 3:
        errors.append("scheduler_cycle_budget_below_domain_count")
    if int(policy["domains"]["execution"].get("reserved_jobs_per_cycle") or 0) < 1:
        errors.append("execution_capacity_not_reserved")
    return errors


def order_by_domain(
    records: Iterable[T],
    *,
    service_id_getter,
    secondary_priority_getter,
) -> tuple[T, ...]:
    """Put execution first while preserving fair ordering within each domain."""

    policy = load_domain_policy()
    return _order_by_domain(records, service_id_getter=service_id_getter,
                            secondary_priority_getter=secondary_priority_getter, policy=policy)


def _order_by_domain(records, *, service_id_getter, secondary_priority_getter, policy):
    materialized = tuple(records)
    priorities = {
        domain: int(record.get("priority") or 0)
        for domain, record in policy["domains"].items()
    }
    input_order = {
        str(service_id_getter(record)): index
        for index, record in enumerate(materialized)
    }
    return tuple(
        sorted(
            materialized,
            key=lambda record: (
                priorities[_service_domain(service_id_getter(record), policy)],
                secondary_priority_getter(record),
                input_order[str(service_id_getter(record))],
            ),
        )
    )


def order_by_domain_reservations(
    records: Iterable[T],
    *,
    service_id_getter,
    secondary_priority_getter,
    max_jobs: int,
) -> tuple[T, ...]:
    """Place each domain's reserved work before overflow can consume the budget."""

    policy = load_domain_policy()
    ordered = _order_by_domain(
        records,
        service_id_getter=service_id_getter,
        secondary_priority_getter=secondary_priority_getter,
        policy=policy,
    )
    domains = tuple(
        sorted(
            policy["domains"],
            key=lambda domain: int(policy["domains"][domain].get("priority") or 0),
        )
    )
    required_reservations = sum(
        min(
            int(policy["domains"][domain].get("reserved_jobs_per_cycle") or 0),
            sum(
                _service_domain(str(service_id_getter(record)), policy) == domain
                for record in ordered
            ),
        )
        for domain in domains
    )
    if max_jobs < required_reservations:
        return ordered

    reserved: list[T] = []
    reserved_service_ids: set[str] = set()
    for domain in domains:
        domain_records = [
            record
            for record in ordered
            if _service_domain(str(service_id_getter(record)), policy) == domain
        ]
        count = int(policy["domains"][domain].get("reserved_jobs_per_cycle") or 0)
        for record in domain_records[:count]:
            reserved.append(record)
            reserved_service_ids.add(str(service_id_getter(record)))

    return tuple(
        reserved
        + [
            record
            for record in ordered
            if str(service_id_getter(record)) not in reserved_service_ids
        ]
    )


def max_jobs_per_cycle() -> int:
    """Return the reviewed global ceiling after domain reservations."""

    value = int(load_domain_policy().get("max_jobs_per_cycle") or 0)
    if value < 3:
        raise ValueError("scheduler_cycle_budget_below_domain_count")
    return value


__all__ = [
    "load_domain_policy",
    "max_jobs_per_cycle",
    "order_by_domain",
    "order_by_domain_reservations",
    "service_domain",
    "validate_domain_coverage",
]
