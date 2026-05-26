#!/usr/bin/env node

const {
    assert,
    assertIncludes,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

async function main() {
    const handoff = status.phase5_phase6_handoff || {};
    assert(handoff.phase === "Q5", "Phase 6 handoff phase mismatch");
    assert(handoff.stage === "Q5E-10", "Phase 6 handoff stage mismatch");
    assert(handoff.public_safe === true, "Phase 6 handoff is not public-safe");
    assert(handoff.recorded === true, "Phase 6 handoff is not recorded");
    assert(handoff.status === "eligible", "Phase 6 handoff is not eligible");
    assert(
        handoff.handoff_state === "phase6_learning_loop_plan_ready",
        "Phase 6 handoff state mismatch"
    );
    assert(handoff.phase5_certified === true, "Phase 5 is not certified in handoff");
    assert(handoff.phase5_exit_gate === true, "Phase 5 exit gate not open in handoff");
    assert(handoff.phase6_handoff_allowed === true, "Phase 6 handoff not allowed");
    assert(handoff.phase7_planning_allowed === true, "Phase 7 planning not allowed");
    assert(handoff.phase7_proof_credit_allowed === false, "Phase 7 proof credit allowed");
    assert(
        handoff.phase5_test_trades_count_for_phase7 === false,
        "Phase 5 test trades count toward Phase 7"
    );
    assert(
        handoff.phase6_learning_loop_plan_allowed === true,
        "Phase 6 plan not allowed"
    );
    assert(
        handoff.phase6_learning_loop_implementation_allowed === false,
        "Phase 6 implementation allowed"
    );
    assert(handoff.phase6_learning_write_allowed === false, "Phase 6 learning write allowed");
    assert(
        handoff.phase6_knowledge_graph_write_allowed === false,
        "Phase 6 knowledge graph write allowed"
    );
    assert(
        handoff.phase6_model_weight_update_allowed === false,
        "Phase 6 model weight update allowed"
    );
    assert(
        handoff.phase6_trust_score_update_allowed === false,
        "Phase 6 trust score update allowed"
    );
    assert(
        handoff.phase6_architect_policy_mutation_allowed === false,
        "Phase 6 policy mutation allowed"
    );
    assert(handoff.paper_trade_drill_complete === true, "Paper trade drill incomplete");
    assert(
        handoff.paper_trade_drill_exit_gate_passed === true,
        "Paper trade drill exit gate not passed"
    );
    assert(handoff.blocker_count === 0, "Phase 6 handoff blockers present");
    assert(handoff.validation_error_count === 0, "Phase 6 handoff validation errors present");
    assert(handoff.event_log_written === true, "Phase 6 handoff event log missing");
    assert(handoff.closed_trade_count >= 1, "Phase 6 handoff closed trade missing");
    assert(handoff.postmortem_due_count >= 1, "Phase 6 handoff postmortem due missing");

    for (const key of [
        "broker_post_called_count",
        "alpaca_post_called_count",
        "broker_write_allowed_count",
        "prediction_market_write_allowed_count",
        "crypto_perps_write_allowed_count",
        "live_endpoint_allowed_count",
        "live_capital_enabled_count",
        "phase7_proof_credit_allowed_count",
        "phase6_learning_write_allowed_count",
        "phase6_knowledge_graph_write_allowed_count",
        "phase6_model_weight_update_allowed_count",
        "phase6_trust_score_update_allowed_count",
        "phase6_policy_mutation_allowed_count"
    ]) {
        assert(Number(handoff[key] || 0) === 0, `Phase 6 handoff unsafe count nonzero: ${key}`);
    }

    const rendered = await renderWithStatus(status);
    assertIncludes(rendered, "[data-trade-layer]", "Q5E-10 Phase 6 Handoff Closeout");
    assertIncludes(rendered, "[data-trade-layer]", "Phase 6 plan");
    assertIncludes(rendered, "[data-trade-layer]", "Phase 6 implementation blocked");
    assertIncludes(rendered, "[data-trade-layer]", "knowledge graph writes blocked");
    assertIncludes(rendered, "[data-trade-layer]", "no Phase 7 proof credit");
    assertIncludes(rendered, "[data-trade-layer]", "live capital disabled");
    assertIncludes(rendered, "[data-trade-layer]", "Q6-0 Phase 6 re-entry");

    console.log("dashboard_phase5_phase6_handoff=ok");
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
