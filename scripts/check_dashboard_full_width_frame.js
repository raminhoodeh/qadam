#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "..");
const dashboardSiteRoot = path.resolve(
    process.env.QADAM_DASHBOARD_SITE_ROOT || path.join(repoRoot, "landing-page-repo")
);
const css = fs.readFileSync(path.join(dashboardSiteRoot, "auth.css"), "utf8");
const renderer = fs.readFileSync(path.join(dashboardSiteRoot, "dashboard.js"), "utf8");
const dashboardHtml = fs.readFileSync(path.join(dashboardSiteRoot, "dashboard/index.html"), "utf8");
const releaseManifest = JSON.parse(fs.readFileSync(path.join(dashboardSiteRoot, "status/dashboard-release.json"), "utf8"));

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

function ruleBodies(selector) {
    const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const matches = Array.from(css.matchAll(new RegExp(`${escaped}\\s*\\{([^}]+)\\}`, "g")));
    assert(matches.length, `missing CSS rule ${selector}`);
    return matches.map((match) => match[1]);
}

function assertDeclarations(selector, declarations) {
    const bodies = ruleBodies(selector);
    declarations.forEach((declaration) => {
        assert(bodies.some((body) => body.includes(declaration)), `${selector} is missing ${declaration}`);
    });
}

assert(dashboardHtml.includes(releaseManifest.css_asset), "dashboard CSS release asset is stale");
assert(dashboardHtml.includes(releaseManifest.javascript_asset), "dashboard JS release asset is stale");
assert(dashboardHtml.includes(releaseManifest.auth_asset), "dashboard auth release asset is stale");

assertDeclarations("body.qadam-dashboard-page .qadam-dashboard-shell", [
    "margin: 0;",
    "max-width: none;",
    "padding: 0;",
    "width: 100%;"
]);
assertDeclarations("body.qadam-dashboard-page .qadam-dashboard-workspace", [
    "gap: 0;",
    "padding: 0;"
]);
assertDeclarations("body.qadam-dashboard-page .qsase-navigation-layout", [
    "gap: 0;",
    "grid-template-columns: 15rem minmax(0, 1fr);"
]);
assertDeclarations("body.qadam-dashboard-page #qsase-dashboard-sidebar", [
    "align-self: start;",
    "border-right: 1px solid var(--qadam-color-rule);",
    "height: 100dvh;",
    "min-height: 100dvh;",
    "position: sticky;",
    "top: 0;"
]);
assertDeclarations("body.qadam-dashboard-page .qsase-sidebar", [
    "height: 100%;",
    "max-height: 100%;",
    "position: static;"
]);
assertDeclarations("body.qadam-dashboard-page .qsase-sidebar > nav", [
    "display: flex;",
    "flex-direction: column;",
    "min-height: 100%;"
]);
assertDeclarations("body.qadam-dashboard-page .qsase-system-nav", [
    "margin-top: auto;"
]);
assertDeclarations("body.qadam-dashboard-page .qsase-module-workspace", [
    "padding: clamp(1.25rem, 2vw, 2rem);"
]);
assertDeclarations("body.qadam-dashboard-page .qsase-dashboard-hero h2", [
    "font-size: clamp(2rem, 3vw, 3.25rem);",
    "letter-spacing: 0;"
]);
assertDeclarations("body.qadam-dashboard-page .qsase-section-head strong", [
    "font-size: clamp(1.35rem, 2vw, 1.9rem);"
]);
assertDeclarations("body.qadam-dashboard-page .qsase-kpi-row.stage7-kpi-strip.compact", [
    "grid-template-columns: repeat(4, minmax(8rem, 1fr));"
]);
assertDeclarations("body.qadam-dashboard-page .qsase-kpi-row .qsase-final-gate-summary", [
    "grid-column: 1 / -1;"
]);
assertDeclarations("body.qadam-dashboard-page .qsase-dashboard-footer", [
    "border-top: 1px solid var(--qadam-color-rule);",
    "justify-content: space-between;"
]);

assert(!css.includes("width: min(100%, 1400px);"), "dashboard shell still has the old centred width cap");
assert(!css.includes(".qsase-journey-footer"), "removed previous/next route footer is still styled");
assert(renderer.includes("<h2>Performance</h2>"), "portfolio chart lacks the performance heading");
assert(!renderer.includes("qsase-performance-period"), "portfolio chart still renders a competing period-start date");
assert(renderer.includes("qsase-performance-outcome"), "portfolio performance outcome is not compacted");
assert(!renderer.includes("<h2>${formatMoney(latestValue, currency)}</h2>"), "portfolio value is still duplicated as a giant heading");
assert(!renderer.includes("<strong>${formatMoney(latestValue, currency)} current value</strong>"), "portfolio chart still repeats the current account value");
assert(!renderer.includes("The paper portfolio is currently ${value}"), "portfolio explanation still repeats the current account value");
assert(renderer.includes("renderQsasePortfolioPage(qsase)"), "consolidated Portfolio page is missing");
assert(renderer.includes("renderQsasePortfolioAnalytics(qsase, model)"), "portfolio composition analytics are missing");
assert(renderer.includes("Gross exposure") && renderer.includes("Net exposure"), "portfolio risk strip lacks unique exposure metrics");
assert(renderer.includes("qsase-cash-allocation"), "empty portfolio lacks the compact cash allocation visual");
assert(renderer.includes("Why Qadam is holding cash"), "empty portfolio lacks its Decision Room handoff");
assert(!renderer.includes("qsase-journey-edge"), "journey navigation still renders inactive edge placeholders");
assert(!renderer.includes("Start of dashboard") && !renderer.includes("End of dashboard"), "journey navigation still contains inactive endpoint copy");
assert(!renderer.includes("renderMetric(\"Available cash\", fundSummary.cash_available)"), "portfolio still repeats the persistent header cash value");
assert(renderer.includes("maxAxisLabel === minAxisLabel"), "flat portfolio charts still repeat identical value-axis labels");
assert(!renderer.includes("renderMetric(\"Patterns\", (qsase.linear_pattern_count"), "fund summary still mixes pattern counts into account metrics");
assert(renderer.includes("class=\"qsase-nav-group-icon\""), "sidebar module icons are missing");
assert(!renderer.includes("${qsaseHtmlText(module.stage)}</span>"), "sidebar still renders stage numbers instead of icons");
assert(!renderer.includes("renderQsaseJourneyFooter"), "removed previous/next route footer is still rendered");
assert(renderer.includes("Paper trading only. No real money is connected."), "plain-language dashboard footer is missing");
assert(!renderer.includes("qsase-global-boundary"), "internal dashboard contract footer is still rendered");
assert(!renderer.includes("QSASE dashboard contract is public-safe"), "internal dashboard contract language leaked into the renderer");

const panelCount = (renderer.match(/renderQsaseModulePanel\("/g) || []).length;
assert(panelCount === 13, `expected all 13 dashboard route panels, found ${panelCount}`);
assert(css.includes("@media (max-width: 1100px)"), "responsive sidebar breakpoint is missing");
assert(css.includes("@media (max-width: 760px)"), "mobile layout breakpoint is missing");
assert(/@media \(max-width: 760px\)[\s\S]*?\.trade-toast-rail\s*\{\s*display: none;/m.test(css), "mobile dashboard header still renders the activity ticker");

console.log("dashboard_full_width_frame=ok routes=13");
