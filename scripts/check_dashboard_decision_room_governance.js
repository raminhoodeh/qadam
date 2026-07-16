#!/usr/bin/env node

const {
    assert,
    html,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

function decisionRoomHtml(rendered) {
    const dashboard = html(rendered, "[data-stage7-dashboard-visibility]");
    const start = dashboard.indexOf('data-qsase-module-panel="decide" data-qsase-view-panel="decision"');
    const end = dashboard.indexOf('data-qsase-module-panel="trade" data-qsase-view-panel="orders"', start);
    assert(start >= 0 && end > start, "Decision Room route is missing from the rendered dashboard");
    return dashboard.slice(start, end);
}

function assertIncludesAll(text, needles) {
    needles.forEach((needle) => assert(text.includes(needle), `Decision Room missing ${needle}`));
}

function assertClosedDetails(text, attribute, label) {
    const tag = text.match(new RegExp(`<details\\b[^>]*${attribute}[^>]*>`));
    assert(tag, `${label} disclosure is missing`);
    assert(!/\sopen(?:\s|=|>)/.test(tag[0]), `${label} disclosure must be collapsed by default`);
}

async function main() {
    const rendered = await renderWithStatus(status);
    const decision = decisionRoomHtml(rendered);

    assertIncludesAll(decision, [
        "INVESTMENT COMMITTEE GOVERNANCE",
        "Decision Room",
        "A read-only governance projection. This room aggregates active research, Akber's 6-Stage Filter, and downstream router data to audit fund readiness. This interface holds no execution, broker-write, or capital-allocation authority.",
        "What is Akber's 6-Stage Filter and how does it evaluate an edge?",
        "Explicit adverse evidence",
        "Missing required evidence",
        "Hold (Missing Context)",
        "All required evidence clean",
        "1. Research Pipelines Approaching Gate",
        "EVIDENCE",
        "Active research pipelines approaching a decision, currently awaiting processing by Akber's 6-Stage Filter (Stage 6 of the 10-stage lifecycle).",
        "Eligible Historical Snapshots</dt><dd>0",
        "Completed Backtests</dt><dd>0",
        "Validated Edges</dt><dd>0",
        "2. Post-Filter Pipeline &amp; Current Candidates",
        "CONSEQUENCE",
        "0 Active Candidates in Queue",
        "Stage 1 (Context) Holds/Vetoes: 0",
        "Stage 2 (Catalyst) Holds/Vetoes: 0",
        "Stage 3 (Confirmation) Holds/Vetoes: 0",
        "Stage 4 (Risk) Holds/Vetoes: 0",
        "Stage 5 (Execution) Holds/Vetoes: 0",
        "Passed to Stage 6 Forward-Shadowing: 0",
        "PaperOps Handoffs</dt><dd>0",
        "Paper Orders</dt><dd>0",
        "Broker Writes</dt><dd>0",
        "Paper Route Status: WATCH-ONLY (Research Lock Active)",
        "3. Ultimate Committee Verdict",
        "DECISION",
        "WAIT — no validated idea is ready for paper-trade review.",
        "Review Archive: 16 Previous Decision Reviews",
        "14 Holds",
        "2 Safety Stops",
        "Refreshes automatically every 15 seconds. Expanded container states are preserved across live intervals."
    ]);

    assert((decision.match(/data-qsase-decision-research-idea/g) || []).length === 5, "Decision Room must show five under-testing research relationships");
    assert((decision.match(/data-qsase-akber-stage=/g) || []).length === 6, "Akber matrix must show six auditable buckets");
    assert((decision.match(/data-qsase-decision-candidate=/g) || []).length === 0, "zero validated edges must not render a current candidate");
    assertClosedDetails(decision, "data-qsase-akber-explainer", "Akber educational");
    assertClosedDetails(decision, "data-qsase-previous-decision-reviews", "Review Archive");

    const overview = decision.indexOf('data-qsase-section="akber_explainer"');
    const evidence = decision.indexOf('data-qsase-section="decision_research_pipeline"');
    const consequence = decision.indexOf('data-qsase-section="trade_intents"');
    const verdict = decision.indexOf('data-qsase-section="router_paperops_gate"');
    assert(
        overview >= 0 && overview < evidence && evidence < consequence && consequence < verdict,
        "Decision Room order must be governance overview, evidence, consequence, then decision"
    );

    [
        "execution approval",
        "risk approval",
        "capital allocation authority",
        "broker write authority",
        "paper order authority"
    ].forEach((unsafeClaim) => {
        assert(!decision.toLowerCase().includes(`has ${unsafeClaim}`), `Decision Room implies unsafe authority: ${unsafeClaim}`);
    });

    console.log("dashboard_decision_room_governance=ok");
    console.log("research_relationship_count=5");
    console.log("validated_edge_count=0");
    console.log("active_candidate_count=0");
    console.log("archived_review_count=16");
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
