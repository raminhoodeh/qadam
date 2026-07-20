#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const {
    assert,
    html,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

const repoRoot = path.resolve(__dirname, "..");
const runtimeDir = process.env.QADAM_RUNTIME_DIR
    ? path.resolve(process.env.QADAM_RUNTIME_DIR)
    : path.join(repoRoot, "data", "runtime");

function readJson(filename) {
    const artifactPath = path.join(runtimeDir, filename);
    assert(fs.existsSync(artifactPath), `missing runtime artifact ${filename}`);
    return JSON.parse(fs.readFileSync(artifactPath, "utf8"));
}

function clone(value) {
    return JSON.parse(JSON.stringify(value));
}

async function main() {
    const pattern = readJson("qadam_pattern_discovery_dashboard.json");
    const quantum = readJson("qadam_quantum_review_dashboard.json");
    const operator = readJson("qadam_operator_dashboard_view_model.json");
    const fixtureStatus = clone(status);
    fixtureStatus.qsase_dashboard = fixtureStatus.qsase_dashboard || {};
    fixtureStatus.qsase_dashboard.sections = fixtureStatus.qsase_dashboard.sections || {};
    fixtureStatus.qsase_dashboard.sections.operator_dashboard = operator;
    const rendered = await renderWithStatus(fixtureStatus);
    const stageHtml = html(rendered, "[data-stage7-dashboard-visibility]");

    [
        "Pattern Discovery",
        "Qualitative analysis",
        "What Qadam most recently noticed",
        "No repeatable historical edge has been validated yet",
        "Relationships mapped",
        "Eligible historical snapshots",
        "Under testing",
        "Where it goes next",
        "It advances when",
        "Quantum Edge"
    ].forEach((needle) => {
        assert(stageHtml.includes(needle), `pattern dashboard UI missing ${needle}`);
    });

    [
        "Pattern Recognition Findings",
        "Most actionable pattern",
        "No public explanation was exported for this review.",
        "8 completed reviews",
        "Technical evidence ledger"
    ].forEach((needle) => {
        assert(!stageHtml.includes(needle), `pattern dashboard UI still shows obsolete copy ${needle}`);
    });

    assert(pattern.artifact_type === "qadam_pattern_discovery_dashboard", "Pattern Discovery artifact type invalid");
    assert(pattern.relationship_count === pattern.relationships.length, "Pattern relationship count mismatch");
    assert(pattern.qualitative_analysis.bullet_count > 0, "Pattern qualitative bullets missing");
    assert(pattern.relationships.every((row) => row.raw_pattern_score_is_probability === false), "Pattern score probability boundary failed");
    assert(pattern.relationships.every((row) => row.current_stage && row.next_destination && row.advance_when.length), "Pattern advancement contract incomplete");
    assert(pattern.paper_order_allowed === false, "Pattern Discovery can create paper orders");
    assert(pattern.broker_write_allowed === false, "Pattern Discovery can write to broker");
    assert(pattern.live_capital_enabled === false, "Pattern Discovery can enable live capital");

    assert(quantum.artifact_type === "qadam_quantum_review_dashboard", "Quantum Review artifact type invalid");
    assert(quantum.empirical_comparison_count > 0, "Completed empirical comparisons are missing");
    assert(quantum.defined_protocol_count >= quantum.empirical_comparison_count, "Empirical comparisons exceed registered protocols");
    assert(quantum.defined_protocol_count > 0, "Quantum experiment protocols missing");
    assert(quantum.reviews.every((row) => ["classical_preferred", "not_measurable"].includes(row.verdict)), "Current quantum verdict is overstated");
    assert(quantum.reviews.every((row) => row.returned_to === "Pattern Recognition"), "Quantum review return path missing");
    assert(quantum.reviews.every((row) => row.classical_baseline?.name), "Matched classical baseline missing");
    assert(quantum.reviews.every((row) => row.hardware_used === false), "Simulator or inspired work reported as hardware execution");
    assert(quantum.paper_order_allowed === false, "Quantum Review can create paper orders");
    assert(quantum.broker_write_allowed === false, "Quantum Review can write to broker");
    assert(quantum.live_capital_enabled === false, "Quantum Review can enable live capital");

    console.log("dashboard_pattern_intelligence=ok");
    console.log(`pattern_relationship_count=${pattern.relationship_count}`);
    console.log(`recent_pattern_bullet_count=${pattern.qualitative_analysis.bullet_count}`);
    console.log(`quantum_protocol_count=${quantum.defined_protocol_count}`);
    console.log(`quantum_empirical_comparison_count=${quantum.empirical_comparison_count}`);
}

if (require.main === module) {
    main().catch((error) => {
        console.error(error.message);
        process.exitCode = 1;
    });
}
