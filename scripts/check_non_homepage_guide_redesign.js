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

const guideHtml = read("landing-page-repo/guide/index.html");
const whitepaperHtml = read("landing-page-repo/whitepaper/index.html");
const css = read("landing-page-repo/whitepaper.css");
const authJs = read("landing-page-repo/auth.js");

assertIncludes(guideHtml, [
    '<body class="qadam-guide-page">',
    'qadam-guide-header',
    'qadam-guide-utility',
    'qadam-guide-shell',
    'hidden" data-dashboard',
    'qadam-guide-section-nav',
    'href="#current-hypotheses"',
    'href="#guide-start"',
    'href="#guide-dashboard"',
    'href="#guide-states"',
    'href="#guide-routine"',
    'href="#guide-boundaries"',
    'qadam-guide-hero',
    'qadam-guide-hero-copy',
    'qadam-guide-hero-facts',
    'qadam-guide-article',
    'id="current-hypotheses"',
    'id="guide-start"',
    'id="guide-dashboard"',
    'id="guide-states"',
    'id="guide-routine"',
    'id="guide-boundaries"',
    'data-user-email',
    'data-signout',
    '<script src="/auth.js?v=20260517-guide"></script>'
], "guide html");

assertIncludes(css, [
    "body.qadam-guide-page",
    ".qadam-guide-page .hidden",
    ".qadam-guide-page .qadam-guide-header",
    ".qadam-guide-page .qadam-guide-utility",
    ".qadam-guide-page .qadam-guide-shell",
    ".qadam-guide-section-nav",
    ".qadam-guide-page .qadam-guide-hero",
    ".qadam-guide-hero-facts",
    ".qadam-guide-page .qadam-guide-article",
    ".qadam-guide-page .guide-card",
    ".qadam-guide-page .guide-table div",
    ".qadam-guide-page .manual-cta",
    "@media (max-width: 800px)"
], "guide css");

[
    "--qadam-component-page-bg",
    "--qadam-component-header-bg",
    "--qadam-component-nav-bg",
    "--qadam-color-brand",
    "--qadam-color-info-soft",
    "--qadam-font-display",
    "--qadam-layout-page",
    "--qadam-layout-gutter"
].forEach((token) => {
    assert(css.includes(token), `guide redesign must use token ${token}`);
});

assertIncludes(authJs, [
    'const dashboard = document.querySelector("[data-dashboard]");',
    'dashboard.classList.remove("hidden");',
    'window.location.replace(`/login/?next=${encodeURIComponent(currentPath)}`);',
    'emailIsAllowed(session.user.email)'
], "auth js");

assert(!whitepaperHtml.includes("qadam-guide-page"), "whitepaper must not opt into guide redesign");
assert(!whitepaperHtml.includes("qadam-guide-section-nav"), "whitepaper must not render guide section nav");
assertIncludes(guideHtml, [
    "Three Current Hypotheses",
    "Consumer AI execution",
    "Quantum pattern recognition",
    "Akber's investment filter",
    "not proven claims",
    "Public read-only access",
    "Protected member features",
    "The Current 13 Dashboard Routes",
    "The Canonical Ten-Stage Lifecycle",
    "Outbound explanation",
    "Inbound research intake"
], "guide canonical operating copy");

[
    /PVZ[0-9A-Za-z_-]{20,}/,
    /\d{6,}:[A-Za-z0-9_-]{20,}/,
    /OPENAI_API_KEY=/,
    /ANTHROPIC_API_KEY=/,
    /TELEGRAM_BOT_TOKEN=/
].forEach((pattern) => {
    assert(!pattern.test(guideHtml), `guide contains unsafe public text: ${pattern}`);
});

console.log("non_homepage_guide_redesign=ok");
