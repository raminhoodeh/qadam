#!/usr/bin/env node

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const contract = JSON.parse(fs.readFileSync(path.join(root, "docs/qadam-documentation-contract.json"), "utf8"));

function read(relativePath) {
    return fs.readFileSync(path.join(root, relativePath), "utf8");
}

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

function decodeEntities(text) {
    return text
        .replace(/&amp;/g, "&")
        .replace(/&pound;/g, "£")
        .replace(/&dollar;/g, "$")
        .replace(/&#39;|&apos;/g, "'")
        .replace(/&quot;/g, '"')
        .replace(/&nbsp;/g, " ")
        .replace(/&rarr;|&#8594;/g, "→")
        .replace(/&mdash;/g, "—");
}

function semanticText(source) {
    return decodeEntities(source)
        .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, " ")
        .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, " ")
        .replace(/<[^>]+>/g, " ")
        .replace(/[`*_#|>-]/g, " ")
        .replace(/\s+/g, " ")
        .trim();
}

function includesNormalized(source, needle) {
    return semanticText(source).toLowerCase().includes(semanticText(needle).toLowerCase());
}

function assertIncludesEvery(source, needles, label) {
    for (const needle of needles) {
        assert(includesNormalized(source, needle), `${label} is missing: ${needle}`);
    }
}

function assertOmitsEvery(source, needles, label) {
    for (const needle of needles) {
        assert(!includesNormalized(source, needle), `${label} retains stale or unsafe wording: ${needle}`);
    }
}

function assertOrdered(source, needles, label) {
    const normalized = semanticText(source).toLowerCase();
    let cursor = -1;
    for (const needle of needles) {
        const next = normalized.indexOf(semanticText(needle).toLowerCase(), cursor + 1);
        assert(next >= 0, `${label} is missing ordered item: ${needle}`);
        assert(next > cursor, `${label} has items out of order near: ${needle}`);
        cursor = next;
    }
}

function sha256(source) {
    return crypto.createHash("sha256").update(source).digest("hex");
}

function metaValue(html, name) {
    const pattern = new RegExp(`<meta\\s+name=["']${name}["']\\s+content=["']([^"']*)["']\\s*\\/?>`, "gi");
    const matches = [...html.matchAll(pattern)];
    assert(matches.length === 1, `expected exactly one ${name} metadata tag, found ${matches.length}`);
    return matches[0][1];
}

function dashboardRouteRecords(source) {
    const records = [];
    const team = source.match(
        /const QSASE_TEAM_ROUTE\s*=\s*\{\s*moduleId:\s*"([^"]+)",\s*viewId:\s*"([^"]+)",\s*label:\s*"([^"]+)"\s*\}/,
    );
    assert(team, "dashboard team route is missing");
    records.push({ route: `${team[1]}/${team[2]}`, label: team[3] });

    const navigation = source.match(
        /const QSASE_DASHBOARD_NAVIGATION\s*=\s*\[([\s\S]*?)\];\nconst QSASE_ROUTE_INDEX/,
    )?.[1];
    assert(navigation, "dashboard navigation block is missing");
    const modulePattern = /\{\s*id:\s*"([^"]+)"[\s\S]*?views:\s*\[([\s\S]*?)\]\s*\n\s*\}/g;
    for (const moduleMatch of navigation.matchAll(modulePattern)) {
        const moduleId = moduleMatch[1];
        const viewPattern = /\{\s*id:\s*"([^"]+)",\s*label:\s*"([^"]+)"\s*\}/g;
        for (const viewMatch of moduleMatch[2].matchAll(viewPattern)) {
            records.push({ route: `${moduleId}/${viewMatch[1]}`, label: viewMatch[2] });
        }
    }
    return records;
}

const guideSourcePath = contract.canonical_sources.user_guide;
const whitepaperSourcePath = contract.canonical_sources.whitepaper;
const guideMarkdown = read(guideSourcePath);
const whitepaperMarkdown = read(whitepaperSourcePath);
const guideHtml = read(contract.published_materializations.user_guide[0]);
const whitepaperHtml = read(contract.published_materializations.whitepaper[0]);
const cockpitWhitepaperHtml = read(contract.published_materializations.whitepaper[1]);
const retiredWhitepaper = read("docs/qadam-for-fund-managers.md");
const dashboardJs = read("landing-page-repo/dashboard.js");

const documents = {
    "guide Markdown": guideMarkdown,
    "published guide": guideHtml,
    "whitepaper Markdown": whitepaperMarkdown,
    "published whitepaper": whitepaperHtml,
    "cockpit whitepaper": cockpitWhitepaperHtml,
};

const contentOnly = process.argv.includes("--content-only");
if (!contentOnly) {
    for (const [documentId, sourcePath] of Object.entries(contract.canonical_sources)) {
        const source = read(sourcePath);
        const digest = sha256(source);
        for (const targetPath of contract.published_materializations[documentId]) {
            const target = read(targetPath);
            assert(metaValue(target, "qadam-canonical-source") === sourcePath, `${targetPath} has the wrong canonical source`);
            assert(metaValue(target, "qadam-canonical-sha256") === digest, `${targetPath} canonical source hash is stale`);
            assert(metaValue(target, "qadam-document-version") === contract.document_versions[documentId], `${targetPath} document version is stale`);
            assert(metaValue(target, "qadam-reviewed-on") === contract.reviewed_on, `${targetPath} review date is stale`);
        }
    }
}

const routeLabels = contract.dashboard_routes.map((route) => route.label);
assert(contract.dashboard_routes.length === 13, "documentation contract must define 13 dashboard routes");
assert(
    JSON.stringify(dashboardRouteRecords(dashboardJs)) === JSON.stringify(contract.dashboard_routes),
    "dashboard module/view routes and documentation contract have diverged",
);
assertIncludesEvery(dashboardJs, routeLabels, "dashboard route contract");
assertIncludesEvery(guideMarkdown, routeLabels, "guide Markdown route map");
assertIncludesEvery(guideHtml, routeLabels, "published guide route map");
assertIncludesEvery(whitepaperMarkdown, routeLabels, "whitepaper conceptual page map");
assertIncludesEvery(whitepaperHtml, routeLabels, "published whitepaper conceptual page map");
assertOrdered(guideMarkdown, routeLabels, "guide Markdown route map");
assertOrdered(guideHtml, routeLabels, "published guide route map");
assertOrdered(whitepaperMarkdown, routeLabels, "whitepaper conceptual page map");
assertOrdered(whitepaperHtml, routeLabels, "published whitepaper conceptual page map");

const lifecycleLabels = contract.lifecycle.map((stage) => stage.label);
assert(contract.lifecycle.length === 10, "documentation contract must define the ten lifecycle stages");
for (const [label, source] of Object.entries(documents)) {
    assertIncludesEvery(source, lifecycleLabels, `${label} lifecycle`);
    assertOrdered(source, lifecycleLabels, `${label} lifecycle`);
}

assertIncludesEvery(guideMarkdown, contract.decision_room_sequence, "guide Markdown Decision Room sequence");
assertIncludesEvery(guideHtml, contract.decision_room_sequence, "published guide Decision Room sequence");
assertOrdered(guideMarkdown, contract.decision_room_sequence, "guide Markdown Decision Room sequence");
assertOrdered(guideHtml, contract.decision_room_sequence, "published guide Decision Room sequence");

for (const [label, source] of Object.entries(documents)) {
    assertIncludesEvery(source, contract.quantum_edge_sequence, `${label} Quantum Edge sequence`);
    assertOrdered(source, contract.quantum_edge_sequence, `${label} Quantum Edge sequence`);
}
assertIncludesEvery(guideMarkdown, contract.system_overview_disclosures, "guide Markdown System Overview");
assertIncludesEvery(guideHtml, contract.system_overview_disclosures, "published guide System Overview");

for (const [page, question] of Object.entries(contract.learn_improve_questions)) {
    assertIncludesEvery(guideMarkdown, [page, question], "guide Learn and Improve contract");
    assertIncludesEvery(guideHtml, [page, question], "published guide Learn and Improve contract");
    assertIncludesEvery(whitepaperMarkdown, [page, question], "whitepaper Learn and Improve contract");
    assertIncludesEvery(whitepaperHtml, [page, question], "published whitepaper Learn and Improve contract");
}

const whitepaperCopies = {
    "whitepaper Markdown": whitepaperMarkdown,
    "published whitepaper": whitepaperHtml,
    "cockpit whitepaper": cockpitWhitepaperHtml,
};
const paperAccount = contract.paper_account;
const snapshot = contract.dated_operating_snapshot;
for (const [label, source] of Object.entries(whitepaperCopies)) {
    assertIncludesEvery(source, [
        paperAccount.reference_baseline,
        paperAccount.broker,
        "designed",
        "implemented",
        "current operating",
        snapshot.mode,
        snapshot.paperops_state,
        snapshot.evidence_state,
        snapshot.quantum_verdict,
        snapshot.quantum_engineering_checks,
        snapshot.quantum_market_proof_checks,
        ...(snapshot.ibm_hardware_experiment_executed ? [] : ["no IBM hardware experiment"]),
        "research eligibility",
        "risk approval",
        "untouched holdout",
        "forward observation",
        "approved version",
        "public-safe",
        "read-only",
    ], `${label} current-truth contract`);
    assertOmitsEvery(source, [
        "£100,000",
        "GBP 100000",
        "paper-live control plane is certified",
        "All saved Qadam data lives on Ramin's MacBook",
        "Turn strategies on or off",
    ], label);
}

assert(contract.authority_boundaries.paper_only === true, "documentation contract must remain paper-only");
assert(contract.authority_boundaries.dashboard_read_only === true, "dashboard authority contract must remain read-only");
assert(contract.authority_boundaries.akber_is_research_eligibility_only === true, "Akber authority contract has drifted");
assert(contract.authority_boundaries.live_capital_enabled === false, "documentation contract must not enable live capital");
assert(contract.authority_boundaries.dashboard_broker_writes_allowed === false, "dashboard broker-write authority must remain false");
assert(contract.authority_boundaries.telegram_command_authority === false, "Telegram command authority must remain false");
assert(contract.authority_boundaries.automatic_policy_mutation_allowed === false, "automatic policy mutation must remain false");

const akberOperationalStages = [
    "Context",
    "Catalyst",
    "Confirmation",
    "Risk",
    "Execution suitability",
    "Postmortem learning",
];
for (const [label, source] of Object.entries(documents)) {
    assertIncludesEvery(source, akberOperationalStages, `${label} Akber operational model`);
}

assertIncludesEvery(guideMarkdown, [
    "Public read-only access",
    "Protected member features",
    contract.operator_workflows.paperops_pass,
    contract.operator_workflows.daily_learning_live_pass,
    "Outbound explanation",
    "Inbound research intake",
], "guide authority and operator contract");
assertIncludesEvery(guideHtml, [
    "Public read-only access",
    "Protected member features",
    contract.operator_workflows.paperops_pass,
    contract.operator_workflows.daily_learning_live_pass,
    "Outbound explanation",
    "Inbound research intake",
], "published guide authority and operator contract");
assertOmitsEvery(guideMarkdown, [
    ".venv/bin/python scripts/run_phase7_demo_proof_harness.py",
    "the paper-live control plane is certified",
    "IBM Quantum token/instance configuration before device probing",
], "guide Markdown");
assertOmitsEvery(guideHtml, [
    "Read first Safety Status",
    "First-release access is limited",
    "The dashboard, guide, and settings routes are protected",
    "The Five States",
    "Current Fund Position stays open",
    "Research Ideas Approaching Decision",
    "Ready for Decision Room",
    "Previous Decision Reviews",
    "Pattern Discovery",
    "Founder Decision Blocks",
    "Start with Overview",
    "Advanced / Debug Mode",
    "Telegram is Qadam's outbound member notification rail",
    "Gemma 4 E4B",
    "Live capital is enabled",
], "published guide");

for (const [label, source] of Object.entries(whitepaperCopies)) {
    assertOmitsEvery(source, [
        "Qadam For The Founding Fund Managers",
        "The founding Fund Managers are",
        "In the first release",
        "All saved Qadam data lives on Ramin's MacBook",
        "Turn strategies on or off",
        "100 closed proof trades",
        "60-day paper growth trial",
        "weekly oracle",
    ], label);
}

assertIncludesEvery(retiredWhitepaper, [
    "Deprecated",
    "qadam-whitepaper.md",
], "retired duplicate whitepaper pointer");
assert(retiredWhitepaper.includes("./qadam-whitepaper.md"), "retired duplicate whitepaper pointer must link to the canonical file");
assert(retiredWhitepaper.split(/\r?\n/).length <= 40, "retired duplicate whitepaper must remain a concise pointer");

assert(
    whitepaperHtml === cockpitWhitepaperHtml,
    "landing and cockpit whitepaper copies must remain byte-identical",
);

for (const [assetId, assetPaths] of Object.entries(contract.published_assets)) {
    assert(assetPaths.length >= 2, `${assetId} must define every published copy`);
    const canonicalAsset = read(assetPaths[0]);
    for (const assetPath of assetPaths.slice(1)) {
        assert(read(assetPath) === canonicalAsset, `${assetId} has diverged at ${assetPath}`);
    }
}

console.log("qadam_documentation_parity=ok");
console.log(`reviewed_on=${contract.reviewed_on}`);
console.log(`dashboard_route_count=${contract.dashboard_routes.length}`);
console.log(`lifecycle_stage_count=${contract.lifecycle.length}`);
console.log(`canonical_user_guide=${guideSourcePath}`);
console.log(`canonical_whitepaper=${whitepaperSourcePath}`);
