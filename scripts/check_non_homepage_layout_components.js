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

const layoutCss = read("landing-page-repo/non-homepage-layout.css");
const authCss = read("landing-page-repo/auth.css");
const whitepaperCss = read("landing-page-repo/whitepaper.css");
const homeHtml = read("landing-page-repo/index.html");
const homeCss = read("landing-page-repo/style.css");

[
    "@layer qadam-nonhomepage-layout",
    ".auth-shell",
    ".dashboard-shell",
    ".page-shell",
    ".site-header",
    ".topbar",
    ".nav-actions",
    ".nav-links",
    ".button",
    ".nav-link",
    ".hero",
    ".dashboard-hero",
    ".article > section",
    ".panel",
    ".card",
    ".guide-card",
    ".system-diagram",
    ".guide-grid",
    ".guide-table",
    ".qadam-layout-shell",
    ".qadam-layout-header",
    ".qadam-layout-hero",
    ".qadam-card",
    ".qadam-card-grid",
    ".qadam-definition-list",
    ".qadam-section-band",
    ".qadam-layout-footer"
].forEach((needle) => {
    assert(layoutCss.includes(needle), `layout component missing ${needle}`);
});

[
    "--qadam-layout-readable",
    "--qadam-layout-page",
    "--qadam-layout-gutter",
    "--qadam-section-gap",
    "--qadam-touch-target",
    "--qadam-component-card-bg",
    "--qadam-component-nav-bg"
].forEach((token) => {
    assert(layoutCss.includes(token), `layout layer must use token ${token}`);
});

const expectedPrelude = [
    '@import url("/non-homepage-tokens.css?v=20260628-stage1");',
    '@import url("/non-homepage-layout.css?v=20260628-stage2");'
].join("\n");

assert(authCss.startsWith(expectedPrelude), "auth.css must import tokens then layout before all rules");
assert(whitepaperCss.startsWith(expectedPrelude), "whitepaper.css must import tokens then layout before all rules");

[
    "landing-page-repo/login/index.html",
    "landing-page-repo/sign-up/index.html",
    "landing-page-repo/dashboard/index.html",
    "landing-page-repo/whitepaper/index.html",
    "landing-page-repo/guide/index.html"
].forEach((relativePath) => {
    const html = read(relativePath);
    const usesKnownLayout =
        html.includes("auth-shell") ||
        html.includes("dashboard-shell") ||
        html.includes("page-shell");
    assert(usesKnownLayout, `${relativePath} must use a shared shell class`);
});

assert(!homeHtml.includes("non-homepage-layout.css"), "homepage HTML must not import non-homepage layout");
assert(!homeCss.includes("non-homepage-layout.css"), "homepage CSS must not import non-homepage layout");
assert(!homeCss.includes("qadam-nonhomepage-layout"), "homepage CSS must not define non-homepage layout layer");

console.log("non_homepage_layout_components=ok");
