#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "..");

function read(relativePath) {
    return fs.readFileSync(path.join(repoRoot, relativePath), "utf8");
}

function assert(condition, message) {
    if (!condition) {
        throw new Error(message);
    }
}

function assertIncludes(text, needles, label) {
    needles.forEach((needle) => {
        assert(text.includes(needle), `${label} missing ${needle}`);
    });
}

const whitepaperHtml = read("landing-page-repo/whitepaper/index.html");
const guideHtml = read("landing-page-repo/guide/index.html");
const css = read("landing-page-repo/whitepaper.css");

assertIncludes(whitepaperHtml, [
    '<body class="qadam-whitepaper-page">',
    'qadam-whitepaper-header',
    'qadam-whitepaper-utility',
    'qadam-whitepaper-section-nav',
    'href="#experiment"',
    'href="#origin"',
    'href="#hypotheses"',
    'href="#team"',
    'href="#evidence"',
    'href="#method"',
    'href="#proof"',
    'href="#findings"',
    'href="#governance"',
    'href="#conclusion"',
    'qadam-whitepaper-shell',
    'qadam-whitepaper-hero',
    'qadam-whitepaper-hero-copy',
    'qadam-whitepaper-hero-facts',
    'qadam-whitepaper-article',
    '/whitepaper.css?v=20260721-final-ux-polish-v1',
    '<section id="experiment"',
    '<section id="origin"',
    '<section id="hypotheses"',
    '<section id="team"',
    '<section id="evidence"',
    '<section id="method"',
    '<section id="proof"',
    '<section id="findings"',
    '<section id="governance"',
    '<section id="conclusion"'
], "whitepaper html");

assertIncludes(whitepaperHtml, [
    "Can a small artificial hedge fund team",
    "The Qadam Experiment",
    "Why Qadam Exists",
    "Three Foundational Hypotheses",
    "Consumer AI execution",
    "Quantum pattern recognition",
    "Akber's investment filter",
    "not proven claims",
    "The Artificial Hedge Fund Team",
    "Gemma on Ramin's machine",
    "Google Gemini",
    "IBM Quantum",
    "The Evidence Universe",
    "The 10-Stage Experimental Method",
    "Observe the World",
    "Qualify the Evidence",
    "Discover Patterns",
    "Akber's 6-Stage Filter",
    "How Qadam Establishes Proof",
    "Current Findings",
    "US$100,000",
    "Alpaca Paper",
    "No edge, no trade",
    "No proof, no claim"
], "whitepaper canonical operating copy");

assert(!whitepaperHtml.includes("Account Sign In"), "whitepaper must not advertise account sign in");

assertIncludes(css, [
    "body.qadam-whitepaper-page",
    ".qadam-whitepaper-page .qadam-whitepaper-header",
    ".qadam-whitepaper-section-nav",
    ".qadam-whitepaper-page .qadam-whitepaper-shell",
    ".qadam-whitepaper-page .qadam-whitepaper-hero",
    ".qadam-whitepaper-hero-facts",
    ".qadam-whitepaper-page .qadam-whitepaper-article",
    ".qadam-whitepaper-page .guide-card span",
    ".qadam-whitepaper-page .guide-table strong",
    ".qadam-whitepaper-page .guide-table span",
    ".experiment-spine",
    ".hypothesis-card",
    ".team-table",
    ".evidence-universes",
    ".lifecycle-line",
    ".method-chapter",
    ".proof-steps",
    ".live-status-panel",
    ".success-grid",
    "@media (max-width: 800px)"
], "whitepaper css");

assertIncludes(css, [
    "position: static;",
    "scroll-margin-top: calc(64px + var(--qadam-space-4));",
    "scroll-margin-top: calc(52px + var(--qadam-space-4));"
], "whitepaper sticky navigation and anchor clearance");

assertIncludes(css, [
    ".qadam-whitepaper-page .guide-card {",
    "background: var(--qadam-color-canvas);",
    ".qadam-whitepaper-page .guide-table div {",
    "background: var(--qadam-color-surface);",
    "color: var(--qadam-color-muted);"
], "whitepaper light-theme card contrast");

assertIncludes(css, [
    ".qadam-whitepaper-page .qadam-whitepaper-article .team-system-note *",
    ".qadam-whitepaper-page .qadam-whitepaper-article .method-chapter > header *",
    ".qadam-whitepaper-page .qadam-whitepaper-article .live-status-panel *",
    "color: var(--qadam-color-inverse);"
], "whitepaper dark-panel text contrast");

[
    "--qadam-component-page-bg",
    "--qadam-component-header-bg",
    "--qadam-component-nav-bg",
    "--qadam-color-brand",
    "--qadam-color-section-band",
    "--qadam-font-display",
    "--qadam-layout-page",
    "--qadam-layout-gutter"
].forEach((token) => {
    assert(css.includes(token), `whitepaper redesign must use token ${token}`);
});

assert(!guideHtml.includes("qadam-whitepaper-page"), "guide must not opt into whitepaper page redesign");
assert(!guideHtml.includes("qadam-whitepaper-section-nav"), "guide must not render whitepaper section nav");

[
    /PVZ[0-9A-Za-z_-]{20,}/,
    /\d{6,}:[A-Za-z0-9_-]{20,}/,
    /OPENAI_API_KEY=/,
    /ANTHROPIC_API_KEY=/,
    /TELEGRAM_BOT_TOKEN=/
].forEach((pattern) => {
    assert(!pattern.test(whitepaperHtml), `whitepaper contains unsafe public text: ${pattern}`);
});

console.log("non_homepage_whitepaper_redesign=ok");
