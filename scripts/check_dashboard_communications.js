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
    "daily_portfolio_digest_daily_trade_count",
    "daily_portfolio_digest_due_for_delivery",
    "daily_portfolio_digest_enabled",
    "daily_portfolio_digest_portfolio_balance_gbp",
    "daily_portfolio_digest_portfolio_performance_pct",
    "daily_portfolio_digest_status",
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

const TELEGRAM_DAILY_DIGEST_FIELDS = [
    "already_sent",
    "blocker_count",
    "blockers",
    "boundary",
    "broker_write_allowed",
    "daily_trade_count",
    "daily_trade_summaries",
    "delivery_after_local_time",
    "dry_run",
    "due_for_delivery",
    "enabled",
    "last_delivery_failure_category",
    "live_capital_enabled",
    "live_send_attempted",
    "live_send_succeeded",
    "local_date",
    "message_fingerprint",
    "message_specificity_score",
    "message_specificity_status",
    "paper_order_allowed",
    "paperops_idle_reason",
    "paperops_qualified_setup_count",
    "paperops_submitted_paper_order_count",
    "portfolio_balance_gbp",
    "portfolio_performance_pct",
    "portfolio_total_pnl_gbp",
    "schema_version",
    "status",
    "target",
    "telegram_command_path_enabled",
    "telegram_message_id_present",
    "timezone"
];

