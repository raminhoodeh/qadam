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
    "data-dashboard-safety-strip",
    "data-balance-ticker",
    "data-trade-toast-rail",
    "data-overview-first-screen",
    "Paper Trading Overview",
    "data-overview-command-surface",
    "data-overview-review-card",
    "data-overview-proof-flow",
    "data-overview-system-summary",
    "data-overview-status-rail",
    "data-overview-hero",
    "data-overview-lifecycle",
    "data-overview-mini-map",
    "data-overview-boundary-rail",
    "data-overview-next-links",
    "data-mission-primary",
    "system-flow-diagram",
    "Closed-loop rule",
    "data-section-explainer",
    "explainer-grid",
    "data-panel-brief",
    "data-dashboard-view-target=\"evidence\"",
    "/auth.css?v=20260603-rs0-paper-authority",
    "/dashboard.js?v=20260603-rs0-paper-authority"
].forEach((needle) => assertText(html, needle, "dashboard HTML"));

[
    "Readout only; this page cannot place orders.",
    "Map only; nodes are not controls.",
    "No command route",
    "A trade idea is not an order",
    "live capital disabled",
    "Notify-only; no command path.",
    "Context only; requires live corroboration.",
    "Event stream only; not shell access.",
    "Paper mirror; no funding authority.",
    "cannot originate trades or bypass risk"
].forEach((needle) => assertText(html, needle, "dashboard authority copy"));

[
    "--bg: #0a0a0c",
    "--font-sans",
    "--font-mono",
    "--glow-cyan",
    "backdrop-filter: blur",
    ".dashboard-detail-flow",
    ".dashboard-safety-strip",
    ".overview-first-screen",
    ".overview-command-surface",
    ".overview-review-card",
    ".overview-proof-flow",
    ".overview-system-summary",
    ".overview-status-rail",
    ".overview-readout-list",
    ".overview-lifecycle-strip",
    ".overview-mini-map",
    ".overview-mini-guide",
    ".overview-expandable-ledger",
    ".overview-ledger-group",
    ".system-flow-diagram",
    ".panel-brief",
    ".section-explainer"
].forEach((needle) => assertText(css, needle, "dashboard CSS"));

[
    "function renderPanelBrief",
    "function replacePanelBrief",
    "function renderMissionControl",
    "function renderOverviewFirstScreen",
    "function overviewNodeGuide",
    "function renderOverviewSourcePipeline",
    "function renderOverviewStrategyRow",
    "function renderDashboardSafetyStrip",
    "function buildBalanceTickerModel",
    "function renderBalanceTicker",
    "function buildTradeTimelineTokens",
    "function renderFlowMap",
    "function renderOperatingSummary",
    "DASHBOARD_LEGACY_HASH_TARGETS",
    "renderQadamDashboardStatus"
].forEach((needle) => assertText(renderer, needle, "dashboard renderer"));

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

assertNoUnsafePublicText(html, "dashboard HTML");
assertNoUnsafePublicText(css, "dashboard CSS");
assertNoUnsafePublicText(renderer, "dashboard renderer");

(async () => {
    const rendered = await renderWithStatus(status);

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
        ["[data-dashboard-safety-strip]", "OK - paper only"],
        ["[data-dashboard-safety-strip]", "OK - live capital off"],
        ["[data-dashboard-safety-strip]", "Dashboard cannot place orders"],
        ["[data-overview-status-rail]", "Paper growth trial"],
        ["[data-overview-status-rail]", "Autonomous runner"],
        ["[data-overview-status-rail]", "Potential setups"],
        ["[data-overview-hero]", "Current summary"],
        ["[data-overview-review-card]", "Needs review"],
        ["[data-overview-lifecycle]", "Observed signals"],
        ["[data-overview-mini-map]", "Python script"],
        ["[data-overview-mini-map]", "Local LLM"],
        ["[data-overview-mini-map]", "Quantum computer"],
        ["[data-overview-mini-map]", "How to read this node"],
        ["[data-overview-mini-map]", "Currently"],
        ["[data-overview-mini-map]", "Next handoff"],
        ["[data-overview-data-sources]", "Click to expand the full source list"],
        ["[data-overview-data-sources]", "ACLED API"],
        ["[data-overview-data-sources]", "credential"],
        ["[data-overview-trading-strategies]", "Click to expand every strategy family"],
        ["[data-overview-trading-strategies]", "Crude Oil Energy Security Disruption"],
        ["[data-overview-trading-strategies]", "no broker write"],
        ["[data-overview-boundary-rail]", "Safety Status"],
        ["[data-overview-next-links]", "#trades"],
        ["[data-mission-primary]", "Operating thesis"],
        ["[data-mission-primary]", "hypotheses"],
        ["[data-mission-primary]", "Replay"],
        ["[data-mission-sources]", "logged-in/configured"],
        ["[data-mission-sources]", "replay"],
        ["[data-mission-philosophy]", "Trading philosophy"],
        ["[data-mission-stack]", "Local LLM"],
        ["[data-mission-stack]", "replay"],
        ["[data-mission-trades]", "Trade intent"],
        ["[data-mission-portfolio]", "Paper account"],
        ["[data-operating-summary]", "Paper account"],
        ["[data-operating-summary]", "Source quality"],
        ["[data-operating-summary]", "Safety strip"],
        ["[data-operating-summary]", "Bridge"],
        ["[data-fund-model]", "Fund Manager"],
        ["[data-fund-model]", "Python records the system"],
        ["[data-fund-model]", "Models inform, gates decide"],
        ["[data-flow-map]", "Watched Sources"],
        ["[data-flow-map]", "Event Log"],
        ["[data-flow-map]", "Research Analyst"],
        ["[data-flow-map]", "Risk Agent"],
        ["[data-flow-map]", "Paper Account Mirror"],
        ["[data-flow-map]", "Telegram Bot"],
        ["[data-flow-map]", "Closed-loop rule"],
        ["[data-flow-map]", "Input"],
        ["[data-flow-map]", "Output"],
        ["[data-source-summary]", "Sources"],
        ["[data-watching-list]", "pipeline-row"],
        ["[data-cognition]", "Reasoning readout"],
        ["[data-cognition]", "Hypotheses and evidence"],
        ["[data-worldview]", "Panel readout"],
        ["[data-worldview]", "Decision chain"],
        ["[data-forbidden-actions]", "live capital"],
        ["[data-communications]", "Panel readout"],
        ["[data-communications]", "Recent outbox"],
        ["[data-trade-layer]", "Consolidated trade readout"],
        ["[data-trade-layer]", "Paper trade lifecycle"],
        ["[data-trade-layer]", "Gate chain and broker readiness"],
        ["[data-trade-layer]", "Signals, trade ideas, and paper trades"],
        ["[data-trade-layer]", "Observed signals"],
        ["[data-trade-layer]", "Trade ideas"],
        ["[data-trade-layer]", "Blocked trades"],
        ["[data-capital]", "Panel readout"],
        ["[data-capital]", "Current"],
        ["[data-capital]", "Closed trades"],
        ["[data-comments-summary]", "Local notes"],
        ["[data-comments-list]", "<li>"],
        ["[data-process-console]", "<li>"]
    ].forEach(([selector, expected]) => assertIncludes(rendered, selector, expected));

    console.log("dashboard_acceptance=ok");
})().catch((error) => {
    console.error(error.message);
    process.exit(1);
});
