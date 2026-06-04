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

const EXPECTED_SURFACES = new Set([
    "strategy_weights",
    "source_trust",
    "risk_sizing",
    "market_context_interpretation",
    "worldview_lens_strength"
]);

const AUTHORITY_FIELDS = [
    "strategy_weight_mutation_allowed",
    "source_trust_mutation_allowed",
    "risk_sizing_mutation_allowed",
    "market_context_interpretation_mutation_allowed",
    "worldview_lens_strength_mutation_allowed",
    "knowledge_graph_write_allowed",
    "model_weight_update_allowed",
    "trust_score_update_allowed",
    "policy_mutation_allowed",
    "strategy_mutation_allowed",
    "learning_write_allowed",
    "dashboard_command_authority",
    "telegram_command_authority",
    "broker_write_allowed",
    "broker_post_allowed",
    "alpaca_post_allowed",
    "live_capital_enabled",
    "phase7_proof_credit_allowed"
];

const UNSAFE_COUNT_FIELDS = [
    "broker_post_called_count",
    "alpaca_post_called_count",
    "broker_write_allowed_count",
    "live_endpoint_called_count",
    "live_capital_enabled_count",
    "phase7_proof_credit_allowed_count",
    "unsafe_write_counter_total",
    "raw_payload_exposed_count",
    "private_payload_exposed_count",
    "local_path_exposed_count",
    "secret_ref_exposed_count",
    "broker_identifier_exposed_count"
];

