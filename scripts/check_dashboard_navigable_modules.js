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
const css = fs.readFileSync(path.join(repoRoot, "landing-page-repo", "auth.css"), "utf8");

function count(text, needle) {
    return text.split(needle).length - 1;
}

async function main() {
    const rendered = await renderWithStatus(status);
    const dashboard = html(rendered, "[data-stage7-dashboard-visibility]");

    const groups = [
        "Fund Overview",
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

    const routes = [
        "fund/portfolio", "fund/holdings", "fund/timeline",
        "observe/sources", "observe/universe",
        "patterns/findings", "patterns/nonlinear",
        "decide/strategies", "decide/intents", "decide/decision",
        "trade/orders", "trade/lifecycle",
        "learn/outcomes", "learn/improvements", "learn/replay", "learn/briefs",
        "system/team", "system/activity", "system/health"
    ];
    routes.forEach((route) => {
        const [moduleId, viewId] = route.split("/");
        assert(dashboard.includes(`data-qsase-module-panel="${moduleId}" data-qsase-view-panel="${viewId}"`), `missing module panel ${route}`);
        assert(dashboard.includes(`data-qsase-module-target="${moduleId}" data-qsase-view-target="${viewId}"`), `missing sidebar route ${route}`);
    });
    assert(count(dashboard, "data-qsase-module-panel=") === routes.length, "dashboard should render exactly one panel per declared route");

    [
        "Qadam Paper Fund",
        "Portfolio Overview",
        "Current Portfolio",
        "Trading History",
        "Qadam Team Overview",
        "Data Sources",
        "Trading Universe",
        "Pattern Recognition Findings",
        "Core Trading Strategies"
    ].forEach((copy) => assert(dashboard.includes(copy), `protected curated copy missing: ${copy}`));

    [
        "function resolveQsaseDashboardRoute",
        "function syncQsaseModuleNavigation",
        "window.history.pushState",
        "window.addEventListener(\"popstate\"",
        "captureQsaseOpenDetails",
        "restoreQsaseOpenDetails",
        "captureQsaseNavigationState",
        "restoreQsaseNavigationState",
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
