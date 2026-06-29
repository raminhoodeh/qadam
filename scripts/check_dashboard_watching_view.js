#!/usr/bin/env node

const {
    assert,
    assertIncludes,
    html,
    renderWithStatus,
    status,
    statusPath
} = require("./check_dashboard_renderer.js");

const EXPECTED_REGISTRY_SOURCE_COUNT = 35;
const EXPECTED_RENDERED_SOURCE_COUNT = EXPECTED_REGISTRY_SOURCE_COUNT + 1;
const EXPECTED_PIPELINE_COUNT = 5;

const REQUIRED_SOURCE_FIELDS = [
    "auth_class",
    "cadence",
    "can_authorize_orders",
    "can_influence_signals",
    "credential_status",
    "degraded_reason",
    "endpoint_count",
    "eligible_for_signal_review",
    "influence_boundary",
    "last_heartbeat",
    "last_payload_time",
    "latency_ms",
    "order_authority_boundary",
    "pipeline",
    "promoted_adapter",
    "raw_status",
    "readiness",
    "registry_status",
    "source_key",
    "source_name",
    "status",
    "tier",
    "trust_score",
    "usable_for_research_context"
];

const ALLOWED_RENDERED_STATUSES = new Set([
    "degraded",
    "local_only",
    "online",
    "pending"
]);

function hasOwn(value, key) {
    return Object.prototype.hasOwnProperty.call(value, key);
}

async function main() {
    const watching = Array.isArray(status.watching) ? status.watching : [];
    const pipelineSummary = Array.isArray(status.source_pipeline_summary) ? status.source_pipeline_summary : [];

    assert(
        watching.length >= EXPECTED_RENDERED_SOURCE_COUNT,
        `expected at least ${EXPECTED_RENDERED_SOURCE_COUNT} watched sources, got ${watching.length}`
    );
    assert(
        pipelineSummary.length === EXPECTED_PIPELINE_COUNT,
        `expected ${EXPECTED_PIPELINE_COUNT} source pipeline groups, got ${pipelineSummary.length}`
    );

    const sourceKeys = new Set();
    const pipelineNames = new Set(watching.map((source) => source.pipeline));
    const summarySourceTotal = pipelineSummary.reduce((total, pipeline) => total + Number(pipeline.source_count || 0), 0);

    assert(summarySourceTotal === watching.length, "source pipeline summary does not equal watched source count");
    assert(
        pipelineSummary.every((pipeline) => pipelineNames.has(pipeline.pipeline)),
        "source pipeline summary includes a pipeline absent from watching"
    );

    for (const source of watching) {
        assert(source.source_key, "watched source is missing source_key");
        assert(!sourceKeys.has(source.source_key), `duplicate watched source key: ${source.source_key}`);
        sourceKeys.add(source.source_key);

        const missing = REQUIRED_SOURCE_FIELDS.filter((field) => !hasOwn(source, field));
        assert(!missing.length, `${source.source_key} missing D3 fields: ${missing.join(", ")}`);
        assert(
            ALLOWED_RENDERED_STATUSES.has(source.status),
            `${source.source_key} has unsupported rendered status: ${source.status}`
        );
        assert(source.can_authorize_orders === false, `${source.source_key} can authorize orders`);
        assert(
            source.can_influence_signals === source.eligible_for_signal_review,
            `${source.source_key} signal-review alias mismatch`
        );
        assert(
            typeof source.influence_boundary === "string" && source.influence_boundary.length > 0,
            `${source.source_key} missing influence boundary`
        );
        assert(
            typeof source.order_authority_boundary === "string" && source.order_authority_boundary.includes("no_source_can_authorize_orders"),
            `${source.source_key} missing order-authority boundary`
        );
    }

    assert(sourceKeys.has("tradingview_paid_alerts"), "TradingView paid alerts source row is missing");
    const coveredProxySourceCount = Number(status.mission_control?.data_sources?.covered_proxy_source_count || 0);
    const allOptionalSourcesConfigured = status.paperops_source_gap_visibility?.status === "all_optional_sources_configured";
    assert(
        watching.some((source) => source.credential_status === "missing") || (allOptionalSourcesConfigured && coveredProxySourceCount > 0),
        "missing-credential or covered-proxy state is not represented"
    );
    assert(watching.some((source) => source.promoted_adapter), "promoted-adapter state is not represented");
    assert(watching.some((source) => source.auth_class === "credential_required"), "credential-required auth state is not represented");
    assert(watching.some((source) => source.usable_for_research_context), "research-usable source state is not represented");
    assert(watching.some((source) => source.eligible_for_signal_review), "signal-review eligible source state is not represented");
    assert(watching.every((source) => source.can_authorize_orders === false), "source order authority must remain blocked");

    const rendered = await renderWithStatus(status);
    assertIncludes(rendered, "[data-source-summary]", "Required not configured");
    assertIncludes(rendered, "[data-source-summary]", "Research usable");
    assertIncludes(rendered, "[data-source-summary]", "Signal review eligible");
    assertIncludes(rendered, "[data-source-summary]", "Order authority");
    assertIncludes(rendered, "[data-source-summary]", "Yahoo Finance");
    assertIncludes(rendered, "[data-source-summary]", "Preference MCP");
    assertIncludes(rendered, "[data-watching-list]", "ACLED API");
    assertIncludes(rendered, "[data-watching-list]", "credential required");
    assertIncludes(rendered, "[data-watching-list]", "ready to port");
    assertIncludes(rendered, "[data-watching-list]", "1 endpoints");
    assertIncludes(rendered, "[data-watching-list]", "evidence only");
    assertIncludes(rendered, "[data-watching-list]", "research usable");
    assertIncludes(rendered, "[data-watching-list]", "signal review eligible");
    assertIncludes(rendered, "[data-watching-list]", "no order authority");
    assertIncludes(rendered, "[data-watching-list]", "payload Not connected");
    assertIncludes(rendered, "[data-watching-list]", "TradingView Paid Alerts");
    assertIncludes(rendered, "[data-watching-list]", "Supplemental market confirmation");
    assertIncludes(rendered, "[data-watching-list]", "Yahoo Finance");
    assertIncludes(rendered, "[data-watching-list]", "Yahoo Finance deferred");
    assertIncludes(rendered, "[data-watching-list]", "no reconciliation truth");
    assertIncludes(rendered, "[data-watching-list]", "Preference MCP data plane");
    assertIncludes(rendered, "[data-watching-list]", "Domain-pack coverage");
    assertIncludes(rendered, "[data-watching-list]", "Blocked paid tools");
    assertIncludes(rendered, "[data-watching-list]", "no trade authority");
    assertIncludes(rendered, "[data-watching-list]", "d7 local contract");
    assertIncludes(rendered, "[data-watching-list]", "observed signal only no execution path");

    const emptyStatus = {
        ...status,
        watching: [],
        source_pipeline_summary: []
    };
    const emptyRendered = await renderWithStatus(emptyStatus);
    assertIncludes(emptyRendered, "[data-watching-list]", "No watched-source records have been exported");

    console.log("Dashboard watching view contract OK");
    console.log(`Rendered snapshot: ${statusPath}`);
    console.log(`Watched sources: ${watching.length}`);
    console.log(`Pipeline groups: ${pipelineSummary.length}`);
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
