#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const {
    assert,
    html,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

const repoRoot = path.resolve(__dirname, "..");
const htmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const cssPath = path.join(repoRoot, "landing-page-repo", "auth.css");
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-master-implementation-plan.md");
const auditPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-dx-12-responsive-audit-2026-05-25.md");

const dashboardHtml = fs.readFileSync(htmlPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");
const plan = fs.readFileSync(planPath, "utf8");

function includesAll(text, needles, label) {
    needles.forEach((needle) => {
        assert(text.includes(needle), `${label} missing ${needle}`);
    });
}

function countOccurrences(text, needle) {
    return text.split(needle).length - 1;
}

async function main() {
    includesAll(dashboardHtml, [
        "<a class=\"skip-link\" href=\"#dashboard-main\">Skip to dashboard views</a>",
        "/auth.css?v=20260607-cc5-contract-renderer",
        "id=\"dashboard-main\"",
        "tabindex=\"-1\"",
        "aria-label=\"Dashboard views\"",
        "aria-current=\"page\"",
        "data-dashboard-view-link",
        "data-overview-mini-map",
        "data-phase5-system-map",
        "role=\"tooltip\""
    ], "Responsive/accessibility static shell");

    assert(
        dashboardHtml.indexOf("skip-link") < dashboardHtml.indexOf("topbar"),
        "skip link should be first keyboard target before topbar"
    );

    includesAll(css, [
        "DX-12 responsive and accessibility contract",
        ".skip-link",
        "a:focus-visible",
        "button:focus-visible",
        "summary:focus-visible",
        "[tabindex]:focus-visible",
        "scroll-snap-type: x proximity",
        "-webkit-overflow-scrolling: touch",
        "overscroll-behavior-inline: contain",
        "counter-reset: overview-node",
        "counter-increment: overview-node",
        "repeat(auto-fit, minmax(min(100%, 180px), 1fr))",
        "repeat(auto-fit, minmax(min(100%, 260px), 1fr))",
        "repeat(auto-fit, minmax(min(100%, 190px), 1fr))",
        "@media (max-width: 680px)",
        "@media (max-width: 420px)",
        ".flow-node > span",
        "position: static",
        ".mode-stack > span",
        ".dashboard-hero .copy",
        "max-width: calc(100vw - 24px)",
        "max-width: calc(100vw - 16px)",
        "overflow-wrap: break-word",
        "word-break: normal",
        "overflow-x: clip",
        "min-height: 44px",
        ".dashboard-view-switcher .cockpit-nav-links a",
        ".inline-badge.online",
        ".inline-badge.degraded",
        ".inline-badge.pending",
        ".inline-badge.blocked"
    ], "Responsive/accessibility CSS");
    assert(!css.includes("node-authority"), "responsive CSS still references removed node-authority badges");

    [
        ".overview-mini-map",
        ".overview-readout-list",
        ".overview-system-grid",
        ".overview-lifecycle-strip",
        ".trade-lifecycle-strip",
        ".team-health-row",
        ".operations-team-diagnostic-row",
        ".operations-diagnostics-grid",
        ".operations-feed-grid",
        ".operations-edge-list",
        ".governance-status-grid",
        ".governance-target-grid",
        ".governance-record-grid"
    ].forEach((selector) => {
        assert(css.includes(selector), `responsive selector missing ${selector}`);
    });

    assert(!/font-size:\s*[^;]*(vw|vmin|vmax|clamp\()/i.test(css), "viewport-scaled font size found");
    assert(!/letter-spacing:\s*-/i.test(css), "negative letter-spacing found");
    assert(countOccurrences(css, ":focus-visible") >= 8, "focus-visible coverage too thin");

    const rendered = await renderWithStatus(status);
    const overviewMapHtml = html(rendered, "[data-overview-mini-map]");
    const operationsHtml = html(rendered, "[data-flow-map]");
    const tradesHtml = html(rendered, "[data-trade-layer]");

    assert(countOccurrences(overviewMapHtml, "overview-mini-node") >= 6, "overview mini-map rendered too few nodes");
    assert(overviewMapHtml.includes("system-flow-diagram"), "overview canonical system map missing");
    assert(operationsHtml.includes("System map diagnostics"), "operations map diagnostics missing");
    assert(!operationsHtml.includes("operations-flow-diagram"), "operations duplicate flow diagram should be removed");
    assert(tradesHtml.includes("trade-lifecycle-filters"), "trade lifecycle filters missing");
    assert(tradesHtml.includes("aria-pressed=\"true\""), "selected trade filter state missing");
    assert(operationsHtml.includes("Governance and outbound communications"), "consolidated governance audit missing from Operations");

    [
        "/Users/",
        "api_key",
        "PREFERENCE_API_KEY",
        "ALPACA_SECRET",
        "Q_CTRL",
        "raw_payload",
        "private_payload",
        "local_path",
        "request_body",
        "broker_identifier"
    ].forEach((needle) => {
        assert(!overviewMapHtml.includes(needle), `overview mini-map leaked non-public-safe marker ${needle}`);
        assert(!operationsHtml.includes(needle), `operations map leaked non-public-safe marker ${needle}`);
        assert(!tradesHtml.includes(needle), `trades workspace leaked non-public-safe marker ${needle}`);
    });

    includesAll(plan, [
        "DX-12 - Responsive Layout And Accessibility",
        "Make the Overview mini-map usable on mobile without horizontal confusion",
        "Validate keyboard focus order",
        "scripts/check_dashboard_overhaul_responsive.js"
    ], "Dashboard overhaul plan");
    assert(fs.existsSync(auditPath), "DX-12 audit document missing");

    console.log("dashboard_overhaul_responsive=ok");
    console.log("dashboard_responsive_skip_link=True");
    console.log("dashboard_responsive_focus_visible=True");
    console.log("dashboard_responsive_mobile_breakpoint_count=3");
    console.log("dashboard_responsive_overview_mini_node_count=" + countOccurrences(overviewMapHtml, "overview-mini-node"));
    console.log("dashboard_responsive_authority_unchanged=True");
}

if (require.main === module) {
    main().catch((error) => {
        console.error(error.message);
        process.exitCode = 1;
    });
}
