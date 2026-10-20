"""Bound public history windows while preserving totals and canonical records."""

from copy import deepcopy

HISTORY_FIELDS = frozenset({
    "events", "learning_events", "reference_records", "learnable_outcomes",
    "proposals", "active_candidates", "rejected_or_held",
})


def bounded_operator_dashboard(document, *, limit=50):
    if limit < 1:
        raise ValueError("public_history_limit_must_be_positive")
    result = dict(document)
    views = dict(result.get("views") or {})
    result["views"] = views
    for route in ("learn/outcomes", "learn/improvements"):
        if not isinstance(views.get(route), dict):
            continue
        view = dict(views[route])
        totals = {}
        for field in HISTORY_FIELDS:
            rows = view.get(field)
            if isinstance(rows, list):
                totals[field] = len(rows)
                view[field] = deepcopy(rows[:limit])
        repositories = {}
        for name, original in (view.get("repositories") or {}).items():
            repository = dict(original)
            rows = repository.get("records")
            if isinstance(rows, list):
                repository.update(records=deepcopy(rows[:limit]), visible_count=min(limit, len(rows)),
                                  total_record_count=len(rows))
            repositories[name] = repository
        view["repositories"] = repositories
        view["display_window"] = {
            "limit": limit, "total_records_by_field": totals,
            "truncated": any(total > limit for total in totals.values()),
            "note": "Latest records shown; summary counts include the full history.",
            "canonical_history_retained": True,
        }
        views[route] = view
    return result
