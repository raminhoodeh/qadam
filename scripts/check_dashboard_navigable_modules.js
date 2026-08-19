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
const dashboardSiteRoot = path.resolve(
    process.env.QADAM_DASHBOARD_SITE_ROOT || path.join(repoRoot, "landing-page-repo")
);
const renderer = fs.readFileSync(path.join(dashboardSiteRoot, "dashboard.js"), "utf8");
const css = fs.readFileSync(path.join(dashboardSiteRoot, "auth.css"), "utf8");

function count(text, needle) {
    return text.split(needle).length - 1;
}

async function main() {
    const rendered = await renderWithStatus(status);
    const dashboard = html(rendered, "[data-stage7-dashboard-visibility]");

    const groups = [
        "Fund",
        "Observe",
        "Find Patterns",
        "Test &amp; Decide",
        "Trade",
        "Learn &amp; Improve",
        "System"
    ];
    const groupPositions = groups.map((label) => dashboard.indexOf(label));
    assert(groupPositions.every((position) => position >= 0), "navigable dashboard is missing a sidebar group");
    assert(groupPositions.every((position, index) => index === 0 || position > groupPositions[index - 1]), "sidebar groups do not follow the Qadam operating flow");

    const compatibilityStatus = JSON.parse(JSON.stringify(status));
    if (compatibilityStatus.qsase_dashboard?.sections) {
        delete compatibilityStatus.qsase_dashboard.sections.operator_dashboard;
    }
    const compatibilityRendered = await renderWithStatus(compatibilityStatus);
    const compatibilityDashboard = html(
        compatibilityRendered,
        "[data-stage7-dashboard-visibility]"
    );
    assert(
        compatibilityRendered.errors.length === 0,
        `legacy learning projection crashed the dashboard: ${compatibilityRendered.errors.join(", ")}`
    );
    assert(
        groups.every((label) => compatibilityDashboard.includes(label)),
        "legacy learning projection removed dashboard navigation"
    );

    const routes = [
        "system/team",
        "fund/portfolio", "fund/timeline",
        "observe/sources", "observe/universe",
        "patterns/findings", "patterns/nonlinear",
        "decide/strategies", "decide/decision",
        "trade/orders",
        "learn/outcomes", "learn/improvements",
        "system/overview"
    ];
    routes.forEach((route) => {
        const [moduleId, viewId] = route.split("/");
        assert(dashboard.includes(`data-qsase-module-panel="${moduleId}" data-qsase-view-panel="${viewId}"`), `missing module panel ${route}`);
        assert(dashboard.includes(`data-qsase-module-target="${moduleId}" data-qsase-view-target="${viewId}"`), `missing sidebar route ${route}`);
    });
    assert(count(dashboard, "data-qsase-module-panel=") === routes.length, "dashboard should render exactly one panel per declared route");

    [
        "Portfolio",
        "Performance",
        "Portfolio Composition",
        "Gross exposure",
        "Net exposure",
        "Positions",
        "Trading History",
        "Qadam Team Overview",
        "Data Sources",
        "Trading Universe",
        "Pattern Discovery",
        "Quantum Edge",
        "Trading Strategies",
        "Decision Room",
        "Results &amp; Lessons",
        "Tests &amp; Improvements",
        "10-Stage Lifecycle",
        "Primary stages 6 and 7; supports stage 8",
        "INVESTMENT COMMITTEE GOVERNANCE",
        "1. Research Pipelines Approaching Gate",
        "2. Post-Filter Pipeline &amp; Current Candidates",
        "3. Ultimate Committee Verdict",
        "What is Akber's 6-Stage Filter and how does it evaluate an edge?",
        "System Overview",
        "Lifecycle Health by Stage",
        "Running Now",
        "Health by Domain",
        "Needs Attention",
        "Recent Activity",
        "Technical Diagnostics"
    ].forEach((copy) => assert(dashboard.includes(copy), `protected curated copy missing: ${copy}`));
    assert(
        renderer.includes("Why Qadam is holding cash"),
        "empty-portfolio Decision Room handoff copy is missing"
    );

    assert(!dashboard.includes('data-qsase-view-panel="intents"'), "trade intents should not render as a separate page");
    assert(!dashboard.includes('data-qsase-view-panel="holdings"'), "holdings should not render as a separate page");
    assert(renderer.includes('candidate === "fund/holdings"'), "legacy holdings route should resolve to Portfolio");
    assert(renderer.includes('candidate === "decide/intents"'), "legacy trade-intents route should resolve to the Decision Room");
    assert(renderer.includes('candidate === "learn/replay"'), "legacy replay route should resolve to Tests & Improvements");
    assert(renderer.includes('candidate === "learn/briefs"'), "legacy brief route should resolve to Results & Lessons");
    assert(renderer.includes('candidate === "system/activity"'), "legacy activity route should resolve to System Overview");
    assert(renderer.includes('candidate === "system/health"'), "legacy health route should resolve to System Overview");
    assert(
        dashboard.indexOf('data-qsase-module-target="system" data-qsase-view-target="team"')
            < dashboard.indexOf('data-qsase-module-target="fund" data-qsase-view-target="portfolio"'),
        "Qadam Team should be pinned above Fund"
    );
    assert(
        dashboard.indexOf('data-qsase-section="akber_explainer"') < dashboard.indexOf('data-qsase-section="decision_research_pipeline"')
            && dashboard.indexOf('data-qsase-section="decision_research_pipeline"') < dashboard.indexOf('data-qsase-section="trade_intents"')
            && dashboard.indexOf('data-qsase-section="trade_intents"') < dashboard.indexOf('data-qsase-section="router_paperops_gate"')
            && dashboard.indexOf('data-qsase-section="router_paperops_gate"') < dashboard.indexOf("data-qsase-previous-decision-reviews"),
        "Decision Room should retain its governance overview → evidence → consequence → decision order"
    );

    [
        "function resolveQsaseDashboardRoute",
        "function syncQsaseModuleNavigation",
        "window.history.pushState",
        "window.addEventListener(\"popstate\"",
        "captureQsaseOpenDetails",
        "restoreQsaseOpenDetails",
        "captureQsaseNavigationState",
        "restoreQsaseNavigationState",
        "captureQsaseViewportState",
        "restoreQsaseViewportState",
        "options.closeSidebar !== false",
        "{ scroll: false, closeSidebar: false }"
    ].forEach((contract) => assert(renderer.includes(contract), `navigation behavior missing ${contract}`));

    [
        ".qsase-navigation-layout",
        ".qsase-sidebar",
        ".qsase-mobile-navigation",
        ".qsase-module-panel[hidden]",
        ".qsase-navigable-dashboard.is-sidebar-open",
        "@media (max-width: 1100px)",
        "@media (max-width: 620px)"
    ].forEach((contract) => assert(css.includes(contract), `responsive navigation style missing ${contract}`));

    [
        "Paper trading mode",
        "Paper-only monitoring",
        "Overview",
        "Advanced"
    ].forEach((copy) => assert(!dashboard.includes(`>${copy}<`), `obsolete navigation label returned: ${copy}`));

    console.log("dashboard_navigable_modules=ok");
    console.log(`dashboard_navigable_routes=${routes.length}`);
    console.log("dashboard_protected_copy_present=True");
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
