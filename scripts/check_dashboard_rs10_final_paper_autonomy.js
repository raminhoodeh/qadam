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

const AUTHORITY_FIELDS = [
    "dashboard_command_authority",
    "telegram_command_authority",
    "local_llm_execution_authority",
    "frontier_llm_execution_authority",
    "quantum_execution_authority",
    "unmanaged_broker_write_allowed",
    "broker_post_allowed",
    "alpaca_post_allowed",
    "live_capital_enabled",
    "phase7_proof_credit_allowed"
];

const UNSAFE_COUNT_FIELDS = [
    "live_endpoint_called_count",
    "broker_post_called_count",
    "alpaca_post_called_count",
    "broker_write_allowed_count",
    "telegram_command_path_enabled_count",
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
                !["raw_payload", "private_payload", "broker_order_id", "external_order_id", "access_token", "refresh_token", "secret", "chat_id", "bot_token"].includes(key),
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
    const rs10 = status.rs10_final_paper_autonomy_certification || {};
    const mission = status.mission_control || {};
    const missionRs10 = mission.rs10_final_paper_autonomy_certification || {};
    const stack = mission.system_stack || {};

    assert(rs10.phase === "RS", "RS-10 phase mismatch");
    assert(rs10.stage === "RS-10", "RS-10 stage mismatch");
    assert(rs10.public_safe === true, "RS-10 is not public-safe");
    assert(rs10.recorded === true, "RS-10 artifact is not recorded");
    assert(rs10.event_log_written === true, "RS-10 Event Log missing");
    assert(Number(rs10.event_log_event_count || 0) === 1, "RS-10 Event Log count mismatch");
    assert(Number(rs10.validation_error_count || 0) === 0, "RS-10 validation errors present");
    assert(
        ["certified_actionable", "certified_waiting_for_qualified_setup", "certified_idle"].includes(rs10.status),
        "RS-10 status is not certified"
    );
    assert(rs10.final_paper_autonomy_certified === true, "RS-10 final paper autonomy is not certified");
    assert(rs10.guarded_paper_autonomy_allowed === true, "RS-10 guarded paper autonomy is not allowed");
    assert(rs10.multiple_paper_trades_per_day_allowed_when_gates_pass === true, "RS-10 multiple paper trade policy disabled");
    assert(Number(rs10.certification_blocker_count || 0) === 0, "RS-10 certification blockers present");
    assert(Number(rs10.safety_blocker_count || 0) === 0, "RS-10 safety blockers present");
    assert(Number(rs10.stale_blocker_in_current_count || 0) === 0, "RS-10 stale blockers appear current");
    assert(rs10.paper_submission_transport === "paperops_guarded_alpaca_paper", "RS-10 paper transport mismatch");
    assert(rs10.daily_target_policy === "minimum_not_ceiling", "RS-10 daily target policy mismatch");
    assert(Number(rs10.opportunity_scan_interval_minutes || 0) === 20, "RS-10 scan cadence mismatch");
    assert(Number(rs10.max_guarded_submit_attempts_per_run || 0) <= 3, "RS-10 submit attempt cap too high");
    assert(rs10.rate_limit_policy_present === true, "RS-10 rate-limit policy missing");

    for (const field of AUTHORITY_FIELDS) {
        assert(rs10[field] === false, `RS-10 authority enabled: ${field}`);
    }
    for (const field of UNSAFE_COUNT_FIELDS) {
        assert(Number(rs10[field] || 0) === 0, `RS-10 unsafe/exposure count nonzero: ${field}`);
    }
    if (rs10.paper_submit_currently_allowed === true) {
        assert(rs10.paperops_active_status === "active_automation_ready_to_submit", "RS-10 invented current submit authority");
    }
    if (rs10.autonomy_currently_actionable === true) {
        assert(
            rs10.paper_submit_currently_allowed === true || rs10.paper_poll_currently_allowed === true || rs10.paper_exit_currently_allowed === true,
            "RS-10 actionable without an allowed action"
        );
    }
    assertNoPublicLeak(rs10, "$.rs10_final_paper_autonomy_certification");

    assert(missionRs10.status === rs10.status, "Mission Control RS-10 status mismatch");
    assert(missionRs10.final_paper_autonomy_certified === rs10.final_paper_autonomy_certified, "Mission Control RS-10 certification mismatch");
    assert(missionRs10.guarded_paper_autonomy_allowed === rs10.guarded_paper_autonomy_allowed, "Mission Control RS-10 guarded autonomy mismatch");
    assert(missionRs10.autonomy_currently_actionable === rs10.autonomy_currently_actionable, "Mission Control RS-10 actionability mismatch");
    assert(missionRs10.current_blocker_count === rs10.current_blocker_count, "Mission Control RS-10 blocker count mismatch");
    assert(stack.rs10_final_paper_autonomy_certification === rs10.status, "Mission stack RS-10 status mismatch");
    assert(stack.rs10_final_paper_autonomy_certified === rs10.final_paper_autonomy_certified, "Mission stack RS-10 certification mismatch");
    assert(stack.rs10_guarded_paper_autonomy_allowed === rs10.guarded_paper_autonomy_allowed, "Mission stack RS-10 guarded autonomy mismatch");

    assert(dashboardCode.includes("data-rs10-final-paper-autonomy"), "Dashboard missing RS-10 panel selector");
    assert(dashboardCode.includes("status.rs10_final_paper_autonomy_certification"), "Dashboard does not read RS-10 backend status");
    assert(dashboardCode.includes("htmlText(rs10FinalPaperAutonomy.boundary"), "Dashboard does not escape RS-10 boundary");
    assert(!/rs10FinalPaperAutonomy\\.status\\s*=/.test(dashboardCode), "Dashboard mutates RS-10 backend status");

    const rendered = await renderWithStatus(status);
    assertIncludes(rendered, "[data-mission-stack]", "RS-10");
    assertIncludes(rendered, "[data-mission-stack]", "guarded paper autonomy allowed");
    assertIncludes(rendered, "[data-mission-stack]", "multiple paper trades/day when gates pass");
    assertIncludes(rendered, "[data-trade-layer]", "RS-10 Final Paper Autonomy Certification");
    assertIncludes(rendered, "[data-trade-layer]", "Guarded autonomy");
    assertIncludes(rendered, "[data-trade-layer]", "multiple paper trades/day when gates pass");
    assertIncludes(rendered, "[data-trade-layer]", "live capital off");
    assertIncludes(rendered, "[data-trade-layer]", "dashboard commands off");
    assertIncludes(rendered, "[data-trade-layer]", "Telegram commands off");
    assertIncludes(rendered, "[data-trade-layer]", "Local LLM cannot execute");
    assertIncludes(rendered, "[data-trade-layer]", "Frontier LLM cannot execute");
    assertIncludes(rendered, "[data-trade-layer]", "Quantum cannot execute");
    assertIncludes(rendered, "[data-trade-layer]", "Why not trading now");

    const unsafeStatus = JSON.parse(JSON.stringify(status));
    unsafeStatus.rs10_final_paper_autonomy_certification.boundary = "<script>alert(1)</script>";
    unsafeStatus.rs10_final_paper_autonomy_certification.why_not_trading_now = "<script>alert(2)</script>";
    unsafeStatus.rs10_final_paper_autonomy_certification.next_action = "<script>alert(3)</script>";
    unsafeStatus.rs10_final_paper_autonomy_certification.current_blockers = ["<script>alert(4)</script>"];
    unsafeStatus.mission_control.rs10_final_paper_autonomy_certification.boundary = "<script>alert(1)</script>";
    const unsafe = await renderWithStatus(unsafeStatus);
    const tradeHtml = html(unsafe, "[data-trade-layer]");
    assert(!tradeHtml.includes("<script>"), "RS-10 panel emitted raw script tag from status data");
    assert(tradeHtml.includes("&lt;script&gt;alert(1)&lt;/script&gt;"), "RS-10 panel did not escape boundary");
    assert(tradeHtml.includes("&lt;script&gt;alert(2)&lt;/script&gt;"), "RS-10 panel did not escape why-not-trading reason");
    assert(tradeHtml.includes("&lt;script&gt;alert(3)&lt;/script&gt;"), "RS-10 panel did not escape next action");
    assert(tradeHtml.includes("&lt;script&gt;alert(4)&lt;/script&gt;"), "RS-10 panel did not escape blocker tag");

    console.log("dashboard_rs10_final_paper_autonomy=ok");
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
