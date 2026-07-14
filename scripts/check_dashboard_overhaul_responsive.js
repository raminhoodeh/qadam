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
const patternCssPath = path.join(repoRoot, "landing-page-repo", "quantum-edge-wave-f.css");
const releaseManifestPath = path.join(repoRoot, "landing-page-repo", "status", "dashboard-release.json");
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-master-implementation-plan.md");
const auditPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-dx-12-responsive-audit-2026-05-25.md");

const dashboardHtml = fs.readFileSync(htmlPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");
const patternCss = fs.readFileSync(patternCssPath, "utf8");
const releaseManifest = JSON.parse(fs.readFileSync(releaseManifestPath, "utf8"));
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
        releaseManifest.css_asset,
        "id=\"dashboard-main\"",
        "tabindex=\"-1\"",
        "data-overview-control-plane",
        "Control Plane",
        "role=\"tooltip\""
    ], "Responsive/accessibility static shell");
    [
        "dashboard-view-switcher",
        "data-dashboard-view-link",
        "aria-label=\"Dashboard views\"",
        "Hide diagnostics"
    ].forEach((needle) => {
        assert(!dashboardHtml.includes(needle), `removed dashboard navigation/control returned: ${needle}`);
    });

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
        ".control-plane-grid",
        ".overview-operating-flow-head",
        ".overview-operating-node-grid",
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
    assert(
        css.includes(".control-plane-grid {\n    grid-template-columns: 1fr;"),
        "Control Plane must render as a full-width section"
    );
    assert(
        css.includes(".overview-operating-node-grid {\n    align-items: start;\n    grid-template-columns: repeat(2, minmax(0, 1fr));"),
        "operating team nodes must use two broad columns on desktop"
    );
    assert(
        css.includes(".overview-operating-node-grid {\n        grid-template-columns: 1fr;"),
        "operating team nodes must collapse to one column on narrower screens"
    );

    assert(
        !/font-size:\s*[^;]*(vw|vmin|vmax|clamp\()/i.test(patternCss),
        "Pattern Recognition introduced viewport-scaled font size"
    );
    assert(
        !/letter-spacing:\s*-/i.test(patternCss),
        "Pattern Recognition introduced negative letter-spacing"
    );
    assert(countOccurrences(css, ":focus-visible") >= 8, "focus-visible coverage too thin");

    const rendered = await renderWithStatus(status);
    const controlPlaneHtml = html(rendered, "[data-overview-control-plane]");
    const operationsHtml = html(rendered, "[data-flow-map]");
    const tradesHtml = html(rendered, "[data-trade-layer]");

    assert(countOccurrences(controlPlaneHtml, "overview-mini-node") >= 6, "Control Plane rendered too few nodes");
    assert(controlPlaneHtml.includes("system-flow-diagram"), "Control Plane canonical system map missing");
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
        assert(!controlPlaneHtml.includes(needle), `Control Plane leaked non-public-safe marker ${needle}`);
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
    console.log("dashboard_responsive_control_plane_node_count=" + countOccurrences(controlPlaneHtml, "overview-mini-node"));
    console.log("dashboard_responsive_authority_unchanged=True");
}

if (require.main === module) {
    main().catch((error) => {
        console.error(error.message);
        process.exitCode = 1;
    });
}
