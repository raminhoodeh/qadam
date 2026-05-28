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
    "delivery_target_count",
    "delivery_target_modes",
    "dry_run_message_count",
    "failed_count",
    "group_chat_configured",
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

const TELEGRAM_INTAKE_FIELDS = [
    "bot_configured",
    "boundary",
    "broker_write_allowed",
    "enabled",
    "execution_allowed",
    "ignored_message_count",
    "latest_intake_type",
    "latest_observed_at",
    "latest_status",
    "live_capital_enabled",
    "paper_order_allowed",
    "polling_mode",
    "recent_records",
    "recent_strategy_considerations",
    "recent_world_events",
    "record_count",
    "research_triage_packet_count",
    "risk_handoff_allowed",
    "schema_version",
    "status",
    "strategy_consideration_count",
    "telegram_command_authority",
    "trade_candidate_creation_allowed",
    "world_event_datapoint_count"
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
    const telegramIntake = communications.telegram_intake || {};
    const messages = Array.isArray(telegram.recent_messages) ? telegram.recent_messages : [];
    const missing = missingFields(telegram, TELEGRAM_FIELDS);
    const missingIntake = missingFields(telegramIntake, TELEGRAM_INTAKE_FIELDS);
    assert(!missing.length, `communications.telegram missing fields: ${missing.join(", ")}`);
    assert(!missingIntake.length, `communications.telegram_intake missing fields: ${missingIntake.join(", ")}`);

    assert(telegram.status === "dry_run", "Telegram status is not dry_run");
    assert(telegram.mode === "dry_run", "Telegram mode is not dry_run");
    assert(telegram.send_gate === "disabled", "Telegram send gate is not disabled");
    assert(telegram.default_chat_configured === true, "Telegram private target is not configured");
    assert(telegram.group_chat_configured === true, "Telegram group target is not configured");
    assert(telegram.delivery_target_count >= 2, "Telegram delivery target count is too low");
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
    assert(telegramIntake.world_event_datapoint_count >= 1, "Telegram intake world-event datapoints missing");
    assert(telegramIntake.strategy_consideration_count >= 1, "Telegram intake strategy considerations missing");
    assert(telegramIntake.research_triage_packet_count >= 1, "Telegram intake research packet missing");
    assert(/read-only member research intake/i.test(telegramIntake.boundary || ""), "Telegram intake boundary is weak");
    [
        "trade_candidate_creation_allowed",
        "risk_handoff_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "telegram_command_authority",
        "live_capital_enabled"
    ].forEach((field) => {
        assert(telegramIntake[field] === false, `Telegram intake authority enabled: ${field}`);
    });
    const intakePublic = JSON.stringify(telegramIntake);
    assert(!/@/.test(intakePublic), "Telegram intake public status leaked handle-like content");
    assert(!/\/Users\//.test(intakePublic), "Telegram intake public status leaked local path");
    assert(!/chat_id|username|first_name|last_name/i.test(intakePublic), "Telegram intake public status leaked identifiers");
    assert(!/\d{6,}:[A-Za-z0-9_-]{20,}/.test(intakePublic), "Telegram intake public status leaked token-like content");

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
    assertIncludes(rendered, "[data-communications]", "Inbound member research");
    assertIncludes(rendered, "[data-communications]", "World datapoints");
    assertIncludes(rendered, "[data-communications]", "Strategy notes");
    assertIncludes(rendered, "[data-communications]", "Research packets");
    assertIncludes(rendered, "[data-communications]", "read-only member research intake");

    const html = fs.readFileSync(htmlPath, "utf8");
    const renderer = fs.readFileSync(rendererPath, "utf8");
    [
        "communications-panel",
        "data-communications",
        "Telegram notifications",
        "Telegram cannot place, approve, reject, modify, close, or resize trades"
    ].forEach((needle) => assert(html.includes(needle), `dashboard communications HTML missing ${needle}`));
    [
        "function renderCommunications",
        "status.communications?.telegram",
        "status.communications?.telegram_intake",
        "Telegram Bot",
        "notify_only",
        "Inbound member research",
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
