#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "..");
const siteRoot = path.resolve(
    process.env.QADAM_DASHBOARD_SITE_ROOT || path.join(repoRoot, "landing-page-repo")
);
const contract = JSON.parse(fs.readFileSync(path.join(repoRoot, "docs/qadam-documentation-contract.json"), "utf8"));
const guideDoc = fs.readFileSync(path.join(repoRoot, contract.canonical_sources.user_guide), "utf8");
const guideHtml = fs.readFileSync(path.join(siteRoot, "guide/index.html"), "utf8");
const dashboardJs = fs.readFileSync(path.join(siteRoot, "dashboard.js"), "utf8");
const protectedGuideCheck = fs.readFileSync(path.join(repoRoot, "scripts/check_protected_user_guide.js"), "utf8");
const parityCheck = fs.readFileSync(path.join(repoRoot, "scripts/check_qadam_documentation_parity.js"), "utf8");
const preflight = fs.readFileSync(path.join(repoRoot, "scripts/preflight_dashboard_deployment.sh"), "utf8");
const regressionSuite = fs.readFileSync(path.join(repoRoot, "scripts/check_non_homepage_regression_suite.js"), "utf8");
const plan = fs.readFileSync(path.join(repoRoot, "docs/qadam-dashboard-overhaul-master-implementation-plan.md"), "utf8");

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

function normalize(source) {
    return source
        .replace(/&amp;/g, "&")
        .replace(/<[^>]+>/g, " ")
        .replace(/[`*_#|>-]/g, " ")
        .replace(/\s+/g, " ")
        .trim()
        .toLowerCase();
}

function includesAll(source, needles, label) {
    const normalized = normalize(source);
    for (const needle of needles) {
        assert(normalized.includes(normalize(needle)), `${label} missing: ${needle}`);
    }
}

function dashboardRouteRecords() {
    const records = [];
    const team = dashboardJs.match(
        /const QSASE_TEAM_ROUTE\s*=\s*\{\s*moduleId:\s*"([^"]+)",\s*viewId:\s*"([^"]+)",\s*label:\s*"([^"]+)"\s*\}/,
    );
    assert(team, "dashboard team route is missing");
    records.push({ route: `${team[1]}/${team[2]}`, label: team[3] });

    const navigation = dashboardJs.match(
        /const QSASE_DASHBOARD_NAVIGATION\s*=\s*\[([\s\S]*?)\];\nconst QSASE_ROUTE_INDEX/,
    )?.[1];
    assert(navigation, "dashboard navigation block is missing");
    const modulePattern = /\{\s*id:\s*"([^"]+)"[\s\S]*?views:\s*\[([\s\S]*?)\]\s*\n\s*\}/g;
    for (const moduleMatch of navigation.matchAll(modulePattern)) {
        const viewPattern = /\{\s*id:\s*"([^"]+)",\s*label:\s*"([^"]+)"\s*\}/g;
        for (const viewMatch of moduleMatch[2].matchAll(viewPattern)) {
            records.push({ route: `${moduleMatch[1]}/${viewMatch[1]}`, label: viewMatch[2] });
        }
    }
    return records;
}

const expectedRoutes = contract.dashboard_routes;
assert(
    JSON.stringify(dashboardRouteRecords()) === JSON.stringify(expectedRoutes),
    `dashboard navigation and documentation contract diverged: ${JSON.stringify(dashboardRouteRecords())}`
);
const expectedRouteLabels = expectedRoutes.map((route) => route.label);

const alignedTerms = [
    ...expectedRouteLabels,
    ...contract.lifecycle.map((stage) => stage.label),
    ...contract.decision_room_sequence,
    ...contract.quantum_edge_sequence,
    ...contract.system_overview_disclosures,
    ...Object.values(contract.learn_improve_questions),
    "Start with Portfolio",
    "Every dashboard page is read-only",
    "blocked, held, or empty state often means Qadam's controls are working",
    "no-trade rationale",
    "public read-only",
    "protected member features",
];
includesAll(guideDoc, alignedTerms, "canonical guide Markdown");
includesAll(guideHtml, alignedTerms, "published guide");

[
    "Open Watching",
    "Open Cognition",
    "Open Worldview",
    "Open Trade Layer",
    "Open Money",
    "Open Forbidden",
    "Start with Mission Control",
].forEach((needle) => {
    assert(!guideDoc.includes(needle), `canonical guide still teaches an old panel: ${needle}`);
    assert(!guideHtml.includes(needle), `published guide still teaches an old panel: ${needle}`);
});

includesAll(protectedGuideCheck, [
    "qadam-documentation-contract.json",
    "public read-only visitor",
    "dashboard_route_count",
    "lifecycle_stage_count",
], "protected-guide checker");
includesAll(parityCheck, [
    "qadam_documentation_parity=ok",
    "qadam-canonical-sha256",
    "dashboard_route_count",
    "lifecycle_stage_count",
], "documentation parity checker");
includesAll(regressionSuite, [
    '"scripts/check_protected_user_guide.js"',
    '"scripts/check_qadam_documentation_parity.js"',
], "documentation regression-suite wiring");
includesAll(preflight, [
    "scripts/sync_qadam_documentation_metadata.py --check",
], "documentation preflight wiring");
includesAll(plan, [
    "D11N - Documentation And Guide Alignment",
    "D11O - Deployment Discipline",
], "historical documentation plan linkage");

console.log("dashboard_d11n_documentation_guide_alignment=ok");
console.log(`dashboard_d11n_views=${dashboardRouteRecords().map((route) => route.label).join(",")}`);
console.log("dashboard_d11n_old_panel_hunt_removed=True");
console.log("dashboard_authority_unchanged=True");
