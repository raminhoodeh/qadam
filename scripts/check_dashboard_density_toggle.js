#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const {
    assert,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

const repoRoot = path.resolve(__dirname, "..");
const htmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const cssPath = path.join(repoRoot, "landing-page-repo", "auth.css");
const rendererPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-implementation-plan.md");

const html = fs.readFileSync(htmlPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");
const renderer = fs.readFileSync(rendererPath, "utf8");
const plan = fs.readFileSync(planPath, "utf8");

function assertIncludes(text, needle, label) {
    assert(text.includes(needle), `${label} missing ${needle}`);
}

[
    "data-density-toggle",
    "data-density-option=\"executive\"",
    "data-density-option=\"terminal\"",
    "aria-pressed=\"true\"",
    "aria-pressed=\"false\"",
    "Executive",
    "Terminal",
    "/auth.css?v=20260526-paper-equity-chart",
    "/dashboard.js?v=20260526-paper-equity-chart"
].forEach((needle) => assertIncludes(html, needle, "dashboard HTML"));

[
    "DASHBOARD_DENSITY_KEY",
    "qadam.dashboard.density",
    "function normalizeDashboardDensity",
    "function setDashboardDensity",
    "function initDashboardDensityToggle",
    "document.documentElement.dataset.dashboardDensity",
    "window.setDashboardDensity",
    "data-density-option"
].forEach((needle) => assertIncludes(renderer, needle, "dashboard renderer"));

[
    ".density-toggle",
    ".density-toggle button[aria-pressed=\"true\"]",
    "html[data-dashboard-density=\"terminal\"] .dashboard-shell",
    "html[data-dashboard-density=\"terminal\"] .priority-grid",
    "html[data-dashboard-density=\"terminal\"] .panel-brief",
    "html[data-dashboard-density=\"terminal\"] .metric",
    "html[data-dashboard-density=\"terminal\"] .trade-route span"
].forEach((needle) => assertIncludes(css, needle, "density CSS"));

assertIncludes(plan, "Phase D10G - Executive / Terminal Density Toggle", "implementation plan");

(async () => {
    const rendered = await renderWithStatus(status);
    assert(
        rendered.document.documentElement.dataset.dashboardDensity === "executive",
        "dashboard density should default to executive in renderer contract"
    );
    console.log("dashboard_density_toggle=ok");
})().catch((error) => {
    console.error(error);
    process.exit(1);
});
