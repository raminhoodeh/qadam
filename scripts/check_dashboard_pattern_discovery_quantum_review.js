#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const renderer = fs.readFileSync(path.join(root, "landing-page-repo", "dashboard.js"), "utf8");
const css = fs.readFileSync(path.join(root, "landing-page-repo", "auth.css"), "utf8");
const pattern = JSON.parse(fs.readFileSync(path.join(root, "data", "runtime", "qadam_pattern_discovery_dashboard.json"), "utf8"));
const quantum = JSON.parse(fs.readFileSync(path.join(root, "data", "runtime", "qadam_quantum_review_dashboard.json"), "utf8"));

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

function includesAll(text, values, label) {
    values.forEach((value) => assert(text.includes(value), `${label} missing ${value}`));
}

function excludesAll(text, values, label) {
    values.forEach((value) => assert(!text.includes(value), `${label} still contains ${value}`));
}

includesAll(renderer, [
    '{ id: "findings", label: "Pattern Recognition" }',
    '{ id: "nonlinear", label: "Quantum Edge" }',
    'operatorViews["patterns/findings"]',
    'operatorViews["patterns/nonlinear"]',
    "Qualitative analysis",
    "What Qadam most recently noticed",
    "Last observation is out of date",
    "qsase-recent-pattern-score",
    "qsaseResearchScoreValue",
    "scoreRecordExplanation",
    "data-qsase-supporting-reading-toggle",
    "View more readings",
    "instrument-level reading behind",
    "qsase-supporting-research-score-tooltip",
    'class="qsase-recent-pattern-list qsase-supporting-reading-list"',
    "qsaseEvidenceFunnelHelp",
    "data-qsase-pattern-filter",
    "primaryTabs",
    "primaryRelationships",
    "archiveRows",
    "Research pipeline",
    "Noticed → tested → validated",
    "Research archive",
    "Disproved or faded",
    "Ideas that failed testing or stopped appearing in current evidence",
    "data-qsase-research-archive",
    "data-qsase-pattern-card",
    "Where it goes next",
    "It advances when",
    "Quantum Edge",
    "One question only",
    "Matched classical baseline",
    "Quantum or nonlinear result",
    "initQsasePatternDiscoveryFilters",
    "initQsaseSupportingReadings"
], "dashboard renderer");

excludesAll(renderer, [
    "Most actionable pattern",
    "No public explanation was exported for this review.",
    "8 completed reviews",
    "Pattern Recognition Findings",
    "Nonlinear Review",
    "qsase-pattern-flow",
    "qsase-quantum-metrics",
    "View ${scoreReadingPageSize} supporting readings",
    "View ${nextCount} more readings",
    "A higher score is not a higher chance of profit",
    "the score is not a buy or sell signal"
], "dashboard renderer");

assert(!css.includes(".qsase-quantum-metrics"), "Dashboard styles still contain the removed duplicate Quantum metrics grid");

includesAll(css, [
    ".qsase-pattern-discovery",
    ".qsase-discovery-analysis",
    ".qsase-recent-pattern-list",
    ".qsase-recent-pattern-score",
    ".qsase-score-record-explainer",
    ".qsase-supporting-reading-list",
    ".qsase-supporting-reading-toggle",
    ".qsase-evidence-funnel",
    ".qsase-evidence-funnel-tooltip",
    ".qsase-pattern-filter-bar",
    ".qsase-pattern-pipeline",
    ".qsase-pattern-pipeline-head",
    ".qsase-research-archive",
    ".qsase-research-archive-body",
    ".qsase-discovery-card",
    ".qsase-advancement-panel",
    ".qsase-quantum-review",
    ".qsase-quantum-comparison-grid",
    ".qsase-quantum-method-list"
], "dashboard styles");

assert(pattern.artifact_type === "qadam_pattern_discovery_dashboard", "Pattern Discovery artifact type invalid");
assert(pattern.qualitative_analysis.bullet_count > 0, "Recent qualitative pattern bullets missing");
const recordedScoreCount = pattern.funnel.find((row) => row.key === "recorded")?.count || 0;
const linkedScoreCount = pattern.relationships.reduce((total, row) => total + (row.instrument_results || []).length, 0);
assert(pattern.funnel.find((row) => row.key === "recorded")?.label === "Instrument score records", "Score-record funnel label is ambiguous");
assert(pattern.qualitative_analysis.total_score_record_count === recordedScoreCount, "Total score-record explanation count mismatch");
assert(pattern.qualitative_analysis.strategy_linked_score_record_count === linkedScoreCount, "Strategy-linked score-record count mismatch");
assert(pattern.qualitative_analysis.context_and_control_score_record_count === recordedScoreCount - linkedScoreCount, "Context/control score-record count mismatch");
assert(pattern.qualitative_analysis.score_record_explanation.includes("not additional discoveries"), "Score-record distinction is not explained");
assert(pattern.qualitative_analysis.bullets.every((row) => Number.isFinite(row.raw_pattern_score)), "Recent pattern score value missing");
assert(pattern.qualitative_analysis.bullets.every((row) => Number.isFinite(row.fresh_source_ratio) && row.fresh_source_ratio >= 0 && row.fresh_source_ratio <= 1), "Recent pattern freshness ratio missing");
assert(pattern.relationship_count === pattern.relationships.length, "Pattern relationship count mismatch");
assert(new Set(pattern.relationships.map((row) => row.pattern_id)).size === pattern.relationships.length, "Pattern identities are duplicated");
assert(pattern.relationships.every((row) => row.raw_pattern_score_is_probability === false), "Raw pattern score shown as probability");
assert(pattern.relationships.every((row) => row.current_stage && row.next_destination && row.advance_when.length), "Pattern advancement contract incomplete");

assert(quantum.artifact_type === "qadam_quantum_review_dashboard", "Quantum Review artifact type invalid");
assert(
    quantum.empirical_comparison_count === quantum.reviews.reduce((total, row) => total + row.empirical_comparison_count, 0),
    "Empirical comparison total does not match review evidence"
);
assert(quantum.defined_protocol_count > 0, "Quantum protocols missing");
assert(quantum.reviews.every((row) => row.returned_to === "Pattern Recognition"), "Quantum verdict does not return to Pattern Recognition");
assert(quantum.reviews.every((row) => row.hardware_used === false), "Quantum hardware use misrepresented");
assert(quantum.current_method_state.hardware_completed_count === 0, "Quantum hardware count is overstated");
assert(quantum.reviews.every((row) => ["incremental", "neutral", "fallback", "not_useful"].includes(row.contribution)), "Quantum contribution class is missing");
assert(quantum.reviews.every((row) => row.verdict !== "nonlinear_strengthened" || row.contribution === "incremental"), "Quantum review strengthened without explicit incremental credit");
if (quantum.empirical_comparison_count > 0) {
    assert(quantum.current_method_state.simulator_completed_count > 0, "Completed simulator evidence is hidden");
} else {
    assert(quantum.reviews.every((row) => row.execution_mode_label === "Experiment designed; empirical comparison not run"), "Protocol state is not explained honestly");
    assert(quantum.reviews.every((row) => row.verdict === "not_measurable"), "Unmeasured quantum review has an empirical verdict");
}

console.log("dashboard_pattern_discovery_quantum_review=ok");
console.log(`pattern_relationship_count=${pattern.relationship_count}`);
console.log(`recent_pattern_bullet_count=${pattern.qualitative_analysis.bullet_count}`);
console.log(`quantum_protocol_count=${quantum.defined_protocol_count}`);
console.log(`quantum_empirical_comparison_count=${quantum.empirical_comparison_count}`);
