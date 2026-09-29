#!/usr/bin/env node
const { assert, renderWithStatus, status } = require("./check_dashboard_renderer.js");

async function main() {
    const { context } = await renderWithStatus(status);
    const position = { instrument: "NVDA", direction: "short", quantity: 13, current_value_gbp: -2970.89, unrealized_pnl_gbp: 18.68 };
    const portfolio = {
        current_value_gbp: 100131.17, cash_gbp: 103101.93, starting_balance_gbp: 100000,
        display_currency: "USD", positions: [position],
        equity_curve: [
            { timestamp: "2026-09-28T16:18:00Z", portfolio_value: 100086 },
            { timestamp: "2026-09-28T19:45:00Z", portfolio_value: 100131.17 }
        ],
        cash_position_reconciliation: { status: "within_mark_tolerance", unreconciled_difference: 0.13 }
    };
    const qsase = { dashboard_portfolio: portfolio };
    const model = context.qsasePortfolioAnalyticsModel(qsase);
    assert(Math.abs(model.cashPercent - 102.966868) < 0.00001, "cash must use net equity denominator");
    assert(Math.abs(model.netExposurePercent + 2.966998) < 0.00001, "short must carry a negative weight");
    assert(model.requiresSignedAllocation, "short portfolio cannot be an ordinary pie");
    assert(model.largestPercent === model.grossExposurePercent, "largest/gross must use the same denominator");
    const holdings = context.renderQsasePortfolioAnalytics(qsase, model);
    assert(holdings.includes("data-signed-exposure"), "signed exposure presentation absent");
    assert(holdings.includes("NVDA (short)"), "short direction absent");
    assert(!holdings.includes("qsase-allocation-donut"), "short cannot be presented as positive invested allocation");
    assert(holdings.includes("0.13"), "mark discrepancy must remain visible");
    const chart = context.renderQsasePortfolioValue(qsase, model);
    assert(chart.includes("since paper-account start"), "total-return period must be explicit");
    assert(chart.includes("Chart window:"), "chart period must be explicit");
    const ticks = [...chart.matchAll(/class="chart-axis-label" x="4" y="([\d.]+)"/g)].map((match) => Number(match[1]));
    assert(ticks.length === 3 && Math.abs(ticks[1] - ticks[0]) >= 50 && Math.abs(ticks[2] - ticks[1]) >= 50, "vertical labels must not overlap");
    for (const [cash, value, direction, signed] of [[97000, 3000, "long", false], [-50000, 150000, "long", true], [103000, -3000, "short", true]]) {
        const result = context.qsasePortfolioAnalyticsModel({ dashboard_portfolio: {
            current_value_gbp: 100000, cash_gbp: cash,
            positions: [{ instrument: "SPY", direction, market_value: value }]
        } });
        assert(result.requiresSignedAllocation === signed, "long/short/borrowed-cash classification wrong");
        assert(result.cashPercent === cash / 1000, "cash cannot be clamped or renormalized");
    }
    const empty = context.qsasePortfolioAnalyticsModel({ dashboard_portfolio: { current_value_gbp: 100000, cash_gbp: 100000, positions: [] } });
    assert(empty.cashPercent === 100 && empty.grossExposurePercent === 0, "all-cash regression");
    console.log("Portfolio accounting renderer checks passed: signed exposure, borrowing, cash, reconciliation, chart periods and separated ticks.");
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
