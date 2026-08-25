# Qadam Simplified Operating Architecture

Qadam uses one paper-only operating contract. Its purpose is to run enough small,
independent experiments to measure whether an edge exists without allowing broker
state, duplicated automation or missing lineage to become ambiguous.

## Canonical Flow

1. A research hypothesis and its evidence are written to the SQLite control plane.
2. The Router assigns exactly one outcome and one trading lane.
3. The portfolio-risk engine approves a bounded notional or rejects the setup.
4. PaperOps writes the order and its exit plan atomically before any broker call.
5. The single execution-owner lease performs an immediate Alpaca Paper readback,
   submits at most once, refreshes the mirror and reconciles again.
6. Every fill, position, exit and closed outcome returns to the same ledger.
7. Cohorts compare outcomes with no-trade and provider-matched benchmarks when those
   observations exist. Learning can propose changes but cannot silently alter risk
   or execution authority.

## Two Trading Lanes

- **Validated:** larger bounded paper positions for strategies that have survived
  historical and forward validation.
- **Discovery:** small paper experiments for promising but unvalidated patterns.
  Optional evidence may reduce confidence or size; it does not automatically veto
  the experiment.

Both lanes require a direction, positive size and risk reference, a clear
invalidation, a tradable paper instrument, an open regular session, current broker
truth, an approved portfolio-risk amount and no reconciliation freeze.

## Risk And Exit Contract

Risk is controlled at portfolio level: per-position size, aggregate exposure,
correlated exposure, daily loss, drawdown and duplicate exposure are evaluated by
the existing portfolio-risk engine before the ledger accepts an order. The ledger
will not accept more notional than the approved amount.

Every new entry receives a stop reference, a two-to-one profit target, a maximum
holding period and a thesis invalidation before submission. The canonical exit
engine is part of the same PaperOps pass and uses the same execution-owner lease.

## Broker Truth And Liveness

An unexplained broker order, position or quantity change freezes new execution.
Only a subsequent successful reconciliation may clear that freeze. The former
auxiliary exit writer is not installed; it remains a read-only compatibility
monitor only.

Every autonomous pass records what happened to each setup. If nothing advances,
the liveness artifact states where and why each setup stopped. An idle but explained
cycle is healthy; silence or unexplained state is not.

## What This Does Not Promise

The architecture does not guarantee a daily trade, uninterrupted profit or that
the first paper gain is repeatable. It makes Qadam capable of taking controlled
discovery risk while preserving evidence, exact-once submission and broker truth.
Success must be judged by positive expectancy after costs, controlled drawdown and
enough independent outcomes to distinguish a real edge from luck.
