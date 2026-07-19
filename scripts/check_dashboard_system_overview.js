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
const dashboardSiteRoot = path.resolve(
    process.env.QADAM_DASHBOARD_SITE_ROOT || path.join(repoRoot, "landing-page-repo")
);
const renderer = fs.readFileSync(path.join(dashboardSiteRoot, "dashboard.js"), "utf8");
const css = fs.readFileSync(path.join(dashboardSiteRoot, "auth.css"), "utf8");
const operatorDashboard = status.qsase_dashboard?.sections?.operator_dashboard || {};

const expectedRoutes = [
    "system/team",
    "fund/portfolio",
    "fund/timeline",
    "observe/sources",
    "observe/universe",
    "patterns/findings",
    "patterns/nonlinear",
    "decide/strategies",
    "decide/decision",
    "trade/orders",
    "learn/outcomes",
    "learn/improvements",
    "system/overview"
];

async function main() {
    const rendered = await renderWithStatus(status);
    const dashboard = html(rendered, "[data-stage7-dashboard-visibility]");
    const renderedRoutes = [];
    const panelPattern = /data-qsase-module-panel="([^"]+)" data-qsase-view-panel="([^"]+)"/g;
    let match;
    while ((match = panelPattern.exec(dashboard)) !== null) {
        renderedRoutes.push(`${match[1]}/${match[2]}`);
    }

    assert(JSON.stringify(renderedRoutes) === JSON.stringify(expectedRoutes), "System Overview route matrix mismatch");
    assert(
        dashboard.indexOf('data-qsase-module-target="system" data-qsase-view-target="team"')
            < dashboard.indexOf('data-qsase-module-target="fund" data-qsase-view-target="portfolio"'),
        "Qadam Team is not pinned above Fund"
    );
    assert(!dashboard.includes('data-qsase-nav-group="system"'), "System returned as a nested sidebar group");
    assert(dashboard.includes("qsase-standalone-nav qsase-system-nav"), "standalone System link missing");
    assert(dashboard.includes("<strong>System</strong><small>Full operating picture</small>"), "standalone System label missing");
    assert(
        dashboard.indexOf("qsase-standalone-nav qsase-system-nav")
            > dashboard.indexOf('data-qsase-module-target="learn" data-qsase-view-target="improvements"'),
        "standalone System link is not below the operating journey"
    );

    [
        "System Operations &amp; Diagnostics",
        "System Overview",
        "Overall infrastructure health",
        "Expected operating restriction — not an infrastructure incident",
        "What Needs Attention Now",
        "Infrastructure &amp; Connections",
        "Automations &amp; Scheduled Work",
        "Data Freshness &amp; Monitoring",
        "Effect on Qadam",
        "Incidents &amp; Recoveries",
        "Technical Evidence"
    ].forEach((needle) => assert(dashboard.includes(needle), `System Overview missing ${needle}`));
    assert(dashboard.includes("data-qadam-system-diagnostic-console"), "System diagnostic console hook missing");
    assert(dashboard.includes("data-qadam-system-health-verdict"), "always-visible infrastructure verdict missing");
    assert(dashboard.includes("Page updated"), "page projection timestamp missing");
    assert(dashboard.includes("Last operator-service check"), "operator-service evidence timestamp missing");
    assert(!dashboard.includes("Last complete system check"), "an operator-service timestamp was overstated as a complete system check");
    const operatorServiceEvidenceStart = dashboard.indexOf("<small>Last operator-service check</small>");
    const operatorServiceEvidenceEnd = dashboard.indexOf("</span>", operatorServiceEvidenceStart);
    assert(operatorServiceEvidenceStart >= 0 && operatorServiceEvidenceEnd > operatorServiceEvidenceStart, "operator-service evidence element missing");
    const operatorServiceEvidence = dashboard.slice(operatorServiceEvidenceStart, operatorServiceEvidenceEnd);
    const operatorCheckState = operatorDashboard.views?.["system/overview"]?.overall_health?.operator_service_check_state;
    if (operatorCheckState === "stale") {
        assert(operatorServiceEvidence.includes("Evidence overdue"), "stale service evidence is not clearly labelled");
    } else {
        assert(!operatorServiceEvidence.includes("Evidence overdue"), "fresh service evidence was incorrectly labelled overdue");
    }
    assert(
        (dashboard.match(/data-qadam-system-accordion="/g) || []).length === 6,
        "System Overview should contain exactly six major diagnostic disclosures"
    );
    assert(
        !/data-qadam-system-accordion="[^"]+"[^>]*\sopen(?:\s|>)/.test(dashboard),
        "major System disclosures must be collapsed by default"
    );
    assert(
        (dashboard.match(/data-qadam-system-domain-tab="/g) || []).length
            === (operatorDashboard.views?.["system/overview"]?.infrastructure_domains || []).length,
        "rendered infrastructure domain count does not reconcile with the canonical projection"
    );

    [
        'data-qsase-view-panel="activity"',
        'data-qsase-view-panel="health"',
        "Qadam Pulse Terminal",
        "Public thought stream",
        "matrix-rain",
        "qsase-terminal-frame"
    ].forEach((needle) => assert(!dashboard.includes(needle), `legacy System surface returned: ${needle}`));

    [
        "candidate === \"system/activity\"",
        "candidate === \"system/health\"",
        "function renderQadamLifecycleTimeline",
        "function renderQadamLifecycleHealthMatrix",
        "data-qsase-nav-route",
        "window.history.replaceState",
        "function qsaseSystemOverviewModel",
        "function renderQsaseSystemOverview",
        "function renderQsaseSystemDisclosure",
        "function renderQsaseSystemIncidents",
        "function renderQsaseSystemInfrastructure",
        "function renderQsaseSystemAutomations",
        "function renderQsaseSystemDataDependencies",
        "function renderQsaseSystemEvents",
        "function renderQsaseSystemTechnical",
        "function qsaseSystemCountReport",
        "function qsaseSystemJobTone",
        "function qsaseSystemAutomationMeta",
        "last_operator_service_check_at",
        "Generated-evidence state not reported",
        "diskFreeRaw !== null",
        "function initQsaseSystemDiagnostics",
        "data-qadam-system-accordion-group",
        "data-qadam-system-domain-tab",
        "candidate.open = false"
    ].forEach((needle) => assert(renderer.includes(needle), `System route behavior missing ${needle}`));
    assert(!renderer.includes("last_complete_system_check_at"), "legacy complete-system-check field remains in the frontend model");

    [
        ".qsase-standalone-nav",
        ".qsase-system-nav",
        ".qsase-system-verdict",
        ".qsase-system-mode-context",
        ".qsase-system-priority",
        ".qsase-system-incident",
        ".qsase-system-disclosure",
        ".qsase-system-domain-browser",
        ".qsase-system-domain-tabs",
        ".qsase-system-domain-panels",
        ".qsase-system-service-details",
        ".qsase-system-data-summary",
        ".qsase-system-event-list",
        ".qsase-system-technical-group",
        ".qadam-lifecycle-health-table",
        ".qsase-system-freshness-list",
        "prefers-reduced-motion"
    ].forEach((needle) => assert(css.includes(needle), `System Overview CSS missing ${needle}`));

    assert(!css.includes(".qsase-pulse-terminal"), "legacy pulse terminal CSS returned");
    assert(!css.includes(".matrix-rain"), "legacy matrix CSS returned");

    const truthStatus = JSON.parse(JSON.stringify(status));
    const truthOverview = truthStatus.qsase_dashboard?.sections?.operator_dashboard?.views?.["system/overview"];
    assert(truthOverview, "System truth-case fixture is unavailable");
    truthOverview.overall_health.last_operator_service_check_at = "2026-07-17T00:00:00Z";
    truthOverview.services_schedules_jobs.last_checked_at = null;
    truthOverview.services_schedules_jobs.service_count = 8;
    truthOverview.services_schedules_jobs.scheduled_count = 6;
    truthOverview.services_schedules_jobs.running_count = 0;
    truthOverview.services_schedules_jobs.running_count_known = false;
    truthOverview.services_schedules_jobs.policy_paused_count = 2;
    truthOverview.services_schedules_jobs.services[0].diagnostic_state = "paused_by_policy";
    truthOverview.services_schedules_jobs.services[0].tone = "policy";
    truthOverview.data_dependencies = {
        sources: { source_count: 0, fresh_count: 0, last_checked_at: null },
        artifacts: { artifact_count: 0, fresh_count: 0, stale_count: 0, missing_count: 0, last_checked_at: "2026-07-17T00:00:00Z" },
        historical_jobs: { total_jobs: 2, completed_jobs: 0, remaining_jobs: 2, status: "In progress", tone: "degraded", last_checked_at: "2026-07-17T00:00:00Z" },
        key_dependencies: []
    };
    truthOverview.technical_diagnostics.operator_service.running = null;
    truthOverview.technical_diagnostics.supervisor.generated_at = null;
    truthOverview.technical_diagnostics.supervisor.progress = {
        completed_jobs: 0,
        total_jobs: 0
    };
    truthOverview.technical_diagnostics.supervisor.resource_state.disk_free_gb = null;
    const truthRendered = await renderWithStatus(truthStatus);
    const truthDashboard = html(truthRendered, "[data-stage7-dashboard-visibility]");
    assert(truthDashboard.includes("Run state unverified · 6 scheduled workflows · 2 policy-paused"), "unverified automation state was presented as a verified running ratio");
    assert(/qsase-system-data-summary[\s\S]*?<article class="unmonitored"><span>Data sources<\/span><strong>Not reported<\/strong>/.test(truthDashboard), "unreported source counts were presented as healthy");
    assert(/qsase-system-data-summary[\s\S]*?<article class="unmonitored"><span>Generated evidence<\/span><strong>Not reported<\/strong>/.test(truthDashboard), "zero-denominator artifact counts were presented as healthy");
    assert(/qsase-system-data-summary[\s\S]*?<article class="pending"><span>Historical preparation<\/span><strong>0 \/ 2 complete<\/strong><p>In progress/.test(truthDashboard), "an in-progress historical job was presented as degraded");
    assert(truthDashboard.includes("<dt>Running</dt><dd>Not verified</dd>"), "unknown operator running state was presented as No");
    assert(truthDashboard.includes("<dt>Disk free</dt><dd>Not reported</dd>"), "null disk capacity was presented as a numeric reading");
    assert(truthDashboard.includes("<dt>Historical progress</dt><dd>Not reported</dd>"), "missing historical progress was presented as 0 / 0");
    assert(/qsase-system-service-details[\s\S]*?<details class="policy">/.test(truthDashboard), "policy-paused workflow did not honor its exported tone");

    const zeroDiskStatus = JSON.parse(JSON.stringify(truthStatus));
    zeroDiskStatus.qsase_dashboard.sections.operator_dashboard.views["system/overview"].technical_diagnostics.supervisor.resource_state.disk_free_gb = 0;
    const zeroDiskDashboard = html(await renderWithStatus(zeroDiskStatus), "[data-stage7-dashboard-visibility]");
    assert(zeroDiskDashboard.includes("<dt>Disk free</dt><dd>0.0 GB</dd>"), "a valid zero disk reading was discarded as unreported");

    const missingOnlyStatus = JSON.parse(JSON.stringify(status));
    const missingOnlyOverview = missingOnlyStatus.qsase_dashboard.sections.operator_dashboard.views["system/overview"];
    missingOnlyOverview.data_dependencies.artifacts = {
        artifact_count: 2,
        fresh_count: 1,
        stale_count: 0,
        missing_count: 1,
        last_checked_at: "2026-07-17T00:00:00Z"
    };
    const missingOnlyDashboard = html(await renderWithStatus(missingOnlyStatus), "[data-stage7-dashboard-visibility]");
    assert(
        missingOnlyDashboard.includes("1/2 current · 0 overdue · 1 not present"),
        "collapsed freshness summary hid a missing-only evidence failure"
    );

    const emptyInventoryStatus = JSON.parse(JSON.stringify(status));
    const emptyAutomation = emptyInventoryStatus.qsase_dashboard.sections.operator_dashboard.views["system/overview"].services_schedules_jobs;
    emptyAutomation.last_checked_at = "2026-07-17T00:00:00Z";
    emptyAutomation.check_freshness_state = "fresh";
    emptyAutomation.running_count = null;
    emptyAutomation.running_count_known = false;
    emptyAutomation.scheduled_count = 0;
    emptyAutomation.service_count = 0;
    emptyAutomation.stopped_count = null;
    emptyAutomation.policy_paused_count = 0;
    emptyAutomation.services = [];
    const emptyInventoryDashboard = html(await renderWithStatus(emptyInventoryStatus), "[data-stage7-dashboard-visibility]");
    assert(
        emptyInventoryDashboard.includes("Workflow inventory not reported · 0 policy-paused"),
        "empty workflow inventory was presented as a verified 0 of 0 ratio"
    );

    const contract = operatorDashboard.navigation_contract || {};
    const overview = operatorDashboard.views?.["system/overview"] || {};
    assert(JSON.stringify(contract.route_order) === JSON.stringify(expectedRoutes), "canonical route order mismatch");
    assert(contract.contract_version === "qadam_protected_decision_flow.v5", "navigation contract version mismatch");
    assert(contract.route_count === 13, "canonical route count should be 13");
    assert(contract.cross_cutting_routes_in_journey === false, "cross-cutting routes entered the journey");
    assert(contract.standalone_cross_cutting?.[0]?.view_id === "overview", "standalone System contract missing");
    assert(contract.legacy_route_aliases?.["system/activity"] === "system/overview", "activity alias missing");
    assert(contract.legacy_route_aliases?.["system/health"] === "system/overview", "health alias missing");
    assert(contract.legacy_route_aliases?.["learn/replay"] === "learn/improvements", "replay alias missing");
    assert(contract.legacy_route_aliases?.["learn/briefs"] === "learn/outcomes", "brief alias missing");
    assert(overview.artifact_type === "qadam_system_overview", "canonical System Overview projection missing");
    assert(overview.diagnostic_contract_version === "qadam_system_diagnostics.v2", "System diagnostic V2 contract missing");
    assert(operatorDashboard.end_to_end_lifecycle?.stage_count === 10, "canonical lifecycle should contain ten stages");
    assert(operatorDashboard.end_to_end_lifecycle?.single_global_current_stage === false, "System Overview must not claim one global stage");
    assert(["healthy", "degraded"].includes(overview.overall_health?.state), "overall infrastructure health state invalid");
    assert(overview.operating_mode?.is_infrastructure_failure === false, "operating mode was misclassified as an infrastructure failure");
    assert((overview.infrastructure_domains || []).length === 8, "infrastructure inventory should contain eight domains");
    assert(Array.isArray(overview.services_schedules_jobs?.services), "scheduled workflow inventory missing");
    assert(Array.isArray(overview.root_cause_incidents?.rows), "root-cause incident list missing");
    assert(Array.isArray(overview.system_events?.rows), "typed system event list missing");
    assert(
        overview.root_cause_incidents.total_count === overview.root_cause_incidents.rows.length,
        "root-cause incident totals do not reconcile"
    );
    assert(
        overview.infrastructure_domains.filter((domain) => domain.tone === "unmonitored").length
            === overview.overall_health.monitoring_gap_count,
        "monitoring-gap total does not reconcile with the infrastructure inventory"
    );
    assert(
        overview.infrastructure_domains
            .filter((domain) => domain.tone === "unmonitored")
            .every((domain) => domain.status !== "Healthy"),
        "an unmonitored infrastructure domain was presented as healthy"
    );
    assert(
        !overview.root_cause_incidents.rows.some((incident) => /research lock|validated edge/i.test(`${incident.title} ${incident.summary}`)),
        "intentional research restrictions leaked into infrastructure incidents"
    );

    console.log("dashboard_system_overview=ok");
    console.log(`dashboard_system_overview_route_count=${renderedRoutes.length}`);
    console.log(`dashboard_system_overview_service_count=${overview.services_schedules_jobs.services.length}`);
    console.log(`dashboard_system_overview_incident_count=${overview.root_cause_incidents.rows.length}`);
    console.log(`dashboard_system_overview_domain_count=${overview.infrastructure_domains.length}`);
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
