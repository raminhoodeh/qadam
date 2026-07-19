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
    "potential_pattern_summary",
    "confirmation",
    "falsifier",
    "evidence_state",
    "evidence_label",
    "evidence_help",
    "lifecycle_stage",
    "lifecycle_label",
    "lifecycle_help",
    "lifecycle_position",
    "pattern_category",
    "pattern_category_help",
    "computation_label",
    "blocker",
    "next_action",
    "first_observed_at",
    "last_observed_at",
    "observation_count",
    "research_score",
    "comparison_scope",
    "strategy_lenses",
    "recommended_rank",
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
    assert(Number.isFinite(candidate.research_score.value), `Pattern ${candidate.candidate_id} lacks a numeric score`);
    assert(candidate.research_score.value >= 0 && candidate.research_score.value <= 1, `Pattern ${candidate.candidate_id} score is outside 0 to 1`);
    assert(candidate.research_score.is_probability === false, `Pattern ${candidate.candidate_id} score is misrepresented as probability`);
    assert(list(candidate.strategy_lenses).length > 0, `Pattern ${candidate.candidate_id} lacks strategy fit`);
    assert(candidate.relationship.trim().endsWith("?"), `Pattern ${candidate.candidate_id} is not framed as a question`);
    assert(candidate.observed_at === candidate.last_observed_at, `Pattern ${candidate.candidate_id} does not sort from its latest observation`);
    assert(candidate.observation_count >= 1, `Pattern ${candidate.candidate_id} lacks an observation window count`);
    assert(candidate.comparison_scope.source_count === 41, `Pattern ${candidate.candidate_id} does not preserve source scope`);
    assert(candidate.comparison_scope.instrument_count === 19, `Pattern ${candidate.candidate_id} does not preserve instrument scope`);
    if (candidate.contract_fixture_only === true) {
        assert(candidate.evidence_label === "System test only", "Fixture row lacks plain-English system-test label");
    }
    if (["GLD", "SPY"].some((symbol) => list(candidate.instruments).includes(symbol))) {
        assert(candidate.pattern_category === "Macro Watchlist", "GLD/SPY relationship lacks Macro Watchlist category");
    }
});
const expectedPatternLifecycle = [
    "live_observation",
    "candidate_relationship",
    "awaiting_historical_evidence",
    "under_historical_test",
    "quantum_review",
    "validated_edge",
    "ready_for_strategy_mapping",
    "rejected",
    "decayed"
];
assert(
    JSON.stringify(list(status.pattern_recognition.status_lifecycle).map((row) => row.key)) === JSON.stringify(expectedPatternLifecycle),
    "Pattern status lifecycle is incomplete or out of order"
);
assert(status.pattern_recognition.eyebrow === "Predictive Architecture", "Pattern eyebrow is not Predictive Architecture");
assert(status.pattern_recognition.strategy_path_explainer, "Pattern-to-strategy explainer missing");
assert(status.pattern_recognition.comparison_scope.source_count === 41, "Whole-universe source count changed");
assert(status.pattern_recognition.comparison_scope.instrument_count === 19, "Whole-universe instrument count changed");
assert(status.pattern_recognition.comparison_scope.matrix_row_count === 6232, "Whole-universe matrix count changed");
assert(list(status.pattern_recognition.sort_options).length === 5, "Pattern sort controls missing");

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
    status.trading_strategies.validated_core_strategy_count === list(status.trading_strategies.admitted_strategies).length,
    "Validated core strategy count mismatch"
);
assert(
    status.trading_strategies.validated_pattern_sourced_strategy_count
        === list(status.trading_strategies.pattern_sourced_validated_strategies).length,
    "Validated pattern-sourced strategy count mismatch"
);
assert(
    status.trading_strategies.validated_strategy_count
        === status.trading_strategies.validated_core_strategy_count
            + status.trading_strategies.validated_pattern_sourced_strategy_count,
    "Validated strategy count mismatch"
);
assert(status.trading_strategies.core_strategy_count === 5, "Core strategy count mismatch");
assert(list(status.trading_strategies.core_playbooks).length === 5, "Core strategy records missing");
assert(list(status.trading_strategies.strategy_progression).length === 5, "Pattern-to-strategy progression is incomplete");
assert(status.trading_strategies.emerging_strategy_count === list(status.trading_strategies.emerging_strategy_candidates).length, "Emerging strategy count mismatch");
list(status.trading_strategies.core_playbooks).forEach((strategy) => {
    assert(strategy.pattern_count === list(strategy.pattern_lineage).length, `Strategy ${strategy.strategy_family_id} pattern count mismatch`);
    assert(list(strategy.pattern_lineage).length > 0, `Strategy ${strategy.strategy_family_id} hides its pattern lineage`);
    assert(list(strategy.core_instruments).length > 0, `Strategy ${strategy.strategy_family_id} lacks core instruments`);
    list(strategy.pattern_lineage).forEach((pattern) => {
        assert(String(pattern.relationship || "").endsWith("?"), `Strategy ${strategy.strategy_family_id} lineage is not expressed as a question`);
        assert(Number.isFinite(pattern.research_score?.value), `Strategy ${strategy.strategy_family_id} lineage lacks a research score`);
    });
});

