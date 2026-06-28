#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "..");
const landingRoot = path.join(repoRoot, "landing-page-repo");

function read(relativePath) {
    return fs.readFileSync(path.join(repoRoot, relativePath), "utf8");
}

function assert(condition, message) {
    if (!condition) {
        throw new Error(message);
    }
}

const tokenPath = "landing-page-repo/non-homepage-tokens.css";
const tokenCss = read(tokenPath);
const authCss = read("landing-page-repo/auth.css");
const whitepaperCss = read("landing-page-repo/whitepaper.css");
const homeHtml = read("landing-page-repo/index.html");
const homeCss = read("landing-page-repo/style.css");

[
    "--qadam-token-version",
    "--qadam-color-page",
    "--qadam-color-canvas",
    "--qadam-color-brand",
    "--qadam-color-section-band",
    "--qadam-color-footer",
    "--qadam-font-ui",
    "--qadam-font-display",
    "--qadam-font-mono",
    "--qadam-layout-page",
    "--qadam-component-nav-bg",
    "--qadam-component-button-bg"
].forEach((token) => {
    assert(tokenCss.includes(token), `missing design token ${token}`);
});

assert(
    authCss.startsWith('@import url("/non-homepage-tokens.css?v=20260628-stage1");'),
    "auth.css must import non-homepage tokens before all rules"
);
assert(
    whitepaperCss.startsWith('@import url("/non-homepage-tokens.css?v=20260628-stage1");'),
    "whitepaper.css must import non-homepage tokens before all rules"
);

[
    "--qadam-active-token-layer",
    "--institutional-page",
    "--institutional-canvas",
    "--institutional-brand",
    "--institutional-band",
    "--institutional-footer"
].forEach((alias) => {
    assert(authCss.includes(alias), `auth.css missing compatibility alias ${alias}`);
    assert(whitepaperCss.includes(alias), `whitepaper.css missing compatibility alias ${alias}`);
});

[
    "landing-page-repo/login/index.html",
    "landing-page-repo/sign-up/index.html",
    "landing-page-repo/dashboard/index.html",
    "landing-page-repo/whitepaper/index.html",
    "landing-page-repo/guide/index.html"
].forEach((relativePath) => {
    const html = read(relativePath);
    assert(
        html.includes("/auth.css") || html.includes("/whitepaper.css"),
        `${relativePath} must load a non-homepage CSS entrypoint`
    );
});

assert(!homeHtml.includes("non-homepage-tokens.css"), "homepage HTML must not import non-homepage tokens");
assert(!homeCss.includes("non-homepage-tokens.css"), "homepage CSS must not import non-homepage tokens");
assert(!homeCss.includes("--qadam-token-version"), "homepage CSS must not define non-homepage tokens");

assert(fs.existsSync(path.join(landingRoot, "style.css")), "homepage stylesheet must remain present");

console.log("non_homepage_design_tokens=ok");
