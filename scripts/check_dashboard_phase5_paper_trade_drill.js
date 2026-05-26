#!/usr/bin/env node

const {
    assert,
    assertIncludes,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

async function main() {
    const drill = status.phase5_paper_trade_drill || {};
    assert(drill.phase === "Q5", "paper trade drill phase mismatch");
    assert(drill.stage === "Q5-14", "paper trade drill stage mismatch");
    assert(drill.status === "ok", "paper trade drill status mismatch");
    assert(drill.recorded === true, "paper trade drill not recorded");
    assert(drill.public_safe === true, "paper trade drill not public-safe");
    assert(drill.phase5_paper_trade_drill_implementation_ready === true, "paper trade drill implementation not ready");
    const drillComplete = drill.paper_trade_drill_complete === true;
    assert(
        drill.phase5_paper_trade_drill_exit_gate_passed === drillComplete,
        "paper trade drill exit gate/complete mismatch"
    );
    const approvalPresent = drill.paper_submit_approval_present === true;
    if (approvalPresent) {
        assert(drill.paper_submit_approval_state === "approved", "paper trade drill approval state mismatch");
        assert(!drill.blockers.includes("paper_submit_approval_missing"), "paper trade drill still reports missing approval");
    } else {
        assert(drill.blockers.includes("paper_submit_approval_missing"), "paper trade drill missing approval blocker");
    }
    if (drill.paper_submit_path_available_count > 0) {
        assert(!drill.blockers.includes("paper_submit_path_unavailable"), "paper trade drill still reports submit path unavailable");
    } else {
        assert(drill.blockers.includes("paper_submit_path_unavailable"), "paper trade drill missing submit path blocker");
    }
    if (drill.submitted_paper_order_count > 0) {
        assert(!drill.blockers.includes("submitted_paper_order_missing"), "paper trade drill still reports missing submitted order");
    } else {
        assert(drill.blockers.includes("submitted_paper_order_missing"), "paper trade drill missing submitted-order blocker");
    }
    if (drill.open_position_count > 0 || drill.closed_trade_count > 0) {
        assert(!drill.blockers.includes("open_position_missing"), "paper trade drill still reports missing open position");
    } else {
        assert(drill.blockers.includes("open_position_missing"), "paper trade drill missing open-position blocker");
    }
    if (drill.closed_trade_count > 0) {
        assert(!drill.blockers.includes("closed_trade_missing"), "paper trade drill still reports missing closed trade");
    } else {
        assert(drill.blockers.includes("closed_trade_missing"), "paper trade drill missing closed-trade blocker");
    }
    if (drill.postmortem_due_count > 0) {
        assert(!drill.blockers.includes("postmortem_due_missing"), "paper trade drill still reports missing postmortem due");
    } else {
        assert(drill.blockers.includes("postmortem_due_missing"), "paper trade drill missing postmortem-due blocker");
    }
    if (drillComplete) {
        assert(drill.blocker_count === 0, "paper trade drill complete with blockers");
        assert(drill.blockers.length === 0, "paper trade drill complete with blocker list");
        assert(drill.submitted_paper_order_count > 0, "paper trade drill complete without submitted order");
        assert(drill.position_open_lifecycle_satisfied === true, "paper trade drill complete without open-position lifecycle");
        assert(drill.closed_trade_count > 0, "paper trade drill complete without closed trade");
        assert(drill.postmortem_due_count > 0, "paper trade drill complete without postmortem due");
        assert(drill.position_open_lifecycle_satisfied === true, "paper trade drill complete without open lifecycle");
    } else {
        assert(drill.blocker_count >= 1, "paper trade drill incomplete without blockers");
    }
    assert(drill.broker_post_called_count === 0, "paper trade drill broker POST called");
    assert(drill.alpaca_post_called_count === 0, "paper trade drill Alpaca POST called");
    assert(drill.live_capital_enabled_count === 0, "paper trade drill live capital enabled");
    assert(drill.phase7_proof_credit_allowed === false, "paper trade drill grants Phase 7 proof credit");
    assert(drill.phase7_proof_credit_allowed_count === 0, "paper trade drill Phase 7 proof count nonzero");
    assert(drill.event_log_written === true, "paper trade drill Event Log not written");
    assert(drill.event_log_event_count === 13, "paper trade drill Event Log count mismatch");
    assert(drill.step_count === 13, "paper trade drill step count mismatch");
    assert(Array.isArray(drill.records), "paper trade drill records missing");
    assert(drill.records.length === 13, "paper trade drill record count mismatch");
    for (const record of drill.records) {
        assert(record.display_status === record.backend_status, "paper trade drill display/backend mismatch");
        assert(record.display_derived_from_backend === true, "paper trade drill record not backend-derived");
        assert(record.ui_inferred_readiness === false, "paper trade drill inferred readiness present");
        assert(record.broker_post_called === false, "paper trade drill record broker POST called");
        assert(record.broker_write_allowed === false, "paper trade drill record broker write allowed");
        assert(record.live_capital_enabled === false, "paper trade drill record live capital enabled");
        assert(record.phase7_proof_credit_allowed === false, "paper trade drill record grants Phase 7 proof credit");
    }

    const rendered = await renderWithStatus(status);
    assertIncludes(rendered, "[data-mission-stack]", "Q5-14");
    assertIncludes(rendered, "[data-trade-layer]", "Q5-14 End-To-End Paper Trade Drill");
    assertIncludes(rendered, "[data-trade-layer]", drill.paper_trade_drill_state.replaceAll("_", " "));
    assertIncludes(rendered, "[data-trade-layer]", approvalPresent ? "paper-submit approval present" : "paper-submit approval missing");
    assertIncludes(
        rendered,
        "[data-trade-layer]",
        drill.paper_submit_path_available_count > 0 ? "paper submit path available" : "paper submit path blocked"
    );
    assertIncludes(rendered, "[data-trade-layer]", "no broker POST");
    assertIncludes(rendered, "[data-trade-layer]", "live capital disabled");
    assertIncludes(rendered, "[data-trade-layer]", "no Phase 7 proof credit");

    console.log("dashboard_phase5_paper_trade_drill=ok");
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
