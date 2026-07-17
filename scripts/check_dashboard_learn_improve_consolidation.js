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

function pageBody(panel, marker) {
    const start = panel.indexOf(marker);
    assert(start >= 0, `page body ${marker} could not be isolated`);
    return panel.slice(start);
}

function countMatches(value, expression) {
    return (String(value).match(expression) || []).length;
}

function assertClosedDisclosures(page, keys) {
    keys.forEach((key) => {
        const tag = page.match(new RegExp(`<details[^>]*data-qadam-learning-disclosure-key="${key}"[^>]*>`, "i"));
        assert(tag, `disclosure ${key} missing`);
        assert(!/\sopen(?:\s|=|>)/i.test(tag[0]), `disclosure ${key} should be closed on route entry`);
    });
}

function assertNoCopy(page, phrases, pageName) {
    phrases.forEach((phrase) => assert(!page.includes(phrase), `${pageName} retained forbidden copy: ${phrase}`));
}

async function main() {
    const rendered = await renderWithStatus(status);
    const dashboard = html(rendered, "[data-stage7-dashboard-visibility]");
    const outcomesPanel = learningPanel(dashboard, "outcomes");
    const improvementsPanel = learningPanel(dashboard, "improvements");
    const outcomes = pageBody(outcomesPanel, "data-qadam-results-lessons");
    const improvements = pageBody(improvementsPanel, "data-qadam-tests-improvements");

    [
        "Results &amp; Lessons",
        "Tests &amp; Improvements",
        "data-qadam-results-lessons",
        "data-qadam-tests-improvements"
    ].forEach((needle) => assert(dashboard.includes(needle), `two-page learning navigation missing ${needle}`));

    [
        "Performance Attribution &amp; Governance",
        "What Qadam Learned",
        "The Learning Engine looks backward: Qadam separates its own attributable outcomes from reference history, compares expectation with reality, and records only lessons the evidence can support.",
        "How an outcome becomes a supported lesson +",
        "Attribution status",
        "Waiting for the first complete Qadam paper outcome",
        "What Qadam is learning",
        "Verified lessons",
        "Reference trade history",
        "Learning Reviews (2) +",
        "Reference Broker History (42) +",
        "Continue to Tests &amp; Improvements",
        "See whether a supported lesson survives testing, review, and version approval before it can change Qadam."
    ].forEach((needle) => assert(outcomes.includes(needle), `Results & Lessons missing ${needle}`));

    assert(countMatches(outcomes, /data-learning-counter=/g) === 3, "Results & Lessons must render exactly three counters");
    assert(countMatches(outcomes, /qsase-learning-v2-repository"/g) === 2, "Results & Lessons must render exactly two repositories");
    assert(countMatches(outcomes, /data-qadam-learning-disclosure-key=/g) === 3, "Results & Lessons must render one explainer and two repositories");
    assertClosedDisclosures(outcomes, ["learning_scope", "learning_reviews", "reference_history"]);
    assert(outcomes.includes('data-qsase-progressive-list="learning_reviews"'), "learning review pagination missing");
    assert(outcomes.includes('data-qsase-progressive-list="reference_history"'), "reference history pagination missing");
    assert(outcomes.includes('data-qsase-page-size="7"'), "seven-record page size missing");
    assert(countMatches(outcomes, /<details/g) === 3, "Results & Lessons contains a nested disclosure hierarchy");
    assert(countMatches(outcomes, /qsase-learning-v2-handoff/g) === 1, "Results & Lessons must own exactly one bottom handoff");
    assert(outcomes.indexOf("qsase-learning-v2-handoff") > outcomes.indexOf("reference_history"), "Results & Lessons handoff is not last");

    assertNoCopy(outcomes, [
        "Stage 9",
        "Latest learning brief",
        "Idle State (Zero Track Record)",
        "Verified Algorithmic Proof",
        "Quarantined Broker Mirror Archive",
        "data contamination",
        "live pipeline outcomes",
        "proof credit",
        "Inside Stage 9",
        "Handoff to Stage 10",
        "data-qadam-learning-feed",
        "data-qadam-learning-communications"
    ], "Results & Lessons");

    [
        "Tests &amp; Improvements",
        "What Will Change in Qadam",
        "See which improvements are approved for integration, which are still being evaluated, and which changes are already in use.",
        "How a lesson earns the right to change Qadam +",
        "Integration status",
        "Nothing is currently scheduled to change",
        "Next Qadam Version",
        "No approved changes are scheduled",
        "Scheduled for integration",
        "Still under evaluation",
        "Already integrated",
        "Possible Future Improvements (1) +",
        "Previous Improvement Decisions (1) +",
        "Operational evidence improvement",
        "Historical evidence testing has not started.",
        "Next cycle: No change",
        "Return to Fund Overview"
    ].forEach((needle) => assert(improvements.includes(needle), `Tests & Improvements missing ${needle}`));

    assert(countMatches(improvements, /data-learning-counter=/g) === 3, "Tests & Improvements must render exactly three counters");
    assert(countMatches(improvements, /qsase-learning-v2-repository"/g) === 2, "Tests & Improvements must render exactly two repositories");
    assert(countMatches(improvements, /data-qadam-learning-disclosure-key=/g) === 3, "Tests & Improvements must render one explainer and two repositories");
    assertClosedDisclosures(improvements, ["improvement_scope", "possible_future_improvements", "previous_improvement_decisions"]);
    assert(countMatches(improvements, /<details/g) === 3, "Tests & Improvements contains a nested disclosure hierarchy");
    assert(improvements.includes('data-qadam-improvement-toggle='), "flat proposal detail control missing");
    assert(improvements.includes('aria-expanded="false"'), "proposal detail should be collapsed by default");
    assert(improvements.includes('data-qsase-progressive-list="possible_future_improvements"'), "future improvement pagination missing");
    assert(improvements.includes('data-qsase-progressive-list="previous_improvement_decisions"'), "decision history pagination missing");
    assertNoCopy(improvements, [
        "Stage 10",
        "Inside Stage 10",
        "Stage 10.1",
        "Stage 10.2",
        "Stage 10.3",
        "Stage 10.4",
        "Stage 10.5",
        "Stage 10.6",
        "inert_until_applied",
        "not_started_no_eligible_hypothesis",
        "provider partitions",
        "statistical paths attempted",
        "Supporting check - Quantum usefulness",
        "Return to Stage 1",
        "Cannot affect Qadam yet",
        "data-qadam-improvement-workspace",
        "data-qadam-learning-diagnostics",
        "data-qadam-stage1-feedback"
    ], "Tests & Improvements");

    [
        "function qsaseResultsPresentation",
        "function qsaseImprovementsPresentation",
        "function resetQsaseLearnPageState",
        "function initQsaseLearnV2Interactions",
        "data-qsase-progressive-no-collapse",
        "qadam.dashboard.learn.expanded",
        "ownsPageHandoff"
    ].forEach((needle) => assert(renderer.includes(needle), `learning interaction contract missing ${needle}`));

    [
        ".qsase-learning-page-v2",
        ".qsase-learning-v2-answer",
        ".qsase-learning-v2-counters",
        ".qsase-learning-v2-repository",
        ".qsase-improvement-v2-gates",
        "@media (max-width: 640px)",
        "@media (prefers-reduced-motion: reduce)",
        "@media print"
    ].forEach((needle) => assert(css.includes(needle), `learning V2 CSS missing ${needle}`));

    const contract = operator.navigation_contract || {};
    const outcomeModel = operator.views?.["learn/outcomes"] || {};
    const improvementModel = operator.views?.["learn/improvements"] || {};
    assert(contract.contract_version === "qadam_protected_decision_flow.v5", "V5 route contract missing");
    assert(contract.route_count === 13, "protected route contract should contain 13 routes");
    assert(outcomeModel.presentation_contract_version === "qadam_results_lessons.v2", "Results presentation contract missing");
    assert(improvementModel.presentation_contract_version === "qadam_tests_improvements.v2", "Improvements presentation contract missing");
    assert(outcomeModel.metric_groups?.length === 3, "Results model should export three counters");
    assert(Object.keys(outcomeModel.repositories || {}).length === 2, "Results model should export two repositories");
    assert(outcomeModel.counts?.mirror_reference_count === outcomeModel.repositories?.reference_history?.records?.length, "reference history count mismatch");
    assert(outcomeModel.repositories?.reference_history?.records?.every((row) => row.learnable === false && row.proof_eligible === false), "reference records gained learning authority");
    assert(improvementModel.metric_groups?.length === 3, "Improvement model should export three counters");
    assert(Object.keys(improvementModel.repositories || {}).length === 2, "Improvement model should export two repositories");
    assert(improvementModel.counts?.scheduled_integration_count === 0, "incomplete proposal rendered as scheduled");
    assert(improvementModel.counts?.under_evaluation_count === 1, "current operational proposal classification drifted");
    assert(improvementModel.repositories?.possible_future_improvements?.records?.every((row) => row.public_state === "under_evaluation"), "future repository contains a non-evaluation record");
    assert((improvementModel.stage1_learning_input?.applied_handoff_count || 0) === 0, "unapproved learning reached the next Observe cycle");

    const staleFixture = JSON.parse(JSON.stringify(status));
    const staleOutcome = staleFixture.qsase_dashboard.sections.operator_dashboard.views["learn/outcomes"];
    staleOutcome.immediate_answer = {
        state: "status_unavailable",
        tone: "unavailable",
        eyebrow: "Attribution status",
        headline: "Learning status is temporarily unavailable",
        summary: "Qadam cannot confirm a current learning answer because the public projection is outside its freshness policy. Last known records remain read-only until the projection refreshes."
    };
    staleOutcome.metric_groups.forEach((metric) => { metric.value = null; });
    const staleRendered = await renderWithStatus(staleFixture);
    const staleBody = pageBody(learningPanel(html(staleRendered, "[data-stage7-dashboard-visibility]"), "outcomes"), "data-qadam-results-lessons");
    assert(staleBody.includes("Learning status is temporarily unavailable"), "stale Results answer did not render");
    assert(countMatches(staleBody, /Not available/g) >= 3, "stale Results metrics inferred false zeroes");

    console.log("dashboard_learn_improve_simplification=ok");
    console.log(`learning_review_count=${outcomeModel.counts?.learnable_event_count}`);
    console.log(`learning_reference_only_count=${outcomeModel.counts?.mirror_reference_count}`);
    console.log(`improvement_scheduled_count=${improvementModel.counts?.scheduled_integration_count}`);
    console.log(`improvement_under_evaluation_count=${improvementModel.counts?.under_evaluation_count}`);
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