const TELEGRAM_CODEBASE_UPGRADE_FIELDS = [
    "aliases",
    "already_sent",
    "blocker_count",
    "blockers",
    "boundary",
    "benefits",
    "broker_write_allowed",
    "change_area_lines",
    "dashboard_changed_file_count",
    "dashboard_change_areas",
    "dashboard_commit_short",
    "dashboard_last_commit_subject",
    "dashboard_dirty",
    "deploy_allowed",
    "details",
    "deployment_url",
    "dry_run",
    "enabled",
    "last_delivery_failure_category",
    "live_capital_enabled",
    "live_send_attempted",
    "live_send_succeeded",
    "message_fingerprint",
    "message_specificity_score",
    "message_specificity_status",
    "paper_order_allowed",
    "repository_write_allowed",
    "root_changed_file_count",
    "root_change_areas",
    "root_commit_short",
    "root_last_commit_subject",
    "root_dirty",
    "schema_version",
    "source",
    "status",
    "summary",
    "target",
    "telegram_command_path_enabled",
    "telegram_message_id_present"
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
    const telegramDailyDigest = communications.telegram_daily_portfolio_digest || {};
    const telegramCodebaseUpgrade = communications.telegram_codebase_upgrade || {};
    const messages = Array.isArray(telegram.recent_messages) ? telegram.recent_messages : [];
    const missing = missingFields(telegram, TELEGRAM_FIELDS);
    const missingIntake = missingFields(telegramIntake, TELEGRAM_INTAKE_FIELDS);
    const missingDailyDigest = missingFields(telegramDailyDigest, TELEGRAM_DAILY_DIGEST_FIELDS);
    const missingCodebaseUpgrade = missingFields(telegramCodebaseUpgrade, TELEGRAM_CODEBASE_UPGRADE_FIELDS);
    assert(!missing.length, `communications.telegram missing fields: ${missing.join(", ")}`);
    assert(!missingIntake.length, `communications.telegram_intake missing fields: ${missingIntake.join(", ")}`);
    assert(!missingDailyDigest.length, `communications.telegram_daily_portfolio_digest missing fields: ${missingDailyDigest.join(", ")}`);
    assert(!missingCodebaseUpgrade.length, `communications.telegram_codebase_upgrade missing fields: ${missingCodebaseUpgrade.join(", ")}`);

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
    assert(telegram.daily_portfolio_digest_enabled === true, "Daily portfolio digest is not enabled");
    assert(["not_due", "ready_to_send", "sent", "already_sent", "dry_run_ready"].includes(telegram.daily_portfolio_digest_status), "Daily portfolio digest status is invalid");
    assert(telegramDailyDigest.enabled === true, "Daily portfolio digest public status is not enabled");
    assert(telegramDailyDigest.target === "group", "Daily portfolio digest target is not group");
    assert(Number(telegramDailyDigest.portfolio_balance_gbp) >= 0, "Daily portfolio digest balance is invalid");
    assert(telegramDailyDigest.telegram_command_path_enabled === false, "Daily portfolio digest command authority enabled");
    assert(telegramDailyDigest.broker_write_allowed === false, "Daily portfolio digest broker write allowed");
    assert(telegramDailyDigest.paper_order_allowed === false, "Daily portfolio digest paper order allowed");
    assert(telegramDailyDigest.live_capital_enabled === false, "Daily portfolio digest live capital enabled");
    assert(telegramDailyDigest.message_specificity_status === "specific" || telegramDailyDigest.status === "not_run" || telegramDailyDigest.status === "degraded", "Daily portfolio digest message is not specific");
    assert(Number(telegramDailyDigest.message_specificity_score || 0) >= 70 || telegramDailyDigest.status === "not_run" || telegramDailyDigest.status === "degraded", "Daily portfolio digest specificity score is too low");
    assert(typeof telegramDailyDigest.paperops_idle_reason === "string" || telegramDailyDigest.paperops_idle_reason === null, "Daily portfolio digest idle reason missing");
    assert(/Daily Telegram portfolio digests/i.test(telegramDailyDigest.boundary || ""), "Daily portfolio digest boundary is weak");
    assert(telegram.codebase_upgrade_notifications_enabled === true, "Codebase upgrade notification is not enabled");
    assert(["already_sent", "blocked_pending_enablement", "dry_run_ready", "failed", "not_run", "ready_to_send", "sent", "suppressed_not_safe"].includes(telegram.codebase_upgrade_notifications_status), "Codebase upgrade notification status is invalid");
    assert(telegramCodebaseUpgrade.enabled === true, "Codebase upgrade public status is not enabled");
    assert(telegramCodebaseUpgrade.target === "group", "Codebase upgrade target is not group");
    assert(telegramCodebaseUpgrade.telegram_command_path_enabled === false, "Codebase upgrade command authority enabled");
    assert(telegramCodebaseUpgrade.broker_write_allowed === false, "Codebase upgrade broker write allowed");
    assert(telegramCodebaseUpgrade.paper_order_allowed === false, "Codebase upgrade paper order allowed");
    assert(telegramCodebaseUpgrade.repository_write_allowed === false, "Codebase upgrade repo write allowed");
    assert(telegramCodebaseUpgrade.deploy_allowed === false, "Codebase upgrade deploy authority allowed");
    assert(telegramCodebaseUpgrade.live_capital_enabled === false, "Codebase upgrade live capital enabled");
    assert(/codebase upgrade notifications/i.test(telegramCodebaseUpgrade.boundary || ""), "Codebase upgrade boundary is weak");
    assert(Array.isArray(telegramCodebaseUpgrade.details) && telegramCodebaseUpgrade.details.length >= 2, "Codebase upgrade details are missing");
    assert(Array.isArray(telegramCodebaseUpgrade.benefits) && telegramCodebaseUpgrade.benefits.length >= 2, "Codebase upgrade benefits are missing");
    assert(Array.isArray(telegramCodebaseUpgrade.change_area_lines) && telegramCodebaseUpgrade.change_area_lines.length >= 1, "Codebase upgrade change areas are missing");
    assert(telegramCodebaseUpgrade.message_specificity_status === "specific" || telegramCodebaseUpgrade.status === "not_run" || telegramCodebaseUpgrade.status === "degraded", "Codebase upgrade message is not specific");
    assert(Number(telegramCodebaseUpgrade.message_specificity_score || 0) >= 70 || telegramCodebaseUpgrade.status === "not_run" || telegramCodebaseUpgrade.status === "degraded", "Codebase upgrade specificity score is too low");
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
    assertIncludes(rendered, "[data-communications]", "Daily portfolio digest");
    assertIncludes(rendered, "[data-communications]", "Codebase upgrade notifications");
    assertIncludes(rendered, "[data-communications]", "Core commit");
    assertIncludes(rendered, "[data-communications]", "Dashboard commit");
    assertIncludes(rendered, "[data-communications]", "Why it matters");
    assertIncludes(rendered, "[data-communications]", "Portfolio balance");
    assertIncludes(rendered, "[data-communications]", "Trades today");
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
        "status.communications?.telegram_daily_portfolio_digest",
        "status.communications?.telegram_codebase_upgrade",
        "status.communications?.telegram_intake",
        "Telegram Bot",
        "notify_only",
        "Daily portfolio digest",
        "Codebase upgrade notifications",
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
