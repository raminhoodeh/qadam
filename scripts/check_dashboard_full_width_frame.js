#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "..");
const css = fs.readFileSync(path.join(repoRoot, "landing-page-repo/auth.css"), "utf8");
const renderer = fs.readFileSync(path.join(repoRoot, "landing-page-repo/dashboard.js"), "utf8");
const dashboardHtml = fs.readFileSync(path.join(repoRoot, "landing-page-repo/dashboard/index.html"), "utf8");

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

assert(dashboardHtml.includes("/auth.css?v=20260710-dashboard-coherence-v1"), "dashboard CSS cache key is stale");
assert(dashboardHtml.includes("/dashboard.js?v=20260710-dashboard-coherence-v1"), "dashboard JS cache key is stale");

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
assertDeclarations("body.qadam-dashboard-page .qsase-sidebar", [
    "border-right: 1px solid var(--qadam-color-rule);",
    "height: 100vh;",
    "position: sticky;",
    "top: 0;"
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
    "grid-template-columns: repeat(5, minmax(8rem, 1fr));"
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
assert(renderer.includes("<h2>Portfolio value over time</h2>"), "portfolio chart lacks a compact descriptive heading");
assert(renderer.includes("qsase-performance-summary"), "portfolio value summary is not compacted");
assert(!renderer.includes("<h2>${formatMoney(latestValue, currency)}</h2>"), "portfolio value is still duplicated as a giant heading");
assert(!renderer.includes("renderQsaseJourneyFooter"), "removed previous/next route footer is still rendered");
assert(renderer.includes("Paper trading only. No real money is connected."), "plain-language dashboard footer is missing");
assert(!renderer.includes("qsase-global-boundary"), "internal dashboard contract footer is still rendered");
assert(!renderer.includes("QSASE dashboard contract is public-safe"), "internal dashboard contract language leaked into the renderer");

const panelCount = (renderer.match(/renderQsaseModulePanel\("/g) || []).length;
assert(panelCount === 19, `expected all 19 dashboard route panels, found ${panelCount}`);
assert(css.includes("@media (max-width: 1100px)"), "responsive sidebar breakpoint is missing");
assert(css.includes("@media (max-width: 760px)"), "mobile layout breakpoint is missing");

console.log("dashboard_full_width_frame=ok routes=19");
