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
            assert(
                !["raw_payload", "private_payload", "request_body", "receipt_payload", "broker_order_id", "external_order_id", "fill_id"].includes(key),
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
    const phase7 = status.phase7_demo_proof || {};

    assert(phase7.phase === "Q7", "Phase 7 demo proof phase mismatch");
    assert(phase7.stage === "Q7-15", "Phase 7 demo proof stage mismatch");
    assert(phase7.public_safe === true, "Phase 7 demo proof is not public-safe");
    assert(phase7.recorded === true, "Phase 7 demo proof is not recorded");
    assert(phase7.status === "visible", "Phase 7 demo proof should be visible");
    assert(phase7.stage_status === "phase7_demo_proof_visible", "Phase 7 demo proof stage status mismatch");
    assert(phase7.validation_error_count === 0, "Phase 7 demo proof validation errors present");
    assert(phase7.event_log_written === true, "Phase 7 demo proof Event Log missing");
    assert(phase7.event_log_event_count === 1, "Phase 7 demo proof Event Log count mismatch");
    assert(phase7.backend_derived === true, "Phase 7 demo proof is not backend-derived");
    assert(phase7.display_derived_from_backend === true, "Phase 7 demo proof display is not backend-derived");
    assert(phase7.dashboard_uses_backend_status === true, "Phase 7 demo proof dashboard is not backend-derived");
    assert(phase7.ui_inferred_readiness_count === 0, "Phase 7 demo proof UI inferred readiness present");
    assert(phase7.source_missing_count === 0, "Phase 7 demo proof source artifacts missing");
    assert(phase7.source_validation_error_count === 0, "Phase 7 demo proof source validation errors present");
    assert(phase7.source_artifact_count === phase7.source_status_records.length, "Phase 7 demo proof source record count mismatch");
    assert(phase7.phase7_harness_day_count === 30, "Phase 7 demo proof day count mismatch");
    assert(phase7.weekly_proof_trade_target === 3, "Phase 7 demo proof weekly target mismatch");
    assert(phase7.mature_benchmark === 100, "Phase 7 demo proof maturity benchmark mismatch");
    assert(phase7.phase7_statistical_immaturity_hidden === false, "Phase 7 demo proof hides statistical immaturity");
    assert(phase7.phase5_test_trades_count_for_phase7 === false, "Phase 7 demo proof counts Phase 5 test trades");
    assert(phase7.phase7_proof_credit_allowed === false, "Phase 7 proof credit is falsely allowed");
    assert(phase7.live_capital_enabled === false, "Phase 7 demo proof enables live capital");
    assert(phase7.q7_16_weekly_review_pack_stage_allowed === true, "Q7-16 weekly review pack is not allowed");

    for (const record of phase7.source_status_records) {
        assert(record.display_status === record.backend_status, "Phase 7 source display/backend mismatch");
        assert(record.display_derived_from_backend === true, "Phase 7 source display is not backend-derived");
        assert(record.ui_inferred_readiness === false, "Phase 7 source UI inference present");
        assert(String(record.source_ref || "").startsWith("data/runtime/"), "Phase 7 source ref is not relative runtime path");
        assert(!String(record.source_ref || "").startsWith("/"), "Phase 7 source ref leaked local path");
    }
    for (const key of [
        "broker_write_allowed_count",
        "prediction_market_write_allowed_count",
        "crypto_perps_write_allowed_count",
        "live_endpoint_allowed_count",
        "live_capital_enabled_count",
        "proof_trade_credit_count",
        "phase7_proof_credit_allowed_count",
        "phase5_test_trade_reuse_count",
        "ui_inferred_readiness_count",
        "manual_trade_level_override_count",
        "unsafe_write_counter_total",
        "raw_payload_exposed_count",
        "private_payload_exposed_count",
        "local_path_exposed_count",
        "secret_ref_exposed_count",
        "broker_identifier_exposed_count"
    ]) {
        assert(Number(phase7[key] || 0) === 0, `Phase 7 demo proof unsafe/exposure count nonzero: ${key}`);
    }
    assertNoPublicLeak(phase7, "$.phase7_demo_proof");

    assert(dashboardCode.includes("data-phase7-demo-proof"), "Dashboard missing Q7-15 panel selector");
    assert(dashboardCode.includes("status.phase7_demo_proof"), "Dashboard does not read backend Phase 7 demo proof");
    assert(dashboardCode.includes("htmlText(phase7DemoProof.boundary"), "Dashboard does not escape Phase 7 boundary");
    assert(!/phase7DemoProof\\.status\\s*=/.test(dashboardCode), "Dashboard mutates Phase 7 demo proof status");

    const rendered = await renderWithStatus(status);
    assertIncludes(rendered, "[data-mission-stack]", "Q7-15");
    assertIncludes(rendered, "[data-mission-stack]", "proof trades 0/100");
    assertIncludes(rendered, "[data-mission-stack]", "no Phase 7 proof credit");
    assertIncludes(rendered, "[data-trade-layer]", "Q7-15 Phase 7 Demo Proof Visibility");
    assertIncludes(rendered, "[data-trade-layer]", "backend-derived");
    assertIncludes(rendered, "[data-trade-layer]", "display derived from backend");
    assertIncludes(rendered, "[data-trade-layer]", "no UI inference");
    assertIncludes(rendered, "[data-trade-layer]", "Phase 5 trades excluded from proof");
    assertIncludes(rendered, "[data-trade-layer]", "no Phase 7 proof credit");
    assertIncludes(rendered, "[data-trade-layer]", "live capital disabled");
    assertIncludes(rendered, "[data-trade-layer]", "statistical immaturity visible");
    assertIncludes(rendered, "[data-trade-layer]", "100-trade maturity not met");
    assertIncludes(rendered, "[data-trade-layer]", "Q7-16");
    assertIncludes(rendered, "[data-trade-layer]", "No Q7-15 blockers exported");

    const unsafeStatus = JSON.parse(JSON.stringify(status));
    unsafeStatus.phase7_demo_proof.proof_state = "<script>alert(1)</script>";
    unsafeStatus.phase7_demo_proof.boundary = "<script>alert(2)</script>";
    const unsafe = await renderWithStatus(unsafeStatus);
    const tradeHtml = html(unsafe, "[data-trade-layer]");
    assert(!tradeHtml.includes("<script>"), "Phase 7 panel emitted raw script tag");
    assert(tradeHtml.includes("&lt;script&gt;alert(1)&lt;/script&gt;"), "Phase 7 panel did not escape proof state");
    assert(tradeHtml.includes("&lt;script&gt;alert(2)&lt;/script&gt;"), "Phase 7 panel did not escape boundary");

    console.log("dashboard_phase7_demo_proof=ok");
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
