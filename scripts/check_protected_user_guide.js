#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "..");
const guideHtmlPath = path.join(repoRoot, "landing-page-repo", "guide", "index.html");
const guideDocPath = path.join(repoRoot, "docs", "qadam-user-guide.md");
const dashboardHtmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const authPath = path.join(repoRoot, "landing-page-repo", "auth.js");

const guideHtml = fs.readFileSync(guideHtmlPath, "utf8");
const guideDoc = fs.readFileSync(guideDocPath, "utf8");
const dashboardHtml = fs.readFileSync(dashboardHtmlPath, "utf8");
const auth = fs.readFileSync(authPath, "utf8");

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

function assertIncludes(text, expected, label) {
    assert(text.includes(expected), `${label} missing: ${expected}`);
}

function assertNoUnsafePublicText(text, label) {
    const forbidden = [
        /\/Users\//,
        /\/private\//,
        /\/var\/folders\//,
        /\\Users\\/,
        /\d{6,}:[A-Za-z0-9_-]{20,}/,
        /sk-[A-Za-z0-9_-]{20,}/,
        /ghp_[A-Za-z0-9_]{20,}/,
        /PVZ[0-9A-Za-z_-]{20,}/,
        /TELEGRAM_BOT_TOKEN=/,
        /TELEGRAM_DEFAULT_CHAT_ID=/,
        /SUPABASE_SECRET_KEY=/,
        /GEMINI_API_KEY=/
    ];
    forbidden.forEach((pattern) => {
        assert(!pattern.test(text), `${label} contains unsafe public text: ${pattern}`);
    });
}

function countMatches(text, pattern) {
    return (text.match(pattern) || []).length;
}

[
    "Private user guide",
    "How To Use Qadam",
    "data-dashboard",
    "hidden",
    "data-user-email",
    "data-signout",
    "/auth.js?v=20260517-guide",
    "/dashboard/"
].forEach((needle) => assertIncludes(guideHtml, needle, "guide HTML"));

assertIncludes(dashboardHtml, "href=\"/guide/\"", "dashboard nav");
assertIncludes(dashboardHtml, "User Guide", "dashboard nav");
assertIncludes(auth, "const currentPath = cleanNext(`${window.location.pathname}${window.location.search}`);", "auth redirect");
assertIncludes(auth, "window.location.replace(`/login/?next=${encodeURIComponent(currentPath)}`);", "auth redirect");
assertIncludes(auth, "emailIsAllowed(session.user.email)", "auth allowlist");

[
    "Overview view",
    "Trades view",
    "Evidence view",
    "Reasoning view",
    "Operations view",
    "QSASE Dashboard Sections",
    "Portfolio Value &amp; Return",
    "Current Portfolio",
    "Trading History",
    "Source Intelligence Network",
    "Trading Strategy Universe",
    "Pattern Recognition Findings",
    "Trade Intents / What Qadam Is Thinking",
    "Router &amp; PaperOps Gate",
    "Advanced / Debug Mode",
    "Safety Status",
    "Old Implementation Terms",
    "System map",
    "Secure Live Bridge",
    "Telegram",
    "Status Labels",
    "Trade States",
    "How Qadam Finds And Acts On Edge",
    "edge is not one headline",
    "edge memory ledger",
    "daily Telegram learning brief",
    "weekly thesis refresh",
    "quantum/classical review",
    "Alpaca Paper",
    "30-day paper growth trial",
    "paper proof ledger",
    "Qadam Self-Aware Strategy Engine",
    "Strategy update proposals are not applied automatically",
    "Daily Operating Routine",
    "What Members Can And Cannot Do",
    "Red Flags",
    "First Release Success"
].forEach((needle) => assertIncludes(guideHtml, needle, "guide HTML"));

