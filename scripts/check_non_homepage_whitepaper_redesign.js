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
    '<section id="short-version">',
    '<section id="qsase">',
    '<section id="operating-map">',
    '<section id="trading-universe">',
    '<section id="sources">'
], "whitepaper html");

assertIncludes(whitepaperHtml, [
    "Qadam Self-Aware Strategy Engine",
    "QSASE",
    "Universal source-price matrix",
    "Pattern labs",
    "Strategy Foundry",
    "Router and PaperOps",
    "Learning ledger",
    "portfolio value first",
    "QSASE dashboard"
], "whitepaper QSASE copy");

assertIncludes(css, [
    "body.qadam-whitepaper-page",
    ".qadam-whitepaper-page .qadam-whitepaper-header",
    ".qadam-whitepaper-section-nav",
    ".qadam-whitepaper-page .qadam-whitepaper-shell",
    ".qadam-whitepaper-page .qadam-whitepaper-hero",
    ".qadam-whitepaper-hero-facts",
    ".qadam-whitepaper-page .qadam-whitepaper-article",
    ".qadam-whitepaper-page .system-diagram",
    ".qadam-whitepaper-page .flow-card",
    "@media (max-width: 800px)"
], "whitepaper css");

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
