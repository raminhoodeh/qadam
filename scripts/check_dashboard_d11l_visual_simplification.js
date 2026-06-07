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
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-master-implementation-plan.md");
const auditPath = path.join(repoRoot, "docs", "qadam-dashboard-d11l-visual-simplification-2026-05-26.md");

const html = fs.readFileSync(htmlPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");
const renderer = fs.readFileSync(rendererPath, "utf8");
const plan = fs.readFileSync(planPath, "utf8");

function countOccurrences(text, needle) {
    return text.split(needle).length - 1;
}

function includesAll(text, needles, label) {
    needles.forEach((needle) => assert(text.includes(needle), `${label} missing ${needle}`));
}

function assertNoUnsafePublicText(text, label) {
    [
        "/Users/",
        "/private/",
        "/var/folders/",
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

async function main() {
    const marker = "/* D11L visual simplification contract. */";
    const markerIndex = css.indexOf(marker);
    assert(markerIndex >= 0, "D11L visual simplification contract missing");
    const d11lCss = css.slice(markerIndex);

    includesAll(html, [
        "/auth.css?v=20260607-cc5-contract-renderer",
        "/dashboard.js?v=20260607-cc5-contract-renderer"
    ], "D11L cache keys");

    includesAll(d11lCss, [
        "--surface-page:",
        "--surface-rail:",
        "--surface-section:",
        "--surface-panel:",
        "--surface-panel-quiet:",
        "--line-quiet:",
        "--shadow-quiet:",
        "body:has(.dashboard-shell)",
        "background: var(--surface-page);",
        ".cockpit-nav,\n.dashboard-safety-strip",
        "position: static;",
        "top: auto;",
        "background: var(--surface-rail);",
        ".mission-control-panel,\n.system-map-panel",
        "background: transparent;",
        "border-top: 1px solid var(--line-quiet);",
        ".overview-hero,\n.overview-review-card",
        ".trade-consolidated-snapshot",
        ".evidence-consolidated-readout",
        ".reasoning-consolidated-readout",
        ".operations-consolidated-readout",
        ".performance-workspace",
        ".paper-account-balance-card",
        ".paper-equity-chart-card",
        ".trade-review-group summary",
        ".evidence-review-group summary",
        ".reasoning-review-group summary",
        ".operations-review-group summary",
        ".metric",
        "min-height: 0;",
        ".panel-brief",
        ".performance-boundary-card"
    ], "D11L CSS");

    includesAll(d11lCss, [
        "html[data-dashboard-active-view=\"trades\"] .trade-intent-panel",
        "html[data-dashboard-active-view=\"trades\"] .capital-panel",
        "order: 1;",
        "order: 2;"
    ], "D11L trade-view visual order");

    assert(countOccurrences(d11lCss, "box-shadow: none;") >= 10, "D11L should flatten repeated dashboard shadows");
    assert(!d11lCss.includes("position: sticky"), "D11L should not add new sticky dashboard layers");
    assert(!d11lCss.includes("radial-gradient("), "D11L should not add decorative orb gradients");
    assert(!d11lCss.includes("font-size: 100vw"), "D11L should not use viewport-scaled typography");

    includesAll(plan, [
        "D11L - Visual Simplification",
        "docs/qadam-dashboard-d11l-visual-simplification-2026-05-26.md",
        "scripts/check_dashboard_d11l_visual_simplification.js",
        "D11M - Regression And Acceptance Tests"
    ], "D11L master plan");
    assert(fs.existsSync(auditPath), "D11L audit document missing");

    includesAll(renderer, [
        "model_contract_version: \"dashboard_view_models.cc5.founder_contract.v1\"",
        "renderDashboardSafetyStrip(status, viewModels)",
        "renderCapital(status, viewModels)"
    ], "D11L renderer authority continuity");

    const rendered = await renderWithStatus(status);
    [
        ["[data-dashboard-safety-strip]", "Safety locked: paper-only readout"],
        ["[data-dashboard-safety-strip]", "Paper-only readout · live capital off"],
        ["[data-overview-mission-brief]", "Mission Control brief"],
        ["[data-overview-strategy-narrative]", "What Qadam is choosing now"],
        ["[data-trade-layer]", "Consolidated trade readout"],
        ["[data-source-summary]", "Sources"],
        ["[data-cognition]", "Reasoning readout"],
        ["[data-flow-map]", "System map diagnostics"],
        ["[data-overview-mini-map]", "Closed-loop rule"],
        ["[data-capital]", "60-day paper growth"]
    ].forEach(([selector, expected]) => assertIncludes(rendered, selector, expected));

    assertNoUnsafePublicText(html, "D11L dashboard HTML");
    assertNoUnsafePublicText(css, "D11L dashboard CSS");

    console.log("dashboard_d11l_visual_simplification=ok");
    console.log("dashboard_d11l_primary_panels_flattened=True");
    console.log("dashboard_d11l_sticky_layers_removed=True");
    console.log("dashboard_d11l_cache_key=20260607-cc5-contract-renderer");
    console.log("dashboard_authority_unchanged=True");
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
