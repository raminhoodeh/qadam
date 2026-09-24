#!/usr/bin/env node
const { assert, html, renderWithStatus, status } = require("./check_dashboard_renderer.js");

async function main() {
    const rendered = await renderWithStatus(status);
    const dashboard = html(rendered, "[data-stage7-dashboard-visibility]");
    const start = dashboard.indexOf('data-qsase-module-panel="decide" data-qsase-view-panel="decision"');
    const end = dashboard.indexOf('data-qsase-module-panel="trade" data-qsase-view-panel="orders"', start);
    assert(start >= 0 && end > start, "Decision Room route missing");
    const decision = dashboard.slice(start, end);
    [
        "INVESTMENT COMMITTEE GOVERNANCE", "Decision Room",
        "Qadam owns paper-strategy selection.", "It cannot submit orders or change limits.",
        "1. Research Pipelines Approaching Gate", "2. Qadam Strategy Decisions",
        "3. Ultimate Committee Verdict", "Akber is retired.",
        "Missing optional confirmation reduces size.", "Paper Route Status:",
        "PaperOps Handoffs", "Broker Writes", "Review Archive",
    ].forEach(text => assert(decision.includes(text), "Decision Room missing " + text));
    assert(!decision.includes("data-qsase-akber-stage="), "Retired checklist still active");
    assert(!decision.includes("data-qsase-akber-explainer"), "Retired filter presented as current policy");
    assert((decision.match(/data-qsase-decision-research-idea/g) || []).length === 5,
        "Research relationships disappeared");
    const evidence = decision.indexOf('data-qsase-section="decision_research_pipeline"');
    const selection = decision.indexOf("data-qadam-strategy-decisions");
    const verdict = decision.indexOf('data-qsase-section="router_paperops_gate"');
    assert(evidence >= 0 && evidence < selection && selection < verdict,
        "Expected research, Qadam selection, then guarded Router verdict");
    ["execution approval", "risk approval", "capital allocation authority", "broker write authority", "paper order authority"]
        .forEach(claim => assert(!decision.toLowerCase().includes("has " + claim), "Unsafe UI authority: " + claim));
    console.log("dashboard_decision_room_governance=ok; Akber retired; broker authority unchanged");
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
