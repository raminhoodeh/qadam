#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const {
    assert,
    html,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

const repoRoot = path.resolve(__dirname, "..");
const dashboardHtml = fs.readFileSync(path.join(repoRoot, "landing-page-repo", "dashboard", "index.html"), "utf8");
const renderer = fs.readFileSync(path.join(repoRoot, "landing-page-repo", "dashboard.js"), "utf8");

function textOnly(value) {
    return String(value || "")
        .replace(/<script[\s\S]*?<\/script>/g, " ")
        .replace(/<style[\s\S]*?<\/style>/g, " ")
        .replace(/<[^>]+>/g, " ")
        .replace(/&amp;/g, "&")
        .replace(/\s+/g, " ")
        .trim();
}

function assertIncludes(text, needle, label) {
    assert(text.includes(needle), `${label} missing ${needle}`);
}

function assertAbsent(text, needle, label) {
    assert(!text.includes(needle), `${label} still includes repetitive copy: ${needle}`);
}

function count(text, needle) {
    return String(text).split(needle).length - 1;
}

async function main() {
    const combinedSource = `${dashboardHtml}\n${renderer}`;
    [
        "Paper Trading Overview",
        "Mission Control brief",
        "Mission control is read-only",
        "The current status of Qadam's paper trading system.",
        "Summary first; Diagnostics keeps technical detail.",
        "Canonical operating flow - tap + to expand",
        "Loading what Qadam",
        "You supervise Qadam",
        "Safety Status is the authority summary.",
        "Qadam's thoughts",
        "One screen for what Qadam is watching, thinking, considering, holding, and doing"
    ].forEach((needle) => assertAbsent(combinedSource, needle, "dashboard source"));

    [
        "Mission Control",
        "Founder brief",
        "Strategy posture",
        "Operating flow",
        "Tap + to expand each role",
        "Reasoning queue",
        "Human oversight",
        "This is read-only mission control"
    ].forEach((needle) => assertIncludes(combinedSource, needle, "dashboard source"));

    const rendered = await renderWithStatus(status);
    const overviewText = textOnly([
        html(rendered, "[data-overview-mission-brief]"),
        html(rendered, "[data-overview-strategy-narrative]"),
        html(rendered, "[data-overview-system-summary]"),
        html(rendered, "[data-overview-oversight]"),
        html(rendered, "[data-overview-thought-feed]"),
        html(rendered, "[data-overview-boundary-rail]")
    ].join(" "));

    [
        "Mission Control brief",
        "You supervise Qadam",
        "Qadam's thoughts",
        "A trade idea is not an order",
        "Safety Status is the authority summary"
    ].forEach((needle) => assertAbsent(overviewText, needle, "rendered overview"));

    [
        "Founder brief",
        "Human oversight",
        "Reasoning queue",
        "Trade ideas stay candidates until gated paper-order records exist"
    ].forEach((needle) => assertIncludes(overviewText, needle, "rendered overview"));

    assert(count(overviewText, "This is read-only mission control") <= 2, "rendered overview repeats read-only mission control too often");
    assert(count(overviewText, "Trade ideas stay candidates") <= 2, "rendered overview repeats trade-candidate boundary too often");

    console.log("dashboard_cc9_slop_repetition=ok");
    console.log("dashboard_cc9_cache_key=20260607-cc9-copy-runthrough");
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
