#!/usr/bin/env node
const { assert, html, renderWithStatus, status } = require("./check_dashboard_renderer");

async function main() {
    const snapshot = JSON.parse(JSON.stringify(status));
    snapshot.qsase_dashboard.sections.operator_dashboard = {
        views: { "decide/decision": {
            strategy_decision: {
                schema_version: "qadam_strategy_decision.v1",
                policy_version: "qadam-autonomous-paper.1",
                decision_owner: "qadam_autonomous",
                akber_authority_retired: true,
                implementation_complete: true
            },
            strategy_decision_results: [{
                strategy_decision_id: "test-only",
                decision_owner: "qadam_autonomous",
                policy_version: "qadam-autonomous-paper.1",
                akber_authority_retired: true,
                hypothesis_id: "<script>unsafe</script>",
                decision: "pass", plain_english_explanation: "Test selection"
            }]
        } }
    };
    const selector = "[data-stage7-dashboard-visibility]";
    const current = html(await renderWithStatus(snapshot), selector);
    assert(current.includes("Qadam Strategy Decisions"), "missing current decision section");
    assert(current.includes("1 current decision"), "current result missing");
    assert(current.includes("&lt;script&gt;unsafe&lt;/script&gt;"), "unescaped result");
    assert(!current.includes("<script>unsafe"), "unsafe markup rendered");
    if (process.env.QADAM_UI_FIXTURE_OUTPUT) {
        const section = current.match(/<section[^>]*data-qadam-strategy-decisions>[\s\S]*?<\/section>/)[0];
        require("node:fs").writeFileSync(process.env.QADAM_UI_FIXTURE_OUTPUT,
            `<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>Qadam test fixture</title>
            <link rel="stylesheet" href="http://127.0.0.1:8765/auth.css">
            <body class="qadam-dashboard-page"><main class="dashboard-shell qadam-dashboard-shell is-wide"><h1>Test fixture only</h1>
            <div class="qsase-decision-room">${section}</div></main>`);
    }
    snapshot.qsase_dashboard.sections.operator_dashboard.views["decide/decision"].strategy_decision.policy_version = "retired";
    const retired = html(await renderWithStatus(snapshot), selector);
    assert(retired.includes("AWAITING CURRENT POLICY"), "retired policy appeared current");
    assert(!retired.includes("Test selection"), "retired selection was displayed");
    console.log("Qadam strategy decision UI checks passed");
}

main().catch(error => { console.error(error); process.exitCode = 1; });
