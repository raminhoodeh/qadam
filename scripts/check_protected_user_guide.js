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
    "Portfolio",
    "Qadam Team",
    "System Overview",
    "QSASE Dashboard Sections",
    "Portfolio",
    "Trading History",
    "composition by asset or market sleeve",
    "gross and net exposure",
    "P&amp;L contribution",
    "Every module uses the same 10-stage lifecycle map",
    "Data Sources",
    "Trading Universe",
    "Trading Strategies",
    "Pattern Recognition",
    "Quantum Edge",
    "Decision Room",
    "Current Fund Position",
    "Research Ideas Approaching Decision",
    "Ready for Decision Room",
    "Previous Decision Reviews",
    "Akber's Multi-Stage Decision-Making Filter",
    "The practical questions and auditable lifecycle are one six-stage explanation",
    "Lifecycle Health by Stage",
    "Health by Domain",
    "Technical Diagnostics",
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
    "matched classical baseline",
    "Alpaca Paper",
    "paper evaluation window",
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
    "Portfolio",
    "Trading History",
    "composition by asset or market sleeve",
    "gross and net exposure",
    "P&L contribution",
    "Every module starts with the same 10-stage lifecycle",
    "Data Sources",
    "Trading Universe",
    "Trading Strategies",
    "Pattern Recognition",
    "Quantum Edge",
    "Decision Room",
    "Current Fund Position",
    "Research Ideas Approaching Decision",
    "Ready for Decision Room",
    "Previous Decision Reviews",
    "Akber's Multi-Stage Decision-Making Filter",
    "The practical questions and auditable lifecycle are one six-stage explanation",
    "Lifecycle Health by Stage",
    "Health by Domain",
    "Technical Diagnostics",
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
    "matched classical baseline",
    "Alpaca Paper",
    "paper evaluation window",
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

assert(countMatches(guideHtml, /<h3>Portfolio<\/h3>/g) === 1, "guide has duplicate Portfolio card heading");
assert(countMatches(guideHtml, /<h3>System Overview<\/h3>/g) === 1, "guide has duplicate System Overview card heading");
[
    "The original six trading questions",
    "How Qadam makes those questions auditable",
    "Qadam preserves those questions and turns them into six auditable lifecycle stages"
].forEach((oldHeading) => {
    assert(!guideHtml.includes(oldHeading), `guide HTML retains split Akber explanation: ${oldHeading}`);
    assert(!guideDoc.includes(oldHeading), `guide markdown retains split Akber explanation: ${oldHeading}`);
});
const akberGuideHtml = guideHtml.slice(
    guideHtml.indexOf("<h2>Akber's Multi-Stage Decision-Making Filter</h2>"),
    guideHtml.indexOf("<h2>How Qadam Finds And Acts On Edge</h2>")
);
const akberGuideDoc = guideDoc.slice(
    guideDoc.indexOf("## 13. Akber's Multi-Stage Decision-Making Filter"),
    guideDoc.indexOf("## 14. How To Review A Trade Idea")
);
assert(countMatches(akberGuideHtml, /class="guide-table"/g) === 1, "guide HTML Akber section must contain one merged table");
assert(countMatches(akberGuideHtml, /<div><strong>[1-6]\. /g) === 6, "guide HTML Akber table must contain six merged rows");
assert(countMatches(akberGuideDoc, /^[1-6]\. \*\*/gm) === 6, "guide markdown Akber section must contain six merged stages");
assert(!/<section>\s*<section>/.test(guideHtml), "guide has nested adjacent section tags");
assert(!guideHtml.includes("Planned outbound-only"), "guide still describes Telegram as only planned");
assertNoUnsafePublicText(guideHtml, "guide HTML");
assertNoUnsafePublicText(guideDoc, "guide markdown");

console.log("Protected User Guide contract OK");
console.log(`Guide HTML: ${guideHtmlPath}`);
console.log(`Guide source: ${guideDocPath}`);
