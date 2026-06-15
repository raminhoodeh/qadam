#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const {
    assert,
    assertIncludes,
    html,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

const repoRoot = path.resolve(__dirname, "..");
const htmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const cssPath = path.join(repoRoot, "landing-page-repo", "auth.css");
const rendererPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-master-implementation-plan.md");

const dashboardHtml = fs.readFileSync(htmlPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");
const renderer = fs.readFileSync(rendererPath, "utf8");
const plan = fs.readFileSync(planPath, "utf8");

function includesAll(text, needles, label) {
    needles.forEach((needle) => {
        assert(text.includes(needle), `${label} missing ${needle}`);
    });
}

function buildModels(snapshot = status) {
    const document = {
        documentElement: { dataset: {} },
        querySelector() {
            return null;
        },
        querySelectorAll() {
            return [];
        }
    };
    const window = { document };
    const context = {
        Array,
        Boolean,
        Date,
        Error,
        Intl,
        Map,
        Math,
        Number,
        Object,
        Promise,
        Set,
        String,
        console,
        document,
        fetch: async () => ({ ok: true, json: async () => snapshot }),
        localStorage: {
            getItem() {
                return null;
            },
            setItem() {}
        },
        sessionStorage: {
            getItem() {
                return null;
            },
            setItem() {}
        },
        window
    };
    window.window = window;
    vm.createContext(context);
    vm.runInContext(renderer, context, { filename: rendererPath });
    return window.buildQadamDashboardViewModels(snapshot, { key: "static_snapshot" });
}

async function main() {
    includesAll(dashboardHtml, [
        "data-overview-first-screen",
        "data-overview-portfolio-hero",
        "data-overview-mission-brief",
        "data-overview-strategy-narrative",
        "data-overview-strategy-universe",
        "data-overview-paper-trade-state",
        "data-overview-control-plane",
        "data-overview-source-summary",
        "data-overview-edge-tracker",
    ], "Overview first-screen HTML");

    includesAll(css, [
        ".overview-first-screen",
        ".overview-portfolio-hero",
        ".portfolio-trade-timeline",
        ".portfolio-trade-timeline-grid",
        ".overview-mission-brief",
        ".overview-mission-snapshot-grid",
        ".overview-strategy-narrative",
        ".overview-mission-question",
        ".overview-mission-question-grid",
        ".overview-mission-nav",
        ".overview-paper-trade-state-panel",
        ".paper-trade-state-grid",
        ".overview-control-plane",
        ".control-plane-grid",
        ".overview-source-summary-panel",
        ".source-universe-ledger",
        ".overview-edge-tracker",
        ".edge-sleeve-grid",
        ".overview-plain-grid",
        ".overview-plain-card-grid",
        ".overview-capacity-line",
        ".overview-boundary-rail",
        ".overview-expandable-ledger",
        "@media (max-width: 900px)"
    ], "Overview first-screen CSS");

    includesAll(renderer, [
        "function renderOverviewFirstScreen",
        "function renderContractTeamMap",
        "function renderContractControlPlane",
        "function renderContractStrategyUniverse",
        "function renderContractStrategyNarrative",
        "function renderContractStrategyBlock",
        "function renderContractPortfolioHero",
        "function renderPortfolioTradeTimeline",
        "function renderContractPortfolioBlock",
        "function renderContractTradeStateSummary",
        "function renderContractPaperTradeState",
        "function renderContractSourceSummary",
        "function buildEdgeTrackerModel",
        "function renderOverviewEdgeTracker",
        "founder_contract_model",
        "data-cc5-contract-source",
        "OVERVIEW_NODE_LABELS",
        "Human oversight",
        "Oversight route",
        "detail_ledger_placement",
        "mission_control"
    ], "Overview renderer");

    const models = buildModels();
    const overview = models.overview_model;
    const contract = models.founder_contract_model;
    assert(contract.source === "mission_control", "Overview should expose the founder contract model");
    assert(contract.team.length >= 6, "Founder contract should expose team health nodes");
    assert(contract.sources.ledger.length >= 20, "Founder contract should expose source ledger");
    assert(contract.strategy.active_lens.name, "Founder contract should expose active strategy lens");
    assert(contract.portfolio.equity_curve.length >= 1, "Founder contract should expose paper portfolio line");
    assert(contract.trades.board.length >= 1, "Founder contract should expose trade lifecycle board");
    assert(contract.thinking.research_goal_active_count >= 1, "Founder contract should expose research goals");
    assert(overview.id === "overview", "Overview model id mismatch");
    assert(overview.mission_brief.question_count === 7, "Overview must expose the seven-question Founder brief");
    assert(overview.mission_brief.questions.length === 7, "Overview Mission Brief must expose seven questions");
    assert(overview.mission_brief.questions.some((item) => item.question === "What is Qadam watching?"), "Overview Mission Brief missing watching question");
    assert(overview.mission_brief.questions.some((item) => item.question === "What is Qadam thinking about next?"), "Overview Mission Brief missing thinking question");
    assert(overview.mission_brief.questions.some((item) => item.question === "What is Qadam forbidden from doing?"), "Overview Mission Brief missing forbidden question");
    assert(overview.mission_brief.questions.some((item) => item.question === "Which trades are candidates or blocked?"), "Overview Mission Brief missing trade candidate question");
    assert(overview.mission_brief.questions.some((item) => item.question === "What is the portfolio worth?"), "Overview Mission Brief missing portfolio question");
    assert(overview.mission_brief.navigation.length >= 9, "Overview Mission Brief must expose navigation links");
    assert(overview.mission_brief.authority.live_capital_enabled === false, "Overview Mission Brief must keep live capital disabled");
    assert(overview.mission_brief.authority.dashboard_write_authority === false, "Overview Mission Brief must be read-only");
    assert(overview.trading_strategies.length >= 5, "Overview must expose the current strategy families");
    assert(overview.mini_map.source_model === "system_connectivity_model", "Control Plane must use shared connectivity model");
    assert(overview.system_status.length >= 6, "Overview must expose paper system status and runner cards");
    assert(overview.source_summary.detail_view === "evidence", "Overview must route source detail to Evidence");
    assert(overview.trading_strategies.length >= 5, "Overview must expose the approved strategy families on the main page");
    assert(overview.reasoning_summary.detail_view === "reasoning", "Overview must route reasoning detail to Reasoning");
    assert(overview.trade_state_summary.detail_view === "trades", "Overview must route trade detail to Trades");
    assert(overview.detail_ledger_placement.overview_scope === "summary_only", "Overview must be summary-only for detailed ledgers");
    assert(overview.paper_capacity.total_gbp === 100000, "Overview must expose the GBP 100,000 paper capacity");
    assert(overview.edge_tracker.sleeve_count === 5, "Overview must expose the five-sleeve edge tracker");
    assert(overview.edge_tracker.weekly_thesis.cadence === "weekly", "Overview edge tracker must expose weekly thesis cadence");
    assert(models.system_connectivity_model.overview_scope.placement === "control-plane", "Control Plane placement mismatch");
    assert(models.system_connectivity_model.feed_clusters.length >= 3, "Overview should expose feed clusters");

    const rendered = await renderWithStatus(status);
    assertIncludes(rendered, "[data-overview-portfolio-hero]", "Real portfolio timeline");
    assertIncludes(rendered, "[data-overview-portfolio-hero]", "Paper account portfolio value line");
    assertIncludes(rendered, "[data-overview-portfolio-hero]", "Trade timeline");
    assertIncludes(rendered, "[data-overview-portfolio-hero]", "Bought and held");
    assertIncludes(rendered, "[data-overview-portfolio-hero]", "Sold and closed");
    assertIncludes(rendered, "[data-overview-mission-brief]", "Mission Snapshot");
    assertIncludes(rendered, "[data-overview-mission-brief]", "Durable replay");
    assertIncludes(rendered, "[data-overview-mission-brief]", "Trade lifecycle");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Strategy Universe");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Second-order AI infrastructure beneficiary lens");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Asymmetric Catalyst Proxy Trading");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Qualified now");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Waiting");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Strategy family ledger");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Open the full universe");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Qadam-native edge");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Semiconductor Policy Options Asymmetry");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Defence Repricing Geopolitical Watch");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Silver Macro Liquidity Stress");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Crude Oil Energy Security Disruption");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Prediction Market Geopolitical Dislocation");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Akber filter");
    assertIncludes(rendered, "[data-overview-paper-trade-state]", "Paper Account &amp; Trade State");
    assertIncludes(rendered, "[data-overview-paper-trade-state]", "Balance");
    assertIncludes(rendered, "[data-overview-paper-trade-state]", "Current value");
    assertIncludes(rendered, "[data-overview-paper-trade-state]", "Realized");
    assertIncludes(rendered, "[data-overview-paper-trade-state]", "Unrealized");
    assertIncludes(rendered, "[data-overview-paper-trade-state]", "Total P&amp;L");
    assertIncludes(rendered, "[data-overview-paper-trade-state]", "Trade state");
    assertIncludes(rendered, "[data-overview-control-plane]", "Control Plane");
    assertIncludes(rendered, "[data-overview-control-plane]", "Human oversight");
    assertIncludes(rendered, "[data-overview-control-plane]", "Python COO");
    assertIncludes(rendered, "[data-overview-control-plane]", "Chief Operating Officer");
    assertIncludes(rendered, "[data-overview-control-plane]", "Local LLM");
    assertIncludes(rendered, "[data-overview-control-plane]", "Frontier LLM");
    assertIncludes(rendered, "[data-overview-control-plane]", "Head of Quant");
    assertIncludes(rendered, "[data-overview-source-summary]", "Data source tracker");
    assertIncludes(rendered, "[data-overview-source-summary]", "Source list");
    assertIncludes(rendered, "[data-overview-source-summary]", "signal-review eligible");
    assertIncludes(rendered, "[data-overview-source-summary]", "ACLED API");
    assertIncludes(rendered, "[data-overview-edge-tracker]", "Edge Tracker");
    assertIncludes(rendered, "[data-overview-edge-tracker]", "Current weekly thesis");
    assertIncludes(rendered, "[data-overview-edge-tracker]", "Oil");
    assertIncludes(rendered, "[data-overview-edge-tracker]", "Semiconductors");
    assertIncludes(rendered, "[data-overview-edge-tracker]", "Defence stocks");
    assert(!html(rendered, "[data-overview-paper-trade-state]").includes("USO options watch"), "Overview trade state must not show named trade rows");
    assert(!html(rendered, "[data-overview-source-summary]").includes("Worldview prior"), "Overview source summary must not show reasoning ledger rows");

    const overviewText = [
        html(rendered, "[data-overview-mission-brief]"),
        html(rendered, "[data-overview-strategy-narrative]"),
        html(rendered, "[data-overview-paper-trade-state]"),
        html(rendered, "[data-overview-control-plane]"),
        html(rendered, "[data-overview-source-summary]"),
        html(rendered, "[data-overview-edge-tracker]")
    ].join(" ");
    [
        "D0",
        "D1",
        "D5",
        "D7",
        "D9",
        "Q4",
        "Q5",
        "Q5E",
        "Q6",
        "Q7",
        "Phase 4",
        "Phase 5",
        "Phase 6",
        "Phase 7",
        "static snapshot",
        "secure bridge",
        "shadow toggles"
    ].forEach((term) => {
        assert(!overviewText.includes(term), `Overview first screen contains disallowed primary term: ${term}`);
    });

    [
        "Default to Mission Snapshot",
        "Read paper mirror and lifecycle counts",
        "Use Strategy Universe for strategy posture",
        "Show lifecycle counts only",
        "Show source posture only",
        "Control Plane owns operating flow"
    ].forEach((term) => {
        assert(!overviewText.includes(term), `Overview first screen contains obsolete explanatory text: ${term}`);
    });

    [
        "DX-5 - Overview First Screen",
        "Build the Overview from the `overview_model`",
        "Add a compact lifecycle strip",
        "Add the compact system mini-map"
    ].forEach((needle) => {
        assert(plan.includes(needle), `master plan missing DX-5 marker: ${needle}`);
    });

    console.log("dashboard_overhaul_overview=ok");
    console.log("dashboard_overview_first_screen_enabled=True");
    console.log("dashboard_overview_uses_view_model=True");
    console.log("dashboard_overview_cc2_consolidated=True");
    console.log("dashboard_overview_mini_map_shared_model=True");
    console.log("dashboard_authority_unchanged=True");
}

if (require.main === module) {
    main().catch((error) => {
        console.error(error.message);
        process.exitCode = 1;
    });
}
