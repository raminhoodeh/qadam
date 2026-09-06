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
    "human_brief_brief_date",
    "human_brief_dry_run",
    "human_brief_enabled",
    "human_brief_live_send_allowed",
    "human_brief_live_send_attempted",
    "human_brief_live_send_succeeded",
    "human_brief_message_human_style_status",
    "human_brief_message_specificity_score",
    "human_brief_message_specificity_status",
    "human_brief_status",
    "daily_learning_automation_dry_run",
    "daily_learning_automation_due_for_delivery",
    "daily_learning_automation_enabled",
    "daily_learning_automation_live_send_attempted",
    "daily_learning_automation_live_send_succeeded",
    "daily_learning_automation_local_date",
    "daily_learning_automation_status",
    "daily_learning_brief_brief_date",
    "daily_learning_brief_dry_run",
    "daily_learning_brief_enabled",
    "daily_learning_brief_live_send_allowed",
    "daily_learning_brief_live_send_attempted",
    "daily_learning_brief_live_send_succeeded",
    "daily_learning_brief_message_human_style_status",
    "daily_learning_brief_message_specificity_score",
    "daily_learning_brief_message_specificity_status",
    "daily_learning_brief_status",
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

const TELEGRAM_HUMAN_BRIEF_FIELDS = [
    "active_strategy_mutation_allowed",
    "already_sent",
    "blocker_count",
    "blockers",
    "body",
    "bot_configured",
    "brief_date",
    "boundary",
    "broker_write_allowed",
    "candidate_pattern_count",
    "delivery_key",
    "dry_run",
    "enabled",
    "group_chat_configured",
    "human_approval_missing_count",
    "last_delivery_failure_category",
    "live_capital_enabled",
    "live_send_attempted",
    "live_send_succeeded",
    "message_class",
    "message_fingerprint",
    "message_human_style_status",
    "message_safe",
    "message_section_header_count",
    "message_specificity_score",
    "message_specificity_status",
    "message_technical_noise_count",
    "paper_order_submission_allowed",
    "paragraph_count",
    "promotion_gate_decision_count",
    "promotion_gate_held_count",
    "promotion_review_ready_count",
    "public_safe",
    "quantum_gate_passed",
    "quantum_gate_status",
    "quantum_required",
    "schema_version",
    "source_count",
    "source_daily_edge_findings_status",
    "source_promotion_gates_status",
    "status",
    "target",
    "telegram_command_path_enabled",
    "telegram_live_send_allowed",
    "telegram_message_id_present",
    "title",
    "watched_instrument_count"
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

const DAILY_TELEGRAM_LEARNING_BRIEF_FIELDS = [
    "active_strategy_mutation_allowed",
    "already_sent",
    "blocker_count",
    "blockers",
    "body",
    "bot_configured",
    "brief_date",
    "boundary",
    "broker_write_allowed",
    "candidate_pattern_count",
    "delivery_key",
    "dry_run",
    "enabled",
    "force_delivery_window",
    "group_chat_configured",
    "human_approval_missing_count",
    "last_delivery_failure_category",
    "live_capital_enabled",
    "live_send_attempted",
    "live_send_succeeded",
    "message_human_style_status",
    "message_safe",
    "message_section_header_count",
    "message_specificity_score",
    "message_specificity_status",
    "message_technical_noise_count",
    "paper_order_submission_allowed",
    "paragraph_count",
    "public_safe",
    "quantum_gate_passed",
    "quantum_gate_status",
    "source_count",
    "status",
    "strategy_learning_applied_count",
    "target",
    "telegram_command_path_enabled",
    "telegram_live_send_allowed",
    "title",
    "watched_instrument_count"
];

const DAILY_LEARNING_AUTOMATION_FIELDS = [
    "active_strategy_mutation_allowed",
    "already_sent",
    "automation_live_send_allowed",
    "blocker_count",
    "blockers",
    "boundary",
    "broker_write_allowed",
    "cadence",
    "candidate_pattern_count",
    "daily_edge_findings_status",
    "daily_telegram_learning_brief_human_style_status",
    "daily_telegram_learning_brief_live_send_allowed",
    "daily_telegram_learning_brief_specificity_score",
    "daily_telegram_learning_brief_specificity_status",
    "daily_telegram_learning_brief_status",
    "delivery_after_local_time",
    "delivery_local_times",
    "brief_slot",
    "brief_slot_label",
    "dry_run",
    "due_for_delivery",
    "due_or_forced",
    "effective_send_requested",
    "enabled",
    "force_delivery_window",
    "human_approval_missing_count",
    "live_capital_enabled",
    "live_send_attempted",
    "live_send_succeeded",
    "local_date",
    "paper_order_submission_allowed",
    "public_safe",
    "quantum_gate_passed",
    "quantum_gate_status",
    "send_requested",
    "source_count",
    "status",
    "strategy_learning_applied_count",
    "telegram_command_path_enabled",
    "timezone",
    "watched_instrument_count"
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
    const telegramHumanBrief = communications.telegram_human_brief || {};
    const dailyTelegramLearningBrief = communications.daily_telegram_learning_brief || {};
    const dailyLearningAutomation = communications.daily_learning_automation || {};
    const messages = Array.isArray(telegram.recent_messages) ? telegram.recent_messages : [];
    const missing = missingFields(telegram, TELEGRAM_FIELDS);
    const missingIntake = missingFields(telegramIntake, TELEGRAM_INTAKE_FIELDS);
    const missingDailyDigest = missingFields(telegramDailyDigest, TELEGRAM_DAILY_DIGEST_FIELDS);
    const missingCodebaseUpgrade = missingFields(telegramCodebaseUpgrade, TELEGRAM_CODEBASE_UPGRADE_FIELDS);
    const missingHumanBrief = missingFields(telegramHumanBrief, TELEGRAM_HUMAN_BRIEF_FIELDS);
    const missingDailyLearningBrief = missingFields(dailyTelegramLearningBrief, DAILY_TELEGRAM_LEARNING_BRIEF_FIELDS);
    const missingDailyLearningAutomation = missingFields(dailyLearningAutomation, DAILY_LEARNING_AUTOMATION_FIELDS);
    assert(!missing.length, `communications.telegram missing fields: ${missing.join(", ")}`);
    assert(!missingIntake.length, `communications.telegram_intake missing fields: ${missingIntake.join(", ")}`);
    assert(!missingDailyDigest.length, `communications.telegram_daily_portfolio_digest missing fields: ${missingDailyDigest.join(", ")}`);
    assert(!missingCodebaseUpgrade.length, `communications.telegram_codebase_upgrade missing fields: ${missingCodebaseUpgrade.join(", ")}`);
    assert(!missingHumanBrief.length, `communications.telegram_human_brief missing fields: ${missingHumanBrief.join(", ")}`);
    assert(!missingDailyLearningBrief.length, `communications.daily_telegram_learning_brief missing fields: ${missingDailyLearningBrief.join(", ")}`);
    assert(!missingDailyLearningAutomation.length, `communications.daily_learning_automation missing fields: ${missingDailyLearningAutomation.join(", ")}`);

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
    assert(telegram.human_brief_enabled === true, "Telegram human brief is not enabled");
    assert(["telegram_human_brief_dry_run_ready", "telegram_human_brief_ready_to_send", "telegram_human_brief_sent", "telegram_human_brief_already_sent"].includes(telegram.human_brief_status), "Telegram human brief summary status is invalid");
    assert(["telegram_human_brief_dry_run_ready", "telegram_human_brief_ready_to_send", "telegram_human_brief_sent", "telegram_human_brief_already_sent"].includes(telegramHumanBrief.status), "Telegram human brief status is invalid");
    assert(telegramHumanBrief.target === "group", "Telegram human brief target is not group");
    assert(telegramHumanBrief.public_safe === true, "Telegram human brief is not public safe");
    assert(telegramHumanBrief.message_human_style_status === "human", "Telegram human brief is not human style");
    assert(telegramHumanBrief.message_specificity_status === "specific", "Telegram human brief is not specific");
    assert(Number(telegramHumanBrief.message_specificity_score || 0) >= 70, "Telegram human brief specificity score is too low");
    assert(Number(telegramHumanBrief.paragraph_count || 0) >= 1 && Number(telegramHumanBrief.paragraph_count || 0) <= 2, "Telegram human brief paragraph count invalid");
    assert(Number(telegramHumanBrief.message_technical_noise_count || 0) === 0, "Telegram human brief has technical noise");
    assert(Number(telegramHumanBrief.message_section_header_count || 0) === 0, "Telegram human brief has section headers");
    assert(/quantum/i.test(telegramHumanBrief.body || ""), "Telegram human brief missing quantum explanation");
    assert(/data sources/i.test(telegramHumanBrief.body || ""), "Telegram human brief missing source explanation");
    assert(/paper order/i.test(telegramHumanBrief.body || ""), "Telegram human brief missing paper-order boundary");
    assert(telegramHumanBrief.telegram_command_path_enabled === false, "Telegram human brief command authority enabled");
    assert(telegramHumanBrief.broker_write_allowed === false, "Telegram human brief broker write allowed");
    assert(telegramHumanBrief.paper_order_submission_allowed === false, "Telegram human brief paper order allowed");
    assert(telegramHumanBrief.active_strategy_mutation_allowed === false, "Telegram human brief strategy mutation allowed");
    assert(telegramHumanBrief.live_capital_enabled === false, "Telegram human brief live capital enabled");
    assert(/Telegram Human Brief/i.test(telegramHumanBrief.boundary || ""), "Telegram human brief boundary is weak");
    assert(["daily_learning_automation_disabled", "daily_learning_automation_not_due", "daily_learning_automation_quiet_no_material_change", "daily_learning_automation_dry_run_ready", "daily_learning_automation_ready_to_send", "daily_learning_automation_sent", "daily_learning_automation_already_sent"].includes(dailyLearningAutomation.status), "Daily learning automation status is invalid");
    assert(["daily_telegram_learning_brief_quiet_no_material_change", "daily_telegram_learning_brief_dry_run_ready", "daily_telegram_learning_brief_ready_to_send", "daily_telegram_learning_brief_sent", "daily_telegram_learning_brief_already_sent"].includes(dailyTelegramLearningBrief.status), "Daily Telegram learning brief status is invalid");
    assert(telegram.daily_learning_automation_status === dailyLearningAutomation.status, "Daily learning automation summary mismatch");
    assert(telegram.daily_learning_brief_status === dailyTelegramLearningBrief.status, "Daily learning brief summary mismatch");
    assert(dailyLearningAutomation.cadence === "twice_daily", "Daily learning automation cadence is invalid");
    assert(Array.isArray(dailyLearningAutomation.delivery_local_times) && dailyLearningAutomation.delivery_local_times.length === 2, "Daily learning automation must expose two delivery slots");
    assert(["morning", "evening"].includes(dailyLearningAutomation.brief_slot), "Daily learning automation brief slot is invalid");
    assert(dailyLearningAutomation.public_safe === true, "Daily learning automation is not public safe");
    assert(dailyLearningAutomation.quantum_gate_passed === true, "Daily learning automation quantum gate did not pass");
    assert(Number(dailyLearningAutomation.source_count || 0) >= 30, "Daily learning automation source count too low");
    assert(Number(dailyLearningAutomation.watched_instrument_count || 0) >= 19, "Daily learning automation watched market count too low");
    assert(Number(dailyLearningAutomation.candidate_pattern_count || 0) >= 5, "Daily learning automation candidate pattern count too low");
    assert(dailyLearningAutomation.telegram_command_path_enabled === false, "Daily learning automation command authority enabled");
    assert(dailyLearningAutomation.broker_write_allowed === false, "Daily learning automation broker write allowed");
    assert(dailyLearningAutomation.paper_order_submission_allowed === false, "Daily learning automation paper order allowed");
    assert(dailyLearningAutomation.active_strategy_mutation_allowed === false, "Daily learning automation strategy mutation allowed");
    assert(dailyLearningAutomation.live_capital_enabled === false, "Daily learning automation live capital enabled");
    assert(Number(dailyLearningAutomation.strategy_learning_applied_count || 0) === 0, "Daily learning automation applied learning");
    assert(/Daily Learning Automation/i.test(dailyLearningAutomation.boundary || ""), "Daily learning automation boundary is weak");
    assert(dailyTelegramLearningBrief.target === "group", "Daily Telegram learning brief target is not group");
    assert(dailyTelegramLearningBrief.public_safe === true, "Daily Telegram learning brief is not public safe");
    const dailyLearningIsMateriallyQuiet = (
        dailyTelegramLearningBrief.status === "daily_telegram_learning_brief_quiet_no_material_change"
    );
    // quiet_status_only describes content. A scheduled twice-daily status brief
    // can still be due; only the explicit suppressed delivery state forbids send.
    assert(dailyTelegramLearningBrief.message_human_style_status === "human", "Daily Telegram learning brief is not human style");
    if (dailyLearningIsMateriallyQuiet) {
        assert(dailyTelegramLearningBrief.notification_candidate_created === false, "Quiet daily learning state created a notification candidate");
        assert(dailyTelegramLearningBrief.live_send_attempted === false, "Quiet daily learning state attempted a live send");
    } else {
        assert(dailyTelegramLearningBrief.message_specificity_status === "specific", "Daily Telegram learning brief is not specific");
        assert(Number(dailyTelegramLearningBrief.message_specificity_score || 0) >= 70, "Daily Telegram learning brief specificity score is too low");
    }
    assert(Number(dailyTelegramLearningBrief.paragraph_count || 0) >= 1 && Number(dailyTelegramLearningBrief.paragraph_count || 0) <= 2, "Daily Telegram learning brief paragraph count invalid");
    assert(Number(dailyTelegramLearningBrief.message_technical_noise_count || 0) === 0, "Daily Telegram learning brief has technical noise");
    assert(Number(dailyTelegramLearningBrief.message_section_header_count || 0) === 0, "Daily Telegram learning brief has section headers");
    assert(
        /(?:learn(?:ed|ing)?|lesson|provider-backed evidence|candidate relationship|outcome matured|next question)/i.test(
            dailyTelegramLearningBrief.body || ""
        ),
        "Daily Telegram learning brief missing an evidence-change explanation"
    );
    if (!dailyLearningIsMateriallyQuiet) {
        if (dailyTelegramLearningBrief.quantum_update_included === false) {
            const suppressedSections = Array.isArray(dailyTelegramLearningBrief.suppressed_repeated_section_ids)
                ? dailyTelegramLearningBrief.suppressed_repeated_section_ids
                : [];
            const quantumSection = Array.isArray(dailyTelegramLearningBrief.content_sections)
                ? dailyTelegramLearningBrief.content_sections.find((section) => section.section_id === "quantum_result")
                : null;
            assert(suppressedSections.includes("quantum_result"), "Daily Telegram learning brief omitted quantum without a dedupe record");
            assert(quantumSection?.included === false, "Daily Telegram learning brief quantum suppression state is inconsistent");
            assert(quantumSection?.suppression_reason === "unchanged_within_rolling_window", "Daily Telegram learning brief quantum suppression reason is invalid");
        } else {
            assert(/quantum/i.test(dailyTelegramLearningBrief.body || ""), "Daily Telegram learning brief missing quantum explanation");
        }
        assert(
            /(?:\bsources?\b|source evidence|source freshness|provider-backed evidence|filing-index activity)/i.test(
                dailyTelegramLearningBrief.body || ""
            ),
            "Daily Telegram learning brief missing a source-evidence explanation"
        );
        assert(/paper order/i.test(dailyTelegramLearningBrief.body || ""), "Daily Telegram learning brief missing paper-order boundary");
    }
    assert(dailyTelegramLearningBrief.telegram_command_path_enabled === false, "Daily Telegram learning brief command authority enabled");
    assert(dailyTelegramLearningBrief.broker_write_allowed === false, "Daily Telegram learning brief broker write allowed");
    assert(dailyTelegramLearningBrief.paper_order_submission_allowed === false, "Daily Telegram learning brief paper order allowed");
    assert(dailyTelegramLearningBrief.active_strategy_mutation_allowed === false, "Daily Telegram learning brief strategy mutation allowed");
    assert(dailyTelegramLearningBrief.live_capital_enabled === false, "Daily Telegram learning brief live capital enabled");
    assert(Number(dailyTelegramLearningBrief.strategy_learning_applied_count || 0) === 0, "Daily Telegram learning brief applied learning");
    assert(/Daily Telegram Learning Brief/i.test(dailyTelegramLearningBrief.boundary || ""), "Daily Telegram learning brief boundary is weak");
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
    assertIncludes(rendered, "[data-flow-map]", "No Telegram command path");
    assertIncludes(rendered, "[data-flow-map]", "Governance, inbox, and communications audit");
    assertIncludes(rendered, "[data-flow-map]", "Governance and outbound communications");
    assertIncludes(rendered, "[data-flow-map]", "Fund Manager review and Telegram state without separate duplicate cards");
    assertIncludes(rendered, "[data-flow-map]", "Telegram");
    assertIncludes(rendered, "[data-flow-map]", "dry run");
    assertIncludes(rendered, "[data-flow-map]", "Dry-run");
    assertIncludes(rendered, "[data-flow-map]", "Queued");
    assertIncludes(rendered, "[data-flow-map]", "Failed");
    assertIncludes(rendered, "[data-flow-map]", "Suppressed");
    assertIncludes(rendered, "[data-flow-map]", "Live sends");
    assertIncludes(rendered, "[data-flow-map]", "send gate disabled");
    assertIncludes(rendered, "[data-flow-map]", "outbound notify-only");
    assertIncludes(rendered, "[data-flow-map]", "live send disabled");

    const html = fs.readFileSync(htmlPath, "utf8");
    const renderer = fs.readFileSync(rendererPath, "utf8");
    [
        "data-operations-review-group=\"governance_comms_audit\"",
        "Governance, inbox, and communications audit",
        "outbound-only Telegram notifications",
        "operations-review-group"
    ].forEach((needle) => assert(html.includes(needle), `dashboard communications HTML missing ${needle}`));
    [
        "function renderOperationsWorkspace",
        "renderOperationsReviewGroup",
        "communications_audit",
        "governance_comms_audit",
        "Governance and outbound communications",
        "Visible communications, no command authority",
        "status.communications?.telegram",
        "status.communications?.telegram_daily_portfolio_digest",
        "status.communications?.telegram_codebase_upgrade",
        "status.communications?.telegram_human_brief",
        "status.communications?.daily_learning_automation",
        "status.communications?.daily_telegram_learning_brief",
        "Daily learning automation",
        "Daily Telegram learning brief",
        "status.communications?.telegram_intake",
        "Telegram Bot",
        "notify_only",
        "outbound notify-only",
        "no Telegram command path",
        "live send disabled",
        "send gate"
    ].forEach((needle) => assert(renderer.includes(needle), `dashboard renderer missing ${needle}`));

    console.log("Dashboard Telegram communications contract OK");
    console.log(`Rendered snapshot: ${statusPath}`);
    console.log(`Telegram dry-run messages: ${telegram.dry_run_message_count}`);
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
