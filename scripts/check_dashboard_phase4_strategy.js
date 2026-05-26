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
const dashboardHtmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const dashboardHtml = fs.readFileSync(dashboardHtmlPath, "utf8");

function assertZeroAuthority(value, label) {
    assert(value === 0, `${label} should be zero`);
}

async function main() {
    const phase4 = status.phase4_strategy || {};
    const approval = phase4.approval_event || {};
    const certification = phase4.certification || {};
    const preferenceGate = certification.preference_mcp_certification_gate || {};
    const toggles = phase4.strategy_toggles || {};
    const phase4Approved = phase4.approval_event_status === "approved";

    assert(phase4.phase === "Q4", "Phase 4 status missing Q4 phase");
    assert(phase4.stage === "Q4-12", "Phase 4 status missing Q4-12 stage");
    if (phase4Approved) {
        assert(phase4.stage_status === "phase4_certified", "Phase 4 stage status mismatch");
    } else {
        assert(phase4.stage_status === "blocked_pending_explicit_approval", "Phase 4 stage status mismatch");
    }
    assert(phase4.public_safe === true, "Phase 4 status is not marked public-safe");
    assert(phase4.strategy_document_status === "validated", "Phase 4 strategy document is not validated");
    assert(approval.approval_logged === true, "Phase 4 approval event should be logged");
    if (phase4Approved) {
        assert(approval.required_amendment_count === 0, "Phase 4 approval should have no required amendments");
        assert(phase4.phase4_certification_allowed === true, "Phase 4 certification should be allowed");
        assert(phase4.phase4_certified === true, "Phase 4 should be certified");
        assert(phase4.phase5_handoff_allowed === true, "Phase 5 handoff should be allowed");
        assert(phase4.certification_status === "certified", "Phase 4 certification status should be certified");
    } else {
        assert(phase4.approval_event_status === "amendments_required", "Phase 4 approval should require amendments");
        assert(approval.required_amendment_count >= 1, "Phase 4 approval should list a required amendment");
        assert(phase4.phase4_certification_allowed === false, "Phase 4 certification should remain blocked");
        assert(phase4.phase4_certified === false, "Phase 4 should not be certified");
        assert(phase4.phase5_handoff_allowed === false, "Phase 5 handoff should remain blocked");
        assert(phase4.certification_status === "blocked", "Phase 4 certification status should be blocked");
    }
    assert(certification.validation_error_count === 0, "Phase 4 certification validation errors present");
    assert(preferenceGate.source_promotion_status === "validated", "Phase 4 Preference source-promotion gate not validated");
    assert(preferenceGate.source_promotion_promoted_decision_count === 0, "Phase 4 Preference source-promotion count nonzero");
    assert(preferenceGate.source_promotion_canonical_source_count_after === 35, "Phase 4 Preference source count changed");
    assert(preferenceGate.preference_mcp_source_36 === false, "Phase 4 Preference source 36 flag enabled");
    if (phase4Approved) {
        assert(certification.certification_blocker_count === 0, "Phase 4 certification blockers present");
    } else {
        assert(certification.certification_blocker_count >= 1, "Phase 4 certification blocker missing");
        assert(
            certification.certification_blockers.includes("explicit_fund_manager_approval_required"),
            "Phase 4 certification should expose explicit approval blocker"
        );
    }
    assert(phase4.toggle_count === 5, "Phase 4 should expose 5 strategy toggles");
    assert(toggles.visible_toggle_count === 5, "All Phase 4 toggles should be visible");
    if (phase4Approved) {
        assert(toggles.draft_toggle_count === 0, "Phase 4 approved toggles should not remain draft");
        assert(toggles.approved_shadow_toggle_count === 5, "All Phase 4 toggles should be approved-shadow");
    } else {
        assert(toggles.draft_toggle_count === 5, "Phase 4 toggles should remain draft");
        assert(toggles.approved_shadow_toggle_count === 0, "No Phase 4 approved-shadow toggles should be enabled");
    }
    assert(toggles.validation_error_count === 0, "Phase 4 toggle validation errors present");
    assertZeroAuthority(phase4.trade_candidate_count, "Phase 4 trade candidate count");
    assertZeroAuthority(phase4.execution_allowed_count, "Phase 4 execution allowed count");
    assertZeroAuthority(phase4.paper_order_allowed_count, "Phase 4 paper order allowed count");
    assertZeroAuthority(phase4.broker_write_allowed_count, "Phase 4 broker write allowed count");
    assertZeroAuthority(phase4.live_capital_enabled_count, "Phase 4 live capital enabled count");
    assert(
        /supplemental_market_confirmation_only/.test(
            phase4.market_confirmation_policy?.yahoo_finance_role || ""
        ),
        "Yahoo Finance role should remain supplemental market confirmation only"
    );

    assert(dashboardHtml.includes('id="strategy-manifestation"'), "dashboard missing strategy section");
    assert(dashboardHtml.includes("data-mission-strategy"), "dashboard missing mission strategy card");
    assert(dashboardHtml.includes("data-phase4-summary"), "dashboard missing Phase 4 summary target");
    assert(dashboardHtml.includes("data-phase4-strategy"), "dashboard missing Phase 4 strategy target");

    const rendered = await renderWithStatus(status);
    assertIncludes(rendered, "[data-mission-strategy]", "Phase 4 strategy");
    assertIncludes(rendered, "[data-mission-strategy]", phase4Approved ? "approved" : "amendments required");
    assertIncludes(rendered, "[data-mission-strategy]", phase4Approved ? "certified" : "certification blocked");
    assertIncludes(rendered, "[data-phase4-summary]", "Q4-12");
    assertIncludes(rendered, "[data-phase4-summary]", phase4Approved ? "Certified" : "Blocked");
    assertIncludes(rendered, "[data-phase4-strategy]", phase4Approved ? "approved" : "Explicit Fund Manager approval");
    if (!phase4Approved) {
        assertIncludes(rendered, "[data-phase4-strategy]", "Certification blocker");
        assertIncludes(rendered, "[data-phase4-strategy]", "explicit fund manager approval required");
        assertIncludes(rendered, "[data-phase4-strategy]", "draft");
    }
    assertIncludes(rendered, "[data-phase4-strategy]", "approved-shadow");
    assertIncludes(rendered, "[data-phase4-strategy]", "No execution");
    assertIncludes(rendered, "[data-phase4-strategy]", "No paper orders");
    assertIncludes(rendered, "[data-phase4-strategy]", "No broker writes");
    assertIncludes(rendered, "[data-phase4-strategy]", "Live capital disabled");
    assertIncludes(rendered, "[data-phase4-strategy]", "Yahoo Finance supplemental");
    assertIncludes(rendered, "[data-phase4-strategy]", "Preference zero promoted sources");
    assertIncludes(rendered, "[data-phase4-strategy]", "Preference not source 36");
    assert(
        !/paper ready|live ready|execution ready/i.test(html(rendered, "[data-phase4-strategy]")),
        "Phase 4 panel implies execution readiness"
    );

    console.log("dashboard_phase4_strategy=ok");
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
