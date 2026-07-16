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
const siteRoot = path.resolve(
    process.env.QADAM_DASHBOARD_SITE_ROOT || path.join(repoRoot, "landing-page-repo")
);
const runtimeDir = process.env.QADAM_RUNTIME_DIR
    ? path.resolve(process.env.QADAM_RUNTIME_DIR)
    : path.join(repoRoot, "data", "runtime");
const renderer = fs.readFileSync(path.join(siteRoot, "dashboard.js"), "utf8");
const css = fs.readFileSync(path.join(siteRoot, "auth.css"), "utf8");
const operator = JSON.parse(
    fs.readFileSync(path.join(runtimeDir, "qadam_operator_dashboard_view_model.json"), "utf8")
);

function learningPanel(dashboard, viewId) {
    const marker = `data-qsase-module-panel="learn" data-qsase-view-panel="${viewId}"`;
    const start = dashboard.indexOf(marker);
    assert(start >= 0, `learning panel ${viewId} could not be isolated`);
    const next = dashboard.indexOf("data-qsase-module-panel=", start + marker.length);
    return dashboard.slice(start, next > start ? next : dashboard.length);
}

function assertTooltipIntegrity(dashboard) {
    const tooltipKeys = [...dashboard.matchAll(/data-learning-tooltip="([^"]+)"/g)].map((match) => match[1]);
    const tooltipIds = [...dashboard.matchAll(/id="(qsase-learning-tip-[^"]+)"/g)].map((match) => match[1]);
    const describedIds = [...dashboard.matchAll(/aria-describedby="(qsase-learning-tip-[^"]+)"/g)].map((match) => match[1]);
    const uniqueIds = new Set(tooltipIds);

    assert(tooltipKeys.length >= 25, `learning UI should expose explanatory tooltips throughout, found ${tooltipKeys.length}`);
    assert(uniqueIds.size === tooltipIds.length, "learning tooltip IDs must be unique");
    assert(describedIds.length === tooltipIds.length, "every learning tooltip must have one labelled trigger");
    describedIds.forEach((id) => assert(uniqueIds.has(id), `learning tooltip trigger points to missing target ${id}`));
}

