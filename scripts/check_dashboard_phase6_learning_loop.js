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
    const phase6 = status.phase6_learning_loop || {};
    const mission = status.mission_control || {};
    const missionPhase6 = mission.phase6_learning_loop || {};

    assert(phase6.phase === "Q6", "Phase 6 cockpit visibility phase mismatch");
    assert(phase6.stage === "Q6-16", "Phase 6 cockpit visibility stage mismatch");
    assert(phase6.public_safe === true, "Phase 6 cockpit visibility is not public-safe");
    assert(phase6.recorded === true, "Phase 6 cockpit visibility is not recorded");
    assert(phase6.status === "visible", "Phase 6 cockpit visibility is not visible");
    assert(phase6.visibility_state === "backend_derived_deferred_learning_visible", "Phase 6 visibility state mismatch");
    assert(phase6.learning_state === "deferred_learning_visible", "Phase 6 learning state mismatch");
    assert(phase6.backend_derived === true, "Phase 6 visibility is not backend-derived");
    assert(phase6.display_derived_from_backend === true, "Phase 6 display is not backend-derived");
    assert(phase6.dashboard_uses_backend_status === true, "Phase 6 dashboard is not backend-derived");
    assert(phase6.ui_inferred_readiness_count === 0, "Phase 6 UI inferred readiness present");
    assert(phase6.backend_parity_error_count === 0, "Phase 6 backend parity errors present");
    assert(phase6.validation_error_count === 0, "Phase 6 visibility validation errors present");
    assert(phase6.event_log_written === true, "Phase 6 visibility event log missing");
    assert(phase6.event_log_event_count === 1, "Phase 6 visibility event count mismatch");
    assert(phase6.source_missing_count === 0, "Phase 6 visibility source missing");
    assert(phase6.source_validation_error_count === 0, "Phase 6 visibility source validation errors present");
    assert(Array.isArray(phase6.source_status_records), "Phase 6 source status records missing");
    assert(phase6.source_artifact_count === phase6.source_status_records.length, "Phase 6 source status count mismatch");

    assert(phase6.postmortem_due_count >= 1, "Phase 6 postmortem due count missing");
    assert(phase6.postmortem_resolved_count === 0, "Phase 6 postmortem resolved count should remain zero after deferral");
    assert(phase6.approval_state === "deferred", "Phase 6 approval state mismatch");
    assert(phase6.pending_review_action_count === 0, "Phase 6 pending review actions should be cleared");
    assert(phase6.deferred_action_count === 5, "Phase 6 deferred action count mismatch");
    assert(phase6.explicitly_deferred_action_count === 5, "Phase 6 explicit deferred action count mismatch");
    assert(phase6.learning_actions_review_satisfied === true, "Phase 6 learning review should be satisfied by explicit deferral");
    assert(phase6.staged_graph_entry_count === 0, "Phase 6 staged graph entries should be zero before approval");
    assert(phase6.knowledge_graph_read_result_count >= 1, "Phase 6 knowledge graph read result missing");
    assert(phase6.model_weight_proposal_count >= 1, "Phase 6 model weight proposal missing");
    assert(phase6.trust_score_proposal_count >= 1, "Phase 6 trust score proposals missing");
    assert(phase6.shadow_replay_variant_count >= 1, "Phase 6 shadow replay variants missing");
    assert(phase6.architect_recommendation_count >= 1, "Phase 6 architect recommendations missing");
    assert(phase6.architect_blocked_recommendation_count >= 1, "Phase 6 blocked architect recommendations missing");
    assert(phase6.blocked_authority_count === phase6.blocked_authorities.length, "Phase 6 blocked authority count mismatch");

    for (const key of [
        "phase6_learning_write_allowed",
        "phase6_knowledge_graph_write_allowed",
        "phase6_model_weight_update_allowed",
        "phase6_trust_score_update_allowed",
        "phase6_shadow_strategy_runner_allowed",
        "phase6_architect_policy_mutation_allowed",
        "phase6_policy_mutation_allowed",
        "phase7_proof_credit_allowed",
        "broker_write_allowed",
        "prediction_market_write_allowed",
        "live_capital_enabled"
    ]) {
        assert(phase6[key] === false, `Phase 6 authority enabled: ${key}`);
    }

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
        "raw_payload_exposed_count",
        "private_payload_exposed_count",
        "local_path_exposed_count",
        "secret_ref_exposed_count",
        "broker_identifier_exposed_count"
    ]) {
        assert(Number(phase6[key] || 0) === 0, `Phase 6 unsafe/exposure count nonzero: ${key}`);
    }

    for (const record of phase6.source_status_records) {
        assert(record.display_status === record.backend_status, "Phase 6 source display/backend mismatch");
        assert(record.display_derived_from_backend === true, "Phase 6 source display is not backend-derived");
        assert(record.ui_inferred_readiness === false, "Phase 6 source UI inference present");
        assert(/^data\/runtime\//.test(record.source_ref || ""), "Phase 6 source ref is not public-safe relative");
    }
    assertNoPublicLeak(phase6, "$.phase6_learning_loop");

    assert(missionPhase6.status === phase6.status, "Mission Control Phase 6 status mismatch");
    assert(missionPhase6.learning_state === phase6.learning_state, "Mission Control Phase 6 learning state mismatch");
    assert(missionPhase6.postmortem_due_count === phase6.postmortem_due_count, "Mission Control Phase 6 postmortem mismatch");
    assert(missionPhase6.model_weight_proposal_count === phase6.model_weight_proposal_count, "Mission Control Phase 6 model proposal mismatch");
    assert(missionPhase6.trust_score_proposal_count === phase6.trust_score_proposal_count, "Mission Control Phase 6 trust proposal mismatch");
    assert(mission.system_stack.phase6_learning_loop === phase6.status, "Mission Control stack Phase 6 status mismatch");

    assert(dashboardCode.includes("data-phase6-learning-loop"), "Dashboard missing Q6-16 panel selector");
    assert(dashboardCode.includes("status.phase6_learning_loop"), "Dashboard does not read backend Phase 6 status");
    assert(dashboardCode.includes("htmlText(phase6LearningLoop.boundary"), "Dashboard does not escape Phase 6 boundary");
    assert(!/phase6LearningLoop\\.status\\s*=/.test(dashboardCode), "Dashboard mutates Phase 6 backend status");
    assert(!/learning_state\\s*===\\s*\"approved\"/.test(dashboardCode), "Dashboard infers Phase 6 approval from UI state");

    const rendered = await renderWithStatus(status);
    assertIncludes(rendered, "[data-mission-stack]", "Q6-16 visible");
    assertIncludes(rendered, "[data-mission-stack]", "deferred learning visible");
    assertIncludes(rendered, "[data-trade-layer]", "Q6-16 Learning Loop Journal Visibility");
    assertIncludes(rendered, "[data-trade-layer]", "Postmortem due");
    assertIncludes(rendered, "[data-trade-layer]", "Resolved");
    assertIncludes(rendered, "[data-trade-layer]", "deferred");
    assertIncludes(rendered, "[data-trade-layer]", "Graph staged");
    assertIncludes(rendered, "[data-trade-layer]", "Model proposals");
    assertIncludes(rendered, "[data-trade-layer]", "Trust proposals");
    assertIncludes(rendered, "[data-trade-layer]", "Replay variants");
    assertIncludes(rendered, "[data-trade-layer]", "Architect proposals");
    assertIncludes(rendered, "[data-trade-layer]", "Blocked auth");
    assertIncludes(rendered, "[data-trade-layer]", "learning writes blocked");
    assertIncludes(rendered, "[data-trade-layer]", "model updates blocked");
    assertIncludes(rendered, "[data-trade-layer]", "trust updates blocked");
    assertIncludes(rendered, "[data-trade-layer]", "policy mutation blocked");
    assertIncludes(rendered, "[data-trade-layer]", "no Phase 7 proof credit");
    assertIncludes(rendered, "[data-trade-layer]", "live capital disabled");

    const unsafeStatus = JSON.parse(JSON.stringify(status));
    unsafeStatus.phase6_learning_loop.approval_state = "<script>alert(1)</script>";
    unsafeStatus.phase6_learning_loop.boundary = "<script>alert(2)</script>";
    unsafeStatus.mission_control.phase6_learning_loop.approval_state = "<script>alert(1)</script>";
    unsafeStatus.mission_control.phase6_learning_loop.boundary = "<script>alert(2)</script>";
    const unsafe = await renderWithStatus(unsafeStatus);
    const phase6Html = html(unsafe, "[data-trade-layer]");
    assert(!phase6Html.includes("<script>"), "Phase 6 panel emitted raw script tag from status data");
    assert(phase6Html.includes("&lt;script&gt;alert(1)&lt;/script&gt;"), "Phase 6 panel did not escape approval state");
    assert(phase6Html.includes("&lt;script&gt;alert(2)&lt;/script&gt;"), "Phase 6 panel did not escape boundary");

    console.log("dashboard_phase6_learning_loop=ok");
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