function assertNoPublicLeak(value, pathLabel = "$") {
    if (Array.isArray(value)) {
        value.forEach((item, index) => assertNoPublicLeak(item, `${pathLabel}[${index}]`));
        return;
    }
    if (value && typeof value === "object") {
        Object.entries(value).forEach(([key, nested]) => {
            assert(
                !["raw_payload", "private_payload", "broker_order_id", "external_order_id", "access_token", "refresh_token", "secret"].includes(key),
                `public leak key at ${pathLabel}.${key}`
            );
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
    const rs9 = status.rs9_learning_loop || {};
    const mission = status.mission_control || {};
    const missionRs9 = mission.rs9_learning_loop || {};
    const stack = mission.system_stack || {};

    assert(rs9.phase === "RS", "RS-9 phase mismatch");
    assert(rs9.stage === "RS-9", "RS-9 stage mismatch");
    assert(rs9.public_safe === true, "RS-9 is not public-safe");
    assert(rs9.recorded === true, "RS-9 artifact is not recorded");
    assert(rs9.status === "review_ready" || rs9.status === "blocked", "RS-9 status invalid");
    assert(["improving", "degrading", "uncertain"].includes(rs9.learning_direction), "RS-9 learning direction invalid");
    assert(rs9.full_potential_state === "learning_visible_but_mutation_locked", "RS-9 full-potential state mismatch");
    assert(rs9.paperops_guarded_paper_trading_not_blocked === true, "RS-9 blocks guarded PaperOps");
    assert(Number(rs9.validation_error_count || 0) === 0, "RS-9 validation errors present");
    assert(Number(rs9.source_validation_error_count || 0) === 0, "RS-9 source validation errors present");

    assert(Array.isArray(rs9.source_status_records), "RS-9 source records missing");
    assert(rs9.source_artifact_count === rs9.source_status_records.length, "RS-9 source count mismatch");
    for (const record of rs9.source_status_records) {
        assert(/^data\/runtime\//.test(record.source_ref || ""), "RS-9 source ref is not public-safe relative");
    }

    assert(Array.isArray(rs9.learning_proposals), "RS-9 learning proposals missing");
    assert(rs9.proposal_count === rs9.learning_proposals.length, "RS-9 proposal count mismatch");
    assert(rs9.proposal_count >= 5, "RS-9 proposal count too low");
    assert(rs9.active_proposal_count === 0, "RS-9 active proposals should be zero");
    assert(rs9.blocked_proposal_count === rs9.proposal_count, "RS-9 blocked proposal count mismatch");
    const surfaces = new Set(rs9.learning_proposals.map((proposal) => proposal.proposal_surface));
    assert(surfaces.size === EXPECTED_SURFACES.size, "RS-9 surface count mismatch");
    for (const surface of EXPECTED_SURFACES) {
        assert(surfaces.has(surface), `RS-9 missing proposal surface: ${surface}`);
    }
    for (const proposal of rs9.learning_proposals) {
        assert(proposal.approval_required === true, "RS-9 proposal does not require approval");
        assert(proposal.apply_allowed === false, "RS-9 proposal allows apply");
        assert(proposal.mutation_allowed === false, "RS-9 proposal allows mutation");
        for (const ref of proposal.source_refs || []) {
            assert(/^data\/runtime\//.test(ref), "RS-9 proposal source ref is not public-safe relative");
        }
    }

    assert(rs9.strategy_weight_proposal_count === 1, "RS-9 strategy proposal count mismatch");
    assert(rs9.source_trust_proposal_count === 1, "RS-9 source-trust proposal count mismatch");
    assert(rs9.risk_sizing_proposal_count === 1, "RS-9 risk-sizing proposal count mismatch");
    assert(rs9.market_context_proposal_count === 1, "RS-9 market-context proposal count mismatch");
    assert(rs9.worldview_lens_proposal_count === 1, "RS-9 worldview-lens proposal count mismatch");

    for (const field of AUTHORITY_FIELDS) {
        assert(rs9[field] === false, `RS-9 authority enabled: ${field}`);
    }
    for (const field of UNSAFE_COUNT_FIELDS) {
        assert(Number(rs9[field] || 0) === 0, `RS-9 unsafe/exposure count nonzero: ${field}`);
    }
    assert(rs9.blocked_authority_count === AUTHORITY_FIELDS.length, "RS-9 blocked authority count mismatch");
    assertNoPublicLeak(rs9, "$.rs9_learning_loop");

    assert(missionRs9.status === rs9.status, "Mission Control RS-9 status mismatch");
    assert(missionRs9.learning_direction === rs9.learning_direction, "Mission Control RS-9 direction mismatch");
    assert(missionRs9.full_potential_state === rs9.full_potential_state, "Mission Control RS-9 full-potential mismatch");
    assert(missionRs9.proposal_count === rs9.proposal_count, "Mission Control RS-9 proposal count mismatch");
    assert(missionRs9.blocked_proposal_count === rs9.blocked_proposal_count, "Mission Control RS-9 blocked proposal count mismatch");
    assert(missionRs9.paperops_guarded_paper_trading_not_blocked === true, "Mission Control RS-9 PaperOps state mismatch");
    assert(stack.rs9_learning_loop === rs9.status, "Mission Control stack RS-9 status mismatch");
    assert(stack.rs9_learning_direction === rs9.learning_direction, "Mission Control stack RS-9 direction mismatch");
    assert(stack.rs9_learning_proposal_count === rs9.proposal_count, "Mission Control stack RS-9 proposal count mismatch");
    assert(stack.rs9_learning_blocked_proposal_count === rs9.blocked_proposal_count, "Mission Control stack RS-9 blocked count mismatch");
    assert(stack.rs9_paperops_guarded_paper_trading_not_blocked === true, "Mission Control stack RS-9 PaperOps mismatch");

    assert(dashboardCode.includes("data-rs9-learning-loop"), "Dashboard missing RS-9 panel selector");
    assert(dashboardCode.includes("status.rs9_learning_loop"), "Dashboard does not read RS-9 backend status");
    assert(dashboardCode.includes("htmlText(rs9LearningLoop.boundary"), "Dashboard does not escape RS-9 boundary");
    assert(!/rs9LearningLoop\\.status\\s*=/.test(dashboardCode), "Dashboard mutates RS-9 backend status");

    const rendered = await renderWithStatus(status);
    assertIncludes(rendered, "[data-mission-stack]", "RS-9");
    assertIncludes(rendered, "[data-mission-stack]", "guarded PaperOps not blocked");
    assertIncludes(rendered, "[data-trade-layer]", "RS-9 Learning Loop Full-Potential Review");
    assertIncludes(rendered, "[data-trade-layer]", "Learning proposals");
    assertIncludes(rendered, "[data-trade-layer]", "worldview lens strength");
    assertIncludes(rendered, "[data-trade-layer]", "strategy mutation locked");
    assertIncludes(rendered, "[data-trade-layer]", "source trust locked");
    assertIncludes(rendered, "[data-trade-layer]", "risk sizing locked");
    assertIncludes(rendered, "[data-trade-layer]", "worldview lens locked");
    assertIncludes(rendered, "[data-trade-layer]", "dashboard commands off");
    assertIncludes(rendered, "[data-trade-layer]", "Telegram commands off");
    assertIncludes(rendered, "[data-trade-layer]", "OK - live capital off");
    assertIncludes(rendered, "[data-trade-layer]", "no 60-day paper growth trial proof credit");

    const unsafeStatus = JSON.parse(JSON.stringify(status));
    unsafeStatus.rs9_learning_loop.learning_direction_reason = "<script>alert(1)</script>";
    unsafeStatus.rs9_learning_loop.boundary = "<script>alert(2)</script>";
    unsafeStatus.rs9_learning_loop.learning_proposals[0].rationale = "<script>alert(3)</script>";
    unsafeStatus.mission_control.rs9_learning_loop.learning_direction_reason = "<script>alert(1)</script>";
    unsafeStatus.mission_control.rs9_learning_loop.boundary = "<script>alert(2)</script>";
    const unsafe = await renderWithStatus(unsafeStatus);
    const tradeHtml = html(unsafe, "[data-trade-layer]");
    assert(!tradeHtml.includes("<script>"), "RS-9 panel emitted raw script tag from status data");
    assert(tradeHtml.includes("&lt;script&gt;alert(1)&lt;/script&gt;"), "RS-9 panel did not escape learning direction reason");
    assert(tradeHtml.includes("&lt;script&gt;alert(2)&lt;/script&gt;"), "RS-9 panel did not escape boundary");
    assert(tradeHtml.includes("&lt;script&gt;alert(3)&lt;/script&gt;"), "RS-9 panel did not escape proposal rationale");

    console.log("dashboard_rs9_learning_loop=ok");
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