[
    "Overview",
    "Trades",
    "Evidence",
    "Reasoning",
    "Operations",
    "QSASE Dashboard Sections",
    "Portfolio Value & Return",
    "Current Portfolio",
    "Trading History",
    "Source Intelligence Network",
    "Trading Strategy Universe",
    "Pattern Recognition Findings",
    "Trade Intents / What Qadam Is Thinking",
    "Router & PaperOps Gate",
    "Advanced / Debug Mode",
    "Safety Status",
    "Old Implementation Terms",
    "System map",
    "Secure Live Bridge",
    "Important labels",
    "Trade states",
    "How Qadam Finds And Acts On Edge",
    "edge is not one headline",
    "edge memory ledger",
    "daily Telegram learning brief",
    "weekly thesis refresh",
    "quantum/classical review",
    "Alpaca Paper",
    "30-day paper growth trial",
    "paper proof ledger",
    "Qadam Self-Aware Strategy Engine",
    "Strategy update proposals are not applied automatically",
    "Daily Operating Routine",
    "What Members Can Do",
    "Red Flags",
    "First Release Success"
].forEach((needle) => assertIncludes(guideDoc, needle, "guide markdown"));

[
    guideHtml,
    guideDoc
].forEach((text, index) => {
    const label = index === 0 ? "guide HTML" : "guide markdown";
    assert(!text.includes("five primary views"), `${label} still describes the old five-view IA`);
    assert(!text.includes("Seven Mission Control Sections"), `${label} still describes the old Mission Control IA`);
    assert(!text.includes("60-day paper growth"), `${label} still describes the old 60-day paper growth wording`);
});

[
    "Online",
    "Pending",
    "Degraded",
    "Blocked",
    "Local-only",
    "Read-only ready",
    "Dry-run",
    "Notify-only",
    "OK - paper only",
    "OK - read-only",
    "OK - live capital off",
    "Dashboard cannot place orders",
    "AI cannot bypass risk checks",
    "Observed signal",
    "Candidate",
    "Staged paper order",
    "Submitted paper order",
    "Open position",
    "Closed trade",
    "Postmortem due",
    "Postmortem complete"
].forEach((needle) => assertIncludes(guideHtml, needle, "guide vocabulary"));

[
    "A hypothesis is not a trade",
    "A candidate is not an order",
    "worldview is not evidence",
    "approve, create, modify, close, resize, or submit trades",
    "should never show bot tokens",
    "raw message payloads, or local paths",
    "Use the Secure Live Bridge to run commands or trade",
    "The bridge claims write authority, broker authority, shell access, or local orchestrator exposure",
    "Use Telegram to approve, reject, modify, close, or resize trades",
    "Any secret, token, chat ID, local path, or credential appears in the UI"
].forEach((needle) => assertIncludes(guideDoc, needle, "guide markdown boundary"));

[
    "A hypothesis is not a trade",
    "A candidate is not an order",
    "Telegram cannot place, approve, reject, modify, close, or resize trades",
    "handles or chat IDs",
    "Use the Secure Live Bridge to run commands or trade",
    "The bridge claims write authority, broker authority, shell access, or local orchestrator exposure",
    "Use Telegram to approve, reject, modify, close, or resize trades",
    "Any secret, token, chat ID, local path, or credential appears in the UI"
].forEach((needle) => assertIncludes(guideHtml, needle, "guide HTML boundary"));

[
    "Open Watching",
    "Open Cognition",
    "Open Worldview",
    "Open Trade Layer",
    "Open Money",
    "Open Forbidden",
    "Start with Mission Control"
].forEach((needle) => {
    assert(!guideHtml.includes(needle), `guide HTML still tells users to hunt old panel: ${needle}`);
    assert(!guideDoc.includes(needle), `guide markdown still tells users to hunt old panel: ${needle}`);
});

assert(countMatches(guideHtml, /<h3>Overview view<\/h3>/g) === 1, "guide has duplicate Overview view card heading");
assert(!/<section>\s*<section>/.test(guideHtml), "guide has nested adjacent section tags");
assert(!guideHtml.includes("Planned outbound-only"), "guide still describes Telegram as only planned");
assertNoUnsafePublicText(guideHtml, "guide HTML");
assertNoUnsafePublicText(guideDoc, "guide markdown");

console.log("Protected User Guide contract OK");
console.log(`Guide HTML: ${guideHtmlPath}`);
console.log(`Guide source: ${guideDocPath}`);
