#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const {
    assert,
    assertIncludes,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

const repoRoot = path.resolve(__dirname, "..");
const htmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const cssPath = path.join(repoRoot, "landing-page-repo", "auth.css");
const rendererPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-implementation-plan.md");

const html = fs.readFileSync(htmlPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");
const renderer = fs.readFileSync(rendererPath, "utf8");
const plan = fs.readFileSync(planPath, "utf8");

function assertText(text, needle, label) {
    assert(text.includes(needle), `${label} missing ${needle}`);
}

function assertFileExists(relativePath) {
    const filePath = path.join(repoRoot, relativePath);
    assert(fs.existsSync(filePath), `missing acceptance dependency ${relativePath}`);
}

function assertNoUnsafePublicText(text, label) {
    [
        /\/Users\//,
        /\/private\//,
        /\/var\/folders\//,
        /\\Users\\/,
        /\b[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b/,
        /\d{6,}:[A-Za-z0-9_-]{20,}/,
        /sk-[A-Za-z0-9_-]{20,}/,
        /ghp_[A-Za-z0-9_]{20,}/,
        /PVZ[0-9A-Za-z_-]{20,}/,
        /TELEGRAM_BOT_TOKEN=/,
        /TELEGRAM_DEFAULT_CHAT_ID=/,
        /SUPABASE_SECRET_KEY=/,
        /GEMINI_API_KEY=/,
        /ANTHROPIC_API_KEY=/,
        /OPENAI_API_KEY=/
    ].forEach((pattern) => {
        assert(!pattern.test(text), `${label} contains unsafe public text: ${pattern}`);
    });
}

[
    "scripts/check_dashboard_page_architecture.js",
    "scripts/check_dashboard_information_hierarchy.js",
    "scripts/check_dashboard_system_map.js",
    "scripts/check_dashboard_visual_system.js",
    "scripts/check_dashboard_section_explainers.js",
    "scripts/check_dashboard_panel_redesign.js",
    "scripts/check_dashboard_density_toggle.js",
    "scripts/check_dashboard_overhaul_overview.js",
    "scripts/check_dashboard_stage7_visibility.js",
    "scripts/check_dashboard_d11b_new_navigation_contract.js",
    "scripts/check_dashboard_d11c_canonical_status_language.js",
    "scripts/check_dashboard_d11d_single_safety_strip.js",
    "scripts/check_dashboard_d11e_rebuild_overview.js",
    "scripts/check_dashboard_d11f_trades_view_consolidation.js",
    "scripts/check_dashboard_d11g_evidence_view_consolidation.js",
    "scripts/check_dashboard_d11h_reasoning_view_consolidation.js",
    "scripts/check_dashboard_d11i_operations_view.js",
    "scripts/check_dashboard_d11j_tooltip_simplification.js",
    "scripts/check_dashboard_d11k_view_model_refactor.js",
    "scripts/check_dashboard_d11l_visual_simplification.js",
    "scripts/check_dashboard_d11m_regression_acceptance.js",
    "scripts/check_dashboard_d11n_documentation_guide_alignment.js",
    "scripts/check_dashboard_d11o_deployment_discipline.js",
    "scripts/check_dashboard_d12_language_cleanup.js",
    "scripts/check_dashboard_d13_health_language.js",
    "scripts/check_dashboard_mission_control.js",
    "scripts/check_dashboard_durable_spine.js",
    "scripts/check_dashboard_renderer.js",
    "scripts/check_dashboard_live_bridge.js",
    "scripts/check_dashboard_watching_view.js",
    "scripts/check_dashboard_cognition_view.js",
    "scripts/check_dashboard_trade_board.js",
    "scripts/check_dashboard_money_panel.js",
    "scripts/check_dashboard_tradingview_source.js",
    "scripts/check_dashboard_communications.js",
    "scripts/check_dashboard_forum.js",
    "scripts/check_protected_user_guide.js",
    "scripts/check_cockpit_status.py",
    "scripts/check_live_bridge.py",
    "docs/qadam-dashboard-d12-language-cleanup-2026-05-26.md",
    "docs/qadam-dashboard-d13-health-language-and-ibm-readiness-2026-05-26.md"
].forEach(assertFileExists);

[
    "Phase D10A - Scrollable Cockpit Page Architecture",
    "Phase D10B - Dashboard Information Hierarchy",
    "Phase D10C - Real System Map",
    "Phase D10D - Visual System Upgrade",
    "Phase D10E - Section Explainers",
    "Phase D10F - Panel-Level Redesign",
    "Phase D10G - Executive / Terminal Density Toggle",
    "Phase D10H - Testing And Acceptance"
].forEach((needle) => assertText(plan, needle, "implementation plan"));

[
    "dashboard-detail-flow",
    "data-overview-portfolio-hero",
    "data-balance-ticker",
    "data-trade-toast-rail",
    "data-overview-first-screen",
    "Mission Control",
    "data-mission-control",
    "data-overview-mission-brief",
    "data-overview-strategy-narrative",
    "data-overview-strategy-universe",
    "data-overview-paper-trade-state",
    "data-overview-control-plane",
    "data-overview-source-summary",
    "data-stage7-dashboard-visibility",
    "Mission Control walkthrough",
    "data-operations-consolidated-readout",
    "Control Plane",
    "Real portfolio timeline",
    "Loading portfolio value, trade timeline, and paper-account state.",
    "data-section-explainer",
    "explainer-grid",
    "data-panel-brief",
    "/auth.css?v=20260706-final-gate-inline-v1",
    "/dashboard.js?v=20260706-final-gate-inline-v1"
].forEach((needle) => assertText(html, needle, "dashboard HTML"));

[
    "Mission Snapshot",
    "Paper Account &amp; Trade State",
    "Strategy Universe",
    "Data source tracker"
].forEach((needle) => assertText(html, needle, "dashboard authority copy"));

[
    "Qadam Mission Control",
    "Follow the paper fund from evidence to hypotheses, replay, and paper outcomes.",
    "Paper trading mode",
    "Paper-only monitoring",
    "data-dashboard-debug-toggle",
    "data-dashboard-view-link"
].forEach((needle) => {
    assert(!html.includes(needle), `dashboard HTML still contains removed dashboard chrome ${needle}`);
});

[
    "--bg: #0a0a0c",
    "--font-sans",
    "--font-mono",
    "--glow-cyan",
    "backdrop-filter: blur",
    ".dashboard-detail-flow",
    ".overview-first-screen",
    ".overview-portfolio-hero",
    ".portfolio-trade-timeline",
    ".portfolio-trade-timeline-grid",
    ".overview-mission-brief",
    ".overview-strategy-narrative",
    ".strategy-universe-ledger[open]",
    ".overview-source-summary-panel",
    ".stage7-dashboard-visibility",
    ".mission-paper-fund",
    ".mission-source-network",
    ".mission-markets",
    ".mission-learning",
    ".mission-completion-gaps",
    ".source-universe-ledger",
    ".overview-control-plane",
    ".overview-readout-list",
    ".control-plane-grid",
    ".overview-mini-guide",
    ".overview-expandable-ledger",
    ".overview-ledger-group",
    ".operations-consolidated-readout",
    ".system-flow-diagram",
    ".panel-brief",
    ".section-explainer"
].forEach((needle) => assertText(css, needle, "dashboard CSS"));

[
    "function renderPanelBrief",
    "function replacePanelBrief",
    "function renderMissionControl",
    "function buildStage7VisibilityModel",
    "function renderStage7Visibility",
    "function renderQsaseDashboardVisibility",
    "function renderOverviewFirstScreen",
    "function renderContractPortfolioHero",
    "function renderPortfolioTradeTimeline",
    "function overviewNodeGuide",
    "function renderContractSourceSummary",
    "function renderContractTradeStateSummary",
    "function buildBalanceTickerModel",
    "function renderBalanceTicker",
    "function buildTradeTimelineTokens",
    "function renderFlowMap",
    "function renderOperatingSummary",
    "DASHBOARD_LEGACY_HASH_TARGETS",
    "renderQadamDashboardStatus"
].forEach((needle) => assertText(renderer, needle, "dashboard renderer"));

[
    "qsase-fund-status",
    "qsase-fund-context",
    "qsase-kpi-row",
    "qsase-trading-timeline",
    "qsase-source-category-row",
    "qsase-market-pill-row",
    "qsase-pattern-priority",
    "qsase-guide-marker",
    "qsase-guide-card",
    "qsase-pulse-terminal",
    "qsase-terminal-frame",
    "matrix-rain",
    "Qadam Pulse Terminal",
    "QADAM HEARTBEAT",
    "Python COO",
    "Head of Quant",
    "data-tooltip-contract=\"nontechnical-guide\"",
    "Final Paper-Trade Gate"
].forEach((needle) => assertText(`${renderer}\n${css}`, needle, "simplified QSASE dashboard"));

[
    "data-density-toggle",
    "data-density-option",
    "DASHBOARD_DENSITY_KEY",
    "function initDashboardDensityToggle",
    "window.setDashboardDensity",
    "document.documentElement.dataset.dashboardDensity",
    "html[data-dashboard-density=\"terminal\"]"
].forEach((needle) => {
    assert(!`${html}\n${css}\n${renderer}`.includes(needle), `dashboard acceptance found obsolete density artifact ${needle}`);
});

[
    "Read-only dashboard",
    "Hide diagnostics",
    "Default to Mission Snapshot",
    "Read paper mirror and lifecycle counts",
    "Use Strategy Universe for strategy posture",
    "Show lifecycle counts only",
    "Show source posture only",
    "Control Plane owns operating flow",
    "paper authorized ready to poll",
    "Run the PaperOps lifecycle poller"
].forEach((needle) => {
    assert(!html.includes(needle), `dashboard HTML still contains obsolete visible copy: ${needle}`);
});

assertNoUnsafePublicText(html, "dashboard HTML");
assertNoUnsafePublicText(css, "dashboard CSS");
assertNoUnsafePublicText(renderer, "dashboard renderer");

(async () => {
    const legacyStatus = JSON.parse(JSON.stringify(status));
    delete legacyStatus.qsase_dashboard;
    const rendered = await renderWithStatus(legacyStatus);

    assert(
        rendered.document.documentElement.dataset.dashboardStatus === "rendered",
        "dashboard acceptance expected rendered status"
    );
    assert(
        rendered.document.documentElement.dataset.dashboardStatusSource === "live_bridge",
        "dashboard acceptance expected live bridge preference"
    );
    [
        ["[data-status-banner]", "Dashboard status loaded"],
        ["[data-status-banner]", "Live status connected"],
        ["[data-stage7-dashboard-visibility]", "Paper Fund Status"],
        ["[data-stage7-dashboard-visibility]", "Source Intelligence Network"],
        ["[data-stage7-dashboard-visibility]", "Watched Markets Universe"],
        ["[data-stage7-dashboard-visibility]", "Strategy Playbook"],
        ["[data-stage7-dashboard-visibility]", "Hedge Fund Investment Team"],
        ["[data-stage7-dashboard-visibility]", "Hypotheses &amp; Pattern Recognition"],
        ["[data-stage7-dashboard-visibility]", "Backtesting &amp; Replay Lab"],
        ["[data-stage7-dashboard-visibility]", "Remaining setup"],
        ["[data-stage7-dashboard-visibility]", "What still needs attention"],
        ["[data-stage7-dashboard-visibility]", "Paper blockers"],
        ["[data-stage7-dashboard-visibility]", "GBP 100,000"],
        ["[data-stage7-dashboard-visibility]", "GBP 200,000"],
        ["[data-stage7-dashboard-visibility]", "Mission Control is read-only"],
        ["[data-overview-portfolio-hero]", "Real portfolio timeline"],
        ["[data-overview-portfolio-hero]", "Paper account portfolio value line"],
        ["[data-overview-portfolio-hero]", "Trade timeline"],
        ["[data-overview-portfolio-hero]", "Bought and held"],
        ["[data-overview-portfolio-hero]", "Sold and closed"],
        ["[data-overview-mission-brief]", "Mission Snapshot"],
        ["[data-overview-mission-brief]", "Durable replay"],
        ["[data-overview-mission-brief]", "Trade lifecycle"],
        ["[data-overview-strategy-narrative]", "Strategy Universe"],
        ["[data-overview-strategy-narrative]", "Asymmetric Catalyst Proxy Trading"],
        ["[data-overview-strategy-narrative]", "Universe"],
        ["[data-overview-strategy-narrative]", "Qualified now"],
        ["[data-overview-strategy-narrative]", "Waiting"],
        ["[data-overview-strategy-narrative]", "Second-order AI infrastructure beneficiary lens"],
        ["[data-overview-strategy-narrative]", "Open the full universe"],
        ["[data-overview-strategy-narrative]", "Qadam-native edge"],
        ["[data-overview-strategy-narrative]", "Semiconductor Policy Options Asymmetry"],
        ["[data-overview-strategy-narrative]", "Defence Repricing Geopolitical Watch"],
        ["[data-overview-strategy-narrative]", "Silver Macro Liquidity Stress"],
        ["[data-overview-strategy-narrative]", "Crude Oil Energy Security Disruption"],
        ["[data-overview-strategy-narrative]", "Prediction Market Geopolitical Dislocation"],
        ["[data-overview-strategy-narrative]", "Akber filter"],
        ["[data-overview-strategy-narrative]", "guarded Alpaca Paper"],
        ["[data-overview-paper-trade-state]", "Paper Account &amp; Trade State"],
        ["[data-overview-paper-trade-state]", "Balance"],
        ["[data-overview-paper-trade-state]", "Current value"],
        ["[data-overview-paper-trade-state]", "Total P&amp;L"],
        ["[data-overview-paper-trade-state]", "Trade state"],
        ["[data-overview-control-plane]", "Control Plane"],
        ["[data-overview-control-plane]", "Qadam operating team"],
        ["[data-overview-control-plane]", "Chief Operating Officer"],
        ["[data-overview-control-plane]", "Local LLM"],
        ["[data-overview-control-plane]", "Head of Quant"],
        ["[data-overview-control-plane]", "How to read this node"],
        ["[data-overview-control-plane]", "Currently"],
        ["[data-overview-control-plane]", "Next handoff"],
        ["[data-overview-source-summary]", "Data source tracker"],
        ["[data-overview-source-summary]", "Source list"],
        ["[data-overview-source-summary]", "signal-review eligible"],
        ["[data-overview-source-summary]", "ACLED API"],
        ["[data-mission-sources]", "logged-in/configured"],
        ["[data-mission-sources]", "replay"],
        ["[data-mission-philosophy]", "Trading philosophy"],
        ["[data-mission-stack]", "Local LLM"],
        ["[data-mission-stack]", "replay"],
        ["[data-mission-trades]", "Trade intent"],
        ["[data-mission-portfolio]", "Paper account"],
        ["[data-operating-summary]", "Paper account"],
        ["[data-operating-summary]", "Source quality"],
        ["[data-operating-summary]", "Safety boundary"],
        ["[data-operating-summary]", "Bridge"],
        ["[data-overview-control-plane]", "Research Analyst"],
        ["[data-overview-control-plane]", "PaperOps"],
        ["[data-overview-control-plane]", "Intelligence Pipelines"],
        ["[data-overview-control-plane]", "mission_control"],
        ["[data-overview-control-plane]", "Safety Policy"],
        ["[data-overview-control-plane]", "Paper/Demo State"],
        ["[data-overview-control-plane]", "Learning Review"],
        ["[data-overview-control-plane]", "Closed-loop rule"],
        ["[data-overview-control-plane]", "What it does"],
        ["[data-overview-control-plane]", "Boundary"],
        ["[data-source-summary]", "Sources"],
        ["[data-watching-list]", "pipeline-row"],
        ["[data-cognition]", "Reasoning readout"],
        ["[data-cognition]", "Hypotheses and evidence"],
        ["[data-trade-layer]", "Consolidated trade readout"],
        ["[data-trade-layer]", "Paper trade lifecycle"],
        ["[data-trade-layer]", "Gate chain and broker readiness"],
        ["[data-trade-layer]", "Signals, trade ideas, and paper trades"],
        ["[data-trade-layer]", "Observed signals"],
        ["[data-trade-layer]", "Trade ideas"],
        ["[data-trade-layer]", "Blocked trades"],
        ["[data-capital]", "Panel readout"],
        ["[data-capital]", "Current"],
        ["[data-capital]", "Closed trades"]
    ].forEach(([selector, expected]) => assertIncludes(rendered, selector, expected));

    const overviewSourceSummary = rendered.elements.get("[data-overview-source-summary]")?.innerHTML || "";
    const overviewTradeState = rendered.elements.get("[data-overview-paper-trade-state]")?.innerHTML || "";
    assert(!overviewTradeState.includes("USO options watch"), "acceptance: Overview trade state must not render trade-row ledger entries");
    [
        "Default to Mission Snapshot",
        "Read paper mirror and lifecycle counts",
        "Use Strategy Universe for strategy posture",
        "Show lifecycle counts only",
        "Show source posture only",
        "Control Plane owns operating flow"
    ].forEach((needle) => {
        const renderedHtml = [
            rendered.elements.get("[data-overview-mission-brief]")?.innerHTML || "",
            rendered.elements.get("[data-overview-strategy-narrative]")?.innerHTML || "",
            rendered.elements.get("[data-overview-paper-trade-state]")?.innerHTML || "",
            rendered.elements.get("[data-overview-control-plane]")?.innerHTML || "",
            rendered.elements.get("[data-overview-source-summary]")?.innerHTML || ""
        ].join("\n");
        assert(!renderedHtml.includes(needle), `acceptance: rendered overview still contains obsolete copy ${needle}`);
    });

    console.log("dashboard_acceptance=ok");
})().catch((error) => {
    console.error(error.message);
    process.exit(1);
});
