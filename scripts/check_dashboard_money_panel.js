#!/usr/bin/env node

const {
    assert,
    assertIncludes,
    renderWithStatus,
    status,
    statusPath
} = require("./check_dashboard_renderer.js");

const CAPITAL_REQUIRED_FIELDS = [
    "account_scope",
    "boundary",
    "broker",
    "cash_gbp",
    "closed_trade_count",
    "closed_trades",
    "connection_status",
    "current_balance_gbp",
    "drawdown_pct",
    "equity_curve",
    "equity_gbp",
    "live_capital_enabled",
    "maturity_closed_trade_count",
    "maturity_closed_trade_target",
    "max_drawdown_pct",
    "mirror_status",
    "observed_at",
    "open_order_count",
    "open_position_count",
    "open_positions",
    "order_count",
    "orders",
    "peak_equity_gbp",
    "postmortem_complete_count",
    "postmortem_due_count",
    "postmortems_complete",
    "postmortems_due",
    "realized_pnl_gbp",
    "starting_balance_gbp",
    "timeline_status",
    "unrealized_pnl_gbp",
    "write_authority"
];

const EQUITY_POINT_REQUIRED_FIELDS = ["drawdown_pct", "equity_gbp", "observed_at"];

function hasOwn(value, key) {
    return Object.prototype.hasOwnProperty.call(value, key);
}

function missingFields(value, fields) {
    return fields.filter((field) => !hasOwn(value, field));
}

