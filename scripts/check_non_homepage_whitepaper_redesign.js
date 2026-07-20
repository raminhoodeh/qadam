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
    'href="#current-hypotheses"',
    'href="#short-version"',
    'href="#qsase"',
    'href="#operating-map"',
    'href="#trading-universe"',
    'href="#sources"',
    'qadam-whitepaper-shell',
    'qadam-whitepaper-hero',
    'qadam-whitepaper-hero-copy',
    'qadam-whitepaper-hero-facts',
    'qadam-whitepaper-article',
    '/whitepaper.css?v=20260720-mobile-contrast-v1',
    '<section id="current-hypotheses"',
    '<section id="short-version">',
    '<section id="qsase">',
    '<section id="operating-map">',
    '<section id="trading-universe">',
    '<section id="sources">'
], "whitepaper html");

assertIncludes(whitepaperHtml, [
    "Qadam Self-Aware Strategy Engine",
    "Three Current Hypotheses",
    "Consumer AI execution",
    "Quantum pattern recognition",
    "Akber's investment filter",
    "not proven claims",
    "QSASE",
    "The Canonical 10-Stage Lifecycle",
    "Observe the World",
    "Qualify the Evidence",
    "Discover Patterns",
    "Akber's 6-Stage Filter",
    "Current operating snapshot",
    "US$100,000",
    "Quantum Edge",
    "Alpaca Paper",
    "read-only projection"
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
    ".qadam-whitepaper-page .system-diagram",
    ".qadam-whitepaper-page .flow-card",
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
