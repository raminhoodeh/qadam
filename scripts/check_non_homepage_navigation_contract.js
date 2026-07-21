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

function includesAll(text, needles, label) {
    needles.forEach((needle) => {
        assert(text.includes(needle), `${label} missing ${needle}`);
    });
}

function excludesAll(text, needles, label) {
    needles.forEach((needle) => {
        assert(!text.includes(needle), `${label} should not include ${needle}`);
    });
}

function navItems(html) {
    return Array.from(html.matchAll(/\bdata-qadam-nav-item="([^"]+)"/g)).map((match) => match[1]);
}

function assertNavItems(html, expected, label) {
    const actual = navItems(html);
    expected.forEach((item) => {
        assert(actual.includes(item), `${label} missing nav item ${item}`);
    });
}

const pages = {
    login: read("landing-page-repo/login/index.html"),
    signup: read("landing-page-repo/sign-up/index.html"),
    whitepaper: read("landing-page-repo/whitepaper/index.html"),
    guide: read("landing-page-repo/guide/index.html"),
    dashboard: read("landing-page-repo/dashboard/index.html")
};
const layoutCss = read("landing-page-repo/non-homepage-layout.css");
const authCss = read("landing-page-repo/auth.css");
const whitepaperCss = read("landing-page-repo/whitepaper.css");
const homeHtml = read("landing-page-repo/index.html");
const homeCss = read("landing-page-repo/style.css");

Object.entries(pages).forEach(([name, html]) => {
    includesAll(html, [
        "data-qadam-global-nav",
        "data-qadam-nav-context=",
        "data-qadam-nav-item="
    ], `${name} global nav`);
});

[
    ["login", "public-auth", ["dashboard", "whitepaper", "account", "home"]],
    ["signup", "public-auth", ["dashboard", "whitepaper", "home"]],
    ["whitepaper", "public-doc", ["dashboard", "guide", "whitepaper"]],
    ["guide", "protected-doc", ["dashboard", "guide", "whitepaper"]],
    ["dashboard", "public-dashboard", ["dashboard", "guide", "whitepaper"]]
].forEach(([name, context, expectedItems]) => {
    const html = pages[name];
    assert(html.includes(`data-qadam-nav-context="${context}"`), `${name} nav context mismatch`);
    assertNavItems(html, expectedItems, name);
});

includesAll(pages.whitepaper, [
    'data-qadam-nav-item="whitepaper" aria-current="page"',
    'data-qadam-section-nav="whitepaper"',
    'qadam-whitepaper-section-nav qadam-section-nav qadam-layout-nav-bar'
], "whitepaper nav contract");

excludesAll(`${pages.signup}\n${pages.whitepaper}`, [
    "Account Sign In"
], "public sign-in discovery");

includesAll(pages.guide, [
    'data-qadam-nav-item="guide" aria-current="page"',
    'data-qadam-section-nav="guide"',
    'qadam-guide-section-nav qadam-section-nav qadam-layout-nav-bar',
    'hidden" data-dashboard'
], "guide nav contract");

includesAll(pages.dashboard, [
    'data-qadam-nav-item="dashboard" aria-current="page"',
    'data-stage7-dashboard-visibility',
    'hidden" data-dashboard'
], "dashboard nav contract");

excludesAll(pages.dashboard, [
    'data-qadam-section-nav="dashboard"',
    'data-qadam-dashboard-section-nav',
    'data-dashboard-debug-toggle',
    'data-dashboard-advanced-links',
    'data-dashboard-view-link',
    'data-dashboard-view-target="overview"',
    'data-dashboard-view-target="trades"',
    'data-dashboard-view-target="evidence"',
    'data-dashboard-view-target="reasoning"',
    'data-dashboard-view-target="operations"'
], "dashboard removed section nav contract");

excludesAll(`${pages.login}\n${pages.signup}\n${pages.whitepaper}\n${pages.guide}\n${pages.dashboard}`, [
    "data-signout"
], "public pages");

includesAll(layoutCss, [
    ".qadam-global-nav",
    ".qadam-nav-link",
    ".qadam-nav-link[aria-current=\"page\"]",
    ".qadam-nav-button",
    ".qadam-section-nav",
    ".qadam-section-nav a",
    "--qadam-touch-target",
    "--qadam-component-link"
], "shared navigation layout");

includesAll(`${authCss}\n${whitepaperCss}`, [
    "@import url(\"/non-homepage-layout.css?v=20260628-stage2\");"
], "non-homepage css imports");

excludesAll(`${homeHtml}\n${homeCss}`, [
    "data-qadam-global-nav",
    "qadam-global-nav",
    "qadam-section-nav",
    "data-qadam-nav-item"
], "homepage");

console.log("non_homepage_navigation_contract=ok");