async function main() {
    const capital = status.capital || {};
    const missing = missingFields(capital, CAPITAL_REQUIRED_FIELDS);
    assert(!missing.length, `capital missing fields: ${missing.join(", ")}`);

    const openPositions = Array.isArray(capital.open_positions) ? capital.open_positions : [];
    const closedTrades = Array.isArray(capital.closed_trades) ? capital.closed_trades : [];
    const orders = Array.isArray(capital.orders) ? capital.orders : [];
    const postmortemsDue = Array.isArray(capital.postmortems_due) ? capital.postmortems_due : [];
    const postmortemsComplete = Array.isArray(capital.postmortems_complete) ? capital.postmortems_complete : [];
    const equityCurve = Array.isArray(capital.equity_curve) ? capital.equity_curve : [];

    assert(capital.mirror_status === "ok", "paper mirror is not ok");
    assert(capital.account_scope === "first_release_gbp_1000_trial", "paper account scope mismatch");
    assert(
        ["local_mirror_not_broker_connected", "alpaca_paper_readonly_connected"].includes(capital.connection_status),
        "paper account connection status mismatch"
    );
    assert(capital.live_capital_enabled === false, "live capital is enabled");
    assert(capital.write_authority === false, "paper mirror has write authority");
    assert(capital.starting_balance_gbp === 1000, "starting balance is not 1000 GBP");
    if (capital.connection_status === "local_mirror_not_broker_connected") {
        assert(capital.current_balance_gbp === 1000, "current balance is not 1000 GBP");
        assert(capital.cash_gbp === capital.current_balance_gbp, "cash does not match current balance");
        assert(capital.equity_gbp === capital.current_balance_gbp, "equity does not match current balance");
        assert(capital.peak_equity_gbp === capital.current_balance_gbp, "peak equity does not match current balance");
        assert(capital.realized_pnl_gbp === 0, "realized P&L is not zero");
        assert(capital.unrealized_pnl_gbp === 0, "unrealized P&L is not zero");
        assert(capital.drawdown_pct === 0, "drawdown is not zero");
        assert(capital.max_drawdown_pct === 0, "max drawdown is not zero");
    }
    assert(capital.open_position_count === openPositions.length, "open position count mismatch");
    assert(capital.closed_trade_count === closedTrades.length, "closed trade count mismatch");
    assert(capital.order_count === orders.length, "order count mismatch");
    assert(
        capital.open_order_count === orders.filter((order) => ["new", "accepted", "partially_filled"].includes(order.status)).length,
        "open order count mismatch"
    );
    assert(capital.postmortem_due_count === postmortemsDue.length, "postmortem due count mismatch");
    assert(capital.postmortem_complete_count === postmortemsComplete.length, "postmortem complete count mismatch");
    assert(capital.maturity_closed_trade_target === 100, "maturity target is not 100");
    assert(capital.maturity_closed_trade_count === closedTrades.length, "maturity count does not match closed trades");
    assert(equityCurve.length > 0, "equity curve is missing");
    assert(/No broker connection|read-only|No broker write path/i.test(capital.boundary || ""), "capital boundary is weak");
    assert(orders.every((order) => order.execution_allowed === false && order.paper_order_allowed === false), "order authority is enabled");

    for (const point of equityCurve) {
        const pointMissing = missingFields(point, EQUITY_POINT_REQUIRED_FIELDS);
        assert(!pointMissing.length, `equity point missing fields: ${pointMissing.join(", ")}`);
    }

    const rendered = await renderWithStatus(status);
    assertIncludes(rendered, "[data-capital]", "Starting");
    assertIncludes(rendered, "[data-capital]", "Current");
    assertIncludes(rendered, "[data-capital]", "Cash");
    assertIncludes(rendered, "[data-capital]", "Equity");
    assertIncludes(rendered, "[data-capital]", "Realized");
    assertIncludes(rendered, "[data-capital]", "Unrealized");
    assertIncludes(rendered, "[data-capital]", "Drawdown");
    assertIncludes(rendered, "[data-capital]", "Closed trades");
    assertIncludes(rendered, "[data-capital]", capital.boundary.split("P&L")[0].trim());
    assertIncludes(rendered, "[data-capital]", "mirror ok");
    assertIncludes(rendered, "[data-capital]", "first release gbp 1000 trial");
    assertIncludes(rendered, "[data-capital]", String(capital.broker || "").replaceAll("_", " "));
    assertIncludes(rendered, "[data-capital]", String(capital.connection_status || "").replaceAll("_", " "));
    assertIncludes(rendered, "[data-capital]", "read only");
    assertIncludes(rendered, "[data-capital]", "paper only");
    assertIncludes(rendered, "[data-capital]", "Paper mirror state");
    assertIncludes(rendered, "[data-capital]", String(capital.timeline_status || "").replaceAll("_", " "));
    assertIncludes(rendered, "[data-capital]", "Peak equity");
    assertIncludes(rendered, "[data-capital]", "Max drawdown");
    assertIncludes(rendered, "[data-capital]", "Mirrored paper orders");
    assertIncludes(rendered, "[data-capital]", "Maturity benchmark");
    assertIncludes(rendered, "[data-capital]", "0 of 100 closed proof trades");
    assertIncludes(rendered, "[data-capital]", "No open positions");
    assertIncludes(rendered, "[data-capital]", orders.length ? "Mirrored paper order" : "No mirrored paper orders");
    assertIncludes(rendered, "[data-capital]", "No closed trades");
    assertIncludes(rendered, "[data-capital]", "Equity timeline");

    const emptyStatus = {
        ...status,
        capital: {
            ...capital,
            equity_curve: [],
            open_positions: [],
            orders: [],
            closed_trades: [],
            postmortems_due: [],
            postmortems_complete: [],
            open_position_count: 0,
            order_count: 0,
            open_order_count: 0,
            closed_trade_count: 0,
            postmortem_due_count: 0,
            postmortem_complete_count: 0,
            maturity_closed_trade_count: 0
        }
    };
    const emptyRendered = await renderWithStatus(emptyStatus);
    assertIncludes(emptyRendered, "[data-capital]", "No open positions");
    assertIncludes(emptyRendered, "[data-capital]", "No mirrored paper orders");
    assertIncludes(emptyRendered, "[data-capital]", "No closed trades");
    assertIncludes(emptyRendered, "[data-capital]", "No equity snapshots");

    console.log("Dashboard money panel contract OK");
    console.log(`Rendered snapshot: ${statusPath}`);
    console.log(`Current balance GBP: ${capital.current_balance_gbp}`);
    console.log(`Open positions: ${openPositions.length}`);
    console.log(`Closed trades: ${closedTrades.length}`);
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});
