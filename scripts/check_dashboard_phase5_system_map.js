#!/usr/bin/env node

const {
    assert,
    assertIncludes,
    html,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

const REQUIRED_NODE_KEYS = [
    "watching",
    "yahoo_finance",
    "tradingview_mcp",
    "bookmap_local_bridge",
    "preference_mcp",
    "event_log",
    "live_bridge",
    "worldview",
    "research_analyst",
    "strategy_lead",
    "head_of_quant",
    "shadow_intelligence",
    "signal_integrity_gate",
    "approval_policy_router",
    "risk_agent",
    "kill_switch_ledger",
    "execution_adapter_status",
    "execution_policy",
    "staged_order_contract",
    "broker_reconciliation",
    "paper_submit_receipt",
    "prediction_market_adapter",
    "trade_layer",
    "paper_account",
    "position_monitor",
    "postmortem_loop",
    "telegram_notifier",
    "signal_review",
    "fund_manager_forum"
];

const LAYER_B_NODE_KEYS = [
    "approval_policy_router",
    "risk_agent",
    "kill_switch_ledger",
    "execution_adapter_status",
    "staged_order_contract",
    "paper_submit_receipt",
    "prediction_market_adapter",
    "telegram_notifier",
    "position_monitor",
    "signal_review"
];

function nodeByKey(systemMap, key) {
    const node = (systemMap.nodes || []).find((item) => item.key === key);
    assert(Boolean(node), `missing system-map node: ${key}`);
    return node;
}

function assertNodeStatus(systemMap, key, expected) {
    const node = nodeByKey(systemMap, key);
    assert(node.backend_status === String(expected), `${key} backend status mismatch`);
    assert(node.display_status === node.backend_status, `${key} display status mismatch`);
    assert(node.ui_inferred === false, `${key} inferred UI state`);
}

async function main() {
    const systemMap = status.phase5_system_map || {};
    const nodes = Array.isArray(systemMap.nodes) ? systemMap.nodes : [];
    const lanes = Array.isArray(systemMap.lanes) ? systemMap.lanes : [];

    assert(systemMap.phase === "Q5", "system map phase mismatch");
    assert(systemMap.stage === "Q5-13", "system map stage mismatch");
    assert(systemMap.status === "ok", "system map status mismatch");
    assert(systemMap.public_safe === true, "system map is not public-safe");
    assert(systemMap.recorded === true, "system map runtime artifact missing");
    assert(systemMap.event_log_written === true, "system map event log missing");
    assert(systemMap.event_log_event_count === 1, "system map event log count mismatch");
    assert(systemMap.node_count === REQUIRED_NODE_KEYS.length, "system map node count mismatch");
    assert(systemMap.node_count === nodes.length, "system map public node count mismatch");
    assert(systemMap.lane_count === lanes.length, "system map lane count mismatch");
    assert(systemMap.layer_b_node_count === LAYER_B_NODE_KEYS.length, "system map Layer B node count mismatch");
    assert(systemMap.backend_parity_check_count === systemMap.node_count, "system map parity check count mismatch");
    assert(systemMap.backend_parity_error_count === 0, "system map parity errors present");
    assert(systemMap.unsafe_control_count === 0, "system map unsafe controls present");
    assert(systemMap.ui_inferred_node_count === 0, "system map inferred nodes present");
    assert(systemMap.validation_error_count === 0, "system map validation errors present");

    const nodeKeys = nodes.map((node) => node.key);
    for (const key of REQUIRED_NODE_KEYS) {
        assert(nodeKeys.includes(key), `system map required node missing: ${key}`);
    }
    for (const node of nodes) {
        assert(node.display_status === node.backend_status, `system map node display mismatch: ${node.key}`);
        assert(node.ui_inferred === false, `system map node inferred state: ${node.key}`);
        assert(node.public_safe === true, `system map node is not public-safe: ${node.key}`);
        assert(node.trade_approval_control_enabled === false, `approval control enabled: ${node.key}`);
        assert(node.order_place_control_enabled === false, `order control enabled: ${node.key}`);
        assert(node.broker_write_allowed === false, `broker write enabled: ${node.key}`);
        assert(node.prediction_market_write_allowed === false, `prediction-market write enabled: ${node.key}`);
        assert(node.kill_switch_mutation_authority === false, `kill-switch mutation enabled: ${node.key}`);
        assert(node.live_capital_enabled === false, `live capital enabled: ${node.key}`);
    }

    assertNodeStatus(systemMap, "yahoo_finance", status.yahoo_finance.status);
    assertNodeStatus(systemMap, "tradingview_mcp", status.tradingview_mcp.status);
    assertNodeStatus(systemMap, "bookmap_local_bridge", status.bookmap_local_bridge.status);
    assertNodeStatus(systemMap, "preference_mcp", status.preference_mcp.status);
    assertNodeStatus(systemMap, "live_bridge", status.live_bridge.status);
    assertNodeStatus(systemMap, "kill_switch_ledger", status.phase5_kill_switch_ledger.status);
    assertNodeStatus(systemMap, "execution_adapter_status", status.phase5_execution_adapter_status.status);
    assertNodeStatus(systemMap, "staged_order_contract", status.phase5_paper_order_staging_gate.status);
    assertNodeStatus(systemMap, "paper_submit_receipt", status.phase5_paper_submit_enablement_gate.status);
    assertNodeStatus(systemMap, "prediction_market_adapter", status.phase5_prediction_market_adapter.status);
    assertNodeStatus(systemMap, "telegram_notifier", status.phase5_telegram_notifier.status);
    assertNodeStatus(systemMap, "position_monitor", status.phase5_position_monitor.status);
    assertNodeStatus(systemMap, "signal_review", status.phase5_signal_review.status);

    assert(systemMap.source_posture.canonical.expected_source_count === status.durable_ingestion.expected_source_count, "canonical expected source mismatch");
    assert(systemMap.source_posture.canonical.replayed_source_count === status.durable_ingestion.replayed_source_count, "canonical replayed source mismatch");
    assert(systemMap.source_posture.yahoo_finance.role === "supplemental_market_confirmation_only", "Yahoo Finance role mismatch");
    assert(systemMap.source_posture.tradingview_mcp.role === "supplemental_technical_confirmation_only", "TradingView MCP role mismatch");
    assert(systemMap.source_posture.tradingview_mcp.source_quorum_credit_allowed === false, "TradingView MCP source quorum enabled");
    assert(systemMap.source_posture.tradingview_mcp.trade_candidate_creation_allowed === false, "TradingView MCP candidate creation enabled");
    assert(systemMap.source_posture.bookmap_local_bridge.role === "supplemental_orderflow_confirmation_only", "Bookmap role mismatch");
    assert(systemMap.source_posture.bookmap_local_bridge.source_quorum_credit_allowed === false, "Bookmap source quorum enabled");
    assert(systemMap.source_posture.bookmap_local_bridge.trade_candidate_creation_allowed === false, "Bookmap candidate creation enabled");
    assert(systemMap.source_posture.bookmap_local_bridge.bookmap_order_injection_allowed === false, "Bookmap injection enabled");
    assert(systemMap.source_posture.bookmap_local_bridge.bookmap_trading_mode_allowed === false, "Bookmap trading mode enabled");
    assert(systemMap.source_posture.preference_mcp.source_36 === false, "Preference MCP source 36 enabled");
    assert(systemMap.source_posture.preference_mcp.source_quorum_credit_allowed === false, "Preference MCP source quorum enabled");

    assert(systemMap.guardrails.mode === "paper", "system map mode is not paper");
    assert(systemMap.guardrails.live_capital_enabled === false, "system map live capital enabled");
    assert(systemMap.guardrails.phase5_orchestration_start_allowed === false, "system map orchestration start allowed");
    assert(systemMap.guardrails.paper_submit_path_available_count === status.phase5_paper_submit_enablement_gate.submit_path_available_count, "system map submit path count mismatch");
    assert(systemMap.guardrails.dashboard_claims_trading_now === false, "system map claims trading now");

    const rendered = await renderWithStatus(status);
    const flowHtml = html(rendered, "[data-flow-map]");
    assert(flowHtml.includes("data-phase5-system-map"), "dashboard did not render the Q5-13 backend system-map section");
    assertIncludes(rendered, "[data-flow-map]", "Q5-13 Functional System Map Dashboard");
    assertIncludes(rendered, "[data-flow-map]", "Backend parity");
    assertIncludes(rendered, "[data-flow-map]", "Unsafe controls");
    assertIncludes(rendered, "[data-flow-map]", "canonical sources");
    assertIncludes(rendered, "[data-flow-map]", "Yahoo Finance supplemental market confirmation only");
    assertIncludes(rendered, "[data-flow-map]", "TradingView MCP Technical");
    assertIncludes(rendered, "[data-flow-map]", "Preference/PREF MCP");
    assertIncludes(rendered, "[data-flow-map]", "live capital disabled");
    assertIncludes(rendered, "[data-flow-map]", `paper submit path ${systemMap.guardrails.paper_submit_path_available_count || 0}`);
    assertIncludes(rendered, "[data-flow-map]", "dashboard does not say trading");

    [
        "Approval Policy Router",
        "Kill-Switch Ledger",
        "Execution Adapter Status",
        "Prediction-Market Adapter",
        "Telegram Bot / Notifier",
        "Position Monitor",
        "Signal Review"
    ].forEach((label) => assertIncludes(rendered, "[data-flow-map]", label));

    console.log("dashboard_phase5_system_map=ok");
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
