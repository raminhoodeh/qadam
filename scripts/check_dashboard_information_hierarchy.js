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
const safetyStrip = indexOf("data-dashboard-safety-strip");
const missionControl = indexOf("data-overview-first-screen");
const stage7Cockpit = indexOf("data-stage7-dashboard-visibility");
const portfolioHero = indexOf("data-overview-portfolio-hero");
const mission = indexOf("data-overview-mission-brief");
const paperAccount = indexOf("data-overview-paper-trade-state");
const strategy = indexOf("data-overview-strategy-narrative");
const controlPlane = indexOf("data-overview-control-plane");
const sourceTracker = indexOf("data-overview-source-summary");
const detailFlow = indexOf("dashboard-detail-flow");

assert(hero < safetyStrip, "Safety Status must appear after the hero");
assert(safetyStrip < missionControl, "Mission Control walkthrough must appear after Safety Status");
assert(missionControl < stage7Cockpit, "Mission Control walkthrough must be first inside Overview");
assert(stage7Cockpit < portfolioHero, "advanced portfolio timeline must appear after the Mission Control walkthrough");
assert(portfolioHero < mission, "Mission Snapshot must appear after the Mission Control compatibility shell");
assert(mission < paperAccount, "Paper Account & Trade State must appear after Mission Snapshot");
assert(paperAccount < strategy, "Strategy Universe must appear after Paper Account & Trade State");
assert(strategy < controlPlane, "Control Plane must appear after Strategy Universe");
assert(controlPlane < sourceTracker, "Data source tracker must appear after Control Plane");
assert(sourceTracker < detailFlow, "hidden detail panels must appear after the first-screen mission control");

[
    "data-overview-first-screen",
    "data-dashboard-safety-strip",
    "data-stage7-dashboard-visibility",
    "data-overview-portfolio-hero",
    "data-overview-mission-brief",
    "data-overview-strategy-narrative",
    "data-overview-strategy-universe",
    "data-overview-control-plane",
    "data-overview-paper-trade-state",
    "data-overview-source-summary",
    "Mission Control",
    "Mission Control walkthrough",
    "Real portfolio timeline",
    "Mission Snapshot",
    "Strategy Universe",
    "Paper Account &amp; Trade State",
    "Control Plane",
    "Data source tracker",
    "Loading paper fund status, source network, markets, strategies, investment team, hypotheses, and learning loop.",
    "Mission Control walkthrough: paper fund status, source intelligence network, watched markets, strategy playbook, investment team, hypotheses, and learning loop."
].forEach((needle) => assert(html.includes(needle), `dashboard hierarchy HTML missing ${needle}`));

[
    ".operating-review-panel",
    ".overview-first-screen",
    ".dashboard-safety-strip",
    ".stage7-dashboard-visibility",
    ".mission-paper-fund",
    ".mission-source-network",
    ".mission-markets",
    ".mission-team",
    ".mission-hypotheses",
    ".mission-learning",
    ".overview-portfolio-hero",
    ".portfolio-trade-timeline",
    ".overview-mission-brief",
    ".overview-strategy-narrative",
    ".overview-control-plane",
    ".control-plane-grid",
    ".overview-boundary-rail",
    ".overview-plain-grid",
    ".overview-source-summary-panel",
    ".overview-ledger-routing",
    ".overview-expandable-ledger",
    ".overview-mini-node",
    ".dashboard-detail-flow"
].forEach((needle) => assert(css.includes(needle), `dashboard hierarchy CSS missing ${needle}`));

const missionFunction = renderer.indexOf("function renderMissionControl");
const missionCall = renderer.lastIndexOf("renderMissionControl(status, source)");
const renderFunction = renderer.indexOf("function renderOperatingSummary");
const renderCall = renderer.lastIndexOf("renderOperatingSummary(status, source)");
const overviewFunction = renderer.indexOf("function renderOverviewFirstScreen");
const overviewCall = renderer.lastIndexOf("renderOverviewFirstScreen(viewModels)");
const stage7Function = renderer.indexOf("function renderStage7Visibility");
const stage7Call = renderer.lastIndexOf("renderStage7Visibility(viewModels)");
const portfolioFunction = renderer.indexOf("function renderContractPortfolioHero");
const flowCall = Math.max(
    renderer.lastIndexOf("renderFlowMap(status, source, viewModels)"),
    renderer.lastIndexOf("renderFlowMap(status)")
);
assert(missionFunction >= 0, "renderer missing renderMissionControl");
assert(missionCall >= 0, "renderer does not call renderMissionControl");
assert(renderFunction >= 0, "renderer missing renderOperatingSummary");
assert(renderCall >= 0, "renderer does not call renderOperatingSummary");
assert(overviewFunction >= 0, "renderer missing renderOverviewFirstScreen");
assert(overviewCall >= 0, "renderer does not call renderOverviewFirstScreen");
assert(stage7Function >= 0, "renderer missing renderStage7Visibility");
assert(stage7Call >= 0, "renderer does not call renderStage7Visibility");
assert(portfolioFunction >= 0, "renderer missing renderContractPortfolioHero");
assert(missionCall < renderCall, "mission control must render before operating summary cards");
assert(renderCall < stage7Call, "operating summary compatibility render must run before Mission Control walkthrough");
assert(stage7Call < overviewCall, "Mission Control walkthrough must render before advanced Overview compatibility cards");
assert(overviewCall < flowCall, "Overview must render before the system map");

[
    "renderOverviewFirstScreen",
    "buildStage7VisibilityModel",
    "renderStage7Visibility",
    "Paper Fund Status",
    "Source Intelligence Network",
    "Watched Markets Universe",
    "Strategy Playbook",
    "Hedge Fund Investment Team",
    "Hypotheses & Pattern Recognition",
    "Backtesting & Learning Loop",
    "renderMissionPaperFund",
    "renderMissionSourceNetwork",
    "renderMissionMarkets",
    "renderMissionStrategies",
    "renderMissionTeam",
    "renderMissionHypotheses",
    "renderMissionLearning",
    "renderContractTeamMap",
    "renderContractControlPlane",
    "renderContractStrategyUniverse",
    "renderContractStrategyNarrative",
    "renderContractStrategyBlock",
    "renderContractPortfolioHero",
    "renderContractPortfolioBlock",
    "renderContractTradeStateSummary",
    "renderContractPaperTradeState",
    "renderContractSourceSummary",
    "founder_contract_model",
    "Human oversight",
    "Oversight route",
    "Chief Operating Officer",
    "Local LLM",
    "Frontier LLM",
    "Head of Quant",
    "detail_ledger_placement",
    "data-cc5-contract-source",
    "Real portfolio timeline",
    "Source list",
    "Strategy family ledger"
].forEach((needle) => assert(renderer.includes(needle), `Overview renderer missing ${needle}`));

console.log("dashboard_information_hierarchy=ok");
