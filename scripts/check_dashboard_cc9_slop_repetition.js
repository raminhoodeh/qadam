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

function assertCount(text, needle, expected, label) {
    const actual = count(text, needle);
    assert(actual === expected, `${label} expected ${expected} occurrence(s) of ${needle}, got ${actual}`);
}

function assertCountAtLeast(text, needle, expected, label) {
    const actual = count(text, needle);
    assert(actual >= expected, `${label} expected at least ${expected} occurrence(s) of ${needle}, got ${actual}`);
}

function assertCountAtMost(text, needle, expected, label) {
    const actual = count(text, needle);
    assert(actual <= expected, `${label} expected at most ${expected} occurrence(s) of ${needle}, got ${actual}`);
}

function assertAllAbsent(text, needles, label) {
    needles.forEach((needle) => assertAbsent(text, needle, label));
}

function assertAllIncludes(text, needles, label) {
    needles.forEach((needle) => assertIncludes(text, needle, label));
}

async function main() {
    const combinedSource = `${dashboardHtml}\n${renderer}`;
    assertAllAbsent(combinedSource, [
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
        "One screen for what Qadam is watching, thinking, considering, holding, and doing",
        "One source-backed readout",
        "One source-backed module",
        "Fund Manager oversight",
        "Fund Manager oversight is merged",
        "Loading paper account mirror",
        "Loading the active thesis",
        "The fit matrix below",
        "These families can continue",
        "Unqualified families stay",
        "Loading the operating team, handoff path",
        "Fund Manager oversight, source feed state",
        "Overview shows source posture only",
        "Trade rows are lifecycle state only",
        "Read-only dashboard",
        "Hide diagnostics",
        "Default to Mission Snapshot",
        "Read paper mirror and lifecycle counts",
        "Use Strategy Universe for strategy posture",
        "Show lifecycle counts only",
        "Show source posture only",
        "Control Plane owns operating flow",
        "data-overview-data-sources",
        "data-overview-thought-feed",
        "data-overview-cockpit-grid",
        "data-overview-thinking-grid",
        "data-overview-trade-board"
    ], "dashboard source");

    assertAllIncludes(combinedSource, [
        "Mission Control",
        "Real portfolio timeline",
        "Mission Snapshot",
        "Paper Account &amp; Trade State",
        "Strategy Universe",
        "Control Plane",
        "Data source tracker",
        "Loading portfolio value, trade timeline, and paper-account state.",
        "Human oversight",
        "portfolio-trade-timeline",
        "renderContractPortfolioHero",
        "renderPortfolioTradeTimeline"
    ], "dashboard source");

    assertCount(dashboardHtml, "overview-decision-records", 0, "static dashboard shell decision records");

    const rendered = await renderWithStatus(status);
    const overviewHtml = [
        html(rendered, "[data-overview-portfolio-hero]"),
        html(rendered, "[data-overview-mission-brief]"),
        html(rendered, "[data-overview-strategy-narrative]"),
        html(rendered, "[data-overview-paper-trade-state]"),
        html(rendered, "[data-overview-control-plane]"),
        html(rendered, "[data-overview-source-summary]"),
    ].join(" ");
    const overviewText = textOnly(overviewHtml);

    assertAllAbsent(overviewText, [
        "Mission Control brief",
        "You supervise Qadam",
        "Qadam's thoughts",
        "A trade idea is not an order",
        "Safety Status is the authority summary",
        "One source-backed readout",
        "One source-backed module",
        "Fund Manager oversight",
        "Fund Manager oversight is merged",
        "Loading paper account mirror",
        "Loading the active thesis",
        "The fit matrix below",
        "These families can continue",
        "Unqualified families stay",
        "Overview shows source posture only",
        "Trade rows are lifecycle state only",
        "Default to Mission Snapshot",
        "Read paper mirror and lifecycle counts",
        "Use Strategy Universe for strategy posture",
        "Show lifecycle counts only",
        "Show source posture only",
        "Control Plane owns operating flow",
        "live capital enabled"
    ], "rendered overview");

    assertAllAbsent(overviewHtml, [
        "data-overview-data-sources",
        "data-overview-thought-feed",
        "data-overview-cockpit-grid",
        "data-overview-thinking-grid",
        "data-overview-trade-board",
        "Worldview prior",
        "USO options watch"
    ], "rendered overview html");

    assertAllIncludes(overviewText, [
        "Real portfolio timeline",
        "Trade timeline",
        "Bought and held",
        "Sold and closed",
        "Mission Snapshot",
        "Human oversight",
        "Control Plane",
        "Data source tracker",
        "Source list",
        "Paper Account & Trade State",
        "Total P&L",
        "Strategy family ledger",
        "Safety Policy"
    ], "rendered overview");

    assertCount(overviewHtml, "data-overview-decision-records", 0, "rendered overview decision records");
    assertCountAtMost(overviewText, "This is read-only mission control", 2, "rendered overview read-only mission control copy");
    assertCount(overviewText, "Full source rows and connection ledgers live in Evidence", 0, "rendered overview evidence routing copy");
    assertCount(overviewText, "Full signal rows, candidate lineage", 0, "rendered overview trade routing copy");

    assertAllIncludes(overviewText, [
        "Semiconductor Policy Options Asymmetry",
        "Defence Repricing Geopolitical Watch",
        "Silver Macro Liquidity Stress",
        "Crude Oil Energy Security Disruption",
        "Prediction Market Geopolitical Dislocation",
        "Qadam-native edge"
    ], "rendered overview strategy universe");

    [
        "Semiconductor Policy Options Asymmetry",
        "Defence Repricing Geopolitical Watch",
        "Silver Macro Liquidity Stress",
        "Crude Oil Energy Security Disruption",
        "Prediction Market Geopolitical Dislocation",
        "Qadam-native edge"
    ].forEach((needle) => assertCount(overviewText, needle, 1, "rendered overview strategy universe"));

    assertAllAbsent(overviewText, [
        "Click to see universe",
        "picks-and-shovels",
        "harder to fool",
        "faster to click",
        "AI slop",
        "magic",
        "revolutionary",
        "cutting-edge",
        "game-changing",
        "seamless",
        "unlock",
        "holistic",
        "synergy",
        "AI-powered",
        "intelligent insights"
    ], "rendered overview");

    console.log("dashboard_cc9_slop_repetition=ok");
    console.log("dashboard_cc9_cache_key=20260619-hedge-fund-team");
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
