#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const {
    assert,
    html,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

const repoRoot = path.resolve(__dirname, "..");
const runtimeDir = process.env.QADAM_RUNTIME_DIR
    ? path.resolve(process.env.QADAM_RUNTIME_DIR)
    : path.join(repoRoot, "data", "runtime");
const renderer = fs.readFileSync(path.join(repoRoot, "landing-page-repo", "dashboard.js"), "utf8");
const css = fs.readFileSync(path.join(repoRoot, "landing-page-repo", "auth.css"), "utf8");
const operatorDashboard = JSON.parse(
    fs.readFileSync(path.join(runtimeDir, "qadam_operator_dashboard_view_model.json"), "utf8")
);

const expectedRoutes = [
    "system/team",
    "fund/portfolio",
    "fund/timeline",
    "observe/sources",
    "observe/universe",
    "patterns/findings",
    "patterns/nonlinear",
    "decide/strategies",
    "decide/decision",
    "trade/orders",
    "learn/outcomes",
    "learn/improvements",
    "system/overview"
];

async function main() {
    const rendered = await renderWithStatus(status);
    const dashboard = html(rendered, "[data-stage7-dashboard-visibility]");
    const renderedRoutes = [];
    const panelPattern = /data-qsase-module-panel="([^"]+)" data-qsase-view-panel="([^"]+)"/g;
    let match;
    while ((match = panelPattern.exec(dashboard)) !== null) {
        renderedRoutes.push(`${match[1]}/${match[2]}`);
    }

    assert(JSON.stringify(renderedRoutes) === JSON.stringify(expectedRoutes), "System Overview route matrix mismatch");
    assert(
        dashboard.indexOf('data-qsase-module-target="system" data-qsase-view-target="team"')
            < dashboard.indexOf('data-qsase-module-target="fund" data-qsase-view-target="portfolio"'),
        "Qadam Team is not pinned above Fund"
    );
    assert(!dashboard.includes('data-qsase-nav-group="system"'), "System returned as a nested sidebar group");
    assert(dashboard.includes("qsase-standalone-nav qsase-system-nav"), "standalone System link missing");
    assert(dashboard.includes("<strong>System</strong><small>Full operating picture</small>"), "standalone System label missing");
    assert(
        dashboard.indexOf("qsase-standalone-nav qsase-system-nav")
            > dashboard.indexOf('data-qsase-module-target="learn" data-qsase-view-target="improvements"'),
        "standalone System link is not below the operating journey"
    );

    [
        "System Overview",
        "Current state",
        "Lifecycle Health by Stage",
        "Running Now",
        "Health by Domain",
        "Needs Attention",
        "Recent Activity",
        "Technical Diagnostics",
        "Why Qadam is not trading now"
    ].forEach((needle) => assert(dashboard.includes(needle), `System Overview missing ${needle}`));

    [
        'data-qsase-view-panel="activity"',
        'data-qsase-view-panel="health"',
        "Qadam Pulse Terminal",
        "Public thought stream",
        "matrix-rain",
        "qsase-terminal-frame"
    ].forEach((needle) => assert(!dashboard.includes(needle), `legacy System surface returned: ${needle}`));

    [
        "candidate === \"system/activity\"",
        "candidate === \"system/health\"",
        "function renderQadamLifecycleTimeline",
        "function renderQadamLifecycleHealthMatrix",
        "data-qsase-nav-route",
        "window.history.replaceState",
        "function qsaseSystemOverviewModel",
        "function renderQsaseSystemOverview"
    ].forEach((needle) => assert(renderer.includes(needle), `System route behavior missing ${needle}`));

    [
        ".qsase-standalone-nav",
        ".qsase-system-nav",
        ".qsase-system-current",
        ".qadam-lifecycle-health-table",
        ".qsase-system-service",
        ".qsase-system-health-row",
        ".qsase-system-attention-list",
        ".qsase-system-activity-list",
        ".qsase-system-diagnostics"
    ].forEach((needle) => assert(css.includes(needle), `System Overview CSS missing ${needle}`));

    assert(!css.includes(".qsase-pulse-terminal"), "legacy pulse terminal CSS returned");
    assert(!css.includes(".matrix-rain"), "legacy matrix CSS returned");

    const contract = operatorDashboard.navigation_contract || {};
    const overview = operatorDashboard.views?.["system/overview"] || {};
    assert(JSON.stringify(contract.route_order) === JSON.stringify(expectedRoutes), "canonical route order mismatch");
    assert(contract.contract_version === "qadam_protected_decision_flow.v5", "navigation contract version mismatch");
    assert(contract.route_count === 13, "canonical route count should be 13");
    assert(contract.cross_cutting_routes_in_journey === false, "cross-cutting routes entered the journey");
    assert(contract.standalone_cross_cutting?.[0]?.view_id === "overview", "standalone System contract missing");
    assert(contract.legacy_route_aliases?.["system/activity"] === "system/overview", "activity alias missing");
    assert(contract.legacy_route_aliases?.["system/health"] === "system/overview", "health alias missing");
    assert(contract.legacy_route_aliases?.["learn/replay"] === "learn/improvements", "replay alias missing");
    assert(contract.legacy_route_aliases?.["learn/briefs"] === "learn/outcomes", "brief alias missing");
    assert(overview.artifact_type === "qadam_system_overview", "canonical System Overview projection missing");
    assert(operatorDashboard.end_to_end_lifecycle?.stage_count === 10, "canonical lifecycle should contain ten stages");
    assert(operatorDashboard.end_to_end_lifecycle?.single_global_current_stage === false, "System Overview must not claim one global stage");
    assert((overview.health_domains || []).length === 5, "health overview should contain five domains");
    assert(Array.isArray(overview.running_now?.services), "service inventory missing");
    assert(Array.isArray(overview.recent_activity), "real activity projection missing");

    console.log("dashboard_system_overview=ok");
    console.log(`dashboard_system_overview_route_count=${renderedRoutes.length}`);
    console.log(`dashboard_system_overview_service_count=${overview.running_now.services.length}`);
    console.log(`dashboard_system_overview_blocker_count=${(overview.needs_attention || []).length}`);
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
