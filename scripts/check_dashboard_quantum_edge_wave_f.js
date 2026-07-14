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

function authorityIsZero(value, trail = "root") {
    if (Array.isArray(value)) {
        value.forEach((item, index) => authorityIsZero(item, `${trail}[${index}]`));
        return;
    }
    if (!value || typeof value !== "object") return;
    Object.entries(value).forEach(([key, child]) => {
        if ((key.endsWith("_allowed") || key.endsWith("_enabled")) && child === true) {
            throw new Error(`Wave F grants authority at ${trail}.${key}`);
        }
        authorityIsZero(child, `${trail}.${key}`);
    });
}

const status = JSON.parse(read("status/quantum-edge-wave-f.json"));
const script = read("quantum-edge-wave-f.js");
const stylesheet = read("quantum-edge-wave-f.css");
const auth = read("auth.js");
const dashboardHtml = read("dashboard/index.html");
const dashboardRenderer = read("dashboard.js");

assert(status.schema_version === "qadam.QuantumEdgeWaveFPublicView.v1", "Wave F schema mismatch");
assert(status.routes.pattern_recognition.module_id === "patterns", "Pattern module route changed");
assert(status.routes.pattern_recognition.view_id === "findings", "Pattern view route changed");
assert(status.routes.quantum_edge.module_id === "patterns", "Quantum module route changed");
assert(status.routes.quantum_edge.view_id === "nonlinear", "Quantum view route changed");
assert(status.routes.trading_strategies.module_id === "decide", "Strategy module route changed");
assert(status.routes.trading_strategies.view_id === "strategies", "Strategy view route changed");

const filters = Object.fromEntries(
    list(status.pattern_recognition.filters).map((row) => [row.key, row.count])
);
assert(Object.hasOwn(filters, "all"), "All origin filter missing");
assert(Object.hasOwn(filters, "classical_discovery"), "Classical origin filter missing");
assert(Object.hasOwn(filters, "quantum_assisted_discovery"), "Quantum origin filter missing");
assert(Object.hasOwn(filters, "joint_discovery"), "Joint origin filter missing");
assert(filters.all === list(status.pattern_recognition.candidates).length, "Pattern count mismatch");

const requiredPatternFields = [
    "relationship",
    "source_chain",
    "market",
    "interpretation",
    "confirmation",
    "falsifier",
    "evidence_state",
    "lifecycle_stage",
    "blocker",
    "next_action",
    "discovery_origin",
    "validation_contribution"
];
list(status.pattern_recognition.candidates).forEach((candidate) => {
    requiredPatternFields.forEach((field) => {
        assert(Object.hasOwn(candidate, field), `Pattern ${candidate.candidate_id} lacks ${field}`);
    });
    if (candidate.execution_mode_label === "IBM Quantum via Q-CTRL Fire Opal") {
        assert(candidate.hardware_receipt_verified === true, "IBM hardware label lacks a verified receipt");
    }
});

const expectedProofLadder = [
    "Provider configured",
    "IBM hardware executed",
    "Result reproduced",
    "Classical baseline beaten",
    "Untouched-data advantage survived",
    "Paper decision improved"
];
assert(
    JSON.stringify(list(status.quantum_edge.proof_ladder).map((row) => row.label)) === JSON.stringify(expectedProofLadder),
    "Quantum Edge proof ladder changed"
);
assert(status.quantum_edge.comparison_summary, "Classical comparison summary missing");
assert(status.quantum_edge.strategy_influence, "Strategy influence summary missing");
assert(status.quantum_edge.paper_outcome_lineage, "Paper outcome lineage missing");

if (status.quantum_edge.proof_state === "validated_quantum_contribution") {
    assert(
        list(status.quantum_edge.comparisons).some(
            (row) => row.validation_contribution === "quantum_strengthened" && row.empirical_claim_allowed === true
        ),
        "Validated quantum claim lacks untouched empirical evidence"
    );
}

