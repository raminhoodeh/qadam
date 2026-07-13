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

function count(text, needle) {
    return text.split(needle).length - 1;
}

async function main() {
    const rendered = await renderWithStatus(status);
    const dashboard = html(rendered, "[data-stage7-dashboard-visibility]");
    const routes = [
        "system/team",
        "fund/portfolio",
        "fund/timeline",
        "observe/sources",
        "observe/universe",
        "patterns/findings",
        "patterns/nonlinear",
        "decide/strategies",
        "decide/decision",
        "trade/orders",
        "learn/outcomes",
        "learn/improvements",
        "system/overview"
    ];

    assert(count(dashboard, "data-qadam-lifecycle data-lifecycle-route=") === routes.length, "every route must render exactly one lifecycle");
    assert(count(dashboard, "data-qadam-lifecycle-trigger") === routes.length * 10, "every lifecycle must render exactly ten stage triggers");
    routes.forEach((route) => {
        assert(dashboard.includes(`data-lifecycle-route="${route}"`), `lifecycle route context missing ${route}`);
    });

    [
        "Observe the World",
        "Qualify the Evidence",
        "Discover Patterns",
        "Form Strategy Hypotheses",
        "Validate the Edge",
        "Filter Tradeability",
        "Govern the Decision",
        "Execute and Monitor",
        "Learn From the Outcome",
        "Improve and Re-enter"
    ].forEach((label) => assert(dashboard.includes(label), `lifecycle stage missing ${label}`));

    [
        "Cross-cutting across all 10 stages",
        "Stage 8 outcome mirror; supports stage 9",
        "Primary stage 1 of 10; supports stage 2",
        "Primary stages 4 and 5; supports stage 6",
        "Primary stages 6 and 7; supports stage 8",
        "Primary stage 10 of 10; returns to stage 1",
        "Monitors all 10 stages"
    ].forEach((label) => assert(dashboard.includes(label), `module relationship missing ${label}`));

    assert(!dashboard.includes("data-qsase-journey"), "legacy previous/next journey returned");
    assert(!dashboard.includes("data-qadam-learning-loop-overview"), "duplicated global learning map returned");
    assert(!dashboard.includes("End-to-End Operating Flow"), "duplicated System Overview flow returned");
    assert(!dashboard.includes("Decision Room introduction"), "duplicated Decision Room page guide returned");
    assert(count(dashboard, "data-qadam-local-stage-flow=") === 2, "Stage 9 and Stage 10 need one local sub-flow each");
    assert(count(dashboard, "data-qadam-lifecycle-health") === 1, "System Overview needs one stage-health matrix");
    assert(count(dashboard, "data-source-market-evidence-map=") === 1, "source-to-market map should render only once");
    assert(dashboard.includes("data-source-market-evidence-map=\"markets\""), "Trading Universe should own the detailed source-to-market map");
    assert(dashboard.includes("Stage 1 to Stage 2 handoff"), "Data Sources needs a compact evidence handoff");
    assert(dashboard.includes("Strategy Evidence Path"), "focused Stage 4-5 strategy path missing");

    [
        "function renderQadamLifecycleTimeline",
        "function initQsaseLifecycleDisclosures",
        "function closeQsaseLifecycleDisclosures",
        "data-qadam-lifecycle-close",
        "qadamLifecycleCloseBound",
        "aria-expanded=\"false\"",
        "aria-controls=",
        "aria-describedby=",
        "role=\"tooltip\"",
        "single_global_current_stage"
    ].forEach((needle) => assert(renderer.includes(needle), `lifecycle renderer contract missing ${needle}`));

    [
        ".qadam-lifecycle",
        ".qadam-lifecycle-track",
        ".qadam-lifecycle-tooltip",
        ".qadam-lifecycle-close",
        ".qadam-lifecycle-health-table",
        ".qadam-local-stage-flow",
        "prefers-reduced-motion",
        "@media print",
        "scroll-snap-type"
    ].forEach((needle) => assert(css.includes(needle), `lifecycle style missing ${needle}`));
    assert(renderer.includes('classList.add("suppress-preview")'), "Escape preview suppression is missing");
    assert(renderer.includes('classList.remove("suppress-preview")'), "preview suppression reset is missing");
    assert(css.includes(".qadam-lifecycle-stage:not(.suppress-preview):focus-within .qadam-lifecycle-tooltip"), "keyboard focus preview is missing");
    assert(css.includes(".qadam-lifecycle-stage:not(.is-open):hover .qadam-lifecycle-tooltip"), "mobile tap must suppress the transient hover sheet until disclosure opens");
    assert(css.includes(".qadam-lifecycle-stage:not(.is-open):focus-within .qadam-lifecycle-tooltip"), "mobile tap must suppress the transient focus sheet until disclosure opens");

    const lifecycle = operator.end_to_end_lifecycle || {};
    assert(operator.navigation_contract?.contract_version === "qadam_protected_decision_flow.v5", "V5 navigation contract missing");
    assert(operator.navigation_contract?.lifecycle_timeline_required === true, "lifecycle timeline requirement missing");
    assert(operator.navigation_contract?.previous_next_journey_required === false, "legacy journey should no longer be required");
    assert(lifecycle.stage_count === 10, "operator lifecycle should contain ten stages");
    assert(lifecycle.route_count === routes.length, "operator lifecycle should map every route");
    assert(lifecycle.single_global_current_stage === false, "operator lifecycle must not claim one global stage");
    assert(lifecycle.paper_order_created_count === 0, "lifecycle projection created a paper order");
    assert(lifecycle.broker_write_count === 0, "lifecycle projection wrote to a broker");
    assert(lifecycle.proof_credit_allowed === false, "lifecycle projection granted proof credit");
    assert(lifecycle.live_capital_enabled === false, "lifecycle projection enabled live capital");

    console.log("dashboard_ten_stage_lifecycle=ok");
    console.log(`dashboard_lifecycle_route_count=${routes.length}`);
    console.log(`dashboard_lifecycle_stage_node_count=${routes.length * 10}`);
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
