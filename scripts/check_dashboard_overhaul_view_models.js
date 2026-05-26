#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const repoRoot = path.resolve(__dirname, "..");
const rendererPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");
const statusPath = path.join(repoRoot, "landing-page-repo", "status", "cockpit-status.json");
const planPath = path.join(repoRoot, "docs", "qadam-dashboard-overhaul-master-implementation-plan.md");

const rendererCode = fs.readFileSync(rendererPath, "utf8");
const status = JSON.parse(fs.readFileSync(statusPath, "utf8"));
const plan = fs.readFileSync(planPath, "utf8");

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

function clone(value) {
    return JSON.parse(JSON.stringify(value));
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
        fetch: async () => ({ ok: true, json: async () => ({}) }),
        localStorage: {
            getItem() {
                return null;
            },
            setItem() {}
        },
        window
    };
    window.window = window;
    vm.createContext(context);
    vm.runInContext(rendererCode, context, { filename: rendererPath });
    return window;
}

function build(window, snapshot, source = { key: "live_bridge" }) {
    assert(typeof window.buildQadamDashboardViewModels === "function", "dashboard view-model builder not exported");
    return window.buildQadamDashboardViewModels(snapshot, source);
}

function assertModelShape(models) {
    [
        "overview_model",
        "trades_model",
        "sources_model",
        "reasoning_model",
        "performance_model",
        "system_connectivity_model",
        "operations_model",
        "governance_model",
        "safety_strip_model",
        "safety_model"
    ].forEach((key) => assert(models[key], `view model missing ${key}`));

    assert(models.schema_version === "dashboard_view_models.v1", "wrong dashboard view-model schema version");
    assert(models.public_safe === true, "view models must be public safe");
    assert(models.authority_boundary.includes("read-only projections"), "view-model authority boundary missing");
    assert(models.overview_model.cards.length >= 6, "Overview model should expose first-screen cards");
    assert(models.trades_model.lifecycle.length >= 8, "Trades model should expose lifecycle states");
    assert(models.system_connectivity_model.id === "system_connectivity_model", "connectivity model id mismatch");
    assert(models.system_connectivity_model.nodes.length > 0, "connectivity model has no nodes");
    assert(models.system_connectivity_model.lanes.length > 0, "connectivity model has no lanes");
    assert(models.system_connectivity_model.edges.length > 0, "connectivity model has no edges");
    assert(models.operations_model.system_connectivity_model.id === "system_connectivity_model", "Operations must own full connectivity model");
    assert(models.overview_model.mini_map.source_model === "system_connectivity_model", "Overview mini-map must point at shared connectivity model");

    const nodeKeys = new Set(models.system_connectivity_model.nodes.map((node) => node.key));
    models.overview_model.mini_map.node_keys.forEach((key) => {
        assert(nodeKeys.has(key), `Overview mini-map references missing connectivity node ${key}`);
    });
}

function assertPublicSafe(models) {
    const payload = JSON.stringify(models);
    [
        "/Users/",
        "PREFERENCE_API_KEY",
        "Q_CTRL",
        "ALPACA_SECRET",
        "api_key",
        "private_payload",
        "local_path",
        "request_body",
        "broker_identifier"
    ].forEach((needle) => {
        assert(!payload.includes(needle), `view models leaked non-public-safe marker ${needle}`);
    });
}

function assertPlainOverview(models) {
    const primaryText = models.overview_model.cards
        .map((card) => `${card.label} ${card.state} ${card.summary}`)
        .join(" ");
    [
        "D0",
        "D1",
        "D5",
        "D7",
        "D9",
        "Q4",
        "Q5",
        "Q6",
        "Q7",
        "Phase 4",
        "Phase 5",
        "Phase 6",
        "Phase 7",
        "static snapshot",
        "secure bridge"
    ].forEach((term) => {
        assert(!primaryText.includes(term), `Overview primary view model uses internal term ${term}`);
    });
    assert(
        models.safety_strip_model.live_capital_label === "Live capital off",
        "single safety strip must keep live-capital safety explicit"
    );
    assert(
        models.safety_strip_model.boundary.includes("cannot approve"),
        "single safety strip boundary missing"
    );
}

