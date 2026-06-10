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
        "data-overview-mission-brief",
        "data-overview-strategy-narrative",
        "data-overview-cockpit-grid",
        "data-overview-system-status",
        "data-overview-paper-capacity",
        "data-overview-system-summary",
        "data-overview-oversight",
        "data-overview-feed-strip",
        "data-overview-mini-map",
        "data-overview-boundary-rail",
        "data-overview-data-sources",
        "data-overview-trading-strategies",
        "data-overview-thought-feed",
        "data-overview-trade-considerations"
    ], "Overview first-screen HTML");

    includesAll(css, [
        ".overview-first-screen",
        ".overview-mission-brief",
        ".overview-strategy-narrative",
        ".overview-mission-question",
        ".overview-mission-question-grid",
        ".overview-mission-nav",
        ".overview-cockpit-grid",
        ".overview-system-status-panel",
        ".overview-paper-capacity-panel",
        ".overview-system-summary",
        ".overview-plain-grid",
        ".overview-plain-card-grid",
        ".overview-capacity-line",
        ".overview-mini-map",
        ".overview-boundary-rail",
        ".overview-expandable-ledger",
        "@media (max-width: 900px)"
    ], "Overview first-screen CSS");

    includesAll(renderer, [
        "function renderOverviewFirstScreen",
        "function renderContractTeamMap",
        "function renderContractStrategyNarrative",
        "function renderContractStrategyBlock",
        "function renderContractPortfolioBlock",
        "function renderContractTradeBoard",
        "function renderContractThinkingBlock",
        "founder_contract_model",
        "data-cc5-contract-source",
        "OVERVIEW_NODE_LABELS",
        "Fund Manager oversight",
        "overview-source-ledger",
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
    assert(overview.mini_map.source_model === "system_connectivity_model", "Overview mini-map must use shared connectivity model");
    assert(overview.system_status.length >= 6, "Overview must expose paper system status and runner cards");
    assert(overview.data_sources_connected.length >= 3, "Overview must expose source groups on the main page");
    assert(overview.trading_strategies.length >= 5, "Overview must expose the approved strategy families on the main page");
    assert(overview.thought_feed.length >= 4, "Overview must expose Qadam's thought feed on the main page");
    assert(overview.trade_considerations.length >= 2, "Overview must expose trade considerations on the main page");
    assert(overview.paper_capacity.total_gbp === 100000, "Overview must expose the GBP 100,000 paper capacity");
    assert(models.system_connectivity_model.overview_scope.placement === "overview-mini-map", "Mini-map placement mismatch");
    assert(models.system_connectivity_model.feed_clusters.length >= 3, "Overview should expose feed clusters");

    const rendered = await renderWithStatus(status);
    assertIncludes(rendered, "[data-dashboard-safety-strip]", "Paper-only readout · live capital off");
    assertIncludes(rendered, "[data-overview-mission-brief]", "Founder brief");
    assertIncludes(rendered, "[data-overview-mission-brief]", "Sanitized founder contract");
    assertIncludes(rendered, "[data-overview-mission-brief]", "Authority state");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Second-order AI infrastructure beneficiary lens");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Asymmetric Catalyst Proxy Trading");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Currently qualified");
    assertIncludes(rendered, "[data-overview-strategy-narrative]", "Waiting on gates");
    assertIncludes(rendered, "[data-overview-system-status]", "System status");
    assertIncludes(rendered, "[data-overview-system-status]", "Plain-language mission state");
    assertIncludes(rendered, "[data-overview-paper-capacity]", "Paper portfolio");
    assertIncludes(rendered, "[data-overview-paper-capacity]", "data-paper-capacity-line");
    assertIncludes(rendered, "[data-overview-oversight]", "Human oversight");
    assertIncludes(rendered, "[data-overview-oversight]", "Python COO");
    assertIncludes(rendered, "[data-overview-mini-map]", "Chief Operating Officer");
    assertIncludes(rendered, "[data-overview-mini-map]", "Local LLM");
    assertIncludes(rendered, "[data-overview-mini-map]", "Frontier LLM");
    assertIncludes(rendered, "[data-overview-mini-map]", "Head of Quant");
    assertIncludes(rendered, "[data-overview-boundary-rail]", "This is read-only mission control");
    assertIncludes(rendered, "[data-overview-boundary-rail]", "Trade ideas stay candidates until gated paper-order records exist");
    assertIncludes(rendered, "[data-overview-data-sources]", "Data sources connected");
    assertIncludes(rendered, "[data-overview-data-sources]", "mission_control");
    assertIncludes(rendered, "[data-overview-data-sources]", "ACLED API");
    assertIncludes(rendered, "[data-overview-trading-strategies]", "Trading strategy");
    assertIncludes(rendered, "[data-overview-trading-strategies]", "Open the full universe");
    assertIncludes(rendered, "[data-overview-trading-strategies]", "Asymmetric Catalyst Proxy Trading");
    assertIncludes(rendered, "[data-overview-trading-strategies]", "Semiconductor Policy Options Asymmetry");
    assertIncludes(rendered, "[data-overview-trading-strategies]", "Defence Repricing Geopolitical Watch");
    assertIncludes(rendered, "[data-overview-trading-strategies]", "Silver Macro Liquidity Stress");
    assertIncludes(rendered, "[data-overview-trading-strategies]", "Crude Oil Energy Security Disruption");
    assertIncludes(rendered, "[data-overview-trading-strategies]", "Prediction Market Geopolitical Dislocation");
    assertIncludes(rendered, "[data-overview-trading-strategies]", "Akber filter");
    assertIncludes(rendered, "[data-overview-thought-feed]", "Reasoning queue");
    assertIncludes(rendered, "[data-overview-thought-feed]", "Worldview prior");
    assertIncludes(rendered, "[data-overview-trade-considerations]", "Trades being considered");
    assertIncludes(rendered, "[data-overview-trade-considerations]", "USO options watch");

    const overviewText = [
        html(rendered, "[data-overview-mission-brief]"),
        html(rendered, "[data-overview-strategy-narrative]"),
        html(rendered, "[data-overview-system-status]"),
        html(rendered, "[data-overview-paper-capacity]"),
        html(rendered, "[data-overview-oversight]"),
        html(rendered, "[data-overview-mini-map]"),
        html(rendered, "[data-overview-boundary-rail]"),
        html(rendered, "[data-overview-data-sources]"),
        html(rendered, "[data-overview-trading-strategies]"),
        html(rendered, "[data-overview-thought-feed]"),
        html(rendered, "[data-overview-trade-considerations]")
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
