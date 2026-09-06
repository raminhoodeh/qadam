# Autonomous Paper Fund: Implementation And Verification

Date: 6 September 2026. Scope: paper-only operational repair and bounded research
learning. This document records engineering evidence, not a claim of a profitable
fund, a completed live soak, or failure-free unattended operation.

## Release Contents

| Plan | Implementation in this release | Verification / remaining evidence |
|---|---|---|
| P0 | Isolated baseline checkout, SQLite backup through the backup API, integrity and foreign-key checks, real broker read | Baseline: 961 passing tests, 39 pre-existing failures. Production database was not replaced. |
| P1 | Cause-specific mirror recovery, two distinct fresh observations, preservation of unrelated freezes, typed database/maintenance failures, canonical health in team and dashboard | Timeout, stale-read, manual-hold and incident recovery tests. Production recovery must be verified after installation. |
| P2 | Account/epoch FIFO entry allocation, exact decision linkage, corrected position-to-original-exit association, idempotent cumulative-fill projection | Real-history replay twice: 68 filled orders / 68 cumulative fill projections; five original position exit plans reconciled. Unresolved history stays unknown. |
| P3 | Stable strategy versions, event-level cohorts, unknown-cost exclusion, immutable corrections and registered forward evaluations | 31 historical outcomes: 30 gross reconstructions, five exact decision attributions, 26 unresolved attributions, zero measured-cost outcomes. These are not net strategy profit. |
| P4 | Reuse the existing capability registry, numeric/qualitative trigger producers, typed evidence packets and proxy contracts; bind hypotheses to stable definitions | No new provider entitlement is claimed. Existing real-packet checks must be run against the release; unavailable history and unsupported proxies remain research-only. |
| P5 | Explicit unknown-expectancy discovery contract across foundry, Akber, layered judgment, risk and Router; remove discounted winner-selected return from discovery-micro | Full typed positive/negative path tests. Maximum $250 notional / $5 planned loss at the stop. Known-negative economics cannot use this route. Untouched forward comparison remains pending. |
| P6 | Budget-neutral three-versus-six-slot comparison in risk output; preserve current slot, aggregate, cluster and $5,000 absolute limits | Six slots are not activated by this release. Prospective supply, turnover and risk comparison must precede that amendment. |
| P7 | Original durable exits, provider exchange calendar, terminal partial-exit retry identities, unresolved-order no-retry protection, quantity-bounded close requests | Cancel/partial/ambiguous/repeated-submission tests. Price protection continues without inventing a holiday/session. Broker-hosted stop protection is not claimed. |
| P8 | Learner-owned real tournament, non-overlapping version-matched shadow outcomes, matched SPY/cost comparison, scheduled multiplicity-adjusted review, exact-version foundry consumer | Historical backtest refresh can no longer erase the tournament. No historical survivor is required for emerging forward review. Twenty independent outcomes are not fabricated. |
| P9 | Explicit SQLite connection closing, bounded connection retries only, unleased-generation collection between deep maintenance, one-minute external watchdog, canonical health | No retry of an ambiguous broker write. No automatic code rewrite, disk deletion, risk expansion or arbitrary unfreeze. Real repair latency must still be measured. |
| P10 | Existing dashboard layout retained; canonical execution health and outcome eligibility exposed; guide and whitepaper updated | Telegram team health consumes the same canonical health. Production route, digest and delivery checks are release acceptance, not assumed results. |
| P11 | Exact-commit promotion, maintained paper policy amendment, guarded restart, exact-build exchange-calendar soak, automatic prospective economic report inside the existing active-trial owner | Five distinct real market sessions then 20 observed evaluation sessions remain prospective milestones. No retrospective session credit. |

## Canonical Evidence/Gate Register

This is the index of existing producers and consumers, not another execution
authority. Runtime decisions retain their typed evidence and primary stop reason.

| Field / condition | Producer | Consumer / missing treatment |
|---|---|---|
| Account, positions, orders, fills | `paper_account.py` read-only broker mirror and `qadam_operating_ledger.py` reconciliation | Canonical PaperOps; missing or disagreement freezes execution, never a size haircut |
| Direction and executable proxy | trigger factory, qualitative/power mechanisms, strategy foundry | Akber and Router; unsupported direction or mapping remains research-only |
| Fresh quote, spread and liquidity | market-data evidence and tradeability envelope | Akber / risk / Router; stale or unavailable execution data requires refresh |
| Invalidation, stop, target, horizon | frozen hypothesis plus fresh numeric market geometry | Canonical exit prewrite; no entry without a durable exit plan |
| Unknown expected return | foundry explicitly emits `None`, never zero or an invented positive estimate | Only typed discovery-micro may proceed, with the amended $250/$5 bounds and a size reduction |
| Known non-positive expected return | matched historical or forward evidence | Cannot be relabelled unknown to obtain discovery authority |
| Optional corroboration | source capability registry and evidence profiles | Reduced confidence/size or deferred entry; no fabricated provider field |
| Version, event and decision-time snapshot | stable strategy definition, canonical decision, frozen forward shadow | Learning and promotion; absent lineage is ineligible for proof |
| Aggregate/cluster risk and affordable minimum lot | portfolio risk engine and broker reconciliation | Hard existing budget; rounding cannot raise the approved budget |
| Real market session | Alpaca clock and cached provider calendar | Entry/exit session checks; no weekday-only holiday credit |
| Matured outcome, matched benchmark and costs | registered forward tournament / outcome accounting | Emerging review after scheduled independent checkpoints; not required before the first bounded unknown-return experiment |