function assertFixtureCoverage(window) {
    const missing = build(window, {}, { key: "static_snapshot" });
    assert(missing.sources_model.empty_state?.key === "missing", "missing fixture should expose missing source state");
    assert(missing.trades_model.empty_state?.key === "normal_no_trade", "missing fixture should expose normal no-trade state");
    assert(missing.operations_model.empty_state?.key === "missing", "missing fixture should expose missing operations state");

    const stale = clone(status);
    stale.generated_at = "2000-01-01T00:00:00.000Z";
    const staleModels = build(window, stale);
    assert(staleModels.safety_model.readiness_warnings.includes("stale_status"), "stale fixture not detected");
    assert(staleModels.operations_model.tone === "degraded", "stale fixture should degrade Operations");

    const empty = clone(status);
    empty.trade_layer = { boundary: status.trade_layer.boundary };
    empty.capital = {
        ...status.capital,
        open_positions: [],
        closed_trades: [],
        orders: [],
        postmortems_due: [],
        live_capital_enabled: false,
        write_authority: false
    };
    empty.phase7_demo_proof = {
        phase7_proof_credit_allowed: false,
        phase5_test_trades_count_for_phase7: false,
        closed_proof_trade_count: 0,
        mature_benchmark: 100
    };
    const emptyModels = build(window, empty);
    assert(emptyModels.trades_model.empty_state?.key === "normal_no_trade", "empty fixture should keep normal no-trade state");
    assert(emptyModels.performance_model.demo_proof.display_proof_credit_allowed === false, "empty fixture must not grant proof credit");

    const degraded = clone(status);
    degraded.phase5_system_map.source_posture.canonical = {
        expected_source_count: 35,
        replayed_source_count: 31,
        missing_source_count: 4,
        status: "degraded"
    };
    degraded.source_pipeline_summary = [{ pipeline: "test", missing_credential_count: 3 }];
    degraded.watching = [{ source_key: "probe", source_name: "Probe", status: "degraded" }];
    const degradedModels = build(window, degraded);
    assert(degradedModels.sources_model.tone === "degraded", "degraded fixture should degrade Sources");
    assert(degradedModels.safety_model.missing_source_quorum_detected === true, "degraded fixture should detect missing source quorum");

    const activeProof = clone(status);
    activeProof.phase7_demo_proof = {
        ...activeProof.phase7_demo_proof,
        completed_calendar_day_count: 30,
        phase7_harness_day_count: 30,
        closed_proof_trade_count: 100,
        mature_benchmark: 100,
        phase7_proof_credit_allowed: true,
        phase5_test_trades_count_for_phase7: false
    };
    const activeProofModels = build(window, activeProof);
    assert(activeProofModels.performance_model.demo_proof.display_proof_credit_allowed === true, "active proof fixture should allow displayed proof credit only after maturity");
}

function assertNodeStateCoverage(window) {
    const stateFixture = {
        phase5_system_map: {
            status: "ok",
            boundary: "Read-only fixture map.",
            nodes: [
                { key: "online_node", label: "Online", display_status: "online", authority: "observation_only", public_safe: true },
                { key: "degraded_node", label: "Degraded", display_status: "degraded", authority: "observation_only", public_safe: true },
                { key: "blocked_node", label: "Blocked", display_status: "blocked", authority: "no_submit", public_safe: true },
                { key: "pending_node", label: "Pending", display_status: "pending", authority: "observation_only", public_safe: true },
                { key: "local_node", label: "Local", display_status: "local_only", authority: "local_only", public_safe: true },
                { key: "read_node", label: "Read", display_status: "read_only", authority: "read_only", public_safe: true },
                { key: "supplemental_node", label: "Supplemental", display_status: "supplemental", authority: "supplemental_context", public_safe: true },
                { key: "shadow_node", label: "Shadow", display_status: "shadow_only", authority: "shadow_only", public_safe: true }
            ],
            lanes: [
                {
                    key: "fixture",
                    title: "Fixture",
                    summary: "Fixture lane.",
                    tone: "online",
                    handoff: "passes state",
                    node_keys: [
                        "online_node",
                        "degraded_node",
                        "blocked_node",
                        "pending_node",
                        "local_node",
                        "read_node",
                        "supplemental_node",
                        "shadow_node"
                    ]
                }
            ]
        }
    };
    const model = build(window, stateFixture).system_connectivity_model;
    const health = new Set(model.nodes.map((node) => node.health));
    [
        "online",
        "degraded",
        "blocked",
        "pending",
        "local-only",
        "read-only",
        "supplemental",
        "shadow-only"
    ].forEach((state) => assert(health.has(state), `connectivity node state missing ${state}`));
}

