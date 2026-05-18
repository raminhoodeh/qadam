#!/usr/bin/env node

const {
    assert,
    assertIncludes,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

async function main() {
    const live = await renderWithStatus(status);
    assert(live.requests.length === 1, "live bridge render should stop after the first successful source");
    assert(live.requests[0].url.includes("/api/cockpit-status"), "live bridge was not the first dashboard source");
    assert(
        live.requests[0].init.headers?.Authorization === "Bearer test-session-token",
        "live bridge request did not include the Supabase bearer token"
    );
    assert(
        live.document.documentElement.dataset.dashboardStatusSource === "live_bridge",
        "live bridge source was not recorded"
    );
    assertIncludes(live, "[data-snapshot-meta]", "D9 read-only live bridge");

    const fallback = await renderWithStatus(status, { liveFetchOk: false, statusCode: 503 });
    assert(fallback.requests.length === 2, "static fallback should be requested after live bridge failure");
    assert(fallback.requests[0].url.includes("/api/cockpit-status"), "fallback test did not try live bridge first");
    assert(fallback.requests[1].url.includes("/status/cockpit-status.json"), "fallback test did not request static snapshot");
    assert(
        fallback.document.documentElement.dataset.dashboardStatusSource === "static_snapshot",
        "static fallback source was not recorded"
    );
    assertIncludes(fallback, "[data-snapshot-meta]", "static snapshot fallback");
    assertIncludes(fallback, "[data-status-banner]", "D9 static fallback loaded");

    const failed = await renderWithStatus(status, { fetchOk: false, statusCode: 500 });
    assert(
        failed.document.documentElement.dataset.dashboardStatus === "snapshot-error",
        "dashboard should fail closed when bridge and fallback are both unavailable"
    );
    assertIncludes(failed, "[data-status-banner]", "neither /api/cockpit-status nor /status/cockpit-status.json");

    console.log("Dashboard live bridge source order OK");
}

if (require.main === module) {
    main().catch((error) => {
        console.error(error.message);
        process.exitCode = 1;
    });
}
