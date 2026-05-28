#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const { assert } = require("./check_dashboard_renderer.js");

const repoRoot = path.resolve(__dirname, "..");
const htmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const cssPath = path.join(repoRoot, "landing-page-repo", "auth.css");
const rendererPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");
const dashboardPlanPath = path.join(repoRoot, "docs", "qadam-dashboard-implementation-plan.md");
const navPlanPath = path.join(repoRoot, "docs", "qadam-dashboard-navigation-ux-plan.md");

const html = fs.readFileSync(htmlPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");
const renderer = fs.readFileSync(rendererPath, "utf8");
const dashboardPlan = fs.readFileSync(dashboardPlanPath, "utf8");
const navPlan = fs.readFileSync(navPlanPath, "utf8");

function assertIncludes(text, needle, label) {
    assert(text.includes(needle), `${label} missing ${needle}`);
}

[
    "data-cockpit-nav",
    "data-cockpit-nav-current",
    "data-cockpit-nav-link",
    "data-dashboard-view-switcher",
    "data-dashboard-view-current",
    "data-dashboard-view-link",
    "data-dashboard-view-target=\"overview\"",
    "data-dashboard-view-target=\"trades\"",
    "data-dashboard-view-target=\"evidence\"",
    "data-dashboard-view-target=\"reasoning\"",
    "data-dashboard-view-target=\"operations\"",
    "data-dashboard-debug-toggle",
    "data-dashboard-advanced-links hidden",
    "/auth.css?v=20260528-telegram-intake",
    "/dashboard.js?v=20260528-telegram-intake"
].forEach((needle) => assertIncludes(html, needle, "dashboard HTML"));

[
    "mission-control",
    "system-map",
    "watching",
    "cognition",
    "trade-layer",
    "money",
    "forbidden",
    "process-console",
    "governance"
].forEach((id) => {
    assertIncludes(html, `id="${id}"`, "dashboard section anchor");
});

assertIncludes(html, "data-cockpit-section=", "dashboard cockpit sections");

[
    ".cockpit-nav",
    "position: sticky",
    ".cockpit-nav-head",
    ".cockpit-nav-links",
    ".dashboard-debug-toggle",
    ".dashboard-debug-links",
    ".cockpit-nav-links a",
    ".cockpit-nav-links a.active",
    ".cockpit-nav-links a[aria-current=\"page\"]",
    "[data-dashboard-view-section][hidden]",
    ".dashboard-view-switcher",
    "[data-cockpit-section]",
    "scroll-margin-top",
    "@media (max-width: 900px)",
    "@media (max-width: 560px)"
].forEach((needle) => assertIncludes(css, needle, "navigation CSS"));

[
    "function initCockpitNavigation",
    "data-dashboard-view-link",
    "data-cockpit-nav-current",
    "DASHBOARD_LEGACY_HASH_TARGETS",
    "resolveDashboardHash",
    "activateDashboardView",
    "classList.toggle(\"active\", active)",
    "window.addEventListener(\"hashchange\"",
    "initCockpitNavigation();"
].forEach((needle) => assertIncludes(renderer, needle, "navigation renderer"));

[
    "Phase D10J - Navigation UX",
    "sticky cockpit navigation",
    "Mission, Map, Sources, Cognition, Trades, Money, Safety, Runtime, Governance"
].forEach((needle) => assertIncludes(dashboardPlan, needle, "dashboard implementation plan"));

for (let index = 0; index <= 9; index += 1) {
    assertIncludes(navPlan, `Phase N${index}`, "navigation UX plan");
}

[
    "read-only",
    "Mission",
    "Map",
    "Sources",
    "Cognition",
    "Trades",
    "Money",
    "Safety",
    "Runtime",
    "Governance"
].forEach((needle) => assertIncludes(navPlan, needle, "navigation UX plan"));

console.log("dashboard_navigation_ux=ok");
