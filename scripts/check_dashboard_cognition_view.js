#!/usr/bin/env node

const {
    assert,
    assertIncludes,
    renderWithStatus,
    status,
    statusPath
} = require("./check_dashboard_renderer.js");

const REQUIRED_SHADOW_PACKET_FIELDS = [
    "agent_key",
    "boundary",
    "created_at",
    "packet_id",
    "source_event_refs",
    "status",
    "summary",
    "uncertainty"
];

const REQUIRED_LOCAL_RESEARCH_FIELDS = [
    "anomalies",
    "assessment_id",
    "confidence",
    "created_at",
    "escalation_recommendation",
    "execution_allowed",
    "missing_correlations",
    "mode",
    "model",
    "next_questions",
    "paper_order_allowed",
    "provider",
    "status",
    "summary",
    "watch_focus"
];

const REQUIRED_HYPOTHESIS_FIELDS = [
    "blocked_reason",
    "confidence",
    "created_at",
    "evidence_packet_id",
    "evidence_source_count",
    "execution_allowed",
    "generated_by",
    "instrument_focus",
    "invalidation",
    "missing_correlations",
    "signal_id",
    "status",
    "thesis",
    "title"
];

const REQUIRED_EVIDENCE_PACKET_FIELDS = [
    "average_trust_score",
    "created_at",
    "items",
    "min_trust_score",
    "missing_correlations",
    "signal_id",
    "source_count",
    "sources",
    "trail_id"
];

const REQUIRED_PAPER_CONTEXT_FIELDS = [
    "account_scope",
    "boundary",
    "broker",
    "capital_policy",
    "closed_trade_count",
    "connection_status",
    "current_balance_gbp",
    "drawdown_pct",
    "execution_allowed",
    "live_capital_enabled",
    "maturity_closed_trade_count",
    "maturity_closed_trade_target",
    "mode",
    "open_order_count",
    "open_position_count",
    "order_count",
    "paper_order_allowed",
    "realized_pnl_gbp",
    "status",
    "timeline_status",
    "trial_allocation_gbp",
    "unrealized_pnl_gbp",
    "write_authority"
];

const REQUIRED_MODEL_ROLES = new Set(["Research Analyst", "Strategy Lead", "Head of Quant"]);

function hasOwn(value, key) {
    return Object.prototype.hasOwnProperty.call(value, key);
}

function missingFields(value, fields) {
    return fields.filter((field) => !hasOwn(value, field));
}

