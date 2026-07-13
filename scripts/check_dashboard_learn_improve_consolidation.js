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
const renderer = fs.readFileSync(path.join(repoRoot, "landing-page-repo", "dashboard.js"), "utf8");
const css = fs.readFileSync(path.join(repoRoot, "landing-page-repo", "auth.css"), "utf8");
const operator = JSON.parse(
    fs.readFileSync(path.join(repoRoot, "data", "runtime", "qadam_operator_dashboard_view_model.json"), "utf8")
);

async function main() {
    const rendered = await renderWithStatus(status);
    const dashboard = html(rendered, "[data-stage7-dashboard-visibility]");

    [
        "Results &amp; Lessons",
        "Tests &amp; Improvements",
        "What Qadam Learned",
        "How Qadam Improves",
        "data-qadam-results-lessons",
        "data-qadam-local-stage-flow=\"stage-9\"",
        "data-qadam-local-stage-flow=\"stage-10\"",
        "Inside Stage 9: turn outcomes into supported lessons",
        "Inside Stage 10: test improvements before Qadam changes",
        "Outcome or research event",
        "Supported lesson",
        "Proposed improvement",
        "Historical test",
        "Forward observation",
        "Stage 10.4 · Review",
        "Stage 10.5 · Applied version",
        "Stage 10.6 · Next Observe cycle",
        "data-qadam-learning-feed",
        "data-qadam-reference-history",
        "data-qadam-learning-communications",
        "data-qadam-tests-improvements",
        "data-qadam-stage1-feedback",
        "data-qadam-learning-diagnostics",
        "Only an approved version can return to Observe"
    ].forEach((needle) => assert(dashboard.includes(needle), `consolidated learning UI missing ${needle}`));

    assert(
        (dashboard.match(/data-qadam-local-stage-flow=/g) || []).length === 2,
        "both learning pages must render one stage-specific local flow"
    );
    assert(!dashboard.includes("data-qadam-learning-loop-overview"), "duplicated full learning overview returned");
    assert(!dashboard.includes('class="qsase-improvement-pipeline"'), "competing seven-step improvement strip returned");

    assert(!dashboard.includes('data-qsase-view-panel="replay"'), "legacy replay panel returned");
    assert(!dashboard.includes('data-qsase-view-panel="briefs"'), "legacy briefs panel returned");
    assert(renderer.includes('candidate === "learn/replay"'), "replay alias missing");
    assert(renderer.includes('candidate === "learn/briefs"'), "brief alias missing");

    [
        ".qsase-learning-answer",
        ".qsase-learning-event",
        ".qadam-local-stage-flow",
        ".qsase-improvement-proposal",
        ".qsase-stage1-feedback",
        ".qsase-learning-disclosure"
    ].forEach((needle) => assert(css.includes(needle), `learning UI CSS missing ${needle}`));

    const contract = operator.navigation_contract || {};
    const outcomes = operator.views?.["learn/outcomes"] || {};
    const improvements = operator.views?.["learn/improvements"] || {};
    assert(contract.contract_version === "qadam_protected_decision_flow.v5", "V5 route contract missing");
    assert(contract.route_count === 13, "V5 route contract should contain 13 routes");
    assert(outcomes.artifact_type === "qadam_learning_cycle_dashboard", "canonical Results & Lessons model missing");
    assert(improvements.artifact_type === "qadam_improvement_pipeline_dashboard", "canonical Tests & Improvements model missing");
    assert(outcomes.loop_overview?.steps?.length === 8, "Results & Lessons loop contract should have eight stages");
    assert(improvements.loop_overview?.steps?.length === 8, "Tests & Improvements loop contract should have eight stages");
    assert(
        JSON.stringify(outcomes.loop_overview?.steps) === JSON.stringify(improvements.loop_overview?.steps),
        "learning pages must use the same stage contract"
    );
    assert(outcomes.counts?.mirror_reference_count === outcomes.reference_records?.length, "reference-only count mismatch");
    assert(improvements.counts?.excluded_mirror_record_count === outcomes.counts?.mirror_reference_count, "mirror exclusion mismatch");
    assert((improvements.stage1_learning_input?.applied_handoff_count || 0) === 0, "unapproved learning reached Stage 1");

    console.log("dashboard_learn_improve_consolidation=ok");
    console.log(`learning_reference_only_count=${outcomes.counts?.mirror_reference_count || 0}`);
    console.log(`improvement_active_count=${improvements.counts?.active_candidate_count || 0}`);
    console.log(`applied_learning_version_count=${improvements.stage1_learning_input?.applied_handoff_count || 0}`);
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
