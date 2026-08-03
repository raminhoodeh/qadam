#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const dashboard = fs.readFileSync(path.join(root, "dashboard.js"), "utf8");
const status = JSON.parse(
    fs.readFileSync(path.join(root, "status", "cockpit-status.json"), "utf8")
);
const trial = status.active_discovery_trial || {};
const stages = Array.isArray(trial.seven_stage_state) ? trial.seven_stage_state : [];
const metrics = trial.metrics || {};

function requireCondition(condition, message) {
    if (!condition) throw new Error(message);
}

requireCondition(
    trial.artifact_type === "qadam_active_discovery_trial_dashboard_summary",
    "active_discovery_trial_projection_missing"
);
requireCondition(
    Number(metrics.current_instrument_evaluation_count) === 19,
    "active_discovery_trial_universe_not_complete"
);
requireCondition(stages.length === 7, "active_discovery_trial_stage_count_invalid");
requireCondition(trial.read_only === true, "active_discovery_trial_not_read_only");
requireCondition(trial.public_safe === true, "active_discovery_trial_not_public_safe");
requireCondition(
    dashboard.includes("active_discovery_trial: status.active_discovery_trial || {}"),
    "active_discovery_trial_view_model_binding_missing"
);
requireCondition(
    dashboard.includes("data-qsase-active-discovery-trial"),
    "active_discovery_trial_renderer_missing"
);
requireCondition(
    dashboard.includes("decisionTotal(\"hold\")"),
    "active_discovery_trial_akber_count_normalization_missing"
);

console.log("active_discovery_trial_dashboard_check=passed");
console.log(`active_discovery_trial_dashboard_status=${trial.status}`);
console.log(`active_discovery_trial_dashboard_stages=${stages.length}`);
console.log(
    `active_discovery_trial_dashboard_instruments=${metrics.current_instrument_evaluation_count}`
);
