#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const {
    assert,
    assertIncludes,
    html: renderedHtml,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

const repoRoot = path.resolve(__dirname, "..");
const dashboardHtmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const cssPath = path.join(repoRoot, "landing-page-repo", "auth.css");
const rendererPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");
const preflightPath = path.join(repoRoot, "scripts", "preflight_dashboard_deployment.sh");
const acceptancePath = path.join(repoRoot, "scripts", "check_dashboard_acceptance.js");
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-master-implementation-plan.md");
const auditPath = path.join(repoRoot, "docs", "qadam-dashboard-d11m-regression-and-acceptance-tests-2026-05-26.md");

const dashboardHtml = fs.readFileSync(dashboardHtmlPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");
const renderer = fs.readFileSync(rendererPath, "utf8");
const preflight = fs.readFileSync(preflightPath, "utf8");
const acceptance = fs.readFileSync(acceptancePath, "utf8");
const plan = fs.readFileSync(planPath, "utf8");

function includesAll(text, needles, label) {
    needles.forEach((needle) => assert(text.includes(needle), `${label} missing ${needle}`));
}

function countOccurrences(text, needle) {
    return text.split(needle).length - 1;
}

function assertNoUnsafePublicText(text, label) {
    [
        "/Users/",
        "/private/",
        "/var/folders/",
        "\\Users\\",
        "ALPACA_SECRET",
        "PREFERENCE_API_KEY",
        "Q_CTRL",
        "TELEGRAM_BOT_TOKEN",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "private_payload",
        "local_path",
        "request_body",
        "broker_identifier"
    ].forEach((needle) => {
        assert(!text.includes(needle), `${label} contains unsafe public marker ${needle}`);
    });
}

function assertNoSecretMaterial(text, label) {
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
        /SUPABASE_SECRET_KEY=/,
        /GEMINI_API_KEY=/,
        /ANTHROPIC_API_KEY=/,
        /OPENAI_API_KEY=/
    ].forEach((pattern) => {
        assert(!pattern.test(text), `${label} contains secret-like material: ${pattern}`);
    });
}

function assertCanonicalViewNav() {
    const viewsBlock = renderer.match(/const DASHBOARD_VIEWS = \[([\s\S]*?)\];/)?.[1] || "";
    const linkMatches = [...viewsBlock.matchAll(/\{\s*id:\s*"([^"]+)",\s*label:\s*"[^"]+"\s*\}/g)].map((match) => match[1]);
    const expectedViews = ["overview", "trades", "evidence", "reasoning", "operations"];
    assert(
        JSON.stringify(linkMatches) === JSON.stringify(expectedViews),
        `dashboard view nav mismatch: ${JSON.stringify(linkMatches)}`
    );
    expectedViews.forEach((view) => {
        assert(
            dashboardHtml.includes(`data-dashboard-view-section="${view}"`),
            `dashboard missing section for view ${view}`
        );
    });
    includesAll(renderer, [
        "DASHBOARD_VIEWS",
        "DASHBOARD_ADVANCED_DEBUG_KEY",
        "data-dashboard-debug-toggle",
        "data-dashboard-advanced-links",
        "function setDashboardDebugMode",
        "window.setQadamDashboardDebugMode",
        "dashboardDebugModeEnabled"
    ], "advanced debug renderer");
    assert(!dashboardHtml.includes("data-dashboard-view-target=\"performance\""), "performance must remain consolidated into Trades");
    assert(!dashboardHtml.includes("data-dashboard-view-target=\"sources\""), "sources must remain consolidated into Evidence");
}

function assertSafetyStripIsSingleGlobalAuthority() {
    assert(
        countOccurrences(dashboardHtml, "data-dashboard-safety-strip") === 1,
        "dashboard must expose exactly one global safety strip"
    );
    includesAll(dashboardHtml, [
        "Paper trading authorized",
        "Paper-only readout · live capital off",
        "Dashboard cannot place orders; model outputs cannot bypass risk checks",
        "One place for paper mode, capital, and order authority"
    ], "single safety strip static shell");
    assert(!dashboardHtml.includes("<dt>Limits</dt>"), "static shell still contains Limits rows");
    assert(!dashboardHtml.includes("<dt>Boundary</dt>"), "static shell still contains Boundary rows");
    assert(!dashboardHtml.includes("node-authority"), "static shell still contains node-authority badges");
    includesAll(renderer, [
        "renderDashboardSafetyStrip(status, viewModels)",
        "const modeLabel = status.mode === \"paper\"",
        "? \"OK - paper only\"",
        "mode_label: modeLabel",
        "safety_label:",
        "Dashboard cannot place orders; model outputs cannot bypass risk checks"
    ], "single safety strip renderer");
}

function assertNoObsoleteComplexity() {
    [
        "data-density-toggle",
        "data-density-option",
        "DASHBOARD_DENSITY_KEY",
        "window.setDashboardDensity",
        "html[data-dashboard-density=\"terminal\"]",
        "Executive View",
        "Terminal View"
    ].forEach((needle) => {
        assert(!`${dashboardHtml}\n${css}\n${renderer}`.includes(needle), `obsolete dashboard artifact remained: ${needle}`);
    });
}

