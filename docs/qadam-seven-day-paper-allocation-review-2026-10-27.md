# Seven-Day Paper Allocation Review

Review date: 27 October 2026, Asia/Dubai. The initial inspection was read-only.
The implementation below follows the user's explicit higher-exposure paper
request and subsequent 60% start-equity drawdown approval. Activation and
production verification are recorded separately; code presence is not deployment.

## Observed Account State

The broker mirror at 17:54 Dubai reported equity of USD 100,593.64, cash of
USD 100,289.51 and two remaining positions. The portfolio risk projection
identified the positions as USO and XLE, with approximately USD 304 invested.

Qadam had already sold six SMH and six SOXX shares that afternoon under its
take-profit rules. Their combined fill-to-fill gain was USD 273.02 before
separately charged fees. The current 0.3% invested fraction therefore does not
describe exposure throughout the day. These were overlapping semiconductor
positions, not two independent demonstrations of a general trading edge.

Sources: `data/runtime/alpaca_paper_mirror.json`, `paper_orders.jsonl`,
`qadam_canonical_exit_engine_history.jsonl`, `qadam_portfolio_risk_state.json`.

## Existing Research Evidence

- The current core-strategy projection had no eligible hypothesis in any of its
  five families. Current triggers did not resolve a tradable direction.
- The 27 October historical run tested 360 hypotheses. Eleven had raw
  significance, but none survived the complete validation process. Its edge
  registry contained zero validated edges.
- The latest forward tournament was dated 26 October, not the current session.
  It contained 79 registered versions, no review-eligible version and at most
  three independent matched outcomes per version. Some returns were positive,
  others negative. Pooling overlapping observations or selecting the best
  version after seeing outcomes would overstate the evidence.
- The current qualitative test summary recorded 24 tested relationships and
  zero qualified candidates. Refreshing a research score is not a new event.

Sources: `qadam_core_strategy_status.json`, `qadam_backtest_results_summary.json`,
`qadam_edge_registry_summary.json`, `qadam_forward_strategy_tournament.json`,
`qadam_qualitative_backtest_summary.json` in `data/runtime/`.

## Binding Design Choices

The portfolio policy permits at most 40% gross exposure, USD 5,000 per position,
5% per instrument, three concurrent discovery positions and one discovery
position per correlated cluster. Unestimated discovery is separately capped at
USD 250 notional and USD 5 planned loss. These are ceilings, not investment
targets. Current inactivity occurs before sizing: no setup is available.

The event-direction fallback requires an absolute price move of at least 0.25%
and a volume ratio of at least 0.35. The adapter computes this ratio from the
latest daily bar versus its rolling daily-volume average. For a partial current
bar, early-session accumulation is compared with mostly complete prior days.
At the inspected 17:51 cut, SMH's move was +1.4911% with volume ratio 0.101;
SOXX's move was +2.0359% with volume ratio 0.1233. Both failed this volume rule.

The threshold is explicitly tested in `test_qadam_strategy_translation.py` and
frozen into entry definitions by `orchestrator/research/foundry.py`. It is not
an accidental missing-data veto. A time-aligned replacement requires a new
version, measured intraday evidence and prospective comparison; do not quietly
lower it and attach the incumbent's historical outcomes to the changed rules.

## Requirements Before Activating A Higher-Exposure Trial

1. Resolve the user's maximum acceptable paper drawdown before choosing the
   allocation and loss envelopes. A drawdown freeze cannot guarantee a loss cap.
2. Limit the trial to the paper account for seven calendar days from activation.
   Record its opening equity, exact UTC start and expiry, and approved limits.
3. Use higher permitted exposure, never mandatory investment or trade quotas.
   A researched idea must still resolve direction, freshness, liquidity and exit.
4. Retain one execution owner, broker reconciliation, duplicate prevention,
   correlation controls, explicit exits and real-money disablement.
5. Keep unvalidated strategies labelled unvalidated. Version all changed sizing
   and signal rules; do not rewrite past outcomes or select winners retrospectively.
6. Compare the aggressive profile prospectively with the incumbent sizing and
   matched market benchmark. Neither comparison may submit duplicate broker orders.
7. Automatically revert new-entry sizing at expiry or breach. Existing positions
   remain managed under recorded exits; do not mass-liquidate merely on expiry.
