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
const siteRoot = path.resolve(
    process.env.QADAM_DASHBOARD_SITE_ROOT || path.join(repoRoot, "landing-page-repo")
);
const css = fs.readFileSync(path.join(siteRoot, "auth.css"), "utf8");
const renderer = fs.readFileSync(path.join(siteRoot, "dashboard.js"), "utf8");
const lifecyclePlan = fs.readFileSync(
    path.join(repoRoot, "docs", "qadam-dashboard-ten-stage-lifecycle-implementation-plan.md"),
    "utf8"
);

function includesAll(text, needles, label) {
    const missing = needles.filter((needle) => !text.includes(needle));
    assert(missing.length === 0, `${label} missing ${missing.join(", ")}`);
}

async function main() {
    const rendered = await renderWithStatus(status);
    const dashboard = html(rendered, "[data-stage7-dashboard-visibility]");

    includesAll(dashboard, [
        "data-qsase-navigation-shell",
        "data-qsase-sidebar",
        "data-qsase-sidebar-toggle",
        "data-qsase-current-view",
        "data-qsase-route",
        "data-qadam-lifecycle",
        "data-qadam-lifecycle-trigger",
        "qsase-team-nav",
        "data-qsase-module-target=\"system\" data-qsase-view-target=\"team\"",
        "data-qsase-module-target=\"fund\" data-qsase-view-target=\"portfolio\"",
        "data-qsase-module-target=\"system\" data-qsase-view-target=\"overview\"",
        "Fund",
        "Observe",
        "Find Patterns",
        "Test &amp; Decide",
        "Trade",
        "Learn &amp; Improve",
        "System"
    ], "routed dashboard shell");

    includesAll(css, [
        ".qsase-navigation-layout",
        ".qsase-sidebar",
        ".qsase-mobile-navigation",
        ".qadam-lifecycle",
        ".qadam-lifecycle-track",
        ".qsase-module-panel[hidden]",
        ".qsase-navigable-dashboard.is-sidebar-open",
        "@media (max-width: 1100px)",
        "@media (max-width: 620px)"
    ], "responsive navigation CSS");

    includesAll(renderer, [
        "const QSASE_DEFAULT_ROUTE = { moduleId: \"fund\", viewId: \"portfolio\" }",
        "const QSASE_DASHBOARD_NAVIGATION",
        "function resolveQsaseDashboardRoute",
        "function syncQsaseModuleNavigation",
        "function renderQadamLifecycleTimeline",
        "function initQsaseLifecycleDisclosures",
        "captureQsaseNavigationState",
        "restoreQsaseNavigationState",
        "captureQsaseViewportState",
        "restoreQsaseViewportState",
        "preserveViewport",
        "window.history.pushState",
        "window.addEventListener(\"popstate\"",
        "{ scroll: false, closeSidebar: false }"
    ], "navigation renderer");

    includesAll(lifecyclePlan, [
        "Canonical 10-Stage Lifecycle",
        "Route-to-Stage Map",
        "Tooltip And Disclosure Specification",
        "Per-Module Consolidation Plan",
        "`fund/portfolio`",
        "`system/team`",
        "`system/overview`",
        "read-only",
        "command-disabled"
    ], "ten-stage lifecycle plan");

    const routeCount = (dashboard.match(/data-qsase-module-panel=/g) || []).length;
    assert(routeCount === 13, `dashboard route count should be 13, received ${routeCount}`);

    console.log("dashboard_navigation_ux=ok");
    console.log(`dashboard_navigation_route_count=${routeCount}`);
    console.log("dashboard_navigation_contract=ten_stage_lifecycle_v1");
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
