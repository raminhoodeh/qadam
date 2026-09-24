# Discovery-to-Paper Handoff Repair

## Scope

Preserve Qadam's existing validated and discovery-micro paper lanes, core
strategy definitions, independent execution owner, portfolio limits, exits,
Q-CTRL and broker reconciliation. No live-capital authority, larger position
limits, forced orders or fabricated evidence are introduced.

All catalogue sources must have an explicit research disposition. Mapping a
source to an instrument is not discovering a predictive relationship. Sources
without access, empty captures, aliases and operational connections cannot be
counted as independent usable evidence. Unknown publication times remain
unknown; current context cannot silently become point-in-time historical data.

## Defects Repaired

1. Technical and order-flow sections overwrote complete price snapshots with
   null fields. SMH, NVDA and other instruments could therefore lose price,
   volatility and volume inputs even though the current market packet had them.
   Supplemental fields now remain separate. A complete provider-backed price
   snapshot is selected by observation time, independent of packet order.
   Its own missing fields remain missing rather than borrowing older values.
   Current price is preferred to the last close; provider quote/trade timestamps
   are preserved rather than replaced by projection time.
2. The cockpit's currently qualified symbol could narrow a family's instrument
   metadata, while watchlist entries missed market fields. Declared instruments
   and families are now retained independently of the cockpit selection, and
   all entries receive the same selected market snapshots. Declared paper-route
   metadata cannot authorize an order or enable futures/prediction contracts.
3. Foundry's discovery-micro admission vetoed missing volume despite the frozen
   policy explicitly making it optional. It now uses the same policy-aware
   missing-evidence adapter as graph discovery. Missing required price,
   volatility, direction, trusted support or an execution mapping still blocks.
4. Graph discovery truncated the research-score ranking before evaluating
   actionability, so a viable lower-ranked candidate could be omitted. All
   current score rows are now evaluated before the shortlist is selected. The
   default bounded limit covers the current core and strategy-agnostic universe;
   any deferred count is explicit. Claimed scope uses actual catalogue and
   instrument counts instead of hard-coded 41/19/779 constants.

## Inspectable Coverage

`qadam_pattern_score_v3.json` contains `discovery_source_coverage`, with each
source's collection state, observed record count, mapped instruments, scored
input count, freshness, aliases and next action. Collected research sources
that do not reach scoring are explicitly identified. This audit does not grant
source-quorum credit or modify scores, thresholds or execution authority.

`qadam_graph_pattern_candidates.json` distinguishes considered, selected and
deferred research candidates. Its actionability ranking is not an order.

## Verification

Regression tests cover price preservation across supplemental sections and
packet order, stable declared-universe membership, coherent snapshot selection, missing-field behavior, optional
volume policy, required evidence rejection, coverage gaps, negative-control
exclusion and shortlist starvation.

The maintained release path is a guarded non-submitting integration check from
source ingestion through scoring, strategy research, graph discovery, canonical
tradeability, forward shadow and portfolio routing; then restart the existing
operator on the committed build and verify its fresh artifacts. The resident
PaperOps owner, not the integration probe, may submit eligible paper orders.

Operational readiness, a research hypothesis, an accepted router handoff and a
broker-confirmed fill are different outcomes. Report the actual terminal state,
including idle or blocked, without promising a trade or profitable performance.
