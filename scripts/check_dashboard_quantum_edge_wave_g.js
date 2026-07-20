#!/usr/bin/env node

"use strict";

const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");
const siteRoot = path.resolve(process.argv[2] || path.join(repoRoot, "landing-page-repo"));

function read(relativePath) {
    return fs.readFileSync(path.join(siteRoot, relativePath), "utf8");
}

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

function list(value) {
    return Array.isArray(value) ? value : [];
}

const status = JSON.parse(read("status/quantum-edge-wave-g.json"));
const quantumPage = JSON.parse(read("status/quantum-edge-page.json"));
const script = read("quantum-edge-wave-g.js");
const stylesheet = read("quantum-edge-wave-g.css");
const auth = read("auth.js");
const dashboardHtml = read("dashboard/index.html");

assert(status.schema_version === "qadam.QuantumEdgeWaveGHybridLoop.v1", "Wave G schema mismatch");
assert(status.automation.provider_calls_this_cycle === 0, "Wave G made a provider call");
assert(status.automation.hardware_submission_allowed === false, "Wave G can submit hardware");
assert(status.paper_integration.paper_order_created_count === 0, "Wave G created an order");
assert(status.paper_integration.broker_write_count === 0, "Wave G wrote to a broker");
assert(status.paper_integration.route_contract.wave_g_calls_broker === false, "Wave G route reaches broker directly");

const expectedStates = [
    "candidate noticed",
    "experiment prepared",
    "experiment executed",
    "result reproduced",
    "evidence strengthened",
    "edge validated",
    "strategy influenced",
    "paper outcome observed"
];
assert(
    JSON.stringify(list(status.public_lifecycle).map((row) => row.state)) === JSON.stringify(expectedStates),
    "Wave G public lifecycle changed"
);
assert(status.public_lifecycle[0].status === "complete", "Candidate state should be visible");
assert(status.public_lifecycle[1].status === "not reached", "Wave G must not claim it prepared the separately authorized hardware run");
assert(status.public_lifecycle[2].status === "complete", "Verified IBM hardware execution is missing");
assert(status.public_lifecycle[3].status === "complete", "Local reproduction should be visible");
assert(status.public_lifecycle[4].status === "not reached", "Evidence strengthening is overstated");
assert(status.public_lifecycle[5].status === "not reached", "Edge validation is overstated");
assert(status.telegram_brief.paragraph_count === 2, "Telegram brief is not two paragraphs");
assert(status.telegram_brief.telegram_send_allowed === false, "Wave G can send Telegram messages");
assert(status.telegram_brief.telegram_command_authority === false, "Wave G accepts Telegram commands");

[
    "Recurring hybrid loop",
    "From research finding to paper outcome",
    "Guarded paper path",
    "Latest unattended cycle",
    "Human daily brief",
    "Wave G does not send messages or accept commands"
].forEach((phrase) => assert(script.includes(phrase), `Wave G renderer missing ${phrase}`));

assert((script.match(/fetch\(/g) || []).length === 1, "Wave G renderer must make one read-only fetch");
assert(script.includes("/status/quantum-edge-wave-g.json"), "Wave G renderer fetches the wrong resource");
assert(!/paper-api\.alpaca|\/v2\/orders|submitOrder|createOrder/i.test(script), "Wave G renderer contains broker/order code");
assert(!auth.includes("/quantum-edge-wave-g.js"), "Wave G still competes for Quantum Edge rendering");
assert(!auth.includes("/quantum-edge-wave-g.css"), "Wave G stylesheet is still loaded into Quantum Edge");
const releaseIdMatch = dashboardHtml.match(/<meta name="qadam-dashboard-release" content="qadam-dashboard-([^"]+)"/);
assert(releaseIdMatch, "Dashboard release identity is missing");
const releaseCacheKey = releaseIdMatch[1];
assert(
    auth.includes(`/quantum-edge-page.js?v=${releaseCacheKey}`),
    "Canonical Quantum Edge renderer does not match the dashboard release"
);
assert(
    auth.includes(`/quantum-edge-page.css?v=${releaseCacheKey}`),
    "Canonical Quantum Edge stylesheet does not match the dashboard release"
);
const pageSource = list(quantumPage.source_artifacts).find((row) => row.source_id === "wave_g");
assert(pageSource, "Wave G is absent from the canonical Quantum Edge page");
assert(pageSource.content_hash === status.content_hash, "Wave G canonical page lineage is stale");
assert(pageSource.content_hash_verified === true, "Wave G canonical page lineage is unverified");
const authAssetMatch = dashboardHtml.match(/\/auth\.js\?v=([^"']+)/);
assert(authAssetMatch, "Dashboard auth.js cache key is missing");
assert(
    authAssetMatch[1] === releaseCacheKey,
    "Dashboard auth.js cache key does not match the dashboard release"
);
assert(stylesheet.includes("body.qadam-dashboard-page .qwg-"), "Wave G CSS is not dashboard scoped");
assert(stylesheet.includes("@media (max-width: 720px)"), "Wave G mobile layout missing");
assert(stylesheet.includes("prefers-reduced-motion"), "Wave G reduced-motion support missing");

process.stdout.write(`${JSON.stringify({
    status: "wave_g_dashboard_acceptance_passed",
    content_hash: status.content_hash,
    cycle_id: status.cycle_id,
    validated_edges: status.validated_edge_admissions.length,
    strategies: status.paper_integration.strategy_count,
    paperops_review_handoffs: status.paper_integration.paperops_review_handoff_count,
    provider_calls_this_cycle: status.automation.provider_calls_this_cycle,
    lifecycle: status.public_lifecycle.map((row) => [row.state, row.status]),
    authority: "read_only"
}, null, 2)}\n`);
