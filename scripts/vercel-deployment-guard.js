#!/usr/bin/env node
"use strict";

const { execFileSync, spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

function checkIdentity(authorEmail, accountEmail) {
  const author = String(authorEmail || "").trim().toLowerCase();
  const account = String(accountEmail || "").trim().toLowerCase();
  if (!author || !account || author !== account) {
    throw new Error(
      "Commit author does not match the authenticated Vercel account. " +
      "Configure this repository's user.email to your registered account email " +
      "and create a new reviewed commit; do not rewrite history or override author metadata."
    );
  }
}

function checkDeployment(deployment, { projectId, commit, deploymentHost }) {
  const state = deployment.readyState || deployment.status;
  if (deployment.seatBlock || ["BLOCKED", "ERROR", "CANCELED"].includes(state)) {
    throw new Error(`Vercel deployment is ${deployment.seatBlock ? "BLOCKED" : state}; production promotion stopped. Check project access or build logs.`);
  }
  if (deployment.projectId !== projectId || deployment.target !== "production" || deployment.url !== deploymentHost) {
    throw new Error("Vercel deployment does not match the expected project, target and URL.");
  }
  const commits = [deployment.gitSource?.sha, deployment.meta?.gitCommitSha, deployment.meta?.githubCommitSha].filter(Boolean);
  if (commits.length === 0 || commits.some((value) => value !== commit)) {
    throw new Error("Vercel deployment does not match the reviewed commit.");
  }
  if (state === "READY") return true;
  if (!["QUEUED", "INITIALIZING", "BUILDING"].includes(state)) {
    throw new Error("Vercel returned an unknown deployment state; production promotion stopped.");
  }
  return false;
}

async function waitUntilReady(read, expected, {
  timeoutMs = 900000, pollMs = 4000, now = Date.now,
  sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
} = {}) {
  const deadline = now() + timeoutMs;
  while (now() < deadline) {
    const deployment = await read(Math.min(20000, deadline - now()));
    if (checkDeployment(deployment, expected)) return deployment;
    await sleep(Math.min(pollMs, Math.max(0, deadline - now())));
  }
  throw new Error("Vercel deployment readiness timed out; no production promotion authorized.");
}

async function api(resource, timeoutMs = 20000) {
  const token = process.env.VERCEL_TOKEN;
  if (!token) throw new Error("VERCEL_TOKEN is required.");
  let response;
  try {
    response = await fetch(`https://api.vercel.com${resource}`, {
      headers: { Authorization: `Bearer ${token}` },
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch {
    throw new Error("Vercel API request failed or timed out; production promotion stopped.");
  }
  if (!response.ok) throw new Error(`Vercel API returned HTTP ${response.status}; production promotion stopped.`);
  return response.json();
}

function runBounded(command, args, timeoutMs = 300000) {
  // Never echo argv: deployment commands may carry runtime credentials.
  return new Promise((resolve, reject) => {
    let timedOut = false;
    const child = spawn(command, args, { stdio: "inherit", detached: true });
    const timer = setTimeout(() => {
      timedOut = true;
      try { process.kill(-child.pid, "SIGKILL"); } catch { /* Child already exited. */ }
    }, timeoutMs);
    child.on("error", () => {
      clearTimeout(timer);
      reject(new Error("Deployment command could not start."));
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      if (timedOut) reject(new Error("Deployment command timed out; inspect Vercel before retrying."));
      else if (code !== 0) reject(new Error(`Deployment command failed with exit code ${code}.`));
      else resolve();
    });
  });
}

async function main(args) {
  const [mode, ...rest] = args;
  if (mode === "run" && rest.length) {
    await runBounded(rest[0], rest.slice(1));
    return;
  }
  if (mode === "identity" && rest.length === 1) {
    const author = execFileSync("git", ["-C", rest[0], "show", "-s", "--format=%ae", "HEAD"], { encoding: "utf8" });
    const { user } = await api("/v2/user");
    checkIdentity(author, user?.email);
    console.log("[qadam-deploy] Commit author matches the authenticated Vercel account.");
    return;
  }
  if (mode === "wait" && rest.length === 3) {
    const [url, commit, siteDir] = rest;
    const parsed = new URL(url);
    if (parsed.protocol !== "https:" || !parsed.hostname.endsWith(".vercel.app") || parsed.pathname !== "/" || parsed.search || parsed.hash || parsed.username || parsed.password || parsed.port) {
      throw new Error("Invalid Vercel deployment URL.");
    }
    const project = JSON.parse(fs.readFileSync(path.join(siteDir, ".vercel/project.json"), "utf8"));
    const team = process.env.VERCEL_TEAM_ID;
    if (!team || project.orgId !== team) throw new Error("Vercel project team does not match the deployment scope.");
    await waitUntilReady(
      (timeoutMs) => api(`/v13/deployments/${encodeURIComponent(parsed.hostname)}?teamId=${encodeURIComponent(team)}`, timeoutMs),
      { projectId: project.projectId, commit, deploymentHost: parsed.hostname },
    );
    console.log("[qadam-deploy] Vercel reports READY for the exact reviewed production commit.");
    return;
  }
  throw new Error("Usage: vercel-deployment-guard.js identity SITE | wait URL COMMIT SITE | run COMMAND ARGS...");
}

module.exports = { checkIdentity, checkDeployment, waitUntilReady, runBounded };
if (require.main === module) {
  main(process.argv.slice(2)).catch((error) => {
    console.error(`[qadam-deploy] ${error.message}`);
    process.exitCode = 1;
  });
}
