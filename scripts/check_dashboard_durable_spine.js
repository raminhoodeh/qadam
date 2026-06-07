#!/usr/bin/env node

const {
    assert,
    assertIncludes,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

const REQUIRED_FIELDS = [
    "boundary",
    "contract_status",
    "database_configured",
    "expected_source_count",
    "missing_source_count",
    "next_step",
    "observation_count",
    "order_authority",
    "replay_status",
    "replayed_source_count",
    "service_status",
    "signal_authority",
    "status",
    "write_authority"
];

function hasOwn(value, key) {
    return Object.prototype.hasOwnProperty.call(value || {}, key);
}

async function main() {
    const durable = status.durable_ingestion || {};
    const missing = REQUIRED_FIELDS.filter((field) => !hasOwn(durable, field));
    assert(!missing.length, `durable ingestion missing fields: ${missing.join(", ")}`);
    assert(durable.expected_source_count >= 35, "durable ingestion expected source count too low");
    assert(durable.replayed_source_count <= durable.expected_source_count, "durable replay count exceeds expected source count");
    assert(durable.write_authority === false, "durable ingestion exposes write authority");
    assert(durable.signal_authority === false, "durable ingestion exposes signal authority");
    assert(durable.order_authority === false, "durable ingestion exposes order authority");
    assert(/cannot create signals/i.test(durable.boundary || ""), "durable ingestion boundary is weak");

    const mission = status.mission_control || {};
    assert(mission.durable_spine, "mission control missing durable spine");
    assert(
        mission.durable_spine.replayed_source_count === durable.replayed_source_count,
        "mission durable replay count differs from top-level durable status"
    );
    assert(
        mission.system_stack?.durable_spine === durable.contract_status,
        "mission stack durable status differs from top-level durable contract"
    );

    const rendered = await renderWithStatus(status);
    assertIncludes(rendered, "[data-overview-system-status]", "Durable replay");
    assertIncludes(rendered, "[data-overview-system-status]", "sources replayed");
    assertIncludes(rendered, "[data-overview-system-status]", "replayed");
    assertIncludes(rendered, "[data-overview-data-sources]", "connected");

    console.log("dashboard_durable_spine=ok");
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
