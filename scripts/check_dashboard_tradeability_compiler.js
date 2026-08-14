#!/usr/bin/env node
/* Verify the compiler's public projection remains read-only and private-data free. */

const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const runtime = path.join(root, "data", "runtime");
const required = [
  "qadam_tradeability_compiler_dashboard_summary.json",
  "qadam_agent_gauntlet_dashboard_summary.json",
  "qadam_tradeability_funnel.json",
  "qadam_tradeability_public_safety_audit.json",
];
const errors = [];
const documents = {};
for (const name of required) {
  const target = path.join(runtime, name);
  if (!fs.existsSync(target)) {
    errors.push(`missing:${name}`);
    continue;
  }
  documents[name] = JSON.parse(fs.readFileSync(target, "utf8"));
}

const serialized = JSON.stringify(documents).toLowerCase();
for (const token of ["/users/", '"api_key":', '"secret":', "compiled_prompt"]) {
  if (serialized.includes(token)) errors.push(`forbidden:${token}`);
}
const dashboard = documents[required[0]] || {};
const safety = documents[required[3]] || {};
if (dashboard.public_safe !== true || dashboard.read_only !== true) {
  errors.push("dashboard_boundary_invalid");
}
if (safety.command_enabled !== false) errors.push("dashboard_command_enabled");
if (safety.status !== "passed") errors.push("public_safety_not_passed");

console.log(`status=${errors.length ? "blocked" : "passed"}`);
console.log(`artifact_count=${Object.keys(documents).length}`);
for (const error of errors) console.log(`error=${error}`);
process.exit(errors.length ? 1 : 0);
