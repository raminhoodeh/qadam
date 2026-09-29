#!/usr/bin/env node
"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { checkIdentity, checkDeployment, waitUntilReady, runBounded } = require("./vercel-deployment-guard");

const expected = { projectId: "project", commit: "reviewed", deploymentHost: "release.vercel.app" };
const ready = { projectId: "project", target: "production", url: expected.deploymentHost, readyState: "READY", meta: { gitCommitSha: "reviewed" } };

test("registered author is accepted without changing author metadata", () => {
  checkIdentity("Owner@Example.com\n", "owner@example.com");
});
test("local or missing author/account fails before preflight", () => {
  for (const pair of [["owner@Mac.local", "owner@example.com"], ["", ""], ["owner@example.com", undefined]]) {
    assert.throws(() => checkIdentity(...pair), /Commit author does not match/);
  }
});
test("exact READY CLI and Git deployments pass", () => {
  assert.equal(checkDeployment(ready, expected), true);
  assert.equal(checkDeployment({ ...ready, meta: {}, gitSource: { sha: "reviewed" } }, expected), true);
});
test("blocked, errored, canceled and unknown deployments cannot be promoted", () => {
  for (const state of ["BLOCKED", "ERROR", "CANCELED", "UNKNOWN", undefined]) {
    assert.throws(() => checkDeployment({ ...ready, readyState: state }, expected));
  }
  assert.throws(() => checkDeployment({ ...ready, readyState: "BUILDING", seatBlock: { blockCode: "TEAM_ACCESS_REQUIRED" } }, expected), /BLOCKED/);
});
test("wrong project, target, URL or commit and missing commit fail closed", () => {
  for (const patch of [{ projectId: "other" }, { target: "preview" }, { url: "other.vercel.app" }, { meta: {} }, { meta: { gitCommitSha: "other" } }, { gitSource: { sha: "other" } }]) {
    assert.throws(() => checkDeployment({ ...ready, ...patch }, expected));
  }
});
test("pending states wait for READY", async () => {
  const states = ["QUEUED", "INITIALIZING", "BUILDING", "READY"];
  let calls = 0;
  const result = await waitUntilReady(async () => ({ ...ready, readyState: states[calls++] }), expected, { sleep: async () => {} });
  assert.equal(result.readyState, "READY");
  assert.equal(calls, 4);
});
test("BLOCKED terminates polling immediately", async () => {
  let calls = 0;
  await assert.rejects(waitUntilReady(async () => { calls++; return { ...ready, readyState: "BLOCKED" }; }, expected), /BLOCKED/);
  assert.equal(calls, 1);
});
test("readiness deadline prevents unbounded BUILDING waits", async () => {
  let clock = 0;
  await assert.rejects(waitUntilReady(async () => ({ ...ready, readyState: "BUILDING" }), expected, {
    timeoutMs: 10, pollMs: 5, now: () => clock, sleep: async (ms) => { clock += ms; },
  }), /timed out/);
  assert.equal(clock, 10);
});
test("API failures are not treated as READY", async () => {
  await assert.rejects(waitUntilReady(async () => { throw new Error("offline"); }, expected), /offline/);
});
test("command deadline and exit failures are bounded without echoing secrets", async () => {
  await assert.rejects(runBounded(process.execPath, ["-e", "setInterval(() => {}, 1000)", "private-token"], 50), /timed out/);
  await assert.rejects(runBounded(process.execPath, ["-e", "process.exit(2)"]), /exit code 2/);
  await runBounded(process.execPath, ["-e", "process.exit(0)"]);
});
test("shell deployment orders identity, preflight, creation, readiness, aliases and receipt", () => {
  const script = fs.readFileSync(path.join(__dirname, "deploy-vercel-production.sh"), "utf8");
  const steps = ['"${deploy_guard}" identity', 'bash "${ROOT_DIR}/scripts/preflight_dashboard_deployment.sh"', '"${vercel_cmd[@]}" deploy', '"${deploy_guard}" wait', '"${vercel_cmd[@]}" alias set', 'receipt_path='];
  const offsets = steps.map((step) => script.indexOf(step));
  assert.ok(offsets.every((offset, index) => offset >= 0 && (index === 0 || offset > offsets[index - 1])));
  assert.match(script, /--no-wait/);
  assert.match(script, /--skip-domain/);
  assert.doesNotMatch(script, /--force \\\n/);
});
