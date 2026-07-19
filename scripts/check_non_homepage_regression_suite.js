#!/usr/bin/env node

const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "..");
const dashboardSiteRoot = path.resolve(
    process.env.QADAM_DASHBOARD_SITE_ROOT || path.join(repoRoot, "landing-page-repo")
);

const nodeChecks = [
    "scripts/check_non_homepage_design_tokens.js",
    "scripts/check_non_homepage_layout_components.js",
    "scripts/check_non_homepage_navigation_contract.js",
    "scripts/check_non_homepage_auth_pages.js",
    "scripts/check_non_homepage_whitepaper_redesign.js",
    "scripts/check_non_homepage_guide_redesign.js",
    "scripts/check_non_homepage_dashboard_redesign.js",
    "scripts/check_non_homepage_accessibility.js",
    "scripts/check_protected_user_guide.js",
    "scripts/check_dashboard_acceptance.js",
    "scripts/check_dashboard_stage7_visibility.js",
    "scripts/check_dashboard_mission_control.js",
    "scripts/check_dashboard_navigable_modules.js",
    "scripts/check_dashboard_full_width_frame.js",
    "scripts/check_dashboard_d11m_regression_acceptance.js",
    "scripts/check_dashboard_deployment_readiness.js"
];

const syntaxChecks = [
    "scripts/check_non_homepage_regression_suite.js",
    ...nodeChecks
];

const landingPageDiffFiles = [
    "auth.css",
    "auth.js",
    "dashboard.js",
    "dashboard/index.html",
    "guide/index.html",
    "login/index.html",
    "sign-up/index.html",
    "whitepaper.css",
    "whitepaper/index.html",
    "non-homepage-layout.css",
    "non-homepage-tokens.css",
    "quantum-edge-page.css",
    "quantum-edge-page.js",
    "quantum-edge-wave-f.css",
    "quantum-edge-wave-f.js",
    "status/quantum-edge-page.json",
    "status/quantum-edge-wave-f.json"
];

const rootDiffFiles = [
    "scripts/check_non_homepage_regression_suite.js",
    ...nodeChecks
];

function assert(condition, message) {
    if (!condition) {
        throw new Error(message);
    }
}

function run(command, args, options = {}) {
    const result = spawnSync(command, args, {
        cwd: options.cwd || repoRoot,
        encoding: "utf8",
        stdio: ["ignore", "pipe", "pipe"]
    });

    const label = [command, ...args].join(" ");
    if (result.status !== 0) {
        const output = `${result.stdout || ""}${result.stderr || ""}`.trim();
        throw new Error(`${label} failed${output ? `\n${output}` : ""}`);
    }

    return `${result.stdout || ""}${result.stderr || ""}`.trim();
}

function assertFile(relativePath) {
    const prefix = "landing-page-repo/";
    const filePath = relativePath.startsWith(prefix)
        ? path.join(dashboardSiteRoot, relativePath.slice(prefix.length))
        : path.join(repoRoot, relativePath);
    assert(fs.existsSync(filePath), `missing regression dependency ${relativePath}`);
}

function assertNoWhitespaceErrors(relativePath) {
    const prefix = "landing-page-repo/";
    const filePath = relativePath.startsWith(prefix)
        ? path.join(dashboardSiteRoot, relativePath.slice(prefix.length))
        : path.join(repoRoot, relativePath);
    const text = fs.readFileSync(filePath, "utf8");
    const lines = text.split("\n");
    lines.forEach((line, index) => {
        assert(!/[ \t]+$/.test(line), `${relativePath}:${index + 1} has trailing whitespace`);
    });
    assert(text.endsWith("\n"), `${relativePath} must end with a newline`);
}

function successMarker(scriptPath, output) {
    const lines = output.split("\n").map((line) => line.trim()).filter(Boolean);
    return lines.find((line) => /=ok(?:\s|$)|contract OK$/i.test(line)) || `${path.basename(scriptPath)}=passed`;
}

function assertHomepageIsolation() {
    const homepageFiles = [
        "index.html",
        "style.css"
    ].map((relativePath) => fs.readFileSync(path.join(dashboardSiteRoot, relativePath), "utf8")).join("\n");

    [
        "qadam-auth-page",
        "qadam-whitepaper-page",
        "qadam-guide-page",
        "qadam-dashboard-page",
        "non-homepage-layout.css",
        "qadam-section-nav",
        "skip-link"
    ].forEach((needle) => {
        assert(!homepageFiles.includes(needle), `homepage isolation failed: found ${needle}`);
    });
}

function assertPublicSafePages() {
    const publicPageText = [
        "login/index.html",
        "sign-up/index.html",
        "whitepaper/index.html",
        "guide/index.html",
        "dashboard/index.html"
    ].map((relativePath) => fs.readFileSync(path.join(dashboardSiteRoot, relativePath), "utf8")).join("\n");

    [
        /\/Users\//,
        /\/private\//,
        /\/var\/folders\//,
        /\b[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b/,
        /\d{6,}:[A-Za-z0-9_-]{20,}/,
        /OPENAI_API_KEY=/,
        /ANTHROPIC_API_KEY=/,
        /TELEGRAM_BOT_TOKEN=/,
        /SUPABASE_SECRET_KEY=/
    ].forEach((pattern) => {
        assert(!pattern.test(publicPageText), `public-safe page check failed: ${pattern}`);
    });
}

nodeChecks.forEach(assertFile);
syntaxChecks.forEach((scriptPath) => run("node", ["--check", scriptPath]));

nodeChecks.forEach((scriptPath) => {
    const output = run("node", [scriptPath]);
    console.log(successMarker(scriptPath, output));
});

run("git", ["diff", "--check", "--", ...rootDiffFiles]);
run("git", ["-C", dashboardSiteRoot, "diff", "--check", "--", ...landingPageDiffFiles]);
[...rootDiffFiles, ...landingPageDiffFiles.map((filePath) => `landing-page-repo/${filePath}`)].forEach(assertNoWhitespaceErrors);
assertHomepageIsolation();
assertPublicSafePages();

console.log(`non_homepage_regression_suite=ok checks=${nodeChecks.length}`);