authorityIsZero(status);

[
    "Predictive Architecture",
    "Pattern Recognition",
    "Quantum Edge",
    "Trading Strategies",
    "Classical comparison",
    "Strategy influence",
    "Paper outcome lineage",
    "Dynamic Strategy Rotation",
    "How a pattern turns into a trading strategy",
    "From pattern to strategy",
    "Patterns feeding this strategy",
    "Core Strategy Families",
    "Emerging Strategies",
    "Validated Strategies",
    "1. Configured Strategy Families",
    "2. Pattern-Sourced Strategies",
    "3. Validated Strategies",
    "Core strategy family",
    "Emerging Strategy Formations",
    "No unclassified strategies generated yet. Every currently recognized relationship maps cleanly to one of the five core families.",
    "No active portfolios deployed. Strategies can only enter this section once their underlying patterns are fully validated via physical hardware runs and historical data observation.",
    "Continue to Decision Room",
    "What is the potential pattern?",
    "Potential strategy fit",
    "Expand Details",
    "Expand section",
    "Confidence score",
    "Sort observations",
    "How a recognised pattern becomes a trading strategy",
    "View More +",
    "Whole-universe search",
    "System test only"
].forEach((phrase) => assert(script.includes(phrase), `Renderer missing ${phrase}`));
assert((script.match(/Whole-universe search/g) || []).length === 1, "Whole-universe scope must render once at page level");
assert(!script.includes('class="qwf-comparison-scope"'), "Whole-universe scope still repeats inside pattern cards");
assert(script.includes("data-qwf-strategy-path-toggle"), "Pattern-to-strategy disclosure control missing");
assert(script.includes("qwf-sort-select"), "Sort control lacks an explicit chevron shell");

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
assert(!script.includes('replacePanel(VIEW_SELECTORS.quantum'), "Wave F still owns the Quantum Edge panel");
assert(!script.includes("quantum: '[data-qsase-module-panel"), "Wave F still declares a Quantum Edge panel selector");
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
assert(
    /\.qwf-filter-bar button\s*\{[^}]*border-radius:\s*0;/s.test(stylesheet),
    "Pattern filter tabs must keep the active underline straight"
);
assert(stylesheet.includes("@media (max-width: 900px)"), "Wave F tablet layout missing");
assert(stylesheet.includes("@media (max-width: 640px)"), "Wave F mobile layout missing");
assert(stylesheet.includes("prefers-reduced-motion"), "Wave F reduced-motion support missing");
assert(stylesheet.includes(".qwf-pattern-card[open]"), "Expanded pattern border style missing");
assert(stylesheet.includes("position: fixed"), "Viewport-safe tooltip positioning missing");
assert(stylesheet.includes(".qwf-view-more"), "Pattern progressive disclosure style missing");
assert(stylesheet.includes(".qwf-pattern-path-toggle"), "Pattern-to-strategy disclosure style missing");
assert(stylesheet.includes(".qwf-universe-scope"), "Page-level whole-universe scope style missing");
assert(stylesheet.includes(".qwf-strategy-progression"), "Strategy progression style missing");
assert(stylesheet.includes(".qwf-strategy-overview"), "Strategy overview disclosure style missing");
assert(script.indexOf('<details class="qwf-strategy-overview">') < script.indexOf('</header>\n                <section class="qwf-strategy-admission"'), "Strategy explainer must remain inside the Trading Strategies title header");
assert(stylesheet.includes(".qwf-strategy-operational-section"), "Strategy operational disclosure style missing");
assert(stylesheet.includes(".qwf-strategy-operational-section[open] > summary .qsase-card-expand b"), "Parent strategy disclosure label is not scoped to its own summary");
assert(stylesheet.includes(".qwf-strategy-card[open] > summary .qsase-card-expand b::after"), "Nested strategy cards do not own their expanded labels");
assert(!stylesheet.includes(".qwf-strategy-operational-section[open] .qsase-card-expand b {"), "Parent strategy disclosure still overrides child labels");
assert(stylesheet.includes(".qwf-validated-strategy-split"), "Validated strategy split-metric style missing");
assert(stylesheet.includes(".qwf-strategy-pattern-lineage"), "Strategy pattern-lineage style missing");
assert(stylesheet.includes(".qwf-strategy-instrument-map"), "Strategy instrument-map style missing");
assert(stylesheet.includes("white-space: pre-line"), "Multiline status lifecycle tooltip style missing");

[
    'data-qsase-progressive-list="fund-timeline"',
    'data-qsase-progressive-list="order-monitor"',
    "function initQsaseProgressiveLists",
    'data-qsase-page-size="7"',
    "View More +"
].forEach((marker) => assert(dashboardRenderer.includes(marker), `Shared progressive disclosure missing ${marker}`));

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
