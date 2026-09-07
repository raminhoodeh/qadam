"""Explicit producer routing for the operator's monitored derived artifacts."""

ARTIFACT_REFRESH_SERVICES = {
    "qsase_dashboard_status.json": ("dashboard_refresh",),
    "qsase_dashboard_portfolio_value_series.json": ("dashboard_refresh",),
    "qsase_dashboard_current_portfolio.json": ("dashboard_refresh",),
    "qadam_source_operational_state.jsonl": ("source_ingestion",),
    "qadam_pattern_score_v3_records.jsonl": ("pattern_scoring",),
    "qadam_edge_registry_summary.json": ("research_evidence_validation",),
    "qadam_akber_filter_v3_dashboard_summary.json": ("akber_review",),
    "qadam_forward_shadow_state.json": ("forward_shadow",),
    "qadam_router_v3_scoreboard.json": ("portfolio_router_review",),
    "qadam_paper_lifecycle_v3.json": ("paper_lifecycle_poll",),
    "qadam_operator_service_status.json": ("dashboard_refresh",),
    "qadam_ef11_dashboard_summary.json": ("market_price_refresh", "open_market_conversion"),
    "qadam_ef11_open_market_conversion_certification.json": (
        "market_price_refresh", "open_market_conversion",
    ),
}


def artifact_refresh_services(artifacts: list) -> set[str] | None:
    services: set[str] = set()
    if not artifacts:
        return None
    for artifact in artifacts:
        filename = str(artifact).removeprefix("data/runtime/")
        owners = ARTIFACT_REFRESH_SERVICES.get(filename)
        if owners is None:
            return None
        services.update(owners)
    return services | {"dashboard_refresh", "public_status_publication"}
