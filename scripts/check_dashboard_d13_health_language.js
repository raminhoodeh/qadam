#!/usr/bin/env node

const {
    assert,
    html,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

(async () => {
    const rendered = await renderWithStatus(status);
    const evidenceHtml = [
        html(rendered, "[data-sources-workspace-slot]"),
        html(rendered, "[data-source-summary]"),
        html(rendered, "[data-watching-list]")
    ].join("\n");
    const safetyStripHtml = html(rendered, "[data-dashboard-safety-strip]");

    const models = rendered.window.qadamDashboardViewModels || {};
    const sources = models.sources_model || {};
    const sourceCounts = sources.counts || {};
    const sourceReliability = Array.isArray(sources.reliability) ? sources.reliability : [];

    assert(sourceCounts.core > 0, "core source count missing");
    assert(sourceCounts.core_ok > 0, "core OK count missing");
    assert(sourceCounts.optional > 0, "optional source count missing");
    assert(sourceCounts.optional_credentials > 0, "optional credential count missing");
    assert(
        sourceCounts.missing_credentials === 0,
        "required source credentials should not be missing in the paper-trading core"
    );
    assert(
        sourceReliability.some((item) => item.label === "Core OK"),
        "Core OK source reliability card missing"
    );
    assert(
        sourceReliability.some((item) => item.label === "Optional not configured"),
        "optional-not-configured source reliability card missing"
    );

    [
        "Core OK",
        "Required not configured",
        "Optional",
        "Optional not configured",
        "Needs attention",
        "Adapter backlog"
    ].forEach((label) => {
        assert(evidenceHtml.includes(label), `health-language evidence label missing: ${label}`);
    });

    [
        "Safety locked: paper-only readout",
        "Paper-only readout · live capital off"
    ].forEach((label) => {
        assert(safetyStripHtml.includes(label), `safety strip OK label missing: ${label}`);
    });

    assert(
        !/Missing creds/.test(evidenceHtml),
        "old missing-creds shorthand leaked into evidence view"
    );
    assert(
        !/Online<\/span>/.test(evidenceHtml),
        "old generic Online metric leaked into evidence view"
    );

    console.log("dashboard_d13_health_language=ok");
    console.log(`dashboard_d13_core_ok=${sourceCounts.core_ok}/${sourceCounts.core}`);
    console.log(`dashboard_d13_optional_sources=${sourceCounts.optional}`);
    console.log(`dashboard_d13_optional_credentials=${sourceCounts.optional_credentials}`);
    console.log("dashboard_d13_required_credentials_missing=0");
})().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
