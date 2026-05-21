#!/usr/bin/env node

const {
    assert,
    assertIncludes,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

const MISSION_REQUIRED_FIELDS = [
    "data_sources",
    "durable_spine",
    "headline",
    "portfolio",
    "safety",
    "schema_version",
    "source",
    "status",
    "system_stack",
    "thinking",
    "trade_intent",
    "trading_philosophy"
];

function hasOwn(value, key) {
    return Object.prototype.hasOwnProperty.call(value, key);
}

function missingFields(value, fields) {
    return fields.filter((field) => !hasOwn(value || {}, field));
}

async function main() {
    const mission = status.mission_control || {};
    const missing = missingFields(mission, MISSION_REQUIRED_FIELDS);
    assert(!missing.length, `mission control missing fields: ${missing.join(", ")}`);
    assert(mission.status === "read_only_mission_control", "mission control status mismatch");
    assert(/sources online/i.test(mission.headline || ""), "mission headline does not summarize source state");
    assert(/live capital disabled/i.test(mission.headline || ""), "mission headline does not show live-capital boundary");
    assert(mission.data_sources.total_count === status.watching.length, "mission source total mismatch");
    assert(Array.isArray(mission.data_sources.logged_in_sources), "mission logged-in sources list missing");
    assert(Array.isArray(mission.data_sources.connected_sources), "mission connected sources list missing");
    assert(mission.data_sources.durable_expected_source_count === status.durable_ingestion.expected_source_count, "mission durable source target mismatch");
    assert(mission.data_sources.durable_replayed_source_count === status.durable_ingestion.replayed_source_count, "mission durable replay count mismatch");
    assert(/observation inputs only/i.test(mission.data_sources.boundary || ""), "mission source boundary is weak");
    assert(mission.durable_spine.expected_source_count === status.durable_ingestion.expected_source_count, "mission durable expected source count mismatch");
    assert(mission.durable_spine.replayed_source_count === status.durable_ingestion.replayed_source_count, "mission durable replayed source count mismatch");
    assert(mission.durable_spine.write_authority === false, "mission durable write authority enabled");
    assert(mission.durable_spine.signal_authority === false, "mission durable signal authority enabled");
    assert(mission.durable_spine.order_authority === false, "mission durable order authority enabled");
    assert(/cannot create signals/i.test(mission.durable_spine.boundary || ""), "mission durable boundary is weak");
    assert(/private prior/i.test(mission.trading_philosophy.boundary || ""), "mission philosophy boundary is weak");
    assert(mission.trading_philosophy.current_self_directive.length >= 4, "mission self-directive is too thin");
    assert(mission.trade_intent.candidate_count === status.trade_layer.candidates.length, "mission candidate count mismatch");
    assert(mission.trade_intent.observed_signal_count === status.trade_layer.watching.length, "mission observed signal count mismatch");
    assert(mission.trade_intent.execution_allowed_count === 0, "mission exposes execution authority");
    assert(mission.trade_intent.paper_order_submitted_count === 0, "mission exposes submitted paper orders");
    assert(mission.trade_intent.broker_post_called_count === 0, "mission exposes broker POST calls");
    assert(mission.portfolio.open_position_count === status.capital.open_positions.length, "mission open position count mismatch");
    assert(mission.portfolio.live_capital_enabled === false, "mission portfolio live capital enabled");
    assert(mission.portfolio.write_authority === false, "mission portfolio write authority enabled");
    assert(mission.safety.live_capital_enabled === false, "mission safety live capital enabled");
    assert(mission.safety.broker_write_allowed === false, "mission safety broker write enabled");
    assert(/read-only/i.test(mission.safety.boundary || ""), "mission safety boundary is weak");

    const rendered = await renderWithStatus(status);
    assertIncludes(rendered, "[data-mission-primary]", "Operating thesis");
    assertIncludes(rendered, "[data-mission-primary]", "hypotheses");
    assertIncludes(rendered, "[data-mission-primary]", "Mission control is read-only");
    assertIncludes(rendered, "[data-mission-primary]", "Replay");
    assertIncludes(rendered, "[data-mission-sources]", "logged-in/configured");
    assertIncludes(rendered, "[data-mission-sources]", "missing credentials");
    assertIncludes(rendered, "[data-mission-sources]", "replay");
    assertIncludes(rendered, "[data-mission-sources]", "observation inputs only");
    assertIncludes(rendered, "[data-mission-philosophy]", "Trading philosophy");
    assertIncludes(rendered, "[data-mission-philosophy]", "private prior");
    assertIncludes(rendered, "[data-mission-stack]", "Local LLM");
    assertIncludes(rendered, "[data-mission-stack]", "quantum oracle");
    assertIncludes(rendered, "[data-mission-stack]", "replay");
    assertIncludes(rendered, "[data-mission-stack]", "risk");
    assertIncludes(rendered, "[data-mission-trades]", "Trade intent");
    assertIncludes(rendered, "[data-mission-trades]", "Submitted");
    assertIncludes(rendered, "[data-mission-trades]", "non-executing");
    assertIncludes(rendered, "[data-mission-portfolio]", "Paper account");
    assertIncludes(rendered, "[data-mission-portfolio]", "P&amp;L");
    assertIncludes(rendered, "[data-mission-portfolio]", "Write");

    console.log("dashboard_mission_control=ok");
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
