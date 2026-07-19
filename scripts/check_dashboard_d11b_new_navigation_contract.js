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
const renderer = fs.readFileSync(path.join(repoRoot, "landing-page-repo", "dashboard.js"), "utf8");
const plan = fs.readFileSync(
    path.join(repoRoot, "docs", "qadam-dashboard-ten-stage-lifecycle-implementation-plan.md"),
    "utf8"
);

const expectedRoutes = [
    "system/team",
    "fund/portfolio", "fund/timeline",
    "observe/sources", "observe/universe",
    "patterns/findings", "patterns/nonlinear",
    "decide/strategies", "decide/decision",
    "trade/orders",
    "learn/outcomes", "learn/improvements",
    "system/overview"
];

async function main() {
    const rendered = await renderWithStatus(status);
    const dashboard = html(rendered, "[data-stage7-dashboard-visibility]");
    const renderedRoutes = [];
    const pattern = /data-qsase-module-panel="([^"]+)" data-qsase-view-panel="([^"]+)"/g;
    let match;
    while ((match = pattern.exec(dashboard)) !== null) {
        renderedRoutes.push(`${match[1]}/${match[2]}`);
    }

    assert(
        JSON.stringify(renderedRoutes) === JSON.stringify(expectedRoutes),
        "current decision-flow route order mismatch"
    );
    expectedRoutes.forEach((route) => {
        const [moduleId, viewId] = route.split("/");
        assert(
            dashboard.includes(
                `data-qsase-module-target="${moduleId}" data-qsase-view-target="${viewId}"`
            ),
            `sidebar route missing ${route}`
        );
    });

    [
        "DASHBOARD_LEGACY_HASH_TARGETS",
        "resolveQadamDashboardHash",
        "function qsaseDashboardRouteHref",
        "const QSASE_ROUTE_ORDER",
        "function renderQadamLifecycleTimeline",
        "candidate === \"fund/holdings\"",
        "candidate === \"decide/intents\"",
        "candidate === \"learn/replay\"",
        "candidate === \"learn/briefs\"",
        "candidate === \"system/activity\"",
        "candidate === \"system/health\""
    ].forEach((needle) => {
        assert(renderer.includes(needle), `legacy/deep-link compatibility missing ${needle}`);
    });

    [
        "Route-to-Stage Map",
        "Preserve all 13 current routes",
        "Shared Lifecycle Component",
        "The old global journey navigator is removed"
    ].forEach((needle) => {
        assert(plan.includes(needle), `current navigation plan missing ${needle}`);
    });

    [
        "data-dashboard-view-target=\"overview\"",
        "data-dashboard-view-target=\"trades\"",
        "data-dashboard-view-target=\"evidence\"",
        "data-dashboard-view-target=\"reasoning\"",
        "data-dashboard-view-target=\"operations\""
    ].forEach((needle) => {
        assert(!dashboard.includes(needle), `superseded five-view route returned: ${needle}`);
    });
    assert(!dashboard.includes('data-qsase-view-panel="intents"'), "trade intents still render as a separate page");
    assert(!dashboard.includes('data-qsase-view-panel="holdings"'), "holdings still render as a separate page");
    assert(!dashboard.includes('data-qsase-view-panel="activity"'), "Live Activity still renders as a separate page");
    assert(!dashboard.includes('data-qsase-view-panel="health"'), "System Health still renders as a separate page");
    assert(dashboard.includes("Decision Room"), "consolidated route is missing the Decision Room label");
    assert(!dashboard.includes("Decision Room introduction"), "duplicate Decision Room introduction returned");
    assert(dashboard.includes("INVESTMENT COMMITTEE GOVERNANCE"), "Decision Room is missing its governance header");
    assert(dashboard.includes("1. Research Pipelines Approaching Gate"), "Decision Room is missing its upstream research evidence");
    assert(dashboard.includes("2. Post-Filter Pipeline &amp; Current Candidates"), "Decision Room is missing its post-filter consequence");
    assert(dashboard.includes("3. Ultimate Committee Verdict"), "Decision Room is missing its final verdict");
    assert(dashboard.includes("What is Akber's 6-Stage Filter and how does it evaluate an edge?"), "Decision Room is missing its Akber explainer");
    assert(
        dashboard.indexOf('data-qsase-section="akber_explainer"') < dashboard.indexOf('data-qsase-section="decision_research_pipeline"')
            && dashboard.indexOf('data-qsase-section="decision_research_pipeline"') < dashboard.indexOf('data-qsase-section="trade_intents"')
            && dashboard.indexOf('data-qsase-section="trade_intents"') < dashboard.indexOf('data-qsase-section="router_paperops_gate"')
            && dashboard.indexOf('data-qsase-section="router_paperops_gate"') < dashboard.indexOf("data-qsase-previous-decision-reviews"),
        "Decision Room should retain its governance overview → evidence → consequence → decision order"
    );
    assert(dashboard.includes("System Overview"), "consolidated System route is missing");
    assert(
        dashboard.indexOf('data-qsase-module-target="system" data-qsase-view-target="team"')
            < dashboard.indexOf('data-qsase-module-target="fund" data-qsase-view-target="portfolio"'),
        "Qadam Team should be pinned above Fund"
    );

    console.log("dashboard_d11b_navigation_contract=ok");
    console.log("dashboard_d11b_contract_state=extended_by_ten_stage_lifecycle_v1");
    console.log(`dashboard_d11b_route_count=${renderedRoutes.length}`);
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
