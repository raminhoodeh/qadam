#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const {
    assert,
    html,
    renderWithStatus,
    status
} = require("./check_dashboard_renderer.js");

const repoRoot = path.resolve(__dirname, "..");
const htmlPath = path.join(repoRoot, "landing-page-repo", "dashboard", "index.html");
const cssPath = path.join(repoRoot, "landing-page-repo", "auth.css");
const rendererPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");
const authPath = path.join(repoRoot, "landing-page-repo", "auth.js");
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-master-implementation-plan.md");
const auditPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-dx-11-governance-audit-2026-05-25.md");

const dashboardHtml = fs.readFileSync(htmlPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");
const renderer = fs.readFileSync(rendererPath, "utf8");
const auth = fs.readFileSync(authPath, "utf8");
const plan = fs.readFileSync(planPath, "utf8");

function includesAll(text, needles, label) {
    needles.forEach((needle) => {
        assert(text.includes(needle), `${label} missing ${needle}`);
    });
}

function loadRendererWindow() {
    const document = {
        documentElement: { dataset: {} },
        querySelector() {
            return null;
        },
        querySelectorAll() {
            return [];
        }
    };
    const window = { document };
    const context = {
        Array,
        Boolean,
        Date,
        Error,
        Intl,
        Map,
        Math,
        Number,
        Object,
        Promise,
        Set,
        String,
        console,
        document,
        fetch: async () => ({ ok: true, json: async () => status }),
        localStorage: {
            getItem() {
                return null;
            },
            setItem() {}
        },
        sessionStorage: {
            getItem() {
                return null;
            },
            setItem() {}
        },
        window
    };
    window.window = window;
    vm.createContext(context);
    vm.runInContext(renderer, context, { filename: rendererPath });
    return window;
}

async function main() {
    includesAll(dashboardHtml, [
        "Governance workspace",
        "Comments, approvals, reviews, and outbound communications",
        "Contextual comment entry points",
        "Comment without memorizing internal reference keys",
        "data-comment-target-button",
        "data-comment-target-select",
        "comments governance-only",
        "approvals audit-only",
        "Telegram outbound-only",
        "live capital disabled"
    ], "Governance workspace static shell");
    assert(!dashboardHtml.includes("placeholder=\"trade_layer\""), "raw reference-key text placeholder still present");
    assert(dashboardHtml.includes("<select name=\"target_key\" data-comment-target-select required>"), "comment target assisted selector missing");

    includesAll(css, [
        ".governance-workspace",
        ".governance-workspace-head",
        ".governance-boundary-card",
        ".governance-status-grid",
        ".governance-target-grid",
        ".governance-record-grid",
        ".governance-action-list",
        ".governance-communications-card",
        ".governance-weekly-card",
        "html[data-dashboard-active-view=\"operations\"] .comments-panel"
    ], "Governance workspace CSS");

    includesAll(renderer, [
        "function buildGovernanceCommentTargets",
        "function buildGovernanceApprovalRecords",
        "function buildGovernanceOpenActions",
        "function renderGovernanceWorkspace",
        "function renderGovernanceTargetButton",
        "function syncGovernanceCommentTargetOptions",
        "function initGovernanceCommentTargetButtons",
        "Telegram outbound-only",
        "no Telegram command path",
        "Live-promotion review workflow",
        "Weekly review pack"
    ], "Governance workspace renderer");

    includesAll(auth, [
        "\"resource\"",
        "\"world_model\"",
        "COMMENT_TARGET_TYPES",
        "buildCommentPayload"
    ], "Governance auth comment target types");

    const window = loadRendererWindow();
    assert(typeof window.buildQadamDashboardGovernanceModel === "function", "governance model builder not exported");
    const governance = window.buildQadamDashboardGovernanceModel(status);
    const commentTargets = governance.comment_targets || [];
    const targetViews = commentTargets.map((target) => target.view);
    const approvals = governance.approvals?.records || [];

    assert(governance.id === "governance", "governance model id mismatch");
    ["Trades", "Evidence", "Reasoning", "Operations"].forEach((view) => {
        assert(targetViews.includes(view), `comment target missing view ${view}`);
    });
    assert(approvals.length >= 6, "approval/review records missing");
    [
        "Phase 4 strategy approval",
        "Phase 5 certification",
        "Phase 6 learning approval",
        "Weekly review pack",
        "Live-promotion review workflow",
        "Telegram send-test approval"
    ].forEach((label) => assert(approvals.some((record) => record.label === label), `missing governance record ${label}`));
    assert(governance.review_packs.weekly_proof_trade_target === 3, "weekly proof target missing from governance");
    assert(governance.communications.command_path_enabled === false, "Telegram command path enabled");
    assert(governance.communications.command_path_enabled_count === 0, "Telegram command path count nonzero");
    assert(governance.communications.live_send_allowed_count === 0, "Telegram live send count nonzero");
    assert(governance.live_promotion.live_capital_enabled === false, "governance reports live capital enabled");

    const rendered = await renderWithStatus(status);
    const governanceHtml = html(rendered, "[data-governance-workspace]");
    [
        "Governance workspace",
        "Comments, approvals, reviews, and outbound communications",
        "comments governance-only",
        "approvals audit-only",
        "Telegram outbound-only",
        "live capital disabled",
        "Contextual comment entry points",
        "Trade candidate:",
        "Observed signal:",
        "Strategy Lead / reasoning chain",
        "30-day demo proof",
        "Operations health",
        "Approval and review records",
        "Phase 4 strategy approval",
        "Phase 5 certification",
        "Phase 6 learning approval",
        "Weekly review pack",
        "Live-promotion review workflow",
        "Telegram send-test approval",
        "Open action items",
        "Telegram outbound state",
        "no Telegram command path",
        "live send disabled",
        "outbound notify-only",
        "Weekly review and live-promotion workflow"
    ].forEach((needle) => assert(governanceHtml.includes(needle), `rendered governance workspace missing ${needle}`));

    [
        "/Users/",
        "api_key",
        "PREFERENCE_API_KEY",
        "ALPACA_SECRET",
        "Q_CTRL",
        "raw_payload",
        "private_payload",
        "local_path",
        "request_body",
        "broker_identifier"
    ].forEach((needle) => {
        assert(!governanceHtml.includes(needle), `governance workspace leaked non-public-safe marker ${needle}`);
    });

    [
        "DX-11 - Governance And Communications Workspace",
        "Move Fund Manager comments, approval records, weekly review packs",
        "Replace raw reference-key entry with assisted selectors",
        "scripts/check_dashboard_overhaul_governance.js"
    ].forEach((needle) => {
        assert(plan.includes(needle), `master plan missing DX-11 marker: ${needle}`);
    });
    assert(fs.existsSync(auditPath), "DX-11 audit document missing");

    console.log("dashboard_overhaul_governance=ok");
    console.log("dashboard_governance_comment_target_count=" + commentTargets.length);
    console.log("dashboard_governance_approval_record_count=" + approvals.length);
    console.log("dashboard_governance_open_action_count=" + governance.open_actions.length);
    console.log("dashboard_governance_telegram_command_path_enabled=False");
    console.log("dashboard_governance_authority_unchanged=True");
}

if (require.main === module) {
    main().catch((error) => {
        console.error(error.message);
        process.exitCode = 1;
    });
}
