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
const authPath = path.join(repoRoot, "landing-page-repo", "auth.js");
const migrationPath = path.join(repoRoot, "migrations", "0004_fund_manager_forum.sql");

const FORUM_FIELDS = [
    "allowed_statuses",
    "allowed_target_types",
    "boundary",
    "browser_write_scope",
    "comment_count",
    "event_log_export_count",
    "local_event_log_export",
    "recent_comments",
    "schema_version",
    "status",
    "supabase_table",
    "visibility"
];

const COMMENT_FIELDS = [
    "author_label",
    "body",
    "comment_id",
    "created_at",
    "status",
    "tags",
    "target_key",
    "target_type",
    "visibility"
];

function hasOwn(value, key) {
    return Object.prototype.hasOwnProperty.call(value, key);
}

function missingFields(value, fields) {
    return fields.filter((field) => !hasOwn(value, field));
}

async function main() {
    const notes = status.fund_manager_notes || {};
    const comments = Array.isArray(notes.recent_comments) ? notes.recent_comments : [];
    const missing = missingFields(notes, FORUM_FIELDS);
    assert(!missing.length, `fund_manager_notes missing fields: ${missing.join(", ")}`);

    assert(notes.status === "ok", "fund_manager_notes status is not ok");
    assert(notes.supabase_table === "fund_manager_comments", "forum Supabase table mismatch");
    assert(notes.browser_write_scope === "comments_only", "forum browser write scope is too broad");
    assert(notes.local_event_log_export === "accepted_or_implemented_only", "forum Event Log export boundary mismatch");
    assert(notes.visibility === "founding_fund_managers", "forum visibility mismatch");
    assert(/governance notes only/i.test(notes.boundary || ""), "forum boundary is weak");
    assert(/cannot approve trades/i.test(notes.boundary || ""), "forum boundary does not block trade approval");
    assert(Array.isArray(notes.allowed_target_types), "forum target types are not an array");
    assert(Array.isArray(notes.allowed_statuses), "forum statuses are not an array");

    ["module", "source", "signal", "trade_candidate", "postmortem"].forEach((targetType) => {
        assert(notes.allowed_target_types.includes(targetType), `forum target type missing: ${targetType}`);
    });
    ["suggestion", "accepted", "rejected", "implemented"].forEach((commentStatus) => {
        assert(notes.allowed_statuses.includes(commentStatus), `forum status missing: ${commentStatus}`);
    });

    assert(notes.comment_count >= 1, "forum has no local comments");
    assert(comments.length >= 1, "forum recent comments missing");
    comments.forEach((comment) => {
        const missingCommentFields = missingFields(comment, COMMENT_FIELDS);
        assert(!missingCommentFields.length, `${comment.comment_id || "comment"} missing fields: ${missingCommentFields.join(", ")}`);
        assert(!hasOwn(comment, "author_email"), `${comment.comment_id} leaked author email`);
        assert(!hasOwn(comment, "path"), `${comment.comment_id} leaked local path`);
        assert(comment.visibility === "founding_fund_managers", `${comment.comment_id} visibility mismatch`);
    });
    assert(
        comments.some((comment) => comment.target_type === "module" && comment.target_key === "trade_layer"),
        "D8 sample trade_layer comment missing"
    );
    assert(!/@/.test(JSON.stringify(notes)), "fund_manager_notes leaked email-like content");
    assert(!/\/Users\//.test(JSON.stringify(notes)), "fund_manager_notes leaked local path");

    const rendered = await renderWithStatus(status);
    assertIncludes(rendered, "[data-flow-map]", "Governance, inbox, and communications audit");
    assertIncludes(rendered, "[data-flow-map]", "Governance and outbound communications");
    assertIncludes(rendered, "[data-flow-map]", "Comments");
    assertIncludes(rendered, "[data-flow-map]", "Approval");
    assertIncludes(rendered, "[data-flow-map]", "Review Fund Manager suggestions");
    assertIncludes(rendered, "[data-flow-map]", "suggestions mirrored");
    assertIncludes(rendered, "[data-flow-map]", "governance notes only");
    assertIncludes(rendered, "[data-flow-map]", "cannot approve trades");

    const html = fs.readFileSync(htmlPath, "utf8");
    const auth = fs.readFileSync(authPath, "utf8");
    const migration = fs.readFileSync(migrationPath, "utf8");

    [
        "data-operations-review-group=\"governance_comms_audit\"",
        "Governance, inbox, and communications audit",
        "Fund Manager comments, Chief Operating Officer inbox items, approval records, weekly review state, and outbound-only Telegram notifications.",
        "operations-review-group"
    ].forEach((needle) => assert(html.includes(needle), `dashboard forum HTML missing ${needle}`));

    [
        "const COMMENT_TABLE = \"fund_manager_comments\"",
        "wireFundManagerForum(session)",
        ".from(COMMENT_TABLE).insert",
        ".from(COMMENT_TABLE)",
        ".update({",
        "event_log_export_status",
        "pending_local_event_log_export"
    ].forEach((needle) => assert(auth.includes(needle), `auth forum client missing ${needle}`));

    [
        "CREATE TABLE IF NOT EXISTS fund_manager_comments",
        "event_log_export_status",
        "target_type",
        "target_key",
        "status TEXT NOT NULL DEFAULT 'suggestion'"
    ].forEach((needle) => assert(migration.includes(needle), `forum migration missing ${needle}`));

    console.log("Dashboard Fund Manager forum contract OK");
    console.log(`Rendered snapshot: ${statusPath}`);
    console.log(`Forum comments: ${comments.length}`);
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