async function main() {
    const cognition = status.cognition || {};
    const shadowPackets = Array.isArray(cognition.shadow_packets) ? cognition.shadow_packets : [];
    const localResearch = Array.isArray(cognition.local_research_assessments)
        ? cognition.local_research_assessments
        : [];
    const hypotheses = Array.isArray(cognition.hypotheses) ? cognition.hypotheses : [];
    const evidencePackets = Array.isArray(cognition.evidence_packets) ? cognition.evidence_packets : [];
    const modelActivity = Array.isArray(cognition.model_activity) ? cognition.model_activity : [];
    const timeline = Array.isArray(cognition.analysis_timeline) ? cognition.analysis_timeline : [];
    const blockedReasons = Array.isArray(cognition.blocked_reasons) ? cognition.blocked_reasons : [];
    const paperContext = cognition.paper_account_context || {};

    assert(cognition.status, "cognition status is missing");
    assert(Array.isArray(cognition.current_focus) && cognition.current_focus.length, "current focus is missing");
    assert(shadowPackets.length > 0, "shadow packets are missing");
    assert(localResearch.length > 0, "local Research Analyst assessments are missing");
    assert(hypotheses.length > 0, "hypotheses are missing");
    assert(evidencePackets.length > 0, "evidence packets are missing");
    assert(modelActivity.length >= REQUIRED_MODEL_ROLES.size, "model activity is incomplete");
    assert(timeline.includes("trade layer not reached"), "analysis timeline does not show the trade boundary");
    assert(timeline.includes("paper account mirror context"), "analysis timeline does not include paper account context");
    assert(
        blockedReasons.includes("shadow_only_no_signal_integrity_gate"),
        "blocked reasons do not include signal integrity gate"
    );
    assert(
        blockedReasons.includes("paper_account_context_read_only"),
        "blocked reasons do not include paper account read-only context"
    );
    assert(
        /shadow-only until Signal Integrity Gate and Risk Agent exist/i.test(cognition.boundary || ""),
        "cognition boundary is weak or missing"
    );

    const modelRoles = new Set(modelActivity.map((model) => model.role));
    for (const role of REQUIRED_MODEL_ROLES) {
        assert(modelRoles.has(role), `model role missing: ${role}`);
    }
    for (const model of modelActivity) {
        assert(model.authority === "non_executable", `${model.role} has executable authority`);
        assert(model.current_task, `${model.role} missing current task`);
    }

    const missingPaperContext = missingFields(paperContext, REQUIRED_PAPER_CONTEXT_FIELDS);
    assert(!missingPaperContext.length, `paper account context missing fields: ${missingPaperContext.join(", ")}`);
    assert(paperContext.execution_allowed === false, "paper account context allows execution");
    assert(paperContext.paper_order_allowed === false, "paper account context allows paper orders");
    assert(paperContext.write_authority === false, "paper account context exposes write authority");
    assert(paperContext.live_capital_enabled === false, "paper account context enables live capital");
    assert(/read-only/i.test(paperContext.boundary || ""), "paper account context boundary is weak");

    for (const packet of shadowPackets) {
        const missing = missingFields(packet, REQUIRED_SHADOW_PACKET_FIELDS);
        assert(!missing.length, `${packet.packet_id || "shadow packet"} missing fields: ${missing.join(", ")}`);
        assert(
            /No signal, risk decision, or execution authority/i.test(packet.boundary || ""),
            `${packet.packet_id} has weak shadow boundary`
        );
    }

    for (const assessment of localResearch) {
        const missing = missingFields(assessment, REQUIRED_LOCAL_RESEARCH_FIELDS);
        assert(!missing.length, `${assessment.assessment_id || "local assessment"} missing fields: ${missing.join(", ")}`);
        assert(assessment.execution_allowed === false, `${assessment.assessment_id} allows execution`);
        assert(assessment.paper_order_allowed === false, `${assessment.assessment_id} allows paper order`);
        assert(Array.isArray(assessment.next_questions), `${assessment.assessment_id} next questions are not structured`);
    }

    const evidenceBySignal = new Map(evidencePackets.map((packet) => [packet.signal_id, packet]));
    for (const packet of evidencePackets) {
        const missing = missingFields(packet, REQUIRED_EVIDENCE_PACKET_FIELDS);
        assert(!missing.length, `${packet.trail_id || "evidence packet"} missing fields: ${missing.join(", ")}`);
        assert(Array.isArray(packet.items) && packet.items.length, `${packet.trail_id} has no evidence items`);
        for (const item of packet.items) {
            assert(!hasOwn(item, "raw_ref"), `${packet.trail_id} leaked a raw evidence reference`);
            assert(item.source && item.summary && item.event_type, `${packet.trail_id} has an incomplete evidence item`);
        }
    }

    for (const hypothesis of hypotheses) {
        const missing = missingFields(hypothesis, REQUIRED_HYPOTHESIS_FIELDS);
        assert(!missing.length, `${hypothesis.signal_id || "hypothesis"} missing fields: ${missing.join(", ")}`);
        assert(hypothesis.execution_allowed === false, `${hypothesis.signal_id} allows execution`);
        assert(
            hypothesis.blocked_reason === "shadow_only_no_signal_integrity_gate",
            `${hypothesis.signal_id} has an unexpected block reason`
        );
        assert(
            evidenceBySignal.has(hypothesis.signal_id),
            `${hypothesis.signal_id} has no linked evidence packet`
        );
    }

    const rendered = await renderWithStatus(status);
    assertIncludes(rendered, "[data-cognition]", "Cognition state");
    assertIncludes(rendered, "[data-cognition]", "Paper account context");
    assertIncludes(rendered, "[data-cognition]", "Broker mirror");
    assertIncludes(rendered, "[data-cognition]", "no paper order authority");
    assertIncludes(rendered, "[data-cognition]", "read only");
    assertIncludes(rendered, "[data-cognition]", "shadow ready");
    assertIncludes(rendered, "[data-cognition]", "Hypothesis, not trade");
    assertIncludes(rendered, "[data-cognition]", "Execution blocked");
    assertIncludes(rendered, "[data-cognition]", "Trade layer not reached");
    assertIncludes(rendered, "[data-cognition]", "Research Analyst");
    assertIncludes(rendered, "[data-cognition]", "Strategy Lead");
    assertIncludes(rendered, "[data-cognition]", "Head of Quant");
    assertIncludes(rendered, "[data-cognition]", "non executable");
    assertIncludes(rendered, "[data-cognition]", "Shadow packets");
    assertIncludes(rendered, "[data-cognition]", "Local Research Analyst");
    assertIncludes(rendered, "[data-cognition]", "Hypotheses and evidence");
    assertIncludes(rendered, "[data-cognition]", "Evidence packet index");
    assertIncludes(rendered, "[data-cognition]", "Missing corroboration");
    assertIncludes(rendered, "[data-cognition]", "research shadow triage packet");
    assertIncludes(rendered, "[data-cognition]", "trade layer not reached");
    assertIncludes(rendered, "[data-cognition]", "Cognition is shadow-only until Signal Integrity Gate and Risk Agent exist.");

    const emptyStatus = {
        ...status,
        cognition: {
            status: "shadow_ready",
            current_focus: [],
            shadow_packets: [],
            local_research_assessments: [],
            hypotheses: [],
            evidence_packets: [],
            model_activity: [],
            paper_account_context: {},
            analysis_timeline: [],
            blocked_reasons: [],
            boundary: "Cognition is shadow-only until Signal Integrity Gate and Risk Agent exist."
        }
    };
    const emptyRendered = await renderWithStatus(emptyStatus);
    assertIncludes(emptyRendered, "[data-cognition]", "No active focus");
    assertIncludes(emptyRendered, "[data-cognition]", "No model activity yet");
    assertIncludes(emptyRendered, "[data-cognition]", "No shadow packets");
    assertIncludes(emptyRendered, "[data-cognition]", "No local assessment yet");
    assertIncludes(emptyRendered, "[data-cognition]", "No hypotheses yet");
    assertIncludes(emptyRendered, "[data-cognition]", "No evidence packets");
    assertIncludes(emptyRendered, "[data-cognition]", "Paper account context");
    assertIncludes(emptyRendered, "[data-cognition]", "trade layer not reached");

    console.log("Dashboard cognition view contract OK");
    console.log(`Rendered snapshot: ${statusPath}`);
    console.log(`Hypotheses: ${hypotheses.length}`);
    console.log(`Evidence packets: ${evidencePackets.length}`);
    console.log(`Shadow packets: ${shadowPackets.length}`);
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
