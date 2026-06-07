#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "..");
const htmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const cssPath = path.join(repoRoot, "landing-page-repo", "auth.css");
const jsPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-consolidation-cut-implementation-plan-2026-06-05.md");

const html = fs.readFileSync(htmlPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");
const js = fs.readFileSync(jsPath, "utf8");
const plan = fs.readFileSync(planPath, "utf8");

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

function includesAll(text, needles, label) {
    needles.forEach((needle) => {
        assert(text.includes(needle), `${label} missing ${needle}`);
    });
}

includesAll(html, [
    "/auth.css?v=20260607-cc9-copy-runthrough",
    "/dashboard.js?v=20260607-cc9-copy-runthrough",
    "<a class=\"skip-link\" href=\"#dashboard-main\">Skip to dashboard views</a>",
    "aria-current=\"page\"",
    "aria-controls=\"dashboard-debug-tabs\"",
    "id=\"dashboard-debug-tabs\"",
    "role=\"region\"",
    "aria-label=\"Diagnostics navigation\""
], "CC7 dashboard shell");

assert(!css.includes("var(--mono)"), "CC7 CSS must use --font-mono, not --mono");
assert(!css.includes("var(--font)"), "CC7 CSS must use --font-sans, not --font");
includesAll(css, [
    "CC7 visual system, responsive, and accessibility hardening",
    "--section-gap: 22px",
    "--section-pad: 22px",
    "@media (prefers-reduced-motion: reduce)",
    ".paper-equity-line",
    ".trade-toast-token",
    "@media (max-width: 480px)",
    ".dashboard-view-switcher .cockpit-nav-links",
    "grid-template-columns: 1fr",
    "overflow-wrap: anywhere",
    "touch-action: manipulation",
    ".overview-mini-node > summary::after",
    ".overview-expandable-ledger > summary::after"
], "CC7 CSS contract");

includesAll(js, [
    "Hide diagnostics navigation",
    "Show diagnostics navigation",
    "Diagnostics navigation",
    "\"ArrowLeft\"",
    "\"ArrowRight\"",
    "\"Home\"",
    "\"End\"",
    "event?.key !== \"Escape\"",
    "aria-describedby",
    "role=\"group\""
], "CC7 JS contract");

includesAll(plan, [
    "CC7",
    "Visual system, responsive, a11y",
    "Reuse `auth.css` tokens only",
    "single-column phone layout",
    "drawer is keyboard-operable"
], "CC7 plan contract");

assert(!/font-size:\s*[^;]*(vw|vmin|vmax|clamp\()/i.test(css), "CC7 should not introduce viewport-scaled font sizes");
assert(!/letter-spacing:\s*-/i.test(css), "CC7 should not introduce negative letter spacing");

console.log("dashboard_cc7_visual_a11y=ok");
console.log("dashboard_cc7_cache_key=20260607-cc9-copy-runthrough");
console.log("dashboard_cc7_phone_single_column=True");
console.log("dashboard_cc7_keyboard_drawer=True");
