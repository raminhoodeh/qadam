#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const {
    assert,
    assertIncludes,
    renderWithStatus,
    status,
    statusPath
} = require("./check_dashboard_renderer.js");

const repoRoot = path.resolve(__dirname, "..");
const htmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const rendererPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");

const TELEGRAM_FIELDS = [
    "active_message_classes",
    "bot_configured",
    "boundary",
    "default_chat_configured",
    "dry_run_message_count",
    "failed_count",
    "last_sent_time",
    "member_count",
    "mode",
    "pending_member_count",
    "pending_queue_count",
    "recent_messages",
    "schema_version",
    "send_gate",
    "sent_count",
    "status",
    "suppressed_count",
    "verified_member_count"
];

const MESSAGE_FIELDS = [
    "created_at",
    "message_class",
    "message_id",
    "mode",
    "send_allowed",
    "status",
    "target_ref",
    "title"
];

function hasOwn(value, key) {
    return Object.prototype.hasOwnProperty.call(value, key);
}

function missingFields(value, fields) {
    return fields.filter((field) => !hasOwn(value, field));
}

async function main() {
    const communications = status.communications || {};
    const telegram = communications.telegram || {};
    const messages = Array.isArray(telegram.recent_messages) ? telegram.recent_messages : [];
    const missing = missingFields(telegram, TELEGRAM_FIELDS);
    assert(!missing.length, `communications.telegram missing fields: ${missing.join(", ")}`);

    assert(telegram.status === "dry_run", "Telegram status is not dry_run");
    assert(telegram.mode === "dry_run", "Telegram mode is not dry_run");
    assert(telegram.send_gate === "disabled", "Telegram send gate is not disabled");
    assert(telegram.member_count >= 5, "Telegram member count missing");
    assert(telegram.pending_queue_count >= 4, "Telegram dry-run queue missing");
    assert(telegram.dry_run_message_count >= 4, "Telegram dry-run messages missing");
    assert(/outbound-only/i.test(telegram.boundary || ""), "Telegram boundary is weak");
    ["place", "approve", "reject", "modify", "close", "resize"].forEach((verb) => {
        assert((telegram.boundary || "").includes(verb), `Telegram boundary missing ${verb}`);
    });
    ["trade_candidate", "blocked_trade", "insight_digest", "source_degraded"].forEach((messageClass) => {
        assert(telegram.active_message_classes.includes(messageClass), `Telegram class missing: ${messageClass}`);
    });
    assert(messages.length > 0, "Telegram recent messages are missing");
    messages.forEach((message) => {
        const messageMissing = missingFields(message, MESSAGE_FIELDS);
        assert(!messageMissing.length, `${message.message_id || "message"} missing fields: ${messageMissing.join(", ")}`);
        assert(message.send_allowed === false, `${message.message_id} allows sending`);
        assert(!hasOwn(message, "body"), `${message.message_id} leaked message body`);
        assert(!hasOwn(message, "chat_id"), `${message.message_id} leaked chat_id`);
        assert(!hasOwn(message, "handle"), `${message.message_id} leaked handle`);
    });
    assert(!/@/.test(JSON.stringify(telegram)), "Telegram public status leaked handle-like content");
    assert(!/\/Users\//.test(JSON.stringify(telegram)), "Telegram public status leaked local path");
    assert(!/\d{6,}:[A-Za-z0-9_-]{20,}/.test(JSON.stringify(telegram)), "Telegram public status leaked token-like content");

    const rendered = await renderWithStatus(status);
    assertIncludes(rendered, "[data-flow-map]", "Telegram Bot");
    assertIncludes(rendered, "[data-flow-map]", "Notify only");
    assertIncludes(rendered, "[data-communications]", "Status");
    assertIncludes(rendered, "[data-communications]", "dry run");
    assertIncludes(rendered, "[data-communications]", "send gate disabled");
    assertIncludes(rendered, "[data-communications]", "trade candidate");
    assertIncludes(rendered, "[data-communications]", "blocked trade");
    assertIncludes(rendered, "[data-communications]", "insight digest");
    assertIncludes(rendered, "[data-communications]", "outbound-only");

    const html = fs.readFileSync(htmlPath, "utf8");
    const renderer = fs.readFileSync(rendererPath, "utf8");
    [
        "communications-panel",
        "data-communications",
        "Telegram rail",
        "Telegram cannot place, approve, reject, modify, close, or resize trades"
    ].forEach((needle) => assert(html.includes(needle), `dashboard communications HTML missing ${needle}`));
    [
        "function renderCommunications",
        "status.communications?.telegram",
        "Telegram Bot",
        "notify_only",
        "renderCommunications(status)"
    ].forEach((needle) => assert(renderer.includes(needle), `dashboard renderer missing ${needle}`));

    console.log("Dashboard Telegram communications contract OK");
    console.log(`Rendered snapshot: ${statusPath}`);
    console.log(`Telegram dry-run messages: ${telegram.dry_run_message_count}`);
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
