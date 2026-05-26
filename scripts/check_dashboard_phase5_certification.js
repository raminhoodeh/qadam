#!/usr/bin/env node

const {
    assert,
    assertIncludes,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

async function main() {
    const certification = status.phase5_certification || {};
    const certified = certification.phase5_certified === true;
    assert(certification.phase === "Q5", "Phase 5 certification phase mismatch");
    assert(certification.stage === "Q5-15", "Phase 5 certification stage mismatch");
    assert(
        certification.status === (certified ? "eligible" : "blocked"),
        "Phase 5 certification status mismatch"
    );
    assert(
        certification.stage_status === (certified ? "phase5_certified" : "blocked_pending_q5_14"),
        "Phase 5 certification stage status mismatch"
    );
    assert(certification.recorded === true, "Phase 5 certification not recorded");
    assert(certification.public_safe === true, "Phase 5 certification not public-safe");
    assert(certification.event_log_written === true, "Phase 5 certification Event Log missing");
    assert(certification.event_log_event_count === 1, "Phase 5 certification Event Log count mismatch");
    assert(certification.validation_error_count === 0, "Phase 5 certification validation errors present");
    assert(certification.phase7_proof_credit_allowed === false, "Phase 7 proof credit allowed");
    assert(certification.input_gate_count === 15, "Phase 5 certification input gate count mismatch");
    assert(
        certification.input_gate_blocked_count === certification.input_gate_count - certification.input_gate_passed_count,
        "Phase 5 certification blocked count mismatch"
    );
    if (certified) {
        assert(certification.phase5_exit_gate === true, "Phase 5 exit gate not open");
        assert(certification.phase6_handoff_allowed === true, "Phase 6 handoff not allowed");
        assert(certification.phase7_planning_allowed === true, "Phase 7 planning not allowed");
        assert(certification.input_gate_passed_count === certification.input_gate_count, "Phase 5 certification passed count mismatch");
        assert(certification.input_gate_blocked_count === 0, "Phase 5 certification blocked count nonzero");
        assert(certification.certification_blocker_count === 0, "Phase 5 certification blockers present");
        assert(certification.certification_blockers.length === 0, "Phase 5 certification blocker list present");
        assert(certification.paper_trade_drill_complete === true, "paper trade drill incomplete");
        assert(certification.paper_trade_drill_exit_gate_passed === true, "paper trade drill exit gate not passed");
        assert(certification.submitted_paper_order_count > 0, "submitted paper order missing");
        assert(certification.open_position_count > 0, "open position missing");
        assert(certification.closed_trade_count > 0, "closed trade missing");
        assert(certification.postmortem_due_count > 0, "postmortem due missing");
    } else {
        assert(certification.phase5_exit_gate === false, "Phase 5 exit gate open");
        assert(certification.phase6_handoff_allowed === false, "Phase 6 handoff allowed");
        assert(certification.phase7_planning_allowed === false, "Phase 7 planning allowed");
        assert(certification.input_gate_blocked_count >= 1, "Phase 5 certification blockers missing");
        assert(certification.certification_blocker_count >= 1, "Phase 5 certification blockers missing");
        assert(certification.certification_blockers.includes("q5_14_exit_gate_not_passed"), "Q5-14 exit blocker missing");
        assert(certification.certification_blockers.includes("q5_14_paper_trade_lifecycle_incomplete"), "Q5-14 lifecycle blocker missing");
        assert(certification.paper_trade_drill_complete === false, "paper trade drill unexpectedly complete");
        assert(certification.paper_trade_drill_exit_gate_passed === false, "paper trade drill exit gate passed");
        if (certification.submitted_paper_order_count > 0) {
            assert(!certification.certification_blockers.includes("submitted_paper_order_missing"), "submitted paper order still blocked");
        } else {
            assert(certification.certification_blockers.includes("submitted_paper_order_missing"), "submitted paper order blocker missing");
        }
        if (certification.open_position_count > 0 || certification.closed_trade_count > 0) {
            assert(!certification.certification_blockers.includes("open_position_missing"), "open position still blocked");
        } else {
            assert(certification.certification_blockers.includes("open_position_missing"), "open position blocker missing");
        }
        if (certification.closed_trade_count > 0) {
            assert(!certification.certification_blockers.includes("closed_trade_missing"), "closed trade still blocked");
        } else {
            assert(certification.certification_blockers.includes("closed_trade_missing"), "closed trade blocker missing");
        }
        if (certification.postmortem_due_count > 0) {
            assert(!certification.certification_blockers.includes("postmortem_due_missing"), "postmortem due still blocked");
        } else {
            assert(certification.certification_blockers.includes("postmortem_due_missing"), "postmortem due blocker missing");
        }
    }
    assert(certification.live_capital_enabled_count === 0, "live capital enabled");
    assert(Array.isArray(certification.gate_records), "certification gate records missing");
    assert(certification.gate_records.length === 15, "certification gate record count mismatch");
    for (const record of certification.gate_records) {
        assert(record.display_status === record.backend_status, "certification gate display/backend mismatch");
        assert(record.display_derived_from_backend === true, "certification gate not backend-derived");
        assert(record.ui_inferred_readiness === false, "certification gate inferred readiness");
        assert(record.phase7_proof_credit_allowed === false, "certification gate grants proof credit");
    }

    const rendered = await renderWithStatus(status);
    assertIncludes(rendered, "[data-mission-stack]", "Q5-15");
    assertIncludes(rendered, "[data-trade-layer]", "Q5-15 Phase 5 Certification");
    assertIncludes(rendered, "[data-trade-layer]", certified ? "Phase 5 certified" : "Phase 5 not certified");
    assertIncludes(rendered, "[data-trade-layer]", certified ? "Q5-14 exit passed" : "Q5-14 exit blocked");
    assertIncludes(rendered, "[data-trade-layer]", certified ? "Phase 6 handoff allowed" : "Phase 6 handoff blocked");
    assertIncludes(rendered, "[data-trade-layer]", "no Phase 7 proof credit");
    assertIncludes(rendered, "[data-trade-layer]", "live capital disabled");

    console.log("dashboard_phase5_certification=ok");
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