const validatedPatternIds = new Set(
    list(status.pattern_recognition.candidates)
        .filter((candidate) => candidate.validated_edge === true)
        .map((candidate) => candidate.candidate_id)
);
list(status.trading_strategies.admitted_strategies).forEach((strategy) => {
    assert(
        list(strategy.underlying_pattern_ids).some((patternId) => validatedPatternIds.has(patternId)),
        `Strategy ${strategy.strategy_family_id} lacks validated pattern lineage`
    );
});
assert(
    status.trading_strategies.validated_strategy_count === list(status.trading_strategies.admitted_strategies).length,
    "Validated strategy count mismatch"
);

authorityIsZero(status);

[
    "Pattern Recognition",
    "Quantum Edge",
    "Trading Strategies",
    "Classical comparison",
    "Strategy influence",
    "Paper outcome lineage",
    "No strategy has passed admission yet"
].forEach((phrase) => assert(script.includes(phrase), `Renderer missing ${phrase}`));

assert((script.match(/fetch\(/g) || []).length === 1, "Wave F renderer must make one read-only fetch");
assert(script.includes('/status/quantum-edge-wave-f.json'), "Wave F renderer fetches the wrong resource");
assert(!/paper-api\.alpaca|\/v2\/orders|submitOrder|createOrder/i.test(script), "Wave F renderer contains broker/order code");
const releaseIdMatch = dashboardHtml.match(/<meta name="qadam-dashboard-release" content="qadam-dashboard-([^"]+)"/);
assert(releaseIdMatch, "Dashboard release identity is missing");
const releaseCacheKey = releaseIdMatch[1];
assert(
    auth.includes(`/quantum-edge-wave-f.js?v=${releaseCacheKey}`),
    "Wave F script loader does not match the dashboard release"
);
assert(
    auth.includes(`/quantum-edge-wave-f.css?v=${releaseCacheKey}`),
    "Wave F style loader does not match the dashboard release"
);
assert(
    script.includes(`/status/quantum-edge-wave-f.json?v=${releaseCacheKey}`),
    "Wave F status projection does not match the dashboard release"
);
assert(script.includes("provider_status_summary"), "Wave F renderer lacks provider-state copy");
const authAssetMatch = dashboardHtml.match(/\/auth\.js\?v=([^"']+)/);
assert(authAssetMatch, "Dashboard auth.js cache key is missing");
assert(
    !["20260712-wave-f-v1", "20260712-wave-g-v1", "20260712-wave-h-v1"].includes(authAssetMatch[1]),
    "Dashboard auth.js cache key predates the Wave H loader"
);

[
    'data-qsase-module-panel="${moduleId}"',
    'data-qsase-view-panel="${viewId}"'
].forEach((marker) => assert(dashboardRenderer.includes(marker), `Dashboard renderer lacks ${marker}`));

assert(stylesheet.includes("body.qadam-dashboard-page .qwf-"), "Wave F CSS is not dashboard scoped");
assert(stylesheet.includes("@media (max-width: 900px)"), "Wave F tablet layout missing");
assert(stylesheet.includes("@media (max-width: 640px)"), "Wave F mobile layout missing");
assert(stylesheet.includes("prefers-reduced-motion"), "Wave F reduced-motion support missing");

process.stdout.write(`${JSON.stringify({
    status: "wave_f_dashboard_acceptance_passed",
    content_hash: status.content_hash,
    patterns: status.pattern_recognition.candidate_count,
    origin_counts: filters,
    proof_state: status.quantum_edge.proof_state,
    completed_proof_steps: status.quantum_edge.completed_proof_step_count,
    hardware_experiment_completed: status.quantum_edge.hardware_authenticity.hardware_experiment_completed,
    validated_strategies: status.trading_strategies.validated_strategy_count,
    research_playbooks: status.trading_strategies.research_playbook_count,
    authority: "read_only"
}, null, 2)}\n`);
