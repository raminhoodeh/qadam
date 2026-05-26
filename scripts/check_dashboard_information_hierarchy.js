#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "..");
const htmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const cssPath = path.join(repoRoot, "landing-page-repo", "auth.css");
const rendererPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");

const html = fs.readFileSync(htmlPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");
const renderer = fs.readFileSync(rendererPath, "utf8");

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

function indexOf(needle, label = needle) {
    const index = html.indexOf(needle);
    assert(index >= 0, `dashboard HTML missing ${label}`);
    return index;
}

const hero = indexOf("dashboard-hero");
const safety = indexOf("dashboard-safety-strip");
const review = indexOf("operating-review-panel");
const map = indexOf("system-map-panel");
const detailIntro = indexOf("dashboard-section-intro");
const detailFlow = indexOf("dashboard-detail-flow");

assert(hero < review, "mission control must appear after the hero");
assert(hero < safety, "safety strip must appear after the hero");
assert(safety < review, "safety strip must appear before mission control");
assert(review < map, "mission control must appear before the system map");
assert(map < detailIntro, "section intro must appear after the system map");
assert(detailIntro < detailFlow, "detail panels must appear after the section intro");

[
    "data-overview-first-screen",
    "data-dashboard-safety-strip",
    "data-overview-status-rail",
    "data-overview-hero",
    "data-overview-lifecycle",
    "data-overview-mini-map",
    "data-overview-boundary-rail",
    "What is happening now?",
    "data-mission-primary",
    "paper/demo scope",
    "live-capital state",
    "Fund Manager oversight",
    "Use the view switcher when a first-screen item needs detail"
].forEach((needle) => assert(html.includes(needle), `dashboard hierarchy HTML missing ${needle}`));

[
    ".operating-review-panel",
    ".dashboard-safety-strip",
    ".overview-first-screen",
    ".overview-status-rail",
    ".overview-snapshot-grid",
    ".overview-lifecycle-strip",
    ".overview-mini-map",
    ".overview-boundary-rail",
    ".overview-next-links",
    ".dashboard-detail-flow",
    "grid-template-columns: repeat(12, minmax(0, 1fr))",
    "order: 9"
].forEach((needle) => assert(css.includes(needle), `dashboard hierarchy CSS missing ${needle}`));

const missionFunction = renderer.indexOf("function renderMissionControl");
const missionCall = renderer.lastIndexOf("renderMissionControl(status, source)");
const renderFunction = renderer.indexOf("function renderOperatingSummary");
const renderCall = renderer.lastIndexOf("renderOperatingSummary(status, source)");
const safetyFunction = renderer.indexOf("function renderDashboardSafetyStrip");
const safetyCall = renderer.lastIndexOf("renderDashboardSafetyStrip(status, viewModels)");
const overviewFunction = renderer.indexOf("function renderOverviewFirstScreen");
const overviewCall = renderer.lastIndexOf("renderOverviewFirstScreen(viewModels)");
const flowCall = Math.max(
    renderer.lastIndexOf("renderFlowMap(status, source, viewModels)"),
    renderer.lastIndexOf("renderFlowMap(status)")
);
assert(missionFunction >= 0, "renderer missing renderMissionControl");
assert(missionCall >= 0, "renderer does not call renderMissionControl");
assert(renderFunction >= 0, "renderer missing renderOperatingSummary");
assert(renderCall >= 0, "renderer does not call renderOperatingSummary");
assert(safetyFunction >= 0, "renderer missing renderDashboardSafetyStrip");
assert(safetyCall >= 0, "renderer does not call renderDashboardSafetyStrip");
assert(overviewFunction >= 0, "renderer missing renderOverviewFirstScreen");
assert(overviewCall >= 0, "renderer does not call renderOverviewFirstScreen");
assert(missionCall < renderCall, "mission control must render before operating summary cards");
assert(safetyCall < missionCall, "safety strip must render before mission control");
assert(renderCall < overviewCall, "operating summary compatibility render must run before the new Overview");
assert(overviewCall < flowCall, "Overview must render before the system map");

[
    "renderOverviewFirstScreen",
    "Fund Manager oversight",
    "Python script",
    "Local LLM",
    "Frontier LLM",
    "Quantum computer",
    "Use the single safety strip for authority state",
    "Candidate is not an order"
].forEach((needle) => assert(renderer.includes(needle), `Overview renderer missing ${needle}`));

console.log("dashboard_information_hierarchy=ok");