async function main() {
    const rendered = await renderWithStatus(status);
    const dashboard = html(rendered, "[data-stage7-dashboard-visibility]");
    const outcomesPanel = learningPanel(dashboard, "outcomes");
    const improvementsPanel = learningPanel(dashboard, "improvements");

    [
        "Results &amp; Lessons",
        "Tests &amp; Improvements",
        "data-qadam-results-lessons",
        "data-qadam-tests-improvements"
    ].forEach((needle) => assert(dashboard.includes(needle), `consolidated learning navigation missing ${needle}`));

    [
        "Performance Attribution &amp; Governance",
        "What Qadam Learned",
        "What happened, and what can Qadam legitimately learn?",
        "How a trade outcome turns into a supported lesson +",
        "data-qadam-local-stage-flow=\"stage-9\"",
        "Inside Stage 9: turn outcomes into supported lessons",
        "What Qadam is learning",
        "Lessons proved so far",
        "Past History Kept for Reference",
        "Outcome or research event",
        "Supported lesson",
        "Original expectation",
        "Actual result",
        "Financial result",
        "Evidence contribution",
        "Lesson confidence",
        "Next test",
        "Destination",
        "data-qadam-learning-feed",
        "data-qadam-reference-history",
        "data-qadam-learning-communications",
        "Technical evidence +"
    ].forEach((needle) => assert(outcomesPanel.includes(needle), `Results & Lessons missing ${needle}`));

    [
        "Strategy &amp; System Improvement",
        "How Qadam Improves",
        "Has that lesson earned the right to change Qadam’s behaviour?",
        "How a supported lesson becomes a strategy or system improvement +",
        "data-qadam-local-stage-flow=\"stage-10\"",
        "Inside Stage 10: test improvements before Qadam changes",
        "Supported lesson",
        "Proposed improvement",
        "Historical and real-time testing",
        "Approve, reject, or keep testing",
        "New strategy or system version",
        "What Qadam is testing",
        "Improvements proved so far",
        "Improvements now in use",
        "data-qadam-improvement-workspace",
        "data-qadam-change-readiness",
        "Can Qadam change yet?",
        "Improvements being tested",
        "Success criteria",
        "Rejection criteria",
        "Rollback condition",
        "Testing evidence and technical detail +",
        "What changes in the next cycle?",
        "Nothing yet.",
        "data-qadam-learning-diagnostics",
        "data-qadam-stage1-feedback"
    ].forEach((needle) => assert(improvementsPanel.includes(needle), `Tests & Improvements missing ${needle}`));

    assert(
        (dashboard.match(/data-qadam-local-stage-flow=/g) || []).length === 2,
        "both learning pages must render exactly one stage-specific local flow"
    );
    assert(
        (outcomesPanel.match(/data-qadam-learning-field=/g) || []).length >= 10,
        "each visible learning record should expose the complete outcome-to-lesson story"
    );
    assert(!improvementsPanel.includes("data-qadam-stage1-destination"), "a destination appeared without an applied learning version");
    assert(!dashboard.includes("data-qadam-learning-loop-overview"), "duplicated full learning overview returned");
    assert(!dashboard.includes('class="qsase-improvement-pipeline"'), "competing improvement pipeline strip returned");
    assert(!dashboard.includes('data-qsase-view-panel="replay"'), "legacy replay panel returned");
    assert(!dashboard.includes('data-qsase-view-panel="briefs"'), "legacy briefs panel returned");
    assert(renderer.includes('candidate === "learn/replay"'), "replay alias missing");
    assert(renderer.includes('candidate === "learn/briefs"'), "brief alias missing");
    assertTooltipIntegrity(`${outcomesPanel}${improvementsPanel}`);

    [
        "Stage 10.2 · Historical test",
        "Stage 10.3 · Forward observation",
        "Stage 10.4 · Review",
        "Stage 10.5 · Implementation route",
        "Stage 10.6 · Return to Stage 1",
        "const QSASE_LEARNING_TOOLTIPS",
        "function renderQsaseLearningTooltip",
        "function renderQsaseLearningPageHeader",
        "function renderQsaseChangeReadinessRail",
        "function renderQsaseImprovementJourney"
    ].forEach((needle) => assert(renderer.includes(needle), `learning renderer missing ${needle}`));

    [
        ".qsase-learning-page-header",
        ".qsase-learning-governing-question",
        ".qsase-learning-help",
        ".qsase-learning-help-card",
        ".qsase-learning-help:focus-within",
        ".qsase-learning-workflow-disclosure",
        ".qsase-learning-current-grid",
        ".qsase-learning-summary-groups",
        ".qsase-learning-event-body > article",
        ".qsase-learning-technical-evidence",
        ".qsase-improvement-journey",
        ".qsase-improvement-workspace",
        ".qsase-change-readiness",
        ".qsase-improvement-evidence-path",
        ".qsase-improvement-decision-criteria",
        ".qsase-stage1-no-destination"
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

    const appliedFixture = JSON.parse(JSON.stringify(status));
    const fixtureImprovement = appliedFixture.qsase_dashboard?.sections?.operator_dashboard?.views?.["learn/improvements"];
    assert(fixtureImprovement, "applied-version fixture is missing the canonical improvements view");
    fixtureImprovement.counts.applied_version_count = 1;
    fixtureImprovement.applied_versions = [{
        applied_version: "learning-v1",
        change_hypothesis: "Use the approved evidence-quality rule in the next Observe cycle.",
        effective_from: "2026-07-16T12:30:00Z",
        monitoring_window: "30 real calendar days",
        rollback_condition: "Rollback if evidence quality deteriorates."
    }];
    fixtureImprovement.stage1_learning_input.applied_handoff_count = 1;
    fixtureImprovement.stage1_learning_input.applied_learning_version_ids = ["learning-v1"];
    fixtureImprovement.stage1_learning_input.handoffs = [{
        applied_version: "learning-v1",
        target_stage: "patterns"
    }];
    fixtureImprovement.stage1_learning_input.next_cycle_behavior = "The next Observe cycle records learning-v1 in downstream lineage.";
    fixtureImprovement.current_answer = "One approved learning version can now enter the next Observe cycle.";

    const appliedRendered = await renderWithStatus(appliedFixture);
    const appliedDashboard = html(appliedRendered, "[data-stage7-dashboard-visibility]");
    const appliedPanel = learningPanel(appliedDashboard, "improvements");
    assert(appliedPanel.includes("Yes. An approved version is ready for the next Observe cycle."), "applied-version readiness answer did not render");
    assert(appliedPanel.includes("data-qadam-stage1-destination"), "approved version did not expose its Stage 1 destination");
    assert(appliedPanel.includes("learning-v1"), "approved learning version ID is missing from the destination");

    console.log("dashboard_learn_improve_consolidation=ok");
    console.log(`learning_reference_only_count=${outcomes.counts?.mirror_reference_count || 0}`);
    console.log(`improvement_active_count=${improvements.counts?.active_candidate_count || 0}`);
    console.log(`learning_tooltip_count=${(dashboard.match(/data-learning-tooltip=/g) || []).length}`);
    console.log(`applied_learning_version_count=${improvements.stage1_learning_input?.applied_handoff_count || 0}`);
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
