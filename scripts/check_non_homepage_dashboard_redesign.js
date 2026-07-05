#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "..");

function read(relativePath) {
    return fs.readFileSync(path.join(repoRoot, relativePath), "utf8");
}

function assert(condition, message) {
    if (!condition) {
        throw new Error(message);
    }
}

function includesAll(text, needles, label) {
    needles.forEach((needle) => {
        assert(text.includes(needle), `${label} missing ${needle}`);
    });
}

const html = read("landing-page-repo/dashboard/index.html");
const css = read("landing-page-repo/auth.css");
const homeHtml = read("landing-page-repo/index.html");
const homeCss = read("landing-page-repo/style.css");

includesAll(html, [
    '<body class="qadam-dashboard-page">',
    "dashboard-shell qadam-dashboard-shell qadam-layout-shell is-wide",
    "topbar qadam-dashboard-header qadam-layout-header is-institutional",
    "dashboard-workspace qadam-dashboard-workspace hidden",
    "data-stage7-dashboard-visibility",
    "data-dashboard",
    "data-qadam-nav-context=\"public-dashboard\"",
    "/dashboard.js?v=20260705-position-orders-v1",
    "/auth.js?v=20260517-d9-release"
], "dashboard html");

assert(!html.includes("data-signout"), "public dashboard must not expose sign-out control");
[
    "cockpit-nav dashboard-view-switcher qadam-dashboard-nav",
    "data-dashboard-view-current",
    "data-dashboard-view-link",
    "data-dashboard-debug-toggle",
    "data-dashboard-advanced-links",
    "data-dashboard-safety-strip",
    "Qadam Mission Control",
    "Paper trading mode",
    "Paper-only monitoring"
].forEach((needle) => {
    assert(!html.includes(needle), `dashboard html should not include removed UX chrome ${needle}`);
});

includesAll(css, [
    "Stage 6: institutional dashboard redesign",
    "body.qadam-dashboard-page",
    "--bg: var(--qadam-color-page)",
    "--panel: var(--qadam-color-canvas)",
    "--text: var(--qadam-color-ink)",
    "--surface-page: var(--qadam-color-page)",
    ".qadam-dashboard-shell",
    ".qadam-dashboard-header",
    ".qadam-dashboard-workspace",
    ".qsase-status-card",
    ".qsase-kpi-row",
    ".qsase-trading-timeline",
    ".qsase-source-category-row",
    ".qsase-market-pill-row",
    ".stage7-hero",
    ".stage7-section",
    ".mission-flow-lifecycle",
    ".mission-source-category",
    ".mission-market-card",
    ".mission-strategy-card",
    ".mission-team-card",
    ".mission-hypothesis-card",
    ".mission-learning-item",
    ".mission-paper-drawer-panel",
    ".mission-source-drawer-panel",
    ".mission-market-drawer-panel",
    ".mission-strategy-drawer-panel",
    ".mission-team-drawer-panel",
    ".mission-hypothesis-drawer-panel",
    ".mission-learning-drawer-panel",
    "var(--qadam-color-brand)",
    "var(--qadam-color-section-band)",
    "var(--qadam-font-display)",
    "@media (max-width: 1020px)",
    "@media (max-width: 760px)"
], "dashboard css");

[
    ".qsase-jump-row"
].forEach((needle) => {
    assert(!css.includes(needle), `dashboard css should not include removed QSASE jump chrome ${needle}`);
});

assert(
    css.indexOf("body.qadam-dashboard-page") > css.indexOf("/* Dashboard polish: reduce first-viewport density without changing IA. */"),
    "dashboard institutional layer must come after earlier dashboard polish overrides"
);

const stage6Css = css.slice(css.indexOf("/* Stage 6: institutional dashboard redesign"));
assert(
    !stage6Css.includes("position: sticky"),
    "dashboard institutional layer must not add sticky dashboard layers"
);

assert(
    !homeHtml.includes("qadam-dashboard-page") &&
    !homeHtml.includes("qadam-dashboard-nav") &&
    !homeCss.includes("qadam-dashboard-page"),
    "homepage must remain outside the dashboard redesign scope"
);

console.log("non_homepage_dashboard_redesign=ok");
