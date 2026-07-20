#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const dashboardRoot = path.resolve(
    process.env.QADAM_DASHBOARD_SITE_ROOT || path.join(root, "landing-page-repo")
);
const getApi = fs.readFileSync(path.join(dashboardRoot, "api/cockpit-status.js"), "utf8");
const publishApi = fs.readFileSync(path.join(dashboardRoot, "api/cockpit-status-publish.js"), "utf8");
const dashboard = fs.readFileSync(path.join(dashboardRoot, "dashboard.js"), "utf8");
const sql = fs.readFileSync(path.join(root, "ops/supabase/qadam_public_status_snapshots.sql"), "utf8");

const errors = [];
function requireText(name, text, expected) {
    if (!text.includes(expected)) errors.push(`${name}:missing:${expected}`);
}

requireText("get_api", getApi, '["GET", "HEAD"]');
requireText("get_api", getApi, "canonical_payload");
requireText("get_api", getApi, "signature_verified: true");
requireText("get_api", getApi, 'storage_backend: "supabase_private_object"');
requireText("get_api", getApi, 'state: "static_fallback"');
requireText("publish_api", publishApi, 'req.method !== "POST"');
requireText("publish_api", publishApi, "createHmac");
requireText("publish_api", publishApi, "canonical_payload: raw.toString");
requireText("publish_api", publishApi, "ensurePrivateBucket");
requireText("publish_api", publishApi, '"x-upsert": "true"');
requireText("publish_api", publishApi, "validateBoundary");
requireText("dashboard", dashboard, 'If-None-Match');
requireText("sql", sql, "canonical_payload text");
requireText("sql", sql, "enable row level security");

for (const forbidden of ["place_order", "submit_order", "cancel_order", "broker_write_allowed: true"]) {
    if (getApi.includes(forbidden) || publishApi.includes(forbidden)) {
        errors.push(`forbidden_authority:${forbidden}`);
    }
}

async function productionCheck() {
    if (!process.argv.includes("--production")) return;
    const base = process.env.QADAM_DASHBOARD_BASE_URL || "https://qadam.trade";
    const response = await fetch(`${base.replace(/\/$/, "")}/api/cockpit-status`, {
        method: "GET",
        cache: "no-store"
    });
    if (!response.ok) {
        errors.push(`production_http_status:${response.status}`);
        return;
    }
    const source = response.headers.get("x-qadam-status-source");
    const payload = await response.json();
    if (source !== "signed_public_status_store") errors.push(`production_source:${source}`);
    if (payload.live_bridge?.delivery?.signature_verified !== true) {
        errors.push("production_signature_not_verified");
    }
    if (payload.live_bridge?.delivery?.state !== "live") {
        errors.push(`production_delivery_state:${payload.live_bridge?.delivery?.state}`);
    }
}

productionCheck().then(() => {
    console.log(`dashboard_live_bridge_check=${errors.length ? "blocked" : "passed"}`);
    console.log(`dashboard_live_bridge_error_count=${errors.length}`);
    console.log("dashboard_live_bridge_command_route=false");
    console.log("dashboard_live_bridge_broker_write_route=false");
    errors.forEach((error) => console.log(`dashboard_live_bridge_error=${error}`));
    process.exitCode = errors.length ? 1 : 0;
}).catch((error) => {
    console.log("dashboard_live_bridge_check=blocked");
    console.log(`dashboard_live_bridge_error=${error.name}`);
    process.exitCode = 1;
});