## Verification Record

The final clean-checkout suite reports 1,013 passed and 39 failed.
The same 39 tests fail on the unchanged baseline; most use absent untracked
runtime/site fixtures. No new failing test was introduced in the comparison.
The failed-test identities were compared against the baseline XML and are
identical. This is not a claim that the repository-wide suite is green. All changed Python
files pass Ruff. Additional release-only checks and deployment receipts must be
reported separately from unit tests.

The foundry now registers each valid immutable strategy definition before
publishing its draft. Registration uses the actual write time, not a backdated
research timestamp, and rejects a mismatched definition hash. Invalid foundry
generations cannot replace the last valid drafts. Registration is research
metadata only and grants no broker or portfolio authority.

Live recovery on 6 September passed three guarded PaperOps revalidations and
separate portfolio-review, lifecycle-poll and dashboard revalidations. At
07:52:55 UTC, the operator reported 21/21 fresh services, zero open circuits and
zero repair requests. Canonical broker reconciliation removed the recoverable
mirror freeze without clearing an unrelated hold or submitting an order. A
further exact-build verification is required after the preregistration patch.

Real read-only Alpaca verification on 6 September returned five positions, no
open orders, 31 closed-trade records and USD 100,123.80 equity. Those are a dated
snapshot, not permanent operating figures. The provider clock reported the next
regular session as 8 September 2026 at 09:30 America/New_York. No Sunday trade is
required or manufactured for acceptance.

## Limits And Next Evidence

- Cumulative order fill snapshots are labelled as aggregates, not individual
  exchange executions. Incomplete history, corporate-action ambiguity and missing
  costs must remain excluded from net-performance attribution.
- Gross reconstructed closed-order P&L is not interchangeable with broker account
  return. Legacy starting balances, residual positions and unresolved attribution
  must not be filled in with zero-valued estimates.
- The old bounded-experimental tier still labels its rejected historical result
  as provisional. It is not promoted to validated status by this amendment.
- Existing source access is not proof of a useful numeric trigger. Programme
  supply, unchanged-event suppression and untouched performance require continued
  real-packet and forward checks.
- The six-slot allocation challenger, threshold superiority, regime robustness,
  five-session operational soak and 20-session economics review remain pending.
- Stops describe planned risk, not guaranteed maximum loss. The laptop and network
  must remain available for synthetic exits. Paper fills do not establish live
  market impact, queue priority or real-money profitability.
- Self-healing may retry known, bounded recoverable failures and then escalate.
  It cannot promise to repair arbitrary defects, provider outages or hardware
  failure without intervention. A manual/risk hold remains authoritative.

Primary broker references: [Alpaca paper trading](https://docs.alpaca.markets/us/docs/paper-trading),
[order lifecycle](https://docs.alpaca.markets/us/docs/orders-at-alpaca),
[exchange calendar](https://docs.alpaca.markets/us/reference/legacycalendar).

## Final Integration Repairs

Real Gemma verification identified a provider grammar failure: nested string
length limits exceeded llama.cpp grammar expansion limits. The transport schema
now omits string repetition bounds while the canonical output schema and critic
still enforce them. The local task uses a compact 900-token output budget,
180-second request timeout and disabled optional reasoning. On 6 September at
08:54:42 UTC, an actual research packet returned `live_local_llm`,
`raw_response_status=ok`, with one packet processed. Endpoint availability alone
is not considered successful analysis.

Local inference and configured-model reloads now share a nonblocking process
lock. A failed live inference can trigger only a localhost, configured-model
reload, with a persisted 15-minute cooldown. Active requests cannot be interrupted
by another Qadam reload; remote endpoints cannot trigger local model operations.

The 20-session report is embedded in the existing active-trial status and public
summary. It freezes the policy/account/epoch binding and start-state baseline,
waits for the corrected five-session soak, then samples actual provider sessions.
Repeated polls, closed dates and holidays cannot create session credit. Software
changes alone do not reset this economic record; policy/account changes require
a separate evaluation. Reports include distinct canonical opportunities,
independent completed experiments, deployed capital, filled turnover, sampled
account return and drawdown, and measured net/benchmark outcomes where available.
Missing cost, cash-flow and human-intervention measurements remain explicitly
unknown. Completion creates a review, never capital expansion or proof credit.

The final runtime handover also exposed a duplicate full-database integrity scan
in the PaperOps summary/publication path. The wrapper now builds and publishes one
checked snapshot instead of immediately rebuilding it. The integrity scan itself,
freeze handling and pre/post broker reconciliation are retained; no cached report
is used to authorise an order. Both healthy and frozen-state publication are tested.

A deployment can also supersede an in-flight critic request. The singleton
correctly refuses a different build's request; the critic now ends that obsolete
wait explicitly instead of waiting up to two hours for an impossible receipt.
It reports `replan_required`, not success. The existing watchdog can then wake a
fresh critic; neither a newer request nor an execution hold is overwritten.
