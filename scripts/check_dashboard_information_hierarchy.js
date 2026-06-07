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
const detailFlow = indexOf("dashboard-detail-flow");

assert(hero < review, "mission control must appear after the hero");
assert(hero < safety, "safety strip must appear after the hero");
assert(safety < review, "safety strip must appear before mission control");
assert(review < map, "mission control must appear before the system map");
assert(map < detailFlow, "detail panels must appear after the system map");

[
    "data-overview-first-screen",
    "data-dashboard-safety-strip",
    "data-overview-mission-brief",
    "data-overview-strategy-narrative",
    "data-overview-system-summary",
    "data-overview-mini-map",
    "data-overview-boundary-rail",
    "data-overview-cockpit-grid",
    "data-overview-data-sources",
    "data-overview-trading-strategies",
    "data-overview-thought-feed",
    "data-overview-trade-considerations",
    "Mission Control",
    "Founder brief",
    "Strategy posture",
    "Data sources connected",
    "Trading strategies",
    "Trades being considered",
    "Human oversight",
    "How Qadam turns data into controlled paper trades"
].forEach((needle) => assert(html.includes(needle), `dashboard hierarchy HTML missing ${needle}`));

[
    ".operating-review-panel",
    ".dashboard-safety-strip",
    ".overview-first-screen",
    ".overview-mission-brief",
    ".overview-strategy-narrative",
    ".overview-system-summary",
    ".overview-mini-map",
    ".overview-boundary-rail",
    ".overview-cockpit-grid",
    ".overview-plain-grid",
    ".overview-expandable-ledger",
    ".overview-mini-node",
    ".dashboard-detail-flow"
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
    "renderContractTeamMap",
    "renderContractStrategyNarrative",
    "renderContractStrategyBlock",
    "renderContractPortfolioBlock",
    "renderContractTradeBoard",
    "renderContractThinkingBlock",
    "founder_contract_model",
    "Fund Manager oversight",
    "Chief Operating Officer",
    "Local LLM",
    "Frontier LLM",
    "Head of Quant",
    "overview-source-ledger",
    "data-cc5-contract-source",
    "Trade ideas stay candidates until gated paper-order records exist"
].forEach((needle) => assert(renderer.includes(needle), `Overview renderer missing ${needle}`));

console.log("dashboard_information_hierarchy=ok");