function assertDishonestPayloadProbes(window) {
    const uiInferred = clone(status);
    uiInferred.phase7_demo_proof.ui_inferred_readiness_count = 1;
    assert(build(window, uiInferred).safety_model.ui_inferred_readiness_detected === true, "UI-inferred readiness probe not detected");

    const liveCapital = clone(status);
    liveCapital.capital.live_capital_enabled = true;
    liveCapital.capital.write_authority = true;
    const liveCapitalModels = build(window, liveCapital);
    assert(liveCapitalModels.safety_model.authority_unchanged === false, "hidden live capital probe did not change safety state");
    assert(liveCapitalModels.safety_model.authority_flags.includes("capital.live_capital_enabled"), "hidden live capital flag missing");
    assert(liveCapitalModels.overview_model.tone === "blocked", "hidden live capital should block Overview");

    const sourceQuorum = clone(status);
    sourceQuorum.phase5_system_map.source_posture.canonical.missing_source_count = 2;
    sourceQuorum.phase5_system_map.source_posture.canonical.replayed_source_count = 33;
    const sourceQuorumModels = build(window, sourceQuorum);
    assert(sourceQuorumModels.safety_model.missing_source_quorum_detected === true, "missing source quorum probe not detected");
    assert(sourceQuorumModels.sources_model.quorum.status === "degraded", "missing source quorum should degrade source model");

    const falseProof = clone(status);
    falseProof.phase7_demo_proof.phase7_proof_credit_allowed = true;
    falseProof.phase7_demo_proof.closed_proof_trade_count = 1;
    falseProof.phase7_demo_proof.mature_benchmark = 100;
    falseProof.phase7_demo_proof.completed_calendar_day_count = 1;
    falseProof.phase7_demo_proof.phase7_harness_day_count = 30;
    const falseProofModels = build(window, falseProof);
    assert(falseProofModels.safety_model.false_proof_credit_detected === true, "false proof credit probe not detected");
    assert(falseProofModels.performance_model.demo_proof.backend_reported_proof_credit_allowed === true, "false proof backend flag should remain visible");
    assert(falseProofModels.performance_model.demo_proof.display_proof_credit_allowed === false, "false proof credit must not become display credit");
}

function main() {
    const window = loadRendererWindow();
    const models = build(window, status);
    assertModelShape(models);
    assertPublicSafe(models);
    assertPlainOverview(models);
    assertFixtureCoverage(window);
    assertNodeStateCoverage(window);
    assertDishonestPayloadProbes(window);

    [
        "DX-3 - Dashboard View Model Layer",
        "Add pure view-model builders",
        "system_connectivity_model",
        "dishonest-payload probes"
    ].forEach((needle) => {
        assert(plan.includes(needle), `master plan missing DX-3 marker: ${needle}`);
    });

    console.log("dashboard_overhaul_view_models=ok");
    console.log(`dashboard_view_model_count=${[
        "overview_model",
        "trades_model",
        "sources_model",
        "reasoning_model",
        "performance_model",
        "operations_model",
        "governance_model"
    ].length}`);
    console.log(`dashboard_connectivity_node_count=${models.system_connectivity_model.node_count}`);
    console.log(`dashboard_connectivity_edge_count=${models.system_connectivity_model.edges.length}`);
    console.log("dashboard_system_map_shared_model=True");
    console.log("dashboard_missing_state_fixture_passed=True");
    console.log("dashboard_stale_state_fixture_passed=True");
    console.log("dashboard_empty_state_fixture_passed=True");
    console.log("dashboard_degraded_state_fixture_passed=True");
    console.log("dashboard_active_proof_fixture_passed=True");
    console.log("dashboard_dishonest_payload_probes_passed=True");
    console.log("dashboard_authority_unchanged=True");
}

main();