8. Test sizing, outstanding-order reservations, loss freezes, expiry, restart,
   correlation limits and all downstream execution ceilings before deployment.

## Approved Temporary Sizing Envelope

The user explicitly selected a 60% drawdown from starting paper equity to stop
new entries. This is an extreme paper experiment tolerance, not a recommended
real-money loss budget, target loss or guaranteed stop. The existing stricter
2% daily loss opening freeze and explicit position exits remain in place.

- Seven calendar days, account-fingerprint and paper-epoch bound, with fixed
  start equity and expiry. No renewal on restart and no live-capital authority.
- Up to 75% gross exposure, at least 25% cash, USD 5,000 per position and 5%
  per instrument, 20% per correlated cluster and 16 discovery slots (four per
  cluster). Capacity is permission, not an investment or trade quota.
- Unestimated discovery can use up to USD 5,000 notional and USD 125 planned
  loss at invalidation. It remains unestimated and unvalidated. The absolute
  0.5% equity planned-risk ceiling, adverse-evidence vetoes, executable liquidity,
  direction, evidence freshness and durable exits are retained.
- Approval identifiers enter strategy definitions, risk decisions and handoffs.
  A sizing version change cannot bypass same-economic-signal deduplication.
- Held positions and queued entry orders consume the same transactional budget.
  Both preparation and the final submission transition recheck authority,
  expiry, cash, cluster, position-count and daily-loss constraints.
- A 60% start-equity breach is recorded durably and freezes further entries
  even if equity recovers. Expiry returns new sizing to baseline; neither event
  invents a mass liquidation or disables existing position care.
- Each trial proposal records an incumbent-sizing comparison using the same
  current portfolio and entry evidence. This is a sizing counterfactual, not a
  separately traded portfolio or unbiased full-path performance comparison.
  Existing benchmark/outcome learning remains prospective; no past result is
  relabelled as evidence for the new sizing rules.

No new scheduler or execution owner is installed. Provider spending limits,
paper-only safeguards and the trades-and-patterns notification preference are
unchanged. No claim is made that all available capital should be deployed, that
an eligible setup exists immediately or that higher exposure increases expectancy.

## Deployment Evidence

- Implementation commits: `e5c01abc` and `3d7cd9a0`, pushed to the existing
  `codex/weekend-engine-preservation-20260719` branch. No frontend redesign.
- Final isolated regression: 2,228 passed. The 200 Qiskit deprecation warnings
  predate this trial. Changed-code Ruff and `git diff --check` passed.
- Approved interval: 27 October 2026 14:55 UTC through 3 November 2026 14:55 UTC
  (18:55 Dubai on both dates). Starting equity USD 100,590.93 was read from the
  matching account at 14:49:43 UTC. The 60% start-equity entry-freeze threshold
  is USD 40,236.372; the stricter daily-loss constraint remains independent.
- Trial ID: `paper-allocation-20261027`. The account-bound approval digest is
  `704c55458192287c36cec27bb878841c69eae8294c63de7d90693a47756212bf`.
- The execution policy was explicitly reinstalled under maintenance after the
  reviewed code/config changes. Its digest must match the running code; a Git
  push alone does not grant order authority.
- At 15:06:35 UTC the real portfolio policy contained the active trial and the
  75%/16-slot/four-per-cluster/USD 5,000 envelope. At 15:08 UTC the effective
  experimental policy validated with no errors and USD 5,000/USD 125 unknown
  expectancy bounds. The frozen admission file remains the base approval;
  compilers apply the expiring overlay when they consume it. Tests cover both
  activation and reversion without rewriting that file.
- The contemporaneous Router state was `no-setup`, with zero accepted handoffs.
  Higher limits did not manufacture an order. Evidence freshness, direction
  and same-economic-signal checks still determine whether an entry exists.

Current liveness must be checked against fresh runtime receipts, not inferred
from this static implementation record. Final deployment acceptance uses the
reviewed database execution-policy digest, guarded operator lease,
`qadam_position_care_status.json`, `paperops_autonomous_pass_summary.json`,
`qadam_operator_circuit_breakers.json`, `qadam_operator_repair_queue.json` and
the signed public-status bridge. A deployment hold is not a completed recovery.
No seven-day performance result or future market session is certified here.
