#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const {
    assert,
    assertIncludes,
    html,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

const repoRoot = path.resolve(__dirname, "..");
const rendererPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");
const cssPath = path.join(repoRoot, "landing-page-repo", "auth.css");
const dashboardHtmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const releaseManifestPath = path.join(repoRoot, "landing-page-repo", "status", "dashboard-release.json");
const cockpitPath = path.join(repoRoot, "orchestrator", "cockpit_status.py");
const runtimeDir = process.env.QADAM_RUNTIME_DIR
    ? path.resolve(process.env.QADAM_RUNTIME_DIR)
    : path.join(repoRoot, "data", "runtime");

const renderer = fs.readFileSync(rendererPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");
const dashboardHtml = fs.readFileSync(dashboardHtmlPath, "utf8");
const releaseManifest = JSON.parse(fs.readFileSync(releaseManifestPath, "utf8"));
const cockpitStatus = fs.readFileSync(cockpitPath, "utf8");

const artifactMap = {
    status: "qsase_dashboard_status.json",
    portfolio_value: "qsase_dashboard_portfolio_value_series.json",
    current_portfolio: "qsase_dashboard_current_portfolio.json",
    trading_history: "qsase_dashboard_trading_history.json",
    source_network: "qsase_dashboard_source_network.json",
    strategy_universe: "qsase_dashboard_strategy_universe.json",
    pattern_lab: "qsase_dashboard_pattern_lab.json",
    trade_intents: "qsase_dashboard_trade_intents.json",
    pattern_to_paper_workflow: "qsase_pattern_to_paper_workflow.json",
    pattern_intelligence: "qsase_pattern_intelligence.json",
    learning_ledger: "qsase_dashboard_learning_ledger.json",
    repair_queue: "qsase_dashboard_repair_queue.json",
    router: "qsase_strategy_router_decisions.json",
    paperops_gate: "qsase_paperops_gate_interface.json",
    operator_dashboard: "qadam_operator_dashboard_view_model.json",
    telegram_summary_v2: "qsase_telegram_summary_v2.json",
    telegram_communications_mirror_v2: "qsase_telegram_communications_mirror_v2.json"
};

function readJson(filename) {
    const artifactPath = path.join(runtimeDir, filename);
    assert(fs.existsSync(artifactPath), `missing QSASE runtime artifact ${filename}`);
    return JSON.parse(fs.readFileSync(artifactPath, "utf8"));
}

function clone(value) {
    return JSON.parse(JSON.stringify(value));
}

function assertIncludesAll(text, needles, label) {
    needles.forEach((needle) => assert(text.includes(needle), `${label} missing ${needle}`));
}

function detailsWithAttribute(text, attribute) {
    const pattern = new RegExp(`<details\\b[^>]*\\b${attribute}(?=[\\s=>])[^>]*>`, "g");
    return text.match(pattern) || [];
}

function assertClosedDetails(text, attribute, expectedCount, label) {
    const tags = detailsWithAttribute(text, attribute);
    assert(tags.length === expectedCount, `${label} expected ${expectedCount} details element${expectedCount === 1 ? "" : "s"}, found ${tags.length}`);
    tags.forEach((tag) => assert(!/\sopen(?:\s|>)/.test(tag), `${label} must be collapsed initially`));
    return tags;
}

function buildQsaseFixture() {
    const artifactStatus = readJson(artifactMap.status);
    const sections = Object.fromEntries(
        Object.entries(artifactMap)
            .filter(([key]) => key !== "status")
            .map(([key, filename]) => [key, readJson(filename)])
    );
    sections.operator_dashboard = clone(status.qsase_dashboard?.sections?.operator_dashboard || {});

    return {
        ...artifactStatus,
        schema_version: "qsase_public_dashboard.v1",
        status: artifactStatus.status || "qsase_dashboard_visibility_ready",
        public_safe: true,
        read_only: true,
        sections,
        boundary: "Public dashboard visibility only. QSASE cannot create orders, approvals, broker writes, Telegram commands, live-capital authority, or paper proof ledger credit.",
        authority_flags: {
            creates_trade_candidates: false,
            creates_paper_orders: false,
            grants_proof_credit: false,
            enables_live_capital: false,
            sends_broker_writes: false,
            telegram_command_path_enabled: false
        }
    };
}

function assertStaticContract() {
    assertIncludesAll(renderer, [
        "function buildQsaseDashboardModel(status = {})",
        "status.qsase_dashboard",
        "qsase_dashboard_model",
        "function renderQsaseDashboardVisibility(qsase = {})",
        "QSASE_DASHBOARD_NAVIGATION",
        "function resolveQsaseDashboardRoute(search = \"\")",
        "function syncQsaseModuleNavigation",
        "data-qsase-navigation-shell",
        "data-qsase-module-panel",
        "Fund",
        "Observe",
        "Find Patterns",
        "Test & Decide",
        "Learn & Improve",
        "data-qsase-dashboard-rendered",
        "data-qsase-dashboard-contract=\"qsase_public_dashboard_v2\"",
        "data-qsase-section=\"portfolio_value_return\"",
        "data-qsase-section=\"portfolio_allocation_risk\"",
        "data-qsase-section=\"current_portfolio\"",
        "data-qsase-section=\"trading_history\"",
        "data-qsase-section=\"hedge_fund_team\"",
        "data-qsase-section=\"source_intelligence_network\"",
        "data-qsase-section=\"trading_universe\"",
        "data-qsase-section=\"trading_strategy_universe\"",
        "data-qsase-section=\"pattern_discovery\"",
        "data-qsase-section=\"trade_intents\"",
        "data-qsase-section=\"router_paperops_gate\"",
        "data-qsase-section=\"system_overview\"",
        "function qsaseSystemOverviewModel(qsase = {})",
        "function renderQsaseSystemOverview(qsase = {})",
        "data-qsase-portfolio-page",
        "function qsasePortfolioAnalyticsModel(qsase = {})",
        "function renderQsasePortfolioAnalytics(qsase = {}, model = {})",
        "function renderQsasePortfolioPage(qsase = {})",
        "function selectQsaseAllocationMode(button)",
        "const delta = Math.abs(rawDelta) < 0.5 ? 0 : rawDelta;",
        "Performance",
        "qsase-performance-period",
        "Portfolio Composition",
        "Gross exposure",
        "Net exposure",
        "Active sleeves",
        "P&amp;L contribution",
        "Positions",
        "No open positions",
        "Why Qadam is holding cash",
        "Timeline",
        "Hedge Fund Team",
        "Qadam Team Overview",
        "A hedge fund that fits inside your laptop.",
        "understand the world, understand its own machinery",
        "It treats cognition, latency, source freshness, and data quality as part of the strategy rather than hidden implementation details.",
        "qsase-team-facts",
        "qsase-team-card-role",
        "qsase-team-card-current",
        "Mandate",
        "Current assignment",
        "Works closely with",
        "Place in the fund",
        "When this role says no",
        "Python script [COO]",
        "local LLM [Research Analyst]",
        "frontier LLM [Strategy Lead]",
        "quantum computer [Head of Quant]",
        "Alternative Data Network",
        "Data Sources",
        "connected sources covering",
        "qsaseSourcePublicDescription",
        "data-qsase-source-category",
        "qsaseRestoreSourceCategoryState",
        "Structured political-violence and protest events",
        "MMSI, vessel name/type",
        "Federal Reserve economic series",
        "Satellite fire hotspot data from MODIS and VIIRS",
        "SEC filing data",
        "Multi-Asset Funds",
        "Trading Universe",
        "QSASE_INSTRUMENT_FULL_NAMES",
        "United States Brent Oil Fund LP",
        "qsaseInstrumentTooltip",
        "qsase-trading-universe-card",
        "qsase-instrument-chip",
        "Self-Refining Multi-Strategy Approach",
        "Trading Strategies",
        "Five defined strategies, with room to discover better ones.",
        "Defined",
        "Discovered",
        "Admitted",
        "Strategy Discovery Engine",
        "Emerging Strategy Candidates",
        "Strategy Evidence Path",
        "Explore section",
        "No new strategy has earned candidate status yet.",
        "Stages 4-5 only",
        "renderQsaseExplainedInstrumentCards",
        "renderQsaseSelfRefinementLoop",
        "renderQsaseStrategyDiscoveryEngine",
        "renderQsaseEmergingStrategyCandidates",
        "renderQsaseStrategyAdmissionPath",
        "qsase-strategy-playbook-card",
        "How this strategy works",
        "Why it could create an edge",
        "Core instruments explained",
        "Secondary instruments Qadam can use for context",
        "How the self-refinement loop works",
        "How backtesting improves this strategy over time",
        "View details",
        "cannot create a trade candidate",
        "Pattern Recognition",
        "Ready for Decision Room",
        "Current Fund Position",
        "Decision Room",
        "This is where an evidence-backed idea is checked for practical tradeability",
        "data-qsase-decision-room",
        "Why?",
        "What happens next?",
        "Research Ideas Approaching Decision",
        "Previous Decision Reviews",
        "Akber's multi-stage decision-making filter",
        "QSASE_AKBER_DECISION_STAGES",
        "Low volatility",
        "Options distribution",
        "On-balance volume and flow",
        "Judgment",
        "Execution suitability",
        "Postmortem learning",
        "Akber decision checklist",
        "Technical and operational details",
        "Filter Tradeability",
        "Govern the Decision",
        "Order Monitor",
        "renderQsaseActiveOrderRow",
        "renderQsaseActivePositionRow",
        "renderQsaseRecentOrderActivityRow",
        "renderQsaseTradingTimelineRows",
        "renderQsaseOrderMonitor",
        "candidate === \"fund/holdings\"",
        "candidate === \"trade/lifecycle\"",
        "candidate === \"decide/intents\"",
        "data-lifecycle-relationship",
        "Pipeline",
        "Active now",
        "Recent activity",
        "Stage 9 learning queue",
        "View full Fund Timeline",
        "No active paper orders or positions",
        "data-qsase-order-active",
        "data-qsase-order-recent",
        "Read-only Alpaca Paper mirror",
        "renderQsaseResultsAndLessons",
        "renderQsaseTestsAndImprovements",
        "Current learning answer",
        "Chronological learning record",
        "Reference-only broker history",
        "Communication record",
        "Current improvement answer",
        "Only an approved version can return to Observe",
        "candidate === \"learn/replay\"",
        "candidate === \"learn/briefs\"",
        "System Overview",
        "Lifecycle Health by Stage",
        "Running Now",
        "Health by Domain",
        "Needs Attention",
        "Recent Activity",
        "Technical Diagnostics",
        "candidate === \"system/activity\"",
        "candidate === \"system/health\"",
        "How to read the portfolio",
        "What Qadam most recently noticed",
        "renderQsaseRecentPatternAnalysis",
        "Sort observations",
        "Recommended",
        "Highest score",
        "Freshest sources",
        "A–Z",
        "How observation ordering works",
        "qsase-recent-pattern-sort-tooltip",
        "qsase-recent-pattern-score-tooltip",
        "Qadam found a possible relationship between recent activity and a future price move",
        "Higher scores are investigated first",
        "estimated chance of a price move",
        "View more readings",
        "instrument-level reading behind",
        "qsase-supporting-research-score-tooltip",
        "qsaseEvidenceFunnelHelp",
        "qsase-evidence-funnel-tooltip",
        "How many possible connections Qadam has listed",
        "Past moments with enough trustworthy data",
        "it still is not permission to place a trade",
        "Research pipeline",
        "Noticed → tested → validated",
        "Research archive",
        "Disproved or faded",
        "Ideas that failed testing or stopped appearing in current evidence",
        "data-qsase-research-archive",
        "primaryRelationships",
        "archiveRows",
        "data-qsase-recent-pattern-sort-explanation",
        "initQsaseRecentPatternSorting",
        "data-qsase-supporting-reading-toggle",
        "initQsaseSupportingReadings",
        "qadam.patternDiscovery.supportingReadingCount",
        "qadam.patternDiscovery.recentSort",
        "Where it goes next",
        "Quantum Edge",
        "Matched classical baseline",
        "data-tooltip-contract=\"nontechnical-guide\"",
        "data-guide-marker=",
        "system_overview",
        "Python COO",
        "Local LLM",
        "Frontier LLM",
        "Head of Quant",
        "renderQsaseSystemOverview",
        "qsase-system-current",
        "qadam-lifecycle-health",
        "current_portfolio",
        "pattern_intelligence_findings",
        "No order authority",
        "qsase-detail-ledger",
        "qsase-portfolio-page",
        "qsase-portfolio-page-head",
        "qsase-portfolio-meta",
        "qsase-allocation-donut",
        "qsase-cash-allocation",
        "qsase-allocation-legend",
        "qsase-pnl-contribution",
        "qsase-risk-strip",
        "qsase-positions-empty",
        "qsase-trading-timeline",
        "qsase-source-category-row",
        "qsase-market-pill-row",
        "pointTimeMs",
        "xForPoint",
        "timeTicks",
        "data-time-scaled-axis=",
        "data-qsase-time-axis",
        "chart-axis-time",
        "qsaseTradeAmountLabel",
        "qsaseClosedTradesInWindow",
        "qsaseOpenDetailKey",
        "renderQsaseSourceMarketEvidenceMap",
        "holding::${holding}",
        "closed trades in the last 7 days",
        "Amount"
    ], "QSASE renderer");
    [
        "qsase-jump-row",
        "Money first. Decisions last.",
        "Portfolio value</a>",
        "Holdings</a>",
        "Pattern workflow</a>",
        "PaperOps gate</a>",
        "Portfolio status: flat",
        "connected source rows",
        "19 Instruments over 6 Fund Categories",
        "Visible rows",
        "paper-proxy candidates",
        "watch-only/context instruments",
        "Route:",
        "Current state:",
        "credential-gated",
        "qsase-universe-key",
        "The Trading Universe defines where Qadam may look for paper ideas.",
        "paper-trading runner checks pass",
        "${qsaseHtmlText(role.status)} · no live-capital authority.",
        "means Qadam can watch the instrument, but cannot submit it directly as an Alpaca paper order.",
        "means the instrument helps compare market conditions but is not a paper-order target.",
        "means no setup is currently accepted for paper execution."
    ].forEach((needle) => {
        assert(!renderer.includes(needle), `QSASE renderer still contains removed navigation/copy ${needle}`);
    });

    assertIncludesAll(css, [
        ".qsase-dashboard-shell",
        ".qsase-portfolio-page",
        ".qsase-portfolio-chart",
        ".qsase-card-grid",
        ".qsase-table",
        ".qsase-source-category-list",
        ".qsase-source-category-row",
        ".qsase-source-category-row[open]",
        ".qsase-source-category-row > summary strong",
        ".qsase-source-category-row .qsase-instrument-tooltip",
        ".qsase-source-category-row .qsase-instrument-chip:hover .qsase-instrument-tooltip",
        ".qsase-source-market-map",
        ".qsase-source-market-flow",
        ".qsase-source-market-bridge",
        ".qsase-recent-pattern-controls",
        ".qsase-score-record-explainer",
        ".qsase-supporting-reading-list",
        ".qsase-supporting-reading-toggle",
        ".qsase-evidence-funnel-tooltip",
        ".qsase-pattern-pipeline",
        ".qsase-pattern-pipeline-head",
        ".qsase-research-archive",
        ".qsase-research-archive-body",
        "gap: clamp(1.5rem, 2.5vw, 2.25rem)",
        ".qsase-trading-timeline",
        ".qsase-trade-event",
        ".qsase-trade-event-amount",
        "cursor: default",
        ".qsase-portfolio-page-head",
        ".qsase-portfolio-meta",
        ".qsase-portfolio-analytics-grid",
        ".qsase-allocation-donut",
        ".qsase-cash-allocation",
        ".qsase-allocation-legend",
        ".qsase-pnl-contribution",
        ".qsase-risk-strip",
        ".qsase-positions-empty",
        ".qsase-market-pill-row",
        ".qsase-strategy-playbook-card",
        ".qsase-strategy-playbook-card[open]",
        ".qsase-strategy-summary-grid",
        "grid-template-columns: minmax(0, 1fr)",
        "View full playbook",
        "Hide full playbook",
        ".qsase-strategy-detail-body",
        ".qsase-strategy-explainer",
        ".qsase-explained-instrument-grid",
        ".qsase-strategy-evidence-grid",
        ".qsase-strategy-refinement-detail",
        ".qsase-strategy-refinement-toggle",
        ".qsase-order-monitor-v2",
        ".qsase-page-flow-explanation",
        ".qsase-order-current-state",
        ".qsase-order-state-counts",
        ".qsase-active-trade-row",
        ".qsase-order-lifecycle",
        ".qsase-recent-order-row",
        ".qsase-order-learning-handoff",
        ".qsase-final-decision",
        ".qsase-decision-disclosure",
        ".qsase-decision-disclosure:not([open]) > .qsase-decision-disclosure-body",
        ".qsase-decision-research-idea:not([open]) > .qsase-decision-research-idea-body",
        ".qsase-akber-explainer-stages > li > details:not([open]) > .qsase-akber-explainer-detail",
        ".qsase-guide-marker",
        ".qsase-guide-card",
        ".qsase-callout-head",
        ".qsase-segmented-control",
        ".chart-time-tick",
        ".qsase-portfolio-chart .chart-time-tick:nth-child(even)",
        ".chart-axis-time",
        "grid-template-columns: minmax(22rem, 1.05fr) minmax(20rem, 0.95fr);",
        "data-guide-tooltip-bound=\"true\"",
        "--qadam-tooltip-left",
        "--qadam-tooltip-top",
        "position: fixed;",
        "max-height: min(72vh, 32rem);",
        ".qsase-workflow-message",
        ".qsase-dashboard-v2",
        ".qsase-detail-ledger",
        ".qsase-system-overview",
        ".qsase-system-current",
        ".qadam-lifecycle-health-table",
        ".qsase-system-service",
        ".qsase-system-health-row",
        ".qsase-system-attention-list",
        ".qsase-system-activity-list",
        ".qsase-system-diagnostics",
        ".qsase-team-nav",
        ".qsase-team-facts",
        ".qsase-team-fact",
        ".qsase-team-card-role",
        ".qsase-team-card-technology",
        ".qsase-team-card-current",
        ".qsase-team-collective",
        ".qsase-navigation-layout",
        ".qsase-sidebar",
        ".qsase-nav-group",
        ".qsase-module-panel",
        ".qsase-dashboard-footer",
        ".qsase-intent-row",
        ".qsase-learning-loop",
        ".qsase-source-api-list p",
        "grid-template-columns: minmax(0, 1fr);",
        "max-width: 100%;",
        "grid-template-columns: repeat(4, minmax(0, 1fr));"
    ], "QSASE stylesheet");
    assert(
        !css.includes("grid-template-columns: minmax(0, 1fr) minmax(18rem, 0.68fr);"),
        "QSASE hero stylesheet still contains the removed two-column dashboard hero layout"
    );
    assert(!css.includes(".qsase-jump-row"), "QSASE stylesheet still styles removed jump row");

    assertIncludesAll(renderer, [
        "function positionDashboardGuideTooltip(marker)",
        "function initDashboardGuideTooltips()",
        "clampDashboardTooltipValue",
        "data-tooltip-contract=\"nontechnical-guide\"",
        "initDashboardGuideTooltips();"
    ], "QSASE tooltip positioning controller");

    assertIncludesAll(dashboardHtml, [
        releaseManifest.css_asset,
        releaseManifest.javascript_asset,
        "data-stage7-dashboard-visibility"
    ], "dashboard shell");
    [
        "Qadam Mission Control",
        "Paper trading mode",
        "Paper-only monitoring",
        "data-dashboard-debug-toggle",
        "data-dashboard-view-link"
    ].forEach((needle) => {
        assert(!dashboardHtml.includes(needle), `dashboard shell still contains removed chrome ${needle}`);
    });

    assertIncludesAll(cockpitStatus, [
        "QSASE_DASHBOARD_PUBLIC_ARTIFACTS",
        "\"pattern_to_paper_workflow\": \"qsase_pattern_to_paper_workflow.json\"",
        "\"pattern_intelligence\": \"qsase_pattern_intelligence.json\"",
        "def _qsase_dashboard_public_status",
        "\"qsase_dashboard\": _qsase_dashboard_public_status(settings)",
        "\"creates_paper_orders\": False",
        "\"enables_live_capital\": False",
        "\"telegram_command_path_enabled\": False"
    ], "cockpit status QSASE export");
}

async function assertRenderedContract() {
    const fixtureStatus = clone(status);
    fixtureStatus.qsase_dashboard = buildQsaseFixture();
    const patternTitles = [
        "Macro liquidity pressure across silver proxies",
        "Physical disruption pressure across crude-oil proxies",
        "Geopolitical repricing pressure across defence assets",
        "Policy and innovation pressure across semiconductor assets",
        "Event-market odds diverging from geopolitical evidence"
    ];
    const existingPatternView = readJson("qadam_pattern_discovery_dashboard.json");
    fixtureStatus.qsase_dashboard.sections.operator_dashboard.views["patterns/findings"] = {
        ...existingPatternView,
        artifact_type: "qadam_pattern_discovery_dashboard",
        generated_at: "2026-07-11T20:14:04.887295+00:00",
        status: "awaiting_empirical_evidence",
        headline: "No repeatable historical edge has been validated yet.",
        primary_blocker: "Provider-backed historical score rows and forward outcomes are still missing.",
        tabs: [
            {key: "live_observations", label: "Live observations", count: 0},
            {key: "under_testing", label: "Under testing", count: 5},
            {key: "validated_edges", label: "Validated edges", count: 0}
        ],
        funnel: [
            {key: "eligible", label: "Eligible historical snapshots", count: 0},
            {key: "backtested", label: "Backtested relationships", count: 0},
            {key: "validated", label: "Validated edges", count: 0}
        ],
        relationships: patternTitles.map((title) => ({
            ...(existingPatternView.relationships || []).find((relationship) => relationship.title === title),
            title,
            tab: "under_testing",
            relationship_type: "source-to-market lead lag",
            freshness: {state: "stale", observed_at: "2026-07-05T19:22:00.549555+00:00"},
            next_destination: {reason: "Collect provider-backed outcomes and run the frozen historical test."}
        }))
    };
    fixtureStatus.qsase_dashboard.sections.router.generated_at = "2026-07-06T09:36:54.085266+00:00";
    if (fixtureStatus.qsase_dashboard.sections.operator_dashboard.compatibility_sections?.router) {
        fixtureStatus.qsase_dashboard.sections.operator_dashboard.compatibility_sections.router.generated_at = "2026-07-06T09:36:54.085266+00:00";
    }
    fixtureStatus.qsase_dashboard.sections.trade_intents.intent_count = 3;
    fixtureStatus.qsase_dashboard.sections.trade_intents.rows = [
        {
            instrument: "CL=F",
            strategy_family: "crude_oil_energy_security_disruption",
            thesis: "Energy disruption may create a delayed move in crude oil.",
            state: "hold_missing_evidence",
            reason: "Required evidence is missing: akber_filter_hold_missing_context.",
            next_allowed_action: "watch_for_missing_confirmation",
            source_quorum: "pass",
            akber_filter: "hold_missing_context",
            quantum_review: "downgrade_or_hold"
        },
        {
            instrument: "CL=F",
            strategy_family: "crude_oil_energy_security_disruption",
            thesis: "Energy disruption may create a delayed move in crude oil.",
            state: "blocked_safety_boundary",
            reason: "Hard safety boundary blocks paper review: quantum_ambiguity_too_high.",
            next_allowed_action: "clear_safety_boundary_or_remap_to_paperable_expression",
            source_quorum: "pass",
            akber_filter: "reject",
            quantum_review: "hold"
        },
        {
            instrument: "SLV",
            strategy_family: "silver_macro_liquidity_stress",
            thesis: "Liquidity stress may support a confirmed move in silver.",
            state: "paper_review_candidate",
            reason: "Evidence is ready for paper review.",
            next_allowed_action: "candidate_for_paper_review",
            source_quorum: "pass",
            akber_filter: "pass",
            quantum_review: "pass"
        }
    ];
    const rendered = await renderWithStatus(fixtureStatus);
    const stageHtml = html(rendered, "[data-stage7-dashboard-visibility]");
    const portfolioStart = stageHtml.indexOf('data-qsase-view-panel="portfolio"');
    const portfolioEnd = stageHtml.indexOf('data-qsase-module-panel="fund" data-qsase-view-panel="timeline"', portfolioStart);
    const portfolioHtml = stageHtml.slice(portfolioStart, portfolioEnd);
    const teamStart = stageHtml.indexOf('data-qsase-module-panel="system" data-qsase-view-panel="team"');
    const teamEnd = stageHtml.indexOf('data-qsase-module-panel="fund" data-qsase-view-panel="portfolio"', teamStart);
    const teamHtml = stageHtml.slice(teamStart, teamEnd);
    const decisionStart = stageHtml.indexOf('data-qsase-module-panel="decide" data-qsase-view-panel="decision"');
    const decisionEnd = stageHtml.indexOf('data-qsase-module-panel="trade" data-qsase-view-panel="orders"', decisionStart);
    const decisionHtml = stageHtml.slice(decisionStart, decisionEnd);

    assert(portfolioStart >= 0 && portfolioEnd > portfolioStart, "rendered dashboard missing consolidated Portfolio panel");
    assert(teamStart >= 0 && teamEnd > teamStart, "rendered dashboard missing Qadam Team panel");
    assert(decisionStart >= 0 && decisionEnd > decisionStart, "rendered dashboard missing Decision Room panel");
    [
        "This is where an evidence-backed idea is checked for practical tradeability",
        "Current Fund Position",
        "Why?",
        "What happens next?",
        "Research Ideas Approaching Decision",
        "Akber's multi-stage decision-making filter",
        "Ready for Decision Room",
        "No current decision candidates",
        "Previous Decision Reviews",
        "Technical and operational details",
        "Filter Tradeability",
        "Govern the Decision"
    ].forEach((needle) => assert(decisionHtml.includes(needle), `Decision Room missing ${needle}`));
    const positionIndex = decisionHtml.indexOf('data-qsase-section="router_paperops_gate"');
    const researchIndex = decisionHtml.indexOf('id="qsase-research-ideas-approaching-decision"');
    const akberIndex = decisionHtml.indexOf('data-qsase-section="akber_explainer"');
    const readyIndex = decisionHtml.indexOf('id="qsase-decisions-brewing"');
    const previousIndex = decisionHtml.indexOf("data-qsase-previous-decision-reviews");
    const operationsIndex = decisionHtml.indexOf("data-qsase-decision-operations");
    assert(
        positionIndex >= 0
            && positionIndex < researchIndex
            && researchIndex < akberIndex
            && akberIndex < readyIndex
            && readyIndex < previousIndex
            && previousIndex < operationsIndex,
        "Decision Room hierarchy is not current position → research → Akber → candidates → history → operations"
    );
    assert(!decisionHtml.includes("Today's Decision"), "Decision Room must not imply a same-day decision without a fresh decision artifact");
    assert(/<section\b[^>]*data-qsase-section="router_paperops_gate"[^>]*>/.test(decisionHtml), "Current Fund Position must remain a visible section");
    assert(!/<details\b[^>]*data-qsase-section="router_paperops_gate"[^>]*>/.test(decisionHtml), "Current Fund Position must not become a collapsed details element");
    [
        ["data-qsase-decision-research", "Research Ideas Approaching Decision"],
        ["data-qsase-akber-explainer", "Akber's multi-stage decision-making filter"],
        ["data-qsase-decision-ready", "Ready for Decision Room"],
        ["data-qsase-previous-decision-reviews", "Previous Decision Reviews"],
        ["data-qsase-decision-operations", "Technical and operational details"]
    ].forEach(([attribute, label]) => assertClosedDetails(decisionHtml, attribute, 1, label));
    assertClosedDetails(decisionHtml, "data-qsase-decision-research-idea", 5, "Decision Room research rows");
    const akberStageTags = assertClosedDetails(decisionHtml, "data-qsase-akber-stage", 6, "Akber merged stage rows");
    const akberStageKeys = akberStageTags.map((tag) => tag.match(/data-qsase-akber-stage="([^"]+)"/)?.[1]);
    assert(
        JSON.stringify(akberStageKeys) === JSON.stringify(["context", "catalyst", "confirmation", "risk", "execution", "postmortem_learning"]),
        `Akber merged stage order mismatch: ${akberStageKeys.join(",")}`
    );
    assert(!decisionHtml.includes("Akber's six practical questions"), "Decision Room must not retain the duplicate practical-questions section");
    assert(!decisionHtml.includes("Six auditable lifecycle stages"), "Decision Room must not retain the duplicate lifecycle-stages heading");
    assert(!decisionHtml.includes("How Akber's multi-stage decision-making filter works"), "Decision Room must not retain the superseded Akber section title");
    assert((decisionHtml.match(/data-qsase-decision-candidate=/g) || []).length === 0, "zero validated edges must produce zero current decision candidates");
    assert((decisionHtml.match(/data-qsase-previous-decision-candidate/g) || []).length === 2, "three old review records should consolidate into two historical idea groups");
    assert((decisionHtml.match(/data-qsase-section="akber_explainer"/g) || []).length === 1, "Decision Room needs exactly one standalone Akber explainer");
    assert(decisionHtml.includes("3 older Router review records"), "historical review count must remain explicit");
    assert(decisionHtml.includes("2 previous reviews"), "consolidated idea should retain its two review records as history");
    assert((teamHtml.match(/class="qsase-source-category-row qsase-team-card /g) || []).length === 4, "Qadam Team panel should contain exactly four team profiles");
    assert((teamHtml.match(/<b>Currently<\/b>/g) || []).length === 4, "each Qadam team profile should show a Currently line");
    [
        ["COO", "Python script"],
        ["Research Analyst", "Local LLM"],
        ["Strategy Lead", "Frontier LLM"],
        ["Head of Quant", "Quantum computer"]
    ].forEach(([title, technology]) => {
        const titleIndex = teamHtml.indexOf(`<strong class="qsase-team-card-role">${title}</strong>`);
        const technologyIndex = teamHtml.indexOf(technology, titleIndex);
        const cardEnd = teamHtml.indexOf("</details>", titleIndex);
        assert(titleIndex >= 0 && technologyIndex > titleIndex && cardEnd > technologyIndex, `${title} should appear before its supporting technology`);
        assert(!teamHtml.slice(titleIndex, cardEnd).toLowerCase().includes("no live-capital authority"), `${title} restored the removed role annotation`);
    });
    [
        "<dt>Fund Manager</dt><dd>You</dd>",
        "<dt>Team</dt><dd>4 specialists</dd>",
        "<dt>Operating mode</dt><dd>Paper fund</dd>",
        "A hedge fund that fits inside your laptop.",
        "understand the world, understand its own machinery",
        "It treats cognition, latency, source freshness, and data quality as part of the strategy rather than hidden implementation details.",
        "Mandate",
        "Current assignment",
        "Works closely with",
        "Place in the fund",
        "When this role says no",
        "View profile",
        "Close profile",
        "Four specialised software colleagues, one human Fund Manager"
    ].forEach((needle) => assert(teamHtml.includes(needle), `Qadam Team panel missing ${needle}`));
    assert(!teamHtml.includes("500+ live data feeds"), "Qadam Team panel still contains the unsupported hardcoded source claim");
    assert(!teamHtml.includes("5 intelligence pipelines"), "Qadam Team panel still collapses current source categories into a hardcoded pipeline count");
    assert(teamHtml.includes("This team can observe, reason, challenge, and review."), "Qadam Team panel lost its collective boundary note");
    assert(portfolioHtml.includes("Updated"), "healthy portfolio metadata should show its broker update time");
    assert(!portfolioHtml.includes("Reconciled"), "healthy reconciliation should remain quiet");
    assert(!portfolioHtml.includes("<span>Fund</span>"), "Portfolio heading should not repeat its Fund navigation group");
    assert(!portfolioHtml.includes("qsase-allocation-donut"), "empty portfolio should use the compact cash allocation visual");
    assert(!portfolioHtml.includes("Since reset"), "Portfolio performance still exposes reset mechanics");
    assert(!portfolioHtml.includes("Allocation &amp; Risk"), "Portfolio composition still uses the retired risk-heavy heading");
    assert(!portfolioHtml.includes("-0.00%"), "Portfolio performance displays negative zero percent");
    assert(!portfolioHtml.includes("-US$0"), "Portfolio performance displays negative zero money");
    assert(!html(rendered, "[data-balance-ticker]").includes("30-day paper growth trial"), "balance ticker still exposes the retired trial calendar");
    assert(!html(rendered, "[data-balance-ticker]").includes("reset base"), "balance ticker still exposes reset mechanics");
    assert((stageHtml.match(/data-qadam-lifecycle data-lifecycle-route=/g) || []).length === 13, "every dashboard route should render one lifecycle map");
    assert(!stageHtml.includes("data-qsase-journey"), "legacy previous/next journey returned");

    [
        "Portfolio",
        "Performance",
        "From",
        "Portfolio Composition",
        "No open positions",
        "100% cash",
        "Positions",
        "Timeline",
        "Hedge Fund Team",
        "Alternative Data Network",
        "Data Sources",
        "connected sources covering",
        "Multi-Asset Funds",
        "Trading Universe",
        "United States Brent Oil Fund LP",
        "tabindex=\"0\" aria-describedby=\"qsase-instrument-bno-tooltip\"",
        "id=\"qsase-instrument-bno-tooltip\" class=\"qsase-instrument-tooltip\" role=\"tooltip\"",
        "United States Oil Fund",
        "Lockheed Martin Corporation",
        "Kalshi event contracts",
        "Self-Refining Multi-Strategy Approach",
        "Trading Strategies",
        "How this strategy works",
        "Why it could create an edge",
        "Core instruments explained",
        "Secondary instruments Qadam can use for context",
        "How the self-refinement loop works",
        "How backtesting improves this strategy over time",
        "Current blocker",
        "Next action",
        "Historical expectancy",
        "Nonlinear review",
        "Open Decision Room",
        "Pattern Recognition",
        "Research Ideas Approaching Decision",
        "Ready for Decision Room",
        "Current Fund Position",
        "Previous Decision Reviews",
        "This is where an evidence-backed idea is checked for practical tradeability",
        "Akber's multi-stage decision-making filter",
        "Decision Room",
        "System Overview",
        "Lifecycle Health by Stage",
        "Running Now",
        "Health by Domain",
        "Needs Attention",
        "Recent Activity",
        "Technical Diagnostics",
        "data-time-scaled-axis=\"true\"",
        "data-qsase-time-axis",
        "chart-axis-time",
        "closed trades in the last 7 days",
        "Amount",
        "data-qsase-source-category",
        "Structured political-violence and protest events",
        "MMSI, vessel name/type",
        "acquisition date and time",
        "company identifiers, current and former names",
        "series: observations, releases, release dates"
    ].forEach((needle) => assertIncludes(rendered, "[data-stage7-dashboard-visibility]", needle));

    [
        "portfolio_value_return",
        "portfolio_allocation_risk",
        "current_portfolio",
        "trading_history",
        "hedge_fund_team",
        "source_intelligence_network",
        "trading_universe",
        "pattern_discovery",
        "trading_strategy_universe",
        "trade_intents",
        "router_paperops_gate",
        "results_lessons",
        "tests_improvements",
        "system_overview"
    ].forEach((section) => {
        assert(stageHtml.includes(`data-qsase-section="${section}"`), `rendered QSASE dashboard missing section ${section}`);
    });

    const navigationOrder = [
        ["system", "team"],
        ["fund", "portfolio"],
        ["observe", "sources"],
        ["patterns", "findings"],
        ["decide", "strategies"],
        ["trade", "orders"],
        ["learn", "outcomes"],
        ["system", "overview"]
    ].map(([moduleId, viewId]) => stageHtml.indexOf(`data-qsase-module-target="${moduleId}" data-qsase-view-target="${viewId}"`));
    assert(navigationOrder.every((index) => index >= 0), "rendered QSASE dashboard missing required sidebar destinations");
    assert(navigationOrder.every((index, position) => position === 0 || index > navigationOrder[position - 1]), "rendered QSASE sidebar does not follow the fund-to-learning flow");

    [
        "Portfolio",
        "Portfolio Composition",
        "Positions",
        "Timeline",
        "Qadam Team Overview",
        "Data Sources",
        "Trading Universe",
        "Pattern Recognition",
        "Trading Strategies",
        "Results &amp; Lessons",
        "Tests &amp; Improvements",
        "System Overview"
    ].forEach((copy) => assert(stageHtml.includes(copy), `protected dashboard copy changed or disappeared: ${copy}`));

    [
        "live-capital authority",
        "paper proof ledger credit"
    ].forEach((needle) => {
        assert(stageHtml.toLowerCase().includes(needle.toLowerCase()), `rendered QSASE dashboard missing boundary wording ${needle}`);
    });

    [
        "data-cc6-real-portfolio-timeline",
        "Mission Control walkthrough",
        "qsase-jump-row",
        "Money first. Decisions last.",
        "Paper trading mode",
        "Paper-only monitoring",
        "Connected Data Sources",
        "Watched Trading Universe",
        "19 watched instruments · 6 categories · 19 paper-route candidates",
        "source network visible",
        "dashboard portfolio consistent",
        "portfolio values match",
        "Snapshot fresh (age unknown)",
        "trade markers are read-only history, not proof credit",
        "Portfolio status: flat",
        "connected source rows",
        "19 Instruments over 6 Fund Categories",
        "Visible rows",
        "Source Intelligence Network",
        "freshness not exported",
        "trust posture pending",
        "last update not exported",
        "moderate trust",
        "Qadam Paper Fund",
        "Paper Fund Status",
        "Portfolio Overview",
        "Current Portfolio",
        "What this means",
        "Available cash",
        "Final gate",
        "Start of dashboard",
        "End of dashboard",
        "Telegram Summary Mirror",
        "short message candidates",
        "duplicates held",
        "Duplicates held",
        "Live sends",
        "message ready for review",
        "message rejected duplicate",
        "message vetoed duplicate"
    ].forEach((needle) => {
        assert(!stageHtml.includes(needle), `QSASE dashboard should not render old overview element ${needle}`);
    });

    [
        "qsase-portfolio-page",
        "qsase-portfolio-page-head",
        "qsase-portfolio-analytics",
        "qsase-cash-allocation",
        "qsase-risk-strip",
        "qsase-positions-empty",
        "Alpaca Paper",
        "Updated",
        "Performance",
        "From",
        "Portfolio Composition",
        "Gross exposure",
        "Net exposure",
        "<dt>Gross exposure</dt><dd>0%</dd>",
        "<dt>Net exposure</dt><dd>0%</dd>",
        "Cash",
        "Largest position",
        "Active sleeves",
        "<dt>Active sleeves</dt><dd>0</dd>",
        "Positions",
        "No open positions",
        "100% cash",
        "Why Qadam is holding cash",
        "qsase-trading-timeline",
        "qsase-trading-summary",
        "Recent trading summary",
        "Accepted paper orders are up to date with Alpaca.",
        "qsase-source-category-row",
        "qsase-trading-universe-card",
        "qsase-instrument-chip-cloud",
        "qsase-instrument-chip",
        "qsase-instrument-tooltip",
        "An exchange-traded fund designed to follow Brent crude oil futures",
        "An exchange-traded fund holding U.S. aerospace and defence companies",
        "WTI crude oil futures continuous contract",
        "NVIDIA Corporation",
        "qsase-market-pill-row",
        "qsase-strategy-playbook-card",
        "qsase-strategy-page-summary",
        "qsase-strategy-workspace-section",
        "qsase-strategy-empty-state",
        "qsase-strategy-admission-track",
        "qsase-strategy-summary-grid",
        "View details",
        "qsase-discovery-analysis",
        "qsase-recent-pattern-list",
        "qsase-recent-pattern-controls",
        "Sort observations",
        "qsase-recent-pattern-select",
        "Highest score",
        "Freshest sources",
        "qsase-recent-pattern-sort-tooltip",
        "qsase-score-record-explainer",
        "relationship summaries",
        "qsase-supporting-reading-list",
        "qsase-supporting-reading-toggle",
        "View more readings",
        "qsase-evidence-funnel",
        "qsase-evidence-funnel-tooltip",
        "Research pipeline",
        "Research archive",
        "Where it goes next",
        "Order Monitor",
        "data-qsase-trade-monitor-flow",
        "Pipeline",
        "Order Monitor Health",
        "Recent activity",
        "Stage 9 learning queue",
        "View full Fund Timeline",
        "No active paper orders or positions",
        "Read-only Alpaca Paper mirror",
        "Results &amp; Lessons",
        "Tests &amp; Improvements",
        "What Qadam Learned",
        "How Qadam Improves",
        "Chronological learning record",
        "Reference-only broker history",
        "Communication record",
        "Only an approved version can return to Observe",
        "What Qadam most recently noticed",
        "Quantum Edge",
        "No incremental value has been measured yet.",
        "data-tooltip-contract=\"nontechnical-guide\"",
        "data-guide-marker=\"pattern_intelligence_findings\"",
        "How to read pattern recognition",
        "Guide: How to read pattern recognition",
        "What a current decision candidate means",
        "What System Overview reports",
        "System Overview",
        "Lifecycle Health by Stage",
        "Running Now",
        "Health by Domain",
        "Needs Attention",
        "Recent Activity",
        "Technical Diagnostics",
        "Python script",
        "COO",
        "Research Analyst",
        "Local LLM",
        "Strategy Lead",
        "Frontier LLM",
        "Head of Quant",
        "Quantum computer",
        "View profile",
        "Mandate",
        "Current assignment",
        "Works closely with",
        "Place in the fund",
        "When this role says no",
        "System Overview is public-safe and read-only",
        "What currently blocks it",
        "Technical evidence and falsifiers",
        "These sources can inform hypotheses, but none of them can place trades.",
        "Source-to-market evidence map",
        "View map",
        "qsase-source-market-map-summary",
        "Every connected source category is checked against every watched market.",
        "All source categories against the full watched universe",
        "Did the evidence change before or after price?",
        "a shipping disruption is checked not only against oil"
    ].forEach((needle) => {
        assert(stageHtml.includes(needle), `rendered QSASE dashboard missing redesigned UX element ${needle}`);
    });
    assert(
        stageHtml.includes("fallback review path") || stageHtml.includes("configured quantum provider path"),
        "rendered QSASE dashboard missing the current Head of Quant review path"
    );

    const evidenceMapCount = (stageHtml.match(/data-source-market-evidence-map=/g) || []).length;
    assert(evidenceMapCount === 1, `expected one detailed source-to-market evidence map owned by Trading Universe, found ${evidenceMapCount}`);
    assert(stageHtml.includes("Stage 1 to Stage 2 handoff"), "Data Sources compact evidence handoff missing");
    const openEvidenceMapCount = (stageHtml.match(/<details class="qsase-source-market-map"[^>]*\sopen(?:\s|>)/g) || []).length;
    assert(openEvidenceMapCount === 0, `source-to-market evidence maps should be collapsed by default, found ${openEvidenceMapCount} open`);
    const timelineSurfaceCount = (stageHtml.match(/data-qsase-timeline-surface=/g) || []).length;
    assert(timelineSurfaceCount === 1, `expected only the Fund Timeline surface, found ${timelineSurfaceCount}`);
    [
        "Position Lifecycle",
        "Orders needing attention",
        "Paper account chronology",
        "Same read-only chronology as the Fund Timeline",
        "data-qsase-order-timeline",
        "data-qsase-timeline-surface=\"order-monitor\""
    ].forEach((needle) => assert(!stageHtml.includes(needle), `Order Monitor still renders repeated content ${needle}`));
    [
        "Broker context",
        "Can this snapshot be trusted?"
    ].forEach((needle) => assert(!stageHtml.includes(needle), `Order Monitor still renders retired label ${needle}`));

    [
        "Router &amp; PaperOps Gate",
        "guarded PaperOps decision state",
        "Nothing is currently being considered by QSASE",
        "No filled holdings yet",
        "0 filled holdings",
        "Current Holdings",
        "qsase-fund-detail",
        "proof-eligible",
        "Lifecycle audit:",
        "Paper proof ledger:",
        "stale accepted order mirrors need review",
        "Hybrid boutique macro desk: Python COO, local analyst, frontier strategist, Head of Quant",
        "Self-awareness",
        "Mode: deterministic classical shadow",
        "State: consultation recorded",
        "Qadam can analyse this market sleeve, but each instrument still needs evidence, risk, and PaperOps gates before paper execution.",
        "paper-proxy candidates",
        "watch-only/context instruments",
        "qsase-universe-key",
        "The Trading Universe defines where Qadam may look for paper ideas.",
        "paper-trading runner checks pass",
        "means Qadam can watch the instrument, but cannot submit it directly as an Alpaca paper order.",
        "means the instrument helps compare market conditions but is not a paper-order target.",
        "means no setup is currently accepted for paper execution.",
        "alpaca paper proxy available guarded route only",
        "research only proxy not direct alpaca paperable",
        "context only until governed prediction market paper route"
    ].forEach((needle) => {
        assert(!stageHtml.includes(needle), `rendered QSASE dashboard still exposes internal copy ${needle}`);
    });
}

async function assertFilledHoldingsContract() {
    const fixtureStatus = clone(status);
    fixtureStatus.qsase_dashboard = buildQsaseFixture();
    const position = {
        row_type: "open_paper_position_mirror",
        position_id: "paper-position-smh-1",
        instrument: "SMH",
        symbol: "SMH",
        status: "open",
        direction: "long",
        quantity: 20,
        entry_price: 310.5,
        current_price: 315,
        market_value_gbp: 6300,
        unrealized_pnl_gbp: 90,
        source_intent_id: "intent-smh-1",
        invalidation: "Exit if export-control evidence reverses or the paper risk limit is breached.",
        next_lifecycle_action: "Monitor the semiconductor thesis and paper risk limit."
    };
    fixtureStatus.dashboard_portfolio = {
        artifact_type: "dashboard_portfolio_canonical_contract",
        status: "dashboard_portfolio_consistent",
        current_value_gbp: 100000,
        cash_gbp: 93700,
        display_currency: "USD",
        open_position_count: 1,
        open_order_count: 0,
        positions: [position],
        portfolio_consistency: {
            status: "ok",
            reported_open_position_count: 1,
            holding_row_count: 1
        }
    };
    fixtureStatus.qsase_dashboard.sections.current_portfolio = {
        status: "current_portfolio_present",
        position_count: 1,
        reported_open_position_count: 1,
        holding_row_count: 1,
        reconciliation_status: "ok",
        rows: [position]
    };
    fixtureStatus.qsase_dashboard.sections.trade_intents = {
        status: "trade_intents_visible",
        rows: [{
            intent_id: "intent-smh-1",
            instrument: "SMH",
            strategy_family: "semiconductor_policy_optionality",
            thesis: "Semiconductor export-control asymmetry may not yet be fully reflected in the sector proxy.",
            akber_filter: "passed_for_paper_position",
            quantum_review: "nonlinear interaction review supported the paper thesis"
        }]
    };
    fixtureStatus.qsase_dashboard.sections.pattern_intelligence = {
        status: "pattern_intelligence_visible",
        findings: [{
            pattern_id: "pattern-smh-1",
            instrument_symbols: ["SMH", "SOXX"],
            market_affected: "Semiconductors",
            evidence_summary: "Export-control filings and supply-chain evidence aligned with semiconductor price confirmation.",
            source_chain: ["SEC filings", "UN Comtrade trade data", "TradingView technical analysis"],
            quantum_review: {
                plain_english_result: "The nonlinear review supported the relationship but did not create the trade."
            }
        }]
    };
    fixtureStatus.qsase_dashboard.sections.trading_history = {
        status: "trading_history_visible",
        rows: [{
            row_type: "buy_order",
            event_type: "buy",
            instrument: "SMH",
            quantity: 20,
            submitted_at: "2026-07-10T12:00:00Z"
        }]
    };

    const rendered = await renderWithStatus(fixtureStatus);
    const holdingsHtml = html(rendered, "[data-stage7-dashboard-visibility]");
    [
        "data-qsase-portfolio-page",
        "Portfolio Composition",
        "Assets",
        "Sleeves",
        "data-qsase-allocation-mode",
        "P&amp;L contribution",
        "Gross exposure",
        "Net exposure",
        "<dt>Gross exposure</dt><dd>6.3%</dd>",
        "<dt>Net exposure</dt><dd>6.3%</dd>",
        "Cash",
        "Largest position",
        "Active sleeves",
        "<dt>Active sleeves</dt><dd>1</dd>",
        "Positions",
        "1 open",
        'data-qsase-holding="SMH"',
        "VanEck Semiconductor ETF",
        "Semiconductors · Long paper position",
        "Quantity",
        "Average entry",
        "Current price",
        "Market value",
        "Unrealized P&amp;L",
        "6.3% of paper portfolio",
        "Why this holding?",
        "Why Qadam holds it",
        "Semiconductor export-control asymmetry",
        "Strategy and decision path",
        "Evidence behind the position",
        "Nonlinear review",
        "Risk and exit condition",
        "What Qadam does next",
        "Visible position timeline",
        "Bought / ordered 20 units"
    ].forEach((needle) => assert(holdingsHtml.includes(needle), `filled portfolio view missing ${needle}`));
    assert(!holdingsHtml.includes("No open positions"), "filled portfolio view rendered the empty state");
    assert(!holdingsHtml.includes("Why Qadam is holding cash"), "filled portfolio view rendered the cash-state handoff");
    assert(!holdingsHtml.includes('data-qsase-view-panel="holdings"'), "filled portfolio rendered a separate Holdings page");
    assert(!holdingsHtml.includes('data-qsase-module-target="fund" data-qsase-view-target="holdings"'), "filled portfolio rendered a Holdings navigation link");
}

async function assertZeroValueEmptyPortfolioContract() {
    const fixtureStatus = clone(status);
    fixtureStatus.qsase_dashboard = buildQsaseFixture();
    fixtureStatus.dashboard_portfolio = {
        artifact_type: "dashboard_portfolio_canonical_contract",
        status: "dashboard_portfolio_consistent",
        current_value_gbp: 0,
        cash_gbp: 0,
        display_currency: "USD",
        open_position_count: 0,
        open_order_count: 0,
        positions: [],
        portfolio_consistency: { status: "ok", reported_open_position_count: 0, holding_row_count: 0 }
    };
    fixtureStatus.qsase_dashboard.sections.current_portfolio = {
        status: "current_portfolio_empty",
        position_count: 0,
        reported_open_position_count: 0,
        holding_row_count: 0,
        reconciliation_status: "ok",
        rows: []
    };

    const rendered = await renderWithStatus(fixtureStatus);
    const portfolioHtml = html(rendered, "[data-stage7-dashboard-visibility]");
    [
        'aria-label="Asset allocation: Cash 100%"',
        "qsase-cash-allocation",
        "Gross exposure",
        "Net exposure",
        "<dt>Gross exposure</dt><dd>0%</dd>",
        "<dt>Net exposure</dt><dd>0%</dd>",
        "<dt>Active sleeves</dt><dd>0</dd>",
        "0%",
        "100% cash",
        "No open positions",
        "Why Qadam is holding cash"
    ].forEach((needle) => assert(portfolioHtml.includes(needle), `zero-value empty portfolio missing ${needle}`));
}

async function assertPortfolioAttentionMetadataContract() {
    const fixtureStatus = clone(status);
    fixtureStatus.qsase_dashboard = buildQsaseFixture();
    fixtureStatus.dashboard_portfolio = {
        ...fixtureStatus.dashboard_portfolio,
        broker_mirror_freshness: {
            status: "stale",
            observed_at: "2026-07-10T10:00:00Z"
        },
        portfolio_consistency: { status: "mismatch" }
    };

    const rendered = await renderWithStatus(fixtureStatus);
    const stageHtml = html(rendered, "[data-stage7-dashboard-visibility]");
    ["Stale mirror", "Needs reconciliation"].forEach((needle) => {
        assert(stageHtml.includes(needle), `portfolio attention metadata missing ${needle}`);
    });
}

async function main() {
    assertStaticContract();
    await assertRenderedContract();
    await assertZeroValueEmptyPortfolioContract();
    await assertPortfolioAttentionMetadataContract();
    await assertFilledHoldingsContract();
    console.log("dashboard_qsase_public_frontend=ok");
}

if (require.main === module) {
    main().catch((error) => {
        console.error(error.message);
        process.exitCode = 1;
    });
}
