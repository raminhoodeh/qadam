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
const guideDocPath = path.join(repoRoot, "docs", "qadam-user-guide.md");
const guideHtmlPath = path.join(repoRoot, "landing-page-repo", "guide", "index.html");

const dashboardHtml = fs.readFileSync(htmlPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");
const renderer = fs.readFileSync(rendererPath, "utf8");
const guideDoc = fs.readFileSync(guideDocPath, "utf8");
const guideHtml = fs.readFileSync(guideHtmlPath, "utf8");

const REQUIRED_SECTIONS = [
    "paper_fund_status",
    "source_intelligence_network",
    "watched_markets_universe",
    "strategy_playbook",
    "hedge_fund_investment_team",
    "hypotheses_pattern_recognition",
    "backtesting_learning_loop"
];

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
        "data-stage7-dashboard-visibility",
        "Mission Control walkthrough",
        "Mission Control walkthrough: paper fund status, source intelligence network, watched markets, strategy playbook, investment team, hypotheses, and learning loop.",
        "data-dashboard-debug-only hidden",
        "data-overview-portfolio-hero",
        "data-overview-mission-brief",
        "data-overview-control-plane",
        "data-overview-source-summary",
        "data-overview-edge-tracker"
    ], "Stage 7 dashboard HTML");

    includesAll(css, [
        ".stage7-dashboard-visibility",
        ".stage7-visibility-shell",
        ".mission-control-walkthrough",
        ".mission-paper-fund",
        ".mission-paper-metrics",
        ".mission-paper-exposure",
        ".mission-paper-columns",
        ".mission-paper-timeline",
        ".mission-paper-drawer",
        ".mission-source-network",
        ".mission-markets",
        ".mission-strategies",
        ".mission-team",
        ".mission-hypotheses",
        ".mission-learning",
        ".mission-flow-lifecycle",
        ".stage7-proof-drawer",
        ".mission-source-category-grid",
        ".mission-source-category",
        ".mission-source-drawer",
        ".mission-source-observation",
        ".mission-market-grid",
        ".mission-market-card-button",
        ".mission-market-drawer",
        ".mission-market-drawer-grid",
        ".mission-market-movement",
        ".mission-hypothesis-filter",
        ".mission-akber-pipeline",
        ".mission-strategy-card",
        ".mission-strategy-drawer",
        ".mission-strategy-gate-breakdown",
        ".mission-team-card",
        ".mission-team-drawer",
        ".mission-team-quant-badge",
        ".mission-team-cannot-list",
        "@media (max-width: 900px)"
    ], "Mission Control dashboard CSS");

    includesAll(renderer, [
        "const STAGE7_LEVEL1_SECTIONS",
        "function buildStage7VisibilityModel",
        "function renderStage7Visibility",
        "function renderMissionPaperFund",
        "function initMissionPaperFundDrawer",
        "function renderMissionPaperFundDrawer",
        "function renderMissionSourceNetwork",
        "function initMissionSourceNetworkDrawer",
        "function renderMissionSourceDrawer",
        "function renderMissionSourceDrawerBody",
        "function renderMissionMarkets",
        "function initMissionMarketDrawer",
        "function renderMissionMarketDrawer",
        "function renderMissionMarketDrawerBody",
        "function missionMarketPayload",
        "Full instrument list",
        "Data sources feeding this sleeve",
        "function renderMissionStrategies",
        "function stage7StrategyPlaybookFamilies",
        "function stage7StrategyLifecycle",
        "function initMissionStrategyDrawer",
        "function renderMissionStrategyDrawer",
        "function renderMissionStrategyDrawerBody",
        "function renderMissionStrategyPipeline",
        "function missionStrategyPayload",
        "Akber six-stage filter",
        "Full Akber gate breakdown",
        "function stage7InvestmentTeamRoles",
        "function missionTeamPayload",
        "function initMissionTeamDrawer",
        "function renderMissionTeamDrawer",
        "function renderMissionTeamDrawerBody",
        "Cannot do",
        "Recent run types",
        "Authority level",
        "function renderMissionTeam",
        "function renderMissionHypotheses",
        "function renderMissionLearning",
        "stage7_visibility_model",
        "Mission Control is read-only"
    ], "Mission Control dashboard renderer");

    [guideDoc, guideHtml].forEach((guideText, index) => {
        const label = index === 0 ? "Mission Control guide markdown" : "Mission Control guide HTML";
        includesAll(guideText, [
            "Seven Mission Control Sections",
            "Paper Fund Status",
            "Source Intelligence Network",
            "Watched Markets Universe",
            "Strategy Playbook",
            "Hedge Fund Investment Team",
            index === 0 ? "Hypotheses & Pattern Recognition" : "Hypotheses &amp; Pattern Recognition",
            index === 0 ? "Backtesting & Learning Loop" : "Backtesting &amp; Learning Loop",
            "Advanced / Debug Mode",
            "GBP 100,000",
            "GBP 200,000",
            "hidden chain-of-thought"
        ], label);
    });

    const models = buildModels();
    const stage7 = models.stage7_visibility_model;
    assert(stage7.schema_version === "mission_control_walkthrough.v1", "Mission Control schema mismatch");
    assert(stage7.legacy_schema_version === "stage7_dashboard_visibility.v1", "Mission Control compatibility schema missing");
    assert(stage7.status === "mission_control_walkthrough_ready", "Mission Control status mismatch");
    assert(stage7.level_1_section_count === 7, "Mission Control must expose seven default sections");
    assert(JSON.stringify(stage7.level_1_sections.map((section) => section.id)) === JSON.stringify(REQUIRED_SECTIONS), "Mission Control section order mismatch");
    assert(stage7.paper_fund_status.current_value_gbp > 0, "Mission Control paper fund value missing");
    assert(stage7.paper_fund_status.starting_balance_gbp === 100000, "Mission Control paper fund starting balance missing");
    assert(stage7.paper_fund_status.cash_available_gbp > 0, "Mission Control paper cash available missing");
    assert(stage7.paper_fund_status.capacity_used_label, "Mission Control paper capacity label missing");
    assert(stage7.paper_fund_status.exposure_by_sleeve.length >= 5, "Mission Control exposure by sleeve missing");
    assert(stage7.paper_fund_status.timeline_events.length > 0, "Mission Control paper timeline missing");
    assert(stage7.paper_fund_status.quantum_review_method, "Mission Control paper trade drawer quantum method missing");
    assert(stage7.paper_fund_status.quantum_review_method === "Classical Fallback (Deterministic)", "Mission Control must not label credential readiness as hardware quantum use");
    assert(stage7.source_intelligence_network.total >= 30, "Mission Control source count too low");
    assert(stage7.source_intelligence_network.required_blocker_count === 0, "Mission Control should not show required trade-blocking source gaps");
    assert(stage7.source_intelligence_network.groups.length === 5, "Mission Control must expose five source intelligence categories");
    assert(JSON.stringify(stage7.source_intelligence_network.groups.map((group) => group.label)) === JSON.stringify([
        "Conflict & Geopolitics",
        "Physical World Signals",
        "Macro & Trade Data",
        "Markets & Technical Analysis",
        "Social News & Filings"
    ]), "Mission Control source category labels mismatch");
    assert(stage7.source_intelligence_network.groups.every((group) => group.summary.includes("connected") && group.summary.includes("degraded")), "Mission Control source categories need plain connected/degraded counts");
    assert(stage7.source_intelligence_network.groups.some((group) => group.currently_influencing), "Mission Control source categories missing currently influencing tag");
    assert(stage7.source_intelligence_network.groups.flatMap((group) => group.sources).every((source) => ["Connected", "Degraded", "Optional Gap"].includes(source.status_label)), "Mission Control source rows must use simple source status labels");
    assert(stage7.source_intelligence_network.groups.flatMap((group) => group.sources).every((source) => source.last_update), "Mission Control source rows missing last update");
    assert(stage7.source_intelligence_network.groups.flatMap((group) => group.sources).every((source) => source.description), "Mission Control source rows missing plain-English contribution");
    assert(stage7.source_intelligence_network.groups.flatMap((group) => group.sources).some((source) => source.recent_observation), "Mission Control source rows missing observation text");
    assert(stage7.watched_markets_universe.sleeve_count === 5, "Mission Control watched-market sleeve count mismatch");
    assert(JSON.stringify(stage7.watched_markets_universe.sleeves.map((sleeve) => sleeve.label)) === JSON.stringify([
        "Crude Oil",
        "Silver",
        "Semiconductors",
        "Prediction Markets",
        "Defence"
    ]), "Mission Control watched-market sleeve labels/order mismatch");
    stage7.watched_markets_universe.sleeves.forEach((sleeve) => {
        assert(["Holding", "Watching", "Ignoring"].includes(sleeve.current_state), `Mission Control sleeve current state invalid: ${sleeve.label}`);
        assert(sleeve.instrument_summary, `Mission Control sleeve instrument summary missing: ${sleeve.label}`);
        assert(sleeve.why_this_market_matters, `Mission Control sleeve reason missing: ${sleeve.label}`);
        assert(sleeve.active_strategy, `Mission Control sleeve active strategy missing: ${sleeve.label}`);
        assert(sleeve.akber_gate, `Mission Control sleeve Akber gate missing: ${sleeve.label}`);
        assert(sleeve.recent_movement_direction, `Mission Control sleeve movement direction missing: ${sleeve.label}`);
        assert(sleeve.recent_movement_reason, `Mission Control sleeve movement reason missing: ${sleeve.label}`);
        assert(Number.isFinite(sleeve.active_hypothesis_count), `Mission Control sleeve hypothesis count missing: ${sleeve.label}`);
    });
    const sleevesByLabel = new Map(stage7.watched_markets_universe.sleeves.map((sleeve) => [sleeve.label, sleeve]));
    assert(sleevesByLabel.get("Semiconductors")?.current_state === "Holding", "Mission Control semiconductors sleeve should show holding state");
    assert(sleevesByLabel.get("Defence")?.current_state === "Holding", "Mission Control defence sleeve should show holding state");
    ["Crude Oil", "Silver", "Prediction Markets"].forEach((label) => {
        assert(sleevesByLabel.get(label)?.current_state === "Watching", `Mission Control ${label} sleeve should show watching state`);
    });
    assert(stage7.watched_markets_universe.sleeves.every((sleeve) => sleeve.active_hypothesis_count >= 1), "Mission Control every watched sleeve should expose active hypothesis count");
    assert(stage7.watched_markets_universe.sleeves.every((sleeve) => sleeve.watched_instruments.length >= 2), "Mission Control market drawers need full instrument lists");
    assert(stage7.strategy_playbook.mandate.includes("GBP 100,000"), "Mission Control mandate missing paper baseline");
    assert(stage7.strategy_playbook.mandate.includes("GBP 200,000"), "Mission Control mandate missing paper target");
    assert(JSON.stringify(stage7.strategy_playbook.akber_lens.stages) === JSON.stringify([
        "Context",
        "Catalyst",
        "Confirmation",
        "Risk",
        "Execution",
        "Postmortem Learning"
    ]), "Mission Control Akber stages mismatch");
    assert(stage7.strategy_playbook.families.length === 5, "Mission Control must expose five strategy cards");
    assert(JSON.stringify(stage7.strategy_playbook.families.map((family) => family.label)) === JSON.stringify([
        "Semiconductor Policy Options Asymmetry",
        "Defence Repricing Geopolitical Watch",
        "Silver Macro Liquidity Stress",
        "Crude Oil Energy Security Disruption",
        "Prediction Market Geopolitical Dislocation"
    ]), "Mission Control strategy card order mismatch");
    const allowedStrategyStates = [
        "Watching for context",
        "Catalyst detected",
        "Waiting for confirmation",
        "Under risk review",
        "Ready for paper review",
        "In paper position",
        "Learning from outcome"
    ];
    stage7.strategy_playbook.families.forEach((family) => {
        assert(allowedStrategyStates.includes(family.lifecycle_status), `Mission Control strategy uses invalid status vocabulary: ${family.label}`);
        assert(!/\b(waiting_on_required_gates|qualified_for_guarded_paper_review|qualified now|waiting)\b/i.test(family.lifecycle_status), `Mission Control strategy leaked raw status vocabulary: ${family.label}`);
        assert(family.display_rank, `Mission Control strategy rank missing: ${family.label}`);
        assert(family.display_fit_score, `Mission Control strategy fit score missing: ${family.label}`);
        assert(family.trend_direction, `Mission Control strategy trend missing: ${family.label}`);
        assert(family.current_akber_gate, `Mission Control strategy Akber gate missing: ${family.label}`);
        assert(family.last_gate_passed, `Mission Control strategy last gate missing: ${family.label}`);
        assert(family.next_gate_needed, `Mission Control strategy next gate missing: ${family.label}`);
        assert(family.gate_breakdown.length === 6, `Mission Control strategy drawer gate breakdown incomplete: ${family.label}`);
        assert(family.evidence_summary, `Mission Control strategy evidence summary missing: ${family.label}`);
        assert(family.linked_hypothesis, `Mission Control strategy linked hypothesis missing: ${family.label}`);
        if (family.lifecycle_status !== "In paper position") {
            assert(family.why_not_ready, `Mission Control strategy missing why-not-ready explanation: ${family.label}`);
        }
    });
    ["Prediction markets", "Crude oil", "Defence", "Silver", "Semiconductors"].forEach((domain) => {
        assert(stage7.strategy_playbook.universe.map((item) => item.toLowerCase()).includes(domain.toLowerCase()), `Mission Control strategy domain missing ${domain}`);
    });
    assert(stage7.hedge_fund_investment_team.role_count === 7, "Mission Control investment team must expose exactly seven readable roles");
    assert(JSON.stringify(stage7.hedge_fund_investment_team.roles.map((role) => role.label)) === JSON.stringify([
        "Chief Operating Officer (Python)",
        "Research Analyst (Local LLM)",
        "Strategy Lead (Frontier LLM)",
        "Head of Quant",
        "Risk Desk",
        "Paper Trading Desk",
        "Learning Review"
    ]), "Mission Control investment team role labels/order mismatch");
    const allowedRoleStatuses = ["Active", "Idle", "Monitoring"];
    const allowedAuthorityLevels = ["Read Only", "Propose Only", "Execute Paper Only", "Human Governed"];
    stage7.hedge_fund_investment_team.roles.forEach((role) => {
        assert(allowedRoleStatuses.includes(role.status_label), `Mission Control role status invalid: ${role.label}`);
        assert(allowedAuthorityLevels.includes(role.authority_level), `Mission Control role authority invalid: ${role.label}`);
        assert(role.job_description, `Mission Control role job description missing: ${role.label}`);
        assert(role.current_task, `Mission Control role current task missing: ${role.label}`);
        assert(Array.isArray(role.cannot_do) && role.cannot_do.length >= 4, `Mission Control role guardrail list too thin: ${role.label}`);
    });
    const headOfQuant = stage7.hedge_fund_investment_team.roles.find((role) => role.key === "head_of_quant");
    assert(headOfQuant, "Mission Control Head of Quant role missing");
    assert([
        "IBM / Q-CTRL Hardware",
        "Fire Opal Optimisation",
        "Classical Fallback (Deterministic)"
    ].includes(headOfQuant.quant_method_label), "Mission Control Head of Quant method label invalid");
    assert(headOfQuant.quant_method_label !== "Quantum", "Mission Control Head of Quant must not use generic Quantum label");
    assert(Array.isArray(headOfQuant.quant_run_log) && headOfQuant.quant_run_log.length >= 3, "Mission Control Head of Quant run log missing");
    assert(stage7.hypotheses_pattern_recognition.candidate_pattern_count >= 5, "Mission Control pattern section missing candidates");
    assert(stage7.backtesting_learning_loop.cards.length >= 6, "Mission Control learning loop is too thin");
    assert(stage7.paper_portfolio_capacity.baseline_gbp === 100000, "Stage 7 paper capacity baseline mismatch");
    assert(stage7.paper_portfolio_capacity.target_gbp === 200000, "Stage 7 paper capacity target mismatch");
    Object.entries(stage7.authority).forEach(([key, value]) => {
        assert(value === false, `Stage 7 authority flag must be false: ${key}`);
    });

    const rendered = await renderWithStatus(status);
    const stage7Html = html(rendered, "[data-stage7-dashboard-visibility]");
    REQUIRED_SECTIONS.forEach((sectionId) => {
        assert(stage7Html.includes(`data-stage7-section="${sectionId}"`), `Rendered Stage 7 missing section ${sectionId}`);
    });
    [
        "Paper Fund Status",
        "Source Intelligence Network",
        "Watched Markets Universe",
        "Strategy Playbook",
        "Hedge Fund Investment Team",
        "Hypotheses &amp; Pattern Recognition",
        "Backtesting &amp; Learning Loop",
        "Today&#39;s Fund Brief",
        "Qadam as a paper hedge fund",
        "Portfolio Value",
        "Starting Balance",
        "Paper Capacity Used",
        "Cash Available",
        "Exposure by Market Sleeve",
        "Open Positions",
        "Recent Buys &amp; Sells",
        "Closed Trades",
        "Chronological Trade Timeline",
        "Why This Trade?",
        "Conflict &amp; Geopolitics",
        "Physical World Signals",
        "Macro &amp; Trade Data",
        "Markets &amp; Technical Analysis",
        "Social News &amp; Filings",
        "These sources inform Qadam&#39;s hypotheses. None of them can place trades.",
        "Currently influencing:",
        "Paper route",
        "Research Analyst",
        "Chief Operating Officer (Python)",
        "Research Analyst (Local LLM)",
        "Current task",
        "Authority",
        "Strategy Lead",
        "Strategy Lead (Frontier LLM)",
        "Head of Quant",
        "Classical Fallback (Deterministic)",
        "Risk Desk",
        "Paper Trading Desk",
        "Learning Review",
        "data-team-role-detail=",
        "data-team-drawer",
        "Strategy feedback model",
        "Current State",
        "Holding",
        "Watching",
        "Active Hypotheses",
        "Strategy currently applied",
        "Recent Movement",
        "Current Akber gate",
        "data-market-sleeve-detail=",
        "data-market-drawer",
        "data-market-hypothesis-link=",
        "id=\"hypotheses_pattern_recognition\"",
        "Akber six-stage filter",
        "Context",
        "Catalyst",
        "Confirmation",
        "Risk",
        "Execution",
        "Postmortem Learning",
        "Semiconductor Policy Options Asymmetry",
        "Defence Repricing Geopolitical Watch",
        "Silver Macro Liquidity Stress",
        "Crude Oil Energy Security Disruption",
        "Prediction Market Geopolitical Dislocation",
        "Current Rank",
        "Fit Score",
        "Trend",
        "Why not ready?",
        "In paper position",
        "data-strategy-detail=",
        "data-strategy-drawer",
        "Prediction markets",
        "Crude Oil",
        "Defence",
        "Silver",
        "Semiconductors",
        "GBP 100,000",
        "GBP 200,000",
        "Mission Control is read-only"
    ].forEach((needle) => {
        assert(stage7Html.includes(needle), `Rendered Stage 7 missing visible copy: ${needle}`);
    });
    assert(stage7Html.includes("data-paper-fund-detail="), "Rendered Stage 7 missing paper-fund detail payload buttons");
    assert(stage7Html.includes("data-paper-fund-drawer"), "Rendered Stage 7 missing shared paper-fund drawer");
    assert(stage7Html.includes("data-source-category-detail="), "Rendered Stage 7 missing source category drawer payload buttons");
    assert(stage7Html.includes("data-source-network-drawer"), "Rendered Stage 7 missing shared source network drawer");
    assert(!stage7Html.includes("<details class=\"mission-source-group"), "Rendered Stage 7 must not use expandable source detail cards");
    assert(!stage7Html.includes("<details class=\"stage7-map-node mission-team-role"), "Rendered Stage 7 must not use expandable investment team detail cards");
    assertIncludes(rendered, "[data-stage7-dashboard-visibility]", "data-stage7-contract=\"mission_control_walkthrough_v1\"");
    assert(!stage7Html.includes("Phase 7"), "Mission Control default dashboard should not expose Phase 7 copy");
    assert(!stage7Html.includes("Stage 7"), "Mission Control default dashboard should not expose Stage 7 copy");
    assert(
        !/\b(can|may|allowed to|able to)\s+(submit paper orders?|place orders?|approve trades?|enable live capital)\b/i.test(stage7Html),
        "Mission Control rendered permissive unsafe action language"
    );

    console.log("Dashboard Mission Control walkthrough contract OK");
    console.log(`Mission Control sections: ${REQUIRED_SECTIONS.join(", ")}`);
}

if (require.main === module) {
    main().catch((error) => {
        console.error(error.message);
        process.exitCode = 1;
    });
}
