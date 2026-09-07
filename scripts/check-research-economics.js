#!/usr/bin/env node
"use strict";
const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const path = require("node:path");
const source = fs.readFileSync(path.join(__dirname, "..", "dashboard.js"), "utf8");
const start = source.indexOf("function renderQsaseResearchEconomics(");
const end = source.indexOf("function renderQsaseSidebar(", start);
assert(start > 0 && end > start);
const context = {
    asArray: (value) => Array.isArray(value) ? value : [],
    qsaseHtmlText: (value) => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;"),
    modelNumber: (value, fallback) => typeof value === "number" && Number.isFinite(value) ? value : fallback,
    formatTime: (value) => value
};
vm.createContext(context);
vm.runInContext(source.slice(start, end), context);
const empty = context.renderQsaseResearchEconomics();
assert(empty.includes("Not reconciled"));
assert(empty.includes("not cash income"));
assert(!empty.includes("US$0.00"));
const measured = context.renderQsaseResearchEconomics({research_economics: {
    subscription_expense_usd: 0, model_expense_usd: 12.5,
    cost_state: "partial_receipts_not_total_operating_cost", input_window_complete: false,
    components: [{component_id: "source:<script>", associated_event_count: 2,
        ablations: [{scope: "source_dependent_setup_vs_abstention", independent_event_count: 1, mean_modelled_return_delta: -.05}]}]
}, strategy_reviews: [{strategy_family_id: "<img onerror=alert(1)>", mean_net_return: -.1}]});
assert(measured.includes("US$0.00") && measured.includes("US$12.50"));
assert(measured.includes("-5.00%") && measured.includes("-10.00%"));
assert(measured.includes("The input window is incomplete"));
assert(measured.includes("Component value remains unproven"));
assert(!measured.includes("<script>") && !measured.includes("<img"));
console.log("research_economics_render=passed unknown_zero_negative_escaping_scope");
