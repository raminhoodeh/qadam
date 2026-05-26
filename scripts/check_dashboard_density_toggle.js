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
const auditPath = path.join(repoRoot, "docs", "qadam-dashboard-d11a-information-diet-audit-2026-05-26.md");

const html = fs.readFileSync(htmlPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");
const renderer = fs.readFileSync(rendererPath, "utf8");
const audit = fs.readFileSync(auditPath, "utf8");

function assertAbsent(text, needle, label) {
    assert(!text.includes(needle), `${label} still contains obsolete density artifact: ${needle}`);
}

[
    "data-density-toggle",
    "data-density-option",
    "Dashboard density",
    ">Executive<",
    ">Terminal<"
].forEach((needle) => assertAbsent(html, needle, "dashboard HTML"));

[
    "DASHBOARD_DENSITY_KEY",
    "qadam.dashboard.density",
    "function normalizeDashboardDensity",
    "function setDashboardDensity",
    "function initDashboardDensityToggle",
    "document.documentElement.dataset.dashboardDensity",
    "window.setDashboardDensity",
    "data-density-option"
].forEach((needle) => assertAbsent(renderer, needle, "dashboard renderer"));

[
    ".density-toggle",
    "data-dashboard-density",
    "dashboard-density"
].forEach((needle) => assertAbsent(css, needle, "dashboard CSS"));

assert(
    audit.includes("`Executive / Terminal` density toggle") && audit.includes("Delete from UI"),
    "D11A audit must authorize deleting the density toggle"
);

(async () => {
    const rendered = await renderWithStatus(status);
    assert(
        rendered.document.documentElement.dataset.dashboardDensity === undefined,
        "renderer should not set dashboard density after D11B"
    );
    console.log("dashboard_density_toggle_removed=ok");
    console.log("dashboard_density_toggle_present=False");
    console.log("dashboard_density_renderer_state_present=False");
})();
