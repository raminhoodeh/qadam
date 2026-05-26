#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const {
    assert,
    assertIncludes,
    html,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

const repoRoot = path.resolve(__dirname, "..");
const dashboardPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");
const dashboardCode = fs.readFileSync(dashboardPath, "utf8");

function assertNoPublicLeak(value, pathLabel = "$") {
    if (Array.isArray(value)) {
        value.forEach((item, index) => assertNoPublicLeak(item, `${pathLabel}[${index}]`));
        return;
    }
    if (value && typeof value === "object") {
        Object.entries(value).forEach(([key, nested]) => {
            assert(!["raw_payload", "private_payload", "broker_order_id", "external_order_id"].includes(key), `public leak key at ${pathLabel}.${key}`);
            assertNoPublicLeak(nested, `${pathLabel}.${key}`);
        });
        return;
    }
    if (typeof value !== "string") return;
    assert(!value.includes("/Users/"), `local path leaked at ${pathLabel}`);
    assert(!/api_key|secret_|secret=|token_|token=|bearer /i.test(value), `secret marker leaked at ${pathLabel}`);
    assert(!/broker_order_id|external_order_id|fill_id/i.test(value), `broker identifier leaked at ${pathLabel}`);
}

async function main() {
    const certification = status.phase6_certification || {};

    assert(certification.phase === "Q6", "Phase 6 certification phase mismatch");
    assert(certification.stage === "Q6-17", "Phase 6 certification stage mismatch");
    assert(certification.public_safe === true, "Phase 6 certification is not public-safe");
    assert(certification.recorded === true, "Phase 6 certification is not recorded");
    assert(certification.status === "certified", "Phase 6 certification should be certified after explicit deferral");
    assert(certification.stage_status === "phase6_certified", "Phase 6 certification stage status mismatch");
    assert(certification.phase6_certified === true, "Phase 6 is not certified");
    assert(certification.phase6_exit_gate === true, "Phase 6 exit gate is not open");
    assert(certification.phase7_demo_proof_planning_allowed === true, "Phase 7 demo planning is not allowed");
    assert(certification.phase7_proof_credit_allowed === false, "Phase 7 proof credit is falsely allowed");
    assert(certification.phase5_test_trades_count_for_phase7 === false, "Phase 5 test trades counted for Phase 7");
    assert(certification.input_gate_count === 17, "Phase 6 input gate count mismatch");
    assert(certification.input_gate_passed_count === 17, "Phase 6 input gates are not all implemented");
    assert(certification.input_gate_blocked_count === 0, "Phase 6 input gates are blocked");
    assert(certification.certification_blocker_count === 0, "Phase 6 certification blockers present");
    assert(certification.postmortem_due_count >= 1, "Phase 6 certification postmortem due missing");
    assert(certification.unresolved_postmortem_count === 0, "Phase 6 certification unresolved postmortem remains");
    assert(certification.reviewed_postmortem_coverage_satisfied === true, "Phase 6 certification does not mark postmortems reviewed/deferred");
    assert(certification.approval_state === "deferred", "Phase 6 certification approval state mismatch");
    assert(certification.pending_review_action_count === 0, "Phase 6 certification pending actions remain");
    assert(certification.explicitly_deferred_action_count === certification.proposed_action_count, "Phase 6 certification deferred action count mismatch");
    assert(certification.learning_actions_review_satisfied === true, "Phase 6 certification does not mark learning reviewed/deferred");
    assert(certification.knowledge_graph_requirement_satisfied === true, "Phase 6 certification does not satisfy KG deferral requirement");

    for (const key of [
        "knowledge_graph_read_result_count",
        "model_weight_proposal_count",
        "trust_score_proposal_count",
        "shadow_replay_variant_count",
        "architect_recommendation_count"
    ]) {
        assert(Number(certification[key] || 0) >= 1, `Phase 6 certification missing count: ${key}`);
    }

    assert(certification.cockpit_visibility_status === "visible", "Phase 6 certification does not see cockpit visibility");
    assert(certification.cockpit_backend_derived === true, "Phase 6 certification cockpit input is not backend-derived");
    assert(certification.cockpit_ui_inferred_readiness_count === 0, "Phase 6 certification cockpit input has UI inference");

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
        "phase6_policy_mutation_allowed_count",
        "unsafe_write_counter_total",
        "blocking_unsafe_count"
    ]) {
        assert(Number(certification[key] || 0) === 0, `Phase 6 certification unsafe count nonzero: ${key}`);
    }

    for (const gate of certification.gate_records) {
        assert(gate.display_status === gate.backend_status, "Phase 6 certification gate display/backend mismatch");
        assert(gate.display_derived_from_backend === true, "Phase 6 certification gate display is not backend-derived");
        assert(gate.ui_inferred_readiness === false, "Phase 6 certification gate UI inference present");
        assert(!String(gate.source_ref || "").startsWith("/"), "Phase 6 certification gate local path leaked");
    }
    assertNoPublicLeak(certification, "$.phase6_certification");

    assert(dashboardCode.includes("data-phase6-certification"), "Dashboard missing Q6-17 panel selector");
    assert(dashboardCode.includes("status.phase6_certification"), "Dashboard does not read backend Phase 6 certification");
    assert(dashboardCode.includes("htmlText(phase6Certification.boundary"), "Dashboard does not escape Phase 6 certification boundary");
    assert(!/phase6Certification\\.status\\s*=/.test(dashboardCode), "Dashboard mutates Phase 6 certification status");

    const rendered = await renderWithStatus(status);
    assertIncludes(rendered, "[data-mission-stack]", "Q6-17");
    assertIncludes(rendered, "[data-mission-stack]", "Phase 7 demo plan allowed");
    assertIncludes(rendered, "[data-trade-layer]", "Q6-17 Phase 6 Certification");
    assertIncludes(rendered, "[data-trade-layer]", "Phase 6 certified");
    assertIncludes(rendered, "[data-trade-layer]", "postmortems reviewed/deferred");
    assertIncludes(rendered, "[data-trade-layer]", "learning review done");
    assertIncludes(rendered, "[data-trade-layer]", "KG requirement satisfied");
    assertIncludes(rendered, "[data-trade-layer]", "Phase 7 demo planning allowed");
    assertIncludes(rendered, "[data-trade-layer]", "no Phase 7 proof credit");
    assertIncludes(rendered, "[data-trade-layer]", "Phase 5 trades excluded from proof");
    assertIncludes(rendered, "[data-trade-layer]", "live capital disabled");

    const unsafeStatus = JSON.parse(JSON.stringify(status));
    unsafeStatus.phase6_certification.approval_state = "<script>alert(1)</script>";
    unsafeStatus.phase6_certification.boundary = "<script>alert(2)</script>";
    const unsafe = await renderWithStatus(unsafeStatus);
    const phase6Html = html(unsafe, "[data-trade-layer]");
    assert(!phase6Html.includes("<script>"), "Phase 6 certification panel emitted raw script tag");
    assert(phase6Html.includes("&lt;script&gt;alert(1)&lt;/script&gt;"), "Phase 6 certification panel did not escape approval state");
    assert(phase6Html.includes("&lt;script&gt;alert(2)&lt;/script&gt;"), "Phase 6 certification panel did not escape boundary");

    console.log("dashboard_phase6_certification=ok");
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