function assertPlanAndOrchestration() {
    includesAll(plan, [
        "D11M - Regression And Acceptance Tests",
        "docs/qadam-dashboard-d11m-regression-and-acceptance-tests-2026-05-26.md",
        "scripts/check_dashboard_d11m_regression_acceptance.js",
        "D11N - Documentation And Guide Alignment",
        "D11O - Deployment Discipline",
        "D11P - Performance View Consolidation"
    ], "D11M master plan");
    includesAll(preflight, [
        "node scripts/check_dashboard_d11l_visual_simplification.js",
        "node scripts/check_dashboard_d11m_regression_acceptance.js",
        "docs/qadam-dashboard-d11m-regression-and-acceptance-tests-2026-05-26.md",
        "scripts/check_dashboard_d11m_regression_acceptance.js"
    ], "D11M preflight wiring");
    assert(
        acceptance.includes("\"scripts/check_dashboard_d11m_regression_acceptance.js\""),
        "dashboard acceptance missing D11M dependency"
    );
    assert(fs.existsSync(auditPath), "D11M audit document missing");
}

async function assertRenderedDashboardContract() {
    const rendered = await renderWithStatus(status);

    assert(
        rendered.document.documentElement.dataset.dashboardStatus === "rendered",
        "D11M expected rendered dashboard status"
    );
    assert(
        rendered.document.documentElement.dataset.dashboardStatusSource === "live_bridge",
        "D11M expected live bridge source preference"
    );

    [
        ["[data-dashboard-safety-strip]", "Paper trading authorized"],
        ["[data-dashboard-safety-strip]", "Paper-only readout · live capital off"],
        ["[data-dashboard-safety-strip]", "Dashboard cannot place orders; model outputs cannot bypass risk checks"],
        ["[data-stage7-dashboard-visibility]", "Paper Fund Status"],
        ["[data-stage7-dashboard-visibility]", "Source Intelligence Network"],
        ["[data-stage7-dashboard-visibility]", "Watched Markets Universe"],
        ["[data-stage7-dashboard-visibility]", "Strategy Playbook"],
        ["[data-stage7-dashboard-visibility]", "Hedge Fund Investment Team"],
        ["[data-stage7-dashboard-visibility]", "Hypotheses &amp; Pattern Recognition"],
        ["[data-stage7-dashboard-visibility]", "Backtesting &amp; Learning Loop"],
        ["[data-balance-ticker]", "Paper balance"],
        ["[data-trade-toast-rail]", "crude oil"],
        ["[data-overview-mission-brief]", "Mission Snapshot"],
        ["[data-overview-strategy-narrative]", "Strategy Universe"],
        ["[data-overview-strategy-narrative]", "What Qadam is choosing now"],
        ["[data-overview-control-plane]", "Control Plane"],
        ["[data-trade-layer]", "Trade lifecycle board"],
        ["[data-trade-layer]", "Consolidated trade readout"],
        ["[data-trade-layer]", "Paper trade lifecycle"],
        ["[data-trade-layer]", "Gate chain and broker readiness"],
        ["[data-trade-layer]", "Signals, trade ideas, and paper trades"],
        ["[data-capital]", "60-day paper growth"],
        ["[data-capital]", "Paper trading account"],
        ["[data-capital]", "Verified paper trades"],
        ["[data-sources-workspace-slot]", "Evidence workspace"],
        ["[data-source-summary]", "Sources"],
        ["[data-watching-list]", "pipeline-row"],
        ["[data-cognition]", "Reasoning readout"],
        ["[data-cognition]", "Hypotheses and evidence"],
        ["[data-cognition]", "Prior is not evidence"],
        ["[data-cognition]", "private priors"],
        ["[data-flow-map]", "Operations diagnostics and event trail"],
        ["[data-flow-map]", "System map diagnostics"],
        ["[data-overview-control-plane]", "Closed-loop rule"],
        ["[data-flow-map]", "Governance, inbox, and communications audit"],
        ["[data-flow-map]", "Process console"]
    ].forEach(([selector, expected]) => assertIncludes(rendered, selector, expected));

    const publicRendered = [
        "[data-dashboard-safety-strip]",
        "[data-balance-ticker]",
        "[data-trade-toast-rail]",
        "[data-overview-mission-brief]",
        "[data-overview-strategy-narrative]",
        "[data-overview-control-plane]",
        "[data-trade-layer]",
        "[data-capital]",
        "[data-sources-workspace-slot]",
        "[data-source-summary]",
        "[data-watching-list]",
        "[data-cognition]",
        "[data-flow-map]",
        "[data-overview-control-plane]"
    ].map((selector) => renderedHtml(rendered, selector)).join("\n");

    assertNoUnsafePublicText(publicRendered, "D11M rendered dashboard output");
}

async function main() {
    includesAll(dashboardHtml, [
        "/auth.css?v=20260619-hypotheses-patterns",
        "/dashboard.js?v=20260619-hypotheses-patterns"
    ], "D11M cache-key continuity");

    assertCanonicalViewNav();
    assertSafetyStripIsSingleGlobalAuthority();
    assertNoObsoleteComplexity();
    assertPlanAndOrchestration();
    assertNoUnsafePublicText(dashboardHtml, "D11M dashboard HTML");
    assertNoUnsafePublicText(css, "D11M dashboard CSS");
    assertNoSecretMaterial(renderer, "D11M dashboard renderer");
    await assertRenderedDashboardContract();

    console.log("dashboard_d11m_regression_acceptance=ok");
    console.log("dashboard_d11m_views=overview,trades,evidence,reasoning,operations");
    console.log("dashboard_d11m_primary_views_visible=True");
    console.log("dashboard_d11m_diagnostics_toggle=True");
    console.log("dashboard_d11m_single_safety_strip=True");
    console.log("dashboard_d11m_authority_unchanged=True");
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
